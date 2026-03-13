"""
sentence_understanding.py
Camada 5 — Sentence Understanding Layer

Interpreta decisões jurídicas em linguagem natural retornadas pela IA
e as transforma em estruturas de dados padronizadas.

Consumido pelo processor.py após a chamada ao Gemini.
"""

import re
import logging
from typing import Optional
from datetime import datetime

from services.normalizer import normalizar, normalizar_lista

logger = logging.getLogger("[UNDERSTAND]")

# ---------------------------------------------------------------------------
# Status possíveis de uma verba
# ---------------------------------------------------------------------------

STATUS_DEFERIDA   = "DEFERIDA"
STATUS_INDEFERIDA = "INDEFERIDA"
STATUS_PARCIAL    = "PARCIAL"

# ---------------------------------------------------------------------------
# Padrões regex de apoio
# ---------------------------------------------------------------------------

_PADROES_DEFERIDA = [
    r"\bdeferid[oa]\b",
    r"\bcondenad[oa]\b",
    r"\bprocedente\b",
    r"\bpagamento de\b",
    r"\bdevo pagar\b",
    r"\bfica condenad[oa]\b",
]

_PADROES_INDEFERIDA = [
    r"\bindeferid[oa]\b",
    r"\bimprocedente\b",
    r"\bnão há\b",
    r"\bnão faz jus\b",
    r"\bnão se reconhece\b",
    r"\bnão reconheço\b",
    r"\bafasto\b",
    r"\brejeito\b",
]

_PADROES_PERCENTUAL = [
    r"(\d{1,3})\s*%",
    r"adicional de\s+(\d{1,3})\s*(?:por cento|%)",
]

_PADROES_DATA = [
    r"(\d{2})[\/\-\.](\d{2})[\/\-\.](\d{4})",
    r"(\d{4})[\/\-\.](\d{2})[\/\-\.](\d{2})",
]

_REFLEXOS_CONHECIDOS = [
    "férias", "férias proporcionais", "férias + 1/3",
    "décimo terceiro", "13°", "13º",
    "fgts", "dsr", "repouso semanal",
    "aviso prévio", "verbas rescisórias",
]

# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------

def extrair_verbas_deferidas(texto: str) -> list[dict]:
    """
    Identifica verbas deferidas e indeferidas no texto da IA.
    Retorna lista de dicts com nome normalizado e status.
    """
    if not texto:
        return []

    verbas = []
    linhas = _segmentar_texto(texto)

    for linha in linhas:
        status = _detectar_status(linha)
        if status is None:
            continue

        # Tenta extrair o nome da verba da linha
        nome_raw = _extrair_nome_verba(linha)
        if not nome_raw:
            continue

        nome_normalizado = normalizar(nome_raw) or nome_raw

        verba = {
            "nome_original": nome_raw,
            "nome": nome_normalizado,
            "status": status,
            "linha_fonte": linha.strip(),
        }

        verbas.append(verba)
        logger.debug(f"Verba extraída: {nome_normalizado} → {status}")

    return verbas


def extrair_reflexos(texto: str) -> list[str]:
    """
    Extrai reflexos mencionados no texto (ex: 'refletindo em férias, 13º e FGTS').
    Retorna lista de chaves normalizadas.
    """
    if not texto:
        return []

    texto_lower = texto.lower()
    reflexos_raw = []

    # Busca padrão: "refletindo em X, Y e Z" ou "com reflexos em X"
    padroes = [
        r"refletind[oa]\s+em\s+(.+?)(?:\.|$)",
        r"com reflexos\s+em\s+(.+?)(?:\.|$)",
        r"reflexos\s+em\s+(.+?)(?:\.|$)",
        r"repercutind[oa]\s+em\s+(.+?)(?:\.|$)",
    ]

    for padrao in padroes:
        match = re.search(padrao, texto_lower)
        if match:
            trecho = match.group(1)
            # Separa por vírgula e "e"
            itens = re.split(r',|\se\s', trecho)
            reflexos_raw.extend([i.strip() for i in itens if i.strip()])
            break

    # Busca direta por reflexos conhecidos se padrão não encontrado
    if not reflexos_raw:
        for reflexo in _REFLEXOS_CONHECIDOS:
            if reflexo in texto_lower:
                reflexos_raw.append(reflexo)

    return normalizar_lista(reflexos_raw)


def extrair_adicionais(texto: str) -> dict[str, float]:
    """
    Extrai percentuais de adicionais mencionados no texto.
    Retorna dict: tipo_adicional → valor_percentual (float).
    """
    if not texto:
        return {}

    adicionais = {}
    texto_lower = texto.lower()

    mapeamento = {
        "insalubridade":    "adicional_insalubridade",
        "periculosidade":   "adicional_periculosidade",
        "noturno":          "adicional_noturno",
        "hora extra":       "adicional_hora_extra",
        "horas extras":     "adicional_hora_extra",
        "transferência":    "adicional_transferencia",
    }

    for termo, chave in mapeamento.items():
        if termo in texto_lower:
            percentual = _extrair_percentual_proximo(texto_lower, termo)
            if percentual is not None:
                adicionais[chave] = percentual

    return adicionais


def extrair_periodos(texto: str) -> Optional[dict]:
    """
    Extrai período (data início e fim) mencionado no texto.
    Retorna dict {inicio, fim} com datas em formato ISO (YYYY-MM-DD) ou None.
    """
    if not texto:
        return None

    datas = _extrair_todas_datas(texto)

    if len(datas) >= 2:
        return {"inicio": datas[0], "fim": datas[-1]}
    elif len(datas) == 1:
        return {"inicio": datas[0], "fim": None}

    return None


def extrair_base_calculo(texto: str) -> Optional[str]:
    """
    Identifica a base de cálculo mencionada no texto.
    Retorna chave padronizada ou None.
    """
    if not texto:
        return None

    texto_lower = texto.lower()

    bases = {
        "salário hora":         "salario_hora",
        "valor hora":           "salario_hora",
        "salário base":         "salario_base",
        "salário contratual":   "salario_base",
        "última remuneração":   "ultima_remuneracao",
        "remuneração":          "ultima_remuneracao",
        "salário mínimo":       "salario_minimo",
    }

    for termo, chave in bases.items():
        if termo in texto_lower:
            return chave

    return None


def interpretar_decisao(texto_ia: str) -> dict:
    """
    Função principal — recebe o texto completo retornado pela IA
    e retorna estrutura de decisão jurídica completa.
    """
    logger.info("Iniciando interpretação da decisão jurídica...")

    resultado = {
        "verbas":       extrair_verbas_deferidas(texto_ia),
        "reflexos":     extrair_reflexos(texto_ia),
        "adicionais":   extrair_adicionais(texto_ia),
        "periodo":      extrair_periodos(texto_ia),
        "base_calculo": extrair_base_calculo(texto_ia),
    }

    logger.info(
        f"Interpretação concluída — "
        f"{len(resultado['verbas'])} verbas, "
        f"{len(resultado['reflexos'])} reflexos"
    )

    return resultado


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _segmentar_texto(texto: str) -> list[str]:
    """Divide o texto em segmentos por pontuação e quebras de linha."""
    segmentos = re.split(r'[;\n]|(?<=[a-záéíóúãõ])\.\s', texto, flags=re.IGNORECASE)
    return [s.strip() for s in segmentos if s.strip()]


def _detectar_status(texto: str) -> Optional[str]:
    """Detecta se o trecho indica deferimento, indeferimento ou parcial."""
    texto_lower = texto.lower()

    tem_deferida   = any(re.search(p, texto_lower) for p in _PADROES_DEFERIDA)
    tem_indeferida = any(re.search(p, texto_lower) for p in _PADROES_INDEFERIDA)

    if tem_deferida and tem_indeferida:
        return STATUS_PARCIAL
    if tem_deferida:
        return STATUS_DEFERIDA
    if tem_indeferida:
        return STATUS_INDEFERIDA

    return None


def _extrair_nome_verba(texto: str) -> Optional[str]:
    """
    Tenta extrair o nome da verba de um trecho de texto.
    Busca por verbas conhecidas no normalizer.
    """
    from services.normalizer import MAPA_NORMALIZACAO

    texto_lower = texto.lower()
    melhor = None
    maior_len = 0

    for padrao in MAPA_NORMALIZACAO.keys():
        if padrao in texto_lower and len(padrao) > maior_len:
            melhor = padrao
            maior_len = len(padrao)

    return melhor


def _extrair_percentual_proximo(texto: str, termo: str) -> Optional[float]:
    """Extrai o percentual mais próximo de um termo no texto."""
    idx = texto.find(termo)
    if idx == -1:
        return None

    trecho = texto[max(0, idx - 30): idx + 60]

    for padrao in _PADROES_PERCENTUAL:
        match = re.search(padrao, trecho)
        if match:
            return float(match.group(1))

    return None


def _extrair_todas_datas(texto: str) -> list[str]:
    """Extrai todas as datas do texto e retorna em formato ISO."""
    datas = []

    for padrao in _PADROES_DATA:
        for match in re.finditer(padrao, texto):
            grupos = match.groups()
            try:
                if len(grupos[0]) == 4:
                    # YYYY-MM-DD
                    dt = datetime(int(grupos[0]), int(grupos[1]), int(grupos[2]))
                else:
                    # DD/MM/YYYY
                    dt = datetime(int(grupos[2]), int(grupos[1]), int(grupos[0]))
                datas.append(dt.strftime("%Y-%m-%d"))
            except ValueError:
                continue

    # Remove duplicatas mantendo ordem
    vistas = set()
    return [d for d in datas if not (d in vistas or vistas.add(d))]

"""
calculation_parameters.py
Camada 7 — Calculation Parameters

Transforma decisões jurídicas estruturadas (saída do sentence_understanding)
em parâmetros numéricos prontos para uso no PJeCalc ou motor de cálculo.
"""

import math
import logging
from typing import Optional

logger = logging.getLogger("[CALC_PARAMS]")

# ---------------------------------------------------------------------------
# Mapa de divisores de jornada
# ---------------------------------------------------------------------------

MAPA_DIVISORES: dict[int, int] = {
    30: 150,
    35: 175,
    36: 180,
    40: 200,
    44: 220,
}

# ---------------------------------------------------------------------------
# Alíquotas padrão
# ---------------------------------------------------------------------------

ALIQUOTA_FGTS          = 0.08
MULTA_FGTS             = 0.40
ALIQUOTA_FERIAS        = 1 / 3   # terço constitucional
ADICIONAL_HE_PADRAO    = 0.50    # 50% — art. 7º, XVI CF
ADICIONAL_HE_DSR       = 0.50    # mesmo percentual para DSR


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def gerar_parametros(dados_extracao: dict) -> dict:
    """
    Recebe o dict completo da extração (saída do processor)
    e retorna parâmetros numéricos estruturados para cálculo.
    """
    logger.info("Gerando parâmetros de cálculo...")

    parametros = {
        "periodo":  _calcular_periodo(dados_extracao),
        "jornada":  _calcular_jornada(dados_extracao),
        "verbas":   _estruturar_verbas(dados_extracao),
        "indices":  _determinar_indices(dados_extracao),
        "fgts":     _calcular_fgts(dados_extracao),
        "inss":     _determinar_inss(dados_extracao),
        "honorarios": _calcular_honorarios(dados_extracao),
    }

    logger.info("Parâmetros de cálculo gerados com sucesso.")
    return parametros


# ---------------------------------------------------------------------------
# Período
# ---------------------------------------------------------------------------

def _calcular_periodo(dados: dict) -> dict:
    """Calcula meses e avos a partir das datas de admissão e demissão."""
    admissao  = dados.get("data_admissao")
    demissao  = dados.get("data_demissao")
    meses     = None
    avos      = None

    if admissao and demissao:
        try:
            from datetime import date
            fmt = "%Y-%m-%d"
            d_adm = date.fromisoformat(admissao)
            d_dem = date.fromisoformat(demissao)
            delta_meses = (
                (d_dem.year - d_adm.year) * 12 +
                (d_dem.month - d_adm.month)
            )
            # Avos: se passou de 14 dias no último mês, conta o mês
            if d_dem.day >= 15:
                delta_meses += 1
            meses = max(delta_meses, 0)
            avos  = meses % 12 if meses >= 12 else meses
        except (ValueError, TypeError):
            logger.warning("Erro ao calcular período — datas inválidas.")

    return {
        "inicio": admissao,
        "fim":    demissao,
        "meses":  meses,
        "avos":   avos,
    }


# ---------------------------------------------------------------------------
# Jornada
# ---------------------------------------------------------------------------

def calcular_divisor(horas_semanais: int) -> int:
    """
    Retorna o divisor de jornada correspondente às horas semanais.
    Fallback: fórmula CLT — ceil((horas / 6) * 30).
    """
    if horas_semanais in MAPA_DIVISORES:
        return MAPA_DIVISORES[horas_semanais]
    divisor = math.ceil((horas_semanais / 6) * 30)
    logger.debug(f"Divisor calculado por fórmula: {horas_semanais}h → {divisor}")
    return divisor


def _calcular_jornada(dados: dict) -> dict:
    """Determina jornada contratual e divisor."""
    jornada_raw = dados.get("jornada_contratual", "")
    horas       = _extrair_horas_jornada(jornada_raw)

    if horas is None:
        horas = 44  # padrão CLT

    divisor = calcular_divisor(horas)

    # Horas extras diárias (acima da 8ª)
    horas_dia       = round(horas / 6, 2)
    he_diaria       = round(horas_dia - 8, 2) if horas_dia > 8 else 0.0

    return {
        "contratual_horas": horas,
        "divisor":          divisor,
        "horas_dia":        horas_dia,
        "horas_extras_diaria": he_diaria,
    }


def _extrair_horas_jornada(texto: str) -> Optional[int]:
    """Extrai número de horas semanais de um texto como '44h semanais'."""
    import re
    if not texto:
        return None
    match = re.search(r"(\d{2})\s*h", str(texto).lower())
    if match:
        return int(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Verbas
# ---------------------------------------------------------------------------

def _estruturar_verbas(dados: dict) -> list[dict]:
    """
    Estrutura cada verba deferida com adicional, base e reflexos.
    """
    verbas_raw = dados.get("verbas_deferidas", [])
    if not verbas_raw:
        # Tenta ler do campo padrão do extrator
        verbas_raw = dados.get("verbas", [])

    verbas = []
    for v in verbas_raw:
        nome    = v.get("nome") or v.get("nome_normalizado", "")
        status  = v.get("status", "DEFERIDA")

        if status != "DEFERIDA":
            continue

        verba = {
            "nome":     nome,
            "adicional": _determinar_adicional(v, dados),
            "base":      _determinar_base(v),
            "reflexos":  _determinar_reflexos(v, dados),
            "periodo":   v.get("periodo") or {
                "inicio": dados.get("data_admissao"),
                "fim":    dados.get("data_demissao"),
            },
        }
        verbas.append(verba)

    return verbas


def _determinar_adicional(verba: dict, dados: dict) -> float:
    """Determina o multiplicador de adicional da verba."""
    percentual = verba.get("percentual") or verba.get("adicional_percentual")

    if percentual:
        try:
            return 1 + (float(percentual) / 100)
        except (ValueError, TypeError):
            pass

    nome = verba.get("nome", "")

    if "horas_extras" in nome:
        return 1 + ADICIONAL_HE_PADRAO
    if "insalubridade" in nome:
        salario_minimo = dados.get("salario_minimo", 1518.00)
        grau = verba.get("grau_insalubridade", "medio")
        graus = {"minimo": 0.10, "medio": 0.20, "maximo": 0.40}
        return salario_minimo * graus.get(grau, 0.20)
    if "periculosidade" in nome:
        return 0.30  # 30% sobre salário base

    return 1.0


def _determinar_base(verba: dict) -> str:
    """Determina a base de cálculo da verba."""
    base = verba.get("base_calculo") or verba.get("base")

    if base:
        return base

    nome = verba.get("nome", "")

    if "horas_extras" in nome:
        return "salario_hora"
    if "insalubridade" in nome:
        return "salario_minimo"
    if "periculosidade" in nome:
        return "salario_base"
    if "dano" in nome:
        return "valor_fixado"

    return "salario_base"


def _determinar_reflexos(verba: dict, dados: dict) -> list[str]:
    """Determina reflexos da verba com base na sentença e nas súmulas."""
    reflexos = verba.get("reflexos", [])

    if reflexos:
        return reflexos

    nome = verba.get("nome", "")

    # Reflexos padrão por Súmula 264 TST
    if "horas_extras" in nome:
        return ["dsr", "ferias_proporcionais", "decimo_terceiro", "fgts_depositos"]
    if "adicional_noturno" in nome:
        return ["dsr", "ferias_proporcionais", "decimo_terceiro", "fgts_depositos"]
    if "dsr" in nome:
        # OJ 394 — DSR não reflete em férias/13º/FGTS
        return []

    return []


# ---------------------------------------------------------------------------
# Índices
# ---------------------------------------------------------------------------

def _determinar_indices(dados: dict) -> dict:
    """Determina índices de correção e juros conforme ADC 58."""
    indice_raw = str(dados.get("indice_correcao", "")).upper()
    juros_raw  = str(dados.get("juros_mora", "")).upper()

    indice = "IPCAE"
    if "TR" in indice_raw:
        indice = "TR"
    elif "IPCA" in indice_raw:
        indice = "IPCAE"

    juros = "SELIC"
    if "1%" in juros_raw or "1 %" in juros_raw:
        juros = "1%_ao_mes"

    return {
        "correcao":          indice,
        "juros":             juros,
        "juros_a_partir_de": "data_ajuizamento",
        "fundamento":        "ADC 58 STF — IPCA-E até ajuizamento, SELIC após",
    }


# ---------------------------------------------------------------------------
# FGTS
# ---------------------------------------------------------------------------

def _calcular_fgts(dados: dict) -> dict:
    """Estrutura parâmetros de FGTS com fundamentos jurídicos."""
    incide_ap = dados.get("fgts_sobre_aviso_previo", True)

    return {
        "aliquota":                  ALIQUOTA_FGTS,
        "multa":                     MULTA_FGTS,
        "incide_sobre_aviso_previo": incide_ap,
        "fundamento_ap":             "Súmula 305 TST",
        "nao_incide_ferias_indenizadas": True,
        "fundamento_ferias":         "OJ 195 SDI-I TST",
        "multa_nao_incide_ap_indenizado": True,
        "fundamento_multa_ap":       "OJ 42 SDI-I TST",
    }


# ---------------------------------------------------------------------------
# INSS
# ---------------------------------------------------------------------------

def _determinar_inss(dados: dict) -> dict:
    """Determina parâmetros de desconto previdenciário."""
    contrib = dados.get("contribuicao_previdenciaria", True)

    return {
        "descontar":  contrib,
        "teto":       7786.02,
        "fundamento": "Lei 8.212/1991 — tabela progressiva INSS",
    }


# ---------------------------------------------------------------------------
# Honorários
# ---------------------------------------------------------------------------

def _calcular_honorarios(dados: dict) -> dict:
    """Estrutura parâmetros de honorários advocatícios."""
    percentual_raw = dados.get("percentual_honorarios")
    tem_honorarios = dados.get("honorarios_sucumbenciais", False)

    percentual = None
    if percentual_raw:
        try:
            percentual = float(percentual_raw)
        except (ValueError, TypeError):
            percentual = None

    return {
        "devidos":     tem_honorarios,
        "percentual":  percentual,
        "faixa_legal": "5% a 15%",
        "fundamento":  "Art. 791-A CLT",
    }

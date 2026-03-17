"""
parecer_engine.py

Responsável pela geração do Parecer Técnico completo e da seção
"I. PARCELAS APURADAS" (texto pericial), separado do ExplanationEngine.

Mantém o contrato público usado pelo processor:
- gerar_parecer_parcelas_apuradas
- gerar_parecer_tecnico_completo
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from .explanation_engine import (
    TEXTOS_PADRAO_CRITERIOS_PARECER,
    obter_textos_padrao_criterios_parecer,
)


def _is_fgts_verba(nome: str) -> bool:
    nome = (nome or "").lower()
    return "fgts" in nome or "fundo de garantia" in nome


def _reflexos_contem_fgts(reflexos: List[str]) -> bool:
    if not reflexos:
        return False
    for r in reflexos:
        if "fgts" in (r or "").lower():
            return True
    return False


def _eh_verba_principal(nome: str) -> bool:
    n = (nome or "").lower()
    return any(
        p in n
        for p in [
            "insalubridade",
            "hora extra",
            "horas extras",
            "intervalo intrajornada",
            "intervalo intra",
            "férias",
            "13",
            "décimo terceiro",
            "aviso prévio",
        ]
    )


def _classificar_verba(nome: str) -> str | None:
    n = (nome or "").lower()
    if "insalubridade" in n:
        return "insalubridade"
    if "hora extra" in n or "horas extras" in n:
        return "horas_extras"
    if "intervalo" in n:
        return "intervalo"
    return None


def _agrupar_verbas_para_parecer(verbas: List[dict]) -> List[dict]:
    """
    Agrupa verbas de 13º e férias em um item cada para o parecer,
    mantendo as demais individualmente.
    """
    outras: List[dict] = []
    verba_13: dict | None = None
    verba_ferias: dict | None = None

    for v in verbas:
        nome = (v.get("nome") or "").lower()
        if "13" in nome or "décimo terceiro" in nome:
            if not verba_13:
                verba_13 = {
                    "nome_display": "13º salário",
                    "reflexos": list(v.get("reflexos") or []),
                }
        elif "férias" in nome or "ferias" in nome:
            if not verba_ferias:
                verba_ferias = {
                    "nome_display": "Férias + 1/3",
                    "reflexos": list(v.get("reflexos") or []),
                }
        else:
            outras.append({"nome_display": v.get("nome") or "Verba", "reflexos": v.get("reflexos") or []})

    agrupadas: List[dict] = []
    if verba_13:
        agrupadas.append(verba_13)
    if verba_ferias:
        agrupadas.append(verba_ferias)
    agrupadas.extend(outras)
    return agrupadas


def _formatar_reflexos(reflexos: List[str], fgts_na_condenacao: bool) -> str:
    if not reflexos:
        return ""
    base = [r for r in reflexos if isinstance(r, str) and r.strip()]
    if fgts_na_condenacao and "FGTS" not in " ".join(base):
        base.append("FGTS + 40%")
    if not base:
        return ""
    if len(base) == 1:
        return f"em {base[0]}"
    return "em " + ", ".join(base[:-1]) + " e " + base[-1]


def _normalizar_texto_reflexos(texto: str) -> str:
    if not texto:
        return texto
    texto = texto.replace("reflexos reflexos", "reflexos")
    texto = texto.replace("com reflexos, com reflexos", "com reflexos")
    return texto


def gerar_parecer_parcelas_apuradas(
    verbas_deferidas: List[dict],
    dados: dict,
) -> Dict[str, Any]:
    """
    Gera a seção "I. PARCELAS APURADAS" no formato da perita.
    Mantém o mesmo contrato usado por processor.py.
    """
    verbas = list(verbas_deferidas) if verbas_deferidas else []
    dados = dados or {}

    intro = "Foram apuradas as parcelas de acordo com as decisões, conforme relatado a seguir:"
    itens: List[Dict[str, str]] = []
    alinea_idx = 0

    fgts_na_condenacao = any(
        _is_fgts_verba(v.get("nome") if isinstance(v, dict) else getattr(v, "nome", ""))
        for v in verbas
    ) or any(
        _reflexos_contem_fgts(
            v.get("reflexos") if isinstance(v, dict) else getattr(v, "reflexos", []) or [],
        )
        for v in verbas
    )

    divisor_geral = dados.get("divisor_horas")
    divisor_txt = str(divisor_geral) if divisor_geral else "120/180"
    divisor_intervalo = "180"
    data_intervalo = "01/07/2017"

    ordem_tipos = ["insalubridade", "horas_extras", "intervalo"]
    verbas_por_tipo: Dict[str, dict] = {}
    outras_principais: List[dict] = []
    for v in verbas:
        if not isinstance(v, dict):
            continue
        nome = v.get("nome") or ""
        if not _eh_verba_principal(nome):
            continue
        tipo = _classificar_verba(nome)
        if tipo:
            if tipo not in verbas_por_tipo:
                verbas_por_tipo[tipo] = v
        else:
            outras_principais.append(v)

    for tipo in ordem_tipos:
        v = verbas_por_tipo.get(tipo)
        if not v:
            continue
        nome = v.get("nome") or "Verba"
        reflexos_raw = v.get("reflexos")
        reflexos_lista = list(reflexos_raw) if isinstance(reflexos_raw, (list, tuple)) else []

        if tipo == "insalubridade":
            reflexos_str = _formatar_reflexos(reflexos_lista, fgts_na_condenacao)
            titulo = "ADICIONAL DE INSALUBRIDADE E REFLEXOS" if reflexos_str else "ADICIONAL DE INSALUBRIDADE"
            if reflexos_str:
                texto = f"Apuração do adicional de insalubridade, com reflexos no {reflexos_str}"
            else:
                texto = "Apuração do adicional de insalubridade;"
        elif tipo == "horas_extras":
            reflexos_str = _formatar_reflexos(reflexos_lista, fgts_na_condenacao)
            titulo = "HORAS EXTRAS E REFLEXOS" if reflexos_str else "HORAS EXTRAS"
            pct = str((v.get("percentual") or "50")).strip()
            texto = (
                f"Apuração das horas extras durante todo o contrato de trabalho, "
                f"utilizadas as Súmulas 264 e 347 do TST, observado o divisor {divisor_txt}, "
                f"com percentual de {pct}%"
            )
            if reflexos_str:
                texto += f", com reflexos {reflexos_str}"
            else:
                texto += ";"
        else:
            reflexos_str = _formatar_reflexos(reflexos_lista, fgts_na_condenacao)
            titulo = "INTERVALO INTRAJORNADA E REFLEXOS" if reflexos_str else "INTERVALO INTRAJORNADA"
            pct = str((v.get("percentual") or "60")).strip()
            texto = (
                f"Apuração do intervalo intrajornada a partir de {data_intervalo}, "
                f"utilizadas as Súmulas 264 e 347 do TST, observado o divisor {divisor_intervalo}, "
                f"com percentual de {pct}%"
            )
            if reflexos_str:
                texto += f", com reflexos {reflexos_str}"
            else:
                texto += ";"

        texto = _normalizar_texto_reflexos(texto)
        letra = chr(97 + alinea_idx)
        alinea_idx += 1
        itens.append({"alinea": letra, "titulo": titulo, "texto": texto})

    agrupadas = _agrupar_verbas_para_parecer(outras_principais)
    for item in agrupadas:
        nome_display = item.get("nome_display") or "Verba"
        reflexos_lista = item.get("reflexos") or []
        reflexos_str = _formatar_reflexos(reflexos_lista, fgts_na_condenacao)
        titulo_base = nome_display.upper()
        if titulo_base.endswith(" REFLEXOS"):
            titulo = titulo_base
        else:
            titulo = titulo_base + " E REFLEXOS" if reflexos_str else titulo_base
        if reflexos_str:
            texto = f"Apuração de {nome_display}, com reflexos no {reflexos_str}"
        else:
            texto = f"Apuração de {nome_display};"
        texto = _normalizar_texto_reflexos(texto)
        letra = chr(97 + alinea_idx)
        alinea_idx += 1
        itens.append({"alinea": letra, "titulo": titulo, "texto": texto})

    valor_pericia = dados.get("honorarios_periciais_valor") or dados.get("honorarios_periciais")
    if valor_pericia:
        valor_txt = str(valor_pericia).strip()
        if not re.search(r"R\$\s*[\d.,]+", valor_txt, re.IGNORECASE):
            valor_txt = f"R$ {valor_txt}"
    else:
        valor_txt = "no valor definido na sentença"
    letra = chr(97 + alinea_idx)
    alinea_idx += 1
    itens.append(
        {
            "alinea": letra,
            "titulo": "HONORÁRIOS PERICIAIS",
            "texto": f"Apuração dos honorários periciais no valor de {valor_txt};",
        }
    )

    pct_hon = dados.get("percentual_honorarios") or "5"
    pct_hon = str(pct_hon).strip().replace("%", "")
    letra = chr(97 + alinea_idx)
    alinea_idx += 1
    itens.append(
        {
            "alinea": letra,
            "titulo": "HONORÁRIOS SUCUMBENCIAIS",
            "texto": f"Honorários sucumbenciais no percentual de {pct_hon}% sobre o valor da condenação;",
        }
    )

    return {"intro": intro, "itens": itens}


def _load_skill_parecer_pericial() -> str:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    skill_path = os.path.join(base_dir, "skills", "parecer_pericial.md")
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return (
            "Manual mínimo de redação do parecer pericial:\n"
            "- Iniciar as frases com 'Apuração'.\n"
            "- Usar numeração alfabética a), b), c).\n"
            "- Agrupar reflexos no final com 'com reflexos em ...'.\n"
        )


def gerar_parecer_tecnico_completo(
    dados: Dict[str, Any],
    verbas_deferidas: List[dict],
) -> Dict[str, Any]:
    """
    Gera o parecer técnico completo (texto contínuo) usando:
    - Cabeçalho padrão do processo;
    - Seção I (slot IA) + Seção II (TEXTOS_PADRAO_CRITERIOS_PARECER).
    """
    from services.ai_client import gerar_parcelas_parecer

    dados = dados or {}
    numero = dados.get("numero_processo") or "processo"
    reclamante = dados.get("reclamante") or "reclamante"
    reclamada = dados.get("reclamada") or "reclamada"

    cabecalho = (
        f"Processo nº {numero}\n"
        f"Reclamante: {reclamante}\n"
        f"Reclamada: {reclamada}\n\n"
        "O(a) perito(a) abaixo assinado(a) vem, respeitosamente, apresentar o presente parecer técnico:\n\n"
    )

    skill_text = _load_skill_parecer_pericial()
    ia_result = gerar_parcelas_parecer(verbas_deferidas or [], dados, skill_text)
    parcelas_txt = ia_result.get("texto") or ""

    criterios = obter_textos_padrao_criterios_parecer()
    bloco_criterios = (
        "II. CRITÉRIOS ADOTADOS PARA OS CÁLCULOS:\n\n"
        f"{criterios.get('correcao','')}\n\n"
        f"{criterios.get('inss','')}\n\n"
        f"{criterios.get('irrf','')}\n"
    ).strip()

    parecer_completo = (
        f"{cabecalho}"
        "I. PARCELAS APURADAS:\n"
        f"{parcelas_txt.strip()}\n\n"
        f"{bloco_criterios}"
    ).strip()

    return {
        "texto": parecer_completo,
        "parcelas": parcelas_txt.strip(),
        "model_used": ia_result.get("model_used"),
        "error": ia_result.get("error"),
    }


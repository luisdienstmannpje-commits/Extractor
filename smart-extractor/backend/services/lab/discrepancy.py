"""
discrepancy.py — Confronto Sentença vs. Cálculo e filtros de falsos-positivos (Passo 4).

Função mestre: gerar_relatorio_discrepancia — compara sentença, liquidação e manifestação;
gera discrepâncias (verba_ausente, índice, juros) e aprendizados.
Auxiliares: verba_corresponde_na_liquidacao (canonização + substring + fuzzy);
Guardrails: filtrar_falsos_positivos_verba_ausente, filtrar_logicas_verba_ausente_falsas,
filtrar_aprendizados_verba_ausente_falsas — usam LegalRule._canonizar_verba para evitar
falsos positivos quando a verba já existe na liquidação/PJC.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

from rapidfuzz import fuzz as rapidfuzz_fuzz

from services.legal_engine.rule_base import LegalRule

try:
    from config import settings
    _FUZZ_THRESHOLD = getattr(settings, "RAPIDFUZZ_THRESHOLD", 85)
except Exception:
    _FUZZ_THRESHOLD = 85


def verba_corresponde_na_liquidacao(
    verba_sentenca: str,
    verbas_liq_norm: List[str],
    verbas_liq_canon: Set[str],
    threshold: Optional[int] = None,
) -> bool:
    """
    Verifica se a verba da sentença tem correspondente na liquidação.
    (1) Match canonizado: obrigatório — só considera ausente se não houver match canonizado.
    (2) Substring e fuzzy como fallback para nomes fora do mapa de canonização.
    """
    if not (verba_sentenca or "").strip():
        return False
    if not verbas_liq_norm and not verbas_liq_canon:
        return False
    nome_sent = (verba_sentenca or "").strip()
    canon_sent = LegalRule._canonizar_verba(nome_sent)
    if canon_sent and verbas_liq_canon and canon_sent in verbas_liq_canon:
        return True
    nome_norm = nome_sent.lower()
    for v in verbas_liq_norm:
        if v and (nome_norm in v or v in nome_norm):
            return True
    limiar = threshold if threshold is not None else _FUZZ_THRESHOLD
    for v in verbas_liq_norm:
        if not v:
            continue
        if rapidfuzz_fuzz.token_set_ratio(nome_norm, v) >= limiar:
            return True
    return False


def _campos_chave_sentenca(dados: dict) -> dict:
    chaves = [
        "numero_processo", "reclamante", "reclamada", "data_sentenca",
        "salario_base", "data_admissao", "data_demissao", "indice_correcao",
        "juros_mora", "divisor_horas",
    ]
    return {k: dados.get(k) for k in chaves if dados.get(k)}


def _sugerir_correcao_verba(verba: str, manifestacao: dict) -> str:
    texto = manifestacao.get("texto_bruto") or ""
    trecho = ""
    verba_norm = (verba or "").lower()
    for linha in texto.split("\n"):
        if verba_norm in (linha or "").lower() and len(linha) > 20:
            trecho = linha.strip()[:200]
            break
    if trecho:
        return f"Incluir verba conforme sentença. Trecho da manifestação: {trecho}"
    return f"Incluir {verba} no cálculo conforme determinado na sentença"


def _buscar_fundamento_para_verba(verba: str, manifestacao: dict) -> str:
    fundamentos = manifestacao.get("fundamentos_juridicos") or []
    if fundamentos:
        return "; ".join(fundamentos[:3])
    return "Verificar fundamentação na manifestação"


def _extrair_aprendizados(
    dados_sentenca: dict,
    dados_liquidacao: dict,
    dados_manifestacao: dict,
    discrepancias: list,
) -> List[Dict]:
    """
    Cada discrepância com fundamento gera um aprendizado potencial:
    - tipo "regra"    → candidato a nova regra em legal_engine/rules/
    - tipo "playbook" → candidato a exemplo few-shot no skill
    """
    aprendizados = []
    for disc in discrepancias:
        fundamento = disc.get("fundamento") or ""
        if fundamento and disc.get("nivel") == "ERRO":
            aprendizados.append({
                "tipo": "regra",
                "titulo": f"Discrepância: {disc['tipo']}",
                "descricao": disc["juiz_disse"],
                "correcao": disc["juliana_corrigiu"],
                "base_legal": fundamento,
                "nivel_sugerido": "ERRO",
                "prioridade_sugerida": 40,
            })
    fundamentos_doc = dados_manifestacao.get("fundamentos_juridicos") or []
    tipos_cobertos = {d.get("fundamento") for d in discrepancias}
    for fund in fundamentos_doc:
        if fund not in tipos_cobertos:
            aprendizados.append({
                "tipo": "playbook",
                "titulo": f"Fundamento jurídico identificado: {fund}",
                "descricao": "Fundamento mencionado na manifestação da perita",
                "base_legal": fund,
            })
    return aprendizados


def gerar_relatorio_discrepancia(
    dados_sentenca: Dict,
    dados_liquidacao: Dict,
    dados_manifestacao: Dict,
) -> Dict[str, Any]:
    """
    Compara os 3 conjuntos de dados e gera o relatório de discrepâncias:
    "O juiz disse A, a empresa calculou B, a Juliana corrigiu para C usando D"
    """
    discrepancias = []

    _dados = dados_sentenca.get("dados") or {}
    _verbas_raw = _dados.get("verbas_deferidas") or _dados.get("verbas") or []
    verbas_sentenca = [
        (v.get("nome") or "").strip() for v in _verbas_raw
        if isinstance(v, dict) and (v.get("nome") or "").strip()
    ]
    if not verbas_sentenca and _verbas_raw:
        verbas_sentenca = [str(v).strip() for v in _verbas_raw if str(v).strip()]
    verbas_liquidacao_raw = dados_liquidacao.get("verbas_calculadas") or []
    verbas_liquidacao = [str(v or "").strip() for v in verbas_liquidacao_raw if str(v or "").strip()]
    verbas_liq_norm = [v.lower() for v in verbas_liquidacao]
    verbas_liq_canon = {LegalRule._canonizar_verba(v) for v in verbas_liquidacao}

    for verba in verbas_sentenca:
        if not verba:
            continue
        presente = verba_corresponde_na_liquidacao(verba, verbas_liq_norm, verbas_liq_canon)
        if not presente:
            discrepancias.append({
                "tipo": "verba_ausente",
                "nivel": "ERRO",
                "juiz_disse": f"Deferido: {verba}",
                "empresa_calculou": "Verba ausente no arquivo de liquidação",
                "juliana_corrigiu": _sugerir_correcao_verba(verba, dados_manifestacao),
                "fundamento": _buscar_fundamento_para_verba(verba, dados_manifestacao),
            })

    indice_sentenca = (dados_sentenca.get("dados") or {}).get("indice_correcao") or ""
    indice_liq = dados_liquidacao.get("indice_correcao") or ""
    if indice_sentenca and indice_liq:
        n_sent = indice_sentenca.upper().replace("-", "").replace("_", "")
        n_liq = indice_liq.upper().replace("-", "").replace("_", "")
        if n_sent not in n_liq and n_liq not in n_sent:
            discrepancias.append({
                "tipo": "indice_correcao",
                "nivel": "ERRO",
                "juiz_disse": f"Índice de correção: {indice_sentenca}",
                "empresa_calculou": f"Índice utilizado no cálculo: {indice_liq}",
                "juliana_corrigiu": "Corrigir índice para o determinado na sentença",
                "fundamento": "ADC 58 / Súmula 439 TST",
            })

    juros_sentenca = (dados_sentenca.get("dados") or {}).get("juros_mora") or ""
    juros_liq = dados_liquidacao.get("juros_mora") or ""
    if juros_sentenca and juros_liq:
        if juros_sentenca.lower() not in juros_liq.lower() and juros_liq.lower() not in juros_sentenca.lower():
            discrepancias.append({
                "tipo": "juros_mora",
                "nivel": "AVISO",
                "juiz_disse": f"Juros de mora: {juros_sentenca}",
                "empresa_calculou": f"Juros no cálculo: {juros_liq}",
                "juliana_corrigiu": "Corrigir taxa de juros conforme ADC 58",
                "fundamento": "ADC 58 / Art. 39 da Lei 8.177/91",
            })

    aprendizados = _extrair_aprendizados(
        dados_sentenca, dados_liquidacao, dados_manifestacao, discrepancias
    )

    numero_processo = (dados_sentenca.get("dados") or {}).get("numero_processo") or "desconhecido"

    return {
        "numero_processo": numero_processo,
        "data_analise": datetime.now().isoformat(),
        "resumo": {
            "verbas_sentenca": len(verbas_sentenca),
            "verbas_liquidacao": len(verbas_liquidacao),
            "discrepancias_encontradas": len(discrepancias),
        },
        "sentenca": {
            "doc_type": dados_sentenca.get("doc_type"),
            "model_used": dados_sentenca.get("model_used"),
            "campos_chave": _campos_chave_sentenca(dados_sentenca.get("dados") or {}),
            "verbas": verbas_sentenca,
            "erro": dados_sentenca.get("erro"),
        },
        "liquidacao": {
            "tipo": dados_liquidacao.get("tipo"),
            "indice_correcao": indice_liq,
            "juros_mora": juros_liq,
            "divisor_horas": dados_liquidacao.get("divisor_horas"),
            "verbas_calculadas": verbas_liquidacao,
            "erro": dados_liquidacao.get("erro"),
        },
        "manifestacao": {
            "fundamentos_juridicos": dados_manifestacao.get("fundamentos_juridicos") or [],
            "discrepancias_levantadas": dados_manifestacao.get("discrepancias_levantadas") or [],
            "erro": dados_manifestacao.get("erro"),
        },
        "discrepancias": discrepancias,
        "aprendizados": aprendizados,
    }


def canon_empresa_e_verba_esta(relatorio: Dict[str, Any]) -> Tuple[Set[str], Callable[[str], bool]]:
    """
    Retorna (set de verbas canonizadas da empresa, função verba_esta(verba) -> bool).
    Usado pelos guardrails de discrepâncias, aprendizados e hipóteses LLM.
    """
    verbas_liq = (relatorio.get("liquidacao") or {}).get("verbas_calculadas") or []
    pjc = relatorio.get("calculo_pjc") or {}
    verbas_pjc = pjc.get("verbas_calculadas") or []
    todos = [str(v).strip() for v in verbas_liq + verbas_pjc if v]
    canon_empresa = {LegalRule._canonizar_verba(n) for n in todos}
    canon_empresa.discard("")

    def verba_esta(verba: str) -> bool:
        if not (verba or "").strip():
            return False
        canon = LegalRule._canonizar_verba(verba.strip())
        if canon in canon_empresa:
            return True
        cl, ce = canon.lower(), [c.lower() for c in canon_empresa if c]
        return any(cl in e or e in cl for e in ce)

    return canon_empresa, verba_esta


def filtrar_falsos_positivos_verba_ausente(relatorio: Dict[str, Any]) -> None:
    """
    Remove da lista de discrepâncias itens em que o LLM apontou 'verba ausente'
    mas a verba deferida (canonizada) existe nas verbas da liquidação ou do PJC.
    Mutates relatorio["discrepancias"] e relatorio["resumo"]["discrepancias_encontradas"].
    """
    discrepancias = relatorio.get("discrepancias") or []
    if not discrepancias:
        return
    _, verba_esta = canon_empresa_e_verba_esta(relatorio)
    filtradas = []
    for d in discrepancias:
        tipo = (d.get("tipo") or "").strip()
        empresa_calculou = (d.get("empresa_calculou") or "").lower()
        juiz_disse = d.get("juiz_disse") or ""
        is_verba_ausente = (
            tipo == "verba_ausente"
            or ("ausente" in empresa_calculou and "deferido" in juiz_disse.lower())
        )
        if not is_verba_ausente:
            filtradas.append(d)
            continue
        match = re.search(r"deferido:\s*(.+)", juiz_disse, re.IGNORECASE)
        verba_deferida = match.group(1).strip() if match else ""
        if not verba_deferida:
            filtradas.append(d)
            continue
        if verba_esta(verba_deferida):
            continue
        filtradas.append(d)
    relatorio["discrepancias"] = filtradas
    if "resumo" in relatorio and isinstance(relatorio["resumo"], dict):
        relatorio["resumo"]["discrepancias_encontradas"] = len(filtradas)


def filtrar_logicas_verba_ausente_falsas(
    logicas: List[Dict], relatorio: Dict[str, Any]
) -> List[Dict]:
    """
    Remove da lista de hipóteses (saída do Gemini) itens do tipo verba_ausente
    cuja verba canonizada existe na liquidação/PJC. Evita que regras falsas entrem no KB.
    """
    if not logicas:
        return logicas
    _, verba_esta = canon_empresa_e_verba_esta(relatorio)
    filtradas = []
    for logica in logicas:
        cond = logica.get("condicao") or {}
        if (cond.get("tipo") or "").strip() != "verba_ausente":
            filtradas.append(logica)
            continue
        verba = (cond.get("verba") or "").strip()
        if not verba:
            desc = (logica.get("descricao") or "").lower()
            match = re.search(r"deferido:\s*(.+?)(?:\s*[;.]|$)", desc, re.IGNORECASE)
            verba = match.group(1).strip() if match else ""
        if verba and verba_esta(verba):
            continue
        filtradas.append(logica)
    return filtradas


def filtrar_aprendizados_verba_ausente_falsas(relatorio: Dict[str, Any]) -> None:
    """
    Remove de relatorio["aprendizados"] itens que representam verba_ausente falsa
    (verba canonizada existe no PJC/Liquidação). Mutates relatorio["aprendizados"].
    """
    aprendizados = relatorio.get("aprendizados") or []
    if not aprendizados:
        return
    _, verba_esta = canon_empresa_e_verba_esta(relatorio)
    filtrados = []
    for ap in aprendizados:
        titulo = (ap.get("titulo") or "").lower()
        descricao = (ap.get("descricao") or "") or ""
        desc_lower = descricao.lower()
        is_verba_ausente = (
            "verba_ausente" in titulo
            or "ausente" in titulo
            or ("ausente" in desc_lower and "deferido" in desc_lower)
        )
        if not is_verba_ausente:
            filtrados.append(ap)
            continue
        match = re.search(r"deferido:\s*(.+?)(?:\s*[;.]|$)", descricao, re.IGNORECASE)
        verba = match.group(1).strip() if match else ""
        if not verba:
            filtrados.append(ap)
            continue
        if verba_esta(verba):
            continue
        filtrados.append(ap)
    relatorio["aprendizados"] = filtrados


__all__ = [
    "verba_corresponde_na_liquidacao",
    "gerar_relatorio_discrepancia",
    "canon_empresa_e_verba_esta",
    "filtrar_falsos_positivos_verba_ausente",
    "filtrar_logicas_verba_ausente_falsas",
    "filtrar_aprendizados_verba_ausente_falsas",
]

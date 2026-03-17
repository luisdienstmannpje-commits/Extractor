"""
titulo_executivo.py — Título Executivo Complexo: tiers (1º Grau, TRT, TST) e hierarquia (Passo 3).

Funções extraídas de learning_engine.py:
  - classificar_tier_decisao: nome do arquivo + texto (após cabeçalho 1000 chars) → '1GRAU'|'TRT'|'TST'.
  - extrair_data_documento: texto do documento → data do julgamento/assinatura (nunca Data da Autuação).
  - extrair_titulo_executivo_multiplos: múltiplos (bytes, filename) → fusão por tier + data; Tier diferente = ambos mantidos.

Regra crítica (AI_NAVIGATION_LAYER): prioridade ao nome do arquivo; regex no texto só para nome genérico;
ignora os primeiros 1000 chars (cabeçalho PJe). Data: linha "Data da Autuação" removida antes das regex.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from services.lab import extractors

# ── Tier por nome do arquivo (prioridade absoluta — evita falso positivo pelo cabeçalho PJe) ─
TIER_1GRAU_PELO_NOME = ("1grau", "atord", "sentenca", "sentença")
TIER_TRT_PELO_NOME = ("2grau", "2º grau", "2_grau", "rot", "rot_", "acordao", "acórdão")
TIER_TST = ("tst", "recurso_de_revista", "recurso de revista", "rr_", "_rr.", "acórdão_tst", "acordao_tst")
TIER_TRT = (
    "trt", "recurso_ordinario", "recurso ordinário", "ro_", "_ro.",
    "acórdão_trt", "acordao_trt", "acórdão", "acordao",
    "2grau", "2º grau", "2_grau",
)

TIER_ORDER = {"1GRAU": 0, "TRT": 1, "TST": 2}
TIER_LABELS = {
    "1GRAU": "SENTENÇA DE 1º GRAU",
    "TRT": "ACÓRDÃO TRT (RECURSO ORDINÁRIO)",
    "TST": "ACÓRDÃO TST (RECURSO DE REVISTA)",
}

MESES_NUM = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}

FALLBACK_DATE = date(1900, 1, 1)


def classificar_tier_decisao(filename: str, texto_primeiras_paginas: Optional[str] = None) -> str:
    """
    Classifica o nível hierárquico pelo NOME primeiro; só usa texto se o nome for genérico.
    Retorna 'TST', 'TRT' ou '1GRAU'.
    Regras: 1grau/ATOrd/Sentenca no nome → 1GRAU; 2grau/ROT/Acordao no nome → TRT.
    Regex no texto só para nome genérico; ignora cabeçalho PJe (1000 chars) via extractors.
    """
    n = (filename or "").lower()
    if any(k in n for k in TIER_1GRAU_PELO_NOME):
        return "1GRAU"
    if any(k in n for k in TIER_TRT_PELO_NOME):
        return "TRT"
    if any(k in n for k in TIER_TST):
        return "TST"
    if any(k in n for k in TIER_TRT):
        return "TRT"
    if extractors.tem_indicador_2grau_apos_cabecalho(texto_primeiras_paginas):
        return "TRT"
    return "1GRAU"


def extrair_data_documento(texto: str) -> date:
    """
    Extrai a data mais provável de um documento judicial (data do julgamento/assinatura).
    Usada para desempatar documentos da mesma instância no Card 3.
    NUNCA usa "Data da Autuação": a linha que a contém é removida antes de rodar as regex.
    """
    if not (texto or "").strip():
        return FALLBACK_DATE
    texto = extractors.remover_linha_autuacao(texto)
    if not (texto or "").strip():
        return FALLBACK_DATE
    texto_norm = (texto or "").lower()
    tamanho_final = 2000
    trecho_final = texto[-tamanho_final:] if len(texto) > tamanho_final else texto
    trecho_final_norm = trecho_final.lower()
    offset_final = len(texto) - len(trecho_final)

    def _tentar_trecho(bloco: str, bloco_norm: str, offset: int) -> Optional[date]:
        m = re.search(
            r"assinado eletronicamente em\s+(\d{2}/\d{2}/\d{4})",
            bloco_norm, re.IGNORECASE
        )
        if m and not extractors.contexto_eh_autuacao(bloco, m.start()):
            try:
                return datetime.strptime(m.group(1), "%d/%m/%Y").date()
            except ValueError:
                pass

        m = re.search(
            r"(?:data\s+do\s+julgamento|julgado\s+em)[:\s]+(\d{1,2})\s+de\s+"
            r"(\w+)\s+de\s+(\d{4})",
            bloco_norm, re.IGNORECASE
        )
        if m and not extractors.contexto_eh_autuacao(bloco, m.start()):
            try:
                dia = int(m.group(1))
                mes = MESES_NUM.get(m.group(2).lower().strip(), 0)
                ano = int(m.group(3))
                if mes and 1 <= dia <= 31 and 2000 <= ano <= 2099:
                    return date(ano, mes, dia)
            except (ValueError, KeyError):
                pass

        m = re.search(
            r",\s*(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s*[.\n]",
            bloco_norm, re.IGNORECASE
        )
        if m and not extractors.contexto_eh_autuacao(bloco, m.start()):
            try:
                dia = int(m.group(1))
                mes = MESES_NUM.get(m.group(2).lower().strip(), 0)
                ano = int(m.group(3))
                if mes and 2000 <= ano <= 2099:
                    return date(ano, mes, dia)
            except (ValueError, KeyError):
                pass

        ultimos = bloco[-500:] if len(bloco) > 500 else bloco
        datas = re.findall(r"\b(\d{2}/\d{2}/\d{4})\b", ultimos)
        for d in reversed(datas):
            try:
                dt = datetime.strptime(d, "%d/%m/%Y").date()
                if 2000 <= dt.year <= 2099:
                    pos = ultimos.rfind(d)
                    if pos >= 0 and not extractors.contexto_eh_autuacao(ultimos, pos):
                        return dt
            except ValueError:
                continue
        return None

    resultado = _tentar_trecho(trecho_final, trecho_final_norm, offset_final)
    if resultado is not None:
        return resultado
    resultado = _tentar_trecho(texto, texto_norm, 0)
    if resultado is not None:
        return resultado
    print("[LAB] extrair_data_documento: nenhuma data encontrada, usando fallback", flush=True)
    return FALLBACK_DATE


def extrair_titulo_executivo_multiplos(
    arquivos: List[tuple],
    contexto_amostragens: Optional[str] = None,
    *,
    extrair_processo: Callable[..., Dict[str, Any]],
    extrair_texto_arquivo: Callable[[bytes, str], str],
    bloco_amostragens_perita: Callable[[str], str],
) -> Dict[str, Any]:
    """
    Processa múltiplos documentos decisórios (sentença + acórdãos) como Título Executivo Complexo.

    Hierarquia: 1º Grau → TRT → TST. Entre documentos da MESMA instância, o mais RECENTE prevalece.
    Tier diferente = ambos mantidos. Cabeçalho PJe 1000 chars ignorado (extractors).

    Callbacks injetados pelo learning_engine: extrair_processo, extrair_texto_arquivo, bloco_amostragens_perita.
    """
    arquivos_ignorados: List[str] = []

    if not arquivos:
        return {"dados": {}, "doc_type": "titulo_executivo_vazio", "arquivos_ignorados_duplicados": []}

    hashes_vistos = set()
    arquivos_unicos: List[tuple] = []
    for file_bytes, filename in arquivos:
        h = hashlib.sha256(file_bytes).hexdigest()
        if h in hashes_vistos:
            print(f"[LAB] Duplicata ignorada: '{filename}' (hash {h[:8]}...)", flush=True)
            arquivos_ignorados.append(filename)
            continue
        hashes_vistos.add(h)
        arquivos_unicos.append((file_bytes, filename))

    arquivos = arquivos_unicos
    if not arquivos:
        return {"dados": {}, "doc_type": "titulo_executivo_vazio", "arquivos_ignorados_duplicados": arquivos_ignorados}

    if len(arquivos) == 1:
        b, fn = arquivos[0]
        result = extrair_processo(b, fn)
        result["instancias_detectadas"] = [classificar_tier_decisao(fn)]
        result["contexto_decisao_final"] = None
        texto_uno = extrair_texto_arquivo(b, fn)
        data_doc = extrair_data_documento(texto_uno)
        result["data_documento"] = data_doc.isoformat()
        result["arquivos_ignorados_duplicados"] = arquivos_ignorados
        return result

    por_tier = defaultdict(list)
    for file_bytes, filename in arquivos:
        texto_temp = extrair_texto_arquivo(file_bytes, filename)
        tier = classificar_tier_decisao(filename, texto_temp[:4000] if texto_temp else None)
        data_doc = extrair_data_documento(texto_temp)
        por_tier[tier].append({
            "bytes": file_bytes,
            "filename": filename,
            "tier": tier,
            "data": data_doc,
            "texto": texto_temp,
        })
        print(f"[LAB] '{filename}' -> tier={tier}, data={data_doc}", flush=True)

    arquivos_selecionados: List[Dict[str, Any]] = []
    for tier, docs in por_tier.items():
        if len(docs) == 1:
            arquivos_selecionados.append(docs[0])
        else:
            docs_ordenados = sorted(docs, key=lambda d: d["data"], reverse=True)
            vencedor = docs_ordenados[0]
            arquivos_selecionados.append(vencedor)
            for ig in docs_ordenados[1:]:
                print(
                    f"[LAB] '{ig['filename']}' ignorado - mesma instancia ({tier}) "
                    f"com data {ig['data']} < {vencedor['data']}",
                    flush=True,
                )
                arquivos_ignorados.append(ig["filename"])

    arquivos_selecionados.sort(key=lambda d: TIER_ORDER.get(d["tier"], 0))
    docs_com_tier = [(d["tier"], d["bytes"], d["filename"]) for d in arquivos_selecionados]
    datas_documentos = [d["data"].isoformat() for d in arquivos_selecionados]
    instancias = [d["tier"] for d in arquivos_selecionados]
    tem_tst = "TST" in instancias
    tem_trt = "TRT" in instancias

    print(f"[LEARNING] Titulo Executivo Complexo - instancias detectadas: {instancias}", flush=True)

    blocos_texto = []
    for d in arquivos_selecionados:
        tier, fn, texto = d["tier"], d["filename"], d["texto"]
        label = TIER_LABELS.get(tier, tier)
        if (texto or "").strip():
            blocos_texto.append(f"{'='*60}\n{label} — {fn}\n{'='*60}\n{texto[:4000]}")

    if not blocos_texto:
        return {
            "dados": {},
            "doc_type": "titulo_executivo",
            "erro": "Nenhum texto legível extraído dos documentos",
            "instancias_detectadas": instancias,
            "arquivos_ignorados_duplicados": arquivos_ignorados,
        }

    contexto_decisao_final = "\n\n".join(blocos_texto)
    if contexto_amostragens:
        contexto_decisao_final = bloco_amostragens_perita(contexto_amostragens) + contexto_decisao_final

    instrucao_tst = (
        "\nCRÍTICO — RECURSO DE REVISTA DETECTADO:\n"
        "O Acórdão do TST representa jurisprudência consolidada (Súmulas e OJs). "
        "Dê peso DOBRADO às teses extraídas do Acórdão TST/RR. "
        "Verbas ou parâmetros alterados pelo TST têm prioridade absoluta sobre TRT e 1º grau.\n"
    ) if tem_tst else ""

    instrucao_reforma = (
        "\nHIERARQUIA DE REFORMA:\n"
        "Leia os documentos na ordem: 1º Grau → TRT → TST.\n"
        "Se um acórdão REFORMOU uma verba da instância anterior:\n"
        "  - Marque a verba como 'reformada' com o status final (deferida/excluída/reduzida)\n"
        "  - Somente inclua em 'verbas_deferidas' verbas com status FINAL após todas as reformas\n"
        "  - Liste as verbas EXCLUÍDAS/REFORMADAS separadamente em 'verbas_reformadas'\n"
    ) if (tem_trt or tem_tst) else ""

    try:
        from services.ai_client import extract_data_with_gemini
        from services.learning_skill_loader import carregar_skill_para_lab

        playbook_base = carregar_skill_para_lab("sentenca")
        playbook_titulo = (
            "# ANÁLISE DE REFORMA DE DECISÃO — TÍTULO EXECUTIVO COMPLEXO\n\n"
            "Você está analisando um TÍTULO EXECUTIVO COMPLEXO composto por múltiplas decisões judiciais.\n"
            "TAREFA: Ler a sentença inicial e dar PRIORIDADE ABSOLUTA às reformas contidas nos "
            "Acórdãos posteriores (TRT/TST) para definir as verbas FINAIS devidas.\n"
            f"{instrucao_reforma}"
            f"{instrucao_tst}"
            "\nAlém dos campos padrão, inclua obrigatoriamente:\n"
            '- "verbas_reformadas": lista de verbas excluídas ou alteradas pela instância superior\n'
            '- "instancia_final": "TST", "TRT" ou "1GRAU"\n\n'
            "────────────────────────────────────────\n"
            "PLAYBOOK PADRÃO DE SENTENÇA:\n"
            + (playbook_base or "")
        )

        ai_result = extract_data_with_gemini(
            contexto_decisao_final,
            playbook=playbook_titulo,
        )

        return {
            "doc_type": "titulo_executivo_complexo",
            "instancias_detectadas": instancias,
            "datas_documentos": datas_documentos,
            "instancia_final": instancias[-1] if instancias else "1GRAU",
            "tem_recurso_revista": tem_tst,
            "contexto_decisao_final": contexto_decisao_final[:500] + "…" if len(contexto_decisao_final) > 500 else contexto_decisao_final,
            "dados": ai_result.get("data") or {},
            "model_used": ai_result.get("model_used"),
            "erro": ai_result.get("error"),
            "arquivos_ignorados_duplicados": arquivos_ignorados,
        }
    except Exception as e:
        tier_final, b_final, fn_final = docs_com_tier[-1]
        resultado = extrair_processo(b_final, fn_final, contexto_amostragens=contexto_amostragens)
        resultado["instancias_detectadas"] = instancias
        resultado["datas_documentos"] = datas_documentos
        resultado["erro_fusao"] = str(e)
        resultado["arquivos_ignorados_duplicados"] = arquivos_ignorados
        return resultado


__all__ = [
    "classificar_tier_decisao",
    "extrair_data_documento",
    "extrair_titulo_executivo_multiplos",
    "TIER_ORDER",
    "TIER_LABELS",
    "FALLBACK_DATE",
]

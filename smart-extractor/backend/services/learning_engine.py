"""
learning_engine.py — Laboratório de Aprendizado da Perita

Fluxo: recebe 3 arquivos (Sentença PDF, Liquidação PDF/.PJC, Manifestação DOCX),
processa cada um de forma independente e gera um Relatório de Discrepância:

  "O juiz disse A, a empresa calculou B, a Juliana corrigiu para C usando a Súmula D"

Saída:
  - relatorio: dict com seções (sentenca, liquidacao, manifestacao, discrepancias)
  - aprendizados: list[dict] — cada item é um aprendizado extraível como regra/playbook
  - metadados: processo, data, origem

Salvamento do aprendizado (sem guardar arquivos):
  - Adiciona exemplo few-shot ao skills/sentenca_ordinaria.md
  - Gera arquivo de nova regra em services/legal_engine/rules/ (rascunho Python)
  - Registra aprendizado em learning_log.json (JSONL) para audit trail

SEGURANÇA: Nenhum arquivo binário é persistido. Apenas a lógica extraída é salva.
"""
from __future__ import annotations

import json
import os
import re
import textwrap
import zipfile
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

# ── Caminhos de saída ─────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_BACKEND = os.path.abspath(os.path.join(_HERE, ".."))
_SKILLS_DIR = os.path.join(_BACKEND, "skills")
_RULES_DIR = os.path.join(_BACKEND, "services", "legal_engine", "rules")

# Persistência e I/O do Lab: facade para services.lab.learning_io (refatoração Passo 1)
from services.lab import learning_io

preview_aprendizado = learning_io.preview_aprendizado
salvar_aprendizado = learning_io.salvar_aprendizado
_LEARNING_LOG = learning_io.LEARNING_LOG_PATH

# Limpeza e regex: facade para services.lab.extractors (refatoração Passo 2)
from services.lab import extractors

_regex_verbas = extractors.regex_verbas
VERBAS_PJE_CALC_NOMENCLATURA = getattr(extractors, "VERBAS_PJE_CALC_NOMENCLATURA", {})
INSTRUCOES_EXTRAÇÃO_VERBAS_DISPOSITIVO = getattr(
    extractors, "INSTRUCOES_EXTRAÇÃO_VERBAS_DISPOSITIVO", ""
)
_regex_indice = extractors.regex_indice
_regex_juros = extractors.regex_juros
_regex_divisor = extractors.regex_divisor
_liquidacao_from_text = extractors.liquidacao_from_text
_extrair_fundamentos_juridicos = extractors.extrair_fundamentos_juridicos
_extrair_discrepancias_perita = extractors.extrair_discrepancias_perita
_remover_linha_autuacao = extractors.remover_linha_autuacao
_contexto_eh_autuacao = extractors.contexto_eh_autuacao

# Título Executivo e tiers (1º Grau / TRT / TST): facade para services.lab.titulo_executivo (Passo 3)
from services.lab import titulo_executivo

# Confronto Sentença vs. Cálculo e guardrails: facade para services.lab.discrepancy (Passo 4)
from services.lab import discrepancy

# Duplo Style Transfer (Impugnação + Manifestação → manifestacao_style.md): facade (Passo 5)
from services.lab import style_transfer

# Self-Healing e codificação de insight (regras Python + KB multi-tenant): facade (Passo 6)
from services.lab import self_healing
from services.request_context import current_tenant_id

_logger = logging.getLogger("smart_extractor")


# ── Parser de DOCX (sem dependência externa) ─────────────────────────────────

def _extrair_texto_docx(docx_bytes: bytes) -> str:
    """
    Extrai texto puro de um DOCX (ZIP com word/document.xml).
    Sem dependência de python-docx — usa zipfile + minidom.
    """
    try:
        from xml.dom.minidom import parseString

        with zipfile.ZipFile(__import__("io").BytesIO(docx_bytes)) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_content = z.read("word/document.xml")

        dom = parseString(xml_content)
        # Coleta todos os nós <w:t> (texto) em ordem
        paragrafos = []
        for para in dom.getElementsByTagNameNS("*", "p"):
            textos = []
            for t in para.getElementsByTagNameNS("*", "t"):
                if t.firstChild:
                    textos.append(t.firstChild.nodeValue or "")
            linha = "".join(textos).strip()
            if linha:
                paragrafos.append(linha)

        return "\n".join(paragrafos)
    except Exception as e:
        _logger.warning(
            "learning_docx_extract_error",
            extra={"error": str(e), "tenant_id": current_tenant_id() or "anonimo"},
        )
        return ""


# ── Garantia de saída: verbas_deferidas nunca vazio quando há deferimentos ─────

def _normalizar_nomes_verbas_pje_calc(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mapeia termos jurídicos para nomes oficiais do PJe-Calc (ex: "Art. 477" -> "Multa Art. 477 CLT",
    "13o" -> "13º Salário Proporcional"). Aceita nome com underscore (ex.: aviso_previo_indenizado).
    """
    if not VERBAS_PJE_CALC_NOMENCLATURA:
        return dados
    verbas = list(dados.get("verbas_deferidas") or [])
    if not verbas:
        return dados
    out = []
    for v in verbas:
        if isinstance(v, dict):
            nome = (v.get("nome") or "").strip()
        else:
            nome = (v or "").strip() if isinstance(v, str) else ""
        if not nome:
            out.append(v)
            continue
        nome_lower = nome.lower()
        nome_compare = nome_lower.replace("_", " ")
        for alias, nome_padrao in VERBAS_PJE_CALC_NOMENCLATURA.items():
            al = alias.lower()
            if al in nome_lower or nome_lower in al or al in nome_compare or nome_compare in al:
                nome = nome_padrao
                break
        if isinstance(v, dict):
            out.append({**v, "nome": nome})
        else:
            out.append({"nome": nome, "status_final": "deferido"})
    dados = dict(dados)
    dados["verbas_deferidas"] = out
    return dados


def _garantir_verbas_deferidas_preenchidas(dados: Dict[str, Any], texto: str) -> Dict[str, Any]:
    """
    Se verbas_deferidas vier vazio mas o texto mencionar deferimentos (ex.: DISPOSITIVO,
    procedente), preenche a partir de sentence_understanding ou regex + padrões PJe-Calc.
    Objetivo: array verbas_deferidas nunca vazio quando a decisão deferiu parcelas.
    """
    verbas = dados.get("verbas_deferidas") or []
    if verbas and any((v.get("nome") if isinstance(v, dict) else v) for v in verbas):
        return dados
    fallback_verbas: List[Dict[str, Any]] = []
    try:
        from services.sentence_understanding import interpretar_decisao

        resultado = interpretar_decisao(texto)
        for item in (resultado.get("verbas") or []):
            nome = (item.get("nome") or item.get("nome_original") or "").strip()
            if not nome:
                continue
            status = (item.get("status") or "deferido").lower()
            if "indefer" in status:
                continue
            fallback_verbas.append({
                "nome": nome,
                "status_final": "deferido" if "defer" in status or "procedente" in status else "mantida",
                "periodo": item.get("periodo"),
                "observacoes": item.get("linha_fonte", "")[:200],
            })
    except Exception as _e:
        _logger.warning(
            "learning_fallback_interpretar_decisao_failed",
            extra={"error": str(_e), "tenant_id": current_tenant_id() or "anonimo"},
        )

    if not fallback_verbas and texto and VERBAS_PJE_CALC_NOMENCLATURA:
        texto_lower = texto.lower()
        for alias, nome_padrao in VERBAS_PJE_CALC_NOMENCLATURA.items():
            if alias.lower() in texto_lower and nome_padrao not in [v.get("nome") for v in fallback_verbas]:
                fallback_verbas.append({"nome": nome_padrao, "status_final": "deferido"})
    if fallback_verbas:
        dados = dict(dados)
        dados["verbas_deferidas"] = fallback_verbas
        _logger.info(
            "learning_fallback_verbas_preenchidas",
            extra={
                "quantidade": len(fallback_verbas),
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
    return dados


# ── Extração da Sentença ─────────────────────────────────────────────────────

def _extrair_sentenca(pdf_bytes: bytes, contexto_amostragens: Optional[str] = None) -> Dict[str, Any]:
    """
    Reutiliza o pipeline existente para extrair dados da sentença.
    Retorna apenas os dados estruturados (não gera cache, não debita crédito).
    Se contexto_amostragens for fornecido, é injetado no prompt sob <AMOSTRAGENS_DA_PERITA>.
    """
    try:
        from services.sentence_finder import extract_sentence_from_pdf
        from services.ai_client import extract_data_with_gemini
        from services.learning_skill_loader import carregar_skill_para_lab

        texto, doc_type = extract_sentence_from_pdf(pdf_bytes)
        if not texto.strip():
            return {"erro": "PDF sem texto legível", "doc_type": "desconhecido"}

        if contexto_amostragens:
            texto = _bloco_amostragens_perita(contexto_amostragens) + texto

        playbook_base = carregar_skill_para_lab(doc_type)
        playbook = (playbook_base or "") + "\n\n" + (INSTRUCOES_EXTRAÇÃO_VERBAS_DISPOSITIVO or "")
        ai_result = extract_data_with_gemini(texto, playbook=playbook)

        dados = ai_result.get("data") or {}
        dados = _garantir_verbas_deferidas_preenchidas(dados, texto)
        dados = _normalizar_nomes_verbas_pje_calc(dados)

        return {
            "doc_type": doc_type,
            "dados": dados,
            "model_used": ai_result.get("model_used"),
            "erro": ai_result.get("error"),
        }
    except Exception as e:
        return {"erro": str(e), "doc_type": "desconhecido"}


# ── Extração da Liquidação (PDF ou .PJC) ─────────────────────────────────────

def _extrair_liquidacao(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai parâmetros da liquidação.
    - Se .pjc / .xml  → PjcParser
    - Se .pdf         → extração de texto simples + regex para parâmetros-chave
    """
    fname = (filename or "").lower()

    if fname.endswith(".pjc") or fname.endswith(".xml"):
        try:
            from services.pjc_parser import PjcParser
            parser = PjcParser.from_string(file_bytes)
            dados = parser.extrair_dados_basicos()
            return {
                "tipo": "pjc",
                "indice_correcao": dados.indice_trabalhista,
                "juros_mora": dados.juros_trabalhistas,
                "divisor_horas": dados.divisor_horas,
                "verbas_calculadas": dados.nomes_verbas,
                "erro": None,
            }
        except Exception as e:
            return {"tipo": "pjc", "erro": str(e)}

    if fname.endswith(".pdf"):
        try:
            import pdfplumber
            import io
            texto = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages[:10]:
                    texto += (page.extract_text() or "") + "\n"

            return {
                "tipo": "pdf",
                "texto_bruto": texto[:3000],
                "verbas_calculadas": _regex_verbas(texto),
                "indice_correcao": _regex_indice(texto),
                "juros_mora": _regex_juros(texto),
                "divisor_horas": _regex_divisor(texto),
                "erro": None,
            }
        except Exception as e:
            return {"tipo": "pdf", "erro": str(e)}

    return {"tipo": "desconhecido", "erro": "Formato não suportado"}


# ── Liquidação/Regex/Manifestação (facade → extractors) ───────────────────────
# _liquidacao_from_text, _regex_verbas/_indice/_juros/_divisor, _extrair_fundamentos_juridicos,
# _extrair_discrepancias_perita movidos para services.lab.extractors (Passo 2).

# ── Extração da Manifestação (DOCX) ─────────────────────────────────────────

def _extrair_manifestacao(docx_bytes: bytes) -> Dict[str, Any]:
    """
    Extrai texto da manifestação e identifica:
    - Fundamentos jurídicos mencionados (súmulas, OJs, artigos CLT, ADC)
    - Discrepâncias que a perita levantou
    - Correções propostas
    """
    texto = _extrair_texto_docx(docx_bytes)
    if not texto:
        return {"erro": "Não foi possível extrair texto do DOCX", "texto": ""}

    fundamentos = _extrair_fundamentos_juridicos(texto)
    discrepancias_levantadas = _extrair_discrepancias_perita(texto)

    return {
        "texto_bruto": texto[:4000],
        "fundamentos_juridicos": fundamentos,
        "discrepancias_levantadas": discrepancias_levantadas,
        "erro": None,
    }


def _extrair_manifestacao_from_text(texto: str) -> Dict[str, Any]:
    """
    Mesma lógica de _extrair_manifestacao, recebendo texto já extraído (ex.: do Timeline Extractor).
    """
    if not (texto or "").strip():
        return {"erro": "Texto vazio", "texto_bruto": "", "fundamentos_juridicos": [], "discrepancias_levantadas": []}
    fundamentos = _extrair_fundamentos_juridicos(texto)
    discrepancias_levantadas = _extrair_discrepancias_perita(texto)
    return {
        "texto_bruto": texto[:4000],
        "fundamentos_juridicos": fundamentos,
        "discrepancias_levantadas": discrepancias_levantadas,
        "erro": None,
    }


# ── Geração do Relatório de Discrepância — módulo canônico: services/lab/discrepancy.py ──
from services.lab.discrepancy import (
    verba_corresponde_na_liquidacao as _verba_corresponde_na_liquidacao,
    gerar_relatorio_discrepancia,
    filtrar_logicas_verba_ausente_falsas as _filtrar_logicas_verba_ausente_falsas,
    filtrar_falsos_positivos_verba_ausente as _filtrar_falsos_positivos_verba_ausente,
    filtrar_aprendizados_verba_ausente_falsas as _filtrar_aprendizados_verba_ausente_falsas,
)
# Helpers internos mantidos como aliases para chamadas existentes no arquivo
from services.lab.discrepancy import (
    gerar_relatorio_discrepancia as _gerar_relatorio_discrepancia,
)


def _campos_chave_sentenca(dados: dict) -> dict:
    from services.lab.discrepancy import _campos_chave_sentenca as _cks
    return _cks(dados)


def _sugerir_correcao_verba(verba: str, manifestacao: dict) -> str:
    from services.lab.discrepancy import _sugerir_correcao_verba as _scv
    return _scv(verba, manifestacao)


def _buscar_fundamento_para_verba(verba: str, manifestacao: dict) -> str:
    from services.lab.discrepancy import _buscar_fundamento_para_verba as _bfv
    return _bfv(verba, manifestacao)


def _extrair_aprendizados(ds, dl, dm, disc):
    from services.lab.discrepancy import _extrair_aprendizados as _ea
    return _ea(ds, dl, dm, disc)


# ── Pré-visualização e Salvamento do Aprendizado (facade → learning_io) ───────
# Corpos movidos para services.lab.learning_io (refatoração Passo 1).

# ══════════════════════════════════════════════════════════════════════════════
# CODIFICAÇÃO DE INSIGHT — Camada dupla: Log + Lógica (Gemini)
# ══════════════════════════════════════════════════════════════════════════════

def _chamar_gemini_para_codify(prompt: str) -> tuple[str, str]:
    """
    Chama Gemini (modelo de raciocínio) para gerar conteúdo a partir de um prompt.
    Usa cascata gemini-2.5-pro → gemini-2.0-flash.
    Retorna (conteudo_gerado, model_used). Nunca lança exceção.
    """
    try:
        from google import genai as _genai
        from config import settings as _settings
        import time as _time

        _client = _genai.Client(api_key=_settings.GEMINI_API_KEY)
        cascade = ["models/gemini-2.5-pro", "gemini-2.0-flash"]

        for model in cascade:
            for attempt in range(1, 3):
                try:
                    response = _client.models.generate_content(
                        model=model,
                        contents=prompt,
                    )
                    text = (response.text or "").strip()
                    if text:
                        _logger.info(
                            "codify_generated",
                            extra={
                                "model": model,
                                "attempt": attempt,
                                "tenant_id": current_tenant_id() or "anonimo",
                            },
                        )
                        return text, model
                except Exception as e:
                    err = str(e).lower()
                    if "429" in err or "quota" in err or "rate" in err:
                        _time.sleep(10 * attempt)
                        continue
                    _logger.warning(
                        "codify_model_error",
                        extra={
                            "model": model,
                            "attempt": attempt,
                            "error": str(e),
                            "tenant_id": current_tenant_id() or "anonimo",
                        },
                    )
                    break

        _logger.error(
            "codify_all_models_failed",
            extra={"tenant_id": current_tenant_id() or "anonimo"},
        )
        return "", "fallback"

    except Exception as e:
        _logger.error(
            "codify_critical_error",
            extra={"error": str(e), "tenant_id": current_tenant_id() or "anonimo"},
        )
        return "", "fallback"


def codify_insight(
    aprendizado: dict,
    numero_processo: str = "",
    conteudo_editado: Optional[str] = None,
) -> dict:
    return self_healing.codify_insight(
        aprendizado,
        numero_processo,
        conteudo_editado,
        rules_dir=_RULES_DIR,
        skills_dir=_SKILLS_DIR,
        learning_log_path=_LEARNING_LOG,
        chamar_gemini_para_codify=_chamar_gemini_para_codify,
    )


# ── Extração de documento textual genérico (PDF, DOC, DOCX) ─────────────────

def _extrair_texto_arquivo(file_bytes: bytes, filename: str) -> str:
    """
    Extrai texto de PDF, DOC ou DOCX.
    - .pdf  → pdfplumber (primeiras 10 páginas)
    - .docx → _extrair_texto_docx (zipfile / XML)
    - .doc  → tenta decodificar como texto simples (fallback)
    """
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):
        try:
            import pdfplumber
            import io
            texto = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages[:10]:
                    texto += (page.extract_text() or "") + "\n"
            return texto.strip()
        except Exception as e:
            _logger.warning(
                "learning_pdf_extract_error",
                extra={
                    "pdf_filename": filename,
                    "error": str(e),
                    "tenant_id": current_tenant_id() or "anonimo",
                },
            )
            return ""
    elif fname.endswith(".docx"):
        return _extrair_texto_docx(file_bytes)
    elif fname.endswith(".doc"):
        # .doc binário: tenta decodificar como Latin-1 e extrair strings legíveis
        try:
            raw = file_bytes.decode("latin-1", errors="ignore")
            linhas = [l.strip() for l in raw.split("\n") if len(l.strip()) > 20]
            return "\n".join(linhas[:200])
        except Exception:
            return ""
    return ""


def _extrair_texto_arquivo_com_marcadores_pagina(
    file_bytes: bytes,
    filename: str,
    max_pages: int = 25,
) -> str:
    """
    Texto com marcadores --- PÁGINA N --- para ancoragem (mesmo contrato que sentence_finder).
    PDF: uma seção por página (limitado a max_pages). DOC/DOCX/DOC: bloco único como página 1.
    """
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):
        try:
            import io

            import pdfplumber

            partes: List[str] = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                n = min(len(pdf.pages), max(1, int(max_pages)))
                for i in range(n):
                    pg = pdf.pages[i]
                    t = (pg.extract_text() or "").strip()
                    partes.append(f"--- PÁGINA {i + 1} ---\n{t}")
            return "\n".join(partes).strip()
        except Exception as e:
            _logger.warning(
                "learning_pdf_marcadores_error",
                extra={
                    "pdf_filename": filename,
                    "error": str(e),
                    "tenant_id": current_tenant_id() or "anonimo",
                },
            )
            return ""
    flat = _extrair_texto_arquivo(file_bytes, filename)
    if not (flat or "").strip():
        return ""
    return f"--- PÁGINA 1 ---\n{flat.strip()}"


def _derivar_campos_legados_contestacao(
    teses_defesa: List[Any],
) -> tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Preenche argumentos_exclusao, verbas_negadas e teses_empresa a partir de teses_defesa (Lab)."""
    argumentos: List[Dict[str, Any]] = []
    verbas_neg: List[str] = []
    teses_set: List[str] = []
    for raw in teses_defesa or []:
        if not isinstance(raw, dict):
            continue
        alvo = str(raw.get("verba_alvo") or raw.get("verba") or "").strip()
        tese = str(raw.get("tese_principal") or raw.get("argumento") or "").strip()
        incont = bool(raw.get("incontroversa"))
        base_legal = str(raw.get("base_legal") or "").strip()
        if alvo or tese:
            argumentos.append(
                {
                    "verba": alvo or "—",
                    "argumento": tese or "—",
                    "base_legal": base_legal or "—",
                }
            )
        if alvo and not incont:
            verbas_neg.append(alvo)
        if tese and tese not in teses_set:
            teses_set.append(tese)
    return argumentos, verbas_neg, teses_set


# ── Dossiê de Amostragens / Provas Adicionais (multi-upload) ─────────────────

# Classificação por conteúdo: Parecer (style_transfer, fundamentos), Amostragem (tabelas, R$), Manifestação
_RE_PARECER = re.compile(
    r"(?i)(?:parecer\s+t[eé]cnico|conclui[- ]se|vem\s+apresentar|laudo\s+pericial)",
)
_RE_MANIFESTACAO = re.compile(
    r"(?i)(?:manifesta[çc][ãa]o|peti[çc][ãa]o\s+de\s+resposta|vem\s+apresentar|combate)",
)
_RE_AMOSTRAGEM_MAT = re.compile(
    r"(?i)(?:R\$\s*\d|janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
    r"|(?:\d{1,3}(?:\.\d{3})*,\d{2})",  # 1.234,56
)


def _classificar_tipo_documento_prova(texto: str, filename: str) -> str:
    """
    Classifica um documento do Card de Provas por conteúdo.
    Retorna 'parecer' | 'amostragem' | 'manifestacao' | 'generic'.
    Parecer: estratégia e fundamentos da perita (style_transfer, fundamentos_perita).
    Amostragem: tabelas de valores, R$, meses → conferência centavo a centavo no .PJC.
    Manifestação: petição de resposta, combate.
    """
    if not (texto or "").strip():
        return "generic"
    t = (texto or "")[:6000].lower()
    # Ordem: parecer e manifestação podem coexistir; amostragem tem prioridade se forte sinal de tabela
    if _RE_AMOSTRAGEM_MAT.search(t) and (t.count("r$") + t.count("janeiro") + t.count("fevereiro") >= 2):
        return "amostragem"
    if _RE_PARECER.search(t):
        return "parecer"
    if _RE_MANIFESTACAO.search(t):
        return "manifestacao"
    if _RE_AMOSTRAGEM_MAT.search(t):
        return "amostragem"
    return "generic"


def _fusionar_provas_com_cards(
    amostragens_arquivos: List[tuple],
    parecer_bytes: Optional[bytes],
    parecer_filename: Optional[str],
    amostragem_pdf_bytes: Optional[bytes],
    amostragem_pdf_filename: Optional[str],
    amostragem_word_bytes: Optional[bytes],
    amostragem_word_filename: Optional[str],
    manifestacao_bytes: Optional[bytes],
    manifestacao_filename: Optional[str],
) -> tuple:
    """
    Analisa cada arquivo do Card de Provas e, se os Cards 5/8 ou amostragem não foram
    preenchidos, preenche a partir do primeiro arquivo classificado como parecer/amostragem/manifestação.
    Preserva bytes e filename quando já fornecidos pelos cards explícitos.
    Retorna (texto_dossie, parecer_bytes, parecer_fn, amostragem_pdf_*, amostragem_word_*, manifestacao_*).
    """
    texto_dossie = ""
    out_parecer_fn = parecer_filename or ""
    out_amostragem_pdf_fn = amostragem_pdf_filename or ""
    out_amostragem_word_fn = amostragem_word_filename or ""
    out_manifestacao_fn = manifestacao_filename or ""
    usado_para_parecer = False
    usado_para_amostragem_pdf = False
    usado_para_amostragem_word = False
    usado_para_manifestacao = False

    for file_bytes, filename in amostragens_arquivos or []:
        texto = _extrair_texto_arquivo(file_bytes, filename)
        conteudo = (texto or "").strip() or "(sem texto legível)"
        if len(conteudo) > 8000:
            conteudo = conteudo[:8000] + "\n[... truncado ...]"
        texto_dossie += f"\n--- PROVA: {filename} ---\n{conteudo}\n"

        tipo = _classificar_tipo_documento_prova(texto, filename)
        fname = (filename or "").lower()

        if tipo == "parecer" and not parecer_bytes and not usado_para_parecer:
            parecer_bytes = file_bytes
            out_parecer_fn = filename or ""
            usado_para_parecer = True
            _logger.info(
                "learning_autoclass_parecer",
                extra={"nome_arquivo": filename, "tenant_id": current_tenant_id() or "anonimo"},
            )
        elif tipo == "amostragem":
            if fname.endswith(".pdf") and not amostragem_pdf_bytes and not usado_para_amostragem_pdf:
                amostragem_pdf_bytes = file_bytes
                out_amostragem_pdf_fn = filename or ""
                usado_para_amostragem_pdf = True
                _logger.info(
                    "learning_autoclass_amostragem_pdf",
                    extra={"nome_arquivo": filename, "tenant_id": current_tenant_id() or "anonimo"},
                )
            elif (fname.endswith(".docx") or fname.endswith(".doc")) and not amostragem_word_bytes and not usado_para_amostragem_word:
                amostragem_word_bytes = file_bytes
                out_amostragem_word_fn = filename or ""
                usado_para_amostragem_word = True
                _logger.info(
                    "learning_autoclass_amostragem_word",
                    extra={"nome_arquivo": filename, "tenant_id": current_tenant_id() or "anonimo"},
                )
        elif tipo == "manifestacao" and not manifestacao_bytes and not usado_para_manifestacao:
            manifestacao_bytes = file_bytes
            out_manifestacao_fn = filename or ""
            usado_para_manifestacao = True
            _logger.info(
                "learning_autoclass_manifestacao",
                extra={"nome_arquivo": filename, "tenant_id": current_tenant_id() or "anonimo"},
            )

    return (
        texto_dossie.strip(),
        parecer_bytes,
        out_parecer_fn,
        amostragem_pdf_bytes,
        out_amostragem_pdf_fn,
        amostragem_word_bytes,
        out_amostragem_word_fn,
        manifestacao_bytes,
        out_manifestacao_fn,
    )


def _processar_dossie_amostragens(lista_arquivos: List[tuple]) -> str:
    """
    Processa uma lista de (bytes, filename) de provas/amostragens, extrai texto
    de cada um (PDF ou DOCX) e concatena com rótulo por arquivo.
    Retorna uma única string para ser injetada no prompt sob <AMOSTRAGENS_DA_PERITA>.
    """
    if not lista_arquivos:
        return ""
    partes = []
    for file_bytes, filename in lista_arquivos:
        texto = _extrair_texto_arquivo(file_bytes, filename)
        conteudo = (texto or "").strip() or "(sem texto legível)"
        if len(conteudo) > 8000:
            conteudo = conteudo[:8000] + "\n[... truncado ...]"
        partes.append(f"\n--- PROVA: {filename} ---\n{conteudo}")
    return "\n".join(partes)


_INSTRUCAO_PROMPT_UNIFICADO = (
    "Você recebeu uma pasta de documentos do Perito Assistente. "
    "Identifique qual arquivo é o Parecer e qual é a Amostragem. "
    "Use o Parecer para entender a estratégia de combate e a Amostragem para conferir os valores centavo por centavo no arquivo .PJC.\n\n"
)


def _bloco_amostragens_perita(texto_dossie: str) -> str:
    """Envolve o texto do dossiê na tag e instrução unificada para a IA."""
    if not (texto_dossie or "").strip():
        return ""
    return (
        "<AMOSTRAGENS_DA_PERITA>\n"
        + _INSTRUCAO_PROMPT_UNIFICADO
        + "Se houver dados na tag abaixo, use-os como verdade absoluta para confrontar os cálculos da empresa. "
        "Estas são as provas levantadas pelo perito assistente.\n\n"
        f"{texto_dossie.strip()}\n"
        "</AMOSTRAGENS_DA_PERITA>\n\n"
    )


# ── Extração do Processo / Sentença ─────────────────────────────────────────

def _extrair_processo(file_bytes: bytes, filename: str, contexto_amostragens: Optional[str] = None) -> Dict[str, Any]:
    """
    Extrai dados estruturados do processo/sentença.
    - PDF → pipeline completo (sentence_finder + IA)
    - DOC/DOCX → extrai texto e chama IA com texto bruto
    Se contexto_amostragens for fornecido, é injetado no prompt sob <AMOSTRAGENS_DA_PERITA>.
    """
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):
        return _extrair_sentenca(file_bytes, contexto_amostragens=contexto_amostragens)

    # DOC/DOCX: extrai texto e usa IA
    try:
        from services.ai_client import extract_data_with_gemini
        from services.learning_skill_loader import carregar_skill_para_lab

        texto = _extrair_texto_arquivo(file_bytes, filename)
        if not texto.strip():
            return {"erro": "Documento sem texto legível", "doc_type": "sentenca"}

        if contexto_amostragens:
            texto = _bloco_amostragens_perita(contexto_amostragens) + texto

        playbook = carregar_skill_para_lab("sentenca")
        ai_result = extract_data_with_gemini(texto, playbook=playbook)
        return {
            "doc_type": "sentenca",
            "dados": ai_result.get("data") or {},
            "model_used": ai_result.get("model_used"),
            "erro": ai_result.get("error"),
        }
    except Exception as e:
        return {"erro": str(e), "doc_type": "sentenca"}


# ── Título Executivo Complexo: facade para services.lab.titulo_executivo (Passo 3) ───

def _classificar_tier_decisao(filename: str, texto_primeiras_paginas: Optional[str] = None) -> str:
    return titulo_executivo.classificar_tier_decisao(filename, texto_primeiras_paginas)


def _extrair_data_documento(texto: str) -> date:
    return titulo_executivo.extrair_data_documento(texto)


def _extrair_titulo_executivo_multiplos(
    arquivos: List[tuple],
    contexto_amostragens: Optional[str] = None,
) -> Dict[str, Any]:
    return titulo_executivo.extrair_titulo_executivo_multiplos(
        arquivos,
        contexto_amostragens=contexto_amostragens,
        extrair_processo=_extrair_processo,
        extrair_texto_arquivo=_extrair_texto_arquivo,
        bloco_amostragens_perita=_bloco_amostragens_perita,
    )


# ── Extração da Impugnação ───────────────────────────────────────────────────

def _extrair_impugnacao(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai fundamentos e argumentos da impugnação da parte contrária.
    Estrutura idêntica à manifestação — fundamentos + trechos de contestação.
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto:
        return {"erro": "Não foi possível extrair texto da impugnação", "texto": ""}

    fundamentos = _extrair_fundamentos_juridicos(texto)
    argumentos  = _extrair_discrepancias_perita(texto)  # reutiliza heurística

    return {
        "texto_bruto": texto[:3000],
        "fundamentos_juridicos": fundamentos,
        "argumentos_da_parte": argumentos,
        "erro": None,
    }


def _extrair_impugnacao_from_text(texto: str) -> Dict[str, Any]:
    """Mesma lógica de _extrair_impugnacao a partir de texto já extraído (ex.: Timeline)."""
    if not (texto or "").strip():
        return {"erro": "Texto vazio", "texto_bruto": "", "fundamentos_juridicos": [], "argumentos_da_parte": []}
    fundamentos = _extrair_fundamentos_juridicos(texto)
    argumentos = _extrair_discrepancias_perita(texto)
    return {
        "texto_bruto": texto[:3000],
        "fundamentos_juridicos": fundamentos,
        "argumentos_da_parte": argumentos,
        "erro": None,
    }


# ── Extração do Cálculo (.PJC, PDF, DOC, DOCX) ───────────────────────────────

def _extrair_calculo_pjc(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai parâmetros do arquivo de cálculo PJe-Calc.
    - .pjc / .xml → PjcParser (parâmetros estruturados)
    - .pdf / .doc / .docx → extração de texto + regex
    """
    return _extrair_liquidacao(file_bytes, filename)


# ── Guardrail: filtro de falsos positivos (facade → discrepancy, Passo 4) ─────
from services.lab.discrepancy import (
    canon_empresa_e_verba_esta as _canon_empresa_e_verba_esta,
)

# ── Relatório ampliado com impugnação e cálculo PJC ──────────────────────────

def _enriquecer_relatorio_com_extras(
    relatorio: Dict[str, Any],
    dados_impugnacao: Optional[Dict],
    dados_calculo_pjc: Optional[Dict],
) -> Dict[str, Any]:
    """
    Adiciona seções de impugnação e cálculo PJC ao relatório base.
    Também cruza fundamentos da impugnação vs parecer para identificar pontos de conflito.
    """
    if dados_impugnacao:
        relatorio["impugnacao"] = {
            "fundamentos_juridicos": dados_impugnacao.get("fundamentos_juridicos") or [],
            "argumentos_da_parte":   dados_impugnacao.get("argumentos_da_parte") or [],
            "erro": dados_impugnacao.get("erro"),
        }
        # Fundamentos em conflito: mencionados na impugnação mas NÃO na manifestação/parecer
        fund_parecer    = set(relatorio.get("manifestacao", {}).get("fundamentos_juridicos") or [])
        fund_impugnacao = set(dados_impugnacao.get("fundamentos_juridicos") or [])
        relatorio["pontos_de_conflito"] = list(fund_impugnacao - fund_parecer)
    else:
        relatorio["impugnacao"] = None
        relatorio["pontos_de_conflito"] = []

    if dados_calculo_pjc:
        relatorio["calculo_pjc"] = {
            "tipo": dados_calculo_pjc.get("tipo"),
            "indice_correcao": dados_calculo_pjc.get("indice_correcao"),
            "juros_mora": dados_calculo_pjc.get("juros_mora"),
            "divisor_horas": dados_calculo_pjc.get("divisor_horas"),
            "verbas_calculadas": dados_calculo_pjc.get("verbas_calculadas") or [],
            "erro": dados_calculo_pjc.get("erro"),
        }

        # Adiciona divergências entre calculo_pjc e sentença ao relatório principal
        dados_sentenca_dados = relatorio.get("sentenca", {})
        # Checar índice se PJC tiver índice diferente do já detectado via liquidação
        indice_pjc = dados_calculo_pjc.get("indice_correcao") or ""
        indice_sent = dados_sentenca_dados.get("campos_chave", {}).get("indice_correcao") or ""
        if indice_pjc and indice_sent:
            n_pjc  = indice_pjc.upper().replace("-", "").replace("_", "")
            n_sent = indice_sent.upper().replace("-", "").replace("_", "")
            if n_pjc not in n_sent and n_sent not in n_pjc:
                relatorio["discrepancias"].append({
                    "tipo": "indice_calculo_pjc",
                    "nivel": "ERRO",
                    "juiz_disse": f"Índice determinado: {indice_sent}",
                    "empresa_calculou": f"Índice no .PJC: {indice_pjc}",
                    "juliana_corrigiu": "Corrigir índice no arquivo PJe-Calc",
                    "fundamento": "ADC 58 / Súmula 439 TST",
                })
        relatorio["resumo"]["discrepancias_encontradas"] = len(relatorio["discrepancias"])
    else:
        relatorio["calculo_pjc"] = None

    return relatorio


# ── Interface pública ─────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# FASE DE CONHECIMENTO — Amostragem Pericial (PDF + Word)
# Analisa as provas produzidas pela perita para alimentar cross-reference e
# style transfer antes de comparar sentença ↔ liquidação ↔ parecer.
# ══════════════════════════════════════════════════════════════════════════════

def _extrair_amostragem_pdf(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Analisa o relatório de amostragem (PDF de holerites / cartões de ponto) para
    identificar a tese vencedora que a perita provou.

    Extrai:
    - teses_provadas:      lista das irregularidades comprovadas
    - verbas_prova:        verbas trabalhistas objeto da prova
    - evidencias:          tipos de documento usados como prova
    - irregularidades:     [{verba, irregularidade, art_clt}]
    - resumo:              descrição concisa do que foi provado

    Essa informação alimenta o cross-reference com a sentença para gerar regras
    preditivas do tipo: "Sempre que a sentença deferir X, verificar parâmetro Y
    no PJe-Calc pois a empresa omite isso sistematicamente."
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto.strip():
        return {"erro": "PDF sem texto legível", "teses_provadas": [], "verbas_prova": [], "irregularidades": []}

    prompt = (
        "Você é um assistente jurídico especializado em Direito do Trabalho Brasileiro.\n"
        "Analise o relatório de amostragem pericial abaixo e extraia informações em JSON puro.\n\n"
        "O relatório de amostragem é uma prova produzida por um perito judicial que cruza\n"
        "holerites, cartões de ponto e dados da empresa para provar irregularidades trabalhistas.\n\n"
        "Extraia EXATAMENTE no formato JSON:\n"
        "{\n"
        '  "teses_provadas": ["lista das teses/irregularidades provadas pelo perito"],\n'
        '  "verbas_prova": ["lista de verbas trabalhistas objeto da prova"],\n'
        '  "evidencias_utilizadas": ["holerites", "cartões de ponto", "contracheques", etc.],\n'
        '  "periodo_analisado": "ex: jan/2020 a dez/2022 ou vazio se não identificado",\n'
        '  "irregularidades": [\n'
        '    {\n'
        '      "verba": "nome da verba trabalhista",\n'
        '      "irregularidade": "descrição objetiva do erro/omissão identificado",\n'
        '      "art_clt": "dispositivo legal aplicável, ex: Art. 58 §1º CLT"\n'
        '    }\n'
        '  ],\n'
        '  "resumo": "2-3 frases resumindo o que foi provado e qual era a irregularidade central"\n'
        "}\n\n"
        "IMPORTANTE: Responda APENAS com o JSON válido, sem markdown, sem texto antes ou depois.\n\n"
        f"TEXTO DA AMOSTRAGEM (primeiros 4000 caracteres):\n{texto[:4000]}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)

    dados: Dict[str, Any] = {}
    try:
        conteudo_limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        dados = json.loads(conteudo_limpo)
    except Exception:
        dados = {
            "teses_provadas": [],
            "verbas_prova": [],
            "evidencias_utilizadas": [],
            "irregularidades": [],
            "resumo": (conteudo[:500] if conteudo else "Não foi possível analisar o relatório de amostragem"),
        }

    dados["model_used"] = model
    dados["texto_bruto"] = texto[:2000]
    return dados


def _extrair_amostragem_word(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Analisa a petição ou relatório Word da amostragem para:
    1. Extrair o vocabulário jurídico e o estilo argumentativo da perita (Style Transfer).
    2. Salvar os padrões aprendidos em skills/amostragem_style.md para uso futuro.

    Isso garante que o sistema replique o vocabulário, estrutura e tom da perita
    ao gerar futuros pareceres técnicos — quanto mais arquivos Word, mais fiel fica.
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto.strip():
        return {"erro": "Documento sem texto legível", "style_atualizado": False, "estilo": {}}

    prompt = (
        "Você é especialista em análise de linguagem jurídica e style transfer.\n"
        "Analise o documento pericial trabalhista abaixo e extraia os padrões de escrita.\n\n"
        "Extraia em JSON puro:\n"
        "{\n"
        '  "vocabulario_tecnico": ["10-20 termos jurídicos/técnicos usados pela perita"],\n'
        '  "expressoes_caracteristicas": ["5-10 expressões ou frases típicas da escrita"],\n'
        '  "estrutura_argumentativa": "descrição da estrutura lógica (ex: tese → prova → conclusão)",\n'
        '  "tom": "objetivo|formal|técnico|misto",\n'
        '  "exemplo_paragrafo_abertura": "trecho real de como a perita abre um relatório/petição",\n'
        '  "exemplo_paragrafo_conclusao": "trecho real de como a perita conclui uma irregularidade",\n'
        '  "verbas_mencionadas": ["verbas trabalhistas identificadas no documento"],\n'
        '  "tabelas_comparativas": true,\n'
        '  "resumo_estilo": "2-3 frases descrevendo o estilo de escrita da perita"\n'
        "}\n\n"
        "IMPORTANTE: Responda APENAS com o JSON válido, sem markdown.\n\n"
        f"DOCUMENTO (primeiros 5000 caracteres):\n{texto[:5000]}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)

    dados_estilo: Dict[str, Any] = {}
    try:
        conteudo_limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        dados_estilo = json.loads(conteudo_limpo)
    except Exception:
        dados_estilo = {
            "resumo_estilo": (conteudo[:500] if conteudo else "Não foi possível analisar o estilo"),
            "vocabulario_tecnico": [],
            "expressoes_caracteristicas": [],
            "tom": "desconhecido",
        }

    # Style Transfer: persiste em skills/amostragem_style.md
    style_salvo = _atualizar_skill_amostragem(dados_estilo, texto[:2000], filename)

    return {
        "estilo": dados_estilo,
        "model_used": model,
        "style_atualizado": style_salvo,
        "texto_bruto": texto[:1000],
        "erro": None,
    }


def _extrair_peticao_inicial(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai da Petição Inicial (PDF ou DOCX) as verbas PEDIDAS pelo reclamante,
    causa de pedir, período reivindicado e valor da causa.
    Foco: quais verbas o reclamante pediu e qual o fundamento jurídico.
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto.strip():
        return {
            "erro": "Documento sem texto legível",
            "verbas_pedidas": [],
            "causa_pedir": "",
            "periodo_reivindicado": "",
            "valor_causa": None,
        }

    prompt = (
        "Você é um assistente jurídico especializado em Direito do Trabalho Brasileiro.\n"
        "Analise o texto abaixo de uma PETIÇÃO INICIAL trabalhista e extraia informações em JSON puro.\n\n"
        "Foco: quais verbas o reclamante PEDIU (independente de terem sido deferidas) e qual o fundamento jurídico.\n\n"
        "Extraia EXATAMENTE no formato JSON:\n"
        "{\n"
        '  "verbas_pedidas": ["lista de verbas trabalhistas pedidas pelo reclamante, ex: Horas Extras, FGTS, 13º Salário"],\n'
        '  "causa_pedir": "resumo objetivo da causa de pedir principal",\n'
        '  "periodo_reivindicado": "período em formato DD/MM/AAAA a DD/MM/AAAA ou vazio se não identificado",\n'
        '  "valor_causa": "R$ X.XXX,XX ou null se não informado"\n'
        "}\n\n"
        "IMPORTANTE: Responda APENAS com o JSON válido, sem markdown, sem texto antes ou depois.\n\n"
        f"TEXTO DA PETIÇÃO INICIAL (primeiros 5000 caracteres):\n{texto[:5000]}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)

    dados: Dict[str, Any] = {
        "verbas_pedidas": [],
        "causa_pedir": "",
        "periodo_reivindicado": "",
        "valor_causa": None,
    }
    try:
        conteudo_limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        parsed = json.loads(conteudo_limpo)
        dados["verbas_pedidas"] = parsed.get("verbas_pedidas") or []
        dados["causa_pedir"] = (parsed.get("causa_pedir") or "").strip()
        dados["periodo_reivindicado"] = (parsed.get("periodo_reivindicado") or "").strip()
        dados["valor_causa"] = parsed.get("valor_causa")
    except Exception:
        pass

    dados["model_used"] = model
    return dados


def _extrair_contestacao(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai da Contestação (PDF ou DOCX) teses de defesa estruturadas e campos legados
    para o Lab (argumentos_exclusao, teses_empresa, verbas_negadas, sumulas_citadas).

    O array `teses_defesa` é a fonte principal (Cenário 2); os campos legados são
    derivados quando a IA não os preenche, para não quebrar relatórios existentes.
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto.strip():
        return {
            "erro": "Documento sem texto legível",
            "numero_processo": None,
            "reclamante": None,
            "reclamada": None,
            "valor_causa": None,
            "teses_defesa": [],
            "argumentos_exclusao": [],
            "teses_empresa": [],
            "verbas_negadas": [],
            "sumulas_citadas": [],
        }

    trecho_ia = texto[:8000]
    prompt = (
        "Você é um assistente jurídico especializado em Direito do Trabalho Brasileiro.\n"
        "Analise o texto abaixo de uma CONTESTAÇÃO trabalhista (resposta da reclamada) "
        "e responda em JSON puro.\n\n"
        "1) Preencha `teses_defesa`: para cada PEDIDO da inicial que a defesa trate, "
        "uma linha com verba_alvo, tese_principal, trecho_fundamentacao (trecho CURTO, "
        "máximo 150 caracteres, copiado do texto quando possível), incontroversa "
        "(true se não impugnar ou admitir/confessar).\n"
        "2) Opcionalmente preencha argumentos_exclusao, teses_empresa, verbas_negadas, "
        "sumulas_citadas; se omitir, serão deduzidos de teses_defesa.\n"
        "3) Se possível, numero_processo, reclamante, reclamada e valor_causa.\n\n"
        "Formato JSON esperado:\n"
        "{\n"
        '  "numero_processo": null,\n'
        '  "reclamante": null,\n'
        '  "reclamada": null,\n'
        '  "valor_causa": null,\n'
        '  "teses_defesa": [\n'
        "    {\n"
        '      "verba_alvo": "Horas Extras",\n'
        '      "tese_principal": "Resumo da tese (ex.: cargo de confiança)",\n'
        '      "trecho_fundamentacao": "trecho curto literal",\n'
        '      "incontroversa": false\n'
        "    }\n"
        "  ],\n"
        '  "argumentos_exclusao": [],\n'
        '  "teses_empresa": [],\n'
        '  "verbas_negadas": [],\n'
        '  "sumulas_citadas": []\n'
        "}\n\n"
        "IMPORTANTE: Responda APENAS com JSON válido, sem markdown.\n\n"
        f"TEXTO DA CONTESTAÇÃO (até 8000 caracteres):\n{trecho_ia}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)

    dados: Dict[str, Any] = {
        "numero_processo": None,
        "reclamante": None,
        "reclamada": None,
        "valor_causa": None,
        "teses_defesa": [],
        "argumentos_exclusao": [],
        "teses_empresa": [],
        "verbas_negadas": [],
        "sumulas_citadas": [],
    }
    try:
        conteudo_limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        parsed = json.loads(conteudo_limpo)
        dados["numero_processo"] = parsed.get("numero_processo")
        dados["reclamante"] = parsed.get("reclamante")
        dados["reclamada"] = parsed.get("reclamada")
        dados["valor_causa"] = parsed.get("valor_causa")
        dados["teses_defesa"] = parsed.get("teses_defesa") or []
        dados["argumentos_exclusao"] = parsed.get("argumentos_exclusao") or []
        dados["teses_empresa"] = parsed.get("teses_empresa") or []
        dados["verbas_negadas"] = parsed.get("verbas_negadas") or []
        dados["sumulas_citadas"] = parsed.get("sumulas_citadas") or []
    except Exception:
        pass

    teses = dados.get("teses_defesa") or []
    arg_ded, verbas_ded, teses_ded = _derivar_campos_legados_contestacao(teses)
    if not (dados.get("argumentos_exclusao") or []):
        dados["argumentos_exclusao"] = arg_ded
    if not (dados.get("verbas_negadas") or []):
        dados["verbas_negadas"] = verbas_ded
    if not (dados.get("teses_empresa") or []):
        dados["teses_empresa"] = teses_ded

    dados["model_used"] = model
    return dados


def _atualizar_skill_amostragem(dados_estilo: dict, trecho_original: str, filename: str = "") -> bool:
    """
    Cria ou atualiza skills/amostragem_style.md com os padrões de estilo extraídos
    do documento Word da perita. Cada chamada ADICIONA um novo bloco ao arquivo,
    acumulando aprendizado de múltiplas amostragens.
    """
    os.makedirs(_SKILLS_DIR, exist_ok=True)
    destino = os.path.join(_SKILLS_DIR, "amostragem_style.md")
    data = datetime.now().strftime("%Y-%m-%d %H:%M")

    vocabulario = "\n".join(
        f"- {v}" for v in (dados_estilo.get("vocabulario_tecnico") or [])[:20]
    )
    expressoes = "\n".join(
        f"- {e}" for e in (dados_estilo.get("expressoes_caracteristicas") or [])[:10]
    )

    bloco = f"""

---

## Amostragem Analisada — {data} | {filename}

**Resumo do estilo:**
{dados_estilo.get("resumo_estilo") or "Não identificado"}

**Tom:** {dados_estilo.get("tom") or "—"}
**Estrutura argumentativa:** {dados_estilo.get("estrutura_argumentativa") or "—"}
**Tabelas comparativas:** {"Sim" if dados_estilo.get("tabelas_comparativas") else "Não"}

**Vocabulário técnico identificado:**
{vocabulario or "— Não identificado"}

**Expressões características da perita:**
{expressoes or "— Não identificadas"}

**Exemplo de abertura:**
> {dados_estilo.get("exemplo_paragrafo_abertura") or "—"}

**Exemplo de conclusão de irregularidade:**
> {dados_estilo.get("exemplo_paragrafo_conclusao") or "—"}

**Trecho original (referência):**
```
{trecho_original[:500]}
```
"""

    try:
        if not os.path.exists(destino):
            cabecalho = (
                "# Guia de Estilo da Perita — Amostragens Analisadas\n\n"
                "Este arquivo é atualizado automaticamente pelo Laboratório de Aprendizado\n"
                "sempre que uma nova **Amostragem Word** é submetida.\n\n"
                "Ele serve como base para **Style Transfer**: garante que o sistema replique\n"
                "o vocabulário, a estrutura argumentativa e o tom da perita ao gerar pareceres.\n\n"
                "**Como usar:** inclua este arquivo no system prompt ao gerar pareceres técnicos.\n"
                "**Nota:** cada bloco abaixo representa uma amostragem diferente — mais blocos = mais fidelidade.\n"
            )
            with open(destino, "w", encoding="utf-8") as f:
                f.write(cabecalho + bloco)
        else:
            with open(destino, "a", encoding="utf-8") as f:
                f.write(bloco)
        _logger.info(
            "learning_amostragem_style_updated",
            extra={"nome_arquivo": filename, "tenant_id": current_tenant_id() or "anonimo"},
        )
        return True
    except Exception as e:
        _logger.error(
            "learning_amostragem_style_update_error",
            extra={"nome_arquivo": filename, "error": str(e), "tenant_id": current_tenant_id() or "anonimo"},
        )
        return False


def _gerar_regras_preditivas_amostragem(
    dados_amostragem_pdf: Dict,
    dados_sentenca: Dict,
    dados_liquidacao: Dict,
) -> List[Dict]:
    """
    Cross-reference entre Amostragem + Sentença + Liquidação para gerar regras preditivas.

    Lógica de causa e efeito:
      "Sempre que a sentença deferir [verba X] com base na tese [Y] (provada na amostragem),
       verifique [parâmetro Z] no PJe-Calc (Art. W CLT), pois é uma omissão sistemática."

    Essas regras são adicionadas com prioridade máxima aos aprendizados do relatório.
    """
    regras: List[Dict] = []
    irregularidades = dados_amostragem_pdf.get("irregularidades") or []
    teses           = dados_amostragem_pdf.get("teses_provadas") or []

    # Regras preditivas baseadas em irregularidades detalhadas
    for irreg in irregularidades:
        verba         = (irreg.get("verba") or "").strip()
        irregularidade = (irreg.get("irregularidade") or "").strip()
        art_clt       = (irreg.get("art_clt") or "CLT").strip()

        if verba and irregularidade:
            regras.append({
                "tipo": "regra",
                "titulo": f"Regra Preditiva: {verba} — {irregularidade[:60]}",
                "descricao": (
                    f"Tese vencedora identificada na amostragem pericial: {irregularidade}. "
                    f"Quando a sentença deferir '{verba}', auditar parametrização no PJe-Calc "
                    f"pois a empresa omite sistematicamente este parâmetro."
                ),
                "correcao": (
                    f"Verificar e corrigir parametrização de '{verba}' no PJe-Calc "
                    f"conforme {art_clt}. Usar holerites e cartões de ponto como contraprova."
                ),
                "base_legal": art_clt,
                "nivel_sugerido": "AVISO",
                "prioridade_sugerida": 25,
                "origem": "amostragem_cross_reference",
            })

    # Regras genéricas para teses sem irregularidades estruturadas
    for tese in teses[:5]:
        tese_norm = tese.lower()
        already_covered = any(tese_norm in r["titulo"].lower() for r in regras)
        if not already_covered:
            regras.append({
                "tipo": "playbook",
                "titulo": f"Tese Vencedora: {tese[:80]}",
                "descricao": (
                    f"Tese provada pela perita na amostragem pericial: {tese}. "
                    "Registrar como playbook para orientar auditoria futura de cálculos similares."
                ),
                "base_legal": "Amostragem pericial — cross-reference sentença/liquidação",
                "nivel_sugerido": "INFO",
                "prioridade_sugerida": 35,
                "origem": "amostragem_tese",
            })

    return regras


def _resumir_triada_pericial(
    dados_amostragem_pdf: Optional[Dict],
    dados_sentenca: Dict,
    dados_calculo_pjc: Optional[Dict],
) -> Dict[str, Any]:
    """
    Gera um resumo estruturado da "Tríade da Liquidação":
      - Tese na Amostragem (prova)
      - Deferimento na Sentença (direito)
      - Estado no cálculo (.PJC)

    Esse resumo é usado apenas para interface (view do Lab) e para logs;
    o aprendizado autônomo continua sendo feito pelo Self-Healing Rule Engine.
    """
    amos_ok = bool(dados_amostragem_pdf and (dados_amostragem_pdf.get("teses_provadas") or dados_amostragem_pdf.get("irregularidades")))
    sent_ok = bool(dados_sentenca)
    pjc_ok  = bool(dados_calculo_pjc)

    triade = {
        "amostragem_presente": amos_ok,
        "sentenca_presente": sent_ok,
        "pjc_presente": pjc_ok,
    }

    teses = (dados_amostragem_pdf or {}).get("teses_provadas") or []
    irregs = (dados_amostragem_pdf or {}).get("irregularidades") or []
    triade["tese_principal"] = teses[0] if teses else (irregs[0].get("irregularidade") if irregs else None)

    campos_sent = (dados_sentenca or {}).get("campos_chave") or {}
    triade["verba_chave_sentenca"] = None
    if (dados_sentenca or {}).get("verbas"):
        triade["verba_chave_sentenca"] = (dados_sentenca.get("verbas") or [None])[0]

    verbas_pjc = (dados_calculo_pjc or {}).get("verbas_calculadas") or []
    triade["tem_verbas_pjc"] = bool(verbas_pjc)

    ausentes = []
    if not amos_ok:
        ausentes.append("Amostragem")
    if not sent_ok:
        ausentes.append("Processo")
    if not pjc_ok:
        ausentes.append(".PJC")

    if not ausentes:
        triade["aviso"] = "Tríade completa: Amostragem, Processo e .PJC disponíveis para auditoria cruzada."
    elif not pjc_ok and sent_ok:
        triade["aviso"] = (
            "Cálculo .PJC não fornecido: a IA não pôde validar a parametrização matemática deste caso."
        )
    else:
        triade["aviso"] = (
            f"Análise parcial: {', '.join(ausentes)} não fornecido(s). "
            "Recomenda-se Amostragem + Processo + .PJC para auditoria completa."
        )

    return triade


# ══════════════════════════════════════════════════════════════════════════════
# SELF-HEALING RULE ENGINE — Aprendizado Autônomo
# Extrai lógica de correção em JSON estruturado, atualiza o Knowledge Base e
# avalia hipóteses shadow contra os pareceres reais submetidos ao laboratório.
# ══════════════════════════════════════════════════════════════════════════════

def _montar_bloco_tese_impugnacao(relatorio: Dict) -> str:
    """
    Monta o bloco de texto com a tese de combate / argumento da impugnação ou parecer
    para injetar no prompt do Gemini, de modo que a regra gerada foque no erro de
    cálculo (ex: 6/12 vs 8/12 avos) e não apenas em 'verba ausente'.
    """
    partes = []
    # Manifestação pericial (Tríade 8 arquivos): argumento vencedor
    man_pericial = relatorio.get("manifestacao_pericial") or {}
    arg_vencedor = (man_pericial.get("argumento_vencedor") or "").strip()
    if arg_vencedor:
        partes.append(f"ARGUMENTO VENCEDOR DA PERITA (use como foco da regra):\n{arg_vencedor[:1500]}")
    # Impugnação (fluxo 5 arquivos): argumentos da parte
    impug = relatorio.get("impugnacao") or {}
    args_parte = impug.get("argumentos_da_parte") or []
    if args_parte:
        if isinstance(args_parte, list):
            texto_args = "\n".join(str(a)[:300] for a in args_parte[:5])
        else:
            texto_args = str(args_parte)[:800]
        partes.append(f"ARGUMENTOS DA IMPUGNAÇÃO (erro alegado pela empresa / rebate da perita):\n{texto_args}")
    # Manifestação/parecer: discrepâncias levantadas (trechos que a perita corrigiu)
    manifest = relatorio.get("manifestacao") or {}
    disc_levant = manifest.get("discrepancias_levantadas") or []
    if disc_levant:
        if isinstance(disc_levant, list):
            texto_disc = "\n".join(str(d)[:200] for d in disc_levant[:5])
        else:
            texto_disc = str(disc_levant)[:600]
        partes.append(f"DISCREPÂNCIAS LEVANTADAS NO PARECER:\n{texto_disc}")
    if not partes:
        return "TESE DE COMBATE / ARGUMENTO DA IMPUGNAÇÃO: (não informado neste relatório)"
    return "TESE DE COMBATE / ARGUMENTO DA IMPUGNAÇÃO OU PARECER (use como foco principal da regra):\n" + "\n\n".join(partes)


def _tese_tem_argumento_matematico(relatorio: Dict) -> bool:
    """
    Detecta se a impugnação ou manifestação contém argumentos detalhados de cálculo
    (avos, frações, projeção) para que o prompt do Gemini priorize regra sobre o erro
    matemático e ignore discrepâncias genéricas de verba_ausente.
    """
    texto = ""
    for key in ("manifestacao_pericial", "impugnacao", "manifestacao"):
        bloc = relatorio.get(key) or {}
        if isinstance(bloc, dict):
            arg = bloc.get("argumento_vencedor") or bloc.get("argumentos_da_parte") or ""
            if isinstance(arg, list):
                arg = " ".join(str(x) for x in arg)
            texto += " " + (arg or "")
        else:
            texto += " " + str(bloc)
    texto = texto.lower()
    padroes = [
        r"\d+\s*/\s*12",           # 6/12, 8/12 avos
        r"avos?\b",
        r"proje[cç][aã]o",
        r"proporcional",
        r"f[eé]rias.*13|13.*f[eé]rias",
        r"aviso\s*pr[eé]vio.*(?:f[eé]rias|13)",
    ]
    for pat in padroes:
        if re.search(pat, texto, re.IGNORECASE):
            return True
    return False


def _extrair_logica_correcao_gemini(relatorio: Dict) -> List[Dict]:
    """
    Usa Gemini para extrair, do relatório de discrepâncias, a lógica de correção
    em formato JSON estruturado — não gera código Python imediatamente.

    Cada item retornado representa uma hipótese de regra candidata ao Knowledge Base:
    {
      "descricao":   str,
      "condicao":    {"tipo": "verba_ausente|campo_diferente|...", "verba"?: str, "campo"?: str, "valor_esperado"?: str},
      "acao":        {"tipo": "alerta", "nivel": "AVISO|ERRO", "mensagem": str},
      "base_legal":  str
    }

    Tipos de condição suportados pelo DynamicLegalRule:
      verba_ausente   — verba deferida mas não calculada
      verba_presente  — verba inesperadamente presente
      indice_ausente  — índice de correção não informado
      campo_ausente   — campo obrigatório vazio
      campo_diferente — campo diverge do esperado
    """
    # Lista já filtrada pelo guardrail (falsos positivos de verba ausente removidos)
    discrepancias_filtradas = relatorio.get("discrepancias") or []
    verbas_sentenca = (relatorio.get("sentenca") or {}).get("verbas") or []
    verbas_liquidacao = (relatorio.get("liquidacao") or {}).get("verbas_calculadas") or []
    indice_sentenca = ((relatorio.get("sentenca") or {}).get("campos_chave") or {}).get("indice_correcao", "")
    indice_liq = (relatorio.get("liquidacao") or {}).get("indice_correcao", "")

    tese_tem_detalhe = _tese_tem_argumento_matematico(relatorio)

    # REGRA 3 (early exit): sem discrepâncias filtradas e sem tese matemática → não chamar Gemini
    if not discrepancias_filtradas and not tese_tem_detalhe:
        return []

    if not discrepancias_filtradas and not verbas_sentenca:
        return []

    tese_bloco = _montar_bloco_tese_impugnacao(relatorio)
    # JSON explícito das discrepâncias FILTRADAS — única fonte permitida para regras de discrepância
    disc_filtradas_json = json.dumps(discrepancias_filtradas[:10], ensure_ascii=False)

    instrucao_avos = (
        "\nREGRA OBRIGATÓRIA: Se a TESE DE COMBATE / ARGUMENTO contiver detalhes de CÁLCULO "
        "(avos, frações como 6/12 vs 8/12, projeção de aviso prévio em férias ou 13º), "
        "a IA DEVE criar a regra BASEADA NESSE ARGUMENTO MATEMÁTICO/JURÍDICO. "
        "NÃO gere hipóteses com tipo 'verba_ausente' nesse caso — ignore discrepâncias genéricas de ausência. "
        "Use condicao tipo 'campo_diferente' com campo/valor_esperado que espelhem o erro (ex: 8/12 avos, método correto).\n\n"
    ) if tese_tem_detalhe else ""

    prompt = (
        "Você é um Engenheiro de Machine Learning especializado em Direito Trabalhista.\n"
        "Analise o relatório abaixo e extraia a lógica de correção como uma lista de HIPÓTESES DE REGRA em JSON puro.\n\n"
        "FONTE ÚNICA PARA DISCREPÂNCIAS: Use APENAS o JSON de 'DISCREPÂNCIAS FILTRADAS' abaixo. "
        "Essa lista já passou por um guardrail que removeu falsos positivos de verba ausente.\n\n"
        "INSTRUÇÕES ESTRITAS:\n"
        "REGRA 1: É ESTRITAMENTE PROIBIDO gerar regras do tipo 'verba_ausente' ou apontar falta de verbas que NÃO estejam explicitamente listadas no JSON de discrepâncias filtradas. Só use verba_ausente se a verba aparecer em alguma entrada desse JSON.\n"
        "REGRA 2: Se houver texto na seção de IMPUGNAÇÃO/MANIFESTAÇÃO, você DEVE ignorar discrepâncias genéricas e criar regras EXCLUSIVAMENTE baseadas nos argumentos matemáticos e teses da defesa (ex: diferenças de avos 6/12 vs 8/12, bases de cálculo, exclusão de reflexos).\n"
        "REGRA 3: Se as discrepâncias filtradas estiverem vazias e a impugnação não contiver uma tese matemática clara, retorne uma lista vazia [].\n\n"
        "PRIORIDADE: Use a TESE DE COMBATE / ARGUMENTO DA IMPUGNAÇÃO OU PARECER como foco principal. "
        "Quando o argumento descrever um ERRO DE CÁLCULO, gere a regra com condicao tipo campo_diferente e NÃO use verba_ausente.\n\n"
        f"{instrucao_avos}"
        "Para cada hipótese, gere um objeto com:\n"
        "{\n"
        '  "descricao": "frase curta (preferir tese de combate quando houver)",\n'
        '  "condicao": {\n'
        '    "tipo": "verba_ausente" | "verba_presente" | "indice_ausente" | "campo_ausente" | "campo_diferente",\n'
        '    "verba": "nome da verba somente se constar no JSON de discrepâncias filtradas",\n'
        '    "campo": "nome do campo Python se aplicável",\n'
        '    "valor_esperado": "valor correto esperado (ex: 8/12 avos)"\n'
        "  },\n"
        '  "acao": {"tipo": "alerta", "nivel": "ERRO" | "AVISO", "mensagem": "texto do alerta"},\n'
        '  "base_legal": "ex: Art. 59 CLT, Súmula 264 TST"\n'
        "}\n\n"
        "REGRAS GERAIS:\n"
        "- Gere APENAS hipóteses com fundamento nos dados abaixo (nenhuma invenção).\n"
        "- Máximo 5 hipóteses. Responda APENAS com o array JSON, sem markdown.\n\n"
        f"{tese_bloco}\n\n"
        f"Verbas na sentença: {verbas_sentenca}\n"
        f"Verbas na liquidação: {verbas_liquidacao}\n"
        f"Índice sentença: {indice_sentenca} | Índice liquidação: {indice_liq}\n\n"
        f"DISCREPÂNCIAS FILTRADAS (use somente esta lista — não invente verbas ausentes):\n{disc_filtradas_json}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)
    logicas: List[Dict] = []

    try:
        limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        parsed = json.loads(limpo)
        if isinstance(parsed, list):
            logicas = [l for l in parsed if isinstance(l, dict) and "condicao" in l]
        elif isinstance(parsed, dict) and "condicao" in parsed:
            logicas = [parsed]
    except Exception:
        _logger.warning(
            "kb_gemini_logic_json_invalid",
            extra={"tenant_id": current_tenant_id() or "anonimo"},
        )

    _logger.info(
        "kb_logic_hypotheses_extracted",
        extra={"quantidade": len(logicas), "model": model, "tenant_id": current_tenant_id() or "anonimo"},
    )
    return logicas


def processar_aprendizado_autonomo(
    relatorio: Dict,
    numero_processo: str = "",
    user_id: Optional[str] = None,
) -> Dict:
    return self_healing.processar_aprendizado_autonomo(
        relatorio,
        numero_processo,
        user_id=user_id,
        extrair_logica_correcao_gemini=_extrair_logica_correcao_gemini,
        filtrar_logicas_verba_ausente_falsas=_filtrar_logicas_verba_ausente_falsas,
    )


# ── Manifestação Pericial: Duplo Style Transfer (facade → style_transfer, Passo 5) ─

def _merge_dados_manifestacao(
    base: Optional[Dict[str, Any]], novo: Dict[str, Any]
) -> Dict[str, Any]:
    return style_transfer.merge_dados_manifestacao(base, novo)


def _extrair_manifestacao_pericial(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    return style_transfer.extrair_manifestacao_pericial(
        file_bytes,
        filename,
        extrair_texto_arquivo=_extrair_texto_arquivo,
        chamar_gemini_para_codify=_chamar_gemini_para_codify,
        skills_dir=_SKILLS_DIR,
    )


# ── Processamento com 7 arquivos (Linha do Tempo completa) ───────────────────

def processar_sete_arquivos(
    processo_bytes: Optional[bytes] = None,
    processo_filename: str = "",
    processo_arquivos: Optional[List[tuple]] = None,
    liquidacao_bytes: Optional[bytes] = None,
    liquidacao_filename: str = "",
    parecer_bytes: Optional[bytes] = None,
    parecer_filename: str = "",
    impugnacao_bytes: Optional[bytes] = None,
    impugnacao_filename: str = "",
    calculo_pjc_bytes: Optional[bytes] = None,
    calculo_pjc_filename: str = "",
    amostragem_pdf_bytes: Optional[bytes] = None,
    amostragem_pdf_filename: str = "",
    amostragem_word_bytes: Optional[bytes] = None,
    amostragem_word_filename: str = "",
    amostragens_arquivos: Optional[List[tuple]] = None,
    manifestacao_bytes: Optional[bytes] = None,
    manifestacao_filename: str = "",
    peticao_bytes: Optional[bytes] = None,
    peticao_filename: str = "",
    contestacao_bytes: Optional[bytes] = None,
    contestacao_filename: str = "",
) -> Dict[str, Any]:
    """
    Ponto de entrada para o endpoint /lab/analisar (até 8 arquivos).

    Linha do Tempo da Fraude Trabalhista:
      [1] Amostragem PDF  — O que a perita provou (holerites / cartões de ponto)
      [2] Amostragem Word — Como a perita escreve (Style Transfer → amostragem_style.md)
      [3] Sentença         — O que o juiz deferiu (com base na prova)
      [4] Liquidação       — O que a empresa calculou (com omissões)
      [5] Parecer          — Como a perita corrigiu
      [6] Impugnação       — Como a empresa contestou (opcional)
      [7] Cálculo PJC      — Parâmetros PJe-Calc para auditoria (opcional)
      [8] Manifestação     — Como a perita rebateu a empresa — retórica de combate (opcional)

    Ao combinar todos os dados, o motor gera:
    - Regras preditivas baseadas na tese vencedora (amostragem × sentença)
    - Style transfer: atualiza skills/amostragem_style.md e skills/manifestacao_style.md
    - Padrões Ataque/Defesa codificados no Knowledge Base como Shadow Rules
    - Aprendizados para codificação (regras Python + playbook Markdown)

    Obrigatórios lógicos para discrepâncias ricas: processo, liquidacao, parecer.
    Porém, a API permite qualquer combinação (inclusive apenas processo ou apenas
    parecer). Quando algum estiver ausente, partes do relatório ficam vazias,
    mas o motor continua funcionando sem erro.
    """
    _logger.info(
        "learning_timeline_analysis_start",
        extra={
            "amostragem_pdf": amostragem_pdf_filename or "(nao enviado)",
            "amostragem_word": amostragem_word_filename or "(nao enviado)",
            "sentenca": processo_filename,
            "liquidacao": liquidacao_filename,
            "parecer": parecer_filename,
            "impugnacao": impugnacao_filename or "(nao enviado)",
            "calculo_pjc": calculo_pjc_filename or "(nao enviado)",
            "manifestacao": manifestacao_filename or "(nao enviado)",
            "tenant_id": current_tenant_id() or "anonimo",
        },
    )

    # ── Fusão: Card de Provas pode suprir Parecer, Amostragem e Manifestação ──
    # Se o usuário enviou tudo no Card "Amostragens e Provas", autoclassificamos por conteúdo.
    texto_dossie_amostragens = None
    if amostragens_arquivos:
        (
            texto_dossie_amostragens,
            parecer_bytes,
            parecer_filename,
            amostragem_pdf_bytes,
            amostragem_pdf_filename,
            amostragem_word_bytes,
            amostragem_word_filename,
            manifestacao_bytes,
            manifestacao_filename,
        ) = _fusionar_provas_com_cards(
            amostragens_arquivos,
            parecer_bytes,
            parecer_filename,
            amostragem_pdf_bytes,
            amostragem_pdf_filename,
            amostragem_word_bytes,
            amostragem_word_filename,
            manifestacao_bytes,
            manifestacao_filename,
        )

    # ── Fase base: lógica dos 5 arquivos existente ────────────────────────────
    relatorio = processar_cinco_arquivos(
        processo_bytes=processo_bytes,
        processo_filename=processo_filename,
        processo_arquivos=processo_arquivos,
        liquidacao_bytes=liquidacao_bytes,
        liquidacao_filename=liquidacao_filename,
        parecer_bytes=parecer_bytes,
        parecer_filename=parecer_filename,
        impugnacao_bytes=impugnacao_bytes,
        impugnacao_filename=impugnacao_filename,
        calculo_pjc_bytes=calculo_pjc_bytes,
        calculo_pjc_filename=calculo_pjc_filename,
        peticao_bytes=peticao_bytes,
        peticao_filename=peticao_filename,
        contestacao_bytes=contestacao_bytes,
        contestacao_filename=contestacao_filename,
        texto_dossie_amostragens=texto_dossie_amostragens,
    )

    dados_amostragem_pdf_result = None

    # ── Fase de Conhecimento 1: Amostragem PDF (tese vencedora) ───────────────
    if amostragem_pdf_bytes:
        _logger.info(
            "learning_analisar_amostragem_pdf",
            extra={
                "nome_arquivo": amostragem_pdf_filename,
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
        dados_amostragem_pdf_result = _extrair_amostragem_pdf(amostragem_pdf_bytes, amostragem_pdf_filename)
        relatorio["amostragem_pdf"] = {
            "teses_provadas":      dados_amostragem_pdf_result.get("teses_provadas")      or [],
            "verbas_prova":        dados_amostragem_pdf_result.get("verbas_prova")        or [],
            "evidencias_utilizadas": dados_amostragem_pdf_result.get("evidencias_utilizadas") or [],
            "periodo_analisado":   dados_amostragem_pdf_result.get("periodo_analisado")   or "",
            "irregularidades":     dados_amostragem_pdf_result.get("irregularidades")     or [],
            "resumo":              dados_amostragem_pdf_result.get("resumo")              or "",
            "model_used":          dados_amostragem_pdf_result.get("model_used"),
            "erro":                dados_amostragem_pdf_result.get("erro"),
        }

    # ── Fase de Conhecimento 2: Amostragem Word (Style Transfer) ──────────────
    if amostragem_word_bytes:
        _logger.info(
            "learning_analisar_amostragem_word",
            extra={
                "nome_arquivo": amostragem_word_filename,
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
        dados_word = _extrair_amostragem_word(amostragem_word_bytes, amostragem_word_filename)
        relatorio["amostragem_word"] = {
            "estilo":          dados_word.get("estilo")          or {},
            "style_atualizado": dados_word.get("style_atualizado", False),
            "model_used":      dados_word.get("model_used"),
            "erro":            dados_word.get("erro"),
        }

    # ── Cross-reference: Amostragem × Sentença → Regras Preditivas ───────────
    # (só executa quando Amostragem PDF foi enviada)
    if dados_amostragem_pdf_result:
        dados_sentenca_raw   = relatorio.get("sentenca")   or {}
        dados_liquidacao_raw = relatorio.get("liquidacao") or {}
        regras_preditivas = _gerar_regras_preditivas_amostragem(
            dados_amostragem_pdf_result,
            dados_sentenca_raw,
            dados_liquidacao_raw,
        )
        if regras_preditivas:
            relatorio["aprendizados"] = regras_preditivas + (relatorio.get("aprendizados") or [])
            _logger.info(
                "learning_regras_preditivas_geradas",
                extra={
                    "quantidade": len(regras_preditivas),
                    "tenant_id": current_tenant_id() or "anonimo",
                },
            )

    # ── Tríade Pericial: sempre montada com o que estiver disponível ──────────
    # Independe da presença de Amostragem PDF — garante que a UI nunca
    # exiba falso-negativo para arquivos que foram realmente enviados.
    _sentenca_raw   = relatorio.get("sentenca")    or {}
    _calculo_pjc_raw = relatorio.get("calculo_pjc") or None
    relatorio["triade_pericial"] = _resumir_triada_pericial(
        dados_amostragem_pdf_result,  # None se não enviada — tratado internamente
        _sentenca_raw,
        _calculo_pjc_raw,
    )

    # ── Fase de Conhecimento 3: Duplo Style Transfer — Impugnação (Card 6) + Manifestação (Card 8) ───
    # Analisa padrões ataque/defesa de AMBOS os arquivos e atualiza skills/manifestacao_style.md com os dois.
    dados_manifestacao_pericial = None
    if impugnacao_bytes:
        _logger.info(
            "learning_analisar_impugnacao",
            extra={
                "nome_arquivo": impugnacao_filename,
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
        dados_imp = _extrair_manifestacao_pericial(impugnacao_bytes, impugnacao_filename)
        dados_manifestacao_pericial = _merge_dados_manifestacao(dados_manifestacao_pericial, dados_imp)
    if manifestacao_bytes:
        _logger.info(
            "learning_analisar_manifestacao",
            extra={
                "nome_arquivo": manifestacao_filename,
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
        dados_man = _extrair_manifestacao_pericial(manifestacao_bytes, manifestacao_filename)
        dados_manifestacao_pericial = _merge_dados_manifestacao(dados_manifestacao_pericial, dados_man)

    if dados_manifestacao_pericial:
        relatorio["manifestacao_pericial"] = {
            "frases_impacto":       dados_manifestacao_pericial.get("frases_impacto")       or [],
            "fundamentos_juridicos": dados_manifestacao_pericial.get("fundamentos_juridicos") or [],
            "padroes_ataque_defesa": dados_manifestacao_pericial.get("padroes_ataque_defesa") or [],
            "parametros_fraudados": dados_manifestacao_pericial.get("parametros_fraudados")  or [],
            "argumento_vencedor":   dados_manifestacao_pericial.get("argumento_vencedor")   or "",
            "verbas_em_disputa":    dados_manifestacao_pericial.get("verbas_em_disputa")    or [],
            "resumo":               dados_manifestacao_pericial.get("resumo")               or "",
            "style_atualizado":     dados_manifestacao_pericial.get("style_atualizado",     False),
            "model_used":           dados_manifestacao_pericial.get("model_used"),
            "erro":                 dados_manifestacao_pericial.get("erro"),
        }
        relatorio["triade_pericial"]["manifestacao"] = {
            "presente":           True,
            "argumento_vencedor": dados_manifestacao_pericial.get("argumento_vencedor") or "",
            "padroes_count":      len(dados_manifestacao_pericial.get("padroes_ataque_defesa") or []),
        }

    # ── Metadados completos ───────────────────────────────────────────────────
    arquivos = relatorio.get("arquivos_analisados") or {}
    arquivos["amostragem_pdf"]  = amostragem_pdf_filename  or None
    arquivos["amostragem_word"] = amostragem_word_filename or None
    if amostragens_arquivos:
        relatorio["dossie_amostragens_n_arquivos"] = len(amostragens_arquivos)
        arquivos["amostragens"] = [fn for _, fn in amostragens_arquivos]
    arquivos["manifestacao"]    = manifestacao_filename    or None
    arquivos["impugnacao"]      = impugnacao_filename     or None
    arquivos["peticao"]         = peticao_filename        or None
    arquivos["contestacao"]     = contestacao_filename     or None
    relatorio["arquivos_analisados"] = arquivos

    # ── Self-Healing Rule Engine: aprendizado autônomo ────────────────────────
    # Extrai hipóteses de regra das discrepâncias, atualiza o Knowledge Base e
    # avalia regras shadow existentes. Tudo em background, sem bloquear o fluxo.
    try:
        numero = relatorio.get("numero_processo", "")
        kb_resultado = processar_aprendizado_autonomo(relatorio, numero)
        relatorio["kb_aprendizado"] = kb_resultado
        _logger.info(
            "kb_self_healing_result",
            extra={
                "hipoteses": kb_resultado.get("hipoteses_extraidas", 0),
                "ativadas": kb_resultado.get("ativadas", 0),
                "stats": kb_resultado.get("stats_kb"),
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
    except Exception as e_kb:
        _logger.warning(
            "kb_self_healing_error",
            extra={"error": str(e_kb), "tenant_id": current_tenant_id() or "anonimo"},
        )
        relatorio["kb_aprendizado"] = {"erro": str(e_kb)}

    # Guardrail: remove aprendizados de verba_ausente falsa antes de enviar ao frontend
    _filtrar_aprendizados_verba_ausente_falsas(relatorio)

    total_disc = len(relatorio.get("discrepancias") or [])
    total_ap   = len(relatorio.get("aprendizados")  or [])
    _logger.info(
        "learning_analise_completa",
        extra={
            "discrepancias": total_disc,
            "aprendizados": total_ap,
            "tenant_id": current_tenant_id() or "anonimo",
        },
    )
    return relatorio


def processar_cinco_arquivos(
    processo_bytes: Optional[bytes] = None,
    processo_filename: str = "",
    processo_arquivos: Optional[List[tuple]] = None,
    liquidacao_bytes: Optional[bytes] = None,
    liquidacao_filename: str = "",
    parecer_bytes: Optional[bytes] = None,
    parecer_filename: str = "",
    impugnacao_bytes: Optional[bytes] = None,
    impugnacao_filename: str = "",
    calculo_pjc_bytes: Optional[bytes] = None,
    calculo_pjc_filename: str = "",
    peticao_bytes: Optional[bytes] = None,
    peticao_filename: str = "",
    contestacao_bytes: Optional[bytes] = None,
    contestacao_filename: str = "",
    texto_dossie_amostragens: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ponto de entrada para o endpoint /lab/analisar (5 arquivos).

    Obrigatórios lógicos para discrepâncias cheias: processo, liquidação, parecer.
    Porém, o chamador pode omitir qualquer um; nesse caso o motor preenche
    dicionários vazios e apenas reduz a riqueza do relatório, sem erro.

    Opcionais: impugnação, cálculo .PJC, petição inicial, contestação.

    Não salva nada — apenas analisa. Salvamento é feito via /lab/salvar.
    """
    print(f"[LEARNING] Iniciando análise: "
          f"{processo_filename or '(sem processo)'} | {liquidacao_filename or '(sem liquidação)'} | {parecer_filename or '(sem parecer)'} "
          f"| {impugnacao_filename or '—'} | {calculo_pjc_filename or '—'}")

    # 1. Processo/Sentença (ou Título Executivo Complexo quando há múltiplos arquivos)
    _arqs_processo = processo_arquivos if processo_arquivos else (
        [(processo_bytes, processo_filename or "processo.pdf")] if processo_bytes else []
    )
    timeline_result: Optional[Dict[str, Any]] = None
    pecas_extraidas_do_pdf: Dict[str, bool] = {}

    # PJe Timeline Extractor: quando há um único PDF no Card 3, mapear e fatiar peças
    if len(_arqs_processo) == 1:
        _proc_bytes, _proc_fn = _arqs_processo[0]
        if (_proc_fn or "").lower().endswith(".pdf"):
            try:
                from services.process_timeline_extractor import extract_timeline_from_pdf
                timeline_result = extract_timeline_from_pdf(_proc_bytes)
                for _line in timeline_result.get("log", []):
                    _logger.info(
                        "timeline_log_line",
                        extra={"line": _line, "tenant_id": current_tenant_id() or "anonimo"},
                    )
            except Exception as _e:
                _logger.warning(
                    "timeline_extract_error",
                    extra={"error": str(_e), "tenant_id": current_tenant_id() or "anonimo"},
                )
                timeline_result = None

    if len(_arqs_processo) > 1:
        _logger.info(
            "learning_titulo_executivo_complexo",
            extra={
                "quantidade_docs": len(_arqs_processo),
                "arquivos": [fn for _, fn in _arqs_processo],
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
        dados_processo = _extrair_titulo_executivo_multiplos(_arqs_processo, contexto_amostragens=texto_dossie_amostragens)
        ctx_texto = (dados_processo.get("contexto_decisao_final") or "")[:50000]
        if ctx_texto and dados_processo.get("dados") is not None:
            dados_processo["dados"] = _normalizar_nomes_verbas_pje_calc(
                _garantir_verbas_deferidas_preenchidas(dados_processo["dados"], ctx_texto)
            )
    elif _arqs_processo:
        dados_processo = _extrair_processo(_arqs_processo[0][0], _arqs_processo[0][1], contexto_amostragens=texto_dossie_amostragens)
    else:
        dados_processo = {"dados": {}}
        _logger.info(
            "learning_sem_processo",
            extra={"tenant_id": current_tenant_id() or "anonimo"},
        )

    # 2. Liquidação — opcional; ou extraída do PDF integral (Timeline)
    if liquidacao_bytes:
        dados_liquidacao = _extrair_liquidacao(liquidacao_bytes, liquidacao_filename)
    elif timeline_result and (timeline_result.get("textos") or {}).get("liquidacao"):
        dados_liquidacao = _liquidacao_from_text(timeline_result["textos"]["liquidacao"])
        pecas_extraidas_do_pdf["liquidacao"] = True
        _logger.info(
            "learning_liquidacao_extraida_timeline",
            extra={"tenant_id": current_tenant_id() or "anonimo"},
        )
    else:
        dados_liquidacao = {
            "verbas_calculadas": [],
            "indice_correcao": None,
            "juros_mora": None,
            "erro": "Liquidação não fornecida — comparação de verbas indisponível.",
        }
        _logger.info(
            "learning_liquidacao_nao_enviada",
            extra={"tenant_id": current_tenant_id() or "anonimo"},
        )

    # 3. Parecer — fundamentos + trechos; ou extraído do PDF integral (Timeline)
    if parecer_bytes:
        dados_parecer = _extrair_manifestacao(parecer_bytes)
    elif timeline_result and (timeline_result.get("textos") or {}).get("parecer"):
        dados_parecer = _extrair_manifestacao_from_text(timeline_result["textos"]["parecer"])
        pecas_extraidas_do_pdf["parecer"] = True
        _logger.info(
            "learning_parecer_extraido_timeline",
            extra={"tenant_id": current_tenant_id() or "anonimo"},
        )
    else:
        dados_parecer = {
            "texto_bruto": "",
            "fundamentos_juridicos": [],
            "discrepancias_levantadas": [],
            "erro": "Parecer não fornecido.",
        }
        _logger.info(
            "learning_parecer_nao_enviado",
            extra={"tenant_id": current_tenant_id() or "anonimo"},
        )

    # 4. Impugnação (opcional); ou extraída do PDF integral (Timeline)
    dados_impugnacao = None
    if impugnacao_bytes:
        dados_impugnacao = _extrair_impugnacao(impugnacao_bytes, impugnacao_filename)
    elif timeline_result and (timeline_result.get("textos") or {}).get("impugnacao"):
        dados_impugnacao = _extrair_impugnacao_from_text(timeline_result["textos"]["impugnacao"])
        pecas_extraidas_do_pdf["impugnacao"] = True
        _logger.info(
            "learning_impugnacao_extraida_timeline",
            extra={"tenant_id": current_tenant_id() or "anonimo"},
        )

    # 5. Cálculo .PJC (opcional)
    dados_calculo_pjc = None
    if calculo_pjc_bytes:
        dados_calculo_pjc = _extrair_calculo_pjc(calculo_pjc_bytes, calculo_pjc_filename)

    # Relatório base (processo como sentença, liquidação, parecer como manifestação)
    relatorio = gerar_relatorio_discrepancia(
        dados_sentenca=dados_processo,
        dados_liquidacao=dados_liquidacao,
        dados_manifestacao=dados_parecer,
    )

    # Renomear chave "manifestacao" → "parecer" no relatório para consistência com a UI
    if "manifestacao" in relatorio:
        relatorio["parecer"] = relatorio.pop("manifestacao")

    # Flex-Analysis: voto de maioria para numero_processo sempre que possível.
    # Candidatos:
    #  - numero_processo da sentença (já em relatorio)
    #  - numero_processo bruto do título executivo (dados_processo)
    #  - numero_processo eventualmente extraído da Petição Inicial
    #  - CNJ presente nos nomes de arquivos (processo/liquidação/parecer/petição/contestação)
    try:
        candidatos: list[str] = []

        atual = (relatorio.get("numero_processo") or "").strip()
        if atual:
            candidatos.append(atual)

        bruto_proc = (dados_processo.get("dados") or {}).get("numero_processo") or ""
        if bruto_proc:
            candidatos.append(str(bruto_proc).strip())

        pet = relatorio.get("peticao_inicial") or {}
        pet_num = (pet.get("numero_processo") or "").strip()
        if pet_num:
            candidatos.append(pet_num)

        import re as _re_cnj

        def _cnj_from_filename(fn: str | None) -> str | None:
            if not fn:
                return None
            m = _re_cnj.search(
                r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", fn
            )
            return m.group(0) if m else None

        for fn in [
            processo_filename,
            liquidacao_filename,
            parecer_filename,
            peticao_filename,
            contestacao_filename,
        ]:
            cnj = _cnj_from_filename(fn)
            if cnj:
                candidatos.append(cnj)

        votos: dict[str, int] = {}
        for c in candidatos:
            norm = c.strip()
            if not norm or norm.lower() in ("desconhecido", "n/a", "nao informado"):
                continue
            votos[norm] = votos.get(norm, 0) + 1

        if votos:
            vencedor = max(votos.items(), key=lambda kv: kv[1])[0]
            relatorio["numero_processo"] = vencedor
    except Exception:
        # Em caso de qualquer erro inesperado, preserva o comportamento anterior.
        pass

    # Enriquece com impugnação e cálculo PJC
    relatorio = _enriquecer_relatorio_com_extras(relatorio, dados_impugnacao, dados_calculo_pjc)

    # Propagar arquivos ignorados (duplicatas por hash ou mesma instância) do Card 3
    relatorio["arquivos_ignorados_duplicados"] = dados_processo.get("arquivos_ignorados_duplicados", [])

    # Timeline: fatiamento e peças extraídas do PDF (Barra de Eficiência)
    if timeline_result:
        relatorio["timeline_fatiamento"] = timeline_result.get("log", [])
    if pecas_extraidas_do_pdf:
        relatorio["pecas_extraidas_do_pdf"] = pecas_extraidas_do_pdf

    # ── Petição Inicial (opcional): verbas pedidas; ou extraída do PDF integral (Timeline) ──
    if peticao_bytes:
        _logger.info(
            "learning_analisar_peticao_inicial",
            extra={
                "nome_arquivo": peticao_filename,
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
        dados_peticao = _extrair_peticao_inicial(peticao_bytes, peticao_filename)
        relatorio["peticao_inicial"] = {
            "verbas_pedidas":       dados_peticao.get("verbas_pedidas") or [],
            "causa_pedir":          dados_peticao.get("causa_pedir") or "",
            "periodo_reivindicado": dados_peticao.get("periodo_reivindicado") or "",
            "valor_causa":          dados_peticao.get("valor_causa"),
            "model_used":           dados_peticao.get("model_used"),
            "erro":                 dados_peticao.get("erro"),
        }
        # Cruzar verbas pedidas com deferidas para identificar verbas negadas
        verbas_pedidas = [str(v).strip() for v in (dados_peticao.get("verbas_pedidas") or []) if str(v).strip()]
        verbas_deferidas = list((relatorio.get("sentenca") or {}).get("verbas") or [])
        try:
            from services.legal_engine.rule_base import LegalRule
            canon_deferidas = {LegalRule._canonizar_verba(v) for v in verbas_deferidas}
            verbas_negadas_identificadas = [
                v for v in verbas_pedidas
                if LegalRule._canonizar_verba(v) and LegalRule._canonizar_verba(v) not in canon_deferidas
            ]
            relatorio["peticao_inicial"]["verbas_negadas_identificadas"] = verbas_negadas_identificadas
        except Exception:
            relatorio["peticao_inicial"]["verbas_negadas_identificadas"] = []
    elif timeline_result and (timeline_result.get("textos") or {}).get("peticao_inicial"):
        try:
            from services.process_timeline_extractor import PjeTimelineExtractor, CHAVE_PETICAO
            from services.ai_client import extract_data_with_gemini
            _txt = timeline_result["textos"]["peticao_inicial"]
            _meta = PjeTimelineExtractor.extrair_metadados_peca(CHAVE_PETICAO, _txt, extract_data_with_gemini)
            _d = _meta.get("dados") or {}
            relatorio["peticao_inicial"] = {
                "verbas_pedidas":       _d.get("verbas_pedidas") or [],
                "causa_pedir":          (_d.get("causa_pedir") or "").strip(),
                "periodo_reivindicado": (_d.get("periodo_reivindicado") or "").strip(),
                "valor_causa":          _d.get("valor_causa"),
                "model_used":           _meta.get("model_used"),
                "erro":                 _meta.get("erro"),
            }
            pecas_extraidas_do_pdf["peticao"] = True
            verbas_pedidas = [str(v).strip() for v in relatorio["peticao_inicial"].get("verbas_pedidas") or [] if str(v).strip()]
            verbas_deferidas = list((relatorio.get("sentenca") or {}).get("verbas") or [])
            try:
                from services.legal_engine.rule_base import LegalRule
                canon_deferidas = {LegalRule._canonizar_verba(v) for v in verbas_deferidas}
                relatorio["peticao_inicial"]["verbas_negadas_identificadas"] = [
                    v for v in verbas_pedidas
                    if LegalRule._canonizar_verba(v) and LegalRule._canonizar_verba(v) not in canon_deferidas
                ]
            except Exception:
                relatorio["peticao_inicial"]["verbas_negadas_identificadas"] = []
        except Exception as _e:
            _logger.warning(
                "timeline_peticao_metadados_failed",
                extra={"error": str(_e), "tenant_id": current_tenant_id() or "anonimo"},
            )

    # ── Contestação (opcional); ou extraída do PDF integral (Timeline) ─────────
    if contestacao_bytes:
        _logger.info(
            "learning_analisar_contestacao",
            extra={
                "nome_arquivo": contestacao_filename,
                "tenant_id": current_tenant_id() or "anonimo",
            },
        )
        dados_contestacao = _extrair_contestacao(contestacao_bytes, contestacao_filename)
        relatorio["contestacao"] = {
            "teses_defesa":        dados_contestacao.get("teses_defesa") or [],
            "numero_processo":     dados_contestacao.get("numero_processo"),
            "reclamante":          dados_contestacao.get("reclamante"),
            "reclamada":           dados_contestacao.get("reclamada"),
            "valor_causa":         dados_contestacao.get("valor_causa"),
            "argumentos_exclusao": dados_contestacao.get("argumentos_exclusao") or [],
            "teses_empresa":       dados_contestacao.get("teses_empresa") or [],
            "verbas_negadas":      dados_contestacao.get("verbas_negadas") or [],
            "sumulas_citadas":     dados_contestacao.get("sumulas_citadas") or [],
            "model_used":          dados_contestacao.get("model_used"),
            "erro":                dados_contestacao.get("erro"),
        }
    elif timeline_result and (timeline_result.get("textos") or {}).get("contestacao"):
        try:
            from services.process_timeline_extractor import PjeTimelineExtractor, CHAVE_CONTESTACAO
            from services.ai_client import extract_data_with_gemini
            _txt = timeline_result["textos"]["contestacao"]
            _meta = PjeTimelineExtractor.extrair_metadados_peca(CHAVE_CONTESTACAO, _txt, extract_data_with_gemini)
            _d = _meta.get("dados") or {}
            relatorio["contestacao"] = {
                "teses_defesa":        _d.get("teses_defesa") or [],
                "numero_processo":     _d.get("numero_processo"),
                "reclamante":          _d.get("reclamante"),
                "reclamada":           _d.get("reclamada"),
                "valor_causa":         _d.get("valor_causa"),
                "argumentos_exclusao": _d.get("argumentos_exclusao") or [],
                "teses_empresa":       _d.get("teses_de_merito") or _d.get("teses_empresa") or [],
                "verbas_negadas":      _d.get("verbas_negadas") or [],
                "sumulas_citadas":     _d.get("sumulas_citadas") or [],
                "model_used":          _meta.get("model_used"),
                "erro":                _meta.get("erro"),
            }
            pecas_extraidas_do_pdf["contestacao"] = True
        except Exception as _e:
            _logger.warning(
                "timeline_contestacao_metadados_failed",
                extra={"error": str(_e), "tenant_id": current_tenant_id() or "anonimo"},
            )

    # Guardrail: remove falsos positivos de "verba ausente" (canonização vs verbas da empresa)
    _filtrar_falsos_positivos_verba_ausente(relatorio)

    # Guardrail: remove aprendizados de verba_ausente falsa antes de retornar ao frontend
    _filtrar_aprendizados_verba_ausente_falsas(relatorio)

    # Metadados de origem dos arquivos
    relatorio["arquivos_analisados"] = {
        "processo":    processo_filename,
        "liquidacao":  liquidacao_filename,
        "parecer":     parecer_filename,
        "impugnacao":  impugnacao_filename or None,
        "calculo_pjc": calculo_pjc_filename or None,
        "peticao":     peticao_filename or None,
        "contestacao": contestacao_filename or None,
    }

    # Memorial de Análise da IA (modo Lab):
    # Constrói um "resultado_engine" sintético a partir das discrepâncias para
    # alimentar o ExplanationEngine e gerar um memorial textual consolidado.
    try:
        from services.explanation_engine import ExplanationEngine

        # Dados mínimos para os templates de explicação
        dados_templates = {
            "numero_processo": relatorio.get("numero_processo"),
            "reclamada": (relatorio.get("sentenca") or {}).get("campos_chave", {}).get(
                "reclamada"
            ),
            "verbas_deferidas": (relatorio.get("sentenca") or {}).get("verbas") or [],
            "indice_correcao": (relatorio.get("liquidacao") or {}).get("indice_correcao"),
            "juros_mora": (relatorio.get("liquidacao") or {}).get("juros_mora"),
        }

        memorial_entries = []
        for disc in relatorio.get("discrepancias") or []:
            fundamento = disc.get("fundamento") or ""
            nivel = disc.get("nivel") or "AVISO"
            memorial_entries.append(
                {
                    "id": disc.get("tipo") or "LAB_DISC",
                    "titulo": f"Discrepância: {disc.get('tipo') or 'Anomalia'}",
                    "descricao": disc.get("juliana_corrigiu")
                    or disc.get("juiz_disse")
                    or "",
                    "base_legal": fundamento,
                    "prioridade": 40 if nivel == "ERRO" else 60,
                }
            )

        if memorial_entries:
            resultado_engine = {"memorial_juridico": memorial_entries}
            explicacoes = ExplanationEngine.gerar(resultado_engine, dados_templates)
            bloco_texto = "\n\n".join(e.get("explicacao", "") for e in explicacoes)
            if bloco_texto.strip():
                relatorio["memorial_juridico"] = bloco_texto
    except Exception as _e_exp:
        _logger.warning(
            "learning_memorial_analise_ia_failed",
            extra={"error": str(_e_exp), "tenant_id": current_tenant_id() or "anonimo"},
        )

    _logger.info(
        "learning_analise_discrepancias_concluida",
        extra={
            "discrepancias": len(relatorio.get("discrepancias") or []),
            "tenant_id": current_tenant_id() or "anonimo",
        },
    )
    return relatorio


# Mantém compatibilidade com versão anterior (3 arquivos)
def processar_trio_arquivos(
    sentenca_bytes: bytes,
    liquidacao_bytes: bytes,
    liquidacao_filename: str,
    manifestacao_bytes: bytes,
) -> Dict[str, Any]:
    return processar_cinco_arquivos(
        processo_bytes=sentenca_bytes,
        processo_filename="sentenca.pdf",
        liquidacao_bytes=liquidacao_bytes,
        liquidacao_filename=liquidacao_filename,
        parecer_bytes=manifestacao_bytes,
        parecer_filename="manifestacao.docx",
    )


__all__ = [
    "processar_sete_arquivos",
    "processar_cinco_arquivos",
    "processar_trio_arquivos",
    "preview_aprendizado",
    "salvar_aprendizado",
    "codify_insight",
    "processar_aprendizado_autonomo",
    "_LEARNING_LOG",
]

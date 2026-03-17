from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import Response
from typing import List, Optional
from pathlib import Path
import json
import logging

from services.request_context import get_request_context
from services.database import get_extraction_repo, registrar_uso_lab, quota_excedida

router = APIRouter(prefix="/lab", tags=["Laboratório"])
_logger = logging.getLogger("smart_extractor")


def _ext_ok(filename: str, allowed: list[str]) -> bool:
    return any((filename or "").lower().endswith(e) for e in allowed)


_DOCS_EXTS = [".pdf", ".doc", ".docx"]
_PJC_EXTS = [".pdf", ".doc", ".docx", ".pjc", ".xml"]


@router.post("/analisar")
async def lab_analisar(
    processo:         List[UploadFile] = File(default=[]),
    liquidacao:       UploadFile = File(None),
    parecer:          UploadFile = File(None),
    impugnacao:       UploadFile = File(None),
    calculo_pjc:      UploadFile = File(None),
    amostragem_pdf:   UploadFile = File(None),
    amostragem_word:  UploadFile = File(None),
    amostragens:      List[UploadFile] = File(default=[]),
    manifestacao:     UploadFile = File(None),
    peticao:          UploadFile = File(None),
    contestacao:      UploadFile = File(None),
    user_id:          str        = Form("anonimo"),
):
    """
    Recebe até 8 arquivos (todos opcionais) e retorna o Relatório de Discrepância
    com Linha do Tempo quando houver dados suficientes.

    Nenhum campo é estritamente obrigatório do ponto de vista da API.
    Combinações recomendadas:
      - Comparar sentença × cálculo: processo + liquidacao + parecer
      - Tríade da Liquidação: amostragem_pdf + processo + calculo_pjc
      - Tríade de Ouro Expandida: amostragem_pdf + processo + calculo_pjc + manifestacao

    Opcionais (enriquecimento e aprendizado):
      - amostragem_pdf:  PDF           — relatório de prova (holerites/cartões de ponto)
      - amostragem_word: DOC/DOCX      — petição Word → style transfer (amostragem_style.md)
      - processo:        PDF/DOC/DOCX  — sentença ou decisão judicial
      - liquidacao:      PDF/DOC/DOCX  — cálculo da parte adversa (onde errou)
      - parecer:         PDF/DOC/DOCX  — parecer/manifestação da perita (correção)
      - impugnacao:      PDF/DOC/DOCX  — impugnação da parte contrária
      - calculo_pjc:     PDF/.PJC/.XML — planilha PJe-Calc para auditoria de parâmetros
      - manifestacao:    PDF/DOC/DOCX  — petição de resposta / manifestação pericial
                                         → extrai retórica de combate, padrões Ataque/Defesa,
                                           súmulas estratégicas → salva em skills/manifestacao_style.md

    Use /lab/salvar para persistir regras e aprendizados no sistema.
    """
    # Sprint 1/2: contexto de tenant/usuário vem do header (x-user-id); user_id do form é legado.
    ctx = get_request_context()
    effective_user_id = ctx.user_id or (user_id or "anonimo")
    _PDF_ONLY = [".pdf"]
    _WORD_ONLY = [".doc", ".docx"]

    # Sprint 5: validação de quota de análises do Lab por plano
    if quota_excedida(effective_user_id, "lab_analises"):
        _logger.warning(
            "quota_lab_excedida",
            extra={"tenant_id": effective_user_id},
        )
        raise HTTPException(
            status_code=429,
            detail="Limite de análises do Laboratório atingido para o plano atual.",
        )

    # Validações de formato — todos opcionais
    for _pf in (processo or []):
        if _pf and _pf.filename and not _ext_ok(_pf.filename, _DOCS_EXTS):
            raise HTTPException(400, f"Campo 'processo' aceita PDF, DOC ou DOCX (arquivo: {_pf.filename})")
    if parecer and parecer.filename and not _ext_ok(parecer.filename, _DOCS_EXTS):
        raise HTTPException(400, "Campo 'parecer' aceita PDF, DOC ou DOCX")
    if liquidacao and liquidacao.filename and not _ext_ok(liquidacao.filename, _DOCS_EXTS):
        raise HTTPException(400, "Campo 'liquidacao' aceita PDF, DOC ou DOCX")
    if impugnacao and impugnacao.filename and not _ext_ok(impugnacao.filename, _DOCS_EXTS):
        raise HTTPException(400, "Campo 'impugnacao' aceita PDF, DOC ou DOCX")
    if calculo_pjc and calculo_pjc.filename and not _ext_ok(calculo_pjc.filename, _PJC_EXTS):
        raise HTTPException(400, "Campo 'calculo_pjc' aceita PDF, DOC, DOCX ou .PJC")
    if amostragem_pdf and amostragem_pdf.filename and not _ext_ok(amostragem_pdf.filename, _PDF_ONLY):
        raise HTTPException(400, "Campo 'amostragem_pdf' aceita apenas PDF")
    if amostragem_word and amostragem_word.filename and not _ext_ok(amostragem_word.filename, _WORD_ONLY):
        raise HTTPException(400, "Campo 'amostragem_word' aceita DOC ou DOCX")
    if manifestacao and manifestacao.filename and not _ext_ok(manifestacao.filename, _DOCS_EXTS):
        raise HTTPException(400, "Campo 'manifestacao' aceita PDF, DOC ou DOCX")
    for _af in (amostragens or []):
        if _af and _af.filename and not _ext_ok(_af.filename, _DOCS_EXTS):
            raise HTTPException(400, f"Campo 'amostragens' aceita PDF, DOC ou DOCX (arquivo: {_af.filename})")
    if peticao and peticao.filename and not _ext_ok(peticao.filename, _DOCS_EXTS):
        raise HTTPException(400, "Campo 'peticao' aceita PDF ou DOCX")
    if contestacao and contestacao.filename and not _ext_ok(contestacao.filename, _DOCS_EXTS):
        raise HTTPException(400, "Campo 'contestacao' aceita PDF ou DOCX")

    # Leitura dos bytes (cada campo é opcional — só lê se enviado com filename)
    # Card 3: lista de documentos decisórios (sentença + acórdãos TRT/TST)
    processo_arquivos = []
    for _pf in (processo or []):
        if _pf and _pf.filename:
            _pb = await _pf.read()
            if _pb:
                processo_arquivos.append((_pb, _pf.filename))
    # Compatibilidade retroativa: expõe o primeiro arquivo como processo_bytes
    processo_bytes    = processo_arquivos[0][0]        if processo_arquivos else None
    processo_filename_first = processo_arquivos[0][1]  if processo_arquivos else ""
    liquidacao_bytes      = await liquidacao.read()  if (liquidacao  and liquidacao.filename)  else None
    parecer_bytes         = await parecer.read()     if (parecer     and parecer.filename)     else None
    impugnacao_bytes      = await impugnacao.read()      if (impugnacao      and impugnacao.filename)      else None
    calculo_pjc_bytes     = await calculo_pjc.read()     if (calculo_pjc     and calculo_pjc.filename)     else None
    amostragem_pdf_bytes  = await amostragem_pdf.read()  if (amostragem_pdf  and amostragem_pdf.filename)  else None
    amostragem_word_bytes = await amostragem_word.read() if (amostragem_word and amostragem_word.filename) else None
    manifestacao_bytes    = await manifestacao.read()    if (manifestacao    and manifestacao.filename)    else None
    manifestacao_filename = (manifestacao.filename or "") if manifestacao else ""
    peticao_bytes         = await peticao.read()         if (peticao        and peticao.filename)        else None
    peticao_filename      = (peticao.filename or "")     if peticao else ""
    contestacao_bytes     = await contestacao.read()     if (contestacao    and contestacao.filename)    else None
    contestacao_filename  = (contestacao.filename or "") if contestacao else ""

    amostragens_arquivos = []
    for _af in (amostragens or []):
        if _af and _af.filename:
            _ab = await _af.read()
            if _ab:
                amostragens_arquivos.append((_ab, _af.filename))
    if amostragens_arquivos:
        # Logging estruturado já cobre o request; manter apenas contagem em memória se necessário.
        pass

    n_proc = len(processo_arquivos)
    n_rest = sum(1 for (b, _) in [
        (liquidacao_bytes, liquidacao), (parecer_bytes, parecer), (impugnacao_bytes, impugnacao),
        (calculo_pjc_bytes, calculo_pjc), (amostragem_pdf_bytes, amostragem_pdf),
        (amostragem_word_bytes, amostragem_word), (manifestacao_bytes, manifestacao),
        (peticao_bytes, peticao), (contestacao_bytes, contestacao),
    ] if b)

    from services.learning_engine import processar_sete_arquivos
    try:
        relatorio = processar_sete_arquivos(
            processo_bytes=processo_bytes,
            processo_filename=processo_filename_first,
            processo_arquivos=processo_arquivos,
            liquidacao_bytes=liquidacao_bytes,
            liquidacao_filename=(liquidacao.filename or "") if liquidacao else "",
            parecer_bytes=parecer_bytes,
            parecer_filename=(parecer.filename or "") if parecer else "",
            impugnacao_bytes=impugnacao_bytes,
            impugnacao_filename=(impugnacao.filename or "") if impugnacao else "",
            calculo_pjc_bytes=calculo_pjc_bytes,
            calculo_pjc_filename=(calculo_pjc.filename or "") if calculo_pjc else "",
            amostragem_pdf_bytes=amostragem_pdf_bytes,
            amostragem_pdf_filename=(amostragem_pdf.filename or "") if amostragem_pdf else "",
            amostragem_word_bytes=amostragem_word_bytes,
            amostragem_word_filename=(amostragem_word.filename or "") if amostragem_word else "",
            amostragens_arquivos=amostragens_arquivos,
            manifestacao_bytes=manifestacao_bytes,
            manifestacao_filename=manifestacao_filename,
            peticao_bytes=peticao_bytes,
            peticao_filename=peticao_filename,
            contestacao_bytes=contestacao_bytes,
            contestacao_filename=contestacao_filename,
        )

        # Registra na tabela extracoes para contagem de processos únicos.
        # Só salva se houver número de processo identificado (evita poluir com
        # análises de arquivos sem processo identificável).
        numero = relatorio.get("numero_processo") or ""
        if numero and numero.lower() not in ("desconhecido", ""):
            # Sprint 2: Repository Pattern — usa repositório com tenant_id == effective_user_id
            extraction_repo = get_extraction_repo(tenant_id=effective_user_id or "anonimo")
            extraction_repo.save_extraction(
                user_id=effective_user_id or "anonimo",
                data={"numero_processo": numero, "origem": "lab", **relatorio},
                doc_type="lab_analise",
                model_used=relatorio.get("model_used"),
            )
            # Sprint 4: registra uso do Lab para billing/usage por tenant
            try:
                registrar_uso_lab(effective_user_id or "anonimo")
            except Exception as e:
                _logger.warning(
                    "lab_registrar_uso_error",
                    extra={"user_id": effective_user_id or "anonimo", "error": str(e)},
                )

        return relatorio
    except Exception as e:
        raise HTTPException(500, f"Erro na análise: {str(e)}")


@router.post("/preview")
async def lab_preview(body: dict):
    """
    Retorna o conteúdo que seria gravado para cada aprendizado selecionado,
    sem gravar nada em disco.

    Body JSON:
    {
      "aprendizados": [ { "tipo": "regra"|"playbook", "titulo": "...", ... }, ... ]
    }

    Retorna:
    {
      "previews": [
        { "tipo": "regra", "destino": "services/.../lab_xxx.py",
          "nome_arquivo": "lab_xxx.py", "conteudo": "...", "linguagem": "python" },
        ...
      ]
    }
    """
    aprendizados = body.get("aprendizados")
    if not aprendizados or not isinstance(aprendizados, list):
        raise HTTPException(400, "Campo 'aprendizados' é obrigatório e deve ser uma lista")

    from services.learning_engine import preview_aprendizado

    try:
        previews = [preview_aprendizado(ap) for ap in aprendizados]
        return {"previews": previews}
    except Exception as e:
        print(f"[LAB] Erro ao gerar preview: {e}", flush=True)
        raise HTTPException(500, f"Erro ao gerar pré-visualização: {str(e)}")


@router.post("/salvar")
async def lab_salvar(body: dict):
    """
    Consolida um aprendizado aprovado pelo usuário em duas camadas:

    CAMADA 1 — Histórico (Log):
      Grava em learning_log.jsonl:
      { data, processo_id, discrepancia, correcao_aplicada, base_legal, caminhos_gerados, model_used_* }

    CAMADA 2 — Lógica (Código/Skills):
      Invoca learning_engine.codify_insight() que usa Gemini para:
        - tipo "regra":    gera arquivo Python LegalRule em legal_engine/rules/
                           + injeta exemplo de Engenharia Reversa em skills/sentenca_ordinaria.md
        - tipo "playbook": injeta bloco Markdown enriquecido em skills/sentenca_ordinaria.md

    Body JSON:
    {
      "aprendizado":      { "tipo": "regra"|"playbook", "titulo": "...", "descricao": "...",
                            "correcao": "...", "base_legal": "..." },
      "numero_processo":  "0001234-...",
      "conteudo_editado": "..."   (opcional — conteúdo revisado pelo usuário no preview)
    }

    Se conteudo_editado for fornecido, o sistema respeita a edição do usuário e
    ainda assim usa Gemini para enriquecer o skill com Engenharia Reversa.
    """
    aprendizado = body.get("aprendizado")
    if not aprendizado or not isinstance(aprendizado, dict):
        raise HTTPException(400, "Corpo inválido: 'aprendizado' é obrigatório")

    numero_processo  = body.get("numero_processo") or ""
    conteudo_editado = body.get("conteudo_editado") or None

    from services.learning_engine import codify_insight

    try:
        resultado = codify_insight(aprendizado, numero_processo, conteudo_editado)
        return resultado
    except Exception as e:
        print(f"[LAB] Erro ao consolidar aprendizado: {e}", flush=True)
        raise HTTPException(500, f"Erro ao salvar: {str(e)}")


@router.post("/gerar-docx")
async def lab_gerar_docx(body: dict):
    """
    Ghostwriter: gera documento Word (.docx) com minuta da Manifestação aos Cálculos.

    Body: relatório do Laboratório (mesmo JSON retornado por POST /lab/analisar),
    contendo numero_processo, sentenca.campos_chave, discrepancias, etc.

    Retorna o arquivo .docx para download. Usa skills/manifestacao_style.md como
    estilo de redação e ai_writer + document_generator para o conteúdo.
    """
    if not body or not isinstance(body, dict):
        raise HTTPException(400, "Corpo inválido: envie o relatório JSON do Laboratório (ex.: resultado de /lab/analisar).")
    skills_dir = Path(__file__).resolve().parent / "skills"
    style_path = skills_dir / "manifestacao_style.md"
    estilo_mapeado = ""
    if style_path.exists():
        try:
            estilo_mapeado = style_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[LAB] Aviso: não foi possível ler {style_path}: {e}", flush=True)

    from services.document_generator import gerar_minuta
    try:
        docx_bytes = gerar_minuta(body, estilo_mapeado)
    except Exception as e:
        print(f"[LAB] Erro ao gerar minuta DOCX: {e}", flush=True)
        raise HTTPException(500, f"Erro ao gerar documento: {str(e)}")

    numero = (body.get("numero_processo") or "minuta").replace("/", "-").replace("\\", "-")[:80]
    filename = f"Manifestacao_{numero}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/historico")
def lab_historico(limit: int = 50):
    """Retorna os últimos aprendizados salvos (lê learning_log.jsonl)."""
    import os
    from services.learning_engine import _LEARNING_LOG

    if not os.path.exists(_LEARNING_LOG):
        return {"aprendizados": [], "total": 0}

    linhas = []
    try:
        with open(_LEARNING_LOG, "r", encoding="utf-8") as f:
            linhas = [json.loads(l) for l in f if l.strip()]
    except Exception as e:
        raise HTTPException(500, f"Erro ao ler histórico: {e}")

    linhas.reverse()
    return {"aprendizados": linhas[:limit], "total": len(linhas)}


@router.get("/knowledge-base")
def lab_knowledge_base(status: str = "all"):
    """
    Inspeciona o Knowledge Base do Self-Healing Rule Engine.

    Query param `status`:
      all     — todas as regras (exceto deletadas)
      active  — apenas regras ativas (confidence_score >= 3)
      shadow  — apenas regras em observação silenciosa
      deleted — apenas regras descartadas por punição (histórico)
    """
    from services.knowledge_base import KnowledgeBase
    from services.request_context import current_tenant_id

    kb = KnowledgeBase(tenant_id=current_tenant_id())

    if status == "active":
        rules = kb.get_regras_ativas()
    elif status == "shadow":
        rules = kb.get_regras_shadow()
    elif status == "deleted":
        rules = [r for r in kb._data.get("rules", []) if r.get("status") == "deleted"]
    else:
        rules = kb._data.get("rules", [])

    return {
        "stats":  kb.stats(),
        "rules":  rules,
        "total":  len(rules),
        "filter": status,
    }


@router.delete("/knowledge-base/{rule_id}")
def lab_kb_delete_rule(rule_id: str):
    """
    Força a exclusão manual de uma regra do Knowledge Base.
    Útil para remover falsos positivos identificados pelo perito.
    """
    from services.knowledge_base import KnowledgeBase
    from services.request_context import current_tenant_id

    kb = KnowledgeBase(tenant_id=current_tenant_id())
    regra = kb.get_por_id(rule_id)
    if not regra:
        raise HTTPException(404, f"Regra '{rule_id}' não encontrada")

    resultado = kb.decrementar(rule_id)  # força score abaixo do threshold
    # Se ainda não foi deletada, força diretamente
    kb._recarregar()
    for r in kb._data.get("rules", []):
        if r.get("rule_id") == rule_id:
            r["status"] = "deleted"
            r["confidence_score"] = -99
            break
    kb._salvar()

    return {"mensagem": f"Regra '{rule_id}' excluída manualmente", "rule_id": rule_id}


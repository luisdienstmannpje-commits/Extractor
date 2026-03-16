"""
main.py — API FastAPI — PjeCalc Smart Extractor v3.2

v3.2 (patch pjc_exporter v5.3):
  - media_type: "application/zip" → "application/xml" (correção definitiva)
  - .pjc é XML puro ISO-8859-1 — confirmado via análise de arquivo real 2.13.0
  - X-PJC-Version: "5.3" → "5.4"

v3.1 — WebSocket push (substituição do polling):
  - Novo endpoint GET /ws/{job_id} — WebSocket por job
  - _set_job() notifica conexões WS ativas ao finalizar
  - Fallback HTTP /status/{job_id} mantido para compatibilidade e restart recovery
  - _ws_connections: dict job_id → asyncio.Queue (thread-safe via run_coroutine_threadsafe)
  - Frontend conecta WS após upload; polling só ativa se WS falhar (graceful degradation)

v2.2 — base:
  - Jobs persistidos no SQLite, timeout 5min, threading.Lock
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from typing import List
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from workers.processor import process_lawsuit_pdf, process_lawsuit_dossie
from services.database import (
    save_job_status,
    get_job_status,
    get_user_credits,
    get_user_history,
    cleanup_old_jobs,
    get_total_extractions,
    clear_extracoes,
)

from services.pjc_exporter import exportar_pjc, gerar_nome_arquivo
from services.excel_exporter import exportar_excel
from services.pjc_parser import PjcParser
from services.pjc_auditor import auditar_pjc_vs_sentenca
from config import settings
import os
import uvicorn
import uuid
import threading
import asyncio
import json
from pathlib import Path


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup e shutdown (substitui on_event deprecado)."""
    # Startup
    cleanup_old_jobs(days=7)
    _port = os.environ.get("PORT", "8000")
    print("[MAIN] API v3.2 iniciada. WebSocket push ativo. pjc_exporter v5.4 (XML puro + gprec fix).", flush=True)
    print(f"[MAIN] Abra o sistema na MESMA PORTA que o Uvicorn mostra abaixo (ex.: se aparecer 'running on ...8001', use http://localhost:8001/)", flush=True)
    yield
    # Shutdown (opcional)


app = FastAPI(
    title="PjeCalc Smart Extractor API",
    version="3.2",
    description="Extração automática de verbas trabalhistas de sentenças e acórdãos PJe",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log em arquivo para ver atividade quando o terminal nao mostra (subprocess com --reload no Windows)
_LOG_FILE = Path(__file__).resolve().parent / "server.log"
def _log(msg: str):
    print(msg, flush=True)
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(datetime.now().strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


async def _log_request(request, call_next):
    """Registra cada requisição (terminal + server.log)."""
    method = request.method
    path = request.url.path
    _log(f"[HTTP] {method} {path}")
    return await call_next(request)


app.middleware("http")(_log_request)

# ── Cache em memória ──────────────────────────────────────────────────────────
_jobs_mem:  dict = {}
_jobs_lock  = threading.Lock()

# ── WebSocket: job_id → asyncio.Queue ────────────────────────────────────────
# Cada conexão WS tem sua própria Queue. _set_job() coloca o resultado na fila
# quando o job termina — o endpoint /ws/{job_id} consome e envia ao browser.
_ws_queues: dict = {}
_ws_lock    = threading.Lock()

JOB_TIMEOUT_SECONDS = 300  # 5 minutos


# ── Helpers de job ────────────────────────────────────────────────────────────

def _set_job(job_id: str, user_id: str, data: dict):
    """
    Salva job em memória + SQLite.
    Se job finalizado (done/error/timeout), notifica WebSocket aguardando.
    """
    status = data.get("status", "queued")
    result = data if status not in ("queued", "processing") else None

    with _jobs_lock:
        _jobs_mem[job_id] = data

    save_job_status(job_id, user_id, status, result)

    # Notificar WebSocket se job terminou
    if status not in ("queued", "processing"):
        _notify_ws(job_id, data)


def _notify_ws(job_id: str, data: dict):
    """
    Coloca o resultado na fila do WebSocket deste job (thread-safe).
    Usa run_coroutine_threadsafe porque _set_job é chamado de thread worker,
    não do event loop do asyncio.
    """
    with _ws_lock:
        queue = _ws_queues.get(job_id)

    if queue is None:
        return  # Nenhum WS conectado para este job — sem ação

    try:
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(queue.put_nowait, data)
    except Exception as e:
        print(f"[WS] Falha ao notificar job {job_id}: {e}", flush=True)


def _get_job(job_id: str) -> dict | None:
    """Lê da memória (rápido). Fallback para SQLite (após restart)."""
    with _jobs_lock:
        if job_id in _jobs_mem:
            return _jobs_mem[job_id]
    row = get_job_status(job_id)
    if not row:
        return None
    if row["status"] in ("done", "error", "timeout") and row.get("result"):
        return row["result"]
    return {"status": row["status"]}


# ── Job runner com timeout ────────────────────────────────────────────────────

def _run_job_with_timeout(job_id: str, user_id: str, file_bytes: bytes = None, files_list: list = None):
    result_container = {}
    done_event = threading.Event()

    def _worker():
        try:
            if files_list and len(files_list) > 0:
                result = process_lawsuit_dossie(user_id, files_list, job_id=job_id)
            else:
                result = process_lawsuit_pdf(user_id, file_bytes, job_id=job_id)
        except Exception as e:
            result = {"status": "erro", "msg": f"Exceção não tratada: {str(e)}"}
        result_container["result"] = result
        done_event.set()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    finished = done_event.wait(timeout=JOB_TIMEOUT_SECONDS)

    if finished:
        final = result_container.get("result", {"status": "erro", "msg": "Resultado vazio"})
    else:
        final = {
            "status": "erro",
            "msg": f"Timeout: processamento excedeu {JOB_TIMEOUT_SECONDS // 60} minutos.",
        }
        print(f"[MAIN] AVISO: Job {job_id} expirou por timeout ({JOB_TIMEOUT_SECONDS}s)", flush=True)

    # Normaliza status: "sucesso"→"done", "erro"→"error"
    _STATUS_MAP = {"sucesso": "done", "erro": "error"}
    if final.get("status") in _STATUS_MAP:
        final["status"] = _STATUS_MAP[final["status"]]

    _set_job(job_id, user_id, final)  # ← notifica WS aqui


def _start_job(job_id: str, user_id: str, file_bytes: bytes = None, files_list: list = None):
    _set_job(job_id, user_id, {"status": "processing"})
    controller = threading.Thread(
        target=_run_job_with_timeout,
        args=(job_id, user_id),
        kwargs={"file_bytes": file_bytes, "files_list": files_list},
        daemon=True
    )
    controller.start()


# ── Endpoints HTTP ────────────────────────────────────────────────────────────

@app.get("/api/status")
def api_status():
    """Status da API (abrir o sistema em / para o frontend)."""
    return {"status": "online", "version": "3.2", "docs": "/docs"}


_EXT_UPLOAD = (".pdf", ".doc", ".docx", ".pjc", ".xml", ".xlsx", ".xls", ".jpg", ".jpeg", ".png")


@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    user_id: str = Form(...),
    files: List[UploadFile] = File(..., alias="files"),
):
    """
    Recebe um ou mais arquivos (dossiê): PDF, DOC, DOCX, PJC, XML.
    Um único PDF: fluxo clássico (sentence_finder + IA).
    Múltiplos arquivos ou não-PDF: extração de texto por arquivo, concatenação e IA sobre o super-contexto.
    """
    print(f"[UPLOAD] Arquivos recebidos: {[f.filename for f in files]}", flush=True)
    if not files or len(files) == 0:
        raise HTTPException(400, "Envie pelo menos um arquivo (PDF, Word, Excel, PJC, XML ou imagens).")

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    collected: list = []
    for f in files:
        fn = (f.filename or "").strip().lower()
        if not any(fn.endswith(ext) for ext in _EXT_UPLOAD):
            raise HTTPException(400, f"Tipo não aceito: {f.filename}. Use: PDF, DOC, DOCX, PJC, XML, XLSX, XLS, JPG, PNG.")
        content = await f.read()
        if len(content) > max_bytes:
            raise HTTPException(400, f"Arquivo {f.filename} excede {settings.MAX_FILE_SIZE_MB}MB.")
        if len(content) < 10:
            raise HTTPException(400, f"Arquivo {f.filename} está vazio ou inválido.")
        collected.append((f.filename or "arquivo", content))

    job_id = str(uuid.uuid4())
    _set_job(job_id, user_id, {"status": "queued"})

    if len(collected) == 1 and collected[0][0].lower().endswith(".pdf"):
        background_tasks.add_task(_start_job, job_id, user_id, file_bytes=collected[0][1], files_list=None)
    else:
        background_tasks.add_task(_start_job, job_id, user_id, file_bytes=None, files_list=collected)

    return {
        "job_id": job_id,
        "status": "queued",
        "timeout_seconds": JOB_TIMEOUT_SECONDS,
        "ws_url": f"/ws/{job_id}",
    }


@app.post("/upload-pjc/{job_id}")
async def upload_pjc_for_audit(
    job_id: str,
    file: UploadFile = File(...),
):
    """
    Recebe um arquivo .PJC (XML do PJe-Calc) para auditoria cruzada com a sentença.

    Pré-condição: o job do PDF correspondente já deve ter sido processado com sucesso.
    A auditoria não altera o cálculo; apenas gera uma lista de divergências textuais
    que pode ser exibida no frontend e incluída no Excel.
    """
    filename = (file.filename or "").lower()
    if not (filename.endswith(".pjc") or filename.endswith(".xml")):
        raise HTTPException(400, "Apenas arquivos .pjc ou .xml são aceitos para auditoria.")

    job = _get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' não encontrado")

    status = job.get("status")
    if status in ("queued", "processing"):
        raise HTTPException(202, f"Job ainda em processamento (status: {status})")
    if status in ("error", "erro"):
        raise HTTPException(400, "Job terminou com erro — não é possível auditar o .PJC.")

    dados_job = job.get("result") or job
    if not isinstance(dados_job, dict):
        raise HTTPException(400, "Resultado inválido para auditoria do .PJC.")

    # Dados estruturados da sentença/IA
    dados_ia = dados_job.get("data") or dados_job
    if not isinstance(dados_ia, dict):
        raise HTTPException(400, "Estrutura de dados da sentença inesperada para auditoria do .PJC.")

    xml_bytes = await file.read()
    try:
        parser = PjcParser.from_string(xml_bytes)
        dados_pjc = parser.extrair_dados_basicos()
    except Exception as e:
        print(f"[PJC_AUDITOR] Erro ao parsear arquivo .pjc para job {job_id}: {e}", flush=True)
        raise HTTPException(400, f"Arquivo .PJC inválido ou não suportado: {type(e).__name__}")

    divergencias = auditar_pjc_vs_sentenca(dados_ia=dados_ia, dados_pjc=dados_pjc)

    # Armazena divergências em memória para este job, para consumo posterior (Excel, frontend)
    with _jobs_lock:
        base = _jobs_mem.get(job_id) or job
        if isinstance(base, dict):
            if isinstance(base.get("result"), dict):
                base["result"]["pjc_auditoria_divergencias"] = divergencias
            else:
                base["pjc_auditoria_divergencias"] = divergencias
            _jobs_mem[job_id] = base

    return {
        "job_id": job_id,
        "filename": file.filename,
        "divergencias": divergencias,
    }


@app.get("/status/{job_id}")
def get_status(job_id: str):
    """
    Fallback HTTP para polling.
    Usado quando WebSocket não está disponível ou após restart.
    """
    job = _get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' não encontrado")
    return job


@app.get("/credits/{user_id}")
def get_credits_endpoint(user_id: str):
    return {"user_id": user_id, "credits": get_user_credits(user_id)}


@app.get("/historico/{user_id}")
def get_historico(user_id: str, limit: int = 20):
    if limit > 100:
        limit = 100
    return {"user_id": user_id, "extractions": get_user_history(user_id, limit=limit)}


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    with _jobs_lock:
        removed = _jobs_mem.pop(job_id, None)
    return {"deleted": removed is not None, "job_id": job_id}


@app.get("/export-excel/{job_id}")
def export_excel_endpoint(job_id: str):
    """
    Gera e retorna o arquivo .xlsx estruturado para o job informado.

    Retorna FileResponse com Content-Disposition: attachment.
    O arquivo é gerado sob demanda — não é cacheado em disco permanentemente.

    Status possíveis:
      200 — arquivo .xlsx gerado e retornado
      202 — job ainda em processamento
      404 — job não encontrado
      400 — job terminou com erro
      500 — falha na geração do Excel
    """
    from fastapi.responses import FileResponse

    job = _get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' não encontrado"
        )

    status = job.get("status")

    if status in ("queued", "processing"):
        raise HTTPException(
            status_code=202,
            detail=f"Processamento em andamento (status: {status})"
        )

    if status in ("error", "erro"):
        raise HTTPException(
            status_code=400,
            detail="Job terminou com erro — não é possível exportar"
        )

    # Mesmo padrão do /export-pjc: resultado pode estar na raiz ou em "result"
    dados = job.get("result") or job

    if not dados or not isinstance(dados, dict):
        raise HTTPException(
            status_code=400,
            detail="Resultado vazio ou inválido — não é possível exportar"
        )

    dados_limpos = {k: v for k, v in dados.items() if k != "status"}

    try:
        caminho_xlsx = exportar_excel(dados_limpos, job_id)

        numero = (dados_limpos.get("numero_processo") or "processo") \
                     .replace("/", "-").replace(".", "")
        nome_download = f"extrator_{numero}.xlsx"

        return FileResponse(
            path=caminho_xlsx,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=nome_download,
            headers={
                "Content-Disposition": f'attachment; filename="{nome_download}"',
            }
        )

    except Exception as e:
        print(f"[EXCEL] Erro ao gerar .xlsx para job {job_id}: {e}", flush=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar Excel: {str(e)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# LABORATÓRIO DE APRENDIZADO DA PERITA
# ══════════════════════════════════════════════════════════════════════════════

def _ext_ok(filename: str, allowed: list[str]) -> bool:
    return any((filename or "").lower().endswith(e) for e in allowed)

_DOCS_EXTS = [".pdf", ".doc", ".docx"]
_PJC_EXTS  = [".pdf", ".doc", ".docx", ".pjc", ".xml"]


@app.post("/lab/analisar")
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
    print("[LAB] POST /lab/analisar recebida.", flush=True)
    _PDF_ONLY = [".pdf"]
    _WORD_ONLY = [".doc", ".docx"]

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
        print(f"[LEARNING] Processando {len(amostragens_arquivos)} arquivo(s) de amostragem...", flush=True)

    n_proc = len(processo_arquivos)
    n_rest = sum(1 for (b, _) in [
        (liquidacao_bytes, liquidacao), (parecer_bytes, parecer), (impugnacao_bytes, impugnacao),
        (calculo_pjc_bytes, calculo_pjc), (amostragem_pdf_bytes, amostragem_pdf),
        (amostragem_word_bytes, amostragem_word), (manifestacao_bytes, manifestacao),
        (peticao_bytes, peticao), (contestacao_bytes, contestacao),
    ] if b)
    print(f"[LAB] Arquivos recebidos: {n_proc} processo(s) + {n_rest} outro(s) + {len(amostragens_arquivos)} amostragem(ns). Iniciando análise...", flush=True)

    from services.learning_engine import processar_sete_arquivos
    from services.database import save_extraction

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
            save_extraction(
                user_id=user_id or "anonimo",
                data={"numero_processo": numero, "origem": "lab", **relatorio},
                doc_type="lab_analise",
                model_used=relatorio.get("model_used"),
            )
            print(f"[LAB] Processo '{numero}' registrado em extracoes (user={user_id}).", flush=True)

        disc = len(relatorio.get("discrepancias") or [])
        apr = len(relatorio.get("aprendizados") or [])
        print(f"[LAB] Análise concluída: {disc} discrepância(s), {apr} aprendizado(s), processo={relatorio.get('numero_processo', '?')}.", flush=True)
        return relatorio
    except Exception as e:
        import traceback
        print(f"[LAB] Erro na análise: {e}", flush=True)
        traceback.print_exc()
        raise HTTPException(500, f"Erro na análise: {str(e)}")


@app.post("/lab/preview")
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


@app.post("/lab/salvar")
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


@app.post("/lab/gerar-docx")
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


@app.get("/lab/historico")
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


@app.get("/lab/knowledge-base")
def lab_knowledge_base(status: str = "all"):
    """
    Inspeciona o Knowledge Base do Self-Healing Rule Engine.

    Query param `status`:
      all     — todas as regras (exceto deletadas)
      active  — apenas regras ativas (confidence >= 3)
      shadow  — apenas regras em observação silenciosa
      deleted — apenas regras descartadas por punição (histórico)
    """
    from services.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()

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


@app.delete("/lab/knowledge-base/{rule_id}")
def lab_kb_delete_rule(rule_id: str):
    """
    Força a exclusão manual de uma regra do Knowledge Base.
    Útil para remover falsos positivos identificados pelo perito.
    """
    from services.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
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


@app.get("/api/knowledge-base")
async def get_knowledge_base():
    """
    Retorna o conteúdo completo do knowledge_base.json para o painel de gestão
    (card Inteligência Pericial + modal Biblioteca de Regras).
    Rota obrigatória para o frontend; nunca retorna 404.
    """
    try:
        from services.knowledge_base import KnowledgeBase

        kb = KnowledgeBase()
        data = kb.get_all()
        if not isinstance(data.get("rules"), list):
            data = {"rules": [], "_meta": data.get("_meta", {"version": "1.0"})}
        rules = data.get("rules") or []
        # Regra de segurança SaaS: se vazio, envia regra de teste para validar conexão
        if not rules:
            data["rules"] = [
                {
                    "rule_id": "SISTEMA_OK",
                    "descricao": "Conexão estabelecida. Aguardando novos aprendizados...",
                    "condicao": {"tipo": "verba_ausente"},
                    "status": "active",
                    "confidence_score": 100,
                }
            ]
        print(f"DEBUG: Enviando {len(data['rules'])} regras para o front.", flush=True)
        return data
    except Exception as e:
        _log(f"[API] /api/knowledge-base erro: {e}")
        return {
            "rules": [
                {
                    "rule_id": "SISTEMA_OK",
                    "descricao": "Conexão estabelecida. Aguardando novos aprendizados...",
                    "condicao": {"tipo": "verba_ausente"},
                    "status": "active",
                    "confidence_score": 100,
                }
            ],
            "_meta": {"version": "1.0", "error": str(e)},
        }


@app.get("/api/stats")
def api_stats():
    """
    Dashboard de estatísticas para o frontend (view 'Estatísticas').

    Retorna:
      - processos_analisados: total de registros na tabela extracoes.
      - regras_oficiais_ativas: regras dinâmicas com status 'active' (confidence_score >= 3).
      - regras_em_teste_shadow: regras dinâmicas com status 'shadow'.
      - omissoes_detectadas: soma dos campos 'punicoes' das regras dinâmicas (proxy de omissões).
      - ultimas_regras: últimas 5 regras dinâmicas (ordenadas por updated_at/created_at).
      - top_verbas_divergencias: top verbas presentes nas condições de tipo 'verba_*'.
    """
    from services.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    stats_kb = kb.stats()
    rules_all = kb._data.get("rules", []) if hasattr(kb, "_data") else []

    # KPIs de regras dinâmicas
    regras_ativas = stats_kb.get("active", 0)
    regras_shadow = stats_kb.get("shadow", 0)

    # Omissões detectadas: soma das punições (regras que "erraram" predições)
    omissoes = 0
    total_acertos = 0
    total_punicoes = 0
    for r in rules_all:
        try:
            total_acertos  += int(r.get("acertos",  0) or 0)
            total_punicoes += int(r.get("punicoes", 0) or 0)
            omissoes       += int(r.get("punicoes", 0) or 0)
        except Exception:
            continue

    # Eficiência do motor: acertos / (acertos + punições), em percentual
    total_avaliados = total_acertos + total_punicoes
    eficiencia_motor = round((total_acertos / total_avaliados) * 100, 1) if total_avaliados > 0 else None

    # Últimas regras aprendidas (5 mais recentes)
    ultimas = sorted(
        rules_all,
        key=lambda r: (r.get("updated_at") or r.get("created_at") or ""),
        reverse=True,
    )[:5]

    ultimas_slim = [
        {
            "rule_id": r.get("rule_id"),
            "descricao": r.get("descricao"),
            "status": r.get("status"),
            "confidence_score": r.get("confidence_score", 0),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
        }
        for r in ultimas
    ]

    # Top verbas com divergências: condicao.tipo verba_ausente / verba_presente
    contagens: dict[str, int] = {}
    for r in rules_all:
        cond = r.get("condicao") or {}
        tipo = (cond.get("tipo") or "").lower()
        if tipo not in ("verba_ausente", "verba_presente"):
            continue
        verba = (cond.get("verba") or "").strip()
        if not verba:
            continue
        key = verba
        contagens[key] = contagens.get(key, 0) + 1

    total_refs = sum(contagens.values()) or 1
    top_verbas = sorted(
        [{"verba": k, "contagem": v, "percentual": (v / total_refs) * 100.0} for k, v in contagens.items()],
        key=lambda x: x["contagem"],
        reverse=True,
    )[:5]

    # Se não houver dados suficientes, retorna um mock seguro
    if not rules_all and not contagens:
        top_verbas = [
            {"verba": "Horas Extras", "contagem": 0, "percentual": 0.0},
            {"verba": "DSR", "contagem": 0, "percentual": 0.0},
            {"verba": "Aviso Prévio", "contagem": 0, "percentual": 0.0},
        ]

    return {
        "processos_analisados": get_total_extractions(),
        "regras_oficiais_ativas": regras_ativas,
        "regras_em_teste_shadow": regras_shadow,
        "omissoes_detectadas": omissoes,
        "eficiencia_motor": eficiencia_motor,   # float 0-100 ou null se sem dados
        "ultimas_regras": ultimas_slim,
        "top_verbas_divergencias": top_verbas,
    }


@app.delete("/api/admin/reset-contagem")
def reset_contagem():
    """
    Zera o histórico de extrações (tabela extracoes).

    Isso faz com que 'Processos Analisados' volte a 0 no Dashboard.
    Não apaga: créditos, cache de PDFs, jobs, Knowledge Base, learning_log.
    Use apenas para reiniciar os testes sem contaminar estatísticas.
    """
    deleted = clear_extracoes()
    return {"ok": True, "registros_removidos": deleted, "mensagem": f"{deleted} extração(ões) removida(s). Contador zerado."}


@app.get("/health")
def health():
    with _jobs_lock:
        active = sum(
            1 for j in _jobs_mem.values()
            if isinstance(j, dict) and j.get("status") in ("queued", "processing")
        )
    with _ws_lock:
        ws_active = len(_ws_queues)
    return {
        "status": "healthy",
        "active_jobs": active,
        "ws_connections": ws_active,
        "version": "3.2",
    }


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/{job_id}")
async def websocket_job(websocket: WebSocket, job_id: str):
    """
    WebSocket por job. O frontend conecta após receber job_id no upload.

    Fluxo:
      1. Aceita conexão
      2. Verifica se job já terminou (race condition: pipeline rápido)
      3. Se não terminou, aguarda na Queue até _set_job() notificar
      4. Envia resultado como JSON e fecha conexão
      5. Remove Queue do registro

    Heartbeat: envia {"status": "processing"} a cada 10s para manter conexão viva.
    """
    await websocket.accept()
    print(f"[WS] Conectado: {job_id}", flush=True)

    # Race condition: job pode ter terminado antes do WS conectar
    job = _get_job(job_id)
    if job and job.get("status") not in ("queued", "processing"):
        await websocket.send_text(json.dumps(job))
        await websocket.close()
        print(f"[WS] Job {job_id} ja estava pronto - enviado imediatamente", flush=True)
        return

    # Registrar Queue para este job
    queue: asyncio.Queue = asyncio.Queue()
    with _ws_lock:
        _ws_queues[job_id] = queue

    try:
        while True:
            try:
                # Aguarda resultado com heartbeat a cada 10s
                result = await asyncio.wait_for(queue.get(), timeout=10.0)
                await websocket.send_text(json.dumps(result))
                print(f"[WS] Resultado enviado: {job_id} -> status={result.get('status')}", flush=True)
                break  # job terminou — fecha conexão

            except asyncio.TimeoutError:
                # Heartbeat — mantém conexão viva no browser
                try:
                    await websocket.send_text(json.dumps({"status": "processing"}))
                except Exception:
                    break  # browser desconectou

    except WebSocketDisconnect:
        print(f"[WS] Cliente desconectou: {job_id}", flush=True)
    finally:
        # Limpar Queue do registro
        with _ws_lock:
            _ws_queues.pop(job_id, None)
        print(f"[WS] Encerrado: {job_id}", flush=True)


# Servir frontend em / — deve ficar por último para não sombrear rotas da API (/api/*)
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
    _port = os.environ.get("PORT", "8000")
    print(f"[MAIN] Frontend servido em http://localhost:{_port}/ -> {_FRONTEND_DIR}", flush=True)
else:
    print(f"[MAIN] AVISO: pasta frontend nao encontrada em {_FRONTEND_DIR}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"[MAIN] Usando porta {port} (altere com PORT=8001)", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
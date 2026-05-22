from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from typing import List, Tuple, Optional
from fastapi.responses import FileResponse
from workers.processor import process_lawsuit_pdf, process_lawsuit_dossie
from services.database import get_job_repo
from services.request_context import get_request_context, set_job_id
from services.pjc_parser import PjcParser
from services.pjc_auditor import auditar_pjc_vs_sentenca
from config import settings
import uuid
import threading
import asyncio
import json
import logging


router = APIRouter(tags=["Extrator Principal"])


# ── Cache em memória ──────────────────────────────────────────────────────────
_jobs_mem: dict = {}
_jobs_lock = threading.Lock()

# ── WebSocket: job_id → asyncio.Queue ────────────────────────────────────────
# Cada conexão WS tem sua própria Queue. _set_job() coloca o resultado na fila
# quando o job termina — o endpoint /ws/{job_id} consome e envia ao browser.
_ws_queues: dict = {}
_ws_lock = threading.Lock()
_logger = logging.getLogger("smart_extractor")

# Loop do Uvicorn (definido no lifespan de main.py). Evita get_event_loop() na thread
# do worker — em Windows isso falha e gera ws_enqueue_failed.
_uvicorn_loop: Optional[asyncio.AbstractEventLoop] = None

JOB_TIMEOUT_SECONDS = 300  # 5 minutos


def register_worker_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Chamado uma vez no startup do FastAPI com asyncio.get_running_loop()."""
    global _uvicorn_loop
    _uvicorn_loop = loop


def _should_run_process_lawsuit_pdf_upload(
    collected: List[Tuple[str, bytes]],
    cache_context: str,
) -> Tuple[bool, Optional[str]]:
    """
    Decide se o upload de um ficheiro deve usar `process_lawsuit_pdf` (job único)
    em vez de `process_lawsuit_dossie`.

    Retorno
    -------
    (True, None)   → `process_lawsuit_pdf` com cache_context / filename.
    (False, None)  → dossiê (vários ficheiros ou um único não-PDF com contexto auto).
    (False, "msg") → rejeitar pedido (HTTP 400).
    """
    ctx_norm = (cache_context or "auto").strip().lower()
    n = len(collected)
    if ctx_norm == "peticao_inicial" and n != 1:
        return (
            False,
            "Para petição inicial envie exatamente um arquivo PDF, DOC ou DOCX.",
        )
    if ctx_norm == "contestacao" and n != 1:
        return (
            False,
            "Para contestação envie exatamente um arquivo PDF, DOC ou DOCX.",
        )
    if n != 1:
        return False, None
    name0, _ = collected[0]
    fn0 = (name0 or "arquivo").lower()
    if ctx_norm == "peticao_inicial":
        if not (
            fn0.endswith(".pdf") or fn0.endswith(".doc") or fn0.endswith(".docx")
        ):
            return False, "Petição inicial: use PDF, DOC ou DOCX."
    if ctx_norm == "contestacao":
        if not (
            fn0.endswith(".pdf") or fn0.endswith(".doc") or fn0.endswith(".docx")
        ):
            return False, "Contestação: use PDF, DOC ou DOCX."
    if fn0.endswith(".pdf"):
        return True, None
    if ctx_norm in ("peticao_inicial", "contestacao"):
        return True, None
    return False, None


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

    job_repo = get_job_repo()
    job_repo.save_job_status(job_id, user_id, status, result)

    # Notificar WebSocket se job terminou
    if status not in ("queued", "processing"):
        _notify_ws(job_id, data)


def _enqueue_ws_message(job_id: str, data: dict) -> None:
    """
    Enfileira mensagem para o WebSocket deste job (thread-safe).
    Usado para resultado final e para eventos `partial_update` vindos do worker.
    """
    with _ws_lock:
        queue = _ws_queues.get(job_id)

    if queue is None:
        return

    loop = _uvicorn_loop
    if loop is None:
        _logger.warning(
            "ws_enqueue_failed",
            extra={
                "job_id": job_id,
                "error": "event loop não registrado (register_worker_event_loop no lifespan)",
            },
        )
        return
    if not loop.is_running():
        _logger.warning(
            "ws_enqueue_failed",
            extra={"job_id": job_id, "error": "event loop do servidor inativo"},
        )
        return

    try:
        loop.call_soon_threadsafe(queue.put_nowait, data)
    except Exception as e:
        _logger.warning(
            "ws_enqueue_failed",
            extra={"job_id": job_id, "error": str(e)},
        )


def _notify_ws(job_id: str, data: dict):
    """Compat: notificação final — delega para a fila comum."""
    _enqueue_ws_message(job_id, data)


def push_ws_partial(job_id: str, payload: dict, message: str = "") -> None:
    """
    Envia fatia incremental de `ProcessoTrabalhista` para clientes conectados em /ws/{job_id}.
    Contrato alinhado ao frontend: type partial_update + payload (merge defensivo).
    """
    if not job_id or not str(job_id).strip():
        return
    evt: dict = {"type": "partial_update", "payload": payload}
    if message:
        evt["message"] = message
    _enqueue_ws_message(str(job_id).strip(), evt)


def _ws_payload_is_terminal(msg: dict) -> bool:
    """True se a mensagem encerra a conexão (resultado final do job)."""
    if msg.get("type") == "partial_update":
        return False
    st = msg.get("status")
    return st in ("done", "error", "timeout", "sucesso", "erro")


def _get_job(job_id: str) -> dict | None:
    """Lê da memória (rápido). Fallback para SQLite (após restart)."""
    with _jobs_lock:
        if job_id in _jobs_mem:
            return _jobs_mem[job_id]
    job_repo = get_job_repo()
    row = job_repo.get_job_status(job_id)
    if not row:
        return None
    if row["status"] in ("done", "error", "timeout") and row.get("result"):
        return row["result"]
    return {"status": row["status"]}


# ── Job runner com timeout ────────────────────────────────────────────────────

def _run_job_with_timeout(
    job_id: str,
    user_id: str,
    tenant_id: str,
    file_bytes: bytes = None,
    files_list: list = None,
    cache_context: str = "auto",
    single_filename: str = "documento.pdf",
):
    result_container = {}
    done_event = threading.Event()

    def _worker():
        try:
            if files_list and len(files_list) > 0:
                result = process_lawsuit_dossie(tenant_id, files_list, job_id=job_id)
            else:
                result = process_lawsuit_pdf(
                    tenant_id,
                    file_bytes,
                    job_id=job_id,
                    cache_context=cache_context or "auto",
                    filename=single_filename or "documento.pdf",
                )
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

    # Normaliza status: "sucesso"→"done", "erro"→"error"
    _STATUS_MAP = {"sucesso": "done", "erro": "error"}
    if final.get("status") in _STATUS_MAP:
        final["status"] = _STATUS_MAP[final["status"]]

    _set_job(job_id, user_id, final)  # ← notifica WS aqui


def _start_job(
    job_id: str,
    user_id: str,
    tenant_id: str,
    file_bytes: bytes = None,
    files_list: list = None,
    cache_context: str = "auto",
    single_filename: str = "documento.pdf",
):
    _set_job(job_id, user_id, {"status": "processing"})
    controller = threading.Thread(
        target=_run_job_with_timeout,
        args=(job_id, user_id, tenant_id),
        kwargs={
            "file_bytes": file_bytes,
            "files_list": files_list,
            "cache_context": cache_context,
            "single_filename": single_filename,
        },
        daemon=True,
    )
    controller.start()


_EXT_UPLOAD = (".pdf", ".doc", ".docx", ".pjc", ".xml", ".xlsx", ".xls", ".jpg", ".jpeg", ".png")


@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    user_id: str = Form(...),
    files: List[UploadFile] = File(..., alias="files"),
    cache_context: str = Form("auto"),
):
    """
    Recebe um ou mais arquivos (dossiê): PDF, DOC, DOCX, PJC, XML.
    Um único PDF: fluxo clássico (sentence_finder + IA).
    Um único PDF/DOC/DOCX com cache_context=peticao_inicial ou contestacao: fluxo dedicado
    (pedidos da inicial / teses de defesa — mesmo contrato que POST /api/extract).
    Múltiplos arquivos ou não-PDF (com contexto auto): extração por arquivo, super-contexto.
    """
    # Sprint 1/2: tenant_id == user_id — vem do header (x-user-id); user_id do form é legado.
    ctx = get_request_context()
    tenant_id = ctx.tenant_id or (user_id or "anonimo")
    effective_user_id = tenant_id
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
    # Atualiza contexto com o job_id para logs e serviços downstream.
    set_job_id(job_id)
    _set_job(job_id, effective_user_id, {"status": "queued"})

    use_single_pdf, err_msg = _should_run_process_lawsuit_pdf_upload(
        collected, cache_context
    )
    if err_msg:
        raise HTTPException(400, err_msg)

    if use_single_pdf:
        fname, fbytes = collected[0]
        background_tasks.add_task(
            _start_job,
            job_id,
            effective_user_id,
            tenant_id,
            file_bytes=fbytes,
            files_list=None,
            cache_context=cache_context or "auto",
            single_filename=fname or "documento.pdf",
        )
    else:
        background_tasks.add_task(
            _start_job,
            job_id,
            effective_user_id,
            tenant_id,
            file_bytes=None,
            files_list=collected,
            cache_context="auto",
            single_filename="documento.pdf",
        )

    return {
        "job_id": job_id,
        "status": "queued",
        "timeout_seconds": JOB_TIMEOUT_SECONDS,
        "ws_url": f"/ws/{job_id}",
    }


@router.post("/extract")
@router.post("/api/extract")
async def extract_single(
    file: UploadFile = File(...),
    user_id: str = Form("anonimo"),
    cache_context: str = Form("auto"),
):
    """
    Extrator rápido — fluxo síncrono para um único arquivo (Processo/Sentença).

    Usa o mesmo pipeline do worker principal (`process_lawsuit_pdf`), mas retorna
    o resultado diretamente sem criar job em background.

    cache_context: "auto" (padrão), "peticao_inicial" ou "contestacao" — chave composta e
    fluxo dedicado (PDF/DOC/DOCX).
    """
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in _EXT_UPLOAD):
        raise HTTPException(
            400,
            "Tipo não aceito. Use PDF, DOC, DOCX, PJC, XML, XLSX, XLS, JPG ou PNG.",
        )

    content = await file.read()
    if len(content) < 10:
        raise HTTPException(400, "Arquivo vazio ou inválido.")

    # Sprint 1: user_id efetivo vem do contexto (header x-user-id).
    ctx = get_request_context()
    effective_user_id = ctx.user_id or (user_id or "anonimo")

    result = process_lawsuit_pdf(
        effective_user_id,
        content,
        job_id="",
        cache_context=cache_context or "auto",
        filename=file.filename or "documento.pdf",
    )
    if not isinstance(result, dict):
        raise HTTPException(500, "Resposta inesperada do motor de extração.")

    return result


@router.post("/upload-pjc/{job_id}")
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


@router.get("/status/{job_id}")
def get_status(job_id: str):
    """
    Fallback HTTP para polling.
    Usado quando WebSocket não está disponível ou após restart.
    """
    job = _get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' não encontrado")
    return job


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    with _jobs_lock:
        removed = _jobs_mem.pop(job_id, None)
    return {"deleted": removed is not None, "job_id": job_id}


@router.get("/export-excel/{job_id}")
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
    job = _get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' não encontrado",
        )

    status = job.get("status")

    if status in ("queued", "processing"):
        raise HTTPException(
            status_code=202,
            detail=f"Processamento em andamento (status: {status})",
        )

    if status in ("error", "erro"):
        raise HTTPException(
            status_code=400,
            detail="Job terminou com erro — não é possível exportar",
        )

    # Mesmo padrão do /export-pjc: resultado pode estar na raiz ou em "result".
    # Se "result" existe, não faça fallback por falsy: lista vazia/None deve ser inválido.
    dados = job["result"] if "result" in job else job

    if not dados or not isinstance(dados, dict):
        raise HTTPException(
            status_code=400,
            detail="Resultado vazio ou inválido — não é possível exportar",
        )

    dados_limpos = {k: v for k, v in dados.items() if k != "status"}

    try:
        from services.excel_exporter import exportar_excel

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
            },
        )

    except Exception as e:
        print(f"[EXCEL] Erro ao gerar .xlsx para job {job_id}: {e}", flush=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar Excel: {str(e)}",
        )


@router.get("/health")
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
    }


@router.websocket("/ws/{job_id}")
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
        await websocket.send_text(json.dumps(job, ensure_ascii=False, default=str))
        await websocket.close()
        print(f"[WS] Job {job_id} ja estava pronto - enviado imediatamente", flush=True)
        return

    # Registrar Queue para este job
    queue: asyncio.Queue = asyncio.Queue()
    with _ws_lock:
        _ws_queues[job_id] = queue

    def _dumps(obj: dict) -> str:
        try:
            return json.dumps(obj, ensure_ascii=False, default=str)
        except TypeError:
            return json.dumps({"status": "error", "msg": "Falha ao serializar evento WS"})

    try:
        while True:
            try:
                result = await asyncio.wait_for(queue.get(), timeout=10.0)
                await websocket.send_text(_dumps(result))
                if result.get("type") == "partial_update":
                    continue
                if _ws_payload_is_terminal(result):
                    print(
                        f"[WS] Resultado enviado: {job_id} -> status={result.get('status')}",
                        flush=True,
                    )
                    break
                # Mensagem legada ou formato inesperado: envia uma vez e encerra
                break

            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(_dumps({"status": "processing"}))
                except Exception:
                    break

    except WebSocketDisconnect:
        print(f"[WS] Cliente desconectou: {job_id}", flush=True)
    finally:
        # Limpar Queue do registro
        with _ws_lock:
            _ws_queues.pop(job_id, None)
        print(f"[WS] Encerrado: {job_id}", flush=True)


@router.websocket("/ws/lab-pipeline")
async def websocket_lab_pipeline(websocket: WebSocket):
    """
    Canal do Laboratório (useAnalyze). POST /lab/analisar é síncrono; mantém heartbeat
    até o cliente encerrar — evita 404. Evolução futura: session_id + fila como /ws/{job_id}.
    """
    await websocket.accept()
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=25.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(
                        json.dumps({"status": "processing", "channel": "lab-pipeline"})
                    )
                except Exception:
                    break
    except WebSocketDisconnect:
        pass

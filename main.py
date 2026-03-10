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

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from workers.processor import process_lawsuit_pdf
from services.database import (
    save_job_status,
    get_job_status,
    get_user_credits,
    get_user_history,
    cleanup_old_jobs,
)
from services.pjc_exporter import exportar_pjc, gerar_nome_arquivo
from config import settings
import uvicorn
import uuid
import threading
import asyncio
import json

app = FastAPI(
    title="PjeCalc Smart Extractor API",
    version="3.2",
    description="Extração automática de verbas trabalhistas de sentenças e acórdãos PJe",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        print(f"[WS] Falha ao notificar job {job_id}: {e}")


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

def _run_job_with_timeout(job_id: str, user_id: str, file_bytes: bytes):
    result_container = {}
    done_event = threading.Event()

    def _worker():
        try:
            result = process_lawsuit_pdf(user_id, file_bytes)
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
        print(f"[MAIN] ⚠️ Job {job_id} expirou por timeout ({JOB_TIMEOUT_SECONDS}s)")

    # Normaliza status: "sucesso"→"done", "erro"→"error"
    _STATUS_MAP = {"sucesso": "done", "erro": "error"}
    if final.get("status") in _STATUS_MAP:
        final["status"] = _STATUS_MAP[final["status"]]

    _set_job(job_id, user_id, final)  # ← notifica WS aqui


def _start_job(job_id: str, user_id: str, file_bytes: bytes):
    _set_job(job_id, user_id, {"status": "processing"})
    controller = threading.Thread(
        target=_run_job_with_timeout,
        args=(job_id, user_id, file_bytes),
        daemon=True
    )
    controller.start()


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    cleanup_old_jobs(days=7)
    print("[MAIN] API v3.2 iniciada. WebSocket push ativo. pjc_exporter v5.4 (XML puro + gprec fix).")


# ── Endpoints HTTP ────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"status": "online", "version": "3.2", "docs": "/docs"}


@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Recebe PDF, valida e enfileira. Retorna job_id para WS ou polling."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Apenas arquivos PDF são aceitos")

    file_bytes = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            400,
            f"Arquivo muito grande ({len(file_bytes) // (1024*1024)}MB). "
            f"Máximo: {settings.MAX_FILE_SIZE_MB}MB"
        )
    if len(file_bytes) < 100:
        raise HTTPException(400, "Arquivo PDF inválido ou vazio")

    job_id = str(uuid.uuid4())
    _set_job(job_id, user_id, {"status": "queued"})
    background_tasks.add_task(_start_job, job_id, user_id, file_bytes)

    return {
        "job_id": job_id,
        "status": "queued",
        "timeout_seconds": JOB_TIMEOUT_SECONDS,
        "ws_url": f"/ws/{job_id}",
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


@app.get("/export-pjc/{job_id}")
def export_pjc(job_id: str):
    """
    Gera e retorna o arquivo .pjc para importação no PJeCalc Cidadão.

    v5.3: .pjc é XML puro ISO-8859-1 (SEM ZIP).
    Formato confirmado via análise do arquivo real do processo 0010070-87.2020.5.03.0092.
    Versões 2.13.0 e 2.14.0 usam o mesmo formato XML plano.
    """
    job = _get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' não encontrado")

    status = job.get("status")

    # Job ainda em andamento
    if status in ("queued", "processing"):
        raise HTTPException(
            status_code=400,
            detail=f"Job ainda não concluído (status: {status})"
        )

    # Job com erro
    if status in ("error", "erro"):
        raise HTTPException(
            status_code=400,
            detail="Job terminou com erro — não é possível exportar"
        )

    # _get_job retorna o dict de resultado diretamente quando done.
    # O resultado pode estar na raiz ou aninhado em "result" (fallback SQLite).
    dados = job.get("result") or job

    if not dados or not isinstance(dados, dict):
        raise HTTPException(
            status_code=400,
            detail="Resultado vazio ou inválido — não é possível exportar"
        )

    # Remover chave "status" antes de passar ao exportador
    dados_limpos = {k: v for k, v in dados.items() if k != "status"}

    try:
        pjc_bytes = exportar_pjc(dados_limpos)
        nome      = gerar_nome_arquivo(dados_limpos)
        return Response(
            content=pjc_bytes,
            media_type="application/xml",          # v5.3: .pjc é XML puro (não ZIP)
            headers={
                "Content-Disposition": f'attachment; filename="{nome}"',
                "X-PJC-Version": "5.4",
            }
        )
    except Exception as e:
        print(f"[PJC] ❌ Erro ao gerar .pjc para job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar .pjc: {str(e)}")


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
    print(f"[WS] Conectado: {job_id}")

    # Race condition: job pode ter terminado antes do WS conectar
    job = _get_job(job_id)
    if job and job.get("status") not in ("queued", "processing"):
        await websocket.send_text(json.dumps(job))
        await websocket.close()
        print(f"[WS] Job {job_id} já estava pronto — enviado imediatamente")
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
                print(f"[WS] Resultado enviado: {job_id} → status={result.get('status')}")
                break  # job terminou — fecha conexão

            except asyncio.TimeoutError:
                # Heartbeat — mantém conexão viva no browser
                try:
                    await websocket.send_text(json.dumps({"status": "processing"}))
                except Exception:
                    break  # browser desconectou

    except WebSocketDisconnect:
        print(f"[WS] Cliente desconectou: {job_id}")
    finally:
        # Limpar Queue do registro
        with _ws_lock:
            _ws_queues.pop(job_id, None)
        print(f"[WS] Encerrado: {job_id}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
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
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import os
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routers import lab, extractor, admin, exports
from services.database import cleanup_old_jobs
from services.request_context import (
    set_request_context,
    set_job_id,
    log_structured,
)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup e shutdown (substitui on_event deprecado)."""
    # Startup
    cleanup_old_jobs(days=7)
    _port = os.environ.get("PORT", "8000")
    print(
        "[MAIN] API v3.2 iniciada. WebSocket push ativo. pjc_exporter v5.4 (XML puro + gprec fix).",
        flush=True,
    )
    print(
        f"[MAIN] Abra o sistema na MESMA PORTA que o Uvicorn mostra abaixo (ex.: se aparecer 'running on ...8001', use http://localhost:8001/)",
        flush=True,
    )
    yield
    # Shutdown (opcional)


# Configuração básica de logging: um logger principal que escreve JSON no stdout.
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)


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


CRITICAL_PATHS = {"/api/extract", "/lab/analisar", "/api/stats"}
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.middleware("http")
async def _request_context_and_logging(request: Request, call_next):
    """
    Middleware central:
    - Extrai x-user-id e inicializa RequestContext (tenant_id == user_id na fase 1).
    - Mede latência e registra log estruturado em JSON para endpoints críticos.
    """
    user_id_header = request.headers.get("x-user-id") or "anonimo"
    ctx = set_request_context(tenant_id=user_id_header, user_id=user_id_header)

    start = time.perf_counter()
    status_code = 500
    error: str | None = None

    try:
        response = await call_next(request)
        status_code = response.status_code
        # Se a resposta contiver job_id no corpo JSON, atualiza o contexto
        try:
            if (
                request.url.path in ("/upload", "/api/extract")
                and hasattr(response, "body")
                and response.body
            ):
                data = json.loads(response.body.decode("utf-8"))
                job_id = data.get("job_id")
                if job_id:
                    set_job_id(job_id)
        except Exception:
            # Logging de falha de inspeção não deve derrubar a requisição
            pass
        return response
    except Exception as exc:
        status_code = 500
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        latency_ms = (time.perf_counter() - start) * 1000.0
        path = request.url.path
        if path in CRITICAL_PATHS:
            level = "ERROR" if status_code >= 500 else "INFO"
            log_structured(
                level=level,
                method=request.method,
                path=path,
                status_code=status_code,
                latencia_ms=latency_ms,
                error=error,
            )


@app.middleware("http")
async def _spa_fallback(request: Request, call_next):
    """
    SPA fallback: qualquer GET que não seja rota de API e retorne 404
    recebe o index.html do frontend (React Router trata o path no cliente).
    Prefixos de API excluídos do fallback: /api, /lab, /ws.
    """
    response = await call_next(request)
    _API_PREFIXES = ("/api", "/lab", "/ws")
    if (
        response.status_code == 404
        and request.method == "GET"
        and not request.url.path.startswith(_API_PREFIXES)
    ):
        index = _FRONTEND_DIR / "index.html"
        if index.exists():
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=index.read_text(encoding="utf-8"), status_code=200)
    return response


app.include_router(lab.router)
app.include_router(extractor.router)
app.include_router(admin.router)
app.include_router(exports.router)


# Servir frontend em / — deve ficar por último para não sombrear rotas da API (/api/*)
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
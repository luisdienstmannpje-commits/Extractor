"""
request_context.py — Contexto de requisição e helpers de tenant/log

Objetivo desta sprint:
- Padronizar propagação de `tenant_id`/`user_id` usando contextvars.
- Expor um `RequestContext` acessível em qualquer camada (routers, services, KB, DB).
- Fornecer helpers para logging estruturado em JSON.

Assunção TEMPORÁRIA (SaaS fase 1):
- `tenant_id == user_id` enquanto não houver modelo de identidade separado.
  Isso está documentado aqui para futura separação explícita.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import contextvars
import logging
import uuid
import json


@dataclass
class RequestContext:
    request_id: str
    tenant_id: str
    user_id: str
    job_id: Optional[str] = None


_ctx_var: contextvars.ContextVar[Optional[RequestContext]] = contextvars.ContextVar(
    "request_context", default=None
)


def set_request_context(
    *, tenant_id: str, user_id: str, job_id: Optional[str] = None
) -> RequestContext:
    """
    Inicializa o contexto da requisição para o ciclo atual.
    Assumimos temporariamente tenant_id == user_id (SaaS fase 1).
    """
    # Fase 1: se tenant_id vier vazio, usa user_id como fallback
    effective_tenant = tenant_id or user_id or "anonymous"
    effective_user = user_id or effective_tenant

    ctx = RequestContext(
        request_id=str(uuid.uuid4()),
        tenant_id=effective_tenant,
        user_id=effective_user,
        job_id=job_id,
    )
    _ctx_var.set(ctx)
    return ctx


def get_request_context() -> RequestContext:
    """
    Retorna o contexto atual da requisição.
    Se ainda não existir (ex.: código fora de middleware), retorna um contexto anônimo.
    """
    ctx = _ctx_var.get()
    if ctx is None:
        ctx = RequestContext(
            request_id=str(uuid.uuid4()),
            tenant_id="anonymous",
            user_id="anonymous",
            job_id=None,
        )
        _ctx_var.set(ctx)
    return ctx


def set_job_id(job_id: str) -> None:
    """Atualiza apenas o job_id no contexto atual (quando conhecido depois)."""
    ctx = get_request_context()
    _ctx_var.set(
        RequestContext(
            request_id=ctx.request_id,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            job_id=job_id,
        )
    )


def current_tenant_id() -> str:
    """Helper para usar em serviços/KB/DB sem importar toda a estrutura."""
    return get_request_context().tenant_id or "default"


def current_user_id() -> str:
    return get_request_context().user_id or "anonymous"


def build_log_payload(
    *,
    level: str,
    method: str,
    path: str,
    status_code: int,
    latencia_ms: float,
    error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Constrói o JSON de log estruturado com base no contrato definido para a sprint.
    """
    ctx = get_request_context()
    payload: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "request_id": ctx.request_id,
        "tenant_id": ctx.tenant_id,
        "user_id": ctx.user_id,
        "job_id": ctx.job_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "latencia_ms": round(latencia_ms, 3),
        "error": error,
    }
    if extra:
        payload.update(extra)
    return payload


def log_structured(
    *,
    level: str,
    method: str,
    path: str,
    status_code: int,
    latencia_ms: float,
    error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Envia o log estruturado em JSON para o logger principal.
    O lado consumidor (Cloud Logging, ELK, etc.) assume que cada linha é um JSON.
    """
    logger = logging.getLogger("smart_extractor")
    payload = build_log_payload(
        level=level,
        method=method,
        path=path,
        status_code=status_code,
        latencia_ms=latencia_ms,
        error=error,
        extra=extra,
    )
    text = json.dumps(payload, ensure_ascii=False)
    if level.upper() == "ERROR":
        logger.error(text)
    else:
        logger.info(text)


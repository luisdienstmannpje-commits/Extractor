"""
database.py — Factory de repositórios (Repository Pattern)

ANTES:
- Centralizava toda a lógica SQLite em funções de módulo.

AGORA (Sprint 2 — Commit A):
- Expõe apenas factories de repositório (Extraction/Cache/Job).
- Mantém funções de conveniência com a mesma assinatura antiga,
  delegando internamente para os repositórios para compatibilidade.

Tabelas (SQLite):
  users      — user_id, credits
  extracoes  — histórico de extrações (JSON completo)
  cache      — cache SHA-256 → JSON (evita reprocessamento)
  jobs       — status de jobs em background (persistência entre restarts)
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List

from config import settings
from services.repositories import (
    ExtractionRepository,
    CacheRepository,
    JobRepository,
    CreditsRepository,
    SQLiteExtractionRepository,
    SQLiteCacheRepository,
    SQLiteJobRepository,
    SQLiteCreditsRepository,
)

_logger = logging.getLogger("smart_extractor")


# ── Factories ─────────────────────────────────────────────────────────────────

def get_extraction_repo(tenant_id: str) -> ExtractionRepository:
    """
    Factory oficial para o domínio de extrações.

    Futuras implementações (ex.: Postgres) devem ser plugadas aqui.
    """
    return SQLiteExtractionRepository(tenant_id=tenant_id)


def get_cache_repo() -> CacheRepository:
    """Factory para o domínio de cache de PDFs."""
    return SQLiteCacheRepository()


def get_job_repo() -> JobRepository:
    """Factory para o domínio de jobs (status de background)."""
    return SQLiteJobRepository()


# ── Créditos (Billing) — domínio da Sprint 3 ────────────────────────────────

def get_credits_repo() -> CreditsRepository:
    """Factory para o domínio de créditos/Billing."""
    return SQLiteCreditsRepository()


def get_user_credits(user_id: str) -> int:
    """Wrapper de compatibilidade — delega para CreditsRepository."""
    return get_credits_repo().get_user_credits(user_id)


def deduct_credit(user_id: str) -> None:
    """Wrapper de compatibilidade — delega para CreditsRepository."""
    get_credits_repo().deduct_credit(user_id)


def add_credits(user_id: str, amount: int) -> None:
    """Wrapper de compatibilidade — delega para CreditsRepository."""
    get_credits_repo().add_credits(user_id, amount)


def get_plan(user_id: str) -> str:
    """Retorna o plano atual do tenant/usuário."""
    return get_credits_repo().get_plan(user_id)


def set_plan(user_id: str, plan: str) -> None:
    """Define o plano do tenant/usuário."""
    get_credits_repo().set_plan(user_id, plan)


def get_usage_stats(user_id: str) -> dict:
    """Retorna métricas de uso e billing para o tenant/usuário."""
    return get_credits_repo().get_usage_stats(user_id)


def registrar_uso_lab(user_id: str) -> None:
    """Registra uma análise do Laboratório para o tenant/usuário."""
    get_credits_repo().registrar_uso_lab(user_id)


def quota_excedida(user_id: str, tipo: str) -> bool:
    """Verifica se o tenant atingiu o limite do plano para o tipo informado."""
    return get_credits_repo().quota_excedida(user_id, tipo)


# ── Operações administrativas diversas ────────────────────────────────────────

def clear_extracoes() -> int:
    """
    Zera o histórico de extrações (tabela extracoes).

    Operação global (tenant_id='default') usada pelo endpoint
    /api/admin/reset-contagem para reiniciar o contador de processos analisados.
    """
    repo = get_extraction_repo(tenant_id="default")
    return repo.clear_extracoes()


# cleanup_old_jobs permanece disponível como helper administrativo

def cleanup_old_jobs(days: int = 7) -> None:
    """Remove jobs mais antigos que N dias. Chamar periodicamente."""
    get_job_repo().cleanup_old_jobs(days=days)

"""
services.repositories.base

Interfaces (Repository Pattern) para persistência.

Domínios mapeados a partir de `services/database.py`:
- Domínio 1 — Extrações
- Domínio 2 — Cache de PDFs
- Domínio 3 — Jobs (background tasks)
- Domínio 4 — Créditos/Billing (stub para Sprint 3)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ExtractionRepository(ABC):
    """Domínio 1 — Extrações (histórico, stats)."""

    @abstractmethod
    def save_extraction(
        self,
        user_id: str,
        data: Dict[str, Any],
        doc_type: Optional[str] = None,
        model_used: Optional[str] = None,
    ) -> str:
        ...

    @abstractmethod
    def get_extraction(self, doc_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_user_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_total_extractions(self, user_id: Optional[str] = None) -> int:
        ...

    @abstractmethod
    def clear_extracoes(self) -> int:
        ...


class CacheRepository(ABC):
    """Domínio 2 — Cache de PDFs."""

    @abstractmethod
    def get_cache(self, pdf_hash: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def save_cache(self, pdf_hash: str, data: Dict[str, Any]) -> None:
        ...


class JobRepository(ABC):
    """Domínio 3 — Jobs (status de processamento em background)."""

    @abstractmethod
    def save_job_status(
        self,
        job_id: str,
        user_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...

    @abstractmethod
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def cleanup_old_jobs(self, days: int = 7) -> None:
        ...


class CreditsRepository(ABC):
    """
    Domínio 4 — Créditos/Billing.

    ATENÇÃO: domínio fora do escopo da Sprint 2.
    Mantido aqui apenas como contrato para a Sprint 3.
    """

    @abstractmethod
    def get_user_credits(self, user_id: str) -> int:
        ...

    @abstractmethod
    def deduct_credit(self, user_id: str) -> None:
        ...

    @abstractmethod
    def add_credits(self, user_id: str, amount: int) -> None:
        ...

    @abstractmethod
    def get_plan(self, user_id: str) -> str:
        """Retorna o plano do tenant: 'free' | 'pro' | 'enterprise'. Padrão: 'free'."""
        ...

    @abstractmethod
    def set_plan(self, user_id: str, plan: str) -> None:
        """Define o plano do tenant. Valores válidos: 'free', 'pro', 'enterprise'."""
        ...

    @abstractmethod
    def get_usage_stats(self, user_id: str) -> dict:
        """
        Retorna dict com métricas de uso do tenant:
        {
          "creditos_restantes": int,
          "plano": str,
          "limite_pdfs": int,       # -1 = ilimitado
          "limite_lab": int,        # -1 = ilimitado
          "pdfs_usados": int,
          "lab_analises_usadas": int,
        }
        """
        ...

    @abstractmethod
    def registrar_uso_lab(self, user_id: str) -> None:
        """Incrementa o contador de análises do Laboratório para o tenant."""
        ...

    @abstractmethod
    def quota_excedida(self, user_id: str, tipo: str) -> bool:
        """Retorna True se o tenant atingiu o limite do plano para o tipo."""
        ...


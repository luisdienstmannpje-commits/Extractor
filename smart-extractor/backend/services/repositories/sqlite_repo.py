"""
Implementações SQLite das interfaces de repositório.

Extraído de `services/database.py`, separado por domínio:
- Extrações
- Cache de PDFs
- Jobs (status de background)

Objetivo: permitir troca futura por Postgres implementando um novo arquivo
sem alterar o restante do código (Repository Pattern).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config import settings
from models import SCHEMA_VERSION
from .base import ExtractionRepository, CacheRepository, JobRepository, CreditsRepository

_logger = logging.getLogger("smart_extractor")

# Limites por plano. -1 = ilimitado.
# enterprise e dev: Lab + PDFs ilimitados no cálculo de quota.
_PLANOS: dict = {
    "free":       {"pdfs": 10,  "lab_analises": 3},
    "pro":        {"pdfs": 100, "lab_analises": 30},
    "enterprise": {"pdfs": -1,  "lab_analises": -1},
    "dev":        {"pdfs": -1,  "lab_analises": -1},
}

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "local_db.sqlite")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode para melhor concorrência entre threads
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db() -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            user_id  TEXT PRIMARY KEY,
            credits  INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS extracoes (
            id         TEXT PRIMARY KEY,
            user_id    TEXT,
            data       TEXT,
            doc_type   TEXT,
            model_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS cache (
            pdf_hash       TEXT PRIMARY KEY,
            data           TEXT,
            schema_version TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        # Migração suave: adiciona coluna se tabela já existia sem ela
        try:
            conn.execute("ALTER TABLE cache ADD COLUMN schema_version TEXT")
        except Exception:
            pass  # Coluna já existe — ignorar
        # Migração suave: colunas de plano e uso do Lab na tabela users
        try:
            conn.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN lab_analises_usadas INTEGER DEFAULT 0")
        except Exception:
            pass
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id     TEXT PRIMARY KEY,
            user_id    TEXT,
            status     TEXT DEFAULT 'queued',
            result     TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        # Índices para queries comuns
        conn.execute("CREATE INDEX IF NOT EXISTS idx_extracoes_user ON extracoes(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        conn.commit()
    finally:
        conn.close()


_init_db()


class SQLiteExtractionRepository(ExtractionRepository):
    """Implementação SQLite para o domínio de extrações."""

    def __init__(self, tenant_id: Optional[str] = None) -> None:
        # tenant_id mantido para futura segmentação física; hoje fica em nível lógico.
        self.tenant_id = tenant_id or "default"

    def save_extraction(
        self,
        user_id: str,
        data: Dict[str, Any],
        doc_type: Optional[str] = None,
        model_used: Optional[str] = None,
    ) -> str:
        doc_id = str(uuid.uuid4())
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO extracoes (id, user_id, data, doc_type, model_used) VALUES (?, ?, ?, ?, ?)",
                (
                    doc_id,
                    user_id,
                    json.dumps(data, ensure_ascii=False, default=str),
                    doc_type,
                    model_used,
                ),
            )
            conn.commit()
            return doc_id
        finally:
            conn.close()

    def get_extraction(self, doc_id: str) -> Optional[Dict[str, Any]]:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT data FROM extracoes WHERE id=?",
                (doc_id,),
            ).fetchone()
            return json.loads(row["data"]) if row else None
        finally:
            conn.close()

    def get_user_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        conn = _get_conn()
        try:
            rows = conn.execute(
                """
                SELECT id, doc_type, model_used, created_at,
                       json_extract(data, '$.numero_processo') as numero_processo,
                       json_extract(data, '$.reclamante') as reclamante,
                       json_extract(data, '$.reclamada') as reclamada
                FROM extracoes
                WHERE user_id=?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_total_extractions(self, user_id: Optional[str] = None) -> int:
        conn = _get_conn()
        try:
            if user_id:
                row = conn.execute(
                    """
                    SELECT COUNT(DISTINCT json_extract(data, '$.numero_processo')) AS total
                    FROM extracoes
                    WHERE user_id = ?
                      AND json_extract(data, '$.numero_processo') IS NOT NULL
                      AND json_extract(data, '$.numero_processo') != ''
                    """,
                    (user_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT COUNT(DISTINCT json_extract(data, '$.numero_processo')) AS total
                    FROM extracoes
                    WHERE json_extract(data, '$.numero_processo') IS NOT NULL
                      AND json_extract(data, '$.numero_processo') != ''
                    """
                ).fetchone()
            return int(row["total"]) if row else 0
        finally:
            conn.close()

    def clear_extracoes(self) -> int:
        conn = _get_conn()
        try:
            cursor = conn.execute("DELETE FROM extracoes")
            conn.commit()
            deleted = cursor.rowcount
            _logger.info(f'{{"event":"clear_extracoes","deleted":%d}}', deleted)
            return deleted
        finally:
            conn.close()


class SQLiteCacheRepository(CacheRepository):
    """Implementação SQLite para cache de PDFs."""

    def get_cache(self, pdf_hash: str) -> Optional[Dict[str, Any]]:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT data, schema_version FROM cache WHERE pdf_hash=?",
                (pdf_hash,),
            ).fetchone()
            if not row:
                return None
            versao_cache = row["schema_version"]
            if versao_cache != SCHEMA_VERSION:
                _logger.info(
                    '{"event":"cache_miss_schema","cache_version":"%s","current_version":"%s"}',
                    versao_cache,
                    SCHEMA_VERSION,
                )
                return None
            return json.loads(row["data"])
        finally:
            conn.close()

    def save_cache(self, pdf_hash: str, data: Dict[str, Any]) -> None:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO cache (pdf_hash, data, schema_version) VALUES (?, ?, ?)",
                (pdf_hash, json.dumps(data, ensure_ascii=False), SCHEMA_VERSION),
            )
            conn.commit()
        finally:
            conn.close()


class SQLiteJobRepository(JobRepository):
    """Implementação SQLite para status de jobs."""

    def save_job_status(
        self,
        job_id: str,
        user_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        conn = _get_conn()
        try:
            result_json = json.dumps(result, ensure_ascii=False) if result else None
            conn.execute(
                """
                INSERT INTO jobs (job_id, user_id, status, result, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    result = excluded.result,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (job_id, user_id, status, result_json),
            )
            conn.commit()
        finally:
            conn.close()

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retorna o status completo de um job."""
        conn = _get_conn()
        try:
            row = conn.execute(
                """
                SELECT job_id, user_id, status, result, created_at, updated_at
                FROM jobs WHERE job_id=?
                """,
                (job_id,),
            ).fetchone()
            if not row:
                return None
            result: Dict[str, Any] = dict(row)
            if result.get("result"):
                result["result"] = json.loads(result["result"])
            return result
        finally:
            conn.close()

    def cleanup_old_jobs(self, days: int = 7) -> None:
        """Remove jobs mais antigos que N dias."""
        conn = _get_conn()
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            deleted = conn.execute(
                "DELETE FROM jobs WHERE created_at < ?",
                (cutoff,),
            ).rowcount
            conn.commit()
            if deleted:
                _logger.info(
                    '{"event":"cleanup_old_jobs","deleted":%d,"days":%d}', deleted, days
                )
        finally:
            conn.close()


class SQLiteCreditsRepository(CreditsRepository):
    """Implementação SQLite para o domínio de créditos/Billing."""

    def get_user_credits(self, user_id: str) -> int:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT credits FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO users (user_id, credits) VALUES (?, ?)",
                    (user_id, settings.PDFS_GRATUITOS_POR_USUARIO),
                )
                return settings.PDFS_GRATUITOS_POR_USUARIO
            return int(row["credits"])

    def deduct_credit(self, user_id: str) -> None:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE users SET credits = MAX(0, credits - 1) WHERE user_id = ?",
                (user_id,),
            )

    def add_credits(self, user_id: str, amount: int) -> None:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE users SET credits = credits + ? WHERE user_id = ?",
                (amount, user_id),
            )

    def get_plan(self, user_id: str) -> str:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT plan FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row is None:
                return "free"
            return (row["plan"] or "free") if isinstance(row, sqlite3.Row) else (row[0] or "free")

    def set_plan(self, user_id: str, plan: str) -> None:
        planos_validos = {"free", "pro", "enterprise", "dev"}
        if plan not in planos_validos:
            raise ValueError(f"Plano inválido: {plan}. Válidos: {planos_validos}")
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, plan)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET plan = excluded.plan
                """,
                (user_id, plan),
            )

    def get_usage_stats(self, user_id: str) -> dict:
        creditos = self.get_user_credits(user_id)
        plano = self.get_plan(user_id)
        limites = _PLANOS.get(plano, _PLANOS["free"])
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT lab_analises_usadas FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if isinstance(row, sqlite3.Row):
                lab_usadas = row["lab_analises_usadas"]
            else:
                lab_usadas = row[0] if row else 0
        limite_pdfs = limites["pdfs"]
        pdfs_usados = (
            max(0, limite_pdfs - creditos) if limite_pdfs != -1 else -1
        )
        resultado = {
            "creditos_restantes": creditos,
            "plano": plano,
            "limite_pdfs": limite_pdfs,
            "limite_lab": limites["lab_analises"],
            "pdfs_usados": pdfs_usados,
            "lab_analises_usadas": lab_usadas,
        }

        # Alertas de quota (80% e 100%) para PDFs e análises do Lab
        for tipo, chave_usados, chave_limite in [
            ("pdfs", "pdfs_usados", "limite_pdfs"),
            ("lab_analises", "lab_analises_usadas", "limite_lab"),
        ]:
            limite = resultado[chave_limite]
            usados = resultado[chave_usados]
            if limite == -1 or usados < 0:
                continue
            pct = (usados / limite) * 100 if limite > 0 else 0
            if pct >= 100:
                _logger.warning(
                    "quota_100pct",
                    extra={
                        "user_id": user_id,
                        "tipo": tipo,
                        "usados": usados,
                        "limite": limite,
                    },
                )
            elif pct >= 80:
                _logger.warning(
                    "quota_80pct",
                    extra={
                        "user_id": user_id,
                        "tipo": tipo,
                        "usados": usados,
                        "limite": limite,
                    },
                )

        return resultado

    def registrar_uso_lab(self, user_id: str) -> None:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, lab_analises_usadas)
                VALUES (?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    lab_analises_usadas = lab_analises_usadas + 1
                """,
                (user_id,),
            )

    def quota_excedida(self, user_id: str, tipo: str) -> bool:
        """
        Verifica se o tenant atingiu o limite do plano para o tipo dado.
        tipo: 'pdfs' | 'lab_analises'
        Retorna False se limite == -1 (ilimitado).
        """
        plano = self.get_plan(user_id)
        # Desenvolvimento local: sem teto de análises do Lab para este user ou plano dev.
        if tipo == "lab_analises" and (
            user_id == "usuario_teste" or plano == "dev"
        ):
            return False
        limites = _PLANOS.get(plano, _PLANOS["free"])
        limite = limites.get(tipo, 0)
        if limite == -1:
            return False
        stats = self.get_usage_stats(user_id)
        if tipo == "pdfs":
            usados = stats.get("pdfs_usados", 0)
            if usados < 0:
                return False
            return usados >= limite
        if tipo == "lab_analises":
            return stats.get("lab_analises_usadas", 0) >= limite
        return False


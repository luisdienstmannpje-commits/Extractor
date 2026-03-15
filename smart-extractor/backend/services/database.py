"""
database.py — Persistência SQLite local

Tabelas:
  users      — user_id, credits
  extracoes  — histórico de extrações (JSON completo)
  cache      — cache SHA-256 → JSON (evita reprocessamento)
  jobs       — status de jobs em background (persistência entre restarts)
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime, timedelta
from config import settings
from models import SCHEMA_VERSION

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "local_db.sqlite")


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode para melhor concorrência entre threads
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id  TEXT PRIMARY KEY,
            credits  INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extracoes (
            id         TEXT PRIMARY KEY,
            user_id    TEXT,
            data       TEXT,
            doc_type   TEXT,
            model_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            pdf_hash       TEXT PRIMARY KEY,
            data           TEXT,
            schema_version TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migração suave: adiciona coluna se tabela já existia sem ela
    try:
        conn.execute("ALTER TABLE cache ADD COLUMN schema_version TEXT")
    except Exception:
        pass  # Coluna já existe — ignorar
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id     TEXT PRIMARY KEY,
            user_id    TEXT,
            status     TEXT DEFAULT 'queued',
            result     TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Índices para queries comuns
    conn.execute("CREATE INDEX IF NOT EXISTS idx_extracoes_user ON extracoes(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    conn.commit()
    conn.close()


_init_db()


# ── Créditos ──────────────────────────────────────────────────────────────────

def get_user_credits(user_id: str) -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT credits FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO users (user_id, credits) VALUES (?, ?)",
                (user_id, settings.PDFS_GRATUITOS_POR_USUARIO)
            )
            conn.commit()
            return settings.PDFS_GRATUITOS_POR_USUARIO
        return row["credits"]
    finally:
        conn.close()


def deduct_credit(user_id: str):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE users SET credits = credits - 1 WHERE user_id=?",
            (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


def add_credits(user_id: str, amount: int):
    """Adiciona créditos a um usuário (cria se não existir)."""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO users (user_id, credits)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET credits = credits + ?
        """, (user_id, amount, amount))
        conn.commit()
    finally:
        conn.close()


# ── Extrações ─────────────────────────────────────────────────────────────────

def save_extraction(
    user_id: str,
    data: dict,
    doc_type: str = None,
    model_used: str = None
) -> str:
    doc_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO extracoes (id, user_id, data, doc_type, model_used) VALUES (?, ?, ?, ?, ?)",
            (doc_id, user_id, json.dumps(data, ensure_ascii=False), doc_type, model_used)
        )
        conn.commit()
        return doc_id
    finally:
        conn.close()


def get_extraction(doc_id: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT data FROM extracoes WHERE id=?", (doc_id,)
        ).fetchone()
        return json.loads(row["data"]) if row else None
    finally:
        conn.close()


def get_user_history(user_id: str, limit: int = 20) -> list[dict]:
    """Retorna as últimas N extrações de um usuário."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT id, doc_type, model_used, created_at,
                   json_extract(data, '$.numero_processo') as numero_processo,
                   json_extract(data, '$.reclamante') as reclamante,
                   json_extract(data, '$.reclamada') as reclamada
            FROM extracoes
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Cache SHA-256 ─────────────────────────────────────────────────────────────

def get_cache(pdf_hash: str) -> dict | None:
    """
    Retorna cache apenas se schema_version bater com a versão atual.
    Se divergir, descarta a entrada (cache miss forçado) — o PDF será
    reprocessado e o novo resultado será salvo com a versão correta.
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT data, schema_version FROM cache WHERE pdf_hash=?", (pdf_hash,)
        ).fetchone()
        if not row:
            return None
        versao_cache = row["schema_version"]
        if versao_cache != SCHEMA_VERSION:
            print(
                f"[CACHE] Miss forçado — schema desatualizado: "
                f"cache={versao_cache} | atual={SCHEMA_VERSION}"
            )
            return None
        return json.loads(row["data"])
    finally:
        conn.close()


def save_cache(pdf_hash: str, data: dict):
    """Salva resultado no cache junto com a versão atual do schema."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cache (pdf_hash, data, schema_version) VALUES (?, ?, ?)",
            (pdf_hash, json.dumps(data, ensure_ascii=False), SCHEMA_VERSION)
        )
        conn.commit()
    finally:
        conn.close()


# ── Jobs (persistência entre restarts) ───────────────────────────────────────

def save_job_status(job_id: str, user_id: str, status: str, result: dict = None):
    """
    Cria ou atualiza o status de um job.
    status: 'queued' | 'processing' | 'done' | 'error' | 'timeout'
    """
    conn = _get_conn()
    try:
        result_json = json.dumps(result, ensure_ascii=False) if result else None
        conn.execute("""
            INSERT INTO jobs (job_id, user_id, status, result, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(job_id) DO UPDATE SET
                status = excluded.status,
                result = excluded.result,
                updated_at = CURRENT_TIMESTAMP
        """, (job_id, user_id, status, result_json))
        conn.commit()
    finally:
        conn.close()


def get_job_status(job_id: str) -> dict | None:
    """Retorna o status completo de um job."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT job_id, user_id, status, result, created_at, updated_at "
            "FROM jobs WHERE job_id=?",
            (job_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        if result.get("result"):
            result["result"] = json.loads(result["result"])
        return result
    finally:
        conn.close()


def cleanup_old_jobs(days: int = 7):
    """Remove jobs mais antigos que N dias. Chamar periodicamente."""
    conn = _get_conn()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        deleted = conn.execute(
            "DELETE FROM jobs WHERE created_at < ?", (cutoff,)
        ).rowcount
        conn.commit()
        if deleted:
            print(f"[DB] Limpeza: {deleted} jobs removidos (> {days} dias)")
    finally:
        conn.close()


# ── Estatísticas globais ──────────────────────────────────────────────────────

def get_total_extractions() -> int:
    """
    Retorna o total de **processos únicos** analisados.

    Conta DISTINCT numero_processo extraído do JSON — evita contar o mesmo
    processo várias vezes caso seja reprocessado. Registros sem numero_processo
    (campo nulo ou vazio) não são contados.
    """
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT COUNT(DISTINCT json_extract(data, '$.numero_processo')) AS total
            FROM extracoes
            WHERE json_extract(data, '$.numero_processo') IS NOT NULL
              AND json_extract(data, '$.numero_processo') != ''
        """).fetchone()
        return int(row["total"]) if row else 0
    finally:
        conn.close()


def clear_extracoes() -> int:
    """
    Remove TODOS os registros da tabela extracoes (reset de contagem).

    Usado pelo endpoint de administração para zerar o contador de processos
    analisados antes de iniciar um novo ciclo de testes. Não afeta:
    - créditos de usuários
    - cache de PDFs
    - jobs em andamento
    - Knowledge Base de regras
    - learning_log.jsonl
    Retorna o número de linhas deletadas.
    """
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM extracoes")
        conn.commit()
        deleted = cursor.rowcount
        print(f"[DB] clear_extracoes: {deleted} registro(s) removido(s).")
        return deleted
    finally:
        conn.close()
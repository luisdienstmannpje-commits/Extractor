"""
schema_version_guard.py — Proteção de Schema (S12)

Detecta quando models.py foi alterado sem que o cache do SQLite
tenha sido invalidado — evita retornar JSON com campos faltantes
ou desatualizados para o frontend.

Como funciona:
  1. Ao iniciar, computa um hash canônico dos campos de models.py
     (nomes + ordem das classes ProcessoTrabalhista e VerbaDeferida)
  2. Compara com o hash salvo na tabela `schema_versions` do SQLite
  3. Se divergir:
     - modo "warn"  → loga aviso e continua (padrão em dev)
     - modo "strict" → lança RuntimeError e bloqueia a API (padrão em prod)
  4. Se igual → silêncio total

Uso em main.py (startup):
    from services.schema_version_guard import SchemaVersionGuard
    SchemaVersionGuard().verificar()          # warn (dev)
    SchemaVersionGuard(strict=True).verificar()  # strict (prod)

Uso como script de diagnóstico:
    python schema_version_guard.py
    python schema_version_guard.py --registrar   ← após atualizar models.py

Tabela SQLite criada automaticamente:
    schema_versions(
        componente   TEXT PRIMARY KEY,
        hash         TEXT,
        campos_json  TEXT,   ← snapshot dos campos para diff legível
        atualizado_em TIMESTAMP
    )
"""

import ast
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime
from typing import Optional


# ── Caminhos ──────────────────────────────────────────────────────────────────

_HERE      = os.path.dirname(os.path.abspath(__file__))
_MODELS_PY = os.path.join(_HERE, "..", "models.py")
_DB_PATH   = os.path.join(_HERE, "..", "local_db.sqlite")

# Componente monitorado — chave na tabela schema_versions
_COMPONENTE = "models_py"


# ── Extração canônica de campos ───────────────────────────────────────────────

def _extrair_campos(models_path: str) -> dict[str, list[str]]:
    """
    Parseia models.py via AST e retorna um dict:
      { "ProcessoTrabalhista": ["campo1", "campo2", ...],
        "VerbaDeferida":       ["nome", "status_final", ...] }

    Usa AST (não import) — funciona mesmo sem as dependências instaladas.
    Considera apenas anotações de tipo (campos Pydantic), ignora métodos.
    """
    content = open(models_path, encoding="utf-8").read()
    tree    = ast.parse(content)

    resultado = {}
    classes_alvo = {"ProcessoTrabalhista", "VerbaDeferida"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name not in classes_alvo:
            continue
        campos = [
            item.target.id
            for item in node.body
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
        ]
        resultado[node.name] = campos

    return resultado


def _computar_hash(campos: dict[str, list[str]]) -> str:
    """
    Gera hash SHA-256 determinístico dos campos.
    Serialização canônica: JSON com chaves ordenadas.
    """
    canonical = json.dumps(campos, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ── SQLite ────────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_tabela():
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                componente    TEXT PRIMARY KEY,
                hash          TEXT NOT NULL,
                campos_json   TEXT,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _salvar_hash(componente: str, hash_atual: str, campos: dict):
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO schema_versions (componente, hash, campos_json, atualizado_em)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(componente) DO UPDATE SET
                hash          = excluded.hash,
                campos_json   = excluded.campos_json,
                atualizado_em = CURRENT_TIMESTAMP
        """, (componente, hash_atual, json.dumps(campos, ensure_ascii=False)))
        conn.commit()
        print(f"[GUARD] OK Hash registrado: {componente} → {hash_atual[:12]}...")
    finally:
        conn.close()


def _ler_hash_salvo(componente: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT hash, campos_json, atualizado_em FROM schema_versions WHERE componente=?",
            (componente,)
        ).fetchone()
        if not row:
            return None
        return {
            "hash":         row["hash"],
            "campos":       json.loads(row["campos_json"]) if row["campos_json"] else {},
            "atualizado_em": row["atualizado_em"],
        }
    finally:
        conn.close()


# ── Diff legível ──────────────────────────────────────────────────────────────

def _gerar_diff(campos_antigos: dict, campos_novos: dict) -> str:
    """Gera diff legível entre dois snapshots de campos."""
    linhas = []

    todas_classes = set(campos_antigos) | set(campos_novos)
    for cls in sorted(todas_classes):
        antigos = set(campos_antigos.get(cls, []))
        novos   = set(campos_novos.get(cls,  []))

        adicionados = novos - antigos
        removidos   = antigos - novos

        if not adicionados and not removidos:
            continue

        linhas.append(f"  Classe {cls}:")
        for c in sorted(adicionados):
            linhas.append(f"    + {c}  ← NOVO")
        for c in sorted(removidos):
            linhas.append(f"    - {c}  ← REMOVIDO")

    return "\n".join(linhas) if linhas else "  (sem diff detectado)"


# ── Guard principal ───────────────────────────────────────────────────────────

class SchemaVersionGuard:
    """
    Verifica integridade do schema de models.py contra o hash salvo no SQLite.

    Args:
        strict: Se True, lança RuntimeError quando schema diverge (prod).
                Se False, apenas loga aviso (dev). Padrão: False.
        models_path: Caminho para models.py. Padrão: detectado automaticamente.
    """

    def __init__(self, strict: bool = False, models_path: str = None):
        self.strict      = strict
        self.models_path = models_path or _MODELS_PY
        _init_tabela()

    def verificar(self) -> bool:
        """
        Executa a verificação.

        Returns:
            True  → schema OK (hash bate ou primeira execução)
            False → schema divergiu (apenas em modo warn)
        Raises:
            RuntimeError → schema divergiu em modo strict
        """
        if not os.path.exists(self.models_path):
            print(f"[GUARD] AVISO:  models.py não encontrado: {self.models_path}")
            return True  # não bloquear se caminho errado

        campos_atuais = _extrair_campos(self.models_path)
        hash_atual    = _computar_hash(campos_atuais)
        salvo         = _ler_hash_salvo(_COMPONENTE)

        # Primeira execução — registrar e continuar
        if salvo is None:
            print(f"[GUARD] >> Primeira execução — registrando hash: {hash_atual[:12]}...")
            _salvar_hash(_COMPONENTE, hash_atual, campos_atuais)
            return True

        # Hash igual — tudo OK
        if salvo["hash"] == hash_atual:
            print(f"[GUARD] OK Schema OK ({hash_atual[:12]})")
            return True

        # Hash divergiu — gerar relatório
        campos_salvos = salvo.get("campos", {})
        diff          = _gerar_diff(campos_salvos, campos_atuais)
        atualizado_em = salvo.get("atualizado_em", "desconhecido")

        msg = (
            f"\n{'='*60}\n"
            f"[GUARD] AVISO:  SCHEMA DIVERGIU — models.py foi alterado!\n"
            f"{'='*60}\n"
            f"  Hash anterior : {salvo['hash'][:12]}... (registrado em {atualizado_em})\n"
            f"  Hash atual    : {hash_atual[:12]}...\n"
            f"\n  Diferenças detectadas:\n{diff}\n"
            f"\n  AVISO:  Cache SQLite pode conter extrações com schema antigo.\n"
            f"  Execute para limpar o cache:\n"
            f"    python -c \"import sqlite3; c=sqlite3.connect('local_db.sqlite'); "
            f"c.execute('DELETE FROM cache'); c.commit(); print('Cache limpo')\"\n"
            f"\n  Depois registre o novo schema:\n"
            f"    python services/schema_version_guard.py --registrar\n"
            f"{'='*60}\n"
        )

        print(msg)

        if self.strict:
            raise RuntimeError(
                "Schema divergiu — API bloqueada. "
                "Limpe o cache e execute: python services/schema_version_guard.py --registrar"
            )

        return False

    def registrar(self) -> None:
        """Força registro do hash atual — usar após atualizar models.py."""
        campos_atuais = _extrair_campos(self.models_path)
        hash_atual    = _computar_hash(campos_atuais)
        _salvar_hash(_COMPONENTE, hash_atual, campos_atuais)

        total = sum(len(v) for v in campos_atuais.values())
        print(f"[GUARD] OK Schema registrado: {total} campos | hash: {hash_atual[:12]}...")
        for cls, campos in campos_atuais.items():
            print(f"  {cls}: {len(campos)} campos")

    def status(self) -> dict:
        """Retorna dict com status atual — útil para /health endpoint."""
        if not os.path.exists(self.models_path):
            return {"ok": False, "motivo": "models.py não encontrado"}

        campos_atuais = _extrair_campos(self.models_path)
        hash_atual    = _computar_hash(campos_atuais)
        salvo         = _ler_hash_salvo(_COMPONENTE)

        if salvo is None:
            return {"ok": True, "motivo": "primeira_execucao", "hash": hash_atual[:12]}

        ok = salvo["hash"] == hash_atual
        return {
            "ok":           ok,
            "hash_atual":   hash_atual[:12],
            "hash_salvo":   salvo["hash"][:12],
            "atualizado_em": salvo.get("atualizado_em"),
            "motivo":       "ok" if ok else "schema_divergiu",
        }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Garantir UTF-8 no terminal Windows (Git Bash / cmd / PowerShell)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import argparse

    parser = argparse.ArgumentParser(
        description="PjeCalc Smart Extractor — Schema Version Guard"
    )
    parser.add_argument(
        "--registrar", action="store_true",
        help="Registra o hash atual do models.py (usar após atualizar campos)"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Sai com código 1 se schema divergiu"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Mostra status atual sem fazer nada"
    )
    args = parser.parse_args()

    guard = SchemaVersionGuard(strict=args.strict)

    if args.registrar:
        guard.registrar()
        sys.exit(0)

    if args.status:
        s = guard.status()
        print(json.dumps(s, indent=2, ensure_ascii=False))
        sys.exit(0 if s["ok"] else 1)

    # Verificação padrão
    ok = guard.verificar()
    sys.exit(0 if ok else 1)
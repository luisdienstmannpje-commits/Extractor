"""
Chaves de cache para PDF — permite isolar contextos (ex.: petição inicial vs. fluxo automático).

- `auto` (padrão): chave = apenas o SHA-256 do arquivo (compatível com caches existentes).
- Outros valores: chave composta `{hash}:{contexto_normalizado}` (sem alterar o esquema SQL:
  o valor completo continua na coluna `pdf_hash`).
"""

from __future__ import annotations


def pdf_cache_storage_key(file_hash: str, cache_context: str) -> str:
    """
    Args:
        file_hash: SHA-256 hex do conteúdo do ficheiro.
        cache_context: "auto" | "peticao_inicial" | ...
    """
    ctx = (cache_context or "auto").strip().lower()
    if ctx in ("", "auto", "default"):
        return file_hash
    # Normaliza separador interno para evitar colisões acidentais
    safe = ctx.replace(":", "_")
    return f"{file_hash}:{safe}"

"""Chaves de cache por contexto."""

from services.cache_key import pdf_cache_storage_key


def test_auto_uses_raw_hash():
    h = "a" * 64
    assert pdf_cache_storage_key(h, "auto") == h
    assert pdf_cache_storage_key(h, "") == h
    assert pdf_cache_storage_key(h, "DEFAULT") == h


def test_peticao_inicial_compound():
    h = "b" * 64
    assert pdf_cache_storage_key(h, "peticao_inicial") == f"{h}:peticao_inicial"


def test_contestacao_compound():
    h = "d" * 64
    assert pdf_cache_storage_key(h, "contestacao") == f"{h}:contestacao"


def test_colon_sanitized_in_context():
    h = "c" * 64
    assert ":" not in pdf_cache_storage_key(h, "foo:bar") or pdf_cache_storage_key(
        h, "foo:bar"
    ).endswith("foo_bar")

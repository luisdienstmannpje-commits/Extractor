"""
Ciclo TDD — vara_trabalho (HIGH string)
Gaps principais:
  1. ALL CAPS — 'VARA DO TRABALHO DE RECIFE': split("de") é case-sensitive → None
  2. Sufixo '/UF'  — '4ª Vara do Trabalho de Belo Horizonte/MG' → inclui '/MG'
  3. Sufixo '- UF' — '1ª Vara do Trabalho de São Paulo - SP' → inclui '- SP'
"""
import pytest
from services.pre_extractor import PreExtractor


def _vara(text: str):
    return PreExtractor(text).run()["high"].get("vara_trabalho")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_vara_numerada_simples():
    assert _vara("1ª Vara do Trabalho de São Paulo") == "1ª Vara do Trabalho de São Paulo"


def test_vara_sem_numero():
    assert _vara("Vara do Trabalho de Ribeirão Preto") == "Vara do Trabalho de Ribeirão Preto"


def test_vara_com_juizo():
    assert _vara("Juízo da 5ª Vara do Trabalho de Fortaleza") == "5ª Vara do Trabalho de Fortaleza"


def test_vara_10a():
    assert _vara("10ª Vara do Trabalho de Salvador") == "10ª Vara do Trabalho de Salvador"


def test_vara_perante():
    assert _vara("tramita perante a 2ª Vara do Trabalho de Natal") == "2ª Vara do Trabalho de Natal"


# ---------------------------------------------------------------------------
# GAP 1 — ALL CAPS (split("de") é case-sensitive)
# ---------------------------------------------------------------------------

def test_vara_all_caps():
    """ALL CAPS — 'DE' maiúsculo não é encontrado por split case-sensitive."""
    assert _vara("VARA DO TRABALHO DE RECIFE") == "VARA DO TRABALHO DE RECIFE"


def test_vara_all_caps_numerada():
    assert _vara("3ª VARA DO TRABALHO DE MANAUS") == "3ª VARA DO TRABALHO DE MANAUS"


# ---------------------------------------------------------------------------
# GAP 2 — sufixo '/UF' deve ser aparado
# ---------------------------------------------------------------------------

def test_vara_sufixo_barra_uf():
    assert _vara("4ª Vara do Trabalho de Belo Horizonte/MG") == "4ª Vara do Trabalho de Belo Horizonte"


def test_vara_sufixo_barra_uf_brasilia():
    assert _vara("Vara do Trabalho de Brasília/DF") == "Vara do Trabalho de Brasília"


# ---------------------------------------------------------------------------
# GAP 3 — sufixo '- UF' deve ser aparado
# ---------------------------------------------------------------------------

def test_vara_sufixo_traco_uf():
    assert _vara("1ª Vara do Trabalho de São Paulo - SP") == "1ª Vara do Trabalho de São Paulo"


def test_vara_sufixo_traco_uf_sem_espaco():
    assert _vara("2ª Vara do Trabalho de Curitiba-PR") == "2ª Vara do Trabalho de Curitiba"


# ---------------------------------------------------------------------------
# Sem contexto / falsos positivos
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _vara("O reclamante foi admitido em 2020.") is None


# ---------------------------------------------------------------------------
# GAP 4 — sigla VT (com e sem ordinal)
# ---------------------------------------------------------------------------

def test_ordinal_vt_de_cidade():
    """1a VT de Sao Paulo — sigla sem acento"""
    assert _vara("1a VT de Sao Paulo") == "1a VT de Sao Paulo"

def test_ordinal_vt_com_acento():
    """3ª VT de Campinas"""
    assert _vara("3ª VT de Campinas") == "3ª VT de Campinas"

def test_vt_sem_ordinal():
    """VT de Ribeirao Preto — sem número"""
    assert _vara("VT de Ribeirao Preto") == "VT de Ribeirao Preto"

def test_vt_ordinal_cidade_uf():
    """3a VT de Campinas/SP — UF aparado"""
    assert _vara("3a VT de Campinas/SP") == "3a VT de Campinas"


# ---------------------------------------------------------------------------
# GAP 5 — "Vara Trabalhista" (alias de Vara do Trabalho)
# ---------------------------------------------------------------------------

def test_vara_trabalhista_numerada():
    """2a Vara Trabalhista de Fortaleza"""
    assert _vara("2a Vara Trabalhista de Fortaleza") == "2a Vara Trabalhista de Fortaleza"

def test_vara_trabalhista_com_juizo():
    """Juizo da 5a Vara Trabalhista de Belo Horizonte"""
    assert _vara("Juizo da 5a Vara Trabalhista de Belo Horizonte") == "5a Vara Trabalhista de Belo Horizonte"

def test_juizo_trabalhista_de_cidade():
    """Juizo Trabalhista de Sao Paulo"""
    assert _vara("Juizo Trabalhista de Sao Paulo") == "Juizo Trabalhista de Sao Paulo"


# ---------------------------------------------------------------------------
# GAP 6 — cidade com apenas 2 caracteres (sigla como 'BH')
# ---------------------------------------------------------------------------

def test_vara_cidade_bh():
    """'5ª Vara do Trabalho de BH' — cidade com 2 chars (mínimo era 3)."""
    assert _vara("5a Vara do Trabalho de BH") == "5a Vara do Trabalho de BH"

def test_vara_cidade_bh_no_contexto():
    """Contexto completo com 'Central de Mandados da'."""
    v = _vara("Central de Mandados da 5a Vara do Trabalho de BH")
    assert v == "5a Vara do Trabalho de BH"

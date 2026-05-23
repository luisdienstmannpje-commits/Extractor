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

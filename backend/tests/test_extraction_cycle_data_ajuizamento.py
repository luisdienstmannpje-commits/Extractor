"""
Ciclo TDD — data_ajuizamento (MEDIUM data dd/mm/aaaa)
Gaps principais:
  1. 'ajuizada/ajuizado em' — verbo ajuizar (f/m) não estava no padrão
  2. 'recebida em' — petição recebida pelo cartório
"""
import pytest
from services.pre_extractor import PreExtractor


def _aj(text: str):
    return PreExtractor(text).run()["medium"].get("data_ajuizamento")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_distribuida_em():
    assert _aj("distribuída em 15/06/2021") == "15/06/2021"


def test_proposta_em():
    assert _aj("proposta em 01/01/2023") == "01/01/2023"


def test_data_de_ajuizamento_colon():
    assert _aj("data de ajuizamento: 05/05/2020") == "05/05/2020"


def test_protocolo_em():
    assert _aj("protocolo em 03/03/2021") == "03/03/2021"


# ---------------------------------------------------------------------------
# GAPS — ajuizada / ajuizado
# ---------------------------------------------------------------------------

def test_ajuizada_em():
    """'ajuizada em' — forma feminina ('ação ajuizada em')."""
    assert _aj("ação trabalhista ajuizada em 10/03/2022") == "10/03/2022"


def test_ajuizado_em():
    """'ajuizado em' — forma masculina."""
    assert _aj("o processo foi ajuizado em 20/07/2019") == "20/07/2019"


# ---------------------------------------------------------------------------
# GAPS — recebida em
# ---------------------------------------------------------------------------

def test_recebida_em():
    """'recebida em' — petição recebida pelo sistema."""
    assert _aj("petição inicial recebida em 12/12/2022") == "12/12/2022"


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _aj("O reclamante trabalhou por 3 anos.") is None


# ---------------------------------------------------------------------------
# GAP — 'data de distribuição: DD/MM/AAAA' / 'distribuição: DD/MM/AAAA'
# ---------------------------------------------------------------------------

def test_data_de_distribuicao_colon():
    """'data de distribuição: DD/MM/AAAA' — substantivo, não particípio."""
    assert _aj("data de distribuição: 15/03/2023") == "15/03/2023"

def test_distribuicao_colon():
    """'distribuição: DD/MM/AAAA' — rótulo direto."""
    assert _aj("distribuição: 10/04/2022") == "10/04/2022"

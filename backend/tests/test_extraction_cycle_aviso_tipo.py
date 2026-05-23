"""
Ciclo TDD — aviso_previo_tipo (HIGH string: 'indenizado' | 'trabalhado')
Gaps principais:
  1. 'aviso previo: indenizado' — colon-label
  2. 'aviso previo pago em dinheiro' — locução equivalente a indenizado
  3. 'aviso previo dispensado de cumprir' — dispensado = indenizado
"""
import pytest
from services.pre_extractor import PreExtractor


def _tipo(text: str):
    return PreExtractor(text).run()["high"].get("aviso_previo_tipo")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_indenizado_direto():
    assert _tipo("aviso prévio indenizado de 30 dias") == "indenizado"


def test_trabalhado_direto():
    assert _tipo("aviso prévio trabalhado") == "trabalhado"


def test_indenizado_sem_acento():
    assert _tipo("aviso previo indenizado") == "indenizado"


def test_trabalhado_sem_acento():
    assert _tipo("aviso previo trabalhado") == "trabalhado"


def test_indenizacao_substitutiva():
    assert _tipo("indenização substitutiva do aviso prévio") == "indenizado"


def test_projecao_indenizado():
    assert _tipo("projeção do aviso previo indenizado") == "indenizado"


# ---------------------------------------------------------------------------
# GAPS — indenizado: formas alternativas
# ---------------------------------------------------------------------------

def test_colon_indenizado():
    """'aviso previo: indenizado' — colon seguido de rótulo."""
    assert _tipo("aviso previo: indenizado") == "indenizado"


def test_pago_em_dinheiro():
    """'pago em dinheiro' equivale a indenizado."""
    assert _tipo("aviso prévio pago em dinheiro ao empregado") == "indenizado"


def test_dispensado_de_cumprir():
    """'dispensado de cumprir' — não precisou trabalhar o aviso = indenizado."""
    assert _tipo("aviso prévio dispensado de cumprir") == "indenizado"


# ---------------------------------------------------------------------------
# Prioridade — indenizado > trabalhado
# ---------------------------------------------------------------------------

def test_indenizado_prevalece():
    txt = "aviso prévio indenizado — histórico trabalhado anteriormente"
    assert _tipo(txt) == "indenizado"


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _tipo("O reclamante foi admitido em 2020.") is None

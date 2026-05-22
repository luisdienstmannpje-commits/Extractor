"""
Ciclo TDD — aviso_previo_dias (MEDIUM)
Gaps: label-colon e dias entre parênteses.
"""
import pytest
from services.pre_extractor import PreExtractor


def _med(text: str):
    return PreExtractor(text).run()["medium"].get("aviso_previo_dias")


# ---------------------------------------------------------------------------
# Padrões já cobertos (smoke)
# ---------------------------------------------------------------------------

def test_aviso_de_30_dias():
    assert _med("aviso prévio de 30 dias") == "30 dias"


def test_aviso_indenizado_30():
    assert _med("aviso prévio indenizado de 30 dias") == "30 dias"


def test_aviso_trabalhado_30():
    assert _med("aviso prévio trabalhado de 30 dias") == "30 dias"


def test_aviso_invertido():
    assert _med("30 dias de aviso prévio") == "30 dias"


def test_aviso_proporcional_45():
    assert _med("aviso prévio proporcional de 45 dias") == "45 dias"


def test_aviso_60_dias():
    assert _med("projeção do aviso prévio de 60 dias") == "60 dias"


def test_aviso_extenso_entre_parenteses():
    """'aviso prévio de 30 (trinta) dias' — extenso após número."""
    assert _med("aviso prévio de 30 (trinta) dias") == "30 dias"


# ---------------------------------------------------------------------------
# GAPS NOVOS
# ---------------------------------------------------------------------------

def test_aviso_label_colon():
    """'aviso prévio: 30 dias' — colon sem 'de'."""
    assert _med("aviso prévio: 30 dias") == "30 dias"


def test_aviso_indenizado_entre_parenteses():
    """'aviso prévio indenizado (60 dias)' — número dentro dos parênteses."""
    assert _med("aviso prévio indenizado (60 dias)") == "60 dias"


def test_aviso_colon_indenizado():
    """'aviso prévio indenizado: 45 dias'."""
    assert _med("aviso prévio indenizado: 45 dias") == "45 dias"


# ---------------------------------------------------------------------------
# Plausibilidade — fora do range 20-90 deve ser ignorado
# ---------------------------------------------------------------------------

def test_aviso_1_dia_ignorado():
    assert _med("aviso prévio de 1 dia") is None


def test_aviso_200_dias_ignorado():
    assert _med("aviso prévio de 200 dias") is None


def test_sem_contexto_nao_extrai():
    assert _med("O autor foi dispensado sem justa causa.") is None

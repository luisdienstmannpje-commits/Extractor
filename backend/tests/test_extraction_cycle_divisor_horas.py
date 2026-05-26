"""
Ciclo TDD — divisor_horas (MEDIUM)
Gaps: label-colon, variante "44h semanais", divisor 175.
"""
import pytest
from services.pre_extractor import PreExtractor


def _med(text: str):
    return PreExtractor(text).run()["medium"].get("divisor_horas")


# ---------------------------------------------------------------------------
# Padrões já cobertos (smoke)
# ---------------------------------------------------------------------------

def test_divisor_220():
    assert _med("divisor de 220") == "220"


def test_divisor_150():
    assert _med("utilizando o divisor 150") == "150"


def test_divisor_180():
    assert _med("divisor 180 aplicado") == "180"


def test_divisor_200():
    assert _med("divisor 200") == "200"


def test_inferencia_44h_semanais():
    assert _med("jornada de 44 horas semanais") == "220"


def test_inferencia_40h_semanais():
    assert _med("40 horas semanais") == "200"


def test_inferencia_36h_semanais():
    assert _med("36 horas semanais") == "180"


# ---------------------------------------------------------------------------
# GAPS NOVOS
# ---------------------------------------------------------------------------

def test_divisor_label_colon():
    """'divisor: 220' — colon sem 'de'."""
    assert _med("divisor: 220") == "220"


def test_divisor_horas_label_colon():
    """'Divisor de horas: 220' — label completo com colon."""
    assert _med("Divisor de horas: 220") == "220"


def test_divisor_175():
    """175 = 35 horas semanais — estava ausente do _RE_DIVISOR."""
    assert _med("divisor de 175") == "175"


def test_inferencia_35h_semanais():
    """35 horas semanais → divisor 175."""
    assert _med("35 horas semanais") == "175"


def test_inferencia_44h_compacto():
    """'44h semanais' (sem espaço entre número e h)."""
    assert _med("jornada de 44h semanais") == "220"


def test_inferencia_30h_compacto():
    """'30h semanais' (sem espaço)."""
    assert _med("30h semanais") == "150"


# ---------------------------------------------------------------------------
# Não extrai sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _med("O reclamante trabalhou por 3 anos.") is None


# ---------------------------------------------------------------------------
# GAP — 'módulo de N horas' como sinônimo de divisor
# ---------------------------------------------------------------------------

def test_modulo_220():
    """'módulo de 220 horas' — sinônimo de divisor usado em algumas sentenças."""
    assert _med("adotar o módulo de 220 horas mensais") == "220"

def test_modulo_200():
    assert _med("módulo de 200 horas para o cálculo") == "200"

def test_modulo_colon():
    """'módulo: 220' — label com colon."""
    assert _med("módulo: 220") == "220"


def test_numero_isolado_nao_extrai():
    """Número avulso 220 sem prefixo de divisor."""
    assert _med("O processo nº 220 foi autuado.") is None


# ---------------------------------------------------------------------------
# GAP — 12x36 e jornada semanal invertida
# ---------------------------------------------------------------------------

def test_12x36_regime():
    """jornada 12x36 -> divisor 220"""
    assert _med("jornada de 12x36") == "220"

def test_12_por_36():
    assert _med("regime de 12 por 36 horas") == "220"

def test_jornada_semanal_44h():
    """jornada semanal de 44 horas (numero antes de horas)"""
    assert _med("jornada semanal de 44 horas") == "220"

def test_jornada_semanal_40h():
    assert _med("jornada semanal de 40 horas") == "200"

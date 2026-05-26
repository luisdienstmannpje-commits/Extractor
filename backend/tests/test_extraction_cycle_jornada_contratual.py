"""
Ciclo TDD — jornada_contratual (MEDIUM string)
Nota: o extractor retorna o texto capturado como está.
Gaps principais:
  1. 'jornada semanal de 44 horas' — 'semanal' entre trigger e número
  2. 'carga semanal de 44 horas' — 'semanal' em vez de 'horária' em carga
  3. 'trabalhava/trabalhou X horas por dia' — trigger ausente + 'por dia' como variante
"""
import pytest
from services.pre_extractor import PreExtractor


def _jc(text: str):
    return PreExtractor(text).run()["medium"].get("jornada_contratual")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_jornada_diarias():
    v = _jc("jornada de 8 horas diárias")
    assert v is not None and "8" in v


def test_jornada_diarias_e_semanais():
    v = _jc("jornada de trabalho de 8h diárias e 44h semanais")
    assert v is not None and "8" in v and "44" in v


def test_carga_horaria_semanais():
    v = _jc("carga horária de 40h semanais")
    assert v is not None and "40" in v


def test_jornada_de_semanais():
    v = _jc("jornada de 44 horas semanais")
    assert v is not None and "44" in v


# ---------------------------------------------------------------------------
# GAP 1 — 'jornada semanal de X horas'
# ---------------------------------------------------------------------------

def test_jornada_semanal_horas():
    v = _jc("jornada semanal de 44 horas")
    assert v is not None and "44" in v


def test_jornada_semanal_h():
    v = _jc("cumpria jornada semanal de 44h")
    assert v is not None and "44" in v


# ---------------------------------------------------------------------------
# GAP 2 — 'carga semanal de X horas'
# ---------------------------------------------------------------------------

def test_carga_semanal():
    v = _jc("carga semanal de 44 horas")
    assert v is not None and "44" in v


def test_carga_horaria_semanal():
    """'carga horária semanal de 40h' — combinação dos dois modificadores."""
    v = _jc("carga horária semanal de 40 horas")
    assert v is not None and "40" in v


# ---------------------------------------------------------------------------
# GAP 3 — 'trabalhava/trabalhou X horas por dia'
# ---------------------------------------------------------------------------

def test_trabalhava_por_dia():
    v = _jc("trabalhava 8 horas por dia")
    assert v is not None and "8" in v


def test_trabalhou_por_dia_e_semanais():
    v = _jc("trabalhou 6h por dia, 36h semanais")
    assert v is not None and "6" in v


def test_trabalhou_diarias():
    """'trabalhou' como trigger (passado perfeito — comum em reclamações)."""
    v = _jc("trabalhou 6 horas diárias")
    assert v is not None and "6" in v


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _jc("O reclamante foi admitido em 2020.") is None


# ---------------------------------------------------------------------------
# GAP — 'jornada diária de X horas' (adjetivo 'diária' entre trigger e valor)
# ---------------------------------------------------------------------------

def test_jornada_diaria_de_h():
    """'jornada diária de 8 horas' — adjetivo 'diária' não coberto."""
    v = _jc("jornada diária de 8 horas")
    assert v is not None and "8" in v

def test_jornada_diaria_sem_acento():
    v = _jc("jornada diaria de 6h")
    assert v is not None and "6" in v


# ---------------------------------------------------------------------------
# GAP — 'jornada de trabalho: X' (colon antes do valor)
# ---------------------------------------------------------------------------

def test_jornada_trabalho_colon():
    """'jornada de trabalho: 8h diárias' — colon separa trigger do valor."""
    v = _jc("jornada de trabalho: 8h diárias")
    assert v is not None and "8" in v

def test_carga_horaria_colon():
    v = _jc("carga horária: 44h semanais")
    assert v is not None and "44" in v

"""
Ciclo TDD — horario_trabalho (MEDIUM string)
Nota: o extractor retorna o texto capturado como está (sem normalizar para "HHhMM").
Gaps principais:
  1. 'trabalhava de 07:30 às 16:30' — 'de' não coberto (só 'das?')
  2. 'horário de trabalho: 08h às 17h' — sem artigo das/de antes do horário
  3. 'Entrada: 08h00 Saída: 17h00' — formato Entrada/Saída sem cobertura
"""
import pytest
from services.pre_extractor import PreExtractor


def _ht(text: str):
    return PreExtractor(text).run()["medium"].get("horario_trabalho")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_horario_das_h():
    assert _ht("horário das 9h às 18h") is not None


def test_trabalhava_das():
    assert _ht("trabalhava das 07h30 às 17h30") is not None


def test_horario_de_trabalho_das():
    v = _ht("horário de trabalho: das 08:00 às 17:00")
    assert v is not None and "08" in v and "17" in v


def test_laborava_das():
    v = _ht("laborava das 08:00 às 17:00")
    assert v is not None and "08" in v


def test_jornada_das():
    v = _ht("jornada das 09h às 18h")
    assert v is not None and "09" in v


# ---------------------------------------------------------------------------
# GAP 1 — 'de HH' como início (artigo 'de' em vez de 'das')
# ---------------------------------------------------------------------------

def test_trabalhava_de_colon():
    v = _ht("trabalhava de 07:30 às 16:30")
    assert v is not None and "07" in v and "16" in v


def test_jornada_de_h():
    v = _ht("jornada de 08h às 17h")
    assert v is not None and "08" in v and "17" in v


# ---------------------------------------------------------------------------
# GAP 2 — sem artigo (tempo direto após trigger)
# ---------------------------------------------------------------------------

def test_horario_sem_das():
    """'horário de trabalho: 08h às 17h' — sem 'das' antes do número."""
    v = _ht("horário de trabalho: 08h às 17h")
    assert v is not None and "08" in v and "17" in v


def test_laborava_sem_das():
    v = _ht("laborava 08h00 às 17h00 de segunda a sexta")
    assert v is not None and "08" in v


# ---------------------------------------------------------------------------
# GAP 3 — formato Entrada/Saída
# ---------------------------------------------------------------------------

def test_entrada_saida_h():
    v = _ht("Entrada: 08h00 Saída: 17h00")
    assert v is not None and "08" in v and "17" in v


def test_entrada_saida_colon():
    v = _ht("Entrada: 08:00 Saída: 17:00")
    assert v is not None and "08" in v and "17" in v


def test_entrada_saida_sem_dois_pontos():
    v = _ht("Entrada 08h00 Saída 17h00")
    assert v is not None and "08" in v and "17" in v


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _ht("O reclamante foi admitido em 2020.") is None


# ---------------------------------------------------------------------------
# GAP — 'horário: HH às HH' (sem 'de trabalho', colon direto)
# ---------------------------------------------------------------------------

def test_horario_colon_direto():
    """'horário: 07h30 às 17h30' — colon imediatamente após horário."""
    v = _ht("horário: 07h30 às 17h30")
    assert v is not None and "07" in v and "17" in v

def test_horario_colon_sem_acento():
    v = _ht("horario: 08:00 às 17:00")
    assert v is not None and "08" in v and "17" in v


# ---------------------------------------------------------------------------
# GAP — 'expediente das X às Y'
# ---------------------------------------------------------------------------

def test_expediente_das():
    """'expediente' como trigger de horário."""
    v = _ht("expediente das 8h às 18h")
    assert v is not None and "8" in v and "18" in v

def test_expediente_de():
    v = _ht("expediente de 09h às 18h")
    assert v is not None and "09" in v


# ---------------------------------------------------------------------------
# GAP — 'Entrada: HH e Saída: HH' (com 'e' entre as partes)
# ---------------------------------------------------------------------------

def test_entrada_saida_com_e():
    """'Entrada: 06h00 e Saída: 14h00' — 'e' entre entrada e saída."""
    v = _ht("Entrada: 06h00 e Saída: 14h00")
    assert v is not None and "06" in v and "14" in v


# ---------------------------------------------------------------------------
# GAP — 'jornada: HH às HH' (colon direto após 'jornada')
# ---------------------------------------------------------------------------

def test_jornada_colon_direto():
    """'jornada: 07h30 as 16h30' — colon logo após 'jornada'."""
    v = _ht("jornada: 07h30 as 16h30")
    assert v is not None and "07" in v and "16" in v

def test_jornada_colon_formato_hhmm():
    v = _ht("jornada: 08:00 às 17:00")
    assert v is not None and "08" in v and "17" in v

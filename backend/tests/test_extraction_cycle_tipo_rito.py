"""
Ciclo TDD — tipo_rito (HIGH string)
Gaps principais:
  1. 'rito sumario' / 'sumarissimo' sem acento — não bate em sumar[ií]ssimo
  2. 'processo ordinario' — prefixo 'processo' não coberto
  3. 'rito comum ordinário' — adjetivo 'comum' interposto bloqueia o match
"""
import pytest
from services.pre_extractor import PreExtractor


def _rito(text: str):
    return PreExtractor(text).run()["high"].get("tipo_rito")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_rito_sumarissimo():
    assert _rito("rito sumaríssimo") == "Sumaríssimo"


def test_procedimento_sumarissimo():
    assert _rito("procedimento sumaríssimo conforme CLT") == "Sumaríssimo"


def test_sumarissimo_standalone():
    assert _rito("sumaríssimo conforme art. 852-A da CLT") == "Sumaríssimo"


def test_rito_ordinario():
    assert _rito("rito ordinário") == "Ordinário"


def test_procedimento_ordinario():
    assert _rito("procedimento ordinário") == "Ordinário"


def test_ordinario_sem_acento():
    """'rito ordinario' sem acento — [aá] já cobre."""
    assert _rito("rito ordinario") == "Ordinário"


# ---------------------------------------------------------------------------
# GAPS — Sumaríssimo sem acento / variante 'sumário'
# ---------------------------------------------------------------------------

def test_rito_sumario_sem_acento():
    """'rito sumario' (OCR strip) — deve mapear para Sumaríssimo."""
    assert _rito("rito sumario") == "Sumaríssimo"


def test_sumarissimo_sem_acento_ss():
    """'sumarissimo' — sem acento no í, mantém ss."""
    assert _rito("processo tramita pelo rito sumarissimo") == "Sumaríssimo"


def test_procedimento_sumario():
    assert _rito("procedimento sumário") == "Sumaríssimo"


# ---------------------------------------------------------------------------
# GAPS — Ordinário com prefixo alternativo
# ---------------------------------------------------------------------------

def test_processo_ordinario():
    """'processo ordinário' — prefixo 'processo' não estava coberto."""
    assert _rito("processo ordinário") == "Ordinário"


def test_processo_ordinario_sem_acento():
    assert _rito("processo ordinario") == "Ordinário"


def test_rito_comum_ordinario():
    """'rito comum ordinário' — adjetivo 'comum' interposto."""
    assert _rito("rito comum ordinário") == "Ordinário"


def test_rito_comum_ordinario_sem_acento():
    assert _rito("rito comum ordinario") == "Ordinário"


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _rito("O reclamante foi admitido em 2020.") is None


# ---------------------------------------------------------------------------
# GAP — label com colon "Rito: Ordinário" / "Rito: Sumaríssimo"
# ---------------------------------------------------------------------------

def test_rito_label_colon_ordinario():
    assert _rito("Rito: Ordinario") == "Ordinário"

def test_rito_label_colon_sumarissimo():
    assert _rito("Rito: Sumarissimo") == "Sumaríssimo"

def test_rito_label_hifen_ordinario():
    assert _rito("Rito - Ordinario") == "Ordinário"

"""
Ciclo TDD — juiz_responsavel (HIGH string)
Gaps principais:
  1. 'Magistrado: Dr. Nome' — rótulo 'Magistrado' não estava no padrão
  2. 'Juiz(a) do Trabalho: Dra. Nome' — parêntese em Juiz(a) bloqueava o match
  3. 'pelo Juiz Dr. Nome' — ausência de dois-pontos/traço após rótulo
"""
import pytest
from services.pre_extractor import PreExtractor


def _juiz(text: str):
    return PreExtractor(text).run()["high"].get("juiz_responsavel")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_juiz_do_trabalho_dr():
    assert _juiz("Juiz do Trabalho: Dr. João Silva") == "João Silva"


def test_juiza_do_trabalho_dra():
    assert _juiz("Juíza do Trabalho: Dra. Maria Santos") == "Maria Santos"


def test_mm_juiz():
    assert _juiz("MM. Juiz do Trabalho: Carlos Oliveira") == "Carlos Oliveira"


def test_juiz_titular():
    assert _juiz("Juiz Titular: Dr. Paulo Lima") == "Paulo Lima"


def test_juiz_substituto():
    assert _juiz("Juiz Substituto: Ana Costa") == "Ana Costa"


def test_juiz_label_simples():
    assert _juiz("Juiz: Dr. Roberto Alves") == "Roberto Alves"


def test_all_caps():
    assert _juiz("JUIZ DO TRABALHO: DR. ANTONIO SILVA") == "ANTONIO SILVA"


# ---------------------------------------------------------------------------
# GAP 1 — 'Magistrado'
# ---------------------------------------------------------------------------

def test_magistrado_dr():
    assert _juiz("Magistrado: Dr. Henrique Porto") == "Henrique Porto"


def test_magistrada_dra():
    assert _juiz("Magistrada: Dra. Cristina Faria") == "Cristina Faria"


# ---------------------------------------------------------------------------
# GAP 2 — 'Juiz(a)' com parênteses
# ---------------------------------------------------------------------------

def test_juiz_parentese_a():
    assert _juiz("Juiz(a) do Trabalho: Dra. Patrícia Ramos") == "Patrícia Ramos"


def test_mm_juiza_substituta():
    assert _juiz("MM. Juíza Substituta: Dra. Luciana Melo") == "Luciana Melo"


# ---------------------------------------------------------------------------
# GAP 3 — 'pelo Juiz Dr.' sem dois-pontos
# ---------------------------------------------------------------------------

def test_prolatada_pelo_juiz():
    assert _juiz("Prolatada pelo Juiz Dr. Marcos Nunes nesta data") == "Marcos Nunes"


def test_assinado_pela_juiza():
    assert _juiz("Assinado pela Juíza Dra. Sandra Lima") == "Sandra Lima"


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _juiz("O processo foi distribuído em 2023.") is None

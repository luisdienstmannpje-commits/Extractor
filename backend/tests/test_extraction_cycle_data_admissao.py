"""
Ciclo TDD — data_admissao (MEDIUM data DD/MM/AAAA)
Nota: o extractor retorna a data normalizada no formato DD/MM/AAAA.
Gaps principais:
  1. 'admissão: DD/MM/AAAA' — label com dois-pontos sem cobertura
  2. 'admitido na empresa em DD/MM/AAAA' — frase curta entre trigger e 'em'
  3. 'iniciou atividades em DD/MM/AAAA' — variante do trigger 'iniciou em'
"""
import pytest
from services.pre_extractor import PreExtractor


def _da(text: str):
    return PreExtractor(text).run()["medium"].get("data_admissao")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_admitido_em():
    assert _da("admitido em 01/03/2018") == "01/03/2018"


def test_admissao_em():
    assert _da("admissão em 15/06/2019") == "15/06/2019"


def test_contratado_em():
    assert _da("contratado em 10/01/2020") == "10/01/2020"


def test_inicio_contrato_em():
    assert _da("início do contrato em 05/05/2017") == "05/05/2017"


def test_data_de_admissao_label():
    assert _da("data de admissão: 20/02/2016") == "20/02/2016"


def test_admitido_extenso():
    assert _da("admitido em 10 de março de 2015") == "10/03/2015"


# ---------------------------------------------------------------------------
# GAP 1 — label 'admissão: DD/MM/AAAA' (sem 'em')
# ---------------------------------------------------------------------------

def test_admissao_colon():
    """'admissão: DD/MM/AAAA' — label direto sem 'em'."""
    assert _da("admissão: 01/03/2018") == "01/03/2018"


def test_admissao_label_maiusculo():
    assert _da("Admissão: 15/06/2019") == "15/06/2019"


# ---------------------------------------------------------------------------
# GAP 2 — 'admitido na empresa/no quadro em DD/MM/AAAA'
# ---------------------------------------------------------------------------

def test_admitido_na_empresa_em():
    """Frase curta entre 'admitido' e 'em' — comum em peças processuais."""
    assert _da("foi admitido na empresa em 01/03/2018") == "01/03/2018"


def test_admitido_no_quadro_em():
    assert _da("admitido no quadro em 10/01/2020") == "10/01/2020"


# ---------------------------------------------------------------------------
# GAP 3 — 'iniciou atividades/trabalho em DD/MM/AAAA'
# ---------------------------------------------------------------------------

def test_iniciou_atividades_em():
    """'iniciou atividades em' — 'iniciou em' já cobre só sem substantivo."""
    assert _da("iniciou atividades em 05/05/2017") == "05/05/2017"


def test_iniciou_trabalho_em():
    assert _da("iniciou o trabalho em 20/02/2016") == "20/02/2016"


# ---------------------------------------------------------------------------
# Sem contexto / sem data completa
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _da("O reclamante foi admitido em 2020.") is None


def test_data_incompleta_nao_extrai():
    """Ano apenas — não deve extrair."""
    assert _da("admitido em janeiro de 2020 sem data exata") is None

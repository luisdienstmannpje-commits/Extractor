"""
Ciclo TDD — data_admissao + data_demissao (MEDIUM)
Foco: gaps identificados — datas por extenso e verbos não cobertos.
"""
import pytest
from services.pre_extractor import PreExtractor


def _med(text: str, campo: str):
    return PreExtractor(text).run()["medium"].get(campo)


# ---------------------------------------------------------------------------
# data_admissao — padrões já cobertos (smoke — formato DD/MM/YYYY)
# ---------------------------------------------------------------------------

def test_admissao_admitido_em():
    assert _med("admitido em 15/01/2020", "data_admissao") == "15/01/2020"


def test_admissao_data_de_admissao():
    assert _med("data de admissão: 01/03/2019", "data_admissao") == "01/03/2019"


def test_admissao_contratado_em():
    assert _med("contratada em 10/10/2021 pelo regime CLT", "data_admissao") == "10/10/2021"


def test_admissao_inicio_do_contrato():
    assert _med("início do contrato em 05/05/2017", "data_admissao") == "05/05/2017"


# ---------------------------------------------------------------------------
# data_admissao — GAPS NOVOS
# ---------------------------------------------------------------------------

def test_admissao_iniciou_em():
    """Verbo 'iniciou em' não estava no padrão."""
    assert _med("iniciou em 15/01/2020", "data_admissao") == "15/01/2020"


def test_admissao_extenso():
    """'admitido em 15 de janeiro de 2020' — data por extenso."""
    assert _med("admitido em 15 de janeiro de 2020", "data_admissao") == "15/01/2020"


def test_admissao_extenso_contratado():
    """'contratado em 10 de março de 2019' — extenso + verbo alternativo."""
    assert _med("contratado em 10 de março de 2019", "data_admissao") == "10/03/2019"


# ---------------------------------------------------------------------------
# data_admissao — não extrai sem contexto
# ---------------------------------------------------------------------------

def test_admissao_sem_contexto():
    assert _med("O autor trabalhou por três anos.", "data_admissao") is None


def test_admissao_a_partir_de_nao_extrai():
    assert _med("vigente a partir de 01/01/2024", "data_admissao") is None


# ---------------------------------------------------------------------------
# data_demissao — padrões já cobertos (smoke)
# ---------------------------------------------------------------------------

def test_demissao_dispensado_em():
    assert _med("dispensado em 30/06/2023", "data_demissao") == "30/06/2023"


def test_demissao_data_da_rescisao():
    assert _med("data da rescisão: 15/12/2022", "data_demissao") == "15/12/2022"


def test_demissao_desligado_em():
    assert _med("desligado em 01/03/2024 da empresa", "data_demissao") == "01/03/2024"


def test_demissao_rescisao_em():
    assert _med("rescisão em 30/06/2023", "data_demissao") == "30/06/2023"


# ---------------------------------------------------------------------------
# data_demissao — GAPS NOVOS
# ---------------------------------------------------------------------------

def test_demissao_rescindido_em():
    """Verbo 'rescindido em' não estava no padrão."""
    assert _med("foi rescindido em 30/06/2023", "data_demissao") == "30/06/2023"


def test_demissao_extenso():
    """'dispensado em 30 de junho de 2023' — data por extenso."""
    assert _med("dispensado em 30 de junho de 2023", "data_demissao") == "30/06/2023"


def test_demissao_extenso_desligado():
    """'desligado em 15 de dezembro de 2022' — extenso + verbo alternativo."""
    assert _med("desligado em 15 de dezembro de 2022", "data_demissao") == "15/12/2022"


# ---------------------------------------------------------------------------
# data_demissao — não extrai sem contexto
# ---------------------------------------------------------------------------

def test_demissao_sem_contexto():
    assert _med("O prazo prescricional é de 2 anos.", "data_demissao") is None

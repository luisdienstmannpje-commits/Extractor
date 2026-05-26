"""
Ciclo TDD — data_sentenca (HIGH data dd/mm/aaaa)
Gaps principais: padrão dd/mm/aaaa com marcadores diretos de sentença não coberto
(só PJe, 'publicado em' e extenso "Cidade, DD de mês" existiam).
"""
import pytest
from services.pre_extractor import PreExtractor


def _ds(text: str):
    return PreExtractor(text).run()["high"].get("data_sentenca")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_publicada_em():
    assert _ds("publicada em 12/12/2022") == "12/12/2022"


def test_publicado_em():
    assert _ds("publicado em 05/05/2020") == "05/05/2020"


# ---------------------------------------------------------------------------
# GAPS — marcadores de sentença + dd/mm/aaaa
# ---------------------------------------------------------------------------

def test_sentenca_proferida_em():
    assert _ds("sentença proferida em 10/03/2023") == "10/03/2023"


def test_sentenca_de():
    """'sentença de DD/MM/AAAA' — forma compacta."""
    assert _ds("sentença de 15/06/2021") == "15/06/2021"


def test_julgado_em():
    assert _ds("julgado em 01/01/2022") == "01/01/2022"


def test_julgada_em():
    assert _ds("ação julgada em 30/09/2023") == "30/09/2023"


def test_data_da_sentenca_colon():
    assert _ds("data da sentença: 05/05/2020") == "05/05/2020"


def test_decisao_proferida_em():
    assert _ds("decisão proferida em 20/07/2019") == "20/07/2019"


def test_prolacao_sentenca_em():
    assert _ds("prolação da sentença em 08/08/2023") == "08/08/2023"


def test_sentenciado_em():
    assert _ds("sentenciado em 22/04/2022") == "22/04/2022"


def test_sentenca_datada_de():
    assert _ds("sentença datada de 03/03/2021") == "03/03/2021"


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _ds("O reclamante foi admitido em 2020.") is None


# ---------------------------------------------------------------------------
# GAP — prolatada em / sentenca label / decidida em
# ---------------------------------------------------------------------------

def test_prolatada_em():
    assert _ds("prolatada em 15/03/2024") == "15/03/2024"

def test_sentenca_label_colon():
    assert _ds("Sentenca: 20/05/2023") == "20/05/2023"

def test_decidida_em():
    assert _ds("decidida em 22/11/2022") == "22/11/2022"

def test_prolatado_em_masculino():
    assert _ds("prolatado em 08/08/2023") == "08/08/2023"

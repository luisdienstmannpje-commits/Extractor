"""
Ciclo TDD — indice_correcao + juros_mora (MEDIUM)
indice_correcao: cobertura verificada (ADC58 > IPCA+SELIC > IPCA > SELIC > TR).
juros_mora: gap label-colon "juros: 1% ao mês".
"""
import pytest
from services.pre_extractor import PreExtractor


def _med(text: str, campo: str):
    return PreExtractor(text).run()["medium"].get(campo)


# ---------------------------------------------------------------------------
# indice_correcao — smoke (todos devem passar já)
# ---------------------------------------------------------------------------

def test_ic_adc58_prioritario():
    v = _med("correção conforme ADC 58 do STF", "indice_correcao")
    assert v is not None and "ADC 58" in v


def test_ic_ipca_e_selic():
    v = _med("IPCA-E pré-judicial e SELIC pós-ajuizamento", "indice_correcao")
    assert v is not None and "IPCA" in v.upper() and "SELIC" in v


def test_ic_apenas_ipca():
    assert _med("correção pelo IPCA-E", "indice_correcao") == "IPCA-E"


def test_ic_apenas_selic():
    assert _med("correção pela SELIC", "indice_correcao") == "SELIC"


def test_ic_apenas_tr():
    assert _med("atualização pela TR", "indice_correcao") == "TR"


def test_ic_label_colon_ipca():
    assert _med("índice de correção: IPCA-E", "indice_correcao") == "IPCA-E"


def test_ic_sem_indice_nao_extrai():
    assert _med("O reclamante foi admitido em 2020.", "indice_correcao") is None


# ---------------------------------------------------------------------------
# juros_mora — smoke
# ---------------------------------------------------------------------------

def test_jm_selic():
    assert _med("juros de mora pela SELIC", "juros_mora") == "SELIC"


def test_jm_um_porcento():
    assert _med("juros de mora de 1% ao mês", "juros_mora") == "1% ao mês"


def test_jm_legais():
    assert _med("juros legais", "juros_mora") == "Juros legais"


def test_jm_sem_contexto_nao_extrai():
    assert _med("O processo foi distribuído em 2023.", "juros_mora") is None


# ---------------------------------------------------------------------------
# juros_mora — GAP NOVO
# ---------------------------------------------------------------------------

def test_jm_colon_um_porcento():
    """'juros: 1% ao mês' — colon sem 'de mora'."""
    assert _med("juros: 1% ao mês", "juros_mora") == "1% ao mês"


def test_jm_mora_um_porcento_sem_de():
    """'juros mora de 1%' — sem 'de' entre 'juros' e 'mora'."""
    assert _med("juros mora de 1% ao mês", "juros_mora") == "1% ao mês"


# ---------------------------------------------------------------------------
# GAP — INPC e IPCA simples (sem -E)
# ---------------------------------------------------------------------------

def test_ic_inpc():
    assert _med("correcao pelo INPC", "indice_correcao") == "INPC"

def test_ic_inpc_atualizacao():
    assert _med("atualizacao monetaria pelo INPC", "indice_correcao") == "INPC"

def test_ic_ipca_simples():
    """IPCA sem o sufixo -E deve ser reconhecido como IPCA-E"""
    assert _med("correcao monetaria: IPCA", "indice_correcao") == "IPCA-E"

def test_ic_ipca_label():
    assert _med("indice: IPCA", "indice_correcao") == "IPCA-E"

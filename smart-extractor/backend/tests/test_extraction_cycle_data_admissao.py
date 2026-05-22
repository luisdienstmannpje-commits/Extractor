"""Ciclo de extração incremental — dado-alvo: data_admissao (pre_extractor MEDIUM)."""

from services.pre_extractor import pre_extract


def test_data_admissao_admitido_em():
    texto = "O reclamante foi admitido em 01/03/2018 para a função de operador."

    r = pre_extract(texto)

    assert r["medium"]["data_admissao"] == "01/03/2018"
    assert "data_admissao" not in r["high"]


def test_data_admissao_data_de_admissao_rotulo():
    texto = """
    --- PAGINA 2 ---
    Data de admissão: 15/01/2019
    """

    r = pre_extract(texto)

    assert r["medium"]["data_admissao"] == "15/01/2019"


def test_data_admissao_data_da_admissao_rotulo():
    texto = "Data da admissão: 22/06/2020"

    r = pre_extract(texto)

    assert r["medium"]["data_admissao"] == "22/06/2020"


def test_data_admissao_admissao_dois_pontos_sem_em():
    texto = "Qualificação. Admissão: 10/11/2017. Cargo: auxiliar."

    r = pre_extract(texto)

    assert r["medium"]["data_admissao"] == "10/11/2017"


def test_data_admissao_contratada_em():
    texto = "A autora foi contratada em 05/04/2021 pela reclamada."

    r = pre_extract(texto)

    assert r["medium"]["data_admissao"] == "05/04/2021"


def test_data_admissao_ingressou_em():
    texto = "Ingressou em 30/12/2015 no quadro de funcionários."

    r = pre_extract(texto)

    assert r["medium"]["data_admissao"] == "30/12/2015"


def test_data_admissao_a_partir_de():
    texto = "Vínculo a partir de 01/08/2016, conforme CTPS."

    r = pre_extract(texto)

    assert r["medium"]["data_admissao"] == "01/08/2016"


def test_data_admissao_ausente():
    texto = "Discussão sobre horas extras sem menção de data de vínculo."

    r = pre_extract(texto)

    assert "data_admissao" not in r["medium"]

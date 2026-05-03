"""Ciclo de extração incremental — dado-alvo: data_demissao (pre_extractor MEDIUM)."""

from services.pre_extractor import pre_extract


def test_data_demissao_demitido_em():
    texto = "O reclamante foi demitido em 30/06/2022 sem justa causa."

    r = pre_extract(texto)

    assert r["medium"]["data_demissao"] == "30/06/2022"
    assert "data_demissao" not in r["high"]


def test_data_demissao_data_de_demissao_rotulo():
    texto = """
    --- PAGINA 2 ---
    Data de demissão: 15/03/2023
    """

    r = pre_extract(texto)

    assert r["medium"]["data_demissao"] == "15/03/2023"


def test_data_demissao_data_da_demissao_rotulo():
    texto = "Data da demissão: 01/12/2021"

    r = pre_extract(texto)

    assert r["medium"]["data_demissao"] == "01/12/2021"


def test_data_demissao_demissao_dois_pontos_sem_em():
    texto = "Qualificação. Demissão: 10/08/2020. Aviso prévio indenizado."

    r = pre_extract(texto)

    assert r["medium"]["data_demissao"] == "10/08/2020"


def test_data_demissao_rescisao_dois_pontos():
    texto = "Rescisão: 05/05/2019. Encerramento do vínculo."

    r = pre_extract(texto)

    assert r["medium"]["data_demissao"] == "05/05/2019"


def test_data_demissao_data_da_rescisao():
    texto = "Data da rescisão: 22/04/2024"

    r = pre_extract(texto)

    assert r["medium"]["data_demissao"] == "22/04/2024"


def test_data_demissao_desligada_em():
    texto = "A autora foi desligada em 11/11/2018."

    r = pre_extract(texto)

    assert r["medium"]["data_demissao"] == "11/11/2018"


def test_data_demissao_ausente():
    texto = "Discussão sobre intervalo intrajornada sem datas de saída."

    r = pre_extract(texto)

    assert "data_demissao" not in r["medium"]

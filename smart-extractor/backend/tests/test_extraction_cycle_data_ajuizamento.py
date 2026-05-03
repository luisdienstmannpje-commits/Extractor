"""Ciclo de extração incremental — dado-alvo: data_ajuizamento (pre_extractor MEDIUM)."""

from services.pre_extractor import pre_extract


def test_data_ajuizamento_rotulo_data_de_ajuizamento():
    texto = """
    --- PAGINA 1 ---
    Data de ajuizamento: 15/03/2024
    """

    r = pre_extract(texto)

    assert r["medium"]["data_ajuizamento"] == "15/03/2024"
    assert "data_ajuizamento" not in r["high"]


def test_data_ajuizamento_data_da_autuacao_pje():
    """PJe costuma usar 'Data da Autuação' na capa — alinhado ao merge do processor."""
    texto = """
    --- PAGINA 1 ---
    Data da Autuação: 20/01/2023
    Processo: 0001234-56.2023.5.02.0001
    """

    r = pre_extract(texto)

    assert r["medium"]["data_ajuizamento"] == "20/01/2023"


def test_data_ajuizamento_distribuida_em():
    texto = "A presente reclamação foi distribuída em 10/05/2022 ao juízo."

    r = pre_extract(texto)

    assert r["medium"]["data_ajuizamento"] == "10/05/2022"


def test_data_ajuizamento_distribuida_sem_acento():
    texto = "Distribuida em 08/11/2021 para esta vara."

    r = pre_extract(texto)

    assert r["medium"]["data_ajuizamento"] == "08/11/2021"


def test_data_ajuizamento_protocolou_em():
    texto = "O autor protocolou em 01/02/2025 a petição inicial."

    r = pre_extract(texto)

    assert r["medium"]["data_ajuizamento"] == "01/02/2025"


def test_data_ajuizamento_protocolou_a_presente_em():
    texto = "Protocolou a presente em 03/04/2024 nos autos."

    r = pre_extract(texto)

    assert r["medium"]["data_ajuizamento"] == "03/04/2024"


def test_data_ajuizamento_ausente_sem_rotulo():
    texto = "Petição inicial sem menção de datas de autuação ou distribuição."

    r = pre_extract(texto)

    assert "data_ajuizamento" not in r["medium"]

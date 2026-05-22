"""Ciclo de extração incremental — dado-alvo: data_sentenca (pre_extractor HIGH)."""

from services.pre_extractor import pre_extract


def test_data_sentenca_assinado_eletronicamente():
    texto = """
    --- PAGINA 5 ---
    Assinado eletronicamente em 12/08/2024
    Fulano de Tal — Juiz do Trabalho
    """

    r = pre_extract(texto)

    assert r["high"]["data_sentenca"] == "12/08/2024"


def test_data_sentenca_assinado_digitalmente():
    texto = "Assinado digitalmente em 03/11/2023 pelo sistema PJe."

    r = pre_extract(texto)

    assert r["high"]["data_sentenca"] == "03/11/2023"


def test_data_sentenca_varias_assinaturas_usa_data_mais_recente():
    texto = """
    Assinado eletronicamente em 05/06/2024
    ...
    Assinado eletronicamente em 18/06/2024
    """

    r = pre_extract(texto)

    assert r["high"]["data_sentenca"] == "18/06/2024"


def test_data_sentenca_data_julgamento_quando_sem_assinado():
    texto = """
    Acórdão
    Data do Julgamento: 01/09/2023
    Relator: Desembargador X
    """

    r = pre_extract(texto)

    assert r["high"]["data_sentenca"] == "01/09/2023"


def test_data_sentenca_prioridade_assinado_sobre_data_julgamento():
    texto = """
    Data do Julgamento: 01/01/2025
    Assinado eletronicamente em 10/01/2025
    """

    r = pre_extract(texto)

    assert r["high"]["data_sentenca"] == "10/01/2025"


def test_data_sentenca_publicado_em_fallback():
    texto = "Certidão de publicação. Publicado em 05/06/2022 no Diário."

    r = pre_extract(texto)

    assert r["high"]["data_sentenca"] == "05/06/2022"


def test_data_sentenca_extenso_fallback():
    texto = """
    Brasília, 20 de abril de 2025
    """

    r = pre_extract(texto)

    assert r["high"]["data_sentenca"] == "20/04/2025"


def test_data_sentenca_ausente():
    texto = "Petição sem datas de julgamento ou assinatura no formato esperado."

    r = pre_extract(texto)

    assert "data_sentenca" not in r["high"]


def test_data_sentenca_em_high_nao_em_medium():
    texto = "Assinado eletronicamente em 01/01/2024"

    r = pre_extract(texto)

    assert r["high"]["data_sentenca"] == "01/01/2024"
    assert "data_sentenca" not in r["medium"]

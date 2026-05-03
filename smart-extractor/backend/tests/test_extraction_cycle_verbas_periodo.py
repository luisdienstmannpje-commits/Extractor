"""Ciclo incremental — verbas_deferidas[].periodo (fase 2: só mesma linha da verba, dispositivo)."""

from services.pre_extractor import pre_extract


def test_periodo_de_a_na_mesma_linha():
    texto = """
    DISPOSITIVO
    Defiro horas extras de 01/03/2020 a 15/12/2022.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    he = next(i for i in itens if "horas" in i["nome"].lower())
    assert he.get("periodo") == "01/03/2020 a 15/12/2022"


def test_periodo_entre_e_na_mesma_linha():
    texto = """
    DISPOSITIVO
    Concedo intervalo intrajornada entre 10/05/2021 e 30/11/2023.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    iv = next(i for i in itens if "intervalo" in i["nome"].lower())
    assert iv.get("periodo") == "10/05/2021 a 30/11/2023"


def test_periodo_traco_na_mesma_linha():
    texto = """
    DISPOSITIVO
    Defiro férias 01/01/2019 – 31/12/2019 acrescidas de 1/3.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    fer = next(i for i in itens if "férias" in i["nome"].lower())
    assert fer.get("periodo") == "01/01/2019 a 31/12/2019"


def test_periodo_em_outra_linha_nao_vincula():
    """Intervalo só na linha anterior à verba — não inferir período para a verba."""
    texto = """
    DISPOSITIVO
    No período de 01/01/2019 a 31/12/2023 o autor laborou ininterruptamente.
    Defiro horas extras.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    he = next(i for i in itens if "horas" in i["nome"].lower())
    assert "periodo" not in he


def test_sem_marcador_dispositivo_nao_preenche_itens():
    texto = "Menciono horas extras de 01/01/2020 a 02/02/2020 sem seção dispositivo."

    r = pre_extract(texto)

    assert "verbas_deferidas_itens" not in r["medium"]
    assert "verbas_deferidas_nomes" not in r["medium"]


def test_duas_verbas_so_uma_linha_tem_intervalo():
    texto = """
    DISPOSITIVO
    Defiro FGTS sobre verbas deferidas.
    Defiro adicional noturno de 01/06/2020 a 31/05/2021.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    fgts = next(i for i in itens if "fgts" in i["nome"].lower().replace(".", ""))
    assert "periodo" not in fgts
    ad = next(i for i in itens if "noturno" in i["nome"].lower())
    assert ad.get("periodo") == "01/06/2020 a 31/05/2021"


def test_itens_alinhados_a_nomes_e_ordem_primeira_ocorrencia():
    texto = """
    DISPOSITIVO
    Defiro aviso prévio indenizado.
    Homologo horas extras de 02/02/2022 a 03/03/2023.
    """

    r = pre_extract(texto)

    nomes = r["medium"]["verbas_deferidas_nomes"]
    itens = r["medium"]["verbas_deferidas_itens"]
    assert [i["nome"] for i in itens] == nomes


def test_data_invalida_nao_gera_periodo():
    texto = """
    DISPOSITIVO
    Defiro horas extras de 99/99/2020 a 15/12/2022.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    he = next(i for i in itens if "horas" in i["nome"].lower())
    assert "periodo" not in he

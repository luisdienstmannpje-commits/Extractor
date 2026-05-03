"""Ciclo incremental — verbas_deferidas[].reflexos (fase 3: mesma linha ou continuação imediata no dispositivo)."""

from services.pre_extractor import pre_extract


def test_reflexos_explicitos_mesma_linha():
    texto = """
    DISPOSITIVO
    Defiro horas extras com reflexos em DSR e férias.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    he = next(i for i in itens if "horas" in i["nome"].lower())
    assert he.get("reflexos") == ["DSR", "Férias"]


def test_reflexo_singular_incidencia():
    texto = """
    DISPOSITIVO
    Homologo adicional noturno com incidência em 13º salário.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    ad = next(i for i in itens if "noturno" in i["nome"].lower())
    assert ad.get("reflexos") == ["13º salário"]


def test_sem_gatilho_reflexo_nao_preenche():
    """Mencionar outra verba alvo na linha sem 'reflexo/incidência' não basta."""
    texto = """
    DISPOSITIVO
    Defiro horas extras e férias.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    he = next(i for i in itens if "horas" in i["nome"].lower())
    assert "reflexos" not in he


def test_reflexo_linha_seguinte_com_continuacao():
    texto = """
    DISPOSITIVO
    Defiro horas extras
    com reflexos em DSR.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    he = next(i for i in itens if "horas" in i["nome"].lower())
    assert he.get("reflexos") == ["DSR"]


def test_frase_encerrada_nao_puxa_proxima_linha():
    texto = """
    DISPOSITIVO
    Defiro horas extras.
    Com reflexos em DSR.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    he = next(i for i in itens if "horas" in i["nome"].lower())
    assert "reflexos" not in he


def test_sem_marcador_dispositivo():
    texto = "Reflexos em DSR sobre horas extras sem seção dispositivo."

    r = pre_extract(texto)

    assert "verbas_deferidas_itens" not in r["medium"]


def test_ferias_com_terco_canonico():
    texto = """
    DISPOSITIVO
    Defiro intervalo intrajornada com reflexos em férias acrescidas de 1/3.
    """

    r = pre_extract(texto)

    itens = r["medium"]["verbas_deferidas_itens"]
    iv = next(i for i in itens if "intervalo" in i["nome"].lower())
    assert iv.get("reflexos") == ["Férias acrescidas de 1/3"]

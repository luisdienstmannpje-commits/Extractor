"""Ciclo de extração incremental — verbas_deferidas[].nome (fase 1: só nomes no dispositivo)."""

from services.pre_extractor import pre_extract


def test_verbas_extraidas_somente_do_dispositivo():
    """Menção a 'horas extras' só na fundamentação; no dispositivo outra verba."""
    texto = """
    A fundamentação trata de horas extras e art. 59 da CLT.
    --- PAGINA 3 ---
    DISPOSITIVO

    Defiro o pagamento de férias acrescidas de 1/3.
    Concedo aviso prévio indenizado.
    """

    r = pre_extract(texto)

    nomes = r["medium"]["verbas_deferidas_nomes"]
    assert "férias" in [x.lower() for x in nomes]
    assert "horas extras" not in [x.lower() for x in nomes]
    assert any("aviso" in x.lower() and "prévio" in x.lower() for x in nomes)


def test_verbas_deduplicadas_mesmo_dispositivo():
    texto = """
    DISPOSITIVO
    Defiro horas extras.
    Homologo horas extras conforme laudo.
    """

    r = pre_extract(texto)

    nomes = r["medium"]["verbas_deferidas_nomes"]
    assert len([x for x in nomes if "horas extras" in x.lower()]) == 1


def test_fallback_isto_posto_sem_titulo_dispositivo():
    texto = """
    ISTO POSTO, julgo procedente em parte.
    Defiro intervalo intrajornada não concedido.
    """

    r = pre_extract(texto)

    nomes = r["medium"]["verbas_deferidas_nomes"]
    assert any("intervalo" in x.lower() for x in nomes)


def test_sem_marcador_dispositivo_nao_preenche():
    texto = "O autor pleiteia apenas danos morais, sem seção de decisão marcada."

    r = pre_extract(texto)

    assert "verbas_deferidas_nomes" not in r["medium"]


def test_dispositivo_sem_padrao_de_verba_conhecido():
    texto = """
    DISPOSITIVO
    Julgo improcedentes os pedidos.
    """

    r = pre_extract(texto)

    assert "verbas_deferidas_nomes" not in r["medium"]


def test_verbas_nomes_fica_em_medium_nao_high():
    texto = """
    DISPOSITIVO
    Defiro FGTS.
    """

    r = pre_extract(texto)

    assert "verbas_deferidas_nomes" in r["medium"]
    assert "verbas_deferidas_nomes" not in r["high"]

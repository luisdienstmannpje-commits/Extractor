"""
Ciclo TDD: multa_diaria e multa_limite em obrigacoes_fazer de seguro-desemprego.
Seguro CD/SD e alvará/guias agora suportam o mesmo hookup de astreintes que CTPS e guias rescisórias.
"""
from services.pre_extractor import pre_extract


def test_seguro_cd_sd_com_multa_diaria():
    texto = (
        "A reclamada deverá entregar as guias CD/SD para habilitação no seguro-desemprego, "
        "sob pena de multa diaria de R$ 200,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["tipo"] == "seguro_desemprego"
    assert obrigacoes[0]["multa_diaria"] == "R$ 200,00"


def test_seguro_cd_sd_com_multa_diaria_e_limite():
    texto = (
        "Determino a entrega das guias CD/SD do seguro-desemprego, "
        "sob pena de astreintes de R$ 150,00 por dia, limitada a R$ 4.500,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["tipo"] == "seguro_desemprego"
    assert obrigacoes[0]["multa_diaria"] == "R$ 150,00"
    assert obrigacoes[0]["multa_limite"] == "R$ 4.500,00"


def test_seguro_alvara_com_multa_diaria():
    texto = (
        "Expeça-se alvará para habilitação no seguro-desemprego, "
        "sob pena de multa diaria de R$ 300,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["tipo"] == "seguro_desemprego"
    assert obrigacoes[0]["multa_diaria"] == "R$ 300,00"


def test_seguro_alvara_com_multa_diaria_e_limite():
    texto = (
        "Expeça-se alvará para habilitação no seguro-desemprego, "
        "sob pena de multa de R$ 100,00 por dia, nao podendo exceder R$ 3.000,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["tipo"] == "seguro_desemprego"
    assert obrigacoes[0]["multa_diaria"] == "R$ 100,00"
    assert obrigacoes[0]["multa_limite"] == "R$ 3.000,00"


def test_seguro_sem_multa_nao_altera_item():
    """Item sem multa no fragmento deve continuar sem multa_diaria/multa_limite."""
    texto = "A reclamada deverá entregar as guias CD/SD para habilitação no seguro-desemprego."
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert "multa_diaria" not in obrigacoes[0]
    assert "multa_limite" not in obrigacoes[0]

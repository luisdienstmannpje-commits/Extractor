"""
Ciclo TDD: prazo_dias em obrigacoes_fazer de seguro-desemprego.
Paridade com CTPS: CD/SD e alvará recebem prazo_dias quando expresso no fragmento.
"""
from services.pre_extractor import pre_extract


def test_seguro_cd_sd_com_prazo_dias():
    texto = (
        "A reclamada deverá entregar as guias CD/SD para habilitação no seguro-desemprego "
        "no prazo de 10 dias."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["tipo"] == "seguro_desemprego"
    assert obrigacoes[0]["prazo_dias"] == "10 dias"


def test_seguro_alvara_com_prazo_dias():
    texto = (
        "Expeça-se alvará para habilitação no seguro-desemprego "
        "no prazo de 5 dias."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["tipo"] == "seguro_desemprego"
    assert obrigacoes[0]["prazo_dias"] == "5 dias"


def test_seguro_cd_sd_prazo_e_multa_juntos():
    texto = (
        "Determino entregar guias CD/SD do seguro-desemprego no prazo de 8 dias, "
        "sob pena de multa diaria de R$ 200,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    item = obrigacoes[0]
    assert item["prazo_dias"] == "8 dias"
    assert item["multa_diaria"] == "R$ 200,00"


def test_seguro_sem_prazo_nao_preenche_campo():
    texto = "A reclamada deverá entregar as guias CD/SD para habilitação no seguro-desemprego."
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert "prazo_dias" not in obrigacoes[0]


def test_seguro_prazo_fora_do_limite_ignorado():
    """Prazo de 200 dias está fora do limite plausível (1–120) e não deve ser extraído."""
    texto = (
        "A reclamada deverá entregar as guias CD/SD para habilitação no seguro-desemprego "
        "no prazo de 200 dias."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert "prazo_dias" not in obrigacoes[0]

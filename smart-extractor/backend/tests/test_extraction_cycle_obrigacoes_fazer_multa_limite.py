"""
Ciclo TDD: obrigacoes_fazer[].multa_limite
Teto da multa diária (astreintes), somente quando houver multa_diaria no mesmo fragmento.
"""
from services.pre_extractor import build_anchor_section, pre_extract


def test_ctps_multa_limite_limitada_a():
    texto = (
        "Determino a anotacao da CTPS com admissao em 01/02/2023, "
        "sob pena de multa diaria de R$ 100,00, limitada a R$ 3.000,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["multa_diaria"] == "R$ 100,00"
    assert obrigacoes[0]["multa_limite"] == "R$ 3.000,00"


def test_ctps_multa_limite_ate_o_limite_de():
    texto = (
        "A reclamada devera anotar a CTPS, sob pena de astreintes de R$ 200,00 por dia, "
        "ate o limite de R$ 6.000,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["multa_diaria"] == "R$ 200,00"
    assert obrigacoes[0]["multa_limite"] == "R$ 6.000,00"


def test_guias_multa_limite_nao_podendo_exceder():
    texto = (
        "Determino fornecer o TRCT ao reclamante, "
        "sob pena de multa diaria de R$ 150,00, "
        "nao podendo exceder R$ 4.500,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["tipo"] == "guias_rescisorias"
    assert obrigacoes[0]["multa_diaria"] == "R$ 150,00"
    assert obrigacoes[0]["multa_limite"] == "R$ 4.500,00"


def test_sem_multa_diaria_nao_extrai_limite():
    """Limite nao deve ser extraido se nao houver multa_diaria no mesmo fragmento."""
    texto = (
        "Determino a anotacao da CTPS com admissao em 01/02/2023, "
        "no prazo de 5 dias, limitada a R$ 3.000,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"].get("obrigacoes_fazer", [])
    for item in obrigacoes:
        assert "multa_limite" not in item


def test_limite_nao_captura_multa_art_477():
    """Valor da multa art. 477 nao deve virar multa_limite de obrigacao."""
    texto = (
        "Determino a anotacao da CTPS, sob pena de multa diaria de R$ 100,00. "
        "Defiro a multa do art. 477 da CLT."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert len(obrigacoes) == 1
    assert obrigacoes[0]["multa_diaria"] == "R$ 100,00"
    assert "multa_limite" not in obrigacoes[0]


def test_anchor_section_renderiza_limite():
    anchor = build_anchor_section(
        {
            "obrigacoes_fazer": [
                {
                    "tipo": "CTPS",
                    "descricao": "Anotar CTPS",
                    "multa_diaria": "R$ 100,00",
                    "multa_limite": "R$ 3.000,00",
                }
            ]
        }
    )
    assert "multa diaria: R$ 100,00" in anchor
    assert "limite: R$ 3.000,00" in anchor

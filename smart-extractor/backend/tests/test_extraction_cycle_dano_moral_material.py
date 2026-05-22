"""
Ciclo TDD: dano_moral e dano_material (pre_extractor MEDIUM).

Valores fixados a título de dano moral/material aparecem com padrões
altamente reconhecíveis: verbo de condenação + valor R$ + rótulo do dano.
Extraídos como MEDIUM para reduzir alucinação da IA nesses campos de alto risco.
"""
from services.pre_extractor import pre_extract


# ── dano_moral ────────────────────────────────────────────────────────────────

def test_dano_moral_condenacao_classica():
    texto = "Condeno a reclamada ao pagamento de R$ 5.000,00 a título de dano moral."
    result = pre_extract(texto)
    assert result["medium"].get("dano_moral") == "R$ 5.000,00"


def test_dano_moral_fixo_em():
    texto = "Fixo o dano moral em R$ 3.500,00."
    result = pre_extract(texto)
    assert result["medium"].get("dano_moral") == "R$ 3.500,00"


def test_dano_moral_indenizacao():
    texto = "Defiro indenização por dano moral no valor de R$ 10.000,00."
    result = pre_extract(texto)
    assert result["medium"].get("dano_moral") == "R$ 10.000,00"


def test_dano_moral_sem_rs_explicito():
    texto = "Condeno ao pagamento de dano moral no importe de 2.000,00 reais."
    result = pre_extract(texto)
    assert result["medium"].get("dano_moral") == "R$ 2.000,00"


def test_dano_moral_nao_extrai_sem_valor():
    """Menção a dano moral sem valor fixado não deve preencher o campo."""
    texto = "O reclamante pleiteia dano moral em razão do assédio sofrido."
    result = pre_extract(texto)
    assert "dano_moral" not in result["medium"]


def test_dano_moral_nao_extrai_de_pedido_narrativo():
    """'alega dano moral' sem verbo judicial de condenação não deve preencher."""
    texto = "O autor alega dano moral e requer R$ 50.000,00 a este título."
    result = pre_extract(texto)
    assert "dano_moral" not in result["medium"]


# ── dano_material ─────────────────────────────────────────────────────────────

def test_dano_material_condenacao():
    texto = "Condeno a reclamada ao pagamento de R$ 1.200,00 a título de dano material."
    result = pre_extract(texto)
    assert result["medium"].get("dano_material") == "R$ 1.200,00"


def test_dano_material_emergente():
    texto = "Defiro o dano emergente no valor de R$ 800,00."
    result = pre_extract(texto)
    assert result["medium"].get("dano_material") == "R$ 800,00"


def test_dano_material_lucros_cessantes():
    texto = "Condeno ao pagamento de R$ 4.500,00 a título de lucros cessantes."
    result = pre_extract(texto)
    assert result["medium"].get("dano_material") == "R$ 4.500,00"


def test_dano_material_nao_extrai_sem_valor():
    texto = "O reclamante pleiteia dano material emergente sem especificar o montante."
    result = pre_extract(texto)
    assert "dano_material" not in result["medium"]


# ── Coexistência moral + material ────────────────────────────────────────────

def test_moral_e_material_no_mesmo_texto():
    texto = (
        "Condeno a reclamada ao pagamento de R$ 5.000,00 a título de dano moral "
        "e R$ 1.500,00 a título de dano material."
    )
    result = pre_extract(texto)
    assert result["medium"].get("dano_moral") == "R$ 5.000,00"
    assert result["medium"].get("dano_material") == "R$ 1.500,00"


def test_anchor_section_renderiza_dano_moral():
    from services.pre_extractor import build_anchor_section
    texto = "Fixo o dano moral em R$ 7.000,00."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "dano_moral" in anchor.lower() or "moral" in anchor.lower()
    assert "7.000,00" in anchor

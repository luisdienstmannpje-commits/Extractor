"""
Ciclo TDD: multa_art_467 (pre_extractor MEDIUM).

Multa do art. 467 da CLT — 50% sobre verbas incontroversas nao pagas na rescisao.
Parceiro natural de multa_art_477 ja implementado. Mesmo contrato: "Deferida" / "Indeferida".
"""
from services.pre_extractor import pre_extract


def test_467_deferida_condeno():
    texto = "Condeno a reclamada ao pagamento da multa do art. 467 da CLT."
    result = pre_extract(texto)
    assert result["medium"].get("multa_art_467") == "Deferida"


def test_467_deferida_defiro():
    texto = "Defiro a multa prevista no art. 467 da CLT, no valor de 50% sobre as verbas incontroversas."
    result = pre_extract(texto)
    assert result["medium"].get("multa_art_467") == "Deferida"


def test_467_deferida_julgo_procedente():
    texto = "Julgo procedente o pedido de multa do art. 467 CLT."
    result = pre_extract(texto)
    assert result["medium"].get("multa_art_467") == "Deferida"


def test_467_indeferida():
    texto = "Indefiro o pedido de multa do art. 467 da CLT por ausencia de verbas incontroversas."
    result = pre_extract(texto)
    assert result["medium"].get("multa_art_467") == "Indeferida"


def test_467_improcedente():
    texto = "Julgo improcedente o pedido de multa prevista no art. 467 da CLT."
    result = pre_extract(texto)
    assert result["medium"].get("multa_art_467") == "Indeferida"


def test_467_nao_extrai_sem_mencao():
    """Texto sem art. 467 nao deve preencher o campo."""
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "multa_art_467" not in result["medium"]


def test_467_nao_confunde_com_477():
    """Mencao exclusiva ao art. 477 nao deve preencher multa_art_467."""
    texto = "Defiro a multa do art. 477 da CLT por atraso no pagamento rescisorio."
    result = pre_extract(texto)
    assert "multa_art_467" not in result["medium"]
    assert result["medium"].get("multa_art_477") == "Deferida"


def test_467_e_477_independentes():
    """Sentenca com ambos os artigos preenche os dois campos independentemente."""
    texto = (
        "Condeno a reclamada ao pagamento da multa do art. 467 da CLT. "
        "Defiro tambem a multa do art. 477 da CLT."
    )
    result = pre_extract(texto)
    assert result["medium"].get("multa_art_467") == "Deferida"
    assert result["medium"].get("multa_art_477") == "Deferida"

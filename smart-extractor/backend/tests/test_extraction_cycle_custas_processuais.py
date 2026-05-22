"""
Ciclo TDD: custas_processuais (pre_extractor MEDIUM).

Extrai quem paga as custas processuais e o valor base quando expresso.
Formato: "Reclamada" | "Reclamada, sobre R$ X,XX" | "Reclamante" | "Isencao reclamante".
"""
from services.pre_extractor import pre_extract


def test_custas_reclamada_basico():
    texto = "Condeno a reclamada ao pagamento das custas processuais."
    result = pre_extract(texto)
    assert result["medium"].get("custas_processuais") == "Reclamada"


def test_custas_pela_reclamada():
    texto = "Custas pela reclamada."
    result = pre_extract(texto)
    assert result["medium"].get("custas_processuais") == "Reclamada"


def test_custas_reclamada_calculadas_sobre():
    texto = "Custas pela reclamada, calculadas sobre R$ 5.000,00."
    result = pre_extract(texto)
    assert result["medium"].get("custas_processuais") == "Reclamada, sobre R$ 5.000,00"


def test_custas_reclamada_no_valor_de():
    texto = "Condeno ao pagamento das custas processuais, no valor de R$ 200,00."
    result = pre_extract(texto)
    val = result["medium"].get("custas_processuais", "")
    assert "Reclamada" in val or "200,00" in val


def test_custas_pelo_reu():
    """Reu/reclamado sao sinonimos de reclamada no contexto de custas."""
    texto = "Custas pelo reu."
    result = pre_extract(texto)
    assert result["medium"].get("custas_processuais") == "Reclamada"


def test_custas_reclamante():
    texto = "Custas pelo reclamante, dada a sucumbencia parcial."
    result = pre_extract(texto)
    assert result["medium"].get("custas_processuais") == "Reclamante"


def test_custas_isencao_gratuidade():
    texto = "Isento o reclamante do pagamento das custas processuais, nos termos da Lei 1.060/50."
    result = pre_extract(texto)
    val = result["medium"].get("custas_processuais", "")
    assert "sencao" in val.lower() or "isento" in val.lower() or "reclamante" in val.lower()


def test_custas_nao_extrai_sem_mencao():
    """Sentenca sem mencao a custas nao deve preencher o campo."""
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "custas_processuais" not in result["medium"]


def test_custas_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "Custas pela reclamada, calculadas sobre R$ 3.000,00."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "custas" in anchor.lower() or "3.000,00" in anchor

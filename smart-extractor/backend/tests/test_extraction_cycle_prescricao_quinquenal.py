"""
Ciclo TDD: prescricao_quinquenal (pre_extractor MEDIUM).

Resultado da prescricao quinquenal/bienal na sentenca.
Formatos esperados:
  "Acolhida"          — prescricao reconhecida (parcial ou total)
  "Afastada"          — prescricao rejeitada pelo juiz
  "Parcial"           — acolhida apenas para parte do periodo
"""
from services.pre_extractor import pre_extract


# ── Acolhida ──────────────────────────────────────────────────────────────────

def test_prescricao_acolho():
    texto = "Acolho a prescricao quinquenal arguida pela reclamada."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Acolhida"


def test_prescricao_declaro_prescrito():
    texto = "Declaro prescritos os creditos anteriores a 01/01/2018, nos termos do art. 7, XXIX, da CF."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Acolhida"


def test_prescricao_reconheco():
    texto = "Reconheco a prescricao quinquenal e excluo o periodo anterior a cinco anos do ajuizamento."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Acolhida"


def test_prescricao_pronuncio():
    texto = "Pronuncio a prescricao bienal das pretensoes anteriores ao termino do contrato."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Acolhida"


# ── Afastada ──────────────────────────────────────────────────────────────────

def test_prescricao_afasto():
    texto = "Afasto a prescricao quinquenal, pois o contrato ainda estava vigente."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Afastada"


def test_prescricao_rejeito():
    texto = "Rejeito a preliminar de prescricao arguida em defesa."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Afastada"


def test_prescricao_nao_acolho():
    texto = "Nao acolho a prescricao quinquenal, uma vez que o prazo nao decorreu."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Afastada"


# ── Parcial ───────────────────────────────────────────────────────────────────

def test_prescricao_parcial():
    texto = "Acolho parcialmente a prescricao quinquenal, limitando a condenacao aos ultimos cinco anos."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Parcial"


def test_prescricao_parcialmente_acolhida():
    texto = "A prescricao quinquenal e parcialmente acolhida quanto ao periodo anterior a 2017."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Parcial"


# ── Prioridade: Parcial > Acolhida ────────────────────────────────────────────

def test_prescricao_parcial_prevalece_sobre_acolhida():
    """'Acolho parcialmente' deve resultar em Parcial, nao Acolhida."""
    texto = "Acolho parcialmente a prescricao arguida pela reclamada, excluindo creditos anteriores a 2016."
    result = pre_extract(texto)
    assert result["medium"].get("prescricao_quinquenal") == "Parcial"


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_prescricao_nao_extrai_sem_mencao():
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "prescricao_quinquenal" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_prescricao_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "Acolho a prescricao quinquenal arguida pela reclamada."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "prescri" in anchor.lower() or "quinquenal" in anchor.lower()

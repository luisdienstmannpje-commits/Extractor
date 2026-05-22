"""
Ciclo TDD: jornada_contratual (pre_extractor MEDIUM).

Jornada contratual padrao reconhecida pelo juiz.
Formatos esperados (normalizados):
  "44h semanais"
  "8h diárias"
  "12x36"
  "6h diárias"
  "220h mensais"
  "40h semanais"
"""
from services.pre_extractor import pre_extract


# ── 44h semanais (padrao CLT) ─────────────────────────────────────────────────

def test_jornada_44h_semanais():
    texto = "Reconheco a jornada de 44 horas semanais contratada entre as partes."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "44h semanais"


def test_jornada_44h_abreviado():
    texto = "O reclamante laborava em jornada de 44h semanais."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "44h semanais"


def test_jornada_8h_diarias():
    texto = "A jornada contratual era de 8 horas diarias, de segunda a sexta-feira."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "8h diárias"


def test_jornada_8h_diarias_abreviado():
    texto = "Fixo a jornada em 8h diarias com base nos cartoes de ponto."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "8h diárias"


# ── 12x36 ────────────────────────────────────────────────────────────────────

def test_jornada_12x36():
    texto = "O reclamante cumpria escala 12x36, conforme clausula convencional."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "12x36"


def test_jornada_12_por_36():
    texto = "Reconheco a escala de 12 por 36 horas de trabalho."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "12x36"


# ── 6h diarias (telemarketing/bancarios) ─────────────────────────────────────

def test_jornada_6h_diarias():
    texto = "A jornada prevista em norma coletiva era de 6 horas diarias."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "6h diárias"


# ── 220h mensais ──────────────────────────────────────────────────────────────

def test_jornada_220h_mensais():
    texto = "O divisor aplicavel e 220, correspondente a jornada de 220 horas mensais."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "220h mensais"


# ── 40h semanais ──────────────────────────────────────────────────────────────

def test_jornada_40h_semanais():
    texto = "A jornada contratual era de 40 horas semanais, conforme contrato de trabalho."
    result = pre_extract(texto)
    assert result["medium"].get("jornada_contratual") == "40h semanais"


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_jornada_nao_extrai_sem_mencao():
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "jornada_contratual" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_jornada_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "Reconheco a jornada de 44h semanais."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "jornada" in anchor.lower() or "44h" in anchor.lower()

"""
Ciclo TDD: contribuicao_previdenciaria (pre_extractor MEDIUM).

Responsavel pelo recolhimento do INSS.
Formatos esperados:
  "Reclamada"                          — so cota patronal
  "Reclamante"                         — so cota do empregado (raro)
  "Ambas as partes"                    — cada qual recolhe a propria cota
  "Reclamada recolhe e desconta"       — patronal + desconto na fonte
  "Sem incidencia"                     — verba indenizatoria, sem INSS
"""
from services.pre_extractor import pre_extract


# ── Reclamada recolhe (cota patronal) ────────────────────────────────────────

def test_contrib_prev_reclamada_recolhe_cota_patronal():
    texto = "Condeno a reclamada ao recolhimento das contribuicoes previdenciarias, cota patronal."
    result = pre_extract(texto)
    assert result["medium"].get("contribuicao_previdenciaria") == "Reclamada"


def test_contrib_prev_reclamada_recolhe_inss():
    texto = "A reclamada devera recolher o INSS incidente sobre as verbas deferidas."
    result = pre_extract(texto)
    assert result["medium"].get("contribuicao_previdenciaria") == "Reclamada"


def test_contrib_prev_recolhimento_patronal():
    texto = "Determino o recolhimento da contribuicao previdenciaria patronal pela reclamada."
    result = pre_extract(texto)
    assert result["medium"].get("contribuicao_previdenciaria") == "Reclamada"


# ── Ambas as partes ───────────────────────────────────────────────────────────

def test_contrib_prev_ambas_as_partes():
    texto = "Cada parte devera recolher a sua cota de contribuicao previdenciaria."
    result = pre_extract(texto)
    assert result["medium"].get("contribuicao_previdenciaria") == "Ambas as partes"


def test_contrib_prev_ambas_cota_propria():
    texto = "As contribuicoes previdenciarias serao recolhidas por ambas as partes, cada qual sua cota."
    result = pre_extract(texto)
    assert result["medium"].get("contribuicao_previdenciaria") == "Ambas as partes"


# ── Reclamada recolhe e desconta do reclamante ───────────────────────────────

def test_contrib_prev_reclamada_recolhe_e_desconta():
    texto = (
        "A reclamada recolhera as contribuicoes previdenciarias, "
        "descontando a cota do empregado das verbas a pagar."
    )
    result = pre_extract(texto)
    val = result["medium"].get("contribuicao_previdenciaria", "")
    assert "Reclamada" in val


def test_contrib_prev_desconto_na_fonte():
    texto = (
        "Condeno a reclamada ao recolhimento do INSS, "
        "autorizando o desconto da parte do reclamante na fonte."
    )
    result = pre_extract(texto)
    val = result["medium"].get("contribuicao_previdenciaria", "")
    assert "Reclamada" in val


# ── Sem incidencia (verba indenizatoria) ─────────────────────────────────────

def test_contrib_prev_sem_incidencia():
    texto = "As verbas deferidas possuem natureza indenizatoria, sem incidencia de contribuicao previdenciaria."
    result = pre_extract(texto)
    assert result["medium"].get("contribuicao_previdenciaria") == "Sem incidencia"


def test_contrib_prev_sem_incidencia_inss():
    texto = "Indenizacao por danos morais — nao ha incidencia de INSS."
    result = pre_extract(texto)
    assert result["medium"].get("contribuicao_previdenciaria") == "Sem incidencia"


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_contrib_prev_nao_extrai_sem_mencao():
    """Sentenca sem mencao a INSS/contribuicao nao deve preencher o campo."""
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "contribuicao_previdenciaria" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_contrib_prev_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "A reclamada devera recolher o INSS sobre as verbas deferidas."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "previdenci" in anchor.lower() or "inss" in anchor.lower() or "contrib" in anchor.lower()

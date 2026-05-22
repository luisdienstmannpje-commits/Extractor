"""
Ciclo TDD: banco_horas_valido (pre_extractor MEDIUM).

Banco de horas reconhecido como valido (True) ou invalido (False) pelo juiz.
Campo bool — extraido como string "true"/"false" no MEDIUM dict
para compatibilidade com _set_medium, ou diretamente como bool.
"""
from services.pre_extractor import pre_extract


# ── Banco de horas INVALIDO (False) ──────────────────────────────────────────

def test_banco_horas_invalido_declaro():
    texto = "Declaro invalido o banco de horas, por ausencia de previsao em norma coletiva."
    result = pre_extract(texto)
    assert result["medium"].get("banco_horas_valido") is False


def test_banco_horas_invalido_nao_reconheco():
    texto = "Nao reconheco a validade do banco de horas instituido unilateralmente."
    result = pre_extract(texto)
    assert result["medium"].get("banco_horas_valido") is False


def test_banco_horas_invalido_irregular():
    texto = "O banco de horas e irregular, por nao estar previsto em ACT."
    result = pre_extract(texto)
    assert result["medium"].get("banco_horas_valido") is False


def test_banco_horas_invalido_nulo():
    texto = "Declaro nulo o banco de horas compensatorio firmado sem negociacao coletiva."
    result = pre_extract(texto)
    assert result["medium"].get("banco_horas_valido") is False


# ── Banco de horas VALIDO (True) ──────────────────────────────────────────────

def test_banco_horas_valido_reconheco():
    texto = "Reconheco a validade do banco de horas previsto em norma coletiva."
    result = pre_extract(texto)
    assert result["medium"].get("banco_horas_valido") is True


def test_banco_horas_valido_declaro():
    texto = "Declaro valido o banco de horas, nos termos da Sumula 85 do TST."
    result = pre_extract(texto)
    assert result["medium"].get("banco_horas_valido") is True


def test_banco_horas_valido_regular():
    texto = "O banco de horas e regular e foi devidamente ajustado por acordo coletivo."
    result = pre_extract(texto)
    assert result["medium"].get("banco_horas_valido") is True


# ── Prioridade: invalido prevalece ────────────────────────────────────────────

def test_banco_horas_invalido_prevalece():
    """Quando a sentenca descreve o banco mas o invalida, resultado e False."""
    texto = (
        "A reclamada alegou banco de horas valido, porem declaro invalido "
        "por falta de norma coletiva autorizadora."
    )
    result = pre_extract(texto)
    assert result["medium"].get("banco_horas_valido") is False


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_banco_horas_nao_extrai_sem_mencao():
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "banco_horas_valido" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_banco_horas_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "Declaro invalido o banco de horas."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "banco" in anchor.lower() or "horas" in anchor.lower()

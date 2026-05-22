"""
Ciclo TDD: cargo_confianca (pre_extractor MEDIUM).

Cargo de confianca reconhecido (True) ou afastado (False) pelo juiz.
Art. 62, II CLT — isenta de controle de jornada.
Campo bool.
"""
from services.pre_extractor import pre_extract


# ── Cargo de confianca RECONHECIDO (True) ─────────────────────────────────────

def test_cargo_confianca_reconheco():
    texto = "Reconheco o cargo de confianca do reclamante, nos termos do art. 62, II, da CLT."
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is True


def test_cargo_confianca_enquadrado():
    texto = "O reclamante exercia cargo de confianca, razao pela qual nao faz jus as horas extras."
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is True


def test_cargo_confianca_gerente():
    texto = "Reconheco que o autor exercia funcao de gerencia com poderes de mando e gestao."
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is True


def test_cargo_confianca_art62():
    texto = "O empregado se enquadra na excecao do art. 62, II, CLT, por exercer cargo de fidúcia."
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is True


# ── Cargo de confianca AFASTADO (False) ───────────────────────────────────────

def test_cargo_confianca_afasto():
    texto = "Afasto o enquadramento no art. 62, II, da CLT, pois o reclamante nao detinha poderes de gestao."
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is False


def test_cargo_confianca_nao_reconheco():
    texto = "Nao reconheco o cargo de confianca, uma vez que o autor nao tinha autonomia para admitir ou demitir."
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is False


def test_cargo_confianca_nao_comprovado():
    texto = "O cargo de confianca nao restou comprovado nos autos."
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is False


def test_cargo_confianca_afastado_diretamente():
    texto = "Afastado o cargo de confianca, defiro as horas extras pleiteadas."
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is False


# ── Prioridade: afastado prevalece ────────────────────────────────────────────

def test_cargo_confianca_afastado_prevalece():
    """Quando descrito mas depois afastado, resultado e False."""
    texto = (
        "A reclamada alega cargo de confianca, contudo nao reconheco tal enquadramento "
        "por ausencia de poderes de mando."
    )
    result = pre_extract(texto)
    assert result["medium"].get("cargo_confianca") is False


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_cargo_confianca_nao_extrai_sem_mencao():
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "cargo_confianca" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_cargo_confianca_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "Reconheco o cargo de confianca do reclamante."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "cargo" in anchor.lower() or "confian" in anchor.lower()

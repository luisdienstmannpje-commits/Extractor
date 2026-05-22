"""
Ciclo TDD: valor_causa (pre_extractor MEDIUM).

Valor da causa declarado no cabecalho ou dispositivo da sentenca.
Formatos esperados normalizados para "R$ X.XXX,XX".
"""
from services.pre_extractor import pre_extract


# ── Formatos de cabecalho ─────────────────────────────────────────────────────

def test_valor_causa_cabecalho_classico():
    texto = "Valor da causa: R$ 25.000,00."
    result = pre_extract(texto)
    assert result["medium"].get("valor_causa") == "R$ 25.000,00"


def test_valor_causa_cabecalho_sem_espaco():
    texto = "Valor da causa:R$10.500,00"
    result = pre_extract(texto)
    assert result["medium"].get("valor_causa") == "R$ 10.500,00"


def test_valor_causa_da_acao():
    texto = "Valor da acao: R$ 5.000,00."
    result = pre_extract(texto)
    assert result["medium"].get("valor_causa") == "R$ 5.000,00"


# ── Formatos em sentenca ──────────────────────────────────────────────────────

def test_valor_causa_atribuo():
    texto = "Atribuo a causa o valor de R$ 15.000,00."
    result = pre_extract(texto)
    assert result["medium"].get("valor_causa") == "R$ 15.000,00"


def test_valor_causa_fixo_em():
    texto = "Fixo o valor da causa em R$ 8.300,00 para fins de custas."
    result = pre_extract(texto)
    assert result["medium"].get("valor_causa") == "R$ 8.300,00"


def test_valor_causa_dado_a_causa():
    texto = "Dou a causa o valor de R$ 50.000,00."
    result = pre_extract(texto)
    assert result["medium"].get("valor_causa") == "R$ 50.000,00"


# ── Normalizacao monetaria ────────────────────────────────────────────────────

def test_valor_causa_sem_rs():
    texto = "Valor da causa: 3.200,00."
    result = pre_extract(texto)
    assert result["medium"].get("valor_causa") == "R$ 3.200,00"


def test_valor_causa_sem_ponto_milhar():
    texto = "Valor da causa: R$ 500,00."
    result = pre_extract(texto)
    assert result["medium"].get("valor_causa") == "R$ 500,00"


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_valor_causa_nao_extrai_sem_mencao():
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "valor_causa" not in result["medium"]


# ── Nao confunde com outros valores ──────────────────────────────────────────

def test_valor_causa_nao_confunde_com_condenacao():
    """Valor de condenacao nao deve preencher valor_causa."""
    texto = "Condeno a reclamada ao pagamento de R$ 12.000,00 a titulo de dano moral."
    result = pre_extract(texto)
    assert "valor_causa" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_valor_causa_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "Valor da causa: R$ 30.000,00."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "causa" in anchor.lower() or "30.000" in anchor

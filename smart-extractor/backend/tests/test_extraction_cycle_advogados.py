"""
Ciclo TDD: advogado_reclamante + advogado_reclamada (pre_extractor MEDIUM).

Nomes dos advogados extraidos do cabecalho da sentenca.
Formatos tipicos:
  "Advogado(s): Dr. Fulano de Tal - OAB/SP 123.456"
  "Adv. reclamante: Fulana da Silva (OAB/MG 78.901)"
  "Patrono: Dr. Jose Carlos Santos OAB/RJ 12345"
"""
from services.pre_extractor import pre_extract


# ── advogado_reclamante ───────────────────────────────────────────────────────

def test_adv_reclamante_classico():
    texto = "Advogado do reclamante: Dr. Carlos Eduardo Lima - OAB/SP 123.456"
    result = pre_extract(texto)
    val = result["medium"].get("advogado_reclamante", "")
    assert "Carlos Eduardo Lima" in val


def test_adv_reclamante_dr_oab():
    texto = "Adv. reclamante: Dr. Joao da Silva OAB/MG 78.901"
    result = pre_extract(texto)
    val = result["medium"].get("advogado_reclamante", "")
    assert "Joao da Silva" in val


def test_adv_reclamante_sem_dr():
    texto = "Advogado do autor: Maria Fernanda Costa OAB/RJ 11.222"
    result = pre_extract(texto)
    val = result["medium"].get("advogado_reclamante", "")
    assert "Maria Fernanda Costa" in val


def test_adv_reclamante_patrono():
    texto = "Patrono do reclamante: Ana Paula Rocha - OAB/PR 45.678"
    result = pre_extract(texto)
    val = result["medium"].get("advogado_reclamante", "")
    assert "Ana Paula Rocha" in val


# ── advogado_reclamada ────────────────────────────────────────────────────────

def test_adv_reclamada_classico():
    texto = "Advogado da reclamada: Dr. Pedro Henrique Souza - OAB/SP 654.321"
    result = pre_extract(texto)
    val = result["medium"].get("advogado_reclamada", "")
    assert "Pedro Henrique Souza" in val


def test_adv_reclamada_empresa():
    texto = "Adv. reclamada: Lucia Menezes OAB/RS 33.444"
    result = pre_extract(texto)
    val = result["medium"].get("advogado_reclamada", "")
    assert "Lucia Menezes" in val


def test_adv_reclamada_reu():
    texto = "Advogado do reu: Dr. Fernando Alves Costa - OAB/BA 99.000"
    result = pre_extract(texto)
    val = result["medium"].get("advogado_reclamada", "")
    assert "Fernando Alves Costa" in val


def test_adv_reclamada_patrono():
    texto = "Patrono da empresa: Roberto Lima OAB/GO 22.333"
    result = pre_extract(texto)
    val = result["medium"].get("advogado_reclamada", "")
    assert "Roberto Lima" in val


# ── Ambos no mesmo bloco ──────────────────────────────────────────────────────

def test_ambos_advogados_mesmo_texto():
    texto = (
        "Advogado do reclamante: Dr. Carlos Lima OAB/SP 11.111\n"
        "Advogado da reclamada: Dra. Silvia Torres OAB/SP 22.222"
    )
    result = pre_extract(texto)
    assert "Carlos Lima" in result["medium"].get("advogado_reclamante", "")
    assert "Silvia Torres" in result["medium"].get("advogado_reclamada", "")


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_adv_nao_extrai_sem_mencao():
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "advogado_reclamante" not in result["medium"]
    assert "advogado_reclamada" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_adv_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "Advogado do reclamante: Dr. Carlos Lima OAB/SP 11.111"
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "advogado" in anchor.lower() or "carlos" in anchor.lower()

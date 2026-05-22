"""
Ciclo TDD: ir_retido_fonte (pre_extractor MEDIUM).

Desconto do Imposto de Renda na fonte sobre as verbas deferidas.
Formatos esperados:
  "Reclamada desconta"       — empresa e responsavel pelo recolhimento/desconto
  "Sem incidencia"           — verbas indenizatorias, sem IR
  "Conforme tabela IRRF"     — remissao generica a tabela progressiva
"""
from services.pre_extractor import pre_extract


# ── Reclamada desconta / retem IR ─────────────────────────────────────────────

def test_ir_reclamada_desconta_na_fonte():
    texto = "A reclamada devera descontar o imposto de renda retido na fonte sobre as verbas tributaveis."
    result = pre_extract(texto)
    assert result["medium"].get("ir_retido_fonte") == "Reclamada desconta"


def test_ir_reclamada_reter():
    texto = "Condeno a reclamada a reter e recolher o IR sobre as verbas deferidas."
    result = pre_extract(texto)
    assert result["medium"].get("ir_retido_fonte") == "Reclamada desconta"


def test_ir_reclamada_recolher_irrf():
    texto = "A reclamada recolhera o IRRF incidente sobre as verbas de natureza salarial."
    result = pre_extract(texto)
    assert result["medium"].get("ir_retido_fonte") == "Reclamada desconta"


def test_ir_desconto_na_fonte_generico():
    texto = "Autorizo o desconto do imposto de renda na fonte das verbas tributaveis."
    result = pre_extract(texto)
    val = result["medium"].get("ir_retido_fonte", "")
    assert val != ""


# ── Sem incidencia ────────────────────────────────────────────────────────────

def test_ir_sem_incidencia_indenizatoria():
    texto = "As verbas possuem natureza indenizatoria, sem incidencia de imposto de renda."
    result = pre_extract(texto)
    assert result["medium"].get("ir_retido_fonte") == "Sem incidencia"


def test_ir_sem_incidencia_irrf():
    texto = "Indenizacao por danos morais — nao ha incidencia de IRRF."
    result = pre_extract(texto)
    assert result["medium"].get("ir_retido_fonte") == "Sem incidencia"


def test_ir_isento():
    texto = "O reclamante e isento de imposto de renda sobre as verbas rescisorioas."
    result = pre_extract(texto)
    assert result["medium"].get("ir_retido_fonte") == "Sem incidencia"


# ── Conforme tabela IRRF ──────────────────────────────────────────────────────

def test_ir_conforme_tabela():
    texto = "O imposto de renda sera calculado conforme a tabela progressiva do IRRF."
    result = pre_extract(texto)
    assert result["medium"].get("ir_retido_fonte") == "Conforme tabela IRRF"


def test_ir_tabela_progressiva():
    texto = "Incide IR na fonte, observada a tabela progressiva vigente."
    result = pre_extract(texto)
    assert result["medium"].get("ir_retido_fonte") == "Conforme tabela IRRF"


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_ir_nao_extrai_sem_mencao():
    """Sentenca sem mencao a IR/IRRF nao deve preencher o campo."""
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "ir_retido_fonte" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_ir_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "A reclamada devera descontar o IR retido na fonte sobre as verbas tributaveis."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "ir" in anchor.lower() or "imposto" in anchor.lower() or "irrf" in anchor.lower()

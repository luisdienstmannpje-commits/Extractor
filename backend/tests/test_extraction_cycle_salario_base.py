"""
Ciclo TDD — salario_base (MEDIUM)
Foco: formato de saída exato "R$ X.XXX,XX" + padrões não cobertos.
"""
import pytest
from services.pre_extractor import PreExtractor


def _med(text: str):
    return PreExtractor(text).run()["medium"].get("salario_base")


# ---------------------------------------------------------------------------
# Padrões básicos já cobertos — verificam FORMATO EXATO de saída
# ---------------------------------------------------------------------------

def test_formato_rs_pontovigula():
    """Saída deve ser 'R$ X.XXX,XX' (ponto milhar, vírgula decimal)."""
    v = _med("salário de R$ 3.500,00 mensais")
    assert v == "R$ 3.500,00"


def test_formato_valor_inteiro_milhar():
    v = _med("remuneração mensal de R$ 2.500,00")
    assert v == "R$ 2.500,00"


def test_formato_sem_milhar():
    """Valores abaixo de 1.000."""
    v = _med("salário de R$ 900,00 mensais")
    assert v == "R$ 900,00"


def test_salario_fixo_formato():
    v = _med("salário fixo de R$ 2.800,00 por mês")
    assert v == "R$ 2.800,00"


def test_salario_contratual():
    v = _med("salário contratual de R$ 1.980,00 mensais")
    assert v == "R$ 1.980,00"


def test_salario_normativo():
    v = _med("salário normativo de R$ 1.600,00")
    assert v == "R$ 1.600,00"


def test_piso_salarial():
    v = _med("piso salarial de R$ 1.412,00 mensais")
    assert v == "R$ 1.412,00"


def test_vencimento():
    v = _med("vencimento de R$ 4.200,00 mensais")
    assert v == "R$ 4.200,00"


def test_ultima_remuneracao():
    v = _med("última remuneração de R$ 3.200,00")
    assert v == "R$ 3.200,00"


def test_percebia_o_salario():
    v = _med("percebia o salário de R$ 2.000,00 mensais")
    assert v == "R$ 2.000,00"


# ---------------------------------------------------------------------------
# Padrões NOVOS — cobertura adicional
# ---------------------------------------------------------------------------

def test_salario_label_colon():
    """'Salário base: R$ 3.500,00' — padrão label:valor comum em peças."""
    v = _med("Salário base: R$ 3.500,00")
    assert v == "R$ 3.500,00"


def test_auferia_remuneracao():
    """'auferia remuneração de' — verbo ainda não coberto."""
    v = _med("auferia remuneração de R$ 2.200,00 mensais")
    assert v == "R$ 2.200,00"


def test_salario_mensal_liquido():
    v = _med("salário mensal líquido de R$ 1.800,00")
    assert v == "R$ 1.800,00"


# ---------------------------------------------------------------------------
# Filtros de plausibilidade
# ---------------------------------------------------------------------------

def test_abaixo_minimo_ignorado():
    assert _med("valor de R$ 100,00") is None


def test_acima_maximo_ignorado():
    assert _med("salário de R$ 200.000,00") is None


def test_sem_contexto_nao_extrai():
    assert _med("O reclamante foi dispensado sem justa causa em 30/06/2023.") is None


# ---------------------------------------------------------------------------
# Múltiplos valores — prioriza o mais frequente
# ---------------------------------------------------------------------------

def test_multiplos_escolhe_mais_frequente():
    texto = (
        "Salário de R$ 3.500,00 mensais. "
        "A empresa alegou remuneração de R$ 2.000,00. "
        "O juiz reconheceu salário de R$ 3.500,00. "
        "Base de cálculo: salário de R$ 3.500,00."
    )
    v = _med(texto)
    assert v == "R$ 3.500,00"


# ---------------------------------------------------------------------------
# GAP 1 — 'recebia a quantia/importância de R$ X'
# ---------------------------------------------------------------------------

def test_recebia_a_quantia():
    v = _med("recebia a quantia de R$ 1.800,00 mensais")
    assert v == "R$ 1.800,00"


def test_recebia_a_importancia():
    """'recebia a importância de' — só 'percebia' é coberto, não 'recebia'."""
    v = _med("recebia a importância de R$ 2.200,00")
    assert v == "R$ 2.200,00"


# ---------------------------------------------------------------------------
# GAP 2 — 'vencimentos de R$ X' (plural)
# ---------------------------------------------------------------------------

def test_vencimentos_plural():
    v = _med("vencimentos de R$ 4.500,00 mensais")
    assert v == "R$ 4.500,00"


def test_vencimentos_servidor():
    """Contexto servidor público — vencimentos mensais."""
    v = _med("percebia vencimentos de R$ 6.000,00 mensais")
    assert v == "R$ 6.000,00"


# ---------------------------------------------------------------------------
# GAP 3 — 'recebia mensalmente R$ X' (sem substantivo)
# ---------------------------------------------------------------------------

def test_recebia_mensalmente():
    v = _med("recebia mensalmente R$ 2.000,00")
    assert v == "R$ 2.000,00"


def test_recebia_mensalmente_valor():
    v = _med("recebia mensalmente o valor de R$ 3.200,00 brutos")
    assert v == "R$ 3.200,00"

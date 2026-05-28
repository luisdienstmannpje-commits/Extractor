"""
Ciclo TDD — justica_gratuita (HIGH bool)
Gaps principais:
  TRUE:  'gratuidade de justiça' (variante com 'de'), 'concedo', 'beneficiário'
  FALSE: 'indefiro' (verbo), 'gratuidade de justiça indeferida', 'revogo'
"""
import pytest
from services.pre_extractor import PreExtractor


def _jg(text: str):
    r = PreExtractor(text).run()
    v = r["high"].get("justica_gratuita")
    if v is None:
        v = r["medium"].get("justica_gratuita")
    return v


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_defiro_justica_gratuita():
    assert _jg("defiro a justiça gratuita ao reclamante") is True


def test_justica_gratuita_deferida():
    assert _jg("justiça gratuita deferida") is True


def test_beneficios_assistencia_judiciaria():
    assert _jg("benefícios da assistência judiciária gratuita") is True


def test_defiro_gratuidade_da_justica():
    assert _jg("defiro a gratuidade da justiça") is True


def test_indeferido_pedido_jg():
    assert _jg("indeferido o pedido de justiça gratuita") is False


def test_justica_gratuita_indeferida():
    assert _jg("justiça gratuita indeferida por ausência de prova") is False


def test_nao_faz_jus():
    assert _jg("não faz jus à justiça gratuita") is False


# ---------------------------------------------------------------------------
# GAPS TRUE — variante 'gratuidade de justiça'
# ---------------------------------------------------------------------------

def test_gratuidade_de_justica_deferida():
    """'gratuidade de justiça' com 'de' em vez de 'da'."""
    assert _jg("gratuidade de justiça deferida") is True


def test_concedo_gratuidade_de_justica():
    assert _jg("concedo os benefícios da gratuidade de justiça ao autor") is True


def test_defiro_gratuidade_de_justica():
    assert _jg("defiro a gratuidade de justiça requerida") is True


# ---------------------------------------------------------------------------
# GAPS TRUE — outros verbos/formas
# ---------------------------------------------------------------------------

def test_beneficiario_da_justica_gratuita():
    assert _jg("declaro o reclamante beneficiário da justiça gratuita") is True


# ---------------------------------------------------------------------------
# GAPS FALSE — 'indefiro' (verbo presente, não particípio)
# ---------------------------------------------------------------------------

def test_indefiro_gratuidade_de_justica():
    assert _jg("indefiro o pedido de gratuidade de justiça") is False


def test_indefiro_justica_gratuita():
    assert _jg("indefiro o benefício da justiça gratuita") is False


# ---------------------------------------------------------------------------
# GAPS FALSE — 'revogo' (cassação posterior)
# ---------------------------------------------------------------------------

def test_revogo_justica_gratuita():
    """Revogação posterior equivale a indeferimento para fins de extração."""
    assert _jg("revogo a justiça gratuita anteriormente deferida") is False


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _jg("O processo foi distribuído em 2023.") is None


# ---------------------------------------------------------------------------
# GAP — 'benefício de justiça gratuita deferido' (singular + de + masculino)
# ---------------------------------------------------------------------------

def test_beneficio_de_jg_deferido():
    """'benefício de justiça gratuita deferido' — singular, 'de', masculino."""
    assert _jg("benefício de justiça gratuita deferido") is True

def test_beneficio_da_jg_deferido():
    """'benefício da justiça gratuita deferido' — masculino."""
    assert _jg("benefício da justiça gratuita deferido") is True


# ---------------------------------------------------------------------------
# GAP — 'gratuidade de justiça concedida' (particípio de conceder)
# ---------------------------------------------------------------------------

def test_gratuidade_de_justica_concedida():
    """'gratuidade de justiça concedida'."""
    assert _jg("gratuidade de justiça concedida ao autor") is True

def test_gratuidade_de_justica_concedido():
    assert _jg("benefício de gratuidade de justiça concedido") is True

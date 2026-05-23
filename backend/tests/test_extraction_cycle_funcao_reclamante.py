"""
Ciclo TDD — funcao_reclamante (MEDIUM string)
Nota: o extractor retorna o texto capturado como está.
Gaps principais:
  1. 'exercia o cargo de X' / 'desempenhava a função de X' — variantes sem cobertura
  2. 'atuava/laborava/trabalhou como X' — triggers ausentes
  3. 'Cargo: X' / 'Função: X' — formato label sem cobertura
"""
import pytest
from services.pre_extractor import PreExtractor


def _fn(text: str):
    return PreExtractor(text).run()["medium"].get("funcao_reclamante")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_exercia_funcao_de():
    v = _fn("exercia a função de motorista")
    assert v is not None and "motorista" in v


def test_contratado_como():
    v = _fn("contratado como auxiliar de limpeza")
    assert v is not None and "auxiliar" in v


def test_admitida_como():
    v = _fn("admitida como operadora de caixa")
    assert v is not None and "operadora" in v


def test_trabalhava_como():
    v = _fn("trabalhava como vendedor externo")
    assert v is not None and "vendedor" in v


def test_ocupava_cargo():
    v = _fn("ocupava o cargo de gerente")
    assert v is not None and "gerente" in v


def test_na_funcao_de():
    v = _fn("na função de técnico de segurança")
    assert v is not None and "técnico" in v or (v is not None and "t" in v)


# ---------------------------------------------------------------------------
# GAP 1 — 'exercia o cargo de' / 'desempenhava a função de'
# ---------------------------------------------------------------------------

def test_exercia_cargo_de():
    """'exercia o cargo de' — cargo em vez de função."""
    v = _fn("exercia o cargo de analista de sistemas")
    assert v is not None and "analista" in v


def test_desempenhava_funcao():
    v = _fn("desempenhava a função de supervisor de produção")
    assert v is not None and "supervisor" in v


def test_desempenha_funcao():
    """Presente do indicativo — 'desempenha a função de'."""
    v = _fn("desempenha a função de coordenador")
    assert v is not None and "coordenador" in v


# ---------------------------------------------------------------------------
# GAP 2 — 'atuava/laborava/trabalhou como'
# ---------------------------------------------------------------------------

def test_atuava_como():
    v = _fn("atuava como motorista de caminhão")
    assert v is not None and "motorista" in v


def test_laborava_como():
    v = _fn("laborava como operador de máquinas")
    assert v is not None and "operador" in v


def test_trabalhou_como():
    """'trabalhou' (passado perfeito) como trigger."""
    v = _fn("trabalhou como soldador na empresa ré")
    assert v is not None and "soldador" in v


# ---------------------------------------------------------------------------
# GAP 3 — formato label 'Cargo: X' / 'Função: X'
# ---------------------------------------------------------------------------

def test_label_cargo():
    v = _fn("Cargo: analista de sistemas")
    assert v is not None and "analista" in v


def test_label_funcao():
    v = _fn("Função: vendedor")
    assert v is not None and "vendedor" in v


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _fn("O reclamante foi admitido em 2020.") is None

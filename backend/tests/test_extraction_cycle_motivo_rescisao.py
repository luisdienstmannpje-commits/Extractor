"""
Ciclo TDD — motivo_rescisao (MEDIUM)
Gaps principais:
  1. Texto sem acento ('rescisao', 'demissao', 'termino')
  2. 'demitido sem justa causa' (demitid[oa] vs demitiu)
  3. 'imotivadamente'
  4. Novos motivos: aposentadoria, acordo rescisório, falecimento
"""
import pytest
from services.pre_extractor import PreExtractor


def _med(text: str):
    return PreExtractor(text).run()["medium"].get("motivo_rescisao")


# ---------------------------------------------------------------------------
# Padrões cobertos — com acento (smoke)
# ---------------------------------------------------------------------------

def test_sjc_dispensado():
    assert _med("dispensado sem justa causa") == "Sem justa causa"


def test_sjc_demissao_sem_jc():
    assert _med("demissão sem justa causa") == "Sem justa causa"


def test_jc_com():
    assert _med("com justa causa pelo empregador") == "Com justa causa"


def test_rescisao_indireta_acentuada():
    assert _med("rescisão indireta por falta grave") == "Rescisão indireta"


def test_pedido_demissao_acentuado():
    assert _med("pedido de demissão do reclamante") == "Pedido de demissão"


def test_termino_contrato_acentuado():
    assert _med("término do prazo do contrato") == "Término de contrato"


# ---------------------------------------------------------------------------
# GAPS — texto sem acento (PDF strips accents)
# ---------------------------------------------------------------------------

def test_sjc_rescisao_sem_acento():
    """'rescisao sem justa causa' — sem acento, sem verbo antecedente."""
    assert _med("rescisao sem justa causa") == "Sem justa causa"


def test_sjc_demitido():
    """'demitido sem justa causa' — particípio, não estava no padrão."""
    assert _med("demitido sem justa causa") == "Sem justa causa"


def test_sjc_dispensada():
    assert _med("dispensada imotivadamente") == "Sem justa causa"


def test_rescisao_indireta_sem_acento():
    assert _med("rescisao indireta") == "Rescisão indireta"


def test_pedido_demissao_sem_acento():
    assert _med("pedido de demissao") == "Pedido de demissão"


def test_termino_sem_acento():
    assert _med("termino do contrato") == "Término de contrato"


# ---------------------------------------------------------------------------
# GAPS — novos motivos
# ---------------------------------------------------------------------------

def test_aposentadoria():
    assert _med("aposentadoria espontânea do reclamante") == "Aposentadoria"


def test_aposentadoria_sem_acento():
    assert _med("aposentadoria espontanea") == "Aposentadoria"


def test_acordo_rescisorio():
    assert _med("acordo rescisório entre as partes") == "Acordo rescisório"


def test_acordo_entre_partes():
    assert _med("acordo entre as partes (art. 484-A CLT)") == "Acordo rescisório"


def test_falecimento():
    assert _med("falecimento do empregado") == "Falecimento"


# ---------------------------------------------------------------------------
# Prioridade — indireta > SJC > JC
# ---------------------------------------------------------------------------

def test_indireta_prevalece_sobre_jc():
    txt = "rescisao indireta em razão da justa causa do empregador"
    assert _med(txt) == "Rescisão indireta"


def test_sem_contexto_nao_extrai():
    assert _med("O processo foi distribuído em 2023.") is None


# ---------------------------------------------------------------------------
# GAP — "por justa causa" (além de "com justa causa")
# ---------------------------------------------------------------------------

def test_jc_por_justa_causa():
    assert _med("dispensado por justa causa") == "Com justa causa"

def test_jc_motivada():
    assert _med("dispensado por justa causa motivada em desídia") == "Com justa causa"

def test_abandono_emprego():
    """abandono de emprego → Com justa causa (falta grave do empregado)"""
    assert _med("justa causa por abandono de emprego") == "Com justa causa"


# ---------------------------------------------------------------------------
# GAP — "culpa do empregador" → rescisão indireta
# ---------------------------------------------------------------------------

def test_culpa_empregador():
    assert _med("rescindiu o contrato por culpa do empregador") == "Rescisão indireta"

def test_falta_grave_empregador():
    assert _med("rescisão por falta grave do empregador") == "Rescisão indireta"


# ---------------------------------------------------------------------------
# GAP — "exoneração a pedido" → pedido de demissão
# ---------------------------------------------------------------------------

def test_exoneracao_a_pedido():
    assert _med("exoneração a pedido do servidor") == "Pedido de demissão"

def test_exonerou_a_pedido():
    assert _med("exonerou-se a pedido") == "Pedido de demissão"


# ---------------------------------------------------------------------------
# GAP — "encerramento da empresa" / "fim do prazo"
# ---------------------------------------------------------------------------

def test_encerramento_atividades():
    assert _med("rescisão por encerramento das atividades da empresa") == "Término de contrato"

def test_fim_prazo():
    assert _med("contrato encerrou pelo fim do prazo") == "Término de contrato"

def test_extincao_empresa():
    assert _med("extinção do estabelecimento") == "Término de contrato"


# ---------------------------------------------------------------------------
# GAP — dispensa imotivada → SJC
# ---------------------------------------------------------------------------

def test_dispensa_imotivada():
    """'dispensa imotivada' é sinônimo de sem justa causa."""
    assert _med("dispensa imotivada do reclamante") == "Sem justa causa"

def test_demissao_imotivada():
    assert _med("demissão imotivada pelo empregador") == "Sem justa causa"


# ---------------------------------------------------------------------------
# GAP — rescisão a pedido → pedido de demissão
# ---------------------------------------------------------------------------

def test_rescisao_a_pedido():
    assert _med("rescisão a pedido do empregado") == "Pedido de demissão"

def test_iniciativa_do_empregado():
    """'por iniciativa do empregado' → pedido de demissão."""
    assert _med("rescisão por iniciativa do empregado") == "Pedido de demissão"


# ---------------------------------------------------------------------------
# GAP — extinção da empresa → término de contrato
# ---------------------------------------------------------------------------

def test_extincao_da_empresa():
    assert _med("extinção da empresa empregadora") == "Término de contrato"

def test_fechamento_empresa():
    assert _med("fechamento da empresa") == "Término de contrato"

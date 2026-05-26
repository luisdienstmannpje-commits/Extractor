"""
Ciclo TDD — tipo_contrato (HIGH + MEDIUM)
Gaps principais:
  1. 'contrato intermitente' retorna 'CLT' em vez de 'Intermitente'
     (o literal 'CLT' no art. 443 CLT dispara _RE_CONTRATO_CLT antes)
  2. 'trabalho intermitente' — sem padrão
  3. 'contrato de aprendizagem' / 'menor aprendiz' — sem padrão
  4. 'contrato temporario' / 'trabalho temporario' — sem padrão
"""
import pytest
from services.pre_extractor import PreExtractor


def _tc(text: str):
    r = PreExtractor(text).run()
    return r["high"].get("tipo_contrato") or r["medium"].get("tipo_contrato")


# ---------------------------------------------------------------------------
# Smoke — padrões já cobertos
# ---------------------------------------------------------------------------

def test_experiencia_com_acento():
    assert _tc("contrato de experiência") == "Experiência"


def test_experiencia_sem_acento():
    assert _tc("contrato de experiencia") == "Experiência"


def test_periodo_experiencia():
    assert _tc("período de experiência com duração de 45 dias") == "Experiência"


def test_prazo_determinado():
    assert _tc("contrato por prazo determinado") == "Prazo determinado"


def test_prazo_determinado_com_contrato_antes():
    assert _tc("contrato de trabalho com prazo determinado") == "Prazo determinado"


def test_pejotizacao():
    assert _tc("pejotização reconhecida como fraude pelo juiz") == "Pejotização reconhecida"


def test_autonomo_reconhecido():
    assert _tc("autônomo reconhecido como empregado") == "Autônomo reconhecido"


def test_clt_vinculo():
    assert _tc("vínculo de emprego celetista") == "CLT"


# ---------------------------------------------------------------------------
# GAPS — Intermitente
# ---------------------------------------------------------------------------

def test_contrato_intermitente():
    """'contrato intermitente' — não deve retornar 'CLT' pelo art. 443 CLT."""
    assert _tc("contrato intermitente nos termos do art. 443 CLT") == "Intermitente"


def test_trabalho_intermitente():
    assert _tc("modalidade de trabalho intermitente") == "Intermitente"


def test_intermitente_sem_acento_contrato():
    assert _tc("contrato intermitente conforme art. 443 da CLT") == "Intermitente"


# ---------------------------------------------------------------------------
# GAPS — Aprendiz
# ---------------------------------------------------------------------------

def test_contrato_aprendizagem():
    assert _tc("contrato de aprendizagem celebrado com o reclamante") == "Aprendiz"


def test_menor_aprendiz():
    assert _tc("menor aprendiz admitido na empresa") == "Aprendiz"


def test_aprendiz_simples():
    assert _tc("na qualidade de aprendiz conforme a Lei 10.097") == "Aprendiz"


# ---------------------------------------------------------------------------
# GAPS — Temporário
# ---------------------------------------------------------------------------

def test_contrato_temporario():
    assert _tc("contrato temporário de trabalho (Lei 6.019)") == "Temporário"


def test_trabalho_temporario():
    assert _tc("admitido como trabalhador temporário") == "Temporário"


def test_temporario_sem_acento():
    assert _tc("contrato temporario nos termos da Lei 6.019") == "Temporário"


# ---------------------------------------------------------------------------
# Prioridade — intermitente > CLT
# ---------------------------------------------------------------------------

def test_intermitente_prevalece_sobre_clt():
    txt = "contrato intermitente conforme CLT art. 443"
    assert _tc(txt) == "Intermitente"


# ---------------------------------------------------------------------------
# Sem contexto
# ---------------------------------------------------------------------------

def test_sem_contexto_nao_extrai():
    assert _tc("O reclamante trabalhou por 3 anos na empresa.") is None


# ---------------------------------------------------------------------------
# GAP — Prazo indeterminado (tipo mais comum no Brasil — faltava regex)
# ---------------------------------------------------------------------------

def test_contrato_prazo_indeterminado():
    assert _tc("contrato por prazo indeterminado") == "Prazo indeterminado"

def test_contrato_tempo_indeterminado():
    assert _tc("contrato de trabalho por tempo indeterminado") == "Prazo indeterminado"

def test_contrato_duracao_indeterminada():
    assert _tc("contrato de duração indeterminada") == "Prazo indeterminado"

def test_vinculo_prazo_indeterminado():
    assert _tc("vínculo empregatício por prazo indeterminado") == "Prazo indeterminado"

def test_vinculo_tempo_indeterminado():
    assert _tc("vínculo de emprego por tempo indeterminado") == "Prazo indeterminado"


# ---------------------------------------------------------------------------
# GAP — Prazo determinado com vínculo/contrato de trabalho (antes não capturava)
# ---------------------------------------------------------------------------

def test_vinculo_prazo_determinado():
    assert _tc("vínculo empregatício por prazo determinado") == "Prazo determinado"

def test_contrato_trabalho_tempo_determinado():
    assert _tc("contrato de trabalho por tempo determinado") == "Prazo determinado"


# ---------------------------------------------------------------------------
# GAP — 'contrato a termo' (sinônimo de prazo determinado)
# ---------------------------------------------------------------------------

def test_contrato_a_termo():
    """'contrato a termo' é sinônimo legal de prazo determinado."""
    assert _tc("contrato a termo nos termos do art. 443 CLT") == "Prazo determinado"

def test_contrato_a_termo_simples():
    assert _tc("rescisão de contrato a termo") == "Prazo determinado"


# ---------------------------------------------------------------------------
# GAP — 'regime de experiência' (sem 'contrato de' ou 'período de')
# ---------------------------------------------------------------------------

def test_regime_experiencia():
    """'regime de experiência' não tem 'contrato de' nem 'período de'."""
    assert _tc("admitido em regime de experiência") == "Experiência"

def test_regime_experiencia_sem_acento():
    assert _tc("regime de experiencia de 90 dias") == "Experiência"

"""
Ciclo TDD — reclamante + reclamada (HIGH)
Extrai nomes das partes a partir do cabeçalho do documento.
"""
import pytest
from services.pre_extractor import PreExtractor


def _high(text: str, campo: str):
    return PreExtractor(text).run()["high"].get(campo)


# ---------------------------------------------------------------------------
# reclamante
# ---------------------------------------------------------------------------

def test_reclamante_simples():
    assert _high("Reclamante: João da Silva", "reclamante") == "João da Silva"


def test_reclamante_caps():
    assert _high("RECLAMANTE: JOÃO DA SILVA", "reclamante") == "JOÃO DA SILVA"


def test_reclamante_com_cpf():
    """Para antes do CPF."""
    assert _high("Reclamante: João da Silva, CPF: 123.456.789-00", "reclamante") == "João da Silva"


def test_reclamante_autor():
    assert _high("Autor: Pedro Henrique Costa", "reclamante") == "Pedro Henrique Costa"


def test_reclamante_autora():
    assert _high("Autora: Maria Aparecida Souza", "reclamante") == "Maria Aparecida Souza"


def test_reclamante_multiline_para_antes_da_proxima_linha():
    """Não ultrapassa a linha."""
    txt = "Reclamante: João da Silva\nReclamada: Empresa XYZ Ltda"
    assert _high(txt, "reclamante") == "João da Silva"


def test_reclamante_cabecalho_completo():
    """Extrai corretamente de bloco de cabeçalho típico."""
    txt = (
        "Processo nº 0001234-58.2023.5.04.0001\n"
        "Reclamante: Ana Paula Ferreira\n"
        "Reclamada: Comércio e Serviços Ltda\n"
    )
    assert _high(txt, "reclamante") == "Ana Paula Ferreira"


def test_reclamante_sem_rotulo_nao_extrai():
    assert _high("O reclamante foi dispensado sem justa causa.", "reclamante") is None


def test_reclamante_adv_nao_confunde():
    """'Advogado do Reclamante:' não deve ser capturado como nome da parte."""
    txt = "Advogado do Reclamante: Dr. Carlos Mendes OAB/SP 12345"
    assert _high(txt, "reclamante") is None


# ---------------------------------------------------------------------------
# reclamada
# ---------------------------------------------------------------------------

def test_reclamada_ltda():
    assert _high("Reclamada: Empresa XYZ Ltda", "reclamada") == "Empresa XYZ Ltda"


def test_reclamada_sa():
    assert _high("Reclamada: BANCO BRADESCO S/A", "reclamada") == "BANCO BRADESCO S/A"


def test_reclamada_caps():
    assert _high("RECLAMADA: COMERCIO E SERVICOS LTDA", "reclamada") == "COMERCIO E SERVICOS LTDA"


def test_reclamada_com_cnpj():
    """Para antes do CNPJ."""
    assert _high(
        "Reclamada: EMPRESA LTDA, CNPJ: 00.000.000/0001-00", "reclamada"
    ) == "EMPRESA LTDA"


def test_reclamado_masculino():
    """Aceita 'Reclamado' (masculino)."""
    assert _high("Reclamado: MUNICÍPIO DE SÃO PAULO", "reclamada") == "MUNICÍPIO DE SÃO PAULO"


def test_reclamada_multiline_para_antes_da_proxima_linha():
    txt = "Reclamante: João da Silva\nReclamada: Empresa XYZ Ltda\n"
    assert _high(txt, "reclamada") == "Empresa XYZ Ltda"


def test_reclamada_sem_rotulo_nao_extrai():
    assert _high("A reclamada foi condenada ao pagamento.", "reclamada") is None


def test_reclamada_adv_nao_confunde():
    """'Advogado da Reclamada:' não deve ser capturado como nome da parte."""
    txt = "Advogado da Reclamada: Dra. Beatriz Lima OAB/RJ 55555"
    assert _high(txt, "reclamada") is None


# ---------------------------------------------------------------------------
# Ambos no mesmo cabeçalho
# ---------------------------------------------------------------------------

def test_ambos_no_cabecalho():
    txt = (
        "Reclamante: João da Silva\n"
        "Reclamada: Comércio e Serviços Ltda\n"
    )
    r = PreExtractor(txt).run()
    assert r["high"].get("reclamante") == "João da Silva"
    assert r["high"].get("reclamada") == "Comércio e Serviços Ltda"


# ---------------------------------------------------------------------------
# GAP — labels alternativos reclamante
# ---------------------------------------------------------------------------

def test_parte_autora_label():
    txt = "Parte Autora: Carlos Braga\nReclamada: Empresa XYZ"
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamante') == 'Carlos Braga'

def test_empregado_label():
    txt = "Empregado: Paulo Ferreira\nEmpregadora: Banco ABC"
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamante') == 'Paulo Ferreira'


# ---------------------------------------------------------------------------
# GAP — labels alternativos reclamada
# ---------------------------------------------------------------------------

def test_re_label():
    """RE: em cabeçalho estruturado = Reclamada"""
    txt = "Reclamante: Joao Silva\nRE: Empresa ABC S/A"
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamada') == 'Empresa ABC S/A'

def test_parte_passiva_label():
    txt = 'Parte Passiva: XYZ Comercio LTDA'
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamada') == 'XYZ Comercio LTDA'

def test_empregadora_label():
    txt = 'Empregadora: Banco ABC S.A.'
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamada') == 'Banco ABC S.A'  # rstrip remove ponto final


# ---------------------------------------------------------------------------
# GAP — Polo Ativo / Polo Passivo
# ---------------------------------------------------------------------------

def test_polo_ativo_reclamante():
    """'Polo Ativo:' é o reclamante em ações trabalhistas."""
    txt = 'Polo Ativo: Carlos Lima'
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamante') == 'Carlos Lima'

def test_polo_passivo_reclamada():
    txt = 'Polo Passivo: Banco ABC S/A'
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamada') == 'Banco ABC S/A'


# ---------------------------------------------------------------------------
# GAP — Demandante / Demandada
# ---------------------------------------------------------------------------

def test_demandante_reclamante():
    txt = 'DEMANDANTE: Paulo Ferreira'
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamante') == 'Paulo Ferreira'

def test_demandada_reclamada():
    txt = 'DEMANDADA: Industrias ABC LTDA'
    r = PreExtractor(txt).run()
    assert r['high'].get('reclamada') == 'Industrias ABC LTDA'

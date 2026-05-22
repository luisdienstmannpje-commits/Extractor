"""
Ciclo TDD — natureza_reclamada
Valores possíveis: "fazenda_publica" | "privada"
Fazenda pública tem prioridade sobre privada quando ambos presentes.
"""
import pytest
from services.pre_extractor import PreExtractor


def _run(text: str) -> dict:
    return PreExtractor(text).run()


# ---------------------------------------------------------------------------
# Fazenda pública
# ---------------------------------------------------------------------------

def test_natureza_municipio():
    r = _run("Reclamada: MUNICIPIO DE SAO PAULO.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_prefeitura():
    r = _run("Prefeitura Municipal de Campinas, pessoa jurídica de direito público.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_estado():
    r = _run("Reclamado: ESTADO DE MINAS GERAIS, por meio de sua Procuradoria.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_uniao():
    r = _run("UNIAO FEDERAL, representada pela Advocacia-Geral da União.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_autarquia():
    r = _run("INSS - autarquia federal, com sede em Brasília.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_ente_publico():
    r = _run("A reclamada é ente público, sujeita ao regime de precatórios.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_empresa_publica():
    r = _run("A reclamada CORREIOS é empresa pública federal.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_precatorio():
    r = _run("O crédito deverá ser executado via precatório, nos termos do art. 100 CF.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_fundacao_publica():
    r = _run("Reclamada FUNAI, fundação pública federal.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


def test_natureza_distrito_federal():
    r = _run("Reclamado: DISTRITO FEDERAL, por sua Procuradoria-Geral.")
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


# ---------------------------------------------------------------------------
# Privada
# ---------------------------------------------------------------------------

def test_natureza_ltda():
    r = _run("Reclamada: COMERCIO E SERVICOS LTDA, CNPJ 00.000.000/0001-00.")
    assert r["medium"].get("natureza_reclamada") == "privada"


def test_natureza_sa():
    r = _run("BANCO BRADESCO S/A, instituição financeira privada.")
    assert r["medium"].get("natureza_reclamada") == "privada"


def test_natureza_empresa_privada():
    r = _run("A reclamada é empresa privada de grande porte.")
    assert r["medium"].get("natureza_reclamada") == "privada"


# ---------------------------------------------------------------------------
# Prioridade: fazenda_publica prevalece
# ---------------------------------------------------------------------------

def test_natureza_fazenda_prevalece_sobre_privada():
    r = _run(
        "SERVICOS MUNICIPAIS LTDA, empresa pública municipal, "
        "sujeita a precatório."
    )
    assert r["medium"].get("natureza_reclamada") == "fazenda_publica"


# ---------------------------------------------------------------------------
# Ausência — não extrai sem menção
# ---------------------------------------------------------------------------

def test_natureza_nao_extrai_sem_mencao():
    r = _run("O reclamante trabalhou das 08h às 17h com uma hora de intervalo.")
    assert "natureza_reclamada" not in r["medium"]


# ---------------------------------------------------------------------------
# build_anchor_section — campo aparece no mapeamento de labels
# ---------------------------------------------------------------------------

def test_natureza_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    html = build_anchor_section({"natureza_reclamada": "fazenda_publica"})
    assert "Natureza" in html or "natureza_reclamada" in html

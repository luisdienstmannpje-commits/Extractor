"""Testes do gate de qualidade por tipo de documento (processor._qualidade_ok)."""

from workers.processor import _qualidade_ok


def _base_dados_ok() -> dict:
    return {
        "numero_processo": "0000000-00.0000.0.00.0000",
        "reclamante": "Autor",
        "reclamada": "Ré",
        "data_sentenca": "01/01/2024",
        "salario_base": "R$ 1.500,00",
        "verbas_deferidas": [
            {"nome": "A"},
            {"nome": "B"},
            {"nome": "C"},
        ],
    }


def test_sentenca_exige_salario_e_tres_verbas():
    d = _base_dados_ok()
    ok, _ = _qualidade_ok(d, "sentenca")
    assert ok is True

    d2 = {**d, "salario_base": None}
    ok2, motivo = _qualidade_ok(d2, "sentenca")
    assert ok2 is False
    assert "salario_base" in motivo or "obrigatórios" in motivo

    d3 = {**d, "verbas_deferidas": [{"nome": "X"}, {"nome": "Y"}]}
    ok3, motivo3 = _qualidade_ok(d3, "sentenca")
    assert ok3 is False
    assert "verbas" in motivo3.lower()


def test_liquidacao_nao_exige_salario_base():
    d = {
        "numero_processo": "0000000-00.0000.0.00.0000",
        "reclamante": None,
        "reclamada": None,
        "data_sentenca": "01/01/2024",
        "salario_base": None,
        "verbas_deferidas": [{"nome": "HE"}],
    }
    ok, _ = _qualidade_ok(d, "liquidacao")
    assert ok is True


def test_liquidacao_partes_sem_numero():
    d = {
        "numero_processo": None,
        "reclamante": "Fulano",
        "reclamada": None,
        "verbas_deferidas": [{"nome": "HE"}],
    }
    ok, _ = _qualidade_ok(d, "liquidacao")
    assert ok is True


def test_liquidacao_reclamada_sem_reclamante():
    d = {
        "numero_processo": None,
        "reclamante": None,
        "reclamada": "Empresa X",
        "verbas_deferidas": [{"nome": "HE"}],
    }
    ok, _ = _qualidade_ok(d, "liquidacao")
    assert ok is True


def test_liquidacao_rejeita_sem_id_nem_partes():
    d = {
        "numero_processo": None,
        "reclamante": None,
        "reclamada": None,
        "verbas_deferidas": [{"nome": "HE"}],
    }
    ok, motivo = _qualidade_ok(d, "liquidacao")
    assert ok is False
    assert "identificação" in motivo.lower() or "liquidacao" in motivo.lower()


def test_liquidacao_rejeita_verbas_vazias():
    d = {
        "numero_processo": "0000000-00.0000.0.00.0000",
        "verbas_deferidas": [],
    }
    ok, motivo = _qualidade_ok(d, "liquidacao")
    assert ok is False
    assert "vazias" in motivo.lower()


def test_acordao_usa_regra_estrita_como_sentenca():
    d = _base_dados_ok()
    ok, _ = _qualidade_ok(d, "acordao")
    assert ok is True

    d2 = {**d, "salario_base": None}
    ok2, _ = _qualidade_ok(d2, "acordao")
    assert ok2 is False

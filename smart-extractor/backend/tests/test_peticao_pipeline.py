"""Fluxo petição inicial (cache composto + memorial) — IA mockada."""

from unittest.mock import patch, MagicMock

from workers.processor import (
    _montar_base_peticao_inicial,
    _qualidade_ok,
    _verba_dict_from_pedido_item,
)


def test_verba_from_string():
    v = _verba_dict_from_pedido_item(" Horas extras ")
    assert v and v["nome"] == "Horas extras"
    assert v["status_final"] == "pedido"


def test_verba_from_dict():
    v = _verba_dict_from_pedido_item({"nome": "FGTS", "observacoes": "x"})
    assert v and v["nome"] == "FGTS" and v.get("observacoes") == "x"


def test_montar_base_peticao():
    raw = {
        "verbas_pedidas": ["A", "B"],
        "valor_causa": "R$ 10,00",
    }
    b = _montar_base_peticao_inicial(raw)
    assert len(b["verbas_pedidas"]) == 2
    assert b["valor_causa"] == "R$ 10,00"


def test_qualidade_peticao_ok():
    d = {
        "verbas_pedidas": [{"nome": "X", "status_final": "pedido", "reflexos": []}],
        "verbas_deferidas": [],
    }
    ok, _ = _qualidade_ok(d, "peticao_inicial")
    assert ok is True


def test_qualidade_peticao_vazio():
    d = {"verbas_pedidas": [], "verbas_deferidas": []}
    ok, m = _qualidade_ok(d, "peticao_inicial")
    assert ok is False
    assert "nenhum" in m.lower()


@patch("workers.processor.deduct_credit")
@patch("workers.processor.gerar_memoria")
@patch("services.learning_engine._extrair_peticao_inicial")
def test_pipeline_peticao_salva_cache_separado(
    mock_extrair,
    _mock_mem,
    _mock_deduct,
):
    """Mesmo hash de ficheiro: cache petição ≠ cache auto (chaves distintas)."""
    from workers.processor import _pipeline_peticao_inicial

    mock_extrair.return_value = {
        "verbas_pedidas": ["Horas extras"],
        "causa_pedir": "Demissão",
        "periodo_reivindicado": "",
        "valor_causa": None,
        "model_used": "test-model",
    }

    cache_repo = MagicMock()
    cache_repo.get_cache.return_value = None
    ex_repo = MagicMock()
    ex_repo.save_extraction.return_value = "doc-1"

    fb = b"%PDF-1.4 minimal"

    out = _pipeline_peticao_inicial(
        "user-test",
        fb,
        "job1",
        "inicial.pdf",
        cache_repo,
        ex_repo,
    )

    assert out["status"] == "sucesso"
    assert out["doc_type"] == "peticao_inicial"
    assert out["data"].get("memorial_juridico")
    cache_repo.save_cache.assert_called_once()
    sk = cache_repo.save_cache.call_args[0][0]
    assert "peticao_inicial" in sk

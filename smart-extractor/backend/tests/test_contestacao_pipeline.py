"""Fluxo contestação (cache composto + teses_defesa) — IA mockada."""

from unittest.mock import MagicMock, patch

from workers.processor import (
    _montar_base_contestacao,
    _qualidade_ok,
    _tese_item_para_dict,
)


def test_tese_item_normaliza():
    t = _tese_item_para_dict(
        {
            "verba_alvo": "Horas extras",
            "tese_principal": "Cargo de confiança",
            "trecho_fundamentacao": "Ré confessa vínculo...",
            "incontroversa": False,
        }
    )
    assert t and t["verba_alvo"] == "Horas extras"
    assert t["tese_principal"] == "Cargo de confiança"
    assert t["incontroversa"] is False


def test_montar_base_contestacao():
    raw = {
        "numero_processo": "0000000-00.0000.0.00.0000",
        "reclamante": "A",
        "reclamada": "B",
        "valor_causa": "R$ 1,00",
        "teses_defesa": [
            {"verba_alvo": "FGTS", "tese_principal": "Prescrição", "incontroversa": False},
        ],
    }
    b = _montar_base_contestacao(raw)
    assert b["numero_processo"] == "0000000-00.0000.0.00.0000"
    assert len(b["teses_defesa"]) == 1
    assert b["verbas_deferidas"] == []


def test_qualidade_contestacao_ok():
    d = {"teses_defesa": [{"verba_alvo": "X", "tese_principal": "Y"}]}
    ok, _ = _qualidade_ok(d, "contestacao")
    assert ok is True


def test_qualidade_contestacao_vazio():
    ok, m = _qualidade_ok({"teses_defesa": []}, "contestacao")
    assert ok is False
    assert "tese" in m.lower()


@patch("workers.processor.executar_shadow_pipeline")
@patch("workers.processor.deduct_credit")
@patch("workers.processor.gerar_memoria")
@patch("services.learning_engine._extrair_contestacao")
def test_pipeline_contestacao_salva_cache_separado(
    mock_extrair,
    _mock_mem,
    _mock_deduct,
    _mock_shadow,
):
    from workers.processor import _pipeline_contestacao

    _mock_shadow.return_value = []
    mock_extrair.return_value = {
        "erro": None,
        "numero_processo": "1",
        "reclamante": "A",
        "reclamada": "B",
        "valor_causa": None,
        "teses_defesa": [
            {
                "verba_alvo": "Horas extras",
                "tese_principal": "Nega fato",
                "trecho_fundamentacao": "Trecho curto",
                "incontroversa": False,
            }
        ],
        "model_used": "test-model",
    }

    cache_repo = MagicMock()
    cache_repo.get_cache.return_value = None
    ex_repo = MagicMock()
    ex_repo.save_extraction.return_value = "doc-c1"

    fb = b"%PDF-1.4 minimal"

    out = _pipeline_contestacao(
        "user-test",
        fb,
        "job1",
        "contestacao.pdf",
        cache_repo,
        ex_repo,
    )

    assert out["status"] == "sucesso"
    assert out["doc_type"] == "contestacao"
    assert out["data"].get("memorial_juridico")
    assert len(out["data"].get("teses_defesa") or []) == 1
    cache_repo.save_cache.assert_called_once()
    sk = cache_repo.save_cache.call_args[0][0]
    assert "contestacao" in sk

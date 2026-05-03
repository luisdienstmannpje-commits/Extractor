"""Dossiê com ≥3 arquivos: merge de quadro_comparativo antes do pipeline pós-IA."""

from unittest.mock import MagicMock, patch


@patch("workers.processor._extrair_texto_arquivo_dossie")
@patch("workers.processor.get_user_credits")
@patch("workers.processor.get_cache_repo")
@patch("workers.processor.extract_data_with_gemini")
@patch("services.ai_client.extrair_quadro_comparativo_dossie")
@patch("workers.processor._executar_pipeline_pos_ia")
def test_tres_arquivos_dispara_quadro_e_mescla(
    mock_pos_ia,
    mock_quadro,
    mock_gemini,
    mock_cache_getter,
    mock_credits,
    mock_txt,
):
    mock_credits.return_value = 10
    mock_txt.return_value = "parágrafo do documento"
    repo = MagicMock()
    repo.get_cache.return_value = None
    mock_cache_getter.return_value = repo

    verbas = [
        {"nome": f"V{i}", "status_final": "deferida", "reflexos": []}
        for i in range(3)
    ]
    mock_gemini.return_value = {
        "data": {
            "numero_processo": "000-00.0000.0.00.0000",
            "reclamante": "A",
            "reclamada": "B",
            "data_sentenca": "01/01/2024",
            "salario_base": "R$ 1,00",
            "justica_gratuita": False,
            "verbas_deferidas": verbas,
        },
        "model_used": "gemini-test",
        "error": None,
    }
    mock_quadro.return_value = {
        "quadro_comparativo": [
            {
                "verba_alvo": "HE",
                "resumo_pedido": "p",
                "resumo_defesa": "d",
                "resumo_decisao": "j",
                "status_final": "Deferida",
            }
        ],
        "model_used": "gemini-test",
        "error": None,
    }
    mock_pos_ia.return_value = {"status": "sucesso", "source": "ai"}

    from workers.processor import process_lawsuit_dossie

    files = [("1.pdf", b"a"), ("2.pdf", b"b"), ("3.pdf", b"c")]
    out = process_lawsuit_dossie("user-t", files, job_id="job-x")

    assert out["status"] == "sucesso"
    mock_quadro.assert_called_once()
    kwargs = mock_pos_ia.call_args[1]
    assert len(kwargs["dados_limpos"].get("quadro_comparativo") or []) == 1
    assert kwargs["dados_limpos"]["quadro_comparativo"][0]["verba_alvo"] == "HE"


@patch("workers.processor._extrair_texto_arquivo_dossie")
@patch("workers.processor.get_user_credits")
@patch("workers.processor.get_cache_repo")
@patch("workers.processor.extract_data_with_gemini")
@patch("services.ai_client.extrair_quadro_comparativo_dossie")
@patch("workers.processor._executar_pipeline_pos_ia")
def test_dois_arquivos_nao_chama_quadro(
    mock_pos_ia,
    mock_quadro,
    mock_gemini,
    mock_cache_getter,
    mock_credits,
    mock_txt,
):
    mock_credits.return_value = 10
    mock_txt.return_value = "x"
    repo = MagicMock()
    repo.get_cache.return_value = None
    mock_cache_getter.return_value = repo
    verbas = [
        {"nome": f"V{i}", "status_final": "deferida", "reflexos": []}
        for i in range(3)
    ]
    mock_gemini.return_value = {
        "data": {
            "numero_processo": "1",
            "reclamante": "A",
            "reclamada": "B",
            "data_sentenca": "01/01/2024",
            "salario_base": "1",
            "justica_gratuita": False,
            "verbas_deferidas": verbas,
        },
        "model_used": "m",
        "error": None,
    }
    mock_pos_ia.return_value = {"status": "sucesso"}

    from workers.processor import process_lawsuit_dossie

    process_lawsuit_dossie("u", [("a.pdf", b"a"), ("b.pdf", b"b")], "")
    mock_quadro.assert_not_called()
    kwargs = mock_pos_ia.call_args[1]
    assert kwargs["dados_limpos"].get("quadro_comparativo") == []

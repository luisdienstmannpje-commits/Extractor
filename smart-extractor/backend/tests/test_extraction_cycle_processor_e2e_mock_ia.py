"""
Ciclo e2e enxuto: um caminho feliz do process_lawsuit_pdf com IA mockada.

Helpers locais (infra, parecer, payloads IA): `_e2e_infra`, `_stub_parecer`,
`_liquidacao_data_minima`, `_strict_qualidade_data`, `_gemini_response`, `_make_gemini_stub`.

Contrato mínimo:
  - Entrada: bytes de PDF opacos (não inspecionados quando o extrator de texto está stubado).
  - Sem API Gemini real: `workers.processor.extract_data_with_gemini` substituído por stub que
    devolve payload mínimo válido pós-`_validate_result` para doc_type `liquidacao`.
  - Sem segunda chamada de IA no parecer: `workers.processor.gerar_parecer_tecnico_completo` stubado.
  - Crédito/cache: `get_user_credits` > 0, `quota_excedida` falso, cache miss.
  - Saída: `status == "sucesso"`, `source == "ai"`, `doc_type == "liquidacao"`,
    `qualidade_ok is True`, e identificação (`numero_processo`) coerente com o stub.

Contrato estrutural (mesmo fluxo):
  - Topo: `alertas_juridicos`, `regras_aplicadas`, `explicacoes` como listas; `memorial_juridico`
    como lista de entradas do motor; `raiox` como dict enriquecido.
  - `data`: `verbas_deferidas` lista não vazia; `alertas_juridicos` e `regras_aplicadas` listas;
    `fontes_extracao` lista (pode ser vazia).

Segundo caminho (`test_process_lawsuit_pdf_sentenca_caminho_feliz_ia_mockada`):
  - `extract_sentence_from_pdf` → `"sentenca"`; stub IA satisfaz `_qualidade_ok` (campos obrigatórios,
    salario_base, ≥3 verbas).

Paralelo a sentenca (`test_process_lawsuit_pdf_acordao_caminho_feliz_ia_mockada`):
  - `extract_sentence_from_pdf` → `"acordao"`; mesmo gate rígido; fixture sem gatilhos HIGH (foco em doc_type).

Paralelo (`test_process_lawsuit_pdf_embargos_caminho_feliz_ia_mockada`):
  - `extract_sentence_from_pdf` → `"embargos"`; `_qualidade_ok` cai no bloco padrão (igual sentenca/acordao).

Paralelo (`test_process_lawsuit_pdf_despacho_caminho_feliz_ia_mockada`):
  - `extract_sentence_from_pdf` → `"despacho"`; mesmo gate default (`_CAMPOS_OBRIGATORIOS` + ≥3 verbas).

Terceiro (`test_liquidacao_e2e_pre_high_sobrescreve_numero_e_log`):
  - Texto com CNJ capturável pelo `pre_extract` (HIGH); stub IA devolve outro `numero_processo`.
  - Resposta final com CNJ do pré-extrator; stdout contém `[PRE-HIGH]` e `numero_processo`.

Quarto (`test_liquidacao_e2e_pre_high_sobrescreve_data_sentenca_e_log`):
  - Texto com assinatura PJe (`Assinado eletronicamente em DD/MM/AAAA`); stub IA com `data_sentenca` diferente.
  - Resposta mantém data HIGH; stdout contém `[PRE-HIGH]` e `data_sentenca`.

Quinto (`test_liquidacao_e2e_pre_high_sobrescreve_reclamante_e_log`):
  - Texto com `Reclamante:` na capa; CNJ alinhado ao stub; sem outras âncoras HIGH conflitantes.
  - Stub IA com `reclamante` divergente; resposta mantém nome HIGH; stdout `[PRE-HIGH]` + `reclamante`.

Sexto (`test_liquidacao_e2e_pre_high_sobrescreve_reclamada_e_log`):
  - Texto com `Reclamada:` na capa; CNJ igual no stub; sem Reclamante/assinatura PJe no trecho.
  - Stub IA com `reclamada` divergente; stdout `[PRE-HIGH]` + `reclamada`.

Sétimo (`test_liquidacao_e2e_pre_high_sobrescreve_vara_trabalho_e_log`):
  - Texto com `Vara do Trabalho: …` plausível; CNJ alinhado; sem partes/assinatura PJe.
  - Stub IA com `vara_trabalho` divergente; stdout `[PRE-HIGH]` + `vara_trabalho`.

Oitavo (`test_liquidacao_e2e_pre_high_sobrescreve_justica_gratuita_e_log`):
  - Texto com frase de defiro de justiça gratuita; CNJ alinhado; sem outras linhas HIGH conflitantes.
  - Stub IA com `justica_gratuita: false`; resposta `True`; stdout `[PRE-HIGH]` + `justica_gratuita`.

Nono (`test_liquidacao_e2e_pre_high_sobrescreve_tipo_rito_e_log`):
  - Texto com menção a rito sumaríssimo; CNJ alinhado; sem JG, partes, vara, assinatura PJe.
  - Stub IA com `tipo_rito` ordinário; resposta com valor HIGH (`Sumaríssimo`); stdout `[PRE-HIGH]` + `tipo_rito`.

Décimo (`test_liquidacao_e2e_pre_high_merge_numero_e_reclamante_uma_linha`):
  - Dois HIGH divergentes (CNJ + reclamante) no mesmo fluxo `liquidacao`; uma linha `[PRE-HIGH]` com ambos os nomes.

Fluxo dedicado (`test_process_lawsuit_pdf_peticao_inicial_cache_context_mockada`):
  - `cache_context="peticao_inicial"` chama learning engine dedicado e não passa por sentence_finder/Gemini padrão.
  - Stub retorna um pedido; gate de qualidade petição fica OK, cache composto é usado e memorial é gerado.

Fluxo dedicado (`test_process_lawsuit_pdf_contestacao_cache_context_mockada`):
  - `cache_context="contestacao"` chama learning engine dedicado e não passa por sentence_finder/Gemini padrão.
  - Stub retorna uma tese de defesa; gate de qualidade contestação fica OK, cache composto é usado e memorial é gerado.

Cache dedicado (`test_process_lawsuit_pdf_peticao_inicial_cache_hit_qualificado`):
  - Cache composto válido para petição inicial retorna `source="cache"` antes do learning engine dedicado.

Cache dedicado (`test_process_lawsuit_pdf_contestacao_cache_hit_qualificado`):
  - Cache composto válido para contestação retorna `source="cache"` antes do learning engine dedicado.

Cache dedicado (`test_process_lawsuit_pdf_peticao_inicial_cache_invalido_reprocessa`):
  - Cache composto insuficiente para petição inicial é descartado e o learning engine dedicado roda.

Cache dedicado (`test_process_lawsuit_pdf_contestacao_cache_invalido_reprocessa`):
  - Cache composto insuficiente para contestação é descartado e o learning engine dedicado roda.

Rejeição dedicada (`test_process_lawsuit_pdf_peticao_inicial_extensao_invalida`):
  - `cache_context="peticao_inicial"` com extensão fora de PDF/DOC/DOCX retorna erro antes do pipeline dedicado.

Rejeição dedicada (`test_process_lawsuit_pdf_contestacao_extensao_invalida`):
  - `cache_context="contestacao"` com extensão fora de PDF/DOC/DOCX retorna erro antes do pipeline dedicado.

Dossiê (`test_process_lawsuit_dossie_tres_arquivos_quadro_no_payload_final`):
  - Três arquivos disparam segunda IA mockada de quadro comparativo e o item chega ao `data` final.

Dossiê (`test_process_lawsuit_dossie_dois_arquivos_sem_quadro_no_payload_final`):
  - Dois arquivos não chamam a segunda IA de quadro e retornam `quadro_comparativo=[]`.

Dossiê (`test_process_lawsuit_dossie_quadro_falha_nao_bloqueia_fluxo`):
  - Três arquivos com falha na segunda IA de quadro seguem com `sucesso` e quadro vazio.

Dossiê (`test_process_lawsuit_dossie_cache_hit_qualificado`):
  - Cache válido de dossiê retorna `source="cache"` antes de extrair textos ou chamar IAs.

Dossiê (`test_process_lawsuit_dossie_cache_invalido_reprocessa`):
  - Cache insuficiente de dossiê é descartado e o fluxo reprocessa com IAs mockadas.

Dossiê (`test_process_lawsuit_dossie_saldo_esgotado_para_antes_de_cache_texto_ia`):
  - Sem créditos, dossiê retorna erro antes de cache, texto e IAs.
"""

from __future__ import annotations

from typing import Any, Callable
from unittest.mock import MagicMock

import services.ai_client as ai_client
import services.learning_engine as learning_engine
import workers.processor as proc

_VERBAS_TRES_DEFERIDAS: tuple[dict[str, str], ...] = (
    {"nome": "Verba Alfa", "status_final": "deferida"},
    {"nome": "Verba Beta", "status_final": "deferida"},
    {"nome": "Verba Gama", "status_final": "deferida"},
)


def _e2e_infra(monkeypatch: Any, *, credits: int = 10) -> MagicMock:
    """Crédito, quota livre e cache miss (padrão dos e2e mockados)."""
    monkeypatch.setattr(proc, "get_user_credits", lambda _uid: credits)
    monkeypatch.setattr(proc, "quota_excedida", lambda _uid, _kind: False)
    repo = MagicMock()
    repo.get_cache.return_value = None
    monkeypatch.setattr(proc, "get_cache_repo", lambda: repo)
    return repo


def _stub_parecer(monkeypatch: Any, texto: str = "parecer stub") -> None:
    monkeypatch.setattr(
        proc,
        "gerar_parecer_tecnico_completo",
        lambda _dados, _verbas: {
            "texto": texto,
            "parcelas": "",
            "model_used": "mock-parecer",
            "error": None,
        },
    )


def _liquidacao_data_minima(numero_processo: str, **overrides: Any) -> dict[str, Any]:
    """Payload `data` mínimo válido para `_qualidade_ok` em `liquidacao`."""
    data: dict[str, Any] = {
        "numero_processo": numero_processo,
        "reclamante": "Autor Teste",
        "reclamada": None,
        "salario_base": None,
        "data_sentenca": None,
        "verbas_deferidas": [{"nome": "Horas extras", "status_final": "deferida"}],
    }
    data.update(overrides)
    return data


def _strict_qualidade_data(cnj: str, **overrides: Any) -> dict[str, Any]:
    """Campos obrigatórios + ≥3 verbas (gate default: sentenca, acordao, embargos, despacho)."""
    data: dict[str, Any] = {
        "numero_processo": cnj,
        "reclamante": "Autor Stub",
        "reclamada": "Ré Stub",
        "data_sentenca": "01/01/2024",
        "salario_base": "R$ 1.500,00",
        "verbas_deferidas": list(_VERBAS_TRES_DEFERIDAS),
    }
    data.update(overrides)
    return data


def _gemini_response(model_used: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"error": None, "model_used": model_used, "data": data}


def _make_gemini_stub(
    model_used: str,
    data: dict[str, Any],
    *,
    on_call: Callable[..., None] | None = None,
) -> Callable[..., dict[str, Any]]:
    def stub(
        texto: str,
        playbook: str = "",
        pre_fields: Any = None,
        pipeline_debug_meta: Any = None,
    ) -> dict[str, Any]:
        if on_call is not None:
            on_call(texto, playbook, pre_fields, pipeline_debug_meta)
        return _gemini_response(model_used, data)

    return stub


def test_process_lawsuit_pdf_caminho_feliz_ia_mockada(monkeypatch):
    texto_fixture = (
        "Processo 1234567-89.2023.5.03.0068\n"
        "Liquidacao de sentenca — texto minimo para pre_extract.\n"
    )
    cnj_stub = "1234567-89.2023.5.03.0068"

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    chamadas_gemini: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        _make_gemini_stub(
            "mock-e2e",
            _liquidacao_data_minima(cnj_stub),
            on_call=lambda *a: chamadas_gemini.append(a),
        ),
    )

    _stub_parecer(monkeypatch)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf("user-e2e-stub", b"%PDF-1.4\n", job_id="job-e2e-1")

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "liquidacao"
    assert out["model_used"] == "mock-e2e"
    assert out.get("qualidade_ok") is True
    assert out["data"].get("numero_processo") == cnj_stub
    assert len(chamadas_gemini) == 1

    # Contrato estrutural mínimo (regressão no envelope da resposta / schema em data)
    assert isinstance(out["alertas_juridicos"], list)
    assert isinstance(out["regras_aplicadas"], list)
    assert isinstance(out["explicacoes"], list)
    assert isinstance(out["memorial_juridico"], list)
    assert isinstance(out["raiox"], dict)

    payload = out["data"]
    assert isinstance(payload.get("verbas_deferidas"), list)
    assert len(payload["verbas_deferidas"]) >= 1
    assert isinstance(payload["verbas_deferidas"][0], dict)
    assert payload["verbas_deferidas"][0].get("nome")

    assert isinstance(payload.get("alertas_juridicos"), list)
    assert isinstance(payload.get("regras_aplicadas"), list)
    assert isinstance(payload.get("fontes_extracao"), list)


def test_process_lawsuit_pdf_peticao_inicial_cache_context_mockada(monkeypatch):
    """
    Fluxo de negocio dedicado: cache_context peticao_inicial.

    O objetivo e validar a chave de entrada publica `process_lawsuit_pdf(..., cache_context=...)`,
    nao so o helper interno `_pipeline_peticao_inicial`.
    """
    _e2e_infra(monkeypatch)
    extraction_repo = MagicMock()
    extraction_repo.save_extraction.return_value = "doc-peticao-1"
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        MagicMock(side_effect=AssertionError("peticao_inicial nao deve usar sentence_finder")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("peticao_inicial nao deve usar Gemini padrao")),
    )
    monkeypatch.setattr(proc, "executar_shadow_pipeline", lambda _dados: [])
    monkeypatch.setattr(proc, "gerar_memoria", MagicMock())
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    partials: list[tuple[Any, str]] = []
    monkeypatch.setattr(
        proc,
        "_emit_ws_partial",
        lambda _job_id, payload, message: partials.append((payload, message)),
    )

    monkeypatch.setattr(
        learning_engine,
        "_extrair_peticao_inicial",
        lambda _file_bytes, filename: {
            "verbas_pedidas": [
                {
                    "nome": "Horas extras",
                    "trecho_fundamentacao": "O autor laborava em sobrejornada.",
                }
            ],
            "causa_pedir": "Jornada extraordinaria habitual",
            "periodo_reivindicado": "01/2020 a 12/2020",
            "valor_causa": "R$ 10.000,00",
            "model_used": f"mock-peticao-{filename}",
        },
    )

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-peticao-e2e",
        b"%PDF-1.4 peticao inicial fixture",
        job_id="job-peticao-e2e",
        cache_context="peticao_inicial",
        filename="inicial.pdf",
    )

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "peticao_inicial"
    assert out["model_used"] == "mock-peticao-inicial.pdf"
    assert out["qualidade_ok"] is True
    assert out["qualidade_motivo"] is None

    data = out["data"]
    assert data["_meta_doc_type"] == "peticao_inicial"
    assert data["valor_causa"] == "R$ 10.000,00"
    assert data["verbas_pedidas"][0]["nome"] == "Horas extras"
    assert data["verbas_pedidas"][0]["status_final"] == "pedido"
    assert data["verbas_deferidas"][0]["nome"] == "Horas extras"
    assert data["memorial_juridico"]
    assert out["memorial_juridico"] == data["memorial_juridico"]
    assert isinstance(data["fontes_extracao"], list)

    cache_repo = proc.get_cache_repo()
    cache_repo.save_cache.assert_called_once()
    assert "peticao_inicial" in cache_repo.save_cache.call_args[0][0]
    extraction_repo.save_extraction.assert_called_once()
    deduct_mock.assert_called_once_with("user-peticao-e2e")
    assert partials
    assert "PETI" in partials[0][1].upper()


def test_process_lawsuit_pdf_contestacao_cache_context_mockada(monkeypatch):
    """
    Fluxo de negocio dedicado: cache_context contestacao.

    Complementa o teste direto de `_pipeline_contestacao` cobrindo a entrada publica
    `process_lawsuit_pdf(..., cache_context=...)`.
    """
    _e2e_infra(monkeypatch)
    extraction_repo = MagicMock()
    extraction_repo.save_extraction.return_value = "doc-contestacao-1"
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        MagicMock(side_effect=AssertionError("contestacao nao deve usar sentence_finder")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("contestacao nao deve usar Gemini padrao")),
    )
    monkeypatch.setattr(proc, "executar_shadow_pipeline", lambda _dados: [])
    monkeypatch.setattr(proc, "gerar_memoria", MagicMock())
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    partials: list[tuple[Any, str]] = []
    monkeypatch.setattr(
        proc,
        "_emit_ws_partial",
        lambda _job_id, payload, message: partials.append((payload, message)),
    )

    monkeypatch.setattr(
        learning_engine,
        "_extrair_contestacao",
        lambda _file_bytes, filename: {
            "numero_processo": "0000000-00.0000.0.00.0000",
            "reclamante": "Autor Contestacao",
            "reclamada": "Empresa Defesa Ltda",
            "valor_causa": "R$ 20.000,00",
            "teses_defesa": [
                {
                    "verba_alvo": "Horas extras",
                    "tese_principal": "Nega labor extraordinario habitual",
                    "incontroversa": False,
                }
            ],
            "model_used": f"mock-contestacao-{filename}",
        },
    )
    monkeypatch.setattr(
        learning_engine,
        "_extrair_texto_arquivo_com_marcadores_pagina",
        lambda _file_bytes, _filename: "--- PAGINA 1 ---\nContestacao com tese de defesa.",
    )

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-contestacao-e2e",
        b"%PDF-1.4 contestacao fixture",
        job_id="job-contestacao-e2e",
        cache_context="contestacao",
        filename="contestacao.pdf",
    )

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "contestacao"
    assert out["model_used"] == "mock-contestacao-contestacao.pdf"
    assert out["qualidade_ok"] is True
    assert out["qualidade_motivo"] is None

    data = out["data"]
    assert data["_meta_doc_type"] == "contestacao"
    assert data["numero_processo"] == "0000000-00.0000.0.00.0000"
    assert data["reclamada"] == "Empresa Defesa Ltda"
    assert data["teses_defesa"][0]["verba_alvo"] == "Horas extras"
    assert data["teses_defesa"][0]["tese_principal"] == "Nega labor extraordinario habitual"
    assert data["memorial_juridico"]
    assert out["memorial_juridico"] == data["memorial_juridico"]
    assert isinstance(data["fontes_extracao"], list)

    cache_repo = proc.get_cache_repo()
    cache_repo.save_cache.assert_called_once()
    assert "contestacao" in cache_repo.save_cache.call_args[0][0]
    extraction_repo.save_extraction.assert_called_once()
    deduct_mock.assert_called_once_with("user-contestacao-e2e")
    assert partials
    assert "CONTESTA" in partials[0][1].upper()


def test_process_lawsuit_pdf_peticao_inicial_cache_hit_qualificado(monkeypatch):
    """Cache composto valido de peticao_inicial evita reprocessamento dedicado."""
    cached = {
        "_meta_doc_type": "peticao_inicial",
        "verbas_pedidas": [{"nome": "Horas extras", "status_final": "pedido"}],
        "verbas_deferidas": [],
        "memorial_juridico": "Memorial em cache",
    }

    repo = _e2e_infra(monkeypatch)
    repo.get_cache.return_value = cached
    extraction_repo = MagicMock()
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        learning_engine,
        "_extrair_peticao_inicial",
        MagicMock(side_effect=AssertionError("cache hit nao deve chamar learning engine")),
    )
    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        MagicMock(side_effect=AssertionError("cache hit peticao nao deve usar sentence_finder")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("cache hit peticao nao deve usar Gemini padrao")),
    )
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-peticao-cache-e2e",
        b"%PDF-1.4 peticao cache fixture",
        job_id="job-peticao-cache-e2e",
        cache_context="peticao_inicial",
        filename="inicial.pdf",
    )

    assert out == {
        "status": "sucesso",
        "source": "cache",
        "doc_type": "peticao_inicial",
        "data": cached,
    }
    repo.get_cache.assert_called_once()
    assert "peticao_inicial" in repo.get_cache.call_args[0][0]
    repo.save_cache.assert_not_called()
    extraction_repo.save_extraction.assert_not_called()
    deduct_mock.assert_not_called()


def test_process_lawsuit_pdf_contestacao_cache_hit_qualificado(monkeypatch):
    """Cache composto valido de contestacao evita reprocessamento dedicado."""
    cached = {
        "_meta_doc_type": "contestacao",
        "teses_defesa": [
            {
                "verba_alvo": "Horas extras",
                "tese_principal": "Nega jornada extraordinaria",
            }
        ],
        "verbas_deferidas": [],
        "memorial_juridico": "Memorial de defesa em cache",
    }

    repo = _e2e_infra(monkeypatch)
    repo.get_cache.return_value = cached
    extraction_repo = MagicMock()
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        learning_engine,
        "_extrair_contestacao",
        MagicMock(side_effect=AssertionError("cache hit nao deve chamar learning engine")),
    )
    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        MagicMock(side_effect=AssertionError("cache hit contestacao nao deve usar sentence_finder")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("cache hit contestacao nao deve usar Gemini padrao")),
    )
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-contestacao-cache-e2e",
        b"%PDF-1.4 contestacao cache fixture",
        job_id="job-contestacao-cache-e2e",
        cache_context="contestacao",
        filename="contestacao.pdf",
    )

    assert out == {
        "status": "sucesso",
        "source": "cache",
        "doc_type": "contestacao",
        "data": cached,
    }
    repo.get_cache.assert_called_once()
    assert "contestacao" in repo.get_cache.call_args[0][0]
    repo.save_cache.assert_not_called()
    extraction_repo.save_extraction.assert_not_called()
    deduct_mock.assert_not_called()


def test_process_lawsuit_pdf_peticao_inicial_cache_invalido_reprocessa(monkeypatch):
    """Cache composto insuficiente de peticao_inicial deve cair no fluxo dedicado."""
    cached_invalido = {
        "_meta_doc_type": "peticao_inicial",
        "verbas_pedidas": [],
        "verbas_deferidas": [],
    }

    repo = _e2e_infra(monkeypatch)
    repo.get_cache.return_value = cached_invalido
    extraction_repo = MagicMock()
    extraction_repo.save_extraction.return_value = "doc-peticao-reprocessada"
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        MagicMock(side_effect=AssertionError("peticao_inicial nao deve usar sentence_finder")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("peticao_inicial nao deve usar Gemini padrao")),
    )
    monkeypatch.setattr(proc, "executar_shadow_pipeline", lambda _dados: [])
    monkeypatch.setattr(proc, "gerar_memoria", MagicMock())
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)
    monkeypatch.setattr(proc, "_emit_ws_partial", MagicMock())

    extrair_mock = MagicMock(
        return_value={
            "verbas_pedidas": ["Horas extras"],
            "causa_pedir": "Jornada extraordinaria",
            "periodo_reivindicado": "01/2020 a 12/2020",
            "valor_causa": None,
            "model_used": "mock-peticao-reprocessada",
        }
    )
    monkeypatch.setattr(learning_engine, "_extrair_peticao_inicial", extrair_mock)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-peticao-cache-invalido-e2e",
        b"%PDF-1.4 peticao cache invalido fixture",
        job_id="job-peticao-cache-invalido-e2e",
        cache_context="peticao_inicial",
        filename="inicial.pdf",
    )

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "peticao_inicial"
    assert out["model_used"] == "mock-peticao-reprocessada"
    assert out["qualidade_ok"] is True
    assert out["data"]["verbas_pedidas"][0]["nome"] == "Horas extras"

    extrair_mock.assert_called_once()
    repo.save_cache.assert_called_once()
    assert "peticao_inicial" in repo.save_cache.call_args[0][0]
    extraction_repo.save_extraction.assert_called_once()
    deduct_mock.assert_called_once_with("user-peticao-cache-invalido-e2e")


def test_process_lawsuit_pdf_contestacao_cache_invalido_reprocessa(monkeypatch):
    """Cache composto insuficiente de contestacao deve cair no fluxo dedicado."""
    cached_invalido = {
        "_meta_doc_type": "contestacao",
        "teses_defesa": [],
        "verbas_deferidas": [],
    }

    repo = _e2e_infra(monkeypatch)
    repo.get_cache.return_value = cached_invalido
    extraction_repo = MagicMock()
    extraction_repo.save_extraction.return_value = "doc-contestacao-reprocessada"
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        MagicMock(side_effect=AssertionError("contestacao nao deve usar sentence_finder")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("contestacao nao deve usar Gemini padrao")),
    )
    monkeypatch.setattr(proc, "executar_shadow_pipeline", lambda _dados: [])
    monkeypatch.setattr(proc, "gerar_memoria", MagicMock())
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)
    monkeypatch.setattr(proc, "_emit_ws_partial", MagicMock())

    extrair_mock = MagicMock(
        return_value={
            "numero_processo": "0000000-00.0000.0.00.0000",
            "reclamante": "Autor Contestacao",
            "reclamada": "Empresa Defesa Ltda",
            "valor_causa": None,
            "teses_defesa": [
                {
                    "verba_alvo": "Horas extras",
                    "tese_principal": "Nega jornada extraordinaria",
                    "incontroversa": False,
                }
            ],
            "model_used": "mock-contestacao-reprocessada",
        }
    )
    monkeypatch.setattr(learning_engine, "_extrair_contestacao", extrair_mock)
    monkeypatch.setattr(
        learning_engine,
        "_extrair_texto_arquivo_com_marcadores_pagina",
        lambda _file_bytes, _filename: "--- PAGINA 1 ---\nContestacao reprocessada.",
    )

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-contestacao-cache-invalido-e2e",
        b"%PDF-1.4 contestacao cache invalido fixture",
        job_id="job-contestacao-cache-invalido-e2e",
        cache_context="contestacao",
        filename="contestacao.pdf",
    )

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "contestacao"
    assert out["model_used"] == "mock-contestacao-reprocessada"
    assert out["qualidade_ok"] is True
    assert out["data"]["teses_defesa"][0]["verba_alvo"] == "Horas extras"

    extrair_mock.assert_called_once()
    repo.save_cache.assert_called_once()
    assert "contestacao" in repo.save_cache.call_args[0][0]
    extraction_repo.save_extraction.assert_called_once()
    deduct_mock.assert_called_once_with("user-contestacao-cache-invalido-e2e")


def test_process_lawsuit_pdf_peticao_inicial_extensao_invalida(monkeypatch):
    """Peticao inicial rejeita extensao invalida antes do pipeline dedicado."""
    _e2e_infra(monkeypatch)
    extraction_repo = MagicMock()
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        learning_engine,
        "_extrair_peticao_inicial",
        MagicMock(side_effect=AssertionError("extensao invalida nao deve chamar learning engine")),
    )
    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        MagicMock(side_effect=AssertionError("peticao_inicial invalida nao deve usar sentence_finder")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("peticao_inicial invalida nao deve usar Gemini padrao")),
    )
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-peticao-ext-invalida-e2e",
        b"conteudo opaco",
        job_id="job-peticao-ext-invalida-e2e",
        cache_context="peticao_inicial",
        filename="inicial.exe",
    )

    assert out["status"] == "erro"
    assert "Petição inicial" in out["msg"] or "Peti" in out["msg"]
    assert "PDF" in out["msg"] and "DOC" in out["msg"]
    proc.get_cache_repo().get_cache.assert_not_called()
    extraction_repo.save_extraction.assert_not_called()
    deduct_mock.assert_not_called()


def test_process_lawsuit_pdf_contestacao_extensao_invalida(monkeypatch):
    """Contestacao rejeita extensao invalida antes do pipeline dedicado."""
    _e2e_infra(monkeypatch)
    extraction_repo = MagicMock()
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        learning_engine,
        "_extrair_contestacao",
        MagicMock(side_effect=AssertionError("extensao invalida nao deve chamar learning engine")),
    )
    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        MagicMock(side_effect=AssertionError("contestacao invalida nao deve usar sentence_finder")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("contestacao invalida nao deve usar Gemini padrao")),
    )
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-contestacao-ext-invalida-e2e",
        b"conteudo opaco",
        job_id="job-contestacao-ext-invalida-e2e",
        cache_context="contestacao",
        filename="contestacao.exe",
    )

    assert out["status"] == "erro"
    assert "Contest" in out["msg"]
    assert "PDF" in out["msg"] and "DOC" in out["msg"]
    proc.get_cache_repo().get_cache.assert_not_called()
    extraction_repo.save_extraction.assert_not_called()
    deduct_mock.assert_not_called()


def test_process_lawsuit_dossie_tres_arquivos_quadro_no_payload_final(monkeypatch):
    """Dossie com tres arquivos mescla quadro_comparativo no payload final."""
    _e2e_infra(monkeypatch)
    extraction_repo = MagicMock()
    extraction_repo.save_extraction.return_value = "doc-dossie-quadro-1"
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "_extrair_texto_arquivo_dossie",
        lambda nome, _content: f"Texto processual controlado do arquivo {nome}.",
    )

    cnj_stub = "2222222-22.2024.5.02.0002"
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        _make_gemini_stub(
            "mock-dossie-principal",
            _strict_qualidade_data(cnj_stub),
        ),
    )

    quadro_mock = MagicMock(
        return_value={
            "quadro_comparativo": [
                {
                    "verba_alvo": "Horas extras",
                    "resumo_pedido": "Pedido de horas extras na inicial.",
                    "resumo_defesa": "Defesa nega sobrejornada.",
                    "resumo_decisao": "Sentenca deferiu parcialmente.",
                    "status_final": "Deferida parcialmente",
                }
            ],
            "model_used": "mock-quadro-dossie",
            "error": None,
        }
    )
    monkeypatch.setattr(ai_client, "extrair_quadro_comparativo_dossie", quadro_mock)

    _stub_parecer(monkeypatch)
    monkeypatch.setattr(proc, "gerar_memoria", MagicMock())
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    partials: list[tuple[Any, str]] = []
    monkeypatch.setattr(
        proc,
        "_emit_ws_partial",
        lambda _job_id, payload, message: partials.append((payload, message)),
    )

    from workers.processor import process_lawsuit_dossie

    files = [
        ("inicial.pdf", b"%PDF inicial"),
        ("contestacao.pdf", b"%PDF contestacao"),
        ("sentenca.pdf", b"%PDF sentenca"),
    ]
    out = process_lawsuit_dossie("user-dossie-quadro-e2e", files, job_id="job-dossie-quadro")

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "completo"
    assert out["model_used"] == "mock-dossie-principal"
    assert out["qualidade_ok"] is True
    assert out["data"]["numero_processo"] == cnj_stub
    assert out["data"]["quadro_comparativo"][0]["verba_alvo"] == "Horas extras"
    assert out["data"]["quadro_comparativo"][0]["status_final"] == "Deferida parcialmente"

    quadro_mock.assert_called_once()
    texto_quadro = quadro_mock.call_args[0][0]
    assert "IN" in texto_quadro.upper()
    assert "inicial.pdf" in texto_quadro
    assert "contestacao.pdf" in texto_quadro
    assert "sentenca.pdf" in texto_quadro
    proc.get_cache_repo().save_cache.assert_called_once()
    extraction_repo.save_extraction.assert_called_once()
    deduct_mock.assert_called_once_with("user-dossie-quadro-e2e")
    assert any("DOSSI" in message.upper() for _payload, message in partials)


def test_process_lawsuit_dossie_dois_arquivos_sem_quadro_no_payload_final(monkeypatch):
    """Dossie com dois arquivos nao chama IA de quadro e mantem quadro vazio no payload final."""
    _e2e_infra(monkeypatch)
    extraction_repo = MagicMock()
    extraction_repo.save_extraction.return_value = "doc-dossie-sem-quadro-1"
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "_extrair_texto_arquivo_dossie",
        lambda nome, _content: f"Texto processual controlado do arquivo {nome}.",
    )

    cnj_stub = "3333333-33.2024.5.03.0003"
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        _make_gemini_stub(
            "mock-dossie-sem-quadro",
            _strict_qualidade_data(cnj_stub),
        ),
    )

    quadro_mock = MagicMock(side_effect=AssertionError("dois arquivos nao devem chamar quadro"))
    monkeypatch.setattr(ai_client, "extrair_quadro_comparativo_dossie", quadro_mock)

    _stub_parecer(monkeypatch)
    monkeypatch.setattr(proc, "gerar_memoria", MagicMock())
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    partials: list[tuple[Any, str]] = []
    monkeypatch.setattr(
        proc,
        "_emit_ws_partial",
        lambda _job_id, payload, message: partials.append((payload, message)),
    )

    from workers.processor import process_lawsuit_dossie

    files = [
        ("inicial.pdf", b"%PDF inicial"),
        ("sentenca.pdf", b"%PDF sentenca"),
    ]
    out = process_lawsuit_dossie("user-dossie-sem-quadro-e2e", files, job_id="job-dossie-sem-quadro")

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "completo"
    assert out["model_used"] == "mock-dossie-sem-quadro"
    assert out["qualidade_ok"] is True
    assert out["data"]["numero_processo"] == cnj_stub
    assert out["data"]["quadro_comparativo"] == []

    quadro_mock.assert_not_called()
    proc.get_cache_repo().save_cache.assert_called_once()
    extraction_repo.save_extraction.assert_called_once()
    deduct_mock.assert_called_once_with("user-dossie-sem-quadro-e2e")
    assert any("DOSSI" in message.upper() for _payload, message in partials)


def test_process_lawsuit_dossie_quadro_falha_nao_bloqueia_fluxo(monkeypatch):
    """Falha nao critica da IA de quadro em dossie nao deve bloquear o resultado principal."""
    _e2e_infra(monkeypatch)
    extraction_repo = MagicMock()
    extraction_repo.save_extraction.return_value = "doc-dossie-quadro-falha-1"
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "_extrair_texto_arquivo_dossie",
        lambda nome, _content: f"Texto processual controlado do arquivo {nome}.",
    )

    cnj_stub = "4444444-44.2024.5.04.0004"
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        _make_gemini_stub(
            "mock-dossie-quadro-falha",
            _strict_qualidade_data(cnj_stub),
        ),
    )

    quadro_mock = MagicMock(side_effect=RuntimeError("falha fake quadro"))
    monkeypatch.setattr(ai_client, "extrair_quadro_comparativo_dossie", quadro_mock)

    _stub_parecer(monkeypatch)
    monkeypatch.setattr(proc, "gerar_memoria", MagicMock())
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    partials: list[tuple[Any, str]] = []
    monkeypatch.setattr(
        proc,
        "_emit_ws_partial",
        lambda _job_id, payload, message: partials.append((payload, message)),
    )

    from workers.processor import process_lawsuit_dossie

    files = [
        ("inicial.pdf", b"%PDF inicial"),
        ("contestacao.pdf", b"%PDF contestacao"),
        ("sentenca.pdf", b"%PDF sentenca"),
    ]
    out = process_lawsuit_dossie("user-dossie-quadro-falha-e2e", files, job_id="job-dossie-quadro-falha")

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "completo"
    assert out["model_used"] == "mock-dossie-quadro-falha"
    assert out["qualidade_ok"] is True
    assert out["data"]["numero_processo"] == cnj_stub
    assert out["data"]["quadro_comparativo"] == []

    quadro_mock.assert_called_once()
    proc.get_cache_repo().save_cache.assert_called_once()
    extraction_repo.save_extraction.assert_called_once()
    deduct_mock.assert_called_once_with("user-dossie-quadro-falha-e2e")
    assert any("DOSSI" in message.upper() for _payload, message in partials)


def test_process_lawsuit_dossie_cache_hit_qualificado(monkeypatch):
    """Cache valido de dossie evita extracao de texto e chamadas de IA."""
    cached = _strict_qualidade_data(
        "5555555-55.2024.5.05.0005",
        _meta_doc_type="completo",
        quadro_comparativo=[
            {
                "verba_alvo": "Horas extras",
                "resumo_pedido": "Pedido em cache",
                "resumo_defesa": "Defesa em cache",
                "resumo_decisao": "Decisao em cache",
                "status_final": "Deferida",
            }
        ],
    )

    repo = _e2e_infra(monkeypatch)
    repo.get_cache.return_value = cached
    extraction_repo = MagicMock()
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "_extrair_texto_arquivo_dossie",
        MagicMock(side_effect=AssertionError("cache hit dossie nao deve extrair texto")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("cache hit dossie nao deve chamar IA principal")),
    )
    monkeypatch.setattr(
        ai_client,
        "extrair_quadro_comparativo_dossie",
        MagicMock(side_effect=AssertionError("cache hit dossie nao deve chamar IA de quadro")),
    )
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    from workers.processor import process_lawsuit_dossie

    files = [
        ("inicial.pdf", b"%PDF inicial"),
        ("contestacao.pdf", b"%PDF contestacao"),
        ("sentenca.pdf", b"%PDF sentenca"),
    ]
    out = process_lawsuit_dossie("user-dossie-cache-e2e", files, job_id="job-dossie-cache")

    assert out == {
        "status": "sucesso",
        "source": "cache",
        "doc_type": "completo",
        "data": cached,
    }
    repo.get_cache.assert_called_once()
    repo.save_cache.assert_not_called()
    extraction_repo.save_extraction.assert_not_called()
    deduct_mock.assert_not_called()


def test_process_lawsuit_dossie_cache_invalido_reprocessa(monkeypatch):
    """Cache insuficiente de dossie deve cair no fluxo de reprocessamento."""
    cached_invalido = {
        "_meta_doc_type": "completo",
        "numero_processo": "5555555-55.2024.5.05.0005",
        "reclamante": "Autor Cache Invalido",
        "verbas_deferidas": [],
    }

    repo = _e2e_infra(monkeypatch)
    repo.get_cache.return_value = cached_invalido
    extraction_repo = MagicMock()
    extraction_repo.save_extraction.return_value = "doc-dossie-cache-invalido-1"
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    texto_mock = MagicMock(
        side_effect=lambda nome, _content: f"Texto reprocessado do arquivo {nome}."
    )
    monkeypatch.setattr(proc, "_extrair_texto_arquivo_dossie", texto_mock)

    cnj_stub = "6666666-66.2024.5.06.0006"
    gemini_mock = MagicMock(
        return_value=_gemini_response(
            "mock-dossie-cache-invalido",
            _strict_qualidade_data(cnj_stub),
        )
    )
    monkeypatch.setattr(proc, "extract_data_with_gemini", gemini_mock)

    quadro_mock = MagicMock(
        return_value={
            "quadro_comparativo": [
                {
                    "verba_alvo": "Horas extras",
                    "resumo_pedido": "Pedido reprocessado",
                    "resumo_defesa": "Defesa reprocessada",
                    "resumo_decisao": "Decisao reprocessada",
                    "status_final": "Deferida",
                }
            ],
            "model_used": "mock-quadro-cache-invalido",
            "error": None,
        }
    )
    monkeypatch.setattr(ai_client, "extrair_quadro_comparativo_dossie", quadro_mock)

    _stub_parecer(monkeypatch)
    monkeypatch.setattr(proc, "gerar_memoria", MagicMock())
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    from workers.processor import process_lawsuit_dossie

    files = [
        ("inicial.pdf", b"%PDF inicial"),
        ("contestacao.pdf", b"%PDF contestacao"),
        ("sentenca.pdf", b"%PDF sentenca"),
    ]
    out = process_lawsuit_dossie(
        "user-dossie-cache-invalido-e2e",
        files,
        job_id="job-dossie-cache-invalido",
    )

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "completo"
    assert out["model_used"] == "mock-dossie-cache-invalido"
    assert out["qualidade_ok"] is True
    assert out["data"]["numero_processo"] == cnj_stub
    assert out["data"]["quadro_comparativo"][0]["verba_alvo"] == "Horas extras"

    assert texto_mock.call_count == 3
    gemini_mock.assert_called_once()
    quadro_mock.assert_called_once()
    repo.save_cache.assert_called_once()
    extraction_repo.save_extraction.assert_called_once()
    deduct_mock.assert_called_once_with("user-dossie-cache-invalido-e2e")


def test_process_lawsuit_dossie_saldo_esgotado_para_antes_de_cache_texto_ia(monkeypatch):
    """Saldo esgotado em dossie deve parar antes de cache, extracao de texto e IAs."""
    monkeypatch.setattr(proc, "get_user_credits", lambda _uid: 0)

    cache_repo = MagicMock()
    monkeypatch.setattr(proc, "get_cache_repo", lambda: cache_repo)
    extraction_repo = MagicMock()
    monkeypatch.setattr(proc, "get_extraction_repo", lambda tenant_id: extraction_repo)

    monkeypatch.setattr(
        proc,
        "_extrair_texto_arquivo_dossie",
        MagicMock(side_effect=AssertionError("sem saldo nao deve extrair texto")),
    )
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        MagicMock(side_effect=AssertionError("sem saldo nao deve chamar IA principal")),
    )
    monkeypatch.setattr(
        ai_client,
        "extrair_quadro_comparativo_dossie",
        MagicMock(side_effect=AssertionError("sem saldo nao deve chamar IA de quadro")),
    )
    deduct_mock = MagicMock()
    monkeypatch.setattr(proc, "deduct_credit", deduct_mock)

    from workers.processor import process_lawsuit_dossie

    out = process_lawsuit_dossie(
        "user-dossie-sem-saldo-e2e",
        [
            ("inicial.pdf", b"%PDF inicial"),
            ("contestacao.pdf", b"%PDF contestacao"),
            ("sentenca.pdf", b"%PDF sentenca"),
        ],
        job_id="job-dossie-sem-saldo",
    )

    assert out["status"] == "erro"
    assert "Saldo esgotado" in out["msg"]
    cache_repo.get_cache.assert_not_called()
    cache_repo.save_cache.assert_not_called()
    extraction_repo.save_extraction.assert_not_called()
    deduct_mock.assert_not_called()


def test_process_lawsuit_pdf_sentenca_caminho_feliz_ia_mockada(monkeypatch):
    """
    Segundo caminho feliz e2e: doc_type sentenca.

    Contrato:
      - Mesmos mocks de infra (crédito, quota, cache miss, parecer stubado).
      - extract_sentence_from_pdf -> (texto, \"sentenca\").
      - Stub Gemini com _CAMPOS_OBRIGATORIOS (processor), salario_base e >= 3 verbas.
      - Sem API real.
    """
    texto_fixture = (
        "Sentenca — Processo 0000000-00.0000.0.00.0000\n"
        "Reclamante X vs Reclamada Y. Data da sentenca 01/01/2024.\n"
        "DISPOSITIVO: Ante o exposto...\n"
    )
    cnj = "0000000-00.0000.0.00.0000"

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "sentenca"),
    )

    chamadas: list[int] = []
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        _make_gemini_stub(
            "mock-e2e-sentenca",
            _strict_qualidade_data(cnj),
            on_call=lambda *a: chamadas.append(1),
        ),
    )

    _stub_parecer(monkeypatch, "parecer stub sentenca")

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf("user-e2e-sentenca", b"%PDF-1.5\n", job_id="job-e2e-sentenca")

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "sentenca"
    assert out["model_used"] == "mock-e2e-sentenca"
    assert out.get("qualidade_ok") is True
    assert len(chamadas) == 1

    data = out["data"]
    assert data.get("numero_processo") == cnj
    assert data.get("salario_base") == "R$ 1.500,00"
    assert len(data.get("verbas_deferidas") or []) >= 3


def test_process_lawsuit_pdf_acordao_caminho_feliz_ia_mockada(monkeypatch):
    """
    Caminho feliz e2e: doc_type acordao (mesmo gate _qualidade_ok que sentenca).

    Fixture neutra: sem CNJ de capa, partes, vara, JG, assinatura PJe ou rito — evita merge HIGH.
    """
    texto_fixture = (
        "Acordao do TRT — trecho minimo para pipeline e2e.\n"
        "Corpo sem linhas que acionem pre_extract HIGH.\n"
    )
    cnj = "0000000-00.0000.0.00.0000"

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "acordao"),
    )

    chamadas: list[int] = []
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        _make_gemini_stub(
            "mock-e2e-acordao",
            _strict_qualidade_data(cnj),
            on_call=lambda *a: chamadas.append(1),
        ),
    )

    _stub_parecer(monkeypatch, "parecer stub acordao")

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf("user-e2e-acordao", b"%PDF-1.4\n", job_id="job-e2e-acordao")

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "acordao"
    assert out["model_used"] == "mock-e2e-acordao"
    assert out.get("qualidade_ok") is True
    assert len(chamadas) == 1
    assert out["data"].get("numero_processo") == cnj


def test_process_lawsuit_pdf_embargos_caminho_feliz_ia_mockada(monkeypatch):
    """
    Caminho feliz e2e: doc_type embargos.

    `_qualidade_ok`: sem ramo específico — exige `_CAMPOS_OBRIGATORIOS` e ≥3 verbas (como sentenca).
    """
    texto_fixture = (
        "Embargos de declaracao — trecho minimo para pipeline e2e.\n"
        "Corpo sem linhas que acionem pre_extract HIGH.\n"
    )
    cnj = "0000000-00.0000.0.00.0000"

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "embargos"),
    )

    chamadas: list[int] = []
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        _make_gemini_stub(
            "mock-e2e-embargos",
            _strict_qualidade_data(cnj),
            on_call=lambda *a: chamadas.append(1),
        ),
    )

    _stub_parecer(monkeypatch, "parecer stub embargos")

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf("user-e2e-embargos", b"%PDF-1.4\n", job_id="job-e2e-embargos")

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "embargos"
    assert out["model_used"] == "mock-e2e-embargos"
    assert out.get("qualidade_ok") is True
    assert len(chamadas) == 1
    assert out["data"].get("numero_processo") == cnj


def test_process_lawsuit_pdf_despacho_caminho_feliz_ia_mockada(monkeypatch):
    """
    Caminho feliz e2e: doc_type despacho.

    `_qualidade_ok`: sem ramo específico — exige `_CAMPOS_OBRIGATORIOS` e ≥3 verbas (como sentenca/embargos).
    """
    texto_fixture = (
        "Despacho em execucao — trecho minimo para pipeline e2e.\n"
        "Corpo sem linhas que acionem pre_extract HIGH.\n"
    )
    cnj = "0000000-00.0000.0.00.0000"

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "despacho"),
    )

    chamadas: list[int] = []
    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        _make_gemini_stub(
            "mock-e2e-despacho",
            _strict_qualidade_data(cnj),
            on_call=lambda *a: chamadas.append(1),
        ),
    )

    _stub_parecer(monkeypatch, "parecer stub despacho")

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf("user-e2e-despacho", b"%PDF-1.4\n", job_id="job-e2e-despacho")

    assert out["status"] == "sucesso"
    assert out["source"] == "ai"
    assert out["doc_type"] == "despacho"
    assert out["model_used"] == "mock-e2e-despacho"
    assert out.get("qualidade_ok") is True
    assert len(chamadas) == 1
    assert out["data"].get("numero_processo") == cnj


def test_liquidacao_e2e_pre_high_sobrescreve_numero_e_log(capsys, monkeypatch):
    """
    Integração e2e mínima: pre_extract (HIGH) → merge pós-IA → observabilidade [PRE-HIGH].

    O texto contém um CNJ válido para regex do pré-extrator; a IA mockada devolve número divergente.
    """
    cnj_pre = "1234567-89.2023.5.03.0068"
    cnj_ia_errado = "2222222-22.2222.2.22.2222"

    texto_fixture = (
        f"Processo {cnj_pre}\n"
        "Liquidacao de sentenca — texto minimo para pre_extract.\n"
    )

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        lambda *a, **k: _gemini_response(
            "mock-e2e-prehigh",
            _liquidacao_data_minima(cnj_ia_errado),
        ),
    )

    _stub_parecer(monkeypatch)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-e2e-prehigh", b"%PDF-1.4\n", job_id="job-e2e-prehigh"
    )

    assert out["status"] == "sucesso"
    assert out["data"].get("numero_processo") == cnj_pre

    captured = capsys.readouterr().out
    assert "[PRE-HIGH]" in captured
    assert "numero_processo" in captured


def test_liquidacao_e2e_pre_high_sobrescreve_data_sentenca_e_log(capsys, monkeypatch):
    """Merge HIGH para data_sentenca (assinatura PJe no texto vs data errada da IA mockada)."""
    cnj = "1234567-89.2023.5.03.0068"
    data_high = "15/03/2024"
    data_ia_errada = "01/01/2020"

    texto_fixture = (
        f"Processo {cnj}\n"
        f"Assinado eletronicamente em {data_high}\n"
        "Liquidacao — corpo minimo.\n"
    )

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        lambda *a, **k: _gemini_response(
            "mock-e2e-prehigh-dt",
            _liquidacao_data_minima(cnj, data_sentenca=data_ia_errada),
        ),
    )

    _stub_parecer(monkeypatch)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-e2e-prehigh-dt", b"%PDF-1.4\n", job_id="job-e2e-prehigh-dt"
    )

    assert out["status"] == "sucesso"
    assert out["data"].get("data_sentenca") == data_high

    captured = capsys.readouterr().out
    assert "[PRE-HIGH]" in captured
    assert "data_sentenca" in captured


def test_liquidacao_e2e_pre_high_sobrescreve_reclamante_e_log(capsys, monkeypatch):
    """Merge HIGH para reclamante (rótulo de capa vs nome errado da IA mockada)."""
    cnj = "1234567-89.2023.5.03.0068"
    nome_high = "Maria Silva Oliveira"
    nome_ia_errado = "Fulano Inventado Pela IA"

    texto_fixture = (
        f"Processo {cnj}\n"
        f"Reclamante: {nome_high}\n"
        "Liquidacao — corpo minimo sem assinatura PJe neste trecho.\n"
    )

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        lambda *a, **k: _gemini_response(
            "mock-e2e-prehigh-rec",
            _liquidacao_data_minima(cnj, reclamante=nome_ia_errado),
        ),
    )

    _stub_parecer(monkeypatch)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-e2e-prehigh-rec", b"%PDF-1.4\n", job_id="job-e2e-prehigh-rec"
    )

    assert out["status"] == "sucesso"
    assert out["data"].get("reclamante") == nome_high

    captured = capsys.readouterr().out
    assert "[PRE-HIGH]" in captured
    assert "reclamante" in captured


def test_liquidacao_e2e_pre_high_sobrescreve_reclamada_e_log(capsys, monkeypatch):
    """Merge HIGH para reclamada (rótulo de capa vs nome errado da IA mockada)."""
    cnj = "1234567-89.2023.5.03.0068"
    empresa_high = "Indústria Beta Ltda"
    empresa_ia_errada = "Empresa Totalmente Errada S.A."

    texto_fixture = (
        f"Processo {cnj}\n"
        f"Reclamada: {empresa_high}\n"
        "Liquidacao — corpo minimo sem reclamante nem assinatura PJe.\n"
    )

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        lambda *a, **k: _gemini_response(
            "mock-e2e-prehigh-recl",
            _liquidacao_data_minima(
                cnj,
                reclamante=None,
                reclamada=empresa_ia_errada,
            ),
        ),
    )

    _stub_parecer(monkeypatch)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-e2e-prehigh-recl", b"%PDF-1.4\n", job_id="job-e2e-prehigh-recl"
    )

    assert out["status"] == "sucesso"
    assert out["data"].get("reclamada") == empresa_high

    captured = capsys.readouterr().out
    assert "[PRE-HIGH]" in captured
    assert "reclamada" in captured


def test_liquidacao_e2e_pre_high_sobrescreve_vara_trabalho_e_log(capsys, monkeypatch):
    """Merge HIGH para vara_trabalho (rótulo de capa vs valor errado da IA mockada)."""
    cnj = "1234567-89.2023.5.03.0068"
    vara_high = "3ª Vara do Trabalho de Belo Horizonte"
    vara_ia_errada = "1ª Vara do Trabalho de São Paulo"

    texto_fixture = (
        f"Processo {cnj}\n"
        f"Vara do Trabalho: {vara_high}\n"
        "Liquidacao — corpo minimo sem partes nem assinatura PJe.\n"
    )

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        lambda *a, **k: _gemini_response(
            "mock-e2e-prehigh-vara",
            _liquidacao_data_minima(
                cnj,
                reclamante=None,
                reclamada=None,
                vara_trabalho=vara_ia_errada,
            ),
        ),
    )

    _stub_parecer(monkeypatch)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-e2e-prehigh-vara", b"%PDF-1.4\n", job_id="job-e2e-prehigh-vara"
    )

    assert out["status"] == "sucesso"
    assert out["data"].get("vara_trabalho") == vara_high

    captured = capsys.readouterr().out
    assert "[PRE-HIGH]" in captured
    assert "vara_trabalho" in captured


def test_liquidacao_e2e_pre_high_sobrescreve_justica_gratuita_e_log(capsys, monkeypatch):
    """Merge HIGH para justica_gratuita (frase de defiro vs bool falso da IA mockada)."""
    cnj = "1234567-89.2023.5.03.0068"

    texto_fixture = (
        f"Processo {cnj}\n"
        "Defiro os benefícios da justiça gratuita.\n"
        "Liquidacao — corpo minimo sem partes, vara extra ou assinatura PJe.\n"
    )

    monkeypatch.setattr(proc, "get_user_credits", lambda _uid: 10)
    monkeypatch.setattr(proc, "quota_excedida", lambda _uid, _kind: False)

    repo = MagicMock()
    repo.get_cache.return_value = None
    monkeypatch.setattr(proc, "get_cache_repo", lambda: repo)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        lambda *a, **k: {
            "error": None,
            "model_used": "mock-e2e-prehigh-jg",
            "data": {
                "numero_processo": cnj,
                "reclamante": None,
                "reclamada": None,
                "justica_gratuita": False,
                "salario_base": None,
                "data_sentenca": None,
                "verbas_deferidas": [{"nome": "Horas extras", "status_final": "deferida"}],
            },
        },
    )

    monkeypatch.setattr(
        proc,
        "gerar_parecer_tecnico_completo",
        lambda _dados, _verbas: {
            "texto": "parecer stub",
            "parcelas": "",
            "model_used": "mock-parecer",
            "error": None,
        },
    )

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-e2e-prehigh-jg", b"%PDF-1.4\n", job_id="job-e2e-prehigh-jg"
    )

    assert out["status"] == "sucesso"
    assert out["data"].get("justica_gratuita") is True

    captured = capsys.readouterr().out
    assert "[PRE-HIGH]" in captured
    assert "justica_gratuita" in captured


def test_liquidacao_e2e_pre_high_sobrescreve_tipo_rito_e_log(capsys, monkeypatch):
    """Merge HIGH para tipo_rito (menção sumaríssimo no texto vs ordinário da IA mockada)."""
    cnj = "1234567-89.2023.5.03.0068"
    tipo_high = "Sumaríssimo"
    tipo_ia_errado = "Ordinário"

    texto_fixture = (
        f"Processo {cnj}\n"
        "Rito sumaríssimo.\n"
        "Liquidacao — corpo minimo sem JG, partes, vara ou assinatura PJe.\n"
    )

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        lambda *a, **k: _gemini_response(
            "mock-e2e-prehigh-rito",
            _liquidacao_data_minima(
                cnj,
                reclamante=None,
                reclamada=None,
                tipo_rito=tipo_ia_errado,
            ),
        ),
    )

    _stub_parecer(monkeypatch)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-e2e-prehigh-rito", b"%PDF-1.4\n", job_id="job-e2e-prehigh-rito"
    )

    assert out["status"] == "sucesso"
    assert out["data"].get("tipo_rito") == tipo_high

    captured = capsys.readouterr().out
    assert "[PRE-HIGH]" in captured
    assert "tipo_rito" in captured


def test_liquidacao_e2e_pre_high_merge_numero_e_reclamante_uma_linha(capsys, monkeypatch):
    """Dois campos HIGH corrigem a IA no mesmo merge; observabilidade em uma única linha."""
    cnj_high = "1234567-89.2023.5.03.0068"
    cnj_ia_errado = "2222222-22.2222.2.22.2222"
    nome_high = "Maria Silva Correta"
    nome_ia_errado = "Fulano Errado IA"

    texto_fixture = (
        f"Processo {cnj_high}\n"
        f"Reclamante: {nome_high}\n"
        "Liquidacao — minimo sem reclamada, vara, JG, rito ou assinatura PJe.\n"
    )

    _e2e_infra(monkeypatch)

    monkeypatch.setattr(
        proc,
        "extract_sentence_from_pdf",
        lambda _b: (texto_fixture, "liquidacao"),
    )

    monkeypatch.setattr(
        proc,
        "extract_data_with_gemini",
        lambda *a, **k: _gemini_response(
            "mock-e2e-prehigh-2",
            _liquidacao_data_minima(
                cnj_ia_errado,
                reclamante=nome_ia_errado,
            ),
        ),
    )

    _stub_parecer(monkeypatch)

    from workers.processor import process_lawsuit_pdf

    out = process_lawsuit_pdf(
        "user-e2e-prehigh-2", b"%PDF-1.4\n", job_id="job-e2e-prehigh-2"
    )

    assert out["status"] == "sucesso"
    assert out["data"].get("numero_processo") == cnj_high
    assert out["data"].get("reclamante") == nome_high

    captured = capsys.readouterr().out
    assert captured.count("[PRE-HIGH]") == 1
    pre_lines = [ln for ln in captured.splitlines() if "[PRE-HIGH]" in ln]
    assert len(pre_lines) == 1
    assert "numero_processo" in pre_lines[0]
    assert "reclamante" in pre_lines[0]

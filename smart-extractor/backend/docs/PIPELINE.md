# Pipeline de extração — workers/processor.py

Referência única para os 10 passos. Não alterar a ordem ou os contratos sem análise arquitetural.

## Visão geral

| # | Etapa | Módulo / Ação | Saída típica |
|---|--------|----------------|--------------|
| 1 | Freemium | `database.get_user_credits` | Continua ou retorna erro. |
| 2 | Cache | `_hash_pdf` → `pdf_cache_storage_key(hash, cache_context)` → `get_cache`; `_qualidade_ok` | Se OK, retorno imediato com dados em cache. Com `cache_context=auto` (padrão) a chave é só o hash (compatível com entradas antigas; ver `services/cache_key.py`). |
| 3 | Extração de texto | `sentence_finder.extract_sentence_from_pdf` | `(texto, doc_type)` — bloco decisório + capa; texto pode incluir **anexos** (páginas fora do recorte com sinais de modificativa/liquidação/recurso ou parâmetros/acordo/ata), com tetos por categoria. |
| 4 | Playbook | `_load_skill(skill_file)` por `doc_type` | String do playbook .md. |
| 5 | IA | `pre_extract(texto)` + `ai_client.extract_data_with_gemini(texto, playbook, pre_fields=...)` | `{ "data", "error", "model_used" }`. Campos MEDIUM do pré-extrator entram como âncoras no prompt; HIGH não vai ao prompt como autoridade final. |
| 6 | Pós-IA | `_validate_result(ai_result["data"])` + `_aplicar_pre_high(dados, pre_fields["high"])` | Dict limpo + derivações (jornada, divisor_horas, prescrição, evolucao_salarial). Campos HIGH whitelisted sobrescrevem a IA quando válidos e emitem `[PRE-HIGH]` se houver mudança real. |
| 6b | Deduplicação | `deduplicar_verbas(verbas)` (jurisprudencia) | `verbas_dedup`, `avisos_dedup`. |
| 7 | Pydantic | `ProcessoTrabalhista(**dados_limpos)` | `dados_finais` (dict). |
| 7c | Ancoragem de fonte | `verba_page_anchor.anchor_verbas_to_pages(texto, verbas)` (após merge regex no cabeçalho) | `pagina_origem` em `verbas_deferidas`: match completo → prefixos → prefixo+sufixo (mesma página) → texto compacto alfanum. → `rapidfuzz.partial_ratio` com score/gap mínimos. |
| 8 | Validação jurídica | `validar_dados(dados_finais)` + `_RULE_ENGINE.executar(dados_finais)` + `gerar_explicacoes(...)` | `alertas_juridicos`, `regras_aplicadas`, `memorial_juridico`, `explicacoes`. |
| 8d | Shadow (KB) | `executar_shadow_pipeline(dados_finais)` após parecer | `shadow_logs`: lista de hits de regras dinâmicas com `status=shadow` (mesmo tenant); não altera alertas de UI. Corre também no fluxo **petição inicial**. Hits por execução via `ContextoJuridico.shadow_hits`. |
| 9 | Persistência | `_qualidade_ok` → `save_cache`, `save_extraction`, `deduct_credit` | Cache e extração gravados. |
| 10 | Memória de cálculo | `memoria_calculo.gerar_memoria(job_id, dados, ...)` | Arquivo `memoria_{job_id}.json`. |

## Debug do pipeline de texto (opcional)

Com `DEBUG_PIPELINE=1` em `backend/.env` (ver `config.py`), o terminal recebe linhas `[DEBUG-PIPELINE]` com tamanho/hash e snippets após: **passo 3** (`step3_sentence_finder` ou `step3_dossie_supercontexto`), e dentro de `ai_client._call_model`: **antes** de `_remove_duplicatas`, **depois** da deduplicação, **depois** de `_smart_truncate_after_dedup`. Se o texto após dedup **ultrapassar** `max_chars`, `_smart_truncate_after_dedup` emite `[DEBUG-PIPELINE][truncate]` com `parte1_chars`/`parte2_chars`, e ou `dispositivo_encontrado=True` + `disp_pos`/`start2`/`end2`, ou `dispositivo_encontrado=False` + fallback de verbas (`matches_verbas`). O `job_id`/`user_id` vêm de `pipeline_debug_meta` passado ao Gemini. Opcional: `DEBUG_PIPELINE_DUMP=1` grava `.txt` em `PIPELINE_DEBUG_OUT` (padrão `backend/pipeline_debug_out/`); dados sensíveis — só em ambiente seguro. Módulo: `services/pipeline_debug.py` (`log_truncate_*`).

## Dependências entre passos

- 2 depende de 1 (crédito já verificado).
- 4 depende de 3 (doc_type).
- 5 depende de 3 e 4 (texto + playbook).
- 6 depende de 5; 6b depende de 6 (verbas).
- 7 depende de 6 e 6b.
- 7c depende de 7, do texto do passo 3 e da lista de verbas (usa marcadores `--- PÁGINA N ---`).
- 8 depende de 7 e 7c (dados_finais com páginas, quando aplicável).
- 9 depende de 7 e 8 (dados + qualidade).
- 8d (shadow) depende de dados estáveis e do KB do tenant; corre após parecer no `_executar_pipeline_pos_ia` e na petição inicial.
- 10 depende de 7, 8 e do resultado da IA (model_used, doc_type, explicacoes); inclui `shadow_logs` no JSON de memória.

## Fluxo petição inicial (`cache_context=peticao_inicial`)

Quando `process_lawsuit_pdf(..., cache_context="peticao_inicial", filename=...)` ou `POST /api/extract` / `POST /upload` com Form `cache_context=peticao_inicial` (um único PDF/DOC/DOCX elegível), o processador usa `_pipeline_peticao_inicial`: cache `{hash}:peticao_inicial`, extração `learning_engine._extrair_peticao_inicial`, `memorial_juridico` via `memorial_pedidos.gerar_memorial_pedidos` (inclui `trecho_fundamentacao` por pedido quando houver), **sem** passo 8 completo de motor de sentença. **`data`** inclui `_meta_doc_type=peticao_inicial` para Excel (`excel_exporter` ramifica abas/nomes) e UI (`AnalysisReport`: sem PJC, Excel de pedidos). `POST /api/export/excel`: ficheiro `Pedidos_Inicial_*.xlsx` e corpo preserva `memorial_juridico` só nesse caso. Com `auto`, `/upload` inalterado para PDF único vs. dossiê.

## Fluxo contestação (`cache_context=contestacao`)

Quando `cache_context=contestacao` (um único PDF/DOC/DOCX), o processador usa `_pipeline_contestacao`: chave `{hash}:contestacao`, IA via `learning_engine._extrair_contestacao` (JSON com `teses_defesa` + campos legados derivados para o Lab), `ProcessoTrabalhista.teses_defesa`, ancoragem com `learning_engine._extrair_texto_arquivo_com_marcadores_pagina` + `anchor_verbas_to_pages` nos itens de tese (`trecho_fundamentacao`), `memorial_juridico` via `memorial_pedidos.gerar_memorial_defesa`, **sem** motor de sentença (como a petição). `_qualidade_ok(..., "contestacao")` exige ≥1 tese. **`SCHEMA_VERSION=2.14`** inclui `teses_defesa`. Shadow: `executar_shadow_pipeline` grava `shadow_logs`. Excel/UI: `_meta_doc_type=contestacao`, aba "Teses de defesa", download `Contestacao_*.xlsx`; UI sem PJC nem quadro de verbas deferidas.

## Contratos que não devem ser quebrados

- **Entrada de `process_lawsuit_pdf`**: `(user_id: str, file_bytes: bytes, job_id: str)`; kwargs opcionais `cache_context: str = "auto"`, `filename: str = "documento.pdf"` (API síncrona passa o nome real do ficheiro).
- **Retorno**: dict com `status`, `data`, `alertas_juridicos`, `regras_aplicadas`, `memorial_juridico`, `explicacoes`, e demais campos documentados no README.
- **Validação jurídica**: `legal_validator.validar_dados(dados)` retorna `list[str]`; `validar_dados_completo(dados)` retorna dict com `alertas`, `regras_aplicadas`, `memorial_juridico`.
- **Upload async**: `POST /upload` retorna `job_id` e `queued`; clientes acompanham por `GET /status/{job_id}` ou `WebSocket /ws/{job_id}`. O WS envia o dict do job como mensagem terminal (`status=done/error/timeout/...`) e pode enviar eventos `{"type":"partial_update","payload":...}` antes do terminal.
- **Export por job**: `GET /export-excel/{job_id}` só exporta job finalizado com resultado dict; job ausente, em processamento, em erro, resultado inválido e falha do exporter têm respostas HTTP próprias cobertas por `tests/test_extraction_cycle_export_job_excel.py`.

Para alterar um passo, verificar testes em `tests/` e `tests/jurisprudencia/` e rodar `pytest -q` após a mudança.

**Nota:** O Laboratório de Aprendizado (`learning_engine.py` como facade; módulos `services/lab/learning_io.py`, `services/lab/extractors.py`, `services/lab/self_healing.py` — codify e Shadow Rules) possui fluxo próprio (analisar, preview, salvar, codify); ver `CODE_MAP.md` e `AI_NAVIGATION_LAYER.md` § 2.9 e § 2.10.

**Nota de implementação:** Os passos 4b–10 são compartilhados entre `process_lawsuit_pdf` e `process_lawsuit_dossie` via função privada `_executar_pipeline_pos_ia` em `processor.py`. Alterações nesses passos devem ser feitas nessa função única.

## Dossiê multi-arquivo — quadro comparativo (≥3 ficheiros)

Após o passo 6b (deduplicação de verbas), se `len(files_list) >= 3`, o processador chama **`services.ai_client.extrair_quadro_comparativo_dossie(texto)`** (2ª chamada Gemini, prompt dedicado). O resultado normalizado preenche `dados_limpos["quadro_comparativo"]` antes de `_executar_pipeline_pos_ia`. Heurística: três ou mais anexos costumam corresponder a conjunto inicial + defesa + decisão (ou equivalente); a síntese é por IA sobre o super-texto já concatenado. **`SCHEMA_VERSION=2.15`**. O `doc_type` retornado para o dossiê permanece **`completo`** (sem mudança de contrato HTTP).

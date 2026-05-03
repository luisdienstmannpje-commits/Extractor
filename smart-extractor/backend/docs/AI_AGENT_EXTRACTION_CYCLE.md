# Ciclo de Extracao Incremental com IA Agents

Este documento e o ponto de coordenacao entre Codex, Cursor Agent e o usuario.
Antes de codificar melhorias de extracao, leia este arquivo e siga o ciclo abaixo.

## Regra principal

Trabalhar em apenas **um dado-alvo por ciclo**.

Nao misturar correcao de `numero_processo`, `reclamante`, datas, salario e verbas no mesmo patch.
Cada ciclo deve terminar com teste focado passando e uma indicacao clara do proximo campo.

## Protocolo de conversa com Cursor

Quando o Cursor Agent assumir uma tarefa, ele deve:

1. Ler este arquivo.
2. Ler o teste do ciclo atual.
3. Confirmar se concorda com o dado-alvo e o criterio de aceite.
4. Fazer a menor alteracao possivel.
5. Rodar o teste focado.
6. Registrar, no fim da resposta, uma destas decisoes:
   - `APROVADO`: teste passou e podemos seguir para o proximo dado.
   - `BLOQUEADO`: explicar o motivo e qual contexto falta.
   - `DISCORDO`: explicar uma alternativa tecnicamente melhor antes de codificar.

## Ciclo de trabalho

1. Escolher dado-alvo.
2. Criar fixture pequena, preferencialmente texto com marcadores de pagina.
3. Criar teste automatizado com expectativa objetiva.
4. Rodar apenas o teste do ciclo.
5. Corrigir regex, parser, normalizador ou prompt no menor escopo possivel.
6. Rodar teste focado.
7. Rodar uma suite curta de regressao.
8. Registrar proximo dado-alvo.

## Ordem sugerida dos dados

1. `numero_processo`
2. `reclamante`
3. `reclamada`
4. `vara_trabalho`
5. `data_ajuizamento`
6. `data_sentenca`
7. `data_admissao`
8. `data_demissao`
9. `salario_base`
10. `verbas_deferidas[].nome`
11. `verbas_deferidas[].periodo`
12. `verbas_deferidas[].reflexos`
13. `indice_correcao`
14. `juros_mora`
15. `divisor_horas`
16. `aviso_previo_dias` (pos-ordem sugerida — MEDIUM remanescente)
17. `motivo_rescisao`
18. `tipo_contrato`
19. `justica_gratuita` (HIGH remanescente)
20. `tipo_rito` (HIGH remanescente)
21. Integração `pre_extract` → `extract_data_with_gemini` / `processor`
22. Merge pós-IA `pre_fields["high"]` → `dados_limpos`

## Ciclo atual

- Status: `APROVADO` (Codex).
- Dado-alvo concluido: **revisao documental pos-ciclos** — README raiz, README backend, `.cursorrules`, `AI_RULES`, `PIPELINE`, `SYSTEM_OVERVIEW`, `CODE_MAP`, `CODE_INTELLIGENCE_MAP`, `DEVELOPER` e docstring de exportacao foram alinhados aos contratos ja testados (`pre_extract` MEDIUM/HIGH, upload/status/WS, `cache_context`, export API e export por job).
- Camada: documentacao / regras de agentes; sem mudanca de comportamento de producao.
- Teste focado:
  - `python -m pytest -q tests/test_extraction_cycle_export_api.py tests/test_extraction_cycle_export_job_excel.py tests/test_extraction_cycle_upload_status_api.py`
- Resultado:
  - suite curta export/upload-status: `24 passed`.
  - `tests/test_extraction_cycle_*.py` -> `223 passed`.
  - suite completa backend: `1095 passed`.

## Proximo ciclo recomendado

- **Escolha sugerida:** revisar/automatizar contrato que ainda esteja pouco coberto fora dos ciclos atuais, antes de adicionar novos campos. Candidatos pequenos:
  - `GET /status/{job_id}` com job ausente/persistido em repo, se o comportamento ainda nao tiver teste HTTP dedicado.
  - `POST /api/extract` sincrono com `cache_context=peticao_inicial` ou `contestacao`, se quisermos simetria com `/upload`.
  - consolidacao leve de docs somente se novos ciclos alterarem contrato publico.

## Ciclos anteriores (referencia)

- **`/export-excel/{job_id}` com falha do exporter** — `test_export_excel_job_falha_exporter_retorna_500_estavel`.
- **`/export-excel/{job_id}` com resultado invalido** — `test_export_excel_job_resultado_invalido_retorna_400_sem_exporter`; corrigiu fallback `job["result"]`.
- **`/export-excel/{job_id}` com job em erro** — `test_export_excel_job_error_retorna_400_sem_exporter`.
- **`/export-excel/{job_id}` com job em processamento** — `test_export_excel_job_processing_retorna_202_sem_exporter`.
- **`/export-excel/{job_id}` com job ausente** — `test_export_excel_job_ausente_retorna_404_sem_exporter`.
- **Exportacao Excel por job_id (happy path)** — `test_export_excel_job_pronto_retorna_xlsx`.
- **Exportacao PJC com falha do exporter** — `test_export_pjc_falha_exporter_retorna_500_estavel`.
- **Exportacao PJC com corpo vazio/invalido** — `test_export_pjc_corpo_vazio_retorna_400_sem_exporter`.
- **Exportacao PJC via API (happy path)** — `test_export_pjc_happy_path_retorna_xml_com_headers`.
- **Exportacao Excel com falha do exporter** — `test_export_excel_falha_exporter_retorna_500_estavel`.
- **Exportacao Excel com corpo vazio/invalido** — `test_export_excel_corpo_vazio_retorna_400_sem_exporter`.
- **Exportacao Excel de `contestacao` via API** — `test_export_excel_contestacao_preserva_memorial_e_nome_especifico`.
- **Exportacao Excel de `peticao_inicial` via API** — `test_export_excel_peticao_preserva_memorial_e_nome_especifico`.
- **Exportacao Excel via API (sentenca/default)** — `test_export_excel_sentenca_limpa_campos_e_retornaxlsx`; corrigiu filename ASCII `Auditoria_Calculo_...xlsx`.
- **Saldo esgotado em dossie** — `test_process_lawsuit_dossie_saldo_esgotado_para_antes_de_cache_texto_ia`.
- **Cache invalido em dossie reprocessa** — `test_process_lawsuit_dossie_cache_invalido_reprocessa`.
- **Cache hit qualificado em dossie** — `test_process_lawsuit_dossie_cache_hit_qualificado`.
- **Falha nao critica da segunda IA de quadro em dossie** — `test_process_lawsuit_dossie_quadro_falha_nao_bloqueia_fluxo`.
- **Dossie com dois arquivos sem segunda IA de quadro** — `test_process_lawsuit_dossie_dois_arquivos_sem_quadro_no_payload_final`.
- **Dossie com tres arquivos e quadro comparativo no payload final** — `test_process_lawsuit_dossie_tres_arquivos_quadro_no_payload_final`.
- **Rejeicao direta de extensao invalida em `contestacao`** — `test_process_lawsuit_pdf_contestacao_extensao_invalida`.
- **Rejeicao direta de extensao invalida em `peticao_inicial`** — `test_process_lawsuit_pdf_peticao_inicial_extensao_invalida`.
- **Cache invalido em `contestacao`** — `test_process_lawsuit_pdf_contestacao_cache_invalido_reprocessa`.
- **Cache invalido em `peticao_inicial`** — `test_process_lawsuit_pdf_peticao_inicial_cache_invalido_reprocessa`.
- **Cache hit qualificado em `contestacao`** — `test_process_lawsuit_pdf_contestacao_cache_hit_qualificado`.
- **Cache hit qualificado em `peticao_inicial`** — `test_process_lawsuit_pdf_peticao_inicial_cache_hit_qualificado`.
- **Fluxo de negocio `contestacao` via `cache_context`** — `test_process_lawsuit_pdf_contestacao_cache_context_mockada`.
- **Fluxo de negocio `peticao_inicial` via `cache_context`** — `test_process_lawsuit_pdf_peticao_inicial_cache_context_mockada`.
- **Upload com extensao nao permitida** — `test_upload_extensao_nao_permitida_retorna_400_sem_processador`.
- **Upload de PDF menor que 10 bytes** — `test_upload_pdf_menor_que_10_bytes_retorna_400_sem_processador`.
- **Timeout do worker em `/upload` + `/ws/{job_id}`** — `test_upload_worker_timeout_websocket_terminal_error`.
- **Timeout do worker em `/upload` + `/status`** — `test_upload_worker_timeout_surfaces_error_on_status`.
- **WebSocket terminal de erro** após `/upload` — `test_upload_worker_exception_websocket_terminal_error`.
- **`/upload` + `/status` com falha do worker** — `test_upload_worker_exception_surfaces_error_on_status`.
- Consolidação leve helpers no mesmo arquivo HTTP/WS (`_post_minimal_upload_queued`, etc.); quatro cenários felizes/borda antes deste erro.
- WebSocket com `partial_update` antes do terminal — `test_upload_minimal_pdf_websocket_partial_then_terminal` (fake + `threading.Event` visível no teste).
- WebSocket terminal só (sem parcial) — `test_upload_minimal_pdf_websocket_terminal_happy_path`.
- HTTP borda `/upload` **`400`** — `peticao_inicial` com dois PDFs — `test_upload_peticao_inicial_dois_arquivos_retorna_400_sem_processador`.
- HTTP feliz `/upload` + `/status/{job_id}` — `test_upload_minimal_pdf_then_status_happy_path` no mesmo arquivo.
- Consolidação helpers em `tests/test_extraction_cycle_processor_e2e_mock_ia.py` (infra/payload IA); `13 passed` naquele arquivo.
- Testes existentes de roteamento **unitário** do upload (sem HTTP): `tests/test_upload_cache_context.py` — `_should_run_process_lawsuit_pdf_upload`.
- E2e mockado `doc_type == "despacho"` — `test_process_lawsuit_pdf_despacho_caminho_feliz_ia_mockada`.
- E2e mockado `doc_type == "embargos"` — `test_process_lawsuit_pdf_embargos_caminho_feliz_ia_mockada`.
- E2e **`liquidacao`** — merge HIGH **dois campos** (`numero_processo` + `reclamante`) numa linha `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_merge_numero_e_reclamante_uma_linha`.
- E2e mockado `doc_type == "acordao"` — `test_process_lawsuit_pdf_acordao_caminho_feliz_ia_mockada`.
- E2e merge HIGH `tipo_rito` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_tipo_rito_e_log`.
- E2e merge HIGH `justica_gratuita` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_justica_gratuita_e_log`.
- E2e merge HIGH `vara_trabalho` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_vara_trabalho_e_log`.
- E2e merge HIGH `reclamada` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_reclamada_e_log`.
- E2e merge HIGH `reclamante` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_reclamante_e_log`.
- E2e merge HIGH `data_sentenca` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_data_sentenca_e_log`.
- E2e merge HIGH `numero_processo` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_numero_e_log`.
- E2e mockado `doc_type == "sentenca"` — `test_process_lawsuit_pdf_sentenca_caminho_feliz_ia_mockada` no mesmo arquivo.
- Asserts estruturais no e2e `liquidacao` — mesmo arquivo `tests/test_extraction_cycle_processor_e2e_mock_ia.py`.
- E2e enxuto `process_lawsuit_pdf` + IA mockada (sem asserts estruturais extras) — evolução incremental no mesmo arquivo.
- Observabilidade merge HIGH (`[PRE-HIGH]`) — teste: `tests/test_extraction_cycle_pre_high_log.py` (`4 passed`).
- Merge pós-IA `pre_fields["high"]` — teste: `tests/test_extraction_cycle_merge_pre_high.py` (`6 passed`).
- Integração `pre_extract` → IA — teste: `tests/test_extraction_cycle_pre_ia_integration.py` (`1 passed`).
- `tipo_rito` — teste: `tests/test_extraction_cycle_tipo_rito.py` (`8 passed`).
- `justica_gratuita` — teste: `tests/test_extraction_cycle_justica_gratuita.py` (`11 passed`).
- `tipo_contrato` — teste: `tests/test_extraction_cycle_tipo_contrato.py` (`10 passed`).
- `motivo_rescisao` — teste: `tests/test_extraction_cycle_motivo_rescisao.py` (`11 passed`).
- `aviso_previo_dias` — teste: `tests/test_extraction_cycle_aviso_previo_dias.py` (`11 passed`).
- `divisor_horas` — teste: `tests/test_extraction_cycle_divisor_horas.py` (`11 passed`).
- `juros_mora` — teste: `tests/test_extraction_cycle_juros_mora.py` (`9 passed`).
- `indice_correcao` — teste: `tests/test_extraction_cycle_indice_correcao.py` (`9 passed`).
- `verbas_deferidas[].reflexos` (fase 3) — teste: `tests/test_extraction_cycle_verbas_reflexos.py` (`7 passed`).
- `verbas_deferidas[].periodo` (fase 2) — teste: `tests/test_extraction_cycle_verbas_periodo.py` (`8 passed`).
- `verbas_deferidas[].nome` (fase 1) — teste: `tests/test_extraction_cycle_verbas_nomes.py` (`6 passed`).
- `salario_base` — teste: `tests/test_extraction_cycle_salario_base.py` (`8 passed`).
- `data_demissao` — teste: `tests/test_extraction_cycle_data_demissao.py` (`8 passed`).
- `data_admissao` — teste: `tests/test_extraction_cycle_data_admissao.py` (`8 passed`).
- `data_sentenca` — teste: `tests/test_extraction_cycle_data_sentenca.py` (`9 passed`).
- `data_ajuizamento` — teste: `tests/test_extraction_cycle_data_ajuizamento.py` (`7 passed`).
- `vara_trabalho` — teste: `tests/test_extraction_cycle_vara_trabalho.py` (`6 passed`).
- `reclamada` — teste: `tests/test_extraction_cycle_reclamada.py` (`6 passed`).
- `reclamante` — teste: `tests/test_extraction_cycle_reclamante.py` (`5 passed`).
- `numero_processo` — `APROVADO` em 2026-05-01 por Codex; teste: `tests/test_extraction_cycle_numero_processo.py` (`3 passed`).

## Proximo ciclo proposto

- Dado-alvo sugerido: encerrar fio `/export-excel/{job_id}` e escolher novo fluxo de negocio (ex.: Lab/Ghostwriter ou auditoria PJC por job) — **um** objetivo por ciclo.
- Manter proibição de API real nos testes de ciclo.

## Mensagem recomendada para o Cursor

Cursor, revise `backend/docs/AI_AGENT_EXTRACTION_CYCLE.md` e os testes
`backend/tests/test_extraction_cycle_*.py`.

Suite `test_extraction_cycle_upload_status_api.py` ja cobre feliz, `400`, WS, parcial, erro e timeout. Matriz `cache_context` dedicada, fio dossie/quadro/cache/credito, fio Excel API e fio PJC API estao fechados. Fio `/export-excel/{job_id}` cobre happy path, job ausente 404, processing 202, error 400, result invalido 400 e falha exporter 500.
Crie primeiro o teste focado antes de alterar codigo.

Ao final, diga `APROVADO`, `BLOQUEADO` ou `DISCORDO`.

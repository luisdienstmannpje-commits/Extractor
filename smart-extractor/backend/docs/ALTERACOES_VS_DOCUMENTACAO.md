# Alterações feitas vs. documentação (README + docs/)

Este documento lista **apenas as alterações feitas no código** (configuração em nova máquina + preparação para Teste 1) e confirma se há risco de **regressão** ou **divergência** em relação ao que está descrito no README e na pasta `docs/`.

---

## 0. WebSocket terminal `error` após falha do worker (mock) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_upload_status_api.py`: `test_upload_worker_exception_websocket_terminal_error`; docstring do módulo (erro também no WS).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e próximo ciclo.

**Por quê**
- Mesmo envelope de erro do job entregue pelo WebSocket; corrida coberta pelo ramo imediato ou pela fila.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_upload_status_api.py::test_upload_worker_exception_websocket_terminal_error` → **1 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **191 passed**.

---

## 0. HTTP `/upload` + `/status` com exceção no worker (mock, sem Gemini) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_upload_status_api.py`: `test_upload_worker_exception_surfaces_error_on_status`; docstring do módulo sobre `_run_job_with_timeout`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e próximo ciclo sugerido.

**Por quê**
- Garantir que falha no thread do processor aparece como `status` terminal `error` e `msg` estável.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_upload_status_api.py::test_upload_worker_exception_surfaces_error_on_status` → **1 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **190 passed**.

---

## 0. Consolidação leve `test_extraction_cycle_upload_status_api.py` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_upload_status_api.py`: helpers de upload, limpeza de job e leitura WS; quatro testes mantidos explícitos.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual.

**Por quê**
- Menos duplicação sem esconder contratos por cenário.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_upload_status_api.py` → **4 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **189 passed**.

---

## 0. WebSocket `partial_update` antes do terminal (TestClient, Event) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_upload_status_api.py`: `test_upload_minimal_pdf_websocket_partial_then_terminal` (`push_ws_partial` dentro do fake + `threading.Event`).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e corrida fila WS / `_enqueue_ws_message`.

**Por quê**
- Garantir ordem parcial → terminal sem Gemini; sem Event, parcial pode perder-se se o worker correr antes do cliente registar a fila.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_upload_status_api.py` → **4 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **189 passed**.

---

## 0. WebSocket feliz `/ws/{job_id}` após upload (TestClient, IA mockada) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_upload_status_api.py`: `test_upload_minimal_pdf_websocket_terminal_happy_path`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e formato real das mensagens WS (sem `type: "result"`).

**Por quê**
- Contrato end-to-end upload → resultado terminal no WebSocket, sem Gemini; alinhado a `websocket_job` e `_ws_payload_is_terminal`.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_upload_status_api.py` → **3 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **188 passed**.

---

## 0. HTTP `/upload` borda `400` (peticao_inicial, dois ficheiros) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_upload_status_api.py`: `test_upload_peticao_inicial_dois_arquivos_retorna_400_sem_processador`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e nota sobre ordem job vs validação `_should_run_*`.

**Por quê**
- Contrato HTTP de rejeição antes do worker, alinhado a `test_upload_cache_context.test_peticao_multiplo_rejeita`; sem Gemini.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_upload_status_api.py` → **2 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **187 passed**.

---

## 0. E2e HTTP `/upload` + `/status/{job_id}` (TestClient, IA mockada) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_upload_status_api.py`: caminho feliz com `process_lawsuit_pdf` mockado no módulo `api.routers.extractor`; app FastAPI mínima (só router extractor + lifespan do event loop).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e referência a `test_upload_cache_context.py` (já existente, sem HTTP).

**Por quê**
- Cobrir fila + polling HTTP sem Gemini; `test_upload_cache_context.py` continua sendo só decisão de roteamento (`_should_run_process_lawsuit_pdf_upload`).

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_upload_status_api.py` → **1 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **186 passed**.

---

## 0. Consolidação e2e mock IA (helpers no arquivo de teste) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: helpers `_e2e_infra`, `_stub_parecer`, `_liquidacao_data_minima`, `_strict_qualidade_data`, `_gemini_response`, `_make_gemini_stub`; refatoração mecânica dos 13 testes.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual = consolidação; referência a `despacho` movida para ciclos anteriores.

**Por quê**
- Menos duplicação de mocks de infra e payloads IA, mantendo um teste por cenário e asserts explícitos.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_processor_e2e_mock_ia.py` → **13 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **185 passed**.

---

## 0. E2e mockado `doc_type == "despacho"` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_process_lawsuit_pdf_despacho_caminho_feliz_ia_mockada` (stub alinhado ao gate **default** de `_qualidade_ok`: obrigatórios + ≥3 verbas; sem branch `despacho`).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, próximo ciclo sugerido (HIGH triplo ou novo doc_type) e mensagem recomendada.

**Por quê**
- Cobrir caminho feliz do processor com tipo documental despacho sem API; playbook `despacho_execucao.md` já mapeado no processor; qualidade segue o bloco pós-`liquidacao`.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_despacho_caminho_feliz_ia_mockada` → **1 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **185 passed**.

---

## 0. E2e mockado `doc_type == "embargos"` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_process_lawsuit_pdf_embargos_caminho_feliz_ia_mockada` (stub alinhado ao gate **default** de `_qualidade_ok` para `embargos`: obrigatórios + ≥3 verbas).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, próximo ciclo sugerido (`despacho` ou HIGH triplo) e mensagem recomendada.

**Por quê**
- Cobrir caminho feliz do processor com tipo documental embargos sem API; documentar que não há branch específica em `_qualidade_ok` (mesma severidade que sentença/acórdão).

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_embargos_caminho_feliz_ia_mockada` → **1 passed**.
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **184 passed**.

---

## 0. E2e liquidacao — merge HIGH multi-campo (numero + reclamante) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_liquidacao_e2e_pre_high_merge_numero_e_reclamante_uma_linha`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, mensagem recomendada e próximo ciclo sugerido.

**Por quê**
- Garantir observabilidade e dados finais quando dois HIGH divergem da IA na mesma execução.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **183 passed**.

---

## 0. E2e mockado `doc_type == "acordao"` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_process_lawsuit_pdf_acordao_caminho_feliz_ia_mockada`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, mensagem recomendada e próximo ciclo sugerido.

**Por quê**
- Cobrir caminho feliz do processor com tipo documental acórdão e mesmo gate de qualidade que sentença, sem API.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **182 passed**.

---

## 0. E2e liquidacao — merge HIGH `tipo_rito` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_liquidacao_e2e_pre_high_sobrescreve_tipo_rito_e_log`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, mensagem recomendada (matriz `_HIGH_MERGE_KEYS` coberta) e próximo ciclo sugerido.

**Por quê**
- Último campo HIGH da whitelist com e2e isolado no processor mockado.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **181 passed**.

---

## 0. E2e liquidacao — merge HIGH `justica_gratuita` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_liquidacao_e2e_pre_high_sobrescreve_justica_gratuita_e_log`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, mensagem recomendada e próximo ciclo sugerido.

**Por quê**
- Cobrir campo booleano HIGH no pipeline e2e completo (regex vs IA).

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **180 passed**.

---

## 0. E2e liquidacao — merge HIGH `vara_trabalho` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_liquidacao_e2e_pre_high_sobrescreve_vara_trabalho_e_log`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, mensagem recomendada e próximo ciclo sugerido.

**Por quê**
- Cobrir o quinto campo whitelist HIGH de capa no pipeline e2e completo.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **179 passed**.

---

## 0. E2e liquidacao — merge HIGH `reclamada` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_liquidacao_e2e_pre_high_sobrescreve_reclamada_e_log`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, mensagem recomendada e próximo ciclo sugerido.

**Por quê**
- Quarto campo whitelist HIGH coberto no pipeline e2e completo.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **178 passed**.

---

## 0. E2e liquidacao — merge HIGH `reclamante` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_liquidacao_e2e_pre_high_sobrescreve_reclamante_e_log`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual, mensagem recomendada e próximo ciclo sugerido.

**Por quê**
- Cobrir terceiro campo whitelist HIGH no pipeline completo com fixture de capa PJe.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **177 passed**.

---

## 0. E2e liquidacao — merge HIGH `data_sentenca` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_liquidacao_e2e_pre_high_sobrescreve_data_sentenca_e_log`.
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e próximo ciclo sugerido.

**Por quê**
- Garantir segundo campo HIGH no pipeline completo (assinatura PJe vs IA mockada).

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **176 passed**.

---

## 0. E2e liquidacao — merge HIGH + log `[PRE-HIGH]` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: `test_liquidacao_e2e_pre_high_sobrescreve_numero_e_log` (IA mockada com CNJ errado; texto com CNJ para `pre_extract`; assert em `data` e stdout).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e próximo ciclo sugerido.

**Por quê**
- Fechar a malha e2e entre `pre_extract`, `_aplicar_pre_high` e observabilidade, sem `acordao` nem API real.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **175 passed**.

---

## 0. E2e mock IA — segundo caminho `sentenca` — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: novo teste `test_process_lawsuit_pdf_sentenca_caminho_feliz_ia_mockada` (stub com campos obrigatórios, `salario_base`, três verbas; `extract_sentence_from_pdf` → `sentenca`).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e próximo ciclo sugerido.

**Por quê**
- Cobrir o gate `_qualidade_ok` para sentença sem PDF real nem Gemini.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **174 passed**.

---

## 0. E2e mock IA — asserts estruturais na resposta — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: no mesmo teste do fluxo `liquidacao`, validação de tipos do envelope (`alertas_juridicos`, `regras_aplicadas`, `memorial_juridico`, `raiox`, `fontes_extracao`, `verbas_deferidas`).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e próximo ciclo sugerido (`sentenca`).

**Por quê**
- Detectar regressões no formato da resposta/API sem segundo arquivo ou chamada real ao Gemini.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_*.py` → **173 passed**.

---

## 0. E2E processor com IA mockada (ciclo de extração) — Abril/2026

**O que foi alterado**
- `tests/test_extraction_cycle_processor_e2e_mock_ia.py`: teste de fumaça de `process_lawsuit_pdf` com stubs de `extract_sentence_from_pdf`, `extract_data_with_gemini` e `gerar_parecer_tecnico_completo` (sem chamadas reais a API).
- `docs/AI_AGENT_EXTRACTION_CYCLE.md`: ciclo atual e contrato mínimo alinhados a esse teste.

**Por quê**
- Regressão cedo no caminho completo pós-upload simulado, sem PDF real nem Gemini.

**Impacto / ponto de falha**
- Se o teste falhar, verificar assinaturas/ordem de imports em `workers/processor.py` e se o pipeline pós-IA passou a exigir novos passos com chamadas externas (aí o teste deve estender os stubs).

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_processor_e2e_mock_ia.py` → **1 passed**.

---

## 0. Observabilidade merge HIGH (`[PRE-HIGH]`) — Abril/2026

**O que foi alterado**
- `workers/processor.py`: `_aplicar_pre_high` compara valor efetivo antes/depois por chave whitelist; se houver mudança, `print` de uma linha `[PRE-HIGH] campo1, campo2` (`flush=True`). Refatoração interna: atribuição via valor normalizado único (`novo`) para manter comparação e escrita alinhadas.

**Por quê**
- Auditoria em terminal quando o pré-extrator HIGH sobrescreve a saída da IA, sem depender de e2e com PDF.

**Impacto / ponto de falha**
- Servidor/worker: mais uma linha em stdout por merge que altere dado; não altera payload JSON.
- Se observabilidade sumir, verificar `_aplicar_pre_high` e `tests/test_extraction_cycle_pre_high_log.py`.

**Validação executada**
- `venv/Scripts/python.exe -m pytest -q tests/test_extraction_cycle_pre_high_log.py tests/test_extraction_cycle_merge_pre_high.py` → **10 passed**; suite `tests/test_extraction_cycle_*.py` + `test_processor_quality_gate.py` → **179 passed**.

---

## 0. Rastreabilidade por campo (`fontes_extracao`) — Março/2026

**O que foi alterado**
- `models.py`: `SCHEMA_VERSION` atualizado para `2.16`.
- `models.py`: novo modelo `FonteExtracao` e novo campo `ProcessoTrabalhista.fontes_extracao`.
- `workers/processor.py`: novo helper `_coletar_fontes_extracao(...)`, com geração de trilha de origem para:
  - campos de cabeçalho (`numero_processo`, partes, datas, `salario_base`, `valor_causa`);
  - `verbas_deferidas` (nome/período/observações);
  - `teses_defesa`;
  - `quadro_comparativo`;
  - `alertas_juridicos` (mapeamento heurístico para página via verba/campo relacionado).
- `workers/processor.py`: preenchimento de `fontes_extracao` nos fluxos:
  - pós-IA padrão (`_executar_pipeline_pos_ia`);
  - `peticao_inicial`;
  - `contestacao`.
- `frontend`: `AnalysisReport` passou a renderizar botão/fonte também no cabeçalho, consumindo `fontes_extracao`.
- `frontend`: `AnalysisReport` passou a renderizar fonte por alerta (`alertas_juridicos[i]`) quando houver página inferida.
- Refino de UX/diagnóstico: `fontes_extracao.confianca` (0–1) passou a ser preenchido para alertas inferidos; UI exibe badge discreto `conf. alta/média/baixa`.
- Refino de auditoria no frontend: seção de alertas ganhou filtro visual `Todos` / `Somente conf. alta`, para priorizar revisão dos alertas com melhor lastro de fonte.
- Persistência de UX: filtro de alertas agora é salvo em `localStorage` (`analysis_alerta_filtro`) e restaurado ao reabrir o relatório.
- Persistência de auditoria: cada alerta agora suporta `Expandir/Recolher` e o estado é salvo em `localStorage` (`analysis_alertas_expandidos`) para manter o contexto da revisão.
- Navegação rápida de auditoria: adicionados controles globais `Expandir todos` / `Recolher todos` (aplicados aos alertas visíveis no filtro ativo), reutilizando a mesma persistência por chave de alerta.

**Por quê**
- Garantir auditabilidade do dado exibido e reduzir risco operacional para o perito ao conferir origem de cada informação-chave.

**Impacto / ponto de falha**
- Se a UI não mostrar botão de fonte para cabeçalho, verificar primeiro:
  1) presença de `fontes_extracao` no payload;
  2) normalização de `campo` em `workers/processor.py`;
  3) consumo em `frontend/src/components/features/AnalysisReport.tsx`.

**Validação executada**
- Backend: `venv/Scripts/python.exe -m pytest -q` → **859 passed**.
- Frontend: `npm run lint` (tsc) → **OK**.

---

## 0.1 Preparação de UI progressiva (streaming frontend) — Abril/2026

**O que foi alterado**
- `frontend/src/hooks/useAnalyze.ts`:
  - novo estado `partialData` (`Partial<ProcessoTrabalhista> | null`);
  - limpeza de `partialData` e `progressMessages` em `onMutate`;
  - suporte a mensagem WS `type="partial_update"` com merge defensivo de `payload`.
- `frontend/src/components/features/AnalysisReport.tsx`:
  - `processo` agora aceita `Partial<ProcessoTrabalhista>`;
  - nova prop opcional `isLoading`;
  - fallback visual com skeleton para campos principais durante carregamento.
- `frontend/src/pages/Extractor.tsx`:
  - inclusão de `Terminal Live Log` (últimas 3 mensagens, visual terminal);
  - exibição do `AnalysisReport` também durante loading (`isLoading=true`) com `partialData`.
- `frontend/src/pages/Laboratory.tsx`:
  - consumo de `progressMessages` e `partialData` do hook;
  - `Terminal Live Log` acima do relatório em loading;
  - relatório permanece montado durante processamento e troca para payload final ao concluir.

**Por quê**
- Eliminar sensação de tela em branco e preparar o frontend para streaming incremental sem quebrar o contrato atual de resposta final.

**Validação executada**
- Frontend: `npm install` (reposição de dependências após limpeza), `npm run lint` → **OK**.
- Backend: `venv/Scripts/python.exe -m pytest -q` → **859 passed**.

---

## 0.2 Streaming incremental no WebSocket (`POST /upload`) — Abril/2026

**O que foi alterado**
- `api/routers/extractor.py`: a fila de `/ws/{job_id}` pode entregar **várias** mensagens antes do resultado final; `push_ws_partial(job_id, payload, message)` envia `{"type":"partial_update","payload":{...},"message":...}`; `_ws_payload_is_terminal` define quando encerrar o loop; serialização `default=str` nos envios do loop.
- Novo **WebSocket** `GET /ws/lab-pipeline`: heartbeat enquanto o cliente mantém a conexão (evita 404 no `useAnalyze`; `POST /lab/analisar` continua síncrono).
- `workers/processor.py`: `_emit_ws_partial` (import lazy de `extractor`), `_partial_payload_pos_ia` / `_partial_payload_pos_motor` / `_partial_payload_pos_parecer`; emissões após IA+dedup, após ancoragem de verbas, após motor+`fontes_extracao`, após bloco de parecer; dossiê após quadro comparativo; petição inicial e contestação após shadow.
- `tests/test_ws_partial_stream.py`: `partial_update` não é terminal; `push_ws_partial` sem fila não quebra.

**Por quê**
- Permitir que a UI consuma **pedaços** de `ProcessoTrabalhista` durante o job assíncrono de upload, alinhado ao merge de `partialData` no frontend.

**Impacto / ponto de falha**
- Apenas fluxos com **`job_id` não vazio** e cliente em `/ws/{job_id}` recebem parciais. `POST /api/extract` síncrono **não** emite streaming (sem job).
- Se o cliente WS antigo assumir “uma mensagem só”, passa a receber N mensagens terminadas pela mensagem com `status` final (`done`/`error`/…).

**Validação executada**
- Backend: `venv/Scripts/python.exe -m pytest -q` → **862 passed**.

---

## 0.3 Extrator Rápido (SPA) alinhado ao streaming de jobs — Abril/2026

**O que foi alterado**
- `frontend/src/services/api.ts`: `UploadJobResponse`; `DEFAULT_USER_ID` exportado para o Form `user_id` do `POST /upload`.
- `frontend/src/pages/Extractor.tsx`: deixa de usar só `POST /api/extract` síncrono; passa a `POST /upload` (`files`, `cache_context=auto`, `user_id`), WebSocket `/ws/{job_id}` com merge de `partial_update`, fallback `GET /status/{job_id}` se o WS encerrar antes do resultado; limpeza de WebSocket ao trocar arquivo ou reanalisar.

**Por quê**
- Expor na mesma tela o mesmo pipeline assíncrono com `partial_update` já emitido pelo backend, sem regressão do contrato de dados final (`status` done + `data`).

**Impacto / ponto de falha**
- Depende de créditos/quota e do mesmo backend que `/upload` (PDF único → `process_lawsuit_pdf` com `job_id`). Se o proxy bloquear WebSocket, o fallback HTTP deve devolver o job já concluído; se o job ainda estiver `processing`, a mensagem orienta nova tentativa.

**Validação executada**
- Frontend: `npm run lint` (tsc) → **OK**.

---

## 0.4 Event loop do Uvicorn para WebSocket a partir do worker — Abril/2026

**O que foi alterado**
- `main.py`: no `lifespan` (startup), `extractor.register_worker_event_loop(asyncio.get_running_loop())` para o loop real do servidor.
- `api/routers/extractor.py`: `_uvicorn_loop` + `register_worker_event_loop`; `_enqueue_ws_message` usa `call_soon_threadsafe` nesse loop (deixa de confiar em `asyncio.get_event_loop()` na thread do pipeline, que no Windows gerava `ws_enqueue_failed` e impedia `partial_update`/resultado final na fila WS).
- `frontend/vite.config.ts`: proxy de `/upload` e `/status` para `http://localhost:8000` (dev em 5173 sem 404 no Extrator).

**Por quê**
- Garantir que o streaming e o push final do job cheguem ao browser quando o worker roda noutra thread.

**Validação executada**
- Backend: `venv/Scripts/python.exe -m pytest -q` → **862 passed**.
- Frontend: `npm run lint` → **OK**.

---

## 0.5 `memorial_juridico` estruturado (`validar_dados_completo` + ExplanationEngine) — Abril/2026

**O que foi alterado**
- `services/legal_validator.py`: `validar_dados_completo` deixa de substituir `memorial_juridico` por texto concatenado; retorna a lista de dicts produzida por `LegalRuleEngine.executar` (id, titulo, base_legal, descricao, prioridade).
- `services/explanation_engine.py`: `ExplanationEngine.gerar` normaliza entradas — só processa itens `dict` dentro de lista; tipo `str` ou não-lista vira lista vazia (evita iterar caracteres de string).
- `tests/jurisprudencia/test_legal_engine.py`: `test_memorial_juridico_disponivel` passa a assertar `list` de dicts com `id`.
- `tests/test_explanation_engine.py`: `test_memorial_string_nao_itera_caracteres` cobre o caso legado (string).

**Por quê**
- Corrigir `Exceção não tratada: 'str' object has no attribute 'get'` no pipeline pós-motor: `gerar_explicacoes` esperava lista de dicts.

**Impacto / ponto de falha**
- Fluxos **petição / contestação** seguem com `memorial_juridico` string (outro módulo); não passam por `validar_dados_completo` para memorial. Sentença: Excel `_texto_bloco_resumo` usa memorial string só para petição/contestação; demais usam `_montar_texto_parecer`.

**Validação executada**
- Backend: `venv/Scripts/python.exe -m pytest -q` → **863 passed**.

---

## 0.6 Multi-âncora no `sentence_finder` (anexos fora do recorte) — Abril/2026

**O que foi alterado**
- `services/sentence_finder.py`: após capa + bloco decisório contínuo, **Fase 4** anexa até **5** páginas fora do recorte com sinais de decisão modificativa / liquidação / recurso e até **3** com TRCT/registro, conciliação ou ata (texto nativo da varredura leve; OCR/tabelas só nas páginas anexadas efetivamente). Novos regex: embargos (acolho, provimento, erro material, omissão sanada), liquidação (sentença de liquidação, embargos à execução, homologo os cálculos), acórdão modificador, parâmetros base, acordo, ata/termo de audiência.
- `tests/test_sentence_finder_annex.py`: limites, exclusão de páginas já incluídas, precedência modificadora vs. base.

**Por quê**
- Incluir no contexto da IA trechos dispersos (embargos, homologação, TRCT, ata) sem substituir o algoritmo de bloco decisório por data PJe.

**Impacto / ponto de falha**
- PDFs muito grandes: tetos por categoria limitam texto extra. Falso positivo em palavra-chave pode anexar página irrelevante — revisar regex se logs `[FINDER] Anexos fora do recorte` mostrarem ruído.

**Validação executada**
- Backend: `venv/Scripts/python.exe -m pytest -q` → **868 passed**.

---

## 0.7 Raio-X do pipeline de texto (`DEBUG_PIPELINE`) — Abril/2026

**O que foi alterado**
- `config.py`: `DEBUG_PIPELINE`, `DEBUG_PIPELINE_DUMP`, `PIPELINE_DEBUG_OUT` (env).
- `services/pipeline_debug.py`: `log_etapa`, `alert_large_delta`, `maybe_write_dump` — logs `[DEBUG-PIPELINE]` com tamanho, hash curto, início/fim do texto; alerta se queda ≥25% entre etapas; dumps opcionais em `pipeline_debug_out/<user_id>/<job_id>/`. **Extensão (só observabilidade):** `log_truncate_cabe_inteiro`, `log_truncate_inicio_cirurgico`, `log_truncate_com_dispositivo`, `log_truncate_sem_dispositivo_fallback` — prefixo `[DEBUG-PIPELINE][truncate]` com `parte1_chars`/`parte2_chars`, `disp_pos`/`start2`/`end2` ou aviso de fallback quando `_RE_DISPOSITIVO` não casa.
- `workers/processor.py`: após `extract_sentence_from_pdf` / super-contexto dossiê — `step3_sentence_finder` ou `step3_dossie_supercontexto`; `extract_data_with_gemini(..., pipeline_debug_meta=...)`.
- `services/ai_client.py`: `_smart_truncate_after_dedup` aceita `pipeline_debug_meta` opcional; `_call_model` repassa o mesmo `meta` usado nas outras etapas; `_smart_truncate` (quadro/dossiê) continua sem meta. Instrumentação `ai_pre_remove_duplicatas`, `ai_pos_remove_duplicatas`, `ai_pos_smart_truncate` inalterada.
- `tests/test_pipeline_debug.py` (incl. `test_log_truncate_helpers_no_crash_debug_off`); `.gitignore`: `pipeline_debug_out/`.

**Por quê**
- Diagnóstico sem achismo: ver onde o texto degrada (finder vs dedup `_RE_DUPLICATA` vs truncagem) antes do prompt Gemini.

**Impacto / ponto de falha**
- Dumps contêm **PII** processual — usar só em ambiente controlado. Padrão: flags desligadas; zero impacto em produção.

**Validação executada**
- Backend: `venv/Scripts/python.exe -m pytest -q` → **871 passed**.

---

## Resumo executivo

- **Pipeline (10 passos)**: não foi alterado. Ordem, contratos e módulos são os mesmos descritos em `PIPELINE.md` e `README.md`.
- **Regras jurídicas**: nenhuma regra foi adicionada, removida ou alterada. Motor de regras, Shadow Rules e Knowledge Base seguem como documentados.
- **Estrutura (pastas, arquivos principais)**: inicialmente inalterada; em Março/2026 foi realizada uma refatoração para Arquitetura SaaS (API Gateway + roteadores) mantendo os contratos de entrada/saída.
- As mudanças feitas neste período incluem: **configuração de ambiente** (`.env`, Tesseract no Windows), **atualização do modelo Gemini** (2.0-flash deprecado → 2.5-flash), **migração de rotas para roteadores especializados** e **modernização parcial do frontend** (novo Dashboard e Laboratório em React).

---

## 1. config.py — carregamento do .env

**O que a documentação diz**
- README: *"config.py: Variáveis de ambiente (GEMINI_API_KEY, Firebase, MAX_FILE_SIZE_MB, SCHEMA_VERSION etc.)"*
- Nenhum doc exige como o `.env` deve ser carregado.

**O que foi alterado**
- Antes: `load_dotenv()` (carrega a partir do diretório de trabalho atual).
- Depois: `load_dotenv(Path(__file__).resolve().parent / ".env")` — carrega sempre `backend/.env`, independente de onde o processo foi iniciado.

**Regressão?** Não. Mesmas variáveis; comportamento mais previsível em nova máquina ou ao rodar da raiz do projeto.

---

## 2. services/sentence_finder.py — Tesseract no Windows

**O que a documentação diz**
- README / CODE_MAP: *"sentence_finder: extract_sentence_from_pdf; tipo de doc; OCR híbrido; bloco de decisão"*.
- Nenhum doc define onde deve estar o executável do Tesseract.

**O que foi alterado**
- Em Windows, se existir `C:\Program Files\Tesseract-OCR\tesseract.exe`, esse caminho é definido em `pytesseract.pytesseract.tesseract_cmd`.
- Objetivo: evitar `TesseractNotFoundError` quando o Tesseract não está no PATH.

**Regressão?** Não. Só afeta ambiente Windows; lógica de extração e de classificação de documento permanece a mesma.

---

## 3. services/ai_client.py — modelo Gemini

**O que a documentação diz**
- README / PIPELINE: *"IA: ai_client — Gemini (Flash → Pro), playbook, truncagem"* e *"cascata Flash → Pro"*.
- Nenhum doc fixa o nome exato do modelo (ex.: "gemini-2.0-flash").

**O que foi alterado**
- `MODELS_CASCADE`: primeiro modelo de `"gemini-2.0-flash"` para `"gemini-2.5-flash"` (2.0-flash está deprecado e retorna 404 para chaves novas).
- `CHARS_LIMIT`: adicionada entrada para `gemini-2.5-flash`; mantida `gemini-2.0-flash` para compatibilidade.
- `gerar_parcelas_parecer`: valor padrão de `model_name` de `"gemini-2.0-flash"` para `"gemini-2.5-flash"`.

**Regressão?** Não. Contrato continua: cascata Flash → Pro; mesma API e mesmo fluxo. Apenas o identificador do modelo foi atualizado para um que ainda está disponível na API.

---

## 4. test_connection.py (novo arquivo)

**O que a documentação diz**
- Nenhum doc menciona este script. É utilitário de diagnóstico.

**O que foi feito**
- Criado `backend/test_connection.py`: valida carregamento do `.env`, existência de `GEMINI_API_KEY` e uma chamada simples ao Gemini Flash (com fallback de modelos).

**Regressão?** Não. Não faz parte do pipeline nem dos contratos descritos em README/docs; não altera comportamento do extrator.

---

## 5. API Gateway e roteadores — transição do estado global para roteamento dinâmico

**O que a documentação diz**
- `SYSTEM_OVERVIEW.md` e `CODE_MAP.md` agora descrevem o `main.py` como **API Gateway**, sem regras de negócio, delegando para roteadores em `api/routers/`.
- Os domínios documentados são:
  - `extractor.py`: motor principal de upload, background tasks e WebSockets.
  - `lab.py`: rotas de laboratório / aprendizado.
  - `admin.py`: estatísticas, histórico e knowledge base.
  - `exports.py`: exportação de arquivos finais.

**O que foi alterado**
- Antes: o `main.py` concentrava rotas, estado em memória (_jobs, filas de WebSocket, etc.) e imports diretos de serviços.
- Depois: o `main.py` passou a apenas:
  - inicializar o `FastAPI`;
  - registrar middlewares;
  - incluir os roteadores (`app.include_router(...)`).
- O estado em memória e as rotas foram movidos para os arquivos de roteador correspondentes:
  - **Extrator**: controle de jobs, cache em memória, filas WebSocket e rotas `/upload`, `/status/{job_id}`, `/ws/{job_id}` migraram para `api/routers/extractor.py`.
  - **Laboratório**: rotas `/lab/*` migraram para `api/routers/lab.py`, mantendo contratos de entrada/saída.
  - **Admin/Stats/KB**: rotas `/api/stats`, `/api/historico/{user_id}`, `/api/knowledge-base`, `/api/admin/reset-contagem` migraram para `api/routers/admin.py`.
  - **Exports**: rotas de download de arquivos migraram para `api/routers/exports.py`.

**Regressão?** Não. Os caminhos finais das URLs e os contratos Pydantic foram preservados; apenas o local físico do código mudou (redução de estado global acoplado ao `main.py` e centralização em roteadores).

---

## 6. Multi-tenancy da Knowledge Base — Multiton em vez de Singleton

**O que a documentação diz**
- `CODE_MAP.md`, `AI_RULES.md` e `architecture.mdc` descrevem a `KnowledgeBase` como um serviço **Multi-tenant**, usando o padrão **Multiton**.
- Cada cliente deve ter o seu próprio ficheiro físico `knowledge_base_{tenant_id}.json`.

**O que foi alterado**
- Antes: `KnowledgeBase` se comportava como um singleton com um único ficheiro global de knowledge base.
- Depois:
  - foi introduzido um cache interno `_instances` indexado por `tenant_id`;
  - `__new__` e `__init__` passaram a receber `tenant_id` (default `"default"`), instanciando uma KB por tenant;
  - o caminho em disco (`self._path`) passou a ser calculado dinamicamente:
    - `knowledge_base.json` para o tenant `"default"`;
    - `knowledge_base_{tenant_id}.json` para demais tenants.
- As rotas de painel que usam knowledge base (`/api/knowledge-base`, `/api/stats`) passaram a instanciar `KnowledgeBase(tenant_id=user_id)` mantendo o mesmo contrato HTTP.

**Regressão?** Não. A semântica da KB foi mantida; o que mudou foi o isolamento físico por cliente. O tenant `"default"` preserva o comportamento anterior, garantindo compatibilidade com dados já existentes.

---

## 7. Frontend — estado atual (SPA React oficial)

**O que a documentação antiga dizia**
- README e docs mencionavam:
  - um frontend legado (`frontend/`) baseado em HTML/JS (index.html + js/app.js, render.js, lab.js + css/main.css);
  - um frontend novo (`frontend-new/`) em Vite + React + TypeScript, com Tailwind, React Query e Axios, ainda coexistindo com o legado.

**Situação atual**
- O frontend oficial **único** é a SPA React em `frontend/`:
  - `frontend/index.html` (entry, `#root`) + `src/main.tsx`;
  - `src/App.tsx` (rotas: `/`, `/extractor`, `/lab`);
  - `src/pages/Dashboard.tsx`, `Extractor.tsx`, `Laboratory.tsx`;
  - `src/components/layout/MainLayout.tsx`;
  - `src/hooks/useAnalyze.ts`, `src/services/api.ts`, `src/types/`.
- A pasta `frontend-new/` não existe mais como diretório separado; o código React foi consolidado em `frontend/src/`.
- O frontend HTML/JS legado (index.html + app.js + render.js + lab.js + main.css) foi descontinuado; referências a ele em docs devem ser tratadas como **históricas**.

**Impacto para manutenção**
- Qualquer alteração de UI deve ir para `frontend/src/` (páginas, componentes, hooks, serviços).
- Documentos que ainda falam em “frontend legado + frontend-new” precisam ser lidos com este contexto de consolidação; a fonte de verdade é:
  - `DEVELOPER.md` (§ 1 e § 3 — caminhos oficiais e consolidação),
  - `backend/docs/CODE_MAP.md` (§ Frontend),
  - `backend/docs/AI_NAVIGATION_LAYER.md` (§ 2.8, 2.9, 2.11, 2.12),
  - `backend/docs/CODE_INTELLIGENCE_MAP.md` (§ 7, § 8).

---

## 8. Laboratório — modo Flex-Analysis (Scanner Modular)

**O que a documentação diz**
- O laboratório aceita combinações opcionais de arquivos e o backend (`/lab/analisar`) já foi projetado para funcionar com campos ausentes.

**O que foi alterado**
- No `frontend-new/src/pages/Laboratory.tsx`:
  - o botão de análise passa a ser habilitado sempre que houver **pelo menos um arquivo** selecionado em qualquer card (Petição, Título Executivo, Parecer etc.);
  - o `FormData` de envio continua incluindo apenas os campos com arquivos anexados, sem serializar campos vazios;
  - a interface removeu rótulos de “obrigatório” dos cards, reforçando o conceito de **Scanner Modular**: o usuário pode analisar desde um único documento isolado até o conjunto completo de peças.

**Regressão?** Não. O backend já aceitava combinações parciais; a mudança apenas torna o frontend mais flexível e alinhado ao comportamento real da API, sem alterar contratos ou a lógica central de 10 passos.

---

## 9. Learning Engine — Passo 1: camada de persistência (learning_io)

**O que a documentação diz**
- O protocolo de refatoração modular do Laboratório prevê extrair a camada de persistência e I/O para um módulo dedicado, mantendo o `learning_engine.py` como facade.

**O que foi alterado**
- Criado `services/lab/__init__.py` e `services/lab/learning_io.py`.
- Movidas para `learning_io.py`: `preview_aprendizado`, `salvar_aprendizado`, `_salvar_rascunho_regra`, `_salvar_few_shot` (alias documental: `_salvar_insight_em_markdown`), `_registrar_log` (alias: `_registrar_no_log_de_aprendizado`). Caminhos de saída (`_SKILLS_DIR`, `_RULES_DIR`, `_LEARNING_LOG`) e constante exportada `LEARNING_LOG_PATH` ficam em `learning_io`.
- No `learning_engine.py`: removido o corpo dessas funções; mantido facade com `from services.lab import learning_io`, `preview_aprendizado = learning_io.preview_aprendizado`, `salvar_aprendizado = learning_io.salvar_aprendizado`, `_LEARNING_LOG = learning_io.LEARNING_LOG_PATH` (usado por `_registrar_log_enriquecido`).
- Imports `json`, `os`, `re`, `textwrap`, `datetime` permanecem no `learning_engine.py` (usados no restante do arquivo); em `learning_io.py` foram adicionados os necessários para as funções movidas. `hashlib` e `zipfile` não são usados pelas funções de persistência movidas; continuam apenas no `learning_engine.py`.

**Regressão?** Não. Contratos públicos (`preview_aprendizado`, `salvar_aprendizado`) e uso de `_LEARNING_LOG` em `_registrar_log_enriquecido` mantidos; chamadas externas (ex.: `api/routers/lab.py`, `main.py`) seguem importando de `learning_engine` sem alteração.

---

## 10. Learning Engine — Passo 2: limpeza e regex (extractors)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar regex e limpeza de texto em um módulo dedicado; `LegalRule._canonizar_verba` permanece acessível em `legal_engine/rule_base.py`.

**O que foi alterado**
- Criado `services/lab/extractors.py`. Movidas para lá: `regex_verbas`, `regex_indice`, `regex_juros`, `regex_divisor`, `liquidacao_from_text`; `extrair_fundamentos_juridicos`, `extrair_discrepancias_perita`; `remover_linha_autuacao`, `contexto_eh_autuacao` (e constantes `_RE_CONTEXTO_AUTUACAO`, `_RE_LINHA_DATA_AUTUACAO`); constantes e helpers de cabeçalho PJe: `CABECALHO_PJE_CHARS`, `_RE_TEXTO_2GRAU_FORA_CABECALHO`, `texto_apos_cabecalho_pje`, `tem_indicador_2grau_apos_cabecalho`.
- No `learning_engine.py`: removidos os corpos dessas funções e constantes; mantido facade com `from services.lab import extractors` e aliases `_regex_verbas`, `_liquidacao_from_text`, `_extrair_fundamentos_juridicos`, `_extrair_discrepancias_perita`, `_remover_linha_autuacao`, `_contexto_eh_autuacao`. `_classificar_tier_decisao` passou a usar `extractors.tem_indicador_2grau_apos_cabecalho(texto_primeiras_paginas)` em vez da lógica inline de cabeçalho PJe.
- Canonização de verbas: não alterada; continua em `LegalRule._canonizar_verba` (rule_base); `learning_engine` segue importando e usando onde necessário.

**Regressão?** Não. Comportamento de liquidação, manifestação, extração de data e classificação de tier inalterado; chamadas internas do `learning_engine` usam os mesmos nomes via facade. `PIPELINE.md` descreve os 10 passos do `processor.py`; o fluxo do Laboratório não é alterado por esta extração de módulo.

---

## 11. Learning Engine — Passo 3: Título Executivo e Tiers (titulo_executivo)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar a inteligência que define 1º Grau / TRT / TST e a fusão de múltiplos documentos (Título Executivo Complexo) em um módulo dedicado; regra "Tier diferente = ambos mantidos" e ignorar cabeçalho de 1000 chars conforme `AI_NAVIGATION_LAYER.md`.

**O que foi alterado**
- Criado `services/lab/titulo_executivo.py`. Movidas para lá: constantes de tier (`TIER_1GRAU_PELO_NOME`, `TIER_TRT_PELO_NOME`, `TIER_TST`, `TIER_TRT`, `TIER_ORDER`, `TIER_LABELS`), constantes de data (`MESES_NUM`, `FALLBACK_DATE`); funções `classificar_tier_decisao(filename, texto_primeiras_paginas?)`, `extrair_data_documento(texto)` e `extrair_titulo_executivo_multiplos(arquivos, contexto_amostragens?, *, extrair_processo, extrair_texto_arquivo, bloco_amostragens_perita)`. O módulo usa `extractors.remover_linha_autuacao`, `extractors.contexto_eh_autuacao`, `extractors.tem_indicador_2grau_apos_cabecalho`; não importa `learning_engine` (evita ciclo). A fusão multi-doc recebe os três callbacks injetados pelo `learning_engine`.
- No `learning_engine.py`: removidos os corpos e constantes das três funções e do bloco de título executivo; adicionado `from services.lab import titulo_executivo` e facades: `_classificar_tier_decisao`, `_extrair_data_documento` e `_extrair_titulo_executivo_multiplos` (esta chama `titulo_executivo.extrair_titulo_executivo_multiplos(..., extrair_processo=_extrair_processo, extrair_texto_arquivo=_extrair_texto_arquivo, bloco_amostragens_perita=_bloco_amostragens_perita)`). Removidos imports não usados (`hashlib`, `defaultdict`).

**Regressão?** Não. Contratos e comportamento (tier por nome, data sem Data da Autuação, tier diferente = ambos mantidos, cabeçalho 1000 chars ignorado) permanecem; apenas o local do código mudou. Chamadas ao lab e ao Card 3 seguem via `learning_engine` sem alteração de API.

---

## 12. Learning Engine — Passo 4: Discrepância Sentença vs. Cálculo (discrepancy)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar a lógica de confronto (Sentença vs. Cálculo) e os filtros de falsos-positivos em um módulo dedicado. Esta é a mudança mais importante no CODE_MAP: o "coração" do Laboratório. A canonização de verbas usa `LegalRule._canonizar_verba` (legal_engine/rule_base).

**O que foi alterado**
- Criado `services/lab/discrepancy.py`. Movidas para lá: `gerar_relatorio_discrepancia(dados_sentenca, dados_liquidacao, dados_manifestacao)` (comparação verbas deferidas vs. liquidação com canonização + substring + fuzzy; índice de correção; juros de mora; geração de discrepâncias e aprendizados); auxiliares internas `_campos_chave_sentenca`, `_sugerir_correcao_verba`, `_buscar_fundamento_para_verba`, `_extrair_aprendizados`; `verba_corresponde_na_liquidacao(verba_sentenca, verbas_liq_norm, verbas_liq_canon, threshold?)`; `canon_empresa_e_verba_esta(relatorio)`; `filtrar_falsos_positivos_verba_ausente(relatorio)`, `filtrar_logicas_verba_ausente_falsas(logicas, relatorio)`, `filtrar_aprendizados_verba_ausente_falsas(relatorio)`. O módulo importa `LegalRule` de `services.legal_engine.rule_base` e `rapidfuzz`; usa `RAPIDFUZZ_THRESHOLD` de config (ou 85).
- No `learning_engine.py`: removidos os corpos de todas essas funções e os helpers; adicionado `from services.lab import discrepancy` e facades que delegam a `discrepancy.*`. Removidos imports não usados (`rapidfuzz`, `_FUZZ_THRESHOLD`).

**Regressão?** Não. Contratos públicos (`gerar_relatorio_discrepancia`) e uso interno dos guardrails mantidos; chamadas externas (ex.: `api/routers/lab.py`) e fluxo do relatório inalterados. As três camadas de guardrail continuam a ser aplicadas na mesma ordem; a canonização segue usando `LegalRule._canonizar_verba` dentro de `discrepancy.py`.

---

## 13. Learning Engine — Passo 5: Duplo Style Transfer (style_transfer)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar a lógica que aprende como a perita escreve: extração de manifestação pericial, merge dos dados (Impugnação + Manifestação) e integração com `skills/manifestacao_style.md` (Duplo Style Transfer).

**O que foi alterado**
- Criado `services/lab/style_transfer.py`. Movidas para lá: `merge_dados_manifestacao(base, novo)`; `extrair_manifestacao_pericial(file_bytes, filename, *, extrair_texto_arquivo, chamar_gemini_para_codify, skills_dir)` (analisa peça com Gemini, extrai frases de impacto/padrões Ataque/Defesa/argumento vencedor, codifica padrões no KB, atualiza manifestacao_style.md); `atualizar_skill_manifestacao(skills_dir, dados, trecho_original, filename)`; helper interno `_codificar_padroes_ataque_defesa(dados)`. O módulo usa `extractors.extrair_fundamentos_juridicos` e `services.knowledge_base.KnowledgeBase`; não importa `learning_engine` (callbacks injetados).
- No `learning_engine.py`: removidos os corpos de `_merge_dados_manifestacao`, `_extrair_manifestacao_pericial`, `_codificar_padroes_ataque_defesa` e `_atualizar_skill_manifestacao`; adicionado `from services.lab import style_transfer` e facades que delegam a `style_transfer.merge_dados_manifestacao` e `style_transfer.extrair_manifestacao_pericial(..., extrair_texto_arquivo=_extrair_texto_arquivo, chamar_gemini_para_codify=_chamar_gemini_para_codify, skills_dir=_SKILLS_DIR)`.

**Regressão?** Não. Contratos e fluxo do Duplo Style Transfer (Card 6 + Card 8 → manifestacao_style.md e KB) mantidos; chamadas em `processar_sete_arquivos` seguem usando `_extrair_manifestacao_pericial` e `_merge_dados_manifestacao` sem alteração de assinatura.

---

## 14. Learning Engine — Passo 6: Self-Healing e Shadow Rules (self_healing)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar a parte que gera novas regras Python automaticamente: codify_insight, processar_aprendizado_autonomo e _evaluate_shadow_rules. A integração com `services/knowledge_base.py` deve ser mantida via user_id (Multi-tenancy).

**O que foi alterado**
- Criado `services/lab/self_healing.py`. Movidas para lá: `codify_insight(aprendizado, numero_processo, conteudo_editado=None, *, rules_dir, skills_dir, learning_log_path, chamar_gemini_para_codify)` (consolida aprendizado em regra Python + skill + learning_log; usa `learning_io.preview_aprendizado` e helpers internos `_gerar_regra_python_gemini`, `_gerar_exemplo_skill_gemini`, `_registrar_log_enriquecido`); `processar_aprendizado_autonomo(relatorio, numero_processo, user_id=None, *, extrair_logica_correcao_gemini, filtrar_logicas_verba_ausente_falsas)` — cria `KnowledgeBase(tenant_id=user_id or "default")`, extrai hipóteses via callback, filtra falsos positivos, atualiza KB e chama `evaluate_shadow_rules`; `evaluate_shadow_rules(relatorio, kb=None, user_id=None)` (acerto/punição das regras shadow). Removidos de `learning_engine.py`: corpos de codify_insight, processar_aprendizado_autonomo, _evaluate_shadow_rules e dos helpers _gerar_regra_python_gemini, _gerar_exemplo_skill_gemini, _registrar_log_enriquecido; mantidos _chamar_gemini_para_codify (usado por style_transfer e injetado no codify_insight) e _extrair_logica_correcao_gemini (callback injetado no processar_aprendizado_autonomo). Facades em learning_engine delegam a `self_healing.*`; `processar_aprendizado_autonomo` ganhou parâmetro opcional `user_id` para Multi-tenancy.

**Regressão?** Não. Contratos públicos (`codify_insight`, `processar_aprendizado_autonomo`) e chamadas de `api/routers/lab.py` e `processar_sete_arquivos` mantidos. KB continua sendo usado com `tenant_id=user_id or "default"` dentro de self_healing. main.py e processor.py não importam learning_engine diretamente para essas funções; lab router e processar_sete_arquivos seguem funcionando.

---

## Histórico de Correções Técnicas

- **Exportador Excel (`services/excel_exporter.py`) — erro MergedCell**  
  A função `_auto_ajustar_colunas` iterava sobre as células de cada coluna e usava `cell.column_letter` para definir a largura. Em planilhas com células mescladas (ex.: bloco do Memorial na aba "Resumo e Parecer"), o openpyxl devolve instâncias de `MergedCell`, que não possuem o atributo `column_letter`, gerando `AttributeError`. Correção aplicada: import de `MergedCell`; para cada coluna, localização de uma célula "mestre" não mesclada; uso dessa célula para obter `column` e `column_letter` e aplicar o ajuste; `try/except AttributeError` ao acessar `column_letter`, pulando colunas que não permitem o ajuste (evitando falha silenciosamente).

- **Exportador Excel — validação de campos nulos**  
  Para estabilizar o endpoint `/api/export/excel` quando o objeto ProcessoTrabalhista vem com campos ausentes: (1) confirmação de que todos os acessos a `dados` usam `.get()`; (2) quando `salario_base` é `None` ou string vazia, a célula correspondente passa a exibir o texto *"Não identificado na sentença"*; (3) a lista de verbas é obtida com `dados.get("verbas_deferidas") or []`, em seguida garantida como lista com `if not isinstance(verbas, list): verbas = []` e o loop que preenche a aba "Verbas Deferidas" só é executado com `if verbas:`, evitando erros de iteração quando o valor não é lista ou está vazio.

---

## O que NÃO foi alterado (conferido)

- **workers/processor.py**: nenhuma alteração. Os 10 passos, ordem e chamadas estão como em `PIPELINE.md`.
- **legal_engine/**: nenhuma alteração em regras, engine, rule_registry ou dynamic_rule_loader.
- **models.py**: não alterado.
- **learning_engine.py**: contrato público inalterado; persistência a `services.lab.learning_io`; regex a `services.lab.extractors`; confronto e guardrails a `services.lab.discrepancy`; título executivo/tiers a `services.lab.titulo_executivo`; Style Transfer a `services.lab.style_transfer`; Self-Healing e codify a `services.lab.self_healing` (facades). learning_engine permanece como facade orquestrador (apenas imports e delegação).
- **knowledge_base.py**: apenas migração de Singleton para Multiton por `tenant_id`, preservando lógica de pontuação e busca.
- **main.py**: deixou de abrigar regras de negócio; hoje é API Gateway puro incluindo roteadores.
- **Skills (.md)**: não alteradas semanticamente; apenas sincronização de regras de navegação para refletir a nova arquitetura.
- **Frontend legado (`frontend/`)**: permanece funcional, com pequenos ajustes de URLs para `/api/*` onde documentado.
- **Contrato de `process_lawsuit_pdf`**: entrada e retorno (status, data, alertas_juridicos, regras_aplicadas, etc.) permanecem como documentados.

---

## Checklist fonte por página e qualidade por tipo (Mar/2026)

**O quê:** Entrega alinhada a `PR_CHECKLIST_FONTE_E_QUALIDADE.md` — capa adaptativa, gate de cache por `doc_type`, prompt com `trecho_fundamentacao` / `pagina_origem`, UI de página no relatório.

**Arquivos:** `services/sentence_finder.py` (`get_adaptive_capa_pages`), `workers/processor.py` (`_qualidade_ok(..., doc_type)`), `services/ai_client.py` (template JSON + regras), `models.py` (descrição de `trecho_fundamentacao`), `frontend/src/components/features/AnalysisReport.tsx`, `frontend/src/types/api.ts`, `frontend/src/vite-env.d.ts`; testes `tests/test_processor_quality_gate.py`, `tests/test_adaptive_capa_pages.py`.

**Ponto de falha:** Liquidações com cache antigo podem passar a ser cacheáveis com menos campos; regressão de sentença se `doc_type` não for passado ao validar cache (hoje usa `_meta_doc_type`).

---

## Navegação PDF + `pagina_origem` (Mar/2026)

**O quê:** `services/verba_page_anchor.py` preenche `pagina_origem` cruzando `trecho_fundamentacao` com marcadores `--- PÁGINA N ---` do texto do `sentence_finder`; `processor._executar_pipeline_pos_ia` chama após merge regex. Frontend: `PdfViewer.tsx` (pdfjs-dist), `Extractor` e `Laboratory` passam `onNavegar` para `AnalysisReport` e o primeiro PDF de sentença (lab) ou o arquivo analisado (extrator).

**Ponto de falha:** Dossiê ou PDFs sem marcadores de página não ancoram; DOCX no extrator não abre o painel PDF. Trechos muito curtos ou muito diferentes do texto (OCR) podem não casar.

---

## Ancoragem resiliente + feedback “fonte não ancorada” (Mar/2026)

**O quê:** Refino de `verba_page_anchor.py`: após match por substring e prefixos, passa a usar **prefixo e sufixo** na **mesma** página (meio corrompido), **texto compacto** só letras/números (espaços/OCR) e, por último, **`rapidfuzz.partial_ratio`** com score mínimo (93) e folga mínima para o 2º candidato (evita escolha ambígua). No frontend, `AnalysisReport` exibe *Fonte não ancorada no PDF* quando há `trecho_fundamentacao` mas não há `pagina_origem`.

**Riscos:** (1) Fuzzy pode, em teoria, escolher página errada se duas páginas tiverem trechos muito parecidos e o gap entre scores for baixo — mitigado pelo `MIN_GAP`. (2) Prefixo+sufixo na mesma página pode, em texto repetitivo, casar onde não é o dispositivo — mitigado por tentar match completo antes.

**Testes:** `tests/test_verba_page_anchor.py` (incl. corrupt middle, compact, regressão de match integral); `pytest` também em `test_processor_quality_gate` e `test_adaptive_capa_pages` após alterações no processor (não houve mudança de assinatura nesta rodada).

**Docs:** `PIPELINE.md` (linha 7c), `CODE_MAP.md` (`verba_page_anchor.py`).

---

## Cache por contexto + petição inicial no extrator (Mar/2026)

**O quê:**
- `services/cache_key.pdf_cache_storage_key(hash, cache_context)` — com `auto` (padrão) a chave continua **só o SHA-256** do ficheiro (compatível com entradas antigas). Com `peticao_inicial`, a chave é `{hash}:peticao_inicial` (mesma coluna SQLite `pdf_hash`, sem migração).
- `process_lawsuit_pdf(..., cache_context=..., filename=...)` — ramo `peticao_inicial` delega em `learning_engine._extrair_peticao_inicial`, preenche `verbas_pedidas` / espelho em `verbas_deferidas` para a UI, gera `memorial_juridico` via `services/memorial_pedidos.gerar_memorial_pedidos`, **sem** Legal Rule Engine / parecer completo. `_qualidade_ok(..., "peticao_inicial")` exige ≥1 pedido.
- `POST /api/extract`: campo Form opcional `cache_context` (default `auto`).

**Riscos / pontos de falha:** Petição só aceita PDF/DOC/DOCX. Chamadas existentes a `process_lawsuit_pdf(user, bytes, job_id)` mantêm comportamento. Não foi alterado o schema `SCHEMA_VERSION` para não invalidar caches legados.

**Testes:** `tests/test_cache_key.py`, `tests/test_memorial_pedidos.py`, `tests/test_peticao_pipeline.py`; suíte completa `pytest tests/` + `tests/jurisprudencia/`.

---

## Petição: Excel, export API, memorial e UI (Mar/2026)

**O quê:** `memorial_pedidos` passa a listar `trecho_fundamentacao` por pedido; `excel_exporter` ramifica por `_meta_doc_type=peticao_inicial` (abas, coluna de trecho, resumo via `memorial_juridico`, valor da causa); `POST /api/export/excel` mantém `memorial_juridico` só nesse caso e usa ficheiro `Pedidos_Inicial_*.xlsx`; `AnalysisReport` oculta PJC para petição e rotula o Excel.

**Regressão:** Sentença mantém nomes de abas e omissão de `memorial_juridico` no body de export como antes.

**Testes:** `tests/test_excel_exporter_peticao.py`, `tests/test_memorial_pedidos.py`; `pytest tests/` + `tests/jurisprudencia/`.

---

## Shadow KB — persistência em `shadow_logs` (SCHEMA 2.13)

**O quê:** `ContextoJuridico.shadow_hits` acumula hits **por execução** do motor (sem depender do buffer global `_shadow_hits` para o JSON). `LegalRuleEngine.executar` devolve `shadow_hits`. `executar_shadow_pipeline` devolve essa lista; `processor` grava em `dados_finais["shadow_logs"]` (pipeline principal e `_pipeline_peticao_inicial`). `ProcessoTrabalhista.shadow_logs` + **`SCHEMA_VERSION=2.13`** (invalida cache antigo). `memoria_calculo.gerar_memoria` inclui `shadow_logs`. Export Excel omite `shadow_logs` do body (ruído).

**Testes:** `tests/test_shadow_logs_persist.py`; `pytest tests/` + `tests/jurisprudencia/`.

---

## Contestação dedicada — `teses_defesa` (SCHEMA 2.14)

**O quê:** `models.TeseDefesa` + `ProcessoTrabalhista.teses_defesa`; `SCHEMA_VERSION=2.14`. `cache_context=contestacao` → `_pipeline_contestacao`: `learning_engine._extrair_contestacao` (prompt enriquecido com `teses_defesa`; campos legados `argumentos_exclusao` / `verbas_negadas` / `teses_empresa` derivados quando a IA omite, para o relatório Lab), texto com marcadores `_extrair_texto_arquivo_com_marcadores_pagina`, `anchor_verbas_to_pages` nas teses, `gerar_memorial_defesa`, shadow_logs, `_qualidade_ok(..., "contestacao")` (≥1 tese). `extractor._should_run_process_lawsuit_pdf_upload`: mesmo contrato de ficheiro único que petição. Excel/UI/export: ver `exports.py`, `excel_exporter`, `AnalysisReport`.

**Ponto de falha:** se `GEMINI` falhar ou retornar JSON sem teses, `qualidade_ok` bloqueia cache; utilizador vê motivo em `qualidade_motivo`.

**Testes:** `tests/test_contestacao_pipeline.py`, `tests/test_upload_cache_context.py`, `tests/test_excel_exporter_peticao.py`, `tests/test_cache_key.py`; suíte completa `pytest tests/` + `tests/jurisprudencia/` (846 testes na última execução).

---

## Dossiê: quadro comparativo triplo (SCHEMA 2.15)

**O quê:** `ItemComparativo` + `ProcessoTrabalhista.quadro_comparativo`; `SCHEMA_VERSION=2.15`. Em `process_lawsuit_dossie`, com **≥3 ficheiros** no upload, após a extração principal (`extract_data_with_gemini` + dedup), segunda passagem **`ai_client.extrair_quadro_comparativo_dossie`**: truncagem por documento (`--- INÍCIO DO DOCUMENTO:`), JSON só com `quadro_comparativo`, falha segura (lista vazia). **Não** substitui `_executar_pipeline_pos_ia`; `doc_type` do dossiê continua **`completo`**. Excel: aba opcional "Quadro comparativo"; UI: `AnalysisReport`.

**Ponto de falha:** se o segundo modelo falhar ou devolver JSON inválido, o fluxo principal segue sem quadro (log `[AI][QUADRO]`).

**Testes:** `tests/test_quadro_comparativo.py`, `tests/test_dossie_quadro_merge.py`, `tests/test_excel_exporter_peticao.py`; `pytest tests/` + `tests/jurisprudencia/` (854 testes na última execução).

---

## Conclusão

- O código que você trouxe do GitHub **foi modificado** nos pontos acima (config, sentence_finder, ai_client, novo script de teste, arquitetura de roteadores, multi-tenancy da Knowledge Base e início do frontend React).
- Nenhuma **regra jurídica**, **pipeline de 10 passos** ou **contrato HTTP** documentado no README e em `docs/` foi alterado de forma que cause regressão ou comportamento diferente do desenhado.
- As mudanças principais são:
  - **ambiente** (`.env`, Tesseract);
  - **disponibilidade de API** (modelo Gemini);
  - **arquitetura SaaS** (API Gateway + roteadores, Multiton para KB);
  - **lógica de upload multi-card no cliente** (estado por card e suporte a múltiplos arquivos no Título Executivo).
  Todas foram implementadas preservando compatibilidade com os fluxos já descritos na documentação.

Se quiser reverter apenas as alterações de “nova máquina”, basta desfazer as mudanças em `config.py`, `sentence_finder.py` e `ai_client.py` (e opcionalmente remover `test_connection.py`). O restante do repositório está alinhado com a documentação.


---

## Redução de duplicidade de engine + limpeza de prefixo CNJ (Mar/2026)

**O quê:** No `workers/processor.py`, o motor jurídico estático deixou de executar em duplicidade no mesmo request. O fluxo passou a usar somente `validar_dados_completo(dados_finais)` para obter `alertas/regras/memorial` estáticos e depois injeta apenas regras dinâmicas ativas. Em paralelo, `numero_cnj_validator.py` removeu o prefixo textual interno `[ERRO]` da mensagem para evitar saída final duplicada (`[ERRO] [ERRO] ...`).

**Risco de regressão:** baixo. A lógica de regras não foi alterada; apenas eliminada a execução redundante e normalizada a formatação da mensagem.

**Testes:** suíte completa `pytest tests/ tests/jurisprudencia` após cada alteração (854 passed em ambas as execuções).


---

## Ghostwriter — preview Markdown seguro (Passo 12A)

**O quê:** Mantido o endpoint existente `POST /lab/gerar-docx` e adicionada opção de preview textual `POST /lab/gerar-manifestacao` (sem quebrar contrato anterior). O `ai_writer.py` agora normaliza alertas (`str`/`dict`) e aceita `quadro_comparativo` como contexto adicional de redação. Nova função `render_markdown_manifestacao()` converte a saída estruturada em Markdown para revisão no frontend.

**Segurança/Regressão:** baixo risco. Não remove fluxos anteriores; DOCX continua igual. A leitura de estilo (`manifestacao_style.md`) foi centralizada em helper com fallback vazio (falha segura).

**Testes:** `tests/test_ai_writer.py`, `tests/test_lab_manifestacao_helpers.py` + suíte completa `pytest tests/ tests/jurisprudencia` (858 passed).

**Frontend:** `pages/Laboratory.tsx` integrou botão de preview (`/lab/gerar-manifestacao`), painel com Markdown retornado, cópia para clipboard e manutenção do fluxo existente de download DOCX (`/lab/gerar-docx`).
Renderização do preview evoluiu para **rich markdown** com `react-markdown` (títulos, listas, tabelas e código com estilo), mantendo fallback textual e sem alterar o contrato da API.
Adicionado toggle de visualização **Renderizado / Raw** no preview para revisão jurídica linha a linha sem perder a renderização rica.
Preferência de visualização (renderizado/raw) persistida em `localStorage` (`lab_manifestacao_preview_mode`) para manter o modo escolhido entre sessões.
---

## Ciclo extraction: timeout do worker em upload/status

**O que:** Adicionado teste de ciclo para timeout de job em `POST /upload` + `GET /status/{job_id}`. O teste reduz `JOB_TIMEOUT_SECONDS` via `monkeypatch`, usa `process_lawsuit_pdf` mockado e lento, e valida payload terminal `status == "error"` com mensagem `Timeout: processamento excedeu`, sem esperar 300s e sem Gemini/API real.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_upload_status_api.py::test_upload_worker_timeout_surfaces_error_on_status`.
---

## Ciclo extraction: timeout do worker em upload/ws

**O que:** Adicionado teste de ciclo para timeout de job em `POST /upload` + `/ws/{job_id}`. O teste reduz `JOB_TIMEOUT_SECONDS` via `monkeypatch`, usa `process_lawsuit_pdf` mockado e lento, e valida payload terminal `status == "error"` com mensagem `Timeout: processamento excedeu`, sem esperar 300s e sem Gemini/API real.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_upload_status_api.py::test_upload_worker_timeout_websocket_terminal_error`.
---

## Ciclo extraction: upload rejeita PDF menor que 10 bytes

**O que:** Adicionado teste de ciclo para `POST /upload` com arquivo `.pdf` abaixo do tamanho minimo. O contrato validado e `400` com mensagem de arquivo vazio/invalido, sem chamada a `process_lawsuit_pdf` ou `process_lawsuit_dossie`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_upload_status_api.py::test_upload_pdf_menor_que_10_bytes_retorna_400_sem_processador`.
---

## Ciclo extraction: upload rejeita extensao nao permitida

**O que:** Adicionado teste de ciclo para `POST /upload` com arquivo fora da whitelist de extensoes (`.exe`). O contrato validado e `400` com mensagem `Tipo nao aceito`, sem chamada a `process_lawsuit_pdf` ou `process_lawsuit_dossie`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_upload_status_api.py::test_upload_extensao_nao_permitida_retorna_400_sem_processador`.
---

## Ciclo extraction: fluxo peticao_inicial via cache_context

**O que:** Adicionado teste de ciclo para `process_lawsuit_pdf(..., cache_context="peticao_inicial")`. O teste usa learning engine dedicado mockado, garante que `sentence_finder` e Gemini padrao nao sao chamados, valida `doc_type == "peticao_inicial"`, `qualidade_ok`, memorial, verba pedida, cache composto e emissao de partial payload.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_peticao_inicial_cache_context_mockada`.
---

## Ciclo extraction: fluxo contestacao via cache_context

**O que:** Adicionado teste de ciclo para `process_lawsuit_pdf(..., cache_context="contestacao")`. O teste usa learning engine dedicado mockado, garante que `sentence_finder` e Gemini padrao nao sao chamados, valida `doc_type == "contestacao"`, `qualidade_ok`, tese de defesa, memorial, cache composto e emissao de partial payload.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_contestacao_cache_context_mockada`.
---

## Ciclo extraction: cache hit qualificado peticao_inicial

**O que:** Adicionado teste de ciclo para cache composto valido em `process_lawsuit_pdf(..., cache_context="peticao_inicial")`. O contrato validado e retorno `source == "cache"` antes do learning engine dedicado, sem `sentence_finder`, sem Gemini padrao, sem salvar nova extracao e sem descontar credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_peticao_inicial_cache_hit_qualificado`.
---

## Ciclo extraction: cache hit qualificado contestacao

**O que:** Adicionado teste de ciclo para cache composto valido em `process_lawsuit_pdf(..., cache_context="contestacao")`. O contrato validado e retorno `source == "cache"` antes do learning engine dedicado, sem `sentence_finder`, sem Gemini padrao, sem salvar nova extracao e sem descontar credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_contestacao_cache_hit_qualificado`.
---

## Ciclo extraction: cache invalido peticao_inicial reprocessa

**O que:** Adicionado teste de ciclo para cache composto insuficiente em `process_lawsuit_pdf(..., cache_context="peticao_inicial")`. O contrato validado e descarte do cache invalido, execucao do learning engine dedicado mockado, sem `sentence_finder`/Gemini padrao, novo resultado valido salvo em cache e desconto de credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_peticao_inicial_cache_invalido_reprocessa`.
---

## Ciclo extraction: cache invalido contestacao reprocessa

**O que:** Adicionado teste de ciclo para cache composto insuficiente em `process_lawsuit_pdf(..., cache_context="contestacao")`. O contrato validado e descarte do cache invalido, execucao do learning engine dedicado mockado, sem `sentence_finder`/Gemini padrao, novo resultado valido salvo em cache e desconto de credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_contestacao_cache_invalido_reprocessa`.
---

## Ciclo extraction: peticao_inicial rejeita extensao invalida no processor

**O que:** Adicionado teste de ciclo para `process_lawsuit_pdf(..., cache_context="peticao_inicial")` com filename fora de PDF/DOC/DOCX. O contrato validado e retorno `status == "erro"` antes do pipeline dedicado, sem learning engine, sem `sentence_finder`, sem Gemini padrao, sem consulta de cache, sem salvar extracao e sem desconto de credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_peticao_inicial_extensao_invalida`.
---

## Ciclo extraction: contestacao rejeita extensao invalida no processor

**O que:** Adicionado teste de ciclo para `process_lawsuit_pdf(..., cache_context="contestacao")` com filename fora de PDF/DOC/DOCX. O contrato validado e retorno `status == "erro"` antes do pipeline dedicado, sem learning engine, sem `sentence_finder`, sem Gemini padrao, sem consulta de cache, sem salvar extracao e sem desconto de credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_pdf_contestacao_extensao_invalida`.
---

## Ciclo extraction: dossie com quadro comparativo no payload final

**O que:** Adicionado teste de ciclo para `process_lawsuit_dossie` com tres arquivos. A IA principal e a segunda IA de quadro comparativo sao mockadas, o pipeline pos-IA compartilhado roda de verdade, e o contrato validado e `data["quadro_comparativo"]` presente no retorno final, com cache, extracao e desconto de credito exercitados.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_dossie_tres_arquivos_quadro_no_payload_final`.
---

## Ciclo extraction: dossie com dois arquivos sem quadro comparativo

**O que:** Adicionado teste de ciclo para `process_lawsuit_dossie` com dois arquivos. A IA principal e mockada, o pipeline pos-IA compartilhado roda de verdade, a segunda IA de quadro comparativo nao e chamada e o contrato validado e `data["quadro_comparativo"] == []` no retorno final, com cache, extracao e desconto de credito exercitados.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_dossie_dois_arquivos_sem_quadro_no_payload_final`.
---

## Ciclo extraction: dossie com falha nao critica da IA de quadro

**O que:** Adicionado teste de ciclo para `process_lawsuit_dossie` com tres arquivos quando a segunda IA de quadro comparativo levanta excecao. O contrato validado e fluxo principal `sucesso`, `data["quadro_comparativo"] == []`, cache/extracao/desconto de credito preservados e nenhuma API real.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_dossie_quadro_falha_nao_bloqueia_fluxo`.
---

## Ciclo extraction: cache hit qualificado em dossie

**O que:** Adicionado teste de ciclo para cache valido em `process_lawsuit_dossie`. O contrato validado e retorno `source == "cache"` com `_meta_doc_type == "completo"` antes de extrair textos ou chamar IA principal/IA de quadro, sem salvar nova extracao e sem desconto de credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_dossie_cache_hit_qualificado`.
---

## Ciclo extraction: cache invalido em dossie reprocessa

**O que:** Adicionado teste de ciclo para cache insuficiente em `process_lawsuit_dossie`. O contrato validado e descarte do cache invalido, extracao de textos, IA principal mockada, IA de quadro mockada, pipeline pos-IA real, novo resultado salvo em cache e desconto de credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_dossie_cache_invalido_reprocessa`.
---

## Ciclo extraction: saldo esgotado em dossie

**O que:** Adicionado teste de ciclo para `process_lawsuit_dossie` sem creditos. O contrato validado e retorno de erro por saldo esgotado antes de cache, extracao de textos, IA principal e IA de quadro, sem salvar extracao e sem desconto de credito.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_processor_e2e_mock_ia.py::test_process_lawsuit_dossie_saldo_esgotado_para_antes_de_cache_texto_ia`.
---

## Ciclo extraction: exportacao Excel via API

**O que:** Adicionado teste de ciclo para `POST /api/export/excel` com `exportar_excel` mockado. O contrato validado e limpeza de campos pesados antes do exporter, uso do CNJ como `job_id`, retorno XLSX e `Content-Disposition` com filename ASCII.

**Correcao de bug:** O filename padrao usava `Auditoria_Cálculo_...xlsx`; em header HTTP isso quebrou o `TestClient` por byte nao UTF-8. Alterado para `Auditoria_Calculo_...xlsx`.

**Testes:** `tests/test_extraction_cycle_export_api.py::test_export_excel_sentenca_limpa_campos_e_retornaxlsx`.
---

## Ciclo extraction: exportacao Excel peticao_inicial via API

**O que:** Adicionado teste de ciclo para `POST /api/export/excel` com `_meta_doc_type="peticao_inicial"` e `exportar_excel` mockado. O contrato validado e preservacao de `memorial_juridico`, remocao de campos pesados, uso do CNJ como `job_id` e filename `Pedidos_Inicial_...xlsx`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_api.py::test_export_excel_peticao_preserva_memorial_e_nome_especifico`.
---

## Ciclo extraction: exportacao Excel contestacao via API

**O que:** Adicionado teste de ciclo para `POST /api/export/excel` com `_meta_doc_type="contestacao"` e `exportar_excel` mockado. O contrato validado e preservacao de `memorial_juridico`, remocao de campos pesados, uso do CNJ como `job_id` e filename `Contestacao_...xlsx`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_api.py::test_export_excel_contestacao_preserva_memorial_e_nome_especifico`.
---

## Ciclo extraction: exportacao Excel corpo vazio

**O que:** Adicionado teste de ciclo para `POST /api/export/excel` com body vazio. O contrato validado e `400` com mensagem de corpo invalido antes de chamar o exporter.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_api.py::test_export_excel_corpo_vazio_retorna_400_sem_exporter`.
---

## Ciclo extraction: exportacao Excel falha do exporter

**O que:** Adicionado teste de ciclo para `POST /api/export/excel` quando `exportar_excel` levanta `RuntimeError`. O contrato validado e resposta `500` com mensagem estavel contendo tipo e texto do erro.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_api.py::test_export_excel_falha_exporter_retorna_500_estavel`.
---

## Ciclo extraction: exportacao PJC via API

**O que:** Adicionado teste de ciclo para `POST /api/export/pjc` com `exportar_pjc` e `gerar_nome_arquivo` mockados. O contrato validado e retorno de bytes XML/PJC, `Content-Type: application/xml`, header `X-PJC-Version: 5.4`, filename estavel e repasse do body ao exporter.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_api.py::test_export_pjc_happy_path_retorna_xml_com_headers`.
---

## Ciclo extraction: exportacao PJC corpo vazio

**O que:** Adicionado teste de ciclo para `POST /api/export/pjc` com body vazio. O contrato validado e `400` com mensagem de corpo invalido antes de chamar `exportar_pjc`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_api.py::test_export_pjc_corpo_vazio_retorna_400_sem_exporter`.
---

## Ciclo extraction: exportacao PJC falha do exporter

**O que:** Adicionado teste de ciclo para `POST /api/export/pjc` quando `exportar_pjc` levanta `RuntimeError`. O contrato validado e resposta `500` com mensagem estavel contendo tipo e texto do erro.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_api.py::test_export_pjc_falha_exporter_retorna_500_estavel`.
---

## Ciclo extraction: export-excel por job_id

**O que:** Adicionado teste de ciclo para `GET /export-excel/{job_id}` com job finalizado em memoria e `exportar_excel` mockado. O contrato validado e remocao de `status` antes do exporter, uso do `job_id`, retorno XLSX e filename `extrator_<CNJ>.xlsx`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_job_excel.py::test_export_excel_job_pronto_retorna_xlsx`.
---

## Ciclo extraction: export-excel por job_id ausente

**O que:** Adicionado teste de ciclo para `GET /export-excel/{job_id}` com job inexistente. O contrato validado e retorno `404` com mensagem contendo o `job_id`, sem chamar `exportar_excel`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_job_excel.py::test_export_excel_job_ausente_retorna_404_sem_exporter`.
---

## Ciclo extraction: export-excel por job_id processing

**O que:** Adicionado teste de ciclo para `GET /export-excel/{job_id}` com job em `processing`. O contrato validado e retorno `202` com mensagem de processamento, sem chamar `exportar_excel`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_job_excel.py::test_export_excel_job_processing_retorna_202_sem_exporter`.
---

## Ciclo extraction: export-excel por job_id em erro

**O que:** Adicionado teste de ciclo para `GET /export-excel/{job_id}` com job em `error`. O contrato validado e retorno `400` com mensagem de erro/exportacao, sem chamar `exportar_excel`.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_job_excel.py::test_export_excel_job_error_retorna_400_sem_exporter`.
---

## Ciclo extraction: export-excel por job_id resultado invalido

**O que:** Adicionado teste de ciclo para `GET /export-excel/{job_id}` com job finalizado contendo `result` nao-dict. O contrato validado e retorno `400` sem chamar `exportar_excel`.

**Correcao de bug:** O endpoint usava `job.get("result") or job`, o que mascarava `result=[]` e chamava o exporter com o dict do job. Alterado para usar `job["result"]` quando a chave existe, tratando lista vazia/None como resultado invalido.

**Testes:** `tests/test_extraction_cycle_export_job_excel.py::test_export_excel_job_resultado_invalido_retorna_400_sem_exporter`.
---

## Ciclo extraction: export-excel por job_id falha do exporter

**O que:** Adicionado teste de ciclo para `GET /export-excel/{job_id}` com job finalizado valido quando `exportar_excel` levanta `RuntimeError`. O contrato validado e resposta `500` com mensagem estavel contendo o texto do erro.

**Producao:** Sem alteracoes.

**Testes:** `tests/test_extraction_cycle_export_job_excel.py::test_export_excel_job_falha_exporter_retorna_500_estavel`.

---

## Ciclo docs: revisao documental pos-ciclos

**O que:** Revisao estruturada de README, regras de IA e docs de arquitetura apos a sequencia de ciclos TDD. Alinhados os contratos atuais de `pre_extract` MEDIUM/HIGH, merge `[PRE-HIGH]`, `POST /upload` + `/status` + `/ws`, `cache_context`, `POST /api/export/excel`, `POST /api/export/pjc` e `GET /export-excel/{job_id}`.

**Arquivos atualizados:** `README.md`, `backend/README.md`, `.cursorrules`, `DEVELOPER.md`, `backend/docs/AI_RULES.md`, `backend/docs/PIPELINE.md`, `backend/docs/SYSTEM_OVERVIEW.md`, `backend/docs/CODE_MAP.md`, `backend/docs/CODE_INTELLIGENCE_MAP.md`, `backend/docs/AI_AGENT_EXTRACTION_CYCLE.md` e docstring em `backend/api/routers/exports.py`.

**Producao:** Sem alteracao de comportamento; apenas docstring em codigo para refletir filename ASCII `Auditoria_Calculo_*`.

**Testes:** `tests/test_extraction_cycle_export_api.py tests/test_extraction_cycle_export_job_excel.py tests/test_extraction_cycle_upload_status_api.py` -> `24 passed`; `tests/test_extraction_cycle_*.py` -> `223 passed`; suite completa backend `pytest -q` -> `1095 passed`.

# Code Intelligence Map — PJeCalc Smart Extractor

Mapa de **inteligência de código** para agentes de IA. Complementa `CODE_MAP.md`:

- `CODE_MAP.md` = lista arquivo → responsabilidade (nível granular).
- `CODE_INTELLIGENCE_MAP.md` = **onde estão os módulos por domínio**, quais são os
  **entrypoints** e **pontos de extensão seguros**.

Use este arquivo junto com:

- `SYSTEM_OVERVIEW.md` — visão macro do sistema.
- `PIPELINE.md` — fluxo em 10 passos.
- `AI_RULES.md` — regras de atuação da IA.
- `AI_NAVIGATION_LAYER.md` — índice de navegação.

---

## 1. Domínios principais e entrypoints

### 1.1 Domínios

- **API e jobs** — onde o mundo externo conversa com o sistema.
- **Pipeline de extração** — orquestração do fluxo de dados.
- **Legal Rule Engine + jurisprudência** — regras jurídicas e validação.
- **Explanation Engine** — explicações textuais e memorial jurídico.
- **Exportadores** — PJeCalc (.pjc), Excel, memória de cálculo.
- **Modelos, banco e cache** — schema, créditos, histórico, cache.
- **Frontend** — upload de PDF e visualização dos dados extraídos.
- **Testes** — verificação de comportamento e regras.

### 1.2 Entrypoints por domínio

| Domínio | Arquivos de entrada principais |
|--------|---------------------------------|
| API (HTTP/WebSocket) | `main.py` |
| Pipeline de extração | `workers/processor.py` |
| Motor jurídico | `services/legal_engine/engine.py`, `services/legal_engine/rule_registry.py` |
| Regras jurídicas | `services/legal_engine/rules/*.py`, `services/jurisprudencia/**/*.py` |
| Explanation Engine | `services/explanation_engine.py` |
| Exportadores | `services/pjc_exporter.py`, `_archive/pjc/pjc_exporter_v5.9.py`, `services/pjc_template_patcher.py`, `services/excel_exporter.py`, `memoria_calculo/generator.py` |
| Modelos e cache | `models.py`, `services/database.py`, `services/schema_version_guard.py` |
| Frontend | `frontend/index.html`, `frontend/css/main.css`, `frontend/js/app.js`, `frontend/js/render.js`, `frontend/js/lab.js` |
| Laboratório de Aprendizado | `services/learning_engine.py`, `services/learning_skill_loader.py`, `main.py` (bloco lab), `frontend/js/lab.js` |
| Self-Healing Rule Engine | `services/learning_engine.py` (processar_aprendizado_autonomo, _evaluate_shadow_rules), `services/knowledge_base.py`, `services/legal_engine/dynamic_rule_loader.py`, `workers/processor.py` (passo 8b+/8d), `main.py` (`/lab/knowledge-base*`) |
| Dashboard de Estatísticas | `main.py` (GET /api/stats), `services/knowledge_base.py`, `services/database.py` (get_total_extractions), `frontend/js/app.js` (carregarEstatisticas, iniciarPollingEstatisticas) |
| Testes | `backend/tests/**`, `backend/tests/jurisprudencia/**` |

---

## 2. Pipeline de processamento (backend/workers)

### 2.1 Arquivos principais

- `workers/processor.py`
  - Função central: `process_lawsuit_pdf(user_id, file_bytes, job_id)`.
  - Implementa os 10 passos descritos em `PIPELINE.md`.
- `main.py`
  - Endpoints que chamam o worker:
    - `/upload` → inicia job e chama `process_lawsuit_pdf` em background.
    - `/status/{job_id}` → consulta estado do job.
    - `/export-pjc/{job_id}`, `/export-excel/{job_id}` → consomem o resultado do pipeline.
  - Endpoints do Laboratório de Aprendizado (independentes do pipeline):
    - `POST /lab/analisar` — 8 arquivos (peticao, contestacao, processo, liquidacao, parecer, impugnacao, calculo_pjc, manifestacao); processar_sete_arquivos → relatório (peticao_inicial, contestacao, triade_pericial, manifestacao_pericial, etc.).
    - `POST /lab/preview` — pré-visualização do conteúdo a gravar (sem gravar).
    - `POST /lab/salvar` — chama `learning_engine.codify_insight()` (log + regra/playbook); aceita `conteudo_editado`.
    - `GET /lab/historico` — últimos aprendizados (learning_log.jsonl).

### 2.2 Fluxo entre módulos (resumo)

1. **Créditos e cache**
   - `services/database.py` — `get_user_credits`, `get_cache`, `save_cache`.
2. **Extração de texto**
   - `services/sentence_finder.py` — tipo de documento, extração do bloco relevante.
   - `services/text_processor.py` — normalização e localização de seções.
3. **Pré-extração determinística**
   - `services/pre_extractor.py` — campos HIGH/MEDIUM e `anchor` para IA.
4. **IA**
   - `services/ai_client.py` — chamada a Gemini (Flash → Pro), truncagem, playbook de skills.
5. **Pós-IA / Derivações**
   - Dentro de `workers/processor.py` + `services/calculation_parameters.py`.
6. **Pydantic**
   - `models.py` — instanciado como `ProcessoTrabalhista(**dados_limpos)`.
7. **Validação jurídica**
   - `services/legal_validator.py` → `services/legal_engine/engine.py`.
8. **Persistência e memória**
   - `services/database.py` — cache, histórico, créditos.
   - `memoria_calculo/generator.py` — `memoria_{job_id}.json`.

### 2.3 Pontos de extensão seguros

Ao adicionar comportamento novo, prefira:

- Funções auxiliares em módulos já existentes (ex.: novo passo de pós-processamento em
  `calculation_parameters.py`), mantendo o **contrato de entrada/saída existente**.
- Campos derivados adicionais no modelo (`ProcessoTrabalhista`) **respeitando**:
  - atualização de `SCHEMA_VERSION`,
  - impacto no cache (`schema_version_guard.py`),
  - impacto no ContextoJuridico do Legal Rule Engine.

Evite:

- Mudar a assinatura de `process_lawsuit_pdf` sem revisar todos os callers.
- Alterar a ordem dos 10 passos sem atualizar `PIPELINE.md` e os testes.

---

## 3. Legal Rule Engine e jurisprudência

### 3.1 Localização

- Motor principal:
  - `services/legal_engine/rule_base.py` — `LegalRule`, `ContextoJuridico`, `VerbaContexto`.
  - `services/legal_engine/engine.py` — `LegalRuleEngine.executar(dados)`.
  - `services/legal_engine/rule_registry.py` — descoberta automática das regras.
- Regras:
  - Novas regras: `services/legal_engine/rules/*.py` (uma classe por arquivo).
  - Regras legadas: `services/jurisprudencia/**` (STF, TST, CLT, consistência).

### 3.2 Como uma regra é carregada

1. `rule_registry.carregar_todas_as_regras()` varre:
   - `services/legal_engine/rules/` (motor novo),
   - `services/jurisprudencia/` (regras legadas).
2. Para cada módulo, instancia as subclasses de `LegalRule` com `id` definido.
3. IDs duplicados são detectados; apenas a **primeira regra encontrada** é usada.

### 3.3 Como criar/alterar uma regra

1. Escolha um arquivo em `services/legal_engine/rules/` como exemplo (ex.: `reflexos_proibidos.py`).
2. Crie um novo arquivo para sua regra, herdando de `LegalRule`:
   - defina `id`, `titulo`, `base_legal`, `prioridade`;
   - implemente `aplicar(contexto: ContextoJuridico)`.
3. Adicione testes em `backend/tests/jurisprudencia/` seguindo o padrão existente.
4. Execute `pytest -q` antes de concluir a mudança.

### 3.4 Zonas de alto risco

- `rule_base.py` e `engine.py`:
  - mexer aqui altera o comportamento de **todas** as regras.
  - altere apenas com motivação forte, documentação e testes abrangentes.
- `rule_registry.py`:
  - mudanças podem impedir o carregamento de regras.
  - sempre confira o log `[REGISTRY]` ao subir a API.

---

## 4. Explanation Engine

### 4.1 Responsabilidades

- `services/explanation_engine.py`:
  - recebe o resultado do Legal Rule Engine (regras aplicadas, memorial jurídico);
  - gera textos explicativos legíveis para humanos (advogados, peritos);
  - Funções sem LLM: `gerar_explicacoes`, `gerar_parecer_parcelas_apuradas`, `obter_textos_padrao_criterios_parecer`.
  - Função com LLM: `gerar_parecer_tecnico_completo` (vide 4.3).

### 4.2 Relação com o pipeline

- Chamado após a execução do Legal Rule Engine (passo 8 do pipeline).
- Usa `alertas_juridicos`, `regras_aplicadas` e `memorial_juridico` para construir explicações.
- Não deve alterar dados de domínio (ProcessoTrabalhista); apenas enriquecer com explicações.
- `gerar_parecer_tecnico_completo` é chamado no final do pipeline (processor.py) e grava `parecer_texto`, `parecer_parcelas_ia` e `parecer_model_used` em `dados_finais`.

### 4.3 Sistema Templates + Slots — Parecer Técnico Completo

O parecer técnico final é montado em camadas:

1. **Cabeçalho fixo (Python)** — dados do processo (número, partes, data-base, período, cargo, salário) extraídos de `dados`.
2. **Seção I — PARCELAS APURADAS (IA)** — slot preenchido por `ai_client.gerar_parcelas_parecer(verbas, dados, skill_parecer)`:
   - O conteúdo de `skills/parecer_pericial.md` é injetado no system prompt como "MANUAL DE REDAÇÃO" (Padrão Ouro).
   - A IA retorna **somente o texto deste bloco**, em plain text, seguindo: iniciar com "Apuração...", numeração alfabética a), b), c)..., reflexos agrupados ao final de cada verba.
   - `_strip_markdown` + pós-processamento garantem ausência de Markdown.
3. **Seção II — CRITÉRIOS ADOTADOS (Python fixo)** — textos padrão de `TEXTOS_PADRAO_CRITERIOS_PARECER`: `"correcao"` (IPCA-E/SELIC — ADC 58 STF), `"inss"` e `"irrf"`.
4. **`gerar_parecer_tecnico_completo`** concatena as três partes e retorna `{"texto": ..., "parcelas": ..., "model_used": ..., "error": ...}`.

`gerar_parecer_parcelas_apuradas` é mantido para compatibilidade (não usa LLM).

---

## 5. Exportadores e integração com PJeCalc

### 5.1 Exportador PJeCalc (.pjc)

- **Wrapper ativo**:
  - `services/pjc_exporter.py` — reexporta funções de `_archive/pjc/pjc_exporter_v5.9.py`.
- **Implementação detalhada v5.9**:
  - `_archive/pjc/pjc_exporter_v5.9.py` — constrói o XML compatível com PJeCalc 2.14.0.
- **Template patcher**:
  - `services/pjc_template_patcher.py` — recebe um `.pjc` do usuário e aplica um patch cirúrgico
    com os dados extraídos (gprec, datas, FGTS, processo, parâmetros de atualização).

### 5.2 Exportador Excel

- `services/excel_exporter.py`:
  - recebe `dados_limpos`/`dados_finais` e `job_id`;
  - gera um `.xlsx` estruturado com os principais campos em uma ou mais abas;
  - é chamado pelos endpoints `/export-excel/{job_id}` em `main.py`.

### 5.3 Memória de cálculo

- `memoria_calculo/generator.py`:
  - gera `memoria_{job_id}.json`;
  - registra, por job, quais campos e regras levaram ao resultado final;
  - é o ponto de auditoria técnica do sistema.

### 5.4 Contratos de saída (não quebrar)

- `.pjc`:
  - deve permanecer compatível com PJeCalc 2.14.0;
  - campos e tags críticos documentados em `_archive/pjc/pjc_exporter_v5.9.py`.
- `.xlsx`:
  - deve conter os campos esperados pelo fluxo de usuário (como descrito no README);
  - alterações de layout devem ser feitas com cuidado para não quebrar integrações.
- `memoria_{job_id}.json`:
  - deve continuar sendo um JSON legível e estável para auditoria.

---

## 6. Modelos, banco e cache

### 6.1 Modelos

- `models.py`:
  - `ProcessoTrabalhista` — modelo principal do JSON retornado pela API;
  - `VerbaDeferida` — representa cada verba do dispositivo;
  - `SCHEMA_VERSION` — versão do schema de saída.

### 6.2 Banco e cache

- `services/database.py`:
  - créditos de usuários;
  - cache de extrações (por hash do PDF e `SCHEMA_VERSION`);
  - histórico de extrações e jobs.
- `services/schema_version_guard.py`:
  - responsável por invalidar entradas de cache quando `SCHEMA_VERSION` muda.

### 6.3 Boas práticas para alterar o schema

1. Adicionar campo em `ProcessoTrabalhista`:
   - avaliar impacto em: pipeline, Legal Rule Engine, Explanation Engine, exportadores;
   - ajustar validações e default/normalização.
2. Atualizar `SCHEMA_VERSION` conforme política descrita no README/`AI_RULES.md`.
3. Garantir que o cache antigo seja ignorado corretamente (via `schema_version_guard.py`).

---

## 7. Frontend

### 7.1 Localização e estrutura

- **Layout SaaS** (Tailwind CSS em `index.html`):
  - **Sidebar retrátil** (classe `.sidebar-retractil` em `main.css`): largura 4rem recolhida, 16rem ao hover; fixa à esquerda (`position: fixed`); textos dos itens com `opacity-0 group-hover:opacity-100`. Main workspace tem `margin-left: 4rem`. Navegação Extrator / Laboratório / Meus Processos / Estatísticas; troca via `data-nav-view` e `_showView`; preferência em `localStorage`.
  - **Header fixo**: título e subtítulo dinâmicos, créditos, avatar; backdrop blur.
  - **Quatro views**: `#view-extrator` (split-view: upload + **resultados sem barra de KPIs** — Verbas/Alertas/Índice removidos; mais espaço vertical; Raio-X + corpo do relatório), `#view-lab`, `#view-historico`, `#view-estatisticas` (KPIs do dashboard permanecem aqui). **Identificação do processo** existe apenas no Painel Raio-X (Bloco 1); a seção "Identificação do Processo" no corpo do relatório foi removida.
- `frontend/index.html` — estrutura da aplicação; IDs/classes preservados (ex.: `#resultado`, `#status-bar`, `#view-estatisticas`, `.kpi-updated`, `#lab-section`, `.lab-steps.open`).
- `frontend/css/main.css` — estilos dos **componentes dinâmicos** (dark theme, seções, verbas, alertas, `.lab-*`, `.lab-modal-*`). Layout estrutural em Tailwind em `index.html`; animações `.kpi-updated` e `labToastIn` no inline `<style>`.
- `frontend/js/app.js` — upload PDF, polling `/status/{job_id}`, export PJC/Excel, créditos, auditoria .PJC; histórico (carregarHistorico, filtrarHistorico); **Estatísticas**: `carregarEstatisticas(silencioso)`, `iniciarPollingEstatisticas()` (5 s só quando aba Estatísticas visível), `_setKpiValue` (animação .kpi-updated ao mudar valor).
- `frontend/js/lab.js` — Lab: 8 cards (LAB_CAMPOS: peticao, contestacao, processo, …); Card 3 múltiplos (`_processoFiles`); barra de eficiência (0–100%, _EFICIENCIA_PESOS, _atualizarBarraEficiencia); `/lab/analisar`, linha do tempo, modal pré-visualização, salvar; toast .doc; após salvar: _labToastEstatisticas.
- `frontend/js/render.js` — `renderResultado(dados)` e montagem do HTML (resumo, **sem** seção "Identificação do Processo" — essa informação está só no Raio-X); `renderRaiox(raiox)` com **Bloco 1** na ordem `BLOCO1_KEYS` (alinhada a `ESTRUTURAL_KEYS` em `extraction_engine.py`: vara, juiz, datas, valor_causa, reclamante/reclamada, advogados, rito, justiça gratuita). Helpers `val`, `vv`, `statusClass`, `statusLabel`.

### 7.2 Integração com backend

Principais endpoints consumidos:

- `POST /upload` — inicia o job com o PDF.
- `GET /status/{job_id}` — retorna progresso e dados extraídos.
- `GET /export-pjc/{job_id}` — baixa o arquivo `.pjc`.
- `GET /export-excel/{job_id}` — baixa o `.xlsx`.
- `GET /credits/{user_id}` — exibe créditos disponíveis.
- Laboratório: `POST /lab/analisar`, `POST /lab/preview`, `POST /lab/salvar`, `GET /lab/historico`.
- **Dashboard de Estatísticas**: `GET /api/stats` — retorna `processos_analisados`, `regras_oficiais_ativas`, `regras_em_teste_shadow`, `omissoes_detectadas`, `eficiencia_motor` (acertos/(acertos+punicoes) % ou null), `ultimas_regras`, `top_verbas_divergencias`. Dados vêm de `knowledge_base.json` e `database.get_total_extractions()`; polling no frontend a cada 5 s só quando a aba está visível.

Ao alterar o frontend, mantenha:

- a interface de chamadas para esses endpoints;
- a compatibilidade com a estrutura de `data` retornada pelo backend.

---

## 8. Laboratório de Aprendizado da Perita

### 8.1 Objetivo e fluxo

- **8 arquivos** (marcha processual): [1] Petição Inicial [2] Contestação [3] Processo (Título Executivo, múltiplos) [4] Liquidação [5] Parecer [6] Impugnação [7] Cálculo PJC [8] Manifestação. Frontend: barra de eficiência 0–100%. Ver `docs/guia_eficiencia.md`.
- Backend gera relatório de discrepância; perita pré-visualiza e salva (regras em `legal_engine/rules/`, exemplos em `skills/sentenca_ordinaria.md`, log em `learning_log.jsonl`).

### 8.2 Arquivos e funções

- **learning_engine.py**: `processar_sete_arquivos` / `processar_cinco_arquivos` (8 args + peticao/contestacao opcionais); `_extrair_peticao_inicial`, `_extrair_contestacao`; `_extrair_titulo_executivo_multiplos` (data do texto, desempate); `_extrair_amostragem_pdf/word` (retrocompat.); `_extrair_manifestacao_pericial`, `_merge_dados_manifestacao`, `_atualizar_skill_manifestacao`; guardrails; Self-Healing; `preview_aprendizado`, `codify_insight`.
  - `preview_aprendizado(aprendizado)` — retorna o conteúdo que seria gravado (Python ou Markdown), sem gravar.
  - `codify_insight(aprendizado, numero_processo, conteudo_editado=None)` — usado por `POST /lab/salvar`: (1) registra em `learning_log.jsonl` (log enriquecido); (2) grava regra em `legal_engine/rules/` e/ou injeta exemplo em `skills/sentenca_ordinaria.md` (Gemini para gerar; fallback com template). Se `conteudo_editado` for passado, usa esse texto. Também existe `salvar_aprendizado` (compatibilidade).
- **services/learning_skill_loader.py**: `carregar_skill_para_lab(doc_type)` — carrega playbook .md para o lab (sem depender do processor).
- **main.py**: blocos dos endpoints `/lab/analisar`, `/lab/preview`, `/lab/salvar`, `/lab/historico`.
- **frontend/js/lab.js**: upload, análise, lista de aprendizados, abertura do modal de pré-visualização, envio de `conteudo_editado` em "Confirmar e Salvar".

### 8.3 Invariantes

- O laboratório **não** altera o pipeline de extração (`workers/processor.py`).
- Contratos dos endpoints de lab devem ser mantidos ao alterar frontend ou backend do lab.

---

## 9. Mapa de testes

### 9.1 Localização geral

- `backend/tests/`:
  - testes de serviços (`test_sentence_understanding.py`, `test_calculation_parameters.py`,
    `test_explanation_engine.py`, etc.).
- `backend/tests/jurisprudencia/`:
  - testes para regras específicas do Legal Rule Engine.

### 9.2 Como encontrar testes de um módulo

- Para uma regra jurídica específica:
  - arquivo em `services/legal_engine/rules/<nome>.py`;
  - testes correspondentes normalmente em `tests/jurisprudencia/test_<nome>.py` ou similar.
- Para um serviço:
  - procure por `test_<nome_do_arquivo>.py` em `backend/tests/`.

### 9.3 Boas práticas

- Ao alterar comportamento, sempre:
  1. identifique e atualize testes existentes;
  2. adicione testes novos se a funcionalidade for inédita;
  3. execute `pytest -q` antes de concluir a mudança.

---

## 10. Como usar este mapa na prática

- **Para localizar código relevante rapidamente**:
  - comece pelo domínio (pipeline, regras, export, frontend);
  - use as seções acima para ir direto aos arquivos certos;
  - só depois use busca de texto (Grep) se ainda faltar contexto.

- **Para reduzir consumo de tokens**:
  - leia primeiro este arquivo e `CODE_MAP.md`;
  - abra apenas os 2–3 arquivos listados na seção do domínio em que está trabalhando;
  - evite carregar o projeto inteiro na mesma resposta.

- **Para evitar regressões**:
  - use as seções 2, 3, 5, 6 e 8 para entender contratos críticos antes de alterar código;
  - combine com `AI_RULES.md` para seguir as regras de segurança.


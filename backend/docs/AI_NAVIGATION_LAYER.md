# AI Navigation Layer — PJeCalc Smart Extractor

Documento de **entrada obrigatória para agentes de IA** que atuam neste repositório.
Ele não repete toda a documentação: aponta **onde ler primeiro** e **o que não quebrar**.

---

## 1. Quando este arquivo é usado

- Você foi chamado para:
  - entender a arquitetura;
  - localizar módulos relevantes para uma tarefa;
  - alterar ou criar código no backend ou frontend;
  - investigar um bug sem quebrar o pipeline nem o motor jurídico.
- Antes de abrir muitos arquivos de código, **siga a navegação abaixo**.

---

## 2. Roteiros rápidos por tipo de tarefa

### 2.1 Entender o sistema em alto nível

1. Leia `docs/SYSTEM_OVERVIEW.md` — visão do produto, componentes e fluxo em 1 página.
2. Leia `docs/PIPELINE.md` — os 10 passos do pipeline e seus contratos.
3. Se precisar saber qual arquivo faz o quê, veja `docs/CODE_MAP.md`.

### 2.2 Trabalhar no pipeline de extração

1. Leia `docs/PIPELINE.md` (obrigatório).
2. Abra `workers/processor.py` apenas depois de entender os contratos.
3. Consulte `docs/CODE_INTELLIGENCE_MAP.md` → seção **2. Pipeline de processamento** para:
   - localizar serviços chamados em cada passo;
   - saber onde é seguro estender comportamento (ex.: novo pós-processamento).
4. Antes de qualquer alteração, releia:
   - `docs/AI_RULES.md` → seções **Regras críticas** e **Onde ler primeiro**.

### 2.3 Adicionar ou modificar regra jurídica

1. Leia no README do backend a seção **Motor de regras jurídicas (Legal Rule Engine)**.
2. Leia `docs/CODE_INTELLIGENCE_MAP.md` → seção **3. Legal Rule Engine e jurisprudência**.
3. Leia `docs/AI_RULES.md` → seções:
   - **Regras críticas — nunca fazer**;
   - **Convenções do projeto** (uma regra por arquivo; hierarquia 10–50).
4. A partir daí:
   - escolha uma regra existente em `services/legal_engine/rules/` como template;
   - encontre os testes correspondentes em `backend/tests/jurisprudencia/`.

### 2.4 Alterar extração de texto ou integração com IA

1. Leia `docs/PIPELINE.md` (passos 3–5).
2. Leia `docs/CODE_INTELLIGENCE_MAP.md` → partes de:
   - **2. Pipeline de processamento** (extração, playbook, IA),
   - **8. Mapa de testes** (testes de sentence/IA).
3. Só então abra:
   - `services/sentence_finder.py`,
   - `services/pre_extractor.py`,
   - `services/ai_client.py`,
   - `skills/*.md`.

### 2.9 Alterar o Parecer Técnico (Templates + Slots)

1. Leia `README.md` → seção **explanation_engine.py** e **ai_client.py**.
2. Leia `docs/CODE_INTELLIGENCE_MAP.md` → seção **4. Explanation Engine** (especialmente 4.3 — Sistema Templates + Slots).
3. Só então abra:
   - `skills/parecer_pericial.md` — Manual de Redação (Padrão Ouro); altere para ajustar tom e exemplos few-shot.
   - `services/explanation_engine.py` → `gerar_parecer_tecnico_completo` — template fixo e montagem do parecer.
   - `services/ai_client.py` → `gerar_parcelas_parecer` — chamada Gemini para a seção I.
   - `workers/processor.py` — integração e campos `parecer_texto`, `parecer_parcelas_ia`, `parecer_model_used` no JSON final.
4. Nunca usar Markdown nos textos retornados pela IA do parecer.

### 2.5 Alterar exportação (PJeCalc, Excel, memória de cálculo)

1. Leia `docs/CODE_INTELLIGENCE_MAP.md` → seção **5. Exportadores e integração com PJeCalc**.
2. Só depois abra:
   - `services/pjc_exporter.py` e `_archive/pjc/pjc_exporter_v5.9.py`,
   - `services/pjc_template_patcher.py`,
   - `services/excel_exporter.py`,
   - `memoria_calculo/generator.py`.
3. Preste especial atenção aos contratos descritos em `docs/PIPELINE.md` (passo 10) e no README.

### 2.6 Alterar modelo de dados (JSON final, verbas, campos derivados)

1. Leia `docs/SYSTEM_OVERVIEW.md` → referência ao modelo.
2. Leia `docs/CODE_INTELLIGENCE_MAP.md` → seção **6. Modelos, banco e cache**.
3. Só depois abra:
   - `models.py` (ProcessoTrabalhista, VerbaDeferida, SCHEMA_VERSION),
   - `services/database.py`,
   - `services/legal_engine/engine.py` (conversão para ContextoJuridico).
4. Leia `docs/AI_RULES.md` → recomendações sobre SCHEMA_VERSION e cache.

### 2.7 Alterar frontend (site de upload/visualização)

1. Leia `docs/SYSTEM_OVERVIEW.md` → seção de frontend (se disponível).
2. Leia `docs/CODE_INTELLIGENCE_MAP.md` → seção **7. Frontend**.
3. Só então abra:
   - `frontend/index.html` — Workspace App (Tailwind h-screen): sidebar fixa (4 views: Extrator, Laboratório, Meus Processos, Estatísticas), toolbar compacta, split-view extrator (upload-state/viewer-state + KPIs), Laboratório (**8 cards** — Tríade de Ouro Expandida), Meus Processos, #view-estatisticas (KPIs + listas); estilos .kpi-updated e labToastIn; IDs/classes preservados.
   - `frontend/css/main.css` — estilos de componentes dinâmicos (seções, verbas, alertas, lab, modal); não contém layout estrutural (sidebar/header).
   - `frontend/js/app.js` — upload, polling, status, export PJC/Excel, créditos; carregarEstatisticas(), iniciarPollingEstatisticas() (5 s só quando aba Estatísticas visível), animação .kpi-updated.
   - `frontend/js/render.js` — montagem HTML dos dados extraídos (renderResultado, verbas, alertas, parecer).
   - `frontend/js/lab.js` — Laboratório: **8 uploads** (linha do tempo; Tríade de Ouro Expandida; `manifestacao` com formKey; Conclusão grid 2×2), análise, regras preditivas cross-reference, modal de pré-visualização, salvar; após salvar: toast _labToastEstatisticas() e _labNavEstatisticas().

### 2.8 Trabalhar no Laboratório de Aprendizado da Perita

1. Leia no README do backend a seção **Laboratório de Aprendizado da Perita**.
2. Para backend: abra `services/learning_engine.py` (processar_sete_arquivos — **8 arquivos**; _extrair_amostragem_pdf/word; _extrair_manifestacao_pericial; _codificar_padroes_ataque_defesa; _atualizar_skill_manifestacao; _atualizar_skill_amostragem; _gerar_regras_preditivas_amostragem; preview_aprendizado; codify_insight) e `services/learning_skill_loader.py`; em `main.py` veja os blocos dos endpoints `/lab/analisar` (**8 campos** — inclui `manifestacao`), `/lab/preview`, `/lab/salvar`, `/lab/historico`.
3. Para frontend: abra `frontend/js/lab.js` (upload, análise, pré-visualização, modal editável, confirmar e salvar) e `frontend/css/main.css` (estilos `.lab-*`, `.lab-modal-*`).
4. Persistência: regras em `legal_engine/rules/`, exemplos em `skills/sentenca_ordinaria.md`, log em `learning_log.jsonl`. Não alterar o pipeline principal (`workers/processor.py`) ao mudar o lab.

### 2.9 Trabalhar no Self-Healing Rule Engine (aprendizado autônomo de regras)

1. Leia no README do backend:
   - seção **Laboratório de Aprendizado da Perita** (subseção *Self-Healing Rule Engine*),
   - seções de **services/learning_engine.py**, **knowledge_base.py** e **dynamic_rule_loader.py**.
2. Leia `docs/CODE_MAP.md` e `docs/CODE_INTELLIGENCE_MAP.md`:
   - procure pelo domínio **Self-Healing Rule Engine** para localizar entrypoints e contratos.
3. Só então abra:
   - `services/learning_engine.py` → `_extrair_logica_correcao_gemini`, `processar_aprendizado_autonomo`, `_evaluate_shadow_rules`;
   - `services/knowledge_base.py` → estrutura do `knowledge_base.json` e operações de ciclo de vida (`adicionar_ou_incrementar`, `marcar_acerto`, `marcar_punicao`, `stats`);
   - `services/legal_engine/dynamic_rule_loader.py` → `DynamicLegalRule`, `carregar_regras_ativas`, `executar_shadow_pipeline`;
   - `workers/processor.py` → integração no passo 8 (injeção de regras ativas + shadow mode silencioso);
   - `main.py` → endpoints `/lab/knowledge-base` (inspeção/remoção de regras dinâmicas).
4. Nunca gerar ou editar diretamente arquivos em `services/legal_engine/rules/` a partir deste domínio; deixe o fluxo de `codify_insight` e do Self-Healing decidir quando materializar regras em código.

### 2.10 Alterar o Dashboard de Estatísticas

1. Backend: `main.py` → endpoint **GET /api/stats** (lê `KnowledgeBase.stats()`, `get_total_extractions()`, monta `eficiencia_motor`, `ultimas_regras`, `top_verbas_divergencias`). Dados vêm de `knowledge_base.json` e da tabela `extracoes`; não há tabela `stats_summary` separada.
2. Frontend: `frontend/js/app.js` → `carregarEstatisticas(silencioso)`, `_setKpiValue` (animação .kpi-updated), `iniciarPollingEstatisticas()` (setInterval 5 s só quando `#view-estatisticas` visível). `frontend/index.html` → seção `#view-estatisticas`, KPIs (`#stats-kpi-*`), listas `#stats-ultimas-regras` e `#stats-top-verbas`; estilos `.kpi-updated` e `@keyframes labToastIn`.
3. Toast pós-Lab: `frontend/js/lab.js` → `_labToastEstatisticas()`, `_labNavEstatisticas()` (chamados após salvar aprendizado com sucesso).

---

## 3. Documentos de referência (jump table)

Use esta tabela para decidir **qual documentação abrir primeiro**:

| Objetivo | Ler primeiro | Depois disso |
|---------|--------------|--------------|
| Visão geral do sistema | `docs/SYSTEM_OVERVIEW.md` | `docs/PIPELINE.md` |
| Entender fluxo completo do processamento | `docs/PIPELINE.md` | `docs/CODE_INTELLIGENCE_MAP.md` (seção 2) |
| Saber qual arquivo faz o quê | `docs/CODE_MAP.md` | `docs/CODE_INTELLIGENCE_MAP.md` para detalhes por domínio |
| Entender regras e limitações para IA | `docs/AI_RULES.md` | `docs/AI_NAVIGATION_LAYER.md` (este arquivo) |
| Localizar código do Legal Rule Engine | `docs/CODE_INTELLIGENCE_MAP.md` (seção 3) | arquivos em `services/legal_engine/` e `services/jurisprudencia/` |
| Localizar exportadores (PJeCalc/Excel/memória) | `docs/CODE_INTELLIGENCE_MAP.md` (seção 5) | `_archive/pjc/`, `services/pjc_*`, `memoria_calculo/` |
| Localizar testes relevantes | `docs/CODE_INTELLIGENCE_MAP.md` (seção 9) | arquivos em `backend/tests/` |
| Tarefas no Laboratório de Aprendizado | README (seção Laboratório), este arquivo (2.8) | `services/learning_engine.py` (codify_insight), `main.py` (lab), `frontend/js/lab.js` |
| Alterar layout/UI do site (sidebar, header, painéis) | README (seção Frontend), CODE_INTELLIGENCE_MAP (seção 7) | `frontend/index.html` (Tailwind), `frontend/css/main.css` |
| Alterar ou ajustar o Parecer Técnico | README (ai_client + explanation_engine), CODE_INTELLIGENCE_MAP (seção 4.3) | `skills/parecer_pericial.md`, `explanation_engine.py`, `ai_client.py`, `processor.py` |
| Alterar Dashboard de Estatísticas | README (Frontend — Dashboard de Estatísticas), este arquivo (2.10) | `main.py` (/api/stats), `frontend/js/app.js` (carregarEstatisticas, polling), `frontend/index.html` (#view-estatisticas) |

---

## 4. Invariantes e zonas perigosas (NÃO QUEBRAR)

Leia em conjunto com `docs/AI_RULES.md`. Aqui está o resumo de **invariantes arquiteturais**:

- **Pipeline em 10 passos** (`workers/processor.py`):
  - Não altere a **ordem** dos passos sem atualizar `docs/PIPELINE.md` e os testes.
  - Não modifique a **assinatura** de `process_lawsuit_pdf` sem avaliar todos os callers.
  - O retorno deve continuar incluindo: `status`, `data` (ProcessoTrabalhista), `alertas_juridicos`, `regras_aplicadas`, `memorial_juridico`, `explicacoes`.

- **Legal Rule Engine** (`services/legal_engine/` + `services/jurisprudencia/`):
  - `LegalRuleEngine.executar(dados)` é o **único** responsável por regras jurídicas.
  - `legal_validator.py` é apenas um wrapper; não reintroduza lógica ali.
  - Uma regra por arquivo em `legal_engine/rules/`; mantenha IDs estáveis.

- **Modelos e schema** (`models.py`, `SCHEMA_VERSION`):
  - Alterou campos de `ProcessoTrabalhista`? Avalie impacto em cache e engine.
  - Mantenha `SCHEMA_VERSION` coerente com `services/schema_version_guard.py`.

- **Export PJeCalc**:
  - Respeite contratos de `_archive/pjc/pjc_exporter_v5.9.py` ao alterar wrappers.
  - Não mude o formato de saída do `.pjc` sem atualização explícita da documentação.

Sempre que tocar em qualquer zona acima:

1. Atualize os documentos relevantes (`SYSTEM_OVERVIEW`, `PIPELINE`, `CODE_INTELLIGENCE_MAP`, `AI_RULES`).
2. Execute a suíte de testes (`pytest -q`) e só aceite mudanças com 0 falhas.

---

## 5. Como navegar o repositório com Cursor

- **Para localizar rapidamente um módulo**:
  - Use `docs/CODE_MAP.md` para ir direto ao arquivo certo.
  - Use `docs/CODE_INTELLIGENCE_MAP.md` para entender o papel daquele arquivo no domínio.

- **Para responder perguntas conceituais** (ex.: “onde ficam as regras de FGTS?”):
  - Leia primeiro `docs/CODE_INTELLIGENCE_MAP.md` → subseção de FGTS.
  - Só então abra os arquivos de código listados ali.

- **Para economizar tokens**:
  - Evite abrir o README inteiro se a tarefa for localizada.
  - Prefira: `AI_NAVIGATION_LAYER` → documento específico (SYSTEM_OVERVIEW / PIPELINE / CODE_MAP / CODE_INTELLIGENCE_MAP) → somente então 1–3 arquivos de código.

Se em algum momento você estiver perdido, volte para este arquivo, escolha o tipo de tarefa na seção 2 e siga o roteiro indicado.


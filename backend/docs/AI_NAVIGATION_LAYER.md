# AI Navigation Layer — PJeCalc Smart Extractor

Documento de **entrada obrigatória para agentes de IA** que atuam neste repositório.
Não repete toda a documentação — aponta **onde ler primeiro** e **o que não quebrar**.

> **Token-tip:** Leia este arquivo inteiro (< 200 linhas). Só depois abra arquivos de código.

---

## 1. Quando usar este arquivo

- Entender a arquitetura geral.
- Localizar módulos relevantes para uma tarefa.
- Alterar ou criar código no backend ou frontend.
- Investigar um bug sem quebrar o pipeline nem o motor jurídico.

---

## 2. Roteiros rápidos por tipo de tarefa

### 2.1 Visão geral do sistema
1. `docs/SYSTEM_OVERVIEW.md` — produto, componentes, fluxo em 1 página.
2. `docs/PIPELINE.md` — os 10 passos e contratos.
3. `docs/CODE_MAP.md` — qual arquivo faz o quê.

### 2.2 Pipeline de extração (workers/processor.py)
1. `docs/PIPELINE.md` (obrigatório).
2. `docs/CODE_INTELLIGENCE_MAP.md` § 2.
3. `docs/AI_RULES.md` → Regras críticas.

### 2.3 Regra jurídica (Legal Rule Engine)
1. README § Motor de regras.
2. `docs/CODE_INTELLIGENCE_MAP.md` § 3.
3. `docs/AI_RULES.md` → Convenções.
4. Template: um arquivo em `services/legal_engine/rules/` + teste em `tests/jurisprudencia/`.

### 2.4 Extração de texto / IA
1. `docs/PIPELINE.md` passos 3–5.
2. `services/sentence_finder.py`, `services/pre_extractor.py`, `services/ai_client.py`, `skills/*.md`.

### 2.5 Parecer Técnico (templates + IA)
1. README § explanation_engine + ai_client.
2. `docs/CODE_INTELLIGENCE_MAP.md` § 4.3.
3. `skills/parecer_pericial.md`, `services/explanation_engine.py`, `services/ai_client.py` → `gerar_parcelas_parecer`.
4. Nunca usar Markdown no texto retornado pela IA do parecer.

### 2.6 Export (PJeCalc, Excel, memória de cálculo)
1. `docs/CODE_INTELLIGENCE_MAP.md` § 5.
2. `services/pjc_exporter.py`, `services/pjc_template_patcher.py`, `services/excel_exporter.py`, `memoria_calculo/generator.py`.

### 2.7 Modelo de dados (JSON final, verbas, campos)
1. `docs/SYSTEM_OVERVIEW.md` → referência ao modelo.
2. `docs/CODE_INTELLIGENCE_MAP.md` § 6.
3. `models.py` (ProcessoTrabalhista, VerbaDeferida, SCHEMA_VERSION), `services/database.py`, `services/legal_engine/engine.py`.

### 2.8 Frontend (UI, layout, views)
1. `docs/CODE_INTELLIGENCE_MAP.md` § 7.
2. Arquivos: `frontend/index.html` (Tailwind, IDs preservados), `frontend/css/main.css` (componentes dinâmicos — não contém sidebar/header), `frontend/js/app.js` (upload, polling, export, estatísticas), `frontend/js/render.js` (renderResultado), `frontend/js/lab.js` (Laboratório 8 cards).
3. Nunca introduzir React/Vue — o projeto usa Vanilla JS.
4. Preservar IDs: `#resultado`, `#view-extrator`, `#view-lab`, `#view-historico`, `#view-estatisticas`, `.lab-section.open`, `.kpi-updated`.

### 2.9 Laboratório de Aprendizado da Perita
**Backend:** `services/learning_engine.py` (§ 5) + `services/learning_skill_loader.py`.
**Endpoints:** `/lab/analisar` (8 campos: peticao, contestacao, processo, liquidacao, parecer, impugnacao, calculo_pjc, manifestacao; `processo` = List[UploadFile]), `/lab/preview`, `/lab/salvar`, `/lab/historico`, `/lab/knowledge-base`.
**Frontend:** `lab.js` — 8 cards (LAB_CAMPOS), Card 3 múltiplos (`_processoFiles`), barra de eficiência (`_calcularEficiencia`, `_atualizarBarraEficiencia`), `.doc` → toast. **Detalhes Lab:** `docs/guia_eficiencia.md` (evite duplicar aqui).

### 2.10 Self-Healing Rule Engine
1. README § Self-Healing.
2. `services/learning_engine.py` → `_extrair_logica_correcao_gemini`, `processar_aprendizado_autonomo`, `_evaluate_shadow_rules`.
3. `services/knowledge_base.py` → estrutura `knowledge_base.json` e ciclo de vida.
4. `services/legal_engine/dynamic_rule_loader.py` → `DynamicLegalRule`, `carregar_regras_ativas`, `executar_shadow_pipeline`.
5. `workers/processor.py` → passo 8 (regras ativas + shadow mode).
6. Nunca editar diretamente `services/legal_engine/rules/` a partir deste domínio.

### 2.11 Dashboard de Estatísticas
1. **Backend:** `main.py` → `GET /api/stats` (KnowledgeBase.stats() + get_total_extractions()).
2. **Frontend:** `frontend/js/app.js` → `carregarEstatisticas`, `_setKpiValue`, `iniciarPollingEstatisticas()` (5 s só quando `#view-estatisticas` visível). `frontend/index.html` → `#view-estatisticas`, `#stats-kpi-*`, `#stats-ultimas-regras`, `#stats-top-verbas`.

---

## 3. Tabela de referência rápida

| Objetivo | Ler primeiro | Depois |
|----------|-------------|--------|
| Visão geral | `docs/SYSTEM_OVERVIEW.md` | `docs/PIPELINE.md` |
| Qual arquivo faz o quê | `docs/CODE_MAP.md` | `docs/CODE_INTELLIGENCE_MAP.md` por domínio |
| Regras para IA | `docs/AI_RULES.md` | este arquivo (§ 2) |
| Legal Rule Engine | `docs/CODE_INTELLIGENCE_MAP.md` § 3 | `services/legal_engine/` + `services/jurisprudencia/` |
| Exportadores | `docs/CODE_INTELLIGENCE_MAP.md` § 5 | `services/pjc_*`, `memoria_calculo/` |
| Testes | `docs/CODE_INTELLIGENCE_MAP.md` § 9 | `backend/tests/` |
| Laboratório | README § Laboratório, `docs/guia_eficiencia.md` (níveis, pesos, marcha) | `learning_engine.py`, `main.py`, `lab.js` |
| Diretrizes prompt Lab | `docs/guia_eficiencia.md` | Não duplicar em outros docs (economia tokens) |
| Frontend layout/UI | `docs/CODE_INTELLIGENCE_MAP.md` § 7 | `frontend/index.html`, `frontend/css/main.css` |
| Parecer Técnico | `docs/CODE_INTELLIGENCE_MAP.md` § 4.3 | `skills/parecer_pericial.md`, `explanation_engine.py` |
| Dashboard Estatísticas | este arquivo § 2.11 | `main.py` (/api/stats), `frontend/js/app.js` |

---

## 4. Invariantes — NÃO QUEBRAR

### Pipeline (workers/processor.py)
- Não altere a **ordem** dos 10 passos sem atualizar `docs/PIPELINE.md` e testes.
- Assinatura de `process_lawsuit_pdf` é contrato público; avalie todos os callers antes de mudar.
- Retorno deve incluir: `status`, `data`, `alertas_juridicos`, `regras_aplicadas`, `memorial_juridico`, `explicacoes`.

### Legal Rule Engine (services/legal_engine/)
- `LegalRuleEngine.executar(dados)` é o **único** responsável por regras jurídicas.
- `legal_validator.py` é wrapper; não reintroduza lógica ali.
- Uma regra por arquivo; IDs estáveis.

### Modelos e schema (models.py)
- Alterou campos de `ProcessoTrabalhista`? Avalie impacto em cache e engine.
- `SCHEMA_VERSION` coerente com `services/schema_version_guard.py`.

### Export PJeCalc
- Respeite contratos de `_archive/pjc/pjc_exporter_v5.9.py`.
- Não mude formato de saída do `.pjc` sem documentação atualizada.

### Laboratório (learning_engine.py)
- `processar_cinco_arquivos` e `processar_sete_arquivos` são os únicos entrypoints.
- Guardrails (`_filtrar_falsos_positivos_verba_ausente`, `_filtrar_logicas_verba_ausente_falsas`, `_filtrar_aprendizados_verba_ausente_falsas`) devem rodar **após** qualquer enriquecimento do relatório e **antes** do retorno ao frontend.
- `_canon_empresa_e_verba_esta(relatorio)` é o helper compartilhado — não duplicar lógica de canonização.

Sempre que tocar uma zona acima: atualize os docs relevantes + `pytest -q` com 0 falhas.

---

## 5. Estado atual do learning_engine.py — mapa de funções

### Funções de extração e texto
| Função | Descrição |
|--------|-----------|
| `_extrair_texto_docx(bytes)` | DOCX → texto puro (zipfile, sem python-docx) |
| `_extrair_texto_arquivo(bytes, filename)` | PDF/DOCX/DOC → texto |
| `_extrair_sentenca(pdf_bytes)` | PDF sentença → pipeline completo |
| `_extrair_processo(bytes, filename)` | Roteador: PDF → sentenca, DOC/DOCX → Gemini |
| `_classificar_tier_decisao(filename)` | Nome do arquivo → `"TST"` / `"TRT"` / `"1GRAU"` |
| `_extrair_titulo_executivo_multiplos([(bytes, fn)])` | N docs → hierarquia 1ºgrau→TRT→TST; desempate mesma instância = data extraída do texto (`_extrair_data_documento`); retorna `verbas_reformadas`, `datas_documentos`, `instancia_final` |
| `_extrair_liquidacao(bytes, filename)` | PJC/PDF/DOCX → verbas, índice, juros |
| `_extrair_manifestacao(bytes)` | DOCX → fundamentos + discrepâncias |
| `_extrair_impugnacao(bytes, filename)` | PDF/DOCX → fundamentos + argumentos |
| `_extrair_calculo_pjc(bytes, filename)` | Delega para `_extrair_liquidacao` |
| `_extrair_amostragem_pdf(bytes, filename)` | PDF holerites → teses + irregularidades (Gemini) |
| `_extrair_amostragem_word(bytes, filename)` | DOCX → estilo da perita → `skills/amostragem_style.md` |
| `_extrair_manifestacao_pericial(bytes, filename)` | **Duplo Style Transfer** — analisa frases de impacto, súmulas, padrões Ataque/Defesa, argumento vencedor; chamado para Card 6 (impugnação) E Card 8 (manifestação) |
| `_merge_dados_manifestacao(base, novo)` | Junta resultados de impugnação + manifestação sem duplicar; alimenta `skills/manifestacao_style.md` com ambos |

### Guardrails anti-alucinação
| Função | Onde chamada | O que faz |
|--------|-------------|-----------|
| `_canon_empresa_e_verba_esta(relatorio)` | base dos 3 guardrails | Constrói set canônico de verbas da liquidação + PJC; retorna função `verba_esta(nome)` |
| `_filtrar_falsos_positivos_verba_ausente(relatorio)` | `processar_cinco_arquivos` — após `_enriquecer_relatorio_com_extras` | Remove discrepâncias `verba_ausente` quando a verba canônica existe na liquidação/PJC |
| `_filtrar_logicas_verba_ausente_falsas(logicas, relatorio)` | `processar_aprendizado_autonomo` — logo após Gemini | Remove hipóteses KB `verba_ausente` quando verba existe no cálculo da empresa |
| `_filtrar_aprendizados_verba_ausente_falsas(relatorio)` | `processar_cinco_arquivos` e `processar_sete_arquivos` — antes do return | Remove aprendizados com `tipo=verba_ausente` falsos do JSON final |

### Prompt Gemini (_extrair_logica_correcao_gemini)
- **REGRA 1:** proibido `verba_ausente` se a verba não constar nas discrepâncias filtradas.
- **REGRA 2:** se houver tese matemática (avos, frações, método de cálculo), criar regra baseada nesse argumento — ignorar discrepâncias genéricas.
- **REGRA 3:** retornar `[]` se discrepâncias filtradas vazias e sem tese matemática clara.
- Early-exit Python: se `not discrepancias_filtradas and not tese_tem_detalhe` → retorna `[]` sem chamar Gemini.

### Funções de aprendizado autônomo
| Função | Descrição |
|--------|-----------|
| `processar_aprendizado_autonomo(relatorio, numero)` | Fase 1: extrai hipóteses (Gemini + guardrail) → KB; Fase 2: avalia shadow rules |
| `_evaluate_shadow_rules(relatorio, kb)` | Acerto (+1) / Punição (-1); shadow→active em score≥3; shadow→deleted em score≤-1 |
| `_extrair_logica_correcao_gemini(relatorio)` | Gemini → hipóteses JSON; com 3 REGRAS ESTRITAS no prompt + early-exit Python |

### Entrypoints públicos
| Função | Descrição |
|--------|-----------|
| `processar_sete_arquivos(...)` | 8 arquivos + `processo_arquivos: List[tuple]` (Card 3 múltiplos); chama `processar_cinco_arquivos` |
| `processar_cinco_arquivos(...)` | Fluxo principal; inclui guardrails e filtro de aprendizados antes do return |
| `gerar_relatorio_discrepancia(dados_sentenca, dados_liquidacao, dados_manifestacao)` | Cross-reference principal; usa `LegalRule._canonizar_verba` + `_verba_corresponde_na_liquidacao` |
| `preview_aprendizado(aprendizado)` | Retorna conteúdo que seria gravado (sem gravar) |
| `salvar_aprendizado(...)` | Persiste regra/playbook em disco |
| `codify_insight(...)` | Self-Healing: gera rascunho Python + few-shot + registra log |

---

## 6. Como navegar com eficiência (economizar tokens)

1. **Localizar módulo**: use `docs/CODE_MAP.md` → vai direto ao arquivo certo.
2. **Entender papel no domínio**: use `docs/CODE_INTELLIGENCE_MAP.md` → subseção do domínio.
3. **Resposta conceitual** (ex.: "onde ficam as regras de FGTS?"): leia `CODE_MAP.md` → tabela "Por domínio".
4. **Nunca abra o README inteiro** se a tarefa for localizada — use os docs menores.
5. **Caminho ideal**: `AI_NAVIGATION_LAYER` → doc específico → 1–3 arquivos de código.
6. **Guardrails, Duplo Style Transfer, Título Executivo**: ver § 5 acima — não releia o código fonte inteiro.

Se estiver perdido: volte a este arquivo → escolha o tipo de tarefa em § 2 → siga o roteiro.

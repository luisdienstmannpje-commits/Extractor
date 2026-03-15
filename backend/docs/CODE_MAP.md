# Mapa de código — arquivo → responsabilidade

Uso: buscar por **nome de arquivo** ou por **domínio** (FGTS, Laboratório, guardrails, etc.).
Para regras do motor, ver também a tabela de regras no README.

---

## Por arquivo (raiz e workers)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `main.py` | API FastAPI; upload; jobs; WebSocket; export PJC/Excel; lab (`/lab/analisar`, `/lab/preview`, `/lab/salvar`, `/lab/gerar-docx` [Ghostwriter], `/lab/historico`, `/lab/knowledge-base`); `GET /api/stats`; timeout 5 min. |
| `config.py` | Env: GEMINI_API_KEY, Firebase, MAX_FILE_SIZE_MB, SCHEMA_VERSION, RAPIDFUZZ_THRESHOLD, etc. |
| `models.py` | ProcessoTrabalhista, VerbaDeferida (Pydantic); validadores; SCHEMA_VERSION. |
| `workers/processor.py` | Pipeline 10 passos: process_lawsuit_pdf; orquestra todos os serviços. |

---

## Por arquivo — services (extração e texto)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `sentence_finder.py` | `extract_sentence_from_pdf(bytes) → (texto, doc_type)`; OCR híbrido; bloco de decisão. |
| `text_processor.py` | `normalize_text`; `find_section_hybrid` (dispositivo etc.). |
| `pre_extractor.py` | `pre_extract` (regex/campos HIGH/MEDIUM); `build_anchor_section`. |
| `ai_client.py` | `extract_data_with_gemini(texto, playbook, anchor_section)` — cascata Flash→Pro; truncagem; prompt. `gerar_parcelas_parecer(verbas, dados, skill_parecer)` — seção I do parecer (plain text, sem Markdown) orientado por `skills/parecer_pericial.md`. |
| `ai_writer.py` | **Ghostwriter:** `gerar_texto_manifestacao(...)` — Gemini com **Instrução de Tom e Voz** (`manifestacao_style.md`); imita expressões ("esperando haver se desincumbido do múnus", "vem, respeitosamente"); retorna `introducao`, `secoes[]`, `tabela_comparativa[]` (texto limpo). |
| `document_generator.py` | **Ghostwriter:** `gerar_minuta(...)` — python-docx: cabeçalho (Processo, Reclamante, Reclamada), MANIFESTAÇÃO AOS CÁLCULOS, seções, tabela **Table Grid** (prejuízo financeiro), encerramento "Pede Deferimento. [Cidade], [Data]." + espaço assinatura Perito Assistente; retorna bytes .docx. |
| `extraction_engine.py` | **Raio-X:** `enriquecer_para_raiox(dados)` — categoriza em Estrutural (incl. prescricao_quinquenal), Contratual, Condenação; adicionais, verbas_lista; Dicas do Laboratório via KB. Ordem de exibição no frontend é PJe-Calc: Identificação/Juízo → Parâmetros Estruturais → Índices (mini-cards) → Verbas (badges) → Dicas (alerta fixo). |
| `normalizer.py` | `normalizar`; `normalizar_lista`; `eh_chave_valida`; `listar_variacoes`. |
| `sentence_understanding.py` | `extrair_verbas_deferidas`; `extrair_reflexos`; `interpretar_decisao`; etc. |

---

## Por arquivo — services (validação e regras)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `legal_validator.py` | `validar_dados`; `validar_dados_completo`; delega ao Legal Rule Engine. |
| `legal_engine/rule_base.py` | `ContextoJuridico`; `VerbaContexto`; `LegalRule` (base); `LegalRule._canonizar_verba(nome) → str` (normalização canônica de verbas — usado pelos guardrails do lab). |
| `legal_engine/engine.py` | `LegalRuleEngine`; `executar(dados)`. |
| `legal_engine/rule_registry.py` | `carregar_todas_as_regras`; descoberta em `rules/` e `jurisprudencia/`. |
| `legal_engine/dynamic_rule_loader.py` | `DynamicLegalRule`; `carregar_regras_ativas`; `executar_shadow_pipeline`. |
| `legal_engine/rules/*.py` | Uma regra por arquivo (ReflexosProibidosRule, BisInIdemRule, etc.). |
| `jurisprudencia/**/*.py` | Regras legadas (STF, TST, CLT, consistência). |

---

## Por arquivo — services (cálculo e exportação)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `calculation_parameters.py` | `gerar_parametros`; período, divisor, jornada, FGTS, INSS, honorários. |
| `explanation_engine.py` | `gerar_explicacoes`; `gerar_parecer_tecnico_completo` (template fixo + slot IA). |
| `pjc_template_patcher.py` | `aplicar_patch(template_xml, dados)`; `validar_patch`; `gerar_nome_arquivo`. |
| `pjc_parser.py` | Ler `.pjc` (XML) → `PjcDadosBasicos` (índice, juros, divisor, verbas). |
| `pjc_auditor.py` | Sentença (IA) vs. parâmetros `.pjc` → lista de divergências. |
| `excel_exporter.py` | Export Excel (abas estruturadas). |

---

## Por arquivo — services (persistência e utilitários)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `database.py` | Créditos; cache; extrações; histórico; jobs; cleanup. |
| `schema_version_guard.py` | Guarda de versão do schema (invalidar cache). |
| `verba_deduplicator.py` | Deduplicação de verbas (nome + período). |
| `learning_skill_loader.py` | `carregar_skill_para_lab(doc_type)` — playbook para o lab. |
| `process_timeline_extractor.py` | **PJe Timeline Extractor**: `PjeTimelineExtractor._mapear_sumario(pdf_bytes)` (índice nas primeiras 15 pág.), `_buscar_por_ancoras()` (fallback regex), `extract_timeline_from_pdf(pdf_bytes)` → `{mapa, textos, log}`; `extrair_metadados_peca(chave, texto, ai_client)` (ETAPA 3 — Gemini por peça). Chaves: peticao_inicial, contestacao, sentenca, acordao, liquidacao, impugnacao, parecer. |
| `knowledge_base.py` | `KnowledgeBase` — banco `knowledge_base.json`; campos: rule_id, descricao, condicao, acao, base_legal, confidence_score, status (shadow/active/deleted), casos_vistos, acertos, punicoes; operações: `adicionar_ou_incrementar`, `marcar_acerto`, `marcar_punicao`, `stats`. |

---

## Por arquivo — learning_engine.py (detalhe completo)

Entrypoints públicos:

| Função | Assinatura resumida |
|--------|---------------------|
| `processar_sete_arquivos` | 8 arquivos + `processo_arquivos: List[tuple]` → relatório completo com Style Transfer + guardrails |
| `processar_cinco_arquivos` | 5 arquivos (compat.); mesmo pipeline sem Fases de Conhecimento |
| `gerar_relatorio_discrepancia` | `(dados_sentenca, dados_liquidacao, dados_manifestacao) → dict` |
| `preview_aprendizado` | `(aprendizado) → dict` (conteúdo sem gravar) |
| `salvar_aprendizado` | Persiste em disco |
| `codify_insight` | Self-Healing: rascunho Python + few-shot + log |
| `processar_aprendizado_autonomo` | Gemini hipóteses → KB; avaliar shadow rules |

Funções privadas notáveis:

| Função | Descrição |
|--------|-----------|
| `_classificar_tier_decisao(filename, texto?)` | **Prioridade nome:** 1grau/ATOrd/Sentenca→1GRAU; 2grau/ROT/Acordao→TRT. Texto só se nome genérico; ignora 1000 chars (header PJe); no texto só Recurso Ordinário/Relator:/Acórdão. |
| `_extrair_data_documento(texto)` | Remove linha "Data da Autuação" antes de regex; prioriza final do doc. |
| `_extrair_titulo_executivo_multiplos([(bytes,fn)])` | Tier diferente = ambos mantidos; um por tier; desempate por data; prompt Análise de Reforma. |
| `_merge_dados_manifestacao(base, novo)` | Junta listas de padrões sem duplicatas |
| `_extrair_manifestacao_pericial(bytes, filename)` | Gemini: frases, súmulas, padrões Ataque/Defesa, argumento vencedor → `manifestacao_style.md` |
| `_canon_empresa_e_verba_esta(relatorio)` | Helper de canonização compartilhado pelos guardrails |
| `_filtrar_falsos_positivos_verba_ausente(relatorio)` | Guardrail discrepâncias |
| `_filtrar_logicas_verba_ausente_falsas(logicas, relatorio)` | Guardrail hipóteses KB |
| `_filtrar_aprendizados_verba_ausente_falsas(relatorio)` | Guardrail aprendizados antes do return |
| `_extrair_logica_correcao_gemini(relatorio)` | Prompt com REGRAS ESTRITAS 1–3 + early-exit Python |
| `_evaluate_shadow_rules(relatorio, kb)` | Acerto/punição → ciclo de vida shadow→active/deleted |

---

## Por arquivo — skills (playbooks)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `skills/sentenca_ordinaria.md` | Playbook extração sentença; recebe exemplos few-shot pelo Lab. |
| `skills/parecer_pericial.md` | Manual de Redação do Parecer Técnico — Padrão Ouro; system prompt para `gerar_parcelas_parecer`. |
| `skills/amostragem_style.md` | Guia de estilo da perita — acumulado via Amostragem Word (Style Transfer). |
| `skills/manifestacao_style.md` | Retórica de combate — acumulado via **Card 6 (impugnação) E Card 8 (manifestação)**; duplo Style Transfer. |

---

## Por arquivo — memoria_calculo

| Arquivo | Responsabilidade |
|---------|-------------------|
| `memoria_calculo/generator.py` | `gerar_memoria`; gera `memoria_{job_id}.json`. |

---

## Por arquivo — docs (documentação para IA)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `docs/AI_NAVIGATION_LAYER.md` | **Ponto de entrada obrigatório** — roteiros, invariantes, mapa do learning_engine. |
| `docs/AI_RULES.md` | Regras de conduta (nunca fazer, convenções, testes). |
| `docs/SYSTEM_OVERVIEW.md` | Visão macro do produto — 1 página. |
| `docs/PIPELINE.md` | Os 10 passos e contratos. |
| `docs/CODE_MAP.md` | Este arquivo. |
| `docs/CODE_INTELLIGENCE_MAP.md` | Mapa por domínio (pipeline, motor, exportadores, frontend, testes). |
| `docs/guia_eficiencia.md` | Diretrizes de prompt: hierarquia processual, guardrails, nomenclatura de arquivos, duplo Style Transfer, boas práticas de upload. |

---

## Por arquivo — Frontend (frontend/)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `index.html` | SPA Tailwind: sidebar 4 views, header, split-view extrator, Lab 8 cards (Card 3 = `multiple` + `_processoFiles`), estatísticas; IDs preservados para JS. |
| `css/main.css` | Estilos componentes dinâmicos (lab, modal, verbas, alertas). Não contém layout estrutural. |
| `js/app.js` | Upload, polling, export PJC/Excel, créditos, histórico, estatísticas (polling 5 s). |
| `js/render.js` | `renderResultado(dados)` — HTML de resumo, verbas, alertas, parecer. |
| `js/lab.js` | 8 cards; Card 3 múltiplos arquivos (`_processoFiles`, `_classifyDecisaoTier`, `_renderProcessoFiles`); `_isDocAntigo` + toast `.doc`; FormData com `form.append("processo", f)` para cada arquivo; limpa acumulador no `finally`. |

---

## Por domínio (onde procurar)

| Domínio | Arquivos principais |
|---------|---------------------|
| Pipeline | `workers/processor.py` |
| Regras jurídicas | `legal_engine/rule_base.py`, `engine.py`, `rule_registry.py`; `legal_engine/rules/*.py`; `jurisprudencia/**/*.py` |
| FGTS | `legal_engine/rules/fgts_*.py`; `jurisprudencia/orientacoes/oj_42.py`, `oj_195.py`; `jurisprudencia/sumulas/sumula_305.py` |
| Datas e consistência | `legal_engine/rules/consistencia_datas.py`; `jurisprudencia/consistencia/datas.py` |
| Aviso prévio | `legal_engine/rules/aviso_previo_*.py`; `jurisprudencia/clt/lei_12506.py` |
| Multas 467/477 | `legal_engine/rules/multa_467.py`, `multa_477.py`, `multa_477_valor.py` |
| Reflexos e DSR | `legal_engine/rules/reflexos_proibidos.py`, `he_reflexo_dsr.py`, `dsr_bis_in_idem.py`; `jurisprudencia/orientacoes/oj_394.py` |
| Explicações jurídicas | `services/explanation_engine.py` |
| Laboratório / Aprendizado | `services/learning_engine.py`, `learning_skill_loader.py`; `main.py` (lab); `frontend/js/lab.js`. **Card Provas = hub:** multi-upload → `amostragens`; `_fusionar_provas_com_cards` + `_classificar_tipo_documento_prova`; prompt unificado em `<AMOSTRAGENS_DA_PERITA>`. **Ghostwriter:** `POST /lab/gerar-docx` (body = relatório) → `document_generator.gerar_minuta` + `ai_writer.gerar_texto_manifestacao` → .docx da Manifestação (estilo `manifestacao_style.md`). |
| Guardrails anti-alucinação | `services/learning_engine.py` → `_canon_empresa_e_verba_esta`, `_filtrar_*` |
| Título Executivo Complexo | `learning_engine.py` → `_classificar_tier_decisao` (prioridade nome: 1grau/ATOrd→1GRAU, 2grau/ROT→TRT; texto só se genérico, ignorar header PJe), `_extrair_data_documento` (remove linha Data da Autuação), `_extrair_titulo_executivo_multiplos` (tier diferente = ambos mantidos); `main.py`; `lab.js` → `_processoFiles` |
| PJe Timeline Extractor (um PDF no Card 3) | `services/process_timeline_extractor.py`; `learning_engine` chama quando len(processo_arquivos)==1 e PDF; relatório: `timeline_fatiamento`, `pecas_extraidas_do_pdf`; frontend barra de eficiência soma pesos das peças extraídas |
| Duplo Style Transfer | `services/learning_engine.py` → `_extrair_manifestacao_pericial`, `_merge_dados_manifestacao`; `skills/manifestacao_style.md` |
| Self-Healing Rule Engine | `services/learning_engine.py` → `processar_aprendizado_autonomo`, `_evaluate_shadow_rules`; `services/knowledge_base.py`; `legal_engine/dynamic_rule_loader.py` |
| Dashboard Estatísticas | `main.py` (`GET /api/stats`); `services/knowledge_base.py`; `database.get_total_extractions`; `frontend/js/app.js` (`carregarEstatisticas`, polling) |
| IA e prompt | `services/ai_client.py`; `skills/*.md` |
| PDF e texto | `services/sentence_finder.py`, `text_processor.py`, `pre_extractor.py` |

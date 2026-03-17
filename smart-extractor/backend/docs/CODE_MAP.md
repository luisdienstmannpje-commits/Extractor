# Mapa de código — arquivo → responsabilidade

Uso: buscar por **nome de arquivo** ou por **domínio** (FGTS, Laboratório, guardrails, etc.).
Para regras do motor, ver também a tabela de regras no README.

---

## Por arquivo (raiz e workers)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `main.py` | API Gateway FastAPI; inicializa a app, aplica middleware (CORS, logs) e inclui os roteadores em `api/routers/`; não contém mais lógica de upload, WebSocket, laboratório ou estatísticas. |
| `api/routers/extractor.py` | Motor principal de extração: rotas `/upload`, `/upload-pjc/{job_id}`, `/status/{job_id}`, `/jobs/{job_id}`, `/export-excel/{job_id}`, `/health` e WebSocket `/ws/{job_id}`; gerencia jobs, timeout e notificação em background. |
| `api/routers/lab.py` | Rotas do Laboratório: `/lab/analisar`, `/lab/preview`, `/lab/salvar`, `/lab/gerar-docx`, `/lab/historico` e `/lab/knowledge-base`; delega para `services/learning_engine.py` e `services/document_generator.py`. |
| `api/routers/admin.py` | Administração e Dashboard: `/api/status`, `/credits/{user_id}`, `/historico/{user_id}`, `/api/knowledge-base`, `/api/stats` e `/api/admin/reset-contagem`; usa `KnowledgeBase(tenant_id=user_id)` para Multi-tenancy e `database.get_total_extractions`. |
| `api/routers/exports.py` | Exportação dedicada de resultados finais (`.xlsx`, `.pjc`), mantendo compatibilidade com rotas de download/geração do extrator. |
| `config.py` | Env: GEMINI_API_KEY, Firebase, MAX_FILE_SIZE_MB, SCHEMA_VERSION, RAPIDFUZZ_THRESHOLD, etc. |
| `models.py` | ProcessoTrabalhista, VerbaDeferida (Pydantic); validadores; SCHEMA_VERSION. justica_gratuita: field_validator normaliza "concedida"/"deferida"/"sim" → true. |
| `workers/processor.py` | Pipeline 10 passos: `process_lawsuit_pdf` e `process_lawsuit_dossie`. **Regex híbrida:** cabeçalho + final do doc para `data_ajuizamento`, `valor_causa`, **data_sentenca** (Assinado eletronicamente / Data do Julgamento / Publicado em); merge pós-Gemini. Dossiê: `_extrair_texto_arquivo_dossie`, `_hash_dossie`; super-contexto + cache. |

---

## Por arquivo — services (extração e texto)

| Arquivo | Responsabilidade |
|---------|-------------------|
| `sentence_finder.py` | `extract_sentence_from_pdf(bytes) → (texto, doc_type)`; OCR híbrido; bloco decisório. **Capa PJe preservada:** CAPA_PAGES quando bloco não começa na pág 1; nunca remove Data da Autuação nem primeiros chars. |
| `text_processor.py` | `normalize_text`; `find_section_hybrid` (dispositivo etc.). |
| `pre_extractor.py` | `pre_extract` (regex/campos HIGH/MEDIUM); `build_anchor_section`. |
| `ai_client.py` | `extract_data_with_gemini` — cascata Flash→Pro; truncagem 40%+60%; prompt com instrução para cruzar múltiplos documentos/tabelas/imagens no Raio-X. **Dossiê multimodal:** `extrair_texto_ou_descricao_imagem(image_bytes, mime_type)` — Gemini OCR/descrição para JPG/PNG. `gerar_parcelas_parecer` — `skills/parecer_pericial.md`. |
| `ai_writer.py` | **Ghostwriter:** `gerar_texto_manifestacao(...)` — Gemini com **Instrução de Tom e Voz** (`manifestacao_style.md`); imita expressões ("esperando haver se desincumbido do múnus", "vem, respeitosamente"); retorna `introducao`, `secoes[]`, `tabela_comparativa[]` (texto limpo). |
| `document_generator.py` | **Ghostwriter:** `gerar_minuta(...)` — python-docx: cabeçalho (Processo, Reclamante, Reclamada), MANIFESTAÇÃO AOS CÁLCULOS, seções, tabela **Table Grid** (prejuízo financeiro), encerramento "Pede Deferimento. [Cidade], [Data]." + espaço assinatura Perito Assistente; retorna bytes .docx. |
| `extraction_engine.py` | **Raio-X:** `enriquecer_para_raiox(dados)` — ESTRUTURAL_KEYS (Bloco 1) inclui prescricao_quinquenal; CONTRATUAL_KEYS (Bloco 2) sem prescricao. Categorias: Estrutural, Contratual, Condenação; Dicas Lab. Frontend React consome o envelope e exibe o Raio-X (componentes em `frontend/src/`). |
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
| `lab/learning_io.py` | **Persistência do Laboratório (refatoração Passo 1):** `preview_aprendizado`, `salvar_aprendizado`, `_salvar_rascunho_regra`, `_salvar_few_shot` / `_salvar_insight_em_markdown`, `_registrar_log` / `_registrar_no_log_de_aprendizado`; caminhos `LEARNING_LOG_PATH`, skills e rules; JSONL em `learning_log.jsonl`. |
| `lab/extractors.py` | **Limpeza e regex do Laboratório (refatoração Passo 2):** `regex_verbas`, `regex_indice`, `regex_juros`, `regex_divisor`, `liquidacao_from_text`; `extrair_fundamentos_juridicos`, `extrair_discrepancias_perita`; `remover_linha_autuacao`, `contexto_eh_autuacao`; `CABECALHO_PJE_CHARS`, `texto_apos_cabecalho_pje`, `tem_indicador_2grau_apos_cabecalho`. Canonização de verbas permanece em `LegalRule._canonizar_verba` (rule_base). |
| `lab/titulo_executivo.py` | **Título Executivo e Tiers (refatoração Passo 3):** `classificar_tier_decisao(filename, texto?)` → 1GRAU/TRT/TST (prioridade nome; texto só se genérico; ignora 1000 chars via extractors); `extrair_data_documento(texto)` (remove linha Data da Autuação, prioriza final do doc); `extrair_titulo_executivo_multiplos(arquivos, ..., extrair_processo, extrair_texto_arquivo, bloco_amostragens_perita)` — tier diferente = ambos mantidos, desempate por data na mesma instância, prompt Análise de Reforma. Constantes: TIER_ORDER, TIER_LABELS, MESES_NUM, FALLBACK_DATE. |
| `lab/discrepancy.py` | **Confronto Sentença vs. Cálculo e guardrails (refatoração Passo 4):** `gerar_relatorio_discrepancia(dados_sentenca, dados_liquidacao, dados_manifestacao)` — compara verbas deferidas vs. liquidação (canonização + substring + fuzzy), índice de correção, juros de mora; gera discrepâncias e aprendizados. `verba_corresponde_na_liquidacao(verba, verbas_liq_norm, verbas_liq_canon, threshold?)` — match canonizado obrigatório; fallback substring/fuzzy. `canon_empresa_e_verba_esta(relatorio)` → (set canonizado, verba_esta(verba)). Guardrails: `filtrar_falsos_positivos_verba_ausente`, `filtrar_logicas_verba_ausente_falsas`, `filtrar_aprendizados_verba_ausente_falsas` — removem falsos positivos quando verba canonizada existe na liquidação/PJC. **Depende de** `LegalRule._canonizar_verba` (legal_engine/rule_base). |
| `lab/style_transfer.py` | **Duplo Style Transfer (refatoração Passo 5):** `merge_dados_manifestacao(base, novo)` — junta resultados Impugnação (Card 6) + Manifestação (Card 8) sem duplicatas. `extrair_manifestacao_pericial(file_bytes, filename, *, extrair_texto_arquivo, chamar_gemini_para_codify, skills_dir)` — analisa peça com Gemini (frases de impacto, padrões Ataque/Defesa, argumento vencedor); codifica padrões no KB; atualiza `skills/manifestacao_style.md`. `atualizar_skill_manifestacao(skills_dir, dados, trecho, filename)` — append de bloco em manifestacao_style.md. Depende de `extractors.extrair_fundamentos_juridicos` e `KnowledgeBase`. |
| `lab/self_healing.py` | **Self-Healing e codificação de insight (refatoração Passo 6):** `codify_insight(aprendizado, numero_processo, conteudo_editado=None, *, rules_dir, skills_dir, learning_log_path, chamar_gemini_para_codify)` — consolida aprendizado em regra Python + skill (Engenharia Reversa) + learning_log. `processar_aprendizado_autonomo(relatorio, numero_processo, user_id=None, *, extrair_logica_correcao_gemini, filtrar_logicas_verba_ausente_falsas)` — extrai hipóteses, atualiza **Knowledge Base (Multi-tenant via user_id)**, avalia shadow rules. `evaluate_shadow_rules(relatorio, kb=None, user_id=None)` — acerto/punição. Integração com `knowledge_base.py` via `tenant_id=user_id or "default"`. |
| `process_timeline_extractor.py` | **PJe Timeline Extractor**: `PjeTimelineExtractor._mapear_sumario(pdf_bytes)` (índice nas primeiras 15 pág.), `_buscar_por_ancoras()` (fallback regex), `extract_timeline_from_pdf(pdf_bytes)` → `{mapa, textos, log}`; `extrair_metadados_peca(chave, texto, ai_client)` (ETAPA 3 — Gemini por peça). Chaves: peticao_inicial, contestacao, sentenca, acordao, liquidacao, impugnacao, parecer. |
| `knowledge_base.py` | `KnowledgeBase` — banco de regras dinâmicas em arquivo JSON; usa **padrão Multiton por tenant**: `KnowledgeBase(tenant_id)` grava em `knowledge_base_{tenant_id}.json` (ou `knowledge_base.json` para o default); campos: rule_id, descricao, condicao, acao, base_legal, confidence_score, status (shadow/active/deleted), casos_vistos, acertos, punicoes; operações: `adicionar_ou_incrementar`, `marcar_acerto`, `marcar_punicao`, `stats`. |

---

## Por arquivo — learning_engine.py (detalhe completo)

Entrypoints públicos (persistência via facade em `services.lab.learning_io`):

| Função | Assinatura resumida |
|--------|---------------------|
| `processar_sete_arquivos` | 8 arquivos + `processo_arquivos: List[tuple]` → relatório completo com Style Transfer + guardrails |
| `processar_cinco_arquivos` | 5 arquivos (compat.); mesmo pipeline sem Fases de Conhecimento |
| `gerar_relatorio_discrepancia` | `(dados_sentenca, dados_liquidacao, dados_manifestacao) → dict` — **facade** → `lab/discrepancy.gerar_relatorio_discrepancia` (coração do Lab: Sentença vs. Cálculo) |
| `preview_aprendizado` | `(aprendizado) → dict` — **facade** → `lab/learning_io.preview_aprendizado` |
| `salvar_aprendizado` | Persiste em disco — **facade** → `lab/learning_io.salvar_aprendizado` |
| `codify_insight` | **Facade** → `lab/self_healing.codify_insight` (regra Python + skill + learning_log). |
| `processar_aprendizado_autonomo` | **Facade** → `lab/self_healing.processar_aprendizado_autonomo` (user_id para Multi-tenancy; callbacks: _extrair_logica_correcao_gemini, _filtrar_logicas_verba_ausente_falsas). |

Funções privadas notáveis:

| Função | Descrição |
|--------|-----------|
| `_verba_corresponde_na_liquidacao(verba, verbas_liq_norm, verbas_liq_canon, threshold?)` | **Facade** → `lab/discrepancy.verba_corresponde_na_liquidacao`. Match canonizado + substring + fuzzy; só considera verba ausente se não houver correspondente. |
| `_classificar_tier_decisao(filename, texto?)` | **Facade** → `lab/titulo_executivo.classificar_tier_decisao`. Só Título Executivo (Card 3). Prioridade nome; texto só se genérico; ignora 1000 chars. |
| `_extrair_data_documento(texto)` | **Facade** → `lab/titulo_executivo.extrair_data_documento`. Só Título Executivo (data do doc). Remove linha Data da Autuação; prioriza final do doc. |
| `_extrair_titulo_executivo_multiplos([(bytes,fn)])` | **Facade** → `lab/titulo_executivo.extrair_titulo_executivo_multiplos` com callbacks `_extrair_processo`, `_extrair_texto_arquivo`, `_bloco_amostragens_perita`. Tier diferente = ambos mantidos; desempate por data; prompt Análise de Reforma. |
| `_merge_dados_manifestacao(base, novo)` | **Facade** → `lab/style_transfer.merge_dados_manifestacao`. Junta resultados Card 6 + Card 8 (Duplo Style Transfer). |
| `_extrair_manifestacao_pericial(bytes, filename)` | **Facade** → `lab/style_transfer.extrair_manifestacao_pericial` com callbacks `_extrair_texto_arquivo`, `_chamar_gemini_para_codify` e `skills_dir=_SKILLS_DIR`. Gemini: frases, padrões Ataque/Defesa, argumento vencedor → KB + `manifestacao_style.md`. |
| `_canon_empresa_e_verba_esta(relatorio)` | **Facade** → `lab/discrepancy.canon_empresa_e_verba_esta`. Retorna (set verbas canonizadas empresa, verba_esta(verba)); usado pelos 3 guardrails. |
| Regex/limpeza (facade) | `_regex_verbas`, `_liquidacao_from_text`, `_extrair_fundamentos_juridicos`, `_extrair_discrepancias_perita`, `_remover_linha_autuacao`, `_contexto_eh_autuacao` → **`lab/extractors.py`** |
| `_filtrar_falsos_positivos_verba_ausente(relatorio)` | **Facade** → `lab/discrepancy.filtrar_falsos_positivos_verba_ausente`. Guardrail: remove discrepâncias verba_ausente quando verba existe na liquidação/PJC. |
| `_filtrar_logicas_verba_ausente_falsas(logicas, relatorio)` | **Facade** → `lab/discrepancy.filtrar_logicas_verba_ausente_falsas`. Guardrail hipóteses KB. |
| `_filtrar_aprendizados_verba_ausente_falsas(relatorio)` | **Facade** → `lab/discrepancy.filtrar_aprendizados_verba_ausente_falsas`. Guardrail aprendizados antes do return. |
| `_extrair_logica_correcao_gemini(relatorio)` | Prompt com REGRAS ESTRITAS 1–3 + early-exit Python |
| (evaluate_shadow_rules) | Em `lab/self_healing.py`; chamado por `processar_aprendizado_autonomo`. Acerto/punição → ciclo de vida shadow→active/deleted. |

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

## Por arquivo — Frontend (frontend/) — SPA React

| Arquivo | Responsabilidade |
|---------|-------------------|
| `index.html` | Entry: monta `#root` e carrega `src/main.tsx` (Vite). |
| `src/main.tsx` | Bootstrap React; React Query provider; roteamento. |
| `src/App.tsx` | Rotas: `/` (Dashboard), `/extractor` (Extrator), `/lab` (Laboratório). |
| `src/pages/Dashboard.tsx` | Página inicial / resumo. |
| `src/pages/Extractor.tsx` | Upload, processar, exibir resultado e Raio-X; export PJC/Excel. |
| `src/pages/Laboratory.tsx` | **Cérebro Analítico:** termômetro de eficiência (pesos por tipo de arquivo), 5 cards de upload (Sentença, Liquidação, PJC, Manifestação, Parecer), botão global "Analisar Processo Completo" com log animado no botão, painel HITL (aprendizados extraídos), relatório de discrepância, Gerar Minuta Word/PJC/Excel. |
| `src/hooks/useAnalyze.ts` | Mutation `POST /lab/analisar` (FormData); WebSocket opcional para pipeline; retorna `data`, `isLoading`, `isSuccess`. |
| `src/components/features/AnalysisReport.tsx` | Renderiza relatório de discrepância (processo, raw). |
| `src/components/features/LearningPreview.tsx` | Pré-visualização de aprendizados. |
| `src/components/layout/MainLayout.tsx` | Sidebar/navegação e layout global. |
| `src/services/api.ts` | Cliente Axios (baseURL); usado por páginas e hooks. |
| `src/types/api.ts` | Tipos TypeScript (ProcessoTrabalhista, etc.). |

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
| Laboratório / Aprendizado | `services/learning_engine.py` (facade orquestrador); **`lab/discrepancy.py`** (Sentença vs. Cálculo); **`lab/style_transfer.py`** (Duplo Style Transfer); **`lab/self_healing.py`** (codify_insight + Shadow Rules, Multi-tenant); `lab/titulo_executivo.py`, `lab/extractors.py`, `lab/learning_io.py`; `main.py` (lab); **frontend:** `frontend/src/pages/Laboratory.tsx` + `hooks/useAnalyze.ts`. **Ghostwriter:** `POST /lab/gerar-docx` → `document_generator.gerar_minuta` + `ai_writer.gerar_texto_manifestacao` → .docx (estilo `manifestacao_style.md`). |
| **Discrepância Sentença vs. Cálculo** | **`lab/discrepancy.py`** — `gerar_relatorio_discrepancia` (verbas deferidas vs. liquidação, índice, juros; aprendizados); `verba_corresponde_na_liquidacao` (canonização + fuzzy). `learning_engine.py` expõe facades. Depende de `LegalRule._canonizar_verba` (legal_engine/rule_base). |
| Guardrails anti-alucinação | **`lab/discrepancy.py`** — `filtrar_falsos_positivos_verba_ausente`, `filtrar_logicas_verba_ausente_falsas`, `filtrar_aprendizados_verba_ausente_falsas`; `learning_engine.py` expõe facades. Canonização via `canon_empresa_e_verba_esta`. |
| Título Executivo Complexo | `lab/titulo_executivo.py` → `classificar_tier_decisao`, `extrair_data_documento`, `extrair_titulo_executivo_multiplos`; `learning_engine.py` expõe facades; `main.py`. **Não confundir com extração:** na extração (processor + ai_client) o cabeçalho PJe é preservado e Data da Autuação vira data_ajuizamento. |
| PJe Timeline Extractor (um PDF no Card 3) | `services/process_timeline_extractor.py`; `learning_engine` chama quando len(processo_arquivos)==1 e PDF; relatório: `timeline_fatiamento`, `pecas_extraidas_do_pdf`; frontend barra de eficiência soma pesos das peças extraídas |
| Duplo Style Transfer | **`lab/style_transfer.py`** — `merge_dados_manifestacao`, `extrair_manifestacao_pericial` (callbacks: extrair_texto_arquivo, chamar_gemini_para_codify, skills_dir); `atualizar_skill_manifestacao`; `learning_engine.py` expõe facades. Alimenta `skills/manifestacao_style.md` (Card 6 Impugnação + Card 8 Manifestação). |
| Self-Healing Rule Engine | **`lab/self_healing.py`** — `codify_insight`, `processar_aprendizado_autonomo`, `evaluate_shadow_rules`; KB via `KnowledgeBase(tenant_id=user_id)`. `learning_engine.py` expõe facades; `services/knowledge_base.py`; `legal_engine/dynamic_rule_loader.py`. |
| Dashboard Estatísticas | `api/routers/admin.py` (`GET /api/stats`); `services/knowledge_base.py`; `database.get_total_extractions`; frontend React consome via `services/api.ts` (Dashboard ou página de estatísticas). |
| Biblioteca de Regras | `api/routers/admin.py` GET `/api/knowledge-base` (Multi-tenant via `user_id`). Frontend React: exibir contagem e lista de regras (modal/panel) via `api.ts`. |
| IA e prompt | `services/ai_client.py`; `skills/*.md` |
| PDF e texto | `services/sentence_finder.py`, `text_processor.py`, `pre_extractor.py` |

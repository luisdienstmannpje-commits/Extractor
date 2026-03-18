# AI Navigation Layer — PJeCalc Smart Extractor

Documento de **entrada obrigatória para agentes de IA** que atuam neste repositório.
Não repete toda a documentação — aponta **onde ler primeiro** e **o que não quebrar**.

> **Token-tip:** Leia este arquivo inteiro (< 200 linhas). Só depois abra arquivos de código.

### Regras do sistema (resumo — economizar tokens)
- **Extração (sentença/acórdão):** **Camada híbrida (Regex + IA):** em `workers/processor.py`, regex em cabeçalho (3000 chars) e final (2500 chars) extrai `data_ajuizamento`, `valor_causa` e **data_sentenca** (Assinado eletronicamente em / Data do Julgamento / Publicado em); merge pós-Gemini quando IA retorna null ou "não informado". Prompt em `ai_client.py`: data_sentenca crucial; em Acórdão buscar Data do Julgamento/publicação. `models.py`: campos de data aceitam "não informado" → None. **Upload:** frontend envia FormData com campo exatamente `"files"` (plural); backend `files: List[UploadFile] = File(..., alias="files")`; log `[UPLOAD] Arquivos recebidos: [...]` em `main.py`.
- **Título Executivo (Card 3):** **Prioridade ao nome do arquivo.** Nome com 1grau/ATOrd/Sentenca → **1GRAU**. Nome com 2grau/ROT/Acordao → **TRT**. Só usa regex no texto se nome genérico; ao usar texto para classificação, ignora os primeiros 1000 chars (evita "Tribunal Regional" do header) e só considera "Recurso Ordinário", "Relator:", "Acórdão". **Data do documento (hierarquia):** a linha "Data da Autuação" é removida antes de extrair datas (prioriza data do julgamento/assinatura). Essa remoção vale **apenas** para Título Executivo; na extração principal a "Data da Autuação" é **mantida** e mapeada para `data_ajuizamento`.
- **Pipeline:** 10 passos em `workers/processor.py`; não alterar ordem/contratos. **Dossiê (multi-upload):** `POST /upload` aceita `files: List[UploadFile]` — PDF, Word, Excel (.xlsx/.xls), PJC, XML, imagens (JPG/PNG). Um PDF → `process_lawsuit_pdf`; múltiplos ou não-PDF → `process_lawsuit_dossie`. Leitura: Excel → openpyxl (texto); imagens → Gemini multimodal (OCR/descrição em `ai_client.extrair_texto_ou_descricao_imagem`). Prompt instrui a cruzar textos, tabelas e imagens para o Raio-X. Cache por hash composto (inclui binário). UI: identificação só no Raio-X.
- **Regras jurídicas:** só em `legal_engine/`; uma regra por arquivo; `LegalRule._canonizar_verba` para canonização.
- **Guardrails:** `_filtrar_*` em `learning_engine.py` após enriquecimento; não remover nem mover.
- **Frontend:** SPA React (Vite + TypeScript + Tailwind); componentes em frontend/src/; rotas em App.tsx.
- **Arquitetura SaaS e Multi-tenancy:** `main.py` atua apenas como **API Gateway** (inicialização FastAPI + middleware + inclusão de roteadores em `api/routers/`). As rotas vivem em roteadores especializados (`extractor.py`, `lab.py`, `admin.py`, `exports.py`). O KnowledgeBase é **Multi-tenant** (Multiton por `tenant_id`/`user_id`), gravando regras por cliente em arquivos `knowledge_base_{tenant_id}.json` para evitar vazamento de aprendizado entre escritórios.

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

### 2.4 Extração de texto / IA (single PDF ou dossiê)
1. `docs/PIPELINE.md` passos 3–5.
2. **Single PDF:** `sentence_finder.py`, `ai_client.py`, `skills/sentenca_ordinaria.md`. **Dossiê:** `workers/processor.py` → `process_lawsuit_dossie`, `_extrair_texto_arquivo_dossie` (PDF, Word, Excel openpyxl, PJC/XML, imagens via `ai_client.extrair_texto_ou_descricao_imagem`); `_hash_dossie`; `main.py` → `POST /upload` com `files`; super-contexto com separadores. Prompt em `ai_client.py`: cruzar múltiplos documentos/tabelas/imagens para Raio-X.

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
1. `docs/CODE_MAP.md` (§ Por arquivo — Frontend).
2. **SPA React (Vite + TypeScript + Tailwind):** `frontend/index.html` (entry, `#root` + `src/main.tsx`), `frontend/src/App.tsx` (rotas: `/`, `/extractor`, `/lab`), `frontend/src/pages/Dashboard.tsx`, `Extractor.tsx`, `Laboratory.tsx`; `frontend/src/components/layout/MainLayout.tsx`; `frontend/src/hooks/useAnalyze.ts`; `frontend/src/services/api.ts`.
3. **Painel Raio-X (aba Processar):** Exibido no Extractor; dados de `envelope.raiox`. Ordem: número do processo, Dicas Lab, Identificação e Juízo, Parâmetros Estruturais, Índices, Verbas/Adicionais.

### 2.9 Laboratório de Aprendizado da Perita
**Backend:** `services/learning_engine.py` (§ 5) + `services/learning_skill_loader.py`. Persistência e I/O em `services/lab/learning_io.py`; regex e limpeza em `services/lab/extractors.py` (learning_engine expõe facade).
**Endpoints:** `/lab/analisar` (8 campos + `amostragens`), `/lab/preview`, `/lab/salvar`, `/lab/gerar-docx` (Ghostwriter: body = relatório JSON → retorna .docx da Manifestação), `/lab/historico`, `/lab/knowledge-base`.
**Frontend:** `frontend/src/pages/Laboratory.tsx` — Cérebro Analítico (termômetro de eficiência, 5 cards de upload, botão global "Analisar Processo Completo" com log animado, painel HITL de aprendizados, relatório de discrepância, Gerar Minuta Word/PJC/Excel). `frontend/src/hooks/useAnalyze.ts` — POST /lab/analisar. **Detalhes Lab:** `docs/guia_eficiencia.md`.
**Ghostwriter:** O endpoint envia `manifestacao_style.md` como **Instrução de Tom e Voz** (IA imita estilo: "esperando haver se desincumbido do múnus", "vem, respeitosamente"). `document_generator.gerar_minuta`: cabeçalho (Processo, Reclamante, Reclamada), MANIFESTAÇÃO AOS CÁLCULOS, seções, tabela **Table Grid** (prejuízo financeiro), encerramento "Pede Deferimento. [Cidade], [Data]." + espaço assinatura Perito Assistente. `ai_writer.gerar_texto_manifestacao` → Gemini Perito Sênior; retorna `introducao`, `secoes[]`, `tabela_comparativa[]` (texto limpo). Validar com Teste 5 (Victor Felipe) ou Teste 10 (Gustavo Henrique).
**Card de Provas como hub:** O usuário pode anexar **tudo** (Parecer, Amostragens, Manifestações) no Card "Amostragens e Provas". O backend usa `_fusionar_provas_com_cards`: para cada arquivo extrai texto e `_classificar_tipo_documento_prova(texto, filename)` → `parecer` | `amostragem` | `manifestacao` | `generic` (por termos como "Parecer Técnico", "Conclui-se", "R$", meses, tabelas); preenche `parecer_bytes`, `amostragem_pdf/word_bytes`, `manifestacao_bytes` quando os cards 5/6/8 não foram enviados. Todo o texto continua em `<AMOSTRAGENS_DA_PERITA>` com o **prompt unificado**: "Identifique qual arquivo é o Parecer e qual é a Amostragem; use o Parecer para a estratégia de combate e a Amostragem para conferir valores centavo a centavo no .PJC."

### 2.10 Self-Healing Rule Engine
1. README § Self-Healing.
2. **`services/lab/self_healing.py`** — `codify_insight`, `processar_aprendizado_autonomo`, `evaluate_shadow_rules`; integração com `knowledge_base.py` via `user_id` (Multi-tenancy). `learning_engine.py` expõe facades e mantém `_extrair_logica_correcao_gemini` (callback injetado no self_healing).
3. `services/knowledge_base.py` → estrutura `knowledge_base.json` e ciclo de vida.
4. `services/legal_engine/dynamic_rule_loader.py` → `DynamicLegalRule`, `carregar_regras_ativas`, `executar_shadow_pipeline`.
5. `workers/processor.py` → passo 8 (regras ativas + shadow mode).
6. Nunca editar diretamente `services/legal_engine/rules/` a partir deste domínio.

### 2.11 Dashboard de Estatísticas
1. **Backend:** `api/routers/admin.py` → `GET /api/stats` (KnowledgeBase.stats() + get_total_extractions()).
2. **Frontend:** React consome `/api/stats` via `services/api.ts` (Dashboard ou página de estatísticas); exibir KPIs e atualizar conforme necessário.

### 2.12 Biblioteca de Regras (Inteligência Pericial)
1. **Backend:** `api/routers/admin.py` → `GET /api/knowledge-base`. Lê `knowledge_base_{tenant_id}.json` via `KnowledgeBase(tenant_id=user_id)`. Em erro retorna `{"rules": [], "_meta": {...}}` (nunca 404).
2. **Frontend:** React consome `/api/knowledge-base` via `api.ts`; exibir contagem de regras (status !== 'deleted') e lista em modal ou painel; mensagem quando `rules.length === 0`.

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
| Laboratório | README § Laboratório, `docs/guia_eficiencia.md` (níveis, pesos, marcha) | `learning_engine.py`, `main.py`, `frontend/src/pages/Laboratory.tsx`, `frontend/src/hooks/useAnalyze.ts` |
| Diretrizes prompt Lab | `docs/guia_eficiencia.md` | Não duplicar em outros docs (economia tokens) |
| Frontend layout/UI | `docs/CODE_MAP.md` (§ Frontend) | `frontend/src/App.tsx`, `frontend/src/components/layout/MainLayout.tsx`, `frontend/src/pages/*.tsx` |
| Parecer Técnico | `docs/CODE_INTELLIGENCE_MAP.md` § 4.3 | `skills/parecer_pericial.md`, `explanation_engine.py` |
| Dashboard Estatísticas | este arquivo § 2.11 | `api/routers/admin.py` (/api/stats), frontend React `api.ts` |
| Biblioteca de Regras (auditar aprendizado) | este arquivo § 2.12 | `api/routers/admin.py` (/api/knowledge-base), frontend React `api.ts` |

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
- **PJe Timeline Extractor**: com **um único PDF** no Card 3, `process_timeline_extractor.extract_timeline_from_pdf` fatia o processo (sumário ou âncoras) e preenche slots lógicos (petição, contestação, liquidação, impugnação, parecer) se o usuário não anexou; relatório ganha `timeline_fatiamento` e `pecas_extraidas_do_pdf` (Barra de Eficiência).
- Guardrails (`_filtrar_falsos_positivos_verba_ausente`, etc.) devem rodar **após** enriquecimento e **antes** do retorno ao frontend.
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
| `_classificar_tier_decisao(filename, texto?)` | **Apenas Título Executivo.** Prioridade ao nome: 1grau/ATOrd→1GRAU, 2grau/ROT→TRT. Texto só se nome genérico; ignora primeiros 1000 chars; no texto só "Recurso Ordinário", "Relator:", "Acórdão". Não afeta a extração (sentença/acórdão). |
| `_extrair_data_documento(texto)` | **Apenas Título Executivo (data do doc).** Remove a linha "Data da Autuação" antes de regex; prioriza final do doc. Na extração principal, "Data da Autuação" é mantida e mapeada para `data_ajuizamento`. |
| `_classificar_tipo_documento_prova(texto, filename)` | Classifica documento do Card Provas: `parecer` (Parecer Técnico, Conclui-se), `amostragem` (R$, meses, tabelas), `manifestacao` (manifestação, petição resposta), `generic`. |
| `_fusionar_provas_com_cards(amostragens_arquivos, parecer*, amostragem_* , manifestacao*)` | Extrai texto de cada arquivo do Card Provas, classifica e preenche parecer/amostragem PDF ou Word/manifestação quando o card explícito não foi enviado; retorna (texto_dossie, parecer_bytes/fn, amostragem_pdf/word, manifestacao). |
| `_processar_dossie_amostragens(lista (bytes, fn))` | Concatena texto de cada arquivo com `\n--- PROVA: nome ---\n`; usado para tag `<AMOSTRAGENS_DA_PERITA>`. |
| `_bloco_amostragens_perita(texto_dossie)` | Envolve o dossiê em `<AMOSTRAGENS_DA_PERITA>` com **prompt unificado** (identificar Parecer vs Amostragem; usar Parecer para estratégia e Amostragem para conferir .PJC centavo a centavo). |
| `_extrair_titulo_executivo_multiplos([(bytes, fn)], contexto_amostragens?)` | N docs; tier diferente = ambos mantidos; opcionalmente prepende bloco AMOSTRAGENS_DA_PERITA. |
| `_extrair_liquidacao(bytes, filename)` | PJC/PDF/DOCX → verbas, índice, juros |
| `_extrair_manifestacao(bytes)` | DOCX → fundamentos + discrepâncias |
| `_extrair_impugnacao(bytes, filename)` | PDF/DOCX → fundamentos + argumentos |
| `_extrair_calculo_pjc(bytes, filename)` | Delega para `_extrair_liquidacao` |
| `_extrair_amostragem_pdf(bytes, filename)` | PDF holerites → teses + irregularidades (Gemini) |
| `_extrair_amostragem_word(bytes, filename)` | DOCX → estilo da perita → `skills/amostragem_style.md` |
| `_extrair_manifestacao_pericial(bytes, filename)` | **Duplo Style Transfer** — analisa frases de impacto, súmulas, padrões Ataque/Defesa, argumento vencedor; chamado para Card 6 (impugnação) E Card 8 (manifestação) |
| `_merge_dados_manifestacao(base, novo)` | Junta resultados de impugnação + manifestação sem duplicar; alimenta `skills/manifestacao_style.md` com ambos |
| `_liquidacao_from_text(texto)` | Constrói dict de liquidação a partir de texto (Timeline). |
| `_extrair_manifestacao_from_text(texto)` | Manifestação/parecer a partir de texto (Timeline). |
| `_extrair_impugnacao_from_text(texto)` | Impugnação a partir de texto (Timeline). |

**PJe Timeline Extractor** (`services/process_timeline_extractor.py`): `PjeTimelineExtractor._mapear_sumario(pdf_bytes)` (sumário PJe), `_buscar_por_ancoras()` (fallback regex), `extract_timeline_from_pdf(pdf_bytes)` → `{mapa, textos, log}`; `extrair_metadados_peca(chave, texto, ai_client)` para ETAPA 3 (Gemini por peça).

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
| `processar_aprendizado_autonomo(relatorio, numero, user_id?)` | **Facade** → `lab/self_healing`; Fase 1: hipóteses → KB(tenant_id=user_id); Fase 2: evaluate_shadow_rules |
| `evaluate_shadow_rules(relatorio, kb, user_id?)` | Em `lab/self_healing.py`; acerto (+1) / punição (-1); shadow→active/deleted |
| `_extrair_logica_correcao_gemini(relatorio)` | Gemini → hipóteses JSON; callback injetado no self_healing; 3 REGRAS ESTRITAS + early-exit |

### Entrypoints públicos
| Função | Descrição |
|--------|-----------|
| `processar_sete_arquivos(...)` | 8 arquivos + `processo_arquivos: List[tuple]` (Card 3 múltiplos); chama `processar_cinco_arquivos` |
| `processar_cinco_arquivos(...)` | Fluxo principal; inclui guardrails e filtro de aprendizados antes do return |
| `gerar_relatorio_discrepancia(dados_sentenca, dados_liquidacao, dados_manifestacao)` | Cross-reference principal; usa `LegalRule._canonizar_verba` + `_verba_corresponde_na_liquidacao` |
| `preview_aprendizado(aprendizado)` | Retorna conteúdo que seria gravado (sem gravar) |
| `salvar_aprendizado(...)` | Persiste regra/playbook em disco |
| `codify_insight(...)` | **Facade** → `lab/self_healing.codify_insight`; regra Python + skill + learning_log |

---

## 6. Como navegar com eficiência (economizar tokens)

1. **Localizar módulo**: use `docs/CODE_MAP.md` → vai direto ao arquivo certo.
2. **Entender papel no domínio**: use `docs/CODE_INTELLIGENCE_MAP.md` → subseção do domínio.
3. **Resposta conceitual** (ex.: "onde ficam as regras de FGTS?"): leia `CODE_MAP.md` → tabela "Por domínio".
4. **Nunca abra o README inteiro** se a tarefa for localizada — use os docs menores.
5. **Caminho ideal**: `AI_NAVIGATION_LAYER` → doc específico → 1–3 arquivos de código.
6. **Guardrails, Duplo Style Transfer, Título Executivo**: ver § 5 acima — não releia o código fonte inteiro.

Se estiver perdido: volte a este arquivo → escolha o tipo de tarefa em § 2 → siga o roteiro.

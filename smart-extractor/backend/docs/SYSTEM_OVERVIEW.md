# Visão do sistema — PJeCalc Smart Extractor

Documento de referência rápida para agentes de IA.
Para pipeline detalhado: `PIPELINE.md`. Para mapa de arquivos: `CODE_MAP.md`. Para evolução incremental dos extratores regex: `AI_AGENT_EXTRACTION_CYCLE.md`.

---

## O que o sistema faz

- **Entrada**: PDF de sentença, acórdão trabalhista ou múltiplos decisórios hierárquicos.
- **Saída**: JSON estruturado (45+ campos), Excel, memória de cálculo (JSON/job), arquivo `.pjc` compatível com PJeCalc 2.14.0.
- **Objetivo**: Reduzir leitura manual de sentenças de horas para segundos; treinar regras preditivas de forma autônoma.

---

## Componentes principais

| Componente | Onde | Função |
|------------|------|--------|
| API | `main.py` + `api/routers/` | `main.py` atua como **API Gateway**: inicializa o FastAPI, aplica middleware (CORS, logs) e inclui os roteadores. As rotas vivem em `api/routers/extractor.py` (upload/jobs/WebSocket/export Excel), `api/routers/lab.py` (Laboratório), `api/routers/admin.py` (stats, histórico, biblioteca de regras) e `api/routers/exports.py` (exportação dedicada). |
| Pipeline | `workers/processor.py` | Orquestra os 10 passos (créditos → cache → texto → IA → validação → persistência → memória). Regex de cabeçalho/fim do PDF continua no processor para merge pós-IA (ex.: data de autuação, valor da causa). |
| Extração de texto | `services/sentence_finder.py` | PDF → texto, tipo de doc, OCR híbrido. |
| Pré-extração (regex) | `services/pre_extractor.py` | Campos **HIGH/MEDIUM** por padrões estáveis (ex.: CNJ, reclamante/reclamada, vara, datas, salário, nomes de verbas no dispositivo/decisão). `pre_extract` alimenta o processor; MEDIUM vira âncora no prompt via `build_anchor_section` e HIGH sobrescreve campos whitelisted pós-IA com log `[PRE-HIGH]`. Ciclos e critérios em `AI_AGENT_EXTRACTION_CYCLE.md`. |
| Diagnóstico (opcional) | `services/pipeline_debug.py`, `DEBUG_PIPELINE` em `config` | Logs do texto entre o finder e a truncagem enviada ao modelo. Ver `PIPELINE.md`. |
| IA | `services/ai_client.py` | Gemini (Flash → Pro fallback), playbook, truncagem; aceita `pre_fields` do pré-extrator para âncoras quando informados. |
| Validação jurídica | `services/legal_validator.py` → `legal_engine/` | Delega ao Legal Rule Engine; regras em `legal_engine/rules/` e `services/jurisprudencia/`. |
| Explicações / Parecer | `services/explanation_engine.py` + `services/ai_client.py` | Templates jurídicos (sem LLM) + seção I do Parecer Padrão Ouro via Gemini. |
| Memória de cálculo | `memoria_calculo/generator.py` | Gera `memoria_{job_id}.json` (trilha de auditoria). |
| Persistência | `services/database.py` | SQLite: créditos, cache, extrações, jobs. |
| Laboratório de Aprendizado | `services/learning_engine.py`, `services/lab/discrepancy.py`, `services/lab/style_transfer.py`, `services/lab/self_healing.py` (codify + Shadow Rules, Multi-tenant), `main.py (/lab/*)` | Ver abaixo. |
| Frontend | `frontend/` | SPA React (Vite + TypeScript + Tailwind). Ver abaixo. |

---

## Laboratório de Aprendizado — visão geral

8 arquivos (marcha processual). **Barra de eficiência** no frontend: score 0–100%, níveis 1–4. Ver `guia_eficiencia.md` (níveis, pesos, ordem ideal).

| # | Campo | Função |
|---|-------|--------|
| 1 | `peticao` | Petição Inicial → verbas pedidas, causa de pedir |
| 2 | `contestacao` | Contestação → argumentos exclusão, teses empresa |
| 3 | `processo` | Título Executivo (múltiplos; tier + data do texto). Hierarquia e fusão em `lab/titulo_executivo.py`; tier diferente = ambos mantidos; cabeçalho PJe 1000 chars ignorado. |
| 4–8 | liquidacao, parecer, impugnacao, calculo_pjc, manifestacao | Cálculo empresa, parecer, Style Transfer (6+8), PJC, retórica combate |

**Duplo Style Transfer**: Card 6 (Impugnação) + Card 8 (Manifestação) → `skills/manifestacao_style.md`. Lógica em `lab/style_transfer.py` (`merge_dados_manifestacao`, `extrair_manifestacao_pericial`).

**Confronto Sentença vs. Cálculo:** `lab/discrepancy.py` — `gerar_relatorio_discrepancia` (verbas deferidas vs. liquidação, índice, juros; canonização via `LegalRule._canonizar_verba`).

**Guardrails anti-alucinação** (3 camadas; implementados em `lab/discrepancy.py`):
1. Discrepâncias (`filtrar_falsos_positivos_verba_ausente`) — remove `verba_ausente` se a verba está na liquidação/PJC.
2. Hipóteses KB (`filtrar_logicas_verba_ausente_falsas`) — remove hipóteses Gemini falsas antes do Knowledge Base.
3. Aprendizados frontend (`filtrar_aprendizados_verba_ausente_falsas`) — limpa o JSON retornado ao UI.

---

## Fluxo de dados (resumido)

```
PDF(s) → hash → cache? → sentence_finder (texto + doc_type) → playbook → Gemini → dados brutos
→ _validate_result → dedup verbas → ProcessoTrabalhista (Pydantic)
→ LegalRuleEngine (alertas + regras_aplicadas + memorial)
→ explanation_engine (explicacoes + parecer)
→ persistência (cache + extração + crédito)
→ memoria_calculo/generator.py
```

> **Pré-extração** — O `pre_extractor` concentra extratores testados em ciclos (ver `AI_AGENT_EXTRACTION_CYCLE.md`) e alimenta `extract_data_with_gemini(..., pre_fields=...)` com dicionários `high` / `medium`; `medium` orienta a IA e `high` é aplicado depois de `_validate_result` no processor.

> **Contratos HTTP do Extrator** — `POST /upload` cria job assíncrono (`queued` + `job_id`), `GET /status/{job_id}` é o fallback de polling e `WebSocket /ws/{job_id}` envia `partial_update` e uma mensagem terminal (`done`, `error` ou `timeout`). Exportação dedicada: `POST /api/export/excel`, `POST /api/export/pjc` e `GET /export-excel/{job_id}`.

> **Multi-Tenancy (isolamento por cliente)**  
> O Cérebro da IA (KnowledgeBase) isola dados de aprendizado por cliente usando padrão **Multiton**: cada tenant é mapeado para um arquivo físico (`knowledge_base_{tenant_id}.json`, ou `knowledge_base.json` para o default). As rotas administrativas (`/api/knowledge-base`, `/api/stats`) recebem `user_id` e instanciam `KnowledgeBase(tenant_id=user_id)`, evitando que regras de um escritório vazem para outro.

---

## Hierarquia normativa (Legal Rule Engine)

| Prioridade | Nível |
|------------|-------|
| 10 | STF (ADC 58) |
| 20 | TST Súmulas |
| 30 | TST OJs |
| 40 | CLT / legislação federal |
| 50 | Consistência |

---

## Frontend — SPA React (Vite + TypeScript + Tailwind)

| Rota | Página | Conteúdo |
|------|--------|----------|
| `/` | Dashboard | Página inicial / resumo. |
| `/extractor` | Extractor | Upload PDF/dossiê, processar, exibir resultado e Raio-X; export PJC/Excel. |
| `/lab` | Laboratory | **Cérebro Analítico:** termômetro de eficiência, 5 cards de upload (Sentença, Liquidação, PJC, Manifestação, Parecer), botão global "Analisar Processo Completo" (log animado no botão), painel de aprendizados HITL, relatório de discrepância, Gerar Minuta Word/PJC/Excel. |

Arquivos principais: `frontend/src/App.tsx` (rotas), `frontend/src/pages/Laboratory.tsx`, `frontend/src/hooks/useAnalyze.ts`, `frontend/src/services/api.ts`.

---

## Versão e estado

- Versão referência: v5.3+ (com Laboratório expandido, guardrails, Título Executivo Complexo).
- Pipeline estável; não alterar sem análise. Regras críticas em `docs/AI_RULES.md`.
- Modelos Gemini ativos: `gemini-2.5-flash` (principal), fallback `gemini-2.5-pro`.

# Visão do sistema — PJeCalc Smart Extractor

Documento de referência rápida para agentes de IA.
Para pipeline detalhado: `PIPELINE.md`. Para mapa de arquivos: `CODE_MAP.md`.

---

## O que o sistema faz

- **Entrada**: PDF de sentença, acórdão trabalhista ou múltiplos decisórios hierárquicos.
- **Saída**: JSON estruturado (45+ campos), Excel, memória de cálculo (JSON/job), arquivo `.pjc` compatível com PJeCalc 2.14.0.
- **Objetivo**: Reduzir leitura manual de sentenças de horas para segundos; treinar regras preditivas de forma autônoma.

---

## Componentes principais

| Componente | Onde | Função |
|------------|------|--------|
| API | `main.py` | FastAPI: upload, jobs, WebSocket, download Excel/PJC, endpoints `/lab/*`, `GET /api/stats`. |
| Pipeline | `workers/processor.py` | Orquestra os 10 passos (créditos → cache → texto → IA → validação → persistência → memória). |
| Extração de texto | `services/sentence_finder.py` | PDF → texto, tipo de doc, OCR híbrido. |
| IA | `services/ai_client.py` | Gemini (Flash → Pro fallback), playbook, truncagem. |
| Validação jurídica | `services/legal_validator.py` → `legal_engine/` | Delega ao Legal Rule Engine; regras em `legal_engine/rules/` e `services/jurisprudencia/`. |
| Explicações / Parecer | `services/explanation_engine.py` + `services/ai_client.py` | Templates jurídicos (sem LLM) + seção I do Parecer Padrão Ouro via Gemini. |
| Memória de cálculo | `memoria_calculo/generator.py` | Gera `memoria_{job_id}.json` (trilha de auditoria). |
| Persistência | `services/database.py` | SQLite: créditos, cache, extrações, jobs. |
| Laboratório de Aprendizado | `services/learning_engine.py`, `main.py (/lab/*)` | Ver abaixo. |
| Frontend | `frontend/` | Workspace App Tailwind + Vanilla JS. Ver abaixo. |

---

## Laboratório de Aprendizado — visão geral

8 arquivos (marcha processual). **Barra de eficiência** no frontend: score 0–100%, níveis 1–4. Ver `guia_eficiencia.md` (níveis, pesos, ordem ideal).

| # | Campo | Função |
|---|-------|--------|
| 1 | `peticao` | Petição Inicial → verbas pedidas, causa de pedir |
| 2 | `contestacao` | Contestação → argumentos exclusão, teses empresa |
| 3 | `processo` | Título Executivo (múltiplos; tier + data do texto) |
| 4–8 | liquidacao, parecer, impugnacao, calculo_pjc, manifestacao | Cálculo empresa, parecer, Style Transfer (6+8), PJC, retórica combate |

**Duplo Style Transfer**: Card 6 + Card 8 → `manifestacao_style.md` (`_merge_dados_manifestacao`).

**Guardrails anti-alucinação** (3 camadas):
1. Discrepâncias (`_filtrar_falsos_positivos_verba_ausente`) — remove `verba_ausente` se a verba está na liquidação.
2. Hipóteses KB (`_filtrar_logicas_verba_ausente_falsas`) — remove hipóteses Gemini falsas antes do Knowledge Base.
3. Aprendizados frontend (`_filtrar_aprendizados_verba_ausente_falsas`) — limpa o JSON retornado ao UI.

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

## Frontend — 4 views

| View | ID | Conteúdo |
|------|-----|----------|
| Extrator | `#view-extrator` | Upload PDF, split-view, KPIs, resultado JSON renderizado, export PJC/Excel. |
| Laboratório | `#view-lab` | 8 cards de upload; Card 3 aceita múltiplos arquivos; resultado em 4 passos; modal de pré-visualização. |
| Meus Processos | `#view-historico` | Histórico de extrações; busca em tempo real; download PJC/Excel por job. |
| Estatísticas | `#view-estatisticas` | KPIs do aprendizado; polling 5 s; animação `.kpi-updated`. |

---

## Versão e estado

- Versão referência: v5.3+ (com Laboratório expandido, guardrails, Título Executivo Complexo).
- Pipeline estável; não alterar sem análise. Regras críticas em `docs/AI_RULES.md`.
- Modelos Gemini ativos: `gemini-2.5-flash` (principal), fallback `gemini-2.5-pro`.

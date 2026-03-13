# Visão do sistema — PJeCalc Smart Extractor

Documento de referência rápida para agentes de IA. Para detalhes do pipeline e do código, use `PIPELINE.md` e `CODE_MAP.md`.

## O que o sistema faz

- **Entrada**: PDF de sentença ou acórdão trabalhista.
- **Saída**: JSON estruturado (45+ campos), Excel, memória de cálculo (JSON por job), arquivo .pjc compatível com PJeCalc 2.14.0.
- **Objetivo**: Reduzir leitura manual de sentenças de horas para segundos.

## Componentes principais

| Componente | Onde | Função |
|------------|------|--------|
| API | `main.py` | FastAPI: upload, jobs, WebSocket, download Excel/PJC. |
| Pipeline | `workers/processor.py` | Orquestra os 10 passos (créditos → cache → texto → IA → validação → persistência → memória). |
| Extração de texto | `services/sentence_finder.py` | PDF → texto, tipo de doc, OCR se necessário. |
| IA | `services/ai_client.py` | Gemini (Flash → Pro), playbook, truncagem. |
| Validação jurídica | `services/legal_validator.py` → `legal_engine/` | Delega ao Legal Rule Engine; regras em `legal_engine/rules/` e `services/jurisprudencia/`. |
| Explicações | `services/explanation_engine.py` | Templates jurídicos por regra (sem LLM). `gerar_parecer_tecnico_completo` usa IA (via `ai_client.gerar_parcelas_parecer` + `skills/parecer_pericial.md`) para gerar seção I do parecer no Padrão Ouro; seção II é Python fixo (IPCA-E/INSS/IRRF). |
| Memória de cálculo | `memoria_calculo/generator.py` | Gera `memoria_{job_id}.json`. |
| Persistência | `services/database.py` | SQLite: créditos, cache, extrações, jobs. |
| Laboratório de Aprendizado | `services/learning_engine.py`, `main.py` (/lab/*) | **8 arquivos** — Tríade de Ouro Expandida (amostragem PDF/Word + sentença + liquidação + parecer + impugnação + PJC + **manifestação**) → relatório → regras preditivas via cross-reference → style transfer (skills/amostragem_style.md + skills/manifestacao_style.md) → padrões Ataque/Defesa → Shadow Rules no KB → **Self-Healing Rule Engine** (hipóteses JSON + Knowledge Base) → pré-visualização → salvar via codify_insight. |
| Frontend | `frontend/index.html`, `frontend/css/main.css`, `frontend/js/*.js` | Workspace App (Tailwind h-screen): sidebar fixa (4 views: Extrator, Laboratório, Meus Processos, Estatísticas), toolbar compacta, split-view extrator 50/50 (upload-state/viewer-state + KPIs), Laboratório (**8 uploads** — Tríade de Ouro Expandida; Conclusão grid 2×2), Meus Processos, Dashboard Estatísticas (GET /api/stats, polling 5 s quando visível, animação .kpi-updated); app.js, render.js (acordeões), lab.js (toast pós-salvar → Estatísticas). |

## Fluxo de dados (resumido)

1. PDF → hash → cache? → texto (sentence_finder) → playbook → IA → dados brutos.
2. Dados brutos → limpeza e derivações (processor) → dedup verbas → Pydantic (ProcessoTrabalhista).
3. Dados validados → Legal Rule Engine → alertas + regras_aplicadas + memorial_juridico.
4. Explanation Engine → explicacoes.
5. Persistência (cache, extração, crédito) + memória de cálculo (JSON).

## Hierarquia normativa (regras)

10 = STF → 20 = TST Súmulas → 30 = TST OJs → 40 = CLT → 50 = Consistência.

## Versão e estado

- Versão referência: v5.3.
- Pipeline estável; não alterar sem análise. Regras críticas e restrições em `AI_RULES.md`.

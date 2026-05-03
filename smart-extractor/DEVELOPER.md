# Developer — Estrutura oficial e rastreabilidade

> **Repositório único oficial a partir de 2026-03-17: `smart-extractor/`**
> A pasta `Extractor-legacy/` é arquivo histórico — não usar para desenvolvimento.

Documento mestre para desenvolvedores e agentes de IA: caminhos oficiais, unico cerebro do Lab e mapa de consolidacao frontend.

---

## 1. Caminhos oficiais do repositorio

| Camada | Caminho oficial | Descricao |
|--------|-----------------|-----------|
| **Backend** | `./backend` | API FastAPI, pipeline de extracao, motor juridico, Laboratorio de Aprendizado. Toda a logica de servico e regras. |
| **Frontend** | `./frontend` | UI oficial: SPA React (Vite + TypeScript + Tailwind). Entry: `index.html` + `src/main.tsx`; rotas em `App.tsx` (/, /extractor, /lab); páginas em `src/pages/`, hooks em `src/hooks/`, API em `src/services/api.ts`. Build: `npm run build`; servir `dist/` ou via backend. |

Todos os caminhos sao relativos à raiz do repositorio onde este arquivo (DEVELOPER.md) esta. Ao abrir o projeto pelo Cursor/IDE, use esses caminhos para imports, scripts e documentacao.

---

## 2. Backend: unico cerebro (Learning Engine)

O arquivo **`backend/services/learning_engine.py`** e o **unico cerebro** que coordena o Laboratorio de Aprendizado. Nenhum outro modulo deve orquestrar os submodulos de `lab/`.

- **Papel:** Facade orquestrador. Expõe a API publica (funcoes chamadas por `main.py` e por `api/routers/lab.py`) e delega toda a implementacao para os modulos em `backend/services/lab/`.
- **Modulos coordenados (lab/):**
  - `learning_io` — persistencia, preview e salvar aprendizado, learning log.
  - `extractors` — regex, limpeza de texto, extração de tabelas e fundamentos.
  - `titulo_executivo` — tiers (1º Grau/TRT/TST), data do documento, titulo executivo multiplos.
  - `discrepancy` — confronto Sentenca vs. Calculo, relatorio de discrepancia, guardrails.
  - `style_transfer` — manifestacao pericial, merge de dados, manifestacao_style.md.
  - `self_healing` — codify_insight, processar_aprendizado_autonomo, evaluate_shadow_rules; Knowledge Base multi-tenant.

**Rastreabilidade:** Qualquer chamada ao Laboratorio (analisar, preview, salvar, gerar-docx, knowledge-base) deve passar pelo `learning_engine.py`. Os routers importam apenas do `learning_engine`; o `learning_engine` importa de `services.lab.*`. Nao criar novos entrypoints que importem diretamente de `services.lab` fora do learning_engine.

---

## 3. Consolidacao frontend (UI oficial)

### 3.1 Estrutura atual

A **UI oficial** e o frontend em `./frontend` com stack **React + TypeScript + Vite + Tailwind**:

| Local | Conteudo |
|-------|----------|
| **frontend/** | `index.html` (entry, `#root`), `src/main.tsx`, `src/App.tsx` (rotas: `/`, `/extractor`, `/lab`), `src/pages/Dashboard.tsx`, `Extractor.tsx`, `Laboratory.tsx`, `src/components/`, `src/hooks/useAnalyze.ts`, `src/services/api.ts`, `src/types/`. Build: `npm run build` → `dist/`. |

Servir estatico a partir de `frontend/dist/` ou via mesmo host do backend. Nao ha "frontend-new" como pasta separada; a SPA React e a unica UI de producao.

### 3.2 Rastreabilidade

- Toda referencia em docs e scripts ao frontend deve apontar para `./frontend` e, no codigo, para `frontend/src/` (App.tsx, pages/, hooks/, services/, etc.). Ver `backend/docs/CODE_MAP.md` e `backend/docs/AI_NAVIGATION_LAYER.md` § Frontend e Laboratorio.

---

## 4. Referencias rapidas

- **Inicio rapido backend:** `backend/README.md`, `backend/docs/AI_NAVIGATION_LAYER.md`.
- **Mapa de codigo e rotas:** `backend/docs/CODE_MAP.md`, `backend/README_BACKEND.md` (se existir).
- **Regras para IA:** `.cursorrules`, `backend/docs/AI_RULES.md`, `.cursor/rules/` (learning-engine-refactor, etc.).
- **Ciclos Codex/Cursor:** `backend/docs/AI_AGENT_EXTRACTION_CYCLE.md` + `backend/tests/test_extraction_cycle_*.py`; sempre um alvo por vez, TDD e resposta final `APROVADO`/`BLOQUEADO`/`DISCORDO`.

# PJeCalc Smart Extractor

Automatiza a leitura de sentenças e acórdãos trabalhistas em PDF, produz JSON estruturado, Excel, memória de cálculo auditável e arquivo `.pjc` (PJeCalc 2.14.0).
Inclui um **Laboratório de Aprendizado** que treina regras jurídicas preditivas de forma autônoma (Self-Healing Rule Engine).

---

## Estrutura do repositório

```
Extractor/
├── .cursorrules               # Regras de IA para Cursor — ler antes de qualquer tarefa
├── backend/                   # API Python/FastAPI + pipeline + motor jurídico + lab
│   ├── README.md              # Documentação técnica detalhada do backend
│   ├── docs/                  # Documentação para agentes de IA (ler antes de abrir código)
│   │   ├── AI_NAVIGATION_LAYER.md   # PONTO DE ENTRADA obrigatório para IA
│   │   ├── SYSTEM_OVERVIEW.md       # Visão macro do produto (1 página)
│   │   ├── PIPELINE.md              # Os 10 passos do pipeline e contratos
│   │   ├── CODE_MAP.md              # Arquivo → responsabilidade + índice por domínio
│   │   ├── CODE_INTELLIGENCE_MAP.md # Mapa de domínios e entrypoints
│   │   ├── AI_RULES.md              # Regras de conduta para IA
│   │   └── guia_eficiencia.md       # Diretrizes de prompt, hierarquia processual, boas práticas
│   ├── main.py                # API FastAPI (upload, jobs, WebSocket, lab, stats)
│   ├── workers/processor.py   # Pipeline de extração (10 passos)
│   ├── services/              # Todos os módulos de serviço
│   ├── skills/                # Playbooks .md para Gemini (sentença, parecer, estilos)
│   └── ...
└── frontend/
    ├── index.html             # SPA Tailwind (4 views: Extrator, Lab, Histórico, Stats)
    └── js/
        ├── app.js             # Upload, polling, export, histórico, estatísticas
        ├── render.js          # Renderização dos dados extraídos
        └── lab.js             # Laboratório de Aprendizado (8 cards, múltiplos arquivos)
```

---

## Para agentes de IA

**Ordem de leitura para qualquer tarefa:**

1. `.cursorrules` (raiz) — regras críticas e features recentes (já lido automaticamente pelo Cursor).
2. `backend/docs/AI_NAVIGATION_LAYER.md` — roteiro por tipo de tarefa + mapa do `learning_engine.py`.
3. `backend/docs/CODE_MAP.md` — localizar arquivo sem abrir código desnecessário.
4. Somente então abrir 1–3 arquivos de código específicos.

---

## Início rápido

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Testes
pytest -q

# Frontend: abrir frontend/index.html no navegador (ou servir estático)
```

Variáveis de ambiente necessárias em `backend/.env`: `GEMINI_API_KEY`, `FIREBASE_PROJECT_ID`, e opcionais (`MAX_FILE_SIZE_MB`, `SCHEMA_VERSION`, etc.). Ver `backend/config.py`.

---

## Funcionalidades principais

| Funcionalidade | Onde |
|----------------|------|
| Extração de sentença trabalhista (PDF → JSON 45+ campos) | `workers/processor.py` + `services/sentence_finder.py` |
| Export Excel + `.pjc` (PJeCalc 2.14.0) | `services/excel_exporter.py`, `services/pjc_exporter.py` |
| Parecer Técnico Padrão Ouro (IA + templates) | `services/explanation_engine.py` + `services/ai_client.py` + `skills/parecer_pericial.md` |
| Motor de regras jurídicas (STF → TST → CLT) | `services/legal_engine/` + `services/jurisprudencia/` |
| Laboratório de Aprendizado (8 cards: petição, contestação, processo, liquidação, parecer, impugnação, PJC, manifestação) | `services/learning_engine.py` + `frontend/js/lab.js`; barra de eficiência em tempo real; ver `backend/docs/guia_eficiencia.md` |
| Título Executivo Complexo (múltiplos PDFs + hierarquia + data) | `_extrair_titulo_executivo_multiplos` em `learning_engine.py` |
| Duplo Style Transfer (impugnação + manifestação) | `_extrair_manifestacao_pericial` + `_merge_dados_manifestacao` |
| Guardrails anti-alucinação `verba_ausente` | `_filtrar_*` em `learning_engine.py` |
| Self-Healing Rule Engine (regras autônomas) | `services/knowledge_base.py` + `legal_engine/dynamic_rule_loader.py` |
| Dashboard de Estatísticas (polling reativo) | `main.py /api/stats` + `frontend/js/app.js` |

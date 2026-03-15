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
| **Painel Raio-X (aba Processar)** | Ordem otimizada para PJe-Calc (sem rolagem nas 3 primeiras abas): **Bloco 1** Identificação e Juízo (número do processo sticky, reclamante/reclamada, data ajuizamento, prescrição quinquenal); **Bloco 2** Parâmetros Estruturais (admissão, demissão, maior remuneração, divisor de horas, motivo rescisão); **Bloco 3** Índices e Correção (mini-cards Índice/Juros); **Bloco 4** Verbas e Adicionais (badges); **Bloco 5** Dicas do Laboratório (alerta fixo no topo). Cópia inteligente: normaliza datas DD/MM/AAAA e CPF/CNPJ sem pontos/traços. Feedback: animação check verde ao copiar. `extraction_engine.py` inclui `prescricao_quinquenal`; frontend `render.js` → `renderRaiox`. |
| Export Excel + `.pjc` (PJeCalc 2.14.0) | `services/excel_exporter.py`, `services/pjc_exporter.py` |
| Parecer Técnico Padrão Ouro (IA + templates) | `services/explanation_engine.py` + `services/ai_client.py` + `skills/parecer_pericial.md` |
| Motor de regras jurídicas (STF → TST → CLT) | `services/legal_engine/` + `services/jurisprudencia/` |
| Laboratório de Aprendizado (8 cards + Card Provas como hub) | `services/learning_engine.py` + `frontend/js/lab.js`. **Card "Amostragens e Provas Adicionais"** = hub único: o usuário pode anexar aqui **Parecer, Amostragens e Manifestações** em um só upload; o backend autoclassifica por conteúdo (parecer/amostragem/manifestação) e preenche os slots internos; texto completo vai para `<AMOSTRAGENS_DA_PERITA>`. Cards 5, 6 e 8 continuam opcionais para envio explícito. Ver `backend/docs/guia_eficiencia.md`. |
| Título Executivo Complexo (prioridade ao nome: 1grau/ATOrd→1GRAU, 2grau/ROT→TRT; data sem autuação; tier diferente=ambos mantidos) | `learning_engine.py` → `_classificar_tier_decisao`, `_extrair_data_documento`, `_extrair_titulo_executivo_multiplos` |
| Duplo Style Transfer (impugnação + manifestação) | `_extrair_manifestacao_pericial` + `_merge_dados_manifestacao` |
| **Ghostwriter — Minuta Manifestação (.docx)** | `POST /lab/gerar-docx`: body = relatório Lab. O botão "Gerar Minuta Word" aparece **sempre que uma análise for concluída** (mesmo com 0 discrepâncias). Com 0 discrepâncias o .docx traz cabeçalho + mensagem "Nenhuma discrepância registrada". Com discrepâncias: endpoint envia `skills/manifestacao_style.md` como **Instrução de Tom e Voz**; `document_generator.py` monta cabeçalho (Processo, Reclamante, Reclamada), MANIFESTAÇÃO AOS CÁLCULOS, seções, tabela **Table Grid**, encerramento "Pede Deferimento. [Cidade], [Data]." e espaço para assinatura. Validar com Caso Victor Felipe (Teste 5) ou Gustavo Henrique (Teste 10). |
| Guardrails anti-alucinação `verba_ausente` | `_filtrar_*` em `learning_engine.py` |
| Self-Healing Rule Engine (regras autônomas) | `services/knowledge_base.py` + `legal_engine/dynamic_rule_loader.py` |
| Dashboard de Estatísticas (polling reativo) | `main.py /api/stats` + `frontend/js/app.js` |

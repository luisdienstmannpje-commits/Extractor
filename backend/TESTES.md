# Guia de Testes — Smart Extractor

## Rodar todos os testes unitários (sem IA, rápido)

```bash
cd backend
pytest tests/unit/ tests/jurisprudencia/ -v
```

## Rodar só extração regex (mais rápido, zero API)

```bash
pytest tests/unit/test_regex_fields.py -v
```

## Rodar motor jurídico

```bash
pytest tests/unit/test_legal_engine.py tests/jurisprudencia/ -v
```

## Rodar testes de integração (requer GEMINI_API_KEY)

```bash
pytest tests/integration/ -v -m integration
```

## Benchmark completo com PDFs reais

```bash
python tests/run_benchmark.py
# Modo silencioso:
python tests/run_benchmark.py --quiet
```

Resultado salvo em `docs/BENCHMARK_RESULTS.md`.

---

## Estrutura de testes

```
backend/tests/
├── fixtures/
│   ├── pdfs/           ← PDFs reais anonimizados
│   ├── expected/       ← JSON com gabarito validado pela perita
│   └── README.md       ← instruções para adicionar casos
│
├── unit/               ← Zero IA, zero PDF real, rápidos
│   ├── test_regex_fields.py     (pre_extractor — 40+ casos)
│   ├── test_pdf_extraction.py   (text_processor, normalizer, dedup)
│   └── test_legal_engine.py     (motor de regras, explanation engine)
│
├── jurisprudencia/     ← Testes por regra jurídica (pré-existentes)
│   ├── test_legal_engine.py
│   ├── test_aviso_previo_dias.py
│   └── ... (16 arquivos)
│
├── integration/        ← Requerem GEMINI_API_KEY
│   └── test_pipeline_full.py    (pipeline completo com PDFs reais)
│
├── conftest.py         ← Fixtures compartilhadas (sys.path, dados mínimos)
└── run_benchmark.py    ← Script de benchmark (não é pytest)
```

---

## Adicionar novo caso de teste regex

1. Identifique o padrão novo no texto de uma sentença real
2. Adicione em `tests/unit/test_regex_fields.py` na classe correspondente
3. Rode `pytest tests/unit/test_regex_fields.py -v` — deve passar
4. Se falhar, adicione o padrão em `services/pre_extractor.py`
5. Documente em `docs/CHANGELOG_REFATORACAO.md`

## Adicionar novo PDF de benchmark

1. Anonimize o PDF (CPF, nome → dados fictícios)
2. Coloque em `tests/fixtures/pdfs/processo_XXX.pdf`
3. Crie o JSON esperado em `tests/fixtures/expected/processo_XXX.json`
4. **Peça validação à perita antes de comitar**
5. Rode `python tests/run_benchmark.py`

---

## Interpretando o benchmark

| Taxa | Significado | Ação |
|------|-------------|------|
| ≥ 85% | Excelente — meta atingida | Nenhuma |
| 70–84% | Aceitável — melhorar | Investigar campos com falha |
| 50–69% | Atenção | Revisar pipeline |
| < 50% | Crítico | Pipeline com problema grave |

---

## Campos prioritários (em ordem de importância para o PJeCalc)

1. `numero_processo` — identificação do feito
2. `data_admissao` + `data_demissao` — prazo prescricional
3. `salario_base` — base de todos os cálculos
4. `motivo_rescisao` — define verbas rescisórias devidas
5. `verbas_deferidas[]` — o que calcular
6. `indice_correcao` + `juros_mora` — ADC 58
7. `vara_trabalho` + `data_sentenca` — identificação da decisão

---

## Executar testes em CI

```yaml
# Exemplo GitHub Actions
- name: Testes unitários
  run: |
    cd backend
    pip install -r requirements.txt
    pytest tests/unit/ tests/jurisprudencia/ -v --tb=short

- name: Verificar motor jurídico
  run: |
    cd backend
    python services/VERIFICAR_MOTOR.PY
```

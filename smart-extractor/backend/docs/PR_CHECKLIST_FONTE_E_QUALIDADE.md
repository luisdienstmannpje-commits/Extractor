## Checklist de Aceite — Fonte por Página, Prompt e Qualidade por Tipo

### Escopo desta entrega

- [ ] Frontend exibe origem de verba mesmo sem callback de navegação.
- [ ] Prompt de sentença/acórdão/liquidação força `trecho_fundamentacao` curto por verba.
- [ ] Gate de qualidade para `liquidacao` aceita ausência de `salario_base` com identificação mínima.
- [ ] Recorte inicial (`capa`) é adaptativo por tipo/tamanho do PDF.

### Critérios por arquivo

#### `frontend/src/components/features/AnalysisReport.tsx`
- [ ] Quando `verba.pagina_origem != null` e `onNavegar` existe, renderiza botão `🎯 pág. N`.
- [ ] Quando `verba.pagina_origem != null` e `onNavegar` não existe, renderiza fallback textual `p. N`.
- [ ] Não altera a lógica de exibição para verbas sem `pagina_origem`.

#### `frontend/src/vite-env.d.ts`
- [ ] Declara módulo `pdfjs-dist/build/pdf.worker.min.mjs?url`.
- [ ] `npm run lint` sem erro de módulo não encontrado para `PdfViewer`.

#### `backend/services/ai_client.py`
- [ ] Template de `verbas_deferidas[].trecho_fundamentacao` contém exemplo textual (não `null`).
- [ ] Regras obrigatórias incluem instrução explícita para `trecho_fundamentacao` (máx. 150 chars).
- [ ] Fluxo `peticao_inicial` permanece isolado (sem exigir o contrato de sentença/liquidação).

#### `backend/workers/processor.py`
- [ ] `_qualidade_ok(..., doc_type="liquidacao")` exige identificação mínima (`numero_processo` **ou** partes).
- [ ] `_qualidade_ok(..., doc_type="liquidacao")` exige `verbas_deferidas` não vazias.
- [ ] `_qualidade_ok(..., doc_type="sentenca")` continua rígido com `salario_base` obrigatório.

#### `backend/services/sentence_finder.py`
- [ ] Existe `get_adaptive_capa_pages(total_pages, doc_type)`.
- [ ] Regras:
  - [ ] `liquidacao` -> 8
  - [ ] `total_pages > 100` -> 5
  - [ ] padrão -> 2
- [ ] Aplicação do valor adaptativo no cálculo de `capa_indices`.

### Testes obrigatórios (evidências)

#### Frontend
- [ ] `npm run lint`
- [ ] `npm run build`

#### Backend
- [ ] `./venv/Scripts/python.exe -m pytest -q tests/test_smart_truncate.py`
- [ ] `./venv/Scripts/python.exe -m pytest -q tests/test_processor_quality_gate.py`
- [ ] `./venv/Scripts/python.exe -m pytest -q tests/test_document_classifier.py`

### Não-regressão (must-have)

- [ ] `peticao_inicial` não recebe regressão de prompt/contrato de sentença.
- [ ] Sem alteração no comportamento de cache para `sentenca` e `acordao`.
- [ ] Sem quebra de renderização no Laboratório e no Extrator.
- [ ] Sem novos erros de lint.

### Riscos residuais monitorados

- [ ] `trecho_fundamentacao` curto/ruidoso ainda pode gerar `pagina_origem = null`.
- [ ] Aumento de contexto de capa em PDFs longos pode elevar custo de tokens (monitorar logs).

### Documentação sincronizada

- [ ] `backend/docs/ALTERACOES_VS_DOCUMENTACAO.md`
- [ ] `backend/docs/PIPELINE.md`
- [ ] `backend/docs/CODE_MAP.md`
- [ ] `backend/docs/AI_NAVIGATION_LAYER.md`
- [ ] `backend/README.md`

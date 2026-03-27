## Contexto

Este PR padroniza um checklist de revisão focado em:
- rastreabilidade de fonte por página (`pagina_origem`);
- robustez do prompt (`trecho_fundamentacao`);
- qualidade adaptativa por tipo documental (`liquidacao` vs `sentenca/acordao`);
- recorte adaptativo de capa em PDFs longos.

## Resumo da mudança

- Adiciona/organiza checklist de aceite para revisão técnica.
- Define critérios objetivos por arquivo para reduzir regressões silenciosas.
- Estabelece comandos de validação (backend + frontend) para revisão reproduzível.

## Plano de teste (revisor)

- Verificar arquivo de checklist no repositório:
  - `smart-extractor/backend/docs/PR_CHECKLIST_FONTE_E_QUALIDADE.md`
- Executar comandos focais:
  - `pytest -q tests/test_smart_truncate.py tests/test_processor_quality_gate.py tests/test_document_classifier.py`
  - `npm run lint && npm run build`

## ✅ Checklist de Aceite (10 itens)

- [ ] `sentence_finder`: `get_adaptive_capa_pages` aplica **8/5/2** corretamente (`liquidacao` / PDF longo / padrão).
- [ ] `sentence_finder`: guardrail impede extrapolar páginas em PDFs curtos.
- [ ] `ai_client`: template de sentença/liquidação/acórdão usa exemplo textual em `trecho_fundamentacao` (não `null`).
- [ ] `ai_client`: regra explícita de `trecho_fundamentacao` curto (máx. 150 chars).
- [ ] `ai_client`: `peticao_inicial` permanece com contrato próprio (sem contaminação).
- [ ] `processor`: `doc_type="liquidacao"` aceita falta de `salario_base` se houver identificação mínima + verbas.
- [ ] `processor`: `sentenca/acordao` continuam rígidos (sem `salario_base` não cacheia).
- [ ] `AnalysisReport`: sem `onNavegar`, exibe fallback `p. N`; com `onNavegar`, exibe `🎯 pág. N`.
- [ ] Testes focais passaram:
  - `pytest -q tests/test_smart_truncate.py tests/test_processor_quality_gate.py tests/test_document_classifier.py`
  - `npm run lint && npm run build`
- [ ] Docs sincronizadas (`ALTERACOES_VS_DOCUMENTACAO`, `PIPELINE`, `CODE_MAP`, `AI_NAVIGATION_LAYER`, `README`).

## Risco e impacto

**Risco funcional:** baixo (artefato de checklist/documentação).  
**Impacto esperado:** acelera revisão e reduz chance de regressões passarem sem checagem.

## Observabilidade pós-merge (recomendado)

- Monitorar `latencia_ms` em PDFs longos (500-700+ páginas).
- Monitorar taxa de `pagina_origem = null` após obrigatoriedade de `trecho_fundamentacao`.
# Pipeline de extração — workers/processor.py

Referência única para os 10 passos. Não alterar a ordem ou os contratos sem análise arquitetural.

## Visão geral

| # | Etapa | Módulo / Ação | Saída típica |
|---|--------|----------------|--------------|
| 1 | Freemium | `database.get_user_credits` | Continua ou retorna erro. |
| 2 | Cache | `_hash_pdf` → `database.get_cache`; `_qualidade_ok` | Se OK, retorno imediato com dados em cache. |
| 3 | Extração de texto | `sentence_finder.extract_sentence_from_pdf` | `(texto, doc_type)`. |
| 4 | Playbook | `_load_skill(skill_file)` por `doc_type` | String do playbook .md. |
| 5 | IA | `ai_client.extract_data_with_gemini(texto, playbook, anchor)` | `{ "data", "error", "model_used" }`. |
| 6 | Pós-IA | `_validate_result(ai_result["data"])` | Dict limpo + derivações (jornada, divisor_horas, prescrição, evolucao_salarial). |
| 6b | Deduplicação | `deduplicar_verbas(verbas)` (jurisprudencia) | `verbas_dedup`, `avisos_dedup`. |
| 7 | Pydantic | `ProcessoTrabalhista(**dados_limpos)` | `dados_finais` (dict). |
| 8 | Validação jurídica | `validar_dados(dados_finais)` + `_RULE_ENGINE.executar(dados_finais)` + `gerar_explicacoes(...)` | `alertas_juridicos`, `regras_aplicadas`, `memorial_juridico`, `explicacoes`. |
| 9 | Persistência | `_qualidade_ok` → `save_cache`, `save_extraction`, `deduct_credit` | Cache e extração gravados. |
| 10 | Memória de cálculo | `memoria_calculo.gerar_memoria(job_id, dados, ...)` | Arquivo `memoria_{job_id}.json`. |

## Dependências entre passos

- 2 depende de 1 (crédito já verificado).
- 4 depende de 3 (doc_type).
- 5 depende de 3 e 4 (texto + playbook).
- 6 depende de 5; 6b depende de 6 (verbas).
- 7 depende de 6 e 6b.
- 8 depende de 7 (dados_finais).
- 9 depende de 7 e 8 (dados + qualidade).
- 10 depende de 7, 8 e do resultado da IA (model_used, doc_type, explicacoes).

## Contratos que não devem ser quebrados

- **Entrada de `process_lawsuit_pdf`**: `(user_id: str, file_bytes: bytes, job_id: str)`.
- **Retorno**: dict com `status`, `data`, `alertas_juridicos`, `regras_aplicadas`, `memorial_juridico`, `explicacoes`, e demais campos documentados no README.
- **Validação jurídica**: `legal_validator.validar_dados(dados)` retorna `list[str]`; `validar_dados_completo(dados)` retorna dict com `alertas`, `regras_aplicadas`, `memorial_juridico`.

Para alterar um passo, verificar testes em `tests/` e `tests/jurisprudencia/` e rodar `pytest -q` após a mudança.

**Nota:** O Laboratório de Aprendizado (`learning_engine.py` como facade; módulos `services/lab/learning_io.py`, `services/lab/extractors.py`, `services/lab/self_healing.py` — codify e Shadow Rules) possui fluxo próprio (analisar, preview, salvar, codify); ver `CODE_MAP.md` e `AI_NAVIGATION_LAYER.md` § 2.9 e § 2.10.

**Nota de implementação:** Os passos 4b–10 são compartilhados entre `process_lawsuit_pdf` e `process_lawsuit_dossie` via função privada `_executar_pipeline_pos_ia` em `processor.py`. Alterações nesses passos devem ser feitas nessa função única.

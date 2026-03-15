# Verificação: prompt.md vs projeto Smart Extractor

Conferência das opções informadas pelo Gemini no `prompt.md` contra o código e a documentação oficial do projeto. **Sem alterar código** — apenas diagnóstico e ajustes no próprio prompt quando necessário.

---

## 1. Contexto do produto e objetivo

| Item no prompt | No projeto |
|----------------|------------|
| Extração de sentenças trabalhistas em PDF | ✅ `sentence_finder.extract_sentence_from_pdf`, `workers/processor.py` |
| Dados estruturados para PJeCalc | ✅ `excel_exporter`, `pjc_exporter`, modelos em `models.py` |
| Reduzir tempo de leitura (horas → segundos) | ✅ Objetivo do produto |
| Evolução para SaaS LegalTech | ✅ Alinhado ao README e visão |

**Conclusão:** Correto. Nada a acrescentar.

---

## 2. Pipeline atual (prompt vs real)

**No prompt está:**

```
PDF → sentence_finder → OCR híbrido → text_processor → pre_extractor → smart truncate
→ IA (Gemini) → deduplicator → legal_rule_engine → validação jurídica → JSON → frontend → export .pjc
```

**No projeto (PIPELINE.md / workers/processor.py) os 10 passos são:**

1. **Freemium** — créditos (database)
2. **Cache** — hash PDF → get_cache; se hit, retorno imediato
3. **Extração de texto** — `sentence_finder.extract_sentence_from_pdf` (inclui OCR híbrido nas páginas do bloco decisório)
4. **Playbook** — carrega skill por `doc_type`; opcionalmente `filtro_dispositivo.md` se dispositivo não encontrado (usa `text_processor.find_section_hybrid`)
5. **IA** — `ai_client.extract_data_with_gemini(texto, playbook)`; internamente há **smart truncate** por modelo (limite de caracteres)
6. **Pós-IA** — `_validate_result` + derivações (jornada, divisor_horas, prescrição etc.)
6b. **Deduplicação** — `deduplicar_verbas`
7. **Pydantic** — `ProcessoTrabalhista(**dados_limpos)`
8. **Validação jurídica** — `validar_dados` + `LegalRuleEngine.executar` + `gerar_explicacoes`
9. **Persistência** — save_cache, save_extraction, deduct_credit (quando qualidade OK)
10. **Memória de cálculo** — `memoria_calculo.gerar_memoria`

**Divergências:**

- **pre_extractor:** existe em `services/pre_extractor.py` e é usado pelo `ai_client` quando recebe `pre_fields` (âncoras para o prompt). O **processor não chama** o pre_extractor nem passa `pre_fields` para a IA. Ou seja: pre_extractor não é um passo do pipeline atual; é uma capacidade disponível mas não integrada no fluxo principal.
- **OCR híbrido:** está **dentro** do sentence_finder (extração por página, com fallback OCR), não como passo separado.
- **text_processor:** usado apenas para `find_section_hybrid(texto, "dispositivo")` (decidir se carrega `filtro_dispositivo.md`), não como etapa de extração antes da IA.
- **Smart truncate:** existe e está **dentro** do `ai_client` (`_smart_truncate` antes de chamar o modelo).

**Recomendação:** Ajustar o diagrama do pipeline no prompt para não listar pre_extractor como passo obrigatório e opcionalmente mencionar cache e freemium, para não gerar expectativa de que pre_extractor esteja no fluxo principal.

---

## 3. Stack atual

| Item no prompt | No projeto |
|----------------|------------|
| Python | ✅ |
| FastAPI | ✅ `main.py` |
| SQLite | ✅ `services/database.py`, `schema_version_guard.py` — créditos, cache, extrações, jobs |
| Pydantic | ✅ `models.py`, `legal_engine/rule_base.py` |
| RapidFuzz | ✅ (uso em deduplicação/similaridade) |
| pdfplumber | ✅ `sentence_finder`, extração de texto |
| Tesseract | ✅ OCR no sentence_finder |
| IA: Gemini Flash + Pro fallback | ✅ `ai_client.py` (MODELS_CASCADE) |
| Frontend: HTML, CSS, JS | ✅ `frontend/` — Vanilla JS |
| Testes: pytest, "170+ testes" | ✅ pytest; **767 testes** coletados (número no prompt desatualizado) |

**Recomendação:** Atualizar no prompt de "170+ testes" para "750+ testes" (ou "centenas de testes automatizados") para refletir o estado atual.

---

## 4. Princípios de engenharia

Modularidade, baixo acoplamento, alta coesão, observabilidade, tolerância a falhas, código previsível — são diretrizes do documento, não algo que se “verifica” no código. Estão alinhados com `AI_RULES.md` e `.cursorrules`.

**Conclusão:** Manter como está.

---

## 5. Processo obrigatório de resposta (5 passos)

1️⃣ Diagnóstico → 2️⃣ Impacto → 3️⃣ Solução e trade-offs → 4️⃣ Arquivos a alterar → 5️⃣ Código.

Isso está alinhado com `backend/docs/AI_RULES.md` (“Explicar impacto antes de gerar código”) e com o `.cursorrules` (alterações incrementais, documentar impacto).

**Conclusão:** Correto. Nada a acrescentar.

---

## 6. Legal Rule Engine

| Item no prompt | No projeto |
|----------------|------------|
| CLT, Súmulas TST, OJs | ✅ Regras em `legal_engine/rules/` e `jurisprudencia/` (STF, TST, CLT, consistência) |
| Modularizadas, auditáveis, testáveis | ✅ Uma regra por arquivo, herdam `LegalRule`, testes em `tests/jurisprudencia/` |
| Não misturar lógica jurídica no código procedural | ✅ Regras isoladas; engine em `engine.py`; `AI_RULES.md` reforça isso |

**Conclusão:** Correto. Nada a acrescentar.

---

## 7. Redução de custo de IA (ordem de prioridade)

No prompt: 1 regex/parsing → 2 heurísticas jurídicas → 3 smart truncation → 4 cache → 5 embeddings → 6 LLM só para interpretação complexa.

| Item | No projeto |
|------|------------|
| 1 Regex/parsing antes da IA | ✅ pre_extractor (regex); atualmente **não** usado no pipeline principal |
| 2 Heurísticas jurídicas | ✅ Motor de regras (Python puro, zero tokens) |
| 3 Smart truncation | ✅ `ai_client._smart_truncate` antes de enviar ao modelo |
| 4 Cache | ✅ Cache por hash do PDF (database); passo 2 do pipeline |
| 5 Embeddings | ❌ **Não implementado** no app (sem cache por similaridade ou busca semântica) |
| 6 LLM para interpretação complexa | ✅ Gemini só para extração do texto já recortado |

**Conclusão:** A ordem está correta como prioridade. O único item listado que o projeto **não** tem é embeddings (cache semântico). Isso pode ser mantido no prompt como “roadmap” ou removido/qualificado para não sugerir que já existe.

---

## 8. Suíte de testes

- Evitar regressões, manter compatibilidade, sugerir testes ao adicionar features: alinhado com `AI_RULES.md` e `.cursorrules`.
- Número: **767 testes** coletados; no prompt consta “170+”. Recomendação: atualizar para “750+ testes” ou “centenas de testes”.

---

## 9. README como referência

O prompt diz que o README é a referência oficial e não deve ser contradito sem justificativa. Isso está alinhado com `backend/README.md` e com `docs/AI_NAVIGATION_LAYER.md` / `AI_RULES.md`.

**Conclusão:** Manter.

---

## 10. O que NÃO fazer (sem regressão)

- **Não** alterar a ordem dos 10 passos do pipeline nem os contratos em `processor.py` sem atualizar `PIPELINE.md` e testes.
- **Não** remover ou alterar lógica jurídica sem substituição e testes.
- **Não** introduzir uso de pre_extractor ou embeddings no pipeline neste momento — a verificação é só no prompt; mudanças de código seriam outra tarefa.

---

## Resumo das alterações sugeridas no prompt.md

1. **Pipeline:** Ajustar o diagrama para refletir os 10 passos reais (incluindo Freemium e Cache) e deixar claro que **pre_extractor** existe como módulo mas **não** é passo do fluxo principal hoje; OCR híbrido e smart truncate estão dentro de sentence_finder e ai_client.
2. **Testes:** Atualizar “170+ testes” para “750+ testes” (ou “centenas de testes automatizados”).
3. **Redução de custo de IA:** Especificar que “embeddings” está na lista como prioridade futura; no projeto atual há cache por hash e smart truncation, mas não cache por embeddings.

Implementação: aplicar apenas edições no `prompt.md` conforme a seção seguinte.

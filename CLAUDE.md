# Smart Extractor — Instruções para Claude Code

## Leia antes de qualquer tarefa

1. `backend/docs/AI_NAVIGATION_LAYER.md` — mapa do sistema
2. `backend/docs/EXTRACAO_STATUS.md` — status atual de cada campo + bug do pre_extractor desconectado
3. `backend/docs/GEMINI_CALLS_INVENTORY.md` — onde a IA é chamada e o que pode ser substituído
4. `backend/docs/DEAD_CODE.md` — código morto identificado (patches, stubs, duplicatas)
5. `backend/TESTES.md` — como rodar os testes

## Regras absolutas (não viole nenhuma)

1. **Nunca quebre o que funciona.** Antes de alterar qualquer arquivo, liste o que ele faz e confirme o que será preservado.
2. **Teste antes de refatorar.** Se não há teste cobrindo uma função, crie o teste primeiro, depois refatore.
3. **Zero regressão no export .pjc.** Qualquer alteração em `pjc_exporter.py` exige teste com arquivo de referência.
4. **IA é o último recurso.** Toda lógica que pode ser feita com Python puro (regex, pdfplumber) NÃO deve chamar o Gemini.
5. **Uma tarefa por vez.** Não inicie a próxima fase sem confirmar que a anterior passou nos testes.
6. **Documente cada decisão.** Ao excluir ou mover código, registre o motivo em `docs/CHANGELOG_REFATORACAO.md`.

## Tarefa prioritária conhecida

**Bug crítico — pre_extractor desconectado:**
- `services/pre_extractor.py` tem extração regex para 14 campos (HIGH + MEDIUM)
- `workers/processor.py:408` chama `extract_data_with_gemini(texto, playbook=playbook)` **sem** `pre_fields`
- Correção: adicionar antes do step 5 em `processor.py`:
  ```python
  from services.pre_extractor import pre_extract
  pre_fields = pre_extract(texto)
  ```
  E passar `pre_fields=pre_fields` em `extract_data_with_gemini()`.
- Teste obrigatório antes de aplicar: `pytest tests/unit/test_regex_fields.py -v`

## Convenções de código

- Extractors ficam em `backend/services/` (pre_extractor.py já existe)
- Regras jurídicas ficam em `backend/services/legal_engine/`
- Prompts de IA ficam em `backend/services/ai_client.py` e `backend/services/ai_writer.py`
- Skills (playbooks) ficam em `backend/skills/*.md`
- Testes unitários ficam em `backend/tests/unit/`
- Testes de jurisprudência ficam em `backend/tests/jurisprudencia/`
- Testes de integração ficam em `backend/tests/integration/`

## Como adicionar um novo padrão regex

1. Adicione em `services/pre_extractor.py` — método `_extract_CAMPO()` com `_set_high()` ou `_set_medium()`
2. Crie teste em `tests/unit/test_regex_fields.py`
3. Rode `pytest tests/unit/test_regex_fields.py -v`
4. Rode `python tests/run_benchmark.py` e compare com resultado anterior
5. Documente em `docs/CHANGELOG_REFATORACAO.md`

## Como adicionar uma nova regra jurídica

1. Crie arquivo em `services/legal_engine/rules/nova_regra.py` (não use prefixo `lab_` — não ficará ativo automaticamente)
2. Extenda `LegalRule` com `id`, `titulo`, `base_legal`, `prioridade`, método `aplicar()`
3. O `rule_registry.py` carrega automaticamente — sem necessidade de registrar
4. Crie teste em `tests/jurisprudencia/test_nova_regra.py`
5. Rode `python services/VERIFICAR_MOTOR.PY` para confirmar integridade

## Campos obrigatórios para extração

Ver `backend/docs/EXTRACAO_STATUS.md` para lista completa com status atual.

## Sobre o diretório `/smart-extractor/`

Se existir na raiz, é cópia de merge — verificar antes de remover. Comparar com `backend/` antes de qualquer ação.

## Modelos Gemini em uso

| Arquivo | Modelo atual | Observação |
|---------|-------------|------------|
| `services/ai_client.py` | `gemini-2.5-flash` → `models/gemini-2.5-pro` | Cascata extração principal |
| `services/ai_writer.py` | `gemini-2.5-flash` | Geração de manifestação |
| `services/ai_client.py` | `gemini-2.5-flash` | Geração de parecer |
| `services/learning_engine.py` | `models/gemini-2.5-pro` → `gemini-2.0-flash` | **`gemini-2.0-flash` está depreciado** — substituir por `gemini-2.5-flash` |

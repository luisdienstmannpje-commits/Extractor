# DEAD_CODE.md — Mapeamento de Código Morto / Duplicado / Abandonado

> Gerado em: 2026-05-13

---

## Categoria 1 — Scripts one-shot de patch (alta confiança)

Estes arquivos são scripts que **modificam outros arquivos via substituição de string** (`str.replace`). Parecem ter sido executados em algum momento para corrigir código; não têm callers e não deveriam existir no repositório de produção.

| Arquivo | O que faz | Risco de remoção |
|---------|-----------|-----------------|
| `backend/patch_processor.py` | Patcha `workers/processor.py` com novas importações/chamadas | Baixo — se já aplicado |
| `backend/patch_legal_validator.py` | Patcha `services/legal_validator.py` com novos checks | Baixo |
| `backend/patch_pre_extractor.py` | Patcha `services/pre_extractor.py` com validação CNJ | Baixo |
| `backend/patch_generator.py` | Gera código de regras via template | Baixo |
| `backend/patch_reflexos_proibidos.py` | Patcha regra `reflexos_proibidos.py` | Baixo |
| `backend/fix_explanation_engine.py` | Corrige `explanation_engine.py` | Baixo |

**Ação recomendada:** Verificar se os patches foram aplicados comparando o conteúdo do alvo com o `NEW` string do patch. Se aplicados, mover para `_archive/patches/` e registrar no CHANGELOG.

---

## Categoria 2 — Regras `lab_` sem implementação (alta confiança)

7 arquivos gerados automaticamente pelo Laboratório de Aprendizado. **Todos têm `TODO: implemente a condição` sem nenhuma lógica real.** O método `aplicar()` é `pass`.

| Arquivo | Data geração | Status |
|---------|-------------|--------|
| `services/legal_engine/rules/lab_discrepância_verba_ausente_20260313_030900.py` | 13/03/2026 | Stub vazio |
| `services/legal_engine/rules/lab_discrepância_verba_ausente_20260313_030915.py` | 13/03/2026 | Stub vazio |
| `services/legal_engine/rules/lab_discrepância_verba_ausente_20260313_030947.py` | 13/03/2026 | Stub vazio |
| `services/legal_engine/rules/lab_discrepância_verba_ausente_20260313_031000.py` | 13/03/2026 | Stub vazio |
| `services/legal_engine/rules/lab_discrepância_verba_ausente_20260313_031030.py` | 13/03/2026 | Stub vazio |
| `services/legal_engine/rules/lab_discrepância_verba_ausente_20260313_031104.py` | 13/03/2026 | Stub vazio |
| `services/legal_engine/rules/lab_discrepância_verba_ausente_20260313_031131.py` | 13/03/2026 | Stub vazio |

**Confirmado:** `rule_registry.py` carrega TODOS os arquivos `.py` que **não** começam com `_`. Como esses arquivos começam com `lab_`, são carregados e instanciados a cada inicialização do servidor. O método `aplicar()` é `pass` — não geram alertas úteis, mas desperdiçam CPU na carga e poluem o log com as instâncias.

**Ação recomendada:** Renomear estes arquivos adicionando `_` no início (`_lab_discrepância_...py`) para que o registry os ignore. Ou mover para `_archive/lab_rules_draft/`.

---

## Categoria 3 — Arquivos utilitários sem callers identificados

| Arquivo | Propósito declarado | Callers | Risco |
|---------|--------------------|---------|----|
| `backend/gerar_teste_pjc.py` | Gerador de arquivo PJC de teste | Nenhum encontrado | Baixo — script utilitário para dev |
| `backend/init.py` | Desconhecido (arquivo pequeno) | Nenhum encontrado | Baixo |
| `backend/services/VERIFICAR_MOTOR.PY` | Verificador CLI do motor de regras | Não importado — uso via CLI | **Manter** — ferramenta de CI útil. Renomear para minúsculas: `verificar_motor.py` |

---

## Categoria 4 — Arquivos de arquivo duplicado

| Localização | Duplica de | Observação |
|-------------|-----------|------------|
| `backend/_archive/legacy/legal_validator_pre_engine.py` | `services/legal_validator.py` (versão antiga) | Em `_archive/` — ok |
| `backend/_archive/pjc/pjc_exporter_v5.9.py` | `services/pjc_exporter.py` (versão antiga) | Em `_archive/` — ok |
| `_archive/pjc/` (raiz) | `backend/_archive/pjc/` | **Duplicata fora do backend!** Verificar se são iguais. |

---

## Categoria 5 — Possível duplicação de lógica

| Arquivo A | Arquivo B | Função duplicada |
|-----------|-----------|-----------------|
| `services/jurisprudencia/consistencia/verba_deduplicator.py` | `services/verba_deduplicator.py` | Deduplicação de verbas |

**Ação:** Ler os dois arquivos e verificar se são idênticos ou têm divergências. O `processor.py:417` importa de `services/jurisprudencia/consistencia/verba_deduplicator` — o arquivo raiz pode ser um legado não usado.

---

## Categoria 6 — TODOs sem resolução

| Arquivo | Linha | Conteúdo |
|---------|-------|----------|
| `services/learning_engine.py` | 579 | `TODO: implemente a condição de acionamento desta regra` (no template de geração de regras — parte do template, não um TODO de produção) |
| `services/learning_engine.py` | 740 | `TODO: implementar condição de acionamento com base na análise` (idem) |
| `services/legal_engine/rules/lab_discrepância_verba_ausente_*.py` | 32 | `TODO: implemente a condição` — 7 arquivos, nenhum implementado |

---

## Categoria 7 — Modelo depreciado em uso

| Arquivo | Linha | Modelo | Status |
|---------|-------|--------|--------|
| `services/learning_engine.py` | 828 | `gemini-2.0-flash` | **Depreciado** — substituir por `gemini-2.5-flash` |
| `services/ai_client.py` | 35 | `gemini-2.0-flash` (fallback legado em `CHARS_LIMIT`) | Referência morta — modelo nunca mais será usado se não estiver em `MODELS_CASCADE` |

---

## Sumário de Ações

| Prioridade | Ação | Impacto |
|-----------|------|---------|
| 🔴 Alta | Reconectar `pre_extractor` ao pipeline (ver `EXTRACAO_STATUS.md`) | Reduz chamadas IA em ~35% |
| 🔴 Alta | Substituir `gemini-2.0-flash` por `gemini-2.5-flash` em `learning_engine.py:828` | Evita erros de modelo depreciado |
| 🟡 Média | Verificar se `rule_registry.py` carrega arquivos `lab_*.py` e filtrar stubs | Evita poluição do motor de regras |
| 🟡 Média | Investigar duplicata `verba_deduplicator.py` (raiz vs jurisprudencia/) | Eliminar um dos dois |
| 🟡 Média | Mover `patch_*.py` e `fix_*.py` para `_archive/patches/` | Limpar raiz do backend |
| 🟢 Baixa | Renomear `VERIFICAR_MOTOR.PY` para `verificar_motor.py` | Convenção Python |
| 🟢 Baixa | Investigar e remover `_archive/pjc/` duplicado na raiz | Reduzir confusão |

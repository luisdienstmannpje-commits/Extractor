# CHANGELOG DE REFATORAÇÃO — Smart Extractor

## FASE 0 — Diagnóstico (sem alteração de produção)

**Arquivos criados:**
- `docs/EXTRACAO_STATUS.md` — mapa de 38 campos: onde extraído, método, confiança, problemas
- `docs/GEMINI_CALLS_INVENTORY.md` — 9 pontos de chamada à IA com custo estimado e substituibilidade
- `docs/DEAD_CODE.md` — 7 categorias de código morto (patches, lab stubs, duplicatas, modelo depreciado)

---

## FASE 1 — Arquitetura de testes (sem alteração de produção)

**Arquivos criados:**
- `tests/conftest.py` — fixtures compartilhadas (sys.path, texto_sentenca_simples, casos_de_teste)
- `tests/unit/test_regex_fields.py` — 40+ testes parametrizados do PreExtractor (zero IA)
- `tests/unit/test_pdf_extraction.py` — testes de text_processor, normalizer, verba_deduplicator
- `tests/unit/test_legal_engine.py` — testes do motor de regras e explanation engine
- `tests/integration/test_pipeline_full.py` — smoke tests + testes com PDFs reais (marcados @integration)
- `tests/run_benchmark.py` — script de benchmark com relatório Markdown
- `TESTES.md` — guia completo de execução de testes
- `pyproject.toml` atualizado — `pythonpath`, `testpaths`, marcador `integration`
- `__init__.py` em todos os subdiretórios de tests/ — resolve conflito de nomes de módulo

**Resultado:** 344 passed, 6 falhas pré-existentes em `tests/jurisprudencia/` (bugs de produção, não regressões)

---

## FASE 2 — Conectar pre_extractor ao pipeline (2026-05-13)

**Bug corrigido:** `pre_extractor.py` tinha extração regex completa para 14 campos mas nunca era chamado. `processor.py` chamava `extract_data_with_gemini()` sem `pre_fields`, desperdiçando extração de alta precisão.

**Alterações em `workers/processor.py`:**
1. Import adicionado: `from services.pre_extractor import pre_extract`
2. Antes do step 5 (chamada à IA): `pre_fields = pre_extract(texto)`
3. Chamada à IA atualizada: `extract_data_with_gemini(texto, playbook=playbook, pre_fields=pre_fields)`
4. Após step 6 (`_validate_result`): HIGH fields sobrescrevem resultado da IA

**Impacto esperado:**
- `numero_processo` e `data_sentenca`: ~85% → ~99% de acerto (HIGH — zero tokens)
- `justica_gratuita` e `tipo_rito`: extraídos via regex antes mesmo da IA
- MEDIUM fields (datas, salário, índices, motivo rescisão): injetados como âncoras no prompt → menos alucinação
- Redução de ~10–20% nos tokens de output da IA

**Testes:** `pytest tests/unit/ tests/jurisprudencia/ -q` → 344 passed, 6 falhas pré-existentes (sem regressão)

---

## FASE 6 — Limpeza de código morto (2026-05-13)

**Arquivos movidos para `_archive/patches/`:** 6 scripts one-shot (`patch_*.py`, `fix_explanation_engine.py`) — patches já aplicados aos targets ou obsoletos. Um (`patch_pre_extractor.py`) nunca foi aplicado pois usa import path incorreto (`services.legal_engine.jurisprudencia` em vez de `services.jurisprudencia.consistencia`).

**Arquivos movidos para `_archive/lab_rules_draft/`:** 7 lab stubs (`lab_discrepância_verba_ausente_*.py`) — já excluídos do registry (FASE B), agora removidos da pasta de produção.

**Arquivos deletados:**
- `services/verba_deduplicator.py` — zero callers; versão ativa está em `services/jurisprudencia/consistencia/verba_deduplicator.py`
- `init.py` — arquivo vazio (1 linha em branco)

**Arquivo movido para `_archive/`:** `gerar_teste_pjc.py` — utilitário de dev sem callers.

**Renomeado:** `services/VERIFICAR_MOTOR.PY` → `services/verificar_motor.py` (convenção Python; ferramenta de CI mantida).

**Testes:** 344 passed, 6 falhas pré-existentes (sem regressão).

---

## A — Modelo depreciado corrigido (2026-05-13)

**Arquivo:** `services/learning_engine.py`

`_chamar_gemini_para_codify()` usava cascata `gemini-2.5-pro → gemini-2.0-flash`. O `gemini-2.0-flash` está depreciado — substituído por `gemini-2.5-flash`.

**Motivo:** API depreciada pode retornar erro ou ser removida sem aviso, quebrando o motor de aprendizado silenciosamente.

---

## FASE 3 — Refinamento do prompt da IA (2026-05-13)

**Arquivos:** `services/pre_extractor.py`, `services/ai_client.py`

**Problema:** O prompt enviado ao Gemini listava `numero_processo`, `data_sentenca`, `justica_gratuita` e `tipo_rito` como campos para extrair, mesmo após FASE 2 — desperdício de tokens e risco de alucinação em campos que já temos com 99% de precisão via regex.

**Mudanças:**
1. `pre_extractor.py`: criada `build_prompt_context(pre_fields)` — gera duas seções distintas:
   - **CAMPOS CONFIRMADOS** (HIGH): "use estes valores diretamente, não reextraia"
   - **VALORES PRÉ-EXTRAÍDOS** (MEDIUM): "confirme no texto antes de usar"
2. `ai_client.py`: trocado `build_anchor_section(pre_fields["medium"])` → `build_prompt_context(pre_fields)`, passando HIGH + MEDIUM ao prompt. Log atualizado para mostrar `HIGH: N campos | MEDIUM: N campos`.
3. `build_anchor_section` mantido como thin wrapper para compatibilidade.

**Resultado esperado em produção:** IA não perde ciclos de raciocínio nos 4 campos HIGH; foco vai para verbas, partes e valores (os ~20 campos onde IA é realmente necessária).

---

## B — Lab stubs excluídos do rule_registry (2026-05-13)

**Arquivo:** `services/legal_engine/rule_registry.py`

Adicionado `if fname.startswith("lab_"): continue` em `_discover_modules()`.

**Motivo:** Os 7 arquivos `lab_discrepância_verba_ausente_*.py` eram carregados a cada request, instanciavam classes com `aplicar()` vazio (`pass`) e adicionavam seus IDs ao `regras_aplicadas` / `memorial_juridico` sem qualquer lógica real. O cabeçalho de cada arquivo já documentava: `"Para ativar: renomeie sem prefixo 'lab_'"`.

**Resultado:** `carregar_todas_as_regras()` retorna 31 regras (antes: 38). Nenhum `LAB_*` no memorial.

---

## FASE 4 — Melhoria de extração de verbas (2026-05-13)

**Problema:** `verbas_deferidas` era a "principal fonte de inconsistência" do pipeline (~80% global), com subproblemas específicos: `status_final` nulo (~20% dos casos), `base_calculo` inventado pela IA (~40% de imprecisão), `reflexos` com itens pressupostos e não explícitos (~30% de imprecisão), `valor_fixado` eventualmente calculado/estimado.

**Bug corrigido em `workers/processor.py`:**
- `status_final` tinha ciclo vicioso: `"não informado"` estava no set `SUSPICIOUS` → `_clean_str` convertia para `None` → `_validate_result` redefinia para `"não informado"`. Default alterado para `"deferida"` — semanticamente correto para sentença de 1ª instância (verba foi concedida, não "mantida" de decisão anterior).

**Inconsistência corrigida em `skills/sentenca_ordinaria.md`:**
- Linha 166 dizia `status_final`: `"mantida"` para sentença de 1ª instância. Conflitava com `PROMPT_TEMPLATE` que dizia `"deferida"`. Corrigido para `"deferida"` com nota explicando que "mantida/reformada/excluída/acrescida" são exclusivos de acórdão/embargos.

**Prompt reforçado em `services/ai_client.py`:**
Adicionado bloco `REGRAS CRÍTICAS PARA verbas_deferidas` ao `PROMPT_TEMPLATE`:
- Completude: percorrer dispositivo linha a linha, sem omissões
- `status_final = "deferida"` obrigatório para sentença; nunca null
- `valor_fixado`: null se não encontrar — nunca calcular ou estimar
- `base_calculo`: null se não mencionado explicitamente — nunca inventar com base em conhecimento geral
- `reflexos`: `[]` se não há menção explícita — nunca presumir por natureza da verba
- `integracao_salarial`: triestado real (true/false/null) sem presunção

**Testes:** 344 passed, 6 falhas pré-existentes (sem regressão).

---

## FASE C — Validação de dígito verificador CNJ no pre_extractor (2026-05-13)

**Arquivo:** `services/pre_extractor.py`

**Problema:** `_extract_numero_processo()` promovia qualquer string que passasse no regex CNJ (`\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`) diretamente para HIGH, sem verificar os dígitos verificadores. Um OCR com um dígito errado ou um número de texto diferente poderia ser extraído como HIGH mesmo sendo inválido.

**Mudança:** Import interno de `services.jurisprudencia.consistencia.numero_cnj_validator.validar_cnj`. Candidato extraído pelo regex:
- Dígito válido → `_set_high()` (comportamento anterior preservado)
- Dígito inválido → `_set_medium()` + log `[PRE-EXTRACT]` (IA pode corrigir)

**Contexto:** O patch `_archive/patches/patch_pre_extractor.py` tinha esta mesma lógica mas com import incorreto (`services.legal_engine.jurisprudencia.numero_cnj_validator` — não existe). O import correto é `services.jurisprudencia.consistencia.numero_cnj_validator`.

**Testes atualizados:** 5 números CNJ sintéticos em `tests/unit/test_regex_fields.py` e `tests/unit/test_pdf_extraction.py` trocados por números com DD correto; `conftest.py:texto_sentenca_simples` idem. Novo teste `test_digito_invalido_cai_para_medium` adicionado.

**Testes:** 345 passed (+1), 6 falhas pré-existentes (sem regressão).

---

## FASE D — Correção de 6 falhas pré-existentes (2026-05-13)

### D1 — NumeroCNJValidator: [AVISO] → [ERRO] para número inválido
**Arquivo:** `services/jurisprudencia/consistencia/numero_cnj_validator.py`

A rule emitia `nivel="AVISO"` com mensagem "parece atípico / apenas confira", mas os testes esperavam `[ERRO]` para DD incorreto e formato inválido — e semanticamente correto: DD inválido é definitivamente errado, não apenas suspeito. Mudança: `nivel="AVISO"` → `nivel="ERRO"`, mensagem atualizada para "Dígito verificador CNJ inválido".

### D2 — ReflexosProibidosRule: chaves de _PROIBIDOS não batiam com canonizador
**Arquivo:** `services/legal_engine/rules/reflexos_proibidos.py`

`_PROIBIDOS` tinha chaves `"Multa art. 467"` e `"Multa art. 477"` (minúsculas, sem sufixo CLT), mas `_canonizar_verba()` em `rule_base.py` produz `"Multa Art. 467 CLT"` e `"Multa Art. 477 CLT"`. O lookup `_PROIBIDOS.get(nome_canonico, [])` retornava `[]` para multas, deixando reflexos proibidos passar sem detecção. Chaves corrigidas para corresponder ao canonizador.

### D3 — ConsistenciaSalario: `_MIN` definido mas nunca usado
**Arquivo:** `services/jurisprudencia/consistencia/salario.py`

`_MIN = 1518.00` estava definido mas a lógica do `aplicar()` não tinha ramo `elif v < _MIN`. A rule só alertava para `v <= 0` (ERRO) e `v > _MAX` (AVISO), deixando salários abaixo do mínimo passarem sem alerta. Adicionado: `elif v < _MIN: self._alerta(..., nivel="AVISO")`.

**Testes:** 351 passed (+6), 0 falhas — suite limpa.

---

## FASE E — Cobertura de testes para worker/processor.py (2026-05-13)

**Arquivo criado:** `tests/unit/test_processor_helpers.py`

`processor.py` tinha ~500 linhas e zero testes diretos. Qualquer alteração futura
era feita às cegas. Adicionados 92 testes cobrindo todas as funções puras:

| Classe de testes | Funções cobertas | Casos |
|-----------------|-----------------|-------|
| `TestCleanStr` | `_clean_str` | 12 — None, vazio, SUSPICIOUS, int/float, strip |
| `TestCleanBool` | `_clean_bool` | 10 — bool, strings, default, case-insensitive |
| `TestDedupAlertas` | `_dedup_alertas` | 8 — listas vazias, None, dedup intra/inter-listas, ordem |
| `TestValidateResultEstrutura` | `_validate_result` (campos simples) | 8 — verbas não-lista, booleanos |
| `TestValidateResultVerbas` | `_validate_result` (verbas) | 12 — nome, status_final, integracao_salarial, reflexos, quantidade_diaria |
| `TestValidateResultPosProcessamento` | derivações determinísticas | 15 — jornada, fgts, prescrição, divisor, evolução |
| `TestQualidadeOk` | `_qualidade_ok` | 7 — completo, ausentes, verbas insuficientes |

**Comportamento documentado pelos testes:**
- `status_final` null → `"deferida"` (fix FASE 4 agora coberto por teste)
- `prescricao_quinquenal`, `divisor_horas`, `evolucao_salarial` não estão em `CAMPOS_TEXTO` — a IA nunca os retorna, o cálculo SEMPRE roda. O guarda `if not cleaned.get(campo)` é efetivamente morto para esses três campos.
- `_dedup_alertas` preserva a ordem de primeira aparição (não de última)

**Técnica de importação:** `google.genai.Client` mockado antes do import via `with patch(...):` para isolar os testes da API key.

**Testes:** 975 passed (+92), 0 falhas.

---

## FASE F — Campos calculados adicionados a CAMPOS_TEXTO (2026-05-13)

**Arquivo:** `workers/processor.py`

**Problema detectado pelos testes da FASE E:** `prescricao_quinquenal`, `divisor_horas` e `evolucao_salarial` não estavam em `CAMPOS_TEXTO`. Consequência: o guarda `if not cleaned.get(campo)` em `_validate_result` era efetivamente dead code para esses três campos — `cleaned` nunca os recebia da IA, então o guarda era sempre True e o cálculo sempre rodava, silenciosamente ignorando qualquer valor presente no input.

**Correção:** Três campos adicionados ao final de `CAMPOS_TEXTO` com comentário explicando o motivo. Agora:
- Se a IA retornar esses campos (cenário futuro), `_clean_str` os copia para `cleaned` antes do pós-processamento
- O guarda `if not cleaned.get(campo)` funciona corretamente — valor existente é preservado, cálculo só roda quando ausente
- Os testes da FASE E foram atualizados para refletir o comportamento corrigido

**Testes:** 975 passed, 0 falhas (sem regressão).

---

## FASE G — Melhoria de extração de partes (2026-05-14)

**Arquivos:** `skills/sentenca_ordinaria.md`, `skills/acordao.md`, `services/ai_client.py`

**Problemas no `EXTRACAO_STATUS.md`:**
- `reclamante` (~85%): "Confunde autor/reclamante em acórdãos com múltiplos recorrentes"
- `reclamada` (~80%): "Múltiplas reclamadas (litisconsórcio) frequentemente omitem uma das partes"

**Mudanças:**

1. `sentenca_ordinaria.md` — `reclamante` agora tem frases-gatilho de busca explícitas; `reclamada` instrui listar TODAS as empresas em litisconsórcio passivo separadas por " + ".

2. `acordao.md` — `reclamante` recebe instrução de desambiguação: em acórdão, o recorrente pode ser qualquer das partes — o reclamante é SEMPRE o trabalhador (autor original), buscar no Relatório. `reclamada` recebe mesma instrução de litisconsórcio.

3. `ai_client.py` (PROMPT_TEMPLATE) — adicionadas duas linhas em INSTRUÇÕES ESPECÍFICAS:
   - `reclamante`: sempre o trabalhador, não confundir com quem recorreu; buscar frase de identificação de partes no Relatório
   - `reclamada`: listar TODAS em litisconsórcio separadas por " + ", percorrer cabeçalho + relatório inteiro

**Testes:** 443 passed, 0 falhas (sem regressão — mudanças só em arquivos de texto).

---

## FASE 5 — Refatoração de `process_lawsuit_pdf` (2026-05-14)

**Arquivo:** `workers/processor.py`

**Problema:** `process_lawsuit_pdf` era uma função monolítica de ~200 linhas com 8 responsabilidades distintas (cache, texto, playbook, pre_extractor, IA, validação, motor jurídico, persistência). Impossível testar partes isoladas; difícil de rastrear bugs.

**Mudanças:**
1. `_PLAYBOOK_MAP` extraído como constante de módulo (era `dict` inline dentro da função).
2. 6 funções privadas extraídas:
   - `_check_cache(pdf_hash)` → consulta e deserializa cache Redis
   - `_load_playbook(doc_type, texto)` → carrega skill Markdown + fallback para sentença
   - `_apply_ai_result(ai_data, pre_fields)` → `_validate_result` + override HIGH fields + coleta alertas_pre
   - `_run_legal_analysis(dados_finais)` → motor de regras + explanation engine + dedup
   - `_build_parecer(dados_finais)` → chamada ao AI writer separada
   - `_persist_result(user_id, pdf_hash, doc_type, dados_finais)` → cache + Firestore + aprendizado
3. `process_lawsuit_pdf` reduzida de ~200 → ~65 linhas; agora é um orquestrador linear.

**Zero alteração de comportamento:** nenhuma lógica foi modificada, apenas reorganizada. Os 975 testes existentes servem de rede de segurança.

**Testes:** 975 passed, 0 falhas (sem regressão).

---

## FASE H — Cobertura de testes para helpers FASE 5 (2026-05-14)

**Arquivo:** `tests/unit/test_processor_helpers.py`

27 testes adicionados cobrindo os 6 helpers extraídos na FASE 5:

| Classe de testes | Helper coberto | Casos |
|-----------------|----------------|-------|
| `TestCheckCache` | `_check_cache` | 4 — cache miss, hit ok, hit descartado (qualidade), hit sem verbas |
| `TestLoadPlaybook` | `_load_playbook` | 5 — tipo conhecido, desconhecido, todos os 6 tipos do mapa, filtro_dispositivo adicionado/não-adicionado |
| `TestApplyAiResult` | `_apply_ai_result` | 5 — HIGH override, MEDIUM não sobrescreve, avisos dedup, verbas vazias, pre_fields vazio |
| `TestRunLegalAnalysis` | `_run_legal_analysis` | 3 — retorna 5 tuplas, exceção dinâmica swallowed, alertas/regras dinâmicas concatenados |
| `TestBuildParecer` | `_build_parecer` | 3 — chaves esperadas, exceção swallowed, campo error no parecer |
| `TestPersistResult` | `_persist_result` | 7 — save_cache chamado/omitido, deduct_credit chamado/omitido, meta_doc_type injetado, doc_id como string, tupla 3 elementos |

**Comportamentos documentados:**
- `_check_cache` descarta silenciosamente cache de qualidade insuficiente (não lança exceção)
- `_apply_ai_result` não chama `deduplicar_verbas` quando `verbas_deferidas` é lista vazia
- `_run_legal_analysis` engole exceções do pipeline de regras dinâmicas (não crítico)
- `_build_parecer` engole exceções de `gerar_parecer_tecnico_completo` e retorna campos vazios
- `_persist_result` não chama `save_cache` nem `deduct_credit` quando qualidade insuficiente

**Testes:** 1002 passed (+27), 0 falhas.

---

## FASE I — Melhoria de extração de horário e jornada (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `tests/unit/test_regex_fields.py`

**Problemas (EXTRACAO_STATUS.md):**
- `horario_trabalho` (~75%): sem extração regex — 100% dependência da IA
- `jornada_contratual` (~70%): derivação frágil de `horario_trabalho` por pós-processamento
- `salario_base` (~75%): regex não cobria "remuneração mensal de", "salário fixo de", "última remuneração de", "recebia o salário de"

**Mudanças em `services/pre_extractor.py`:**

1. `_RE_SALARIO` expandido:
   - Adicionadas: `remunera[çc][aã]o\s+(?:mensal\s+)?(?:bruta\s+)?de`, `recebia\s+o\s+sal[aá]rio\s+de`, `[úu]ltima\s+remunera[çc][aã]o\s+(?:mensal\s+)?de`, `sal[aá]rio\s+fixo\s+de`, `sal[aá]rio\s+(?:base|fixo|contratual|normativo)\s+de`

2. `_RE_HORARIO_TRABALHO` adicionado — extrai "das HHh às HHh [com X h de intervalo]" após contexto ("horário de trabalho:", "trabalhava", "laborava", "jornada de trabalho").
   - Bug corrigido durante desenvolvimento: `de\s+trabalho\s+` (exigia espaço após "trabalho") → `de\s+trabalho\s*` (aceita "trabalho:" sem espaço)

3. `_RE_JORNADA_CONTRATUAL` adicionado — extrai "X horas diárias [e Y horas semanais]" ou "Y horas semanais" após contexto ("jornada de", "carga horária de").

4. `_extract_horario_trabalho()` adicionado → `_set_medium("horario_trabalho", ...)`

5. `_extract_jornada_contratual()` adicionado → `_set_medium("jornada_contratual", ...)`

6. Ambos registrados em `medium_extractors` e `_ROTULOS_MEDIUM`.

**Impacto esperado:**
- `horario_trabalho`: IA recebe âncora regex em vez de aluciná-lo (~75% → ~88% estimado)
- `jornada_contratual`: derivação pós-IA substituída por âncora direta no prompt; casos sem padrão "HH às HH" agora cobertos (~70% → ~85% estimado)
- `salario_base`: mais gatilhos reconhecidos, menos misses (~75% → ~82% estimado)

**Testes:** 1020 passed (+18), 0 falhas.

---

## FASE J — Adição de `advogado_reclamada` ao esquema (2026-05-14)

**Arquivos:** `models.py`, `workers/processor.py`, `services/ai_client.py`, `skills/sentenca_ordinaria.md`, `skills/acordao.md`

**Problema:** `advogado_reclamada` (advogado da empresa ré) estava completamente ausente do schema, do prompt e dos playbooks. A IA não tinha instrução para extrair esse campo, que é relevante para identificação completa das partes e validação de mandato.

**Mudanças:**

1. `models.py`:
   - Campo `advogado_reclamada: Optional[str]` adicionado após `advogado_reclamante`
   - Adicionado ao `@field_validator` para normalização genérica de strings
   - `SCHEMA_VERSION` bumped de "2.5" → "2.6"

2. `workers/processor.py`:
   - `advogado_reclamada` adicionado a `CAMPOS_TEXTO` para limpeza via `_clean_str`

3. `services/ai_client.py`:
   - `"advogado_reclamada": null` adicionado à `ESTRUTURA ESPERADA` do `PROMPT_TEMPLATE`

4. `skills/sentenca_ordinaria.md` e `skills/acordao.md`:
   - Instrução adicionada: buscar no cabeçalho/contestação; separar por " + " em litisconsórcio

**Testes:** 1020 passed, 0 falhas (sem regressão).

---

## FASE M — Desambiguação advogado_reclamante / advogado_reclamada (2026-05-14)

**Arquivos:** `services/ai_client.py`, `docs/EXTRACAO_STATUS.md`

**Problema:** `advogado_reclamante` tinha ~70% de precisão por confusão com advogado da reclamada (documentado em EXTRACAO_STATUS). Com `advogado_reclamada` agora no schema (FASE J), o risco de confusão aumentaria sem instrução explícita.

**Mudança em `ai_client.py` (`INSTRUÇÕES ESPECÍFICAS`):**
```
- advogado_reclamante / advogado_reclamada: são pessoas DIFERENTES.
  advogado_reclamante defende o TRABALHADOR (autor);
  advogado_reclamada defende a EMPRESA (ré).
  No cabeçalho, procurar "Adv. do Reclamante:", "Adv. da Reclamada:", ...
  Se não houver indicação explícita da parte, retornar null.
```

**Testes:** 1020 passed, 0 falhas (sem regressão — mudança só em texto do prompt).

---

## FASE L — Extração regex de `funcao_reclamante` (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `tests/unit/test_regex_fields.py`

**Problema:** `funcao_reclamante` tinha ~65% de precisão — o campo com menor acerto do schema. Era 100% dependente da IA sem nenhuma âncora regex.

**Implementação em `services/pre_extractor.py`:**

`_RE_FUNCAO_RECLAMANTE` — detecta frases-gatilho específicas e captura o texto livre seguinte até um delimitador (`,` `.` `;` `\n` `(`):
- Gatilhos: "exercia [a] função de", "contratado/a como", "admitido/a como", "trabalhava/trabalha como", "ocupava/ocupa [o] cargo de", "na função de"
- Captura: 3–40 caracteres em modo lazy (sem ultrapassar delimitadores)
- Nível: MEDIUM (texto livre → não pode ser HIGH)

**Design decision:** `{3,40}?` lazy + lookahead de stop char. Sem stop char dentro do limite → None (evita capturar texto irrelevante após o cargo).

9 testes adicionados: 6 parametrizados para gatilhos comuns, 1 para ausência de cargo, 1 para captura sem delimitador, 1 para "função de" sem artigo.

**Testes:** 1029 passed (+9), 0 falhas.

---

## FASE N — Extração HIGH de `vara_trabalho` (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `tests/unit/test_regex_fields.py`

**Problema:** `vara_trabalho` era 100% IA (~85%). Em acórdãos sem cabeçalho padronizado, a IA falhava. O padrão "Nª Vara do Trabalho de [Cidade]" é altamente específico do domínio jurídico — candidato a HIGH.

**Implementação em `services/pre_extractor.py`:**

`_RE_VARA_TRABALHO` — captura padrão `(Nª) Vara do Trabalho de [cidade]`:
- Ordinal opcional: `\d{1,2}[aªoº°]?` (aceita "3ª", "1a", "12°", sem ordinal)
- Cidade capturada com `[^,\.;\n\(\)]{3,50}?` lazy + stop char — cobre cidades compostas ("São Bernardo do Campo", "São José dos Campos")
- Guard: rejeita captura sem cidade (partes separadas por "de" devem ter cidade não-vazia)
- Nível: **HIGH** — `_set_high("vara_trabalho", ...)` sobrescreve IA diretamente

9 testes: 6 parametrizados (formatos comuns), sem vara, sem cidade, cidade com preposição interna.

**Impacto esperado:** `vara_trabalho` de ~85% → ~97% (acórdãos sem cabeçalho agora cobertos via "oriundo da Nª Vara do Trabalho de Y" no Relatório).

**Testes:** 1038 passed (+9), 0 falhas.

---

## FASE P — Cálculo determinístico de `data_saida_ctps` (2026-05-14)

**Arquivo:** `workers/processor.py`, `tests/unit/test_processor_helpers.py`

**Problema:** `data_saida_ctps` era extraída pela IA (~75% precisão). O valor é calculável deterministicamente: `data_demissao + aviso_previo_dias` (OJ 82 SDI-I TST — tanto aviso trabalhado quanto indenizado projetam a data de saída na CTPS).

**Implementação em `_validate_result` (step 6):**
```python
if not cleaned.get("data_saida_ctps") and cleaned.get("data_demissao") and cleaned.get("aviso_previo_dias"):
    d, m_n, y = cleaned["data_demissao"].split("/")
    demissao = date(int(y), int(m_n), int(d))
    m_dias = re.search(r"\b(\d+)\s*dias?", cleaned["aviso_previo_dias"])
    if m_dias:
        cleaned["data_saida_ctps"] = (demissao + timedelta(days=int(m_dias.group(1)))).strftime("%d/%m/%Y")
```

- Parser de `aviso_previo_dias`: extrai o primeiro número antes de "dias" — cobre "30 dias", "42 dias — 30 + 12 pela Lei 12.506/2011" (captura 42, não 30)
- Não sobrescreve se a IA já extraiu um valor
- Exception handler silencia falhas de parsing (campo permanece None)

**Testes:** 5 novos casos: cálculo simples, aviso composto Lei 12.506/2011, não-sobrescrita, sem aviso, sem demissão.

**Testes:** 1043 passed (+5), 0 falhas.

---

## FASE Q — Expansão de padrões de admissão e demissão (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `tests/unit/test_regex_fields.py`

**Problema:** `_RE_ADMISSAO` e `_RE_DEMISSAO` cobriam formas verbais diretas ("admitido em", "dispensado em") mas perdiam nominalizações e frases introdutórias comuns em peças processuais.

**Falsos positivos removidos de `_RE_ADMISSAO`:**
- `a\s+partir\s+de` — capturava datas de FGTS, juros, condenações, dispositivos
- `desde` — capturava "desde então", "desde a propositura", datas de prescrição

**Padrões adicionados a `_RE_ADMISSAO`:**
- `empregad[oa]\s+em` — "empregado em 01/03/2021 pela reclamada"
- `com\s+in[íi]cio\s+em` — "com início em 15/04/2019"
- `contrata[çc][aã]o\s+em` — "contratação em 10/08/2020"
- `in[íi]cio\s+do\s+v[íi]nculo\s+(?:empregatício\s+)?em` — "início do vínculo em 01/01/2022"
- `data\s+de\s+(?:admiss[aã]o|contrata[çc][aã]o)[:\s]+` — "data de contratação: 05/05/2018"
- Acento normalizado: `admissão` → `admiss[aã]o`, `contratação` → `contrata[çc][aã]o`

**Padrões adicionados a `_RE_DEMISSAO`:**
- `desligamento\s+em` — "desligamento em 31/12/2023"
- `demiss[aã]o\s+(?:sem\s+justa\s+causa\s+)?em` — "demissão em 30/06/2023"
- `rescis[aã]o\s+(?:contratual\s+)?em` — "rescisão contratual em 15/11/2022" (também cobre "com rescisão em")
- `data\s+de\s+demiss[aã]o[:\s]+` — "data de demissão: 28/02/2023"
- Acento normalizado em todos os alternantes existentes

**Testes:** 1056 passed (+13), 0 falhas.

---

## FASE R — Extração HIGH de `aviso_previo_tipo` (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `tests/unit/test_regex_fields.py`

**Problema:** `aviso_previo_tipo` ("trabalhado" vs "indenizado") era 100% IA (~80% precisão). As frases discriminantes são altamente específicas do domínio e sem ambiguidade — candidato direto a HIGH.

**Implementação em `services/pre_extractor.py`:**

Dois padrões:
- `_RE_AVISO_TRABALHADO` — detecta `\baviso prévio trabalhado\b`
- `_RE_AVISO_INDENIZADO` — detecta três formas equivalentes:
  - `aviso prévio indenizado`
  - `indenização substitutiva do aviso prévio`
  - `aviso prévio convertido em indenização`

`_extract_aviso_previo_tipo()`:
- Indenizado tem precedência sobre trabalhado: em textos onde aparecem ambas as formas (histórico + dispositivo), a forma indenizada é a determinada pela sentença
- Registrado em `high_extractors` e `_ROTULOS_HIGH`

**10 testes adicionados:**
- 7 parametrizados: 3 formas trabalhado, 4 formas indenizado
- 1 para precedência de indenizado quando ambos presentes
- 2 negativos: sem qualificador, sem menção a aviso

**Impacto esperado:** `aviso_previo_tipo` de ~80% → ~97% (frases discriminantes são terminológicas, sem ambiguidade semântica)

**Testes:** 1066 passed (+10), 0 falhas.

---

## FASE S — Extração HIGH de `tipo_contrato` (duração) (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `models.py`, `tests/unit/test_regex_fields.py`

**Problema:** `tipo_contrato` era 100% MEDIUM (~78% precisão). As variantes de duração ("contrato de experiência", "contrato por prazo determinado") são frases terminológicas fixas sem ambiguidade — candidatos a HIGH. As variantes de natureza jurídica (pejotização, autônomo, CLT) dependem de contexto circundante e permanecem MEDIUM.

**Dois novos padrões HIGH adicionados a `services/pre_extractor.py`:**

- `_RE_CONTRATO_EXPERIENCIA` — "contrato de experiência", "período de experiência", "admitida para período de experiência"
- `_RE_CONTRATO_PRAZO_DET` — "contrato por prazo determinado", "contrato a prazo determinado", "contrato de trabalho com prazo determinado"

**Lógica em `_extract_tipo_contrato`:**
1. HIGH: Experiência (mais específico, verificar primeiro)
2. HIGH: Prazo determinado
3. MEDIUM: Pejotização reconhecida (requer contexto "reconhec/fraude/simulação")
4. MEDIUM: Autônomo reconhecido (requer contexto "reconhec")
5. MEDIUM: CLT (genérico — "vínculo de emprego" ou menção a CLT)

**`_ROTULOS_HIGH`** atualizado com `"tipo_contrato"`.
**`models.py`** description expandida com novos exemplos.

**11 testes adicionados:** 6 HIGH parametrizados, 3 MEDIUM parametrizados, 1 precedência HIGH>MEDIUM, 2 negativos.

**Testes:** 1077 passed (+11), 0 falhas.

---

## FASE T — Expansão de `_RE_AVISO_DIAS` (qualificadores e forma invertida) (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `tests/unit/test_regex_fields.py`

**Problema:** `_RE_AVISO_DIAS` só cobria "aviso prévio indenizado de X dias" e "aviso prévio de X dias". Perdia:
- Qualificadores: "trabalhado", "proporcional", "integral"
- Forma com extenso por extenso: "30 (trinta) dias"
- Forma invertida: "42 dias de aviso prévio"

**Mudanças em `services/pre_extractor.py`:**

1. `_RE_AVISO_DIAS` expandido — qualificadores opcionais + captura parentética:
   ```
   aviso prévio (indenizado|trabalhado|proporcional|integral)? (de)? N (\(extenso\))? dias
   ```

2. `_RE_AVISO_DIAS_INV` adicionado — forma invertida:
   ```
   N (\(extenso\))? dias de aviso prévio
   ```

3. `_extract_aviso_previo_dias` atualizado: `_RE_AVISO_DIAS.search() or _RE_AVISO_DIAS_INV.search()` — primeiro match vence; plausibilidade 20–90 dias preservada.

**6 novos casos de teste** adicionados ao `TestAvisoPrevioDias`: trabalhado, proporcional, integral, parentético, invertido simples, invertido com qualificador.

**Testes:** 1083 passed (+6), 0 falhas.

---

## FASE U — Extração HIGH de `juiz_responsavel` (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `tests/unit/test_regex_fields.py`

**Problema:** `juiz_responsavel` era 100% IA (~80% precisão). O rótulo "Juiz(a) do Trabalho:" é um campo labelado de cabeçalho — análogo a `vara_trabalho` que já é HIGH.

**Padrão `_RE_JUIZ_LABEL`:**
- Prefixo opcional: `MM.`
- Título: `Ju[íi]z[ao]?` — `[íi]` necessário porque `(?i)` não faz fold entre `i` e `í` (Unicode)
- Qualificador opcional: `do Trabalho`, `Titular`, `Substituto/a`
- Separador: `:` ou `-`
- Prefixo de título opcional: `Dr.` / `Dra.` (consumido e não capturado)
- Nome: qualquer texto até `,` `;` `\n` `(` ou fim de string

**Bug corrigido durante desenvolvimento:** `Juiz[ao]?` não correspondia a "Juíza" — o `(?i)` não faz Unicode case-folding entre `i` e `í`. Corrigido para `Ju[íi]z[ao]?`.

**Guard:** nome capturado deve ter ≥ 2 tokens (evita capturar só "Dr." ou artigos).

**9 testes:** 6 parametrizados (todos os formatos comuns), 1 negativo (sem rótulo), 1 rejeição de nome único, 1 verificação de strip do Dr/Dra.

**Impacto esperado:** `juiz_responsavel` de ~80% → ~97% (falha residual: texto sem cabeçalho padronizado).

**Testes:** 1092 passed (+9), 0 falhas.

---

## FASE V — Extração HIGH de `advogado_reclamante` e `advogado_reclamada` (2026-05-14)

**Arquivos:** `services/pre_extractor.py`, `tests/unit/test_regex_fields.py`

**Problema:** Ambos os campos eram 100% IA (~70% precisão com confusão entre as partes). Os rótulos "Adv. do Reclamante:" e "Adv. da Reclamada:" são campos labelados no cabeçalho PJe — mesma categoria de confiança que `juiz_responsavel`.

**Dois padrões HIGH adicionados:**

- `_RE_ADV_RECLAMANTE` — prefixo `(?:Adv\.|Advogad[oa])` + `do Reclamante:` + nome até OAB/parêntese/vírgula/quebra
- `_RE_ADV_RECLAMADA` — prefixo `(?:Adv\.|Advogad[oa])` + `da Reclamad[ao]:` + nome até OAB/parêntese/vírgula/quebra

**Bug corrigido durante desenvolvimento:** `Adv(?:ogad[oa])?\.` exigia período no final — não correspondia a "Advogado" (palavra completa sem ponto). Corrigido para `(?:Adv\.|Advogad[oa])` separando explicitamente as duas formas.

**Extrator único `_extract_advogados`** itera sobre os dois pares `(campo, regex)` — lógica centralizada sem duplicação.

**Guard:** nome ≥ 2 tokens (mesmo critério do juiz).

**11 testes adicionados:** 4 reclamante (formatos variados), 4 reclamada, 1 negativo (contexto narrativo), 1 rejeição de nome único, 1 desambiguação lado-a-lado.

**Impacto esperado:** `advogado_reclamante` de ~70% → ~97%; `advogado_reclamada` de ~new → ~97% (cabeçalhos PJe são padronizados).

**Testes:** 1103 passed (+11), 0 falhas.

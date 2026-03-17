# Alterações feitas vs. documentação (README + docs/)

Este documento lista **apenas as alterações feitas no código** (configuração em nova máquina + preparação para Teste 1) e confirma se há risco de **regressão** ou **divergência** em relação ao que está descrito no README e na pasta `docs/`.

---

## Resumo executivo

- **Pipeline (10 passos)**: não foi alterado. Ordem, contratos e módulos são os mesmos descritos em `PIPELINE.md` e `README.md`.
- **Regras jurídicas**: nenhuma regra foi adicionada, removida ou alterada. Motor de regras, Shadow Rules e Knowledge Base seguem como documentados.
- **Estrutura (pastas, arquivos principais)**: inicialmente inalterada; em Março/2026 foi realizada uma refatoração para Arquitetura SaaS (API Gateway + roteadores) mantendo os contratos de entrada/saída.
- As mudanças feitas neste período incluem: **configuração de ambiente** (`.env`, Tesseract no Windows), **atualização do modelo Gemini** (2.0-flash deprecado → 2.5-flash), **migração de rotas para roteadores especializados** e **modernização parcial do frontend** (novo Dashboard e Laboratório em React).

---

## 1. config.py — carregamento do .env

**O que a documentação diz**
- README: *"config.py: Variáveis de ambiente (GEMINI_API_KEY, Firebase, MAX_FILE_SIZE_MB, SCHEMA_VERSION etc.)"*
- Nenhum doc exige como o `.env` deve ser carregado.

**O que foi alterado**
- Antes: `load_dotenv()` (carrega a partir do diretório de trabalho atual).
- Depois: `load_dotenv(Path(__file__).resolve().parent / ".env")` — carrega sempre `backend/.env`, independente de onde o processo foi iniciado.

**Regressão?** Não. Mesmas variáveis; comportamento mais previsível em nova máquina ou ao rodar da raiz do projeto.

---

## 2. services/sentence_finder.py — Tesseract no Windows

**O que a documentação diz**
- README / CODE_MAP: *"sentence_finder: extract_sentence_from_pdf; tipo de doc; OCR híbrido; bloco de decisão"*.
- Nenhum doc define onde deve estar o executável do Tesseract.

**O que foi alterado**
- Em Windows, se existir `C:\Program Files\Tesseract-OCR\tesseract.exe`, esse caminho é definido em `pytesseract.pytesseract.tesseract_cmd`.
- Objetivo: evitar `TesseractNotFoundError` quando o Tesseract não está no PATH.

**Regressão?** Não. Só afeta ambiente Windows; lógica de extração e de classificação de documento permanece a mesma.

---

## 3. services/ai_client.py — modelo Gemini

**O que a documentação diz**
- README / PIPELINE: *"IA: ai_client — Gemini (Flash → Pro), playbook, truncagem"* e *"cascata Flash → Pro"*.
- Nenhum doc fixa o nome exato do modelo (ex.: "gemini-2.0-flash").

**O que foi alterado**
- `MODELS_CASCADE`: primeiro modelo de `"gemini-2.0-flash"` para `"gemini-2.5-flash"` (2.0-flash está deprecado e retorna 404 para chaves novas).
- `CHARS_LIMIT`: adicionada entrada para `gemini-2.5-flash`; mantida `gemini-2.0-flash` para compatibilidade.
- `gerar_parcelas_parecer`: valor padrão de `model_name` de `"gemini-2.0-flash"` para `"gemini-2.5-flash"`.

**Regressão?** Não. Contrato continua: cascata Flash → Pro; mesma API e mesmo fluxo. Apenas o identificador do modelo foi atualizado para um que ainda está disponível na API.

---

## 4. test_connection.py (novo arquivo)

**O que a documentação diz**
- Nenhum doc menciona este script. É utilitário de diagnóstico.

**O que foi feito**
- Criado `backend/test_connection.py`: valida carregamento do `.env`, existência de `GEMINI_API_KEY` e uma chamada simples ao Gemini Flash (com fallback de modelos).

**Regressão?** Não. Não faz parte do pipeline nem dos contratos descritos em README/docs; não altera comportamento do extrator.

---

## 5. API Gateway e roteadores — transição do estado global para roteamento dinâmico

**O que a documentação diz**
- `SYSTEM_OVERVIEW.md` e `CODE_MAP.md` agora descrevem o `main.py` como **API Gateway**, sem regras de negócio, delegando para roteadores em `api/routers/`.
- Os domínios documentados são:
  - `extractor.py`: motor principal de upload, background tasks e WebSockets.
  - `lab.py`: rotas de laboratório / aprendizado.
  - `admin.py`: estatísticas, histórico e knowledge base.
  - `exports.py`: exportação de arquivos finais.

**O que foi alterado**
- Antes: o `main.py` concentrava rotas, estado em memória (_jobs, filas de WebSocket, etc.) e imports diretos de serviços.
- Depois: o `main.py` passou a apenas:
  - inicializar o `FastAPI`;
  - registrar middlewares;
  - incluir os roteadores (`app.include_router(...)`).
- O estado em memória e as rotas foram movidos para os arquivos de roteador correspondentes:
  - **Extrator**: controle de jobs, cache em memória, filas WebSocket e rotas `/upload`, `/status/{job_id}`, `/ws/{job_id}` migraram para `api/routers/extractor.py`.
  - **Laboratório**: rotas `/lab/*` migraram para `api/routers/lab.py`, mantendo contratos de entrada/saída.
  - **Admin/Stats/KB**: rotas `/api/stats`, `/api/historico/{user_id}`, `/api/knowledge-base`, `/api/admin/reset-contagem` migraram para `api/routers/admin.py`.
  - **Exports**: rotas de download de arquivos migraram para `api/routers/exports.py`.

**Regressão?** Não. Os caminhos finais das URLs e os contratos Pydantic foram preservados; apenas o local físico do código mudou (redução de estado global acoplado ao `main.py` e centralização em roteadores).

---

## 6. Multi-tenancy da Knowledge Base — Multiton em vez de Singleton

**O que a documentação diz**
- `CODE_MAP.md`, `AI_RULES.md` e `architecture.mdc` descrevem a `KnowledgeBase` como um serviço **Multi-tenant**, usando o padrão **Multiton**.
- Cada cliente deve ter o seu próprio ficheiro físico `knowledge_base_{tenant_id}.json`.

**O que foi alterado**
- Antes: `KnowledgeBase` se comportava como um singleton com um único ficheiro global de knowledge base.
- Depois:
  - foi introduzido um cache interno `_instances` indexado por `tenant_id`;
  - `__new__` e `__init__` passaram a receber `tenant_id` (default `"default"`), instanciando uma KB por tenant;
  - o caminho em disco (`self._path`) passou a ser calculado dinamicamente:
    - `knowledge_base.json` para o tenant `"default"`;
    - `knowledge_base_{tenant_id}.json` para demais tenants.
- As rotas de painel que usam knowledge base (`/api/knowledge-base`, `/api/stats`) passaram a instanciar `KnowledgeBase(tenant_id=user_id)` mantendo o mesmo contrato HTTP.

**Regressão?** Não. A semântica da KB foi mantida; o que mudou foi o isolamento físico por cliente. O tenant `"default"` preserva o comportamento anterior, garantindo compatibilidade com dados já existentes.

---

## 7. Frontend — estado atual (SPA React oficial)

**O que a documentação antiga dizia**
- README e docs mencionavam:
  - um frontend legado (`frontend/`) baseado em HTML/JS (index.html + js/app.js, render.js, lab.js + css/main.css);
  - um frontend novo (`frontend-new/`) em Vite + React + TypeScript, com Tailwind, React Query e Axios, ainda coexistindo com o legado.

**Situação atual**
- O frontend oficial **único** é a SPA React em `frontend/`:
  - `frontend/index.html` (entry, `#root`) + `src/main.tsx`;
  - `src/App.tsx` (rotas: `/`, `/extractor`, `/lab`);
  - `src/pages/Dashboard.tsx`, `Extractor.tsx`, `Laboratory.tsx`;
  - `src/components/layout/MainLayout.tsx`;
  - `src/hooks/useAnalyze.ts`, `src/services/api.ts`, `src/types/`.
- A pasta `frontend-new/` não existe mais como diretório separado; o código React foi consolidado em `frontend/src/`.
- O frontend HTML/JS legado (index.html + app.js + render.js + lab.js + main.css) foi descontinuado; referências a ele em docs devem ser tratadas como **históricas**.

**Impacto para manutenção**
- Qualquer alteração de UI deve ir para `frontend/src/` (páginas, componentes, hooks, serviços).
- Documentos que ainda falam em “frontend legado + frontend-new” precisam ser lidos com este contexto de consolidação; a fonte de verdade é:
  - `DEVELOPER.md` (§ 1 e § 3 — caminhos oficiais e consolidação),
  - `backend/docs/CODE_MAP.md` (§ Frontend),
  - `backend/docs/AI_NAVIGATION_LAYER.md` (§ 2.8, 2.9, 2.11, 2.12),
  - `backend/docs/CODE_INTELLIGENCE_MAP.md` (§ 7, § 8).

---

## 8. Laboratório — modo Flex-Analysis (Scanner Modular)

**O que a documentação diz**
- O laboratório aceita combinações opcionais de arquivos e o backend (`/lab/analisar`) já foi projetado para funcionar com campos ausentes.

**O que foi alterado**
- No `frontend-new/src/pages/Laboratory.tsx`:
  - o botão de análise passa a ser habilitado sempre que houver **pelo menos um arquivo** selecionado em qualquer card (Petição, Título Executivo, Parecer etc.);
  - o `FormData` de envio continua incluindo apenas os campos com arquivos anexados, sem serializar campos vazios;
  - a interface removeu rótulos de “obrigatório” dos cards, reforçando o conceito de **Scanner Modular**: o usuário pode analisar desde um único documento isolado até o conjunto completo de peças.

**Regressão?** Não. O backend já aceitava combinações parciais; a mudança apenas torna o frontend mais flexível e alinhado ao comportamento real da API, sem alterar contratos ou a lógica central de 10 passos.

---

## 9. Learning Engine — Passo 1: camada de persistência (learning_io)

**O que a documentação diz**
- O protocolo de refatoração modular do Laboratório prevê extrair a camada de persistência e I/O para um módulo dedicado, mantendo o `learning_engine.py` como facade.

**O que foi alterado**
- Criado `services/lab/__init__.py` e `services/lab/learning_io.py`.
- Movidas para `learning_io.py`: `preview_aprendizado`, `salvar_aprendizado`, `_salvar_rascunho_regra`, `_salvar_few_shot` (alias documental: `_salvar_insight_em_markdown`), `_registrar_log` (alias: `_registrar_no_log_de_aprendizado`). Caminhos de saída (`_SKILLS_DIR`, `_RULES_DIR`, `_LEARNING_LOG`) e constante exportada `LEARNING_LOG_PATH` ficam em `learning_io`.
- No `learning_engine.py`: removido o corpo dessas funções; mantido facade com `from services.lab import learning_io`, `preview_aprendizado = learning_io.preview_aprendizado`, `salvar_aprendizado = learning_io.salvar_aprendizado`, `_LEARNING_LOG = learning_io.LEARNING_LOG_PATH` (usado por `_registrar_log_enriquecido`).
- Imports `json`, `os`, `re`, `textwrap`, `datetime` permanecem no `learning_engine.py` (usados no restante do arquivo); em `learning_io.py` foram adicionados os necessários para as funções movidas. `hashlib` e `zipfile` não são usados pelas funções de persistência movidas; continuam apenas no `learning_engine.py`.

**Regressão?** Não. Contratos públicos (`preview_aprendizado`, `salvar_aprendizado`) e uso de `_LEARNING_LOG` em `_registrar_log_enriquecido` mantidos; chamadas externas (ex.: `api/routers/lab.py`, `main.py`) seguem importando de `learning_engine` sem alteração.

---

## 10. Learning Engine — Passo 2: limpeza e regex (extractors)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar regex e limpeza de texto em um módulo dedicado; `LegalRule._canonizar_verba` permanece acessível em `legal_engine/rule_base.py`.

**O que foi alterado**
- Criado `services/lab/extractors.py`. Movidas para lá: `regex_verbas`, `regex_indice`, `regex_juros`, `regex_divisor`, `liquidacao_from_text`; `extrair_fundamentos_juridicos`, `extrair_discrepancias_perita`; `remover_linha_autuacao`, `contexto_eh_autuacao` (e constantes `_RE_CONTEXTO_AUTUACAO`, `_RE_LINHA_DATA_AUTUACAO`); constantes e helpers de cabeçalho PJe: `CABECALHO_PJE_CHARS`, `_RE_TEXTO_2GRAU_FORA_CABECALHO`, `texto_apos_cabecalho_pje`, `tem_indicador_2grau_apos_cabecalho`.
- No `learning_engine.py`: removidos os corpos dessas funções e constantes; mantido facade com `from services.lab import extractors` e aliases `_regex_verbas`, `_liquidacao_from_text`, `_extrair_fundamentos_juridicos`, `_extrair_discrepancias_perita`, `_remover_linha_autuacao`, `_contexto_eh_autuacao`. `_classificar_tier_decisao` passou a usar `extractors.tem_indicador_2grau_apos_cabecalho(texto_primeiras_paginas)` em vez da lógica inline de cabeçalho PJe.
- Canonização de verbas: não alterada; continua em `LegalRule._canonizar_verba` (rule_base); `learning_engine` segue importando e usando onde necessário.

**Regressão?** Não. Comportamento de liquidação, manifestação, extração de data e classificação de tier inalterado; chamadas internas do `learning_engine` usam os mesmos nomes via facade. `PIPELINE.md` descreve os 10 passos do `processor.py`; o fluxo do Laboratório não é alterado por esta extração de módulo.

---

## 11. Learning Engine — Passo 3: Título Executivo e Tiers (titulo_executivo)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar a inteligência que define 1º Grau / TRT / TST e a fusão de múltiplos documentos (Título Executivo Complexo) em um módulo dedicado; regra "Tier diferente = ambos mantidos" e ignorar cabeçalho de 1000 chars conforme `AI_NAVIGATION_LAYER.md`.

**O que foi alterado**
- Criado `services/lab/titulo_executivo.py`. Movidas para lá: constantes de tier (`TIER_1GRAU_PELO_NOME`, `TIER_TRT_PELO_NOME`, `TIER_TST`, `TIER_TRT`, `TIER_ORDER`, `TIER_LABELS`), constantes de data (`MESES_NUM`, `FALLBACK_DATE`); funções `classificar_tier_decisao(filename, texto_primeiras_paginas?)`, `extrair_data_documento(texto)` e `extrair_titulo_executivo_multiplos(arquivos, contexto_amostragens?, *, extrair_processo, extrair_texto_arquivo, bloco_amostragens_perita)`. O módulo usa `extractors.remover_linha_autuacao`, `extractors.contexto_eh_autuacao`, `extractors.tem_indicador_2grau_apos_cabecalho`; não importa `learning_engine` (evita ciclo). A fusão multi-doc recebe os três callbacks injetados pelo `learning_engine`.
- No `learning_engine.py`: removidos os corpos e constantes das três funções e do bloco de título executivo; adicionado `from services.lab import titulo_executivo` e facades: `_classificar_tier_decisao`, `_extrair_data_documento` e `_extrair_titulo_executivo_multiplos` (esta chama `titulo_executivo.extrair_titulo_executivo_multiplos(..., extrair_processo=_extrair_processo, extrair_texto_arquivo=_extrair_texto_arquivo, bloco_amostragens_perita=_bloco_amostragens_perita)`). Removidos imports não usados (`hashlib`, `defaultdict`).

**Regressão?** Não. Contratos e comportamento (tier por nome, data sem Data da Autuação, tier diferente = ambos mantidos, cabeçalho 1000 chars ignorado) permanecem; apenas o local do código mudou. Chamadas ao lab e ao Card 3 seguem via `learning_engine` sem alteração de API.

---

## 12. Learning Engine — Passo 4: Discrepância Sentença vs. Cálculo (discrepancy)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar a lógica de confronto (Sentença vs. Cálculo) e os filtros de falsos-positivos em um módulo dedicado. Esta é a mudança mais importante no CODE_MAP: o "coração" do Laboratório. A canonização de verbas usa `LegalRule._canonizar_verba` (legal_engine/rule_base).

**O que foi alterado**
- Criado `services/lab/discrepancy.py`. Movidas para lá: `gerar_relatorio_discrepancia(dados_sentenca, dados_liquidacao, dados_manifestacao)` (comparação verbas deferidas vs. liquidação com canonização + substring + fuzzy; índice de correção; juros de mora; geração de discrepâncias e aprendizados); auxiliares internas `_campos_chave_sentenca`, `_sugerir_correcao_verba`, `_buscar_fundamento_para_verba`, `_extrair_aprendizados`; `verba_corresponde_na_liquidacao(verba_sentenca, verbas_liq_norm, verbas_liq_canon, threshold?)`; `canon_empresa_e_verba_esta(relatorio)`; `filtrar_falsos_positivos_verba_ausente(relatorio)`, `filtrar_logicas_verba_ausente_falsas(logicas, relatorio)`, `filtrar_aprendizados_verba_ausente_falsas(relatorio)`. O módulo importa `LegalRule` de `services.legal_engine.rule_base` e `rapidfuzz`; usa `RAPIDFUZZ_THRESHOLD` de config (ou 85).
- No `learning_engine.py`: removidos os corpos de todas essas funções e os helpers; adicionado `from services.lab import discrepancy` e facades que delegam a `discrepancy.*`. Removidos imports não usados (`rapidfuzz`, `_FUZZ_THRESHOLD`).

**Regressão?** Não. Contratos públicos (`gerar_relatorio_discrepancia`) e uso interno dos guardrails mantidos; chamadas externas (ex.: `api/routers/lab.py`) e fluxo do relatório inalterados. As três camadas de guardrail continuam a ser aplicadas na mesma ordem; a canonização segue usando `LegalRule._canonizar_verba` dentro de `discrepancy.py`.

---

## 13. Learning Engine — Passo 5: Duplo Style Transfer (style_transfer)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar a lógica que aprende como a perita escreve: extração de manifestação pericial, merge dos dados (Impugnação + Manifestação) e integração com `skills/manifestacao_style.md` (Duplo Style Transfer).

**O que foi alterado**
- Criado `services/lab/style_transfer.py`. Movidas para lá: `merge_dados_manifestacao(base, novo)`; `extrair_manifestacao_pericial(file_bytes, filename, *, extrair_texto_arquivo, chamar_gemini_para_codify, skills_dir)` (analisa peça com Gemini, extrai frases de impacto/padrões Ataque/Defesa/argumento vencedor, codifica padrões no KB, atualiza manifestacao_style.md); `atualizar_skill_manifestacao(skills_dir, dados, trecho_original, filename)`; helper interno `_codificar_padroes_ataque_defesa(dados)`. O módulo usa `extractors.extrair_fundamentos_juridicos` e `services.knowledge_base.KnowledgeBase`; não importa `learning_engine` (callbacks injetados).
- No `learning_engine.py`: removidos os corpos de `_merge_dados_manifestacao`, `_extrair_manifestacao_pericial`, `_codificar_padroes_ataque_defesa` e `_atualizar_skill_manifestacao`; adicionado `from services.lab import style_transfer` e facades que delegam a `style_transfer.merge_dados_manifestacao` e `style_transfer.extrair_manifestacao_pericial(..., extrair_texto_arquivo=_extrair_texto_arquivo, chamar_gemini_para_codify=_chamar_gemini_para_codify, skills_dir=_SKILLS_DIR)`.

**Regressão?** Não. Contratos e fluxo do Duplo Style Transfer (Card 6 + Card 8 → manifestacao_style.md e KB) mantidos; chamadas em `processar_sete_arquivos` seguem usando `_extrair_manifestacao_pericial` e `_merge_dados_manifestacao` sem alteração de assinatura.

---

## 14. Learning Engine — Passo 6: Self-Healing e Shadow Rules (self_healing)

**O que a documentação diz**
- O protocolo de refatoração modular prevê isolar a parte que gera novas regras Python automaticamente: codify_insight, processar_aprendizado_autonomo e _evaluate_shadow_rules. A integração com `services/knowledge_base.py` deve ser mantida via user_id (Multi-tenancy).

**O que foi alterado**
- Criado `services/lab/self_healing.py`. Movidas para lá: `codify_insight(aprendizado, numero_processo, conteudo_editado=None, *, rules_dir, skills_dir, learning_log_path, chamar_gemini_para_codify)` (consolida aprendizado em regra Python + skill + learning_log; usa `learning_io.preview_aprendizado` e helpers internos `_gerar_regra_python_gemini`, `_gerar_exemplo_skill_gemini`, `_registrar_log_enriquecido`); `processar_aprendizado_autonomo(relatorio, numero_processo, user_id=None, *, extrair_logica_correcao_gemini, filtrar_logicas_verba_ausente_falsas)` — cria `KnowledgeBase(tenant_id=user_id or "default")`, extrai hipóteses via callback, filtra falsos positivos, atualiza KB e chama `evaluate_shadow_rules`; `evaluate_shadow_rules(relatorio, kb=None, user_id=None)` (acerto/punição das regras shadow). Removidos de `learning_engine.py`: corpos de codify_insight, processar_aprendizado_autonomo, _evaluate_shadow_rules e dos helpers _gerar_regra_python_gemini, _gerar_exemplo_skill_gemini, _registrar_log_enriquecido; mantidos _chamar_gemini_para_codify (usado por style_transfer e injetado no codify_insight) e _extrair_logica_correcao_gemini (callback injetado no processar_aprendizado_autonomo). Facades em learning_engine delegam a `self_healing.*`; `processar_aprendizado_autonomo` ganhou parâmetro opcional `user_id` para Multi-tenancy.

**Regressão?** Não. Contratos públicos (`codify_insight`, `processar_aprendizado_autonomo`) e chamadas de `api/routers/lab.py` e `processar_sete_arquivos` mantidos. KB continua sendo usado com `tenant_id=user_id or "default"` dentro de self_healing. main.py e processor.py não importam learning_engine diretamente para essas funções; lab router e processar_sete_arquivos seguem funcionando.

---

## Histórico de Correções Técnicas

- **Exportador Excel (`services/excel_exporter.py`) — erro MergedCell**  
  A função `_auto_ajustar_colunas` iterava sobre as células de cada coluna e usava `cell.column_letter` para definir a largura. Em planilhas com células mescladas (ex.: bloco do Memorial na aba "Resumo e Parecer"), o openpyxl devolve instâncias de `MergedCell`, que não possuem o atributo `column_letter`, gerando `AttributeError`. Correção aplicada: import de `MergedCell`; para cada coluna, localização de uma célula "mestre" não mesclada; uso dessa célula para obter `column` e `column_letter` e aplicar o ajuste; `try/except AttributeError` ao acessar `column_letter`, pulando colunas que não permitem o ajuste (evitando falha silenciosamente).

- **Exportador Excel — validação de campos nulos**  
  Para estabilizar o endpoint `/api/export/excel` quando o objeto ProcessoTrabalhista vem com campos ausentes: (1) confirmação de que todos os acessos a `dados` usam `.get()`; (2) quando `salario_base` é `None` ou string vazia, a célula correspondente passa a exibir o texto *"Não identificado na sentença"*; (3) a lista de verbas é obtida com `dados.get("verbas_deferidas") or []`, em seguida garantida como lista com `if not isinstance(verbas, list): verbas = []` e o loop que preenche a aba "Verbas Deferidas" só é executado com `if verbas:`, evitando erros de iteração quando o valor não é lista ou está vazio.

---

## O que NÃO foi alterado (conferido)

- **workers/processor.py**: nenhuma alteração. Os 10 passos, ordem e chamadas estão como em `PIPELINE.md`.
- **legal_engine/**: nenhuma alteração em regras, engine, rule_registry ou dynamic_rule_loader.
- **models.py**: não alterado.
- **learning_engine.py**: contrato público inalterado; persistência a `services.lab.learning_io`; regex a `services.lab.extractors`; confronto e guardrails a `services.lab.discrepancy`; título executivo/tiers a `services.lab.titulo_executivo`; Style Transfer a `services.lab.style_transfer`; Self-Healing e codify a `services.lab.self_healing` (facades). learning_engine permanece como facade orquestrador (apenas imports e delegação).
- **knowledge_base.py**: apenas migração de Singleton para Multiton por `tenant_id`, preservando lógica de pontuação e busca.
- **main.py**: deixou de abrigar regras de negócio; hoje é API Gateway puro incluindo roteadores.
- **Skills (.md)**: não alteradas semanticamente; apenas sincronização de regras de navegação para refletir a nova arquitetura.
- **Frontend legado (`frontend/`)**: permanece funcional, com pequenos ajustes de URLs para `/api/*` onde documentado.
- **Contrato de `process_lawsuit_pdf`**: entrada e retorno (status, data, alertas_juridicos, regras_aplicadas, etc.) permanecem como documentados.

---

## Conclusão

- O código que você trouxe do GitHub **foi modificado** nos pontos acima (config, sentence_finder, ai_client, novo script de teste, arquitetura de roteadores, multi-tenancy da Knowledge Base e início do frontend React).
- Nenhuma **regra jurídica**, **pipeline de 10 passos** ou **contrato HTTP** documentado no README e em `docs/` foi alterado de forma que cause regressão ou comportamento diferente do desenhado.
- As mudanças principais são:
  - **ambiente** (`.env`, Tesseract);
  - **disponibilidade de API** (modelo Gemini);
  - **arquitetura SaaS** (API Gateway + roteadores, Multiton para KB);
  - **lógica de upload multi-card no cliente** (estado por card e suporte a múltiplos arquivos no Título Executivo).
  Todas foram implementadas preservando compatibilidade com os fluxos já descritos na documentação.

Se quiser reverter apenas as alterações de “nova máquina”, basta desfazer as mudanças em `config.py`, `sentence_finder.py` e `ai_client.py` (e opcionalmente remover `test_connection.py`). O restante do repositório está alinhado com a documentação.

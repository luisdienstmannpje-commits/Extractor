# PJeCalc Smart Extractor — Backend

## O que é

O **PJeCalc Smart Extractor** automatiza a leitura de sentenças e acórdãos trabalhistas em PDF. Ele extrai verbas deferidas, datas contratuais, parâmetros de cálculo e índices jurídicos, e produz:

- **JSON** estruturado (45+ campos)
- **Excel** com abas estruturadas
- **Memória de cálculo** auditável (JSON por job)
- **Arquivo .pjc** compatível com PJeCalc 2.14.0

Objetivo: reduzir a leitura manual de sentenças de horas para segundos.

---

## Estrutura do projeto

```
backend/
├── main.py                    # API FastAPI (upload PDF, jobs, WebSocket, export PJC/Excel)
├── config.py                  # Configuração (Gemini, Firebase, limites, SCHEMA_VERSION)
├── models.py                  # Pydantic: ProcessoTrabalhista, VerbaDeferida, validadores
├── workers/
│   └── processor.py           # Pipeline de extração (passos 1–10)
├── services/
│   ├── legal_validator.py     # Interface de validação → delega ao Legal Rule Engine
│   ├── ai_client.py           # Chamada Gemini (cascata Flash → Pro), truncagem, prompt
│   ├── sentence_finder.py    # Extração de texto do PDF (OCR híbrido), classificação doc
│   ├── text_processor.py      # Normalização de texto, find_section_hybrid (dispositivo etc.)
│   ├── pre_extractor.py       # Pré-extração determinística (regex/campos HIGH/MEDIUM)
│   ├── normalizer.py          # Normalização de chaves/valores (verbas, listas)
│   ├── sentence_understanding.py  # Pós-processamento de texto da IA (verbas, reflexos, períodos)
│   ├── calculation_parameters.py   # Geração de parâmetros para cálculo (divisor, FGTS, honorários)
│   ├── explanation_engine.py  # Explicações jurídicas por regra (templates, sem LLM)
│   ├── pjc_template_patcher.py     # Patch do XML .pjc (datas, FGTS, processo, parâmetros)
│   ├── database.py           # SQLite: créditos, cache, extrações, jobs
│   ├── schema_version_guard.py     # Guarda de versão do schema (invalidar cache)
│   ├── verba_deduplicator.py  # Deduplicação de verbas (assinatura nome+período)
│   ├── learning_engine.py     # Laboratório: 8 arquivos (linha do tempo), cross-reference, style transfer, manifestação pericial, codify_insight, Self-Healing
│   ├── learning_skill_loader.py  # Carrega playbook .md para o lab
│   ├── knowledge_base.py      # Banco de Conhecimento das regras dinâmicas (confidence_score, status shadow/active/deleted)
│   ├── legal_engine/dynamic_rule_loader.py  # Carrega/aplica regras dinâmicas (ativas + shadow) a partir do Knowledge Base
│   ├── legal_engine/          # Motor de regras jurídicas
│   │   ├── rule_base.py       # ContextoJuridico, VerbaContexto, LegalRule (base)
│   │   ├── engine.py          # LegalRuleEngine: executar(dados) → alertas, regras_aplicadas
│   │   ├── rule_registry.py   # Descoberta de regras (rules/ + jurisprudencia/)
│   │   └── rules/             # Regras em arquivos .py (uma classe por arquivo)
│   └── jurisprudencia/       # Regras legadas (STF, TST, CLT, consistência)
│       ├── stf/adc_58.py
│       ├── sumulas/, orientacoes/, clt/, consistencia/
├── memoria_calculo/
│   └── generator.py          # Geração de memoria_{job_id}.json (trilha de auditoria)
├── tests/                    # Testes unitários e de integração
│   ├── jurisprudencia/       # Testes do motor de regras (uma pasta por regra/teste)
│   ├── test_normalizer.py, test_sentence_understanding.py, test_calculation_parameters.py
│   └── test_explanation_engine.py
├── skills/                   # Playbooks .md para a IA (sentença, acórdão, liquidação etc.)
│   ├── parecer_pericial.md    # Manual de redação do Parecer Técnico — Padrão Ouro (regras + exemplos few-shot)
│   ├── amostragem_style.md    # Guia de estilo da perita — acumulado automaticamente pelo Lab (Style Transfer)
│   └── manifestacao_style.md  # Retórica de combate — frases de impacto, súmulas estratégicas, padrões Ataque/Defesa; acumulado automaticamente pela Manifestação Pericial
├── _archive/                 # Código legado (referência)
│   ├── legacy/legal_validator_pre_engine.py
│   └── pjc/
├── REFATORACAO_VALIDADOR.md  # Nota sobre migração validador → engine
```

---

## Documentação para desenvolvimento assistido por IA

Para agentes (humanos ou IA) que vão **ler ou alterar código**, use sempre os documentos em `backend/docs/` como primeira camada:

- `docs/AI_NAVIGATION_LAYER.md` — **ponto de entrada** para IA: roteiros por tipo de tarefa (pipeline, regras, IA, export, modelo, frontend) e invariantes que não podem ser quebrados.
- `docs/SYSTEM_OVERVIEW.md` — visão macro do sistema (produto, componentes, fluxo).
- `docs/PIPELINE.md` — descrição detalhada dos 10 passos do pipeline e seus contratos.
- `docs/CODE_MAP.md` — mapa rápido arquivo → responsabilidade, e índice por domínio (FGTS, datas, regras, IA, etc.).
- `docs/CODE_INTELLIGENCE_MAP.md` — mapa de **inteligência de código por domínio** (pipeline, Legal Rule Engine, exportadores, modelos/cache, frontend, testes).
- `docs/AI_RULES.md` — regras para desenvolvimento assistido por IA (o que nunca fazer, onde ler primeiro, como reduzir consumo de tokens).

Recomendação:

- Para qualquer tarefa: comece em `docs/AI_NAVIGATION_LAYER.md` e siga o roteiro apropriado.
- Use `CODE_MAP` e `CODE_INTELLIGENCE_MAP` para localizar arquivos antes de abrir grandes blocos de código.
- Sempre respeite as regras de `AI_RULES.md` antes de modificar código.

---

## Pipeline de extração (workers/processor.py)

Fluxo em 10 passos:

| # | Etapa | Módulo / Ação |
|---|--------|----------------|
| 1 | Freemium | Verificação de créditos (database) |
| 2 | Cache | Busca por hash do PDF; se qualidade OK, retorno imediato |
| 3 | Extração de texto | sentence_finder: detecta tipo (sentença/acórdão/etc.), extrai bloco relevante, OCR se necessário |
| 4 | Playbook | Carrega skill .md conforme tipo de documento |
| 5 | IA | ai_client: Gemini (Flash → Pro fallback), playbook + anchor (pre_extractor) |
| 6 | Pós-IA | _validate_result: limpeza de strings, booleanos, listas; derivações (jornada, divisor_horas, prescrição etc.) |
| 6b | Deduplicação | deduplicar_verbas (jurisprudencia/consistencia) |
| 7 | Pydantic | ProcessoTrabalhista(**dados_limpos) |
| 8 | Validação jurídica | validar_dados (legal_validator → engine) + LegalRuleEngine.executar + **regras dinâmicas Self-Healing** + gerar_explicacoes |
| 9 | Persistência | Cache (se qualidade OK), save_extraction, deduct_credit |
| 10 | Memória de cálculo | memoria_calculo.generator: memoria_{job_id}.json |

---

## Motor de regras jurídicas (Legal Rule Engine)

A validação é feita **exclusivamente** pelo Legal Rule Engine. `legal_validator.validar_dados()` e `validar_dados_completo()` delegam ao engine.

- **Entrada**: `dados` (dict com campos do ProcessoTrabalhista).
- **Saída**: `alertas` (list[str] `[NIVEL] mensagem`), `regras_aplicadas` (IDs), `memorial_juridico` (list[dict]).

### Hierarquia de prioridade (rule_base.py)

| Prioridade | Nível |
|------------|--------|
| 10 | STF (ADC 58 etc.) |
| 20 | TST Súmulas |
| 30 | TST OJs |
| 40 | CLT / legislação federal |
| 50 | Consistência |

### Regras em services/legal_engine/rules/

| Arquivo | Regra | Base / Função |
|---------|--------|----------------|
| reflexos_proibidos.py | ReflexosProibidosRule | OJ 394 TST; DSR/multas/danos não refletem em certas verbas |
| bis_in_idem.py | BisInIdemReflexosRule | Verba não pode refletir em si mesma |
| integracao_sem_reflexos.py | IntegracaoSemReflexosRule | Verba com integracao_salarial=True deve ter reflexos |
| dano_moral_em_verbas.py | DanoMoralEmVerbasRule | Dano moral não deve estar em verbas_deferidas |
| consistencia_datas.py | ConsistenciaDatasRule | Ordem lógica das datas (admissão, demissão, sentença, ajuizamento) |
| salario_base_minimo.py | SalarioBaseMinimoRule | Salário > 0 e ≥ mínimo vigente |
| aviso_previo_dias.py | AvisoPrevioDiasRule | Dias entre 30 e 90 (art. 487 CLT, Lei 12.506) |
| aviso_previo_sem_justa_causa.py | AvisoPrevioSemJustaCausaRule | Dispensa sem justa causa → aviso deve constar |
| multa_477_valor.py | Multa477ValorRule | Multa art. 477 ≈ 1 salário (tolerância 5%) |
| verbas_duplicadas.py | VerbasDuplicadasRule | Mesmo nome canônico + período = duplicata |
| he_reflexo_dsr.py | HeReflexoDsrRule | Súm. 264: HE reflete em DSR |
| fgts_aviso_previo.py | FgtsAvisoPrevioRule | FGTS sobre aviso prévio |
| fgts_ferias_indenizadas.py | FgtsFeriasIndenizadasRule | FGTS não incide férias indenizadas (OJ 195) |
| fgts_multa_40_ap_indenizado.py | FgtsMulta40ApIndenizadoRule | OJ 42: multa 40% não incide AP indenizado |
| honorarios_advocaticios.py | HonorariosAdvocaticiosRule | Art. 791-A CLT (5%–15%) |
| multa_467.py, multa_477.py | Multa467Rule, Multa477Rule | Arts. 467 e 477 CLT |
| aviso_previo_proporcional.py | AvisoPrevioProporcionaRule | Lei 12.506 (aviso proporcional) |
| dsr_bis_in_idem.py | DsrBisInIdemRule | DSR bis in idem |
| base_calculo_art_457.py | BaseCalculoArt457Rule | Consistência: lembrete de base de cálculo global (art. 457 CLT) para verbas integráveis |
| deducao_autorizada.py | DeducaoAutorizadaRule | Proteção financeira: alerta quando há dedução/compensação autorizada pelo juiz |

### Regras em services/jurisprudencia/

- **stf/adc_58.py**: ADC58CorrecaoMonetaria — IPCA-E + SELIC.
- **sumulas/**: sumula_264, sumula_305, sumula_91.
- **orientacoes/**: oj_42, oj_195, oj_394.
- **clt/**: art_791a, lei_12506, art_477a, art_223g, art_58_itinere.
- **consistencia/**: datas (CronologiaDatas), salario, verbas (BisInIdem), verba_deduplicator, numero_cnj_validator.

O **rule_registry** varre `legal_engine/rules/` e `jurisprudencia/` e instancia todas as subclasses de `LegalRule` com `id` definido.

---

## Laboratório de Aprendizado da Perita

O **Laboratório** permite à perita treinar o sistema com a visão completa da **Linha do Tempo da Fraude Trabalhista** (até 8 arquivos). Recebe um relatório de discrepância enriquecido e pode salvar aprendizados como **regras** ou **exemplos** em skills. Nenhum arquivo binário é persistido.

### Upload — 8 campos — Tríade de Ouro Expandida

> O botão "Analisar" fica sempre liberado. **Tríade de Ouro Expandida** (máxima inteligência): Amostragem + Processo + Cálculo .PJC + **Manifestação**. Obrigatórios mínimos: Processo + Liquidação + Parecer.

| # | Campo | Tipo | Status | Função |
|---|-------|------|--------|--------|
| 1 | `amostragem_pdf` | PDF | opcional | Holerites/ponto → extrai tese vencedora + irregularidades via Gemini |
| 2 | `amostragem_word` | DOC/DOCX | opcional | Petição Word → **Style Transfer** → acumula em `skills/amostragem_style.md` |
| 3 | `processo` | PDF/DOC/DOCX | recomendado | Sentença/decisão — o que o juiz deferiu |
| 4 | `liquidacao` | PDF/DOC/DOCX | recomendado | Cálculo da empresa — onde errou |
| 5 | `parecer` | PDF/DOC/DOCX | recomendado | Parecer da perita — como corrigiu |
| 6 | `impugnacao` | PDF/DOC/DOCX | opcional | Contestação da empresa |
| 7 | `calculo_pjc` | PDF/.PJC/.XML | opcional | Parâmetros PJe-Calc para auditoria matemática |
| 8 | `manifestacao` | PDF/DOC/DOCX | opcional | **Petição de Resposta** — retórica de combate, padrões Ataque/Defesa, súmulas → acumula em `skills/manifestacao_style.md` |

### Fluxo

analisar → relatório enriquecido (linha do tempo + `triade_pericial` com nós Amostragem/Processo/PJC/Manifestação) → Resultado 1 (verde=tese/roxo=estilo/azul=sentença) → Resultado 2 (divergências) → Resultado 3 (regras preditivas + fundamentos) → Resultado 4 (salvar) → Pré-visualizar (modal editável) → Confirmar e Salvar (log + regra + playbook).

### Endpoints (`/lab/...`)

- `POST /lab/analisar` — FormData 8 campos; chama `processar_sete_arquivos`; retorna relatório enriquecido.
- `POST /lab/preview` — `{aprendizados:[...]}` → previews sem gravar.
- `POST /lab/salvar` — `{aprendizado, numero_processo, conteudo_editado?}` → `codify_insight`.
- `GET  /lab/historico` — lê `learning_log.jsonl`, retorna últimos aprendizados.
- `GET  /lab/knowledge-base` — inspeciona o Knowledge Base (`status=all|active|shadow|deleted`).
- `DELETE /lab/knowledge-base/{rule_id}` — exclui regra dinâmica manualmente.

### Módulos

- `learning_engine.py`: `processar_sete_arquivos` (entrada principal — 8 arquivos), `processar_cinco_arquivos` (compat.), `_extrair_amostragem_pdf/word`, `_atualizar_skill_amostragem`, `_extrair_manifestacao_pericial`, `_codificar_padroes_ataque_defesa`, `_atualizar_skill_manifestacao`, `_gerar_regras_preditivas_amostragem` + Self-Healing Rule Engine.
- `skills/amostragem_style.md`: acumula padrões de estilo (vocab, expressões, estrutura, tom) de cada Amostragem Word. Usar no system prompt de pareceres.
- `skills/manifestacao_style.md`: acumula retórica de combate (frases de impacto, súmulas estratégicas, padrões Ataque/Defesa) de cada Manifestação Pericial. Grow automático. Usar ao gerar futuras manifestações.
- Frontend: `lab.js` (8 LAB_CAMPOS, formKey; Conclusão da Tríade com 4 nós em grid 2×2), `index.html`, `main.css`.

### Self-Healing Rule Engine (aprendizado autônomo de regras)

O Laboratório também alimenta um **motor de regras auto-ajustável** que aprende hipóteses de regra observando as discrepâncias e os pareceres futuros, sem exigir aprovação manual de código:

- `services/learning_engine.py`:
  - `_extrair_logica_correcao_gemini(relatorio)` — Gemini recebe o relatório do lab e devolve **somente JSON estruturado** com hipóteses de regra (`descricao`, `condicao`, `acao`, `base_legal`), sem gerar código Python diretamente.
  - `processar_aprendizado_autonomo(relatorio, numero_processo)` — para cada hipótese, consulta o Knowledge Base:
    - se já existe uma lógica similar → incrementa `confidence_score` e adiciona o processo em `casos_vistos`;
    - se não existe → cria entrada nova com `confidence_score = 1` e `status = "shadow"`.
  - `_evaluate_shadow_rules(relatorio, kb)` — compara as regras `shadow` com as discrepâncias reais (parecer final):
    - **acerto**: a regra previu um problema que realmente apareceu → `confidence_score += 1`;
    - **punição**: a regra previu um problema que **não** apareceu → `confidence_score -= 1`.
    - `status` muda automaticamente:
      - `shadow` → `active` quando `confidence_score >= 3`;
      - `shadow` → `deleted` quando `confidence_score <= -1`.

- `services/knowledge_base.py`:
  - Armazena todas as regras dinâmicas em `knowledge_base.json`.
  - Campos principais: `rule_id`, `descricao`, `condicao`, `acao`, `base_legal`, `confidence_score`, `status`, `casos_vistos`, `acertos`, `punicoes`, `created_at`, `updated_at`.
  - Fornece consultas (`get_regras_ativas`, `get_regras_shadow`, `stats`) e operações de ciclo de vida (`adicionar_ou_incrementar`, `marcar_acerto`, `marcar_punicao`, `decrementar`).

- `services/legal_engine/dynamic_rule_loader.py`:
  - Define `DynamicLegalRule(LegalRule)` que lê uma entrada do Knowledge Base e implementa a condição/ação da regra no padrão do Legal Rule Engine.
  - Tipos de condição suportados: `verba_ausente`, `verba_presente`, `indice_ausente`, `campo_ausente`, `campo_diferente`.
  - `carregar_regras_ativas()` — instancia apenas as regras com `status == "active"` para o pipeline principal (geram alertas reais).
  - `executar_shadow_pipeline(dados)` — executa apenas as regras `shadow` em modo fantasma, sem escrever em `alertas_juridicos`; usado para coletar métricas (acertos/erros) e ajustar `confidence_score`.

- `backend/workers/processor.py`:
  - No passo 8, além do Legal Rule Engine estático, injeta dinamicamente:
    - **Regras ativas** do KB (via `carregar_regras_ativas` + `LegalRuleEngine`) — seus alertas entram em `alertas_juridicos` normalmente.
    - **Shadow Mode** (via `executar_shadow_pipeline`) — executa regras em background apenas para alimentar o sistema de confiança/punição, sem poluir a interface do usuário.

Resultado: o sistema **cria, testa, ativa e descarta** regras jurídicas de forma autônoma, observando apenas o comportamento empírico dos documentos do laboratório e dos pareceres, sem depender de revisão manual de código Python.
---

## Frontend (site)

O site está em `frontend/` (relativo à raiz do repositório smart-extractor). Layout **SaaS profissional**:

- **index.html**: estrutura da aplicação; **Tailwind CSS** (CDN) para layout: sidebar fixa (nav Extrator / Laboratório / **Meus Processos** / **Estatísticas**), header fixo com título dinâmico, créditos e avatar; quatro painéis de conteúdo (`#view-extrator`, `#view-lab`, `#view-historico`, `#view-estatisticas`). Script inline de troca de view (localStorage). Todos os IDs e classes usados por `app.js`, `render.js` e `lab.js` são preservados.
- **css/main.css**: estilos dos **componentes dinâmicos** (seções, campos, verbas, alertas, modal do lab) gerados por `render.js` e `lab.js`. Não contém layout estrutural da página (sidebar/header); isso fica no Tailwind em `index.html`.
- **js/app.js**: upload de PDF, polling `/status/{job_id}`, exibição de status, export PJC/Excel, créditos, auditoria .PJC; **histórico** (`carregarHistorico`, `renderizarHistorico`, `filtrarHistorico` — busca em tempo real por nº processo / reclamante / reclamada); **Dashboard de Estatísticas** (`carregarEstatisticas`, `iniciarPollingEstatisticas` — polling a cada 5 s só quando a aba Estatísticas está visível; animação `.kpi-updated` quando um KPI muda).
- **js/render.js**: montagem do HTML dos dados extraídos (resumo, seções, verbas, alertas, fundamentação, parecer técnico); helpers `val`, `vv`, `statusClass`, `renderResultado`, etc.
- **js/lab.js**: Laboratório com **8 campos de upload** (LAB_CAMPOS + formKey explícito); `/lab/analisar` (processar_sete_arquivos); exibição em linha do tempo (Resultado 1: 3 fases visuais; Conclusão da Tríade de Ouro Expandida: grid 2×2 com nós Amostragem / Processo / .PJC / Manifestação; Resultado 3: regras preditivas no topo); modal pré-visualização editável; `/lab/preview` e `/lab/salvar`; após salvar, toast `_labToastEstatisticas()` sugere a aba Estatísticas.

**Aba "Meus Processos" (Histórico)**: painel `#view-historico` carregado automaticamente ao entrar na aba. Consome `GET /historico/{user_id}` (endpoint em `main.py`, fonte `database.get_user_history`). Exibe cards com tipo de documento, nº do processo, reclamante, reclamada, data e model usado, com botões de download direto (.PJC e Excel). A barra de busca (`#search-historico`) filtra em tempo real o cache local `_historicoDados` por nº processo, reclamante ou reclamada (sem nova requisição ao servidor).

**Dashboard de Estatísticas (reativo)**: painel `#view-estatisticas` exibe KPIs do aprendizado (processos analisados, regras ativas/shadow, omissões) e listas (últimas regras, top verbas com divergências). Dados vêm de `GET /api/stats` (main.py): lê `knowledge_base.json` + `database.get_total_extractions()`; retorna também `eficiencia_motor` (acertos/(acertos+punicoes) em % ou null). O frontend faz **polling a cada 5 s** apenas quando essa aba está visível (`view-estatisticas.style.display !== 'none'`); ao detectar mudança de valor, aplica animação de brilho verde (`.kpi-updated`) nos números. Ao salvar aprendizado no Laboratório, um toast orienta o usuário a ver a evolução na aba Estatísticas. Autocorreção (regras shadow punidas/deletadas) reflete imediatamente nos contadores na próxima leitura do endpoint.

Ao alterar o frontend: manter os IDs e as classes que o JS usa (ex.: `#resultado`, `.show`, `.lab-section.open`, `.btn-pjc.show`, `#view-estatisticas`, `.kpi-updated`).

---

## Função dos arquivos principais

### Raiz e configuração

- **main.py**: FastAPI; endpoints de upload, status, WebSocket, download Excel/PJC; endpoints do Laboratório (`/lab/analisar`, `/lab/preview`, `/lab/salvar`, `/lab/historico`, `/lab/knowledge-base`); **GET /api/stats** — dashboard de estatísticas (processos_analisados, regras_oficiais_ativas, regras_em_teste_shadow, omissoes_detectadas, eficiencia_motor, ultimas_regras, top_verbas_divergencias); gestão de jobs em memória + SQLite; timeout 5 min.
- **config.py**: Variáveis de ambiente (GEMINI_API_KEY, Firebase, MAX_FILE_SIZE_MB, SCHEMA_VERSION etc.).
- **models.py**: `ProcessoTrabalhista`, `VerbaDeferida` (Pydantic); validadores de normalização; `SCHEMA_VERSION` para cache.

### Workers

- **processor.py**: `process_lawsuit_pdf(user_id, file_bytes, job_id)` — orquestra cache, sentence_finder, playbook, IA, limpeza, dedup, validação Pydantic, legal_validator + engine, explanation_engine, memoria_calculo; retorna `data`, `alertas_juridicos`, `regras_aplicadas`, `explicacoes`. O JSON final agora inclui também `parecer_texto` (parecer completo no Padrão Ouro, texto simples pronto para Word/Excel), `parecer_parcelas_ia` (bloco da seção I gerado por IA) e `parecer_model_used`.

### Services — extração e texto

- **sentence_finder.py**: `extract_sentence_from_pdf(file_bytes)` → (texto, doc_type); extração por página, OCR híbrido, classificação do tipo de documento, recorte do bloco de decisão.
- **text_processor.py**: `normalize_text`, `find_section_hybrid` (busca seções como dispositivo).
- **pre_extractor.py**: `pre_extract(texto)` — extração determinística (regex/campos HIGH/MEDIUM); `build_anchor_section` para o prompt.
- **ai_client.py**: `extract_data_with_gemini(texto, playbook, anchor_section)` — cascata Gemini Flash → Pro, truncagem, montagem de prompt, parse da resposta. `gerar_parcelas_parecer(verbas, dados, skill_parecer)` — chama Gemini para preencher o slot de texto da seção I do parecer técnico seguindo o estilo de `skills/parecer_pericial.md`; retorna plain text sem Markdown.
- **normalizer.py**: `normalizar`, `normalizar_lista`, `eh_chave_valida`, `listar_variacoes` (chaves/valores padronizados).
- **sentence_understanding.py**: Funções auxiliares para interpretar texto da IA (`extrair_verbas_deferidas`, `extrair_reflexos`, `interpretar_decisao` etc.).

### Services — validação e regras

- **legal_validator.py**: `validar_dados(dados)` → list[str] alertas; `validar_dados_completo(dados)` → dict com alertas, regras_aplicadas, memorial_juridico. Ambos delegam ao Legal Rule Engine.
- **legal_engine/rule_base.py**: `ContextoJuridico`, `VerbaContexto` (Pydantic); `LegalRule` (classe abstrata com `aplicar`, `_alerta`, `_registrar`, `_canonizar_verba`).
- **legal_engine/engine.py**: `LegalRuleEngine(rules)`; `executar(dados)` → converte dict em ContextoJuridico, aplica regras por prioridade, retorna alertas em string, regras_aplicadas, memorial.
- **legal_engine/rule_registry.py**: `carregar_todas_as_regras()` — descobre módulos em rules/ e jurisprudencia/, instancia regras, evita ID duplicado.
- **legal_engine/dynamic_rule_loader.py**: `DynamicLegalRule` + `carregar_regras_ativas()` + `executar_shadow_pipeline(dados)` — lê o Knowledge Base e aplica regras dinâmicas: status `"active"` gera alertas reais; status `"shadow"` roda em background apenas para métricas (Shadow Mode).

### Services — cálculo e exportação

- **calculation_parameters.py**: `gerar_parametros(dados_extracao)` — período, divisor, jornada, reflexos, índices, FGTS, INSS, honorários (estrutura para PJC/Excel).
- **explanation_engine.py**: `gerar_explicacoes(verbas, memorial_juridico)` — templates jurídicos por regra (sem LLM); alimenta Excel e memória de cálculo. `gerar_parecer_parcelas_apuradas(verbas, dados)` — seção I do parecer em itens estruturados (a), b), c)) via Python puro (mantido para compatibilidade). `gerar_parecer_tecnico_completo(dados, verbas)` — **novo**: gera o parecer técnico completo usando template fixo (cabeçalho + seção II) + slot preenchido por IA via `ai_client.gerar_parcelas_parecer` orientada por `skills/parecer_pericial.md`; retorna `{"texto", "parcelas", "model_used", "error"}`. `TEXTOS_PADRAO_CRITERIOS_PARECER` agora inclui também a chave `"correcao"` (IPCA-E/SELIC — ADC 58 STF).
- **pjc_template_patcher.py**: `aplicar_patch(template_xml, dados)` — preenche XML .pjc com dados do processo; funções por seção (gprec, datas, FGTS, processo, parâmetros). `validar_patch`, `gerar_nome_arquivo`.

### Services — persistência, utilitários e aprendizado autônomo

- **database.py**: SQLite — créditos, cache (get/save), extrações (save/get), histórico, jobs (save/get), cleanup.
- **schema_version_guard.py**: Guarda de versão do schema para invalidar cache quando modelos mudam.
- **verba_deduplicator.py**: Deduplicação de verbas (assinatura nome+período); também exposta como regra no jurisprudencia.
- **learning_engine.py**: `processar_sete_arquivos` (entrada principal — **8 arquivos**, linha do tempo completa); `processar_cinco_arquivos` (compat. — 5 arquivos); `_extrair_amostragem_pdf` / `_extrair_amostragem_word` (Gemini analisa provas e estilo); `_atualizar_skill_amostragem` (acumula em `skills/amostragem_style.md`); `_gerar_regras_preditivas_amostragem` (cross-reference → regras preditivas); **`_extrair_manifestacao_pericial`** (Gemini extrai retórica de combate — frases de impacto, súmulas, padrões Ataque/Defesa, parâmetros fraudados, argumento vencedor); **`_codificar_padroes_ataque_defesa`** (cada padrão → Shadow Rule no KB); **`_atualizar_skill_manifestacao`** (acumula em `skills/manifestacao_style.md`); `processar_aprendizado_autonomo` (Self-Healing Rule Engine: hipóteses JSON + KB + avalia shadow); `_evaluate_shadow_rules`; `preview_aprendizado`; `codify_insight`.
- **knowledge_base.py**: `KnowledgeBase` — banco de conhecimento em JSON (`knowledge_base.json`) com campos `rule_id`, `descricao`, `condicao`, `acao`, `confidence_score`, `status` (`shadow`/`active`/`deleted`), `casos_vistos`, `acertos`, `punicoes`; métodos `adicionar_ou_incrementar`, `marcar_acerto`, `marcar_punicao`, `stats`.
- **learning_skill_loader.py**: `carregar_skill_para_lab(doc_type)` — carrega playbook .md para o laboratório (independente do processor).

### Memória de cálculo

- **memoria_calculo/generator.py**: `gerar_memoria(job_id, dados, model_used, doc_type, avisos_dedup, explicacoes)` — gera `memoria_{job_id}.json` com trilha de auditoria:
  - `regras_aplicadas`: mapeia campos → regras (ex.: FGTS sobre aviso, multas, honorários);
  - `regras_aplicadas_ids`: lista completa de IDs de regras executadas pelo Legal Rule Engine;
  - `alertas`, `verbas_deferidas`/`verbas_indeferidas`, `explicacoes`.

### Testes

- **tests/jurisprudencia/**: Testes por regra (test_reflexos_proibidos, test_bis_in_idem, test_consistencia_datas, test_legal_engine, test_legal_engine_borda, etc.).
- **tests/test_normalizer.py**, **test_sentence_understanding.py**, **test_calculation_parameters.py**, **test_explanation_engine.py**: Testes dos serviços correspondentes.

### Arquivo de referência

- **REFATORACAO_VALIDADOR.md**: Documenta que a validação é feita pelo Legal Rule Engine; código legado em `_archive/legacy/legal_validator_pre_engine.py`.

---

## Como rodar

- **API**: a partir da raiz do backend, `uvicorn main:app --reload` (ou com host/port desejados). Os endpoints de download dependem de `services.pjc_exporter` e `services.excel_exporter` (ver imports em `main.py`).
- **Testes**: `pytest` ou `pytest tests/ -v`; testes do motor: `pytest tests/jurisprudencia/ -v`.
- **Lint/format**: `ruff check .` e `ruff format .` (config em `pyproject.toml`).

---

## Documentação para desenvolvimento assistido por IA

A pasta **`docs/`** contém documentação splitada para reduzir contexto e custo de tokens para agentes:

| Arquivo | Conteúdo |
|---------|----------|
| [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) | Visão do produto, componentes e fluxo em 1 página. |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Os 10 passos do pipeline e dependências entre eles. |
| [docs/CODE_MAP.md](docs/CODE_MAP.md) | Mapa arquivo → responsabilidade; índice por domínio (FGTS, datas, regras, etc.). |
| [docs/AI_RULES.md](docs/AI_RULES.md) | Regras críticas para IA (o que não fazer, onde ler primeiro por tipo de tarefa). |
| [docs/DIAGNOSTICO_E_PLANO.md](docs/DIAGNOSTICO_E_PLANO.md) | Diagnóstico arquitetural e plano de refatoração da documentação. |

Para alterações pontuais, preferir abrir `docs/AI_RULES.md` e `docs/CODE_MAP.md` em vez do README inteiro.

---

## Regras de contexto do projeto

- Pipeline em 10 passos não deve ser alterado sem análise de impacto.
- Uma regra jurídica por arquivo em `legal_engine/rules/`; registro automático pelo rule_registry.
- Migração do validador legado concluída: não há mais ValidadorReflexos ativo; apenas engine.
- Manter compatibilidade com PJeCalc 2.14.0 para o arquivo .pjc (template e patch).

# Mapa de código — arquivo → responsabilidade

Uso: buscar por nome de arquivo ou por domínio (ex.: FGTS, datas, regras). Para regras do motor, ver também a tabela de regras no README.

## Por arquivo (raiz e workers)

| Arquivo | Responsabilidade |
|---------|-------------------|
| main.py | API FastAPI; upload PDF; jobs (memória + SQLite); WebSocket; download Excel/PJC; lab (/lab/analisar, /lab/preview, /lab/salvar, /lab/historico, /lab/knowledge-base); GET /api/stats (dashboard: processos_analisados, regras ativas/shadow, omissoes, eficiencia_motor, ultimas_regras, top_verbas); timeout 5 min. |
| config.py | Env: GEMINI_API_KEY, Firebase, MAX_FILE_SIZE_MB, SCHEMA_VERSION, etc. |
| models.py | ProcessoTrabalhista, VerbaDeferida (Pydantic); validadores; SCHEMA_VERSION. |
| workers/processor.py | Pipeline completo: process_lawsuit_pdf; orquestra todos os serviços. |

## Por arquivo — services (extração e texto)

| Arquivo | Responsabilidade |
|---------|-------------------|
| sentence_finder.py | extract_sentence_from_pdf; tipo de doc; OCR híbrido; bloco de decisão. |
| text_processor.py | normalize_text; find_section_hybrid (dispositivo etc.). |
| pre_extractor.py | pre_extract (regex/campos HIGH/MEDIUM); build_anchor_section. |
| ai_client.py | extract_data_with_gemini(texto, playbook, anchor_section) — cascata Flash→Pro; truncagem; prompt. gerar_parcelas_parecer(verbas, dados, skill_parecer) — gera apenas o texto da seção I do parecer (plain text, sem Markdown) orientado por skills/parecer_pericial.md. |
| normalizer.py | normalizar; normalizar_lista; eh_chave_valida; listar_variacoes. |
| sentence_understanding.py | extrair_verbas_deferidas; extrair_reflexos; interpretar_decisao; etc. |

## Por arquivo — services (validação e regras)

| Arquivo | Responsabilidade |
|---------|-------------------|
| legal_validator.py | validar_dados; validar_dados_completo; delega ao Legal Rule Engine. |
| legal_engine/rule_base.py | ContextoJuridico; VerbaContexto; LegalRule (base). |
| legal_engine/engine.py | LegalRuleEngine; executar(dados). |
| legal_engine/rule_registry.py | carregar_todas_as_regras; descoberta em rules/ e jurisprudencia/. |
| legal_engine/dynamic_rule_loader.py | DynamicLegalRule (implementa regras dinâmicas a partir do Knowledge Base); carregar_regras_ativas (injeta regras com status “active” no pipeline); executar_shadow_pipeline (executa regras “shadow” em background para coleta de métricas). |
| legal_engine/rules/*.py | Uma regra por arquivo (ReflexosProibidosRule, BisInIdemReflexosRule, etc.). |
| jurisprudencia/**/*.py | Regras legadas (STF, TST, CLT, consistência). |

## Por arquivo — services (cálculo e exportação)

| Arquivo | Responsabilidade |
|---------|-------------------|
| calculation_parameters.py | gerar_parametros; período, divisor, jornada, FGTS, INSS, honorários. |
| explanation_engine.py | gerar_explicacoes(verbas, memorial_juridico) — templates por regra (sem LLM). gerar_parecer_parcelas_apuradas(verbas, dados) — itens estruturados (compat.). gerar_parecer_tecnico_completo(dados, verbas) — parecer completo Padrão Ouro: template fixo (cabeçalho + seção II IPCA-E/INSS/IRRF) + slot da seção I gerado por IA via ai_client + skills/parecer_pericial.md. |
| pjc_template_patcher.py | aplicar_patch(template_xml, dados); validar_patch; gerar_nome_arquivo. |
| pjc_parser.py | Ler arquivos .pjc (XML PJe-Calc) e extrair parâmetros básicos (índice, juros, divisor, verbas). |
| pjc_auditor.py | Comparar dados da sentença (IA) com parâmetros extraídos do .pjc e gerar lista de divergências. |

## Por arquivo — services (persistência e utilitários)

| Arquivo | Responsabilidade |
|---------|-------------------|
| database.py | Créditos; cache; extrações; histórico; jobs; cleanup. |
| schema_version_guard.py | Guarda de versão do schema (invalidar cache). |
| verba_deduplicator.py | Deduplicação de verbas (nome + período). |
| learning_engine.py | processar_sete_arquivos (entrada principal — **8 arquivos**, linha do tempo); processar_cinco_arquivos (compat.); _extrair_amostragem_pdf/word; _atualizar_skill_amostragem (skills/amostragem_style.md); _gerar_regras_preditivas_amostragem (cross-reference); **_extrair_manifestacao_pericial** (Gemini: frases de impacto, súmulas, padrões Ataque/Defesa); **_codificar_padroes_ataque_defesa** (→ Shadow Rules no KB); **_atualizar_skill_manifestacao** (skills/manifestacao_style.md); processar_aprendizado_autonomo (Self-Healing); _evaluate_shadow_rules; preview_aprendizado; codify_insight. |
| knowledge_base.py | KnowledgeBase — banco de conhecimento (knowledge_base.json) com regras dinâmicas aprendidas: rule_id, descricao, condicao, acao, base_legal, confidence_score, status (shadow/active/deleted), casos_vistos, acertos, punicoes; operações de ciclo de vida (adicionar_ou_incrementar, marcar_acerto, marcar_punicao, stats). |
| learning_skill_loader.py | carregar_skill_para_lab(doc_type); playbook para o lab. |

## Por arquivo — skills (playbooks e manuais de redação)

| Arquivo | Responsabilidade |
|---------|-------------------|
| skills/sentenca_ordinaria.md | Playbook de extração para sentenças trabalhistas; receberá exemplos few-shot adicionados via Laboratório (codify_insight). |
| skills/parecer_pericial.md | **Manual de Redação do Parecer Técnico — Padrão Ouro**: regras de tom de voz (iniciar "Apuração...", numeração alfabética, reflexos agrupados ao final), exemplos few-shot (ADICIONAL NOTURNO, HORAS EXTRAS). Passado como system prompt para `ai_client.gerar_parcelas_parecer`. |

---

## Por arquivo — memoria_calculo

| Arquivo | Responsabilidade |
|---------|-------------------|
| memoria_calculo/generator.py | gerar_memoria; gera memoria_{job_id}.json. |

## Por arquivo — Frontend (frontend/)

| Arquivo | Responsabilidade |
|---------|-------------------|
| index.html | Estrutura da aplicação; Tailwind CSS (CDN): sidebar fixa, header com avatar, painéis Extrator (#view-extrator), Laboratório (#view-lab), Meus Processos (#view-historico), Estatísticas (#view-estatisticas); estilos .kpi-updated e @keyframes labToastIn; script inline de troca de view; preserva IDs/classes usados por app.js, render.js, lab.js. |
| css/main.css | Estilos de componentes dinâmicos: seções, campos, verbas, alertas, fundamentação, parecer; lab (.lab-*), modal do lab (.lab-modal-*). Layout estrutural (sidebar, header) fica no Tailwind em index.html. |
| js/app.js | Upload PDF, polling /status/{job_id}, status e meta tags, export PJC/Excel, créditos, auditoria .PJC. Histórico: carregarHistorico(), renderizarHistorico(), filtrarHistorico(). Estatísticas: carregarEstatisticas(silencioso), _setKpiValue (animação .kpi-updated), iniciarPollingEstatisticas() — setInterval 5 s só quando #view-estatisticas visível; GET /api/stats. |
| js/render.js | renderResultado(dados); montagem HTML: resumo, seções, verbas, alertas, fundamentação, parecer técnico; helpers val, vv, statusClass, statusLabel. |
| js/lab.js | Laboratório: **8 uploads** (LAB_CAMPOS; formKey inclui `manifestacao`; Tríade de Ouro Expandida: Amostragem + Processo + .PJC + Manifestação), /lab/analisar (processar_sete_arquivos; botão sempre liberado, apenas bloqueia envio totalmente vazio), Resultado 1–4 (inclui "Conclusão da Tríade de Ouro Expandida" — grid 2×2 com argumento vencedor e padrões Ataque/Defesa), modal pré-visualização (/lab/preview), confirmar e salvar (/lab/salvar). Após salvar: _labToastEstatisticas(), _labNavEstatisticas(). |

## Por domínio (onde procurar)

| Domínio | Arquivos principais |
|---------|---------------------|
| Pipeline e orquestração | workers/processor.py |
| Regras jurídicas (motor) | legal_engine/rule_base.py, engine.py, rule_registry.py; legal_engine/rules/*.py; jurisprudencia/**/*.py |
| FGTS | legal_engine/rules/fgts_*.py; jurisprudencia/orientacoes/oj_42.py, oj_195.py; jurisprudencia/sumulas/sumula_305.py |
| Datas e consistência temporal | legal_engine/rules/consistencia_datas.py; jurisprudencia/consistencia/datas.py |
| Aviso prévio | legal_engine/rules/aviso_previo_*.py; jurisprudencia/clt/lei_12506.py |
| Multas (467/477) | legal_engine/rules/multa_467.py, multa_477.py, multa_477_valor.py |
| Reflexos e DSR | legal_engine/rules/reflexos_proibidos.py, he_reflexo_dsr.py, dsr_bis_in_idem.py; jurisprudencia/orientacoes/oj_394.py |
| Explicações jurídicas | services/explanation_engine.py |
| Laboratório de Aprendizado | services/learning_engine.py, learning_skill_loader.py; main.py (lab); frontend/js/lab.js |
| Dashboard de Estatísticas | main.py (GET /api/stats); services/knowledge_base.py, database.get_total_extractions; frontend/js/app.js (carregarEstatisticas, iniciarPollingEstatisticas, .kpi-updated) |
| IA e prompt | services/ai_client.py; skills/*.md |
| PDF e texto | services/sentence_finder.py, text_processor.py, pre_extractor.py |

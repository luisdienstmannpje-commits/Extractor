# Regras para desenvolvimento assistido por IA (Atualizado)

Documento obrigatório para agentes que alteram código. Reduz risco de regressões e quebra do pipeline.

## Regras críticas — nunca fazer

- **Não quebrar o pipeline**: a ordem e os contratos dos 10 passos em `workers/processor.py` não devem ser alterados sem análise de impacto e atualização dos testes.
- **Não alterar múltiplos módulos de uma vez** sem justificativa (ex.: uma mudança de contrato que exige alterar processor + engine + testes).
- **Não remover lógica jurídica existente** (regras, validações, templates do `explanation_engine`) sem substituição equivalente e testes atualizados.
- **Não introduzir regressões**: após qualquer mudança, rodar `pytest -q` (ou `pytest tests/ -v`) e garantir 0 falhas.
- **Não ignorar o tenant**: ao instanciar serviços de persistência ou inteligência multi-cliente (como `KnowledgeBase`), SEMPRE verificar e passar o `tenant_id`/`user_id` correto. Isolamento de dados entre clientes é prioridade máxima.

## Sempre fazer

- **Manter todos os testes passando** após cada alteração.
- **Justificar mudanças arquiteturais** (por que o passo X foi movido, por que uma regra saiu do `jurisprudencia` para `legal_engine/rules`, etc.).
- **Explicar impacto** antes de gerar código (quais arquivos e testes são afetados).
- **[OBRIGATÓRIO] Atualizar Backlog de Refatoração**: Sempre que você realizar uma alteração que impacte o backend, frontend ou contratos de API, você é OBRIGADO a atualizar o arquivo `refatoracao_necessaria.mdc` seguindo o checklist do item 8, antes de considerar a tarefa finalizada. O objetivo é garantir que o sistema evolua para um padrão SaaS (multi-tenant, escalável e observável).

## Contexto Unificado — Laboratório (`/lab/analisar`)

O endpoint **`POST /lab/analisar`** (ou rota equivalente da API) espera **múltiplos arquivos de uma vez** em um único `FormData`. O frontend (Cérebro Analítico, `Laboratory.tsx`) envia todos os documentos anexados numa única requisição; não há análise por card nem envio parcial.

- **Campos do FormData:** `user_id`, `processo` (múltiplos), `liquidacao`, `calculo_pjc`, `manifestacao`, `parecer`, e opcionais (`amostragem_word`, `amostragem_pdf`, etc.), conforme `useAnalyze` e rota em `api/routers/lab.py`.
- **Comportamento do backend:** o Learning Engine (`learning_engine.py`) coordena os módulos em `services/lab/` e monta um **contexto unificado**. A LLM (Gemini) foi treinada/instruída para **cruzar dados de Sentença vs Liquidação apenas quando ambos estão presentes**; com apenas Sentença, a análise limita-se à extração (verbas deferidas, campos estruturais). Com Sentença + Liquidação + PJC, o motor faz auditoria de cálculos e gera discrepâncias.
- **Style Transfer:** quando Manifestação e/ou Parecer/Amostragem são enviados, o `style_transfer.py` analisa o estilo de redação e o `document_generator.py` usa esse estilo na minuta de Manifestação aos Cálculos (Ghostwriter).

## Onde ler primeiro (por tipo de tarefa)

| Se a tarefa é… | Ler primeiro |
|----------------|--------------|
| Saber o que precisa ser refatorado (Backlog SaaS) | `refatoracao_necessaria.mdc` |
| Alterar passos do pipeline ou ordem | `docs/PIPELINE.md` e `workers/processor.py` |
| Alterar rotas ou API | `backend/api/routers/` (extrator, lab, admin, exports) e `docs/CODE_MAP.md` |
| Adicionar ou modificar regra jurídica | `README.md` (seção Motor de regras), `legal_engine/rule_base.py`, um arquivo existente em `legal_engine/rules/` como exemplo |
| Alterar validação (alertas, níveis) | `legal_engine/engine.py`, `legal_validator.py`, `legal_engine/rule_base.py` |
| Alterar extração de texto ou IA | `ai_client.py`, `sentence_finder.py`, `skills/*.md` |
| Alterar modelo de dados (campos) | `models.py`, `config.SCHEMA_VERSION`, `legal_engine/engine._dict_para_contexto` |
| Alterar memória de cálculo ou explicacoes | `memoria_calculo/generator.py`, `explanation_engine.py` |
| Laboratório de Aprendizado (lab) | `docs/guia_eficiencia.md` (níveis, pesos, marcha), README § Laboratório, `learning_engine.py` (facade), `services/lab/self_healing.py` (codify + Shadow Rules), `main.py`, **frontend:** `frontend/src/pages/Laboratory.tsx`, `frontend/src/hooks/useAnalyze.ts` |
| Alterar layout/UI do frontend (sidebar, header, painéis) | README (seção Frontend), `docs/CODE_MAP.md` (§ Frontend), `frontend/src/App.tsx`, `frontend/src/components/layout/MainLayout.tsx`, `frontend/src/pages/*.tsx` |
| Alterar Parecer Técnico (tom, formato, slots) | `skills/parecer_pericial.md`, `explanation_engine.py` (gerar_parecer_tecnico_completo), `ai_client.py` (gerar_parcelas_parecer), `docs/CODE_INTELLIGENCE_MAP.md` (seção 4.3) |
| Navegação rápida (qual arquivo faz o quê) | `docs/CODE_MAP.md` |
| Visão geral do sistema | `docs/SYSTEM_OVERVIEW.md` |

## Convenções do projeto

- **Uma regra jurídica por arquivo** em `legal_engine/rules/`; a regra deve herdar de `LegalRule`, ter `id`, `titulo`, `base_legal`, `prioridade` e implementar `aplicar(contexto)`.
- **Regras legadas** em `services/jurisprudencia/` (STF, TST, CLT, consistência); o `rule_registry` varre ambas as pastas; IDs duplicados são ignorados (o primeiro vence).
- **Validação**: só o Legal Rule Engine é usado; `legal_validator.py` apenas delega. Código legado em `_archive/legacy/legal_validator_pre_engine.py` é referência, não executado.
- **Compatibilidade .pjc**: manter compatibilidade com PJeCalc 2.14.0 ao alterar `pjc_template_patcher` ou template XML.

## Redução de custo de tokens

- **Tarefa pontual** (ex.: “alterar regra X”), abrir apenas: `docs/AI_RULES.md`, `docs/CODE_MAP.md` (ou trecho relevante) e o arquivo da regra.
- **Lab:** ler `docs/guia_eficiencia.md` (níveis, pesos, marcha); não duplicar tabelas do Lab noutros docs.
- Evitar README inteiro se `SYSTEM_OVERVIEW.md` + `PIPELINE.md` bastarem.
- **Nova regra:** template em `legal_engine/rules/` + teste em `tests/jurisprudencia/`.

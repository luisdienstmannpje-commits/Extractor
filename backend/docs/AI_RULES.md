# Regras para desenvolvimento assistido por IA

Documento obrigatório para agentes que alteram código. Reduz risco de regressões e quebra do pipeline.

## Regras críticas — nunca fazer

- **Não quebrar o pipeline**: a ordem e os contratos dos 10 passos em `workers/processor.py` não devem ser alterados sem análise de impacto e atualização dos testes.
- **Não alterar múltiplos módulos de uma vez** sem justificativa (ex.: uma mudança de contrato que exige alterar processor + engine + testes).
- **Não remover lógica jurídica existente** (regras, validações, templates do explanation_engine) sem substituição equivalente e testes atualizados.
- **Não introduzir regressões**: após qualquer mudança, rodar `pytest -q` (ou `pytest tests/ -v`) e garantir 0 falhas.

## Sempre fazer

- **Manter todos os testes passando** após cada alteração.
- **Justificar mudanças arquiteturais** (por que o passo X foi movido, por que uma regra saiu do jurisprudencia para legal_engine/rules, etc.).
- **Explicar impacto** antes de gerar código (quais arquivos e testes são afetados).

## Onde ler primeiro (por tipo de tarefa)

| Se a tarefa é… | Ler primeiro |
|----------------|--------------|
| Alterar passos do pipeline ou ordem | `docs/PIPELINE.md` e `workers/processor.py` |
| Adicionar ou modificar regra jurídica | `README.md` (seção Motor de regras), `legal_engine/rule_base.py`, um arquivo existente em `legal_engine/rules/` como exemplo |
| Alterar validação (alertas, níveis) | `legal_engine/engine.py`, `legal_validator.py`, `legal_engine/rule_base.py` |
| Alterar extração de texto ou IA | `ai_client.py`, `sentence_finder.py`, `skills/*.md` |
| Alterar modelo de dados (campos) | `models.py`, `config.SCHEMA_VERSION`, `legal_engine/engine._dict_para_contexto` |
| Alterar memória de cálculo ou explicacoes | `memoria_calculo/generator.py`, `explanation_engine.py` |
| Laboratório de Aprendizado (lab) | README (seção Laboratório), `services/learning_engine.py` (codify_insight), `main.py` (lab), `frontend/js/lab.js` |
| Alterar layout/UI do frontend (sidebar, header, painéis) | README (seção Frontend), `docs/CODE_INTELLIGENCE_MAP.md` (seção 7), `frontend/index.html`, `frontend/css/main.css` |
| Alterar Parecer Técnico (tom, formato, slots) | `skills/parecer_pericial.md`, `explanation_engine.py` (gerar_parecer_tecnico_completo), `ai_client.py` (gerar_parcelas_parecer), `docs/CODE_INTELLIGENCE_MAP.md` (seção 4.3) |
| Navegação rápida (qual arquivo faz o quê) | `docs/CODE_MAP.md` |
| Visão geral do sistema | `docs/SYSTEM_OVERVIEW.md` |

## Convenções do projeto

- **Uma regra jurídica por arquivo** em `legal_engine/rules/`; a regra deve herdar de `LegalRule`, ter `id`, `titulo`, `base_legal`, `prioridade` e implementar `aplicar(contexto)`.
- **Regras legadas** em `services/jurisprudencia/` (STF, TST, CLT, consistência); o `rule_registry` varre ambas as pastas; IDs duplicados são ignorados (o primeiro vence).
- **Validação**: só o Legal Rule Engine é usado; `legal_validator.py` apenas delega. Código legado em `_archive/legacy/legal_validator_pre_engine.py` é referência, não executado.
- **Compatibilidade .pjc**: manter compatibilidade com PJeCalc 2.14.0 ao alterar `pjc_template_patcher` ou template XML.

## Redução de custo de tokens

- Para tarefa pontual (ex.: “alterar regra X”), abrir apenas: `docs/AI_RULES.md`, `docs/CODE_MAP.md` (ou trecho relevante) e o arquivo da regra.
- Evitar carregar o README inteiro se já houver contexto em `SYSTEM_OVERVIEW.md` e `PIPELINE.md`.
- Para nova regra: usar um arquivo existente em `legal_engine/rules/` como template (ex.: `reflexos_proibidos.py`) e o teste correspondente em `tests/jurisprudencia/`.

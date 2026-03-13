# Refatoração: Validador → Legal Rule Engine

A validação jurídica é feita **exclusivamente** pelo **Legal Rule Engine**.

- **API**: `validar_dados(dados)` e `validar_dados_completo(dados)` em `services/legal_validator.py` delegam ao engine.
- **Regras**: `services/legal_engine/rules/` e `services/jurisprudencia/` (registry carrega ambas).
- **Referência legada**: `_archive/legacy/legal_validator_pre_engine.py` (ValidadorReflexos) mantido apenas como histórico; não é mais executado.

Ciclo fechado: migração concluída, pipeline usando o engine, código morto removido do validator ativo.

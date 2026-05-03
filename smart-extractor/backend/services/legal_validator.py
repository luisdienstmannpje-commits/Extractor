"""
legal_validator.py — Interface de validação jurídica (Legal Rule Engine)

A validação é executada pelo Legal Rule Engine (services/legal_engine/).
Regras em services/legal_engine/rules/ e services/jurisprudencia/.

Código legado do ValidadorReflexos: _archive/legacy/legal_validator_pre_engine.py

Singleton _RULE_ENGINE: carregado uma vez na importação do módulo (mesmo padrão
de workers/processor.py), evitando recriar o engine a cada chamada de validar_dados.
"""

from services.legal_engine.rule_registry import carregar_todas_as_regras
from services.legal_engine.engine import LegalRuleEngine

# ── Singleton — carregado uma vez na inicialização do módulo ─────────────────
# Falha rápida (fail-fast): se o registry ou o engine falharem, o erro ocorre
# na importação, visível no deploy/CI, e não silenciosamente em runtime.
_RULE_ENGINE = LegalRuleEngine(carregar_todas_as_regras())


def validar_dados(dados: dict) -> list[str]:
    """Retorna lista de alertas [NIVEL] mensagem. Usado por workers/processor.py."""
    return validar_dados_completo(dados)["alertas"]


def validar_dados_completo(dados: dict) -> dict:
    """
    Retorna dict: alertas, regras_aplicadas, memorial_juridico.

    memorial_juridico é lista de dicts (id, titulo, base_legal, descricao,
    prioridade), alinhada a LegalRuleEngine.executar — necessária para
    gerar_explicacoes / ExplanationEngine.gerar no processor.

    Delega ao singleton _RULE_ENGINE (Legal Rule Engine).

    Erros de execução de regra individual são capturados internamente pelo
    engine e registrados como alertas INFO — não chegam aqui como exceção.
    Erros inesperados (ex: dados com tipo incompatível) são propagados para
    que o caller possa registrar e tratar adequadamente, sem mascarar falhas.
    """
    resultado = _RULE_ENGINE.executar(dados)

    alertas = resultado["alertas"]
    regras_aplicadas = resultado["regras_aplicadas"]
    memorial = resultado.get("memorial_juridico") or []
    if not isinstance(memorial, list):
        memorial = []

    return {
        "alertas": alertas,
        "regras_aplicadas": regras_aplicadas,
        "memorial_juridico": memorial,
    }

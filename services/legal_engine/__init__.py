from services.legal_engine.rule_base     import LegalRule, ContextoJuridico, VerbaContexto
from services.legal_engine.engine        import LegalRuleEngine
from services.legal_engine.rule_registry import carregar_todas_as_regras

__all__ = [
    "LegalRule",
    "ContextoJuridico",
    "VerbaContexto",
    "LegalRuleEngine",
    "carregar_todas_as_regras",
]
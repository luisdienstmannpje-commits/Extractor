"""
legal_validator.py — Interface de validação jurídica (Legal Rule Engine)

A validação é executada pelo Legal Rule Engine (services/legal_engine/).
Regras em services/legal_engine/rules/ e services/jurisprudencia/.

Código legado do ValidadorReflexos: _archive/legacy/legal_validator_pre_engine.py
"""


def validar_dados(dados: dict) -> list[str]:
    """Retorna lista de alertas [NIVEL] mensagem. Usado por workers/processor.py."""
    return validar_dados_completo(dados)["alertas"]


def validar_dados_completo(dados: dict) -> dict:
    """
    Retorna dict: alertas, regras_aplicadas, memorial_juridico.
    Delega ao Legal Rule Engine (carregar_todas_as_regras + executar).
    """
    try:
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        from services.legal_engine.engine import LegalRuleEngine

        rules = carregar_todas_as_regras()
        engine = LegalRuleEngine(rules)
        resultado = engine.executar(dados)

        alertas = resultado["alertas"]
        regras_aplicadas = resultado["regras_aplicadas"]
        erros = sum(1 for a in alertas if "[ERRO]" in a)
        avisos = sum(1 for a in alertas if "[AVISO]" in a)

        if alertas:
            linhas_memorial = [
                f"Validação jurídica — {len(regras_aplicadas)} regras aplicadas.",
                f"Resultado: {erros} erro(s), {avisos} aviso(s).",
                "",
            ] + alertas
        else:
            linhas_memorial = [
                f"Validação jurídica — {len(regras_aplicadas)} regras aplicadas.",
                "Resultado: dados consistentes, nenhum alerta gerado.",
            ]

        return {
            "alertas":           alertas,
            "regras_aplicadas":  regras_aplicadas,
            "memorial_juridico": "\n".join(linhas_memorial),
        }
    except Exception as e:
        print(f"[VALIDATOR] Erro crítico em validar_dados_completo: {e}")
        return {
            "alertas":           [],
            "regras_aplicadas":  [],
            "memorial_juridico": f"Erro na validação: {e}",
        }

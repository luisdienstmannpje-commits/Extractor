from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class IntegracaoSemReflexosRule(LegalRule):
    """
    Consistência: verba marcada com integracao_salarial=True mas sem reflexos.

    Equivalente à checagem `_check_integracao_sem_reflexos` do validador legado.
    """

    id = "CONSISTENCIA_INTEGRACAO_SEM_REFLEXOS"
    titulo = "Verba integrada sem reflexos"
    base_legal = (
        "Consistência de cálculo — verbas que integram salário "
        "normalmente geram reflexos em outras parcelas"
    )
    prioridade = 50
    descricao = (
        "Alerta quando uma verba com integracao_salarial=True está sem reflexos "
        "informados, indicando possível omissão de reflexos na extração."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            for verba in contexto.verbas_deferidas or []:
                nome_canonico = self._canonizar_verba(verba.nome or "")
                integracao = verba.integracao_salarial
                reflexos = verba.reflexos or []

                if integracao is True and not reflexos:
                    self._alerta(
                        contexto,
                        (
                            f"'{nome_canonico}' tem integracao_salarial=True mas reflexos=[]. "
                            "Verificar se reflexos foram omitidos na extração."
                        ),
                        nivel="AVISO",
                    )

            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de integração sem reflexos: {e}",
                nivel="ERRO",
            )
        return contexto


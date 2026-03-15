from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class BisInIdemReflexosRule(LegalRule):
    """
    Regra de consistência: uma verba não pode aparecer como reflexo de si mesma.

    Equivalente à checagem `_check_bis_in_idem` do validador legado.
    """

    id = "CONSISTENCIA_BIS_IN_IDEM_REFLEXOS"
    titulo = "Bis in idem em reflexos"
    base_legal = "Consistência de cálculo — vedação a reflexos em si mesmos"
    prioridade = 50
    descricao = (
        "Gera alerta de erro quando uma verba aparece como reflexo de si mesma, "
        "evitando bis in idem nos reflexos trabalhistas."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            for verba in contexto.verbas_deferidas or []:
                nome_canonico = self._canonizar_verba(verba.nome or "")
                reflexos_canonicos = [
                    self._canonizar_verba(r) for r in (verba.reflexos or [])
                ]

                if nome_canonico and nome_canonico in reflexos_canonicos:
                    self._alerta(
                        contexto,
                        f"Bis in idem: '{nome_canonico}' aparece como reflexo de si mesma.",
                        nivel="ERRO",
                    )

            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de bis in idem: {e}",
                nivel="ERRO",
            )
        return contexto


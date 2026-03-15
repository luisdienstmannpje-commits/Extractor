from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class DanoMoralEmVerbasRule(LegalRule):
    """
    Consistência: dano moral não deve aparecer em verbas_deferidas.

    Equivalente à checagem `_check_dano_moral_em_verbas` do validador legado.
    """

    id = "CONSISTENCIA_DANO_MORAL_EM_VERBAS"
    titulo = "Dano moral não deve constar em verbas_deferidas"
    base_legal = (
        "Consistência de modelagem — dano moral possui campo próprio e não deve "
        "ser tratado como verba comum na lista de verbas_deferidas."
    )
    prioridade = 50
    descricao = (
        "Gera aviso quando 'Dano Moral' aparece entre as verbas deferidas, "
        "orientando a usar o campo estruturado específico de dano moral."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            for verba in contexto.verbas_deferidas or []:
                nome = (verba.nome or "").lower()
                if "dano moral" in nome or "danos morais" in nome:
                    self._alerta(
                        contexto,
                        (
                            "Dano moral encontrado em verbas_deferidas. "
                            "Deve estar no campo 'dano_moral', não na lista de verbas."
                        ),
                        nivel="AVISO",
                    )
                    break

            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de dano moral em verbas: {e}",
                nivel="ERRO",
            )
        return contexto


"""
he_reflexo_dsr.py
Regra: Horas extras habituais refletem em DSR.
Fundamento: Súmula 264 TST
Prioridade: 20 (TST Súmulas)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class HeReflexoDsrRule(LegalRule):

    id         = "SUMULA_264_TST"
    titulo     = "Horas Extras — Reflexos em DSR"
    base_legal = "Súmula 264 TST"
    prioridade = 20
    descricao  = (
        "O valor das horas extras habitualmente prestadas integra o cálculo "
        "dos haveres trabalhistas, inclusive o DSR, com reflexos no 13º salário, "
        "férias e FGTS."
    )

    _REFLEXOS_OBRIGATORIOS = [
        "dsr",
        "ferias_proporcionais",
        "decimo_terceiro",
        "fgts_depositos",
    ]

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            for verba in contexto.verbas_deferidas:
                nome = (verba.nome or "").lower()

                if "horas_extras" not in nome and "horas extras" not in nome:
                    continue

                reflexos_atuais = verba.reflexos or []
                adicionados = []

                for reflexo in self._REFLEXOS_OBRIGATORIOS:
                    if reflexo not in reflexos_atuais:
                        reflexos_atuais.append(reflexo)
                        adicionados.append(reflexo)

                verba.reflexos = reflexos_atuais

                if adicionados:
                    self._alerta(
                        contexto,
                        f"Horas extras '{verba.nome}' — reflexos adicionados por Súmula 264 TST: "
                        f"{', '.join(adicionados)}.",
                        nivel="INFO",
                    )

            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar Súmula 264 TST: {e}",
                nivel="ERRO",
            )

        return contexto

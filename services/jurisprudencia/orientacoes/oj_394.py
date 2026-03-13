"""
OJ 394 SDI-I TST — DSR: Vedação de Reflexos em Férias, 13º e FGTS

Regra:
  O DSR majorado por horas extras NÃO reflete em férias, 13º salário
  e FGTS. Configuraria bis in idem.

Base legal:
  OJ 394 SDI-I TST
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class OJ394DSRReflexos(LegalRule):

    id          = "OJ_394_SDI1_TST"
    titulo      = "OJ 394 SDI-I — DSR não reflete em Férias, 13º e FGTS"
    base_legal  = "OJ 394 SDI-I TST"
    prioridade  = 30
    descricao   = (
        "O DSR majorado por horas extras não integra o salário para reflexos "
        "em férias, 13º salário e FGTS. Configuraria bis in idem."
    )

    _PROIBIDOS = {"férias", "ferias", "13º salário", "13 salario", "13º", "fgts"}

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        for verba in contexto.verbas_deferidas:
            nome = (verba.nome or "").lower().strip()
            if "dsr" not in nome and "descanso semanal" not in nome:
                continue

            reflexos_lower = [r.lower() for r in (verba.reflexos or [])]
            for reflexo in reflexos_lower:
                for proibido in self._PROIBIDOS:
                    if proibido in reflexo:
                        self._alerta(
                            contexto,
                            f"OJ 394 SDI-I TST: DSR NÃO pode refletir em '{reflexo}'. "
                            "Configura bis in idem.",
                            nivel="ERRO",
                        )
                        break

        self._registrar(contexto)
        return contexto

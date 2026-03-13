"""
dsr_bis_in_idem.py
Regra: DSR majorado por horas extras NÃO reflete em férias, 13º, FGTS e aviso prévio.
Fundamento: OJ 394 SDI-I TST
Prioridade: 30 (TST Orientações Jurisprudenciais)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class DsrBisInIdemRule(LegalRule):

    id         = "OJ_394_SDI1_TST"
    titulo     = "DSR — Bis in Idem"
    base_legal = "OJ 394 SDI-I TST"
    prioridade = 30
    descricao  = (
        "O DSR calculado com base nas horas extras habitualmente prestadas "
        "não repercute no cálculo das férias, 13º salário, aviso prévio e FGTS, "
        "sob pena de bis in idem."
    )

    _REFLEXOS_PROIBIDOS = [
        "ferias_proporcionais",
        "ferias_vencidas",
        "decimo_terceiro",
        "aviso_previo_indenizado",
        "aviso_previo_trabalhado",
        "fgts_depositos",
        "fgts_com_multa",
    ]

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            for verba in contexto.verbas_deferidas:
                nome = (verba.nome or "").lower()

                if "dsr" not in nome and "repouso semanal" not in nome:
                    continue

                reflexos_atuais = verba.reflexos or []
                removidos = []

                for reflexo in self._REFLEXOS_PROIBIDOS:
                    if reflexo in reflexos_atuais:
                        reflexos_atuais.remove(reflexo)
                        removidos.append(reflexo)

                verba.reflexos = reflexos_atuais

                if removidos:
                    self._alerta(
                        contexto,
                        f"DSR '{verba.nome}' — reflexos removidos para evitar bis in idem "
                        f"(OJ 394 SDI-I TST): {', '.join(removidos)}.",
                        nivel="AVISO",
                    )
                else:
                    self._alerta(
                        contexto,
                        f"DSR '{verba.nome}' — nenhum reflexo indevido encontrado. "
                        "OJ 394 SDI-I TST verificada.",
                        nivel="INFO",
                    )

            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar OJ 394 SDI-I TST: {e}",
                nivel="ERRO",
            )

        return contexto

"""
Súmula 305 TST — FGTS: Incidência sobre Aviso Prévio

Regra:
  O FGTS incide sobre o aviso prévio trabalhado ou indenizado.

Base legal:
  Súmula 305 TST
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class Sumula305FGTSAP(LegalRule):

    id          = "SUMULA_305_TST"
    titulo      = "Súmula 305 TST — FGTS incide sobre aviso prévio"
    base_legal  = "Súmula 305 TST"
    prioridade  = 20
    descricao   = (
        "O FGTS incide sobre o aviso prévio trabalhado ou indenizado. "
        "Se o campo indicar não incidência, emite aviso para verificação."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        fgts_ap = (contexto.fgts_sobre_aviso_previo or "").lower()

        if not fgts_ap:
            return contexto

        nao_incide = (
            ("não" in fgts_ap or "nao" in fgts_ap)
            and "incide" in fgts_ap
        )

        if nao_incide:
            self._alerta(
                contexto,
                "Súmula 305 TST: FGTS DEVE incidir sobre o aviso prévio "
                "(trabalhado ou indenizado). Verificar se o documento realmente "
                "afasta a Súmula 305.",
                nivel="AVISO",
            )

        self._registrar(contexto)
        return contexto

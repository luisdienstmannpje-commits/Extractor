"""
OJ 42 SDI-I TST — FGTS: Multa de 40% sobre Aviso Prévio Indenizado

Regra:
  A multa de 40% do FGTS NÃO incide sobre o valor do FGTS relativo
  ao aviso prévio indenizado. Incide apenas sobre os depósitos realizados
  durante o período contratual efetivo de trabalho.

Base legal:
  OJ 42, II, SDI-I TST
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class OJ42FGTSMultaAvisoPrevio(LegalRule):

    id          = "OJ_42_SDI1_TST"
    titulo      = "OJ 42 SDI-I — Multa 40% FGTS não incide sobre aviso prévio"
    base_legal  = "OJ 42, II, SDI-I TST"
    prioridade  = 30
    descricao   = (
        "A multa de 40% do FGTS não incide sobre o FGTS do aviso prévio indenizado. "
        "Incide apenas sobre os depósitos do período efetivo de trabalho."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        multa_ap = (contexto.fgts_multa_40_aviso_previo or "").lower()

        if not multa_ap:
            return contexto

        incide_incorreto = (
            ("sim" in multa_ap or "incide" in multa_ap)
            and "não" not in multa_ap
            and "nao" not in multa_ap
        )

        if incide_incorreto:
            self._alerta(
                contexto,
                "OJ 42, II, SDI-I TST: a multa de 40% do FGTS NÃO incide sobre "
                "o FGTS referente ao aviso prévio indenizado. Verificar se o "
                "documento realmente determina essa incidência.",
                nivel="ERRO",
            )

        self._registrar(contexto)
        return contexto

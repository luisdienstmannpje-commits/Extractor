"""
OJ 195 SDI-I TST — FGTS sobre Férias Indenizadas

Regra:
  Não incide FGTS sobre férias indenizadas.
  Férias indenizadas têm natureza indenizatória, não salarial.

Base legal:
  OJ 195 SDI-I TST
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class OJ195FGTSFeriasIndenizadas(LegalRule):

    id          = "OJ_195_SDI1_TST"
    titulo      = "OJ 195 SDI-I — FGTS não incide sobre férias indenizadas"
    base_legal  = "OJ 195 SDI-I TST"
    prioridade  = 30
    descricao   = (
        "Não incide FGTS sobre férias indenizadas. "
        "As férias indenizadas têm natureza indenizatória, não salarial."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        fgts_ferias = (contexto.fgts_sobre_ferias_indenizadas or "").lower()

        if not fgts_ferias:
            return contexto

        incide_incorreto = (
            ("sim" in fgts_ferias or "incide" in fgts_ferias)
            and "não" not in fgts_ferias
            and "nao" not in fgts_ferias
        )

        if incide_incorreto:
            self._alerta(
                contexto,
                "OJ 195 SDI-I TST: FGTS NÃO incide sobre férias indenizadas. "
                "As férias indenizadas têm natureza indenizatória, não salarial. "
                "Verificar se o documento realmente determina essa incidência.",
                nivel="ERRO",
            )

        self._registrar(contexto)
        return contexto

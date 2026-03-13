"""
fgts_multa_40_ap_indenizado.py
Regra: Multa de 40% do FGTS NÃO incide sobre aviso prévio indenizado.
Fundamento: OJ 42 SDI-I TST
Prioridade: 30 (TST Orientações Jurisprudenciais)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class FgtsMulta40ApIndenizadoRule(LegalRule):

    id         = "OJ_42_SDI1_TST"
    titulo     = "Multa 40% FGTS — Aviso Prévio Indenizado"
    base_legal = "OJ 42 SDI-I TST"
    prioridade = 30
    descricao  = (
        "A multa de 40% do FGTS não incide sobre o período do aviso prévio "
        "indenizado. Incide apenas sobre o aviso prévio trabalhado."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            # Se já foi definido explicitamente na sentença, respeita
            if contexto.fgts_multa_40_aviso_previo is not None:
                self._registrar(contexto)
                return contexto

            # Verifica se há aviso prévio indenizado entre as verbas
            tem_ap_indenizado = any(
                "indenizado" in (v.nome or "").lower() and
                "aviso" in (v.nome or "").lower()
                for v in contexto.verbas_deferidas
            )

            if tem_ap_indenizado:
                contexto.fgts_multa_40_aviso_previo = "NAO_INCIDE"
                self._alerta(
                    contexto,
                    "Multa de 40% do FGTS NÃO incide sobre aviso prévio indenizado — OJ 42 SDI-I TST.",
                    nivel="AVISO",
                )
            else:
                contexto.fgts_multa_40_aviso_previo = "INCIDE"
                self._alerta(
                    contexto,
                    "Multa de 40% do FGTS incide sobre aviso prévio trabalhado — OJ 42 SDI-I TST.",
                    nivel="INFO",
                )

            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar OJ 42 SDI-I TST: {e}",
                nivel="ERRO",
            )

        return contexto

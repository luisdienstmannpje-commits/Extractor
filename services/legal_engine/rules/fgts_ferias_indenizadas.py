"""
fgts_ferias_indenizadas.py
Regra: FGTS NÃO incide sobre férias indenizadas.
Fundamento: OJ 195 SDI-I TST
Prioridade: 30 (TST Orientações Jurisprudenciais)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class FgtsFeriasIndenizadasRule(LegalRule):

    id         = "OJ_195_SDI1_TST"
    titulo     = "FGTS — Férias Indenizadas"
    base_legal = "OJ 195 SDI-I TST"
    prioridade = 30
    descricao  = (
        "Sobre as férias indenizadas não incide a contribuição para o FGTS. "
        "Distinguir férias gozadas (incide) de férias indenizadas (não incide)."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            # Se já definido na sentença, respeita
            if contexto.fgts_sobre_ferias_indenizadas is not None:
                self._registrar(contexto)
                return contexto

            # Verifica se há férias indenizadas entre as verbas
            tem_ferias_indenizadas = any(
                "indenizada" in (v.nome or "").lower() and
                "férias" in (v.nome or "").lower()
                for v in contexto.verbas_deferidas
            )

            if tem_ferias_indenizadas:
                contexto.fgts_sobre_ferias_indenizadas = "NAO_INCIDE"
                self._alerta(
                    contexto,
                    "FGTS NÃO incide sobre férias indenizadas — OJ 195 SDI-I TST.",
                    nivel="AVISO",
                )
            else:
                contexto.fgts_sobre_ferias_indenizadas = "NAO_APLICAVEL"
                self._alerta(
                    contexto,
                    "Férias indenizadas não identificadas — OJ 195 SDI-I TST não aplicada.",
                    nivel="INFO",
                )

            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar OJ 195 SDI-I TST: {e}",
                nivel="ERRO",
            )

        return contexto

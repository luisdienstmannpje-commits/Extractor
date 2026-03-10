"""
multa_467.py
Regra: Multa de 50% sobre verbas incontroversas não pagas na rescisão.
Fundamento: Art. 467 CLT
Prioridade: 40 (CLT e legislação federal)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class Multa467Rule(LegalRule):

    id         = "ART_467_CLT"
    titulo     = "Multa Art. 467 CLT — Verbas Incontroversas"
    base_legal = "Art. 467 CLT"
    prioridade = 40
    descricao  = (
        "Em caso de rescisão, havendo controvérsia sobre verbas rescisórias, "
        "o empregador deve pagar a parte incontroversa sob pena de acréscimo "
        "de 50% sobre o valor não pago."
    )

    PERCENTUAL_MULTA = 0.50

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            tem_multa_467 = any(
                "467" in (v.nome or "") or
                "multa_art_467" in (v.nome or "").lower()
                for v in contexto.verbas_deferidas
            )

            if tem_multa_467:
                self._alerta(
                    contexto,
                    "Multa art. 467 CLT identificada — 50% sobre verbas incontroversas. "
                    "Base de cálculo: parcela incontroversa não paga na rescisão.",
                    nivel="AVISO",
                )
            else:
                self._alerta(
                    contexto,
                    "Multa art. 467 CLT não identificada nas verbas deferidas.",
                    nivel="INFO",
                )

            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar Art. 467 CLT: {e}",
                nivel="ERRO",
            )

        return contexto

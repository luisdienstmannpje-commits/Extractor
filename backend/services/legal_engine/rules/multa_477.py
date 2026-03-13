"""
multa_477.py
Regra: Multa por atraso no pagamento das verbas rescisórias.
Fundamento: Art. 477 §8º CLT
Prioridade: 40 (CLT e legislação federal)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class Multa477Rule(LegalRule):

    id         = "ART_477_CLT"
    titulo     = "Multa Art. 477 CLT — Atraso Rescisório"
    base_legal = "Art. 477 §8º CLT"
    prioridade = 40
    descricao  = (
        "O empregador que não pagar as verbas rescisórias no prazo de 10 dias "
        "após o término do contrato fica sujeito a multa equivalente a 1 salário "
        "base do empregado."
    )

    PRAZO_DIAS    = 10
    MULTA_VALOR   = "um_salario_base"

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            tem_multa_477 = any(
                "477" in (v.nome or "") or
                "multa_art_477" in (v.nome or "").lower()
                for v in contexto.verbas_deferidas
            )

            if tem_multa_477:
                self._alerta(
                    contexto,
                    "Multa art. 477 CLT identificada — equivalente a 1 salário base. "
                    f"Prazo legal: {self.PRAZO_DIAS} dias após término do contrato.",
                    nivel="AVISO",
                )
            else:
                self._alerta(
                    contexto,
                    "Multa art. 477 CLT não identificada nas verbas deferidas.",
                    nivel="INFO",
                )

            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar Art. 477 CLT: {e}",
                nivel="ERRO",
            )

        return contexto

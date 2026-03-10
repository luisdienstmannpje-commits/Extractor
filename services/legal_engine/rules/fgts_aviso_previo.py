"""
fgts_aviso_previo.py
Regra: FGTS incide sobre aviso prévio trabalhado e indenizado.
Fundamento: Súmula 305 TST
Prioridade: 20 (TST Súmulas)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class FgtsAvisoPrevioRule(LegalRule):

    id         = "SUMULA_305_TST"
    titulo     = "FGTS sobre Aviso Prévio"
    base_legal = "Súmula 305 TST"
    prioridade = 20
    descricao  = (
        "O pagamento relativo ao período de aviso prévio, trabalhado ou não, "
        "está sujeito à contribuição para o FGTS."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            # Se já foi definido explicitamente na sentença, respeita
            if contexto.fgts_sobre_aviso_previo is not None:
                self._registrar(contexto)
                return contexto

            # Aplica a súmula: FGTS incide sobre AP trabalhado e indenizado
            contexto.fgts_sobre_aviso_previo = "SIM"

            self._alerta(
                contexto,
                "FGTS incide sobre aviso prévio (trabalhado e indenizado) — Súmula 305 TST.",
                nivel="INFO",
            )
            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar Súmula 305 TST: {e}",
                nivel="ERRO",
            )

        return contexto

"""
aviso_previo_proporcional.py
Regra: Calcula dias de aviso prévio proporcional.
Fundamento: Art. 487 CLT + Lei 12.506/2011
Prioridade: 40 (CLT e legislação federal)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class AvisoPrevioProporcionaRule(LegalRule):

    id         = "ART_487_CLT_LEI_12506"
    titulo     = "Aviso Prévio Proporcional"
    base_legal = "Art. 487 CLT + Lei 12.506/2011"
    prioridade = 40
    descricao  = (
        "O aviso prévio é de no mínimo 30 dias, acrescido de 3 dias por ano "
        "de serviço prestado, até o máximo de 90 dias (20 anos de contrato)."
    )

    MINIMO_DIAS   = 30
    DIAS_POR_ANO  = 3
    MAXIMO_ANOS   = 20
    MAXIMO_DIAS   = 90

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            # Se já definido na sentença, respeita
            if contexto.aviso_previo_dias is not None:
                self._registrar(contexto)
                return contexto

            # Calcula anos de contrato
            anos = self._calcular_anos(contexto)
            if anos is None:
                self._alerta(
                    contexto,
                    "Aviso prévio proporcional não calculado — datas de admissão/demissão ausentes.",
                    nivel="AVISO",
                )
                return contexto

            dias = self.MINIMO_DIAS + (min(anos, self.MAXIMO_ANOS) * self.DIAS_POR_ANO)
            dias = min(dias, self.MAXIMO_DIAS)

            contexto.aviso_previo_dias = str(dias)

            self._alerta(
                contexto,
                f"Aviso prévio proporcional calculado: {dias} dias "
                f"({anos} ano(s) de contrato) — Art. 487 CLT + Lei 12.506/2011.",
                nivel="INFO",
            )
            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao calcular aviso prévio proporcional: {e}",
                nivel="ERRO",
            )

        return contexto

    def _calcular_anos(self, contexto: ContextoJuridico):
        """Calcula anos completos de contrato."""
        try:
            from datetime import date
            adm = date.fromisoformat(contexto.data_admissao)
            dem = date.fromisoformat(contexto.data_demissao)
            anos = (dem - adm).days // 365
            return max(anos, 0)
        except (TypeError, ValueError):
            return None

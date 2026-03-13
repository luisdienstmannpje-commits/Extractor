"""
honorarios_advocaticios.py
Regra: Valida e completa parâmetros de honorários advocatícios sucumbenciais.
Fundamento: Art. 791-A CLT
Prioridade: 40 (CLT e legislação federal)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class HonorariosAdvocaticiosRule(LegalRule):

    id         = "ART_791A_CLT"
    titulo     = "Honorários Advocatícios Sucumbenciais"
    base_legal = "Art. 791-A CLT"
    prioridade = 40
    descricao  = (
        "Os honorários advocatícios sucumbenciais são devidos entre 5% e 15% "
        "sobre o valor que resultar da liquidação da sentença. "
        "Introduzido pela Reforma Trabalhista (Lei 13.467/2017)."
    )

    PERCENTUAL_MINIMO = 5.0
    PERCENTUAL_MAXIMO = 15.0

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            tipo_hon = contexto.honorarios_sucumbenciais
            pct_raw = contexto.percentual_honorarios

            # Alerta de omissão APENAS quando nenhum dos dois campos veio preenchido
            if (not tipo_hon) and (not pct_raw):
                self._alerta(
                    contexto,
                    "Honorários advocatícios sucumbenciais não identificados na sentença.",
                    nivel="INFO",
                )
                self._registrar(contexto)
                return contexto

            # Se há indicação clara de que NÃO há honorários devidos, não valida percentual
            if tipo_hon not in ("SIM", "sim", True, "true", "1"):
                self._registrar(contexto)
                return contexto

            # Valida percentual informado
            percentual = None
            if contexto.percentual_honorarios:
                try:
                    percentual = float(contexto.percentual_honorarios)
                except (ValueError, TypeError):
                    percentual = None

            if percentual is None:
                self._alerta(
                    contexto,
                    "Honorários devidos mas percentual não identificado — "
                    f"faixa legal: {self.PERCENTUAL_MINIMO}% a {self.PERCENTUAL_MAXIMO}% "
                    "(Art. 791-A CLT). Verificar na sentença.",
                    nivel="AVISO",
                )
            elif not (self.PERCENTUAL_MINIMO <= percentual <= self.PERCENTUAL_MAXIMO):
                self._alerta(
                    contexto,
                    f"Percentual de honorários fora da faixa legal: {percentual}% "
                    f"(permitido: {self.PERCENTUAL_MINIMO}% a {self.PERCENTUAL_MAXIMO}%) "
                    "— Art. 791-A CLT.",
                    nivel="ERRO",
                )
            else:
                self._alerta(
                    contexto,
                    f"Honorários advocatícios: {percentual}% — dentro da faixa legal "
                    f"({self.PERCENTUAL_MINIMO}% a {self.PERCENTUAL_MAXIMO}%) — Art. 791-A CLT.",
                    nivel="INFO",
                )

            self._registrar(contexto)

        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar Art. 791-A CLT: {e}",
                nivel="ERRO",
            )

        return contexto

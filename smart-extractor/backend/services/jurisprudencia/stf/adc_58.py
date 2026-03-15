"""
ADC 58 STF — Correção Monetária Trabalhista

Regra:
  - Pré-ajuizamento: IPCA-E
  - Pós-ajuizamento: SELIC (já inclui juros — afasta juros moratórios separados)

Base legal:
  ADC 58 / STF — julgado em 18/12/2020
  Tema 1.191 STF
"""

from datetime import date
from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class ADC58CorrecaoMonetaria(LegalRule):

    id          = "ADC_58_STF"
    titulo      = "Correção monetária trabalhista — IPCA-E + SELIC"
    base_legal  = "ADC 58/STF — Tema 1.191 STF (18/12/2020)"
    prioridade  = 10  # STF — máxima prioridade
    descricao   = (
        "O STF, no julgamento da ADC 58, fixou que os créditos trabalhistas "
        "devem ser corrigidos pelo IPCA-E na fase pré-judicial e pela taxa SELIC "
        "a partir do ajuizamento. A SELIC já embute juros — não se aplica juros "
        "moratórios separados na fase judicial."
    )
    vigencia_inicio = date(2020, 12, 18)

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        indice = (contexto.indice_correcao or "").lower()

        usa_ipca_selic = ("ipca" in indice and "selic" in indice)
        usa_tr = "tr" in indice and "ipca" not in indice

        if usa_ipca_selic:
            contexto.correcao_pre_judicial = "IPCA-E"
            contexto.correcao_judicial     = "SELIC"
            contexto.juros_judicial        = "sem_juros_separados"
            self._registrar(contexto)

        elif usa_tr:
            self._alerta(
                contexto,
                "ADC 58/STF: índice TR pode estar desatualizado. "
                "O STF determinou IPCA-E (pré-ajuizamento) + SELIC (pós-ajuizamento). "
                "Verificar se a sentença é anterior a 18/12/2020.",
                nivel="AVISO",
            )
            self._registrar(contexto)

        elif indice and "selic" in indice and "ipca" not in indice:
            contexto.correcao_judicial = "SELIC"
            contexto.juros_judicial    = "sem_juros_separados"
            self._registrar(contexto)

        return contexto

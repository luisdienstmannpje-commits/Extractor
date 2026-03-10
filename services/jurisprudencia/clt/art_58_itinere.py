"""
art_58_itinere.py — Art. 58 §2º CLT — Horas In Itinere (extintas pela Reforma Trabalhista)

Fundamento: Lei 13.467/2017, art. 1º (revogou o §2º do art. 58 da CLT)
Vigência:   A partir de 11/11/2017

Lógica:
  - Regra aplicável a contratos ADMITIDOS a partir de 11/11/2017 (data_admissao)
  - Se encontrar verba de horas in itinere DEFERIDA em contrato pós-reforma → ERRO
  - Pré-reforma: engine descarta a regra via is_aplicavel() → sem alerta
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


_PADROES_ITINERE = re.compile(
    r"in\s*itinere"
    r"|horas?\s*de\s*deslocamento"
    r"|percurso\s*casa\s*trabalho"
    r"|tempo\s*de\s*deslocamento"
    r"|horas?\s*trajet",
    re.IGNORECASE,
)


class Art58ItinereReforma(LegalRule):
    """
    Detecta horas in itinere deferidas em contratos pós-reforma — direito extinto.

    A Lei 13.467/2017 revogou o §2º do art. 58 da CLT, eliminando o direito
    a horas in itinere. Qualquer deferimento em contrato admitido após 11/11/2017
    representa risco jurídico relevante e deve ser sinalizado como ERRO.
    """

    id          = "ART_58_ITINERE_REFORMA"
    titulo      = "Horas In Itinere — extintas pela Reforma Trabalhista"
    base_legal  = "Art. 58 §2º CLT revogado pela Lei 13.467/2017, art. 1º"
    prioridade  = 40
    descricao   = (
        "A Reforma Trabalhista (Lei 13.467/2017) revogou o §2º do art. 58 da CLT, "
        "extinguindo o direito a horas in itinere para contratos iniciados a partir "
        "de 11/11/2017. Verbas com este nome deferidas nesse período indicam risco "
        "de reforma em grau de recurso."
    )

    data_ref_campo  = "data_admissao"
    vigencia_inicio = date(2017, 11, 11)

    def is_aplicavel(self, data_referencia: Optional[date] = None) -> bool:
        if data_referencia is None:
            return True
        return data_referencia >= self.vigencia_inicio

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        self._registrar(contexto)

        for verba in contexto.verbas_deferidas:
            status = (verba.status_final or "").lower()
            if status not in ("deferida", "deferido", ""):
                continue

            if _PADROES_ITINERE.search(verba.nome):
                self._alerta(
                    contexto,
                    mensagem=(
                        f"Verba '{verba.nome}' foi DEFERIDA, mas horas in itinere foram "
                        f"extintas pela Reforma Trabalhista (Lei 13.467/2017) para contratos "
                        f"iniciados a partir de 11/11/2017. Risco de reforma em recurso."
                    ),
                    nivel="ERRO",
                )

        return contexto

"""
Art. 791-A CLT — Honorários Advocatícios Sucumbenciais

Regra:
  Honorários entre 5% e 15% sobre o proveito econômico ou valor da causa.

Base legal:
  Art. 791-A CLT — Lei 13.467/2017 (Reforma Trabalhista)
"""

import re
from datetime import date
from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class Art791AHonorarios(LegalRule):

    id          = "ART_791A_CLT"
    titulo      = "Art. 791-A CLT — Honorários sucumbenciais (5% a 15%)"
    base_legal  = "Art. 791-A CLT — Lei 13.467/2017"
    prioridade  = 40
    descricao   = (
        "Honorários advocatícios na Justiça do Trabalho: entre 5% e 15%. "
        "Vigente desde 11/11/2017 (Reforma Trabalhista)."
    )
    vigencia_inicio = date(2017, 11, 11)

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        pct_str = (contexto.percentual_honorarios or "").strip()

        if not pct_str:
            return contexto

        m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", pct_str)
        if not m:
            return contexto

        pct = float(m.group(1).replace(",", "."))

        if pct < 5:
            self._alerta(
                contexto,
                f"Art. 791-A CLT: honorários de {pct}% abaixo do mínimo de 5%.",
                nivel="AVISO",
            )
        elif pct > 15:
            self._alerta(
                contexto,
                f"Art. 791-A CLT: honorários de {pct}% acima do máximo de 15%.",
                nivel="AVISO",
            )

        self._registrar(contexto)
        return contexto

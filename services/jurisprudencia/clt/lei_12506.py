"""
Lei 12.506/2011 — Aviso Prévio Proporcional ao Tempo de Serviço

Regra:
  Mínimo 30 dias, máximo 90 dias (+3 dias por ano além do primeiro).

Base legal:
  Lei 12.506/2011 — Art. 487 CLT
"""

import re
from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class Lei12506AvisoPrevio(LegalRule):

    id          = "LEI_12506_2011"
    titulo      = "Lei 12.506/2011 — Aviso prévio proporcional (30–90 dias)"
    base_legal  = "Lei 12.506/2011 — Art. 487 CLT"
    prioridade  = 40
    descricao   = (
        "Aviso prévio mínimo de 30 dias e máximo de 90 dias, "
        "com acréscimo de 3 dias por ano de serviço além do primeiro."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        aviso = (contexto.aviso_previo_dias or "").strip()

        if not aviso:
            return contexto

        m = re.search(r"(\d+)\s*dias?", aviso, re.IGNORECASE)
        if not m:
            return contexto

        dias = int(m.group(1))

        if dias < 30:
            self._alerta(
                contexto,
                f"Lei 12.506/2011 / Art. 487 CLT: aviso prévio de {dias} dias "
                f"abaixo do mínimo legal de 30 dias.",
                nivel="AVISO",
            )
        elif dias > 90:
            self._alerta(
                contexto,
                f"Lei 12.506/2011: aviso prévio de {dias} dias excede o máximo de 90 dias.",
                nivel="AVISO",
            )

        self._registrar(contexto)
        return contexto

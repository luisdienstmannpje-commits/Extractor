"""
datas.py — Consistência Cronológica de Datas do Processo

Valida a ordem lógica: admissão < demissão < ajuizamento < sentença.
"""

from datetime import datetime, date
from typing import Optional
from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class CronologiaDatas(LegalRule):

    id          = "CONSISTENCIA_DATAS"
    titulo      = "Consistência cronológica das datas do processo"
    base_legal  = "Consistência lógica — sem base normativa específica"
    prioridade  = 50
    descricao   = (
        "Verifica se as datas respeitam a ordem: "
        "admissão → demissão → ajuizamento → sentença."
    )

    @staticmethod
    def _parse(data_str: Optional[str]) -> Optional[date]:
        if not data_str:
            return None
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(data_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        admis    = self._parse(contexto.data_admissao)
        demis    = self._parse(contexto.data_demissao)
        ajuiz    = self._parse(contexto.data_ajuizamento)
        sentenca = self._parse(contexto.data_sentenca)

        if admis and demis and admis > demis:
            self._alerta(
                contexto,
                f"Data de admissão ({contexto.data_admissao}) é posterior à "
                f"data de demissão ({contexto.data_demissao}). Dados incorretos.",
                nivel="ERRO",
            )

        if demis and ajuiz and demis > ajuiz:
            self._alerta(
                contexto,
                f"Data de demissão ({contexto.data_demissao}) é posterior ao "
                f"ajuizamento ({contexto.data_ajuizamento}). Verificar extração.",
                nivel="AVISO",
            )

        if ajuiz and sentenca and ajuiz > sentenca:
            self._alerta(
                contexto,
                f"Data de ajuizamento ({contexto.data_ajuizamento}) é posterior "
                f"à sentença ({contexto.data_sentenca}). Ordem cronológica inválida.",
                nivel="ERRO",
            )

        if admis and ajuiz and admis > ajuiz:
            self._alerta(
                contexto,
                f"Data de admissão ({contexto.data_admissao}) é posterior ao "
                f"ajuizamento ({contexto.data_ajuizamento}). Verificar datas.",
                nivel="AVISO",
            )

        self._registrar(contexto)
        return contexto

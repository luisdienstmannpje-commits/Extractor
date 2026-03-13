"""
lab_discrepância_verba_ausente_20260313_030848.py — RASCUNHO GERADO PELO LABORATÓRIO DE APRENDIZADO

Título:      Discrepância: verba_ausente
Base legal:  artigo 467 e 477 da CLT
Gerado em:   2026-03-13T03:08:48.443012

ATENÇÃO: Revise o método `aplicar` antes de usar em produção.
Para ativar: renomeie sem prefixo "lab_" e implemente a lógica.
"""
from __future__ import annotations

from services.legal_engine.rule_base import ContextoJuridico, LegalRule


class LabRegra20260313030848Rule(LegalRule):
    """
    Deferido: intervalo intrajornada

    Correção identificada pela perita:
    Incluir verba conforme sentença. Trecho da manifestação: b)  INTERVALO INTRAJORNADA
    """

    id = "LAB_DISCREPÂNCIA_VERBA_AUSENTE_20260313_030848"
    titulo = "Discrepância: verba_ausente"
    base_legal = "artigo 467 e 477 da CLT"
    prioridade = 40
    descricao = "Deferido: intervalo intrajornada"

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            # TODO: implemente a condição de acionamento desta regra.
            # Exemplo:
            #   if not contexto.indice_correcao:
            #       self._alerta(contexto, "Índice ausente", nivel="ERRO")
            pass
            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra {self.id}: {e}",
                nivel="AVISO",
            )
        return contexto

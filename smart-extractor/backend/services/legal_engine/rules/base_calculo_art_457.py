"""
base_calculo_art_457.py — Consistência: base de cálculo global (art. 457 CLT)

A perita, em manifestações típicas, lembra que a base de cálculo de verbas que
demandam integração (horas extras, adicional noturno etc.) deve incluir todas
as parcelas salariais previstas no art. 457 da CLT, inclusive férias + 1/3 gozadas
e reflexos de horas extras. Esta regra gera um INFO para o perito conferir
a planilha/Excel antes de gerar o resultado final.
"""
from __future__ import annotations

import re
from services.legal_engine.rule_base import LegalRule, ContextoJuridico, VerbaContexto


# Verbas que tipicamente demandam "base de cálculo global" (integração art. 457)
_PATTERNS_BASE_GLOBAL = [
    re.compile(r"horas?\s*extras?", re.IGNORECASE),
    re.compile(r"adicional\s*noturno", re.IGNORECASE),
    re.compile(r"insalubridade|periculosidade", re.IGNORECASE),
    re.compile(r"intervalo\s*intrajornada", re.IGNORECASE),
]


def _exige_base_global(nome: str) -> bool:
    """True se a verba costuma exigir base de cálculo nos termos do art. 457."""
    if not nome or not isinstance(nome, str):
        return False
    return any(p.search(nome) for p in _PATTERNS_BASE_GLOBAL)


class BaseCalculoArt457Rule(LegalRule):
    """
    Consistência: lembrete sobre base de cálculo nos termos do art. 457 da CLT.

    Quando existem verbas principais que demandam integração (HE, adicional
    noturno, insalubridade, intervalo intrajornada etc.), a base de cálculo
    deve abranger todas as parcelas salariais do art. 457 da CLT, incluindo
    férias + 1/3 gozadas e reflexos de horas extras. Gera INFO para o perito
    conferir antes de gerar o Excel.
    """

    id = "CONSISTENCIA_BASE_CALCULO_ART_457"
    titulo = "Base de cálculo — art. 457 CLT"
    base_legal = "Art. 457 da CLT — parcelas que compõem a remuneração para reflexos"
    prioridade = 50
    descricao = (
        "Emite INFO lembrando que a base de cálculo das verbas que demandam "
        "integração deve incluir todas as parcelas salariais do art. 457 da CLT."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            verbas = list(contexto.verbas_deferidas or [])
            demandam_base_global = []
            for v in verbas:
                nome = v.nome if isinstance(v, VerbaContexto) else getattr(v, "nome", "") or ""
                if _exige_base_global(nome):
                    demandam_base_global.append(nome)

            if demandam_base_global:
                self._alerta(
                    contexto,
                    (
                        "Atenção: A base de cálculo das verbas que demandam integração "
                        "(ex.: horas extras, adicional noturno, insalubridade, intervalo intrajornada) "
                        "deve incluir todas as parcelas salariais previstas no art. 457 da CLT, "
                        "inclusive férias + 1/3 gozadas e reflexos de horas extras. "
                        "Conferir na planilha/Excel antes de gerar o resultado final."
                    ),
                    nivel="INFO",
                )

            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de base de cálculo art. 457: {e}",
                nivel="AVISO",
            )
        return contexto

"""
verba_deduplicator.py — Skill S9: Deduplicação de Verbas Pós-IA

Responsabilidades:
  1. deduplicar_verbas(verbas)  — função utilitária pura (usada pelo processor.py)
     Remove verbas duplicadas da lista retornada pela IA.
     Critério de duplicata: mesmo nome canônico + mesmo período.
     Retorna (verbas_limpas, alertas_gerados).

  2. VerbaDeduplicator          — LegalRule (prioridade 50)
     Roda no legal engine, emite AVISO no memorial jurídico quando
     duplicatas foram detectadas e removidas.

Integração no pipeline:
  processor.py  →  deduplicar_verbas()  →  remove silenciosamente + loga [DEDUP]
  legal_engine  →  VerbaDeduplicator    →  AVISO visível no frontend
"""

from __future__ import annotations

import re
from typing import List, Tuple

from services.legal_engine.rule_base import ContextoJuridico, LegalRule, VerbaContexto


# ─── Mapa canônico (mesmo do rule_base._canonizar_verba) ─────────────────────
_MAPA_CANONICO = [
    (re.compile(r"horas?\s*extras?",                re.I), "horas_extras"),
    (re.compile(r"adicional\s*noturno",             re.I), "adicional_noturno"),
    (re.compile(r"adicional\s*de\s*insalubridade",  re.I), "insalubridade"),
    (re.compile(r"adicional\s*de\s*periculosidade", re.I), "periculosidade"),
    (re.compile(r"dsr|descanso\s*semanal",          re.I), "dsr"),
    (re.compile(r"f\.?g\.?t\.?s",                   re.I), "fgts"),
    (re.compile(r"f[eé]rias",                       re.I), "ferias"),
    (re.compile(r"13[°º]?\s*sal[aá]rio|gratifica",  re.I), "decimo_terceiro"),
    (re.compile(r"aviso\s*pr[eé]vio",               re.I), "aviso_previo"),
    (re.compile(r"saldo\s*de\s*sal[aá]rio",         re.I), "saldo_salario"),
    (re.compile(r"intervalo\s*intrajornada",        re.I), "intervalo_intrajornada"),
    (re.compile(r"dano\s*moral",                    re.I), "dano_moral"),
    (re.compile(r"dano\s*material",                 re.I), "dano_material"),
    (re.compile(r"multa.*467",                      re.I), "multa_467"),
    (re.compile(r"multa.*477",                      re.I), "multa_477"),
    (re.compile(r"seguro.desemprego",               re.I), "seguro_desemprego"),
]


def _canonizar(nome: str) -> str:
    """Retorna chave canônica do nome da verba, ou o próprio nome normalizado."""
    n = (nome or "").strip().lower()
    for pattern, canonico in _MAPA_CANONICO:
        if pattern.search(n):
            return canonico
    return n


def _assinatura(verba: dict) -> str:
    """
    Chave única de uma verba: nome canônico + período normalizado.
    Duas verbas com mesma assinatura são consideradas duplicatas.
    """
    nome     = _canonizar(verba.get("nome", "") or "")
    periodo  = (verba.get("periodo", "") or "").strip().lower()
    return f"{nome}|{periodo}"


def deduplicar_verbas(verbas: List[dict]) -> Tuple[List[dict], List[str]]:
    """
    Remove verbas duplicadas de uma lista de dicts retornada pela IA.

    Critério: mesmo nome canônico + mesmo período.
    Mantém a PRIMEIRA ocorrência, remove as subsequentes.

    Args:
        verbas: lista de dicts com campos da verba (nome, periodo, ...)

    Returns:
        (verbas_limpas, mensagens_aviso)
        - verbas_limpas : lista sem duplicatas
        - mensagens_aviso: lista de strings para log [DEDUP]
    """
    vistas:   set         = set()
    limpas:   List[dict]  = []
    avisos:   List[str]   = []

    for verba in verbas:
        sig = _assinatura(verba)
        if sig in vistas:
            nome    = verba.get("nome", "?")
            periodo = verba.get("periodo", "") or "período não informado"
            msg = (
                f"[DEDUP] Verba duplicada removida: '{nome}' "
                f"(período: {periodo}). Mantida primeira ocorrência."
            )
            avisos.append(msg)
            print(msg)
        else:
            vistas.add(sig)
            limpas.append(verba)

    return limpas, avisos


# ─── LegalRule — integração com o legal engine ───────────────────────────────

class VerbaDeduplicator(LegalRule):
    """
    Skill S9: Detecta e alerta sobre verbas duplicadas no contexto jurídico.

    Roda no legal engine APÓS o processor.py já ter removido as duplicatas.
    Função aqui: emitir AVISO visível no memorial jurídico do frontend.

    Critério: mesmo nome canônico + mesmo período → duplicata.
    """

    id         = "S9_VERBA_DEDUPLICATOR"
    titulo     = "Deduplicação de Verbas Pós-IA"
    base_legal = "Boas práticas de cálculo — integridade do JSON extraído"
    prioridade = 50
    descricao  = (
        "Detecta verbas com mesmo nome e período retornadas mais de uma vez pela IA. "
        "Duplicatas causam erro de cálculo no PJeCalc (verba contada duas vezes)."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            vistas: set = set()

            for verba in contexto.verbas_deferidas:
                # Constrói dict temporário para reaproveitar _assinatura
                v_dict = {
                    "nome":    verba.nome,
                    "periodo": verba.periodo,
                }
                sig = _assinatura(v_dict)

                if sig in vistas:
                    periodo = verba.periodo or "período não informado"
                    self._alerta(
                        contexto,
                        f"[AVISO] Verba duplicada detectada: '{verba.nome}' "
                        f"(período: {periodo}). "
                        f"Verificar se a IA retornou a mesma verba duas vezes — "
                        f"duplicata causa erro de cálculo no PJeCalc.",
                        nivel="AVISO",
                    )
                else:
                    vistas.add(sig)

            self._registrar(contexto)

        except Exception as exc:
            self._alerta(
                contexto,
                f"[AVISO] Falha interna no deduplicador: {exc}",
                nivel="AVISO",
            )
            self._registrar(contexto)

        return contexto
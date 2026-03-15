from __future__ import annotations
import re
from typing import List, Tuple
from services.legal_engine.rule_base import ContextoJuridico, LegalRule, VerbaContexto

_MAPA = [
    (re.compile(r"horas?\s*extras?", re.I), "horas_extras"),
    (re.compile(r"adicional\s*noturno", re.I), "adicional_noturno"),
    (re.compile(r"adicional\s*de\s*insalubridade", re.I), "insalubridade"),
    (re.compile(r"adicional\s*de\s*periculosidade", re.I), "periculosidade"),
    (re.compile(r"dsr|descanso\s*semanal", re.I), "dsr"),
    (re.compile(r"f\.?g\.?t\.?s", re.I), "fgts"),
    (re.compile(r"f[eé]rias", re.I), "ferias"),
    (re.compile(r"13[°º]?\s*sal[aá]rio|gratifica", re.I), "decimo_terceiro"),
    (re.compile(r"aviso\s*pr[eé]vio", re.I), "aviso_previo"),
    (re.compile(r"saldo\s*de\s*sal[aá]rio", re.I), "saldo_salario"),
    (re.compile(r"intervalo\s*intrajornada", re.I), "intervalo_intrajornada"),
    (re.compile(r"dano\s*moral", re.I), "dano_moral"),
    (re.compile(r"dano\s*material", re.I), "dano_material"),
    (re.compile(r"multa.*467", re.I), "multa_467"),
    (re.compile(r"multa.*477", re.I), "multa_477"),
    (re.compile(r"seguro.desemprego", re.I), "seguro_desemprego"),
]

def _canonizar(nome):
    n = (nome or "").strip().lower()
    for pat, can in _MAPA:
        if pat.search(n):
            return can
    return n

def _assinatura(verba):
    nome    = _canonizar(verba.get("nome", "") or "")
    periodo = (verba.get("periodo", "") or "").strip().lower()
    return f"{nome}|{periodo}"

def deduplicar_verbas(verbas):
    vistas, limpas, avisos = set(), [], []
    for verba in verbas:
        sig = _assinatura(verba)
        if sig in vistas:
            nome    = verba.get("nome", "?")
            periodo = verba.get("periodo", "") or "periodo nao informado"
            msg = f"[DEDUP] Verba duplicada removida: '{nome}' (periodo: {periodo})."
            avisos.append(msg)
            print(msg)
        else:
            vistas.add(sig)
            limpas.append(verba)
    return limpas, avisos

class VerbaDeduplicator(LegalRule):
    id         = "S9_VERBA_DEDUPLICATOR"
    titulo     = "Deduplicacao de Verbas Pos-IA"
    base_legal = "Boas praticas de calculo"
    prioridade = 50

    def aplicar(self, contexto):
        try:
            vistas = set()
            for verba in contexto.verbas_deferidas:
                sig = _assinatura({"nome": verba.nome, "periodo": verba.periodo})
                if sig in vistas:
                    periodo = verba.periodo or "periodo nao informado"
                    self._alerta(contexto,
                        f"[AVISO] Verba duplicada: '{verba.nome}' (periodo: {periodo}). "
                        f"Duplicata causa erro de calculo no PJeCalc.",
                        nivel="AVISO")
                else:
                    vistas.add(sig)
            self._registrar(contexto)
        except Exception as exc:
            self._alerta(contexto, f"[AVISO] Falha interna: {exc}", nivel="AVISO")
            self._registrar(contexto)
        return contexto

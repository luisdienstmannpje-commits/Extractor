"""
verbas.py — Bis in Idem em Reflexos de Verbas Trabalhistas

Uma verba não pode aparecer como reflexo de si mesma.
"""

import re
from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class BisInIdem(LegalRule):

    id          = "BIS_IN_IDEM_VERBAS"
    titulo      = "Bis in idem — verba não pode refletir em si mesma"
    base_legal  = "Vedação ao bis in idem — jurisprudência TST"
    prioridade  = 50
    descricao   = (
        "Detecta verbas que aparecem como reflexo de si mesmas. "
        "Configura bis in idem e deve ser corrigido antes dos cálculos."
    )

    _MAPA = {
        r"horas?\s*extras?":                "horas extras",
        r"adicional\s*noturno":             "adicional noturno",
        r"adicional\s*de\s*insalubridade":  "adicional de insalubridade",
        r"adicional\s*de\s*periculosidade": "adicional de periculosidade",
        r"dsr|descanso\s*semanal":          "dsr",
        r"f\.?g\.?t\.?s":                 "fgts",
        r"f[eé]rias":                        "férias",
        r"13[°º]?\s*sal[aá]rio|gratifica":  "13º salário",
        r"aviso\s*pr[eé]vio":               "aviso prévio",
        r"saldo\s*de\s*sal[aá]rio":        "saldo de salário",
        r"dano\s*moral":                    "dano moral",
        r"dano\s*material":                 "dano material",
    }

    def _canonizar(self, nome: str) -> str:
        n = nome.lower().strip()
        for pattern, canonico in self._MAPA.items():
            if re.search(pattern, n, re.IGNORECASE):
                return canonico
        return n

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        for verba in contexto.verbas_deferidas:
            nome_canon = self._canonizar(verba.nome or "")
            reflexos_canon = [self._canonizar(r) for r in (verba.reflexos or [])]

            if nome_canon in reflexos_canon:
                self._alerta(
                    contexto,
                    f"Bis in idem: '{verba.nome}' aparece como reflexo de si mesma.",
                    nivel="ERRO",
                )

        self._registrar(contexto)
        return contexto

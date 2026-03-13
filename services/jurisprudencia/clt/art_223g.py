"""
art_223g.py — Art. 223-G CLT — Tabelamento de Dano Extrapatrimonial

Fundamento: Lei 13.467/2017 — inseriu os arts. 223-A a 223-G na CLT
Vigência:   A partir de 11/11/2017

Nota STF — ADI 6050 / ADI 6069 / ADI 6082 (julgamento conjunto, 2021):
  O STF deu interpretação conforme à Constituição: os valores do art. 223-G
  são PARÂMETROS (não tetos absolutos), podendo o juiz arbitrar acima deles
  desde que fundamentado. A tabelação não é inconstitucional, mas também
  não é teto rígido.

Lógica:
  - Regra aplicável a contratos ADMITIDOS a partir de 11/11/2017
  - Faixas de tarifação (art. 223-G §1º CLT):
      Leve:       até  3x o salário contratual   → INFO
      Médio:      até  5x o salário contratual   → INFO
      Grave:      até 20x o salário contratual   → INFO
      Gravíssimo: até 50x o salário contratual   → INFO
      Acima de gravíssimo: > 50x                 → AVISO (risco recursal)
  - Se não for possível parsear salário ou valor → INFO orientativo sem faixa
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


_PADROES_DANO = re.compile(
    r"dano\s*moral"
    r"|danos?\s*morais"
    r"|dano\s*extrapatrimonial"
    r"|danos?\s*extrapatrimoniais"
    r"|indeniza[çc][aã]o\s+por\s+dano\s+moral",
    re.IGNORECASE,
)

_RE_VALOR = re.compile(r"R?\$?\s*([\d.,]+)", re.IGNORECASE)

_FAIXAS = [
    (3,   "leve"),
    (5,   "médio"),
    (20,  "grave"),
    (50,  "gravíssimo"),
]

_NOTA_STF = (
    "Parâmetros do art. 223-G CLT — STF (ADI 6050/6069/6082): tabelação é constitucional, "
    "mas funciona como parâmetro orientativo, não como teto absoluto."
)


def _parse_valor_br(texto: Optional[str]) -> Optional[float]:
    if not texto:
        return None
    m = _RE_VALOR.search(texto)
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _classificar_faixa(multiplo: float) -> str:
    for limite, nome in _FAIXAS:
        if multiplo <= limite:
            return nome
    return "acima de gravíssimo"


class Art223GDanoExtrapatrimonial(LegalRule):
    """
    Verifica se o valor de dano extrapatrimonial deferido está dentro das faixas
    do art. 223-G CLT e emite alerta informativo ou de aviso conforme o caso.
    """

    id          = "ART_223G_DANO_EXTRAPATRIMONIAL"
    titulo      = "Tarifação de Dano Extrapatrimonial — Art. 223-G CLT"
    base_legal  = "Art. 223-G §1º CLT (Lei 13.467/2017); ADI 6050/6069/6082 STF"
    prioridade  = 40
    descricao   = (
        "O art. 223-G §1º CLT define faixas de tarifação para dano extrapatrimonial: "
        "leve (3x), médio (5x), grave (20x) e gravíssimo (50x) o salário contratual. "
        "O STF (ADI 6050) entendeu que esses valores são parâmetros orientativos. "
        "Valores acima de 50x indicam risco recursal."
    )

    data_ref_campo  = "data_admissao"
    vigencia_inicio = date(2017, 11, 11)

    def is_aplicavel(self, data_referencia: Optional[date] = None) -> bool:
        if data_referencia is None:
            return True
        return data_referencia >= self.vigencia_inicio

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        self._registrar(contexto)

        salario = _parse_valor_br(contexto.salario_base)

        for verba in contexto.verbas_deferidas:
            status = (verba.status_final or "").lower()
            if status not in ("deferida", "deferido", ""):
                continue

            if not _PADROES_DANO.search(verba.nome):
                continue

            valor_dano = _parse_valor_br(verba.valor_fixado)

            if valor_dano is None or salario is None or salario <= 0:
                self._alerta(
                    contexto,
                    mensagem=(
                        f"Verba '{verba.nome}' deferida. Verificar enquadramento nas faixas "
                        f"do art. 223-G §1º CLT (leve=3x, médio=5x, grave=20x, gravíssimo=50x "
                        f"o salário). {_NOTA_STF}"
                    ),
                    nivel="INFO",
                )
                continue

            multiplo = valor_dano / salario
            faixa    = _classificar_faixa(multiplo)

            if faixa == "acima de gravíssimo":
                self._alerta(
                    contexto,
                    mensagem=(
                        f"Verba '{verba.nome}': R$ {valor_dano:,.2f} representa "
                        f"{multiplo:.1f}x o salário — ACIMA da faixa gravíssimo (50x). "
                        f"Risco elevado de reforma em recurso. {_NOTA_STF}"
                    ),
                    nivel="AVISO",
                )
            else:
                self._alerta(
                    contexto,
                    mensagem=(
                        f"Verba '{verba.nome}': R$ {valor_dano:,.2f} ({multiplo:.1f}x o salário) "
                        f"— faixa '{faixa}' do art. 223-G §1º CLT. {_NOTA_STF}"
                    ),
                    nivel="INFO",
                )

        return contexto

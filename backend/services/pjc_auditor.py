"""
pjc_auditor.py — Auditor simples entre Sentença (dados extraídos pela IA) e .PJC.

Objetivo: detectar divergências básicas entre o que a sentença determinou e o que
foi configurado no arquivo .pjc da outra parte (ou do próprio sistema), por exemplo:

- Índice de correção monetária diferente;
- Juros trabalhistas diferentes;
- Verbas deferidas na sentença ausentes no .pjc;
- Divisor de horas extras divergente.

Este módulo **não** altera dados; apenas produz uma lista de divergências em texto
livre para exibição no frontend, Excel ou parecer.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List

from services.pjc_parser import PjcDadosBasicos


def _normalizar_str(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _contém(sub: str, texto: str) -> bool:
    return _normalizar_str(sub) in _normalizar_str(texto)


def auditar_pjc_vs_sentenca(
    dados_ia: Dict,
    dados_pjc: PjcDadosBasicos,
) -> List[str]:
    """
    Compara dados extraídos da sentença (JSON) com os parâmetros básicos do .pjc.

    Retorna lista de divergências em texto simples.
    """
    divergencias: List[str] = []
    dados_ia = dados_ia or {}

    # 1. Índice de correção monetária
    indice_sentenca = (dados_ia.get("indice_correcao") or "").strip()
    indice_pjc = dados_pjc.indice_trabalhista or ""
    if indice_sentenca and indice_pjc:
        if not (_contém(indice_pjc, indice_sentenca) or _contém(indice_sentenca, indice_pjc)):
            divergencias.append(
                f"A sentença/extração indica índice de correção '{indice_sentenca}', "
                f"mas o arquivo .PJC utiliza '{indice_pjc}'."
            )

    # 2. Juros de mora
    juros_sentenca = (dados_ia.get("juros_mora") or "").strip()
    juros_pjc = dados_pjc.juros_trabalhistas or ""
    if juros_sentenca and juros_pjc:
        if not (_contém(juros_pjc, juros_sentenca) or _contém(juros_sentenca, juros_pjc)):
            divergencias.append(
                f"A sentença/extração indica juros de mora '{juros_sentenca}', "
                f"mas o arquivo .PJC utiliza '{juros_pjc}'."
            )

    # 3. Verbas deferidas na sentença que não aparecem no .pjc
    verbas_ia: Iterable[Dict] = dados_ia.get("verbas_deferidas") or []
    nomes_pjc_norm = [_normalizar_str(n) for n in (dados_pjc.nomes_verbas or [])]

    for v in verbas_ia:
        if not isinstance(v, dict):
            continue
        nome = (v.get("nome") or "").strip()
        if not nome:
            continue
        nome_norm = _normalizar_str(nome)
        if not any(nome_norm in n or n in nome_norm for n in nomes_pjc_norm):
            divergencias.append(
                f"A verba deferida na sentença '{nome}' não foi encontrada no arquivo .PJC."
            )

    # 4. Divisor / carga horária padrão para horas extras
    divisor_sentenca = (dados_ia.get("divisor_horas") or "").strip()
    divisor_pjc = dados_pjc.divisor_horas
    if divisor_sentenca and divisor_pjc is not None:
        try:
            div_sentenca_num = float(str(divisor_sentenca).replace(",", "."))
        except ValueError:
            div_sentenca_num = None
        if div_sentenca_num is not None and abs(div_sentenca_num - divisor_pjc) > 0.01:
            divergencias.append(
                f"A sentença/extração indica divisor de horas '{divisor_sentenca}', "
                f"mas o arquivo .PJC usa '{divisor_pjc:.4f}' como valorCargaHorariaPadrao."
            )

    return divergencias


__all__ = ["auditar_pjc_vs_sentenca"]


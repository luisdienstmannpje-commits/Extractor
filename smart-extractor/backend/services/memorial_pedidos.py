"""
Memorial narrativo para Cenário 1 (petição inicial) — pedidos estruturados sem motor de sentença.
"""

from __future__ import annotations

from typing import Any, List, Optional


def _nome_pedido(item: Any) -> Optional[str]:
    if isinstance(item, str):
        s = item.strip()
        return s or None
    if isinstance(item, dict):
        for k in ("nome", "verba", "pedido"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _trecho_um_linha(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    raw = item.get("trecho_fundamentacao")
    if not isinstance(raw, str) or not raw.strip():
        return ""
    return " ".join(raw.split())


def gerar_memorial_pedidos(
    verbas_pedidas: Optional[List[Any]],
    *,
    causa_pedir: str = "",
    periodo_reivindicado: str = "",
) -> str:
    """
    Gera texto executivo listando pedidos da inicial (evita memorial vazio no extrator).
    Inclui trecho_fundamentacao por pedido, quando existir, para conferência pelo perito.
    """
    pedidos = verbas_pedidas or []
    linhas_pedido: list[str] = []
    contador = 0
    for p in pedidos:
        n = _nome_pedido(p)
        if not n:
            continue
        contador += 1
        linhas_pedido.append(f"{contador}. {n}")
        trecho = _trecho_um_linha(p)
        if trecho:
            linhas_pedido.append(f"   Trecho indicado: {trecho}")

    if contador == 0:
        return (
            "Petição inicial analisada; não foram identificados pedidos de verbas específicos "
            "no texto extraído. Confira o documento na íntegra ou o trecho enviado à IA."
        )

    linhas: list[str] = [
        "ANÁLISE DE PEDIDOS (PETIÇÃO INICIAL)",
        "",
        f"Foram identificados {contador} pedido principal(is) na peça exordial:",
        "",
        *linhas_pedido,
    ]

    extras: list[str] = []
    if (causa_pedir or "").strip():
        extras.append(f"Causa de pedir (resumo): {(causa_pedir or '').strip()}")
    if (periodo_reivindicado or "").strip():
        extras.append(f"Período reivindicado: {(periodo_reivindicado or '').strip()}")

    if extras:
        linhas.extend(["", *extras])

    linhas.append(
        "\nNota: Esta análise reflete os pedidos formulados pelo autor. "
        "Deferimento, cálculos e reflexos dependem da decisão judicial."
    )
    return "\n".join(linhas)


def gerar_memorial_defesa(
    teses_defesa: Optional[List[Any]],
    *,
    reclamada: str = "",
) -> str:
    """
    Memorial executivo para contestação (Cenário 2): teses por pedido alvo.
    """
    teses = teses_defesa or []
    linhas_tese: list[str] = []
    n = 0
    for t in teses:
        if not isinstance(t, dict):
            continue
        alvo = str(t.get("verba_alvo") or "").strip()
        tese = str(t.get("tese_principal") or "").strip()
        if not alvo and not tese:
            continue
        n += 1
        inc = bool(t.get("incontroversa"))
        pref = "[Incontroverso/confesso] " if inc else ""
        titulo = alvo or "Pedido"
        linhas_tese.append(f"{n}. {titulo}: {pref}{tese or '—'}")
        trecho = _trecho_um_linha(t)
        if trecho:
            linhas_tese.append(f"   Trecho: {trecho}")

    if n == 0:
        return (
            "Contestação analisada; não foram identificadas teses de defesa estruturadas "
            "no texto extraído. Confira o documento enviado."
        )

    cabeca = "ANÁLISE DE TESES (CONTESTAÇÃO)"
    if (reclamada or "").strip():
        cabeca += f" — Reclamada: {(reclamada or '').strip()}"

    linhas_out: list[str] = [
        cabeca,
        "",
        f"Foram identificadas {n} tese(s) principal(is) ligada(s) a pedidos da inicial:",
        "",
        *linhas_tese,
        "",
        "Nota: Trata-se de resumo dos argumentos de defesa; o deferimento depende do juízo.",
    ]
    return "\n".join(linhas_out)

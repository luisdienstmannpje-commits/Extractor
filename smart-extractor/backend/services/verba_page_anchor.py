"""
Ancoragem de verbas às páginas do PDF usando o texto já extraído (marcadores --- PÁGINA N ---).

Preenche `pagina_origem` (1-based) nos dicts de `verbas_deferidas` quando `trecho_fundamentacao`
tem correspondência no corpo da página — sem nova chamada à IA.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from rapidfuzz import fuzz

_PAGE_MARK = re.compile(r"---\s*P\u00c1GINA\s+(\d+)\s*---", re.IGNORECASE)
# Variação sem acento (OCR ou normalização)
_PAGE_MARK_ASCII = re.compile(r"---\s*PAGINA\s+(\d+)\s*---", re.IGNORECASE)

# Fuzzy (último recurso): exige trecho longo, score alto e folga sobre o 2º colocado.
_ANCHOR_FUZZ_MIN_LEN = 32
_ANCHOR_FUZZ_MIN_SCORE = 93
_ANCHOR_FUZZ_MIN_GAP = 2
# Prefixo + sufixo na mesma página (meio corrompido por OCR)
_PREFIX_SUFFIX_MIN_NT = 40


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def _normalize_for_match(s: str) -> str:
    if not s:
        return ""
    t = _strip_accents(s.lower().strip())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s\d]", "", t)
    return t.strip()


def _compact_alnum(s: str) -> str:
    """Só letras/dígitos — útil quando OCR junta ou remove espaços."""
    t = _strip_accents(s.lower().strip())
    return re.sub(r"[^a-z0-9]", "", t)


def build_page_chunks(texto: str) -> Dict[int, str]:
    """
    Particiona o texto extraído pelo sentence_finder em mapa página (1-based) → conteúdo.
    Se não houver marcadores de página, retorna dict vazio.
    """
    if not texto:
        return {}
    # Junta ocorrências de ambos os padrões por posição
    matches = list(_PAGE_MARK.finditer(texto))
    if not matches:
        matches = list(_PAGE_MARK_ASCII.finditer(texto))
    if not matches:
        return {}
    chunks: Dict[int, str] = {}
    for i, m in enumerate(matches):
        page = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        chunk = texto[start:end]
        if page in chunks:
            chunks[page] = chunks[page] + "\n" + chunk
        else:
            chunks[page] = chunk
    return chunks


def _best_page_for_trecho(
    trecho: str,
    page_chunks: Dict[int, str],
) -> Optional[int]:
    nt = _normalize_for_match(trecho)
    if len(nt) < 12:
        return None

    for page in sorted(page_chunks.keys()):
        pn = _normalize_for_match(page_chunks[page])
        if nt in pn:
            return page

    # Fallback: prefixos decrescentes (IA pode omitir pontuação do original)
    for length in (min(72, len(nt)), min(48, len(nt)), min(32, len(nt)), min(20, len(nt))):
        if length < 12:
            break
        frag = nt[:length]
        for page in sorted(page_chunks.keys()):
            pn = _normalize_for_match(page_chunks[page])
            if frag in pn:
                return page

    # Prefixo e sufixo na mesma página (trecho com erro no meio no PDF/OCR)
    if len(nt) >= _PREFIX_SUFFIX_MIN_NT:
        frag_len = max(12, min(28, len(nt) // 3))
        prefix = nt[:frag_len]
        suffix = nt[-frag_len:]
        for page in sorted(page_chunks.keys()):
            pn = _normalize_for_match(page_chunks[page])
            if prefix in pn and suffix in pn:
                return page

    # Modo compacto: substring só com letras/números
    cn = _compact_alnum(trecho)
    if len(cn) >= 14:
        for page in sorted(page_chunks.keys()):
            cp = _compact_alnum(page_chunks[page])
            if len(cp) >= len(cn) and cn in cp:
                return page
        if len(cn) >= _PREFIX_SUFFIX_MIN_NT:
            frag_c = max(12, min(24, len(cn) // 3))
            pre_c, suf_c = cn[:frag_c], cn[-frag_c]
            for page in sorted(page_chunks.keys()):
                cp = _compact_alnum(page_chunks[page])
                if pre_c in cp and suf_c in cp:
                    return page

    # Último recurso: partial_ratio com desempate (evita empate entre páginas)
    if len(nt) >= _ANCHOR_FUZZ_MIN_LEN:
        scored: List[tuple[int, int]] = []
        for page in sorted(page_chunks.keys()):
            pn = _normalize_for_match(page_chunks[page])
            if not pn:
                continue
            scored.append((fuzz.partial_ratio(nt, pn), page))
        scored.sort(key=lambda x: -x[0])
        if len(scored) >= 1 and scored[0][0] >= _ANCHOR_FUZZ_MIN_SCORE:
            best_s, _ = scored[0]
            second_s = scored[1][0] if len(scored) > 1 else 0
            if best_s - second_s >= _ANCHOR_FUZZ_MIN_GAP:
                return scored[0][1]
    return None


def anchor_verbas_to_pages(texto: str, verbas: List[Dict[str, Any]]) -> int:
    """
    Preenche `pagina_origem` in-place quando ainda ausente.

    Returns:
        Quantidade de verbas que receberam página.
    """
    if not texto or not verbas:
        return 0
    chunks = build_page_chunks(texto)
    if not chunks:
        return 0

    filled = 0
    for v in verbas:
        if not isinstance(v, dict):
            continue
        if v.get("pagina_origem") is not None:
            continue
        raw = v.get("trecho_fundamentacao")
        trecho = (raw or "").strip() if isinstance(raw, str) else ""
        if not trecho:
            continue
        p = _best_page_for_trecho(trecho, chunks)
        if p is not None:
            v["pagina_origem"] = p
            filled += 1

    if filled:
        print(f"[ANCHOR] pagina_origem definida em {filled} verba(s)", flush=True)
    return filled

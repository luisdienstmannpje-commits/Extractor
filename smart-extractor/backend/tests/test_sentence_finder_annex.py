"""Testes dos anexos multi-âncora (sentence_finder._select_annex_pages)."""

from __future__ import annotations

from services.sentence_finder import (
    ANNEX_HEADER_BASE,
    ANNEX_HEADER_MOD,
    MAX_ANNEX_BASE,
    MAX_ANNEX_MODIFICADORA,
    PageInfo,
    _select_annex_pages,
)


def _pages(n: int) -> list[PageInfo]:
    return [PageInfo(idx=i, text="") for i in range(n)]


def test_annex_skips_included_pages() -> None:
    pages = _pages(12)
    pages[5].is_embargos = True
    included = {5}
    assert _select_annex_pages(pages, included) == []


def test_annex_modificadora_cap() -> None:
    pages = _pages(20)
    for i in range(10, 10 + MAX_ANNEX_MODIFICADORA + 3):
        pages[i].is_embargos = True
    included = set(range(10))
    sel = _select_annex_pages(pages, included)
    mod_idxs = [t[0] for t in sel if t[1] == ANNEX_HEADER_MOD]
    assert len(mod_idxs) == MAX_ANNEX_MODIFICADORA
    assert mod_idxs == list(range(10, 10 + MAX_ANNEX_MODIFICADORA))


def test_annex_base_cap_and_order() -> None:
    pages = _pages(25)
    for i in range(15, 15 + MAX_ANNEX_BASE + 2):
        pages[i].is_parametro_base = True
    included = set(range(15))
    sel = _select_annex_pages(pages, included)
    base_idxs = [t[0] for t in sel if t[1] == ANNEX_HEADER_BASE]
    assert len(base_idxs) == MAX_ANNEX_BASE
    assert base_idxs == [15, 16, 17]


def test_modificadora_takes_precedence_over_base() -> None:
    pages = [
        PageInfo(
            idx=0,
            text="",
            is_embargos=True,
            is_parametro_base=True,
        )
    ]
    sel = _select_annex_pages(pages, set())
    assert len(sel) == 1
    assert sel[0] == (0, ANNEX_HEADER_MOD)


def test_base_only_when_not_modificadora() -> None:
    pages = [PageInfo(idx=0, text="", is_parametro_base=True)]
    sel = _select_annex_pages(pages, set())
    assert sel == [(0, ANNEX_HEADER_BASE)]


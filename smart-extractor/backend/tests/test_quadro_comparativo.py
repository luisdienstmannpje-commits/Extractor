"""Quadro comparativo dossiê (SCHEMA 2.15) — modelo e truncagem."""

from models import ItemComparativo, ProcessoTrabalhista
from services.ai_client import (
    _normalize_quadro_comparativo_rows,
    _truncate_texto_dossie_para_quadro,
)


def test_model_quadro_comparativo_field():
    assert "quadro_comparativo" in ProcessoTrabalhista.model_fields


def test_processo_com_quadro_vazio():
    p = ProcessoTrabalhista(verbas_deferidas=[], quadro_comparativo=[])
    assert p.quadro_comparativo == []


def test_item_comparativo_defaults():
    i = ItemComparativo()
    assert i.verba_alvo == ""
    p = ProcessoTrabalhista(
        verbas_deferidas=[],
        quadro_comparativo=[
            ItemComparativo(
                verba_alvo="FGTS",
                resumo_pedido="p",
                resumo_defesa="d",
                resumo_decisao="x",
                status_final="Deferida",
            )
        ],
    )
    assert len(p.quadro_comparativo) == 1


def test_normalize_quadro_skips_empty():
    rows = _normalize_quadro_comparativo_rows(
        [
            {"verba_alvo": "  HE  ", "resumo_pedido": "a"},
            "bad",
            {},
        ]
    )
    assert len(rows) == 1
    assert rows[0]["verba_alvo"] == "HE"
    assert rows[0]["resumo_pedido"] == "a"


def test_truncate_dossie_preserva_marcadores():
    a = "--- INÍCIO DO DOCUMENTO: a.pdf ---\n" + ("x" * 5000)
    b = "--- INÍCIO DO DOCUMENTO: b.pdf ---\n" + ("y" * 5000)
    c = "--- INÍCIO DO DOCUMENTO: c.pdf ---\n" + ("z" * 5000)
    texto = a + b + c
    out = _truncate_texto_dossie_para_quadro(texto, 12_000)
    assert "--- INÍCIO DO DOCUMENTO: a.pdf ---" in out
    assert "--- INÍCIO DO DOCUMENTO: b.pdf ---" in out
    assert "--- INÍCIO DO DOCUMENTO: c.pdf ---" in out
    assert len(out) <= 12_000

"""Testes unitários do ghostwriter (ai_writer)."""

from services.ai_writer import (
    _normalize_alertas,
    _normalize_quadro_comparativo,
    render_markdown_manifestacao,
)


def test_normalize_alertas_accepts_string_and_dict():
    data = [
        "[ERRO] A",
        {"nivel": "aviso", "mensagem": "B"},
        {"texto": "C"},
        123,
    ]
    out = _normalize_alertas(data)
    assert out[0] == "[ERRO] A"
    assert "[AVISO] B" in out
    assert "C" in out


def test_normalize_quadro_filters_empty_rows():
    rows = [
        {"verba_alvo": "HE", "resumo_pedido": "pedido"},
        {},
        "x",
    ]
    out = _normalize_quadro_comparativo(rows)
    assert len(out) == 1
    assert out[0]["verba_alvo"] == "HE"


def test_render_markdown_manifestacao_sections_table_and_fecho():
    resultado = {
        "introducao": "Intro",
        "secoes": [
            {"titulo": "T1", "texto": "Texto 1"},
            {"titulo": "T2", "texto": "Texto 2"},
        ],
        "tabela_comparativa": [
            {
                "descricao": "Diferença",
                "valor_empresa": "100",
                "valor_correto": "120",
            }
        ],
        "fecho": "Pede deferimento",
    }
    md = render_markdown_manifestacao(resultado)
    assert "## Introdução" in md
    assert "### T1" in md
    assert "## Tabela Comparativa" in md
    assert "| Diferença | 100 | 120 |" in md
    assert "## Fecho" in md

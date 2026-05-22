"""Testes de capa adaptativa (sentence_finder.get_adaptive_capa_pages)."""

from services.sentence_finder import get_adaptive_capa_pages


def test_padraio_duas_paginas():
    assert get_adaptive_capa_pages(1, "sentenca") == 1
    assert get_adaptive_capa_pages(2, "sentenca") == 2
    assert get_adaptive_capa_pages(50, "sentenca") == 2
    assert get_adaptive_capa_pages(100, "acordao") == 2


def test_pdf_longo_cinco_paginas():
    assert get_adaptive_capa_pages(101, "sentenca") == 5
    assert get_adaptive_capa_pages(500, "completo") == 5


def test_liquidacao_ate_oito():
    assert get_adaptive_capa_pages(200, "liquidacao") == 8
    assert get_adaptive_capa_pages(3, "liquidacao") == 3


def test_liquidacao_prevalece_sobre_pdf_longo():
    assert get_adaptive_capa_pages(500, "liquidacao") == 8

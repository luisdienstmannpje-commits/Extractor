"""Ciclo de extração incremental — dado-alvo: reclamante (pre_extractor HIGH)."""

from services.pre_extractor import pre_extract


def test_reclamante_cabecalho_rotulo_reclamante():
    texto = """
    --- PAGINA 1 ---
    Processo: 0001234-56.2024.5.02.0031
    Reclamante: Maria da Silva
    Reclamada: Empresa Exemplo Ltda.
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["reclamante"] == "Maria da Silva"


def test_reclamante_rotulo_autor():
    texto = """
    --- PAGINA 1 ---
    Autor: João Pereira Santos
    Reclamada: ACME Indústria S.A.
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["reclamante"] == "João Pereira Santos"


def test_reclamante_rotulo_parte_autora():
    texto = """
    --- PAGINA 1 ---
    Parte autora: Ana Paula Costa
    Reclamada: Logística Beta Ltda.
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["reclamante"] == "Ana Paula Costa"


def test_nao_define_reclamante_so_com_reclamada():
    texto = """
    --- PAGINA 1 ---
    Reclamada: Empresa Exemplo Ltda.
    Vistos.
    """

    resultado = pre_extract(texto)

    assert "reclamante" not in resultado["high"]


def test_reclamante_apos_reclamada_pega_primeiro_rotulo_de_autor():
    """Ordem capa: reclamada antes; primeiro rótulo válido de parte autora deve vencer."""
    texto = """
    --- PAGINA 1 ---
    Reclamada: Empresa Exemplo Ltda.
    Reclamante: Carlos Henrique Lima
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["reclamante"] == "Carlos Henrique Lima"

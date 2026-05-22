"""Ciclo de extração incremental — dado-alvo: reclamada (pre_extractor HIGH)."""

from services.pre_extractor import pre_extract


def test_reclamada_cabecalho_rotulo_reclamada():
    texto = """
    --- PAGINA 1 ---
    Processo: 0001234-56.2024.5.02.0031
    Reclamante: Maria da Silva
    Reclamada: Empresa Exemplo Ltda.
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["reclamada"] == "Empresa Exemplo Ltda."


def test_reclamada_rotulo_reclamado():
    texto = """
    --- PAGINA 1 ---
    Autor: João Pereira Santos
    Reclamado: ACME Indústria S.A.
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["reclamada"] == "ACME Indústria S.A."


def test_reclamada_rotulo_parte_reclamada():
    texto = """
    --- PAGINA 1 ---
    Parte autora: Ana Paula Costa
    Parte reclamada: Logística Beta Ltda.
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["reclamada"] == "Logística Beta Ltda."


def test_nao_define_reclamada_so_com_reclamante():
    texto = """
    --- PAGINA 1 ---
    Reclamante: Carlos Henrique Lima
    Vistos.
    """

    resultado = pre_extract(texto)

    assert "reclamada" not in resultado["high"]


def test_reclamada_apos_reclamante_pega_rotulo_reclamada():
    texto = """
    --- PAGINA 1 ---
    Reclamante: Carlos Henrique Lima
    Reclamada: Gamma Serviços EIRELI
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["reclamada"] == "Gamma Serviços EIRELI"


def test_capa_completa_reclamante_e_reclamada():
    texto = """
    --- PAGINA 1 ---
    Reclamante: Maria da Silva
    Reclamada: Delta Transportes Ltda.
    """

    r = pre_extract(texto)

    assert r["high"]["reclamante"] == "Maria da Silva"
    assert r["high"]["reclamada"] == "Delta Transportes Ltda."

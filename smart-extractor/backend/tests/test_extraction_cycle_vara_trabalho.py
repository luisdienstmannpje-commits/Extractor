"""Ciclo de extração incremental — dado-alvo: vara_trabalho (pre_extractor HIGH)."""

from services.pre_extractor import pre_extract


def test_vara_rotulo_vara_do_trabalho():
    texto = """
    --- PAGINA 1 ---
    Processo: 0001234-56.2024.5.02.0031
    Vara do Trabalho: 2ª Vara do Trabalho de Belo Horizonte
    Reclamante: Maria da Silva
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["vara_trabalho"] == "2ª Vara do Trabalho de Belo Horizonte"


def test_vara_rotulo_vara_curto():
    texto = """
    --- PAGINA 1 ---
    Vara: 1ª Vara do Trabalho de Porto Alegre
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["vara_trabalho"] == "1ª Vara do Trabalho de Porto Alegre"


def test_vara_linha_ordinal_sem_rotulo_no_inicio():
    """Primeiras linhas: padrão 'Nª Vara do Trabalho de ...' sem rótulo explícito."""
    texto = """
    --- PAGINA 1 ---
    3ª Vara do Trabalho de Manaus
    Reclamante: João Teste
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["vara_trabalho"] == "3ª Vara do Trabalho de Manaus"


def test_nao_define_vara_sem_mencao_trabalho():
    texto = """
    --- PAGINA 1 ---
    Vara: Tribunal Regional da 2ª Região
    """

    resultado = pre_extract(texto)

    assert "vara_trabalho" not in resultado["high"]


def test_nao_define_vara_so_trt_sem_vara():
    texto = """
    --- PAGINA 1 ---
    Tribunal Regional do Trabalho da 10ª Região
    Processo: 0001234-56.2024.5.10.0001
    """

    resultado = pre_extract(texto)

    assert "vara_trabalho" not in resultado["high"]


def test_vara_profunda_no_texto_ignorada_sem_rotulo():
    """Sem rótulo 'Vara:', só aceita padrão ordinal no cabeçalho (primeiros chars)."""
    corpo = ("Preambulo irrelevante.\n" * 300)  # > 4000 chars
    texto = (
        corpo
        + "\n5ª Vara do Trabalho de Curitiba\n"
    )

    resultado = pre_extract(texto)

    assert "vara_trabalho" not in resultado["high"]

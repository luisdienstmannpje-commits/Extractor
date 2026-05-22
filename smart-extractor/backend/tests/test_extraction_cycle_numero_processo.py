from services.pre_extractor import pre_extract


def test_numero_processo_cabecalho_explicito():
    texto = """
    --- PAGINA 1 ---
    Processo: 0001234-56.2024.5.02.0031
    Reclamante: Maria da Silva
    Reclamada: Empresa Exemplo Ltda.
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["numero_processo"] == "0001234-56.2024.5.02.0031"


def test_numero_processo_primeira_ocorrencia_cnj_no_corpo():
    texto = """
    --- PAGINA 2 ---
    Vistos etc.
    Trata-se de reclamacao trabalhista vinculada aos autos
    1000456-78.2023.5.15.0099, em fase de conhecimento.
    """

    resultado = pre_extract(texto)

    assert resultado["high"]["numero_processo"] == "1000456-78.2023.5.15.0099"


def test_numero_processo_ignora_numero_fora_do_padrao_cnj():
    texto = """
    --- PAGINA 1 ---
    Protocolo administrativo: 123456-78.2023.5.15.0099
    Documento interno: 10004567820235150099
    Nenhum numero CNJ valido foi informado nesta pagina.
    """

    resultado = pre_extract(texto)

    assert "numero_processo" not in resultado["high"]


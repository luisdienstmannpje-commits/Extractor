"""Testes de ancoragem trecho → página (verba_page_anchor)."""

from services.verba_page_anchor import anchor_verbas_to_pages, build_page_chunks


def test_build_page_chunks_vazio_sem_marcadores():
    assert build_page_chunks("sem marcas aqui") == {}


def test_build_page_chunks_duas_paginas():
    texto = """--- PÁGINA 1 ---
capa
--- PÁGINA 2 ---
defiro horas extras
--- PÁGINA 3 ---
outro
"""
    ch = build_page_chunks(texto)
    assert 1 in ch and 2 in ch and 3 in ch
    assert "defiro" in ch[2]


def test_anchor_preenche_pagina():
    texto = """--- PÁGINA 1 ---
relatorio
--- PÁGINA 4 ---
Ante o exposto DEFIRO o pagamento de horas extras ao autor.
"""
    verbas = [
        {
            "nome": "HE",
            "trecho_fundamentacao": "DEFIRO o pagamento de horas extras ao autor.",
        }
    ]
    n = anchor_verbas_to_pages(texto, verbas)
    assert n == 1
    assert verbas[0]["pagina_origem"] == 4


def test_anchor_nao_sobrescreve_existente():
    texto = """--- PÁGINA 2 ---
texto aqui
"""
    verbas = [{"nome": "X", "trecho_fundamentacao": "texto", "pagina_origem": 99}]
    anchor_verbas_to_pages(texto, verbas)
    assert verbas[0]["pagina_origem"] == 99


def test_anchor_trecho_curto_ignora():
    texto = """--- PÁGINA 1 ---
abcdefghijklm
"""
    verbas = [{"nome": "X", "trecho_fundamentacao": "curto"}]
    assert anchor_verbas_to_pages(texto, verbas) == 0


def test_anchor_prefix_suffix_when_middle_corrupt():
    """Meio do PDF difere do trecho da IA; início e fim batem na mesma página."""
    texto = """--- PÁGINA 5 ---
CONDENO a reclamada ao pagamento de horas xtras noturnas segundo o relatório do juiz.
"""
    verbas = [
        {
            "nome": "HE",
            "trecho_fundamentacao": (
                "CONDENO a reclamada ao pagamento de horas extras noturnas segundo o relatório do juiz."
            ),
        }
    ]
    assert anchor_verbas_to_pages(texto, verbas) == 1
    assert verbas[0]["pagina_origem"] == 5


def test_anchor_compact_joined_words_on_page():
    """OCR junta palavras; trecho da IA mantém espaços — alfanumérico coincide."""
    texto = """--- PÁGINA 7 ---
dispositivo defiroopagamentodehorasextrasaoautor em razão do mérito
"""
    verbas = [
        {
            "nome": "HE",
            "trecho_fundamentacao": "Defiro o pagamento de horas extras ao autor",
        }
    ]
    assert anchor_verbas_to_pages(texto, verbas) == 1
    assert verbas[0]["pagina_origem"] == 7


def test_anchor_regression_full_still_prefixed():
    """Caso que já passava por substring completa continua na página certa."""
    texto = """--- PÁGINA 1 ---
capa
--- PÁGINA 4 ---
Ante o exposto DEFIRO o pagamento de horas extras ao autor.
"""
    verbas = [
        {"nome": "HE", "trecho_fundamentacao": "DEFIRO o pagamento de horas extras ao autor."}
    ]
    assert anchor_verbas_to_pages(texto, verbas) == 1
    assert verbas[0]["pagina_origem"] == 4

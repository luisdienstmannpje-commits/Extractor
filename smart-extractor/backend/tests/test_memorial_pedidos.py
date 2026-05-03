"""Memorial narrativo — petição inicial."""

from services.memorial_pedidos import gerar_memorial_pedidos


def test_memorial_lista_pedidos():
    verbas = [{"nome": "Horas extras"}, {"nome": "FGTS"}]
    t = gerar_memorial_pedidos(
        verbas,
        causa_pedir="Atraso salarial",
        periodo_reivindicado="01/2020 a 12/2021",
    )
    assert "Horas extras" in t
    assert "FGTS" in t
    assert "Atraso salarial" in t
    assert "01/2020" in t


def test_memorial_sem_pedidos():
    t = gerar_memorial_pedidos([])
    assert "identificados" in t.lower()


def test_memorial_strings_na_lista():
    t = gerar_memorial_pedidos(["13º salário", "Férias"])
    assert "13" in t or "13º" in t


def test_memorial_inclui_trecho_fundamentacao():
    verbas = [
        {
            "nome": "Horas extras",
            "trecho_fundamentacao": "Requer\nreconhecimento  de  HE\nnoturnas",
        },
    ]
    t = gerar_memorial_pedidos(verbas)
    assert "Horas extras" in t
    assert "Trecho indicado:" in t
    assert "Requer reconhecimento de HE noturnas" in t

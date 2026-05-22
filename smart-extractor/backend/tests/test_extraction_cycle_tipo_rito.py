"""Ciclo incremental — tipo_rito (HIGH: Sumaríssimo > Ordinário)."""

from services.pre_extractor import pre_extract


def test_rito_sumarissimo():
    texto = "O feito tramita pelo rito sumaríssimo."

    r = pre_extract(texto)

    assert r["high"]["tipo_rito"] == "Sumaríssimo"


def test_procedimento_sumarissimo():
    texto = "Instaura-se o procedimento sumaríssimo."

    r = pre_extract(texto)

    assert r["high"]["tipo_rito"] == "Sumaríssimo"


def test_palavra_sumarissimo_isolada():
    texto = "Adota-se o sumaríssimo nesta Vara."

    r = pre_extract(texto)

    assert r["high"]["tipo_rito"] == "Sumaríssimo"


def test_rito_ordinario():
    texto = "Processo em rito ordinário."

    r = pre_extract(texto)

    assert r["high"]["tipo_rito"] == "Ordinário"


def test_procedimento_ordinario():
    texto = "Segue o procedimento ordinário na forma da lei."

    r = pre_extract(texto)

    assert r["high"]["tipo_rito"] == "Ordinário"


def test_sumarissimo_prevalece_sobre_ordinario():
    texto = """
    Em primeiro grau tramitou rito ordinário.
    Reformado para rito sumaríssimo em recurso.
    """

    r = pre_extract(texto)

    assert r["high"]["tipo_rito"] == "Sumaríssimo"


def test_sem_mencao_nao_preenche():
    texto = "Julgo procedente o pedido de horas extras."

    r = pre_extract(texto)

    assert "tipo_rito" not in r["high"]


def test_tipo_rito_em_high_nao_medium():
    texto = "Autos em rito ordinário."

    r = pre_extract(texto)

    assert "tipo_rito" in r["high"]
    assert "tipo_rito" not in r["medium"]

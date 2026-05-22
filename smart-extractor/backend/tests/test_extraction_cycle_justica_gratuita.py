"""Ciclo incremental — justica_gratuita (HIGH; negação antes de deferimento)."""

from services.pre_extractor import pre_extract


def test_defiro_justica_gratuita():
    texto = "Defiro a justiça gratuita aos autores."

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is True


def test_justica_gratuita_deferida():
    texto = "A justiça gratuita fica deferida nos termos da Lei 1.060/50."

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is True


def test_beneficios_assistencia_judiciaria():
    texto = "Concedo os benefícios da assistência judiciária requeridos."

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is True


def test_beneficios_justica_gratuita_deferidos():
    texto = "Defiro os benefícios da justiça gratuita deferidos à parte."

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is True


def test_gratuidade_defiro():
    texto = "Defiro a gratuidade de justiça pleiteada."

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is True


def test_justica_gratuita_indeferida():
    texto = "A justiça gratuita fica indeferida."

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is False


def test_indeferido_antes_de_justica_gratuita():
    texto = "Indeferido o pedido de justiça gratuita."

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is False


def test_nao_faz_jus():
    texto = "Não faz jus à justiça gratuita, à luz da renda apresentada."

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is False


def test_negacao_prevalece_sobre_deferimento_no_mesmo_texto():
    texto = """
    Defiro justiça gratuita em primeiro grau.
    Em sede recursal, a justiça gratuita fica indeferida.
    """

    r = pre_extract(texto)

    assert r["high"]["justica_gratuita"] is False


def test_sem_mencao_nao_preenche():
    texto = "Julgo procedente o pedido de horas extras."

    r = pre_extract(texto)

    assert "justica_gratuita" not in r["high"]


def test_justica_gratuita_em_high_nao_medium():
    texto = "Defiro justiça gratuita."

    r = pre_extract(texto)

    assert "justica_gratuita" in r["high"]
    assert "justica_gratuita" not in r["medium"]

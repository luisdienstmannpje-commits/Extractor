"""Ciclo de extração incremental — dado-alvo: salario_base (pre_extractor MEDIUM)."""

from services.pre_extractor import pre_extract


def test_salario_salario_de_com_rs():
    texto = "O reclamante percebia salário de R$ 2.345,67 mensais."

    r = pre_extract(texto)

    assert r["medium"]["salario_base"] == "R$ 2.345,67"
    assert "salario_base" not in r["high"]


def test_salario_remuneracao_de_sem_rs_explicito_no_rotulo():
    texto = "Remuneração de 1.800,00 (um mil e oitocentos reais)."

    r = pre_extract(texto)

    assert r["medium"]["salario_base"] == "R$ 1.800,00"


def test_salario_rotulo_salario_base_dois_pontos():
    texto = """
    --- PAGINA 1 ---
    Salário base: R$ 2.500,00
    """

    r = pre_extract(texto)

    assert r["medium"]["salario_base"] == "R$ 2.500,00"


def test_salario_rotulo_salario_dois_pontos():
    texto = "Qualificação. Salário: 3.200,00. Comissões à parte."

    r = pre_extract(texto)

    assert r["medium"]["salario_base"] == "R$ 3.200,00"


def test_salario_moda_quando_repetido():
    texto = """
    Salário de R$ 1.500,00 conforme contrato.
    O salário de R$ 1.500,00 era pago até a dispensa.
    """

    r = pre_extract(texto)

    assert r["medium"]["salario_base"] == "R$ 1.500,00"


def test_salario_abaixo_plausibilidade_nao_define():
    texto = "Salário de R$ 400,00 (valor ilustrativo abaixo do piso legal)."

    r = pre_extract(texto)

    assert "salario_base" not in r["medium"]


def test_salario_acima_teto_nao_define():
    texto = "Remuneração de 95.000,00 mensais (fora do filtro do extrator)."

    r = pre_extract(texto)

    assert "salario_base" not in r["medium"]


def test_salario_ausente():
    texto = "Pedido de horas extras sem menção a salário ou remuneração."

    r = pre_extract(texto)

    assert "salario_base" not in r["medium"]

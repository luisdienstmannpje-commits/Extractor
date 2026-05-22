"""Ciclo incremental — divisor_horas (MEDIUM: divisor explícito > inferência por jornada semanal)."""

from services.pre_extractor import pre_extract


def test_divisor_explicito_220():
    texto = "As horas extras serão calculadas com divisor de horas 220."

    r = pre_extract(texto)

    assert r["medium"]["divisor_horas"] == "220"


def test_divisor_explicito_forma_curta():
    texto = "Aplica-se divisor 200 à base de cálculo."

    r = pre_extract(texto)

    assert r["medium"]["divisor_horas"] == "200"


def test_inferencia_44_horas_semanais():
    texto = "O reclamante cumpria jornada de 44 horas semanais."

    r = pre_extract(texto)

    assert r["medium"]["divisor_horas"] == "220"


def test_inferencia_40_horas():
    texto = "Consta contrato com 40 h semanais."

    r = pre_extract(texto)

    assert r["medium"]["divisor_horas"] == "200"


def test_inferencia_36_horas():
    texto = "Jornada de 36 horas por semana na unidade."

    r = pre_extract(texto)

    assert r["medium"]["divisor_horas"] == "180"


def test_inferencia_35_horas():
    texto = "Trabalhava 35 horas semanais."

    r = pre_extract(texto)

    assert r["medium"]["divisor_horas"] == "175"


def test_inferencia_30_horas():
    texto = "Regime de 30h semanais conforme acordo."

    r = pre_extract(texto)

    assert r["medium"]["divisor_horas"] == "150"


def test_explicito_prevalece_sobre_jornada():
    """Regex de divisor roda antes da inferência; qualquer divisor válido no texto prevalece."""
    texto = """
    O autor alega 44 horas semanais.
    O laudo pericial adotou divisor de 200 para a projeção.
    """

    r = pre_extract(texto)

    assert r["medium"]["divisor_horas"] == "200"


def test_jornada_nao_mapeada_nao_preenche():
    texto = "Jornada de 32 horas semanais."

    r = pre_extract(texto)

    assert "divisor_horas" not in r["medium"]


def test_sem_divisor_nem_jornada():
    texto = "Pedido de horas extras sem menção a divisor ou jornada."

    r = pre_extract(texto)

    assert "divisor_horas" not in r["medium"]


def test_divisor_horas_em_medium_nao_high():
    texto = "Divisor de 180 para extras."

    r = pre_extract(texto)

    assert "divisor_horas" in r["medium"]
    assert "divisor_horas" not in r["high"]

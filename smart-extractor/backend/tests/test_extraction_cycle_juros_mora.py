"""Ciclo incremental — juros_mora (MEDIUM, prioridades SELIC > 1% a.m. > juros legais)."""

from services.pre_extractor import pre_extract


def test_juros_mora_pela_selic():
    texto = "Os valores serão acrescidos de juros de mora pela SELIC."

    r = pre_extract(texto)

    assert r["medium"]["juros_mora"] == "SELIC"


def test_juros_pela_selic_sem_mora_explicito():
    texto = "Incidem juros pela SELIC a partir do vencimento."

    r = pre_extract(texto)

    assert r["medium"]["juros_mora"] == "SELIC"


def test_um_por_cento_ao_mes():
    texto = "Correção monetária e juros de mora de 1% ao mês."

    r = pre_extract(texto)

    assert r["medium"]["juros_mora"] == "1% ao mês"


def test_juros_de_um_por_cento_forma_curta():
    texto = "Condeno juros de 1% ao mês sobre o principal."

    r = pre_extract(texto)

    assert r["medium"]["juros_mora"] == "1% ao mês"


def test_juros_legais():
    texto = "Aplica-se ainda juros legais de mora sobre a condenação."

    r = pre_extract(texto)

    assert r["medium"]["juros_mora"] == "Juros legais"


def test_selic_tem_prioridade_sobre_um_percento():
    texto = """
    Condeno juros de mora pela SELIC.
    Em sede de cálculo auxiliar, menciona-se juros de 1% ao mês apenas como referência.
    """

    r = pre_extract(texto)

    assert r["medium"]["juros_mora"] == "SELIC"


def test_um_percento_tem_prioridade_sobre_juros_legais():
    texto = """
    Incidem juros de 1% ao mês.
    Não se aplica apenas menção genérica a juros legais em outro parágrafo sem o padrão.
    """

    r = pre_extract(texto)

    assert r["medium"]["juros_mora"] == "1% ao mês"


def test_sem_mencao_nao_preenche():
    texto = "O autor pleiteia apenas horas extras e intervalo intrajornada."

    r = pre_extract(texto)

    assert "juros_mora" not in r["medium"]


def test_juros_mora_em_medium_nao_high():
    texto = "Juros de mora pela SELIC desde o vencimento."

    r = pre_extract(texto)

    assert "juros_mora" in r["medium"]
    assert "juros_mora" not in r["high"]

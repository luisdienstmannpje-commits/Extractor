"""Ciclo incremental — tipo_contrato (MEDIUM: pejotização > autônomo > CLT)."""

from services.pre_extractor import pre_extract


def test_pejotizacao_reconhecida():
    texto = "Constatada pejotização reconhecida nos autos."

    r = pre_extract(texto)

    assert r["medium"]["tipo_contrato"] == "Pejotização reconhecida"


def test_contrato_pj_fraude():
    texto = "O contrato de pessoa jurídica configurava fraude trabalhista."

    r = pre_extract(texto)

    assert r["medium"]["tipo_contrato"] == "Pejotização reconhecida"


def test_cnpj_simulacao_curta_distancia():
    texto = "Uso de CNPJ para simulação de vínculo autônomo."

    r = pre_extract(texto)

    assert r["medium"]["tipo_contrato"] == "Pejotização reconhecida"


def test_autonomo_reconhecido():
    texto = "A perícia concluiu que o autônomo era reconhecido como empregado."

    r = pre_extract(texto)

    assert r["medium"]["tipo_contrato"] == "Autônomo reconhecido"


def test_vinculo_emprego():
    texto = "Há prova de vínculo de emprego entre as partes."

    r = pre_extract(texto)

    assert r["medium"]["tipo_contrato"] == "CLT"


def test_sigla_clt():
    texto = "Aplica-se o regime jurídico da CLT ao caso."

    r = pre_extract(texto)

    assert r["medium"]["tipo_contrato"] == "CLT"


def test_pejotizacao_prevalece_sobre_clt():
    texto = """
    Reconhece-se pejotização e fraude à legislação.
    Subsidiariamente, discute-se aplicação da CLT.
    """

    r = pre_extract(texto)

    assert r["medium"]["tipo_contrato"] == "Pejotização reconhecida"


def test_autonomo_prevalece_sobre_clt_isolado():
    texto = "Tratava-se de autônomo, mas reconhecido vínculo. Cita-se CLT apenas doutrinariamente."

    r = pre_extract(texto)

    assert r["medium"]["tipo_contrato"] == "Autônomo reconhecido"


def test_sem_padrao_nao_preenche():
    texto = "Condeno apenas danos morais no valor de R$ 5.000,00."

    r = pre_extract(texto)

    assert "tipo_contrato" not in r["medium"]


def test_tipo_contrato_em_medium_nao_high():
    texto = "Reconheço vínculo de emprego."

    r = pre_extract(texto)

    assert "tipo_contrato" in r["medium"]
    assert "tipo_contrato" not in r["high"]

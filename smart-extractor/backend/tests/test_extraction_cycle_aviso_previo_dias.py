"""Ciclo incremental — aviso_previo_dias (MEDIUM, faixa 20–90 dias)."""

from services.pre_extractor import pre_extract


def test_aviso_previo_de_n_dias():
    texto = "Concedo aviso prévio de 30 dias."

    r = pre_extract(texto)

    assert r["medium"]["aviso_previo_dias"] == "30 dias"


def test_aviso_previo_indenizado():
    texto = "Defiro aviso prévio indenizado de 36 dias."

    r = pre_extract(texto)

    assert r["medium"]["aviso_previo_dias"] == "36 dias"


def test_sem_particula_de():
    texto = "Homologo aviso prévio 33 dias conforme Lei 12.506/2011."

    r = pre_extract(texto)

    assert r["medium"]["aviso_previo_dias"] == "33 dias"


def test_previo_sem_acento():
    texto = "Aplica-se aviso previo de 40 dias."

    r = pre_extract(texto)

    assert r["medium"]["aviso_previo_dias"] == "40 dias"


def test_limite_inferior_20_dias():
    texto = "Aviso prévio de 20 dias."

    r = pre_extract(texto)

    assert r["medium"]["aviso_previo_dias"] == "20 dias"


def test_abaixo_de_20_nao_preenche():
    texto = "Menciona-se aviso prévio de 15 dias apenas como exemplo teórico."

    r = pre_extract(texto)

    assert "aviso_previo_dias" not in r["medium"]


def test_limite_superior_90_dias():
    texto = "Aviso prévio de 90 dias pelo tempo de serviço."

    r = pre_extract(texto)

    assert r["medium"]["aviso_previo_dias"] == "90 dias"


def test_acima_de_90_nao_preenche():
    texto = "Pedido de aviso prévio de 100 dias sem respaldo legal."

    r = pre_extract(texto)

    assert "aviso_previo_dias" not in r["medium"]


def test_primeira_ocorrencia_no_texto():
    texto = """
    O laudo cita aviso prévio de 25 dias.
    O dispositivo fixa aviso prévio de 40 dias.
    """

    r = pre_extract(texto)

    assert r["medium"]["aviso_previo_dias"] == "25 dias"


def test_sem_mencao_nao_preenche():
    texto = "Condeno apenas horas extras e reflexos em DSR."

    r = pre_extract(texto)

    assert "aviso_previo_dias" not in r["medium"]


def test_aviso_previo_dias_em_medium_nao_high():
    texto = "Aviso prévio de 44 dias."

    r = pre_extract(texto)

    assert "aviso_previo_dias" in r["medium"]
    assert "aviso_previo_dias" not in r["high"]

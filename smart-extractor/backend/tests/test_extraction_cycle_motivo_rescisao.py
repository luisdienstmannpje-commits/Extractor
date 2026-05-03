"""Ciclo incremental — motivo_rescisao (MEDIUM, ordem fixa na cadeia elif)."""

from services.pre_extractor import pre_extract


def test_rescisao_indireta():
    texto = "O autor pleiteia rescisão indireta por falta de depósito do FGTS."

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Rescisão indireta"


def test_dispensado_sem_justa_causa():
    texto = "O reclamante foi dispensado sem justa causa em 01/03/2022."

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Sem justa causa"


def test_demissao_sem_justa_causa_proxima():
    texto = "A empregadora promoveu a demissão sem justa causa do obreiro."

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Sem justa causa"


def test_com_justa_causa():
    texto = "Reconheço a dispensa com justa causa devido ao abandono de emprego."

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Com justa causa"


def test_pedido_de_demissao():
    texto = "O autor formalizou pedido de demissão em 10/05/2021."

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Pedido de demissão"


def test_pediu_demissao():
    texto = "A autora pediu demissão e cumpriu aviso trabalhado."

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Pedido de demissão"


def test_termino_do_contrato():
    texto = "Houve término do prazo do contrato de experiência."

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Término de contrato"


def test_indireta_prevalece_sobre_sem_justa_causa():
    texto = """
    O autor foi demitido sem justa causa, mas passou a pleitear rescisão indireta
    em razão de atrasos salariais posteriores.
    """

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Rescisão indireta"


def test_sem_justa_prevalece_sobre_com_justa_quando_ambos_casam():
    """Primeira ramificação que casa na cadeia vence; SJC vem antes de JC."""
    texto = """
    A inicial narra que o obreiro foi dispensado sem justa causa.
    A defesa sustenta com justa causa em preliminar.
    """

    r = pre_extract(texto)

    assert r["medium"]["motivo_rescisao"] == "Sem justa causa"


def test_sem_mencao_nao_preenche():
    texto = "Condeno horas extras e intervalo intrajornada."

    r = pre_extract(texto)

    assert "motivo_rescisao" not in r["medium"]


def test_motivo_rescisao_em_medium_nao_high():
    texto = "Reconheço rescisão indireta."

    r = pre_extract(texto)

    assert "motivo_rescisao" in r["medium"]
    assert "motivo_rescisao" not in r["high"]

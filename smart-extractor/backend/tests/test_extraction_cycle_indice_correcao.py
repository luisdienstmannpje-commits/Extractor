"""Ciclo incremental — indice_correcao (MEDIUM, prioridades ADC58 > IPCA+SELIC > unitários)."""

from services.pre_extractor import pre_extract


def test_adc58_tem_prioridade_sobre_demais_mencoes():
    texto = """
    DISPOSITIVO
    Aplica-se a ADC 58 do STF. Correção pelo IPCA-E e juros pela SELIC.
    """

    r = pre_extract(texto)

    assert (
        r["medium"]["indice_correcao"]
        == "IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF"
    )


def test_ipca_e_selic_sem_adc():
    texto = """
    Atualização monetária pelo IPCA-E até o ajuizamento e SELIC na fase de execução.
    """

    r = pre_extract(texto)

    assert (
        r["medium"]["indice_correcao"]
        == "IPCA-E (pré-judicial) / SELIC (pós-ajuizamento)"
    )


def test_somente_ipca_e():
    texto = "A condenação será atualizada pelo IPCA-E."

    r = pre_extract(texto)

    assert r["medium"]["indice_correcao"] == "IPCA-E"


def test_somente_selic():
    texto = "Os juros de mora incidem pela SELIC."

    r = pre_extract(texto)

    assert r["medium"]["indice_correcao"] == "SELIC"


def test_tr_explicito():
    texto = "Correção monetária pela TR da época dos fatos."

    r = pre_extract(texto)

    assert r["medium"]["indice_correcao"] == "TR"


def test_atualizacao_pela_tr():
    texto = "Haverá atualização pela TR conforme súmulas."

    r = pre_extract(texto)

    assert r["medium"]["indice_correcao"] == "TR"


def test_sem_mencao_nao_preenche():
    texto = "O pedido limita-se a horas extras e intervalo."

    r = pre_extract(texto)

    assert "indice_correcao" not in r["medium"]


def test_indice_correcao_em_medium_nao_high():
    texto = "Valores corrigidos pelo IPCA-E."

    r = pre_extract(texto)

    assert "indice_correcao" in r["medium"]
    assert "indice_correcao" not in r["high"]


def test_adc58_variacao_hifen_espaco():
    texto = "Conforme ADC-58 do Supremo, observa-se o regime híbrido de índices."

    r = pre_extract(texto)

    assert (
        r["medium"]["indice_correcao"]
        == "IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF"
    )

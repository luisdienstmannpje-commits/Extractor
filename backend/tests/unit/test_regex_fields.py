"""
tests/unit/test_regex_fields.py

Testes unitários do PreExtractor (services/pre_extractor.py).
Zero dependências de IA ou PDF — testa apenas a lógica regex.

Execute com:
    pytest tests/unit/test_regex_fields.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from services.pre_extractor import PreExtractor, pre_extract


# ── Helpers ───────────────────────────────────────────────────────────────────

def _high(texto: str, campo: str):
    """Extrai um campo HIGH do texto."""
    return PreExtractor(texto).run()["high"].get(campo)

def _medium(texto: str, campo: str):
    """Extrai um campo MEDIUM do texto."""
    return PreExtractor(texto).run()["medium"].get(campo)


# ═════════════════════════════════════════════════════════════════════════════
# numero_processo (HIGH)
# ═════════════════════════════════════════════════════════════════════════════

class TestNumeroProcesso:

    @pytest.mark.parametrize("texto,esperado", [
        # Formato CNJ padrão (todos com DD correto)
        ("Processo nº 0001234-58.2023.5.04.0001", "0001234-58.2023.5.04.0001"),
        # Cabeçalho com "Autos"
        ("Autos: 0009999-43.2022.5.02.0032", "0009999-43.2022.5.02.0032"),
        # No meio do texto
        ("No processo 0001111-47.2021.5.15.0001 foi proferida sentença", "0001111-47.2021.5.15.0001"),
        # Prefixo "N°"
        ("N° 0007777-58.2024.5.03.0005 — TRT3", "0007777-58.2024.5.03.0005"),
    ])
    def test_formato_cnj(self, texto, esperado):
        assert _high(texto, "numero_processo") == esperado

    def test_sem_numero(self):
        assert _high("Sentença sem número de processo", "numero_processo") is None

    def test_numero_incompleto_ignorado(self):
        assert _high("Processo 12345-67.2023", "numero_processo") is None

    def test_prioridade_cabecalho(self):
        """Prefixo 'Processo:' é encontrado mesmo havendo CNJ solto antes no texto."""
        texto = (
            "Sentença no feito 0000001-76.2020.5.01.0001.\n"
            "Processo: 0001234-58.2023.5.04.0001\n"
            "Reclamante: João"
        )
        assert _high(texto, "numero_processo") == "0001234-58.2023.5.04.0001"

    def test_digito_invalido_cai_para_medium(self):
        """DD incorreto não promove para HIGH — fica MEDIUM para IA corrigir."""
        resultado = pre_extract("Processo nº 0001234-00.2023.5.04.0001")
        assert resultado["high"].get("numero_processo") is None
        assert resultado["medium"].get("numero_processo") == "0001234-00.2023.5.04.0001"


# ═════════════════════════════════════════════════════════════════════════════
# data_sentenca (HIGH)
# ═════════════════════════════════════════════════════════════════════════════

class TestDataSentenca:

    def test_assinatura_eletronica(self):
        texto = "Assinado eletronicamente em 10/03/2024"
        assert _high(texto, "data_sentenca") == "10/03/2024"

    def test_assinatura_digital(self):
        texto = "Assinado digitalmente em 22/07/2025"
        assert _high(texto, "data_sentenca") == "22/07/2025"

    def test_multiplas_assinaturas_pega_mais_recente(self):
        texto = (
            "Assinado eletronicamente em 01/01/2024\n"
            "Assinado eletronicamente em 15/03/2024\n"
        )
        assert _high(texto, "data_sentenca") == "15/03/2024"

    def test_publicado_em_fallback(self):
        texto = "Publicado em 05/06/2024"
        assert _high(texto, "data_sentenca") == "05/06/2024"

    def test_data_por_extenso_no_rodape(self):
        texto = "Porto Alegre, 10 de março de 2024."
        assert _high(texto, "data_sentenca") == "10/03/2024"

    def test_sem_data(self):
        assert _high("Sentença sem data", "data_sentenca") is None


# ═════════════════════════════════════════════════════════════════════════════
# justica_gratuita (HIGH)
# ═════════════════════════════════════════════════════════════════════════════

class TestJusticaGratuita:

    @pytest.mark.parametrize("texto", [
        "Defiro a justiça gratuita.",
        "justiça gratuita deferida ao reclamante",
        "Defiro os benefícios da assistência judiciária",
        "Defiro os benefícios da justiça gratuita, nos termos deferidos",
    ])
    def test_deferida(self, texto):
        assert _high(texto, "justica_gratuita") is True

    @pytest.mark.parametrize("texto", [
        "justiça gratuita indeferida",
        "não faz jus à justiça gratuita",
    ])
    def test_indeferida(self, texto):
        assert _high(texto, "justica_gratuita") is False

    def test_nao_mencionada(self):
        assert _high("Sentença sem menção à gratuidade", "justica_gratuita") is None


# ═════════════════════════════════════════════════════════════════════════════
# tipo_rito (HIGH)
# ═════════════════════════════════════════════════════════════════════════════

class TestTipoRito:

    def test_sumarissimo(self):
        assert _high("Trata-se de rito sumaríssimo.", "tipo_rito") == "Sumaríssimo"

    def test_ordinario(self):
        assert _high("Procedimento ordinário aplicável.", "tipo_rito") == "Ordinário"

    def test_sumario_sem_acento(self):
        assert _high("rito sumarissimo adotado", "tipo_rito") == "Sumaríssimo"

    def test_desconhecido(self):
        assert _high("Sem menção ao rito", "tipo_rito") is None


# ═════════════════════════════════════════════════════════════════════════════
# data_admissao (MEDIUM)
# ═════════════════════════════════════════════════════════════════════════════

class TestDataAdmissao:

    @pytest.mark.parametrize("texto,esperado", [
        # Padrões originais
        ("admitido em 15/01/2020", "15/01/2020"),
        ("data de admissão: 01/03/2019", "01/03/2019"),
        ("foi admitida em 01/06/2018 na empresa", "01/06/2018"),
        ("contratada em 10/10/2021 pelo regime CLT", "10/10/2021"),
        ("início do contrato em 05/05/2017", "05/05/2017"),
        # Novos padrões — FASE Q
        ("empregado em 01/03/2021 pela reclamada", "01/03/2021"),
        ("com início em 15/04/2019", "15/04/2019"),
        ("contratação em 10/08/2020 pelo regime CLT", "10/08/2020"),
        ("data de contratação: 05/05/2018", "05/05/2018"),
        ("início do vínculo em 01/01/2022", "01/01/2022"),
        ("início do vínculo empregatício em 15/03/2023", "15/03/2023"),
    ])
    def test_formatos_variados(self, texto, esperado):
        assert _medium(texto, "data_admissao") == esperado

    def test_sem_data(self):
        assert _medium("Sentença sem data de admissão", "data_admissao") is None

    def test_a_partir_de_nao_extrai(self):
        """'a partir de' é genérico demais — não deve capturar data de admissão."""
        assert _medium("vigente a partir de 01/01/2024", "data_admissao") is None

    def test_desde_nao_extrai(self):
        """'desde' isolado é genérico demais — não deve capturar data de admissão."""
        assert _medium("os reflexos incidem desde 01/06/2020", "data_admissao") is None


# ═════════════════════════════════════════════════════════════════════════════
# data_demissao (MEDIUM)
# ═════════════════════════════════════════════════════════════════════════════

class TestDataDemissao:

    @pytest.mark.parametrize("texto,esperado", [
        # Padrões originais
        ("dispensado em 30/06/2023", "30/06/2023"),
        ("data da rescisão: 15/12/2022", "15/12/2022"),
        ("desligado em 01/03/2024 da empresa", "01/03/2024"),
        ("término do contrato em 31/01/2025", "31/01/2025"),
        # Novos padrões — FASE Q
        ("desligamento em 31/12/2023", "31/12/2023"),
        ("demissão em 30/06/2023", "30/06/2023"),
        ("rescisão contratual em 15/11/2022", "15/11/2022"),
        ("com rescisão em 01/07/2024", "01/07/2024"),
        ("data de demissão: 28/02/2023", "28/02/2023"),
    ])
    def test_formatos_variados(self, texto, esperado):
        assert _medium(texto, "data_demissao") == esperado


# ═════════════════════════════════════════════════════════════════════════════
# salario_base (MEDIUM)
# ═════════════════════════════════════════════════════════════════════════════

class TestSalarioBase:

    def test_salario_simples(self):
        val = _medium("salário de R$ 3.500,00 mensais", "salario_base")
        assert val is not None
        assert "3.500" in val or "3500" in val

    def test_salario_sem_cifrao(self):
        val = _medium("remuneração de 5.000,00 por mês", "salario_base")
        assert val is not None

    def test_salario_abaixo_minimo_ignorado(self):
        assert _medium("valor de R$ 100,00", "salario_base") is None

    def test_salario_acima_maximo_ignorado(self):
        assert _medium("salário de R$ 200.000,00", "salario_base") is None

    def test_multiplos_valores_pega_mais_frequente(self):
        """Quando o mesmo salário aparece várias vezes, deve ser selecionado."""
        texto = (
            "Salário de R$ 3.500,00 mensais. "
            "A empresa alegou remuneração de R$ 2.000,00. "
            "O juiz reconheceu salário de R$ 3.500,00. "
            "Base de cálculo: salário de R$ 3.500,00."
        )
        val = _medium(texto, "salario_base")
        assert val is not None
        assert "3.500" in val

    def test_remuneracao_mensal(self):
        val = _medium("remuneração mensal de R$ 2.500,00", "salario_base")
        assert val is not None
        assert "2.500" in val or "2500" in val

    def test_remuneracao_mensal_bruta(self):
        val = _medium("remuneração mensal bruta de R$ 4.000,00", "salario_base")
        assert val is not None
        assert "4.000" in val or "4000" in val

    def test_ultima_remuneracao(self):
        val = _medium("última remuneração de R$ 3.200,00", "salario_base")
        assert val is not None
        assert "3.200" in val or "3200" in val

    def test_salario_fixo(self):
        val = _medium("salário fixo de R$ 2.800,00 por mês", "salario_base")
        assert val is not None
        assert "2.800" in val or "2800" in val

    def test_recebia_o_salario(self):
        val = _medium("recebia o salário de R$ 1.900,00 mensais", "salario_base")
        assert val is not None
        assert "1.900" in val or "1900" in val


# ═════════════════════════════════════════════════════════════════════════════
# horario_trabalho (MEDIUM) — FASE I
# ═════════════════════════════════════════════════════════════════════════════

class TestHorarioTrabalho:

    def test_trabalhava_das(self):
        val = _medium("trabalhava das 08h às 17h com 1h de intervalo", "horario_trabalho")
        assert val is not None
        assert "08h" in val
        assert "17h" in val

    def test_horario_de_trabalho_com_dois_pontos(self):
        val = _medium("horário de trabalho: das 08:00 às 17:00", "horario_trabalho")
        assert val is not None
        assert "08:00" in val and "17:00" in val

    def test_laborava_das(self):
        val = _medium("laborava das 7h às 16h", "horario_trabalho")
        assert val is not None
        assert "7h" in val and "16h" in val

    def test_jornada_das(self):
        val = _medium("jornada de trabalho das 08h às 18h", "horario_trabalho")
        assert val is not None
        assert "08h" in val and "18h" in val

    def test_horario_sem_contexto_ignorado(self):
        val = _medium("Sentença publicada em 01/01/2024.", "horario_trabalho")
        assert val is None

    def test_capture_inclui_intervalo(self):
        val = _medium(
            "trabalhava das 08h30 às 17h30 com 1h de intervalo para almoço",
            "horario_trabalho",
        )
        assert val is not None
        assert "intervalo" in val.lower() or "almoço" in val.lower()

    def test_horario_formato_hhmm(self):
        val = _medium("horário das 07:30 às 16:30", "horario_trabalho")
        assert val is not None
        assert "07:30" in val


# ═════════════════════════════════════════════════════════════════════════════
# jornada_contratual (MEDIUM) — FASE I
# ═════════════════════════════════════════════════════════════════════════════

class TestJornadaContratual:

    def test_jornada_diaria_e_semanal(self):
        val = _medium("jornada de 8 horas diárias e 44 horas semanais", "jornada_contratual")
        assert val is not None
        assert "8" in val and "44" in val

    def test_jornada_semanal_sem_diaria(self):
        val = _medium("jornada de trabalho de 44 horas semanais", "jornada_contratual")
        assert val is not None
        assert "44" in val

    def test_carga_horaria_semanal(self):
        val = _medium("carga horária de 40 horas semanais", "jornada_contratual")
        assert val is not None
        assert "40" in val

    def test_jornada_com_extenso(self):
        val = _medium(
            "jornada de 8 (oito) horas diárias e 44 (quarenta e quatro) horas semanais",
            "jornada_contratual",
        )
        assert val is not None
        assert "8" in val and "44" in val

    def test_jornada_diaria_apenas(self):
        val = _medium("jornada de 8 horas diárias", "jornada_contratual")
        assert val is not None
        assert "8" in val

    def test_sem_jornada(self):
        val = _medium("Sentença condenatória publicada em 2024.", "jornada_contratual")
        assert val is None


# ═════════════════════════════════════════════════════════════════════════════
# funcao_reclamante (MEDIUM) — FASE L
# ═════════════════════════════════════════════════════════════════════════════

class TestFuncaoReclamante:

    @pytest.mark.parametrize("texto,esperado", [
        ("exercia a função de Operador de Caixa,", "Operador de Caixa"),
        ("contratado como Motorista Carreteiro.", "Motorista Carreteiro"),
        ("admitido como Auxiliar de Produção;", "Auxiliar de Produção"),
        ("trabalhava como Analista de Sistemas,", "Analista de Sistemas"),
        ("ocupava o cargo de Gerente de Vendas,", "Gerente de Vendas"),
        ("na função de Técnico de Segurança do Trabalho,", "Técnico de Segurança do Trabalho"),
    ])
    def test_gatilhos_comuns(self, texto, esperado):
        val = _medium(texto, "funcao_reclamante")
        assert val == esperado

    def test_sem_cargo(self):
        assert _medium("Sentença condenatória publicada em 2024.", "funcao_reclamante") is None

    def test_sem_stop_char_sem_limite_nao_extrai(self):
        """Sem delimitador após o cargo, o resultado pode ser None ou truncado — não deve capturar texto ilimitado."""
        val = _medium(
            "contratado como Motorista sem vírgula nem ponto seguindo indeterminadamente",
            "funcao_reclamante",
        )
        # Aceitável: None ou texto com no máximo 40 chars
        assert val is None or len(val) <= 40

    def test_exercia_funcao_sem_artigo(self):
        val = _medium("exercia função de Vendedor.", "funcao_reclamante")
        assert val is not None
        assert "Vendedor" in val


# ═════════════════════════════════════════════════════════════════════════════
# vara_trabalho (HIGH) — FASE N
# ═════════════════════════════════════════════════════════════════════════════

class TestVaraTrabalho:

    @pytest.mark.parametrize("texto,esperado", [
        ("3ª Vara do Trabalho de São Paulo,", "3ª Vara do Trabalho de São Paulo"),
        ("1a Vara do Trabalho de Campinas.", "1a Vara do Trabalho de Campinas"),
        ("Vara do Trabalho de Porto Alegre\n", "Vara do Trabalho de Porto Alegre"),
        ("12ª Vara do Trabalho de Belo Horizonte,", "12ª Vara do Trabalho de Belo Horizonte"),
        ("oriundo da 5ª Vara do Trabalho de Guarulhos,", "5ª Vara do Trabalho de Guarulhos"),
        ("2ª Vara do Trabalho de São Bernardo do Campo,", "2ª Vara do Trabalho de São Bernardo do Campo"),
    ])
    def test_formatos_comuns(self, texto, esperado):
        val = _high(texto, "vara_trabalho")
        assert val == esperado

    def test_sem_vara(self):
        assert _high("Sentença proferida pelo MM. Juízo.", "vara_trabalho") is None

    def test_sem_cidade_nao_extrai(self):
        # "Vara do Trabalho" sem "de [cidade]" não deve ser capturado
        assert _high("oriundo da Vara do Trabalho.", "vara_trabalho") is None

    def test_captura_cidade_com_preposicao(self):
        """Cidade composta com 'do'/'de' interna deve ser capturada integralmente."""
        val = _high("2ª Vara do Trabalho de São José dos Campos,", "vara_trabalho")
        assert val is not None
        assert "São José dos Campos" in val


# ═════════════════════════════════════════════════════════════════════════════
# juiz_responsavel (HIGH)
# ═════════════════════════════════════════════════════════════════════════════

class TestJuizResponsavel:

    @pytest.mark.parametrize("texto,esperado", [
        ("MM. Juíza do Trabalho: Dra. Maria José da Silva\n", "Maria José da Silva"),
        ("Juiz do Trabalho: João Carlos de Oliveira,", "João Carlos de Oliveira"),
        ("Juíza Titular: Ana Beatriz Ferreira,", "Ana Beatriz Ferreira"),
        ("Juiz Substituto: Pedro Henrique Santos\n", "Pedro Henrique Santos"),
        ("MM. Juiz: Carlos Alberto Lima,", "Carlos Alberto Lima"),
        ("Juíza do Trabalho: Dr. Fernanda Lima Sousa\n", "Fernanda Lima Sousa"),
    ])
    def test_formatos_comuns(self, texto, esperado):
        assert _high(texto, "juiz_responsavel") == esperado

    def test_sem_rotulo_nao_extrai(self):
        """'juiz' em contexto narrativo sem rótulo não deve extrair."""
        assert _high("O juiz deferiu o pedido de aviso prévio.", "juiz_responsavel") is None

    def test_nome_unico_rejeitado(self):
        """Captura com apenas um token não deve ser aceita."""
        assert _high("Juiz: Carlos,", "juiz_responsavel") is None

    def test_nome_com_titulo_stripado(self):
        """Título Dr/Dra não deve aparecer no valor capturado."""
        val = _high("Juíza do Trabalho: Dra. Renata Oliveira Souza,", "juiz_responsavel")
        assert val is not None
        assert not val.startswith("Dr")


# ═════════════════════════════════════════════════════════════════════════════
# advogado_reclamante / advogado_reclamada (HIGH)
# ═════════════════════════════════════════════════════════════════════════════

class TestAdvogados:

    @pytest.mark.parametrize("texto,esperado", [
        ("Adv. do Reclamante: Maria Silva Santos\n", "Maria Silva Santos"),
        ("Adv. do Reclamante: Dr. João Paulo Ferreira OAB", "João Paulo Ferreira"),
        ("Advogado do Reclamante: Dra. Ana Lima (OAB/SP 123456)", "Ana Lima"),
        ("Adv. do Reclamante: Carlos Eduardo de Souza,", "Carlos Eduardo de Souza"),
    ])
    def test_reclamante(self, texto, esperado):
        assert _high(texto, "advogado_reclamante") == esperado

    @pytest.mark.parametrize("texto,esperado", [
        ("Adv. da Reclamada: Pedro Henrique Costa\n", "Pedro Henrique Costa"),
        ("Adv. da Reclamada: Dra. Beatriz Rocha Pereira OAB", "Beatriz Rocha Pereira"),
        ("Advogada da Reclamada: Fernanda Oliveira (OAB/RJ 55555)", "Fernanda Oliveira"),
        ("Adv. da Reclamado: Lucas Martins da Silva,", "Lucas Martins da Silva"),
    ])
    def test_reclamada(self, texto, esperado):
        assert _high(texto, "advogado_reclamada") == esperado

    def test_sem_rotulo_nao_extrai(self):
        assert _high("O advogado do reclamante requereu horas extras.", "advogado_reclamante") is None
        assert _high("O advogado da reclamada contestou o pedido.", "advogado_reclamada") is None

    def test_nome_unico_rejeitado(self):
        """Um único token não deve ser aceito como nome de advogado."""
        assert _high("Adv. do Reclamante: Silva,", "advogado_reclamante") is None

    def test_nao_confunde_partes(self):
        """Rótulo 'Reclamante' não deve capturar o advogado da 'Reclamada' e vice-versa."""
        texto = "Adv. do Reclamante: João da Silva\nAdv. da Reclamada: Maria Souza"
        assert _high(texto, "advogado_reclamante") == "João da Silva"
        assert _high(texto, "advogado_reclamada") == "Maria Souza"


# ═════════════════════════════════════════════════════════════════════════════
# indice_correcao (MEDIUM)
# ═════════════════════════════════════════════════════════════════════════════

class TestIndiceCorrecao:

    def test_adc58_prioritario(self):
        texto = "correção conforme ADC 58 do STF"
        val = _medium(texto, "indice_correcao")
        assert val is not None
        assert "ADC 58" in val

    def test_ipca_e_selic(self):
        texto = "IPCA-E na fase pré-judicial e SELIC após ajuizamento"
        val = _medium(texto, "indice_correcao")
        assert val is not None
        assert "IPCA" in val.upper()

    def test_apenas_selic(self):
        val = _medium("correção pela SELIC", "indice_correcao")
        assert val == "SELIC"

    def test_apenas_tr(self):
        val = _medium("atualização pela TR", "indice_correcao")
        assert val == "TR"

    def test_sem_indice(self):
        assert _medium("Sentença sem menção a índice", "indice_correcao") is None


# ═════════════════════════════════════════════════════════════════════════════
# motivo_rescisao (MEDIUM)
# ═════════════════════════════════════════════════════════════════════════════

class TestMotivoRescisao:

    @pytest.mark.parametrize("texto,esperado", [
        ("dispensado sem justa causa", "Sem justa causa"),
        ("demissão sem justa causa", "Sem justa causa"),
        ("com justa causa pelo empregador", "Com justa causa"),
        ("rescisão indireta por falta grave do empregador", "Rescisão indireta"),
        ("pedido de demissão do reclamante", "Pedido de demissão"),
        ("término do prazo do contrato", "Término de contrato"),
    ])
    def test_motivos_principais(self, texto, esperado):
        assert _medium(texto, "motivo_rescisao") == esperado

    def test_rescisao_indireta_tem_prioridade_sobre_justa_causa(self):
        """Texto com "rescisão indireta" não deve ser classificado como "com justa causa"."""
        texto = "rescisão indireta em razão da justa causa do empregador"
        assert _medium(texto, "motivo_rescisao") == "Rescisão indireta"


# ═════════════════════════════════════════════════════════════════════════════
# divisor_horas (MEDIUM)
# ═════════════════════════════════════════════════════════════════════════════

class TestDivisorHoras:

    @pytest.mark.parametrize("texto,esperado", [
        ("divisor de 220", "220"),
        ("divisor 150 para horas extras", "150"),
        ("divisor de 180 horas", "180"),
        ("44 horas semanais", "220"),   # inferência por jornada
        ("40 horas semanais", "200"),
        ("36 horas semanais", "180"),
        ("30 horas semanais", "150"),
    ])
    def test_divisores_comuns(self, texto, esperado):
        assert _medium(texto, "divisor_horas") == esperado

    def test_sem_divisor(self):
        assert _medium("Sentença sem jornada mencionada", "divisor_horas") is None


# ═════════════════════════════════════════════════════════════════════════════
# aviso_previo_dias (MEDIUM)
# ═════════════════════════════════════════════════════════════════════════════

class TestAvisoPrevioDias:

    @pytest.mark.parametrize("texto,esperado", [
        ("aviso prévio de 30 dias", "30 dias"),
        ("aviso prévio indenizado de 42 dias", "42 dias"),
        ("aviso previo de 90 dias", "90 dias"),
        ("aviso prévio trabalhado de 30 dias", "30 dias"),
        ("aviso prévio proporcional de 25 dias", "25 dias"),
        ("aviso prévio integral de 33 dias", "33 dias"),
        ("aviso prévio de 30 (trinta) dias", "30 dias"),
        ("42 dias de aviso prévio", "42 dias"),
        ("30 dias de aviso previo trabalhado", "30 dias"),
    ])
    def test_dias_validos(self, texto, esperado):
        assert _medium(texto, "aviso_previo_dias") == esperado

    def test_dias_implausivel_ignorado(self):
        """Valor fora de 20–90 dias não deve ser extraído."""
        assert _medium("aviso prévio de 5 dias", "aviso_previo_dias") is None
        assert _medium("aviso prévio de 120 dias", "aviso_previo_dias") is None


# ═════════════════════════════════════════════════════════════════════════════
# tipo_contrato (HIGH para duração; MEDIUM para natureza jurídica)
# ═════════════════════════════════════════════════════════════════════════════

class TestTipoContrato:

    @pytest.mark.parametrize("texto,esperado", [
        ("celebrado contrato de experiência pelo prazo de 45 dias", "Experiência"),
        ("período de experiência encerrado em 01/06/2020", "Experiência"),
        ("admitida para período de experiência", "Experiência"),
        ("contrato por prazo determinado de 12 meses", "Prazo determinado"),
        ("contrato a prazo determinado firmado em 2022", "Prazo determinado"),
        ("contrato de trabalho com prazo determinado", "Prazo determinado"),
    ])
    def test_tipos_high(self, texto, esperado):
        assert _high(texto, "tipo_contrato") == esperado

    @pytest.mark.parametrize("texto,esperado", [
        ("reconhecido o vínculo de emprego CLT", "CLT"),
        ("pejotização reconhecida — fraude à CLT", "Pejotização reconhecida"),
        ("autônomo reconhecido como empregado", "Autônomo reconhecido"),
    ])
    def test_tipos_medium(self, texto, esperado):
        assert _medium(texto, "tipo_contrato") == esperado

    def test_experiencia_tem_precedencia_sobre_clt(self):
        """Contrato de experiência é HIGH e sobrescreve vínculo CLT no mesmo texto."""
        texto = "contrato de experiência firmado com vínculo de emprego CLT"
        assert _high(texto, "tipo_contrato") == "Experiência"

    def test_sem_tipo_nao_extrai(self):
        assert _high("O reclamante foi dispensado sem justa causa", "tipo_contrato") is None
        assert _medium("O reclamante foi dispensado sem justa causa", "tipo_contrato") is None


# ═════════════════════════════════════════════════════════════════════════════
# aviso_previo_tipo (HIGH)
# ═════════════════════════════════════════════════════════════════════════════

class TestAvisoTipo:

    @pytest.mark.parametrize("texto,esperado", [
        ("aviso prévio trabalhado de 30 dias", "trabalhado"),
        ("aviso previo trabalhado cumprido integralmente", "trabalhado"),
        ("O reclamante cumpriu aviso prévio trabalhado", "trabalhado"),
        ("aviso prévio indenizado de 42 dias", "indenizado"),
        ("aviso previo indenizado convertido em pecúnia", "indenizado"),
        ("indenização substitutiva do aviso prévio", "indenizado"),
        ("aviso prévio convertido em indenização", "indenizado"),
    ])
    def test_tipos_principais(self, texto, esperado):
        assert _high(texto, "aviso_previo_tipo") == esperado

    def test_indenizado_tem_precedencia_sobre_trabalhado(self):
        """Quando ambas as formas aparecem, indenizado prevalece (é o determinado)."""
        texto = "O reclamante trabalhou durante o aviso prévio trabalhado porém a sentença deferiu o aviso prévio indenizado"
        assert _high(texto, "aviso_previo_tipo") == "indenizado"

    def test_sem_aviso_nao_extrai(self):
        assert _high("O reclamante foi dispensado sem justa causa", "aviso_previo_tipo") is None

    def test_aviso_previo_sem_tipo_nao_extrai(self):
        """'aviso prévio' sem qualificador não deve extrair."""
        assert _high("aviso prévio de 30 dias foi pago", "aviso_previo_tipo") is None


# ═════════════════════════════════════════════════════════════════════════════
# Teste integrado — run() completo
# ═════════════════════════════════════════════════════════════════════════════

class TestRunCompleto:

    def test_sentenca_completa(self, texto_sentenca_simples):
        """Testa o run() com um texto de sentença real (fixture do conftest)."""
        resultado = pre_extract(texto_sentenca_simples)
        high   = resultado["high"]
        medium = resultado["medium"]

        # HIGH — devem estar presentes
        assert high.get("numero_processo") == "0001234-58.2023.5.04.0001"
        assert high.get("data_sentenca") == "10/03/2024"
        assert high.get("justica_gratuita") is True
        assert high.get("tipo_rito") == "Ordinário"

        # MEDIUM — devem estar presentes
        assert medium.get("data_admissao") == "15/01/2020"
        assert medium.get("data_demissao") == "30/06/2023"
        assert medium.get("motivo_rescisao") == "Sem justa causa"
        assert medium.get("divisor_horas") == "220"

    def test_texto_vazio_nao_crasha(self):
        resultado = pre_extract("")
        assert resultado["high"] == {}
        assert resultado["medium"] == {}

    def test_texto_irrelevante_retorna_vazio(self):
        resultado = pre_extract("Lorem ipsum dolor sit amet, consectetur adipiscing elit.")
        assert resultado["high"] == {}
        assert resultado["medium"] == {}

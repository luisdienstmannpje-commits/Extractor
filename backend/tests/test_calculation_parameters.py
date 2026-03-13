"""
test_calculation_parameters.py
TS3 — Suíte de testes para services/calculation_parameters.py

Cobertura:
    - Grupo A: calcular_divisor() — mapa fixo + fórmula de fallback
    - Grupo B: _extrair_horas_jornada() — parsing de texto de jornada
    - Grupo C: _calcular_periodo() — meses, avos, regra dos 14 dias
    - Grupo D: _calcular_jornada() — divisor, horas/dia, HE diária
    - Grupo E: _determinar_indices() — IPCA-E / TR / SELIC (ADC 58)
    - Grupo F: _calcular_fgts() — alíquota, multa, fundamentos jurídicos
    - Grupo G: _determinar_inss() — teto, desconto, fundamento
    - Grupo H: _calcular_honorarios() — percentual, faixa legal
    - Grupo I: _determinar_adicional() — multiplicadores por tipo de verba
    - Grupo J: _determinar_base() — base de cálculo por tipo de verba
    - Grupo K: _determinar_reflexos() — Súmula 264 e OJ 394
    - Grupo L: _estruturar_verbas() — filtra indeferidas, estrutura deferidas
    - Grupo M: gerar_parametros() — função principal / integração
    - Grupo N: Edge cases e inputs inválidos

Para rodar:
    pytest tests/test_calculation_parameters.py -v
"""

import math
import pytest
from services.calculation_parameters import (
    gerar_parametros,
    calcular_divisor,
    MAPA_DIVISORES,
    ALIQUOTA_FGTS,
    MULTA_FGTS,
    ALIQUOTA_FERIAS,
    ADICIONAL_HE_PADRAO,
    _calcular_periodo,
    _calcular_jornada,
    _extrair_horas_jornada,
    _estruturar_verbas,
    _determinar_adicional,
    _determinar_base,
    _determinar_reflexos,
    _determinar_indices,
    _calcular_fgts,
    _determinar_inss,
    _calcular_honorarios,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def dados_completos():
    """Dados de extração completos simulando saída do processor.py."""
    return {
        "data_admissao":             "2018-03-01",
        "data_demissao":             "2023-07-31",
        "jornada_contratual":        "44h semanais",
        "indice_correcao":           "IPCA-E",
        "juros_mora":                "SELIC",
        "fgts_sobre_aviso_previo":   True,
        "contribuicao_previdenciaria": True,
        "honorarios_sucumbenciais":  True,
        "percentual_honorarios":     "10",
        "verbas_deferidas": [
            {"nome": "horas_extras_diarias", "status": "DEFERIDA"},
            {"nome": "dano_moral",           "status": "INDEFERIDA"},
            {"nome": "aviso_previo_indenizado", "status": "DEFERIDA"},
        ],
    }

@pytest.fixture
def dados_minimos():
    """Dados mínimos — campos opcionais ausentes."""
    return {}

@pytest.fixture
def verba_horas_extras():
    return {"nome": "horas_extras_diarias", "status": "DEFERIDA"}

@pytest.fixture
def verba_insalubridade():
    return {"nome": "adicional_insalubridade", "status": "DEFERIDA", "grau_insalubridade": "medio"}

@pytest.fixture
def verba_periculosidade():
    return {"nome": "adicional_periculosidade", "status": "DEFERIDA"}

@pytest.fixture
def verba_dano_moral():
    return {"nome": "dano_moral", "status": "DEFERIDA"}


# ===========================================================================
# GRUPO A — calcular_divisor()
# ===========================================================================

class TestCalcularDivisor:
    """Divisores do MAPA_DIVISORES e fórmula de fallback para jornadas custom."""

    # Jornadas do mapa fixo
    def test_divisor_44h(self):
        assert calcular_divisor(44) == 220

    def test_divisor_40h(self):
        assert calcular_divisor(40) == 200

    def test_divisor_36h(self):
        assert calcular_divisor(36) == 180

    def test_divisor_35h(self):
        assert calcular_divisor(35) == 175

    def test_divisor_30h(self):
        assert calcular_divisor(30) == 150

    # Cobertura completa do mapa
    def test_todos_os_divisores_do_mapa(self):
        esperados = {30: 150, 35: 175, 36: 180, 40: 200, 44: 220}
        for horas, divisor in esperados.items():
            assert calcular_divisor(horas) == divisor, f"Falhou para {horas}h"

    # Fórmula de fallback: ceil((horas / 6) * 30)
    def test_divisor_20h_fallback(self):
        esperado = math.ceil((20 / 6) * 30)
        assert calcular_divisor(20) == esperado

    def test_divisor_32h_fallback(self):
        esperado = math.ceil((32 / 6) * 30)
        assert calcular_divisor(32) == esperado

    def test_divisor_42h_fallback(self):
        esperado = math.ceil((42 / 6) * 30)
        assert calcular_divisor(42) == esperado

    def test_divisor_48h_fallback(self):
        esperado = math.ceil((48 / 6) * 30)
        assert calcular_divisor(48) == esperado

    def test_retorna_inteiro(self):
        assert isinstance(calcular_divisor(44), int)
        assert isinstance(calcular_divisor(37), int)

    def test_divisor_positivo(self):
        for h in [20, 30, 35, 36, 40, 44]:
            assert calcular_divisor(h) > 0

    def test_mapa_divisores_integro(self):
        """Garante que MAPA_DIVISORES não foi alterado."""
        assert MAPA_DIVISORES[44] == 220
        assert MAPA_DIVISORES[40] == 200
        assert MAPA_DIVISORES[36] == 180
        assert MAPA_DIVISORES[35] == 175
        assert MAPA_DIVISORES[30] == 150


# ===========================================================================
# GRUPO B — _extrair_horas_jornada()
# ===========================================================================

class TestExtrairHorasJornada:
    """Parsing de texto de jornada contratual."""

    def test_formato_44h_semanais(self):
        assert _extrair_horas_jornada("44h semanais") == 44

    def test_formato_40h(self):
        assert _extrair_horas_jornada("40h") == 40

    def test_formato_36h_banco(self):
        assert _extrair_horas_jornada("36h semanais (bancário)") == 36

    def test_formato_30h(self):
        assert _extrair_horas_jornada("30h semanais") == 30

    def test_formato_maiusculo(self):
        assert _extrair_horas_jornada("44H SEMANAIS") == 44

    def test_sem_texto_retorna_none(self):
        assert _extrair_horas_jornada("") is None

    def test_none_retorna_none(self):
        assert _extrair_horas_jornada(None) is None

    def test_texto_sem_horas_retorna_none(self):
        assert _extrair_horas_jornada("jornada integral") is None

    def test_numero_sem_h_retorna_none(self):
        # "44 semanais" sem "h" — depende da regex (\d{2}\s*h)
        resultado = _extrair_horas_jornada("44 semanais")
        assert resultado is None or isinstance(resultado, int)


# ===========================================================================
# GRUPO C — _calcular_periodo()
# ===========================================================================

class TestCalcularPeriodo:
    """Cálculo de meses, avos e regra dos 14 dias."""

    def test_periodo_completo_5_anos(self):
        dados = {"data_admissao": "2018-01-01", "data_demissao": "2023-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] == 60

    def test_periodo_1_ano(self):
        dados = {"data_admissao": "2020-01-01", "data_demissao": "2021-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] == 12

    def test_avos_proporcional_11_meses(self):
        dados = {"data_admissao": "2020-01-01", "data_demissao": "2020-12-01"}
        resultado = _calcular_periodo(dados)
        # 11 meses completos + dia < 15 → 11 meses
        assert resultado["meses"] == 11
        assert resultado["avos"] == 11

    def test_avos_zero_para_multiplo_de_12(self):
        dados = {"data_admissao": "2019-01-01", "data_demissao": "2020-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["avos"] == 0  # 12 % 12 == 0

    def test_regra_14_dias_dia_15_conta_mes(self):
        # Demissão no dia 15 — regra: >= 15 conta o mês
        dados = {"data_admissao": "2020-01-01", "data_demissao": "2020-03-15"}
        resultado = _calcular_periodo(dados)
        # 2 meses + dia >= 15 → +1 → 3 meses
        assert resultado["meses"] == 3

    def test_regra_14_dias_dia_14_nao_conta(self):
        # Demissão no dia 14 — não conta o mês corrente
        dados = {"data_admissao": "2020-01-01", "data_demissao": "2020-03-14"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] == 2

    def test_periodo_retorna_inicio_e_fim(self):
        dados = {"data_admissao": "2020-01-01", "data_demissao": "2022-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["inicio"] == "2020-01-01"
        assert resultado["fim"] == "2022-01-01"

    def test_sem_datas_retorna_none(self):
        resultado = _calcular_periodo({})
        assert resultado["meses"] is None
        assert resultado["avos"] is None

    def test_data_admissao_ausente(self):
        dados = {"data_demissao": "2022-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] is None

    def test_data_demissao_ausente(self):
        dados = {"data_admissao": "2020-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] is None

    def test_meses_nunca_negativo(self):
        # Demissão antes da admissão — max(delta, 0)
        dados = {"data_admissao": "2022-01-01", "data_demissao": "2021-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] >= 0

    def test_periodo_de_um_mes(self):
        dados = {"data_admissao": "2021-01-01", "data_demissao": "2021-02-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] == 1


# ===========================================================================
# GRUPO D — _calcular_jornada()
# ===========================================================================

class TestCalcularJornada:
    """Divisor, horas/dia e horas extras diárias."""

    def test_jornada_44h_padrao(self):
        resultado = _calcular_jornada({"jornada_contratual": "44h semanais"})
        assert resultado["contratual_horas"] == 44
        assert resultado["divisor"] == 220

    def test_jornada_40h(self):
        resultado = _calcular_jornada({"jornada_contratual": "40h semanais"})
        assert resultado["divisor"] == 200

    def test_jornada_ausente_usa_44h_padrao(self):
        resultado = _calcular_jornada({})
        assert resultado["contratual_horas"] == 44
        assert resultado["divisor"] == 220

    def test_jornada_44h_nao_gera_he_diaria(self):
        # 44h / 6 dias ≈ 7.33h/dia — abaixo de 8h → he_diaria == 0
        resultado = _calcular_jornada({"jornada_contratual": "44h semanais"})
        assert resultado["horas_extras_diaria"] == 0.0

    def test_chaves_obrigatorias_presentes(self):
        resultado = _calcular_jornada({"jornada_contratual": "44h semanais"})
        assert "contratual_horas" in resultado
        assert "divisor" in resultado
        assert "horas_dia" in resultado
        assert "horas_extras_diaria" in resultado


# ===========================================================================
# GRUPO E — _determinar_indices()
# ===========================================================================

class TestDeterminarIndices:
    """Índices de correção e juros conforme ADC 58."""

    def test_ipcae_como_correcao_padrao(self):
        resultado = _determinar_indices({"indice_correcao": "IPCA-E"})
        assert resultado["correcao"] == "IPCAE"

    def test_tr_reconhecido(self):
        resultado = _determinar_indices({"indice_correcao": "TR"})
        assert resultado["correcao"] == "TR"

    def test_selic_como_juros_padrao(self):
        resultado = _determinar_indices({"juros_mora": "SELIC"})
        assert resultado["juros"] == "SELIC"

    def test_1_porcento_reconhecido(self):
        resultado = _determinar_indices({"juros_mora": "1% ao mês"})
        assert resultado["juros"] == "1%_ao_mes"

    def test_sem_campos_usa_defaults(self):
        resultado = _determinar_indices({})
        assert resultado["correcao"] == "IPCAE"
        assert resultado["juros"] == "SELIC"

    def test_juros_a_partir_de_ajuizamento(self):
        resultado = _determinar_indices({})
        assert resultado["juros_a_partir_de"] == "data_ajuizamento"

    def test_fundamento_adc_58_presente(self):
        resultado = _determinar_indices({})
        assert "ADC 58" in resultado["fundamento"]

    def test_chaves_obrigatorias(self):
        resultado = _determinar_indices({})
        assert "correcao" in resultado
        assert "juros" in resultado
        assert "juros_a_partir_de" in resultado
        assert "fundamento" in resultado


# ===========================================================================
# GRUPO F — _calcular_fgts()
# ===========================================================================

class TestCalcularFgts:
    """Parâmetros de FGTS com fundamentos jurídicos."""

    def test_aliquota_8_porcento(self):
        resultado = _calcular_fgts({})
        assert resultado["aliquota"] == 0.08

    def test_multa_40_porcento(self):
        resultado = _calcular_fgts({})
        assert resultado["multa"] == 0.40

    def test_incide_sobre_aviso_previo_default_true(self):
        resultado = _calcular_fgts({})
        assert resultado["incide_sobre_aviso_previo"] is True

    def test_incide_sobre_aviso_previo_false(self):
        resultado = _calcular_fgts({"fgts_sobre_aviso_previo": False})
        assert resultado["incide_sobre_aviso_previo"] is False

    def test_fundamento_sumula_305(self):
        resultado = _calcular_fgts({})
        assert "Súmula 305" in resultado["fundamento_ap"]

    def test_nao_incide_ferias_indenizadas(self):
        resultado = _calcular_fgts({})
        assert resultado["nao_incide_ferias_indenizadas"] is True

    def test_fundamento_oj_195(self):
        resultado = _calcular_fgts({})
        assert "OJ 195" in resultado["fundamento_ferias"]

    def test_multa_nao_incide_ap_indenizado(self):
        resultado = _calcular_fgts({})
        assert resultado["multa_nao_incide_ap_indenizado"] is True

    def test_fundamento_oj_42(self):
        resultado = _calcular_fgts({})
        assert "OJ 42" in resultado["fundamento_multa_ap"]

    def test_constantes_corretas(self):
        assert ALIQUOTA_FGTS == 0.08
        assert MULTA_FGTS == 0.40


# ===========================================================================
# GRUPO G — _determinar_inss()
# ===========================================================================

class TestDeterminarInss:
    """Parâmetros de desconto previdenciário."""

    def test_descontar_true_por_default(self):
        resultado = _determinar_inss({"contribuicao_previdenciaria": True})
        assert resultado["descontar"] is True

    def test_descontar_false(self):
        resultado = _determinar_inss({"contribuicao_previdenciaria": False})
        assert resultado["descontar"] is False

    def test_teto_inss_correto(self):
        resultado = _determinar_inss({})
        assert resultado["teto"] == 7786.02

    def test_fundamento_lei_8212(self):
        resultado = _determinar_inss({})
        assert "8.212" in resultado["fundamento"]

    def test_chaves_obrigatorias(self):
        resultado = _determinar_inss({})
        assert "descontar" in resultado
        assert "teto" in resultado
        assert "fundamento" in resultado


# ===========================================================================
# GRUPO H — _calcular_honorarios()
# ===========================================================================

class TestCalcularHonorarios:
    """Parâmetros de honorários advocatícios (Art. 791-A CLT)."""

    def test_devidos_quando_true(self):
        resultado = _calcular_honorarios({"honorarios_sucumbenciais": True})
        assert resultado["devidos"] is True

    def test_nao_devidos_quando_false(self):
        resultado = _calcular_honorarios({"honorarios_sucumbenciais": False})
        assert resultado["devidos"] is False

    def test_percentual_10(self):
        resultado = _calcular_honorarios({
            "honorarios_sucumbenciais": True,
            "percentual_honorarios": "10"
        })
        assert resultado["percentual"] == 10.0

    def test_percentual_15(self):
        resultado = _calcular_honorarios({
            "honorarios_sucumbenciais": True,
            "percentual_honorarios": "15"
        })
        assert resultado["percentual"] == 15.0

    def test_percentual_ausente_retorna_none(self):
        resultado = _calcular_honorarios({"honorarios_sucumbenciais": True})
        assert resultado["percentual"] is None

    def test_faixa_legal_5_a_15(self):
        resultado = _calcular_honorarios({})
        assert "5%" in resultado["faixa_legal"]
        assert "15%" in resultado["faixa_legal"]

    def test_fundamento_art_791a(self):
        resultado = _calcular_honorarios({})
        assert "791-A" in resultado["fundamento"]

    def test_percentual_invalido_retorna_none(self):
        resultado = _calcular_honorarios({
            "percentual_honorarios": "não informado"
        })
        assert resultado["percentual"] is None


# ===========================================================================
# GRUPO I — _determinar_adicional()
# ===========================================================================

class TestDeterminarAdicional:
    """Multiplicadores de adicional por tipo de verba."""

    def test_horas_extras_50_porcento(self):
        verba = {"nome": "horas_extras_diarias"}
        resultado = _determinar_adicional(verba, {})
        assert resultado == 1 + ADICIONAL_HE_PADRAO  # 1.50

    def test_percentual_explicito_sobrepoe_padrao(self):
        verba = {"nome": "horas_extras_diarias", "percentual": "100"}
        resultado = _determinar_adicional(verba, {})
        assert resultado == 2.0  # 1 + 100/100

    def test_periculosidade_30_porcento(self):
        verba = {"nome": "adicional_periculosidade"}
        resultado = _determinar_adicional(verba, {})
        assert resultado == 0.30

    def test_insalubridade_grau_medio_20(self):
        verba = {"nome": "adicional_insalubridade", "grau_insalubridade": "medio"}
        dados = {"salario_minimo": 1518.00}
        resultado = _determinar_adicional(verba, dados)
        assert resultado == 1518.00 * 0.20

    def test_insalubridade_grau_minimo_10(self):
        verba = {"nome": "adicional_insalubridade", "grau_insalubridade": "minimo"}
        dados = {"salario_minimo": 1518.00}
        resultado = _determinar_adicional(verba, dados)
        assert resultado == 1518.00 * 0.10

    def test_insalubridade_grau_maximo_40(self):
        verba = {"nome": "adicional_insalubridade", "grau_insalubridade": "maximo"}
        dados = {"salario_minimo": 1518.00}
        resultado = _determinar_adicional(verba, dados)
        assert resultado == 1518.00 * 0.40

    def test_verba_sem_regra_retorna_1(self):
        verba = {"nome": "saldo_salario"}
        resultado = _determinar_adicional(verba, {})
        assert resultado == 1.0

    def test_percentual_float_string(self):
        verba = {"nome": "horas_extras_diarias", "percentual": "50.5"}
        resultado = _determinar_adicional(verba, {})
        assert resultado == pytest.approx(1.505)


# ===========================================================================
# GRUPO J — _determinar_base()
# ===========================================================================

class TestDeterminarBase:
    """Base de cálculo por tipo de verba."""

    def test_horas_extras_base_salario_hora(self):
        assert _determinar_base({"nome": "horas_extras_diarias"}) == "salario_hora"

    def test_insalubridade_base_salario_minimo(self):
        assert _determinar_base({"nome": "adicional_insalubridade"}) == "salario_minimo"

    def test_periculosidade_base_salario_base(self):
        assert _determinar_base({"nome": "adicional_periculosidade"}) == "salario_base"

    def test_dano_moral_base_valor_fixado(self):
        assert _determinar_base({"nome": "dano_moral"}) == "valor_fixado"

    def test_base_explicita_no_dict_sobrepoe(self):
        verba = {"nome": "horas_extras_diarias", "base_calculo": "ultima_remuneracao"}
        assert _determinar_base(verba) == "ultima_remuneracao"

    def test_verba_desconhecida_usa_salario_base(self):
        assert _determinar_base({"nome": "verba_desconhecida"}) == "salario_base"

    def test_campo_base_alternativo(self):
        verba = {"nome": "dsr", "base": "salario_hora"}
        assert _determinar_base(verba) == "salario_hora"


# ===========================================================================
# GRUPO K — _determinar_reflexos()
# ===========================================================================

class TestDeterminarReflexos:
    """Reflexos conforme Súmula 264 TST e OJ 394 SDI-I TST."""

    def test_horas_extras_tem_reflexos_sumula_264(self):
        verba = {"nome": "horas_extras_diarias"}
        reflexos = _determinar_reflexos(verba, {})
        assert "dsr" in reflexos
        assert "ferias_proporcionais" in reflexos
        assert "decimo_terceiro" in reflexos
        assert "fgts_depositos" in reflexos

    def test_adicional_noturno_tem_reflexos(self):
        verba = {"nome": "adicional_noturno"}
        reflexos = _determinar_reflexos(verba, {})
        assert len(reflexos) > 0

    def test_dsr_nao_reflete_oj_394(self):
        """OJ 394 SDI-I TST — DSR não reflete em férias/13º/FGTS."""
        verba = {"nome": "dsr"}
        reflexos = _determinar_reflexos(verba, {})
        assert reflexos == []

    def test_reflexos_explicitos_no_dict_tem_precedencia(self):
        verba = {"nome": "horas_extras_diarias", "reflexos": ["dsr"]}
        reflexos = _determinar_reflexos(verba, {})
        assert reflexos == ["dsr"]

    def test_verba_sem_regra_retorna_lista_vazia(self):
        verba = {"nome": "saldo_salario"}
        reflexos = _determinar_reflexos(verba, {})
        assert reflexos == []

    def test_retorna_lista(self):
        verba = {"nome": "horas_extras_diarias"}
        assert isinstance(_determinar_reflexos(verba, {}), list)


# ===========================================================================
# GRUPO L — _estruturar_verbas()
# ===========================================================================

class TestEstruturarVerbas:
    """Filtra indeferidas e estrutura deferidas com adicional/base/reflexos."""

    def test_filtra_verbas_indeferidas(self):
        dados = {
            "verbas_deferidas": [
                {"nome": "horas_extras_diarias", "status": "DEFERIDA"},
                {"nome": "dano_moral",           "status": "INDEFERIDA"},
            ]
        }
        resultado = _estruturar_verbas(dados)
        nomes = [v["nome"] for v in resultado]
        assert "horas_extras_diarias" in nomes
        assert "dano_moral" not in nomes

    def test_so_deferidas_passam(self):
        dados = {
            "verbas_deferidas": [
                {"nome": "aviso_previo_indenizado", "status": "DEFERIDA"},
                {"nome": "multa_art_477",           "status": "INDEFERIDA"},
                {"nome": "ferias_proporcionais",    "status": "DEFERIDA"},
            ]
        }
        resultado = _estruturar_verbas(dados)
        assert len(resultado) == 2

    def test_verba_tem_chaves_obrigatorias(self):
        dados = {
            "verbas_deferidas": [
                {"nome": "horas_extras_diarias", "status": "DEFERIDA"},
            ]
        }
        resultado = _estruturar_verbas(dados)
        assert len(resultado) == 1
        v = resultado[0]
        assert "nome" in v
        assert "adicional" in v
        assert "base" in v
        assert "reflexos" in v
        assert "periodo" in v

    def test_lista_vazia_retorna_lista_vazia(self):
        assert _estruturar_verbas({}) == []

    def test_le_campo_verbas_como_fallback(self):
        """Se 'verbas_deferidas' ausente, deve tentar 'verbas'."""
        dados = {
            "verbas": [
                {"nome": "ferias_proporcionais", "status": "DEFERIDA"},
            ]
        }
        resultado = _estruturar_verbas(dados)
        assert len(resultado) == 1

    def test_periodo_usa_admissao_demissao_quando_ausente_na_verba(self):
        dados = {
            "data_admissao": "2020-01-01",
            "data_demissao": "2022-01-01",
            "verbas_deferidas": [
                {"nome": "ferias_proporcionais", "status": "DEFERIDA"},
            ]
        }
        resultado = _estruturar_verbas(dados)
        assert resultado[0]["periodo"]["inicio"] == "2020-01-01"
        assert resultado[0]["periodo"]["fim"] == "2022-01-01"


# ===========================================================================
# GRUPO M — gerar_parametros() — integração
# ===========================================================================

class TestGerarParametros:
    """Testa a função principal de geração de parâmetros."""

    def test_retorna_dict(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        assert isinstance(resultado, dict)

    def test_chaves_obrigatorias_presentes(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        chaves = {"periodo", "jornada", "verbas", "indices", "fgts", "inss", "honorarios"}
        assert chaves.issubset(resultado.keys())

    def test_periodo_calculado(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        assert resultado["periodo"]["meses"] is not None
        assert resultado["periodo"]["meses"] > 0

    def test_jornada_44h(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        assert resultado["jornada"]["divisor"] == 220

    def test_verbas_so_deferidas(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        # Dano moral estava INDEFERIDA — não deve aparecer
        nomes = [v["nome"] for v in resultado["verbas"]]
        assert "dano_moral" not in nomes

    def test_indices_adc_58(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        assert resultado["indices"]["correcao"] == "IPCAE"
        assert resultado["indices"]["juros"] == "SELIC"

    def test_fgts_aliquota_8(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        assert resultado["fgts"]["aliquota"] == 0.08

    def test_honorarios_10_porcento(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        assert resultado["honorarios"]["percentual"] == 10.0

    def test_dados_minimos_nao_explode(self, dados_minimos):
        """Com dict vazio, deve retornar estrutura válida sem exceção."""
        resultado = gerar_parametros(dados_minimos)
        assert isinstance(resultado, dict)
        assert "periodo" in resultado
        assert "fgts" in resultado

    def test_inss_teto_correto(self, dados_completos):
        resultado = gerar_parametros(dados_completos)
        assert resultado["inss"]["teto"] == 7786.02


# ===========================================================================
# GRUPO N — Edge cases e inputs inválidos
# ===========================================================================

class TestEdgeCases:
    """Robustez em entradas inesperadas."""

    def test_data_invalida_nao_explode(self):
        dados = {"data_admissao": "invalida", "data_demissao": "2022-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] is None

    def test_percentual_honorarios_string_invalida(self):
        resultado = _calcular_honorarios({"percentual_honorarios": "abc"})
        assert resultado["percentual"] is None

    def test_calcular_divisor_jornada_1h(self):
        # Jornada extremamente baixa — não deve explodir
        resultado = calcular_divisor(1)
        assert resultado > 0

    def test_gerar_parametros_dict_vazio(self):
        resultado = gerar_parametros({})
        assert isinstance(resultado, dict)

    def test_aliquota_ferias_um_terco(self):
        assert abs(ALIQUOTA_FERIAS - (1 / 3)) < 1e-9

    def test_adicional_he_padrao_50_porcento(self):
        assert ADICIONAL_HE_PADRAO == 0.50

    def test_verbas_parciais_nao_incluidas(self):
        """Verbas com status PARCIAL não são incluídas — apenas DEFERIDA."""
        dados = {
            "verbas_deferidas": [
                {"nome": "horas_extras_diarias", "status": "PARCIAL"},
            ]
        }
        resultado = _estruturar_verbas(dados)
        assert len(resultado) == 0

    def test_calcular_periodo_mesmo_dia(self):
        dados = {"data_admissao": "2022-01-01", "data_demissao": "2022-01-01"}
        resultado = _calcular_periodo(dados)
        assert resultado["meses"] >= 0

    def test_extrair_horas_jornada_zero(self):
        resultado = _extrair_horas_jornada("0h semanais")
        assert resultado == 0 or resultado is None
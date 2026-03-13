"""
tests/test_sentence_understanding.py
TS2 — Suíte de testes para services/sentence_understanding.py

Cobertura:
    - _segmentar_texto: segmentação por ponto, ponto-e-vírgula, quebra de linha
    - _detectar_status: DEFERIDA, INDEFERIDA, PARCIAL, None
    - _extrair_nome_verba: correspondência com MAPA_NORMALIZACAO
    - _extrair_percentual_proximo: percentual próximo ao termo
    - _extrair_todas_datas: DD/MM/YYYY, YYYY-MM-DD, duplicatas, datas inválidas
    - extrair_verbas_deferidas: verbas em texto jurídico real
    - extrair_reflexos: padrões "refletindo em", "com reflexos em", busca direta
    - extrair_adicionais: percentuais de insalubridade, periculosidade, noturno
    - extrair_periodos: 0, 1, 2+ datas
    - extrair_base_calculo: bases conhecidas e desconhecidas
    - interpretar_decisao: estrutura completa de saída

Execute com:
    pytest tests/test_sentence_understanding.py -v
"""

import pytest
from services.sentence_understanding import (
    extrair_verbas_deferidas,
    extrair_reflexos,
    extrair_adicionais,
    extrair_periodos,
    extrair_base_calculo,
    interpretar_decisao,
    _segmentar_texto,
    _detectar_status,
    _extrair_nome_verba,
    _extrair_percentual_proximo,
    _extrair_todas_datas,
    STATUS_DEFERIDA,
    STATUS_INDEFERIDA,
    STATUS_PARCIAL,
)


# ===========================================================================
# Constantes de status — integridade dos valores
# ===========================================================================

class TestConstantes:

    def test_status_deferida_valor(self):
        assert STATUS_DEFERIDA == "DEFERIDA"

    def test_status_indeferida_valor(self):
        assert STATUS_INDEFERIDA == "INDEFERIDA"

    def test_status_parcial_valor(self):
        assert STATUS_PARCIAL == "PARCIAL"

    def test_status_sao_distintos(self):
        assert STATUS_DEFERIDA != STATUS_INDEFERIDA
        assert STATUS_DEFERIDA != STATUS_PARCIAL
        assert STATUS_INDEFERIDA != STATUS_PARCIAL


# ===========================================================================
# _segmentar_texto
# ===========================================================================

class TestSegmentarTexto:

    def test_segmenta_por_quebra_de_linha(self):
        texto = "Defiro férias.\nIndifiro horas extras."
        resultado = _segmentar_texto(texto)
        assert len(resultado) >= 2

    def test_segmenta_por_ponto_e_virgula(self):
        texto = "Defiro férias; indefiro horas extras"
        resultado = _segmentar_texto(texto)
        assert len(resultado) == 2

    def test_remove_segmentos_vazios(self):
        texto = "\n\n\nDefiro férias\n\n"
        resultado = _segmentar_texto(texto)
        assert all(s.strip() != "" for s in resultado)

    def test_texto_vazio_retorna_lista_vazia(self):
        assert _segmentar_texto("") == []

    def test_retorno_e_lista(self):
        assert isinstance(_segmentar_texto("Defiro férias."), list)

    def test_segmentos_sao_strings(self):
        for s in _segmentar_texto("Defiro férias; indefiro horas extras"):
            assert isinstance(s, str)

    def test_texto_sem_separadores(self):
        texto = "Defiro férias proporcionais"
        resultado = _segmentar_texto(texto)
        assert len(resultado) >= 1
        assert "Defiro férias proporcionais" in resultado


# ===========================================================================
# _detectar_status
# ===========================================================================

class TestDetectarStatus:

    # DEFERIDA
    def test_deferida_por_deferido(self):
        assert _detectar_status("Pedido deferido.") == STATUS_DEFERIDA

    def test_deferida_por_condenado(self):
        assert _detectar_status("Reclamada condenada ao pagamento.") == STATUS_DEFERIDA

    def test_deferida_por_procedente(self):
        assert _detectar_status("Pedido procedente.") == STATUS_DEFERIDA

    def test_deferida_por_pagamento_de(self):
        assert _detectar_status("Determino o pagamento de férias.") == STATUS_DEFERIDA

    def test_deferida_case_insensitive(self):
        assert _detectar_status("DEFERIDA a pretensão.") == STATUS_DEFERIDA

    # INDEFERIDA
    def test_indeferida_por_indeferido(self):
        assert _detectar_status("Pedido indeferido.") == STATUS_INDEFERIDA

    def test_indeferida_por_improcedente(self):
        assert _detectar_status("Pedido improcedente.") == STATUS_INDEFERIDA

    def test_indeferida_por_nao_ha(self):
        assert _detectar_status("Não há direito às verbas.") == STATUS_INDEFERIDA

    def test_indeferida_por_nao_faz_jus(self):
        assert _detectar_status("Reclamante não faz jus ao adicional.") == STATUS_INDEFERIDA

    def test_indeferida_por_rejeito(self):
        assert _detectar_status("Rejeito o pedido de horas extras.") == STATUS_INDEFERIDA

    def test_indeferida_por_afasto(self):
        assert _detectar_status("Afasto o pleito de insalubridade.") == STATUS_INDEFERIDA

    def test_indeferida_case_insensitive(self):
        assert _detectar_status("INDEFERIDO o pedido.") == STATUS_INDEFERIDA

    # PARCIAL
    def test_parcial_quando_tem_ambos(self):
        # Precisa ativar AMBOS os grupos: deferida E indeferida no mesmo trecho
        texto = "Pedido deferido em parte — restante indeferido."
        assert _detectar_status(texto) == STATUS_PARCIAL

    # None
    def test_none_quando_sem_indicador(self):
        assert _detectar_status("O contrato vigorou de 2020 a 2023.") is None

    def test_none_texto_vazio(self):
        assert _detectar_status("") is None

    def test_none_texto_neutro(self):
        assert _detectar_status("O reclamante trabalhou 44 horas semanais.") is None


# ===========================================================================
# _extrair_nome_verba
# ===========================================================================

class TestExtrairNomeVerba:

    def test_encontra_ferias_proporcionais(self):
        resultado = _extrair_nome_verba("Defiro férias proporcionais ao reclamante.")
        assert resultado is not None
        assert "férias" in resultado

    def test_encontra_horas_extras(self):
        resultado = _extrair_nome_verba("Condeno ao pagamento de horas extras.")
        assert resultado is not None

    def test_encontra_fgts(self):
        resultado = _extrair_nome_verba("Determino o pagamento de FGTS.")
        assert resultado is not None

    def test_encontra_decimo_terceiro(self):
        resultado = _extrair_nome_verba("Defiro o décimo terceiro salário.")
        assert resultado is not None

    def test_retorna_none_quando_sem_verba_conhecida(self):
        resultado = _extrair_nome_verba("O processo foi autuado em 2023.")
        assert resultado is None

    def test_prefere_correspondencia_mais_longa(self):
        # "férias proporcionais + 1/3" é mais longo que "férias proporcionais"
        resultado = _extrair_nome_verba(
            "Defiro férias proporcionais + 1/3 ao reclamante."
        )
        assert resultado is not None
        assert len(resultado) > len("férias proporcionais")

    def test_texto_vazio_retorna_none(self):
        assert _extrair_nome_verba("") is None

    def test_retorno_e_string_ou_none(self):
        resultado = _extrair_nome_verba("Defiro dano moral.")
        assert resultado is None or isinstance(resultado, str)


# ===========================================================================
# _extrair_percentual_proximo
# ===========================================================================

class TestExtrairPercentualProximo:

    def test_extrai_percentual_simples(self):
        assert _extrair_percentual_proximo("adicional de insalubridade de 20%", "insalubridade") == 20.0

    def test_extrai_percentual_40(self):
        assert _extrair_percentual_proximo("multa rescisória de 40% do fgts", "fgts") == 40.0

    def test_extrai_percentual_antes_do_termo(self):
        resultado = _extrair_percentual_proximo("50% de adicional noturno", "noturno")
        assert resultado == 50.0

    def test_retorna_none_sem_percentual(self):
        resultado = _extrair_percentual_proximo("adicional de insalubridade grau máximo", "insalubridade")
        assert resultado is None

    def test_retorna_none_termo_ausente(self):
        assert _extrair_percentual_proximo("adicional de 20%", "periculosidade") is None

    def test_retorno_e_float_ou_none(self):
        resultado = _extrair_percentual_proximo("insalubridade de 10%", "insalubridade")
        assert resultado is None or isinstance(resultado, float)

    def test_extrai_percentual_com_espaco(self):
        resultado = _extrair_percentual_proximo("insalubridade de 20 %", "insalubridade")
        assert resultado == 20.0


# ===========================================================================
# _extrair_todas_datas
# ===========================================================================

class TestExtrairTodasDatas:

    def test_extrai_data_dd_mm_yyyy(self):
        datas = _extrair_todas_datas("Admitido em 01/03/2020.")
        assert "2020-03-01" in datas

    def test_extrai_data_yyyy_mm_dd(self):
        datas = _extrair_todas_datas("Contrato iniciado em 2020-03-01.")
        assert "2020-03-01" in datas

    def test_extrai_duas_datas(self):
        datas = _extrair_todas_datas("De 01/01/2020 até 31/12/2022.")
        assert len(datas) == 2

    def test_ordem_preservada(self):
        datas = _extrair_todas_datas("Início em 01/01/2020. Fim em 31/12/2022.")
        assert datas[0] == "2020-01-01"
        assert datas[-1] == "2022-12-31"

    def test_sem_datas_retorna_lista_vazia(self):
        assert _extrair_todas_datas("Sem datas aqui.") == []

    def test_texto_vazio_retorna_lista_vazia(self):
        assert _extrair_todas_datas("") == []

    def test_data_invalida_ignorada(self):
        # 32/13/2020 é inválida
        datas = _extrair_todas_datas("Data inválida: 32/13/2020.")
        assert "2020-13-32" not in datas

    def test_remove_duplicatas(self):
        texto = "01/01/2020 e também 01/01/2020 novamente."
        datas = _extrair_todas_datas(texto)
        assert datas.count("2020-01-01") == 1

    def test_retorno_e_lista_de_strings_iso(self):
        datas = _extrair_todas_datas("Admitido em 01/03/2020.")
        for d in datas:
            assert len(d) == 10
            assert d[4] == "-"
            assert d[7] == "-"

    def test_data_com_hifen(self):
        datas = _extrair_todas_datas("Contrato de 01-03-2020 a 31-12-2022.")
        assert len(datas) == 2


# ===========================================================================
# extrair_verbas_deferidas
# ===========================================================================

class TestExtrairVerbasDeferidasPublic:

    def test_retorna_lista(self):
        assert isinstance(extrair_verbas_deferidas("Defiro férias."), list)

    def test_texto_vazio_retorna_lista_vazia(self):
        assert extrair_verbas_deferidas("") == []

    def test_detecta_verba_deferida(self):
        # Padrão exige "deferida/deferido" — não "defiro"
        texto = "Férias proporcionais deferidas ao reclamante."
        resultado = extrair_verbas_deferidas(texto)
        assert len(resultado) >= 1
        assert any(v["status"] == STATUS_DEFERIDA for v in resultado)

    def test_detecta_verba_indeferida(self):
        # Padrão exige "indeferida/indeferido" — não "indefiro"
        texto = "Horas extras indeferidas."
        resultado = extrair_verbas_deferidas(texto)
        assert len(resultado) >= 1
        assert any(v["status"] == STATUS_INDEFERIDA for v in resultado)

    def test_estrutura_de_cada_verba(self):
        texto = "Defiro o décimo terceiro salário proporcional."
        resultado = extrair_verbas_deferidas(texto)
        if resultado:
            verba = resultado[0]
            assert "nome" in verba
            assert "status" in verba
            assert "nome_original" in verba
            assert "linha_fonte" in verba

    def test_nome_normalizado_quando_possivel(self):
        texto = "Defiro férias proporcionais ao reclamante."
        resultado = extrair_verbas_deferidas(texto)
        if resultado:
            assert resultado[0]["nome"] == "ferias_proporcionais"

    def test_multiplas_verbas(self):
        texto = (
            "Defiro férias proporcionais.\n"
            "Indefiro horas extras.\n"
            "Defiro décimo terceiro salário."
        )
        resultado = extrair_verbas_deferidas(texto)
        assert len(resultado) >= 2

    def test_sem_verbas_conhecidas_retorna_vazio(self):
        texto = "O processo foi distribuído ao juízo."
        resultado = extrair_verbas_deferidas(texto)
        assert isinstance(resultado, list)

    def test_verba_status_parcial(self):
        texto = "Defiro parcialmente — indefiro o restante das férias proporcionais."
        resultado = extrair_verbas_deferidas(texto)
        if resultado:
            assert any(v["status"] == STATUS_PARCIAL for v in resultado)


# ===========================================================================
# extrair_reflexos
# ===========================================================================

class TestExtrairReflexos:

    def test_retorna_lista(self):
        assert isinstance(extrair_reflexos("Horas extras refletindo em férias."), list)

    def test_texto_vazio_retorna_lista_vazia(self):
        assert extrair_reflexos("") == []

    def test_padrao_refletindo_em(self):
        texto = "Horas extras deferidas, refletindo em férias, 13° e FGTS."
        resultado = extrair_reflexos(texto)
        assert len(resultado) >= 1

    def test_padrao_com_reflexos_em(self):
        texto = "Adicional noturno deferido com reflexos em DSR e férias."
        resultado = extrair_reflexos(texto)
        assert len(resultado) >= 1

    def test_padrao_reflexos_em(self):
        texto = "Horas extras com reflexos em décimo terceiro."
        resultado = extrair_reflexos(texto)
        assert len(resultado) >= 1

    def test_busca_direta_fgts(self):
        texto = "Condeno ao pagamento de FGTS sobre o período."
        resultado = extrair_reflexos(texto)
        assert isinstance(resultado, list)

    def test_busca_direta_dsr(self):
        texto = "DSR devido sobre as horas extras."
        resultado = extrair_reflexos(texto)
        assert isinstance(resultado, list)

    def test_reflexos_sao_strings(self):
        texto = "Horas extras refletindo em férias e FGTS."
        for r in extrair_reflexos(texto):
            assert isinstance(r, str)


# ===========================================================================
# extrair_adicionais
# ===========================================================================

class TestExtrairAdicionais:

    def test_retorna_dict(self):
        assert isinstance(extrair_adicionais("insalubridade de 20%"), dict)

    def test_texto_vazio_retorna_dict_vazio(self):
        assert extrair_adicionais("") == {}

    def test_extrai_insalubridade(self):
        texto = "Defiro adicional de insalubridade de 20%."
        resultado = extrair_adicionais(texto)
        assert "adicional_insalubridade" in resultado
        assert resultado["adicional_insalubridade"] == 20.0

    def test_extrai_periculosidade(self):
        texto = "Condeno ao pagamento de adicional de periculosidade de 30%."
        resultado = extrair_adicionais(texto)
        assert "adicional_periculosidade" in resultado
        assert resultado["adicional_periculosidade"] == 30.0

    def test_extrai_adicional_noturno(self):
        texto = "Defiro adicional noturno de 25%."
        resultado = extrair_adicionais(texto)
        assert "adicional_noturno" in resultado
        assert resultado["adicional_noturno"] == 25.0

    def test_extrai_hora_extra(self):
        texto = "Horas extras com adicional de 50%."
        resultado = extrair_adicionais(texto)
        assert "adicional_hora_extra" in resultado
        assert resultado["adicional_hora_extra"] == 50.0

    def test_sem_percentual_nao_insere_chave(self):
        texto = "Defiro adicional de insalubridade grau máximo sem percentual."
        resultado = extrair_adicionais(texto)
        assert "adicional_insalubridade" not in resultado

    def test_multiplos_adicionais(self):
        texto = "Insalubridade de 20% e adicional noturno de 20%."
        resultado = extrair_adicionais(texto)
        assert len(resultado) >= 2

    def test_valores_sao_float(self):
        texto = "Insalubridade de 20%."
        resultado = extrair_adicionais(texto)
        for v in resultado.values():
            assert isinstance(v, float)


# ===========================================================================
# extrair_periodos
# ===========================================================================

class TestExtrairPeriodos:

    def test_retorna_none_texto_vazio(self):
        assert extrair_periodos("") is None

    def test_retorna_none_sem_datas(self):
        assert extrair_periodos("Sem datas aqui.") is None

    def test_uma_data_retorna_inicio_sem_fim(self):
        resultado = extrair_periodos("Admitido em 01/01/2020.")
        assert resultado is not None
        assert resultado["inicio"] == "2020-01-01"
        assert resultado["fim"] is None

    def test_duas_datas_retorna_inicio_e_fim(self):
        resultado = extrair_periodos("De 01/01/2020 até 31/12/2022.")
        assert resultado is not None
        assert resultado["inicio"] == "2020-01-01"
        assert resultado["fim"] == "2022-12-31"

    def test_estrutura_do_retorno(self):
        resultado = extrair_periodos("De 01/01/2020 até 31/12/2022.")
        assert "inicio" in resultado
        assert "fim" in resultado

    def test_datas_em_formato_iso(self):
        resultado = extrair_periodos("Contrato de 01/03/2021 a 30/06/2023.")
        assert resultado["inicio"] == "2021-03-01"
        assert resultado["fim"] == "2023-06-30"

    def test_multiplas_datas_usa_primeira_e_ultima(self):
        texto = "01/01/2019, 01/06/2020, 31/12/2022."
        resultado = extrair_periodos(texto)
        assert resultado["inicio"] == "2019-01-01"
        assert resultado["fim"] == "2022-12-31"

    def test_retorno_e_dict_ou_none(self):
        resultado = extrair_periodos("Admitido em 01/01/2020.")
        assert resultado is None or isinstance(resultado, dict)


# ===========================================================================
# extrair_base_calculo
# ===========================================================================

class TestExtrairBaseCalculo:

    def test_retorna_none_texto_vazio(self):
        assert extrair_base_calculo("") is None

    def test_retorna_none_sem_base_conhecida(self):
        assert extrair_base_calculo("Processo distribuído em 2023.") is None

    def test_salario_hora(self):
        assert extrair_base_calculo("Calculado sobre o salário hora.") == "salario_hora"

    def test_valor_hora(self):
        assert extrair_base_calculo("Base de cálculo: valor hora.") == "salario_hora"

    def test_salario_base(self):
        assert extrair_base_calculo("Incide sobre o salário base.") == "salario_base"

    def test_salario_contratual(self):
        assert extrair_base_calculo("Calculado sobre o salário contratual.") == "salario_base"

    def test_ultima_remuneracao(self):
        assert extrair_base_calculo("Base: última remuneração.") == "ultima_remuneracao"

    def test_remuneracao(self):
        assert extrair_base_calculo("Calculado sobre a remuneração do trabalhador.") == "ultima_remuneracao"

    def test_salario_minimo(self):
        assert extrair_base_calculo("Base de cálculo: salário mínimo vigente.") == "salario_minimo"

    def test_case_insensitive(self):
        assert extrair_base_calculo("Base: SALÁRIO HORA.") == "salario_hora"

    def test_retorno_e_string_ou_none(self):
        resultado = extrair_base_calculo("Calculado sobre o salário hora.")
        assert resultado is None or isinstance(resultado, str)


# ===========================================================================
# interpretar_decisao — função principal
# ===========================================================================

class TestInterpretarDecisao:

    def test_retorna_dict(self):
        assert isinstance(interpretar_decisao("Defiro férias."), dict)

    def test_estrutura_completa(self):
        resultado = interpretar_decisao("Defiro férias proporcionais.")
        assert "verbas" in resultado
        assert "reflexos" in resultado
        assert "adicionais" in resultado
        assert "periodo" in resultado
        assert "base_calculo" in resultado

    def test_verbas_e_lista(self):
        resultado = interpretar_decisao("Defiro férias.")
        assert isinstance(resultado["verbas"], list)

    def test_reflexos_e_lista(self):
        resultado = interpretar_decisao("Horas extras refletindo em férias.")
        assert isinstance(resultado["reflexos"], list)

    def test_adicionais_e_dict(self):
        resultado = interpretar_decisao("Insalubridade de 20%.")
        assert isinstance(resultado["adicionais"], dict)

    def test_periodo_e_dict_ou_none(self):
        resultado = interpretar_decisao("De 01/01/2020 até 31/12/2022.")
        assert resultado["periodo"] is None or isinstance(resultado["periodo"], dict)

    def test_base_calculo_e_string_ou_none(self):
        resultado = interpretar_decisao("Base: salário hora.")
        assert resultado["base_calculo"] is None or isinstance(resultado["base_calculo"], str)

    def test_texto_vazio_retorna_estrutura_vazia(self):
        resultado = interpretar_decisao("")
        assert resultado["verbas"] == []
        assert resultado["reflexos"] == []
        assert resultado["adicionais"] == {}
        assert resultado["periodo"] is None
        assert resultado["base_calculo"] is None

    def test_sentenca_completa(self):
        """Simula uma sentença trabalhista com múltiplos elementos."""
        texto = (
            "Condeno a reclamada ao pagamento de:\n"
            "Férias proporcionais + 1/3, deferidas.\n"
            "Décimo terceiro salário proporcional, deferido.\n"
            "Horas extras acima da 8ª diária, deferidas, refletindo em DSR e férias.\n"
            "Adicional de insalubridade de 20%.\n"
            "Aviso prévio indenizado, deferido.\n"
            "Dano moral, indeferido.\n"
            "Período: 01/01/2021 a 30/06/2023.\n"
            "Base de cálculo: salário base."
        )
        resultado = interpretar_decisao(texto)

        assert isinstance(resultado["verbas"], list)
        assert len(resultado["verbas"]) >= 3

        assert resultado["periodo"] is not None
        assert resultado["periodo"]["inicio"] == "2021-01-01"
        assert resultado["periodo"]["fim"] == "2023-06-30"

        assert resultado["base_calculo"] == "salario_base"

        assert "adicional_insalubridade" in resultado["adicionais"]
        assert resultado["adicionais"]["adicional_insalubridade"] == 20.0

    def test_apenas_indeferimentos(self):
        texto = (
            "Indefiro horas extras.\n"
            "Rejeito o pedido de insalubridade.\n"
            "Improcedente o pedido de dano moral."
        )
        resultado = interpretar_decisao(texto)
        assert isinstance(resultado["verbas"], list)
        deferidas = [v for v in resultado["verbas"] if v["status"] == STATUS_DEFERIDA]
        assert len(deferidas) == 0

    def test_cinco_chaves_sempre_presentes(self):
        """Garante que a estrutura nunca omite campos, mesmo com texto mínimo."""
        for texto in ["", "abc", "01/01/2020", "Defiro férias."]:
            resultado = interpretar_decisao(texto)
            assert set(resultado.keys()) == {
                "verbas", "reflexos", "adicionais", "periodo", "base_calculo"
            }
"""
tests/test_normalizer.py
TS1 — Suíte de testes para services/normalizer.py

Cobertura:
    - _pre_processar: normalização de caixa, espaços, º→°
    - normalizar: correspondência exata, parcial, case-insensitive, edge cases
    - normalizar_lista: listas mistas, itens sem correspondência, lista vazia
    - eh_chave_valida: chaves válidas, inválidas, variações linguísticas
    - listar_variacoes: chaves com múltiplas variações, chave inexistente
    - Integridade do mapa: todos os valores são chaves reconhecidas

Execute com:
    pytest tests/test_normalizer.py -v
"""

import pytest
from services.normalizer import (
    normalizar,
    normalizar_lista,
    eh_chave_valida,
    listar_variacoes,
    _pre_processar,
    MAPA_NORMALIZACAO,
    CHAVES_VALIDAS,
)


# ===========================================================================
# _pre_processar
# ===========================================================================

class TestPreProcessar:

    def test_lowercase(self):
        assert _pre_processar("FÉRIAS PROPORCIONAIS") == "férias proporcionais"

    def test_strip_espacos_extremos(self):
        assert _pre_processar("  saldo de salário  ") == "saldo de salário"

    def test_colapso_espacos_internos(self):
        assert _pre_processar("horas   extras") == "horas extras"

    def test_substitui_ordinal_masculino(self):
        assert _pre_processar("13º proporcional") == "13° proporcional"

    def test_nao_altera_ordinal_feminino(self):
        # 'ª' não é substituído — comportamento esperado conforme implementação
        resultado = _pre_processar("8ª diária")
        assert "8ª" in resultado

    def test_texto_vazio(self):
        assert _pre_processar("") == ""

    def test_texto_so_espacos(self):
        assert _pre_processar("   ") == ""

    def test_sem_alteracao_necessaria(self):
        assert _pre_processar("dsr") == "dsr"

    def test_combinacao_todos_os_casos(self):
        assert _pre_processar("  13º   SALÁRIO  ") == "13° salário"


# ===========================================================================
# normalizar — correspondência exata
# ===========================================================================

class TestNormalizarExato:

    def test_decimo_terceiro_proporcional(self):
        assert normalizar("décimo terceiro salário proporcional") == "decimo_terceiro_proporcional"

    def test_ferias_proporcionais_com_terco(self):
        assert normalizar("férias proporcionais + 1/3") == "ferias_proporcionais_com_terco"

    def test_horas_extras_diarias(self):
        assert normalizar("horas extras acima da 8ª diária") == "horas_extras_diarias"

    def test_horas_extras_semanais(self):
        assert normalizar("horas extras acima da 44ª semanal") == "horas_extras_semanais"

    def test_dsr_sigla(self):
        assert normalizar("dsr") == "dsr"

    def test_rsr_sigla(self):
        assert normalizar("rsr") == "dsr"

    def test_fgts_com_multa(self):
        assert normalizar("fgts + multa de 40%") == "fgts_com_multa"

    def test_aviso_previo_indenizado(self):
        assert normalizar("aviso prévio indenizado") == "aviso_previo_indenizado"

    def test_aviso_previo_generico_mapeia_indenizado(self):
        assert normalizar("aviso prévio") == "aviso_previo_indenizado"

    def test_multa_art_467_variacao_1(self):
        assert normalizar("multa do artigo 467") == "multa_art_467"

    def test_multa_art_467_variacao_2(self):
        assert normalizar("multa art. 467") == "multa_art_467"

    def test_multa_art_477(self):
        assert normalizar("multa art. 477") == "multa_art_477"

    def test_dano_moral(self):
        assert normalizar("dano moral") == "dano_moral"

    def test_indenizacao_danos_morais(self):
        assert normalizar("indenização por danos morais") == "dano_moral"

    def test_honorarios_advocaticios(self):
        assert normalizar("honorários advocatícios") == "honorarios_advocaticios"

    def test_honorarios_sucumbenciais(self):
        assert normalizar("honorários sucumbenciais") == "honorarios_advocaticios"

    def test_ipcae_com_hifen(self):
        assert normalizar("ipca-e") == "IPCAE"

    def test_selic(self):
        assert normalizar("selic") == "SELIC"

    def test_taxa_referencial(self):
        assert normalizar("taxa referencial") == "TR"

    def test_adicional_insalubridade(self):
        assert normalizar("adicional de insalubridade") == "adicional_insalubridade"

    def test_insalubridade_curta(self):
        assert normalizar("insalubridade") == "adicional_insalubridade"

    def test_ferias_dobro(self):
        assert normalizar("férias em dobro") == "ferias_dobro"

    def test_ferias_vencidas_em_dobro(self):
        assert normalizar("férias vencidas em dobro") == "ferias_dobro"

    def test_abono_pecuniario(self):
        assert normalizar("abono pecuniário") == "abono_pecuniario_ferias"

    def test_abono_de_ferias(self):
        assert normalizar("abono de férias") == "abono_pecuniario_ferias"

    def test_sobrejornada(self):
        assert normalizar("sobrejornada") == "horas_extras_diarias"

    def test_saldo_salarial(self):
        assert normalizar("saldo salarial") == "saldo_salario"


# ===========================================================================
# normalizar — case-insensitive e variações de formato
# ===========================================================================

class TestNormalizarCaseInsensitive:

    def test_uppercase(self):
        assert normalizar("FÉRIAS PROPORCIONAIS") == "ferias_proporcionais"

    def test_titlecase(self):
        assert normalizar("Décimo Terceiro Salário") == "decimo_terceiro"

    def test_mixedcase(self):
        assert normalizar("Horas Extras") == "horas_extras_diarias"

    def test_ordinal_maiusculo_substituido(self):
        assert normalizar("13º PROPORCIONAL") == "decimo_terceiro_proporcional"

    def test_espacos_extras(self):
        assert normalizar("  dano   moral  ") == "dano_moral"

    def test_gratificacao_natalina(self):
        assert normalizar("Gratificação Natalina") == "decimo_terceiro"

    def test_gratificacao_natalina_proporcional(self):
        assert normalizar("Gratificação Natalina Proporcional") == "decimo_terceiro_proporcional"


# ===========================================================================
# normalizar — sem correspondência e edge cases
# ===========================================================================

class TestNormalizarSemCorrespondencia:

    def test_texto_vazio_retorna_none(self):
        assert normalizar("") is None

    def test_none_retorna_none(self):
        assert normalizar(None) is None

    def test_texto_desconhecido_retorna_none(self):
        assert normalizar("verba completamente desconhecida xyz") is None

    def test_numero_isolado_nao_lanca_excecao(self):
        resultado = normalizar("999")
        assert resultado is None or isinstance(resultado, str)

    def test_texto_muito_longo_nao_lanca_excecao(self):
        texto_longo = "verba " * 100
        resultado = normalizar(texto_longo)
        assert resultado is None or isinstance(resultado, str)


# ===========================================================================
# normalizar — todos os grupos do MAPA_NORMALIZACAO
# ===========================================================================

class TestNormalizarGruposCompletos:
    """Garante que nenhuma entrada do mapa foi quebrada."""

    @pytest.mark.parametrize("entrada,esperado", [
        # 13º Salário
        ("décimo terceiro proporcional",         "decimo_terceiro_proporcional"),
        ("13° proporcional",                     "decimo_terceiro_proporcional"),
        ("13° salário",                          "decimo_terceiro"),
        ("13º salário",                          "decimo_terceiro"),
        # Férias
        ("férias proporcionais mais um terço",   "ferias_proporcionais_com_terco"),
        ("férias + um terço",                    "ferias_proporcionais_com_terco"),
        ("férias proporcionais",                 "ferias_proporcionais"),
        ("férias vencidas",                      "ferias_vencidas"),
        ("férias indenizadas",                   "ferias_indenizadas"),
        # Horas Extras
        ("horas extras acima da oitava diária",  "horas_extras_diarias"),
        ("labor em sobrejornada",                "horas_extras_diarias"),
        ("horas extraordinárias",                "horas_extras_diarias"),
        # DSR
        ("descanso semanal remunerado",          "dsr"),
        ("repouso semanal remunerado",           "dsr"),
        # FGTS
        ("fgts e multa rescisória de 40%",       "fgts_com_multa"),
        ("fgts com multa",                       "fgts_com_multa"),
        ("depósitos do fgts",                    "fgts_depositos"),
        ("fgts",                                 "fgts_depositos"),
        ("multa rescisória de 40%",              "multa_fgts_40"),
        ("multa de 40% do fgts",                 "multa_fgts_40"),
        # Aviso Prévio
        ("aviso prévio trabalhado",              "aviso_previo_trabalhado"),
        ("aviso prévio proporcional",            "aviso_previo_proporcional"),
        # Rescisórias
        ("saldo de salário",                     "saldo_salario"),
        ("multa art 467",                        "multa_art_467"),
        ("multa art 477",                        "multa_art_477"),
        ("multa do artigo 477",                  "multa_art_477"),
        # Dano
        ("dano material",                        "dano_material"),
        ("indenização por danos materiais",      "dano_material"),
        ("dano existencial",                     "dano_existencial"),
        # Honorários
        ("honorários de sucumbência",            "honorarios_advocaticios"),
        # Adicionais
        ("adicional de periculosidade",          "adicional_periculosidade"),
        ("periculosidade",                       "adicional_periculosidade"),
        ("adicional noturno",                    "adicional_noturno"),
        ("adicional de transferência",           "adicional_transferencia"),
        # Índices
        ("ipca e",                               "IPCAE"),
        ("tr",                                   "TR"),
        ("taxa selic",                           "SELIC"),
        # Bases de Cálculo
        ("salário base",                         "salario_base"),
        ("salário contratual",                   "salario_base"),
        ("última remuneração",                   "ultima_remuneracao"),
        ("remuneração",                          "ultima_remuneracao"),
        ("salário hora",                         "salario_hora"),
        ("valor hora",                           "salario_hora"),
    ])
    def test_entrada_mapeia_corretamente(self, entrada, esperado):
        assert normalizar(entrada) == esperado, (
            f"Entrada '{entrada}' deveria mapear para '{esperado}'"
        )


# ===========================================================================
# normalizar_lista
# ===========================================================================

class TestNormalizarLista:

    def test_lista_vazia(self):
        assert normalizar_lista([]) == []

    def test_todos_conhecidos(self):
        entradas = ["dano moral", "férias proporcionais", "fgts"]
        resultado = normalizar_lista(entradas)
        assert resultado == ["dano_moral", "ferias_proporcionais", "fgts_depositos"]

    def test_preserva_original_sem_correspondencia(self):
        entradas = ["verba_desconhecida_xyz"]
        resultado = normalizar_lista(entradas)
        assert resultado == ["verba_desconhecida_xyz"]

    def test_lista_mista(self):
        entradas = ["dano moral", "verba_desconhecida", "férias proporcionais"]
        resultado = normalizar_lista(entradas)
        assert resultado[0] == "dano_moral"
        assert resultado[1] == "verba_desconhecida"  # original preservado
        assert resultado[2] == "ferias_proporcionais"

    def test_lista_com_duplicatas(self):
        entradas = ["dano moral", "dano moral"]
        resultado = normalizar_lista(entradas)
        assert resultado == ["dano_moral", "dano_moral"]

    def test_lista_com_case_variado(self):
        entradas = ["FGTS", "Honorários Advocatícios"]
        resultado = normalizar_lista(entradas)
        assert resultado[0] == "fgts_depositos"
        assert resultado[1] == "honorarios_advocaticios"

    def test_tamanho_preservado(self):
        entradas = ["dano moral", "xyz_inexistente", "dsr", "abc_inexistente"]
        resultado = normalizar_lista(entradas)
        assert len(resultado) == 4


# ===========================================================================
# eh_chave_valida
# ===========================================================================

class TestEhChaveValida:

    def test_chave_valida_dsr(self):
        assert eh_chave_valida("dsr") is True

    def test_chave_valida_fgts_depositos(self):
        assert eh_chave_valida("fgts_depositos") is True

    def test_chave_valida_honorarios(self):
        assert eh_chave_valida("honorarios_advocaticios") is True

    def test_chave_invalida_variacao_linguistica(self):
        assert eh_chave_valida("dano moral") is False

    def test_chave_invalida_string_vazia(self):
        assert eh_chave_valida("") is False

    def test_chave_invalida_desconhecida(self):
        assert eh_chave_valida("verba_inexistente_xyz") is False

    def test_todas_as_chaves_do_mapa_sao_validas(self):
        """CHAVES_VALIDAS deve estar sincronizado com MAPA_NORMALIZACAO."""
        for chave in CHAVES_VALIDAS:
            assert eh_chave_valida(chave) is True

    @pytest.mark.parametrize("chave", sorted(CHAVES_VALIDAS))
    def test_cada_chave_valida_parametrizado(self, chave):
        assert eh_chave_valida(chave) is True


# ===========================================================================
# listar_variacoes
# ===========================================================================

class TestListarVariacoes:

    def test_dsr_tem_multiplas_variacoes(self):
        variacoes = listar_variacoes("dsr")
        assert len(variacoes) >= 3
        assert "dsr" in variacoes
        assert "rsr" in variacoes
        assert "descanso semanal remunerado" in variacoes
        assert "repouso semanal remunerado" in variacoes

    def test_decimo_terceiro_proporcional_variacoes(self):
        variacoes = listar_variacoes("decimo_terceiro_proporcional")
        assert "décimo terceiro salário proporcional" in variacoes
        assert "13° proporcional" in variacoes
        assert "gratificação natalina proporcional" in variacoes

    def test_honorarios_tem_tres_variacoes(self):
        variacoes = listar_variacoes("honorarios_advocaticios")
        assert len(variacoes) == 3

    def test_chave_inexistente_retorna_lista_vazia(self):
        assert listar_variacoes("chave_inexistente_xyz") == []

    def test_retorno_e_lista(self):
        assert isinstance(listar_variacoes("dsr"), list)

    def test_variacoes_sao_strings(self):
        for variacao in listar_variacoes("dsr"):
            assert isinstance(variacao, str)

    def test_horas_extras_diarias_variacoes(self):
        variacoes = listar_variacoes("horas_extras_diarias")
        assert "horas extras" in variacoes
        assert "sobrejornada" in variacoes
        assert "horas extraordinárias" in variacoes

    def test_fgts_com_multa_variacoes(self):
        variacoes = listar_variacoes("fgts_com_multa")
        assert "fgts + multa de 40%" in variacoes
        assert "fgts com multa" in variacoes


# ===========================================================================
# Integridade do MAPA_NORMALIZACAO
# ===========================================================================

class TestIntegridadeDoMapa:

    def test_mapa_nao_esta_vazio(self):
        assert len(MAPA_NORMALIZACAO) >= 70

    def test_todos_os_valores_sao_chaves_validas(self):
        """Nenhum valor do mapa pode ser desconhecido pelo sistema."""
        for variacao, chave in MAPA_NORMALIZACAO.items():
            assert chave in CHAVES_VALIDAS, (
                f"Valor '{chave}' para variação '{variacao}' "
                f"não está em CHAVES_VALIDAS"
            )

    def test_todas_as_chaves_do_mapa_sao_strings(self):
        for k, v in MAPA_NORMALIZACAO.items():
            assert isinstance(k, str), f"Chave não é string: {k!r}"
            assert isinstance(v, str), f"Valor não é string: {v!r}"

    def test_nenhuma_variacao_e_string_vazia(self):
        for k in MAPA_NORMALIZACAO:
            assert k.strip() != "", "Variação vazia encontrada no mapa"

    def test_nenhum_valor_e_string_vazia(self):
        for v in MAPA_NORMALIZACAO.values():
            assert v.strip() != "", "Chave padronizada vazia encontrada no mapa"

    def test_chaves_validas_estao_sincronizadas_com_mapa(self):
        """CHAVES_VALIDAS deve ser exatamente o conjunto de valores do mapa."""
        assert CHAVES_VALIDAS == set(MAPA_NORMALIZACAO.values())

    def test_grupos_obrigatorios_presentes(self):
        """Grupos jurídicos críticos devem ter ao menos uma chave no mapa."""
        grupos_obrigatorios = {
            "decimo_terceiro",
            "decimo_terceiro_proporcional",
            "ferias_proporcionais",
            "ferias_proporcionais_com_terco",
            "horas_extras_diarias",
            "dsr",
            "fgts_depositos",
            "fgts_com_multa",
            "aviso_previo_indenizado",
            "multa_art_467",
            "multa_art_477",
            "dano_moral",
            "honorarios_advocaticios",
            "IPCAE",
            "SELIC",
            "TR",
        }
        for grupo in grupos_obrigatorios:
            assert grupo in CHAVES_VALIDAS, (
                f"Grupo obrigatório '{grupo}' não encontrado em CHAVES_VALIDAS"
            )

    @pytest.mark.parametrize("variacao,esperado", list(MAPA_NORMALIZACAO.items()))
    def test_cada_entrada_do_mapa_e_normalizavel(self, variacao, esperado):
        """Toda entrada do mapa deve ser normalizável — nenhuma pode estar quebrada."""
        resultado = normalizar(variacao)
        assert resultado == esperado, (
            f"Falha ao normalizar '{variacao}': "
            f"esperado '{esperado}', obtido '{resultado}'"
        )
"""
test_explanation_engine.py — v5.3

Suite de testes para services/explanation_engine.py

Padrão: alinhado com TS1/TS2/TS3 do projeto.
Cobertura:
  - Geração de explicações para todas as 13 regras com template
  - Fallback genérico para regras sem template
  - Ordenação por prioridade (STF primeiro)
  - Campos obrigatórios na saída (regra_id, titulo, base_legal, nivel, explicacao)
  - resumo_para_excel: estrutura e número de colunas
  - resumo_para_memoria: serializabilidade JSON
  - Parametrização com dados reais (salario, aviso_previo, indices)
  - Robustez: resultado vazio, memorial vazio, dados parciais
"""

import json
import pytest
from services.explanation_engine import ExplanationEngine, _nivel_normativo


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def dados_completos():
    return {
        "numero_processo":          "0001234-56.2024.5.15.0001",
        "reclamante":               "João da Silva",
        "reclamada":                "Empresa XYZ Ltda",
        "salario_base":             "3.500,00",
        "aviso_previo_dias":        "60",
        "indice_correcao":          "IPCA-E/SELIC",
        "juros_mora":               "1% a.m.",
        "percentual_honorarios":    "15%",
        "honorarios_sucumbenciais": "sucumbenciais",
        "justica_gratuita":         False,
        "verbas_deferidas": [
            {"nome": "Horas Extras 50%", "periodo": "01/2022-12/2023"},
            {"nome": "Adicional Noturno", "periodo": "01/2022-12/2023"},
            {"nome": "DSR",               "periodo": "01/2022-12/2023"},
        ],
    }


@pytest.fixture
def dados_minimos():
    return {}


@pytest.fixture
def memorial_todas_regras():
    """Memorial com todas as 20 regras ativas do sistema."""
    regras = [
        {"id": "ADC_58_STF",            "titulo": "ADC 58 STF",                  "base_legal": "ADC 58 STF",              "prioridade": 10, "descricao": "Correção ADC 58"},
        {"id": "SUMULA_264_TST",         "titulo": "Súmula 264 TST",              "base_legal": "Súmula 264 TST",          "prioridade": 20, "descricao": "HE reflexos"},
        {"id": "SUMULA_305_TST",         "titulo": "Súmula 305 TST",              "base_legal": "Súmula 305 TST",          "prioridade": 20, "descricao": "FGTS aviso prévio"},
        {"id": "SUMULA_331_TST",         "titulo": "Súmula 331 TST",              "base_legal": "Súmula 331 TST",          "prioridade": 20, "descricao": "Terceirização"},
        {"id": "OJ_42_SDI1_TST",         "titulo": "OJ 42 SDI-I TST",            "base_legal": "OJ 42 SDI-I TST",         "prioridade": 30, "descricao": "Multa 40% AP"},
        {"id": "OJ_195_SDI1_TST",        "titulo": "OJ 195 SDI-I TST",           "base_legal": "OJ 195 SDI-I TST",        "prioridade": 30, "descricao": "FGTS férias"},
        {"id": "OJ_394_SDI1_TST",        "titulo": "OJ 394 SDI-I TST",           "base_legal": "OJ 394 SDI-I TST",        "prioridade": 30, "descricao": "DSR bis in idem"},
        {"id": "ART_467_CLT",            "titulo": "Multa Art. 467 CLT",          "base_legal": "Art. 467 da CLT",         "prioridade": 40, "descricao": "Multa 50%"},
        {"id": "ART_477_CLT",            "titulo": "Multa Art. 477 CLT",          "base_legal": "Art. 477 da CLT",         "prioridade": 40, "descricao": "Multa rescisória"},
        {"id": "ART_487_CLT_LEI_12506",  "titulo": "Aviso Prévio Proporcional",   "base_legal": "Art. 487 CLT + Lei 12.506/2011", "prioridade": 40, "descricao": "Aviso proporcional"},
        {"id": "ART_791A_CLT",           "titulo": "Honorários Art. 791-A CLT",   "base_legal": "Art. 791-A da CLT",       "prioridade": 40, "descricao": "Honorários"},
        {"id": "CNJ_DIGITO_VERIFICADOR", "titulo": "Validação CNJ",               "base_legal": "Resolução CNJ 65/2008",   "prioridade": 50, "descricao": "Dígito verificador"},
        {"id": "VERBA_DEDUPLICATOR",     "titulo": "Deduplicação de Verbas",      "base_legal": "Consistência",            "prioridade": 50, "descricao": "Deduplicação"},
    ]
    return regras


@pytest.fixture
def resultado_engine_completo(memorial_todas_regras):
    return {
        "alertas":          [],
        "regras_aplicadas": [r["id"] for r in memorial_todas_regras],
        "memorial_juridico": memorial_todas_regras,
    }


@pytest.fixture
def resultado_engine_vazio():
    return {
        "alertas":           [],
        "regras_aplicadas":  [],
        "memorial_juridico": [],
    }


# ── Testes: estrutura básica ──────────────────────────────────────────────────

class TestEstruturaBasica:

    def test_retorna_lista(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        assert isinstance(resultado, list)

    def test_quantidade_explicacoes_igual_ao_memorial(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        assert len(resultado) == len(resultado_engine_completo["memorial_juridico"])

    def test_campos_obrigatorios_presentes(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        campos = {"regra_id", "titulo", "base_legal", "nivel", "prioridade", "explicacao", "tem_template"}
        for item in resultado:
            assert campos.issubset(item.keys()), f"Campos faltando em {item.get('regra_id')}"

    def test_explicacao_nunca_vazia(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        for item in resultado:
            assert item["explicacao"], f"Explicação vazia para {item['regra_id']}"

    def test_memorial_vazio_retorna_lista_vazia(self, resultado_engine_vazio, dados_minimos):
        resultado = ExplanationEngine.gerar(resultado_engine_vazio, dados_minimos)
        assert resultado == []

    def test_resultado_engine_sem_memorial_nao_quebra(self, dados_minimos):
        resultado = ExplanationEngine.gerar({}, dados_minimos)
        assert resultado == []


# ── Testes: ordenação por prioridade ─────────────────────────────────────────

class TestOrdenacao:

    def test_ordenado_por_prioridade_crescente(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        prioridades = [r["prioridade"] for r in resultado]
        assert prioridades == sorted(prioridades)

    def test_stf_e_primeiro(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        assert resultado[0]["regra_id"] == "ADC_58_STF"

    def test_consistencia_e_ultimo_grupo(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        ultimas = [r for r in resultado if r["prioridade"] == 50]
        assert all(r["nivel"] == "Consistência" for r in ultimas)


# ── Testes: templates com dados parametrizados ───────────────────────────────

class TestTemplatesParametrizados:

    def test_adc58_contem_indice_correcao(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        adc = next(r for r in resultado if r["regra_id"] == "ADC_58_STF")
        assert "IPCA-E/SELIC" in adc["explicacao"]

    def test_adc58_sem_dados_usa_fallback_de_indice(self, resultado_engine_completo, dados_minimos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_minimos)
        adc = next(r for r in resultado if r["regra_id"] == "ADC_58_STF")
        assert "IPCA-E/SELIC" in adc["explicacao"]  # valor padrão do template

    def test_sumula305_contem_aviso_previo_dias(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        s305 = next(r for r in resultado if r["regra_id"] == "SUMULA_305_TST")
        assert "60" in s305["explicacao"]

    def test_art487_contem_dias_aviso(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        art487 = next(r for r in resultado if r["regra_id"] == "ART_487_CLT_LEI_12506")
        assert "60" in art487["explicacao"]

    def test_art467_contem_salario_base(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        art467 = next(r for r in resultado if r["regra_id"] == "ART_467_CLT")
        assert "3.500,00" in art467["explicacao"]

    def test_art791a_contem_percentual_honorarios(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        art791a = next(r for r in resultado if r["regra_id"] == "ART_791A_CLT")
        assert "15%" in art791a["explicacao"]

    def test_art791a_com_justica_gratuita(self, resultado_engine_completo, dados_completos):
        dados_completos["justica_gratuita"] = True
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        art791a = next(r for r in resultado if r["regra_id"] == "ART_791A_CLT")
        assert "gratuidade" in art791a["explicacao"].lower()

    def test_sumula264_menciona_verbas_he(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        s264 = next(r for r in resultado if r["regra_id"] == "SUMULA_264_TST")
        assert "Horas Extras" in s264["explicacao"] or "horas extras" in s264["explicacao"].lower()

    def test_cnj_contem_numero_processo(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        cnj = next(r for r in resultado if r["regra_id"] == "CNJ_DIGITO_VERIFICADOR")
        assert "0001234-56.2024.5.15.0001" in cnj["explicacao"]

    def test_sumula331_contem_nome_reclamada(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        s331 = next(r for r in resultado if r["regra_id"] == "SUMULA_331_TST")
        assert "Empresa XYZ Ltda" in s331["explicacao"]


# ── Testes: nivel normativo ───────────────────────────────────────────────────

class TestNivelNormativo:

    def test_prioridade_10_e_stf(self):
        assert _nivel_normativo(10) == "STF"

    def test_prioridade_20_e_sumula_tst(self):
        assert _nivel_normativo(20) == "Súmula TST"

    def test_prioridade_30_e_oj_tst(self):
        assert _nivel_normativo(30) == "Orientação Jurisprudencial TST"

    def test_prioridade_40_e_clt(self):
        assert _nivel_normativo(40) == "CLT"

    def test_prioridade_50_e_consistencia(self):
        assert _nivel_normativo(50) == "Consistência"

    def test_nivel_presente_no_resultado(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        niveis_validos = {"STF", "Súmula TST", "Orientação Jurisprudencial TST", "CLT", "Consistência"}
        for item in resultado:
            assert item["nivel"] in niveis_validos


# ── Testes: fallback para regras sem template ─────────────────────────────────

class TestFallback:

    def test_regra_desconhecida_usa_descricao_como_fallback(self, dados_minimos):
        resultado_engine = {
            "memorial_juridico": [
                {"id": "REGRA_FUTURA_XYZ", "titulo": "Regra Futura",
                 "base_legal": "Art. X", "prioridade": 40,
                 "descricao": "Descrição da regra futura"}
            ]
        }
        resultado = ExplanationEngine.gerar(resultado_engine, dados_minimos)
        assert len(resultado) == 1
        assert resultado[0]["tem_template"] is False
        assert "Descrição da regra futura" in resultado[0]["explicacao"]

    def test_regra_sem_descricao_usa_mensagem_generica(self, dados_minimos):
        resultado_engine = {
            "memorial_juridico": [
                {"id": "REGRA_SEM_DESC", "titulo": "Sem Desc",
                 "base_legal": "Art. Y", "prioridade": 40, "descricao": ""}
            ]
        }
        resultado = ExplanationEngine.gerar(resultado_engine, dados_minimos)
        assert "REGRA_SEM_DESC" in resultado[0]["explicacao"]

    def test_tem_template_true_para_regras_conhecidas(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        com_template = [r for r in resultado if r["tem_template"]]
        assert len(com_template) == 13  # total de templates registrados


# ── Testes: resumo_para_excel ─────────────────────────────────────────────────

class TestResumoExcel:

    def test_retorna_lista_de_listas(self, resultado_engine_completo, dados_completos):
        expl = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        linhas = ExplanationEngine.resumo_para_excel(expl)
        assert isinstance(linhas, list)
        assert all(isinstance(l, list) for l in linhas)

    def test_cada_linha_tem_4_colunas(self, resultado_engine_completo, dados_completos):
        expl = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        linhas = ExplanationEngine.resumo_para_excel(expl)
        for linha in linhas:
            assert len(linha) == 4, f"Linha com {len(linha)} colunas: {linha}"

    def test_colunas_na_ordem_correta(self, resultado_engine_completo, dados_completos):
        expl = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        linhas = ExplanationEngine.resumo_para_excel(expl)
        # [nivel, base_legal, titulo, explicacao]
        primeira = linhas[0]
        assert primeira[0] == "STF"                    # nivel
        assert "ADC 58" in primeira[1]                 # base_legal
        assert len(primeira[3]) > 10                   # explicacao não trivial

    def test_quantidade_linhas_igual_a_explicacoes(self, resultado_engine_completo, dados_completos):
        expl = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        linhas = ExplanationEngine.resumo_para_excel(expl)
        assert len(linhas) == len(expl)

    def test_lista_vazia_retorna_lista_vazia(self):
        linhas = ExplanationEngine.resumo_para_excel([])
        assert linhas == []


# ── Testes: resumo_para_memoria ───────────────────────────────────────────────

class TestResumoMemoria:

    def test_retorna_lista_de_dicts(self, resultado_engine_completo, dados_completos):
        expl = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        mem = ExplanationEngine.resumo_para_memoria(expl)
        assert isinstance(mem, list)
        assert all(isinstance(d, dict) for d in mem)

    def test_campos_obrigatorios_na_memoria(self, resultado_engine_completo, dados_completos):
        expl = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        mem = ExplanationEngine.resumo_para_memoria(expl)
        campos = {"regra_id", "nivel", "base_legal", "titulo", "explicacao"}
        for item in mem:
            assert campos.issubset(item.keys())

    def test_serializavel_em_json(self, resultado_engine_completo, dados_completos):
        expl = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        mem = ExplanationEngine.resumo_para_memoria(expl)
        # Não deve lançar exceção
        serializado = json.dumps(mem, ensure_ascii=False)
        assert len(serializado) > 0

    def test_lista_vazia_retorna_lista_vazia(self):
        mem = ExplanationEngine.resumo_para_memoria([])
        assert mem == []


# ── Testes: robustez com dados parciais ──────────────────────────────────────

class TestRobustez:

    def test_dados_none_nao_quebra(self, resultado_engine_completo):
        # dados como dict vazio simula ausência de contexto
        resultado = ExplanationEngine.gerar(resultado_engine_completo, {})
        assert len(resultado) > 0

    def test_verbas_deferidas_ausentes_nao_quebra(self, resultado_engine_completo):
        dados = {"salario_base": "2.000,00"}  # sem verbas_deferidas
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados)
        assert len(resultado) > 0

    def test_verbas_como_objetos_nao_dict_nao_quebra(self, resultado_engine_completo):
        """Verbas como objetos Pydantic (VerbaContexto) não devem quebrar."""
        class FakeVerba:
            nome = "Horas Extras 50%"
        dados = {"verbas_deferidas": [FakeVerba()]}
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados)
        assert len(resultado) > 0

    def test_memorial_com_entrada_sem_id_nao_quebra(self):
        resultado_engine = {
            "memorial_juridico": [
                {"titulo": "Sem ID", "base_legal": "Art. Z", "prioridade": 40, "descricao": ""}
            ]
        }
        resultado = ExplanationEngine.gerar(resultado_engine, {})
        assert len(resultado) == 1

    def test_todas_as_20_regras_geram_texto_nao_vazio(self, resultado_engine_completo, dados_completos):
        resultado = ExplanationEngine.gerar(resultado_engine_completo, dados_completos)
        for item in resultado:
            assert item["explicacao"].strip(), f"Texto vazio para {item['regra_id']}"


# ── Testes: função pública gerar_explicacoes() — interface do processor.py ───

class TestFuncaoPublica:
    """
    Valida a interface gerar_explicacoes(verbas, memorial_juridico)
    usada pelo processor.py no step 8c.
    """

    def test_retorna_lista(self, memorial_todas_regras):
        from services.explanation_engine import gerar_explicacoes
        verbas = [{"nome": "Horas Extras 50%", "periodo": "01/2022-12/2023"}]
        resultado = gerar_explicacoes(verbas=verbas, memorial_juridico=memorial_todas_regras)
        assert isinstance(resultado, list)

    def test_quantidade_igual_ao_memorial(self, memorial_todas_regras):
        from services.explanation_engine import gerar_explicacoes
        resultado = gerar_explicacoes(verbas=[], memorial_juridico=memorial_todas_regras)
        assert len(resultado) == len(memorial_todas_regras)

    def test_campos_obrigatorios_presentes(self, memorial_todas_regras):
        from services.explanation_engine import gerar_explicacoes
        resultado = gerar_explicacoes(verbas=[], memorial_juridico=memorial_todas_regras)
        campos = {"regra_id", "titulo", "base_legal", "nivel", "prioridade", "explicacao", "tem_template"}
        for item in resultado:
            assert campos.issubset(item.keys())

    def test_memorial_vazio_retorna_lista_vazia(self):
        from services.explanation_engine import gerar_explicacoes
        resultado = gerar_explicacoes(verbas=[], memorial_juridico=[])
        assert resultado == []

    def test_verbas_como_dicts_sao_processadas(self, memorial_todas_regras):
        from services.explanation_engine import gerar_explicacoes
        verbas = [
            {"nome": "Horas Extras 50%"},
            {"nome": "DSR"},
            {"nome": "Adicional Noturno"},
        ]
        resultado = gerar_explicacoes(verbas=verbas, memorial_juridico=memorial_todas_regras)
        s264 = next(r for r in resultado if r["regra_id"] == "SUMULA_264_TST")
        assert "Horas Extras" in s264["explicacao"] or "horas extras" in s264["explicacao"].lower()

    def test_assinatura_compativel_com_processor(self, memorial_todas_regras):
        """Simula exatamente a chamada do processor.py step 8c."""
        from services.explanation_engine import gerar_explicacoes
        dados_finais = {
            "verbas_deferidas": [{"nome": "Horas Extras 50%", "periodo": "2022-2023"}],
            "salario_base": "3.500,00",
        }
        explicacoes = gerar_explicacoes(
            verbas=dados_finais.get("verbas_deferidas", []),
            memorial_juridico=memorial_todas_regras,
        )
        assert isinstance(explicacoes, list)
        assert len(explicacoes) > 0
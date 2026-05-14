"""
tests/unit/test_processor_helpers.py

Testes das funções puras de workers/processor.py:
  - _clean_str / _clean_bool / _dedup_alertas
  - _validate_result  (inclui pós-processamento determinístico)
  - _qualidade_ok

Não testa o pipeline completo (requer PDF + API Gemini).
O mock de google.genai.Client é necessário pois ai_client.py
instancia o cliente no nível do módulo.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import patch, MagicMock
import pytest

# ── Mock de genai antes de qualquer import que chegue a ai_client.py ────────
with patch("google.genai.Client", MagicMock()):
    from workers.processor import (
        _clean_str,
        _clean_bool,
        _dedup_alertas,
        _validate_result,
        _qualidade_ok,
        SUSPICIOUS,
        _MIN_VERBAS,
    )


# =============================================================================
# _clean_str
# =============================================================================

class TestCleanStr:

    def test_none_retorna_none(self):
        assert _clean_str(None) is None

    def test_string_vazia_retorna_none(self):
        assert _clean_str("") is None

    def test_string_so_espacos_retorna_none(self):
        assert _clean_str("   ") is None

    @pytest.mark.parametrize("suspeito", list(SUSPICIOUS))
    def test_valores_suspeitos_retornam_none(self, suspeito):
        assert _clean_str(suspeito) is None

    def test_suspeito_case_insensitive(self):
        assert _clean_str("NULL") is None
        assert _clean_str("N/A") is None
        assert _clean_str("Não Informado") is None

    def test_texto_normal_preservado(self):
        assert _clean_str("João da Silva") == "João da Silva"

    def test_texto_com_espacos_stripped(self):
        assert _clean_str("  texto com espaços  ") == "texto com espaços"

    def test_inteiro_convertido_para_string(self):
        assert _clean_str(42) == "42"

    def test_float_convertido_para_string(self):
        assert _clean_str(3.5) == "3.5"

    def test_zero_nao_e_none(self):
        # 0 não está em SUSPICIOUS; deve virar "0"
        assert _clean_str(0) == "0"

    def test_data_preservada(self):
        assert _clean_str("15/01/2020") == "15/01/2020"

    def test_valor_monetario_preservado(self):
        assert _clean_str("R$ 3.500,00") == "R$ 3.500,00"


# =============================================================================
# _clean_bool
# =============================================================================

class TestCleanBool:

    def test_true_preservado(self):
        assert _clean_bool(True, default=False) is True

    def test_false_preservado(self):
        assert _clean_bool(False, default=True) is False

    @pytest.mark.parametrize("valor", ["true", "sim", "yes", "1"])
    def test_strings_verdadeiras(self, valor):
        assert _clean_bool(valor, default=False) is True

    @pytest.mark.parametrize("valor", ["false", "não", "nao", "no", "0"])
    def test_strings_falsas(self, valor):
        assert _clean_bool(valor, default=True) is False

    def test_none_retorna_default_false(self):
        assert _clean_bool(None, default=False) is False

    def test_none_retorna_default_true(self):
        assert _clean_bool(None, default=True) is True

    def test_string_desconhecida_retorna_default(self):
        assert _clean_bool("talvez", default=False) is False
        assert _clean_bool("talvez", default=True) is True

    def test_inteiro_1_nao_e_bool(self):
        # int 1 não é bool True — deve cair no default
        assert _clean_bool(1, default=False) is False

    def test_case_insensitive(self):
        assert _clean_bool("TRUE", default=False) is True
        assert _clean_bool("FALSE", default=True) is False
        assert _clean_bool("SIM", default=False) is True


# =============================================================================
# _dedup_alertas
# =============================================================================

class TestDedupAlertas:

    def test_listas_vazias(self):
        assert _dedup_alertas([], []) == []

    def test_nenhuma_lista(self):
        assert _dedup_alertas() == []

    def test_lista_none_ignorada(self):
        assert _dedup_alertas(None, ["A"]) == ["A"]

    def test_lista_unica_sem_dupes(self):
        assert _dedup_alertas(["A", "B", "C"]) == ["A", "B", "C"]

    def test_dedup_entre_listas(self):
        resultado = _dedup_alertas(["A", "B"], ["B", "C"])
        assert resultado == ["A", "B", "C"]

    def test_dedup_dentro_da_mesma_lista(self):
        resultado = _dedup_alertas(["A", "A", "B"])
        assert resultado == ["A", "B"]

    def test_ordem_de_primeira_aparicao_preservada(self):
        resultado = _dedup_alertas(["C", "A"], ["A", "B", "C"])
        assert resultado == ["C", "A", "B"]

    def test_tres_listas(self):
        resultado = _dedup_alertas(["X"], ["X", "Y"], ["Y", "Z"])
        assert resultado == ["X", "Y", "Z"]


# =============================================================================
# _validate_result — estrutura básica
# =============================================================================

class TestValidateResultEstrutura:

    def test_dict_vazio_nao_crasha(self):
        result = _validate_result({})
        assert isinstance(result, dict)

    def test_verbas_nao_lista_vira_lista_vazia(self):
        result = _validate_result({"verbas_deferidas": "não é lista"})
        assert result["verbas_deferidas"] == []

    def test_verbas_none_vira_lista_vazia(self):
        result = _validate_result({"verbas_deferidas": None})
        assert result["verbas_deferidas"] == []

    def test_verbas_com_nao_dict_ignorados(self):
        result = _validate_result({"verbas_deferidas": ["string", 42, None]})
        assert result["verbas_deferidas"] == []

    def test_campos_texto_suspeitos_viram_none(self):
        data = {campo: "não informado" for campo in ["reclamante", "reclamada", "vara_trabalho"]}
        result = _validate_result(data)
        assert result["reclamante"] is None
        assert result["reclamada"] is None
        assert result["vara_trabalho"] is None

    def test_campos_texto_validos_preservados(self):
        result = _validate_result({
            "reclamante": "João da Silva",
            "reclamada": "Empresa XYZ Ltda",
        })
        assert result["reclamante"] == "João da Silva"
        assert result["reclamada"] == "Empresa XYZ Ltda"

    def test_justica_gratuita_false_por_padrao(self):
        result = _validate_result({})
        assert result["justica_gratuita"] is False

    def test_justica_gratuita_string_true_normalizada(self):
        result = _validate_result({"justica_gratuita": "true"})
        assert result["justica_gratuita"] is True

    def test_justica_gratuita_bool_preservado(self):
        result = _validate_result({"justica_gratuita": True})
        assert result["justica_gratuita"] is True


# =============================================================================
# _validate_result — verbas
# =============================================================================

class TestValidateResultVerbas:

    def _verba(self, **kwargs):
        base = {"nome": "Horas Extras", "status_final": "deferida", "reflexos": []}
        base.update(kwargs)
        return base

    def test_nome_null_vira_verba_nao_identificada(self):
        result = _validate_result({"verbas_deferidas": [{"nome": None}]})
        assert result["verbas_deferidas"][0]["nome"] == "Verba não identificada"

    def test_nome_suspeito_vira_verba_nao_identificada(self):
        result = _validate_result({"verbas_deferidas": [{"nome": "null"}]})
        assert result["verbas_deferidas"][0]["nome"] == "Verba não identificada"

    def test_status_final_null_vira_deferida(self):
        result = _validate_result({"verbas_deferidas": [self._verba(status_final=None)]})
        assert result["verbas_deferidas"][0]["status_final"] == "deferida"

    def test_status_final_nao_informado_vira_deferida(self):
        # "não informado" está em SUSPICIOUS → _clean_str → None → default "deferida"
        result = _validate_result({"verbas_deferidas": [self._verba(status_final="não informado")]})
        assert result["verbas_deferidas"][0]["status_final"] == "deferida"

    def test_status_final_valido_preservado(self):
        result = _validate_result({"verbas_deferidas": [self._verba(status_final="reformada")]})
        assert result["verbas_deferidas"][0]["status_final"] == "reformada"

    def test_integracao_salarial_bool_true(self):
        result = _validate_result({"verbas_deferidas": [self._verba(integracao_salarial=True)]})
        assert result["verbas_deferidas"][0]["integracao_salarial"] is True

    def test_integracao_salarial_bool_false(self):
        result = _validate_result({"verbas_deferidas": [self._verba(integracao_salarial=False)]})
        assert result["verbas_deferidas"][0]["integracao_salarial"] is False

    def test_integracao_salarial_string_sim(self):
        result = _validate_result({"verbas_deferidas": [self._verba(integracao_salarial="sim")]})
        assert result["verbas_deferidas"][0]["integracao_salarial"] is True

    def test_integracao_salarial_none_preservado(self):
        result = _validate_result({"verbas_deferidas": [self._verba(integracao_salarial=None)]})
        assert result["verbas_deferidas"][0]["integracao_salarial"] is None

    def test_reflexos_lista_strings_limpas(self):
        result = _validate_result({"verbas_deferidas": [self._verba(reflexos=["DSR", "13º Salário", ""])]})
        assert result["verbas_deferidas"][0]["reflexos"] == ["DSR", "13º Salário"]

    def test_reflexos_nao_lista_vira_lista_vazia(self):
        result = _validate_result({"verbas_deferidas": [self._verba(reflexos="DSR")]})
        assert result["verbas_deferidas"][0]["reflexos"] == []

    def test_reflexos_null_vira_lista_vazia(self):
        result = _validate_result({"verbas_deferidas": [self._verba(reflexos=None)]})
        assert result["verbas_deferidas"][0]["reflexos"] == []

    def test_quantidade_diaria_fracao_12_movida_para_periodo(self):
        # "11/12" é fração de avos — deve ir para periodo, não quantidade_diaria
        result = _validate_result({"verbas_deferidas": [self._verba(quantidade_diaria="11/12", periodo=None)]})
        v = result["verbas_deferidas"][0]
        assert v["quantidade_diaria"] is None
        assert v["periodo"] == "11/12"

    def test_quantidade_diaria_normal_preservada(self):
        result = _validate_result({"verbas_deferidas": [self._verba(quantidade_diaria="2h extras")]})
        assert result["verbas_deferidas"][0]["quantidade_diaria"] == "2h extras"

    def test_multiplas_verbas_processadas(self):
        verbas = [
            {"nome": "Horas Extras", "reflexos": ["DSR"], "status_final": "deferida"},
            {"nome": "FGTS", "reflexos": [], "status_final": "deferida"},
        ]
        result = _validate_result({"verbas_deferidas": verbas})
        assert len(result["verbas_deferidas"]) == 2


# =============================================================================
# _validate_result — pós-processamento determinístico
# =============================================================================

class TestValidateResultPosProcessamento:

    def test_jornada_derivada_de_horario(self):
        """08h às 17h com 1 hora de intervalo → 8h diárias / 48h semanais."""
        result = _validate_result({
            "horario_trabalho": "08h às 17h com 1 hora",
            "jornada_contratual": None,
        })
        assert result.get("jornada_contratual") == "8h diárias / 48h semanais"

    def test_jornada_nao_sobrescreve_existente(self):
        """Se a IA já extraiu jornada_contratual, não deve ser sobrescrita."""
        result = _validate_result({
            "horario_trabalho": "07h às 17h com 1h",
            "jornada_contratual": "44h semanais",
        })
        assert result["jornada_contratual"] == "44h semanais"

    def test_fgts_periodo_completo_completado(self):
        """Texto genérico (sem '/') + datas → completa com datas reais."""
        result = _validate_result({
            "fgts_periodo_completo": "Todo o contrato",
            "data_admissao": "15/01/2020",
            "data_demissao": "30/06/2023",
        })
        assert result["fgts_periodo_completo"] == "Todo o período contratual — 15/01/2020 a 30/06/2023"

    def test_fgts_com_barra_nao_completado(self):
        """Texto com '/' já contém datas — não deve ser alterado."""
        original = "Todo o período contratual — 15/01/2020 a 30/06/2023"
        result = _validate_result({
            "fgts_periodo_completo": original,
            "data_admissao": "15/01/2020",
            "data_demissao": "30/06/2023",
        })
        assert result["fgts_periodo_completo"] == original

    def test_fgts_sem_datas_nao_modificado(self):
        """Sem datas contratuais, não completa."""
        result = _validate_result({"fgts_periodo_completo": "Todo o contrato"})
        assert result["fgts_periodo_completo"] == "Todo o contrato"

    def test_prescricao_quinquenal_calculada(self):
        """Ajuizamento 01/06/2025 → prescrição 01/06/2020."""
        result = _validate_result({"data_ajuizamento": "01/06/2025"})
        assert result.get("prescricao_quinquenal") == "01/06/2020"

    def test_prescricao_preservada_se_ja_presente(self):
        # prescricao_quinquenal agora está em CAMPOS_TEXTO — valor existente é preservado.
        result = _validate_result({
            "data_ajuizamento": "01/06/2025",
            "prescricao_quinquenal": "01/01/2019",
        })
        assert result["prescricao_quinquenal"] == "01/01/2019"

    def test_divisor_horas_detectado_no_jornada(self):
        result = _validate_result({"jornada_contratual": "44h semanais"})
        assert result.get("divisor_horas") == "220"

    def test_divisor_horas_detectado_em_texto_numerico(self):
        result = _validate_result({"horario_trabalho": "observado o divisor 180"})
        assert result.get("divisor_horas") == "180"

    def test_divisor_horas_preservado_se_ja_presente(self):
        # divisor_horas agora está em CAMPOS_TEXTO — valor existente não é sobrescrito.
        result = _validate_result({
            "horario_trabalho": "divisor 180",
            "divisor_horas": "220",
        })
        assert result["divisor_horas"] == "220"

    def test_evolucao_salarial_preenchida_com_salario(self):
        result = _validate_result({"salario_base": "R$ 3.500,00"})
        assert result.get("evolucao_salarial") == "Salário fixo reconhecido: R$ 3.500,00"

    def test_evolucao_salarial_sem_salario_permanece_none(self):
        result = _validate_result({})
        assert result.get("evolucao_salarial") is None

    def test_evolucao_salarial_preservada_se_ja_presente(self):
        # evolucao_salarial agora está em CAMPOS_TEXTO — valor existente não é sobrescrito.
        result = _validate_result({
            "salario_base": "R$ 3.500,00",
            "evolucao_salarial": "Admissão: R$ 2.000,00 | Demissão: R$ 3.500,00",
        })
        assert result["evolucao_salarial"] == "Admissão: R$ 2.000,00 | Demissão: R$ 3.500,00"

    # ── data_saida_ctps (FASE P) ──────────────────────────────────────────────

    def test_data_saida_ctps_calculada(self):
        """30/06/2023 + 30 dias = 30/07/2023 (OJ 82 TST)."""
        result = _validate_result({
            "data_demissao": "30/06/2023",
            "aviso_previo_dias": "30 dias",
        })
        assert result.get("data_saida_ctps") == "30/07/2023"

    def test_data_saida_ctps_aviso_composto(self):
        """'42 dias — 30 + 12 pela Lei 12.506/2011': usa o primeiro número (42)."""
        result = _validate_result({
            "data_demissao": "15/01/2023",
            "aviso_previo_dias": "42 dias — 30 + 12 pela Lei 12.506/2011",
        })
        assert result.get("data_saida_ctps") == "26/02/2023"

    def test_data_saida_ctps_nao_sobrescreve_existente(self):
        """Se a IA já extraiu data_saida_ctps, não deve ser recalculada."""
        result = _validate_result({
            "data_demissao": "30/06/2023",
            "aviso_previo_dias": "30 dias",
            "data_saida_ctps": "01/08/2023",
        })
        assert result["data_saida_ctps"] == "01/08/2023"

    def test_data_saida_ctps_sem_aviso_nao_calcula(self):
        result = _validate_result({"data_demissao": "30/06/2023"})
        assert result.get("data_saida_ctps") is None

    def test_data_saida_ctps_sem_demissao_nao_calcula(self):
        result = _validate_result({"aviso_previo_dias": "30 dias"})
        assert result.get("data_saida_ctps") is None


# =============================================================================
# _qualidade_ok
# =============================================================================

class TestQualidadeOk:

    def _dados_completos(self):
        return {
            "numero_processo": "0001234-58.2023.5.04.0001",
            "reclamante": "João da Silva",
            "reclamada": "Empresa XYZ",
            "data_sentenca": "10/03/2024",
            "salario_base": "R$ 3.500,00",
            "verbas_deferidas": [
                {"nome": "Horas Extras"},
                {"nome": "FGTS + 40%"},
                {"nome": "Aviso Prévio"},
            ],
        }

    def test_dados_completos_retorna_true(self):
        ok, motivo = _qualidade_ok(self._dados_completos())
        assert ok is True
        assert motivo == "ok"

    def test_campo_obrigatorio_ausente_retorna_false(self):
        dados = self._dados_completos()
        del dados["reclamante"]
        ok, motivo = _qualidade_ok(dados)
        assert ok is False
        assert "reclamante" in motivo

    def test_multiplos_campos_ausentes_listados(self):
        dados = self._dados_completos()
        del dados["reclamante"]
        del dados["salario_base"]
        ok, motivo = _qualidade_ok(dados)
        assert ok is False
        assert "reclamante" in motivo
        assert "salario_base" in motivo

    def test_verbas_abaixo_do_minimo_retorna_false(self):
        dados = self._dados_completos()
        dados["verbas_deferidas"] = dados["verbas_deferidas"][:_MIN_VERBAS - 1]
        ok, motivo = _qualidade_ok(dados)
        assert ok is False
        assert "verbas" in motivo.lower() or str(_MIN_VERBAS) in motivo

    def test_verbas_none_retorna_false(self):
        dados = self._dados_completos()
        dados["verbas_deferidas"] = None
        ok, motivo = _qualidade_ok(dados)
        assert ok is False

    def test_verbas_exatamente_no_minimo_retorna_true(self):
        dados = self._dados_completos()
        dados["verbas_deferidas"] = [{"nome": f"Verba {i}"} for i in range(_MIN_VERBAS)]
        ok, _ = _qualidade_ok(dados)
        assert ok is True

    def test_campo_com_valor_suspeito_conta_como_ausente(self):
        # _qualidade_ok usa dados.get(c) → None/""/"null" são falsy
        dados = self._dados_completos()
        dados["reclamante"] = ""
        ok, motivo = _qualidade_ok(dados)
        assert ok is False


# =============================================================================
# Helpers FASE 5 — _check_cache, _load_playbook, _apply_ai_result,
#                   _run_legal_analysis, _build_parecer, _persist_result
# =============================================================================

with patch("google.genai.Client", MagicMock()):
    from workers.processor import (
        _check_cache,
        _load_playbook,
        _apply_ai_result,
        _run_legal_analysis,
        _build_parecer,
        _persist_result,
        _PLAYBOOK_MAP,
    )


def _dados_qualidade_ok():
    return {
        "numero_processo": "0001234-58.2023.5.04.0001",
        "reclamante": "João da Silva",
        "reclamada": "Empresa Ltda",
        "data_sentenca": "01/01/2024",
        "salario_base": "R$ 2.000,00",
        "verbas_deferidas": [{"nome": f"Verba {i}"} for i in range(3)],
    }


# =============================================================================
# _check_cache
# =============================================================================

class TestCheckCache:
    def test_cache_miss_retorna_none(self):
        with patch("workers.processor.get_cache", return_value=None):
            assert _check_cache("abc123") is None

    def test_cache_hit_qualidade_ok_retorna_dados(self):
        dados = _dados_qualidade_ok()
        with patch("workers.processor.get_cache", return_value=dados):
            resultado = _check_cache("abc123")
        assert resultado is dados

    def test_cache_hit_qualidade_insuficiente_retorna_none(self):
        dados = {"numero_processo": "0001234-58.2023.5.04.0001"}  # faltam campos obrigatórios
        with patch("workers.processor.get_cache", return_value=dados):
            resultado = _check_cache("abc123")
        assert resultado is None

    def test_cache_hit_sem_verbas_retorna_none(self):
        dados = _dados_qualidade_ok()
        dados["verbas_deferidas"] = []  # nenhuma verba → qualidade insuficiente
        with patch("workers.processor.get_cache", return_value=dados):
            resultado = _check_cache("abc123")
        assert resultado is None


# =============================================================================
# _load_playbook
# =============================================================================

class TestLoadPlaybook:
    def _mock_load_skill(self, content="PLAYBOOK"):
        return patch("workers.processor._load_skill", return_value=content)

    def _mock_find_section(self, pos=10):
        return patch("workers.processor.find_section_hybrid", return_value=pos)

    def test_tipo_conhecido_carrega_playbook_correto(self):
        chamadas = []
        def fake_load(fname):
            chamadas.append(fname)
            return "CONTEUDO"
        with patch("workers.processor._load_skill", side_effect=fake_load):
            with patch("workers.processor.find_section_hybrid", return_value=10):
                _load_playbook("acordao", "texto qualquer")
        assert chamadas[0] == "acordao.md"

    def test_tipo_desconhecido_usa_sentenca_ordinaria(self):
        chamadas = []
        def fake_load(fname):
            chamadas.append(fname)
            return "CONTEUDO"
        with patch("workers.processor._load_skill", side_effect=fake_load):
            with patch("workers.processor.find_section_hybrid", return_value=10):
                _load_playbook("tipo_inexistente", "texto")
        assert chamadas[0] == "sentenca_ordinaria.md"

    def test_todos_os_tipos_conhecidos_mapeados(self):
        for doc_type in _PLAYBOOK_MAP:
            chamadas = []
            def fake_load(fname, _dt=doc_type):
                chamadas.append(fname)
                return "CONTEUDO"
            with patch("workers.processor._load_skill", side_effect=fake_load):
                with patch("workers.processor.find_section_hybrid", return_value=10):
                    _load_playbook(doc_type, "texto")
            assert chamadas[0] == _PLAYBOOK_MAP[doc_type], f"Falhou para {doc_type}"

    def test_dispositivo_nao_encontrado_adiciona_filtro(self):
        chamadas = []
        def fake_load(fname):
            chamadas.append(fname)
            return "CONTEUDO"
        with patch("workers.processor._load_skill", side_effect=fake_load):
            with patch("workers.processor.find_section_hybrid", return_value=-1):
                resultado = _load_playbook("sentenca", "texto sem dispositivo")
        assert "filtro_dispositivo.md" in chamadas
        assert "CONTEUDO" in resultado  # ambos os conteúdos concatenados

    def test_dispositivo_encontrado_nao_adiciona_filtro(self):
        chamadas = []
        def fake_load(fname):
            chamadas.append(fname)
            return "CONTEUDO"
        with patch("workers.processor._load_skill", side_effect=fake_load):
            with patch("workers.processor.find_section_hybrid", return_value=50):
                _load_playbook("sentenca", "texto com DISPOSITIVO aqui")
        assert "filtro_dispositivo.md" not in chamadas


# =============================================================================
# _apply_ai_result
# =============================================================================

class TestApplyAiResult:
    def _verba(self, nome="Hora extra"):
        return {"nome": nome, "status_final": "deferida", "reflexos": [], "integracao_salarial": None}

    def test_campos_high_sobrescrevem_ai(self):
        ai_data = {"numero_processo": "ERRADO", "verbas_deferidas": [self._verba()]}
        pre_fields = {"high": {"numero_processo": "0001234-58.2023.5.04.0001"}, "medium": {}}
        with patch("workers.processor.deduplicar_verbas", return_value=([self._verba()], [])):
            dados, _ = _apply_ai_result(ai_data, pre_fields)
        assert dados["numero_processo"] == "0001234-58.2023.5.04.0001"

    def test_campos_medium_nao_sobrescrevem_ai(self):
        ai_data = {"salario_base": "R$ 3.000,00", "verbas_deferidas": [self._verba()]}
        pre_fields = {"high": {}, "medium": {"salario_base": "R$ 1.000,00"}}
        with patch("workers.processor.deduplicar_verbas", return_value=([self._verba()], [])):
            dados, _ = _apply_ai_result(ai_data, pre_fields)
        assert dados["salario_base"] == "R$ 3.000,00"

    def test_dedup_retorna_avisos(self):
        verba = self._verba()
        ai_data = {"verbas_deferidas": [verba, verba]}
        pre_fields = {"high": {}, "medium": {}}
        with patch("workers.processor.deduplicar_verbas", return_value=([verba], ["duplicata removida"])):
            dados, avisos = _apply_ai_result(ai_data, pre_fields)
        assert len(avisos) == 1
        assert "duplicata" in avisos[0]

    def test_verbas_vazias_nao_chamam_dedup(self):
        ai_data = {"verbas_deferidas": []}
        pre_fields = {"high": {}, "medium": {}}
        with patch("workers.processor.deduplicar_verbas") as mock_dedup:
            dados, avisos = _apply_ai_result(ai_data, pre_fields)
        mock_dedup.assert_not_called()
        assert avisos == []

    def test_pre_fields_vazio_nao_quebra(self):
        ai_data = {"reclamante": "João", "verbas_deferidas": [self._verba()]}
        pre_fields = {}
        with patch("workers.processor.deduplicar_verbas", return_value=([self._verba()], [])):
            dados, avisos = _apply_ai_result(ai_data, pre_fields)
        assert dados["reclamante"] == "João"


# =============================================================================
# _run_legal_analysis
# =============================================================================

class TestRunLegalAnalysis:
    def _dados(self):
        return {
            "verbas_deferidas": [{"nome": "Hora extra", "status_final": "deferida", "reflexos": []}],
            "salario_base": "R$ 2.000,00",
        }

    def test_retorna_5_elementos(self):
        with patch("workers.processor.validar_dados", return_value=["alerta1"]):
            with patch("workers.processor._RULE_ENGINE") as mock_engine:
                mock_engine.executar.return_value = {
                    "alertas": ["alerta2"],
                    "regras_aplicadas": ["R1"],
                    "memorial_juridico": ["M1"],
                }
                with patch("workers.processor.carregar_regras_ativas", return_value=[]):
                    with patch("workers.processor.gerar_explicacoes", return_value=["E1"]):
                        resultado = _run_legal_analysis(self._dados())
        assert len(resultado) == 5
        alertas_v, alertas_e, regras, memorial, explicacoes = resultado
        assert "alerta1" in alertas_v
        assert "alerta2" in alertas_e
        assert "R1" in regras
        assert "M1" in memorial
        assert "E1" in explicacoes

    def test_erro_regras_dinamicas_nao_propaga(self):
        with patch("workers.processor.validar_dados", return_value=[]):
            with patch("workers.processor._RULE_ENGINE") as mock_engine:
                mock_engine.executar.return_value = {
                    "alertas": [], "regras_aplicadas": [], "memorial_juridico": [],
                }
                with patch("workers.processor.carregar_regras_ativas", side_effect=RuntimeError("falha")):
                    with patch("workers.processor.gerar_explicacoes", return_value=[]):
                        resultado = _run_legal_analysis(self._dados())
        assert len(resultado) == 5  # não lançou exceção

    def test_regras_dinamicas_concatenadas(self):
        with patch("workers.processor.validar_dados", return_value=[]):
            with patch("workers.processor._RULE_ENGINE") as mock_engine:
                mock_engine.executar.return_value = {
                    "alertas": ["a1"], "regras_aplicadas": ["R1"], "memorial_juridico": [],
                }
                mock_dyn_engine = MagicMock()
                mock_dyn_engine.executar.return_value = {
                    "alertas": ["a2"], "regras_aplicadas": ["R2"],
                }
                with patch("workers.processor.carregar_regras_ativas", return_value=["regra_fake"]):
                    with patch("workers.processor.LegalRuleEngine", return_value=mock_dyn_engine):
                        with patch("workers.processor.gerar_explicacoes", return_value=[]):
                            _, alertas_e, regras, _, _ = _run_legal_analysis(self._dados())
        assert "a1" in alertas_e and "a2" in alertas_e
        assert "R1" in regras and "R2" in regras


# =============================================================================
# _build_parecer
# =============================================================================

class TestBuildParecer:
    def _dados(self):
        return {"verbas_deferidas": [{"nome": "FGTS", "status_final": "deferida"}]}

    def test_retorna_chaves_esperadas(self):
        with patch("workers.processor.gerar_parecer_parcelas_apuradas",
                   return_value={"intro": "Intro.", "itens": ["item1"]}):
            with patch("workers.processor.obter_textos_padrao_criterios_parecer",
                       return_value={"inss": "Texto INSS", "irrf": "Texto IRRF"}):
                with patch("workers.processor.gerar_parecer_tecnico_completo",
                           return_value={"texto": "Parecer.", "parcelas": "P.", "model_used": "flash"}):
                    resultado = _build_parecer(self._dados())
        assert resultado["parecer_intro_parcelas"] == "Intro."
        assert resultado["parecer_criterios_inss"] == "Texto INSS"
        assert resultado["parecer_criterios_irrf"] == "Texto IRRF"
        assert resultado["parecer_texto"] == "Parecer."
        assert resultado["parecer_model_used"] == "flash"

    def test_excecao_em_parecer_tecnico_retorna_strings_vazias(self):
        with patch("workers.processor.gerar_parecer_parcelas_apuradas",
                   return_value={"intro": "", "itens": []}):
            with patch("workers.processor.obter_textos_padrao_criterios_parecer",
                       return_value={"inss": "", "irrf": ""}):
                with patch("workers.processor.gerar_parecer_tecnico_completo",
                           side_effect=Exception("API error")):
                    resultado = _build_parecer(self._dados())
        assert resultado["parecer_texto"] == ""
        assert resultado["parecer_parcelas_ia"] == ""
        assert resultado["parecer_model_used"] is None

    def test_campo_error_no_parecer_nao_propaga(self):
        with patch("workers.processor.gerar_parecer_parcelas_apuradas",
                   return_value={"intro": "", "itens": []}):
            with patch("workers.processor.obter_textos_padrao_criterios_parecer",
                       return_value={"inss": "", "irrf": ""}):
                with patch("workers.processor.gerar_parecer_tecnico_completo",
                           return_value={"texto": "T", "parcelas": "P", "model_used": None,
                                         "error": "Timeout na API"}):
                    resultado = _build_parecer(self._dados())
        assert resultado["parecer_texto"] == "T"  # resultado ainda é retornado


# =============================================================================
# _persist_result
# =============================================================================

class TestPersistResult:
    def _dados_ok(self):
        return _dados_qualidade_ok()

    def test_qualidade_ok_chama_save_cache(self):
        dados = self._dados_ok()
        with patch("workers.processor.save_cache") as mock_cache:
            with patch("workers.processor.save_extraction", return_value="doc999"):
                with patch("workers.processor.deduct_credit"):
                    _persist_result("user1", "hash1", "sentenca", dados)
        mock_cache.assert_called_once()

    def test_qualidade_ok_chama_deduct_credit(self):
        dados = self._dados_ok()
        with patch("workers.processor.save_cache"):
            with patch("workers.processor.save_extraction", return_value="doc999"):
                with patch("workers.processor.deduct_credit") as mock_deduct:
                    _persist_result("user1", "hash1", "sentenca", dados)
        mock_deduct.assert_called_once_with("user1")

    def test_qualidade_ok_injeta_meta_doc_type(self):
        dados = self._dados_ok()
        with patch("workers.processor.save_cache"):
            with patch("workers.processor.save_extraction", return_value="doc999"):
                with patch("workers.processor.deduct_credit"):
                    _persist_result("user1", "hash1", "acordao", dados)
        assert dados["_meta_doc_type"] == "acordao"

    def test_qualidade_insuficiente_nao_chama_save_cache(self):
        dados = {"numero_processo": "X"}  # faltam campos
        with patch("workers.processor.save_cache") as mock_cache:
            with patch("workers.processor.save_extraction", return_value="doc999"):
                with patch("workers.processor.deduct_credit"):
                    doc_id, ok, motivo = _persist_result("user1", "hash1", "sentenca", dados)
        mock_cache.assert_not_called()
        assert ok is False

    def test_qualidade_insuficiente_nao_chama_deduct_credit(self):
        dados = {"numero_processo": "X"}
        with patch("workers.processor.save_cache"):
            with patch("workers.processor.save_extraction", return_value="doc999"):
                with patch("workers.processor.deduct_credit") as mock_deduct:
                    _persist_result("user1", "hash1", "sentenca", dados)
        mock_deduct.assert_not_called()

    def test_retorna_doc_id_como_string(self):
        dados = self._dados_ok()
        with patch("workers.processor.save_cache"):
            with patch("workers.processor.save_extraction", return_value=42):
                with patch("workers.processor.deduct_credit"):
                    doc_id, _, _ = _persist_result("user1", "hash1", "sentenca", dados)
        assert isinstance(doc_id, str)
        assert doc_id == "42"

    def test_retorna_tupla_tres_elementos(self):
        dados = self._dados_ok()
        with patch("workers.processor.save_cache"):
            with patch("workers.processor.save_extraction", return_value="doc1"):
                with patch("workers.processor.deduct_credit"):
                    resultado = _persist_result("user1", "hash1", "sentenca", dados)
        assert len(resultado) == 3
        doc_id, ok, motivo = resultado
        assert ok is True
        assert motivo == "ok"

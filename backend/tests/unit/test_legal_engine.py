"""
tests/unit/test_legal_engine.py

Testes do motor de regras jurídicas — camada unitária.
Foca em: carregamento de regras, execução sem crash, alertas corretos.

Os testes de regras individuais já existem em tests/jurisprudencia/.
Este arquivo cobre o motor em si (engine.py, rule_registry.py).

Execute com:
    pytest tests/unit/test_legal_engine.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dados_minimos(**extra) -> dict:
    base = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "reclamante": "João da Silva",
        "reclamada": "Empresa Teste Ltda",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
        "data_ajuizamento": "01/02/2025",
        "data_sentenca": "01/06/2025",
        "salario_base": "R$ 3.500,00",
        "motivo_rescisao": "Sem justa causa",
        "indice_correcao": "IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF",
        "juros_mora": "SELIC",
        "justica_gratuita": False,
        "verbas_deferidas": [],
    }
    base.update(extra)
    return base


# ═════════════════════════════════════════════════════════════════════════════
# Carregamento de regras
# ═════════════════════════════════════════════════════════════════════════════

class TestCarregamentoRegras:

    def test_carrega_regras_sem_crash(self):
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        regras = carregar_todas_as_regras()
        assert isinstance(regras, list)
        assert len(regras) > 0

    def test_todas_regras_tem_id(self):
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        regras = carregar_todas_as_regras()
        for regra in regras:
            assert regra.id, f"Regra sem ID: {regra.__class__.__name__}"

    def test_sem_ids_duplicados(self):
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        regras = carregar_todas_as_regras()
        ids = [r.id for r in regras]
        assert len(ids) == len(set(ids)), f"IDs duplicados: {[x for x in ids if ids.count(x) > 1]}"

    def test_regras_estaticas_presentes(self):
        """Verifica que as regras críticas (STF, TST) estão carregadas."""
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        regras = carregar_todas_as_regras()
        ids = {r.id for r in regras}
        criticas = ["ADC_58_STF", "SUMULA_264_TST", "SUMULA_305_TST"]
        for rid in criticas:
            assert rid in ids, f"Regra crítica ausente: {rid}"

    def test_stubs_lab_nao_geram_alertas(self):
        """Regras lab_ com pass não devem gerar alertas reais."""
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        from services.legal_engine.engine import LegalRuleEngine
        regras = carregar_todas_as_regras()
        engine = LegalRuleEngine(regras)
        resultado = engine.executar(_dados_minimos())
        # Não deve haver alertas com ID que comece com "LAB_" (stubs são pass)
        for alerta in resultado.get("alertas", []):
            if isinstance(alerta, dict):
                rid = alerta.get("regra_id", "")
                assert not rid.startswith("LAB_"), f"Stub lab gerou alerta: {rid}"


# ═════════════════════════════════════════════════════════════════════════════
# Execução do engine
# ═════════════════════════════════════════════════════════════════════════════

class TestExecucaoEngine:

    def test_executa_sem_crash_dados_minimos(self):
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        from services.legal_engine.engine import LegalRuleEngine
        regras = carregar_todas_as_regras()
        engine = LegalRuleEngine(regras)
        resultado = engine.executar(_dados_minimos())
        assert "alertas" in resultado
        assert "regras_aplicadas" in resultado
        assert "memorial_juridico" in resultado

    def test_resultado_tem_estrutura_correta(self):
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        from services.legal_engine.engine import LegalRuleEngine
        regras = carregar_todas_as_regras()
        engine = LegalRuleEngine(regras)
        resultado = engine.executar(_dados_minimos())
        assert isinstance(resultado["alertas"], list)
        assert isinstance(resultado["regras_aplicadas"], list)
        assert isinstance(resultado["memorial_juridico"], list)

    def test_adc58_ativa_para_selic(self):
        """IPCA-E + SELIC deve registrar ADC_58_STF no memorial (admissão pós-ADC58)."""
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        from services.legal_engine.engine import LegalRuleEngine
        regras = carregar_todas_as_regras()
        engine = LegalRuleEngine(regras)
        # data_admissao posterior a 18/12/2020 para ADC58 ser aplicável
        dados = _dados_minimos(
            data_admissao="01/01/2021",
            indice_correcao="IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF",
        )
        resultado = engine.executar(dados)
        ids_memorial = [e.get("id") for e in resultado["memorial_juridico"]]
        assert "ADC_58_STF" in ids_memorial

    def test_indice_errado_gera_alerta(self):
        """TR como índice deve gerar alerta de violação da ADC 58 (admissão pós-ADC58)."""
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        from services.legal_engine.engine import LegalRuleEngine
        regras = carregar_todas_as_regras()
        engine = LegalRuleEngine(regras)
        # data_admissao posterior a 18/12/2020 para ADC58 ser aplicável
        dados = _dados_minimos(data_admissao="01/01/2021", indice_correcao="TR")
        resultado = engine.executar(dados)
        # alertas são strings no formato "[AVISO] [REGRA_ID] mensagem"
        alertas_str = resultado["alertas"]
        assert any("ADC" in a for a in alertas_str), "TR como índice deveria gerar alerta ADC_58_STF"

    def test_dados_vazios_nao_crasha(self):
        """Engine deve ser robusto contra dados incompletos."""
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        from services.legal_engine.engine import LegalRuleEngine
        regras = carregar_todas_as_regras()
        engine = LegalRuleEngine(regras)
        resultado = engine.executar({})
        assert "alertas" in resultado

    def test_engine_instanciado_diretamente_executa(self):
        """LegalRuleEngine instanciado com todas as regras deve executar sem crash."""
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        from services.legal_engine.engine import LegalRuleEngine
        engine = LegalRuleEngine(carregar_todas_as_regras())
        resultado = engine.executar(_dados_minimos())
        assert "alertas" in resultado
        assert isinstance(resultado["alertas"], list)


# ═════════════════════════════════════════════════════════════════════════════
# Explanation engine — zero IA
# ═════════════════════════════════════════════════════════════════════════════

class TestExplanationEngine:

    def test_gera_explicacoes_para_memorial(self):
        from services.explanation_engine import gerar_explicacoes
        memorial = [
            {"id": "ADC_58_STF", "titulo": "ADC 58 STF", "base_legal": "ADC 58",
             "prioridade": 10, "descricao": "teste"},
        ]
        explicacoes = gerar_explicacoes(verbas=[], memorial_juridico=memorial)
        assert len(explicacoes) == 1
        assert explicacoes[0]["regra_id"] == "ADC_58_STF"
        assert explicacoes[0]["explicacao"]  # não deve estar vazio

    def test_memorial_vazio_retorna_lista_vazia(self):
        from services.explanation_engine import gerar_explicacoes
        assert gerar_explicacoes(verbas=[], memorial_juridico=[]) == []

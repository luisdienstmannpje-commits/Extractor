"""Shadow KB: hits por execução (ContextoJuridico) e campo ProcessoTrabalhista.shadow_logs."""

from unittest.mock import patch

from models import ProcessoTrabalhista
from services.legal_engine.dynamic_rule_loader import executar_shadow_pipeline
from services.legal_engine.engine import LegalRuleEngine
from services.legal_engine.rule_base import ContextoJuridico
from workers.processor import _coletar_fontes_extracao


def test_processo_model_has_shadow_logs_field():
    assert "shadow_logs" in ProcessoTrabalhista.model_fields
    assert "teses_defesa" in ProcessoTrabalhista.model_fields
    assert "quadro_comparativo" in ProcessoTrabalhista.model_fields
    assert "fontes_extracao" in ProcessoTrabalhista.model_fields


def test_contexto_juridico_shadow_hits_default():
    ctx = ContextoJuridico(justica_gratuita=False)
    assert ctx.shadow_hits == []


def test_processo_trabalhista_shadow_logs_default():
    p = ProcessoTrabalhista(justica_gratuita=False, verbas_deferidas=[])
    assert p.shadow_logs == []


def test_engine_executar_includes_shadow_hits():
    engine = LegalRuleEngine([])
    r = engine.executar({"verbas_deferidas": [], "justica_gratuita": False})
    assert "shadow_hits" in r
    assert r["shadow_hits"] == []


def test_executar_shadow_pipeline_sem_regras():
    with patch(
        "services.legal_engine.dynamic_rule_loader.carregar_regras_shadow",
        return_value=[],
    ):
        assert executar_shadow_pipeline({"verbas_deferidas": []}) == []


def test_coletar_fontes_extracao_mapeia_campos_e_verbas():
    dados = {
        "numero_processo": "0010032-85.2024.5.15.0097",
        "data_ajuizamento": "01/11/2024",
        "verbas_deferidas": [
            {
                "nome": "Horas Extras",
                "observacoes": "Banco de horas inválido.",
                "trecho_fundamentacao": "Condeno ao pagamento de horas extras.",
                "pagina_origem": 3,
            }
        ],
        "teses_defesa": [],
        "quadro_comparativo": [],
        "alertas_juridicos": ["[ERRO] A verba 'Horas Extras' foi informada sem reflexos."],
    }
    texto = "--- PÁGINA 1 ---\nAjuizamento\n--- PÁGINA 3 ---\nCondeno..."
    fontes = _coletar_fontes_extracao(
        dados_finais=dados,
        texto=texto,
        dados_regex={"data_ajuizamento": "01/11/2024"},
    )
    assert isinstance(fontes, list)
    assert any(f.get("campo") == "numero_processo" for f in fontes)
    assert any(
        f.get("campo") == "data_ajuizamento" and f.get("pagina_origem") == 1
        for f in fontes
    )
    assert any(
        f.get("campo") == "verbas_deferidas[0].nome" and f.get("pagina_origem") == 3
        for f in fontes
    )
    assert any(
        f.get("campo") == "alertas_juridicos[0]" and f.get("pagina_origem") == 3
        for f in fontes
    )
    alerta_fonte = next(
        (f for f in fontes if f.get("campo") == "alertas_juridicos[0]"),
        None,
    )
    assert alerta_fonte is not None
    assert isinstance(alerta_fonte.get("confianca"), float)
    assert alerta_fonte.get("confianca", 0.0) >= 0.8

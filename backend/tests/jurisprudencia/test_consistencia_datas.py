import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico
from services.legal_engine.rules.consistencia_datas import ConsistenciaDatasRule


def _ctx(**kwargs):
    base = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
        "data_saida_ctps": "15/01/2025",
        "data_ajuizamento": "01/02/2025",
        "data_sentenca": "01/06/2025",
    }
    base.update(kwargs)
    return ContextoJuridico(**base)


def _erros(alertas, regra_id):
    return [
        a
        for a in alertas
        if isinstance(a, dict)
        and a.get("nivel") == "ERRO"
        and a.get("regra_id") == regra_id
    ]


def _avisos(alertas, regra_id):
    return [
        a
        for a in alertas
        if isinstance(a, dict)
        and a.get("nivel") == "AVISO"
        and a.get("regra_id") == regra_id
    ]


class TestMetadados:
    def test_id_prioridade(self):
        rule = ConsistenciaDatasRule()
        assert rule.id == "CONSISTENCIA_DATAS"
        assert rule.prioridade == 50


class TestConsistenciaDatas:
    def setup_method(self):
        self.rule = ConsistenciaDatasRule()

    def test_datas_consistentes_nao_geram_alertas(self):
        ctx = _ctx()
        ctx = self.rule.aplicar(ctx)
        assert _erros(ctx.alertas, self.rule.id) == []
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_saida_ctps_antes_demissao_gera_erro(self):
        ctx = _ctx(data_saida_ctps="01/01/2025", data_demissao="15/01/2025")
        ctx = self.rule.aplicar(ctx)
        erros = _erros(ctx.alertas, self.rule.id)
        assert len(erros) == 1
        assert "CTPS" in erros[0].get("mensagem", "")

    def test_admissao_posterior_demissao_gera_erro(self):
        ctx = _ctx(data_admissao="01/01/2026", data_demissao="01/01/2025")
        ctx = self.rule.aplicar(ctx)
        erros = _erros(ctx.alertas, self.rule.id)
        assert len(erros) == 1
        assert "Admissão" in erros[0].get("mensagem", "")

    def test_sentenca_antes_demissao_gera_aviso(self):
        ctx = _ctx(data_sentenca="01/01/2024", data_demissao="01/01/2025")
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "Sentença" in avisos[0].get("mensagem", "")

    def test_ajuizamento_posterior_sentenca_gera_erro(self):
        ctx = _ctx(data_ajuizamento="01/07/2025", data_sentenca="01/06/2025")
        ctx = self.rule.aplicar(ctx)
        erros = _erros(ctx.alertas, self.rule.id)
        assert len(erros) == 1
        assert "Ajuizamento" in erros[0].get("mensagem", "")

    def test_ajuizamento_antes_admissao_gera_aviso(self):
        ctx = _ctx(data_admissao="01/03/2020", data_ajuizamento="01/01/2019")
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "Ajuizamento" in avisos[0].get("mensagem", "")

    def test_regra_registrada(self):
        ctx = _ctx()
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas


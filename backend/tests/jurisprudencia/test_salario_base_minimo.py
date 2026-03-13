import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico
from services.legal_engine.rules.salario_base_minimo import SalarioBaseMinimoRule


def _ctx(**kwargs):
    base = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
        "salario_base": "R$ 3.500,00",
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
        rule = SalarioBaseMinimoRule()
        assert rule.id == "CONSISTENCIA_SALARIO_BASE_MINIMO"
        assert rule.prioridade == 50


class TestSalarioBaseMinimo:
    def setup_method(self):
        self.rule = SalarioBaseMinimoRule()

    def test_salario_valido_nao_gera_alerta(self):
        ctx = _ctx(salario_base="R$ 3.500,00")
        ctx = self.rule.aplicar(ctx)
        assert _erros(ctx.alertas, self.rule.id) == []
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_salario_zerado_gera_erro(self):
        ctx = _ctx(salario_base="R$ 0,00")
        ctx = self.rule.aplicar(ctx)
        erros = _erros(ctx.alertas, self.rule.id)
        assert len(erros) == 1
        assert "inválido" in erros[0].get("mensagem", "").lower()

    def test_salario_negativo_gera_erro(self):
        ctx = _ctx(salario_base="R$ -100,00")
        ctx = self.rule.aplicar(ctx)
        erros = _erros(ctx.alertas, self.rule.id)
        assert len(erros) == 1

    def test_salario_abaixo_minimo_gera_aviso(self):
        ctx = _ctx(salario_base="R$ 1.000,00")
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "abaixo do mínimo vigente" in avisos[0].get("mensagem", "")

    def test_sem_salario_nao_gera_alerta(self):
        ctx = _ctx(salario_base="")
        ctx = self.rule.aplicar(ctx)
        assert _erros(ctx.alertas, self.rule.id) == []
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_regra_registrada(self):
        ctx = _ctx()
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas


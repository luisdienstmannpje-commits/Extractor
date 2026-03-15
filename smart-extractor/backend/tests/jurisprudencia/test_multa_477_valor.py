import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.multa_477_valor import Multa477ValorRule


def _ctx(**kwargs):
    base = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
        "salario_base": "R$ 3.500,00",
    }
    base.update(kwargs)
    return ContextoJuridico(**base)


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
        rule = Multa477ValorRule()
        assert rule.id == "CONSISTENCIA_MULTA_477_VALOR"
        assert rule.prioridade == 50


class TestMulta477Valor:
    def setup_method(self):
        self.rule = Multa477ValorRule()

    def test_multa_igual_salario_nao_gera_aviso(self):
        ctx = _ctx(
            salario_base="R$ 3.500,00",
            verbas_deferidas=[
                VerbaContexto(nome="Multa art. 477", valor_fixado="R$ 3.500,00"),
            ],
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_multa_diferente_mais_5_pct_gera_aviso(self):
        ctx = _ctx(
            salario_base="R$ 3.500,00",
            verbas_deferidas=[
                VerbaContexto(nome="Multa art. 477", valor_fixado="R$ 5.000,00"),
            ],
        )
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "difere do salário base" in avisos[0].get("mensagem", "")

    def test_sem_verba_multa_nao_gera_aviso(self):
        ctx = _ctx(
            salario_base="R$ 3.500,00",
            verbas_deferidas=[VerbaContexto(nome="Horas Extras", valor_fixado="R$ 1.000,00")],
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_sem_salario_base_nao_gera_aviso(self):
        ctx = _ctx(
            salario_base="",
            verbas_deferidas=[
                VerbaContexto(nome="Multa art. 477", valor_fixado="R$ 3.500,00"),
            ],
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_regra_registrada(self):
        ctx = _ctx(verbas_deferidas=[])
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.he_reflexo_dsr import HeReflexoDsrRule


def _ctx(verbas):
    return ContextoJuridico(
        numero_processo="0001234-56.2024.5.03.0001",
        data_admissao="01/03/2020",
        data_demissao="15/01/2025",
        verbas_deferidas=verbas,
    )


class TestMetadados:
    def test_id_prioridade_base(self):
        rule = HeReflexoDsrRule()
        assert rule.id == "SUMULA_264_TST"
        assert rule.prioridade == 20
        assert "Súmula 264" in rule.base_legal


class TestHeReflexoDsr:
    def setup_method(self):
        self.rule = HeReflexoDsrRule()

    def test_adiciona_reflexos_obrigatorios(self):
        ctx = _ctx(
            [VerbaContexto(nome="Horas Extras 50%", reflexos=["dsr"])]
        )
        ctx = self.rule.aplicar(ctx)
        reflexos = ctx.verbas_deferidas[0].reflexos
        for esperado in self.rule._REFLEXOS_OBRIGATORIOS:
            assert esperado in reflexos

    def test_ignora_verbas_sem_horas_extras(self):
        ctx = _ctx(
            [VerbaContexto(nome="Férias", reflexos=[])]
        )
        ctx = self.rule.aplicar(ctx)
        assert ctx.verbas_deferidas[0].reflexos == []

    def test_registra_regra_aplicada(self):
        ctx = _ctx(
            [VerbaContexto(nome="Horas Extras 100%", reflexos=[])]
        )
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas


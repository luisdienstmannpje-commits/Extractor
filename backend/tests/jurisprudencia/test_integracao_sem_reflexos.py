import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.integracao_sem_reflexos import (
    IntegracaoSemReflexosRule,
)


def _ctx(verbas):
    return ContextoJuridico(
        numero_processo="0001234-56.2024.5.03.0001",
        data_admissao="01/03/2020",
        data_demissao="15/01/2025",
        verbas_deferidas=verbas,
    )


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
        rule = IntegracaoSemReflexosRule()
        assert rule.id == "CONSISTENCIA_INTEGRACAO_SEM_REFLEXOS"
        assert rule.prioridade == 50


class TestIntegracaoSemReflexos:
    def setup_method(self):
        self.rule = IntegracaoSemReflexosRule()

    def test_verba_integrada_sem_reflexos_gera_aviso(self):
        ctx = _ctx(
            [
                VerbaContexto(
                    nome="Adicional de Periculosidade",
                    integracao_salarial=True,
                    reflexos=[],
                )
            ]
        )
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "integracao_salarial=True" in avisos[0].get("mensagem", "")

    def test_verba_integrada_com_reflexos_nao_gera_aviso(self):
        ctx = _ctx(
            [
                VerbaContexto(
                    nome="Adicional de Insalubridade",
                    integracao_salarial=True,
                    reflexos=["DSR", "13º Salário"],
                )
            ]
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_verba_sem_integracao_nao_gera_aviso(self):
        ctx = _ctx(
            [
                VerbaContexto(
                    nome="Horas Extras",
                    integracao_salarial=False,
                    reflexos=[],
                )
            ]
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_sem_verbas_regra_ainda_registrada(self):
        ctx = _ctx([])
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas


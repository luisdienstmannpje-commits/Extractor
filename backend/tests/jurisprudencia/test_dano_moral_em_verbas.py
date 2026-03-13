import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.dano_moral_em_verbas import (
    DanoMoralEmVerbasRule,
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
        rule = DanoMoralEmVerbasRule()
        assert rule.id == "CONSISTENCIA_DANO_MORAL_EM_VERBAS"
        assert rule.prioridade == 50


class TestDanoMoralEmVerbas:
    def setup_method(self):
        self.rule = DanoMoralEmVerbasRule()

    def test_encontra_dano_moral_em_verbas(self):
        ctx = _ctx(
            [
                VerbaContexto(nome="Horas Extras", reflexos=[]),
                VerbaContexto(nome="Dano Moral", reflexos=[]),
            ]
        )
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "Dano moral encontrado em verbas_deferidas" in avisos[0].get(
            "mensagem", ""
        )

    def test_encontra_danos_morais_variante_texto(self):
        ctx = _ctx(
            [
                VerbaContexto(nome="indenização por danos morais", reflexos=[]),
            ]
        )
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1

    def test_sem_dano_moral_nao_gera_aviso(self):
        ctx = _ctx(
            [
                VerbaContexto(nome="Horas Extras", reflexos=[]),
                VerbaContexto(nome="Férias", reflexos=[]),
            ]
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_sem_verbas_regra_ainda_registrada(self):
        ctx = _ctx([])
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas


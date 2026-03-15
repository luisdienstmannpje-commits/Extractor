import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.verbas_duplicadas import VerbasDuplicadasRule


def _ctx(**kwargs):
    base = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
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
        rule = VerbasDuplicadasRule()
        assert rule.id == "CONSISTENCIA_VERBAS_DUPLICADAS"
        assert rule.prioridade == 50


class TestVerbasDuplicadas:
    def setup_method(self):
        self.rule = VerbasDuplicadasRule()

    def test_duplicata_mesmo_periodo_gera_aviso(self):
        ctx = _ctx(
            verbas_deferidas=[
                VerbaContexto(nome="Horas Extras", periodo="01/2024 a 12/2024"),
                VerbaContexto(nome="Horas Extras", periodo="01/2024 a 12/2024"),
            ]
        )
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "Verba duplicada" in avisos[0].get("mensagem", "")

    def test_mesma_verba_periodos_diferentes_nao_gera_aviso(self):
        ctx = _ctx(
            verbas_deferidas=[
                VerbaContexto(nome="Férias", periodo="2023/2024"),
                VerbaContexto(nome="Férias", periodo="2024/2025"),
            ]
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_verbas_distintas_nao_gera_aviso(self):
        ctx = _ctx(
            verbas_deferidas=[
                VerbaContexto(nome="Horas Extras", periodo="01/2024"),
                VerbaContexto(nome="DSR", periodo="01/2024"),
            ]
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_sem_verbas_nao_gera_aviso(self):
        ctx = _ctx(verbas_deferidas=[])
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_regra_registrada(self):
        ctx = _ctx(verbas_deferidas=[])
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas

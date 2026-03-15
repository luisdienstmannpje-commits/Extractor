import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico
from services.legal_engine.rules.aviso_previo_dias import AvisoPrevioDiasRule


def _ctx(**kwargs):
    base = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
        "aviso_previo_dias": "33 dias",
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
        rule = AvisoPrevioDiasRule()
        assert rule.id == "CONSISTENCIA_AVISO_PREVIO_DIAS"
        assert rule.prioridade == 50


class TestAvisoPrevioDias:
    def setup_method(self):
        self.rule = AvisoPrevioDiasRule()

    def test_aviso_entre_30_e_90_nao_gera_aviso(self):
        ctx = _ctx(aviso_previo_dias="33 dias")
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_aviso_abaixo_30_gera_aviso(self):
        ctx = _ctx(aviso_previo_dias="20 dias")
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "abaixo do mínimo de 30 dias" in avisos[0].get("mensagem", "")

    def test_aviso_acima_90_gera_aviso(self):
        ctx = _ctx(aviso_previo_dias="95 dias")
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "excede 90 dias máximos" in avisos[0].get("mensagem", "")

    def test_sem_campo_nao_gera_aviso(self):
        ctx = _ctx(aviso_previo_dias="")
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_regra_registrada(self):
        ctx = _ctx()
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas


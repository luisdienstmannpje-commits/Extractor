import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.aviso_previo_sem_justa_causa import (
    AvisoPrevioSemJustaCausaRule,
)


def _ctx(**kwargs):
    base = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
        "motivo_rescisao": "Sem justa causa",
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
        rule = AvisoPrevioSemJustaCausaRule()
        assert rule.id == "CONSISTENCIA_AVISO_PREVIO_SEM_JUSTA_CAUSA"
        assert rule.prioridade == 50


class TestAvisoPrevioSemJustaCausa:
    def setup_method(self):
        self.rule = AvisoPrevioSemJustaCausaRule()

    def test_sem_justa_causa_com_aviso_campo_nao_gera_aviso(self):
        ctx = _ctx(motivo_rescisao="Sem justa causa", aviso_previo_dias="33 dias")
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_sem_justa_causa_com_verba_aviso_nao_gera_aviso(self):
        ctx = _ctx(
            motivo_rescisao="Sem justa causa",
            verbas_deferidas=[VerbaContexto(nome="Aviso Prévio Indenizado", reflexos=[])],
        )
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_sem_justa_causa_sem_aviso_gera_aviso(self):
        ctx = _ctx(motivo_rescisao="Sem justa causa", aviso_previo_dias=None)
        ctx.verbas_deferidas = []
        ctx = self.rule.aplicar(ctx)
        avisos = _avisos(ctx.alertas, self.rule.id)
        assert len(avisos) == 1
        assert "aviso prévio não encontrado" in avisos[0].get("mensagem", "")

    def test_com_justa_causa_nao_gera_aviso(self):
        ctx = _ctx(motivo_rescisao="Com justa causa", aviso_previo_dias=None)
        ctx = self.rule.aplicar(ctx)
        assert _avisos(ctx.alertas, self.rule.id) == []

    def test_regra_registrada(self):
        ctx = _ctx()
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas

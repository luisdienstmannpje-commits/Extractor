import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico
from services.legal_engine.rules.deducao_autorizada import DeducaoAutorizadaRule


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


def _infos(alertas, regra_id):
    return [
        a
        for a in alertas
        if isinstance(a, dict)
        and a.get("nivel") == "INFO"
        and a.get("regra_id") == regra_id
    ]


class TestDeducaoAutorizadaMetadados:
    def test_id_prioridade(self):
        rule = DeducaoAutorizadaRule()
        assert rule.id == "CONSISTENCIA_DEDUCAO_AUTORIZADA"
        assert rule.prioridade == 50


class TestDeducaoAutorizadaAplicacao:
    def test_sem_deducao_nao_emite_info(self):
        ctx = _ctx(autorizada_deducao=False)
        rule = DeducaoAutorizadaRule()
        out = rule.aplicar(ctx)
        infos = _infos(out.alertas, rule.id)
        assert len(infos) == 0

    def test_com_deducao_emite_info(self):
        ctx = _ctx(autorizada_deducao=True)
        rule = DeducaoAutorizadaRule()
        out = rule.aplicar(ctx)
        infos = _infos(out.alertas, rule.id)
        assert len(infos) == 1
        assert "dedução" in infos[0].get("mensagem", "").lower() or "compensa" in infos[0].get("mensagem", "").lower()
        assert "PJe-Calc" in infos[0].get("mensagem", "")

    def test_com_deducao_e_observacoes_inclui_trecho(self):
        ctx = _ctx(
            autorizada_deducao=True,
            observacoes_deducao="O reclamante já recebeu férias proporcionais.",
        )
        rule = DeducaoAutorizadaRule()
        out = rule.aplicar(ctx)
        infos = _infos(out.alertas, rule.id)
        assert len(infos) == 1
        assert "férias proporcionais" in infos[0].get("mensagem", "")

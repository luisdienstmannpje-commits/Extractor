import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.base_calculo_art_457 import BaseCalculoArt457Rule


def _ctx(verbas=None, **kwargs):
    base = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
        "data_saida_ctps": "15/01/2025",
        "data_ajuizamento": "01/02/2025",
        "data_sentenca": "01/06/2025",
    }
    base.update(kwargs)
    if verbas is not None:
        base["verbas_deferidas"] = verbas
    return ContextoJuridico(**base)


def _infos(alertas, regra_id):
    return [
        a
        for a in alertas
        if isinstance(a, dict)
        and a.get("nivel") == "INFO"
        and a.get("regra_id") == regra_id
    ]


class TestBaseCalculoArt457Metadados:
    def test_id_prioridade(self):
        rule = BaseCalculoArt457Rule()
        assert rule.id == "CONSISTENCIA_BASE_CALCULO_ART_457"
        assert rule.prioridade == 50


class TestBaseCalculoArt457Aplicacao:
    def test_sem_verbas_que_demandam_integracao_nao_emite_info(self):
        ctx = _ctx(verbas=[VerbaContexto(nome="Salário", valor_fixado="10000.00")])
        rule = BaseCalculoArt457Rule()
        out = rule.aplicar(ctx)
        infos = _infos(out.alertas, rule.id)
        assert len(infos) == 0

    def test_com_horas_extras_emite_info(self):
        ctx = _ctx(
            verbas=[
                VerbaContexto(nome="Horas extras", valor_fixado="2000.00"),
            ]
        )
        rule = BaseCalculoArt457Rule()
        out = rule.aplicar(ctx)
        infos = _infos(out.alertas, rule.id)
        assert len(infos) == 1
        assert "art. 457" in infos[0].get("mensagem", "").lower() or "457" in infos[0].get("mensagem", "")

    def test_com_adicional_noturno_emite_info(self):
        ctx = _ctx(
            verbas=[
                VerbaContexto(nome="Adicional noturno", valor_fixado="500.00"),
            ]
        )
        rule = BaseCalculoArt457Rule()
        out = rule.aplicar(ctx)
        infos = _infos(out.alertas, rule.id)
        assert len(infos) == 1

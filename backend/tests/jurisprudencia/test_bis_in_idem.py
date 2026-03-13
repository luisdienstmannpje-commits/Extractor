import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.bis_in_idem import BisInIdemReflexosRule


def _ctx(verbas):
    return ContextoJuridico(
        numero_processo="0001234-56.2024.5.03.0001",
        data_admissao="01/03/2020",
        data_demissao="15/01/2025",
        verbas_deferidas=verbas,
    )


def _erros(alertas, regra_id):
    return [
        a
        for a in alertas
        if isinstance(a, dict)
        and a.get("nivel") == "ERRO"
        and a.get("regra_id") == regra_id
    ]


class TestMetadados:
    def test_id_e_prioridade(self):
        rule = BisInIdemReflexosRule()
        assert rule.id == "CONSISTENCIA_BIS_IN_IDEM_REFLEXOS"
        assert rule.prioridade == 50


class TestBisInIdem:
    def setup_method(self):
        self.rule = BisInIdemReflexosRule()

    def test_mesma_verba_nos_reflexos_gera_erro(self):
        ctx = _ctx(
            [
                VerbaContexto(
                    nome="Horas Extras", reflexos=["Horas Extras", "DSR"]
                )
            ]
        )
        ctx = self.rule.aplicar(ctx)
        erros = _erros(ctx.alertas, self.rule.id)
        assert len(erros) == 1
        assert "Bis in idem" in erros[0].get("mensagem", "")

    def test_nome_canonizado_igual_reflexo_canonizado(self):
        # Verifica que a normalização funciona (ex.: variações de grafia)
        ctx = _ctx(
            [
                VerbaContexto(
                    nome="horas extra", reflexos=["HORAS   EXTRAS "]
                )
            ]
        )
        ctx = self.rule.aplicar(ctx)
        erros = _erros(ctx.alertas, self.rule.id)
        assert len(erros) == 1

    def test_reflexos_diferentes_nao_geram_erro(self):
        ctx = _ctx(
            [
                VerbaContexto(
                    nome="Horas Extras", reflexos=["DSR", "Férias"]
                )
            ]
        )
        ctx = self.rule.aplicar(ctx)
        assert _erros(ctx.alertas, self.rule.id) == []

    def test_sem_reflexos_nao_gera_erro(self):
        ctx = _ctx([VerbaContexto(nome="Horas Extras", reflexos=[])])
        ctx = self.rule.aplicar(ctx)
        assert _erros(ctx.alertas, self.rule.id) == []

    def test_sem_verbas_regra_ainda_registrada(self):
        ctx = _ctx([])
        ctx = self.rule.aplicar(ctx)
        assert self.rule.id in ctx.regras_aplicadas


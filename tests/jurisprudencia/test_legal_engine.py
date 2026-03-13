"""
tests/jurisprudencia/test_legal_engine.py

Testes unitários do Motor de Direito Programável.

Cada regra jurídica tem seu próprio caso de teste.
Executar com: python -m pytest tests/jurisprudencia/test_legal_engine.py -v

Filosofia:
  - Um teste por comportamento, não por função
  - Inputs realistas (dados como viriam do pipeline)
  - Assertions claras sobre o ID da regra ativada
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ctx(**kwargs) -> ContextoJuridico:
    """Cria ContextoJuridico com valores padrão mínimos."""
    defaults = {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "data_admissao":   "01/03/2020",
        "data_demissao":   "15/01/2025",
        "data_ajuizamento":"01/02/2025",
        "data_sentenca":   "01/06/2025",
        "salario_base":    "R$ 3.500,00",
    }
    defaults.update(kwargs)
    return ContextoJuridico(**defaults)


def _ids_alertados(alertas: list) -> list[str]:
    """Extrai IDs das regras que geraram alertas."""
    return [a.get("regra_id", "") for a in alertas if isinstance(a, dict)]


def _tem_nivel(alertas: list, nivel: str, regra_id: str) -> bool:
    return any(
        a.get("nivel") == nivel and a.get("regra_id") == regra_id
        for a in alertas if isinstance(a, dict)
    )


# ── ADC 58 STF ────────────────────────────────────────────────────────────────

class TestADC58:

    def test_ipca_selic_correto(self):
        from services.jurisprudencia.stf.adc_58 import ADC58CorrecaoMonetaria
        rule = ADC58CorrecaoMonetaria()
        ctx  = _ctx(indice_correcao="IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento)")
        ctx  = rule.aplicar(ctx)
        assert ctx.correcao_pre_judicial == "IPCA-E"
        assert ctx.correcao_judicial     == "SELIC"
        assert "ADC_58_STF" in ctx.regras_aplicadas

    def test_tr_gera_aviso(self):
        from services.jurisprudencia.stf.adc_58 import ADC58CorrecaoMonetaria
        rule = ADC58CorrecaoMonetaria()
        ctx  = _ctx(indice_correcao="TR")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "AVISO", "ADC_58_STF")


# ── OJ 42 SDI-1 TST ───────────────────────────────────────────────────────────

class TestOJ42:

    def test_multa_nao_incide_correto(self):
        from services.jurisprudencia.orientacoes.oj_42 import OJ42FGTSMultaAvisoPrevio
        rule = OJ42FGTSMultaAvisoPrevio()
        ctx  = _ctx(fgts_multa_40_aviso_previo="Não incide — OJ 42 TST")
        ctx  = rule.aplicar(ctx)
        assert not any(a.get("nivel") == "ERRO" for a in ctx.alertas if isinstance(a, dict))
        assert "OJ_42_SDI1_TST" in ctx.regras_aplicadas

    def test_multa_incide_gera_erro(self):
        from services.jurisprudencia.orientacoes.oj_42 import OJ42FGTSMultaAvisoPrevio
        rule = OJ42FGTSMultaAvisoPrevio()
        ctx  = _ctx(fgts_multa_40_aviso_previo="Sim — incide sobre aviso prévio")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "ERRO", "OJ_42_SDI1_TST")


# ── Súmula 305 TST ────────────────────────────────────────────────────────────

class TestSumula305:

    def test_fgts_incide_correto(self):
        from services.jurisprudencia.sumulas.sumula_305 import Sumula305FGTSAP
        rule = Sumula305FGTSAP()
        ctx  = _ctx(fgts_sobre_aviso_previo="Sim — FGTS incide sobre aviso prévio (Súm. 305 TST)")
        ctx  = rule.aplicar(ctx)
        assert "SUMULA_305_TST" in ctx.regras_aplicadas
        assert not ctx.alertas

    def test_fgts_nao_incide_gera_aviso(self):
        from services.jurisprudencia.sumulas.sumula_305 import Sumula305FGTSAP
        rule = Sumula305FGTSAP()
        ctx  = _ctx(fgts_sobre_aviso_previo="Não incide sobre aviso prévio")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "AVISO", "SUMULA_305_TST")


# ── OJ 195 SDI-1 TST ─────────────────────────────────────────────────────────

class TestOJ195:

    def test_fgts_ferias_nao_incide_correto(self):
        from services.jurisprudencia.orientacoes.oj_195 import OJ195FGTSFeriasIndenizadas
        rule = OJ195FGTSFeriasIndenizadas()
        ctx  = _ctx(fgts_sobre_ferias_indenizadas="Não incide — OJ 195 TST")
        ctx  = rule.aplicar(ctx)
        assert not ctx.alertas

    def test_fgts_ferias_incide_gera_erro(self):
        from services.jurisprudencia.orientacoes.oj_195 import OJ195FGTSFeriasIndenizadas
        rule = OJ195FGTSFeriasIndenizadas()
        ctx  = _ctx(fgts_sobre_ferias_indenizadas="Sim — incide")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "ERRO", "OJ_195_SDI1_TST")


# ── OJ 394 SDI-1 TST ─────────────────────────────────────────────────────────

class TestOJ394:

    def test_dsr_refletindo_em_ferias_gera_erro(self):
        from services.jurisprudencia.orientacoes.oj_394 import OJ394DSRReflexos
        rule = OJ394DSRReflexos()
        ctx  = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="DSR", reflexos=["Férias", "13º Salário", "FGTS"])
        ]
        ctx = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "ERRO", "OJ_394_SDI1_TST")

    def test_dsr_sem_reflexos_proibidos_ok(self):
        from services.jurisprudencia.orientacoes.oj_394 import OJ394DSRReflexos
        rule = OJ394DSRReflexos()
        ctx  = _ctx()
        ctx.verbas_deferidas = [VerbaContexto(nome="DSR", reflexos=[])]
        ctx = rule.aplicar(ctx)
        assert not ctx.alertas


# ── Art. 791-A CLT ────────────────────────────────────────────────────────────

class TestArt791A:

    def test_honorarios_10_pct_ok(self):
        from services.jurisprudencia.clt.art_791a import Art791AHonorarios
        rule = Art791AHonorarios()
        ctx  = _ctx(percentual_honorarios="10%")
        ctx  = rule.aplicar(ctx)
        assert not ctx.alertas
        assert "ART_791A_CLT" in ctx.regras_aplicadas

    def test_honorarios_abaixo_5_gera_aviso(self):
        from services.jurisprudencia.clt.art_791a import Art791AHonorarios
        rule = Art791AHonorarios()
        ctx  = _ctx(percentual_honorarios="3%")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "AVISO", "ART_791A_CLT")

    def test_honorarios_acima_15_gera_aviso(self):
        from services.jurisprudencia.clt.art_791a import Art791AHonorarios
        rule = Art791AHonorarios()
        ctx  = _ctx(percentual_honorarios="20%")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "AVISO", "ART_791A_CLT")


# ── Lei 12.506/2011 ───────────────────────────────────────────────────────────

class TestLei12506:

    def test_42_dias_ok(self):
        from services.jurisprudencia.clt.lei_12506 import Lei12506AvisoPrevio
        rule = Lei12506AvisoPrevio()
        ctx  = _ctx(aviso_previo_dias="42 dias — 30 + 12 pela Lei 12.506/2011")
        ctx  = rule.aplicar(ctx)
        assert not ctx.alertas

    def test_abaixo_30_gera_aviso(self):
        from services.jurisprudencia.clt.lei_12506 import Lei12506AvisoPrevio
        rule = Lei12506AvisoPrevio()
        ctx  = _ctx(aviso_previo_dias="20 dias")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "AVISO", "LEI_12506_2011")

    def test_acima_90_gera_aviso(self):
        from services.jurisprudencia.clt.lei_12506 import Lei12506AvisoPrevio
        rule = Lei12506AvisoPrevio()
        ctx  = _ctx(aviso_previo_dias="95 dias")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "AVISO", "LEI_12506_2011")


# ── Consistência: datas ───────────────────────────────────────────────────────

class TestCronologiaDatas:

    def test_datas_consistentes_ok(self):
        from services.jurisprudencia.consistencia.datas import CronologiaDatas
        rule = CronologiaDatas()
        ctx  = _ctx()
        ctx  = rule.aplicar(ctx)
        assert not ctx.alertas

    def test_admissao_posterior_demissao_gera_erro(self):
        from services.jurisprudencia.consistencia.datas import CronologiaDatas
        rule = CronologiaDatas()
        ctx  = _ctx(data_admissao="01/01/2026", data_demissao="01/01/2020")
        ctx  = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "ERRO", "CONSISTENCIA_DATAS")


# ── Consistência: verbas ──────────────────────────────────────────────────────

class TestBisInIdem:

    def test_verba_reflete_em_si_mesma_gera_erro(self):
        from services.jurisprudencia.consistencia.verbas import BisInIdem
        rule = BisInIdem()
        ctx  = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="Horas Extras", reflexos=["Horas Extras", "DSR"])
        ]
        ctx = rule.aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "ERRO", "BIS_IN_IDEM_VERBAS")

    def test_reflexos_normais_ok(self):
        from services.jurisprudencia.consistencia.verbas import BisInIdem
        rule = BisInIdem()
        ctx  = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="Horas Extras", reflexos=["DSR", "13º Salário"])
        ]
        ctx = rule.aplicar(ctx)
        assert not ctx.alertas


# ── Integração: engine completo ───────────────────────────────────────────────

class TestEngineIntegracao:
    """Testa o engine com todas as regras carregadas (teste de integração)."""

    def _dados_minimos(self, **overrides) -> dict:
        base = {
            "numero_processo":             "0001234-56.2024.5.03.0001",
            "reclamante":                  "João da Silva",
            "reclamada":                   "Empresa Teste Ltda",
            "data_admissao":               "01/03/2020",
            "data_demissao":               "15/01/2025",
            "data_ajuizamento":            "01/02/2025",
            "data_sentenca":               "01/06/2025",
            "salario_base":                "R$ 3.500,00",
            "motivo_rescisao":             "Sem justa causa",
            "indice_correcao":             "IPCA-E (pré) / SELIC (pós) — ADC 58",
            "percentual_honorarios":       "10%",
            "aviso_previo_dias":           "33 dias",
            "fgts_sobre_aviso_previo":     "Sim — incide (Súm. 305 TST)",
            "fgts_multa_40_aviso_previo":  "Não incide — OJ 42 TST",
            "fgts_sobre_ferias_indenizadas": "Não incide — OJ 195 TST",
            "verbas_deferidas":            [],
            "alertas_juridicos":           [],
        }
        base.update(overrides)
        return base

    def test_dados_corretos_sem_alertas(self):
        from services.legal_validator import validar_dados
        dados = self._dados_minimos()
        alertas = validar_dados(dados)
        erros = [a for a in alertas if "[ERRO]" in a]
        assert erros == [], f"Erros inesperados: {erros}"

    def test_retorna_lista_de_strings(self):
        from services.legal_validator import validar_dados
        dados = self._dados_minimos()
        alertas = validar_dados(dados)
        assert isinstance(alertas, list)
        for a in alertas:
            assert isinstance(a, str), f"Alerta não é string: {a}"
            assert a.startswith("["), f"Alerta sem formato [NIVEL]: {a}"

    def test_memorial_juridico_disponivel(self):
        from services.legal_validator import validar_dados_completo
        dados = self._dados_minimos()
        resultado = validar_dados_completo(dados)
        assert "alertas"           in resultado
        assert "regras_aplicadas"  in resultado
        assert "memorial_juridico" in resultado
        assert len(resultado["regras_aplicadas"]) > 0, "Nenhuma regra foi aplicada"
"""
tests/jurisprudencia/test_legal_engine_borda.py

Testes de borda do Motor de Direito Programável.
Complementa test_legal_engine.py (casos nominais).

Foco: inputs None, limites exatos, canonização de strings,
      múltiplas verbas, formatos alternativos e dados ausentes.

Executar com:
    python -m pytest tests/jurisprudencia/test_legal_engine_borda.py -v
    python -m pytest tests/ -v   ← roda nominal + borda juntos
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto


# ── Helpers (mesmos do arquivo nominal) ──────────────────────────────────────

def _ctx(**kwargs) -> ContextoJuridico:
    defaults = {
        "numero_processo":  "0001234-88.2024.5.03.0001",  # CNJ dígito verificador válido
        "data_admissao":    "01/03/2020",
        "data_demissao":    "15/01/2025",
        "data_ajuizamento": "01/02/2025",
        "data_sentenca":    "01/06/2025",
        "salario_base":     "R$ 3.500,00",
    }
    defaults.update(kwargs)
    return ContextoJuridico(**defaults)


def _tem_nivel(alertas: list, nivel: str, regra_id: str) -> bool:
    return any(
        a.get("nivel") == nivel and a.get("regra_id") == regra_id
        for a in alertas if isinstance(a, dict)
    )


def _niveis(alertas: list) -> list:
    return [a.get("nivel") for a in alertas if isinstance(a, dict)]


# ── ADC 58 STF ────────────────────────────────────────────────────────────────

class TestADC58Borda:

    def test_indice_none_sem_alerta(self):
        """Dado ausente não deve gerar alerta — regra não se aplica."""
        from services.jurisprudencia.stf.adc_58 import ADC58CorrecaoMonetaria
        ctx = ADC58CorrecaoMonetaria().aplicar(_ctx(indice_correcao=None))
        assert ctx.alertas == []

    def test_indice_vazio_sem_alerta(self):
        """String vazia equivale a dado ausente."""
        from services.jurisprudencia.stf.adc_58 import ADC58CorrecaoMonetaria
        ctx = ADC58CorrecaoMonetaria().aplicar(_ctx(indice_correcao=""))
        assert ctx.alertas == []

    def test_apenas_selic_sem_pre_judicial(self):
        """Apenas SELIC informada: correcao_judicial preenchida, pre_judicial fica None."""
        from services.jurisprudencia.stf.adc_58 import ADC58CorrecaoMonetaria
        ctx = ADC58CorrecaoMonetaria().aplicar(_ctx(indice_correcao="SELIC"))
        assert ctx.correcao_judicial == "SELIC"
        assert ctx.correcao_pre_judicial is None


# ── OJ 42 SDI-1 TST ───────────────────────────────────────────────────────────

class TestOJ42Borda:

    def test_campo_none_sem_alerta(self):
        """FGTS multa não informado: regra não se aplica, sem alerta."""
        from services.jurisprudencia.orientacoes.oj_42 import OJ42FGTSMultaAvisoPrevio
        ctx = OJ42FGTSMultaAvisoPrevio().aplicar(_ctx(fgts_multa_40_aviso_previo=None))
        assert ctx.alertas == []


# ── Súmula 305 TST ────────────────────────────────────────────────────────────

class TestSumula305Borda:

    def test_campo_none_sem_alerta(self):
        """FGTS AP não informado: regra não se aplica, sem alerta."""
        from services.jurisprudencia.sumulas.sumula_305 import Sumula305FGTSAP
        ctx = Sumula305FGTSAP().aplicar(_ctx(fgts_sobre_aviso_previo=None))
        assert ctx.alertas == []

    def test_nao_incide_com_palavra_incide_gera_aviso(self):
        """
        'Não incide sobre aviso prévio' contém a palavra 'incide'.
        A regra deve identificar a negação e gerar AVISO — não silenciar.
        """
        from services.jurisprudencia.sumulas.sumula_305 import Sumula305FGTSAP
        ctx = Sumula305FGTSAP().aplicar(
            _ctx(fgts_sobre_aviso_previo="Não incide sobre aviso prévio indenizado")
        )
        assert _tem_nivel(ctx.alertas, "AVISO", "SUMULA_305_TST")


# ── OJ 195 SDI-1 TST ─────────────────────────────────────────────────────────

class TestOJ195Borda:

    def test_campo_none_sem_alerta(self):
        """FGTS férias não informado: regra não se aplica."""
        from services.jurisprudencia.orientacoes.oj_195 import OJ195FGTSFeriasIndenizadas
        ctx = OJ195FGTSFeriasIndenizadas().aplicar(_ctx(fgts_sobre_ferias_indenizadas=None))
        assert ctx.alertas == []

    def test_nao_incide_maiusculas_sem_alerta(self):
        """Variação de capitalização não deve gerar falso erro."""
        from services.jurisprudencia.orientacoes.oj_195 import OJ195FGTSFeriasIndenizadas
        ctx = OJ195FGTSFeriasIndenizadas().aplicar(
            _ctx(fgts_sobre_ferias_indenizadas="NÃO INCIDE — OJ 195 TST")
        )
        assert not _tem_nivel(ctx.alertas, "ERRO", "OJ_195_SDI1_TST")


# ── OJ 394 SDI-1 TST ─────────────────────────────────────────────────────────

class TestOJ394Borda:

    def test_nome_por_extenso_detectado(self):
        """
        'Descanso Semanal Remunerado' é o mesmo que 'DSR'.
        A regra deve canonizar o nome e detectar o reflexo proibido.
        """
        from services.jurisprudencia.orientacoes.oj_394 import OJ394DSRReflexos
        ctx = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="Descanso Semanal Remunerado", reflexos=["Férias"])
        ]
        ctx = OJ394DSRReflexos().aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "ERRO", "OJ_394_SDI1_TST")

    def test_reflexo_minusculo_detectado(self):
        """Reflexo 'férias' (minúsculo) deve ser identificado como proibido."""
        from services.jurisprudencia.orientacoes.oj_394 import OJ394DSRReflexos
        ctx = _ctx()
        ctx.verbas_deferidas = [VerbaContexto(nome="DSR", reflexos=["férias"])]
        ctx = OJ394DSRReflexos().aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "ERRO", "OJ_394_SDI1_TST")

    def test_multiplas_verbas_dsr_um_alerta_por_reflexo_proibido(self):
        """
        Duas verbas DSR: uma com reflexo proibido, uma sem.
        Deve gerar exatamente 1 alerta.
        """
        from services.jurisprudencia.orientacoes.oj_394 import OJ394DSRReflexos
        ctx = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="DSR", reflexos=["Férias"]),      # proibido
            VerbaContexto(nome="DSR", reflexos=["Horas Extras"]), # permitido
        ]
        ctx = OJ394DSRReflexos().aplicar(ctx)
        erros = [a for a in ctx.alertas if isinstance(a, dict) and a.get("nivel") == "ERRO"]
        assert len(erros) == 1


# ── Art. 791-A CLT ────────────────────────────────────────────────────────────

class TestArt791ABorda:

    def test_percentual_none_sem_alerta(self):
        """Campo não informado: regra não se aplica."""
        from services.jurisprudencia.clt.art_791a import Art791AHonorarios
        ctx = Art791AHonorarios().aplicar(_ctx(percentual_honorarios=None))
        assert ctx.alertas == []

    def test_percentual_5_limite_minimo_sem_alerta(self):
        """5% é o limite mínimo legal — não deve gerar alerta."""
        from services.jurisprudencia.clt.art_791a import Art791AHonorarios
        ctx = Art791AHonorarios().aplicar(_ctx(percentual_honorarios="5%"))
        assert ctx.alertas == []

    def test_percentual_15_limite_maximo_sem_alerta(self):
        """15% é o limite máximo legal — não deve gerar alerta."""
        from services.jurisprudencia.clt.art_791a import Art791AHonorarios
        ctx = Art791AHonorarios().aplicar(_ctx(percentual_honorarios="15%"))
        assert ctx.alertas == []

    def test_percentual_sem_simbolo_parseable(self):
        """'5' sem '%' deve ser interpretado como 5% e não gerar alerta."""
        from services.jurisprudencia.clt.art_791a import Art791AHonorarios
        ctx = Art791AHonorarios().aplicar(_ctx(percentual_honorarios="5"))
        assert ctx.alertas == []


# ── Lei 12.506/2011 ───────────────────────────────────────────────────────────

class TestLei12506Borda:

    def test_campo_none_sem_alerta(self):
        """Aviso prévio não informado: regra não se aplica."""
        from services.jurisprudencia.clt.lei_12506 import Lei12506AvisoPrevio
        ctx = Lei12506AvisoPrevio().aplicar(_ctx(aviso_previo_dias=None))
        assert ctx.alertas == []

    def test_30_dias_limite_minimo_sem_alerta(self):
        """30 dias é o mínimo legal — não deve gerar alerta."""
        from services.jurisprudencia.clt.lei_12506 import Lei12506AvisoPrevio
        ctx = Lei12506AvisoPrevio().aplicar(_ctx(aviso_previo_dias="30 dias"))
        assert ctx.alertas == []

    def test_90_dias_limite_maximo_sem_alerta(self):
        """90 dias é o teto da Lei 12.506/2011 — não deve gerar alerta."""
        from services.jurisprudencia.clt.lei_12506 import Lei12506AvisoPrevio
        ctx = Lei12506AvisoPrevio().aplicar(_ctx(aviso_previo_dias="90 dias"))
        assert ctx.alertas == []

    def test_formato_calculo_explicito(self):
        """'30 + 3 = 33 dias' — extrai 33 e não gera alerta."""
        from services.jurisprudencia.clt.lei_12506 import Lei12506AvisoPrevio
        ctx = Lei12506AvisoPrevio().aplicar(_ctx(aviso_previo_dias="30 + 3 = 33 dias"))
        assert ctx.alertas == []


# ── Consistência: datas ───────────────────────────────────────────────────────

class TestCronologiaDatasBorda:

    def test_datas_none_sem_alerta(self):
        """Datas ausentes: regra não se aplica, sem alerta."""
        from services.jurisprudencia.consistencia.datas import CronologiaDatas
        ctx = CronologiaDatas().aplicar(_ctx(data_admissao=None, data_demissao=None))
        assert ctx.alertas == []

    def test_demissao_igual_ajuizamento_sem_alerta(self):
        """Demissão e ajuizamento no mesmo dia é válido (demissão → ajuizamento imediato)."""
        from services.jurisprudencia.consistencia.datas import CronologiaDatas
        ctx = CronologiaDatas().aplicar(
            _ctx(data_demissao="01/02/2025", data_ajuizamento="01/02/2025")
        )
        assert not _tem_nivel(ctx.alertas, "ERRO", "CONSISTENCIA_DATAS")

    def test_formato_dd_mm_yy_dois_digitos(self):
        """Datas em formato DD/MM/YY (2 dígitos) devem ser parseadas sem erro."""
        from services.jurisprudencia.consistencia.datas import CronologiaDatas
        ctx = CronologiaDatas().aplicar(
            _ctx(data_admissao="01/03/20", data_demissao="15/01/25")
        )
        # Se fizer parse correto (2020 < 2025), sem erro de cronologia
        erros = [a for a in ctx.alertas if isinstance(a, dict) and a.get("nivel") == "ERRO"]
        assert erros == []


# ── Consistência: verbas (bis in idem) ───────────────────────────────────────

class TestBisInIdemBorda:

    def test_reflexos_none_sem_excecao(self):
        """reflexos=None não deve lançar exceção nem gerar alerta."""
        from services.jurisprudencia.consistencia.verbas import BisInIdem
        ctx = _ctx()
        ctx.verbas_deferidas = [VerbaContexto(nome="Horas Extras", reflexos=None)]
        ctx = BisInIdem().aplicar(ctx)
        assert ctx.alertas == []

    def test_reflexos_lista_vazia_sem_alerta(self):
        """Verba sem reflexos: sem bis in idem possível."""
        from services.jurisprudencia.consistencia.verbas import BisInIdem
        ctx = _ctx()
        ctx.verbas_deferidas = [VerbaContexto(nome="Horas Extras", reflexos=[])]
        ctx = BisInIdem().aplicar(ctx)
        assert ctx.alertas == []

    def test_canonizacao_case_insensitive(self):
        """
        'horas extras' (minúsculo) refletindo 'Horas Extras' (capitalizado)
        deve ser detectado como bis in idem.
        """
        from services.jurisprudencia.consistencia.verbas import BisInIdem
        ctx = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="horas extras", reflexos=["Horas Extras"])
        ]
        ctx = BisInIdem().aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "ERRO", "BIS_IN_IDEM_VERBAS")

    def test_multiplas_verbas_bis_in_idem_alertas_individuais(self):
        """
        Duas verbas com bis in idem devem gerar 2 alertas separados
        (um por verba), não um alerta global.
        """
        from services.jurisprudencia.consistencia.verbas import BisInIdem
        ctx = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="Horas Extras",    reflexos=["Horas Extras"]),
            VerbaContexto(nome="13º Salário",     reflexos=["13º Salário"]),
        ]
        ctx = BisInIdem().aplicar(ctx)
        erros = [a for a in ctx.alertas if isinstance(a, dict) and a.get("nivel") == "ERRO"]
        assert len(erros) >= 2


# ── Súmula 264 TST ────────────────────────────────────────────────────────────

class TestSumula264Borda:

    def test_he_indenizatoria_sem_alerta(self):
        """HE indenizatória (integracao_salarial=False) não deve gerar alerta."""
        from services.jurisprudencia.sumulas.sumula_264 import Sumula264DSRReflexoHE
        ctx = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="Horas Extras", integracao_salarial=False, reflexos=[])
        ]
        ctx = Sumula264DSRReflexoHE().aplicar(ctx)
        assert ctx.alertas == []

    def test_he_integracao_none_gera_aviso(self):
        """
        integracao_salarial=None significa incerteza.
        A regra deve gerar AVISO (verificar, não erro).
        """
        from services.jurisprudencia.sumulas.sumula_264 import Sumula264DSRReflexoHE
        ctx = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="Horas Extras", integracao_salarial=None, reflexos=[])
        ]
        ctx = Sumula264DSRReflexoHE().aplicar(ctx)
        assert _tem_nivel(ctx.alertas, "AVISO", "SUMULA_264_TST")

    def test_he_com_dsr_nos_reflexos_sem_alerta(self):
        """HE habitual com DSR nos reflexos — correto, sem alerta."""
        from services.jurisprudencia.sumulas.sumula_264 import Sumula264DSRReflexoHE
        ctx = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="Horas Extras", integracao_salarial=True, reflexos=["DSR"])
        ]
        ctx = Sumula264DSRReflexoHE().aplicar(ctx)
        assert ctx.alertas == []

    def test_multiplas_he_um_alerta_por_violacao(self):
        """
        Duas verbas HE: uma sem DSR (viola), uma com DSR (ok).
        Deve gerar exatamente 1 alerta.
        """
        from services.jurisprudencia.sumulas.sumula_264 import Sumula264DSRReflexoHE
        ctx = _ctx()
        ctx.verbas_deferidas = [
            VerbaContexto(nome="Horas Extras 50%", integracao_salarial=True, reflexos=[]),
            VerbaContexto(nome="Horas Extras 100%", integracao_salarial=True, reflexos=["DSR"]),
        ]
        ctx = Sumula264DSRReflexoHE().aplicar(ctx)
        avisos = [a for a in ctx.alertas if isinstance(a, dict) and a.get("nivel") == "AVISO"]
        assert len(avisos) == 1


# ── Súmula 91 TST ─────────────────────────────────────────────────────────────

class TestSumula91Borda:

    def test_salario_normal_sem_alerta(self):
        """Salário sem termos suspeitos: sem alerta de complessivo."""
        from services.jurisprudencia.sumulas.sumula_91 import Sumula91SalarioComplessivo
        ctx = Sumula91SalarioComplessivo().aplicar(_ctx(salario_base="R$ 3.500,00"))
        assert ctx.alertas == []

    def test_tudo_incluido_gera_aviso(self):
        """'Tudo incluído' no salário base detecta complessivo."""
        from services.jurisprudencia.sumulas.sumula_91 import Sumula91SalarioComplessivo
        ctx = Sumula91SalarioComplessivo().aplicar(
            _ctx(salario_base="R$ 3.500,00 (tudo incluído)")
        )
        assert _tem_nivel(ctx.alertas, "AVISO", "SUMULA_91_TST")


# ── Consistência: salário ─────────────────────────────────────────────────────

class TestConsistenciaSalarioBorda:

    def test_salario_minimo_exato_sem_alerta(self):
        """R$ 1.518,00 = mínimo exato de 2025 — não deve gerar alerta."""
        from services.jurisprudencia.consistencia.salario import ConsistenciaSalario
        ctx = ConsistenciaSalario().aplicar(_ctx(salario_base="R$ 1.518,00"))
        assert ctx.alertas == []

    def test_salario_um_real_abaixo_gera_aviso(self):
        """R$ 1.517,00 está abaixo do mínimo — deve gerar AVISO."""
        from services.jurisprudencia.consistencia.salario import ConsistenciaSalario
        ctx = ConsistenciaSalario().aplicar(_ctx(salario_base="R$ 1.517,00"))
        assert _tem_nivel(ctx.alertas, "AVISO", "CONSISTENCIA_SALARIO")

    def test_salario_zero_gera_erro(self):
        """R$ 0,00 é inválido — deve gerar ERRO."""
        from services.jurisprudencia.consistencia.salario import ConsistenciaSalario
        ctx = ConsistenciaSalario().aplicar(_ctx(salario_base="R$ 0,00"))
        assert _tem_nivel(ctx.alertas, "ERRO", "CONSISTENCIA_SALARIO")

    def test_salario_nao_parseavel_gera_aviso(self):
        """Texto não numérico deve gerar AVISO de parse, não exceção."""
        from services.jurisprudencia.consistencia.salario import ConsistenciaSalario
        ctx = ConsistenciaSalario().aplicar(_ctx(salario_base="valor não informado"))
        assert _tem_nivel(ctx.alertas, "AVISO", "CONSISTENCIA_SALARIO")

    def test_salario_none_sem_excecao(self):
        """salario_base=None não deve lançar exceção."""
        from services.jurisprudencia.consistencia.salario import ConsistenciaSalario
        ctx = ConsistenciaSalario().aplicar(_ctx(salario_base=None))
        # Pode gerar AVISO ou silenciar — o importante é não lançar exceção
        assert isinstance(ctx.alertas, list)


# ── Integração: engine completo ───────────────────────────────────────────────

class TestEngineBorda:
    """Testes de integração com cenários completos."""

    def _processo_limpo(self, **overrides) -> dict:
        """Processo sem nenhuma violação jurídica."""
        base = {
            "numero_processo":               "0001234-88.2024.5.03.0001",  # CNJ válido (engine)
            "reclamante":                    "João da Silva",
            "reclamada":                     "Empresa Teste Ltda",
            "data_admissao":                 "01/03/2020",
            "data_demissao":                 "15/01/2025",
            "data_ajuizamento":              "01/02/2025",
            "data_sentenca":                 "01/06/2025",
            "salario_base":                  "R$ 3.500,00",
            "motivo_rescisao":               "Sem justa causa",
            "indice_correcao":               "IPCA-E (pré) / SELIC (pós) — ADC 58",
            "percentual_honorarios":         "10%",
            "aviso_previo_dias":             "33 dias",
            "fgts_sobre_aviso_previo":       "Sim — incide (Súm. 305 TST)",
            "fgts_multa_40_aviso_previo":    "Não incide — OJ 42 TST",
            "fgts_sobre_ferias_indenizadas": "Não incide — OJ 195 TST",
            "verbas_deferidas":              [],
            "alertas_juridicos":             [],
        }
        base.update(overrides)
        return base

    def test_processo_completamente_limpo_zero_erros(self):
        """Processo juridicamente correto não deve gerar nenhum ERRO."""
        from services.legal_validator import validar_dados
        alertas = validar_dados(self._processo_limpo())
        erros = [a for a in alertas if "[ERRO]" in a]
        assert erros == [], f"Erros inesperados em processo limpo: {erros}"

    def test_salario_abaixo_minimo_gera_aviso_no_pipeline(self):
        """Salário abaixo do mínimo deve aparecer nos alertas do validar_dados."""
        from services.legal_validator import validar_dados
        alertas = validar_dados(self._processo_limpo(salario_base="R$ 800,00"))
        assert any("CONSISTENCIA_SALARIO" in a or "1.518" in a or "mínimo" in a.lower()
                   for a in alertas), f"Alerta de salário não encontrado: {alertas}"

    def test_multiplas_violacoes_geram_alertas_independentes(self):
        """
        OJ 42 (multa indevida) + honorários fora do limite devem gerar
        pelo menos 2 alertas via engine.

        Nota ADC 58: o engine usa data_admissao como data_ref para is_aplicavel().
        A ADC 58 tem vigencia_inicio=2020-12-18 — contratos admitidos antes dessa
        data (como o padrão 01/03/2020) são pulados. Este é o comportamento correto
        da pirâmide de Kelsen: a decisão só vincula sentenças posteriores a dez/2020.
        Para testar ADC 58 use data_admissao >= 2021-01-01 ou teste a regra isoladamente
        (ver TestADC58::test_tr_gera_aviso em test_legal_engine.py).
        """
        from services.legal_validator import validar_dados_completo
        dados = self._processo_limpo(
            data_admissao="01/01/2021",           # pós-ADC58
            indice_correcao="TR",                  # ADC58 ativa
            fgts_multa_40_aviso_previo="Sim — incide multa 40%",  # OJ42 ativa
        )
        resultado = validar_dados_completo(dados)
        alertas = resultado["alertas"]
        assert len(alertas) >= 2, f"Esperava >= 2 alertas, got {len(alertas)}: {alertas}"

    def test_validar_dados_completo_estrutura(self):
        """validar_dados_completo deve retornar dict com as 3 chaves esperadas."""
        from services.legal_validator import validar_dados_completo
        resultado = validar_dados_completo(self._processo_limpo())
        assert "alertas"           in resultado
        assert "regras_aplicadas"  in resultado
        assert "memorial_juridico" in resultado

    def test_alertas_sao_strings_formatadas(self):
        """Todos os alertas devem ser strings no formato '[NIVEL] [REGRA_ID] mensagem'."""
        from services.legal_validator import validar_dados
        alertas = validar_dados(self._processo_limpo(
            indice_correcao="TR",
            fgts_multa_40_aviso_previo="Sim — incide",
        ))
        for a in alertas:
            assert isinstance(a, str), f"Alerta não é string: {a}"
            assert a.startswith("["), f"Formato incorreto: {a}"
"""
test_verba_deduplicator.py — Testes unitários da Skill S9

Cobre:
  - deduplicar_verbas()     — função utilitária usada pelo processor.py
  - VerbaDeduplicator.aplicar — LegalRule do engine

Executar:
    cd backend
    pytest tests/jurisprudencia/test_verba_deduplicator.py -v

Convenção: test_<função>__<cenário>
"""

import pytest
from services.jurisprudencia.consistencia.verba_deduplicator import deduplicar_verbas, VerbaDeduplicator


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _verba(nome, periodo="2023/2024", **kwargs):
    """Cria dict de verba para testes de deduplicar_verbas()."""
    return {"nome": nome, "periodo": periodo, **kwargs}


def _ctx_verba(nome, periodo="2023/2024"):
    """Cria VerbaContexto para testes do LegalRule."""
    from services.legal_engine.rule_base import VerbaContexto
    return VerbaContexto(nome=nome, periodo=periodo)


def _make_ctx(*verbas_contexto):
    """Cria ContextoJuridico com verbas."""
    from services.legal_engine.rule_base import ContextoJuridico
    ctx = ContextoJuridico()
    ctx.verbas_deferidas = list(verbas_contexto)
    return ctx


# ─────────────────────────────────────────────────────────────────────────────
# deduplicar_verbas — lista vazia / sem duplicatas
# ─────────────────────────────────────────────────────────────────────────────

class TestDeduplicarVerbasSemDuplicatas:

    def test_lista_vazia(self):
        limpas, avisos = deduplicar_verbas([])
        assert limpas == []
        assert avisos == []

    def test_verba_unica_sem_aviso(self):
        verbas = [_verba("Horas Extras")]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 1
        assert avisos == []

    def test_verbas_diferentes_sem_aviso(self):
        verbas = [
            _verba("Horas Extras",      "2023/2024"),
            _verba("Adicional Noturno", "2023/2024"),
            _verba("DSR",               "2023/2024"),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 3
        assert avisos == []

    def test_mesmo_nome_periodos_distintos_sem_aviso(self):
        """Férias com períodos diferentes NÃO são duplicatas."""
        verbas = [
            _verba("Férias", "2022/2023"),
            _verba("Férias", "2023/2024"),
            _verba("Férias", "2024/2025"),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 3
        assert avisos == []

    def test_13_salario_periodos_distintos_sem_aviso(self):
        verbas = [
            _verba("13º Salário", "2023"),
            _verba("13º Salário", "2024"),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 2
        assert avisos == []


# ─────────────────────────────────────────────────────────────────────────────
# deduplicar_verbas — duplicatas detectadas
# ─────────────────────────────────────────────────────────────────────────────

class TestDeduplicarVerbasComDuplicatas:

    def test_duplicata_exata_remove_segunda(self):
        verbas = [
            _verba("Horas Extras", "2023/2024"),
            _verba("Horas Extras", "2023/2024"),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 1
        assert len(avisos) == 1

    def test_duplicata_mantem_primeira(self):
        v1 = _verba("Horas Extras", "2023/2024", valor_fixado="R$ 1.000,00")
        v2 = _verba("Horas Extras", "2023/2024", valor_fixado="R$ 2.000,00")
        limpas, _ = deduplicar_verbas([v1, v2])
        assert limpas[0]["valor_fixado"] == "R$ 1.000,00"

    def test_aviso_contem_nome_verba(self):
        verbas = [_verba("DSR", "2023/2024"), _verba("DSR", "2023/2024")]
        _, avisos = deduplicar_verbas(verbas)
        assert any("DSR" in a for a in avisos)

    def test_aviso_contem_periodo(self):
        verbas = [_verba("Férias", "2023/2024"), _verba("Férias", "2023/2024")]
        _, avisos = deduplicar_verbas(verbas)
        assert any("2023/2024" in a for a in avisos)

    def test_tres_duplicatas_duas_removidas(self):
        verbas = [
            _verba("Horas Extras", "2023/2024"),
            _verba("Horas Extras", "2023/2024"),
            _verba("Horas Extras", "2023/2024"),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 1
        assert len(avisos) == 2

    def test_multiplas_verbas_uma_duplicata(self):
        verbas = [
            _verba("Horas Extras",      "2023/2024"),
            _verba("Adicional Noturno", "2023/2024"),
            _verba("Horas Extras",      "2023/2024"),  # duplicata
            _verba("DSR",               "2023/2024"),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 3
        assert len(avisos) == 1

    def test_canonizacao_case_insensitive(self):
        """'horas extras' e 'Horas Extras' são a mesma verba."""
        verbas = [
            _verba("horas extras",  "2023/2024"),
            _verba("Horas Extras",  "2023/2024"),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 1
        assert len(avisos) == 1

    def test_canonizacao_variante_ortografica(self):
        """'Hora Extra' e 'Horas Extras' são canonizadas igual."""
        verbas = [
            _verba("Hora Extra",   "2023/2024"),
            _verba("Horas Extras", "2023/2024"),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 1
        assert len(avisos) == 1

    def test_periodo_none_tratado(self):
        """periodo=None não deve lançar exceção."""
        verbas = [
            _verba("DSR", None),
            _verba("DSR", None),
        ]
        limpas, avisos = deduplicar_verbas(verbas)
        assert len(limpas) == 1
        assert len(avisos) == 1

    def test_nome_none_nao_explode(self):
        """nome=None não deve lançar exceção."""
        verbas = [{"nome": None, "periodo": "2023/2024"}] * 2
        limpas, avisos = deduplicar_verbas(verbas)
        assert isinstance(limpas, list)
        assert isinstance(avisos, list)


# ─────────────────────────────────────────────────────────────────────────────
# VerbaDeduplicator — LegalRule
# ─────────────────────────────────────────────────────────────────────────────

class TestVerbaDeduplicatorRule:

    @pytest.fixture
    def regra(self):
        return VerbaDeduplicator()

    # -- metadados ------------------------------------------------------------

    def test_id_correto(self, regra):
        assert regra.id == "S9_VERBA_DEDUPLICATOR"

    def test_prioridade(self, regra):
        assert regra.prioridade == 50

    def test_is_aplicavel_sempre_true(self, regra):
        assert regra.is_aplicavel(None) is True

    # -- sem duplicatas -------------------------------------------------------

    def test_sem_verbas__silencio(self, regra):
        ctx = _make_ctx()
        resultado = regra.aplicar(ctx)
        assert resultado.alertas == []

    def test_verbas_unicas__silencio(self, regra):
        ctx = _make_ctx(
            _ctx_verba("Horas Extras",      "2023/2024"),
            _ctx_verba("Adicional Noturno", "2023/2024"),
        )
        resultado = regra.aplicar(ctx)
        assert resultado.alertas == []

    def test_ferias_periodos_distintos__silencio(self, regra):
        """Férias com períodos distintos não são duplicatas."""
        ctx = _make_ctx(
            _ctx_verba("Férias", "2022/2023"),
            _ctx_verba("Férias", "2023/2024"),
            _ctx_verba("Férias", "2024/2025"),
        )
        resultado = regra.aplicar(ctx)
        assert resultado.alertas == []

    # -- com duplicatas -------------------------------------------------------

    def test_duplicata__gera_aviso(self, regra):
        ctx = _make_ctx(
            _ctx_verba("Horas Extras", "2023/2024"),
            _ctx_verba("Horas Extras", "2023/2024"),
        )
        resultado = regra.aplicar(ctx)
        assert any(a["nivel"] == "AVISO" for a in resultado.alertas)

    def test_duplicata__mensagem_contem_nome(self, regra):
        ctx = _make_ctx(
            _ctx_verba("DSR", "2023/2024"),
            _ctx_verba("DSR", "2023/2024"),
        )
        resultado = regra.aplicar(ctx)
        assert any("DSR" in a["mensagem"] for a in resultado.alertas)

    def test_duplicata__regra_registrada(self, regra):
        ctx = _make_ctx(
            _ctx_verba("Horas Extras", "2023/2024"),
            _ctx_verba("Horas Extras", "2023/2024"),
        )
        resultado = regra.aplicar(ctx)
        assert "S9_VERBA_DEDUPLICATOR" in resultado.regras_aplicadas

    def test_duplicata__nao_remove_da_lista(self, regra):
        """O LegalRule só alerta — quem remove é o processor.py."""
        ctx = _make_ctx(
            _ctx_verba("Horas Extras", "2023/2024"),
            _ctx_verba("Horas Extras", "2023/2024"),
        )
        resultado = regra.aplicar(ctx)
        assert len(resultado.verbas_deferidas) == 2

    def test_duas_duplicatas_dois_avisos(self, regra):
        ctx = _make_ctx(
            _ctx_verba("Horas Extras", "2023/2024"),
            _ctx_verba("Horas Extras", "2023/2024"),
            _ctx_verba("DSR",          "2023/2024"),
            _ctx_verba("DSR",          "2023/2024"),
        )
        resultado = regra.aplicar(ctx)
        avisos = [a for a in resultado.alertas if a["nivel"] == "AVISO"]
        assert len(avisos) == 2

    def test_nao_gera_erro__apenas_aviso(self, regra):
        ctx = _make_ctx(
            _ctx_verba("Horas Extras", "2023/2024"),
            _ctx_verba("Horas Extras", "2023/2024"),
        )
        resultado = regra.aplicar(ctx)
        assert not any(a["nivel"] == "ERRO" for a in resultado.alertas)
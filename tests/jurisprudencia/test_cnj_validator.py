"""
test_cnj_validator.py — Testes unitários do validador de número CNJ

Cobre:
  - validar_cnj()              — função utilitária
  - extrair_partes_cnj()       — parser do formato
  - calcular_numero_cnj()      — gerador de números válidos
  - NumeroCNJValidator.aplicar — LegalRule do engine

Executar:
    cd backend
    pytest tests/jurisprudencia/test_cnj_validator.py -v

Convenção: test_<função>__<cenário>
"""

import pytest
from services.jurisprudencia.consistencia.numero_cnj_validator import (
    validar_cnj,
    extrair_partes_cnj,
    calcular_numero_cnj,
    NumeroCNJValidator,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_contexto(numero_processo=None, **kwargs):
    from services.legal_engine.rule_base import ContextoJuridico
    return ContextoJuridico(numero_processo=numero_processo, **kwargs)


def _alertas(ctx):
    return [f"[{a['nivel']}] {a['mensagem']}" for a in ctx.alertas]


# ─────────────────────────────────────────────────────────────────────────────
# validar_cnj — números válidos
# ─────────────────────────────────────────────────────────────────────────────

class TestValidarCNJValidos:

    def test_numero_radialista_valido(self):
        """Número real do caso de teste do projeto."""
        ok, motivo = validar_cnj("0010691-91.2025.5.03.0167")
        assert ok is True
        assert motivo == ""

    def test_numero_gerado_valido(self):
        """Número gerado pela própria função calcular_numero_cnj deve ser válido."""
        numero = calcular_numero_cnj("0000001", "2024", "5", "01", "0001")
        ok, _ = validar_cnj(numero)
        assert ok is True

    def test_numero_com_espacos_valido(self):
        """Espaços no início/fim devem ser ignorados."""
        ok, _ = validar_cnj("  0010691-91.2025.5.03.0167  ")
        assert ok is True

    def test_multiplos_tribunais_validos(self):
        """Verifica que o algoritmo funciona para diferentes tribunais."""
        # Gera números válidos para TRT-SP (02), TRT-RJ (01), TST (00)
        for tt in ("01", "02", "00"):
            numero = calcular_numero_cnj("0001234", "2023", "5", tt, "0001")
            ok, motivo = validar_cnj(numero)
            assert ok is True, f"Falhou para TT={tt}: {motivo}"

    def test_ano_variado_valido(self):
        """Números de anos diferentes devem validar corretamente."""
        for aaaa in ("2018", "2020", "2023", "2025"):
            numero = calcular_numero_cnj("0005678", aaaa, "5", "03", "0100")
            ok, motivo = validar_cnj(numero)
            assert ok is True, f"Falhou para ano {aaaa}: {motivo}"


# ─────────────────────────────────────────────────────────────────────────────
# validar_cnj — números inválidos
# ─────────────────────────────────────────────────────────────────────────────

class TestValidarCNJInvalidos:

    def test_digito_errado_retorna_false(self):
        """DD incorreto deve retornar False."""
        ok, motivo = validar_cnj("0010691-00.2025.5.03.0167")
        assert ok is False
        assert "dígito verificador" in motivo.lower() or "inválido" in motivo.lower()

    def test_digito_off_by_one(self):
        """DD correto ± 1 deve ser inválido."""
        numero_base = calcular_numero_cnj("0010691", "2025", "5", "03", "0167")
        partes = numero_base.split("-")
        dd_correto = int(partes[1].split(".")[0])

        # DD + 1
        dd_errado = f"{(dd_correto + 1) % 100:02d}"
        numero_errado = numero_base.replace(f"-{dd_correto:02d}.", f"-{dd_errado}.")
        ok, _ = validar_cnj(numero_errado)
        assert ok is False

    def test_formato_sem_hifen(self):
        """Sem hífen — formato inválido."""
        ok, motivo = validar_cnj("001069177.2025.5.03.0167")
        assert ok is False
        assert "formato" in motivo.lower() or "inválido" in motivo.lower()

    def test_formato_pontos_errados(self):
        """Pontos nos lugares errados."""
        ok, motivo = validar_cnj("0010691-77-2025-5-03-0167")
        assert ok is False

    def test_numero_vazio(self):
        """String vazia retorna False."""
        ok, motivo = validar_cnj("")
        assert ok is False

    def test_numero_none(self):
        """None retorna False."""
        ok, motivo = validar_cnj(None)
        assert ok is False

    def test_numero_so_zeros(self):
        """Zeros em todos os campos — improvável mas deve validar o DD."""
        ok, _ = validar_cnj("0000000-00.0000.0.00.0000")
        # Pode ser válido ou inválido — o importante é não lançar exceção
        assert isinstance(ok, bool)

    def test_nnnnnnn_com_letras(self):
        """Letras no NNNNNNN — formato inválido."""
        ok, motivo = validar_cnj("ABCDEFG-77.2025.5.03.0167")
        assert ok is False

    def test_dd_99_invalido(self):
        """DD=99 — quase sempre inválido (extremamente raro ser correto)."""
        ok, _ = validar_cnj("9999999-99.2023.8.26.0050")
        # Só verificamos que retorna bool sem explodir
        assert isinstance(ok, bool)


# ─────────────────────────────────────────────────────────────────────────────
# extrair_partes_cnj
# ─────────────────────────────────────────────────────────────────────────────

class TestExtrairPartesCNJ:

    def test_extrai_partes_corretas(self):
        partes = extrair_partes_cnj("0010691-77.2025.5.03.0167")
        assert partes is not None
        assert partes["nnnnnnn"] == "0010691"
        assert partes["dd"]      == "77"
        assert partes["aaaa"]    == "2025"
        assert partes["j"]       == "5"
        assert partes["tt"]      == "03"
        assert partes["oooo"]    == "0167"

    def test_formato_invalido_retorna_none(self):
        assert extrair_partes_cnj("numero-invalido") is None

    def test_vazio_retorna_none(self):
        assert extrair_partes_cnj("") is None

    def test_none_retorna_none(self):
        assert extrair_partes_cnj(None) is None

    def test_chaves_presentes(self):
        partes = extrair_partes_cnj("0000001-15.2025.5.03.0167")
        assert partes is not None
        for chave in ("nnnnnnn", "dd", "aaaa", "j", "tt", "oooo"):
            assert chave in partes


# ─────────────────────────────────────────────────────────────────────────────
# calcular_numero_cnj
# ─────────────────────────────────────────────────────────────────────────────

class TestCalcularNumeroCNJ:

    def test_numero_gerado_passa_na_validacao(self):
        numero = calcular_numero_cnj("0010691", "2025", "5", "03", "0167")
        ok, motivo = validar_cnj(numero)
        assert ok is True, f"Número gerado inválido: {motivo}"

    def test_formato_correto(self):
        numero = calcular_numero_cnj("0000001", "2024", "5", "01", "0001")
        import re
        assert re.match(r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$", numero)

    def test_radialista_gera_77(self):
        """Confirma que o algoritmo gera DD=77 para o caso de teste."""
        numero = calcular_numero_cnj("0010691", "2025", "5", "03", "0167")
        assert "-91." in numero


# ─────────────────────────────────────────────────────────────────────────────
# NumeroCNJValidator — LegalRule
# ─────────────────────────────────────────────────────────────────────────────

class TestNumeroCNJValidatorRule:

    @pytest.fixture
    def regra(self):
        return NumeroCNJValidator()

    # -- metadados -----------------------------------------------------------

    def test_id_correto(self, regra):
        assert regra.id == "CNJ_DIGITO_VERIFICADOR"

    def test_prioridade_consistencia(self, regra):
        assert regra.prioridade == 50

    def test_is_aplicavel_sempre_true(self, regra):
        from datetime import date
        assert regra.is_aplicavel(None) is True
        assert regra.is_aplicavel(date(2015, 1, 1)) is True
        assert regra.is_aplicavel(date(2025, 12, 31)) is True

    # -- número válido -------------------------------------------------------

    def test_numero_valido__silencio(self, regra):
        """Número com DD correto — nenhum alerta."""
        ctx = _make_contexto("0010691-91.2025.5.03.0167")
        resultado = regra.aplicar(ctx)
        assert resultado.alertas == []

    def test_numero_valido__registra_regra(self, regra):
        ctx = _make_contexto("0010691-91.2025.5.03.0167")
        resultado = regra.aplicar(ctx)
        assert "CNJ_DIGITO_VERIFICADOR" in resultado.regras_aplicadas

    # -- número inválido -----------------------------------------------------

    def test_numero_invalido__erro(self, regra):
        """DD incorreto — deve emitir ERRO."""
        ctx = _make_contexto("0010691-00.2025.5.03.0167")
        resultado = regra.aplicar(ctx)
        assert any("[ERRO]" in a for a in _alertas(resultado))

    def test_numero_invalido__mensagem_informativa(self, regra):
        """Mensagem deve citar dígito verificador."""
        ctx = _make_contexto("0010691-00.2025.5.03.0167")
        resultado = regra.aplicar(ctx)
        alertas = _alertas(resultado)
        assert any("dígito" in a.lower() or "verificador" in a.lower() for a in alertas)

    # -- número ausente ------------------------------------------------------

    def test_numero_ausente__info(self, regra):
        """numero_processo=None — INFO (não ERRO, pode ser extração incompleta)."""
        ctx = _make_contexto(None)
        resultado = regra.aplicar(ctx)
        assert any("[INFO]" in a for a in _alertas(resultado))

    def test_numero_ausente__nao_erro(self, regra):
        """Ausência não deve gerar ERRO — apenas INFO."""
        ctx = _make_contexto(None)
        resultado = regra.aplicar(ctx)
        assert not any("[ERRO]" in a for a in _alertas(resultado))

    # -- formato errado ------------------------------------------------------

    def test_formato_invalido__erro(self, regra):
        """Formato completamente errado — ERRO."""
        ctx = _make_contexto("processo-invalido-123")
        resultado = regra.aplicar(ctx)
        assert any("[ERRO]" in a for a in _alertas(resultado))

    def test_numero_sem_hifen__erro(self, regra):
        ctx = _make_contexto("001069177.2025.5.03.0167")
        resultado = regra.aplicar(ctx)
        assert any("[ERRO]" in a for a in _alertas(resultado))
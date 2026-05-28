"""
Ciclo TDD — valor_causa
Campo completamente ausente do pre_extractor (extraído apenas via IA).
Padrões a cobrir:
  PAD 1: "Valor da causa: R$ X" — label clássico
  PAD 2: "Valor atribuído à causa: R$ X" — forma petição inicial
  PAD 3: "causa no valor de R$ X" — forma narrativa
  PAD 4: "dou a causa o valor de R$ X" / "dou à presente causa o valor de R$ X" — fórmula de pedido
  PAD 5: "atribuo à causa o valor de R$ X" — variante
  PAD 6: "Valor total da causa: R$ X" — label com "total"
"""
import pytest
from services.pre_extractor import PreExtractor


def _run(text: str) -> str | None:
    r = PreExtractor(text).run()
    return r["high"].get("valor_causa") or r["medium"].get("valor_causa")


# ── PAD 1: label clássico ────────────────────────────────────────────────────

class TestValorCausaLabelClassico:
    def test_valor_da_causa_reais(self):
        assert _run("Valor da causa: R$ 50.000,00") == "R$ 50.000,00"

    def test_valor_da_causa_sem_espaco(self):
        assert _run("valor da causa: R$12.500,00") == "R$ 12.500,00"

    def test_valor_da_causa_maiusculo(self):
        assert _run("VALOR DA CAUSA: R$ 200.000,00") == "R$ 200.000,00"

    def test_valor_da_causa_hifen(self):
        assert _run("Valor da causa - R$ 35.000,00") == "R$ 35.000,00"

    def test_valor_do_causa(self):
        # "valor do processo" às vezes usado
        assert _run("valor da causa: R$ 8.750,00") == "R$ 8.750,00"


# ── PAD 2: "Valor atribuído à causa" ────────────────────────────────────────

class TestValorCausaAtribuido:
    def test_valor_atribuido_a_causa(self):
        assert _run("Valor atribuido a causa: R$ 35.000,00") == "R$ 35.000,00"

    def test_valor_atribuido_a_causa_acento(self):
        assert _run("Valor atribuído à causa: R$ 45.000,00") == "R$ 45.000,00"

    def test_valor_atribuido_sem_colon(self):
        assert _run("valor atribuido a causa R$ 15.000,00") == "R$ 15.000,00"


# ── PAD 3: "causa no valor de" ───────────────────────────────────────────────

class TestValorCausaNoValor:
    def test_causa_no_valor_de(self):
        assert _run("causa no valor de R$ 8.000,00") == "R$ 8.000,00"

    def test_causa_no_valor_de_minusculo(self):
        assert _run("a causa no valor de R$ 120.000,00") == "R$ 120.000,00"


# ── PAD 4: "dou à causa o valor de" ─────────────────────────────────────────

class TestValorCausaDou:
    def test_dou_a_causa(self):
        assert _run("dou a causa o valor de R$ 120.000,00") == "R$ 120.000,00"

    def test_dou_a_presente_causa(self):
        assert _run("dou a presente causa o valor de R$ 45.000,00") == "R$ 45.000,00"

    def test_dou_acento(self):
        assert _run("dou à causa o valor de R$ 90.000,00") == "R$ 90.000,00"

    def test_dou_a_presente_causa_acento(self):
        assert _run("dou à presente causa o valor de R$ 75.000,00") == "R$ 75.000,00"


# ── PAD 5: "atribuo à causa o valor de" ─────────────────────────────────────

class TestValorCausaAtribuo:
    def test_atribuo_a_causa(self):
        assert _run("atribuo a causa o valor de R$ 75.000,00") == "R$ 75.000,00"

    def test_atribuo_a_presente_causa(self):
        assert _run("atribuo a presente causa o valor de R$ 30.000,00") == "R$ 30.000,00"


# ── PAD 6: "Valor total da causa" ────────────────────────────────────────────

class TestValorCausaTotal:
    def test_valor_total_da_causa(self):
        assert _run("Valor total da causa: R$ 200.000,00") == "R$ 200.000,00"

    def test_valor_total_da_causa_sem_colon(self):
        assert _run("valor total da causa R$ 55.000,00") == "R$ 55.000,00"


# ── Não deve capturar outros valores ────────────────────────────────────────

class TestValorCausaNegativo:
    def test_salario_nao_captura(self):
        """Salário não deve ser confundido com valor da causa"""
        assert _run("recebia salario de R$ 2.000,00") is None

    def test_dano_moral_nao_captura(self):
        assert _run("dano moral no valor de R$ 10.000,00") is None


# ── GAP — 'deu/atribuiu à causa' (pretérito perfeito) ───────────────────────

class TestValorCausaPreterito:
    def test_deu_a_causa(self):
        """'deu à causa o valor de' — pretérito perfeito de 'dou'."""
        assert _run("deu a causa o valor de R$ 12.000,00") == "R$ 12.000,00"

    def test_deu_a_presente_causa(self):
        assert _run("deu a presente causa o valor de R$ 45.000,00") == "R$ 45.000,00"

    def test_atribuiu_a_causa(self):
        """'atribuiu à causa o valor de' — pretérito perfeito de 'atribuo'."""
        assert _run("atribuiu a causa o valor de R$ 9.000,00") == "R$ 9.000,00"


# ── GAP — 'causa: R$ X' (label direto) ──────────────────────────────────────

class TestValorCausaLabelDireto:
    def test_causa_colon_rs(self):
        """'causa: R$ X' — rótulo direto sem 'valor da'."""
        assert _run("causa: R$ 7.500,00") == "R$ 7.500,00"

    def test_causa_hifen_rs(self):
        assert _run("causa - R$ 15.000,00") == "R$ 15.000,00"

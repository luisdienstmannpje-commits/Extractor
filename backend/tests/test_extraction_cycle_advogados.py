"""
Ciclo TDD — advogado_reclamante / advogado_reclamada
Gaps identificados no probe:
  GAP 1: "Patrono do autor:" / "patrono do reclamante:" — label alternativo
  GAP 2: "representado pelo advogado X" — forma narrativa
  GAP 3: "patrono da ré:" / "patrono da reclamada:" — label alternativo reclamada
  GAP 4: "representada pelo advogado X" — forma narrativa reclamada
"""
import pytest
from services.pre_extractor import PreExtractor


def _rec(text: str) -> str | None:
    r = PreExtractor(text).run()
    return r["high"].get("advogado_reclamante") or r["medium"].get("advogado_reclamante")


def _rec2(text: str) -> str | None:
    r = PreExtractor(text).run()
    return r["high"].get("advogado_reclamada") or r["medium"].get("advogado_reclamada")


# ── Regressão — reclamante ──────────────────────────────────────────────────

class TestAdvReclamanteRegressao:
    def test_adv_label_abrev(self):
        assert _rec("Adv. do Reclamante: Dr. Joao Silva, OAB/SP 123456") == "Joao Silva"

    def test_advogado_label(self):
        assert _rec("Advogado do Reclamante: Joao Silva") == "Joao Silva"

    def test_advogada_label(self):
        assert _rec("Advogada do Reclamante: Maria Lima") == "Maria Lima"

    def test_dra_prefix(self):
        assert _rec("Adv. do Reclamante: Dra. Ana Souza, OAB/SP 999") == "Ana Souza"


# ── Regressão — reclamada ───────────────────────────────────────────────────

class TestAdvReclamadaRegressao:
    def test_adv_label_abrev(self):
        assert _rec2("Adv. da Reclamada: Dra. Ana Costa, OAB/SP 222333") == "Ana Costa"

    def test_advogada_label(self):
        assert _rec2("Advogada da Reclamada: Lucia Ferreira") == "Lucia Ferreira"

    def test_advogado_label(self):
        assert _rec2("Advogado da Reclamada: Carlos Borges") == "Carlos Borges"


# ── GAP 1: "Patrono do autor" / "patrono do reclamante" ────────────────────

class TestAdvReclamanteGap1Patrono:
    def test_patrono_autor_colon(self):
        """patrono do autor: Nome Sobrenome"""
        assert _rec("Patrono do autor: Maria Santos, OAB/RJ 98765") == "Maria Santos"

    def test_patrono_reclamante_colon(self):
        """patrono do reclamante: Nome"""
        r = _rec("patrono do reclamante: Carlos Lima, OAB/SP 11111")
        assert r == "Carlos Lima"

    def test_patrono_autor_sem_titulo(self):
        assert _rec("Patrono do autor: Paulo Roberto Mendes") == "Paulo Roberto Mendes"

    def test_patrono_autor_com_dra(self):
        assert _rec("Patrono do autor: Dra. Sofia Alves, OAB/MG 33333") == "Sofia Alves"


# ── GAP 2: "representado pelo advogado X" ──────────────────────────────────

class TestAdvReclamanteGap2Representado:
    def test_representado_pelo_advogado(self):
        """representado pelo advogado Nome, OAB"""
        r = _rec("representado pelo advogado Joao da Silva, OAB no 12345/SP")
        assert r == "Joao da Silva"

    def test_representado_pela_advogada(self):
        r = _rec("representado pela advogada Carla Rocha, OAB/SP 55555")
        assert r == "Carla Rocha"

    def test_autor_representado(self):
        """Autor representado pelo Dr. Nome"""
        r = _rec("Autor representado pelo Dr. Fernando Braga, OAB/RS 77777")
        assert r == "Fernando Braga"


# ── GAP 3: "Patrono da ré" / "patrono da reclamada" ────────────────────────

class TestAdvReclamadaGap3Patrono:
    def test_patrono_da_re(self):
        """patrono da ré: Nome"""
        r = _rec2("Patrono da re: Carlos Mendes, OAB/RS 444555")
        assert r == "Carlos Mendes"

    def test_patrono_reclamada_colon(self):
        r = _rec2("patrono da reclamada: Fernanda Rocha, OAB/SP 88888")
        assert r == "Fernanda Rocha"

    def test_patrono_reu(self):
        r = _rec2("Patrono do reu: Ricardo Oliveira, OAB/MG 22222")
        assert r == "Ricardo Oliveira"

    def test_patrono_da_re_dra(self):
        r = _rec2("Patrono da re: Dra. Beatriz Nunes, OAB/SP 66666")
        assert r == "Beatriz Nunes"


# ── GAP 4: "representada pelo advogado X" ──────────────────────────────────

class TestAdvReclamadaGap4Representada:
    def test_representada_pelo_advogado(self):
        r = _rec2("representada pelo advogado Pedro Lima, OAB no 77788/SP")
        assert r == "Pedro Lima"

    def test_representada_pela_advogada(self):
        r = _rec2("representada pela advogada Silvia Torres, OAB/SP 12321")
        assert r == "Silvia Torres"

    def test_re_representada(self):
        r = _rec2("Re representada pelo Dr. Antonio Branco, OAB/RJ 34534")
        assert r == "Antonio Branco"


# ── GAP 5: "Patrona da reclamante" — artigo feminino 'da' não coberto ───────

class TestAdvReclamanteGap5PatronaDa:
    def test_patrona_da_reclamante(self):
        """'Patrona da reclamante:' — artigo 'da' não coberto (só 'do')."""
        r = _rec("Patrona da reclamante: Dra. Beatriz Lima OAB/RJ 55555")
        assert r == "Beatriz Lima"

    def test_patrono_da_reclamante(self):
        """'Patrono da reclamante:' — reclamante feminina, artigo 'da'."""
        r = _rec("Patrono da reclamante: Carlos Pinto OAB/SP 11111")
        assert r == "Carlos Pinto"

    def test_patrona_da_autora(self):
        """'Patrona da autora:' — variante com 'autora'."""
        r = _rec("Patrona da autora: Ana Lima OAB/MG 88888")
        assert r == "Ana Lima"


# ── GAP 6: "Procurador da reclamante/reclamada" ──────────────────────────────

class TestAdvGap6Procurador:
    def test_procurador_da_reclamante(self):
        """'Procurador da reclamante:' — label não coberto."""
        r = _rec("Procurador da reclamante: Dr. Roberto Silva OAB/SP 22222")
        assert r == "Roberto Silva"

    def test_procurador_do_reclamante(self):
        r = _rec("Procuradora do reclamante: Dra. Carla Rocha OAB/RJ 33333")
        assert r == "Carla Rocha"

    def test_procurador_da_reclamada(self):
        r = _rec2("Procurador da reclamada: Dr. Marcos Dias OAB/SP 77777")
        assert r == "Marcos Dias"

    def test_procurador_do_reclamado(self):
        r = _rec2("Procuradora do reclamado: Silvia Torres OAB/PR 44444")
        assert r == "Silvia Torres"

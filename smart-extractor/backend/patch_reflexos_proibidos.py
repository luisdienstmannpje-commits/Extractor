"""
patch_reflexos_proibidos.py
Execute dentro de backend/:
    python patch_reflexos_proibidos.py
"""
import pathlib, sys

REGRA = pathlib.Path("services/legal_engine/rules/reflexos_proibidos.py")
TESTE = pathlib.Path("tests/jurisprudencia/test_reflexos_proibidos.py")

CONTEUDO_REGRA = '''"""
reflexos_proibidos.py — Regra: Reflexos Proibidos entre Verbas Trabalhistas

Fundamentos:
  - OJ 394 SDI-I TST: DSR nao reflete em Ferias, 13 Salario e FGTS
  - Vedacao legal geral: Multas (467/477), Dano Moral e Dano Material
    nao podem refletir em verbas salariais

Prioridade: 30 (TST Orientacoes Jurisprudenciais)
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


_REFLEXOS_PROIBIDOS: dict[str, list[str]] = {
    "DSR":             ["Ferias", "13 Salario", "FGTS"],
    "Multa art. 467":  ["DSR", "Ferias", "13 Salario", "FGTS", "Aviso Previo"],
    "Multa art. 477":  ["DSR", "Ferias", "13 Salario", "FGTS", "Aviso Previo"],
    "Dano Moral":      ["DSR", "Ferias", "13 Salario", "FGTS", "Aviso Previo"],
    "Dano Material":   ["DSR", "Ferias", "13 Salario", "FGTS", "Aviso Previo"],
    "Aviso Previo":    ["Aviso Previo"],
}

# Mapa canonico local (acentuado) para chave sem acento usada no dict acima
_CANON_MAP = {
    "Ferias":       "Ferias",
    "13 Salario":   "13 Salario",
    "Aviso Previo": "Aviso Previo",
}


def _strip_accents(s: str) -> str:
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


class ReflexosProibidosRule(LegalRule):
    id         = "OJ_394_SDI1_TST_REFLEXOS_PROIBIDOS"
    titulo     = "Reflexos Proibidos entre Verbas"
    base_legal = "OJ 394 SDI-I TST; vedacao legal — multas e indenizacoes"
    prioridade = 30
    descricao  = (
        "DSR nao pode refletir em Ferias, 13 Salario ou FGTS (OJ 394 SDI-I TST). "
        "Multas rescisórias e indenizacoes por dano moral/material nao integram "
        "a remuneracao e nao podem refletir em verbas salariais."
    )

    def _canon(self, nome: str) -> str:
        """Canoniza e remove acentos para usar como chave do dict."""
        return _strip_accents(self._canonizar_verba(nome))

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            for verba in contexto.verbas_deferidas:
                nome_c = self._canon(verba.nome or "")
                reflexos_c = [self._canon(r) for r in (verba.reflexos or [])]
                proibidos = _REFLEXOS_PROIBIDOS.get(nome_c, [])

                for reflexo in reflexos_c:
                    if reflexo in proibidos:
                        base = (
                            "OJ 394 SDI-I TST"
                            if nome_c == "DSR"
                            else "vedacao legal — natureza indenizatoria"
                        )
                        self._alerta(
                            contexto,
                            f"{base}: \'{nome_c}\' NAO pode refletir em "
                            f"\'{reflexo}\'. Verificar dispositivo da sentenca.",
                            nivel="ERRO",
                        )

            self._registrar(contexto)

        except Exception as e:
            self._alerta(contexto, f"Erro ao aplicar {self.id}: {e}", nivel="ERRO")

        return contexto
'''

CONTEUDO_TESTE = '''"""
test_reflexos_proibidos.py — Testes unitarios da ReflexosProibidosRule
Executar: python -m pytest tests/jurisprudencia/test_reflexos_proibidos.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.reflexos_proibidos import ReflexosProibidosRule


def _ctx_verba(nome, reflexos):
    return ContextoJuridico(
        numero_processo="0001234-56.2024.5.03.0001",
        data_admissao="01/03/2020",
        data_demissao="15/01/2025",
        verbas_deferidas=[VerbaContexto(nome=nome, reflexos=reflexos)]
    )

def _tem_erro(alertas, rid):
    return any(a.get("nivel") == "ERRO" and a.get("regra_id") == rid
               for a in alertas if isinstance(a, dict))

def _n_erros(alertas, rid):
    return sum(1 for a in alertas
               if isinstance(a, dict) and a.get("nivel") == "ERRO"
               and a.get("regra_id") == rid)


class TestDSROJ394:
    def setup_method(self): self.rule = ReflexosProibidosRule()
    def test_id_correto(self): assert self.rule.id == "OJ_394_SDI1_TST_REFLEXOS_PROIBIDOS"
    def test_prioridade_oj(self): assert self.rule.prioridade == 30
    def test_dsr_refletindo_em_ferias_gera_erro(self):
        ctx = self.rule.aplicar(_ctx_verba("DSR", ["Ferias"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_dsr_refletindo_em_13_salario_gera_erro(self):
        ctx = self.rule.aplicar(_ctx_verba("DSR", ["13 Salario"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_dsr_refletindo_em_fgts_gera_erro(self):
        ctx = self.rule.aplicar(_ctx_verba("DSR", ["FGTS"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_dsr_tres_proibidos_tres_erros(self):
        ctx = self.rule.aplicar(_ctx_verba("DSR", ["Ferias", "13 Salario", "FGTS"]))
        assert _n_erros(ctx.alertas, self.rule.id) == 3
    def test_dsr_sem_reflexos_silencio(self):
        ctx = self.rule.aplicar(_ctx_verba("DSR", []))
        assert not _tem_erro(ctx.alertas, self.rule.id)
    def test_mensagem_contem_oj394(self):
        ctx = self.rule.aplicar(_ctx_verba("DSR", ["Ferias"]))
        assert any("OJ 394" in a.get("mensagem", "") for a in ctx.alertas)
    def test_regra_registrada(self):
        ctx = self.rule.aplicar(_ctx_verba("DSR", ["Ferias"]))
        assert self.rule.id in ctx.regras_aplicadas


class TestMultasVedacao:
    def setup_method(self): self.rule = ReflexosProibidosRule()
    def test_multa_467_refletindo_em_ferias_gera_erro(self):
        ctx = self.rule.aplicar(_ctx_verba("Multa art. 467", ["Ferias"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_multa_477_refletindo_em_dsr_gera_erro(self):
        ctx = self.rule.aplicar(_ctx_verba("Multa art. 477", ["DSR"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_dano_moral_refletindo_em_fgts_gera_erro(self):
        ctx = self.rule.aplicar(_ctx_verba("Dano Moral", ["FGTS"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_dano_material_refletindo_em_aviso_previo_gera_erro(self):
        ctx = self.rule.aplicar(_ctx_verba("Dano Material", ["Aviso Previo"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_mensagem_contem_vedacao_legal(self):
        ctx = self.rule.aplicar(_ctx_verba("Multa art. 477", ["FGTS"]))
        assert any("vedacao" in a.get("mensagem", "") for a in ctx.alertas)
    def test_aviso_previo_refletindo_em_si_mesmo_gera_erro(self):
        ctx = self.rule.aplicar(_ctx_verba("Aviso Previo", ["Aviso Previo"]))
        assert _tem_erro(ctx.alertas, self.rule.id)


class TestReflexosPermitidos:
    def setup_method(self): self.rule = ReflexosProibidosRule()
    def test_horas_extras_refletindo_em_dsr_ok(self):
        ctx = self.rule.aplicar(_ctx_verba("Horas Extras", ["DSR"]))
        assert not _tem_erro(ctx.alertas, self.rule.id)
    def test_sem_verbas_silencio(self):
        ctx = ContextoJuridico(numero_processo="0001234-56.2024.5.03.0001", data_admissao="01/03/2020")
        ctx = self.rule.aplicar(ctx)
        assert ctx.alertas == []
    def test_verba_sem_reflexos_silencio(self):
        ctx = self.rule.aplicar(_ctx_verba("DSR", []))
        assert not _tem_erro(ctx.alertas, self.rule.id)


class TestCanonicizacao:
    def setup_method(self): self.rule = ReflexosProibidosRule()
    def test_dsr_minusculo_detectado(self):
        ctx = self.rule.aplicar(_ctx_verba("dsr", ["Ferias"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_descanso_semanal_detectado(self):
        ctx = self.rule.aplicar(_ctx_verba("Descanso Semanal Remunerado", ["Ferias"]))
        assert _tem_erro(ctx.alertas, self.rule.id)
    def test_horas_extras_variante_ok(self):
        ctx = self.rule.aplicar(_ctx_verba("hora extra", ["DSR"]))
        assert not _tem_erro(ctx.alertas, self.rule.id)
'''

for path, content in [(REGRA, CONTEUDO_REGRA), (TESTE, CONTEUDO_TESTE)]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[PATCH] Escrito: {path}")

print("[PATCH] Concluido. Rode: python -m pytest tests/jurisprudencia/test_reflexos_proibidos.py -v")
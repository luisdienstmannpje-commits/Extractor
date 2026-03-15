"""
patch_legal_validator.py
Execute dentro de backend/:
    python patch_legal_validator.py
Adiciona _check_oj42_multa_fgts e _check_adc58_indice_correcao ao ValidadorReflexos
e os registra na lista de checks do método validar().
"""
import re, sys, pathlib

ALVO = pathlib.Path("services/legal_validator.py")
if not ALVO.exists():
    sys.exit(f"[PATCH] ERRO: {ALVO} não encontrado. Execute dentro de backend/")

src = ALVO.read_text(encoding="utf-8")

# ── Guarda-chuva: não aplicar duas vezes ─────────────────────────────────────
if "_check_oj42_multa_fgts" in src:
    print("[PATCH] Checks já presentes — nada a fazer.")
    sys.exit(0)

# ── 1. Inserir os dois novos métodos antes de '# ── Execução' ────────────────
NOVOS_CHECKS = '''
    # ── Regras jurisprudenciais ───────────────────────────────────────────────

    def _check_oj42_multa_fgts(self):
        """
        OJ 42 SDI-1 TST: multa de 40% do FGTS NÃO incide sobre aviso prévio indenizado.
        Se o campo indica incidência sem ressalva, gera ERRO.
        """
        campo = (self.dados.get("fgts_multa_40_aviso_previo") or "").lower()
        if not campo:
            return
        tem_nao  = "não" in campo or "nao" in campo
        tem_oj42 = "oj 42" in campo or "oj42" in campo
        tem_sim  = "sim" in campo or ("incide" in campo and "não incide" not in campo)
        if (tem_nao or tem_oj42):
            return
        if tem_sim:
            self._alerta(
                "OJ 42 SDI-1 TST: multa de 40% do FGTS NÃO incide sobre aviso prévio "
                "indenizado. Verificar se o documento realmente determina incidência.",
                nivel="ERRO"
            )

    def _check_adc58_indice_correcao(self):
        """
        ADC 58 STF: correção monetária deve seguir IPCA-E (pré) + SELIC (pós).
        TR foi declarada inconstitucional. Aplica-se a admissões >= 18/12/2020.
        """
        campo = (self.dados.get("indice_correcao") or "").lower()
        if not campo:
            return
        usa_tr      = "tr" in campo or "taxa referencial" in campo
        usa_correto = "ipca" in campo or "selic" in campo or "adc 58" in campo or "adc58" in campo
        if usa_tr and not usa_correto:
            from datetime import date as _date
            admissao = self._parse_data(self.dados.get("data_admissao"))
            if admissao is None or admissao >= _date(2020, 12, 18):
                self._alerta(
                    "ADC 58 STF: TR foi declarada inconstitucional para correção de "
                    "débitos trabalhistas. Utilizar IPCA-E (pré-judicial) + SELIC "
                    "(judicial). Verificar índice aplicado.",
                    nivel="AVISO"
                )

'''

ANCORA_METODOS = "    # ── Execução ──────────────────────────────────────────────────────────────"
if ANCORA_METODOS not in src:
    sys.exit("[PATCH] ERRO: âncora '# ── Execução' não encontrada. Verifique o arquivo.")

src = src.replace(ANCORA_METODOS, NOVOS_CHECKS + ANCORA_METODOS)

# ── 2. Adicionar os dois checks na lista dentro de validar() ─────────────────
ANCORA_LISTA = "            self._check_verbas_duplicadas,\n        ]"
NOVA_LISTA   = "            self._check_verbas_duplicadas,\n            self._check_oj42_multa_fgts,\n            self._check_adc58_indice_correcao,\n        ]"

if ANCORA_LISTA not in src:
    sys.exit("[PATCH] ERRO: âncora da lista de checks não encontrada.")

src = src.replace(ANCORA_LISTA, NOVA_LISTA)

# ── 3. Gravar ────────────────────────────────────────────────────────────────
ALVO.write_text(src, encoding="utf-8")

total = src.count("def _check_")
print(f"[PATCH] ✅ Patch aplicado com sucesso — {total} checks no ValidadorReflexos.")
print("[PATCH] Rode: python -m pytest tests/jurisprudencia/ tests/test_sentence_understanding.py 2>&1 | tail -3")
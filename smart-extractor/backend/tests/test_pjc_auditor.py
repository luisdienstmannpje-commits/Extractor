"""
Testes para services.pjc_auditor — auditar_pjc_vs_sentenca.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.pjc_parser import PjcParser, PjcDadosBasicos
from services.pjc_auditor import auditar_pjc_vs_sentenca


def test_sem_divergencias_quando_iguais():
    dados_ia = {
        "indice_correcao": "IPCAE",
        "juros_mora": "TRD_SIMPLES",
        "divisor_horas": "220",
        "verbas_deferidas": [{"nome": "Horas Extras"}],
    }
    dados_pjc = PjcDadosBasicos(
        indice_trabalhista="IPCAE",
        juros_trabalhistas="TRD_SIMPLES",
        nomes_verbas=["Horas Extras"],
        divisor_horas=220.0,
    )
    divergencias = auditar_pjc_vs_sentenca(dados_ia, dados_pjc)
    assert divergencias == []


def test_divergencia_indice():
    dados_ia = {"indice_correcao": "IPCAE"}
    dados_pjc = PjcDadosBasicos(
        indice_trabalhista="SELIC",
        juros_trabalhistas=None,
        nomes_verbas=[],
        divisor_horas=None,
    )
    divergencias = auditar_pjc_vs_sentenca(dados_ia, dados_pjc)
    assert any("índice" in d.lower() or "correção" in d.lower() for d in divergencias)


def test_divergencia_verba_ausente_no_pjc():
    dados_ia = {
        "verbas_deferidas": [
            {"nome": "Férias vencidas"},
        ],
    }
    dados_pjc = PjcDadosBasicos(
        indice_trabalhista=None,
        juros_trabalhistas=None,
        nomes_verbas=["Horas Extras"],
        divisor_horas=None,
    )
    divergencias = auditar_pjc_vs_sentenca(dados_ia, dados_pjc)
    assert any("Férias" in d and "PJC" in d for d in divergencias)

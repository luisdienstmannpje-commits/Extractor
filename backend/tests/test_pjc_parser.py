"""
Testes para services.pjc_parser — PjcParser e PjcDadosBasicos.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.pjc_parser import PjcParser, PjcDadosBasicos


def _minimal_xml(indice=None, juros=None, divisor=None, verbas_nomes=None):
    parts = [
        "<?xml version='1.0' encoding='ISO-8859-1'?>",
        "<root>",
        "  <ParametrosDeAtualizacao>",
    ]
    if indice is not None:
        parts.append(f"    <indiceTrabalhista>{indice}</indiceTrabalhista>")
    if juros is not None:
        parts.append(f"    <juros>{juros}</juros>")
    parts.append("  </ParametrosDeAtualizacao>")
    if divisor is not None:
        parts.append(f"  <valorCargaHorariaPadrao>{divisor}</valorCargaHorariaPadrao>")
    if verbas_nomes:
        for n in verbas_nomes:
            parts.append("  <Verba><nome>%s</nome></Verba>" % n)
    parts.append("</root>")
    return "\n".join(parts)


class TestPjcParserFromString:
    def test_extrair_indice_trabalhista(self):
        xml = _minimal_xml(indice="IPCAE")
        parser = PjcParser.from_string(xml)
        assert parser.extrair_indice_trabalhista() == "IPCAE"

    def test_extrair_juros_trabalhistas(self):
        xml = _minimal_xml(juros="TRD_SIMPLES")
        parser = PjcParser.from_string(xml)
        assert parser.extrair_juros_trabalhistas() == "TRD_SIMPLES"

    def test_extrair_divisor_horas(self):
        xml = _minimal_xml(divisor="220.0000")
        parser = PjcParser.from_string(xml)
        assert parser.extrair_divisor_horas() == 220.0

    def test_extrair_nomes_verbas(self):
        xml = _minimal_xml(verbas_nomes=["Horas Extras", "Férias"])
        parser = PjcParser.from_string(xml)
        nomes = parser.extrair_nomes_verbas()
        assert "Horas Extras" in nomes
        assert "Férias" in nomes

    def test_extrair_dados_basicos(self):
        xml = _minimal_xml(
            indice="SELIC",
            juros="TRD_SIMPLES",
            divisor="220",
            verbas_nomes=["Salário"],
        )
        parser = PjcParser.from_string(xml)
        dados = parser.extrair_dados_basicos()
        assert isinstance(dados, PjcDadosBasicos)
        assert dados.indice_trabalhista == "SELIC"
        assert dados.juros_trabalhistas == "TRD_SIMPLES"
        assert dados.divisor_horas == 220.0
        assert "Salário" in dados.nomes_verbas

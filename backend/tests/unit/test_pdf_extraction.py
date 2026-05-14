"""
tests/unit/test_pdf_extraction.py

Testes unitários de extração de PDF sem IA.
Cobre: sentence_finder, text_processor, normalizer, verba_deduplicator.

Execute com:
    pytest tests/unit/test_pdf_extraction.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# text_processor — find_section_hybrid
# ═════════════════════════════════════════════════════════════════════════════

class TestFindSectionHybrid:

    def test_encontra_dispositivo(self):
        from services.text_processor import find_section_hybrid
        texto = "FUNDAMENTAÇÃO\n\nTexto da fundamentação.\n\nDISPOSITIVO\n\nJulgo procedente."
        pos = find_section_hybrid(texto, "dispositivo")
        assert pos >= 0
        assert "DISPOSITIVO" in texto[pos:pos+20]

    def test_retorna_negativo_se_ausente(self):
        from services.text_processor import find_section_hybrid
        texto = "Texto sem qualquer marcador de seção relevante."
        pos = find_section_hybrid(texto, "dispositivo")
        assert pos < 0

    def test_encontra_ante_o_exposto(self):
        from services.text_processor import find_section_hybrid
        texto = "ANTE O EXPOSTO, julgo procedente o pedido."
        pos = find_section_hybrid(texto, "dispositivo")
        assert pos >= 0


# ═════════════════════════════════════════════════════════════════════════════
# normalizer
# ═════════════════════════════════════════════════════════════════════════════

class TestNormalizer:

    def test_normaliza_horas_extras(self):
        from services.normalizer import normalizar
        assert normalizar("horas extras") == normalizar("HORAS EXTRAS")

    def test_normaliza_ferias(self):
        from services.normalizer import normalizar
        assert normalizar("férias proporcionais") == normalizar("Férias Proporcionais")

    def test_chave_invalida_retorna_none(self):
        from services.normalizer import normalizar
        assert normalizar("verba inexistente xyz") is None

    def test_normalizar_lista(self):
        from services.normalizer import normalizar_lista
        resultado = normalizar_lista(["horas extras", "FGTS", "aviso prévio"])
        assert len(resultado) == 3
        assert all(r is not None for r in resultado)

    def test_lista_com_invalidos(self):
        from services.normalizer import normalizar_lista
        resultado = normalizar_lista(["horas extras", "verba inexistente"])
        assert resultado[0] is not None
        assert resultado[1] == "verba inexistente"  # original mantido quando não há correspondência


# ═════════════════════════════════════════════════════════════════════════════
# verba_deduplicator
# ═════════════════════════════════════════════════════════════════════════════

class TestVerbaDeduplicator:

    def test_remove_duplicata_exata(self):
        from services.jurisprudencia.consistencia.verba_deduplicator import deduplicar_verbas
        verbas = [
            {"nome": "Horas Extras", "periodo": "2020-2023"},
            {"nome": "Horas Extras", "periodo": "2020-2023"},
        ]
        dedup, avisos = deduplicar_verbas(verbas)
        assert len(dedup) == 1
        assert len(avisos) >= 1

    def test_mantem_verbas_diferentes(self):
        from services.jurisprudencia.consistencia.verba_deduplicator import deduplicar_verbas
        verbas = [
            {"nome": "Horas Extras"},
            {"nome": "Aviso Prévio"},
            {"nome": "FGTS + Multa 40%"},
        ]
        dedup, avisos = deduplicar_verbas(verbas)
        assert len(dedup) == 3

    def test_lista_vazia(self):
        from services.jurisprudencia.consistencia.verba_deduplicator import deduplicar_verbas
        dedup, avisos = deduplicar_verbas([])
        assert dedup == []
        assert avisos == []

    def test_remove_duplicata_por_canonizacao(self):
        """Duas verbas que canonizam para a mesma chave são deduplicadas."""
        from services.jurisprudencia.consistencia.verba_deduplicator import deduplicar_verbas
        verbas = [
            {"nome": "13 Salário"},
            {"nome": "13° Salário"},
        ]
        dedup, avisos = deduplicar_verbas(verbas)
        assert len(dedup) == 1


# ═════════════════════════════════════════════════════════════════════════════
# pre_extractor — integração com texto curto (sem PDF)
# ═════════════════════════════════════════════════════════════════════════════

class TestPreExtractorComTexto:

    def test_numero_processo_cnj(self):
        from services.pre_extractor import pre_extract
        resultado = pre_extract("Processo nº 0001234-58.2023.5.04.0001 — TRT4")
        assert resultado["high"]["numero_processo"] == "0001234-58.2023.5.04.0001"

    def test_nao_lanca_excecao_em_texto_malformado(self):
        from services.pre_extractor import pre_extract
        textos_ruins = [
            None,
            "",
            "   ",
            "12345",
            "!@#$%^&*()",
            "A" * 100_000,
        ]
        for texto in textos_ruins:
            try:
                resultado = pre_extract(texto or "")
                assert isinstance(resultado, dict)
            except Exception as e:
                pytest.fail(f"pre_extract lançou exceção para texto '{texto[:20] if texto else None}': {e}")

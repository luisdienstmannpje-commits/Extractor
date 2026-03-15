"""
Testes de sanidade para classificação de instância (1GRAU/TRT/TST) e extração de data
no Título Executivo Complexo (Card 3).

Garante que:
- ROT_..._2grau.pdf seja classificado como TRT (nunca 1GRAU).
- ATOrd_..._1grau.pdf seja classificado como 1GRAU.
- Texto com "Acórdão" / "Desembargador" force TRT mesmo com nome genérico.
- Data da Autuação não seja usada; Data do Julgamento sim.
- Com 1grau + 2grau no Card 3, ambos os documentos sejam mantidos (não descartar acórdão).
"""

import pytest
from datetime import date

# Funções internas do learning_engine usadas no fluxo do Título Executivo
from services.learning_engine import (
    _classificar_tier_decisao,
    _extrair_data_documento,
    _extrair_titulo_executivo_multiplos,
)


# =============================================================================
# Classificação por nome de arquivo
# =============================================================================

class TestClassificarTierPorNome:
    """ROT e _2grau no nome devem resultar em TRT."""

    def test_rot_2grau_pdf_eh_trt(self):
        assert _classificar_tier_decisao("ROT_0010070-87.2020.5.03.0092_2grau.pdf") == "TRT"

    def test_atord_1grau_pdf_eh_1grau(self):
        assert _classificar_tier_decisao("ATOrd_xxx_1grau.pdf") == "1GRAU"

    def test_nome_com_2grau_eh_trt(self):
        assert _classificar_tier_decisao("decisao_2grau.pdf") == "TRT"

    def test_nome_com_trt_eh_trt(self):
        assert _classificar_tier_decisao("acordao_trt_3regiao.pdf") == "TRT"

    def test_nome_genérico_sem_pistas_eh_1grau(self):
        assert _classificar_tier_decisao("sentenca.pdf") == "1GRAU"


# =============================================================================
# Classificação com texto das primeiras páginas (reclassificação 1GRAU → TRT)
# =============================================================================

class TestClassificarTierComTexto:
    """Texto contendo Acórdão, TRT, Desembargador deve forçar TRT."""

    def test_texto_acordao_forca_trt(self):
        # Nome genérico; texto indica 2º grau
        assert _classificar_tier_decisao("decisao.pdf", "O ACÓRDÃO foi proferido pela Turma.") == "TRT"

    def test_texto_desembargador_forca_trt(self):
        assert _classificar_tier_decisao("doc.pdf", "Desembargador Relator: João da Silva") == "TRT"

    def test_texto_tribunal_regional_nao_forca_trt(self):
        # "Tribunal Regional" sozinho é cabeçalho PJe — não classifica como 2º grau
        assert _classificar_tier_decisao("doc.pdf", "Tribunal Regional do Trabalho da 3ª Região") == "1GRAU"

    def test_texto_recurso_ordinario_forca_trt(self):
        assert _classificar_tier_decisao("doc.pdf", "Recurso Ordinário. Recurso conhecido.") == "TRT"

    def test_texto_sem_2grau_mantem_1grau(self):
        assert _classificar_tier_decisao("sentenca.pdf", "Vistos. Julgo procedente o pedido.") == "1GRAU"


# =============================================================================
# Extração de data (evitar Data da Autuação; priorizar Data do Julgamento)
# =============================================================================

class TestExtrairDataDocumento:
    """Data do julgamento deve prevalecer sobre Data da Autuação."""

    def test_data_julgamento_prevalece_sobre_autuacao(self):
        texto = (
            "Data da Autuação: 28/01/2020\n"
            "Processo 0001234-56.2020.5.03.0092\n\n"
            "(...) DISPOSITIVO (...) "
            "Data do Julgamento: 15 de março de 2021.\n"
        )
        assert _extrair_data_documento(texto) == date(2021, 3, 15)

    def test_assinado_eletronicamente_no_final_prevalece(self):
        texto = (
            "Data da Autuação: 28/01/2020\n"
            "Assinado eletronicamente em 10/09/2021 conforme Art. 5º da Resolução CNJ 332/2020."
        )
        # O último trecho (final do doc) deve ser preferido; 2000 chars incluem isso
        assert _extrair_data_documento(texto) == date(2021, 9, 10)

    def test_belo_horizonte_data_no_final(self):
        texto = "Preliminares. (...) Belo Horizonte, 20 de outubro de 2020.\n"
        assert _extrair_data_documento(texto) == date(2020, 10, 20)

    def test_fallback_quando_nenhuma_data_valida(self):
        assert _extrair_data_documento("Sem datas aqui.") == date(1900, 1, 1)


# =============================================================================
# Integração: dois documentos (1grau + 2grau) ambos mantidos
# =============================================================================

class TestTituloExecutivoDoisDocumentos:
    """Card 3 com 1grau + 2grau deve manter os dois no contexto."""

    def test_dois_arquivos_1grau_e_trt_ambos_presentes(self):
        # Dois PDFs simulados com conteúdos DIFERENTES (hashes distintos) para não serem
        # ignorados como duplicata. Nomes forçam classificação: 1grau → 1GRAU, ROT_2grau → TRT.
        sentenca_bytes = b"%PDF-1.4 sentenca\n1 0 obj\n<<>>\nendobj\n" + b" " * 300
        acordao_bytes = b"%PDF-1.4 acordao\n1 0 obj\n<<>>\nendobj\n" + b"x" * 300
        arquivos = [
            (sentenca_bytes, "ATOrd_001_1grau.pdf"),
            (acordao_bytes, "ROT_0010070-87.2020.5.03.0092_2grau.pdf"),
        ]
        result = _extrair_titulo_executivo_multiplos(arquivos)
        instancias = result.get("instancias_detectadas") or []
        # Deve haver duas instâncias distintas: 1GRAU e TRT (acórdão não descartado como duplicata)
        assert "1GRAU" in instancias
        assert "TRT" in instancias
        assert len(instancias) == 2

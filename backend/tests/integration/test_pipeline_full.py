"""
tests/integration/test_pipeline_full.py

Testes de integração do pipeline completo.
IMPORTANTE: estes testes chamam o Gemini — requerem GEMINI_API_KEY no ambiente.
Pule com: pytest -m "not integration"

Execute com:
    pytest tests/integration/test_pipeline_full.py -v -m integration

Pré-requisitos:
    1. GEMINI_API_KEY configurado
    2. PDFs em tests/fixtures/pdfs/ com JSONs correspondentes em tests/fixtures/expected/
    3. `validado_por` nos JSONs deve ser diferente de "PENDENTE..." para rodar
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import pathlib
import re

import pytest

# Marca todos os testes deste módulo como "integration"
pytestmark = pytest.mark.integration


# ── Helpers de comparação ─────────────────────────────────────────────────────

def _normalizar_str(s: str) -> str:
    """Remove acentos e normaliza para comparação case-insensitive."""
    if not s:
        return ""
    import unicodedata
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def _valor_numerico(s: str) -> float | None:
    """Extrai valor numérico de string monetária brasileira ('R$ 3.500,00' → 3500.0)."""
    if not s:
        return None
    m = re.search(r"[\d.,]+", str(s).replace(".", "").replace(",", "."))
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def _campo_correto(campo: str, esperado, extraido) -> bool:
    """
    Compara esperado vs extraído para um campo específico.
    Regras de match:
      - Datas: exato (DD/MM/AAAA)
      - Valores monetários: ± 1%
      - Strings: case-insensitive, substring bidirecional
      - Booleanos: exato
    """
    if esperado is None:
        return True  # campo opcional não testado

    if isinstance(esperado, bool):
        return esperado == extraido

    if isinstance(esperado, list):
        # verbas_deferidas: verifica se cada nome esperado existe na lista extraída
        if not isinstance(extraido, list):
            return False
        nomes_extraidos = [_normalizar_str(v.get("nome", "") if isinstance(v, dict) else str(v)) for v in extraido]
        for item in esperado:
            nome_esp = _normalizar_str(item.get("nome", "") if isinstance(item, dict) else str(item))
            encontrado = any(
                nome_esp in ne or ne in nome_esp
                for ne in nomes_extraidos
            )
            if not encontrado:
                return False
        return True

    # Campos de data: exato
    if "data" in campo:
        return str(esperado).strip() == str(extraido or "").strip()

    # Campos monetários
    if "salario" in campo or "valor" in campo or "multa" in campo:
        v_esp = _valor_numerico(str(esperado))
        v_ext = _valor_numerico(str(extraido or ""))
        if v_esp is not None and v_ext is not None:
            return abs(v_esp - v_ext) / max(v_esp, 1) < 0.01
        return _normalizar_str(str(esperado)) in _normalizar_str(str(extraido or ""))

    # Strings genéricas: substring bidirecional case-insensitive
    e = _normalizar_str(str(esperado))
    x = _normalizar_str(str(extraido or ""))
    return e in x or x in e


# ═════════════════════════════════════════════════════════════════════════════
# Testes com PDFs reais (requerem fixtures)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestPipelineComPDFsReais:

    def test_tem_pdfs_para_testar(self, casos_de_teste):
        """Falha informativamente se não há fixtures validadas."""
        if not casos_de_teste:
            pytest.skip(
                "Nenhum PDF com expected validado encontrado em tests/fixtures/.\n"
                "Adicione PDFs + JSONs conforme tests/fixtures/README.md"
            )

    @pytest.mark.parametrize("caso", [], ids=[])  # preenchido dinamicamente abaixo
    def test_extrai_campos_obrigatorios(self, caso):
        """Para cada PDF, verifica que os campos obrigatórios são extraídos corretamente."""
        from workers.processor import process_lawsuit_pdf

        pdf_bytes = caso["pdf"].read_bytes()
        expected  = caso["expected"]

        resultado = process_lawsuit_pdf(user_id="test_user", file_bytes=pdf_bytes)
        assert resultado["status"] == "sucesso", f"Pipeline falhou: {resultado.get('msg')}"

        dados = resultado["data"]
        campos_ok   = []
        campos_fail = []

        campos_obrigatorios = [
            "numero_processo", "reclamante", "reclamada",
            "data_admissao", "data_demissao", "salario_base",
            "motivo_rescisao", "data_sentenca", "verbas_deferidas",
        ]

        for campo in campos_obrigatorios:
            if campo not in expected or expected[campo] is None:
                continue
            extraido = dados.get(campo)
            if _campo_correto(campo, expected[campo], extraido):
                campos_ok.append(campo)
            else:
                campos_fail.append({
                    "campo": campo,
                    "esperado": expected[campo],
                    "extraido": extraido,
                })

        taxa = len(campos_ok) / max(len(campos_ok) + len(campos_fail), 1) * 100
        assert taxa >= 80, (
            f"Taxa de acerto {taxa:.1f}% < 80% para {caso['pdf'].name}.\n"
            f"Falhas: {json.dumps(campos_fail, ensure_ascii=False, indent=2)}"
        )


# ── Popula parametrize dinamicamente para PDFs disponíveis ───────────────────

def pytest_generate_tests(metafunc):
    if "caso" in metafunc.fixturenames:
        fixtures_dir = pathlib.Path(__file__).parent.parent / "fixtures"
        pdfs_dir     = fixtures_dir / "pdfs"
        expected_dir = fixtures_dir / "expected"
        casos = []
        ids   = []
        if pdfs_dir.exists() and expected_dir.exists():
            for pdf in sorted(pdfs_dir.glob("*.pdf")):
                json_path = expected_dir / f"{pdf.stem}.json"
                if json_path.exists():
                    expected = json.loads(json_path.read_text(encoding="utf-8"))
                    if "PENDENTE" in str(expected.get("_meta", {}).get("validado_por", "")):
                        continue
                    casos.append({"pdf": pdf, "expected": expected})
                    ids.append(pdf.stem)
        metafunc.parametrize("caso", casos, ids=ids)


# ═════════════════════════════════════════════════════════════════════════════
# Teste de smoke — pipeline sem PDF real (valida imports e estrutura)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestPipelineSmoke:

    def test_imports_criticos(self):
        """Verifica que todos os módulos críticos importam sem erro."""
        modulos = [
            "workers.processor",
            "services.ai_client",
            "services.pre_extractor",
            "services.sentence_finder",
            "services.legal_engine.engine",
            "services.legal_engine.rule_registry",
            "services.explanation_engine",
            "services.pjc_exporter",
            "services.excel_exporter",
        ]
        import importlib
        falhas = []
        for mod in modulos:
            try:
                importlib.import_module(mod)
            except Exception as e:
                falhas.append(f"{mod}: {e}")
        assert not falhas, "Módulos com falha de import:\n" + "\n".join(falhas)

    def test_pdf_invalido_retorna_erro_gracioso(self):
        """Bytes inválidos não devem travar o pipeline."""
        from workers.processor import process_lawsuit_pdf
        resultado = process_lawsuit_pdf(user_id="test_user", file_bytes=b"nao sou um pdf")
        assert resultado["status"] == "erro"
        assert "msg" in resultado

    def test_pdf_vazio_retorna_erro_gracioso(self):
        from workers.processor import process_lawsuit_pdf
        resultado = process_lawsuit_pdf(user_id="test_user", file_bytes=b"")
        assert resultado["status"] == "erro"

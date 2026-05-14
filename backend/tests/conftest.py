"""
conftest.py — Configuração global do pytest para o Smart Extractor.

Adiciona o diretório backend/ ao sys.path para que todos os testes
possam importar diretamente como `from services.xyz import ...`
sem necessidade de instalar o pacote.
"""

import os
import sys
import json
import pathlib

import pytest

# ── sys.path ─────────────────────────────────────────────────────────────────
# Garante que `backend/` está no path independente de onde pytest é executado.
_BACKEND = pathlib.Path(__file__).parent.parent.resolve()
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ── Caminhos de fixtures ──────────────────────────────────────────────────────
FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
PDFS_DIR     = FIXTURES_DIR / "pdfs"
EXPECTED_DIR = FIXTURES_DIR / "expected"


# ── Fixtures compartilhadas ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def fixtures_dir() -> pathlib.Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def pdfs_dir() -> pathlib.Path:
    return PDFS_DIR


@pytest.fixture(scope="session")
def expected_dir() -> pathlib.Path:
    return EXPECTED_DIR


@pytest.fixture(scope="session")
def casos_de_teste() -> list[dict]:
    """
    Carrega todos os pares (pdf_path, expected_dict) da pasta de fixtures.
    Retorna lista vazia se não houver PDFs ou JSONs correspondentes.
    """
    casos = []
    if not PDFS_DIR.exists() or not EXPECTED_DIR.exists():
        return casos
    for pdf in sorted(PDFS_DIR.glob("*.pdf")):
        json_path = EXPECTED_DIR / f"{pdf.stem}.json"
        if json_path.exists():
            expected = json.loads(json_path.read_text(encoding="utf-8"))
            if expected.get("_meta", {}).get("validado_por") == "PENDENTE — substituir por PDF real validado pela perita":
                continue  # pula exemplos não validados
            casos.append({"pdf": pdf, "expected": expected})
    return casos


@pytest.fixture
def processo_minimo() -> dict:
    """Dict mínimo válido para ProcessoTrabalhista — útil em testes de regras."""
    return {
        "numero_processo": "0001234-56.2024.5.03.0001",
        "reclamante": "João da Silva",
        "reclamada": "Empresa Teste Ltda",
        "data_admissao": "01/03/2020",
        "data_demissao": "15/01/2025",
        "data_ajuizamento": "01/02/2025",
        "data_sentenca": "01/06/2025",
        "salario_base": "R$ 3.500,00",
        "motivo_rescisao": "Sem justa causa",
        "indice_correcao": "IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF",
        "juros_mora": "SELIC",
        "justica_gratuita": False,
        "verbas_deferidas": [],
    }


@pytest.fixture
def texto_sentenca_simples() -> str:
    """Texto mínimo de sentença para testes de regex — sem PDF real."""
    return """
TRIBUNAL REGIONAL DO TRABALHO DA 4ª REGIÃO
Processo nº 0001234-58.2023.5.04.0001

Reclamante: João da Silva
Reclamada: Empresa XYZ Ltda

Procedimento ordinário aplicável ao presente feito.

O reclamante foi admitido em 15/01/2020 e dispensado sem justa causa em 30/06/2023.
Data da rescisão: 30/06/2023.
Salário base de R$ 3.500,00 mensais.
Jornada de 44 horas semanais, divisor 220.

DISPOSITIVO

Defiro a justiça gratuita.
Julgo PARCIALMENTE PROCEDENTE o pedido para condenar a reclamada ao pagamento de:
- Horas Extras (50%)
- Aviso Prévio Indenizado (30 dias)
- FGTS + Multa de 40%

Correção monetária: IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF
Juros de mora pela SELIC.

Porto Alegre, 10 de março de 2024.
Assinado eletronicamente em 10/03/2024.
"""

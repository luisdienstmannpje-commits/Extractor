"""
tests/run_benchmark.py — Benchmark do pipeline de extração

Roda todos os PDFs de tests/fixtures/pdfs/ contra o pipeline atual,
compara com tests/fixtures/expected/ e gera relatório em docs/BENCHMARK_RESULTS.md.

Uso:
    cd backend
    python tests/run_benchmark.py

    # Modo silencioso (só totais)
    python tests/run_benchmark.py --quiet

    # Só mostra falhas
    python tests/run_benchmark.py --falhas-apenas

Pré-requisito: GEMINI_API_KEY no ambiente ou no .env
"""

import json
import os
import re
import sys
import pathlib
import unicodedata
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Constantes ────────────────────────────────────────────────────────────────

PDFS_DIR     = pathlib.Path(__file__).parent / "fixtures" / "pdfs"
EXPECTED_DIR = pathlib.Path(__file__).parent / "fixtures" / "expected"
RESULTS_FILE = pathlib.Path(__file__).parent.parent / "docs" / "BENCHMARK_RESULTS.md"

CAMPOS_OBRIGATORIOS = [
    "numero_processo",
    "reclamante",
    "reclamada",
    "data_admissao",
    "data_demissao",
    "salario_base",
    "motivo_rescisao",
    "data_sentenca",
    "vara_trabalho",
    "tipo_rito",
    "indice_correcao",
    "juros_mora",
    "verbas_deferidas",
]

CAMPOS_PRIORITARIOS = [
    "numero_processo", "data_admissao", "data_demissao",
    "salario_base", "motivo_rescisao", "verbas_deferidas",
]


# ── Helpers de comparação ─────────────────────────────────────────────────────

def _norm(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKD", str(s).lower()).encode("ascii", "ignore").decode().strip()


def _valor_numerico(s) -> float | None:
    if s is None:
        return None
    m = re.search(r"[\d.,]+", str(s).replace(".", "").replace(",", "."))
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def _campo_correto(campo: str, esperado, extraido) -> bool:
    if esperado is None:
        return True
    if isinstance(esperado, bool):
        return esperado == extraido
    if isinstance(esperado, list):
        if not isinstance(extraido, list):
            return False
        nomes_ext = [_norm(v.get("nome", "") if isinstance(v, dict) else str(v)) for v in extraido]
        for item in esperado:
            nome_esp = _norm(item.get("nome", "") if isinstance(item, dict) else str(item))
            if not any(nome_esp in ne or ne in nome_esp for ne in nomes_ext):
                return False
        return True
    if "data" in campo:
        return _norm(str(esperado)) == _norm(str(extraido or ""))
    if any(k in campo for k in ["salario", "valor", "multa"]):
        v_esp = _valor_numerico(esperado)
        v_ext = _valor_numerico(extraido)
        if v_esp is not None and v_ext is not None:
            return abs(v_esp - v_ext) / max(v_esp, 1) < 0.01
    e = _norm(str(esperado))
    x = _norm(str(extraido or ""))
    return e in x or x in e


# ── Pipeline ──────────────────────────────────────────────────────────────────

def rodar_pipeline(pdf_path: pathlib.Path) -> tuple[dict, str | None]:
    """Processa um PDF e retorna (dados, erro)."""
    from workers.processor import process_lawsuit_pdf
    try:
        file_bytes = pdf_path.read_bytes()
        resultado  = process_lawsuit_pdf(user_id="benchmark", file_bytes=file_bytes)
        if resultado["status"] != "sucesso":
            return {}, resultado.get("msg", "Erro desconhecido")
        return resultado["data"], None
    except Exception as e:
        return {}, str(e)


# ── Benchmark ─────────────────────────────────────────────────────────────────

def benchmark_pdf(pdf_path: pathlib.Path, expected: dict, quiet: bool = False) -> dict:
    """Roda o pipeline em um PDF e compara com o esperado."""
    if not quiet:
        print(f"\n{'─'*60}")
        print(f"  PDF: {pdf_path.name}")

    dados, erro = rodar_pipeline(pdf_path)

    if erro:
        if not quiet:
            print(f"  ❌ ERRO: {erro}")
        return {
            "pdf": pdf_path.name,
            "status": "erro",
            "erro": erro,
            "taxa_obrigatorios": 0.0,
            "taxa_prioritarios": 0.0,
            "campos_ok": [],
            "campos_fail": [],
        }

    campos_ok   = []
    campos_fail = []

    for campo in CAMPOS_OBRIGATORIOS:
        if campo not in expected or expected.get(campo) is None:
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

    total    = len(campos_ok) + len(campos_fail)
    taxa_obr = len(campos_ok) / max(total, 1) * 100

    ok_prio  = [c for c in campos_ok   if c in CAMPOS_PRIORITARIOS]
    fail_prio= [c for c in [f["campo"] for f in campos_fail] if c in CAMPOS_PRIORITARIOS]
    taxa_prio = len(ok_prio) / max(len(ok_prio) + len(fail_prio), 1) * 100

    icone = "✅" if taxa_obr >= 85 else ("⚠️" if taxa_obr >= 70 else "❌")
    if not quiet:
        print(f"  {icone} Taxa campos obrigatórios: {taxa_obr:.1f}%  |  Prioritários: {taxa_prio:.1f}%")
        if campos_fail:
            print(f"  Falhas:")
            for f in campos_fail:
                print(f"    • {f['campo']}: esperado={f['esperado']!r} | extraído={f['extraido']!r}")

    return {
        "pdf": pdf_path.name,
        "status": "ok",
        "taxa_obrigatorios": taxa_obr,
        "taxa_prioritarios": taxa_prio,
        "campos_ok": campos_ok,
        "campos_fail": campos_fail,
        "model_used": dados.get("_meta_doc_type"),
    }


# ── Relatório Markdown ────────────────────────────────────────────────────────

def gerar_relatorio(resultados: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    taxa_media = sum(r["taxa_obrigatorios"] for r in resultados) / max(len(resultados), 1)
    taxa_prio  = sum(r["taxa_prioritarios"] for r in resultados) / max(len(resultados), 1)

    linhas = [
        f"# BENCHMARK_RESULTS.md\n",
        f"> Gerado em: {now} | PDFs testados: {len(resultados)}\n",
        f"## Resumo\n",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| PDFs testados | {len(resultados)} |",
        f"| Taxa média (obrigatórios) | {taxa_media:.1f}% |",
        f"| Taxa média (prioritários) | {taxa_prio:.1f}% |",
        f"| Acima de 85% | {sum(1 for r in resultados if r['taxa_obrigatorios'] >= 85)} |",
        f"| Com erro | {sum(1 for r in resultados if r['status'] == 'erro')} |\n",
        f"## Resultados por PDF\n",
        f"| PDF | Taxa Obrig. | Taxa Prior. | Falhas |",
        f"|-----|------------|------------|--------|",
    ]

    for r in resultados:
        icone = "✅" if r["taxa_obrigatorios"] >= 85 else ("⚠️" if r["taxa_obrigatorios"] >= 70 else "❌")
        if r["status"] == "erro":
            linhas.append(f"| {r['pdf']} | ❌ ERRO | — | {r.get('erro', '')} |")
        else:
            falhas_str = ", ".join(f["campo"] for f in r["campos_fail"]) or "—"
            linhas.append(f"| {r['pdf']} | {icone} {r['taxa_obrigatorios']:.1f}% | {r['taxa_prioritarios']:.1f}% | {falhas_str} |")

    if any(r["campos_fail"] for r in resultados):
        linhas.append("\n## Falhas Detalhadas\n")
        for r in resultados:
            if not r.get("campos_fail"):
                continue
            linhas.append(f"### {r['pdf']}\n")
            linhas.append("| Campo | Esperado | Extraído |")
            linhas.append("|-------|----------|----------|")
            for f in r["campos_fail"]:
                linhas.append(f"| `{f['campo']}` | `{f['esperado']}` | `{f['extraido']}` |")
            linhas.append("")

    return "\n".join(linhas)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Benchmark do pipeline Smart Extractor")
    parser.add_argument("--quiet", action="store_true", help="Menos output")
    parser.add_argument("--falhas-apenas", action="store_true", help="Só mostra PDFs com falha")
    args = parser.parse_args()

    if not PDFS_DIR.exists():
        print(f"❌ Pasta de PDFs não encontrada: {PDFS_DIR}")
        print("   Crie tests/fixtures/pdfs/ e adicione PDFs de teste.")
        sys.exit(1)

    pdfs = sorted(PDFS_DIR.glob("*.pdf"))
    if not pdfs:
        print("⚠️  Nenhum PDF encontrado em tests/fixtures/pdfs/")
        print("   Adicione PDFs conforme tests/fixtures/README.md")
        sys.exit(0)

    print(f"\n{'═'*60}")
    print(f"  BENCHMARK — Smart Extractor")
    print(f"  {len(pdfs)} PDF(s) encontrado(s)")
    print(f"{'═'*60}")

    resultados = []
    sem_expected = []

    for pdf in pdfs:
        json_path = EXPECTED_DIR / f"{pdf.stem}.json"
        if not json_path.exists():
            print(f"  SKIP {pdf.name} — sem arquivo expected")
            sem_expected.append(pdf.name)
            continue
        expected = json.loads(json_path.read_text(encoding="utf-8"))
        if "PENDENTE" in str(expected.get("_meta", {}).get("validado_por", "")):
            print(f"  SKIP {pdf.name} — expected não validado pela perita")
            sem_expected.append(pdf.name)
            continue

        resultado = benchmark_pdf(pdf, expected, quiet=args.quiet)
        resultados.append(resultado)

    if not resultados:
        print("\n⚠️  Nenhum caso válido para testar.")
        print("   Valide os JSONs em tests/fixtures/expected/ (campo _meta.validado_por)")
        sys.exit(0)

    # ── Sumário ───────────────────────────────────────────────────────────────
    taxa_media = sum(r["taxa_obrigatorios"] for r in resultados) / len(resultados)
    print(f"\n{'═'*60}")
    print(f"  RESULTADO FINAL: {taxa_media:.1f}% (média campos obrigatórios)")
    if taxa_media >= 85:
        print("  ✅ Meta atingida (≥ 85%)")
    elif taxa_media >= 70:
        print("  ⚠️  Abaixo da meta — investigar falhas")
    else:
        print("  ❌ Crítico — pipeline com problema grave")
    print(f"{'═'*60}\n")

    # ── Salva relatório ───────────────────────────────────────────────────────
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    relatorio = gerar_relatorio(resultados)
    RESULTS_FILE.write_text(relatorio, encoding="utf-8")
    print(f"  Relatório salvo em: {RESULTS_FILE}")

    if sem_expected:
        print(f"\n  ⚠️  {len(sem_expected)} PDF(s) sem expected: {', '.join(sem_expected)}")

    # ── Exit code ─────────────────────────────────────────────────────────────
    sys.exit(0 if taxa_media >= 85 else 1)


if __name__ == "__main__":
    main()

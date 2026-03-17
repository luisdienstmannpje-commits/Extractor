"""
document_generator.py — Ghostwriter: geração de documento Word (.docx) da Manifestação

Utiliza python-docx para montar o arquivo. Estrutura:
- Cabeçalho: Processo, Partes (Reclamante x Reclamada)
- Título: MANIFESTAÇÃO AOS CÁLCULOS
- Introdução e seções (uma por discrepância), texto gerado por ai_writer (estilo manifestacao_style.md)
- Tabela comparativa (Valor Devido vs Valor Pago) — estilo Table Grid para destacar prejuízo financeiro
- Encerramento padrão: "Pede Deferimento. [Cidade], [Data]." + espaço para assinatura do Perito Assistente

Usado pelo endpoint POST /lab/gerar-docx.
"""

import io
from datetime import datetime
from typing import Any, Dict, List

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from services.ai_writer import gerar_texto_manifestacao


def _dados_processo_from_relatorio(relatorio: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai do relatório os dados obrigatórios para redação: numero_processo, partes,
    Quadro de Verbas (verbas_deferidas) e Alertas Jurídicos, para a IA redigir a peça formal.
    """
    dados = {}
    dados["numero_processo"] = relatorio.get("numero_processo") or "Sem número"
    sentenca = relatorio.get("sentenca") or {}
    campos = sentenca.get("campos_chave") or {}
    dados["reclamante"] = campos.get("reclamante") or "Reclamante"
    dados["reclamada"] = campos.get("reclamada") or "Reclamada"
    dados["vara_trabalho"] = campos.get("vara_trabalho") or ""
    dados["indice_correcao"] = campos.get("indice_correcao") or ""
    dados["juros_mora"] = campos.get("juros_mora") or ""
    verbas = sentenca.get("verbas") or []
    if not verbas and isinstance(sentenca.get("dados"), dict):
        raw = (sentenca.get("dados") or {}).get("verbas_deferidas") or []
        verbas = [v.get("nome") if isinstance(v, dict) else str(v) for v in raw if v]
    dados["verbas_deferidas"] = [v if isinstance(v, dict) else {"nome": str(v)} for v in verbas]
    dados["alertas_juridicos"] = relatorio.get("alertas_juridicos") or []
    return dados


def gerar_minuta(dados_auditoria: Dict[str, Any], estilo_mapeado: str) -> bytes:
    """
    Gera um documento Word (.docx) com a minuta da Manifestação aos Cálculos.

    Args:
        dados_auditoria: relatório do Laboratório (numero_processo, sentenca.campos_chave,
                        discrepancias, etc.).
        estilo_mapeado: conteúdo de skills/manifestacao_style.md (estilo da perita).

    Returns:
        bytes do arquivo .docx (para envio como download).

    Raises:
        Nenhuma; em caso de erro de IA ou sem discrepâncias, retorna doc com mensagem mínima.
    """
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.size = Pt(12)
    estilo.font.name = "Times New Roman"

    discrepancias = dados_auditoria.get("discrepancias") or []
    dados_proc = _dados_processo_from_relatorio(dados_auditoria)

    # ── Cabeçalho: Processo e Partes ─────────────────────────────────────────
    p_header = doc.add_paragraph()
    p_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_header.add_run("Processo: " + str(dados_proc.get("numero_processo") or ""))
    run.bold = True
    run.font.size = Pt(11)
    run.font.name = "Times New Roman"

    doc.add_paragraph()
    p_partes = doc.add_paragraph()
    p_partes.add_run("Reclamante: ").bold = True
    p_partes.add_run(str(dados_proc.get("reclamante") or "—"))
    p_partes.add_run("\nReclamada: ")
    p_partes.runs[-1].bold = True
    p_partes.add_run(str(dados_proc.get("reclamada") or "—"))

    doc.add_paragraph()

    # ── Título ───────────────────────────────────────────────────────────────
    p_titulo = doc.add_paragraph()
    p_titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = p_titulo.add_run("MANIFESTAÇÃO AOS CÁLCULOS")
    run_t.bold = True
    run_t.font.size = Pt(14)
    run_t.font.name = "Times New Roman"
    doc.add_paragraph()

    # ── Texto gerado pela IA (com ou sem discrepâncias: minuta completa ou esqueleto/template) ───────────────────────────────
    resultado_ia = gerar_texto_manifestacao(discrepancias, estilo_mapeado, dados_proc)
    erro_ia = resultado_ia.get("erro")
    introducao = resultado_ia.get("introducao") or ""
    secoes = resultado_ia.get("secoes") or []
    tabela_comparativa = resultado_ia.get("tabela_comparativa") or []
    fecho = resultado_ia.get("fecho") or ""

    if erro_ia:
        doc.add_paragraph(f"[Erro ao gerar texto com a IA: {erro_ia}].")
        if discrepancias:
            doc.add_paragraph("Resumo das discrepâncias:")
        for d in discrepancias[:15]:
            if isinstance(d, dict):
                doc.add_paragraph(
                    (d.get("juiz_disse") or "") + " | Empresa: " + (d.get("empresa_calculou") or "")
                    + " | Correção: " + (d.get("juliana_corrigiu") or ""),
                    style="List Bullet",
                )
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.getvalue()

    if introducao:
        doc.add_paragraph(introducao)

    for sec in secoes:
        titulo = (sec.get("titulo") or "").strip()
        texto = (sec.get("texto") or "").strip()
        if titulo:
            p_heading = doc.add_paragraph()
            run_h = p_heading.add_run(titulo)
            run_h.bold = True
            run_h.font.size = Pt(12)
            run_h.font.name = "Times New Roman"
        if texto:
            doc.add_paragraph(texto)

    # ── Tabela comparativa (Valor Devido vs Valor Pago) — destaque ao prejuízo financeiro ──
    if tabela_comparativa:
        doc.add_paragraph()
        p_tab_title = doc.add_paragraph()
        run_tab = p_tab_title.add_run("Demonstrativo comparativo — Valor da empresa x Valor correto")
        run_tab.bold = True
        run_tab.font.size = Pt(12)
        run_tab.font.name = "Times New Roman"
        doc.add_paragraph()

        table = doc.add_table(rows=1 + len(tabela_comparativa), cols=3)
        table.style = "Table Grid"
        header_cells = table.rows[0].cells
        header_cells[0].text = "Descrição"
        header_cells[1].text = "Valor apresentado pela empresa"
        header_cells[2].text = "Valor correto"
        for c in header_cells:
            for p in c.paragraphs:
                for r in p.runs:
                    r.bold = True
        for i, row_data in enumerate(tabela_comparativa):
            row = table.rows[i + 1].cells
            row[0].text = str(row_data.get("descricao") or "").strip() or "—"
            row[1].text = str(row_data.get("valor_empresa") or "").strip() or "—"
            row[2].text = str(row_data.get("valor_correto") or "").strip() or "—"

    # ── Fecho (redação pericial: homologação, quantum debeatur, Pede deferimento, local e data) ──
    doc.add_paragraph()
    if fecho:
        doc.add_paragraph(fecho)
    else:
        meses_pt = ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
                    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
        d = datetime.now()
        data_atual = f"{d.day} de {meses_pt[d.month - 1]} de {d.year}"
        p_encerramento = doc.add_paragraph()
        p_encerramento.add_run("Pede Deferimento.").bold = True
        p_encerramento.add_run(f"\n[Cidade], {data_atual}.")
    doc.add_paragraph()
    p_assinatura = doc.add_paragraph()
    p_assinatura.add_run("_________________________________________")
    p_assinatura.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    p_nome = doc.add_paragraph()
    p_nome.add_run("Perito Assistente").bold = True
    p_nome.alignment = WD_ALIGN_PARAGRAPH.CENTER

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

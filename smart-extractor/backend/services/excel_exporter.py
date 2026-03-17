"""
Gera arquivo .xlsx profissional para data entry da perita, a partir do dict de dados
extraídos (resultado do pipeline). Usado pelo endpoint /export-excel/{job_id}.

Layout:
  - Aba 1: "Resumo e Parecer"
  - Aba 2: "Verbas Deferidas"
  - Aba 3: "Parâmetros e Alertas"
"""
from __future__ import annotations

import json
import tempfile
from typing import Any, Dict, Iterable, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.cell.cell import MergedCell


def _flatten_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _auto_ajustar_colunas(ws, max_col_widths: Optional[Dict[int, int]] = None) -> None:
    """
    Ajuste simples de largura de colunas com base no maior conteúdo textual.
    max_col_widths permite limitar colunas muito longas (por índice 1-based).
    """
    max_col_widths = max_col_widths or {}
    for col_cells in ws.columns:
        if not col_cells:
            continue

        # Encontrar uma célula "mestre" válida (não mesclada) para obter a letra da coluna
        master_cell = None
        for c in col_cells:
            if not isinstance(c, MergedCell):
                master_cell = c
                break
        if master_cell is None:
            # Todas as células desta coluna são MergedCell — pula ajuste
            continue

        col_idx = master_cell.column
        max_length = 0
        for cell in col_cells:
            try:
                value = "" if cell.value is None else str(cell.value)
            except Exception:
                value = ""
            if value:
                max_length = max(max_length, len(value))
        if max_length == 0:
            continue

        width = max_length + 2
        limit = max_col_widths.get(col_idx)
        if limit is not None:
            width = min(width, limit)

        try:
            ws.column_dimensions[master_cell.column_letter].width = width
        except AttributeError:
            # Algumas implementações de MergedCell/Cell podem não expor column_letter;
            # neste caso, simplesmente não ajustamos esta coluna.
            continue


def _montar_texto_parecer(dados: dict) -> str:
    """
    Constrói um texto contínuo com o Parecer Técnico/Memorial Jurídico,
    combinando seção I (parcelas apuradas) e, se disponível, os critérios da seção II.
    """
    partes: List[str] = []

    intro = (dados or {}).get("parecer_intro_parcelas") or ""
    if intro:
        partes.append(intro.strip())

    itens: Iterable[Dict[str, Any]] = (dados or {}).get("parecer_parcelas_apuradas") or []
    for item in itens:
        if not isinstance(item, dict):
            continue
        letra = (item.get("alinea") or "").strip()
        titulo = (item.get("titulo") or "").strip()
        texto = (item.get("texto") or "").strip()
        linha_parts: List[str] = []
        if letra:
            linha_parts.append(f"{letra})")
        if titulo:
            linha_parts.append(titulo)
        if texto:
            linha_parts.append(texto)
        linha = " ".join(linha_parts).strip()
        if linha:
            partes.append(linha)

    # Critérios da seção II (quando presentes)
    crit_inss = (dados or {}).get("parecer_criterios_inss") or ""
    crit_irrf = (dados or {}).get("parecer_criterios_irrf") or ""
    indice = (dados or {}).get("indice_correcao") or ""
    juros = (dados or {}).get("juros_mora") or ""

    if indice or juros:
        linha_correcao = "Correção monetária / juros:"
        detalhes: List[str] = []
        if indice:
            detalhes.append(f"índice: {indice}")
        if juros:
            detalhes.append(f"juros: {juros}")
        linha_correcao += " " + "; ".join(detalhes)
        partes.append(linha_correcao)

    if crit_inss:
        partes.append(crit_inss.strip())
    if crit_irrf:
        partes.append(crit_irrf.strip())

    return "\n\n".join(partes).strip()


def exportar_excel(dados: dict, job_id: str) -> str:
    """
    Gera um .xlsx com três abas otimizadas para data entry:

    - Aba 1: \"Resumo e Parecer\"
    - Aba 2: \"Verbas Deferidas\"
    - Aba 3: \"Parâmetros e Alertas\"

    Retorna o caminho do arquivo temporário para o FileResponse enviar o download.
    """
    dados = dados or {}
    wb = Workbook()

    # ----------------------------------------------------------------------
    # Aba 1 — Resumo e Parecer
    # ----------------------------------------------------------------------
    ws_resumo = wb.active
    ws_resumo.title = "Resumo e Parecer"

    bold_font = Font(bold=True)
    wrap_center_top = Alignment(wrap_text=True, vertical="top", horizontal="left")

    # Identificação do processo
    ws_resumo["A1"] = "Identificação do Processo"
    ws_resumo["A1"].font = bold_font

    campos_proc = [
        ("Número do Processo", dados.get("numero_processo") or ""),
        ("Reclamante", dados.get("reclamante") or ""),
        ("Reclamada", dados.get("reclamada") or ""),
    ]
    row = 2
    for rotulo, valor in campos_proc:
        ws_resumo.cell(row=row, column=1, value=rotulo).font = bold_font
        ws_resumo.cell(row=row, column=2, value=_flatten_value(valor))
        row += 1

    # Dados do contrato
    ws_resumo.cell(row=row, column=1, value="Dados do Contrato").font = bold_font
    row += 1
    salario_base_val = dados.get("salario_base")
    salario_base_display = (
        "Não identificado na sentença"
        if (salario_base_val is None or salario_base_val == "")
        else _flatten_value(salario_base_val)
    )
    campos_contrato = [
        ("Data de Admissão", dados.get("data_admissao") or ""),
        ("Data de Demissão", dados.get("data_demissao") or ""),
        ("Salário base", salario_base_display),
        ("Aviso Prévio (dias)", dados.get("aviso_previo_dias") or ""),
    ]
    for rotulo, valor in campos_contrato:
        ws_resumo.cell(row=row, column=1, value=rotulo).font = bold_font
        ws_resumo.cell(row=row, column=2, value=_flatten_value(valor))
        row += 1

    # Espaço e bloco grande para memorial / parecer
    row += 1
    ws_resumo.cell(row=row, column=1, value="Memorial Jurídico / Parecer Técnico").font = bold_font
    row += 1

    texto_parecer = _montar_texto_parecer(dados)
    parecer_cell = ws_resumo.cell(row=row, column=1, value=texto_parecer or "")
    # Mesclar algumas colunas para um bloco grande de texto
    merge_end_col = 6
    ws_resumo.merge_cells(start_row=row, start_column=1, end_row=row + 15, end_column=merge_end_col)
    parecer_cell.alignment = wrap_center_top

    _auto_ajustar_colunas(ws_resumo, max_col_widths={1: 35, 2: 50})

    # ----------------------------------------------------------------------
    # Aba 2 — Verbas Deferidas
    # ----------------------------------------------------------------------
    ws_verbas = wb.create_sheet(title="Verbas Deferidas")

    headers = [
        "Nome da Verba",
        "Status",
        "Período",
        "Base de Cálculo",
        "Percentual",
        "Qtd/Divisor",
        "Integração Salarial",
        "Reflexos",
    ]
    header_fill = PatternFill(start_color="333333", end_color="333333", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    ws_verbas.append(headers)
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws_verbas.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    verbas: List[dict] = dados.get("verbas_deferidas") or []
    if not isinstance(verbas, list):
        verbas = []
    divisor_geral = dados.get("divisor_horas") or ""

    if verbas:
        for verba in verbas:
            if not isinstance(verba, dict):
                continue
            nome = verba.get("nome") or ""
            status = verba.get("status_final") or ""
            periodo = verba.get("periodo") or ""
            base_calculo = verba.get("base_calculo") or ""
            percentual = verba.get("percentual") or ""
            quantidade = verba.get("quantidade_diaria") or ""
            integracao = verba.get("integracao_salarial")
            integracao_str = ""
            if isinstance(integracao, bool):
                integracao_str = "Sim" if integracao else "Não"
            elif integracao is not None:
                integracao_str = str(integracao)

            reflexos_raw = verba.get("reflexos") or []
            if isinstance(reflexos_raw, (list, tuple)):
                reflexos = ", ".join(str(r) for r in reflexos_raw if r is not None)
            else:
                reflexos = str(reflexos_raw) if reflexos_raw is not None else ""

            qtd_divisor = ""
            if quantidade:
                qtd_divisor = str(quantidade)
            elif divisor_geral:
                qtd_divisor = str(divisor_geral)

            row_values = [
                nome,
                status,
                periodo,
                base_calculo,
                str(percentual) if percentual is not None else "",
                qtd_divisor,
                integracao_str,
                reflexos,
            ]
            ws_verbas.append(row_values)

    # Freeze panes após o cabeçalho
    ws_verbas.freeze_panes = "A2"
    # Auto-filtro no cabeçalho
    ws_verbas.auto_filter.ref = f"A1:H{ws_verbas.max_row}"

    # Wrap text para colunas de texto longo
    for col_letter in ("C", "D", "H"):
        for cell in ws_verbas[col_letter]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    _auto_ajustar_colunas(
        ws_verbas,
        max_col_widths={
            1: 35,  # Nome da verba
            3: 40,  # Período
            4: 45,  # Base de cálculo
            8: 50,  # Reflexos
        },
    )

    # ----------------------------------------------------------------------
    # Aba 3 — Parâmetros e Alertas
    # ----------------------------------------------------------------------
    ws_params = wb.create_sheet(title="Parâmetros e Alertas")

    ws_params["A1"] = "Parâmetros de Cálculo"
    ws_params["A1"].font = bold_font

    parametros = [
        ("Correção monetária", dados.get("indice_correcao") or ""),
        ("Juros de mora", dados.get("juros_mora") or ""),
        ("Contribuições Previdenciárias (INSS)", dados.get("parecer_criterios_inss") or ""),
        ("Imposto de Renda (IRRF)", dados.get("parecer_criterios_irrf") or ""),
    ]
    row = 2
    for rotulo, valor in parametros:
        ws_params.cell(row=row, column=1, value=rotulo).font = bold_font
        cell_valor = ws_params.cell(row=row, column=2, value=_flatten_value(valor))
        cell_valor.alignment = Alignment(wrap_text=True, vertical="top")
        row += 1

    row += 1
    ws_params.cell(row=row, column=1, value="Alertas Jurídicos").font = bold_font
    row += 1

    alertas: List[str] = dados.get("alertas_juridicos") or []
    for alerta in alertas:
        if not alerta:
            continue
        cell_alerta = ws_params.cell(row=row, column=1, value=str(alerta))
        cell_alerta.alignment = Alignment(wrap_text=True, vertical="top")
        row += 1

    # Bloco opcional — Auditoria de PJe-Calc (.PJC)
    divergencias_pjc: List[str] = dados.get("pjc_auditoria_divergencias") or []
    if divergencias_pjc:
        row += 1
        ws_params.cell(row=row, column=1, value="Auditoria de PJe-Calc (.PJC)").font = bold_font
        row += 1
        for div in divergencias_pjc:
            if not div:
                continue
            cell_div = ws_params.cell(row=row, column=1, value=str(div))
            cell_div.alignment = Alignment(wrap_text=True, vertical="top")
            row += 1

    _auto_ajustar_colunas(ws_params, max_col_widths={1: 80, 2: 80})

    # ----------------------------------------------------------------------
    # Persistência em arquivo temporário
    # ----------------------------------------------------------------------
    fd, path = tempfile.mkstemp(suffix=".xlsx", prefix=f"extrator_{job_id}_")
    try:
        import os

        os.close(fd)
        wb.save(path)
    except Exception:
        import os

        try:
            os.close(fd)
        except OSError:
            pass
        raise

    return path


__all__ = ["exportar_excel"]

"""
sentence_finder.py — Detecção e Recorte Cirúrgico de Sentença/Acórdão

Estratégia:
  1. Varredura completa leve (só texto nativo, sem OCR) para mapear
     assinatura digital + tipo de cada página.
  2. Identifica o documento decisório (sentença/acórdão) como o bloco
     de páginas que compartilha a data de assinatura MAIS RECENTE,
     contém DISPOSITIVO e NÃO é intimação/certidão.
  3. Retorna as páginas desse bloco (+ janela de contexto) e a capa PJe.
  4. Anexos fora do recorte: até N páginas com decisão modificativa / liquidação
     e até M com parâmetros (TRCT, registro), conciliação ou ata — com teto
     por categoria; OCR só nas páginas efetivamente extraídas.

Por que isso é mais robusto:
  - PDFs de processos PJe sempre têm assinatura digital por documento.
  - A sentença é invariavelmente o documento com data mais recente
    que contenha dispositivo (antes de certidões/despachos de execução).
  - Ignora automaticamente duplicatas dentro de intimações (mesmo texto,
    mesma data, mas prefixo "INTIMAÇÃO" na página de capa).
  - Funciona mesmo que a sentença apareça triplicada no PDF.
"""

import re
import io
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, List, Tuple, Set

import pdfplumber
import pytesseract
from config import settings

# No Windows, apontar sempre para o executável padrão (evita TesseractNotFoundError fora do PATH)
if sys.platform == "win32":
    _tesseract_exe = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.isfile(_tesseract_exe):
        pytesseract.pytesseract.tesseract_cmd = _tesseract_exe

# ---------------------------------------------------------------------------
# Padrões de detecção
# ---------------------------------------------------------------------------

# Extrai data da assinatura digital PJe
_RE_ASSINATURA = re.compile(
    r"(?i)assinado eletronicamente.*?em\s+(\d{2}/\d{2}/\d{4})",
    re.DOTALL,
)

# Detecta início de bloco decisório
_RE_DECISORIO = re.compile(
    r"(?i)("
    r"FUNDAMENTA[ÇC][AÃ]O"
    r"|RELATÓRIO"
    r"|VISTOS[,.]"
    r"|VISTOS, RELATADOS E DISCUTIDOS"
    r"|ACÓRDÃO"
    r"|EMENTA"
    r")"
)

# Detecta dispositivo (decisão final)
_RE_DISPOSITIVO = re.compile(
    r"(?i)("
    r"DISPOSITIVO"
    r"|ANTE O EXPOSTO"
    r"|ISTO POSTO"
    r"|PELO EXPOSTO"
    r"|JULGO PROCEDENTE"
    r"|JULGO PARCIALMENTE"
    r"|JULGO IMPROCEDENTE"
    r"|CONDENO A RECLAMADA"
    r"|ACORDAM"
    r")"
)

# Detecta páginas que são envelope/capa de outro documento (não decisão)
_RE_ENVELOPE = re.compile(
    r"(?i)("
    r"Fica V\. Sa\. intimado"
    r"|INTIMAÇÃO\s*$"
    r"|Certidão de Disponibilização"
    r"|Certidão de Trânsito"
    r"|CERTIDÃO\s*-\s*PJe"
    r"|Certidão de comparecimento"
    r"|Certidão de Distribuição"
    r"|ATA DE AUDIÊNCIA"
    r"|NOTIFICAÇÃO JUDICIAL"
    r"|CARTA DE PREPOSIÇÃO"
    r"|PROCURAÇÃO"
    r"|Relatório de Assinaturas"
    r"|DECLARAÇÃO DE HIPOSSUFICIÊNCIA"
    r"|Sua Petição foi finalizada"
    r"|SUMÁRIO\s*\nDocumentos"
    r")"
)

# Detecta acórdão (2ª instância)
_RE_ACORDAO = re.compile(
    r"(?i)("
    r"VISTOS, RELATADOS E DISCUTIDOS"
    r"|TURMA.*REGIONAL"
    r"|DESEMBARGADOR"
    r"|EMENTA\s*\n"
    r"|ACÓRDÃO\s*\n"
    r")"
)

# Detecta fase de liquidação (homologação de cálculos)
_RE_LIQUIDACAO = re.compile(
    r"(?i)("
    r"fase\s+de\s+liquida[çc][aã]o"
    r"|senten[çc]a\s+de\s+liquida[çc][aã]o"
    r"|homologa[çc][aã]o\s+de\s+c[aá]lculos"
    r"|homologo\s+os\s+c[aá]lculos"
    r"|c[aá]lculos\s+apresentados\s+pela\s+contadoria"
    r"|impugna[çc][aã]o\s+aos\s+c[aá]lculos"
    r"|embargos\s+[àa]\s+execu[çc][aã]o"
    r"|despacho\s+de\s+liquida[çc][aã]o"
    r"|t[ií]tulo\s+executivo\b"
    r")"
)

# Detecta embargos de declaração e trechos típicos de decisão sobre eles
_RE_EMBARGOS = re.compile(
    r"(?i)("
    r"embargos\s+de\s+declara[çc][aã]o"
    r"|acolho\s+os\s+embargos"
    r"|dou\s+provimento\s+aos\s+embargos"
    r"|erro\s+material"
    r"|omiss[aã]o\s+sanada"
    r"|efeito\s+infringente"
    r"|embargante\b"
    r")"
)

# Frases de acórdão / recurso (páginas soltas fora do bloco principal)
_RE_ACORDAO_MODIFICADOR = re.compile(
    r"(?i)("
    r"conhe[cç]er\s+do\s+recurso"
    r"|dar\s+parcial\s+provimento"
    r"|reformar\s+a\s+senten[çc]a"
    r"|negar\s+provimento\s+ao\s+recurso"
    r")"
)

# Documentos de parâmetros salariais / rescisão
_RE_PARAMETRO_BASE = re.compile(
    r"(?i)("
    r"termo\s+de\s+rescis[aã]o\s+do\s+contrato\s+de\s+trabalho"
    r"|\bTRCT\b"
    r"|homologa[çc][aã]o\s+da\s+rescis[aã]o"
    r"|ficha\s+de\s+registro\s+de\s+empregad"
    r"|livro\s+de\s+registro"
    r")"
)

# Acordo / conciliação homologada
_RE_ACORDO = re.compile(
    r"(?i)("
    r"termo\s+de\s+concilia[çc][aã]o"
    r"|acordo\s+homologado"
    r"|partes\s+conciliam"
    r")"
)

# Ata ou termo de audiência (sinal próprio; pode coincidir com is_envelope)
_RE_ATA_AUD = re.compile(
    r"(?i)("
    r"ata\s+de\s+audi[êe]ncia"
    r"|termo\s+de\s+audi[êe]ncia"
    r")"
)

# Detecta despacho/decisão de execução
_RE_DESPACHO = re.compile(
    r"(?i)("
    r"fase\s+de\s+execu[çc][aã]o"
    r"|cumpra-?se\b"
    r"|requisi[çc][aã]o\s+de\s+pagamento"
    r"|\bRPV\b"
    r"|precat[oó]rio\b"
    r"|planilha\s+de\s+d[eé]bito"
    r"|BACENJUD|SISBAJUD"
    r"|intime-?se\s+a\s+executad"
    r")"
)


# ---------------------------------------------------------------------------
# Estrutura de página analisada
# ---------------------------------------------------------------------------

@dataclass
class PageInfo:
    idx: int               # 0-based
    sig_date: Optional[str] = None   # "DD/MM/AAAA"
    is_envelope: bool = False
    has_decisorio: bool = False
    has_dispositivo: bool = False
    is_acordao: bool = False
    is_liquidacao: bool = False
    is_embargos: bool = False
    is_despacho: bool = False
    # Sinais para anexos fora do recorte principal (multi-âncora)
    is_acordao_modificador: bool = False
    is_parametro_base: bool = False
    is_acordo: bool = False
    is_ata_aud: bool = False
    text: str = ""


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _date_to_tuple(date_str: Optional[str]):
    """Converte 'DD/MM/AAAA' em (AAAA, MM, DD) para comparação."""
    if not date_str:
        return (0, 0, 0)
    try:
        d, m, y = date_str.split("/")
        return (int(y), int(m), int(d))
    except Exception:
        return (0, 0, 0)


def _extract_page_text_native(page) -> str:
    """Extração rápida de texto nativo — sem OCR."""
    return page.extract_text() or ""


def _extract_page_text_with_ocr(page, page_num: int) -> str:
    """Extração com fallback OCR quando texto nativo é insuficiente."""
    text = page.extract_text() or ""
    if len(text.strip()) < settings.OCR_CHARS_THRESHOLD:
        try:
            print(f"[FINDER] Pag {page_num}: OCR ativado ({len(text)} chars nativos)", flush=True)
            im = page.to_image(resolution=300).original
            text = pytesseract.image_to_string(im, lang="por")
        except Exception as e:
            print(f"[FINDER] OCR falhou pag {page_num}: {e}", flush=True)
    return text


def _extract_tables_as_markdown(page) -> str:
    """
    Extrai tabelas da página com pdfplumber e converte para Markdown.
    Tabelas são frequentes em sentenças (jornadas, evolução salarial, cálculos).
    Retorna string vazia se não houver tabelas.
    """
    try:
        tables = page.extract_tables()
        if not tables:
            return ""
        md_parts = []
        for table in tables:
            if not table or not table[0]:
                continue
            # Filtro: ignora tabelas com menos de 2 colunas ou 2 linhas (provavelmente ruído)
            if len(table) < 2 or len(table[0]) < 2:
                continue
            # Converte para Markdown
            rows = []
            for i, row in enumerate(table):
                cells = [str(c or "").strip().replace("\n", " ") for c in row]
                rows.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    rows.append("|" + "|".join(["---"] * len(row)) + "|")
            md_parts.append("\n".join(rows))
        return "\n\n".join(md_parts)
    except Exception:
        return ""


def _analyze_page(page, idx: int) -> PageInfo:
    """
    Análise leve (texto nativo apenas) para mapear o PDF.
    OCR só é feito nas páginas do recorte final.
    """
    text = _extract_page_text_native(page)
    info = PageInfo(idx=idx, text=text)

    # Data de assinatura digital
    m = _RE_ASSINATURA.search(text)
    if m:
        info.sig_date = m.group(1)

    # Tipo da página
    info.is_envelope   = bool(_RE_ENVELOPE.search(text))
    info.has_decisorio = bool(_RE_DECISORIO.search(text))
    info.has_dispositivo = bool(_RE_DISPOSITIVO.search(text))
    info.is_acordao    = bool(_RE_ACORDAO.search(text))
    info.is_liquidacao = bool(_RE_LIQUIDACAO.search(text))
    info.is_embargos   = bool(_RE_EMBARGOS.search(text))
    info.is_despacho   = bool(_RE_DESPACHO.search(text))
    info.is_acordao_modificador = bool(_RE_ACORDAO_MODIFICADOR.search(text))
    info.is_parametro_base = bool(_RE_PARAMETRO_BASE.search(text))
    info.is_acordo     = bool(_RE_ACORDO.search(text))
    info.is_ata_aud    = bool(_RE_ATA_AUD.search(text))

    return info


# ---------------------------------------------------------------------------
# Lógica principal de seleção do bloco decisório
# ---------------------------------------------------------------------------

def _classify_doc_type(pages: list) -> str:
    """
    Classifica o tipo de documento com base nos padrões detectados nas páginas.
    Ordem de prioridade: embargos > liquidacao > despacho > acordao > sentenca
    """
    if any(p.is_embargos for p in pages):
        return "embargos"
    if any(p.is_liquidacao for p in pages):
        return "liquidacao"
    if any(p.is_despacho for p in pages):
        return "despacho"
    if any(p.is_acordao for p in pages):
        return "acordao"
    return "sentenca"


def _find_decision_block(pages: List[PageInfo]) -> Tuple[int, int, str]:
    """
    Retorna (start_idx, end_idx, doc_type) do bloco decisório principal.

    Algoritmo:
      1. Agrupa páginas por data de assinatura.
      2. Para cada grupo (da data mais recente para a mais antiga):
         a. Ignora grupos que são só envelopes/certidões.
         b. Verifica se o grupo contém pelo menos um DISPOSITIVO.
         c. Verifica se NÃO é um grupo que começa com capa de intimação
            (intimação = envelope + cópia da decisão — queremos a original).
         d. O primeiro grupo que passar nos critérios é a decisão.
      2. Fallback estrutural: PDFs sem assinatura PJe (Word exportado, outros sistemas).
         Busca bloco por padrão DECISÓRIO + DISPOSITIVO sem depender de data.
      3. Fallback simples: janela adaptativa a partir do último DISPOSITIVO.
      4. Último recurso: texto completo.
    """
    # ── Tentativa 1: clustering por assinatura PJe ────────────────────────────
    by_date: dict[str, list[PageInfo]] = defaultdict(list)
    for p in pages:
        if p.sig_date:
            by_date[p.sig_date].append(p)

    if by_date:
        sorted_dates = sorted(by_date.keys(), key=_date_to_tuple, reverse=True)
        for date in sorted_dates:
            group = by_date[date]
            if not any(p.has_decisorio or p.has_dispositivo for p in group):
                continue
            sub_blocks = _split_contiguous(group)
            for block in sub_blocks:
                if block[0].is_envelope:
                    continue
                if not any(p.has_dispositivo for p in block):
                    continue
                n_env = sum(1 for p in block if p.is_envelope)
                if n_env > len(block) / 2:
                    continue
                start = block[0].idx
                end   = block[-1].idx
                doc_type = _classify_doc_type(block)
                print(f"[FINDER] Bloco decisorio (PJe): pags {start+1}-{end+1} "
                      f"| Data: {date} | Tipo: {doc_type}", flush=True)
                return start, end, doc_type

    # ── Tentativa 2: fallback estrutural (PDFs sem assinatura PJe) ───────────
    print("[FINDER] Sem assinatura PJe - usando fallback estrutural", flush=True)
    candidates = []
    i = 0
    while i < len(pages):
        p = pages[i]
        if (p.has_decisorio or p.has_dispositivo) and not p.is_envelope:
            block_start = i
            block_end   = i
            j = i + 1
            while j < len(pages) and j - i < 60:
                pj = pages[j]
                if pj.is_envelope and not pj.has_dispositivo:
                    break
                if pj.has_decisorio or pj.has_dispositivo or j - block_end <= 5:
                    block_end = j
                j += 1
            block = pages[block_start:block_end + 1]
            if any(pg.has_dispositivo for pg in block):
                is_ac = any(pg.is_acordao for pg in block)
                candidates.append((block_start, block_end, is_ac))
            i = block_end + 1
        else:
            i += 1

    if candidates:
        start, end, is_ac = candidates[-1]
        doc_type = "acordao" if is_ac else "sentenca"
        print(f"[FINDER] Bloco decisorio (estrutural): pags {start+1}-{end+1} | Tipo: {doc_type}", flush=True)
        return start, end, doc_type

    # ── Tentativa 3: fallback simples — último DISPOSITIVO com janela adaptativa
    print("[FINDER] Fallback simples: ultimo dispositivo encontrado", flush=True)
    for p in reversed(pages):
        if p.has_dispositivo and not p.is_envelope:
            start = p.idx
            for q in reversed(pages[:p.idx]):
                if q.has_decisorio:
                    start = q.idx
                    break
                if p.idx - q.idx > 25:
                    break
            end = min(len(pages) - 1, p.idx + 5)
            doc_type = _classify_doc_type(pages[start:end+1])
            print(f"[FINDER] Fallback simples: pags {start+1}-{end+1}", flush=True)
            return start, end, doc_type

    # ── Último recurso: texto completo ────────────────────────────────────────
    print("[FINDER] Ultimo recurso: texto completo", flush=True)
    return 0, len(pages) - 1, "completo"


def _split_contiguous(pages: List[PageInfo]) -> List[List[PageInfo]]:
    """
    Divide uma lista de páginas em sub-listas de índices contíguos.
    Ex: [pág 74, 75, 76, 85, 86] → [[74,75,76], [85,86]]
    """
    if not pages:
        return []
    blocks = []
    current = [pages[0]]
    for p in pages[1:]:
        if p.idx == current[-1].idx + 1:
            current.append(p)
        else:
            blocks.append(current)
            current = [p]
    blocks.append(current)
    return blocks


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------

# Quantas páginas de contexto capturar antes e depois do bloco
CONTEXT_BEFORE = 3   # pega início da sentença (cabeçalho, relatório sumário)
CONTEXT_AFTER  = 0   # sem margem após — o bloco já está completo pelo clustering

# Quantas páginas da capa incluir sempre (têm dados de identificação: advogado, ajuizamento)
CAPA_PAGES = 2


def get_adaptive_capa_pages(total_pages: int, doc_type: str) -> int:
    """
    Páginas iniciais (capa PJe) a incluir no recorte, conforme tipo e tamanho do PDF.

    Regras:
    - liquidação: até 8 páginas (planilhas e cabeçalhos longos);
    - PDF com mais de 100 páginas: até 5;
    - demais: 2 (comportamento histórico).
    """
    if total_pages < 1:
        return 1
    n = total_pages
    dt = (doc_type or "").strip().lower()
    if dt == "liquidacao":
        return min(8, n)
    if n > 100:
        return min(5, n)
    return min(2, n)


# Anexos fora do recorte: tetos para não estourar tokens/OCR em PDFs enormes
MAX_ANNEX_MODIFICADORA = 5
MAX_ANNEX_BASE = 3

ANNEX_HEADER_MOD = "DECISÃO MODIFICATIVA / LIQUIDAÇÃO / RECURSO"
ANNEX_HEADER_BASE = "PARÂMETROS DE CÁLCULO / ACORDO / ATA"


def _is_annex_modificadora(p: PageInfo) -> bool:
    return p.is_embargos or p.is_liquidacao or p.is_acordao_modificador


def _is_annex_base(p: PageInfo) -> bool:
    return p.is_parametro_base or p.is_acordo or p.is_ata_aud


def _select_annex_pages(
    page_infos: List[PageInfo],
    included: Set[int],
) -> List[Tuple[int, str]]:
    """
    Páginas candidatas a anexo, **fora** de `included`, em ordem crescente de índice.
    Prioriza bucket modificador; páginas que casam só base entram no segundo teto.
    """
    n_mod = 0
    n_base = 0
    out: List[Tuple[int, str]] = []
    for p in page_infos:
        idx = p.idx
        if idx in included:
            continue
        mod = _is_annex_modificadora(p)
        base = _is_annex_base(p)
        if mod and n_mod < MAX_ANNEX_MODIFICADORA:
            n_mod += 1
            out.append((idx, ANNEX_HEADER_MOD))
        elif not mod and base and n_base < MAX_ANNEX_BASE:
            n_base += 1
            out.append((idx, ANNEX_HEADER_BASE))
    return out


def _extract_page_segment_with_tables(
    pdf: pdfplumber.PDF,
    page_infos: List[PageInfo],
    idx: int,
    tables_counter: List[int],
) -> str:
    """Texto da página `idx` com OCR se necessário + tabelas em Markdown."""
    cached = page_infos[idx].text
    text = (
        cached
        if len(cached.strip()) >= settings.OCR_CHARS_THRESHOLD
        else _extract_page_text_with_ocr(pdf.pages[idx], idx + 1)
    )
    table_md = _extract_tables_as_markdown(pdf.pages[idx])
    if table_md:
        tables_counter[0] += 1
        text += f"\n\n[TABELA DA PÁGINA {idx+1}]\n{table_md}\n"
    return text


def extract_sentence_from_pdf(file_bytes: bytes) -> tuple[str, str]:
    """
    Extrai apenas o trecho de sentença/acórdão do PDF completo.

    Preservação obrigatória do cabeçalho PJe: quando o bloco decisório não começa
    na página 1, as primeiras páginas de capa (ver get_adaptive_capa_pages) são incluídas (dados de
    identificação: Data da Autuação, Valor da causa, Partes/RECORRENTE/RECORRIDO/ADVOGADO).
    Nenhuma regra neste módulo remove ou ignora os primeiros caracteres do documento.

    Retorna:
        (texto_extraido, tipo_documento)
        tipo_documento: 'sentenca' | 'acordao' | 'completo' (fallback)
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            total = len(pdf.pages)
            print(f"[FINDER] PDF com {total} paginas - analise leve...", flush=True)

            # ── Fase 1: análise leve de TODAS as páginas (sem OCR) ────────────
            page_infos: list[PageInfo] = []
            for i, page in enumerate(pdf.pages):
                info = _analyze_page(page, i)
                page_infos.append(info)

            # ── Fase 2: identificar bloco decisório ───────────────────────────
            start_idx, end_idx, doc_type = _find_decision_block(page_infos)

            # Aplica janela de contexto
            real_start = max(0, start_idx - CONTEXT_BEFORE)
            real_end   = min(total - 1, end_idx + CONTEXT_AFTER)

            n_pages = real_end - real_start + 1
            print(f"[FINDER] Recorte final: pags {real_start+1}-{real_end+1} "
                  f"({n_pages} pags de {total}) | Tipo: {doc_type}", flush=True)

            # ── Fase 3: extração com OCR apenas nas páginas necessárias ─────

            capa_n = get_adaptive_capa_pages(total, doc_type)
            # Sempre inclui capa (págs 1..capa_n) para advogado, ajuizamento etc.
            capa_indices = list(range(0, min(capa_n, real_start)))
            included_indices: Set[int] = set(capa_indices) | set(
                range(real_start, real_end + 1)
            )

            extracted = ""
            tables_found = [0]

            # Capa
            if capa_indices:
                extracted += "\n=== CAPA DO PROCESSO (dados de identificação) ===\n"
                for i in capa_indices:
                    cached = page_infos[i].text
                    text = cached if len(cached.strip()) >= settings.OCR_CHARS_THRESHOLD \
                           else _extract_page_text_with_ocr(pdf.pages[i], i + 1)
                    extracted += f"\n--- PÁGINA {i+1} ---\n{text}"
                extracted += "\n=== FIM DA CAPA ===\n"

            # Bloco da sentença (recorte principal contínuo)
            for i in range(real_start, real_end + 1):
                text = _extract_page_segment_with_tables(pdf, page_infos, i, tables_found)
                extracted += f"\n--- PÁGINA {i+1} ---\n{text}"

            # Fase 4 — anexos multi-âncora (somente fora do recorte + capa já extraída)
            annex_plan = _select_annex_pages(page_infos, included_indices)
            if annex_plan:
                print(
                    f"[FINDER] Anexos fora do recorte: {len(annex_plan)} pagina(s) "
                    f"(mod≤{MAX_ANNEX_MODIFICADORA}, base≤{MAX_ANNEX_BASE})",
                    flush=True,
                )
                extracted += (
                    "\n\n=== INÍCIO ANEXOS (PÁGINAS RELEVANTES FORA DO "
                    "RECORTE PRINCIPAL) ===\n"
                )
                for idx_pg, header_cat in annex_plan:
                    text_ax = _extract_page_segment_with_tables(
                        pdf, page_infos, idx_pg, tables_found
                    )
                    extracted += (
                        f"\n\n=== ANEXO IMPORTANTE: {header_cat} "
                        f"(PÁG {idx_pg+1}) ===\n"
                        f"--- PÁGINA {idx_pg+1} ---\n{text_ax}"
                    )
                extracted += "\n\n=== FIM ANEXOS ===\n"

            if tables_found[0]:
                print(
                    f"[FINDER] {tables_found[0]} tabela(s) extraida(s) "
                    f"e convertidas para Markdown",
                    flush=True,
                )

            chars = len(extracted)
            n_annex = len(annex_plan)
            print(
                f"[FINDER] Texto extraido: {chars} chars "
                f"(capa: {len(capa_indices)} pags + sentenca: "
                f"{real_end - real_start + 1} pags + anexos: {n_annex} pags)",
                flush=True,
            )
            return extracted, doc_type

    except Exception as e:
        print(f"[FINDER] Erro ao abrir PDF: {e}", flush=True)
        return "", "completo"
"""
sentence_finder.py — Detecção e Recorte Cirúrgico de Sentença/Acórdão

Estratégia:
  1. Varredura completa leve (só texto nativo, sem OCR) para mapear
     assinatura digital + tipo de cada página.
  2. Identifica o documento decisório (sentença/acórdão) como o bloco
     de páginas que compartilha a data de assinatura MAIS RECENTE,
     contém DISPOSITIVO e NÃO é intimação/certidão.
  3. Retorna apenas as páginas desse bloco (+ janela pequena de contexto),
     ativando OCR somente nas páginas do recorte final se necessário.

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
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

import pdfplumber
import pytesseract
from config import settings

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
    r"|homologa[çc][aã]o\s+de\s+c[aá]lculos"
    r"|c[aá]lculos\s+apresentados\s+pela\s+contadoria"
    r"|impugna[çc][aã]o\s+aos\s+c[aá]lculos"
    r"|despacho\s+de\s+liquida[çc][aã]o"
    r"|t[ií]tulo\s+executivo\b"
    r")"
)

# Detecta embargos de declaração
_RE_EMBARGOS = re.compile(
    r"(?i)("
    r"embargos\s+de\s+declara[çc][aã]o"
    r"|efeito\s+infringente"
    r"|embargante\b"
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
            print(f"[FINDER] Pág {page_num}: OCR ativado ({len(text)} chars nativos)")
            im = page.to_image(resolution=300).original
            text = pytesseract.image_to_string(im, lang="por")
        except Exception as e:
            print(f"[FINDER] OCR falhou pág {page_num}: {e}")
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
                print(f"[FINDER] Bloco decisório (PJe): págs {start+1}–{end+1} "
                      f"| Data: {date} | Tipo: {doc_type}")
                return start, end, doc_type

    # ── Tentativa 2: fallback estrutural (PDFs sem assinatura PJe) ───────────
    print("[FINDER] Sem assinatura PJe — usando fallback estrutural")
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
        print(f"[FINDER] Bloco decisório (estrutural): págs {start+1}–{end+1} | Tipo: {doc_type}")
        return start, end, doc_type

    # ── Tentativa 3: fallback simples — último DISPOSITIVO com janela adaptativa
    print("[FINDER] Fallback simples: último dispositivo encontrado")
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
            print(f"[FINDER] Fallback simples: págs {start+1}–{end+1}")
            return start, end, doc_type

    # ── Último recurso: texto completo ────────────────────────────────────────
    print("[FINDER] Último recurso: texto completo")
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


def extract_sentence_from_pdf(file_bytes: bytes) -> tuple[str, str]:
    """
    Extrai apenas o trecho de sentença/acórdão do PDF completo.

    Retorna:
        (texto_extraido, tipo_documento)
        tipo_documento: 'sentenca' | 'acordao' | 'completo' (fallback)
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            total = len(pdf.pages)
            print(f"[FINDER] PDF com {total} páginas — análise leve...")

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
            print(f"[FINDER] Recorte final: págs {real_start+1}–{real_end+1} "
                  f"({n_pages} págs de {total}) | Tipo: {doc_type}")

            # ── Fase 3: extração com OCR apenas nas páginas necessárias ─────

            # Sempre inclui capa (págs 1..CAPA_PAGES) para advogado, ajuizamento etc.
            capa_indices = list(range(0, min(CAPA_PAGES, real_start)))

            extracted = ""

            # Capa
            if capa_indices:
                extracted += "\n=== CAPA DO PROCESSO (dados de identificação) ===\n"
                for i in capa_indices:
                    cached = page_infos[i].text
                    text = cached if len(cached.strip()) >= settings.OCR_CHARS_THRESHOLD \
                           else _extract_page_text_with_ocr(pdf.pages[i], i + 1)
                    extracted += f"\n--- PÁGINA {i+1} ---\n{text}"
                extracted += "\n=== FIM DA CAPA ===\n"

            # Bloco da sentença
            tables_found = 0
            for i in range(real_start, real_end + 1):
                cached = page_infos[i].text
                text = cached if len(cached.strip()) >= settings.OCR_CHARS_THRESHOLD \
                       else _extract_page_text_with_ocr(pdf.pages[i], i + 1)

                # Extrai tabelas da página e anexa em Markdown
                table_md = _extract_tables_as_markdown(pdf.pages[i])
                if table_md:
                    tables_found += 1
                    text += f"\n\n[TABELA DA PÁGINA {i+1}]\n{table_md}\n"

                extracted += f"\n--- PÁGINA {i+1} ---\n{text}"

            if tables_found:
                print(f"[FINDER] {tables_found} tabela(s) extraída(s) e convertidas para Markdown")

            chars = len(extracted)
            print(f"[FINDER] Texto extraído: {chars} chars "
                  f"(capa: {len(capa_indices)} págs + sentença: {real_end-real_start+1} págs)")
            return extracted, doc_type

    except Exception as e:
        print(f"[FINDER] Erro ao abrir PDF: {e}")
        return "", "completo"
"""
process_timeline_extractor.py — Fatiador Cronológico e Extrator Preditivo (PJe Timeline Extractor)

Quando o usuário anexa o PDF integral do processo (1º e 2º grau) no Card 3 do Laboratório,
este módulo:
  1. Mapeia o sumário do PJe (primeiras páginas) para localizar peças por número de página.
  2. Fallback: usa âncoras textuais (regex) para identificar início/fim de cada peça.
  3. Fatia o PDF em memória e extrai texto por peça.
  4. Opcionalmente chama o Gemini para extração profunda (metadados JSON) por peça.

Integração: learning_engine chama este módulo quando há um único PDF no Card 3;
o retorno popula slots lógicos (petição, contestação, liquidação, impugnação, parecer)
e alimenta a Barra de Eficiência com peças encontradas automaticamente.

Eficiência: foco no sumário evita consumir milhares de tokens com páginas irrelevantes.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

# Chaves normalizadas das peças (compatíveis com relatório e Barra de Eficiência)
CHAVE_PETICAO = "peticao_inicial"
CHAVE_CONTESTACAO = "contestacao"
CHAVE_SENTENCA = "sentenca"
CHAVE_ACORDAO = "acordao"
CHAVE_LIQUIDACAO = "liquidacao"
CHAVE_IMPUGNACAO = "impugnacao"
CHAVE_PARECER = "parecer"

# Padrões no sumário PJe para identificar tipo de peça (nome do documento)
_SUMARIO_PATTERNS = {
    CHAVE_PETICAO: re.compile(
        r"(?i)(peti[çc][aã]o\s+inicial|reclama[çc][aã]o\s+trabalhista|inicial)",
    ),
    CHAVE_CONTESTACAO: re.compile(
        r"(?i)(contesta[çc][aã]o|defesa\s+do\s+reclamado)",
    ),
    CHAVE_SENTENCA: re.compile(
        r"(?i)(senten[çc]a|decis[aã]o\s+de\s+1[°º]?\s*grau)",
    ),
    CHAVE_ACORDAO: re.compile(
        r"(?i)(ac[oó]rd[aã]o|recurso\s+ordin[aá]rio|recurso\s+de\s+revista|trt|tst)",
    ),
    CHAVE_LIQUIDACAO: re.compile(
        r"(?i)(liquida[çc][aã]o|c[aá]lculos?\s+de\s+liquida[çc][aã]o|resumo\s+do\s+c[aá]lculo|pje[- ]?calc)",
    ),
    CHAVE_IMPUGNACAO: re.compile(
        r"(?i)(impugna[çc][aã]o\s+aos?\s+c[aá]lculos?|manifesta[çc][aã]o\s+sobre\s+os\s+c[aá]lculos?)",
    ),
    CHAVE_PARECER: re.compile(
        r"(?i)(parecer\s+t[eé]cnico|esclarecimentos\s+periciais|manifesta[çc][aã]o\s+pericial)",
    ),
}

def _verbas_pedidas_to_string(value: Any) -> str:
    """
    Converte verbas_pedidas (lista de objetos do Gemini) em uma única string
    para evitar [object Object] no frontend.
    Ex: [{'verba': 'Horas Extras', 'valor': '10.000'}] -> "Horas Extras (10.000)"
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return str(value) if value else ""
    partes = []
    for item in value:
        if isinstance(item, dict):
            verba = item.get("verba") or item.get("nome") or item.get("pedido") or ""
            valor = item.get("valor") or item.get("valor_pedido") or ""
            if valor:
                partes.append(f"{verba} ({valor})".strip())
            elif verba:
                partes.append(verba.strip())
            else:
                partes.append(str(item))
        else:
            partes.append(str(item))
    return ", ".join(partes) if partes else ""


# Âncoras de início/fim por peça (fallback quando sumário falha)
_ANCORAS = {
    CHAVE_PETICAO: {
        "inicio": re.compile(
            r"(?i)(EXCELENT[ÍI]SSIMO|RECLAMA[ÇC][AÃ]O\s+TRABALHISTA|Vara\s+do\s+Trabalho)",
        ),
        "fim": re.compile(
            r"(?i)(D[aá]-se\s+[àa]\s+causa\s+o\s+valor|Termos\s+em\s+que[,.]\s*Pede\s+deferimento|Nestes\s+termos)",
        ),
    },
    CHAVE_CONTESTACAO: {
        "inicio": re.compile(
            r"(?i)(CONTESTA[ÇC][AÃ]O|DEFESA|PRELIMINARMENTE|NO\s+M[EÉ]RITO)",
        ),
        "fim": re.compile(
            r"(?i)(Requer\s+a\s+improced[eê]ncia|Termos\s+em\s+que[,.]\s*Pede\s+deferimento)",
        ),
    },
    CHAVE_LIQUIDACAO: {
        "inicio": re.compile(
            r"(?i)(C[AÁ]LCULOS?\s+DE\s+LIQUIDA[ÇC][AÃ]O|RESUMO\s+DO\s+C[AÁ]LCULO|PJe[- ]?Calc)",
        ),
    },
    CHAVE_IMPUGNACAO: {
        "inicio": re.compile(
            r"(?i)(IMPUGNA[ÇC][AÃ]O\s+AOS?\s+C[AÁ]LCULOS?|MANIFESTA[ÇC][AÃ]O\s+SOBRE\s+OS\s+C[AÁ]LCULOS?)",
        ),
        "fim": re.compile(
            r"(?i)(Requer\s+a\s+retifica[çc][aã]o|Pede\s+deferimento)",
        ),
    },
    CHAVE_PARECER: {
        "inicio": re.compile(
            r"(?i)(PARECER\s+T[EÉ]CNICO|ESCLARECIMENTOS\s+PERICIAIS|Vem\s+respeitosamente\s+apresentar)",
        ),
    },
}


@dataclass
class SlicePeca:
    """Uma peça processual com intervalo de páginas e texto extraído."""
    chave: str
    start: int
    end: int
    texto: str = ""
    titulo_sumario: str = ""


class PjeTimelineExtractor:
    """
    Extrai o mapeamento de peças processuais de um PDF integral do PJe
    (sumário ou âncoras textuais) e permite fatiar o documento por peça.
    """

    MAX_PAGINAS_SUMARIO = 15
    MAX_CHARS_POR_PECA = 120_000  # limite por trecho para não estourar contexto

    def __init__(self, pdf_bytes: bytes):
        self.pdf_bytes = pdf_bytes
        self._pdf = None
        self._paginas_texto: List[str] = []

    def _abrir_pdf(self) -> bool:
        try:
            self._pdf = pdfplumber.open(io.BytesIO(self.pdf_bytes))
            self._paginas_texto = []
            for p in self._pdf.pages:
                self._paginas_texto.append(p.extract_text() or "")
            return True
        except Exception as e:
            print(f"[TIMELINE] Erro ao abrir PDF: {e}", flush=True)
            return False

    def _fechar_pdf(self) -> None:
        if self._pdf:
            try:
                self._pdf.close()
            except Exception:
                pass
            self._pdf = None

    def _mapear_sumario(self) -> Dict[str, Dict[str, int]]:
        """
        ETAPA 1: Lê as primeiras 15 páginas e identifica o índice (Nome da Peça, Data, Página).
        Retorna dicionário: {"peticao_inicial": {"start": 2, "end": 15}, ...}.
        """
        mapa: Dict[str, Dict[str, int]] = {}
        if not self._paginas_texto:
            return mapa

        texto_sumario = "\n".join(
            self._paginas_texto[i] for i in range(min(self.MAX_PAGINAS_SUMARIO, len(self._paginas_texto)))
        )

        # PJe: "PARA ACESSAR O SUMÁRIO" ou "SUMÁRIO" seguido de linhas com documento e página
        if "SUMÁRIO" not in texto_sumario.upper() and "SUMARIO" not in texto_sumario.upper():
            return mapa

        # Procura linhas que contenham número de página (última coluna típica: "Pág. 12" ou "12")
        # Padrão: nome do documento (qualquer texto) + data opcional + número de página
        linhas = texto_sumario.split("\n")
        for i, linha in enumerate(linhas):
            linha_limpa = linha.strip()
            if not linha_limpa or len(linha_limpa) < 5:
                continue
            # Número de página no final da linha (ex.: "...  Pág. 45" ou "  45")
            pag_match = re.search(r"\b(?:p[aá]g\.?)?\s*(\d{1,4})\s*$", linha_limpa, re.IGNORECASE)
            if not pag_match:
                continue
            num_pag = int(pag_match.group(1))
            if num_pag < 1 or num_pag > 9999:
                continue
            # Ajuste 0-based
            idx_pag = num_pag - 1
            # Identifica o tipo de peça pelo texto da linha
            for chave, pattern in _SUMARIO_PATTERNS.items():
                if pattern.search(linha_limpa):
                    if chave not in mapa:
                        mapa[chave] = {"start": idx_pag, "end": idx_pag, "titulo": linha_limpa[:80]}
                    else:
                        # Estende o bloco se já tínhamos essa peça (ex. várias entradas)
                        mapa[chave]["end"] = max(mapa[chave]["end"], idx_pag)
                    break

        # Ajustar "end" para incluir páginas até a próxima peça ou +5 páginas
        total_pags = len(self._paginas_texto)
        chaves_ordenadas = sorted(mapa.keys(), key=lambda k: mapa[k]["start"])
        for j, chave in enumerate(chaves_ordenadas):
            start = mapa[chave]["start"]
            if j + 1 < len(chaves_ordenadas):
                prox_start = mapa[chaves_ordenadas[j + 1]]["start"]
                mapa[chave]["end"] = min(mapa[chave]["end"] + 8, prox_start - 1, total_pags - 1)
            else:
                mapa[chave]["end"] = min(mapa[chave]["end"] + 8, total_pags - 1)
            mapa[chave]["end"] = max(mapa[chave]["end"], mapa[chave]["start"])

        return mapa

    def _buscar_por_ancoras(self) -> Dict[str, Dict[str, int]]:
        """
        ETAPA 2: Fallback quando o sumário falha. Varre o texto das páginas e identifica
        início (e fim quando definido) de cada peça por regex.
        """
        mapa: Dict[str, Dict[str, int]] = {}
        total = len(self._paginas_texto)
        if total == 0:
            return mapa

        for chave, ancoras in _ANCORAS.items():
            re_inicio = ancoras.get("inicio")
            re_fim = ancoras.get("fim")
            start = None
            for idx, texto in enumerate(self._paginas_texto):
                if re_inicio and re_inicio.search(texto):
                    start = idx
                    end = idx
                    if re_fim:
                        for j in range(idx + 1, min(idx + 80, total)):
                            if re_fim.search(self._paginas_texto[j]):
                                end = j
                                break
                            end = j
                    else:
                        end = min(idx + 30, total - 1)
                    mapa[chave] = {"start": start, "end": end}
                    break

        return mapa

    def _extrair_texto_intervalo(self, start: int, end: int) -> str:
        """Extrai e concatena o texto das páginas [start, end] (0-based)."""
        if not self._paginas_texto:
            return ""
        partes = []
        for i in range(max(0, start), min(end + 1, len(self._paginas_texto))):
            partes.append(f"--- PÁGINA {i+1} ---\n{self._paginas_texto[i]}")
        texto = "\n\n".join(partes)
        if len(texto) > self.MAX_CHARS_POR_PECA:
            texto = texto[: self.MAX_CHARS_POR_PECA] + "\n[... texto truncado ...]"
        return texto

    def extract_timeline(self) -> Dict[str, Any]:
        """
        Orquestra: tenta _mapear_sumario; se vazio ou insuficiente, usa _buscar_por_ancoras.
        Retorna:
          - mapa: {chave: {"start", "end"}}
          - textos: {chave: texto extraído}
          - log: lista de mensagens para [TIMELINE]
        """
        if not self._abrir_pdf():
            return {"mapa": {}, "textos": {}, "log": ["[TIMELINE] Falha ao abrir PDF."]}

        log: List[str] = []
        mapa = self._mapear_sumario()
        if not mapa:
            log.append("[TIMELINE] Sumário não encontrado ou ilegível — usando âncoras textuais.")
            mapa = self._buscar_por_ancoras()
        else:
            log.append("[TIMELINE] Sumário PJe identificado.")

        # Sentença/Acórdão: reutilizar sentence_finder se não estiver no mapa
        texto_sentenca_acordao: Optional[str] = None
        chave_sentenca_acordao: Optional[str] = None
        if CHAVE_SENTENCA not in mapa and CHAVE_ACORDAO not in mapa:
            try:
                from services.sentence_finder import extract_sentence_from_pdf
                texto_dec, doc_type = extract_sentence_from_pdf(self.pdf_bytes)
                if texto_dec.strip():
                    chave_sentenca_acordao = CHAVE_ACORDAO if doc_type == "acordao" else CHAVE_SENTENCA
                    mapa[chave_sentenca_acordao] = {"start": 0, "end": 0}
                    texto_sentenca_acordao = texto_dec
                    log.append(f"[TIMELINE] Decisão ({chave_sentenca_acordao}) identificada via sentence_finder.")
            except Exception as e:
                log.append(f"[TIMELINE] sentence_finder falhou: {e}")

        textos: Dict[str, str] = {}
        for chave, interval in mapa.items():
            start, end = interval["start"], interval["end"]
            log.append(f"[TIMELINE] {chave} encontrada nas pág. {start+1} a {end+1}.")
            if chave == chave_sentenca_acordao and texto_sentenca_acordao:
                textos[chave] = texto_sentenca_acordao
            elif start == 0 and end == 0 and chave in (CHAVE_SENTENCA, CHAVE_ACORDAO):
                try:
                    from services.sentence_finder import extract_sentence_from_pdf
                    texto_dec, _ = extract_sentence_from_pdf(self.pdf_bytes)
                    textos[chave] = texto_dec or ""
                except Exception:
                    textos[chave] = ""
            else:
                textos[chave] = self._extrair_texto_intervalo(start, end)

        self._fechar_pdf()

        return {"mapa": mapa, "textos": textos, "log": log}

    @staticmethod
    def extrair_metadados_peca(
        chave_peca: str,
        texto: str,
        ai_client_extract,
    ) -> Dict[str, Any]:
        """
        ETAPA 3: Extração profunda com Gemini para uma peça.
        Retorna JSON com metadados conforme o tipo (petição: datas e verbas_pedidas;
        contestação: teses_preliminares e teses_de_merito; impugnação: parametros_atacados, tese_impugnacao).
        """
        if not texto or len(texto.strip()) < 100:
            return {"erro": "Texto insuficiente", "dados": {}}

        instrucoes = {
            CHAVE_PETICAO: (
                "Extraia do texto da PETIÇÃO INICIAL (Reclamação Trabalhista) os seguintes campos em JSON: "
                '"data_admissao_alegada" (DD/MM/AAAA), "data_demissao_alegada", "salario_alegado", '
                '"verbas_pedidas" (lista de todos os pedidos e valores - limites da lide). '
                "Retorne apenas um objeto JSON válido, sem markdown."
            ),
            CHAVE_CONTESTACAO: (
                "Extraia do texto da CONTESTAÇÃO os campos em JSON: "
                '"teses_preliminares" (ex: prescrição bienal/quinquenal, inépcia), '
                '"teses_de_merito" (ex: cargo de confiança art. 62, justa causa, divisor 220). '
                "Retorne apenas um objeto JSON válido, sem markdown."
            ),
            CHAVE_IMPUGNACAO: (
                "Extraia do texto da IMPUGNAÇÃO AOS CÁLCULOS os campos em JSON: "
                '"parametros_atacados" (ex: juros aplicados incorretamente, erro de avos de férias), '
                '"tese_impugnacao" (argumento usado para tentar derrubar o cálculo). '
                "Retorne apenas um objeto JSON válido, sem markdown."
            ),
        }

        prompt_extra = instrucoes.get(chave_peca)
        if not prompt_extra:
            return {"dados": {}, "model_used": None}

        playbook = (
            "# Extração de metadados processuais\n\n"
            "Você é um assistente que extrai dados estruturados de peças processuais trabalhistas. "
            f"{prompt_extra}\n\n"
            "Retorne apenas um único objeto JSON válido, sem markdown ou explicação."
        )
        texto_limito = texto[:35000]
        try:
            result = ai_client_extract(texto_limito, playbook=playbook)
            data = result.get("data") or {}
            if isinstance(data, dict):
                if chave_peca == CHAVE_PETICAO and "verbas_pedidas" in data:
                    data = dict(data)
                    data["verbas_pedidas"] = _verbas_pedidas_to_string(data["verbas_pedidas"])
                return {"dados": data, "model_used": result.get("model_used"), "erro": result.get("error")}
            return {"dados": {}, "model_used": result.get("model_used"), "erro": result.get("error")}
        except Exception as e:
            return {"dados": {}, "erro": str(e)}


def extract_timeline_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Função de conveniência: instancia PjeTimelineExtractor e retorna o resultado de extract_timeline().
    """
    ext = PjeTimelineExtractor(pdf_bytes)
    return ext.extract_timeline()

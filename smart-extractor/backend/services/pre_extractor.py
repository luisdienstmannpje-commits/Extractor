"""
pre_extractor.py — Skill 7: Extração Pré-IA via Regex

Roda ANTES da chamada à IA e extrai campos usando só Python puro.
Zero tokens. Zero latência de rede.

Dois níveis de confiança:
  HIGH (≥95%): número CNJ, reclamante/reclamada, vara do trabalho (capa), data sentença, justiça gratuita, rito.
               → Sobrescreve o resultado da IA diretamente.
  MEDIUM (~80%): datas contratuais, salário, nomes de verbas (lista fechada no dispositivo),
                 período (intervalo na mesma linha) e reflexos só com gatilho explícito
                 (reflexo/incidência) no fragmento ligado à verba,
                 índices, motivo rescisão, tipo contrato, divisor, aviso prévio.
                 → Injetados como âncoras no prompt para reduzir alucinação.

Estimativa de impacto:
  - ~10–20% menos tokens de output da IA (campos HIGH não são gerados pela IA)
  - Redução de alucinação nos campos MEDIUM (IA confirma em vez de inventar)
  - numero_processo e data_sentenca sobem de ~85% para ~99% de acerto
  - Campos HIGH com alta precisão: liberam a IA para focar no que importa (verbas)

Como expandir:
  Adicione um método _extract_CAMPO(self) que chama self._set_high() ou self._set_medium().
  Ele será detectado e chamado automaticamente pelo método run().
"""

import re
from datetime import datetime, date
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# Padrões regex compilados (performance: compilados uma única vez)
# ---------------------------------------------------------------------------

# Número CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO
_RE_CNJ = re.compile(
    r"\b(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b"
)

# Data por extenso: "12 de setembro de 2025", "12/09/2025", "12-09-2025"
_RE_DATA_EXTENSO = re.compile(
    r"\b(\d{1,2})\s+de\s+"
    r"(janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|"
    r"setembro|outubro|novembro|dezembro)\s+de\s+(\d{4})\b",
    re.IGNORECASE,
)
_RE_DATA_SLASH = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_RE_DATA_HIFEN = re.compile(r"\b(\d{2}-\d{2}-\d{4})\b")

# Assinatura digital PJe (alta confiança para data_sentença)
_RE_ASSINADO = re.compile(
    r"(?i)assinado\s+(?:eletronicamente|digitalmente)(?:.*?)em\s+(\d{2}/\d{2}/\d{4})",
    re.DOTALL,
)

# Data do julgamento (acórdão / sessão) — após assinatura, antes de publicação
_RE_DATA_JULGAMENTO = re.compile(
    r"(?i)Data\s+do\s+Julgamento:\s*(\d{2}/\d{2}/\d{4})"
)

# Justiça gratuita
_RE_JG_TRUE = re.compile(
    r"(?i)(\bdefiro\b.*?\bjusti[çc]a\s+gratuita\b"
    r"|\bjusti[çc]a\s+gratuita\b.*?\bdeferida\b"
    r"|\bbenef[ií]cios\s+da\s+assistência\s+judiciária\b"
    r"|\bbenef[ií]cios\s+da\s+justi[çc]a\s+gratuita\b.*?\bdeferidos?\b"
    r"|\bgratuidade\s+da\s+justi[çc]a\b.*?\bdefiro\b"
    r"|\bdefiro\b.*?\bgratuidade\b)"
)
_RE_JG_FALSE = re.compile(
    r"(?i)(\bindeferido\b.*?\bjusti[çc]a\s+gratuita\b"
    r"|\bjusti[çc]a\s+gratuita\b.*?\bindeferida\b"
    r"|\bnão\s+faz\s+jus\s+à\s+justi[çc]a\s+gratuita\b)"
)

# Rito processual
_RE_RITO_SUMARIO = re.compile(
    r"(?i)\b(rito\s+sumar[ií]ssimo|procedimento\s+sumar[ií]ssimo|sumar[ií]ssimo)\b"
)
_RE_RITO_ORDINARIO = re.compile(
    r"(?i)\b(rito\s+ordin[aá]rio|procedimento\s+ordin[aá]rio)\b"
)

# Datas contratuais (admissão/demissão)
_RE_ADMISSAO = re.compile(
    r"(?i)(?:"
    r"admitid[oa]\s+em|"
    r"admiss[aã]o\s*:\s*|"
    r"admiss[aã]o\s+em|"
    r"data\s+da\s+admiss[aã]o[:\s]+|"
    r"data\s+de\s+admiss[aã]o[:\s]+|"
    r"a\s+partir\s+de|desde|"
    r"ingressou\s+em|contratad[oa]\s+em|início\s+do\s+contrato\s+em"
    r")"
    r"\s*(\d{2}/\d{2}/\d{4})"
)
_RE_DEMISSAO = re.compile(
    r"(?i)(?:"
    r"dispensad[oa]\s+em|"
    r"demitid[oa]\s+em|"
    r"demiss[aã]o\s*:\s*|"
    r"demiss[aã]o\s+em|"
    r"data\s+da\s+demiss[aã]o[:\s]+|"
    r"data\s+de\s+demiss[aã]o[:\s]+|"
    r"rescis[aã]o\s*:\s*|"
    r"rescis[aã]o\s+em|"
    r"data\s+da\s+rescis[aã]o[:\s]+|"
    r"data\s+de\s+rescis[aã]o[:\s]+|"
    r"saiu\s+em|desligad[oa]\s+em|término\s+do\s+contrato\s+em"
    r")"
    r"\s*(\d{2}/\d{2}/\d{4})"
)

# Salário base — diversas formas de menção (inclui rótulos de capa com dois-pontos)
_RE_SALARIO = re.compile(
    r"(?i)(?:"
    r"sal[aá]rio\s+base\s*:\s*|"
    r"sal[aá]rio\s*:\s*|"
    r"sal[aá]rio\s+(?:base\s+)?de|remunera[çc][aã]o\s+de|"
    r"percebia\s+a\s+importância\s+de|piso\s+(?:salarial\s+)?de|"
    r"sal[aá]rio\s+contratual\s+de|sal[aá]rio\s+normativo\s+de|"
    r"vencimento\s+de|sal[aá]rio\s+(?:mensal\s+)?(?:líquido\s+)?de\s+R\$)"
    r"\s*R?\$?\s*"
    r"([\d.,]+(?:\s*(?:reais|mil))?)(?:\s*(?:mensais?|brutos?|líquidos?))?",
    re.IGNORECASE,
)

# Nomes de verbas (lista fechada) — mesmo núcleo de padrões de ai_client._RE_VERBAS; só no dispositivo/decisão
_RE_VERBA_NOME_DISPOSITIVO = re.compile(
    r"(?i)\b("
    r"horas extras|adicional noturno|adicional de insalubridade"
    r"|adicional de periculosidade|f\.?g\.?t\.?s"
    r"|aviso pr[eé]vio|f[eé]rias|d[eé]cimo|13.{0,8}sal[aá]rio"
    r"|saldo de sal[aá]rio|dano moral|dano material"
    r"|multa|art\.?\s*467|art\.?\s*477|intervalo(?:\s+intrajornada)?"
    r")\b"
)

# Início do dispositivo / decisão (texto bruto; evita find_section_hybrid com texto normalizado)
_RE_TRECHO_DISPOSITIVO_TITULO = re.compile(r"(?im)^\s*DISPOSITIVO\s*(?:\n|$)")
_RE_TRECHO_ISTO_POSTO = re.compile(r"(?i)\bISTO\s+POSTO\b")
_RE_TRECHO_JULGO = re.compile(
    r"(?i)\bJULGO\s+(?:PROCEDENTE|PARCIALMENTE\s+PROCEDENTE|IMPROCEDENTE)\b"
)
_TRECHO_DECISAO_MAX_CHARS = 12_000

# Intervalo de datas na mesma linha da verba (conservador: não cruza quebras de linha)
_RE_PERIODO_DE_ATE = re.compile(
    r"(?i)(?:de|desde)\s+(\d{2}/\d{2}/\d{4})\s+(?:a|at[eé])\s+(\d{2}/\d{2}/\d{4})"
)
_RE_PERIODO_ENTRE_E = re.compile(
    r"(?i)entre\s+(\d{2}/\d{2}/\d{4})\s+e\s+(\d{2}/\d{2}/\d{4})"
)
_RE_PERIODO_NO_PERIODO = re.compile(
    r"(?i)no\s+per[ií]odo\s+(?:de\s+)?(\d{2}/\d{2}/\d{4})\s+(?:a|at[eé])\s+(\d{2}/\d{2}/\d{4})"
)
_RE_PERIODO_TRACO = re.compile(
    r"(?i)(\d{2}/\d{2}/\d{4})\s*[-–—]\s*(\d{2}/\d{2}/\d{4})"
)

# Reflexos (lista fechada) — só com gatilho explícito no fragmento ligado à verba
_RE_GATILHO_REFLEXO = re.compile(
    r"(?i)\breflexos?\b|\bincid[eê]ncia\s+(?:em|sobre|nas?|nos?)\b"
)
_RE_ALVO_REFLEXO = re.compile(
    r"(?i)\b("
    r"repouso\s+semanal\s+remunerado|rsr|dsr|d\.?s\.?r\.?"
    r"|f[eé]rias(?:\s+acrescida?s?\s+de\s+1/3)?"
    r"|d[eé]cimo\s+terceiro|13\s*[º°o]?\s*sal[aá]rio"
    r"|aviso\s+pr[eé]vio"
    r")\b"
)
_RE_CONTINUA_REFLEXO_LINHA = re.compile(r"(?i)^\s*(?:com|e)\s+reflexos?\b")

# Índice de correção monetária
_RE_IPCA = re.compile(r"(?i)\bIPCA-?E\b")
_RE_SELIC = re.compile(r"(?i)\bSELIC\b")
_RE_TR = re.compile(r"(?i)\b(atualização\s+pela\s+)?TR\b")
_RE_ADC58 = re.compile(r"(?i)\bADC\s*58\b|\bADC[-\s]*58\b")

# Juros de mora
_RE_JUROS_1 = re.compile(r"(?i)juros\s+de\s+(?:mora\s+de\s+)?1%\s+(?:ao|a\.o\.)\s+m[eê]s")
_RE_JUROS_SELIC = re.compile(r"(?i)juros\s+(?:de\s+mora\s+)?(?:pela\s+)?SELIC")
_RE_JUROS_LEGAIS = re.compile(r"(?i)juros\s+legais")

# Motivo da rescisão
_RE_RESCISAO_SJC = re.compile(
    r"(?i)\b(dispensad[oa]|dispensou|demissão|demitiu)\b.{0,60}"
    r"\bsem\s+justa\s+causa\b",
)
_RE_RESCISAO_JC = re.compile(r"(?i)\bcom\s+justa\s+causa\b")
_RE_RESCISAO_INDIRETA = re.compile(r"(?i)\brescisão\s+indireta\b")
_RE_RESCISAO_PEDIDO = re.compile(
    r"(?i)\b(pedido\s+de\s+demissão|demitiu[-\s]+se|pediu\s+demissão)\b"
)
_RE_RESCISAO_TERMINO = re.compile(
    r"(?i)\btérmino\s+do\s+(?:prazo\s+do\s+)?contrato\b"
)

# Tipo de contrato
_RE_CONTRATO_CLT = re.compile(r"(?i)\bv[íi]nculo\s+(?:de\s+)?emprego\b|\bCLT\b")
_RE_CONTRATO_PEJOTA = re.compile(
    r"(?i)(pejotiza[çc][aã]o|contrato\s+de\s+pessoa\s+jur[ií]dica|CNPJ|MEI\b)"
    r".{0,60}(reconhec|fraude|simula[çc][aã]o|disfarc)",
    re.DOTALL,
)
_RE_CONTRATO_AUTONOMO = re.compile(
    r"(?i)aut[oô]nomo\b.{0,80}reconhec"
)

# Divisor de horas extras
_RE_DIVISOR = re.compile(
    r"(?i)(?:divisor\s+(?:de\s+)?(?:horas\s+)?)(\b150\b|\b180\b|\b200\b|\b220\b)"
)
_RE_HORAS_SEMANAIS = re.compile(
    r"(?i)\b(30|35|36|40|44)h?\b\s*(?:h(?:oras?)?\s*)?(?:semanais?|por\s+semana)\b"
)

# Aviso prévio — dias
_RE_AVISO_DIAS = re.compile(
    r"(?i)aviso\s+pr[eé]vio\s+(?:indenizado\s+)?(?:de\s+)?(\d+)\s*dias?"
)

# Data de ajuizamento (MEDIUM — âncora; processor também lê Data da Autuação no cabeçalho)
_RE_AJUIZAMENTO = re.compile(
    r"(?i)(?:"
    r"data\s+da\s+autua[çc][aã]o[:\s]+|"
    r"data\s+de\s+ajuizamento[:\s]+|"
    r"protocolo(?:u(?:\s+a\s+presente)?)?\s+em\s+|"
    r"proposta\s+em\s+|"
    r"distribu[ií]da\s+em\s+"
    r")"
    r"(\d{2}/\d{2}/\d{4})"
)

# Número de processo na capa (cabeçalho do documento)
_RE_PROCESSO_CABECALHO = re.compile(
    r"(?:Processo|Autos?|N[oº°]\.?|Nº\s+do\s+Processo)[:\s]+"
    r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})",
    re.IGNORECASE,
)

# Reclamante na capa — não incluir "Reclamada" (evita troca de polo)
_RE_RECLAMANTE_CAPA = re.compile(
    r"(?im)^\s*(?:Reclamante|Autor(?:a)?|Parte\s+autora)\s*:\s*(.+)$"
)

# Reclamada na capa — não incluir rótulos de autor/reclamante
_RE_RECLAMADA_CAPA = re.compile(
    r"(?im)^\s*(?:Reclamada|Reclamado|Parte\s+reclamada)\s*:\s*(.+)$"
)

# Vara do trabalho — rótulo de capa ou linha ordinal no cabeçalho (sem rótulo, só início do texto)
_RE_VARA_CAPA_LABEL = re.compile(
    r"(?im)^\s*Vara(?:\s+do\s+Trabalho)?\s*:\s*(.+)$"
)
_RE_VARA_ORDINAL_LINE = re.compile(
    r"(?im)^\s*((?:\d+[º°ª]\s+)?Vara\s+do\s+Trabalho\s+de\s+.+)$"
)
_VARA_HEAD_CHARS = 4000

# ---------------------------------------------------------------------------
# Mapa de meses (para converter data por extenso)
# ---------------------------------------------------------------------------
_MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Mínimo de salário (para filtrar ruído)
_SALARIO_MINIMO_VIGENTE = 1_412.00


def _par_datas_dd_mm_yyyy_validas(d1: str, d2: str) -> bool:
    try:
        datetime.strptime(d1, "%d/%m/%Y")
        datetime.strptime(d2, "%d/%m/%Y")
    except ValueError:
        return False
    return True


def _periodo_intervalo_na_mesma_linha(linha: str) -> Optional[str]:
    """Retorna 'DD/MM/AAAA a DD/MM/AAAA' se houver intervalo claro na linha; senão None."""
    for rx in (
        _RE_PERIODO_DE_ATE,
        _RE_PERIODO_ENTRE_E,
        _RE_PERIODO_NO_PERIODO,
        _RE_PERIODO_TRACO,
    ):
        m = rx.search(linha)
        if not m:
            continue
        d1, d2 = m.group(1), m.group(2)
        if d1 and d2 and _par_datas_dd_mm_yyyy_validas(d1, d2):
            return f"{d1} a {d2}"
    return None


def _linha_do_span(texto: str, start: int, end: int) -> str:
    a = texto.rfind("\n", 0, start) + 1
    b = texto.find("\n", end)
    if b < 0:
        b = len(texto)
    return texto[a:b]


def _fragmento_reflexo_ligado(trecho: str, m: re.Match) -> str:
    """Linha da verba + linha seguinte só se continuação explícita (com/e reflexo...)."""
    ls = trecho.rfind("\n", 0, m.start()) + 1
    le = trecho.find("\n", m.end())
    if le < 0:
        le = len(trecho)
    linha0 = trecho[ls:le]
    frag = linha0
    stripped0 = linha0.rstrip()
    if le < len(trecho) and not stripped0.endswith((".", ";", ":")):
        rest = trecho[le + 1 :]
        ne = rest.find("\n")
        if ne < 0:
            ne = len(rest)
        linha1 = rest[:ne]
        if _RE_CONTINUA_REFLEXO_LINHA.match(linha1):
            frag = linha0 + " " + linha1.strip()
    return frag


def _rotulo_reflexo_canonico(span: str) -> str:
    low = span.strip().lower()
    compact = low.replace(".", "")
    if "repouso" in low or low == "rsr" or "dsr" in compact:
        return "DSR"
    if "férias" in low or "ferias" in low:
        if "1/3" in low or "terço" in low or "terco" in low:
            return "Férias acrescidas de 1/3"
        return "Férias"
    if (
        "décimo" in low
        or "decimo" in low
        or re.search(r"13\s*[º°o]", low)
        or re.search(r"\b13\s+sal", low)
    ):
        return "13º salário"
    if "aviso" in low and ("prévio" in low or "previo" in low):
        return "Aviso prévio"
    return span.strip()


def _reflexos_no_fragmento(fragmento: str) -> List[str]:
    if not _RE_GATILHO_REFLEXO.search(fragmento):
        return []
    out: List[str] = []
    seen: set[str] = set()
    for mx in _RE_ALVO_REFLEXO.finditer(fragmento):
        raw = (mx.group(1) or "").strip()
        if not raw:
            continue
        lab = _rotulo_reflexo_canonico(mx.group(0))
        key = lab.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(lab)
    return out


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------

class PreExtractor:
    """
    Extrai campos de alta e média confiança antes de chamar a IA.

    Uso:
        pe = PreExtractor(texto)
        resultado = pe.run()
        # resultado["high"]   → dict com campos HIGH (sobrescrevem IA)
        # resultado["medium"] → dict com campos MEDIUM (âncoras no prompt)
    """

    def __init__(self, texto: str):
        self.texto = texto
        self._high: dict   = {}
        self._medium: dict = {}

    # ── Helpers internos ─────────────────────────────────────────────────────

    def _set_high(self, campo: str, valor):
        if valor is not None:
            self._high[campo] = valor

    def _set_medium(self, campo: str, valor):
        if valor is not None:
            self._medium[campo] = valor

    @staticmethod
    def _normalizar_data(data_str: str) -> Optional[str]:
        """Garante formato DD/MM/AAAA."""
        data_str = data_str.strip()
        # Já está no formato correto
        if re.match(r"^\d{2}/\d{2}/\d{4}$", data_str):
            return data_str
        # Formato DD-MM-AAAA
        if re.match(r"^\d{2}-\d{2}-\d{4}$", data_str):
            return data_str.replace("-", "/")
        return None

    @staticmethod
    def _data_extenso_para_slash(texto_data: str) -> Optional[str]:
        m = _RE_DATA_EXTENSO.search(texto_data)
        if not m:
            return None
        dia  = int(m.group(1))
        mes  = _MESES.get(m.group(2).lower().replace("ç", "c"))
        ano  = int(m.group(3))
        if not mes:
            return None
        try:
            return datetime(ano, mes, dia).strftime("%d/%m/%Y")
        except ValueError:
            return None

    def _ultima_data_assinatura(self) -> Optional[str]:
        """Última data de 'Assinado eletronicamente em DD/MM/AAAA' — data da sentença."""
        matches = list(_RE_ASSINADO.finditer(self.texto))
        if not matches:
            return None
        datas = []
        for m in matches:
            raw = m.group(1)
            norm = self._normalizar_data(raw)
            if norm:
                try:
                    d, mo, y = norm.split("/")
                    datas.append((datetime(int(y), int(mo), int(d)), norm))
                except Exception:
                    pass
        if not datas:
            return None
        datas.sort(key=lambda x: x[0], reverse=True)
        return datas[0][1]

    # ── Extratores HIGH ──────────────────────────────────────────────────────

    def _extract_numero_processo(self):
        """Número CNJ — altíssima precisão via regex rígido."""
        # Prioridade: cabeçalho explícito
        m = _RE_PROCESSO_CABECALHO.search(self.texto)
        if m:
            self._set_high("numero_processo", m.group(1))
            return
        # Fallback: primeira ocorrência de padrão CNJ no texto
        m = _RE_CNJ.search(self.texto)
        if m:
            self._set_high("numero_processo", m.group(1))

    def _extract_reclamante(self):
        """Nome do reclamante — rótulos típicos de capa (Reclamante, Autor/Autora, Parte autora)."""
        m = _RE_RECLAMANTE_CAPA.search(self.texto)
        if not m:
            return
        nome = (m.group(1) or "").strip()
        if not nome:
            return
        if re.match(
            r"^(?:N/?A|Não\s+informado|S\.?N\.?|[-–—]+|\.{3,})$",
            nome,
            re.IGNORECASE,
        ):
            return
        self._set_high("reclamante", nome)

    def _extract_reclamada(self):
        """Nome da reclamada — rótulos típicos de capa (Reclamada, Reclamado, Parte reclamada)."""
        m = _RE_RECLAMADA_CAPA.search(self.texto)
        if not m:
            return
        nome = (m.group(1) or "").strip()
        if not nome:
            return
        if re.match(
            r"^(?:N/?A|Não\s+informado|S\.?N\.?|[-–—]+|\.{3,})$",
            nome,
            re.IGNORECASE,
        ):
            return
        self._set_high("reclamada", nome)

    @staticmethod
    def _valor_vara_plausivel(texto: str) -> bool:
        """Exige menção explícita a vara + trabalho (evita TRT-only ou rótulos genéricos)."""
        t = (texto or "").strip().lower()
        if len(t) < 8:
            return False
        return "vara" in t and "trabalho" in t

    def _extract_vara_trabalho(self):
        """Identificação da vara — PJe: 'Vara:' / 'Vara do Trabalho:' ou linha 'Nª Vara do Trabalho de ...' no cabeçalho."""
        m = _RE_VARA_CAPA_LABEL.search(self.texto)
        raw: Optional[str] = None
        if m:
            raw = (m.group(1) or "").strip()
        else:
            head = self.texto[:_VARA_HEAD_CHARS]
            m2 = _RE_VARA_ORDINAL_LINE.search(head)
            if m2:
                raw = (m2.group(1) or "").strip()
        if not raw:
            return
        if re.match(
            r"^(?:N/?A|Não\s+informado|S\.?N\.?|[-–—]+|\.{3,})$",
            raw,
            re.IGNORECASE,
        ):
            return
        if not self._valor_vara_plausivel(raw):
            return
        self._set_high("vara_trabalho", raw)

    def _extract_data_sentenca(self):
        """Data da sentença — assinatura PJe (mais recente), Data do Julgamento, Publicado em, extenso."""
        # Prioridade máxima: assinatura digital (mais recente)
        data_ass = self._ultima_data_assinatura()
        if data_ass:
            self._set_high("data_sentenca", data_ass)
            return
        m = _RE_DATA_JULGAMENTO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_high("data_sentenca", norm)
                return
        # Fallback: "Publicado em DD/MM/AAAA"
        m = re.search(
            r"(?i)publicad[oa]\s+em\s+(\d{2}/\d{2}/\d{4})", self.texto
        )
        if m:
            self._set_high("data_sentenca", m.group(1))
            return
        # Fallback: data por extenso perto de marcadores de sentença
        for trecho in re.finditer(
            r"(?i)(?:Cidade|[A-ZÀÁÉÍÓÚ][a-zàáéíóú]+),"
            r"\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}",
            self.texto,
        ):
            data = self._data_extenso_para_slash(trecho.group())
            if data:
                self._set_high("data_sentenca", data)
                return

    def _extract_justica_gratuita(self):
        """Booleano — se justiça gratuita foi deferida."""
        # Primeiro checa negação (mais específico)
        if _RE_JG_FALSE.search(self.texto):
            self._set_high("justica_gratuita", False)
            return
        if _RE_JG_TRUE.search(self.texto):
            self._set_high("justica_gratuita", True)
            return

    def _extract_tipo_rito(self):
        """Rito ordinário ou sumaríssimo."""
        if _RE_RITO_SUMARIO.search(self.texto):
            self._set_high("tipo_rito", "Sumaríssimo")
        elif _RE_RITO_ORDINARIO.search(self.texto):
            self._set_high("tipo_rito", "Ordinário")

    # ── Extratores MEDIUM ────────────────────────────────────────────────────

    def _extract_data_ajuizamento(self):
        """Data de ajuizamento / autuação PJe — primeira ocorrência; saída DD/MM/AAAA."""
        m = _RE_AJUIZAMENTO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_ajuizamento", norm)

    def _extract_data_admissao(self):
        """Data de admissão — primeira ocorrência; saída DD/MM/AAAA (MEDIUM)."""
        m = _RE_ADMISSAO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_admissao", norm)

    def _extract_data_demissao(self):
        """Data de demissão / rescisão — primeira ocorrência; saída DD/MM/AAAA (MEDIUM)."""
        m = _RE_DEMISSAO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_demissao", norm)

    def _extract_salario_base(self):
        """Extrai salário (MEDIUM) — moda entre menções plausíveis; inclui `Salário base:` / `Salário:`."""
        matches = list(_RE_SALARIO.finditer(self.texto))
        candidatos = []
        for m in matches:
            raw = m.group(1).strip()
            # Normaliza para número
            numero_str = re.sub(r"[^\d,.]", "", raw).replace(".", "").replace(",", ".")
            try:
                valor = float(numero_str)
            except ValueError:
                continue
            # Filtro de plausibilidade: entre R$ 800 e R$ 80.000
            if 800 <= valor <= 80_000:
                candidatos.append((valor, raw, m.start()))

        if not candidatos:
            return

        # Prioriza o valor mais mencionado (moda)
        from collections import Counter
        contagem = Counter(str(round(v, 2)) for v, _, _ in candidatos)
        valor_mais_freq = float(max(contagem, key=contagem.get))

        # Formata como valor monetário BR
        salario_fmt = f"R$ {valor_mais_freq:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self._set_medium("salario_base", salario_fmt)

    def _trecho_dispositivo_ou_decisao(self) -> Optional[str]:
        """Recorte aproximado do dispositivo ou linha de decisão (texto original)."""
        t = self.texto
        m = _RE_TRECHO_DISPOSITIVO_TITULO.search(t)
        if m:
            return t[m.start() : m.start() + _TRECHO_DECISAO_MAX_CHARS]
        m = _RE_TRECHO_ISTO_POSTO.search(t)
        if m:
            return t[m.start() : m.start() + _TRECHO_DECISAO_MAX_CHARS]
        m = _RE_TRECHO_JULGO.search(t)
        if m:
            return t[m.start() : m.start() + _TRECHO_DECISAO_MAX_CHARS]
        return None

    def _extract_verbas_deferidas_nomes(self):
        """Nomes de verbas (lista fechada) só no dispositivo / trecho de decisão — MEDIUM."""
        trecho = self._trecho_dispositivo_ou_decisao()
        if not trecho:
            return
        nomes: list[str] = []
        itens: list[dict[str, Any]] = []
        visto: set[str] = set()
        for m in _RE_VERBA_NOME_DISPOSITIVO.finditer(trecho):
            n = (m.group(1) or "").strip()
            if not n:
                continue
            chave = n.casefold()
            if chave in visto:
                continue
            visto.add(chave)
            nomes.append(n)
            linha = _linha_do_span(trecho, m.start(), m.end())
            periodo = _periodo_intervalo_na_mesma_linha(linha)
            frag_ref = _fragmento_reflexo_ligado(trecho, m)
            reflexos = _reflexos_no_fragmento(frag_ref)
            item: dict[str, Any] = {"nome": n}
            if periodo:
                item["periodo"] = periodo
            if reflexos:
                item["reflexos"] = reflexos
            itens.append(item)
        if nomes:
            self._set_medium("verbas_deferidas_nomes", nomes)
            self._set_medium("verbas_deferidas_itens", itens)

    def _extract_indice_correcao(self):
        """Detecta IPCA-E, SELIC, TR — prioriza ADC 58."""
        if _RE_ADC58.search(self.texto):
            self._set_medium(
                "indice_correcao",
                "IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF"
            )
        elif _RE_IPCA.search(self.texto) and _RE_SELIC.search(self.texto):
            self._set_medium(
                "indice_correcao",
                "IPCA-E (pré-judicial) / SELIC (pós-ajuizamento)"
            )
        elif _RE_IPCA.search(self.texto):
            self._set_medium("indice_correcao", "IPCA-E")
        elif _RE_SELIC.search(self.texto):
            self._set_medium("indice_correcao", "SELIC")
        elif _RE_TR.search(self.texto):
            self._set_medium("indice_correcao", "TR")

    def _extract_juros_mora(self):
        if _RE_JUROS_SELIC.search(self.texto):
            self._set_medium("juros_mora", "SELIC")
        elif _RE_JUROS_1.search(self.texto):
            self._set_medium("juros_mora", "1% ao mês")
        elif _RE_JUROS_LEGAIS.search(self.texto):
            self._set_medium("juros_mora", "Juros legais")

    def _extract_motivo_rescisao(self):
        if _RE_RESCISAO_INDIRETA.search(self.texto):
            self._set_medium("motivo_rescisao", "Rescisão indireta")
        elif _RE_RESCISAO_SJC.search(self.texto):
            self._set_medium("motivo_rescisao", "Sem justa causa")
        elif _RE_RESCISAO_JC.search(self.texto):
            self._set_medium("motivo_rescisao", "Com justa causa")
        elif _RE_RESCISAO_PEDIDO.search(self.texto):
            self._set_medium("motivo_rescisao", "Pedido de demissão")
        elif _RE_RESCISAO_TERMINO.search(self.texto):
            self._set_medium("motivo_rescisao", "Término de contrato")

    def _extract_tipo_contrato(self):
        if _RE_CONTRATO_PEJOTA.search(self.texto):
            self._set_medium("tipo_contrato", "Pejotização reconhecida")
        elif _RE_CONTRATO_AUTONOMO.search(self.texto):
            self._set_medium("tipo_contrato", "Autônomo reconhecido")
        elif _RE_CONTRATO_CLT.search(self.texto):
            self._set_medium("tipo_contrato", "CLT")

    def _extract_divisor_horas(self):
        """Divisor de horas extras — regex direto ou inferência da jornada."""
        m = _RE_DIVISOR.search(self.texto)
        if m:
            self._set_medium("divisor_horas", m.group(1))
            return
        # Inferência pela jornada semanal
        m = _RE_HORAS_SEMANAIS.search(self.texto)
        if m:
            h_sem = int(m.group(1))
            mapa = {30: "150", 35: "175", 36: "180", 40: "200", 44: "220"}
            div = mapa.get(h_sem)
            if div:
                self._set_medium("divisor_horas", div)

    def _extract_aviso_previo_dias(self):
        m = _RE_AVISO_DIAS.search(self.texto)
        if m:
            dias = int(m.group(1))
            if 20 <= dias <= 90:  # plausibilidade
                self._set_medium("aviso_previo_dias", f"{dias} dias")

    # ── Interface pública ─────────────────────────────────────────────────────

    def run(self) -> dict:
        """
        Executa todos os extratores e retorna:
        {
            "high":   {campo: valor, ...},   # sobrescreve IA
            "medium": {campo: valor, ...},   # âncoras no prompt
        }
        Qualquer extrator que falhe é silenciado — robustez > completude.
        """
        # HIGH
        high_extractors = [
            self._extract_numero_processo,
            self._extract_reclamante,
            self._extract_reclamada,
            self._extract_vara_trabalho,
            self._extract_data_sentenca,
            self._extract_justica_gratuita,
            self._extract_tipo_rito,
        ]
        for fn in high_extractors:
            try:
                fn()
            except Exception as e:
                print(f"[PRE-EXTRACT] Erro em {fn.__name__}: {e}")

        # MEDIUM
        medium_extractors = [
            self._extract_data_ajuizamento,
            self._extract_data_admissao,
            self._extract_data_demissao,
            self._extract_salario_base,
            self._extract_verbas_deferidas_nomes,
            self._extract_indice_correcao,
            self._extract_juros_mora,
            self._extract_motivo_rescisao,
            self._extract_tipo_contrato,
            self._extract_divisor_horas,
            self._extract_aviso_previo_dias,
        ]
        for fn in medium_extractors:
            try:
                fn()
            except Exception as e:
                print(f"[PRE-EXTRACT] Erro em {fn.__name__}: {e}")

        n_high   = len(self._high)
        n_medium = len(self._medium)
        print(
            f"[PRE-EXTRACT] {n_high + n_medium} campos via regex "
            f"(high={n_high}, medium={n_medium})"
        )
        if self._high:
            print(f"[PRE-EXTRACT] HIGH: {list(self._high.keys())}")
        if self._medium:
            print(f"[PRE-EXTRACT] MEDIUM: {list(self._medium.keys())}")

        return {"high": self._high, "medium": self._medium}


def pre_extract(texto: str) -> dict:
    """Função de conveniência — instancia e executa o PreExtractor."""
    return PreExtractor(texto).run()

# ---------------------------------------------------------------------------
# Função auxiliar para ai_client.py
# ---------------------------------------------------------------------------

def build_anchor_section(medium_fields: dict) -> str:
    """
    Converte os campos MEDIUM do pre_extractor em bloco de âncoras
    para injeção no prompt da IA.

    O objetivo é reduzir alucinação: a IA recebe os valores já extraídos
    via regex como referência, confirmando-os em vez de inventar.

    Args:
        medium_fields: dict com campos de média confiança (saída de PreExtractor.run()["medium"])

    Returns:
        String formatada para inserção no prompt, ou "" se não houver campos.
    """
    if not medium_fields:
        return ""

    # Mapa de campo → rótulo legível para o prompt
    ROTULOS = {
        "data_admissao":     "Data de admissão",
        "data_demissao":     "Data de demissão",
        "data_ajuizamento":  "Data de ajuizamento",
        "salario_base":      "Salário base",
        "indice_correcao":   "Índice de correção monetária",
        "juros_mora":        "Juros de mora",
        "motivo_rescisao":   "Motivo da rescisão",
        "tipo_contrato":     "Tipo de contrato",
        "divisor_horas":     "Divisor de horas extras",
        "aviso_previo_dias": "Aviso prévio (dias)",
    }

    linhas = [
        "VALORES PRÉ-EXTRAÍDOS (média confiança — confirme no texto antes de usar):",
    ]
    for campo, valor in medium_fields.items():
        if campo == "verbas_deferidas_nomes":
            if "verbas_deferidas_itens" in medium_fields:
                continue
            if not isinstance(valor, list) or not valor:
                continue
            linhas.append("  • Verbas (padrões detectados no dispositivo/decisão):")
            for nome in valor:
                linhas.append(f"      - {nome}")
            continue
        if campo == "verbas_deferidas_itens":
            if not isinstance(valor, list) or not valor:
                continue
            linhas.append("  • Verbas (padrões detectados no dispositivo/decisão):")
            for it in valor:
                if not isinstance(it, dict):
                    continue
                nome = (it.get("nome") or "").strip()
                if not nome:
                    continue
                per = (it.get("periodo") or "").strip()
                refs = it.get("reflexos")
                extras: list[str] = []
                if per:
                    extras.append(f"período: {per}")
                if isinstance(refs, list) and refs:
                    extras.append(f"reflexos: {', '.join(str(x) for x in refs)}")
                if extras:
                    linhas.append(f"      - {nome} — " + " — ".join(extras))
                else:
                    linhas.append(f"      - {nome}")
            continue
        rotulo = ROTULOS.get(campo, campo)
        linhas.append(f"  • {rotulo}: {valor}")

    linhas.append(
        "Se o texto confirmar estes valores, use-os. "
        "Se contradizer, prefira o que o texto diz explicitamente."
    )
    return "\n".join(linhas)
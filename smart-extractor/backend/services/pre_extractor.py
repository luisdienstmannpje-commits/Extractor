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
import unicodedata
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

_RE_TRANSITO_JULGADO = re.compile(
    r"(?i)(?:"
    r"(?:o\s+processo\s+)?transitou\s+em\s+julgado\s+em|"
    r"tr[âa]nsito\s+em\s+julgado\s*:?|"
    r"data\s+do\s+tr[âa]nsito\s+em\s+julgado\s*:?"
    r")\s*(\d{2}/\d{2}/\d{4})"
)
_RE_INTIMACAO_CALCULOS = re.compile(
    r"(?is)(?:"
    r"(?:partes\s+)?(?:foram\s+)?intimad[ao]s?\s+em\s+(\d{2}/\d{2}/\d{4}).{0,120}\b(?:c[aá]lculos?|liquida[çc][aã]o)\b|"
    r"intimem-se\s+as\s+partes\s+em\s+(\d{2}/\d{2}/\d{4}).{0,120}\b(?:c[aá]lculos?|liquida[çc][aã]o)\b|"
    r"intima[çc][aã]o\s+para\s+(?:apresenta[çc][aã]o\s+de\s+)?c[aá]lculos?\s+em\s+(\d{2}/\d{2}/\d{4})"
    r")"
)# Justiça gratuita
_RE_JG_TRUE = re.compile(
    r"(?i)(\bdefiro\b.*?\bjusti[çc]a\s+gratuita\b"
    r"|\bjusti[çc]a\s+gratuita\b.*?\bdeferida\b"
    r"|\bbenef[ií]cios\s+da\s+assistência\s+judiciária\b"
    r"|\bbenef[ií]cios\s+da\s+justi[çc]a\s+gratuita\b.*?\bdeferidos?\b"
    r"|\bgratuidade\s+da\s+justi[çc]a\b.*?\bdefiro\b"
    r"|\bdefiro\b.*?\bgratuidade\b)"
)
_RE_PRAZO_CALCULOS = re.compile(
    r"(?is)(?:"
    r"\b(?:c[aá]lculos?|liquida[çc][aã]o)\b.{0,120}\bprazo\s+de\s+(\d{1,2}|oito)\s+dias?\b|"
    r"\bprazo\s+de\s+(\d{1,2}|oito)\s+dias?\b.{0,120}\b(?:c[aá]lculos?|liquida[çc][aã]o)\b"
    r")"
)
_RE_PRAZO_OBRIGACAO_DIAS = re.compile(
    r"(?i)\b(?:no\s+)?prazo\s+de\s+(\d{1,3}|oito)\s+dias?\b"
)
_RE_MULTA_DIARIA_OBRIGACAO = re.compile(
    r"(?is)(?:"
    r"multa\s+di[aá]ria\s+de\s*(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+(?:,\d{2})?)|"
    r"astreintes\s+de\s*(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+(?:,\d{2})?)\s*(?:por\s+dia|di[aá]rios?)?|"
    r"multa\s+de\s*(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+(?:,\d{2})?)\s*(?:por\s+dia|di[aá]rios?)"
    r")"
)
_RE_MULTA_LIMITE_OBRIGACAO = re.compile(
    r"(?is)(?:"
    r"limitad[ao]\s+a\s*(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+(?:,\d{2})?)|"
    r"at[eé]\s+o\s+limite\s+de\s*(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+(?:,\d{2})?)|"
    r"n[aã]o\s+podendo\s+exceder\s*(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+(?:,\d{2})?)|"
    r"com\s+teto\s+de\s*(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+(?:,\d{2})?)"
    r")"
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
_RE_DEMISSAO_DATA_ANTES = re.compile(
    r"(?i)\bem\s+(\d{2}/\d{2}/\d{4})\s*,?\s*(?:foi\s+)?dispensad[oa]\b"
)
_RE_DATA_SAIDA_CTPS = re.compile(
    r"(?i)(?:"
    r"(?:data\s+de\s+)?sa[ií]da\s+da\s+CTPS[:\s]+|"
    r"(?:baixa|anota[çc][aã]o|anote-se|anotar)\s+(?:da\s+|a\s+)?CTPS.{0,80}?\bsa[ií]da\s+(?:em|para)\s+|"
    r"\bCTPS.{0,80}?\bsa[ií]da\s+(?:em|para)\s+|"
    r"proje[çc][aã]o\s+da\s+sa[ií]da\s+(?:em|para)\s+|"
    r"sa[ií]da\s+projetada\s+(?:em|para)\s+|"
    r"sa[ií]da\s+para\s+"
    r")"
    r"(\d{2}/\d{2}/\d{4})"
)
_RE_ANOTACAO_CTPS_FRAGMENTO = re.compile(
    r"(?is)(?:"
    r"anota[çc][aã]o\s+(?:na|da|em)\s+CTPS|"
    r"determino\s+a\s+anota[çc][aã]o\s+da\s+CTPS|"
    r"anote-se\s+a\s+CTPS|"
    r"anotar\s+(?:a\s+)?CTPS|"
    r"retificar\s+(?:a\s+)?CTPS|"
    r"retifica[çc][aã]o\s+(?:na|da|em)\s+CTPS|"
    r"baixa\s+da\s+CTPS|"
    r"proceder\s+a\s+baixa\s+da\s+CTPS"
    r").{0,220}"
)
_RE_CTPS_FUNCAO = re.compile(
    r"(?i)\bfun[çc][aã]o\s+de\s+([A-Za-zÀ-ÿ0-9 .'\-]+?)(?=\s+com\s+sal[aá]rio|[,.;]|$)"
)
_RE_FUNCAO_RECLAMANTE = re.compile(
    r"(?i)\b(?:na\s+)?fun[çc][aã]o\s*(?::|de)\s*([A-Za-zÀ-ÿ0-9 .'\-]+?)(?=\s+com\s+sal[aá]rio|\s+desde|[,.;]|$)"
    r"|\bcargo\s+de\s+([A-Za-zÀ-ÿ0-9 .'\-]+?)(?=\s+desde|\s+com\s+sal[aá]rio|[,.;]|$)"
)
_RE_SEGURO_DESEMPREGO_TERMO = re.compile(r"(?i)seguro[-\s]+desemprego")
_RE_SEGURO_INDEFERIDO = re.compile(
    r"(?is)\b(indefer[io]|indefir[io]|julgo\s+improcedente)\b.{0,80}seguro[-\s]+desemprego"
    r"|seguro[-\s]+desemprego.{0,80}\bindeferid[oa]\b"
)
_RE_SEGURO_INDENIZACAO = re.compile(
    r"(?is)(indeniza[çc][aã]o\s+substitutiva|indenizar).{0,120}seguro[-\s]+desemprego"
    r"|seguro[-\s]+desemprego.{0,120}(indeniza[çc][aã]o\s+substitutiva|indenizar)"
)
_RE_SEGURO_GUIAS_CD_SD = re.compile(
    r"(?is)(guias?.{0,80}(?:CD\s*/\s*SD|SD\s*/\s*CD).{0,120}seguro[-\s]+desemprego"
    r"|seguro[-\s]+desemprego.{0,120}guias?.{0,80}(?:CD\s*/\s*SD|SD\s*/\s*CD))"
)
_RE_SEGURO_GUIAS_ALVARA = re.compile(
    r"(?is)\b(entregar|entrega|fornecer|expedir|expe[çc]a-se|liberar|habilita[çc][aã]o)\b"
    r".{0,120}\b(guias?|alvar[aá])\b.{0,120}seguro[-\s]+desemprego"
    r"|\b(entregar|entrega|fornecer|expedir|expe[çc]a-se|liberar|habilita[çc][aã]o)\b"
    r".{0,120}seguro[-\s]+desemprego"
)
_RE_PPP_FRAGMENTO = re.compile(
    r"(?is)"
    r"\b(determino|condeno|dever[aá]|fornecer|entregar|entrega|expedir|retificar|retifica[çc][aã]o)\b"
    r".{0,160}\bPPP\b"
    r"|\bPPP\b.{0,160}"
    r"\b(determino|condeno|dever[aá]|fornecer|entregar|entrega|expedir|retificar|retifica[çc][aã]o)\b"
)
_RE_PPP_AGENTE_NOCIVO = re.compile(
    r"(?i)\bagente\s+nocivo\s+([\w]+(?:[\s\-][\w]+){0,3})"
)
_RE_GUIAS_RESCISORIAS_FRAGMENTO = re.compile(
    r"(?is)\b(entregar|entrega|fornecer|expedir|expe[çc]a-se|liberar|determino)\b.{0,180}"
    r"\b(TRCT|chave\s+de\s+conectividade|alvar[aá].{0,40}FGTS|FGTS.{0,40}alvar[aá])\b"
)
_RE_GUIAS_RESCISORIAS_TERMO = re.compile(
    r"(?i)\b(TRCT|chave\s+de\s+conectividade|c[oó]digo\s+SJ2|alvar[aá].{0,40}FGTS|FGTS.{0,40}alvar[aá])\b"
)
_RE_MULTA_467_INDEFERIDA = re.compile(
    r"(?is)\b(indefer[io]|indefir[io]|improcedente)\b.{0,100}\b(?:multa\s+(?:do\s+)?)?art\.?\s*467\b"
    r"|\b(?:multa\s+(?:do\s+)?)?art\.?\s*467\b.{0,100}\bindeferid[ao]\b"
)
_RE_MULTA_467_DEFERIDA = re.compile(
    r"(?is)\b(defir[io]|deferid[ao]|conden[oa]|condeno|julgo\s+procedente)\b"
    r".{0,140}\b(?:multa\s+(?:do\s+)?)?art\.?\s*467\b"
    r"|\b(?:multa\s+(?:do\s+)?)?art\.?\s*467\b.{0,140}"
    r"\b(defir[io]|deferid[ao]|conden[oa]|condeno|julgo\s+procedente)\b"
)
_RE_CUSTAS_ISENCAO = re.compile(
    r"(?is)\b(?:isento?|dispensad[ao]|exonerad[ao])\b.{0,80}\bcustas?\b"
    r"|\bcustas?\b.{0,80}\b(?:isento?|gratuidade|dispensad[ao])\b"
)
_RE_CUSTAS_RECLAMANTE = re.compile(
    r"(?is)custas?\s+(?:processuais?\s+)?(?:pelo?\s+|a\s+cargo\s+d[oa]\s+)"
    r"(?:reclamante|autor[ao]?\b)"
)
_RE_CUSTAS_RECLAMADA = re.compile(
    r"(?is)"
    # A: "custas pela/pelo reclamada/réu" — forma nominal direta
    r"custas?\s+(?:processuais?\s+)?(?:pel[ao]\s+|a\s+cargo\s+d[ao]?\s+)"
    r"(?:reclamad[ao]|r[eé]u\b|empresa|parte\s+passiva)"
    r"|"
    # B: "condeno a reclamada ... custas" — condenação explícita
    r"\b(?:conden[oa]|condeno)\b.{0,80}\breclamad[ao]\b.{0,120}\bcustas?\b"
    r"|"
    # C: "condeno ... custas" — condenação sem payer explícito (réu implícito)
    r"\b(?:conden[oa]|condeno)\b.{0,80}\bcustas?\s*(?:processuais?)?\b"
)
_RE_CUSTAS_SOBRE = re.compile(
    r"(?is)(?:calculadas?\s+)?sobre\s+(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2})"
)
_RE_CUSTAS_VALOR_DIRETO = re.compile(
    r"(?is)(?:no\s+valor\s+de|no\s+importe\s+de)\s+(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2})"
)
_RE_MULTA_477_INDEFERIDA = re.compile(
    r"(?is)\b(indefer[io]|indefir[io]|improcedente)\b.{0,100}\b(?:multa\s+(?:do\s+)?)?art\.?\s*477\b"
    r"|\b(?:multa\s+(?:do\s+)?)?art\.?\s*477\b.{0,100}\bindeferid[ao]\b"
)
_RE_MULTA_477_DEFERIDA = re.compile(
    r"(?is)\b(defir[io]|deferid[ao]|conden[oa]|condeno|julgo\s+procedente)\b"
    r".{0,140}\b(?:multa\s+(?:do\s+)?)?art\.?\s*477\b"
    r"|\b(?:multa\s+(?:do\s+)?)?art\.?\s*477\b.{0,140}"
    r"\b(defir[io]|deferid[ao]|conden[oa]|condeno|julgo\s+procedente)\b"
)
_RE_DANO_MORAL = re.compile(
    r"(?is)"
    # A: valor → conector "a título de" → rótulo (conector é discriminante; verbo desnecessário)
    r"(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:\.\d{3})*,\d{2}\s*reais?)"
    r"\s+a\s+t[íi]tulo\s+de\s+dano\s+moral\b"
    r"|"
    # B: verbo + rótulo → conector → valor (Fixo o dano moral em / no valor de / no importe de)
    r"\b(?:condeno|defiro|fixo|arbitro|determino|julgo\s+procedente)\b"
    r".{0,80}\bdano\s+moral\b\s+"
    r"(?:em|no\s+valor\s+de|no\s+importe\s+de|no\s+montante\s+de|de|:)\s*"
    r"(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:\.\d{3})*,\d{2}\s*reais?)"
    r"|"
    # C: verbo + "indenização por dano moral" → conector → valor
    r"\b(?:condeno|defiro|fixo|arbitro|determino|julgo\s+procedente)\b"
    r".{0,80}\bindeniza[çc][aã]o\s+por\s+dano\s+moral\b\s+"
    r"(?:no\s+valor\s+de|de|em)\s*"
    r"(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:\.\d{3})*,\d{2}\s*reais?)"
)
_RE_DANO_MATERIAL = re.compile(
    r"(?is)"
    # A: valor → conector "a título de" → rótulo de dano material / lucros cessantes
    r"(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:\.\d{3})*,\d{2}\s*reais?)"
    r"\s+a\s+t[íi]tulo\s+de\s+(?:dano\s+(?:material|emergente)|lucros?\s+cessantes?)\b"
    r"|"
    # B: verbo + rótulo → conector → valor
    r"\b(?:condeno|defiro|fixo|arbitro|determino|julgo\s+procedente)\b"
    r".{0,80}\b(?:dano\s+(?:material|emergente)|lucros?\s+cessantes?)\b\s+"
    r"(?:em|no\s+valor\s+de|no\s+importe\s+de|no\s+montante\s+de|de|:)\s*"
    r"(R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:\.\d{3})*,\d{2}\s*reais?)"
)
_RE_FGTS_FRAGMENTO = re.compile(r"(?is)\bFGTS\b.{0,220}")
_RE_FGTS_TODO_PERIODO = re.compile(
    r"(?i)\b(todo\s+o\s+(?:per[ií]odo\s+contratual|contrato)|per[ií]odo\s+contratual\s+completo)\b"
)
_RE_FGTS_PERIODO_DATAS = re.compile(
    r"(?i)(?:todo\s+o\s+)?per[ií]odo\s+contratual\s+de\s+(\d{2}/\d{2}/\d{4})\s+(?:a|at[eé])\s+(\d{2}/\d{2}/\d{4})"
)
_RE_FGTS_MULTA_40 = re.compile(r"(?i)\bmulta\s+(?:de\s+)?40\s*%")
_RE_FGTS_MULTA_40_INDEFERIDA = re.compile(
    r"(?is)\b(indefer[io]|indefir[io]|improcedente)\b.{0,120}\bmulta\s+(?:de\s+)?40\s*%.*?\bFGTS\b"
    r"|\bmulta\s+(?:de\s+)?40\s*%.*?\bFGTS\b.{0,120}\bindeferid[ao]\b"
)
_RE_FGTS_MULTA_40_AVISO = re.compile(
    r"(?is)\bFGTS\b.{0,100}\bmulta\s+(?:de\s+)?40\s*%.{0,100}\baviso\s+pr[eé]vio\b"
    r"|\bmulta\s+(?:de\s+)?40\s*%.{0,100}\baviso\s+pr[eé]vio\b"
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
    r"|aviso pr[eé]vio|f[eé]rias|d[eé]cimo|13(?:\s*[º°o])?(?:.{0,18}sal[aá]rio|.{0,18}(?:proporcional|integral))"
    r"|saldo de sal[aá]rios?|dano moral|dano material"
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
_RE_NOVO_DOCUMENTO_PJE = re.compile(r"(?im)^\s*PODER\s+JUDICI[ÁA]RIO\s*$")

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

# Honorarios sucumbenciais (MEDIUM) - percentual legal 5-15 e pagador no fragmento
_RE_HONORARIOS_FRAGMENTO = re.compile(
    r"(?is)(honor[aá]rios(?:\s+advocat[ií]cios)?\s+(?:sucumbenciais|rec[ií]procos?)"
    r"|honor[aá]rios\s+rec[ií]procos?)"
    r".{0,220}?(\d{1,2}(?:[,.]\d+)?)\s*%"
)
_RE_HONORARIOS_RECIPROCA = re.compile(r"(?i)\b(rec[ií]procos?|sucumb[eê]ncia\s+rec[ií]proca)\b")
_RE_HONORARIOS_RECLAMADA = re.compile(
    r"(?i)\b(reclamada|r[eé]|empresa)\b|"
    r"\bem\s+favor\s+do\s+(?:advogado|patrono)\s+do\s+(?:autor|reclamante)\b"
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
    r"(?im)^\s*(?:Reclamada|Reclamado|Parte\s+reclamada|R[ée]u)\s*:\s*(.+)$"
)

# Vara do trabalho — rótulo de capa ou linha ordinal no cabeçalho (sem rótulo, só início do texto)
_RE_VARA_CAPA_LABEL = re.compile(
    r"(?im)^\s*Vara(?:\s+do\s+Trabalho)?\s*:\s*(.+)$"
)
_RE_VARA_ORDINAL_LINE = re.compile(
    r"(?im)^\s*((?:\d+[º°ª]\s+)?Vara\s+do\s+Trabalho\s+de\s+.+)$"
)
_VARA_HEAD_CHARS = 4000

_RE_JUIZ_CARGO_ANTES = re.compile(
    r"(?im)^\s*(?:Ju[ií]z(?:a)?\s+do\s+Trabalho(?:\s+(?:Titular|Substituto|Substituta))?"
    r"|Desembargador(?:a)?(?:\s+Relator(?:a)?)?)\s*:\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ .'\-]{4,})\s*$"
)
_RE_JUIZ_NOME_ANTES = re.compile(
    r"(?im)^\s*([A-ZÀ-Ý][A-ZÀ-Ý .'\-]{6,})\s*\n\s*"
    r"(?:Ju[ií]z(?:a)?\s+do\s+Trabalho(?:\s+(?:Titular|Substituto|Substituta))?"
    r"|Desembargador(?:a)?(?:\s+Relator(?:a)?)?)\b"
)

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


def _sem_acentos(texto: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(ch) != "Mn"
    )


def _detalhe_verba_na_linha(nome: str, linha: str) -> Optional[str]:
    """Detalhe curto da verba quando a propria linha traz subtipo/avos/dias."""
    nome_norm = _sem_acentos(nome).lower()
    linha_limpa = re.sub(r"\s+", " ", (linha or "").strip(" -;\t"))
    linha_norm = _sem_acentos(linha_limpa).lower()

    if nome_norm.startswith("13") or "decimo" in nome_norm:
        m = re.search(r"(?i)\b(proporcional|integral)\s+de\s+(\d{4})(?:\s*\((\d{1,2}/\d{1,2})\))?", linha_norm)
        if m:
            detalhe = f"{m.group(1)} {m.group(2)}"
            if m.group(3):
                detalhe += f" ({m.group(3)})"
            return detalhe

    if "ferias" in nome_norm:
        m_pa = re.search(r"(?i)periodo\s+aquisitivo\s+(\d{4}/\d{4})", linha_norm)
        periodo = f" - periodo aquisitivo {m_pa.group(1)}" if m_pa else ""
        if "vencidas" in linha_norm and "dobro" in linha_norm:
            return f"vencidas em dobro{periodo}"
        if "integrais" in linha_norm and "simples" in linha_norm:
            return f"integrais simples{periodo}"
        m_prop = re.search(r"(?i)\bproporcionais?\b(?:\s*\((\d{1,2}/\d{1,2})\))?", linha_norm)
        if m_prop:
            detalhe = "proporcionais"
            if m_prop.group(1):
                detalhe += f" ({m_prop.group(1)})"
            return detalhe

    if "saldo de salario" in nome_norm:
        m = re.search(r"(?i)\b(\d+)\s+dias?\b", linha_norm)
        mes = re.search(
            r"(?i)\b(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(\d{4})\b",
            linha_norm,
        )
        if m:
            detalhe = f"{m.group(1)} dias"
            if mes:
                detalhe += f" - {mes.group(1)} de {mes.group(2)}"
            return detalhe

    if "aviso" in nome_norm and "previo" in nome_norm:
        partes: list[str] = []
        if "indenizado" in linha_norm:
            partes.append("indenizado")
        m = re.search(r"(?i)\b(\d+)\s+dias?\b", linha_norm)
        if m:
            partes.append(f"{m.group(1)} dias")
        if partes:
            return " - ".join(partes)

    return None


def _normalizar_nome_pessoa(nome: str) -> Optional[str]:
    raw = re.sub(r"\s+", " ", (nome or "").strip(" .:-\t"))
    if not raw or len(raw) < 5:
        return None
    if re.search(r"(?i)\b(advogado|oab|reclamante|reclamada|processo|vara)\b", raw):
        return None
    partes = []
    for p in raw.split():
        if len(p) <= 2 and p.lower() not in {"da", "de", "do", "das", "dos"}:
            partes.append(p.upper())
        else:
            partes.append(p[:1].upper() + p[1:].lower())
    return " ".join(partes)


def _formatar_moeda_br(raw: str) -> Optional[str]:
    numero_str = re.sub(r"[^\d,.]", "", raw or "").replace(".", "").replace(",", ".")
    try:
        valor = float(numero_str)
    except ValueError:
        return None
    if not (1 <= valor <= 1_000_000):
        return None
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _multa_diaria_obrigacao_no_fragmento(frag: str) -> Optional[str]:
    """Astreinte/multa diaria vinculada ao mesmo fragmento da obrigacao."""
    m = _RE_MULTA_DIARIA_OBRIGACAO.search(frag)
    if not m:
        return None
    raw = next((g for g in m.groups() if g), None)
    if not raw:
        return None
    return _formatar_moeda_br(raw)


def _multa_limite_obrigacao_no_fragmento(frag: str) -> Optional[str]:
    """Teto da multa diaria no mesmo fragmento da obrigacao — so extrair se houver multa_diaria."""
    m = _RE_MULTA_LIMITE_OBRIGACAO.search(frag)
    if not m:
        return None
    raw = next((g for g in m.groups() if g), None)
    if not raw:
        return None
    return _formatar_moeda_br(raw)


def _prazo_obrigacao_dias_no_fragmento(frag: str) -> Optional[str]:
    """Prazo em dias, apenas na mesma frase da obrigação de fazer."""
    frase = re.split(r"[.\n]", frag, maxsplit=1)[0]
    m = _RE_PRAZO_OBRIGACAO_DIAS.search(frase)
    if not m:
        return None
    raw = (m.group(1) or "").strip()
    dias = 8 if raw.casefold() == "oito" else int(raw)
    if not (1 <= dias <= 120):
        return None
    return f"{dias} dias"


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
            else:
                for m3 in _RE_VARA_ORDINAL_LINE.finditer(self.texto):
                    contexto = self.texto[max(0, m3.start() - 800) : m3.start()].upper()
                    if "PODER JUDICI" in contexto:
                        raw = (m3.group(1) or "").strip()
                        break
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

    def _extract_juiz_responsavel(self):
        """Juiz/desembargador signatario — MEDIUM por depender do layout da assinatura."""
        m = _RE_JUIZ_CARGO_ANTES.search(self.texto) or _RE_JUIZ_NOME_ANTES.search(self.texto)
        if not m:
            return
        nome = _normalizar_nome_pessoa(m.group(1))
        if nome:
            self._set_medium("juiz_responsavel", nome)

    def _extract_data_ajuizamento(self):
        """Data de ajuizamento / autuação PJe — primeira ocorrência; saída DD/MM/AAAA."""
        m = _RE_AJUIZAMENTO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_ajuizamento", norm)

    def _extract_data_transito_julgado(self):
        """Data do trânsito em julgado — MEDIUM, apenas quando expressa no texto."""
        m = _RE_TRANSITO_JULGADO.search(self.texto)
        if not m:
            return
        norm = self._normalizar_data(m.group(1))
        if not norm:
            return
        try:
            datetime.strptime(norm, "%d/%m/%Y")
        except ValueError:
            return
        self._set_medium("data_transito_julgado", norm)

    def _extract_data_intimacao_calculos(self):
        """Data de intimação para apresentação de cálculos — MEDIUM e explícita."""
        m = _RE_INTIMACAO_CALCULOS.search(self.texto)
        if not m:
            return
        raw = next((g for g in m.groups() if g), None)
        if not raw:
            return
        norm = self._normalizar_data(raw)
        if not norm:
            return
        try:
            datetime.strptime(norm, "%d/%m/%Y")
        except ValueError:
            return
        self._set_medium("data_intimacao_calculos", norm)

    def _extract_prazo_calculos_dias(self):
        """Prazo para apresentação de cálculos — MEDIUM e ligado a cálculos/liquidação."""
        m = _RE_PRAZO_CALCULOS.search(self.texto)
        if not m:
            return
        raw = next((g for g in m.groups() if g), None)
        if not raw:
            return
        if raw.casefold() == "oito":
            dias = 8
        else:
            dias = int(raw)
        if not (1 <= dias <= 60):
            return
        self._set_medium("prazo_calculos_dias", f"{dias} dias")
    def _extract_data_admissao(self):
        """Data de admissão — primeira ocorrência; saída DD/MM/AAAA (MEDIUM)."""
        m = _RE_ADMISSAO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_admissao", norm)

    def _extract_data_demissao(self):
        """Data de demissão / rescisão — primeira ocorrência; saída DD/MM/AAAA (MEDIUM)."""
        m = _RE_DEMISSAO.search(self.texto) or _RE_DEMISSAO_DATA_ANTES.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_demissao", norm)

    def _extract_data_saida_ctps(self):
        """Data de saída projetada para CTPS — apenas quando expressa no texto."""
        m = _RE_DATA_SAIDA_CTPS.search(self.texto)
        if not m:
            return
        norm = self._normalizar_data(m.group(1))
        if not norm:
            return
        try:
            datetime.strptime(norm, "%d/%m/%Y")
        except ValueError:
            return
        self._set_medium("data_saida_ctps", norm)


    def _extract_funcao_reclamante(self):
        """Cargo/função do reclamante — MEDIUM em contexto claro de função/cargo."""
        m = _RE_FUNCAO_RECLAMANTE.search(self.texto)
        if not m:
            return
        contexto = self.texto[max(0, m.start() - 80) : min(len(self.texto), m.end() + 80)]
        if re.search(r"(?i)\b(advogad[oa]|oab|juiz|ju[ií]za|magistrad[oa]|desembargador|procurador)\b", contexto):
            return
        raw = next((g for g in m.groups() if g), "")
        cargo = re.sub(r"\s+", " ", raw.strip(" .:-\t")).lower()
        if not cargo or len(cargo) < 3:
            return
        if re.search(r"(?i)\b(reclamante|reclamada|autor|parte|sal[aá]rio|ctps)\b", cargo):
            return
        self._set_medium("funcao_reclamante", cargo)



    def _append_obrigacao_fazer(self, item: dict[str, str]):
        atuais = self._medium.get("obrigacoes_fazer")
        if not isinstance(atuais, list):
            atuais = []
        chave = (item.get("tipo"), item.get("descricao"))
        for existente in atuais:
            if isinstance(existente, dict) and (existente.get("tipo"), existente.get("descricao")) == chave:
                return
        self._set_medium("obrigacoes_fazer", [*atuais, item])
    def _obrigacao_ctps_do_fragmento(self, frag: str) -> Optional[dict[str, str]]:
        low = frag.casefold()
        if "retificar" in low or "retificação" in low or "retificacao" in low:
            acao = "Retificar CTPS"
        elif "baixa" in low:
            acao = "Baixar CTPS"
        else:
            acao = "Anotar CTPS"

        extras: list[str] = []
        adm = _RE_ADMISSAO.search(frag)
        if adm:
            norm = self._normalizar_data(adm.group(1))
            if norm:
                extras.append(f"admissao {norm}")
        saida = _RE_DATA_SAIDA_CTPS.search(frag)
        if saida:
            norm = self._normalizar_data(saida.group(1))
            if norm:
                extras.append(f"saida {norm}")
        funcao = _RE_CTPS_FUNCAO.search(frag)
        if funcao:
            cargo = re.sub(r"\s+", " ", (funcao.group(1) or "").strip())
            if cargo:
                extras.append(f"funcao {cargo}")
        salario = _RE_SALARIO.search(frag)
        if salario:
            raw = (salario.group(1) or "").strip()
            numero_str = re.sub(r"[^\d,.]", "", raw).replace(".", "").replace(",", ".")
            try:
                valor = float(numero_str)
            except ValueError:
                valor = 0
            if 800 <= valor <= 80_000:
                salario_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                extras.append(f"salario {salario_fmt}")

        descricao = acao
        if extras:
            descricao = f"{acao}: " + "; ".join(extras)
        item = {"tipo": "CTPS", "descricao": descricao}
        prazo = _prazo_obrigacao_dias_no_fragmento(frag)
        if prazo:
            item["prazo_dias"] = prazo
        multa = _multa_diaria_obrigacao_no_fragmento(frag)
        if multa:
            item["multa_diaria"] = multa
            limite = _multa_limite_obrigacao_no_fragmento(frag)
            if limite:
                item["multa_limite"] = limite
        return item

    def _extract_obrigacoes_fazer_ctps(self):
        """Obrigação de fazer estruturada para CTPS — um item conservador."""
        m = _RE_ANOTACAO_CTPS_FRAGMENTO.search(self.texto)
        if not m:
            return
        item = self._obrigacao_ctps_do_fragmento((m.group(0) or "").strip())
        if item:
            self._set_medium("obrigacoes_fazer", [item])

    def _extract_anotacao_ctps(self):
        """Obrigacao de anotar/retificar/baixar CTPS — resumo curto MEDIUM."""
        m = _RE_ANOTACAO_CTPS_FRAGMENTO.search(self.texto)
        if not m:
            return
        frag = (m.group(0) or "").strip()
        low = frag.casefold()
        if "retificar" in low or "retificação" in low or "retificacao" in low:
            acao = "Retificar CTPS"
        elif "baixa" in low:
            acao = "Baixar CTPS"
        else:
            acao = "Anotar CTPS"

        extras: list[str] = []
        adm = _RE_ADMISSAO.search(frag)
        if adm:
            norm = self._normalizar_data(adm.group(1))
            if norm:
                extras.append(f"admissao {norm}")
        saida = _RE_DATA_SAIDA_CTPS.search(frag)
        if saida:
            norm = self._normalizar_data(saida.group(1))
            if norm:
                extras.append(f"saida {norm}")
        funcao = _RE_CTPS_FUNCAO.search(frag)
        if funcao:
            cargo = re.sub(r"\s+", " ", (funcao.group(1) or "").strip())
            if cargo:
                extras.append(f"funcao {cargo}")
        salario = _RE_SALARIO.search(frag)
        if salario:
            raw = (salario.group(1) or "").strip()
            numero_str = re.sub(r"[^\d,.]", "", raw).replace(".", "").replace(",", ".")
            try:
                valor = float(numero_str)
            except ValueError:
                valor = 0
            if 800 <= valor <= 80_000:
                salario_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                extras.append(f"salario {salario_fmt}")

        valor = acao
        if extras:
            valor = f"{acao}: " + "; ".join(extras)
        self._set_medium("anotacao_ctps", valor)

    def _extract_seguro_desemprego(self):
        """Seguro-desemprego — guias, alvara, indenizacao substitutiva ou indeferimento."""
        if not _RE_SEGURO_DESEMPREGO_TERMO.search(self.texto):
            return
        if _RE_SEGURO_INDEFERIDO.search(self.texto):
            self._set_medium("seguro_desemprego", "Indeferido")
        elif _RE_SEGURO_INDENIZACAO.search(self.texto):
            self._set_medium("seguro_desemprego", "Indenizacao substitutiva")
        elif m_cd_sd := _RE_SEGURO_GUIAS_CD_SD.search(self.texto):
            frag = self.texto[m_cd_sd.start(): min(len(self.texto), m_cd_sd.end() + 120)]
            valor = "Entregar guias CD/SD do seguro-desemprego"
            self._set_medium("seguro_desemprego", valor)
            item: dict = {"tipo": "seguro_desemprego", "descricao": valor}
            prazo = _prazo_obrigacao_dias_no_fragmento(frag)
            if prazo:
                item["prazo_dias"] = prazo
            multa = _multa_diaria_obrigacao_no_fragmento(frag)
            if multa:
                item["multa_diaria"] = multa
                limite = _multa_limite_obrigacao_no_fragmento(frag)
                if limite:
                    item["multa_limite"] = limite
            self._append_obrigacao_fazer(item)
        elif m_alvara := _RE_SEGURO_GUIAS_ALVARA.search(self.texto):
            frag = self.texto[m_alvara.start(): min(len(self.texto), m_alvara.end() + 120)]
            self._set_medium("seguro_desemprego", "Entregar guias/alvara para seguro-desemprego")
            item = {"tipo": "seguro_desemprego", "descricao": "Entregar guias/alvará para seguro-desemprego"}
            prazo = _prazo_obrigacao_dias_no_fragmento(frag)
            if prazo:
                item["prazo_dias"] = prazo
            multa = _multa_diaria_obrigacao_no_fragmento(frag)
            if multa:
                item["multa_diaria"] = multa
                limite = _multa_limite_obrigacao_no_fragmento(frag)
                if limite:
                    item["multa_limite"] = limite
            self._append_obrigacao_fazer(item)

    def _extract_obrigacoes_fazer_ppp(self):
        """Obrigacao de fazer — entrega ou retificacao do PPP, com prazo/multa opcionais.

        Exige verbo de ordem judicial antes ou depois de 'PPP' para nao capturar
        mencoes narrativas ('alega que o PPP nao foi entregue').
        """
        m = _RE_PPP_FRAGMENTO.search(self.texto)
        if not m:
            return
        frag = self.texto[m.start(): min(len(self.texto), m.end() + 200)]
        descricao = "Entregar/retificar PPP"
        m_an = _RE_PPP_AGENTE_NOCIVO.search(frag)
        if m_an:
            agente = m_an.group(1).strip()
            descricao = f"Entregar/retificar PPP — agente nocivo: {agente}"
        item: dict = {"tipo": "PPP", "descricao": descricao}
        prazo = _prazo_obrigacao_dias_no_fragmento(frag)
        if prazo:
            item["prazo_dias"] = prazo
        multa = _multa_diaria_obrigacao_no_fragmento(frag)
        if multa:
            item["multa_diaria"] = multa
            limite = _multa_limite_obrigacao_no_fragmento(frag)
            if limite:
                item["multa_limite"] = limite
        self._append_obrigacao_fazer(item)

    def _extract_guias_rescisorias(self):
        """Guias rescisórias/FGTS — TRCT, código SJ2, chave e alvará em contexto de entrega."""
        m = _RE_GUIAS_RESCISORIAS_FRAGMENTO.search(self.texto)
        if not m:
            return
        frag = self.texto[m.start() : min(len(self.texto), m.end() + 120)]
        itens: list[str] = []
        low = frag.casefold()
        if "trct" in low:
            itens.append("TRCT")
        if re.search(r"(?i)c[oó]digo\s+SJ2", frag):
            itens.append("código SJ2")
        if re.search(r"(?i)chave\s+de\s+conectividade", frag):
            itens.append("chave de conectividade")
        if re.search(r"(?i)alvar[aá].{0,50}FGTS|FGTS.{0,50}alvar[aá]", frag):
            itens.append("alvará FGTS")
        if not itens:
            return
        ordenados = []
        for item in ("TRCT", "código SJ2", "alvará FGTS", "chave de conectividade"):
            if item in itens and item not in ordenados:
                ordenados.append(item)
        valor = "; ".join(ordenados)
        self._set_medium("guias_rescisorias", valor)
        item = {
            "tipo": "guias_rescisorias",
            "descricao": f"Entregar guias rescisórias: {valor}",
        }
        multa = _multa_diaria_obrigacao_no_fragmento(frag)
        if multa:
            item["multa_diaria"] = multa
            limite = _multa_limite_obrigacao_no_fragmento(frag)
            if limite:
                item["multa_limite"] = limite
        self._append_obrigacao_fazer(item)

    def _extract_custas_processuais(self):
        """Custas processuais — pagador (Reclamada/Reclamante/Isencao) e valor base opcional."""
        texto = self.texto
        # 1. Isenção tem prioridade sobre tudo
        if _RE_CUSTAS_ISENCAO.search(texto):
            self._set_medium("custas_processuais", "Isencao reclamante")
            return
        # 2. Identifica pagador pela ordem: reclamante (explícito) > reclamada (implícito/explícito)
        m_reclamante = _RE_CUSTAS_RECLAMANTE.search(texto)
        m_reclamada  = _RE_CUSTAS_RECLAMADA.search(texto)
        if m_reclamante and (not m_reclamada or m_reclamante.start() <= m_reclamada.start()):
            pagador   = "Reclamante"
            m_anchor  = m_reclamante
        elif m_reclamada:
            pagador   = "Reclamada"
            m_anchor  = m_reclamada
        else:
            return
        # 3. Extrai valor base do fragmento (120 chars após o match)
        frag = texto[m_anchor.start(): min(len(texto), m_anchor.end() + 120)]
        valor_str = ""
        m_sobre = _RE_CUSTAS_SOBRE.search(frag)
        if m_sobre:
            v = _formatar_moeda_br(m_sobre.group(1))
            if v:
                valor_str = f", sobre {v}"
        else:
            m_val = _RE_CUSTAS_VALOR_DIRETO.search(frag)
            if m_val:
                v = _formatar_moeda_br(m_val.group(1))
                if v:
                    valor_str = f", {v}"
        self._set_medium("custas_processuais", f"{pagador}{valor_str}")

    def _extract_multa_art_467(self):
        """Multa do art. 467 da CLT — deferida/indeferida quando o texto e claro."""
        if _RE_MULTA_467_INDEFERIDA.search(self.texto):
            self._set_medium("multa_art_467", "Indeferida")
        elif _RE_MULTA_467_DEFERIDA.search(self.texto):
            self._set_medium("multa_art_467", "Deferida")

    def _extract_multa_art_477(self):
        """Multa do art. 477 da CLT — deferida/indeferida quando o texto e claro."""
        if _RE_MULTA_477_INDEFERIDA.search(self.texto):
            self._set_medium("multa_art_477", "Indeferida")
        elif _RE_MULTA_477_DEFERIDA.search(self.texto):
            self._set_medium("multa_art_477", "Deferida")

    def _extract_dano_moral(self):
        """Valor fixado a título de dano moral — MEDIUM quando condenação judicial expressa."""
        m = _RE_DANO_MORAL.search(self.texto)
        if not m:
            return
        raw = next((g for g in m.groups() if g), None)
        if not raw:
            return
        valor = _formatar_moeda_br(raw)
        if valor:
            self._set_medium("dano_moral", valor)

    def _extract_dano_material(self):
        """Valor fixado a título de dano material/emergente ou lucros cessantes — MEDIUM."""
        m = _RE_DANO_MATERIAL.search(self.texto)
        if not m:
            return
        raw = next((g for g in m.groups() if g), None)
        if not raw:
            return
        valor = _formatar_moeda_br(raw)
        if valor:
            self._set_medium("dano_material", valor)

    def _extract_fgts(self):
        """FGTS — periodo completo e multa de 40% apenas quando expressos."""
        if not re.search(r"(?i)\bFGTS\b", self.texto):
            return
        fragmentos = [m.group(0) for m in _RE_FGTS_FRAGMENTO.finditer(self.texto)]
        texto_fgts = "\n".join(fragmentos) or self.texto

        m_datas = _RE_FGTS_PERIODO_DATAS.search(texto_fgts)
        if m_datas and _par_datas_dd_mm_yyyy_validas(m_datas.group(1), m_datas.group(2)):
            self._set_medium(
                "fgts_periodo_completo",
                f"Todo o periodo contratual - {m_datas.group(1)} a {m_datas.group(2)}",
            )
        elif _RE_FGTS_TODO_PERIODO.search(texto_fgts):
            self._set_medium("fgts_periodo_completo", "Todo o periodo contratual")

        if _RE_FGTS_MULTA_40_INDEFERIDA.search(self.texto):
            self._set_medium("fgts_observacoes", "Multa de 40% indeferida")
        elif _RE_FGTS_MULTA_40.search(texto_fgts):
            self._set_medium("fgts_observacoes", "Multa de 40% deferida")

        if _RE_FGTS_MULTA_40_AVISO.search(self.texto):
            self._set_medium("fgts_multa_40_aviso_previo", "Incide")

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
            return self._limitar_trecho_decisao(t[m.start() : m.start() + _TRECHO_DECISAO_MAX_CHARS])
        m = _RE_TRECHO_ISTO_POSTO.search(t)
        if m:
            return self._limitar_trecho_decisao(t[m.start() : m.start() + _TRECHO_DECISAO_MAX_CHARS])
        m = _RE_TRECHO_JULGO.search(t)
        if m:
            return self._limitar_trecho_decisao(t[m.start() : m.start() + _TRECHO_DECISAO_MAX_CHARS])
        return None

    @staticmethod
    def _limitar_trecho_decisao(trecho: str) -> str:
        """Evita que o recorte do dispositivo atravesse para nova intimação/documento PJe."""
        m = _RE_NOVO_DOCUMENTO_PJE.search(trecho, 120)
        if m:
            return trecho[: m.start()]
        return trecho

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
            detalhe = _detalhe_verba_na_linha(n, linha)
            item: dict[str, Any] = {"nome": n}
            if detalhe:
                item["detalhe"] = detalhe
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

    def _extract_honorarios_sucumbenciais(self):
        """Honorarios sucumbenciais - pagador e percentual como ancoras MEDIUM."""
        m = _RE_HONORARIOS_FRAGMENTO.search(self.texto)
        if not m:
            return
        raw_pct = (m.group(2) or "").strip()
        try:
            pct = float(raw_pct.replace(",", "."))
        except ValueError:
            return
        if not (5 <= pct <= 15):
            return

        fragmento = self.texto[m.start() : min(len(self.texto), m.end() + 180)]
        if _RE_HONORARIOS_RECIPROCA.search(fragmento):
            self._set_medium("honorarios_sucumbenciais", "Reciproca")
        elif _RE_HONORARIOS_RECLAMADA.search(fragmento):
            self._set_medium("honorarios_sucumbenciais", "Reclamada")
        elif re.search(r"(?i)\bconden[oa]\b", fragmento):
            self._set_medium("honorarios_sucumbenciais", "Reclamada")
        else:
            return

        self._set_medium("percentual_honorarios", f"{raw_pct}%")

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
            self._extract_juiz_responsavel,
            self._extract_data_ajuizamento,
            self._extract_data_transito_julgado,
            self._extract_data_intimacao_calculos,
            self._extract_prazo_calculos_dias,
            self._extract_data_admissao,
            self._extract_data_demissao,
            self._extract_data_saida_ctps,
            self._extract_funcao_reclamante,
            self._extract_anotacao_ctps,
            self._extract_obrigacoes_fazer_ctps,
            self._extract_seguro_desemprego,
            self._extract_obrigacoes_fazer_ppp,
            self._extract_guias_rescisorias,
            self._extract_custas_processuais,
            self._extract_multa_art_467,
            self._extract_multa_art_477,
            self._extract_fgts,
            self._extract_salario_base,
            self._extract_verbas_deferidas_nomes,
            self._extract_indice_correcao,
            self._extract_juros_mora,
            self._extract_motivo_rescisao,
            self._extract_tipo_contrato,
            self._extract_divisor_horas,
            self._extract_aviso_previo_dias,
            self._extract_honorarios_sucumbenciais,
            self._extract_dano_moral,
            self._extract_dano_material,
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
        "data_saida_ctps":   "Data de saída da CTPS",
        "anotacao_ctps":     "Anotação/retificação da CTPS",
        "obrigacoes_fazer":  "Obrigações de fazer",
        "juiz_responsavel":  "Juiz responsavel",
        "funcao_reclamante": "Função do reclamante",
        "seguro_desemprego": "Seguro-desemprego",
        "guias_rescisorias": "Guias rescisórias",
        "multa_art_477":     "Multa do art. 477 da CLT",
        "fgts_periodo_completo": "FGTS - periodo",
        "fgts_observacoes": "FGTS - observacoes",
        "fgts_multa_40_aviso_previo": "FGTS/multa 40% sobre aviso previo",
        "data_ajuizamento":  "Data de ajuizamento",
        "data_transito_julgado": "Data do trânsito em julgado",
        "data_intimacao_calculos": "Data de intimação para cálculos",
        "prazo_calculos_dias": "Prazo para cálculos",
        "salario_base":      "Salário base",
        "indice_correcao":   "Índice de correção monetária",
        "juros_mora":        "Juros de mora",
        "motivo_rescisao":   "Motivo da rescisão",
        "tipo_contrato":     "Tipo de contrato",
        "divisor_horas":     "Divisor de horas extras",
        "aviso_previo_dias": "Aviso prévio (dias)",
        "honorarios_sucumbenciais": "Honorários sucumbenciais",
        "percentual_honorarios": "Percentual de honorários",
        "dano_moral":            "Dano moral",
        "dano_material":         "Dano material",
        "multa_art_467":         "Multa art. 467 CLT",
        "custas_processuais":    "Custas processuais",
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
        if campo == "obrigacoes_fazer":
            if not isinstance(valor, list) or not valor:
                continue
            linhas.append("  • Obrigações de fazer:")
            for item in valor:
                if not isinstance(item, dict):
                    continue
                tipo = (item.get("tipo") or "outro").strip()
                descricao = (item.get("descricao") or "").strip()
                extras: list[str] = []
                prazo = (item.get("prazo_dias") or "").strip()
                multa = (item.get("multa_diaria") or "").strip()
                limite = (item.get("multa_limite") or "").strip()
                if prazo:
                    extras.append(f"prazo: {prazo}")
                if multa:
                    extras.append(f"multa diaria: {multa}")
                if limite:
                    extras.append(f"limite: {limite}")
                base = f"      - {tipo}"
                if descricao:
                    base += f": {descricao}"
                if extras:
                    base += " — " + " — ".join(extras)
                linhas.append(base)
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
                detalhe = (it.get("detalhe") or "").strip()
                refs = it.get("reflexos")
                extras: list[str] = []
                if detalhe:
                    extras.append(f"detalhe: {detalhe}")
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

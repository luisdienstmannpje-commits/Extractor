"""
pre_extractor.py — Skill 7: Extração Pré-IA via Regex

Roda ANTES da chamada à IA e extrai campos usando só Python puro.
Zero tokens. Zero latência de rede.

Dois níveis de confiança:
  HIGH (≥95%): número CNJ, data sentença, justiça gratuita, rito.
               → Sobrescreve o resultado da IA diretamente.
  MEDIUM (~80%): datas contratuais, salário, índices, motivo rescisão,
                 tipo contrato, divisor, aviso prévio.
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
from typing import Optional


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

# Data da sentença — marcadores diretos + dd/mm/aaaa
_RE_DATA_SENTENCA = re.compile(
    r"(?i)(?:senten[çc]a\s+(?:proferida\s+(?:em\s+)?|datada\s+de\s+|de\s+)|"
    r"data\s+d[ao]\s+senten[çc]a\s*[:\s]+|"
    r"senten[çc]a\s*:\s*|"                    # "Sentença: DD/MM/AAAA"
    r"julgad[oa]\s+em\s+|"
    r"prolatad[oa]\s+em\s+|"                  # "prolatada em DD/MM/AAAA"
    r"decidid[oa]\s+em\s+|"                   # "decidida em DD/MM/AAAA"
    r"decis[aã]o\s+proferida\s+em\s+|"
    r"prola[çc][aã]o\s+d[ao]\s+senten[çc]a\s+em\s+|"
    r"sentenciad[oa]\s+em\s+|"
    r"julgou[-\s]+se\s+(?:[^.;\n]{0,30}?\s+)?em\s+)"
    r"(\d{2}/\d{2}/\d{4})"
)

# Assinatura digital PJe (alta confiança para data_sentença)
_RE_ASSINADO = re.compile(
    r"(?i)assinado\s+(?:eletronicamente|digitalmente)(?:.*?)em\s+(\d{2}/\d{2}/\d{4})",
    re.DOTALL,
)

# Justiça gratuita
_RE_JG_TRUE = re.compile(
    r"(?i)(\bdefiro\b.*?\bjusti[çc]a\s+gratuita\b"
    r"|\bjusti[çc]a\s+gratuita\b.*?\bdeferid[ao]s?\b"          # deferido/a/os
    r"|\bbenef[ií]cios\s+da\s+assist[eê]ncia\s+judici[aá]ria\b"
    r"|\bbenef[ií]cios?\s+d[ae]\s+justi[çc]a\s+gratuita\b.*?\bdeferid[ao]s?\b"  # singular/plural, da/de
    r"|\bgratuidade\s+d[ae]\s+justi[çc]a\b.*?\bdefiro\b"
    r"|\bdefiro\b.*?\bgratuidade\b"
    r"|\bconcedo\b.*?\bgratuidade\b"
    r"|\bgratuidade\s+d[ae]\s+justi[çc]a\b.*?\b(?:deferida?|concedid[ao]s?)\b"  # deferida/concedido/a
    r"|\bbenefici[aá]rio\b.*?\bjusti[çc]a\s+gratuita\b)"
)
_RE_JG_FALSE = re.compile(
    r"(?i)(\bindeferido\b.*?\bjusti[çc]a\s+gratuita\b"
    r"|\bjusti[çc]a\s+gratuita\b.*?\bindeferida\b"
    r"|\bnão\s+faz\s+jus\s+[aà]\s+justi[çc]a\s+gratuita\b"
    r"|\bindefiro\b.*?\b(?:gratuidade|justi[çc]a\s+gratuita)\b"
    r"|\bgratuidade\s+de\s+justi[çc]a\b.*?\bindeferida?\b"
    r"|\brevogo\b.*?\bjusti[çc]a\s+gratuita\b)"
)

# Rito processual
_RE_RITO_SUMARIO = re.compile(
    r"(?i)\b(?:rito\s+sumar[ií]{1,2}ssimo|procedimento\s+sumar[ií]{1,2}ssimo|sumar[ií]{1,2}ssimo"
    r"|rito\s+sum[aá]r[ií]o|procedimento\s+sum[aá]r[ií]o"
    r"|rito\s*[:\-]\s*sumar[ií]{1,2}ssimo|rito\s*[:\-]\s*sum[aá]r[ií]o)\b"
)
_RE_RITO_ORDINARIO = re.compile(
    r"(?i)\b(?:rito\s+(?:comum\s+)?ordin[aá]rio"
    r"|procedimento\s+ordin[aá]rio"
    r"|processo\s+ordin[aá]rio"
    r"|rito\s*[:\-]\s*(?:comum\s+)?ordin[aá]rio)\b"
)

# Datas contratuais (admissão/demissão)
_RE_ADMISSAO = re.compile(
    r"(?i)(?:admitid[oa](?:\s+n[ao]\s+\w+)?\s+em|"
    r"admiss[aã]o\s+em|admiss[aã]o\s*[:\-]\s*|"
    r"empregad[oa]\s+em|com\s+in[íi]cio\s+em|"
    r"ingressou\s+em|iniciou\s+(?:atividades?\s+|o\s+trabalho\s+)?em|"
    r"contratad[oa]\s+em|"
    r"contrata[çc][aã]o\s+em|"
    r"in[íi]cio\s+do\s+(?:contrato|v[íi]nculo)\s+(?:empregatício\s+)?em|"
    r"data\s+de\s+(?:admiss[aã]o|contrata[çc][aã]o)[:\s]+|"
    r"(?:empregad[oa]|v[íi]nculo(?:\s+empreg[aá]t[íi]ci[oó])?)\s+desde\s+|"
    r"integrou\s+(?:os\s+quadros\s+(?:da\s+empresa\s+)?|o\s+quadro\s+)?em|"
    r"passou\s+a\s+integrar\s+(?:o\s+quadro\s+(?:da\s+empresa\s+)?)?em)"
    r"\s*(\d{2}/\d{2}/\d{4})"
)
# Extenso: "admitido em 15 de janeiro de 2020"
_RE_ADMISSAO_EXTENSO = re.compile(
    r"(?i)(?:admitid[oa]\s+em|admiss[aã]o\s+em|"
    r"empregad[oa]\s+em|com\s+in[íi]cio\s+em|"
    r"ingressou\s+em|iniciou\s+em|"
    r"contratad[oa]\s+em|contrata[çc][aã]o\s+em|"
    r"in[íi]cio\s+do\s+(?:contrato|v[íi]nculo)\s+(?:empregatício\s+)?em)"
    r"\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})"
)
_RE_DEMISSAO = re.compile(
    r"(?i)"
    r"(?:"
    # Triggers com frase opcional entre trigger e "em" (GAP 2: "dispensada da empresa em" / "sem justa causa em")
    # (?:\s+(?!em\b)\S+){0,4} consome até 4 palavras sem consumir "em"
    r"dispensad[oa](?:\s+(?!em\b)\S+){0,4}\s+em|"
    r"demitid[oa](?:\s+(?!em\b)\S+){0,4}\s+em|"
    r"rescis[aã]o\s+(?:contratual\s+)?em|rescindid[oa]\s+em|"
    r"saiu\s+em|desligad[oa](?:\s+(?!em\b)\S+){0,3}\s+em|desligamento\s+em|"
    r"demiss[aã]o\s+(?:sem\s+justa\s+causa\s+)?em|"
    r"término\s+do\s+(?:contrato|v[íi]nculo(?:\s+empreg[aá]t[íi]ci[oó])?)\s+em|"
    # GAP 4: novos triggers
    r"encerrou\s+o\s+v[íi]nculo(?:\s+empreg[aá]t[íi]ci[oó])?\s+em|"
    r"rompeu\s+o\s+v[íi]nculo(?:\s+empreg[aá]t[íi]ci[oó])?\s+em|"
    r"extin[çc][aã]o\s+do\s+contrato\s+em|"
    # Labels com data (GAP 1: dois-pontos/hífen)
    r"(?:demiss[aã]o|rescis[aã]o|desligamento)\s*[:\-]|"
    # Labels clássicos
    r"data\s+de\s+demiss[aã]o[:\s]+|data\s+d[ao]\s+rescis[aã]o(?:\s+\w+)?[:\s]+|"
    # GAP 5: 'data de saída'
    r"data\s+de\s+sa[íi]da[:\s]+"
    r")"
    r"\s*(\d{2}/\d{2}/\d{4})"
)
# Extenso: "dispensado em 30 de junho de 2023"
_RE_DEMISSAO_EXTENSO = re.compile(
    r"(?i)"
    r"(?:dispensad[oa](?:\s+(?!em\b)\S+){0,4}|"
    r"demitid[oa](?:\s+(?!em\b)\S+){0,4}|"
    r"rescindid[oa]|saiu|"
    r"desligad[oa](?:\s+(?!em\b)\S+){0,3}|desligamento|"
    r"demiss[aã]o\s+(?:sem\s+justa\s+causa\s+)?|"
    r"término\s+do\s+contrato|"
    r"encerrou\s+o\s+v[íi]nculo(?:\s+empregatício)?|"
    r"rompeu\s+o\s+v[íi]nculo(?:\s+empregatício)?)"
    r"\s+em\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})"
)
# GAP 3: padrão invertido "Em DD/MM/AAAA, [frase] foi dispensado/demitido / ocorreu rescisão"
_RE_DEMISSAO_INVERTIDA = re.compile(
    r"(?i)\bem\s+(\d{2}/\d{2}/\d{4})\s*,?\s*"
    r"(?:[^.;\n]{0,30}?\s+)?(?:foi\s+)?(?:dispensad[oa]|demitid[oa]|rescindid[oa]|desligad[oa])\b"
    r"|"
    r"\bem\s+(\d{2}/\d{2}/\d{4})\s*,?\s*ocorreu\s+a?\s*rescis[aã]o\b"
)

# Valor da causa — labels e fórmulas de pedido (MEDIUM)
_RE_VALOR_CAUSA = re.compile(
    r"(?i)"
    r"(?:"
    r"valor\s+(?:total\s+)?d[ao]\s+causa\s*[-:]?\s*|"
    r"valor\s+atribu[ií]do\s+[aà]\s+causa\s*[-:]?\s*|"
    r"causa\s+no\s+valor\s+de\s+|"
    r"dou\s+[aà]\s+(?:presente\s+)?causa\s+o\s+valor\s+de\s+|"
    r"deu\s+[aà]\s+(?:presente\s+)?causa\s+o\s+valor\s+de\s+|"
    r"atribuo\s+[aà]\s+(?:presente\s+)?causa\s+o\s+valor\s+de\s+|"
    r"atribuiu\s+[aà]\s+(?:presente\s+)?causa\s+o\s+valor\s+de\s+|"
    r"(?<!\w)causa\s*[-:]\s*(?=R\$)"
    r")"
    r"R?\$?\s*([\d.,]+(?:\s*(?:reais|mil))?)",
    re.IGNORECASE,
)

# Salário base — diversas formas de menção
_RE_SALARIO = re.compile(
    r"(?i)(?:sal[aá]rio\s+(?:(?:base|fixo|contratual|normativo|bruto)\s+)?de|"
    r"sal[aá]rio(?:\s+(?:base|fixo|contratual|normativo|bruto))?\s*:\s*R\$|"
    r"remunera[çc][aã]o\s+(?:mensal\s+)?(?:bruta\s+)?de|"
    r"percebia\s+(?:o\s+sal[aá]rio\s+de|a\s+import[aâ]ncia\s+de)|"
    r"recebia\s+(?:o\s+sal[aá]rio|a\s+(?:import[aâ]ncia|quantia))\s+de|"
    r"recebia\s+mensalmente\s+(?:o\s+valor\s+de\s+)?|"
    r"[úu]ltima\s+remunera[çc][aã]o\s+(?:mensal\s+)?de|"
    r"piso\s+(?:salarial\s+)?de|"
    r"vencimentos?\s+de|"
    r"sal[aá]rio\s+(?:(?:bruto|l[ií]quido)\s+)?(?:mensal\s+)?(?:(?:bruto|l[ií]quido)\s+)?de\s+R\$)"
    r"\s*R?\$?\s*"
    r"([\d.,]+(?:\s*(?:reais|mil))?)(?:\s*(?:mensais?|brutos?|l[ií]quidos?))?",
    re.IGNORECASE,
)

# Índice de correção monetária
_RE_IPCA = re.compile(r"(?i)\bIPCA(?:-E)?\b")   # cobre IPCA-E e IPCA simples
_RE_SELIC = re.compile(r"(?i)\bSELIC\b")
_RE_TR = re.compile(r"(?i)\b(atualização\s+pela\s+)?TR\b")
_RE_INPC = re.compile(r"(?i)\bINPC\b")
_RE_ADC58 = re.compile(r"(?i)\bADC\s*58\b|\bADC[-\s]*58\b")

# Juros de mora
_RE_JUROS_1 = re.compile(
    r"(?i)juros\s+(?:de\s+)?(?:mora(?:t[oó]rios?)?\s*(?:de\s+)?)?:?\s*"
    r"1%\s+(?:(?:ao|a\.o\.)\s+m[eê]s|a\.m\.)"
    r"|juros\s*:\s*1%\s+(?:(?:ao|a\.o\.)\s+m[eê]s|a\.m\.)"
)
_RE_JUROS_SELIC = re.compile(r"(?i)juros\s+(?:de\s+mora\s+)?(?:pela\s+)?SELIC")
_RE_JUROS_LEGAIS = re.compile(r"(?i)juros\s+legais")

# Motivo da rescisão — padrões aceitam texto com e sem acentos (PDFs variam)
_RE_RESCISAO_SJC = re.compile(
    r"(?i)"
    r"(?:dispensad[oa]|dispensou|demitid[oa]|demitiu|demiss[aã]o|rescis[aã]o)"
    r".{0,60}\bsem\s+justa\s+causa\b"
    r"|\bimotivadamente\b"
    r"|\bsem\s+justa\s+causa\b"          # padrão direto sem verbo antecedente
    r"|\bdispensa\s+imotivada\b"         # sinônimo: dispensa sem motivação
    r"|\bdemiss[aã]o\s+imotivada\b"      # demissão sem justa causa
)
_RE_RESCISAO_JC = re.compile(
    r"(?i)\b(?:com|por)\s+justa\s+causa\b"
    r"|\babandon[oa]\s+de\s+emprego\b"
    r"|\bjusta\s+causa\s+(?:configurad[ao]?|reconhecid[ao]?|comprovad[ao]?)\b"
    r"|\bfalta\s+grave\b"
)
_RE_RESCISAO_CULPA_RECIPROCA = re.compile(
    r"(?i)\bculpa\s+rec[íi]proca\b"
)
_RE_RESCISAO_INDIRETA = re.compile(
    r"(?i)\brescis[aã]o\s+indireta\b"
    r"|\bpor\s+culpa\s+do\s+empregador\b"
    r"|\bfalta\s+grave\s+do\s+empregador\b"
)
_RE_RESCISAO_PEDIDO = re.compile(
    r"(?i)\b(?:pedido\s+de\s+demiss[aã]o|demitiu[-\s]+se|pediu\s+demiss[aã]o"
    r"|exonera[çc][aã]o\s+a\s+pedido|exonerou[-\s]+se\s+a\s+pedido"
    r"|rescis[aã]o\s+a\s+pedido"          # 'rescisão a pedido do empregado'
    r"|(?:por\s+)?iniciativa\s+do\s+empregado)\b"  # 'por iniciativa do empregado'
)
_RE_RESCISAO_TERMINO = re.compile(
    r"(?i)\bt[eé]rmino\s+do\s+(?:prazo\s+do\s+)?contrato\b"
    r"|\bfim\s+do\s+prazo\b"
    r"|\bencerramento\s+d[ao]s?\s+atividades\b"
    r"|\bencerramento\s+d[ao]\s+estabelecimento\b"
    r"|\bextin[çc][aã]o\s+d[ao]\s+estabelecimento\b"
    r"|\bextin[çc][aã]o\s+da\s+empresa\b"       # 'extinção da empresa empregadora'
    r"|\bfechamento\s+da\s+empresa\b"            # 'fechamento da empresa'
)
_RE_RESCISAO_APOSENTADORIA = re.compile(
    r"(?i)\baposentadoria\b"
)
_RE_RESCISAO_ACORDO = re.compile(
    r"(?i)\bacordo\s+rescis[oó]rio\b"
    r"|\bacordo\s+entre\s+as\s+partes\b"
    r"|\bart\.?\s*484-?A\b"
)
_RE_RESCISAO_FALECIMENTO = re.compile(
    r"(?i)\bfalecimento\b"
    r"|\b[oó]bito\s+do\s+empregado\b"
)

# Tipo de contrato — duração (HIGH: frases terminológicas fixas)
_RE_CONTRATO_EXPERIENCIA = re.compile(
    r"(?i)\bcontrato\s+de\s+experi[eê]ncia\b"
    r"|\bper[íi]odo\s+de\s+experi[eê]ncia\b"
    r"|\badmitido[oa]?\s+(?:para\s+)?per[íi]odo\s+de\s+experi[eê]ncia\b"
    r"|\bregime\s+de\s+experi[eê]ncia\b"
)
_RE_CONTRATO_PRAZO_DET = re.compile(
    r"(?i)\bcontrato\s+(?:por|a)\s+prazo\s+determinado\b"
    r"|\bprazo\s+determinado\b.{0,40}\bcontrato\b"
    r"|\bcontrato\s+(?:de\s+trabalho\s+)?(?:com\s+|por\s+)?prazo\s+determinado\b"
    r"|\bcontrato\s+(?:de\s+trabalho\s+)?por\s+tempo\s+determinado\b"
    r"|\bv[íi]nculo\s+(?:empregatício\s+|de\s+emprego\s+)?por\s+(?:prazo|tempo)\s+determinado\b"
    r"|\bcontrato\s+a\s+termo\b"
)
_RE_CONTRATO_PRAZO_INDET = re.compile(
    r"(?i)\bcontrato\s+(?:por|a)\s+prazo\s+indeterminado\b"
    r"|\bcontrato\s+(?:de\s+trabalho\s+)?(?:com\s+|por\s+)?prazo\s+indeterminado\b"
    r"|\bcontrato\s+(?:de\s+trabalho\s+)?por\s+tempo\s+indeterminado\b"
    r"|\bcontrato\s+de\s+dura[çc][aã]o\s+indeterminada\b"
    r"|\bv[íi]nculo\s+(?:empregatício\s+|de\s+emprego\s+)?por\s+(?:prazo|tempo)\s+indeterminado\b"
)
_RE_CONTRATO_INTERMITENTE = re.compile(
    r"(?i)\bcontrato\s+intermitente\b"
    r"|\btrabalho\s+intermitente\b"
    r"|\bmodalidade\s+(?:de\s+)?intermitente\b"
)
_RE_CONTRATO_APRENDIZ = re.compile(
    r"(?i)\bcontrato\s+de\s+aprendizagem\b"
    r"|\bmenor\s+aprendiz\b"
    r"|\bna\s+qualidade\s+de\s+aprendiz\b"
    r"|\baprendiz\b"
)
_RE_CONTRATO_TEMPORARIO = re.compile(
    r"(?i)\bcontrato\s+tempor[aá]rio\b"
    r"|\btrabalho\s+tempor[aá]rio\b"
    r"|\btrabalhador\s+tempor[aá]rio\b"
    r"|\bLei\s+6\.019\b"
)

# Tipo de contrato — natureza jurídica (MEDIUM: dependem de contexto)
_RE_CONTRATO_CLT = re.compile(r"(?i)\bv[íi]nculo\s+(?:de\s+)?emprego\b|\bCLT\b|\bceletista\b")
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
    r"(?i)(?:\bdivisor\b|\bm[oó]dulo\b)(?:\s+de\s+horas?)?\s*(?:de\s+)?:?\s*"
    r"(\b150\b|\b175\b|\b180\b|\b200\b|\b220\b)"
)
# (?<!\d) e (?!\d) evitam casamento dentro de números maiores (ex: "440")
# sem \b...\b no número: "44h" tem h logo após, não haveria word boundary
_RE_HORAS_SEMANAIS = re.compile(
    r"(?i)(?<!\d)(30|35|36|40|44)(?!\d)\s*(?:h(?:oras?)?\s*)?(?:semanais?|por\s+semana)\b"
    r"|"  # forma invertida: "jornada semanal de N horas"
    r"(?:jornada|carga\s+hor[aá]ria)\s+(?:semanal|semanais)\s+de\s+(?<!\d)(30|35|36|40|44)(?!\d)\s*h(?:oras?)?"
)
# Jornada 12x36 — divisor padrão 220
_RE_JORNADA_12X36 = re.compile(
    r"(?i)\b12\s*[xX×]\s*36\b"
    r"|\b12\s+por\s+36\b"
    r"|\bjornada\s+de\s+doze\s+por\s+trinta\s+e\s+seis\b"
)

# Aviso prévio — dias (forma direta e invertida)
_RE_AVISO_DIAS = re.compile(
    r"(?i)aviso\s+pr[eé]vio"
    r"(?:\s+(?:indenizado|trabalhado|proporcional|integral))?"           # adjetivo opcional
    r"\s*(?:de\s+|:\s*|correspondente\s+a\s+|equivalente\s+a\s+)?"     # "de", ":", "correspondente a", "equivalente a"
    r"(?:(\d+)\s*(?:\([^)]{1,20}\)\s*)?dias?"                           # N (extenso) dias
    r"|\((\d+)\s*dias?\))"                                               # (N dias)
)
_RE_AVISO_DIAS_INV = re.compile(
    r"(?i)(\d+)\s*(?:\([^)]{1,20}\)\s*)?dias?\s+de\s+aviso\s+pr[eé]vio"
)
# Aviso prévio em meses — converte para dias (1 mês=30, 2=60, 3=90)
_RE_AVISO_MESES = re.compile(
    r"(?i)aviso\s+pr[eé]vio"
    r"(?:\s+(?:indenizado|trabalhado|proporcional|integral))?"
    r"\s*(?:de\s+|:\s*)?"
    r"(\d+)\s*(?:\([^)]{1,20}\)\s*)?m[eê]s(?:es)?\b"
)

# Aviso prévio — tipo (trabalhado vs indenizado)
_RE_AVISO_TRABALHADO = re.compile(
    r"(?i)\baviso\s+pr[eé]vio\s+trabalhado\b"
    r"|\baviso\s+pr[eé]vio\s*:\s*trabalhado\b"
    r"|\baviso\s+pr[eé]vio\s+cumprido\b"
)
_RE_AVISO_INDENIZADO = re.compile(
    r"(?i)\b(?:aviso\s+pr[eé]vio\s+indenizado"
    r"|indeniza[çc][aã]o\s+substitutiva\s+do\s+aviso\s+pr[eé]vio"
    r"|aviso\s+pr[eé]vio\s+convertido\s+em\s+(?:indeniza[çc][aã]o|pec[uú]nia)"
    r"|aviso\s+pr[eé]vio\s*:\s*indenizado"
    r"|aviso\s+pr[eé]vio.{0,40}pago\s+em\s+dinheiro"
    r"|aviso\s+pr[eé]vio.{0,40}substitu[íi]do\s+em\s+dinheiro"
    r"|aviso\s+pr[eé]vio.{0,40}dispensado\s+de\s+cumprir)\b"
)

# Horário de trabalho — "[das/de] HH[h:mm] às HH[h:mm] [com X h de intervalo]"
# Artigo (das/de) é opcional: aceita "das 08h", "de 08h" e "08h" direto.
# Nota: \s* (não \s+) após "trabalho" para aceitar "trabalho:" sem espaço intermediário.
_RE_HORARIO_TRABALHO = re.compile(
    r"(?i)"
    r"(?:hor[aá]rio\s*(?:de\s+trabalho\s*)?[:\-]?\s*|"   # 'horário:' ou 'horário de trabalho:'
    r"trabalha(?:va|ndo|r)?\s+|labora(?:va|ndo|r)?\s+|"
    r"jornada\s*(?:de\s+trabalho\s*)?[:\-]?\s*|"
    r"expediente\s+)"                                      # 'expediente das X às Y'
    r"((?:das?\s+|de\s+)?\d{1,2}[h:]\d{0,2}\s*[àa][s]?\s*\d{1,2}[h:]\d{0,2}"
    r"(?:[^.;:\n]{0,60}(?:intervalo|almo[çc]o|refei[çc][aã]o)[^.;:\n]{0,20})?)",
    re.IGNORECASE,
)

# Horário de trabalho — formato "Entrada: HHhMM [e] Saída: HHhMM"
_RE_HORARIO_ENTRADA_SAIDA = re.compile(
    r"(?i)entrada\s*:?\s*(\d{1,2}[h:]\d{2})\s+(?:e\s+)?sa[íi]da\s*:?\s*(\d{1,2}[h:]\d{2})"
)

# Vara do Trabalho — padrão completo + sigla VT + Vara Trabalhista (HIGH)
_RE_VARA_TRABALHO = re.compile(
    r"(?i)"
    r"(?:J[uú][íi]zo\s+d[ao]\s+)??"  # prefixo "Juízo da/do" opcional (não-guloso)
    r"("
    r"(?:\d{1,2}[aªoº°]?\s*\.?\s*)?"  # ordinal opcional
    r"(?:"
    r"Vara\s+do\s+Trabalho|"          # "Vara do Trabalho"
    r"Vara\s+Trabalhista|"             # "Vara Trabalhista"
    r"VT|"                             # sigla VT
    r"J[uú][íi]zo\s+Trabalhista"      # "Juízo Trabalhista" sem "da/do"
    r")"
    r"\s+de\s+[^,\.;\n\(\)]{2,50}?"
    r")"
    r"(?=[,\.;\n\(\)/\-]|$)",
    re.IGNORECASE,
)

# Advogados — rótulos explícitos e formas narrativas (HIGH)
# Bloco de nome compartilhado: "(?:Dr(?:a)?\.?\s*)? + NOME_PRÓPRIO"
_RE_ADV_NOME = r"(?:Dr(?:a)?\.?\s*)?([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇÀÜ][^,\n;]{3,80}?)(?=\s*(?:OAB|CNA|\(|,|\n|;|$))"

_RE_ADV_RECLAMANTE = re.compile(
    r"(?i)"
    r"(?:"
    # Labels clássicos: "Adv. do Reclamante:" / "Advogado(a) do Reclamante:"
    r"(?:Adv\.|Advogad[oa])\s*do\s+[Rr]eclamante\s*[:\-]\s*|"
    # GAP 1: "Patrono/Patrona do/da autor/autora/reclamante:"
    r"[Pp]atron[oa]\s+d[ao]\s+(?:autor[ao]?|reclamante)\s*[:\-]\s*|"
    # GAP 5: "Procurador/Procuradora do/da reclamante:"
    r"[Pp]rocurador[ao]?\s+d[ao]\s+[Rr]eclamante\s*[:\-]\s*|"
    # GAP 2: "representado pelo/pela advogado(a)" / "Autor representado pelo Dr."
    r"(?:[Aa]utor\s+)?representad[oa]\s+pel[ao]\s+(?:Dr(?:a)?\.?\s*)?advogad[oa]\s+|"
    r"(?:[Aa]utor\s+)representad[oa]\s+pel[ao]\s+Dr\.\s*"
    r")"
    + _RE_ADV_NOME
)

_RE_ADV_RECLAMADA = re.compile(
    r"(?i)"
    r"(?:"
    # Labels clássicos: "Adv. da Reclamada:" / "Advogado(a) da Reclamada(o):"
    r"(?:Adv\.|Advogad[oa])\s*d[ao]\s+[Rr]eclamad[ao]\s*[:\-]\s*|"
    # GAP 3: "Patrono da ré:" / "Patrono da reclamada:" / "Patrono do réu:"
    r"[Pp]atron[oa]\s+d[ao]\s+(?:r[eé](?:u)?|reclamad[ao])\s*[:\-]\s*|"
    # GAP 6: "Procurador/Procuradora da/do reclamada/reclamado:"
    r"[Pp]rocurador[ao]?\s+d[ao]\s+[Rr]eclamad[ao]\s*[:\-]\s*|"
    # GAP 4: "representada pelo/pela advogado(a)" / "Ré representada pelo Dr."
    r"(?:R[eé](?:u)?\s+)?representad[ao]\s+pel[ao]\s+(?:Dr(?:a)?\.?\s*)?advogad[oa]\s+|"
    r"(?:R[eé](?:u)?\s+)representad[ao]\s+pel[ao]\s+Dr\.\s*"
    r")"
    + _RE_ADV_NOME
)

# Juiz responsável — rótulo explícito no cabeçalho da peça (HIGH: campo labelado)
_RE_JUIZ_LABEL = re.compile(
    r"(?i)"
    r"(?:"
    # Forma 1: rótulo com separador — Juiz(a)/Magistrado(a) + Trabalho/Titular/Substituto + : ou -
    r"(?:MM\.?\s*)?(?:Ju[íi]z(?:\([ao]\))?[ao]?|Magistrad[ao])"
    r"\s*(?:(?:do|da)\s+Trabalho)?\s*(?:Titular|Substitut[ao])?\s*[:\-]\s*"
    r"|"
    # Forma 2: 'pelo/pela Juiz(a) Dr(a).' / 'perante o/a Juiz Dr.' — sem separador
    r"(?:pel[ao]|perante\s+[oa])\s+(?:MM\.?\s*)?Ju[íi]z[ao]?\s+"
    r"|"
    # Forma 3: 'Exmo. Sr. Juiz do Trabalho Dr.' — prefixo de tratamento
    r"Exm[oa]\.\s*Sr[ao]?\.?\s*Ju[íi]z[ao]?\s*(?:(?:do|da)\s+Trabalho\s*)?"
    r")"
    r"(?:Dr(?:a)?\.?\s*)?"
    r"([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇÀÜ][^,\n;(]{3,60}?)(?=[,;\n(]|$)"
)

# Função/cargo do reclamante — frases-gatilho específicas (texto livre: captura até stop char)
_RE_FUNCAO_RECLAMANTE = re.compile(
    r"(?i)"
    r"(?:exerc(?:ia|eu)\s+(?:(?:a\s+)?fun[çc][aã]o|(?:o\s+)?cargo)\s+de\s+|"
    r"desempenh(?:ava|a)\s+(?:a\s+)?fun[çc][aã]o\s+de\s+|"
    r"(?:foi\s+)?contratad[oa]\s+como\s+|"
    r"admitid[oa]\s+como\s+|"
    r"trabalh(?:ou|a(?:va)?)\s+como\s+|"
    r"labor(?:ou|a(?:va|ndo|r)?)\s+como\s+|"
    r"atu(?:ou|a(?:va|ndo|r)?)\s+como\s+|"
    r"serviu\s+como\s+|"
    r"ocupa(?:va)?\s+(?:o\s+)?cargo\s+de\s+|"
    r"na\s+fun[çc][aã]o\s+de\s+|"
    r"cargo\s*[:\-]\s*|"
    r"fun[çc][aã]o\s*[:\-]\s*)"
    r"([^,\.;\n\(\)]{3,40}?)(?=[,\.;\n\(\)]|$)",
    re.IGNORECASE,
)

# Jornada contratual — "X horas diárias/semanais/por dia [e Y horas semanais]"
# Triggers: jornada, carga horária, trabalha*/trabalhou
_RE_JORNADA_CONTRATUAL = re.compile(
    r"(?i)"
    r"(?:jornada\s+(?:di[aá]ria\s+)?(?:de\s+trabalho\s*)?:?\s*(?:de\s+)?"
    r"|carga\s+hor[aá]ria\s*:?\s*(?:de\s+)?"
    r"|trabalh(?:ou|a(?:va|ndo|r)?)\s+)"
    r"(\d+\s*(?:\([^)]{1,30}\)\s*)?h(?:oras?)?"
    r"(?:\s*(?:di[aá]rias?|semanais?|por\s+dia[s]?))?"    # qualificador opcional
    r"(?:\s*[e,]\s*\d+\s*(?:\([^)]{1,30}\)\s*)?h(?:oras?)?\s*(?:semanais?|por\s+semana))?)",
    re.IGNORECASE,
)

# Jornada semanal implícita — "jornada/carga [horária] semanal de Xh[oras]"
# 'semanal' antes do número torna o qualificador implícito (não repete 'semanais' após).
_RE_JORNADA_SEMANAL = re.compile(
    r"(?i)(?:jornada|carga)\s+(?:hor[aá]ria\s+)?semanal\s+(?:de\s+)?(\d+\s*h(?:oras?)?)\b"
)

# Data de ajuizamento
_RE_AJUIZAMENTO = re.compile(
    r"(?i)(?:data\s+de\s+ajuizamento[:\s]+|"
    r"ajuizamento\s*[:\-]\s*|"                              # "ajuizamento: DD/MM" (sem "data de")
    r"protocolo(?:u\s+a\s+presente)?\s+em\s+|"
    r"proposta\s+em\s+|distribu[íi]d[oa]\s+em\s+|"        # distribu[íi]d[oa]: masculino e feminino
    r"distribu[íi]do\s+em\s+|"
    r"autuad[oa]\s+em\s+|"                                 # "autuado em DD/MM"
    r"peti[çc][aã]o\s+inicial\s+de\s+|"                   # "petição inicial de DD/MM"
    r"ajuizad[oa]\s+em\s+|recebida\s+em\s+|"
    r"data\s+de\s+distribui[çc][aã]o[:\s]+|"              # "data de distribuição: DD/MM"
    r"distribui[çc][aã]o\s*[:\-]\s*)"                     # "distribuição: DD/MM"
    r"(\d{2}/\d{2}/\d{4})"
)

# Número de processo na capa (cabeçalho do documento)
_RE_PROCESSO_CABECALHO = re.compile(
    r"(?:Processo|Autos?|N[oº°]\.?|Nº\s+do\s+Processo)[:\s]+"
    r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Partes — reclamante e reclamada (HIGH, via rótulo no cabeçalho)
# ---------------------------------------------------------------------------
# ^ com re.MULTILINE âncora ao início da linha — evita capturar
# "Advogado do Reclamante:" como rótulo de parte.
_RE_NOME_RECLAMANTE = re.compile(
    r"(?im)^\s*(?:Reclamante|Autor[ao]?|Exequente|Parte\s+[Aa]utora|Empregad[oa]"
    r"|Polo\s+Ativo|Demandante)\s*:\s*([^\n\r]{3,100})"
)
_RE_NOME_RECLAMADA = re.compile(
    r"(?im)^\s*(?:Reclamad[ao]|R[eé](?:u|a)?|Executad[ao]|RE|Parte\s+[Pp]assiva|Empregadora?"
    r"|Polo\s+Passivo|Demandad[ao])\s*:\s*([^\n\r]{3,100})"
)
# Remove sufixo "CPF/RG/CNPJ: ..." que aparece após vírgula na mesma linha
_RE_SUFIXO_DOCUMENTO = re.compile(
    r"\s*,\s*(?:CPF|RG|CNPJ)\b.*$", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# natureza_reclamada — "fazenda_publica" | "privada"
# ---------------------------------------------------------------------------
# Fazenda pública: entidades de direito público, autarquias, empresas públicas,
# precatórios (têm prioridade sobre indicadores de privada)
_RE_NATUREZA_FAZENDA = re.compile(
    r"(?i)"
    r"\bmunic[íi]pio\b"
    r"|\bprefeitura\b"
    r"|\bestado\s+de\b"
    r"|\buni[aã]o\s+federal\b"
    r"|\bdistrito\s+federal\b"
    r"|\bautarquia\b"
    r"|\bINSS\b"
    r"|\bfunda[çc][aã]o\s+p[úu]blica\b"
    r"|\bente\s+p[úu]blico\b"
    r"|\bempresa\s+p[úu]blica\b"
    r"|\bsociedade\s+de\s+economia\s+mista\b"
    r"|\bprecat[oó]rio\b"
    r"|\bdireito\s+p[úu]blico\b"
)
# Privada: LTDA, S/A, empresa privada
_RE_NATUREZA_PRIVADA = re.compile(
    r"(?i)"
    r"\bLTDA\.?\b"
    r"|\bS/?A\.?\b"
    r"|\bSA\.?\b"
    r"|\bempresa\s+privada\b"
    r"|\binstitui[çc][aã]o\s+(?:financeira\s+)?privada\b"
    r"|\bpessoa\s+jur[íi]dica\s+de\s+direito\s+privado\b"
    r"|\bEIRELI\b"
    r"|\bEPP\b"
    r"|\bME\.?\b"
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
        """Número CNJ — regex rígido + validação de dígito verificador."""
        from services.jurisprudencia.consistencia.numero_cnj_validator import validar_cnj

        candidato = None

        # Prioridade: cabeçalho explícito
        m = _RE_PROCESSO_CABECALHO.search(self.texto)
        if m:
            candidato = m.group(1)

        # Fallback: primeira ocorrência de padrão CNJ no texto
        if not candidato:
            m = _RE_CNJ.search(self.texto)
            if m:
                candidato = m.group(1)

        if not candidato:
            return

        # Valida dígito verificador — dígito inválido desce para MEDIUM (IA pode corrigir)
        valido, motivo = validar_cnj(candidato)
        if valido:
            self._set_high("numero_processo", candidato)
        else:
            print(f"[PRE-EXTRACT] numero_processo MEDIUM (dígito inválido): {motivo}", flush=True)
            self._set_medium("numero_processo", candidato)

    def _extract_data_sentenca(self):
        """Data da sentença — prioriza assinatura digital PJe."""
        # Prioridade máxima: assinatura digital (mais recente)
        data_ass = self._ultima_data_assinatura()
        if data_ass:
            self._set_high("data_sentenca", data_ass)
            return
        # Fallback 1: "Publicado em DD/MM/AAAA"
        m = re.search(
            r"(?i)publicad[oa]\s+em\s+(\d{2}/\d{2}/\d{4})", self.texto
        )
        if m:
            self._set_high("data_sentenca", m.group(1))
            return
        # Fallback 2: marcadores diretos de sentença + dd/mm/aaaa
        m = _RE_DATA_SENTENCA.search(self.texto)
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

    def _extract_vara_trabalho(self):
        """Vara do Trabalho — 'Nª Vara do Trabalho de [Cidade]' (HIGH: padrão jurídico específico)."""
        m = _RE_VARA_TRABALHO.search(self.texto)
        if m:
            vara = m.group(1).strip()
            # Apara sufixos de UF: '/MG', '-PR', ' - SP', etc.
            vara = re.sub(r"\s*[-/]\s*[A-Z]{2}$", "", vara).strip()
            # Rejeita captura sem cidade — split case-insensitive em "de"
            partes = re.split(r"\bde\b", vara, maxsplit=1, flags=re.IGNORECASE)
            if len(partes) == 2 and partes[1].strip():
                self._set_high("vara_trabalho", vara)

    def _extract_juiz_responsavel(self):
        """Juiz(a) responsável — rótulo 'Juiz(a) do Trabalho: Dr(a). Nome' (HIGH)."""
        m = _RE_JUIZ_LABEL.search(self.texto)
        if m:
            nome = m.group(1).strip().rstrip(".")
            # Apara continuação de frase: para na primeira palavra puramente minúscula ≥4 chars
            # (ex: "nesta", "desta", "pelo") que não seria parte de um nome próprio.
            # Partículas de nome ("de", "da", "do") têm ≤3 chars → não são afetadas.
            nome = re.sub(r"\s+[a-záéíóúâêîôûãõàü]{4,}.*$", "", nome)
            # Rejeita capturas com menos de dois tokens (evita capturar só "Dr." ou artigos)
            if len(nome.split()) >= 2:
                self._set_high("juiz_responsavel", nome)

    def _extract_partes(self):
        """Nomes das partes via rótulo explícito no cabeçalho (HIGH)."""
        for campo, regex in (
            ("reclamante", _RE_NOME_RECLAMANTE),
            ("reclamada",  _RE_NOME_RECLAMADA),
        ):
            m = regex.search(self.texto)
            if m:
                nome = _RE_SUFIXO_DOCUMENTO.sub("", m.group(1)).strip().rstrip(".,")
                if len(nome) >= 3:
                    self._set_high(campo, nome)

    def _extract_advogados(self):
        """Advogados das partes — rótulos 'Adv. do Reclamante:' / 'Adv. da Reclamada:' (HIGH)."""
        for campo, regex in (
            ("advogado_reclamante", _RE_ADV_RECLAMANTE),
            ("advogado_reclamada", _RE_ADV_RECLAMADA),
        ):
            m = regex.search(self.texto)
            if m:
                nome = m.group(1).strip().rstrip(".")
                if len(nome.split()) >= 2:
                    self._set_high(campo, nome)

    # ── Extratores MEDIUM ────────────────────────────────────────────────────

    def _extract_data_ajuizamento(self):
        m = _RE_AJUIZAMENTO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_ajuizamento", norm)

    def _extract_data_admissao(self):
        # Tenta formato slash primeiro (DD/MM/AAAA)
        m = _RE_ADMISSAO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_admissao", norm)
                return
        # Fallback: data por extenso ("admitido em 15 de janeiro de 2020")
        m = _RE_ADMISSAO_EXTENSO.search(self.texto)
        if m:
            norm = self._data_extenso_para_slash(m.group(1))
            if norm:
                self._set_medium("data_admissao", norm)

    def _extract_data_demissao(self):
        # Tenta formato slash primeiro (DD/MM/AAAA) — padrões diretos
        m = _RE_DEMISSAO.search(self.texto)
        if m:
            norm = self._normalizar_data(m.group(1))
            if norm:
                self._set_medium("data_demissao", norm)
                return
        # Fallback: padrão invertido "Em DD/MM/AAAA, [frase] foi dispensado / ocorreu rescisão"
        # _RE_DEMISSAO_INVERTIDA tem 2 grupos (alternativas)
        m = _RE_DEMISSAO_INVERTIDA.search(self.texto)
        if m:
            captured = next((g for g in m.groups() if g), None)
            if captured:
                norm = self._normalizar_data(captured)
                if norm:
                    self._set_medium("data_demissao", norm)
                    return
        # Fallback: data por extenso ("dispensado em 30 de junho de 2023")
        m = _RE_DEMISSAO_EXTENSO.search(self.texto)
        if m:
            norm = self._data_extenso_para_slash(m.group(1))
            if norm:
                self._set_medium("data_demissao", norm)

    def _extract_valor_causa(self):
        """Valor da causa — labels, fórmulas petição e forma narrativa (MEDIUM)."""
        m = _RE_VALOR_CAUSA.search(self.texto)
        if m:
            raw = m.group(1).strip().rstrip(".,")
            # Normaliza para "R$ X.XXX,XX"
            valor = f"R$ {raw}"
            self._set_medium("valor_causa", valor)

    def _extract_salario_base(self):
        """Extrai salário — filtra valores implausíveis."""
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
        elif _RE_INPC.search(self.texto):
            self._set_medium("indice_correcao", "INPC")

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
        elif _RE_RESCISAO_CULPA_RECIPROCA.search(self.texto):
            self._set_medium("motivo_rescisao", "Culpa recíproca")
        elif _RE_RESCISAO_SJC.search(self.texto):
            self._set_medium("motivo_rescisao", "Sem justa causa")
        elif _RE_RESCISAO_JC.search(self.texto):
            self._set_medium("motivo_rescisao", "Com justa causa")
        elif _RE_RESCISAO_PEDIDO.search(self.texto):
            self._set_medium("motivo_rescisao", "Pedido de demissão")
        elif _RE_RESCISAO_TERMINO.search(self.texto):
            self._set_medium("motivo_rescisao", "Término de contrato")
        elif _RE_RESCISAO_APOSENTADORIA.search(self.texto):
            self._set_medium("motivo_rescisao", "Aposentadoria")
        elif _RE_RESCISAO_ACORDO.search(self.texto):
            self._set_medium("motivo_rescisao", "Acordo rescisório")
        elif _RE_RESCISAO_FALECIMENTO.search(self.texto):
            self._set_medium("motivo_rescisao", "Falecimento")

    def _extract_tipo_contrato(self):
        # HIGH: terminologia de duração — inequívoca (ordem importa: específico antes de CLT)
        if _RE_CONTRATO_EXPERIENCIA.search(self.texto):
            self._set_high("tipo_contrato", "Experiência")
        elif _RE_CONTRATO_PRAZO_DET.search(self.texto):
            self._set_high("tipo_contrato", "Prazo determinado")
        elif _RE_CONTRATO_PRAZO_INDET.search(self.texto):
            self._set_high("tipo_contrato", "Prazo indeterminado")
        elif _RE_CONTRATO_INTERMITENTE.search(self.texto):
            self._set_high("tipo_contrato", "Intermitente")
        elif _RE_CONTRATO_APRENDIZ.search(self.texto):
            self._set_high("tipo_contrato", "Aprendiz")
        elif _RE_CONTRATO_TEMPORARIO.search(self.texto):
            self._set_high("tipo_contrato", "Temporário")
        # MEDIUM: natureza jurídica — depende de contexto circundante
        elif _RE_CONTRATO_PEJOTA.search(self.texto):
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
        # Jornada 12x36 → divisor padrão 220
        if _RE_JORNADA_12X36.search(self.texto):
            self._set_medium("divisor_horas", "220")
            return
        # Inferência pela jornada semanal (forma direta ou invertida)
        # _RE_HORAS_SEMANAIS tem 2 grupos alternativos (forma direta e invertida)
        m = _RE_HORAS_SEMANAIS.search(self.texto)
        if m:
            raw = next((g for g in m.groups() if g is not None), None)
            if raw:
                h_sem = int(raw)
                mapa = {30: "150", 35: "175", 36: "180", 40: "200", 44: "220"}
                div = mapa.get(h_sem)
                if div:
                    self._set_medium("divisor_horas", div)

    def _extract_funcao_reclamante(self):
        """Extrai cargo/função por frases-gatilho; texto livre — MEDIUM."""
        m = _RE_FUNCAO_RECLAMANTE.search(self.texto)
        if m:
            funcao = m.group(1).strip()
            if funcao:
                self._set_medium("funcao_reclamante", funcao)

    def _extract_horario_trabalho(self):
        """Extrai horário de trabalho — '[das/de] HHh às HHh [com X h de intervalo]'.
        Fallback: formato 'Entrada: HHhMM Saída: HHhMM'.
        """
        m = _RE_HORARIO_TRABALHO.search(self.texto)
        if m:
            horario = m.group(1).strip().rstrip(",;")
            self._set_medium("horario_trabalho", horario)
            return
        # Fallback: formato Entrada/Saída
        m2 = _RE_HORARIO_ENTRADA_SAIDA.search(self.texto)
        if m2:
            horario = f"{m2.group(1)} às {m2.group(2)}"
            self._set_medium("horario_trabalho", horario)

    def _extract_jornada_contratual(self):
        """Extrai jornada contratual — 'X horas diárias/por dia [e Y semanais]'.
        Fallback: padrão 'jornada/carga semanal de Xh' (qualificador implícito).
        """
        m = _RE_JORNADA_CONTRATUAL.search(self.texto)
        if m:
            jornada = m.group(1).strip()
            self._set_medium("jornada_contratual", jornada)
            return
        # Fallback: "jornada semanal de 44h" — qualificador implícito no trigger
        m2 = _RE_JORNADA_SEMANAL.search(self.texto)
        if m2:
            self._set_medium("jornada_contratual", m2.group(1).strip())

    def _extract_natureza_reclamada(self):
        """
        Detecta se a reclamada é da fazenda pública ou empresa privada.
        Fazenda pública tem prioridade — basta um indicador para prevalecer.
        """
        if _RE_NATUREZA_FAZENDA.search(self.texto):
            self._set_medium("natureza_reclamada", "fazenda_publica")
        elif _RE_NATUREZA_PRIVADA.search(self.texto):
            self._set_medium("natureza_reclamada", "privada")

    def _extract_aviso_previo_dias(self):
        # Tenta meses primeiro (mais específico que dias)
        m_meses = _RE_AVISO_MESES.search(self.texto)
        if m_meses:
            meses = int(m_meses.group(1))
            if 1 <= meses <= 3:  # plausibilidade: 1-3 meses (30-90 dias)
                self._set_medium("aviso_previo_dias", f"{meses * 30} dias")
                return
        # Forma direta ou invertida em dias
        m = _RE_AVISO_DIAS.search(self.texto) or _RE_AVISO_DIAS_INV.search(self.texto)
        if m:
            # _RE_AVISO_DIAS tem grupo 1 (número fora de parênteses)
            # e grupo 2 (número dentro de parênteses "(60 dias)")
            raw = next((g for g in m.groups() if g is not None), None)
            if raw is None:
                return
            dias = int(raw)
            if 20 <= dias <= 90:  # plausibilidade
                self._set_medium("aviso_previo_dias", f"{dias} dias")

    def _extract_aviso_previo_tipo(self):
        # indenizado tem precedência: se o texto menciona ambas as formas, a forma
        # indenizada é a determinada na sentença (trabalhado pode aparecer no histórico)
        if _RE_AVISO_INDENIZADO.search(self.texto):
            self._set_high("aviso_previo_tipo", "indenizado")
        elif _RE_AVISO_TRABALHADO.search(self.texto):
            self._set_high("aviso_previo_tipo", "trabalhado")

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
            self._extract_data_sentenca,
            self._extract_justica_gratuita,
            self._extract_tipo_rito,
            self._extract_vara_trabalho,
            self._extract_aviso_previo_tipo,
            self._extract_juiz_responsavel,
            self._extract_advogados,
            self._extract_partes,
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
            self._extract_valor_causa,
            self._extract_indice_correcao,
            self._extract_juros_mora,
            self._extract_motivo_rescisao,
            self._extract_tipo_contrato,
            self._extract_divisor_horas,
            self._extract_aviso_previo_dias,
            self._extract_funcao_reclamante,
            self._extract_horario_trabalho,
            self._extract_jornada_contratual,
            self._extract_natureza_reclamada,
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

_ROTULOS_HIGH = {
    "numero_processo":      "Número do processo (CNJ)",
    "data_sentenca":        "Data da sentença",
    "justica_gratuita":     "Justiça gratuita",
    "tipo_rito":            "Tipo de rito",
    "vara_trabalho":        "Vara do Trabalho",
    "aviso_previo_tipo":    "Tipo de aviso prévio",
    "tipo_contrato":        "Tipo de contrato",
    "juiz_responsavel":     "Juiz(a) responsável",
    "advogado_reclamante":  "Advogado do reclamante",
    "advogado_reclamada":   "Advogado da reclamada",
    "reclamante":           "Nome do reclamante",
    "reclamada":            "Nome da reclamada",
}

_ROTULOS_MEDIUM = {
    "data_admissao":      "Data de admissão",
    "data_demissao":      "Data de demissão",
    "data_ajuizamento":   "Data de ajuizamento",
    "salario_base":       "Salário base",
    "valor_causa":        "Valor da causa",
    "indice_correcao":    "Índice de correção monetária",
    "juros_mora":         "Juros de mora",
    "motivo_rescisao":    "Motivo da rescisão",
    "tipo_contrato":      "Tipo de contrato",
    "divisor_horas":      "Divisor de horas extras",
    "aviso_previo_dias":  "Aviso prévio (dias)",
    "funcao_reclamante":  "Função/cargo do reclamante",
    "horario_trabalho":    "Horário de trabalho",
    "jornada_contratual":  "Jornada contratual",
    "natureza_reclamada":  "Natureza da reclamada",
}


def build_prompt_context(pre_fields: dict) -> str:
    """
    Constrói o bloco de contexto pré-extraído para injeção no prompt da IA.

    Seção HIGH  — alta confiança (≥95%): instrui a IA a usar esses valores
                  diretamente, sem reextração. Economiza tokens e elimina
                  alucinação para campos como numero_processo e data_sentenca.
    Seção MEDIUM — média confiança (~80%): âncoras para reduzir alucinação;
                  a IA confirma no texto antes de usar.
    """
    high   = pre_fields.get("high", {})
    medium = pre_fields.get("medium", {})
    if not high and not medium:
        return ""

    linhas = []

    if high:
        linhas.append("CAMPOS CONFIRMADOS — ALTA CONFIANÇA (use estes valores diretamente, não reextraia):")
        for campo, valor in high.items():
            rotulo = _ROTULOS_HIGH.get(campo, campo)
            linhas.append(f"  [OK] {rotulo}: {valor}")
        linhas.append("")

    if medium:
        linhas.append("VALORES PRÉ-EXTRAÍDOS — MÉDIA CONFIANÇA (confirme no texto antes de usar):")
        for campo, valor in medium.items():
            rotulo = _ROTULOS_MEDIUM.get(campo, campo)
            linhas.append(f"  • {rotulo}: {valor}")
        linhas.append("Se o texto confirmar estes valores, use-os. Se contradizer, prefira o que o texto diz explicitamente.")

    return "\n".join(linhas)


def build_anchor_section(medium_fields: dict) -> str:
    """Mantido para compatibilidade — prefira build_prompt_context."""
    return build_prompt_context({"medium": medium_fields})
"""
extractors.py — Limpeza de texto, regex e pré-processamento do Laboratório (Passo 2).

Funções extraídas de learning_engine.py:
  - Regex de liquidação: regex_verbas, regex_indice, regex_juros, regex_divisor.
  - liquidacao_from_text: monta dict de liquidação a partir de texto bruto.
  - Regex de manifestação: extrair_fundamentos_juridicos, extrair_discrepancias_perita.
  - Limpeza / regex de cabeçalho e autuação: remover_linha_autuacao, contexto_eh_autuacao.
  - Regex de cabeçalho PJe (título executivo): CABECALHO_PJE_CHARS, texto_apos_cabecalho_pje,
    tem_indicador_2grau_apos_cabecalho.

Canonização de verbas: permanece em services.legal_engine.rule_base.LegalRule._canonizar_verba.

Upgrade jurídico-pericial: VERBAS_PJE_CALC_NOMENCLATURA e INSTRUCOES_EXTRAÇÃO_VERBAS_DISPOSITIVO
para extração agressiva de verbas (DISPOSITIVO/CONCLUSÃO, reflexos, nomenclatura PJe-Calc).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ── Nomenclatura padrão PJe-Calc (alias → nome oficial para saída JSON) ──────────
# Use estes nomes no array verbas_deferidas em vez de variações coloquiais.

VERBAS_PJE_CALC_NOMENCLATURA: Dict[str, str] = {
    "art. 477": "Multa Art. 477 CLT",
    "art 477": "Multa Art. 477 CLT",
    "art. 467": "Multa Art. 467 CLT",
    "art 467": "Multa Art. 467 CLT",
    "13o": "13º Salário Proporcional",
    "13º": "13º Salário Proporcional",
    "13°": "13º Salário Proporcional",
    "décimo terceiro": "13º Salário Proporcional",
    "pagamento de aviso": "Aviso Prévio Indenizado",
    "aviso previo": "Aviso Prévio Indenizado",
    "aviso prévio indenizado": "Aviso Prévio Indenizado",
    "aviso prévio trabalhado": "Aviso Prévio Trabalhado",
    "aviso prévio proporcional": "Aviso Prévio Proporcional",
    "saldo salarial": "Saldo de Salário",
    "saldo de salario": "Saldo de Salário",
    "13 proporcional": "13º Salário Proporcional",
    "13º proporcional": "13º Salário Proporcional",
    "decimo terceiro proporcional": "13º Salário Proporcional",
    "13 integral": "13º Salário Integral",
    "ferias proporcionais": "Férias Proporcionais + 1/3",
    "ferias + 1/3": "Férias Proporcionais + 1/3",
    "ferias vencidas": "Férias Vencidas + 1/3",
    "ferias em dobro": "Férias em Dobro",
    "ferias indenizadas": "Férias Indenizadas",
    "horas extras": "Horas Extras",
    "hora extra": "Horas Extras",
    "adicional noturno": "Adicional Noturno",
    "insalubridade": "Adicional de Insalubridade",
    "periculosidade": "Adicional de Periculosidade",
    "intervalo intrajornada": "Intervalo Intrajornada",
    "multa art 467": "Multa art. 467 CLT",
    "multa art 477": "Multa art. 477 CLT",
    "multa 467": "Multa art. 467 CLT",
    "multa 477": "Multa art. 477 CLT",
    "fgts + 40%": "FGTS + Multa de 40%",
    "fgts e multa": "FGTS + Multa de 40%",
    "multa 40% fgts": "Multa de 40% do FGTS",
    "dsr": "DSR",
    "repouso semanal": "DSR",
}

# Instruções jurídico-periciais para injetar no prompt de extração de sentença.
# Objetivo: popular o Quadro de Verbas com precisão (evitar verbas_deferidas vazio).
INSTRUCOES_EXTRAÇÃO_VERBAS_DISPOSITIVO: str = """
REGRAS DE PENSAMENTO JURÍDICO — EXTRAÇÃO AGRESSIVA DE VERBAS

1) Identificação do DISPOSITIVO / CONCLUSÃO
   - Priorize o tópico "DISPOSITIVO" ou "CONCLUSÃO". Toda verba que constar lá como PROCEDENTE ou PROCEDENTE EM PARTE deve entrar em verbas_deferidas.
   - Nunca retorne verbas_deferidas: [] se o memorial de análise descreveu deferimentos.

2) Mapeamento de verbas típicas (buscar ativamente)
   - Verbas rescisórias: Saldo de Salário, Aviso Prévio (indenizado/trabalhado/proporcional), 13º proporcional/integral, Férias + 1/3 (simples, em dobro ou proporcionais).
   - Indenizações: Multas dos Arts. 467 e 477 da CLT, Multa de 40% do FGTS.
   - Cotas e horas: Horas Extras, Adicional Noturno, Insalubridade, Periculosidade, Intervalo Intrajornada.

3) Lógica de reflexos (essencial)
   - Se a sentença disser "Horas extras com reflexos em FGTS e 13º", crie o item "Horas Extras" e liste os reflexos no campo observacoes ou no array reflexos com status deferido.
   - Reflexos típicos: DSR, Aviso Prévio, Férias + 1/3, 13º Salário, FGTS + 40%.

4) Tratamento de Embargos de Declaração
   - Se o texto for de Embargos de Declaração, extraia o que foi acrescido ou modificado na sentença original, mantendo a integridade do que já havia sido deferido.

5) Requisitos do JSON de saída
   - Se o valor for "a apurar em liquidação", mantenha o campo valor como null, mas o nome da verba e status_final: "deferido" (ou "mantida") devem estar presentes.
   - Use a nomenclatura padrão do PJe-Calc (ex.: "Aviso Prévio Indenizado" em vez de "Pagamento de aviso"; "Horas Extras", "Multa art. 477 CLT", "FGTS + Multa de 40%").
"""

# ── Regex de liquidação (texto → verbas, índice, juros, divisor) ─────────────────
# Padrões expandidos para cobertura jurídico-pericial (rescisórias, indenizações, horas).

_REGEX_VERBAS_PADROES = [
    r"horas?\s*extras?",
    r"adicional\s*noturno",
    r"intervalo\s*intrajornada",
    r"insalubridade",
    r"periculosidade",
    r"f[eé]rias(?:\s*\+?\s*1/3)?",
    r"13[°º]?\s*sal[aá]rio",
    r"d[eé]cimo\s*terceiro",
    r"aviso\s*pr[eé]vio(?:\s*indenizado|\s*trabalhado|\s*proporcional)?",
    r"saldo\s*(?:de\s*)?sal[aá]rio",
    r"saldo\s*salarial",
    r"multa\s*art\.?\s*467",
    r"multa\s*art\.?\s*477",
    r"multa\s*467",
    r"multa\s*477",
    r"dano\s*moral",
    r"FGTS(?:\s*\+\s*40%|\s*e\s*multa)?",
    r"multa\s*(?:de\s*)?40%\s*(?:do\s*)?fgts",
    r"dsr",
    r"repouso\s*semanal\s*remunerado",
]


def regex_verbas(texto: str) -> List[str]:
    """Detecta menções a verbas típicas no texto (liquidação ou sentença)."""
    encontradas: List[str] = []
    for p in _REGEX_VERBAS_PADROES:
        if re.search(p, texto, re.IGNORECASE):
            if p not in encontradas:
                encontradas.append(p)
    return encontradas


def regex_indice(texto: str) -> Optional[str]:
    m = re.search(r"\b(IPCAE|SELIC|TR|IPCA[_\-]?E|TRD)\b", texto, re.IGNORECASE)
    return m.group(0).upper() if m else None


def regex_juros(texto: str) -> Optional[str]:
    m = re.search(r"\b(TRD_SIMPLES|SELIC\s*simples|juros\s+de\s+\d[\d,\.]+\s*%)\b", texto, re.IGNORECASE)
    return m.group(0) if m else None


def regex_divisor(texto: str) -> Optional[str]:
    m = re.search(r"\b(150|180|200|220)\s*(?:h(?:oras?)?|\/\s*m[eê]s)?\b", texto, re.IGNORECASE)
    return m.group(1) if m else None


def liquidacao_from_text(texto: str) -> Dict[str, Any]:
    """
    Constrói o mesmo formato de extração de liquidação (PDF) a partir de texto bruto.
    Usado quando a liquidação foi extraída do PDF integral pelo PJe Timeline Extractor.
    """
    if not (texto or "").strip():
        return {
            "tipo": "texto",
            "verbas_calculadas": [],
            "indice_correcao": None,
            "juros_mora": None,
            "divisor_horas": None,
            "erro": "Texto vazio",
        }
    return {
        "tipo": "texto",
        "texto_bruto": (texto or "")[:3000],
        "verbas_calculadas": regex_verbas(texto),
        "indice_correcao": regex_indice(texto),
        "juros_mora": regex_juros(texto),
        "divisor_horas": regex_divisor(texto),
        "erro": None,
    }


# ── Regex de manifestação (fundamentos jurídicos e discrepâncias) ───────────────

def extrair_fundamentos_juridicos(texto: str) -> List[str]:
    """Identifica referências jurídicas mencionadas na manifestação."""
    padroes = [
        (r"S[uú]mula\s+n[°º]?\s*\d+\s+(?:do\s+)?TST", "Súmula TST"),
        (r"S[uú]mula\s+n[°º]?\s*\d+\s+(?:do\s+)?STF", "Súmula STF"),
        (r"OJ\s+n[°º]?\s*\d+", "OJ"),
        (r"art(?:igo)?\.?\s*\d+[,\s\w]*(?:da\s+CLT|CLT)", "Art. CLT"),
        (r"ADC\s+\d+", "ADC"),
        (r"S[uú]mula\s+n[°º]?\s*\d+", "Súmula"),
        (r"Lei\s+n[°º]?\s*[\d\.]+", "Lei"),
        (r"Decreto[- ]Lei\s+n[°º]?\s*[\d\.]+", "Decreto-Lei"),
    ]
    encontrados = []
    for padrao, _ in padroes:
        for m in re.finditer(padrao, texto, re.IGNORECASE):
            ref = m.group(0).strip()
            if ref not in encontrados:
                encontrados.append(ref)
    return encontrados[:20]


def extrair_discrepancias_perita(texto: str) -> List[str]:
    """
    Tenta identificar frases que descrevem divergências levantadas pela perita.
    Heurística: sentenças com palavras de contraste jurídico.
    """
    palavras_chave = [
        r"diverge?\w*", r"incorreto\w*", r"equivocado\w*", r"erro\w*",
        r"deveria\w*", r"correto\w*", r"corrij\w*", r"recalcul\w*",
        r"indevido\w*", r"desconsider\w*", r"incluir\w*", r"acrescentar\w*",
    ]
    regex = re.compile("|".join(palavras_chave), re.IGNORECASE)
    linhas = texto.split("\n")
    discrepancias = []
    for linha in linhas:
        linha = linha.strip()
        if len(linha) > 20 and regex.search(linha):
            discrepancias.append(linha[:250])
        if len(discrepancias) >= 10:
            break
    return discrepancias


# ── Limpeza e regex de cabeçalho / Data da Autuação ─────────────────────────────

_RE_CONTEXTO_AUTUACAO = re.compile(
    r"(?i)data\s+da\s+autua[çc][ãa]o|autua[çc][ãa]o\s*[:.]",
)

_RE_LINHA_DATA_AUTUACAO = re.compile(
    r"(?im)^.*Data\s+da\s+Autua[çc][ãa]o.*$",
)


def contexto_eh_autuacao(texto: str, posicao_inicio_match: int) -> bool:
    """Retorna True se a LINHA que contém a data contiver 'Data da Autuação' ou 'Autuação'."""
    if not texto or posicao_inicio_match < 0:
        return False
    linha_inicio = texto.rfind("\n", 0, posicao_inicio_match) + 1
    linha_fim = texto.find("\n", posicao_inicio_match)
    if linha_fim == -1:
        linha_fim = len(texto)
    linha = texto[linha_inicio:linha_fim].lower()
    return bool(_RE_CONTEXTO_AUTUACAO.search(linha))


def remover_linha_autuacao(texto: str) -> str:
    """Remove do texto a linha que contém 'Data da Autuação', para não capturá-la nas regex de data."""
    if not texto:
        return texto
    return _RE_LINHA_DATA_AUTUACAO.sub("", texto)


# ── Regex de cabeçalho PJe (título executivo — evita "Tribunal Regional" no header) ─

CABECALHO_PJE_CHARS = 1000

_RE_TEXTO_2GRAU_FORA_CABECALHO = re.compile(
    r"(?:recurso\s+ordinário|relator\s*:|acórdão|acordao)",
    re.IGNORECASE,
)


def texto_apos_cabecalho_pje(texto: str) -> str:
    """Retorna o trecho após os primeiros CABECALHO_PJE_CHARS caracteres, ou o texto inteiro se for curto."""
    if not texto:
        return ""
    if len(texto) > CABECALHO_PJE_CHARS:
        return texto[CABECALHO_PJE_CHARS:]
    return texto


def tem_indicador_2grau_apos_cabecalho(texto: Optional[str]) -> bool:
    """Indica se há indicador de 2º grau (recurso ordinário, relator, acórdão) no texto após o cabeçalho PJe."""
    if not (texto or "").strip():
        return False
    trecho = texto_apos_cabecalho_pje(texto)
    return bool(trecho and _RE_TEXTO_2GRAU_FORA_CABECALHO.search(trecho))


__all__ = [
    "regex_verbas",
    "VERBAS_PJE_CALC_NOMENCLATURA",
    "INSTRUCOES_EXTRAÇÃO_VERBAS_DISPOSITIVO",
    "regex_indice",
    "regex_juros",
    "regex_divisor",
    "liquidacao_from_text",
    "extrair_fundamentos_juridicos",
    "extrair_discrepancias_perita",
    "remover_linha_autuacao",
    "contexto_eh_autuacao",
    "CABECALHO_PJE_CHARS",
    "texto_apos_cabecalho_pje",
    "tem_indicador_2grau_apos_cabecalho",
]

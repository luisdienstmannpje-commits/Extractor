"""
explanation_engine.py — v5.3
Geração de texto jurídico explicativo por regra aplicada.
"""
from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional

# ── Textos padrão da seção "II. CRITÉRIOS UTILIZADOS NOS CÁLCULOS" (Parecer Técnico) ──
# Redação oficial dos peritos da empresa; usados como bloco fixo no parecer.
TEXTOS_PADRAO_CRITERIOS_PARECER: Dict[str, str] = {
    "correcao": (
        "Atualização monetária: Apuração da atualização monetária incidente sobre as parcelas deferidas, "
        "adotando-se, em observância à ADC 58 do STF, os índices de correção monetária IPCA-E na fase "
        "pré-judicial e, a partir da citação, a incidência da taxa SELIC, afastada a aplicação da TR para "
        "períodos posteriores à decisão do STF."
    ),
    "inss": (
        "Contribuições Previdenciárias - Cota parte do Reclamante: Apuração conforme indicado "
        "no Decreto 3.048/99 (artigos 198 e 276, § 4º) e item III da Súmula 368 do TST."
    ),
    "irrf": (
        "Imposto de Renda: calculado pela técnica dos rendimentos acumulados (RRA), conforme previsto "
        "na Instrução Normativa 1500/14 da Receita Federal do Brasil, em substituição à IN 1.127/11 "
        "que foi revogada."
    ),
}


def obter_textos_padrao_criterios_parecer() -> Dict[str, str]:
    """Retorna os textos oficiais para a seção II do Parecer Técnico."""
    return dict(TEXTOS_PADRAO_CRITERIOS_PARECER)


_NIVEL_NORMATIVO: Dict[int, str] = {
    10: "STF", 20: "Súmula TST", 30: "Orientação Jurisprudencial TST",
    40: "CLT", 50: "Consistência",
}

def _verbas_com_nome(dados: dict, pattern: str) -> List[str]:
    verbas = dados.get("verbas_deferidas") or []
    encontradas = []
    for v in verbas:
        nome = v.get("nome", "") if isinstance(v, dict) else getattr(v, "nome", "")
        if re.search(pattern, nome, re.IGNORECASE):
            encontradas.append(nome)
    return encontradas

def _nivel_normativo(prioridade: int) -> str:
    for limiar, nome in sorted(_NIVEL_NORMATIVO.items()):
        if prioridade <= limiar:
            return nome
    return "Consistência"

def _template_adc58(dados):
    indice = dados.get("indice_correcao") or "IPCA-E/SELIC"
    juros = dados.get("juros_mora") or "1% ao mês"
    return (
        "Apuração da atualização monetária incidente sobre as parcelas deferidas, "
        "adotando-se, em observância à ADC 58 do STF, os índices de correção monetária "
        "IPCA-E na fase pré‑judicial e, a partir da citação, a incidência da taxa SELIC. "
        f"Juros de mora de {juros}, afastada a aplicação da TR para períodos posteriores "
        "à decisão do STF, mantendo-se o critério IPCA-E/SELIC fixado no título."
    )

def _template_sumula264(dados):
    p = r"horas?\s*extras?|adicional\s*noturno|insalubridade|periculosidade"
    verbas_he = _verbas_com_nome(dados, p)
    mencao_verbas = f" ({', '.join(verbas_he)})" if verbas_he else ""
    divisor = dados.get("divisor_horas")
    divisor_txt = f"{divisor}" if divisor else "aplicável ao caso concreto"
    # tenta capturar um percentual típico das verbas de HE
    verbas = dados.get("verbas_deferidas") or []
    percentual = None
    for v in verbas:
        if not isinstance(v, dict):
            continue
        nome = v.get("nome", "")
        if re.search(r"horas?\\s*extras?", nome, re.IGNORECASE):
            percentual = v.get("percentual") or percentual
    pct_txt = f"{percentual}" if percentual else "50"
    return (
        "Apuração das horas extras e adicionais" + mencao_verbas +
        f", com reflexos em DSR, férias acrescidas de 1/3, 13º salário e FGTS, "
        "utilizadas as Súmulas 264 e 347 do TST, observado o divisor "
        f"{divisor_txt}, com percentual de {pct_txt}%. "
        "Os reflexos incidem apenas nas parcelas expressamente deferidas "
        "no título executivo."
    )

def _template_sumula305(dados):
    ap_dias = dados.get("aviso_previo_dias")
    mencao  = f" ({ap_dias} dias)" if ap_dias else ""
    return (
        "Apuração da verba de FGTS incidente sobre o aviso prévio indenizado"
        f"{mencao}, com reflexos na base de cálculo da indenização de 40%, "
        "nos termos da Súmula 305 do TST, ainda que não haja efetiva prestação "
        "de serviços no período correspondente."
    )

def _template_sumula331(dados):
    reclamada = dados.get("reclamada") or "a empresa tomadora de serviços"
    return (
        f"Reconhecimento da responsabilidade subsidiária de {reclamada} pelas obrigações "
        "trabalhistas inadimplidas pela prestadora de serviços, em decorrência da "
        "terceirização, nos termos da Súmula 331 do TST, limitada aos títulos "
        "expressamente deferidos na sentença."
    )

def _template_oj42(dados):
    ap_dias = dados.get("aviso_previo_dias")
    mencao  = f" ({ap_dias} dias)" if ap_dias else ""
    return (
        "Apuração da multa de 40% do FGTS, excluindo-se da base de cálculo o aviso "
        f"prévio indenizado{mencao}, em observância à OJ 42 da SDI‑I do TST, de modo "
        "que a indenização rescisória recaia apenas sobre as parcelas de natureza "
        "salarial efetivamente devidas."
    )

def _template_oj195(dados):
    return (
        "Apuração da verba de férias indenizadas, sem incidência de FGTS, uma vez "
        "que as férias não gozadas, convertidas em pecúnia, não integram a base de "
        "cálculo do FGTS, em conformidade com a OJ 195 da SDI‑I do TST."
    )

def _template_oj394(dados):
    verbas_he = _verbas_com_nome(dados, r"horas?\s*extras?|adicional\s*noturno")
    mencao = f" ({', '.join(verbas_he)})" if verbas_he else ""
    return (
        "Apuração do repouso semanal remunerado majorado por horas extras"
        f"{mencao}, observando-se que tais valores não refletem em férias, "
        "13º salário nem FGTS, para evitar bis in idem, nos termos da OJ 394 "
        "da SDI‑I do TST."
    )

def _template_art467(dados):
    salario = dados.get("salario_base")
    mencao  = f" (base: R$ {salario})" if salario else ""
    return (
        "Apuração da multa prevista no art. 467 da CLT, correspondente a 50% "
        f"das verbas rescisórias incontroversas{mencao}, em razão do não pagamento "
        "no prazo legal, com incidência apenas sobre os títulos expressamente "
        "indicados na decisão."
    )

def _template_art477(dados):
    salario = dados.get("salario_base")
    mencao  = f" (equivalente a R$ {salario})" if salario else " (equivalente a 1 salário)"
    return (
        "Apuração da multa do art. 477, § 6º, da CLT, em razão do atraso no "
        f"pagamento das verbas rescisórias{mencao}, calculada sobre a remuneração "
        "mensal do trabalhador, conforme parâmetros fixados na sentença."
    )

def _template_art487(dados):
    ap_dias = dados.get("aviso_previo_dias")
    mencao  = f"{ap_dias} dias" if ap_dias else "proporcional ao tempo de serviço"
    return (
        "Apuração do aviso prévio indenizado pelo período de "
        f"{mencao}, com acréscimo de 3 dias por ano de serviço, até o limite de "
        "90 dias, em conformidade com o art. 487 da CLT combinado com a Lei "
        "12.506/2011, observando-se a projeção do aviso nas demais verbas "
        "rescisórias quando expressamente determinado."
    )

def _template_art791a(dados):
    pct  = dados.get("percentual_honorarios")
    tipo = dados.get("honorarios_sucumbenciais")
    jg   = dados.get("justica_gratuita", False)
    partes = []
    if pct:
        partes.append(f"{pct}% sobre o valor da condenação")
    if tipo:
        partes.append(tipo)
    base = f": {', '.join(partes)}" if partes else ""
    obs  = " Suspensos em razão da gratuidade judiciária." if jg else ""
    return (
        "Apuração dos honorários advocatícios sucumbenciais fixados"
        f"{base}, nos termos do art. 791‑A da CLT (Reforma Trabalhista de 2017), "
        "calculados sobre a base de condenação definida no título executivo."
        f"{obs}"
    )

def _template_cnj(dados):
    num = dados.get("numero_processo") or "informado"
    return (
        f"Validação formal do número do processo {num}, de acordo com o dígito "
        "verificador previsto na Resolução CNJ 65/2008, assegurando a correta "
        "identificação do feito para fins de liquidação."
    )

def _template_deduplicator(dados):
    return (
        "Apuração das verbas deferidas com deduplicação por nome canônico e "
        "período de apuração, de modo a consolidar parcelas eventualmente "
        "repetidas e garantir a unicidade da base de cálculo utilizada na "
        "liquidação."
    )

_TEMPLATES: Dict[str, Any] = {
    "ADC_58_STF":            _template_adc58,
    "SUMULA_264_TST":        _template_sumula264,
    "SUMULA_305_TST":        _template_sumula305,
    "SUMULA_331_TST":        _template_sumula331,
    "OJ_42_SDI1_TST":        _template_oj42,
    "OJ_195_SDI1_TST":       _template_oj195,
    "OJ_394_SDI1_TST":       _template_oj394,
    "ART_467_CLT":           _template_art467,
    "ART_477_CLT":           _template_art477,
    "ART_487_CLT_LEI_12506": _template_art487,
    "ART_791A_CLT":          _template_art791a,
    "CNJ_DIGITO_VERIFICADOR":_template_cnj,
    "VERBA_DEDUPLICATOR":    _template_deduplicator,
}

class ExplanationEngine:
    @staticmethod
    def gerar(resultado_engine: dict, dados: dict) -> List[Dict[str, Any]]:
        memorial: List[dict] = resultado_engine.get("memorial_juridico") or []
        explicacoes: List[Dict[str, Any]] = []
        for entrada in memorial:
            regra_id   = entrada.get("id", "")
            titulo     = entrada.get("titulo", regra_id)
            base_legal = entrada.get("base_legal", "")
            prioridade = entrada.get("prioridade", 50)
            descricao  = entrada.get("descricao", "")
            texto, tem_template = ExplanationEngine._gerar_texto(regra_id, dados, descricao)
            explicacoes.append({
                "regra_id":     regra_id,
                "titulo":       titulo,
                "base_legal":   base_legal,
                "nivel":        _nivel_normativo(prioridade),
                "prioridade":   prioridade,
                "explicacao":   texto,
                "tem_template": tem_template,
            })
        explicacoes.sort(key=lambda x: x["prioridade"])
        print(f"[EXPLANATION] {len(explicacoes)} explicação(ões) gerada(s)")
        return explicacoes

    @staticmethod
    def _gerar_texto(regra_id, dados, descricao_fallback):
        template = _TEMPLATES.get(regra_id)
        if template is None:
            return descricao_fallback or f"Regra {regra_id} aplicada.", False
        if callable(template):
            try:
                return template(dados), True
            except Exception as e:
                print(f"[EXPLANATION] Erro no template {regra_id}: {e}")
                return descricao_fallback or f"Regra {regra_id} aplicada.", False
        return str(template), True

    @staticmethod
    def resumo_para_excel(explicacoes: List[Dict[str, Any]]) -> List[List[str]]:
        return [[e["nivel"], e["base_legal"], e["titulo"], e["explicacao"]] for e in explicacoes]

    @staticmethod
    def resumo_para_memoria(explicacoes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        return [
            {"regra_id": e["regra_id"], "nivel": e["nivel"], "base_legal": e["base_legal"],
             "titulo": e["titulo"], "explicacao": e["explicacao"]}
            for e in explicacoes
        ]

def gerar_explicacoes(verbas: List[dict], memorial_juridico: List[dict]) -> List[Dict[str, Any]]:
    """Interface pública compatível com processor.py (step 8c)."""
    resultado_engine = {"memorial_juridico": memorial_juridico}
    dados = {"verbas_deferidas": verbas}
    return ExplanationEngine.gerar(resultado_engine, dados)


# ── Parecer técnico: I. PARCELAS APURADAS (modelo perita / IA com template fixo) ─

_FGTS_NOME_PATTERN = re.compile(
    r"fgts|multa\s*(?:de\s*)?40\s*%|multa\s*40",
    re.IGNORECASE,
)

# Reflexos padrão quando a extração não traz lista (modelo perita)
_REFLEXOS_PADRAO = ["aviso prévio", "férias + 1/3", "13º salário"]
_REFLEXOS_HE_INTERVALO = ["pela média física sobre RSR", "aviso prévio", "férias + 1/3", "13º salário"]


def _is_fgts_verba(nome: str) -> bool:
    """True se a verba é FGTS / Multa 40% como parcela principal (a ser omitida do parecer)."""
    if not nome or not isinstance(nome, str):
        return False
    return bool(_FGTS_NOME_PATTERN.search(nome))


def _reflexos_contem_fgts(reflexos: List[str]) -> bool:
    """True se na lista de reflexos há menção a FGTS ou multa 40%."""
    if not reflexos:
        return False
    for r in reflexos:
        if isinstance(r, str) and _FGTS_NOME_PATTERN.search(r):
            return True
    return False


def _eh_verba_sobre(nome: str) -> bool:
    """True se a verba é reflexo de outra (ex: 13º SOBRE INTERVALO, AVISO PRÉVIO SOBRE HE)."""
    if not nome or not isinstance(nome, str):
        return False
    n = nome.upper()
    return " SOBRE " in n or n.strip().startswith("SOBRE ")


def _eh_verba_principal(nome: str) -> bool:
    """True se a verba deve gerar linha própria (não é FGTS nem 'sobre X')."""
    return not _is_fgts_verba(nome) and not _eh_verba_sobre(nome)


def _classificar_verba(nome: str) -> Optional[str]:
    """Retorna 'insalubridade' | 'horas_extras' | 'intervalo' | None para outras principais."""
    if not nome or not isinstance(nome, str):
        return None
    n = nome.upper()
    if re.search(r"INSALUBRIDADE|ADICIONAL\s+DE\s+INSALUBRIDADE", n):
        return "insalubridade"
    if re.search(r"HORAS?\s*EXTRAS?|ADICIONAL\s*NOTURNO", n):
        return "horas_extras"
    if re.search(r"INTERVALO\s*INTRAJORNADA", n):
        return "intervalo"
    return None


def _familia_agrupamento_parecer(nome: str) -> Optional[str]:
    """
    Retorna a "família" da verba apenas para agrupamento no texto do parecer.
    Não altera verbas_deferidas; usado só para exibição enxuta (como a perita redige).
    """
    if not nome or not isinstance(nome, str):
        return None
    n = nome.upper()
    if re.search(r"13\s*º|13º|DÉCIMO\s*TERCEIRO|DECIMO\s*TERCEIRO", n):
        return "decimo_terceiro"
    if re.search(r"FÉRIAS|FERIAS", n):
        return "ferias"
    return None


def _agrupar_verbas_para_parecer(verbas: List[dict]) -> List[dict]:
    """
    Agrupa verbas da mesma família só para o texto do parecer (não altera dados de cálculo).
    - Múltiplos 13º → um item "13º Salário (integral e proporcional)" com reflexos unificados.
    - Múltiplas férias → um item "Férias (vencidas, integrais e/ou proporcionais)" com reflexos unificados.
    - Demais verbas permanecem uma linha cada.
    Ordem preservada: primeira aparição de cada tipo (ex.: saldo, depois 13º agrupado, aviso, férias agrupadas, etc.).
    Retorna lista de dicts: {"nome_display": str, "reflexos": list (único/sem duplicata)}.
    """
    if not verbas:
        return []

    # Acumular reflexos por família
    reflexos_13: set = set()
    reflexos_ferias: set = set()
    resultado: List[dict] = []
    emitido_13 = False
    emitido_ferias = False

    for v in verbas:
        if not isinstance(v, dict):
            continue
        nome = v.get("nome") or ""
        familia = _familia_agrupamento_parecer(nome)
        r = v.get("reflexos") or []
        reflexos_lista = list(r) if isinstance(r, (list, tuple)) else []

        if familia == "decimo_terceiro":
            for x in reflexos_lista:
                if x is not None and str(x).strip():
                    reflexos_13.add(str(x).strip())
            if not emitido_13:
                emitido_13 = True
                resultado.append({
                    "nome_display": "13º Salário (integral e proporcional)",
                    "reflexos": sorted(reflexos_13),
                })
        elif familia == "ferias":
            for x in reflexos_lista:
                if x is not None and str(x).strip():
                    reflexos_ferias.add(str(x).strip())
            if not emitido_ferias:
                emitido_ferias = True
                resultado.append({
                    "nome_display": "Férias (vencidas, integrais e/ou proporcionais)",
                    "reflexos": sorted(reflexos_ferias),
                })
        else:
            reflexos_unicos = list(dict.fromkeys(str(x).strip() for x in reflexos_lista if x is not None and str(x).strip()))
            resultado.append({"nome_display": nome, "reflexos": reflexos_unicos})

    # Se houve 13º ou férias, atualizar reflexos no item já emitido (pode ter sido emitido antes de ver todos)
    for item in resultado:
        if item.get("nome_display") == "13º Salário (integral e proporcional)":
            item["reflexos"] = sorted(reflexos_13)
        elif item.get("nome_display") == "Férias (vencidas, integrais e/ou proporcionais)":
            item["reflexos"] = sorted(reflexos_ferias)

    return resultado


def _formatar_reflexos(reflexos_lista: List[str], fgts_na_condenacao: bool) -> str:
    """
    Junta reflexos por vírgula e adiciona sufixo FGTS quando aplicável.

    Importante: se a verba NÃO tiver reflexos na extração (lista vazia ou nula),
    não inventa reflexos padrão. Apenas quando existir ao menos um reflexo real
    é que o texto "com reflexos em ..." será utilizado.
    """
    if not reflexos_lista:
        return ""

    partes = [str(r).strip() for r in reflexos_lista if r is not None and str(r).strip()]
    if not partes:
        return ""

    texto = ", ".join(partes)
    if fgts_na_condenacao:
        texto += ", e de todas estas parcelas em FGTS e multa de 40%;"
    else:
        texto += ";"
    return texto


def _normalizar_texto_reflexos(texto: str) -> str:
    """
    Evita repetições como \"reflexos reflexos\" ou \"com reflexos, com reflexos\"
    que podem surgir quando a lista de reflexos já contém o termo \"reflexos\".
    """
    if not texto:
        return texto
    texto = texto.replace("reflexos reflexos", "reflexos")
    texto = texto.replace("com reflexos, com reflexos", "com reflexos")
    return texto


def gerar_parecer_parcelas_apuradas(
    verbas_deferidas: List[dict],
    dados: dict,
) -> Dict[str, Any]:
    """
    Gera a seção "I. PARCELAS APURADAS" no formato da perita: uma linha por tipo de verba,
    título em maiúsculas + parágrafo de apuração; FGTS omitido (embutido nos reflexos);
    honorários periciais e sucumbenciais ao final.

    Retorna {"intro": str, "itens": [{"alinea", "titulo", "texto"}, ...]}.
    """
    verbas = list(verbas_deferidas) if verbas_deferidas else []
    dados = dados or {}

    intro = "Foram apuradas as parcelas de acordo com as decisões, conforme relatado a seguir:"
    itens: List[Dict[str, str]] = []
    alinea_idx = 0

    # FGTS na condenação
    fgts_na_condenacao = any(
        _is_fgts_verba(v.get("nome") if isinstance(v, dict) else getattr(v, "nome", ""))
        for v in verbas
    ) or any(
        _reflexos_contem_fgts(
            v.get("reflexos") if isinstance(v, dict) else getattr(v, "reflexos", []) or [],
        )
        for v in verbas
    )

    divisor_geral = dados.get("divisor_horas")
    divisor_txt = str(divisor_geral) if divisor_geral else "120/180"
    divisor_intervalo = "180"  # modelo perita
    data_intervalo = "01/07/2017"  # Reforma Trabalhista — modelo perita

    # Ordem desejada: Insalubridade, Horas Extras, Intervalo; depois outras principais
    ordem_tipos = ["insalubridade", "horas_extras", "intervalo"]
    verbas_por_tipo: Dict[str, dict] = {}
    outras_principais: List[dict] = []
    for v in verbas:
        if not isinstance(v, dict):
            continue
        nome = v.get("nome") or ""
        if not _eh_verba_principal(nome):
            continue
        tipo = _classificar_verba(nome)
        if tipo:
            if tipo not in verbas_por_tipo:
                verbas_por_tipo[tipo] = v
        else:
            outras_principais.append(v)

    for tipo in ordem_tipos:
        v = verbas_por_tipo.get(tipo)
        if not v:
            continue
        nome = v.get("nome") or "Verba"
        reflexos_raw = v.get("reflexos")
        reflexos_lista = list(reflexos_raw) if isinstance(reflexos_raw, (list, tuple)) else []

        if tipo == "insalubridade":
            reflexos_str = _formatar_reflexos(reflexos_lista, fgts_na_condenacao)
            titulo = "ADICIONAL DE INSALUBRIDADE E REFLEXOS" if reflexos_str else "ADICIONAL DE INSALUBRIDADE"
            if reflexos_str:
                texto = f"Apuração do adicional de insalubridade, com reflexos no {reflexos_str}"
            else:
                texto = "Apuração do adicional de insalubridade;"
        elif tipo == "horas_extras":
            reflexos_str = _formatar_reflexos(reflexos_lista, fgts_na_condenacao)
            titulo = "HORAS EXTRAS E REFLEXOS" if reflexos_str else "HORAS EXTRAS"
            pct = str((v.get("percentual") or "50")).strip()
            texto = (
                f"Apuração das horas extras durante todo o contrato de trabalho, "
                f"utilizadas as Súmulas 264 e 347 do TST, observado o divisor {divisor_txt}, "
                f"com percentual de {pct}%"
            )
            if reflexos_str:
                texto += f", com reflexos {reflexos_str}"
            else:
                texto += ";"
        else:  # intervalo
            reflexos_str = _formatar_reflexos(reflexos_lista, fgts_na_condenacao)
            titulo = "INTERVALO INTRAJORNADA E REFLEXOS" if reflexos_str else "INTERVALO INTRAJORNADA"
            pct = str((v.get("percentual") or "60")).strip()
            texto = (
                f"Apuração do intervalo intrajornada a partir de {data_intervalo}, "
                f"utilizadas as Súmulas 264 e 347 do TST, observado o divisor {divisor_intervalo}, "
                f"com percentual de {pct}%"
            )
            if reflexos_str:
                texto += f", com reflexos {reflexos_str}"
            else:
                texto += ";"

        texto = _normalizar_texto_reflexos(texto)
        letra = chr(97 + alinea_idx)
        alinea_idx += 1
        itens.append({"alinea": letra, "titulo": titulo, "texto": texto})

    # Outras verbas: agrupamento semântico só para o parecer (13º e férias em um item cada)
    agrupadas = _agrupar_verbas_para_parecer(outras_principais)
    for item in agrupadas:
        nome_display = item.get("nome_display") or "Verba"
        reflexos_lista = item.get("reflexos") or []
        reflexos_str = _formatar_reflexos(reflexos_lista, fgts_na_condenacao)
        titulo_base = nome_display.upper()
        if titulo_base.endswith(" REFLEXOS"):
            titulo = titulo_base
        else:
            titulo = titulo_base + " E REFLEXOS" if reflexos_str else titulo_base
        if reflexos_str:
            texto = f"Apuração de {nome_display}, com reflexos no {reflexos_str}"
        else:
            texto = f"Apuração de {nome_display};"
        texto = _normalizar_texto_reflexos(texto)
        letra = chr(97 + alinea_idx)
        alinea_idx += 1
        itens.append({"alinea": letra, "titulo": titulo, "texto": texto})

    # Honorários periciais (valor definido na sentença quando não extraído)
    valor_pericia = dados.get("honorarios_periciais_valor") or dados.get("honorarios_periciais")
    if valor_pericia:
        valor_txt = str(valor_pericia).strip()
        if not re.search(r"R\$\s*[\d.,]+", valor_txt, re.IGNORECASE):
            valor_txt = f"R$ {valor_txt}"
    else:
        valor_txt = "no valor definido na sentença"
    letra = chr(97 + alinea_idx)
    alinea_idx += 1
    itens.append({
        "alinea": letra,
        "titulo": "HONORÁRIOS PERICIAIS",
        "texto": f"Apuração dos honorários periciais no valor de {valor_txt};",
    })

    # Honorários sucumbenciais
    pct_hon = dados.get("percentual_honorarios") or "5"
    pct_hon = str(pct_hon).strip().replace("%", "")
    letra = chr(97 + alinea_idx)
    alinea_idx += 1
    itens.append({
        "alinea": letra,
        "titulo": "HONORÁRIOS SUCUMBENCIAIS",
        "texto": f"Honorários sucumbenciais no percentual de {pct_hon}% sobre o valor da condenação;",
    })

    print(f"[EXPLANATION] Parecer: intro + {len(itens)} itens (modelo perita)")
    return {"intro": intro, "itens": itens}


def _load_skill_parecer_pericial() -> str:
    """
    Carrega o manual de redação do parecer pericial (skills/parecer_pericial.md).
    Se não encontrado, retorna uma string de fallback mínima.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    skill_path = os.path.join(base_dir, "skills", "parecer_pericial.md")
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return (
            "Manual mínimo de redação do parecer pericial:\n"
            "- Iniciar as frases com 'Apuração'.\n"
            "- Usar numeração alfabética a), b), c).\n"
            "- Agrupar reflexos no final com 'com reflexos em ...'.\n"
        )


def gerar_parecer_tecnico_completo(
    dados: Dict[str, Any],
    verbas_deferidas: List[dict],
) -> Dict[str, Any]:
    """
    Gera o parecer técnico completo (texto contínuo) usando:

    - Cabeçalho padrão do processo;
    - Seção I. PARCELAS APURADAS: preenchida por IA (slot) com base em
      skills/parecer_pericial.md e nas verbas_deferidas;
    - Seção II. CRITÉRIOS ADOTADOS PARA OS CÁLCULOS: blocos fixos padronizados.

    Retorna:
      {
        "texto": str,             # parecer completo, texto simples
        "parcelas": str,          # apenas o bloco da seção I
        "model_used": str|None,   # modelo usado para o slot
        "error": str|None,        # erro na IA (se houver)
      }
    """
    from services.ai_client import gerar_parcelas_parecer

    dados = dados or {}
    numero = dados.get("numero_processo") or "processo"
    reclamante = dados.get("reclamante") or "reclamante"
    reclamada = dados.get("reclamada") or "reclamada"

    cabecalho = (
        f"Processo nº {numero}\n"
        f"Reclamante: {reclamante}\n"
        f"Reclamada: {reclamada}\n\n"
        "O(a) perito(a) abaixo assinado(a) vem, respeitosamente, apresentar o presente parecer técnico:\n\n"
    )

    skill_text = _load_skill_parecer_pericial()
    ia_result = gerar_parcelas_parecer(verbas_deferidas or [], dados, skill_text)
    parcelas_txt = ia_result.get("texto") or ""

    criterios = obter_textos_padrao_criterios_parecer()
    bloco_criterios = (
        "II. CRITÉRIOS ADOTADOS PARA OS CÁLCULOS:\n\n"
        f"{criterios.get('correcao','')}\n\n"
        f"{criterios.get('inss','')}\n\n"
        f"{criterios.get('irrf','')}\n"
    ).strip()

    parecer_completo = (
        f"{cabecalho}"
        "I. PARCELAS APURADAS:\n"
        f"{parcelas_txt.strip()}\n\n"
        f"{bloco_criterios}"
    ).strip()

    return {
        "texto": parecer_completo,
        "parcelas": parcelas_txt.strip(),
        "model_used": ia_result.get("model_used"),
        "error": ia_result.get("error"),
    }


"""
Script auxiliar: escreve services/explanation_engine.py com conteúdo correto.
Executar de dentro de backend/:
    python fix_explanation_engine.py
"""
import os

DEST = os.path.join("services", "explanation_engine.py")

CONTENT = """\
\"\"\"
explanation_engine.py — v5.3
Geração de texto jurídico explicativo por regra aplicada.
\"\"\"
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

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
    juros  = dados.get("juros_mora") or "1% a.m."
    return (
        f"Correção monetária aplicada conforme ADC 58 STF: {indice} "
        f"(pré-ajuizamento) e SELIC (pós-ajuizamento). Juros de mora: {juros}. "
        "Afastada a aplicação da TR para períodos posteriores à decisão do STF."
    )

def _template_sumula264(dados):
    p = r"horas?\\s*extras?|adicional\\s*noturno|insalubridade|periculosidade"
    verbas_he = _verbas_com_nome(dados, p)
    mencao = f" ({', '.join(verbas_he)})" if verbas_he else ""
    return (
        f"Horas extras e adicionais{mencao} integram o salário para fins de reflexos. "
        "Incidência em DSR, férias acrescidas de 1/3, 13º salário e FGTS — Súmula 264 do TST."
    )

def _template_sumula305(dados):
    ap_dias = dados.get("aviso_previo_dias")
    mencao  = f" ({ap_dias} dias)" if ap_dias else ""
    return (
        f"FGTS incide sobre o aviso prévio indenizado{mencao}, "
        "ainda que não haja efetiva prestação de serviços — Súmula 305 do TST."
    )

def _template_sumula331(dados):
    reclamada = dados.get("reclamada") or "a empresa tomadora de serviços"
    return (
        f"Terceirização reconhecida. {reclamada} responde subsidiariamente "
        "pelas obrigações trabalhistas inadimplidas pela prestadora de serviços — Súmula 331 do TST."
    )

def _template_oj42(dados):
    ap_dias = dados.get("aviso_previo_dias")
    mencao  = f" ({ap_dias} dias)" if ap_dias else ""
    return (
        f"Multa de 40% do FGTS não incide sobre o aviso prévio indenizado{mencao}. "
        "A base de cálculo da multa rescisória exclui o aviso prévio indenizado — OJ 42 SDI-I TST."
    )

def _template_oj195(dados):
    return (
        "FGTS não incide sobre férias indenizadas. "
        "Férias não gozadas convertidas em pecúnia não integram a base de cálculo do FGTS — OJ 195 SDI-I TST."
    )

def _template_oj394(dados):
    verbas_he = _verbas_com_nome(dados, r"horas?\\s*extras?|adicional\\s*noturno")
    mencao = f" ({', '.join(verbas_he)})" if verbas_he else ""
    return (
        f"DSR majorado por horas extras{mencao} não reflete em férias, "
        "13º salário nem FGTS — evitado o bis in idem. OJ 394 SDI-I TST."
    )

def _template_art467(dados):
    salario = dados.get("salario_base")
    mencao  = f" (base: R$ {salario})" if salario else ""
    return (
        f"Multa de 50% sobre as verbas rescisórias incontroversas{mencao} "
        "não pagas no prazo legal — Art. 467 da CLT."
    )

def _template_art477(dados):
    salario = dados.get("salario_base")
    mencao  = f" (equivalente a R$ {salario})" if salario else " (equivalente a 1 salário)"
    return (
        f"Multa por atraso no pagamento das verbas rescisórias{mencao}. "
        "Descumprimento do prazo previsto no Art. 477, § 6º da CLT."
    )

def _template_art487(dados):
    ap_dias = dados.get("aviso_previo_dias")
    mencao  = f"{ap_dias} dias" if ap_dias else "proporcional ao tempo de serviço"
    return (
        f"Aviso prévio de {mencao}, calculado com acréscimo de 3 dias por ano "
        "de serviço (máximo 90 dias) — Art. 487 da CLT c/c Lei 12.506/2011."
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
        f"Honorários advocatícios sucumbenciais fixados{base} — "
        f"Art. 791-A da CLT (Reforma Trabalhista 2017).{obs}"
    )

def _template_cnj(dados):
    num = dados.get("numero_processo") or "informado"
    return (
        f"Número do processo ({num}) validado conforme dígito verificador "
        "da Resolução CNJ 65/2008."
    )

def _template_deduplicator(dados):
    return (
        "Verbas duplicadas identificadas e consolidadas. "
        "Deduplicação por nome canônico e período — garantia de unicidade na base de cálculo."
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
    \"\"\"Interface pública compatível com processor.py (step 8c).\"\"\"
    resultado_engine = {"memorial_juridico": memorial_juridico}
    dados = {"verbas_deferidas": verbas}
    return ExplanationEngine.gerar(resultado_engine, dados)
"""

with open(DEST, "w", encoding="utf-8") as f:
    f.write(CONTENT)

# Verificar sintaxe
import py_compile
try:
    py_compile.compile(DEST, doraise=True)
    print(f"✅ {DEST} escrito e validado — sem erros de sintaxe")
except py_compile.PyCompileError as e:
    print(f"❌ Erro de sintaxe: {e}")
"""
extraction_engine.py — Raio-X: enriquecimento dos dados extraídos para o painel split-screen

Usa o knowledge_base.json para:
- Organizar os dados em categorias (Estrutural, Contratual, Condenação) para o painel "Dados Extraídos".
- Forçar destaque a: divisor de horas, adicionais, datas contratuais, índices de juros.
- Gerar a seção "Dicas do Laboratório" com alertas baseados em regras aprendidas (padrões de erro,
  empresas específicas quando houver caso_visto, etc.).

Consumido pelo pipeline (processor) que injeta o resultado no response; o frontend exibe no painel Raio-X.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Chaves por categoria para o painel Raio-X (ordem de exibição)
ESTRUTURAL_KEYS = [
    "numero_processo", "vara_trabalho", "reclamante", "reclamada",
    "tipo_rito", "funcao_reclamante", "advogado_reclamante", "juiz_responsavel",
    "data_sentenca", "data_ajuizamento", "prescricao_quinquenal",
]
CONTRATUAL_KEYS = [
    "data_admissao", "data_demissao", "motivo_rescisao", "tipo_contrato",
    "salario_base", "jornada_contratual", "horario_trabalho",
    "divisor_horas",  # crítico para PJe-Calc
    "aviso_previo_dias", "data_saida_ctps", "anotacao_ctps", "seguro_desemprego",
]
CONDENACAO_KEYS = [
    "indice_correcao", "juros_mora",
    "verbas_deferidas",  # tratado à parte (lista)
    "multa_art_467", "multa_art_477", "dano_moral", "dano_material",
    "fgts_periodo_completo", "fgts_sobre_aviso_previo", "fgts_sobre_ferias_indenizadas", "fgts_multa_40_aviso_previo", "fgts_observacoes",
    "honorarios_sucumbenciais", "percentual_honorarios", "justica_gratuita", "custas_processuais",
]


def _valor_legivel(v: Any) -> str:
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return ""
    if isinstance(v, bool):
        return "Sim" if v else "Não"
    if isinstance(v, list):
        return " | ".join(str(x) for x in v) if v else ""
    return str(v).strip()


def _extrair_adicionais(verbas_deferidas: List[Any]) -> List[Dict[str, str]]:
    """Lista adicionais (noturno, insalubridade, periculosidade, etc.) a partir das verbas deferidas."""
    adicionais = []
    for v in verbas_deferidas or []:
        if isinstance(v, dict):
            nome = (v.get("nome") or "").strip()
            if not nome:
                continue
            n_lower = nome.lower()
            if any(x in n_lower for x in ("noturno", "insalubridade", "periculosidade", "adicional", "sobreaviso", "interjornada")):
                adicionais.append({
                    "nome": nome,
                    "percentual": _valor_legivel(v.get("percentual")),
                    "base_calculo": _valor_legivel(v.get("base_calculo")),
                })
        elif isinstance(v, str) and v.strip():
            adicionais.append({"nome": v.strip(), "percentual": "", "base_calculo": ""})
    return adicionais


def _build_categoria(dados: Dict[str, Any], chaves: List[str]) -> Dict[str, str]:
    """Monta um dict com todas as chaves (valor vazio quando não preenchido) para exibição em ordem fixa."""
    out = {}
    for k in chaves:
        if k == "verbas_deferidas":
            continue
        v = dados.get(k)
        out[k] = _valor_legivel(v)
    return out


def _build_condenacao_verbas(verbas_deferidas: List[Any]) -> List[Dict[str, Any]]:
    """Lista de verbas para a seção Condenação (nome, status, percentual, reflexos)."""
    rows = []
    for v in verbas_deferidas or []:
        if isinstance(v, dict):
            rows.append({
                "nome": _valor_legivel(v.get("nome")),
                "status_final": _valor_legivel(v.get("status_final")),
                "percentual": _valor_legivel(v.get("percentual")),
                "reflexos": _valor_legivel(v.get("reflexos")) if isinstance(v.get("reflexos"), list) else _valor_legivel(v.get("reflexos")),
            })
        elif isinstance(v, str):
            rows.append({"nome": v.strip(), "status_final": "", "percentual": "", "reflexos": ""})
    return rows


def _dicas_do_laboratorio(dados: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Gera dicas a partir do Knowledge Base: regras ativas e shadow que podem se aplicar.
    Inclui padrões de erro (ex.: empresa que costuma errar divisor, índice).
    """
    try:
        from services.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
    except Exception:
        return []

    reclamada = (dados.get("reclamada") or "").strip()
    numero_processo = (dados.get("numero_processo") or "").strip()
    dicas = []

    for regra in kb.get_regras_ativas() + kb.get_regras_shadow():
        cond = regra.get("condicao") or {}
        acao = regra.get("acao") or {}
        msg = acao.get("mensagem") or regra.get("descricao") or ""
        base_legal = (regra.get("base_legal") or "").strip()
        status = regra.get("status", "")
        # Aplica a todos por simplicidade; em versão futura filtrar por reclamada/casos_vistos
        dicas.append({
            "titulo": f"[{status.upper()}] {cond.get('tipo', 'regra')}" + (f" — {cond.get('verba') or cond.get('campo') or ''}" or ""),
            "mensagem": msg[:300] + ("..." if len(msg) > 300 else ""),
            "base_legal": base_legal[:120] or "",
        })

    return dicas[:15]  # Limite para não poluir o painel


def enriquecer_para_raiox(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    A partir dos dados extraídos do PDF (resultado do pipeline), monta o payload do painel Raio-X:
    categorias (Estrutural, Contratual, Condenação) e Dicas do Laboratório.

    Args:
        dados: dict retornado pelo process_lawsuit_pdf (data).

    Returns:
        {
            "categorias": {
                "estrutural": { "numero_processo": "...", ... },
                "contratual": { "divisor_horas": "...", ... },
                "condenacao": { "indice_correcao": "...", ... },
                "adicionais": [ { "nome", "percentual", "base_calculo" }, ... ],
                "verbas_lista": [ { "nome", "status_final", "percentual", "reflexos" }, ... ],
            },
            "dicas_laboratorio": [ { "titulo", "mensagem", "base_legal" }, ... ],
        }
    """
    if not dados or not isinstance(dados, dict):
        return {"categorias": {"estrutural": {}, "contratual": {}, "condenacao": {}, "adicionais": [], "verbas_lista": []}, "dicas_laboratorio": []}

    categorias = {
        "estrutural": _build_categoria(dados, ESTRUTURAL_KEYS),
        "contratual": _build_categoria(dados, CONTRATUAL_KEYS),
        "condenacao": _build_categoria(dados, CONDENACAO_KEYS),
        "adicionais": _extrair_adicionais(dados.get("verbas_deferidas") or []),
        "verbas_lista": _build_condenacao_verbas(dados.get("verbas_deferidas") or []),
    }

    dicas_laboratorio = _dicas_do_laboratorio(dados)

    return {
        "categorias": categorias,
        "dicas_laboratorio": dicas_laboratorio,
    }

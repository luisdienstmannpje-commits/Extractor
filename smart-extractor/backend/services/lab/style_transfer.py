"""
style_transfer.py — Duplo Style Transfer: retórica da perita (Passo 5).

Isola a lógica que aprende como a perita escreve a partir da Impugnação (Card 6)
e da Manifestação (Card 8). Junta resultados com merge_dados_manifestacao;
persiste padrões em skills/manifestacao_style.md.

Funções:
  - merge_dados_manifestacao: junta dados de impugnação + manifestação (Duplo Style Transfer).
  - extrair_manifestacao_pericial: analisa peça com Gemini; extrai frases de impacto, padrões
    Ataque/Defesa, argumento vencedor; codifica padrões no KB; atualiza manifestacao_style.md.
  - atualizar_skill_manifestacao: append em skills/manifestacao_style.md com bloco aprendido.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from services.lab import extractors


def merge_dados_manifestacao(
    base: Optional[Dict[str, Any]], novo: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Junta resultados de impugnação (Card 6) e manifestação (Card 8) para enriquecer o playbook.
    Duplo Style Transfer: ambos os arquivos alimentam o mesmo manifestacao_style.md.
    """
    if not base:
        return dict(novo)
    out = {}
    for key in (
        "frases_impacto",
        "fundamentos_juridicos",
        "padroes_ataque_defesa",
        "parametros_fraudados",
        "verbas_em_disputa",
    ):
        a = (base.get(key) or []) if isinstance(base.get(key), list) else []
        b = (novo.get(key) or []) if isinstance(novo.get(key), list) else []
        seen = set()
        merged = []
        for x in a + b:
            t = (x if isinstance(x, str) else str(x))[:200]
            if t not in seen:
                seen.add(t)
                merged.append(x)
        out[key] = merged
    out["argumento_vencedor"] = (novo.get("argumento_vencedor") or "").strip() or (
        base.get("argumento_vencedor") or ""
    ).strip()
    out["resumo"] = (base.get("resumo") or "").strip()
    if (novo.get("resumo") or "").strip():
        out["resumo"] = (out["resumo"] + "\n\n" + (novo.get("resumo") or "").strip()).strip()
    out["style_atualizado"] = base.get("style_atualizado", False) or novo.get(
        "style_atualizado", False
    )
    out["model_used"] = novo.get("model_used") or base.get("model_used")
    out["erro"] = novo.get("erro") or base.get("erro")
    return out


def _codificar_padroes_ataque_defesa(dados_manifestacao: Dict[str, Any]) -> None:
    """
    Para cada padrão Ataque→Defesa encontrado na Manifestação,
    cria uma Shadow Rule no Knowledge Base.
    """
    padroes = dados_manifestacao.get("padroes_ataque_defesa") or []
    if not padroes:
        return
    from services.knowledge_base import KnowledgeBase
    from services.request_context import current_tenant_id

    kb = KnowledgeBase(tenant_id=current_tenant_id())
    for padrao in padroes[:8]:
        ataque = (padrao.get("ataque_empresa") or "").strip()[:80]
        defesa = (padrao.get("defesa_perita") or "").strip()[:120]
        fundamento = (padrao.get("fundamento") or "").strip()[:60]
        if not ataque or not defesa:
            continue
        condicao = {
            "tipo": "campo_diferente",
            "campo": "argumento_empresa",
            "valor_esperado": ataque,
        }
        acao = f"Sugerir fundamento: {fundamento} — Rebate: {defesa}"
        descricao = f"[Manifestação] Quando empresa alega '{ataque}', aplicar: {defesa}"
        kb.adicionar_ou_incrementar(
            logica={
                "descricao": descricao,
                "condicao": condicao,
                "acao": {"tipo": "alerta", "nivel": "AVISO", "mensagem": acao},
                "base_legal": fundamento,
            },
        )
    print(f"[LEARNING] {len(padroes[:8])} padrao(oes) Ataque/Defesa codificado(s) no KB.", flush=True)


def atualizar_skill_manifestacao(
    skills_dir: str,
    dados: Dict[str, Any],
    trecho_original: str,
    filename: str = "",
) -> bool:
    """
    Cria ou atualiza skills/manifestacao_style.md com os padrões aprendidos.
    Cada chamada ADICIONA um novo bloco, acumulando retórica de múltiplas peças.
    """
    os.makedirs(skills_dir, exist_ok=True)
    destino = os.path.join(skills_dir, "manifestacao_style.md")
    data = datetime.now().strftime("%Y-%m-%d %H:%M")

    frases = "\n".join(f'- "{f}"' for f in (dados.get("frases_impacto") or [])[:10])
    fundamentos = "\n".join(f"- {f}" for f in (dados.get("fundamentos_juridicos") or [])[:15])
    parametros = "\n".join(f"- {p}" for p in (dados.get("parametros_fraudados") or [])[:8])
    padroes_txt = ""
    for p in (dados.get("padroes_ataque_defesa") or [])[:5]:
        ataque = p.get("ataque_empresa", "—")
        defesa = p.get("defesa_perita", "—")
        fund = p.get("fundamento", "—")
        padroes_txt += f"  - **Empresa:** {ataque}\n    **Perita:** {defesa} ({fund})\n"

    bloco = f"""

---

## Manifestação Analisada — {data} | {filename}

**Argumento vencedor:**
> {dados.get("argumento_vencedor") or "—"}

**Resumo:**
{dados.get("resumo") or "—"}

**Tom:** {dados.get("tom") or "—"}

**Frases de impacto (retórica de combate):**
{frases or "— Não identificadas"}

**Fundamentos jurídicos usados:**
{fundamentos or "— Não identificados"}

**Parâmetros matemáticos expostos como indevidos:**
{parametros or "— Não identificados"}

**Padrões Ataque → Defesa:**
{padroes_txt or "— Não identificados"}

**Trecho original (referência):**
```
{trecho_original[:500]}
```
"""

    try:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(bloco)
        print(f"[LEARNING] skills/manifestacao_style.md atualizado ({filename}).", flush=True)
        return True
    except Exception as e:
        print(f"[LEARNING] Erro ao atualizar manifestacao_style.md: {e}", flush=True)
        return False


def extrair_manifestacao_pericial(
    file_bytes: bytes,
    filename: str,
    *,
    extrair_texto_arquivo: Callable[[bytes, str], str],
    chamar_gemini_para_codify: Callable[[str], Tuple[str, str]],
    skills_dir: str,
) -> Dict[str, Any]:
    """
    Analisa a Manifestação (Petição de Resposta / Impugnação à Contestação) para extrair:
    frases de impacto, fundamentos jurídicos, padrões Ataque/Defesa, parâmetros fraudados,
    argumento vencedor. Usa Gemini para análise semântica; codifica padrões no KB;
    persiste em skills/manifestacao_style.md.

    Callbacks injetados pelo learning_engine: extrair_texto_arquivo, chamar_gemini_para_codify.
    """
    texto = extrair_texto_arquivo(file_bytes, filename)
    if not texto.strip():
        return {
            "erro": "Documento sem texto legível",
            "frases_impacto": [],
            "fundamentos_juridicos": [],
            "padroes_ataque_defesa": [],
            "parametros_fraudados": [],
            "argumento_vencedor": "",
            "resumo": "",
        }

    prompt = (
        "Você é especialista em análise de peças jurídicas trabalhistas e inteligência estratégica.\n"
        "Analise a Manifestação Pericial (Impugnação à Contestação de Cálculos) abaixo.\n\n"
        "Extraia em JSON puro os seguintes campos:\n"
        "{\n"
        '  "frases_impacto": ["5-10 expressões retóricas de alto impacto usadas pela perita, ex: \'Divergência aritmética flagrante\', \'Preclusão consumativa\'"],\n'
        '  "fundamentos_juridicos": ["Súmulas, OJs, artigos CLT, ADC usados na defesa (ex: Súmula 172 TST, ADC 58, Art. 477 CLT)"],\n'
        '  "padroes_ataque_defesa": [\n'
        '    {"ataque_empresa": "argumento que a empresa usou", "defesa_perita": "como a perita rebateu", "fundamento": "Súmula/OJ/Art. usado"}\n'
        "  ],\n"
        '  "parametros_fraudados": ["parâmetros matemáticos que a empresa omitiu ou manipulou, ex: \'reflexos em DSR omitidos\', \'gratificação de função não integrada\'"],\n'
        '  "argumento_vencedor": "resumo em 1-2 frases do argumento central vitorioso da perita",\n'
        '  "verbas_em_disputa": ["verbas trabalhistas que foram objeto de contestação"],\n'
        '  "tom": "assertivo|incisivo|técnico|combativo",\n'
        '  "resumo": "resumo geral da manifestação em 2-3 frases"\n'
        "}\n\n"
        "IMPORTANTE: Responda APENAS com o JSON válido, sem markdown.\n\n"
        f"MANIFESTAÇÃO (primeiros 6000 caracteres):\n{texto[:6000]}"
    )

    conteudo, model = chamar_gemini_para_codify(prompt)

    dados: Dict[str, Any] = {}
    try:
        conteudo_limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        dados = json.loads(conteudo_limpo)
    except Exception:
        dados = {
            "frases_impacto": [],
            "fundamentos_juridicos": extractors.extrair_fundamentos_juridicos(texto),
            "padroes_ataque_defesa": [],
            "parametros_fraudados": [],
            "argumento_vencedor": conteudo[:300] if conteudo else "Não foi possível analisar a manifestação",
            "resumo": "",
        }

    dados["model_used"] = model
    dados["texto_bruto"] = texto[:2000]
    dados["erro"] = None

    _codificar_padroes_ataque_defesa(dados)
    dados["style_atualizado"] = atualizar_skill_manifestacao(
        skills_dir, dados, texto[:2000], filename
    )

    return dados


__all__ = [
    "merge_dados_manifestacao",
    "atualizar_skill_manifestacao",
    "extrair_manifestacao_pericial",
]

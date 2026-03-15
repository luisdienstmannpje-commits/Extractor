"""
ai_writer.py — Ghostwriter: geração de texto de Manifestação/Laudo com estilo da perita

Usado pelo endpoint /lab/gerar-docx. Recebe as discrepâncias da auditoria e o conteúdo
de skills/manifestacao_style.md; chama o Gemini para redigir o texto no estilo mapeado.
Retorno: introdução, seções (uma por discrepância) e opcionalmente dados para tabela
comparativa (Valor Devido vs Valor Pago), tudo em texto limpo (sem Markdown).
"""

import json
import re
from typing import Any, Dict, List

from google import genai
from config import settings

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"


def _strip_markdown(text: str) -> str:
    """Remove marcações comuns de Markdown do texto para uso em Word."""
    if not text or not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"\*+([^*]+)\*+", r"\1", text)
    text = re.sub(r"__+([^_]+)__+", r"\1", text)
    text = re.sub(r"```\w*\n?", "", text)
    return text.strip()


def gerar_texto_manifestacao(
    discrepancias: List[Dict[str, Any]],
    estilo_mapeado: str,
    dados_processo: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Gera o texto da manifestação com base nas discrepâncias e no estilo do perito.

    Args:
        discrepancias: lista de dicts com tipo, nivel, juiz_disse, empresa_calculou,
                       juliana_corrigiu, fundamento (saída do relatório de auditoria).
        estilo_mapeado: conteúdo de skills/manifestacao_style.md (frases de impacto,
                        padrões ataque/defesa, tom).
        dados_processo: opcional — numero_processo, reclamante, reclamada (para contexto).

    Returns:
        {
            "introducao": str,
            "secoes": [ {"titulo": str, "texto": str}, ... ],
            "tabela_comparativa": [ {"descricao": str, "valor_empresa": str, "valor_correto": str}, ... ] ou []
        }
        Em caso de erro: {"erro": str, "introducao": "", "secoes": [], "tabela_comparativa": []}
    """
    if not discrepancias:
        return {
            "introducao": "",
            "secoes": [],
            "tabela_comparativa": [],
            "erro": "Nenhuma discrepância fornecida.",
        }

    dados_processo = dados_processo or {}
    processo_str = dados_processo.get("numero_processo") or "Processo em trâmite"
    reclamante = dados_processo.get("reclamante") or "Reclamante"
    reclamada = dados_processo.get("reclamada") or "Reclamada"

    # Limitar tamanho do estilo para não estourar contexto
    estilo_limpo = (estilo_mapeado or "")[:25000].strip() or "Estilo assertivo e técnico; uso de fundamentos legais (CLT, Súmulas TST, ADC 58)."

    disc_resumo = []
    for i, d in enumerate(discrepancias[:20], 1):
        if not isinstance(d, dict):
            continue
        disc_resumo.append({
            "n": i,
            "tipo": d.get("tipo") or "discrepancia",
            "juiz_disse": (d.get("juiz_disse") or "").strip(),
            "empresa_calculou": (d.get("empresa_calculou") or "").strip(),
            "juliana_corrigiu": (d.get("juliana_corrigiu") or "").strip(),
            "fundamento": (d.get("fundamento") or "").strip(),
        })

    prompt = (
        "Você é um Perito Assistente Sênior. Com base nas discrepâncias listadas abaixo e na "
        "INSTRUÇÃO DE TOM E VOZ (arquivo anexo), redija o texto da MANIFESTAÇÃO AOS CÁLCULOS.\n\n"
        "REGRAS DE REDAÇÃO:\n"
        "- IMITE o tom e a voz do perito: use as expressões e fórmulas que constam na Instrução de Tom e Voz "
        "(ex.: 'esperando haver se desincumbido do múnus', 'vem, respeitosamente', 'Vossa Senhoria', "
        "'Caso o MM. Juízo não reconheça', 'Requere', 'Pede Deferimento').\n"
        "- Foque na demonstração matemática e no confronto com o que a empresa calculou.\n"
        "- Tom assertivo e técnico; cite fundamentos (Súmulas TST, CLT, ADC 58) quando aplicável.\n"
        "- NÃO use Markdown (sem #, *, **, ```). Texto limpo para colar em Word.\n\n"
        "INSTRUÇÃO DE TOM E VOZ (obrigatório seguir este estilo — frases de impacto, padrões Ataque/Defesa, "
        "expressões características e trechos de manifestações reais analisadas):\n"
        "────────────────────────────────────────\n"
        f"{estilo_limpo}\n"
        "────────────────────────────────────────\n\n"
        f"Processo: {processo_str} | Reclamante: {reclamante} | Reclamada: {reclamada}\n\n"
        "DISCREPÂNCIAS DA AUDITORIA:\n"
        f"{json.dumps(disc_resumo, ensure_ascii=False, indent=2)}\n\n"
        "TAREFA: Retorne um ÚNICO objeto JSON válido (sem markdown, sem ```) com as chaves:\n"
        '- "introducao": string — um parágrafo de abertura da manifestação (exórdio).\n'
        '- "secoes": array de objetos { "titulo": string, "texto": string } — uma entrada por discrepância; '
        'titulo curto (ex: "1. Verba ausente — Horas Extras"); texto = parágrafo de argumentação.\n'
        '- "tabela_comparativa": array de { "descricao": string, "valor_empresa": string, "valor_correto": string } — '
        'apenas para itens em que há valor monetário ou numérico explícito (ex: valor pago vs valor devido). '
        'Se não houver dados para tabela, retorne [].\n'
        "Retorne apenas o JSON, sem texto antes ou depois."
    )

    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=prompt,
        )
        raw = (response.text or "").strip()
        if not raw:
            return {"introducao": "", "secoes": [], "tabela_comparativa": [], "erro": "Resposta vazia da IA."}

        # Extrair JSON da resposta (pode vir dentro de ```json ... ```)
        raw = _strip_markdown(raw)
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw).rstrip("`").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Tentar achar primeiro { ... }
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                data = json.loads(match.group(0))
            else:
                return {"introducao": "", "secoes": [], "tabela_comparativa": [], "erro": "Resposta da IA não é JSON válido."}

        introducao = _strip_markdown(str(data.get("introducao") or ""))
        secoes_raw = data.get("secoes") or []
        secoes = []
        for s in secoes_raw if isinstance(secoes_raw, list) else []:
            if isinstance(s, dict):
                titulo = _strip_markdown(str(s.get("titulo") or ""))
                texto = _strip_markdown(str(s.get("texto") or ""))
                secoes.append({"titulo": titulo, "texto": texto})

        tabela_raw = data.get("tabela_comparativa") or []
        tabela = []
        for t in tabela_raw if isinstance(tabela_raw, list) else []:
            if isinstance(t, dict):
                tabela.append({
                    "descricao": _strip_markdown(str(t.get("descricao") or "")),
                    "valor_empresa": _strip_markdown(str(t.get("valor_empresa") or "")),
                    "valor_correto": _strip_markdown(str(t.get("valor_correto") or "")),
                })

        return {
            "introducao": introducao,
            "secoes": secoes,
            "tabela_comparativa": tabela,
        }
    except Exception as e:
        return {
            "introducao": "",
            "secoes": [],
            "tabela_comparativa": [],
            "erro": str(e),
        }

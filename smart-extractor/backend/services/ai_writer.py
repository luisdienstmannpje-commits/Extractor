"""
ai_writer.py — Ghostwriter: geração de texto de Manifestação/Laudo com estilo da perita

Usado pelo endpoint /lab/gerar-docx. Recebe as discrepâncias da auditoria, o Quadro de Verbas
(verbas_deferidas), os Alertas Jurídicos e o conteúdo de skills/manifestacao_style.md; chama
o Gemini para redigir documento formal pronto para protocolo (Perito Calculista Trabalhista).
Retorno: introdução, seções (por verba e por discrepância), tabela comparativa, em texto limpo.
"""

import json
import re
from typing import Any, Dict, List

from google import genai
from config import settings

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

# Instruções de estilo e estrutura para a IA (redação pericial formal)
INSTRUCOES_REDACAO_PERICIAL = """
1) Cabeçalho e Preâmbulo (formalidade máxima):
   - Iniciar com: "EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) DA [Vara] VARA DO TRABALHO DE [Cidade]."
   - Referenciar o número do processo e as partes (Reclamante x Reclamada).
   - Usar: "Vem, respeitosamente, à presença de Vossa Excelência, apresentar os CÁLCULOS DE LIQUIDAÇÃO DE SENTENÇA..." ou "apresentar MANIFESTAÇÃO AOS CÁLCULOS...".

2) Metodologia e Parâmetros (obrigatório):
   - Criar tópico informando que os cálculos seguiram a estrita observância da coisa julgada.
   - Mencionar correção monetária (ex.: "Aplicação do IPCA-E na fase pré-judicial e taxa SELIC a partir do ajuizamento, conforme decisão vinculante do STF na ADC 58").

3) Análise de Verbas (corpo do documento):
   - Para cada verba principal deferida (ex.: Horas Extras, Férias, 13º), criar um subtópico.
   - Linguagem: "Da apuração das Horas Extras: Restou apurado o labor extraordinário, observando-se o divisor [X] e os reflexos legais em DSR, Aviso Prévio e FGTS, conforme comandos sentenciais."
   - Usar jargões periciais: "apurou-se", "escorreita liquidação", "rechaça-se", "integração salarial", "bis in idem", "verbas rescisórias".

4) Tratamento dos Alertas Jurídicos:
   - Se houver alertas (ex.: salário base abaixo do mínimo, ausência de multas), criar tópico "ESCLARECIMENTOS ADICIONAIS" ou "PONTOS DE CONTROVÉRSIA" e justificar tecnicamente o impacto nos cálculos.

5) Fecho:
   - "Requer-se, por fim, a intimação das partes e a posterior HOMOLOGAÇÃO dos presentes cálculos, fixando-se o quantum debeatur."
   - "Termos em que, Pede deferimento." Local e Data.
"""


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


def _sanitize_json_response(text: str) -> str:
    """
    Remove blocos de markdown (```json ... ```) e texto em volta para obter
    apenas o conteúdo passível de json.loads(). Reduz JSONDecodeError por 'Extra data'.
    """
    if not text or not isinstance(text, str):
        return ""
    text = text.strip()
    # Remove bloco ``` no início (opcional: ```json ou ```)
    text = re.sub(r"^```\w*\n?", "", text)
    # Remove ``` no final (multiline)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()
    return text


def _extract_first_json_object(text: str) -> str:
    """
    Extrai o primeiro objeto JSON completo { ... } (chaves balanceadas).
    Evita 'Extra data' quando a LLM retorna JSON seguido de texto livre.
    """
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape = False
    quote = None
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if c == quote:
                in_string = False
            continue
        if c in ('"', "'"):
            in_string = True
            quote = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text


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
        dados_processo: opcional — numero_processo, reclamante, reclamada, vara_trabalho,
                        indice_correcao, verbas_deferidas (lista de {nome} ou str), alertas_juridicos (lista).

    Returns:
        {
            "introducao": str,
            "secoes": [ {"titulo": str, "texto": str}, ... ],
            "tabela_comparativa": [ {"descricao": str, "valor_empresa": str, "valor_correto": str}, ... ] ou [],
            "fecho": str (homologação, Pede deferimento, local e data)
        }
        Em caso de erro: {"erro": str, "introducao": "", "secoes": [], "tabela_comparativa": [], "fecho": ""}
    """
    dados_processo = dados_processo or {}
    processo_str = dados_processo.get("numero_processo") or "Processo em trâmite"
    reclamante = dados_processo.get("reclamante") or "Reclamante"
    reclamada = dados_processo.get("reclamada") or "Reclamada"
    vara_trabalho = dados_processo.get("vara_trabalho") or "[Vara]"
    indice_correcao = dados_processo.get("indice_correcao") or ""
    verbas_deferidas = dados_processo.get("verbas_deferidas") or []
    alertas_juridicos = dados_processo.get("alertas_juridicos") or []

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

    verbas_nomes = [v.get("nome") if isinstance(v, dict) else str(v) for v in verbas_deferidas if v]
    contexto_verbas = json.dumps(verbas_nomes, ensure_ascii=False) if verbas_nomes else "[]"
    contexto_alertas = json.dumps(alertas_juridicos, ensure_ascii=False, indent=2) if alertas_juridicos else "[]"

    # Quando não há discrepâncias, a IA gera esqueleto/template (clonador de estilo)
    modo_esqueleto = len(disc_resumo) == 0
    instrucao_modo = (
        "Se a lista de discrepâncias estiver VAZIA, o seu objetivo muda: Você deve atuar como um CLONADOR DE ESTILO. "
        "Gere um ESQUELETO DE PETIÇÃO (Template) utilizando estritamente a linguagem jurídica, formatação de cabeçalhos, "
        "encerramentos e jargões capturados no aprendizado de estilo. No corpo do texto, crie 2 ou 3 parágrafos genéricos "
        "(placeholders) demonstrando o vocabulário aprendido, como se estivesse preparando uma peça em branco para o advogado "
        "preencher depois. Mantenha o mesmo formato JSON de resposta (introducao, secoes, tabela_comparativa, fecho)."
        if modo_esqueleto
        else ""
    )

    prompt = (
        "Você atua como PERITO CALCULISTA TRABALHISTA / ASSISTENTE TÉCNICO SÊNIOR. Seu objetivo é redigir "
        "um documento formal, pronto para protocolo, a partir do JSON de verbas deferidas e alertas gerados pelo motor.\n\n"
        + (f"INSTRUÇÃO ESPECIAL (lista de discrepâncias VAZIA):\n{instrucao_modo}\n\n" if instrucao_modo else "")
        + "ESTRUTURA E ESTILO OBRIGATÓRIOS (siga à risca):\n"
        "────────────────────────────────────────\n"
        f"{INSTRUCOES_REDACAO_PERICIAL.strip()}\n"
        "────────────────────────────────────────\n\n"
        "INSTRUÇÃO DE TOM E VOZ (reforço de estilo — frases de impacto, padrões Ataque/Defesa):\n"
        f"{estilo_limpo}\n\n"
        "CONTEXTO OBRIGATÓRIO DO PROCESSO:\n"
        f"- Processo: {processo_str} | Reclamante: {reclamante} | Reclamada: {reclamada}\n"
        f"- Vara (para cabeçalho): {vara_trabalho}\n"
        f"- Índice de correção monetária (mencione na metodologia): {indice_correcao or 'IPCA-E pré-judicial e SELIC a partir do ajuizamento (ADC 58)'}\n\n"
        "QUADRO DE VERBAS DEFERIDAS (use para criar um subtópico por verba principal no corpo do documento):\n"
        f"{contexto_verbas}\n\n"
        "ALERTAS JURÍDICOS (se não estiver vazio, crie tópico ESCLARECIMENTOS ADICIONAIS ou PONTOS DE CONTROVÉRSIA e justifique o impacto nos cálculos):\n"
        f"{contexto_alertas}\n\n"
        "DISCREPÂNCIAS DA AUDITORIA (confronto empresa x correção pericial):\n"
        f"{json.dumps(disc_resumo, ensure_ascii=False, indent=2)}\n\n"
        "REGRAS: NÃO use Markdown (sem #, *, **, ```). Texto limpo para Word. Use jargão pericial: apurou-se, escorreita liquidação, rechaça-se, integração salarial, bis in idem, verbas rescisórias.\n\n"
        "TAREFA: Retorne um ÚNICO objeto JSON válido (sem markdown, sem ```) com as chaves:\n"
        '- "introducao": string — cabeçalho formal (Excelentíssimo(a) Senhor(a) Doutor(a) Juiz(a)...) + preâmbulo (Vem, respeitosamente...) e, em seguida, tópico de METODOLOGIA E PARÂMETROS (coisa julgada, correção monetária IPCA-E/SELIC, ADC 58).\n'
        '- "secoes": array de { "titulo": string, "texto": string } — uma entrada por verba principal deferida (ex.: "Da apuração das Horas Extras", "Das Férias", "Do 13º salário") com texto pericial; se houver alertas, inclua uma seção "ESCLARECIMENTOS ADICIONAIS" ou "PONTOS DE CONTROVÉRSIA"; pode incluir seções por discrepância quando relevante.\n'
        '- "tabela_comparativa": array de { "descricao", "valor_empresa", "valor_correto" } para itens com valor explícito; se não houver, [].\n'
        '- "fecho": string — parágrafo final com "Requer-se, por fim, a intimação das partes e a posterior HOMOLOGAÇÃO dos presentes cálculos, fixando-se o quantum debeatur." e "Termos em que, Pede deferimento." + Local e Data (ex.: "São Paulo, 16 de março de 2025.").\n\n'
        "IMPORTANTE: RETORNE EXCLUSIVAMENTE UM OBJETO JSON VÁLIDO no formato com as chaves introducao, secoes, tabela_comparativa e fecho. "
        "NÃO adicione saudações, não use formatação markdown (sem ```json ou ```), explicações ou qualquer texto fora das chaves {}."
    )

    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=prompt,
        )
        raw = (response.text or "").strip()
        if not raw:
            return {"introducao": "", "secoes": [], "tabela_comparativa": [], "fecho": "", "erro": "Resposta vazia da IA."}

        # Sanitização: remove markdown (```) e extrai apenas o primeiro objeto JSON
        cleaned = _sanitize_json_response(raw)
        data = None
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                first_obj = _extract_first_json_object(cleaned)
                data = json.loads(first_obj)
            except json.JSONDecodeError:
                # Fallback: LLM retornou texto livre; usa como introdução para o .docx não quebrar
                data = None

        if data is None:
            # Fallback: usa texto bruto para o .docx receber conteúdo limpo (não quebra a aplicação)
            texto_bruto = _strip_markdown(raw[:50000])
            return {
                "introducao": texto_bruto,
                "secoes": [],
                "tabela_comparativa": [],
                "fecho": "",
            }

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

        fecho = _strip_markdown(str(data.get("fecho") or ""))

        return {
            "introducao": introducao,
            "secoes": secoes,
            "tabela_comparativa": tabela,
            "fecho": fecho,
        }
    except Exception as e:
        return {
            "introducao": "",
            "secoes": [],
            "tabela_comparativa": [],
            "fecho": "",
            "erro": str(e),
        }

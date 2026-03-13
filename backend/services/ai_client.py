"""
ai_client.py — Cascata de IA com playbook, pre-fields, truncamento cirúrgico e retry

Ordem de modelos: Flash (rápido/barato) → Pro (poderoso/caro) → erro

Melhorias v2.2:
  - Aceita `pre_fields` do pre_extractor — âncoras de média confiança
  - Prompt sem valores concretos de exemplo (evitava alucinação por cópia)
  - Bloco INSTRUÇÕES ESPECÍFICAS para campos historicamente problemáticos
  - Removida menção ao PjeCalc do prompt base (fica nos playbooks)
  - Separação clara: template base neutro / instruções no playbook .md

Estratégia de truncamento (inalterada):
  1. Remove duplicatas de intimação.
  2. Janela cirúrgica: 35% início + 65% dispositivo.
  Flash usa MAX_CHARS_CONTEXT; Pro usa o dobro.
"""

import json
import time
import re
from google import genai
from config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

MODELS_CASCADE = [
    "gemini-2.0-flash",
    "models/gemini-2.5-pro",
]

CHARS_LIMIT = {
    "gemini-2.0-flash":      settings.MAX_CHARS_CONTEXT,
    "models/gemini-2.5-pro": settings.MAX_CHARS_CONTEXT * 2,
}

# ── Padrões para truncamento inteligente ──────────────────────────────────────

_RE_DISPOSITIVO = re.compile(
    r"(?i)("
    r"DISPOSITIVO\s*\n"
    r"|ANTE O EXPOSTO[,.]"
    r"|ISTO POSTO[,.]"
    r"|PELO EXPOSTO[,.]"
    r"|DIANTE DO EXPOSTO[,.]"
    r"|JULGO PROCEDENTE"
    r"|JULGO PARCIALMENTE"
    r"|JULGO IMPROCEDENTE"
    r"|CONDENO A RECLAMADA"
    r"|ACORDAM\b"
    r")"
)

_RE_DUPLICATA = re.compile(
    r"(?i)("
    r"Fica V\. Sa\. intimado para tomar ciência da Senten[çc]a"
    r"|Fica V\. Sa\. intimado para tomar ciência do Ac[oó]rd[aã]o"
    r"|Certidão de Disponibilização e Publicação"
    r"|INTIMAÇÃO\s*\nFica V\. Sa\. intimado"
    r")"
)

_RE_VERBAS = re.compile(
    r"(?i)("
    r"horas extras|adicional noturno|adicional de insalubridade"
    r"|adicional de periculosidade|f\.?g\.?t\.?s"
    r"|aviso pr[eé]vio|f[eé]rias|d[eé]cimo|13.*sal[aá]rio"
    r"|saldo de sal[aá]rio|dano moral|dano material"
    r"|multa|art\.? ?467|art\.? ?477|intervalo"
    r")"
)


def _remove_duplicatas(text: str) -> str:
    original_len = len(text)
    match = _RE_DUPLICATA.search(text)
    if match:
        text = text[:match.start()].rstrip()
        print(f"   [TRUNCATE] Duplicata removida: {original_len} → {len(text)} chars")
        return text
    matches_disp = list(_RE_DISPOSITIVO.finditer(text))
    if len(matches_disp) >= 2:
        corte = matches_disp[1].start()
        trecho_antes = text[max(0, corte - 300):corte]
        pagina_match = trecho_antes.rfind("--- PÁGINA")
        if pagina_match >= 0:
            corte = corte - 300 + pagina_match
        text = text[:corte].rstrip()
        print(f"   [TRUNCATE] Duplicata (2º dispositivo) removida: {original_len} → {len(text)} chars")
    return text


def _smart_truncate(text: str, max_chars: int) -> str:
    text = _remove_duplicatas(text)
    if len(text) <= max_chars:
        print(f"   [TRUNCATE] Texto cabe inteiro: {len(text)} chars")
        return text

    parte1_chars = int(max_chars * 0.35)
    parte2_chars = max_chars - parte1_chars
    parte1 = text[:parte1_chars]

    match_disp = _RE_DISPOSITIVO.search(text)
    if match_disp:
        disp_pos = match_disp.start()
        start2 = max(parte1_chars, disp_pos - 2000)
        end2   = min(len(text), start2 + parte2_chars)
        parte2 = text[start2:end2]
        print(f"   [TRUNCATE] Janela cirúrgica: início={parte1_chars} + disp={start2}–{end2}")
    else:
        matches = list(_RE_VERBAS.finditer(text))
        start2 = max(parte1_chars, matches[-1].start() - 500) if matches \
                 else max(parte1_chars, len(text) - parte2_chars)
        end2   = min(len(text), start2 + parte2_chars)
        parte2 = text[start2:end2]
        print(f"   [TRUNCATE] Fallback verbas: {start2}–{end2}")

    truncated = parte1 + "\n\n[...FUNDAMENTAÇÃO INTERMEDIÁRIA OMITIDA...]\n\n" + parte2
    print(f"   [TRUNCATE] Total enviado: {len(truncated)} chars (original: {len(text)})")
    return truncated


# ── Prompt principal ──────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """Você é um especialista em direito trabalhista brasileiro e perito em análise de documentos judiciais.

{playbook_section}

{anchor_section}

Analise o documento trabalhista abaixo e extraia TODOS os dados disponíveis.

REGRAS OBRIGATÓRIAS:
- Retorne APENAS JSON válido, sem markdown, sem explicações, sem ```json
- Use null para campos não encontrados — NUNCA invente ou copie valores dos exemplos abaixo
- Datas no formato DD/MM/AAAA
- Valores monetários com R$ e vírgula decimal (ex: "R$ 3.500,00")
- justica_gratuita deve ser true ou false (booleano) — nunca string
- integracao_salarial deve ser true, false ou null — nunca string
- Extraia TODAS as verbas deferidas — não omita nenhuma
- Para reflexos, liste apenas os expressamente deferidos no documento
- Priorize sempre o DISPOSITIVO sobre a fundamentação em caso de conflito
- NÃO copie os valores de exemplo do template — extraia do texto
- status_final de cada verba: use "deferida" para sentença de 1ª instância, "mantida"/"reformada"/"excluída"/"acrescida" para acórdão/embargos — NUNCA deixar null ou "não informado"

INSTRUÇÕES ESPECÍFICAS PARA CAMPOS DIFÍCEIS:
- jornada_contratual: buscar "jornada de X horas", "44h semanais", "horário de X às X" e calcular horas semanais. Se encontrar horário mas não jornada explícita, calcule: (saída - entrada - intervalo) × dias da semana
- fgts_periodo_completo: montar como "Todo o período contratual — [data_admissao] a [data_demissao]" usando as datas do próprio documento
- base_calculo de cada verba: buscar explicitamente o que compõe a base — "calculado sobre o salário base", "sobre a remuneração", "incidindo sobre"
- reflexos de cada verba: buscar frases "com reflexos em", "repercussão em", "integrando o salário para fins de". Listar apenas os explícitos
- fgts_sobre_aviso_previo / fgts_multa_40_aviso_previo / fgts_sobre_ferias_indenizadas: extrair do texto — se não mencionado, retornar null (não copiar regra padrão)
- salario_base: priorizar o valor RECONHECIDO PELO JUIZ, não o alegado pelas partes
- data_sentenca: priorizar "Assinado eletronicamente em DD/MM/AAAA" — se não houver, buscar "Cidade, DD de mês de AAAA" ao final
- aviso_previo_dias: se aplicada a Lei 12.506/2011, registrar total + composição (ex: "42 dias — 30 + 12 pela Lei 12.506/2011")

ESTRUTURA ESPERADA (retorne exatamente estas chaves, com null para não encontrados):
{{
  "numero_processo": null,
  "vara_trabalho": null,
  "reclamante": null,
  "reclamada": null,
  "tipo_rito": null,
  "funcao_reclamante": null,
  "advogado_reclamante": null,
  "juiz_responsavel": null,

  "data_sentenca": null,
  "data_ajuizamento": null,
  "data_admissao": null,
  "data_demissao": null,
  "motivo_rescisao": null,
  "tipo_contrato": null,

  "salario_base": null,
  "jornada_contratual": null,
  "horario_trabalho": null,
  "aviso_previo_dias": null,
  "data_saida_ctps": null,
  "anotacao_ctps": null,
  "seguro_desemprego": null,

  "indice_correcao": null,
  "juros_mora": null,

  "contribuicao_previdenciaria": null,
  "ir_retido_fonte": null,

  "honorarios_sucumbenciais": null,
  "percentual_honorarios": null,
  "justica_gratuita": false,
  "custas_processuais": null,

  "dano_moral": null,
  "dano_material": null,
  "multa_art_467": null,
  "multa_art_477": null,

  "fgts_sobre_aviso_previo": null,
  "fgts_multa_40_aviso_previo": null,
  "fgts_sobre_ferias_indenizadas": null,
  "fgts_periodo_completo": null,
  "fgts_observacoes": null,

  "verbas_deferidas": [
    {{
      "nome": null,
      "status_final": null,
      "periodo": null,
      "percentual": null,
      "quantidade_diaria": null,
      "base_calculo": null,
      "valor_fixado": null,
      "integracao_salarial": null,
      "reflexos": [],
      "observacoes": null
    }}
  ]
}}

DOCUMENTO:
{text}
"""


def _build_prompt(text: str, playbook: str, anchor_section: str = "") -> str:
    if playbook and playbook.strip():
        playbook_section = (
            "MANUAL DE LEITURA DESTE DOCUMENTO (leia antes de extrair):\n"
            "─────────────────────────────────────────────────────────\n"
            + playbook.strip()
            + "\n─────────────────────────────────────────────────────────\n"
        )
    else:
        playbook_section = ""

    if anchor_section and anchor_section.strip():
        anchor_block = (
            "─────────────────────────────────────────────────────────\n"
            + anchor_section.strip()
            + "\n─────────────────────────────────────────────────────────\n"
        )
    else:
        anchor_block = ""

    return PROMPT_TEMPLATE.format(
        playbook_section=playbook_section,
        anchor_section=anchor_block,
        text=text,
    )


# ── Chamada individual com retry ──────────────────────────────────────────────

def _strip_markdown(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw.strip()


def _call_model(
    model_name: str,
    text: str,
    playbook: str = "",
    anchor_section: str = "",
    retries: int = 2
) -> dict:
    max_chars = CHARS_LIMIT.get(model_name, 15_000)
    truncated = _smart_truncate(text, max_chars)
    prompt = _build_prompt(truncated, playbook, anchor_section)

    prompt_chars = len(prompt)
    tokens_est = prompt_chars // 4
    print(f"   [PROMPT] {prompt_chars} chars | ~{tokens_est} tokens estimados")

    last_error = None
    for attempt in range(1, retries + 2):
        try:
            print(f"   [AI] {model_name} — tentativa {attempt}/{retries + 1} "
                  f"({len(truncated)} chars de texto)")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            raw = response.text.strip() if response.text else ""

            if not raw:
                raise ValueError("Resposta vazia da IA")

            raw = _strip_markdown(raw)
            return json.loads(raw)

        except json.JSONDecodeError as e:
            last_error = f"JSON inválido: {e}"
            print(f"   [AI] {model_name} JSON inválido (tentativa {attempt}): {e}")
            break

        except Exception as e:
            last_error = str(e)
            err_str = str(e).lower()

            if "429" in err_str or "quota" in err_str or "rate" in err_str:
                wait = 10 * attempt
                print(f"   [AI] Rate limit. Aguardando {wait}s...")
                time.sleep(wait)
                continue

            if "timeout" in err_str or "deadline" in err_str or "503" in err_str:
                wait = 3 * attempt
                print(f"   [AI] Timeout. Aguardando {wait}s...")
                time.sleep(wait)
                continue

            print(f"   [AI] Erro não recuperável em {model_name}: {e}")
            break

    raise RuntimeError(
        f"{model_name} falhou após {retries + 1} tentativas: {last_error}"
    )


# ── Interface pública ─────────────────────────────────────────────────────────

def extract_data_with_gemini(
    text: str,
    playbook: str = "",
    pre_fields: dict = None,
) -> dict:
    """
    Extrai dados do texto com cascata de modelos Flash → Pro.

    Args:
        text:       Texto do documento (saída do sentence_finder).
        playbook:   Conteúdo do .md de skill correspondente ao tipo de documento.
        pre_fields: Dict {"high": {...}, "medium": {...}} do pre_extractor.
                    medium fields → injetados como âncoras no prompt.
                    high fields → não enviados (aplicados diretamente no processor).

    Returns:
        {"data": dict, "model_used": str, "error": str|None}
    """
    if not text or not text.strip():
        return {"data": None, "model_used": None, "error": "Texto vazio"}

    # Monta seção de âncoras a partir dos medium confidence fields
    anchor_section = ""
    if pre_fields and pre_fields.get("medium"):
        from services.pre_extractor import build_anchor_section
        anchor_section = build_anchor_section(pre_fields["medium"])

    print(
        f"[AI] Iniciando extração | Texto: {len(text)} chars "
        f"| Playbook: {len(playbook)} chars "
        f"| Âncoras: {len(pre_fields.get('medium', {})) if pre_fields else 0} campos"
    )

    for model_name in MODELS_CASCADE:
        try:
            result = _call_model(
                model_name, text,
                playbook=playbook,
                anchor_section=anchor_section
            )
            print(f"[AI] ✓ Sucesso com {model_name}")
            return {"data": result, "model_used": model_name, "error": None}
        except Exception as e:
            print(f"[AI] ✗ {model_name} falhou: {e}")

    return {
        "data": None,
        "model_used": None,
        "error": (
            "Ambos os modelos falharam. Possíveis causas: "
            "PDF sem texto suficiente, quota da API esgotada, "
            "ou documento muito fragmentado para extração."
        ),
    }


# ── Geração de texto para Parecer Técnico (slot de parcelas) ────────────────────

def gerar_parcelas_parecer(
    verbas: list,
    dados: dict,
    skill_parecer: str,
    model_name: str = "gemini-2.0-flash",
) -> dict:
    """
    Gera o bloco de texto da seção "I. PARCELAS APURADAS" do parecer técnico.

    A saída é um texto simples (sem Markdown) contendo apenas as linhas:
        a) ...
        b) ...
        c) ...

    Args:
        verbas: lista de verbas_deferidas (dicts com nome, reflexos, percentual, etc.).
        dados:  dict com dados do processo (pode ser usado em futuras versões).
        skill_parecer: conteúdo de skills/parecer_pericial.md.
        model_name: modelo a ser usado (default: gemini-2.0-flash).

    Returns:
        {"texto": str, "model_used": str, "error": str|None}
    """
    if not verbas:
        return {"texto": "", "model_used": None, "error": "Sem verbas para descrever"}

    # Resumo compacto das verbas para o prompt: evita enviar o JSON completo
    verbas_resumo = []
    for v in verbas:
        if not isinstance(v, dict):
            continue
        nome = v.get("nome") or ""
        if not nome:
            continue
        reflexos = v.get("reflexos") or []
        percentual = v.get("percentual")
        verbas_resumo.append(
            {
                "nome": nome,
                "reflexos": reflexos,
                "percentual": percentual,
            }
        )

    if not verbas_resumo:
        return {"texto": "", "model_used": None, "error": "Sem verbas válidas para descrever"}

    instrucoes = (
        "Você é um perito trabalhista responsável por redigir a seção "
        '"I. PARCELAS APURADAS" de um parecer técnico.\n\n'
        "Siga rigorosamente o MANUAL DE REDAÇÃO abaixo, que define o estilo e os exemplos "
        "de como as parcelas devem ser descritas.\n\n"
        "MANUAL DE REDAÇÃO DO PARECER PERICIAL:\n"
        "────────────────────────────────────────\n"
        f"{skill_parecer.strip()}\n"
        "────────────────────────────────────────\n\n"
        "DADOS DAS PARCELAS A DESCREVER (resumo estruturado):\n"
        f"{json.dumps(verbas_resumo, ensure_ascii=False, indent=2)}\n\n"
        "TAREFA:\n"
        '- Redija SOMENTE o bloco de texto da seção "I. PARCELAS APURADAS", '
        "apenas com as linhas `a)`, `b)`, `c)` etc.\n"
        "- Use o título em maiúsculas antes dos dois pontos, conforme os exemplos do manual.\n"
        "- Cada linha deve começar com a palavra 'Apuração' após os dois pontos.\n"
        "- Agrupe reflexos no final da frase usando 'com reflexos em ...', apenas quando "
        "houver reflexos nas verbas correspondentes.\n"
        "- NÃO use Markdown, NÃO use bullet points com '-', NÃO use cabeçalhos '#', "
        "NÃO envolva o texto em ```.\n"
        "- Retorne apenas texto simples, adequado para colar em Excel ou Word.\n"
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=instrucoes,
        )
        raw = response.text.strip() if response.text else ""
        if not raw:
            raise ValueError("Resposta vazia da IA ao gerar parcelas do parecer")
        texto = _strip_markdown(raw)
        # Como reforço, removemos caracteres típicos de markdown que possam ter escapado
        texto = texto.replace("*", "").replace("#", "").strip()
        return {"texto": texto, "model_used": model_name, "error": None}
    except Exception as e:
        return {"texto": "", "model_used": model_name, "error": str(e)}

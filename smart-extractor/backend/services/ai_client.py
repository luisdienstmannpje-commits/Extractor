"""
ai_client.py — Cascata de IA com playbook, pre-fields, truncamento cirúrgico e retry

Ordem de modelos: Flash (rápido/barato) → Pro (poderoso/caro) → erro

Melhorias v2.2:
  - Aceita `pre_fields` do pre_extractor — âncoras de média confiança
  - Prompt sem valores concretos de exemplo (evitava alucinação por cópia)
  - Bloco INSTRUÇÕES ESPECÍFICAS para campos historicamente problemáticos
  - Removida menção ao PjeCalc do prompt base (fica nos playbooks)
  - Separação clara: template base neutro / instruções no playbook .md

Estratégia de truncamento:
  1. Remove duplicatas de intimação.
  2. Janela cirúrgica: 40% início (página 1 / identificação PJe: valor da causa, Data da Autuação, Partes) + 60% dispositivo. Nunca ignorar os primeiros caracteres do documento na extração.
  Flash usa MAX_CHARS_CONTEXT; Pro usa o dobro.

Observabilidade: com DEBUG_PIPELINE=1 (config), _call_model loga tamanho/hash/snippets
em ai_pre_remove_duplicatas, ai_pos_remove_duplicatas, ai_pos_smart_truncate; _smart_truncate_after_dedup
emite [DEBUG-PIPELINE][truncate] com geometria da janela quando len(texto) > max_chars (ver pipeline_debug.py).
"""

import json
import time
import re
from typing import Any, Dict, List, Mapping, Optional, cast

from google import genai
from google.genai.types import Content, Part, Blob
from config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

MODELS_CASCADE = [
    "gemini-2.5-flash",      # substitui gemini-2.0-flash (deprecado)
    "models/gemini-2.5-pro",
]

CHARS_LIMIT = {
    "gemini-2.5-flash":      settings.MAX_CHARS_CONTEXT,
    "gemini-2.0-flash":      settings.MAX_CHARS_CONTEXT,  # fallback legado
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
        print(f"   [TRUNCATE] Duplicata removida: {original_len} -> {len(text)} chars", flush=True)
        return text
    matches_disp = list(_RE_DISPOSITIVO.finditer(text))
    if len(matches_disp) >= 2:
        corte = matches_disp[1].start()
        trecho_antes = text[max(0, corte - 300):corte]
        pagina_match = trecho_antes.rfind("--- PÁGINA")
        if pagina_match >= 0:
            corte = corte - 300 + pagina_match
        text = text[:corte].rstrip()
        print(f"   [TRUNCATE] Duplicata (2º dispositivo) removida: {original_len} -> {len(text)} chars", flush=True)
    return text


def _smart_truncate_after_dedup(
    text: str,
    max_chars: int,
    pipeline_debug_meta: Optional[Mapping[str, Any]] = None,
) -> str:
    """
    Aplica só limite de caracteres + janela cirúrgica.
    Presume que intimação/2º dispositivo já foram tratados em _remove_duplicatas.
    """
    meta = dict(pipeline_debug_meta or {})
    n = len(text)
    if n <= max_chars:
        print(f"   [TRUNCATE] Texto cabe inteiro: {n} chars", flush=True)
        if settings.DEBUG_PIPELINE:
            from services.pipeline_debug import log_truncate_cabe_inteiro

            log_truncate_cabe_inteiro(n, max_chars, meta=meta)
        return text

    parte1_chars = int(max_chars * 0.40)  # 40% início (cabeçalho, valor da causa, advogados); 60% dispositivo
    parte2_chars = max_chars - parte1_chars
    parte1 = text[:parte1_chars]

    if settings.DEBUG_PIPELINE:
        from services.pipeline_debug import log_truncate_inicio_cirurgico

        log_truncate_inicio_cirurgico(n, max_chars, parte1_chars, parte2_chars, meta=meta)

    match_disp = _RE_DISPOSITIVO.search(text)
    if match_disp:
        disp_pos = match_disp.start()
        start2 = max(parte1_chars, disp_pos - 2000)
        end2   = min(len(text), start2 + parte2_chars)
        parte2 = text[start2:end2]
        print(f"   [TRUNCATE] Janela cirúrgica: início={parte1_chars} + disp={start2}-{end2}", flush=True)
        if settings.DEBUG_PIPELINE:
            from services.pipeline_debug import log_truncate_com_dispositivo

            log_truncate_com_dispositivo(disp_pos, start2, end2, meta=meta)
    else:
        matches = list(_RE_VERBAS.finditer(text))
        start2 = max(parte1_chars, matches[-1].start() - 500) if matches \
                 else max(parte1_chars, len(text) - parte2_chars)
        end2   = min(len(text), start2 + parte2_chars)
        parte2 = text[start2:end2]
        print(f"   [TRUNCATE] Fallback verbas: {start2}–{end2}", flush=True)
        if settings.DEBUG_PIPELINE:
            from services.pipeline_debug import log_truncate_sem_dispositivo_fallback

            log_truncate_sem_dispositivo_fallback(
                start2, end2, len(matches), meta=meta
            )

    truncated = parte1 + "\n\n[...FUNDAMENTAÇÃO INTERMEDIÁRIA OMITIDA...]\n\n" + parte2
    print(f"   [TRUNCATE] Total enviado: {len(truncated)} chars (original: {len(text)})", flush=True)
    return truncated


def _smart_truncate(text: str, max_chars: int) -> str:
    """Remove duplicatas de intimação/decisão colada, depois aplica janela cirúrgica se necessário."""
    return _smart_truncate_after_dedup(_remove_duplicatas(text), max_chars)


# ── Prompt principal ──────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """Você é um especialista em direito trabalhista brasileiro e perito em análise de documentos judiciais.

{playbook_section}

{anchor_section}

Analise o documento trabalhista abaixo e extraia TODOS os dados disponíveis.

Quando o contexto incluir múltiplos documentos (textos, tabelas de planilhas ou descrições de imagens/fotos), cruze todas as informações para preencher o Raio-X de forma completa.

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
- **verbas_deferidas[].trecho_fundamentacao**: para CADA verba, copie um trecho CURTO (máximo 150 caracteres) do DISPOSITIVO ou da fundamentação imediatamente anterior que DEFERE essa verba. Texto literal do documento, sem inventar. Não use null — se não houver trecho identificável, use string vazia "". A frase de exemplo na estrutura JSON abaixo é só ilustrativa; NÃO copie esse texto se não existir no documento.
- **verbas_deferidas[].pagina_origem**: sempre null na resposta da IA (preenchimento é feito no pós-processamento do sistema).

INSTRUÇÕES ESPECÍFICAS PARA CAMPOS DIFÍCEIS:
- jornada_contratual: buscar "jornada de X horas", "44h semanais", "horário de X às X" e calcular horas semanais. Se encontrar horário mas não jornada explícita, calcule: (saída - entrada - intervalo) × dias da semana
- fgts_periodo_completo: montar como "Todo o período contratual — [data_admissao] a [data_demissao]" usando as datas do próprio documento
- base_calculo de cada verba: buscar explicitamente o que compõe a base — "calculado sobre o salário base", "sobre a remuneração", "incidindo sobre"
- reflexos de cada verba: buscar frases "com reflexos em", "repercussão em", "integrando o salário para fins de". Listar apenas os explícitos
- fgts_sobre_aviso_previo / fgts_multa_40_aviso_previo / fgts_sobre_ferias_indenizadas: extrair do texto — se não mencionado, retornar null (não copiar regra padrão)
- salario_base: priorizar o valor RECONHECIDO PELO JUIZ, não o alegado pelas partes
- **data_sentenca**: é crucial para o cache e para juros/prescrição. Priorize "Assinado eletronicamente em DD/MM/AAAA" no cabeçalho. Se for Acórdão, busque "Data do Julgamento:" ou a data de publicação no final do documento ou no cabeçalho; "Publicado em DD/MM/AAAA" também vale. Nunca deixe null se houver qualquer data de assinatura/julgamento/publicação no texto.
- aviso_previo_dias: se aplicada a Lei 12.506/2011, registrar total + composição (ex: "42 dias — 30 + 12 pela Lei 12.506/2011")
- **valor_causa**: localize a expressão "Valor da causa:" no início do documento, em geral logo abaixo do número do processo (cabeçalho PJe/Relatório). Retorne o valor numérico no formato "R$ X.XXX,XX" (ex: R$ 32.181,17). Alternativas: "Valor atribuído à causa", "Dá-se à causa o valor de". Se não encontrar, null. Pode aparecer com barras de escape como "R\\$". Ignore as barras e extraia o valor.
- **advogado_reclamada**: atenção: em instâncias superiores a empresa pode aparecer como RECORRENTE ou RECORRIDO. Extraia os nomes dos advogados listados imediatamente abaixo do nome da empresa reclamada (ex.: KONA TRANSPORTES, PLATLOG), ignorando rótulos de polo processual. Verificar também rodapé da primeira página e assinaturas ao final. Campo da ré, não do reclamante. DICA DE LAYOUT PJE: Os nomes dos advogados costumam aparecer em linhas isoladas iniciadas por "ADVOGADO:" logo abaixo da linha "RECORRENTE:" ou "RECORRIDO:". Capture TODOS os advogados listados em bloco abaixo das empresas reclamadas (ex: LTDA, S.A).
- **data_ajuizamento**: no cabeçalho dos documentos PJe, a "Data da Autuação" deve ser extraída como data de ajuizamento (formato DD/MM/AAAA). Buscar "Data da Autuação:" no início do documento.
- **justica_gratuita**: procurar ativamente no final da fundamentação ou no dispositivo por frases como "concedo/defiro os benefícios da justiça gratuita", "gratuidade judiciária", "Justiça Gratuita", "Isenção de Custas". Em Acórdãos, verificar se o benefício foi mantido da origem. Retornar sempre booleano: true se concedida/deferida/mantida, false se não mencionado ou indeferido.

ESTRUTURA ESPERADA (retorne exatamente estas chaves, com null para não encontrados):
{{
  "numero_processo": null,
  "vara_trabalho": null,
  "reclamante": null,
  "reclamada": null,
  "tipo_rito": null,
  "funcao_reclamante": null,
  "advogado_reclamante": null,
  "advogado_reclamada": null,
  "juiz_responsavel": null,
  "valor_causa": null,

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
      "observacoes": null,
      "trecho_fundamentacao": "Defiro o pagamento de horas extras excedentes à 8ª diária, nos termos da fundamentação.",
      "pagina_origem": null
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
    retries: int = 2,
    pipeline_debug_meta: Optional[Mapping[str, str]] = None,
) -> dict:
    max_chars = CHARS_LIMIT.get(model_name, 15_000)
    meta = dict(pipeline_debug_meta or {})

    if settings.DEBUG_PIPELINE:
        from services.pipeline_debug import (
            alert_large_delta,
            log_etapa,
            maybe_write_dump,
        )

        log_etapa("ai_pre_remove_duplicatas", text, meta=meta)
        maybe_write_dump("ai_pre_remove_duplicatas", text, meta=meta)

    after_dedup = _remove_duplicatas(text)

    if settings.DEBUG_PIPELINE:
        from services.pipeline_debug import (
            alert_large_delta,
            log_etapa,
            maybe_write_dump,
        )

        log_etapa("ai_pos_remove_duplicatas", after_dedup, meta=meta)
        alert_large_delta("remove_duplicatas", text, after_dedup, meta=meta)
        maybe_write_dump("ai_pos_remove_duplicatas", after_dedup, meta=meta)

    truncated = _smart_truncate_after_dedup(
        after_dedup, max_chars, pipeline_debug_meta=meta
    )

    if settings.DEBUG_PIPELINE:
        from services.pipeline_debug import (
            alert_large_delta,
            log_etapa,
            maybe_write_dump,
        )

        log_etapa("ai_pos_smart_truncate", truncated, meta=meta)
        alert_large_delta("smart_truncate", after_dedup, truncated, meta=meta)
        maybe_write_dump("ai_pos_smart_truncate", truncated, meta=meta)
        print(
            f"   [DEBUG-PIPELINE] Corpo do documento enviado ao prompt: {len(truncated)} chars",
            flush=True,
        )

    prompt = _build_prompt(truncated, playbook, anchor_section)

    prompt_chars = len(prompt)
    tokens_est = prompt_chars // 4
    print(f"   [PROMPT] {prompt_chars} chars | ~{tokens_est} tokens estimados", flush=True)

    last_error = None
    for attempt in range(1, retries + 2):
        try:
            print(f"   [AI] {model_name} — tentativa {attempt}/{retries + 1} "
                  f"({len(truncated)} chars de texto)", flush=True)
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
            print(f"   [AI] {model_name} JSON inválido (tentativa {attempt}): {e}", flush=True)
            break

        except Exception as e:
            last_error = str(e)
            err_str = str(e).lower()

            if "429" in err_str or "quota" in err_str or "rate" in err_str:
                wait = 10 * attempt
                print(f"   [AI] Rate limit. Aguardando {wait}s...", flush=True)
                time.sleep(wait)
                continue

            if "timeout" in err_str or "deadline" in err_str or "503" in err_str:
                wait = 3 * attempt
                print(f"   [AI] Timeout. Aguardando {wait}s...")
                time.sleep(wait)
                continue

            print(f"   [AI] Erro não recuperável em {model_name}: {e}", flush=True)
            break

    raise RuntimeError(
        f"{model_name} falhou após {retries + 1} tentativas: {last_error}"
    )


# ── Quadro comparativo (dossiê: pedido × defesa × decisão) ─────────────────────

_DOSSIE_DOC_MARKER = "--- INÍCIO DO DOCUMENTO:"

_QUADRO_COMPARATIVO_INSTRUCTIONS = """Você é um perito calculista (direito do trabalho, Brasil).

O texto abaixo agrupa VÁRIOS documentos de um mesmo processo (seções começam com "{marker}").

TAREFA: cruzamento TRIPLO. Para cada verba ou pedido relevante:
1. resumo_pedido — o que o autor pleiteia na inicial (ou trecho indicado).
2. resumo_defesa — tese da reclamada na contestação; se não houver impugnação desse ponto, use algo como "Não impugnado / incontroverso".
3. resumo_decisao — o que o juiz decidiu (dispositivo/sentença).
4. status_final — em poucas palavras (ex.: "Deferida", "Indeferida", "Parcialmente deferida", "Não conhecida") com base na decisão.

REGRAS:
- Retorne APENAS JSON válido, sem markdown, sem ```json
- quadro_comparativo: lista de objetos com chaves exatas: verba_alvo, resumo_pedido, resumo_defesa, resumo_decisao, status_final (todas strings; use "" se desconhecido)
- Não invente fatos: baseie-se só no texto. Frases curtas (1–3 por campo).
- Priorize verbas trabalhistas (HE, adicionais, FGTS, aviso, férias, 13º, danos, multas etc.).

ESTRUTURA OBRIGATÓRIA:
{{
  "quadro_comparativo": [
    {{
      "verba_alvo": "",
      "resumo_pedido": "",
      "resumo_defesa": "",
      "resumo_decisao": "",
      "status_final": ""
    }}
  ]
}}

TEXTO DO DOSSIÊ:
"""


def _truncate_texto_dossie_para_quadro(texto: str, max_chars: int) -> str:
    """
    Preserva trecho de cada documento do dossiê (marcadores INÍCIO DO DOCUMENTO).
    Se não houver marcadores, reutiliza truncamento cirúrgico padrão.
    """
    if max_chars < 500:
        max_chars = 500
    if not texto:
        return ""
    if len(texto) <= max_chars:
        return texto
    if _DOSSIE_DOC_MARKER not in texto:
        return _smart_truncate(texto, max_chars)

    idxs: List[int] = []
    pos = 0
    while True:
        found = texto.find(_DOSSIE_DOC_MARKER, pos)
        if found < 0:
            break
        idxs.append(found)
        pos = found + 1
    if len(idxs) < 2:
        return _smart_truncate(texto, max_chars)

    segments: List[str] = []
    if idxs[0] > 0:
        head = texto[: idxs[0]].strip()
        if head:
            segments.append(head)
    for i, start in enumerate(idxs):
        end = idxs[i + 1] if i + 1 < len(idxs) else len(texto)
        segments.append(texto[start:end])

    n = len(segments)
    per = max(1, max_chars // n)
    out_chunks: List[str] = []
    for seg in segments:
        if len(seg) <= per:
            out_chunks.append(seg)
        else:
            omit = "\n[... trecho omitido por limite de contexto ...]\n"
            head = max(1, (per - len(omit)) // 2)
            tail = per - head - len(omit)
            if tail < 100:
                out_chunks.append(seg[:per])
            else:
                out_chunks.append(seg[:head] + omit + seg[-tail:])
    joined = "\n".join(out_chunks)
    if len(joined) > max_chars:
        return joined[:max_chars]
    return joined


def _normalize_quadro_comparativo_rows(raw: Any) -> List[Dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, str]] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        row = {
            "verba_alvo": str(it.get("verba_alvo") or "").strip(),
            "resumo_pedido": str(it.get("resumo_pedido") or "").strip(),
            "resumo_defesa": str(it.get("resumo_defesa") or "").strip(),
            "resumo_decisao": str(it.get("resumo_decisao") or "").strip(),
            "status_final": str(it.get("status_final") or "").strip(),
        }
        if not any(row.values()):
            continue
        if not row["verba_alvo"]:
            row["verba_alvo"] = "Pedido não identificado"
        out.append(row)
    return out


def extrair_quadro_comparativo_dossie(texto_dossie: str) -> Dict[str, Any]:
    """
    Segunda passagem opcional no dossiê multi-arquivo: quadro pedido × defesa × decisão.

    Falha segura: em erro retorna quadro_comparativo vazio (sem exceção ao caller).

    Returns:
        {"quadro_comparativo": list[dict], "model_used": str | None, "error": str | None}
    """
    empty: Dict[str, Any] = {
        "quadro_comparativo": [],
        "model_used": None,
        "error": None,
    }
    if not texto_dossie or not texto_dossie.strip():
        return empty

    last_error: str | None = None
    for model_name in MODELS_CASCADE:
        max_chars = CHARS_LIMIT.get(model_name, 15_000)
        # texto + instruções — reserva para o envelope do prompt
        body_budget = max(4000, max_chars - 6000)
        truncated = _truncate_texto_dossie_para_quadro(texto_dossie, body_budget)
        prompt = (
            _QUADRO_COMPARATIVO_INSTRUCTIONS.format(marker=_DOSSIE_DOC_MARKER)
            + truncated
        )
        print(
            f"[AI][QUADRO] modelo={model_name} | texto dossie: {len(texto_dossie)} | "
            f"após truncar: {len(truncated)} | prompt: {len(prompt)} chars",
            flush=True,
        )
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                raw_text = response.text.strip() if response.text else ""
                if not raw_text:
                    raise ValueError("Resposta vazia da IA")
                parsed = cast(
                    Dict[str, Any],
                    json.loads(_strip_markdown(raw_text)),
                )
                rows = _normalize_quadro_comparativo_rows(
                    parsed.get("quadro_comparativo")
                )
                print(f"[AI][QUADRO] OK — {len(rows)} linha(s)", flush=True)
                return {
                    "quadro_comparativo": rows,
                    "model_used": model_name,
                    "error": None,
                }
            except json.JSONDecodeError as e:
                last_error = f"JSON inválido: {e}"
                print(
                    f"[AI][QUADRO] {model_name} JSON inválido: {e}",
                    flush=True,
                )
                break
            except Exception as e:
                last_error = str(e)
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "rate" in err_str:
                    time.sleep(8 * attempt)
                    continue
                if "timeout" in err_str or "deadline" in err_str or "503" in err_str:
                    time.sleep(3 * attempt)
                    continue
                print(f"[AI][QUADRO] Erro {model_name}: {e}", flush=True)
                break

    print(f"[AI][QUADRO] Falha total — {last_error}", flush=True)
    empty["error"] = last_error
    return empty


# ── Extração de texto/OCR de imagem (dossiê multimodal) ───────────────────────

def extrair_texto_ou_descricao_imagem(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Usa Gemini multimodal para extrair texto visível (OCR) ou descrever a imagem.
    Útil para fotos de documentos, prints de tela ou holerites no dossiê.
    """
    if not image_bytes or len(image_bytes) < 10:
        return "[Imagem: vazia ou inválida]"
    prompt = (
        "Extraia ou transcreva TODO o texto visível nesta imagem (documento, print de tela ou foto). "
        "Se for tabela ou planilha, transcreva em formato texto legível (valores, datas, nomes). "
        "Se não houver texto, descreva brevemente o conteúdo da imagem. "
        "Retorne APENAS o texto extraído ou a descrição, sem explicações adicionais."
    )
    try:
        blob = Blob(data=image_bytes, mime_type=mime_type)
        contents = [
            Content(
                role="user",
                parts=[Part(inline_data=blob), Part(text=prompt)],
            )
        ]
        response = client.models.generate_content(
            model=MODELS_CASCADE[0],
            contents=contents,
        )
        raw = response.text.strip() if response.text else ""
        return raw if raw else "[Imagem: não foi possível extrair texto]"
    except Exception as e:
        print(f"[AI] Erro ao processar imagem (OCR/descrição): {e}", flush=True)
        return f"[Imagem: erro ao processar — {str(e)[:80]}]"


# ── Interface pública ─────────────────────────────────────────────────────────

def extract_data_with_gemini(
    text: str,
    playbook: str = "",
    pre_fields: dict = None,
    *,
    pipeline_debug_meta: Optional[Mapping[str, str]] = None,
) -> dict:
    """
    Extrai dados do texto com cascata de modelos Flash → Pro.

    Args:
        text:       Texto do documento (saída do sentence_finder).
        playbook:   Conteúdo do .md de skill correspondente ao tipo de documento.
        pre_fields: Dict {"high": {...}, "medium": {...}} do pre_extractor.
                    medium fields → injetados como âncoras no prompt.
                    high fields → não enviados (aplicados diretamente no processor).
        pipeline_debug_meta: Opcional — se DEBUG_PIPELINE=1, chaves job_id, user_id, label
                    para logs/dumps em services/pipeline_debug.py.

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
        f"| Âncoras: {len(pre_fields.get('medium', {})) if pre_fields else 0} campos",
        flush=True,
    )

    for model_name in MODELS_CASCADE:
        try:
            result = _call_model(
                model_name,
                text,
                playbook=playbook,
                anchor_section=anchor_section,
                pipeline_debug_meta=pipeline_debug_meta,
            )
            print(f"[AI] OK Sucesso com {model_name}", flush=True)
            return {"data": result, "model_used": model_name, "error": None}
        except Exception as e:
            print(f"[AI] FALHA {model_name} falhou: {e}", flush=True)

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
    model_name: str = "gemini-2.5-flash",
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
        model_name: modelo a ser usado (default: gemini-2.5-flash).

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

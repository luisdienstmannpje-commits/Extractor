"""
memoria_calculo/generator.py
M1 — Geração automática de memória de cálculo por extração.

Produz por job:
  - memoria_{job_id}.json  →  trilha de auditoria estruturada
  - (aba dedicada no .xlsx é responsabilidade do excel_exporter)

Princípios:
  - zero dependências externas (stdlib apenas)
  - nunca lança exceção para o caller — falha silenciosa com log
  - idempotente: regerar o mesmo job_id sobrescreve o arquivo anterior
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

# Diretório onde os JSONs de memória são salvos
# Resolvido em relação a este arquivo → backend/memoria_calculo/
_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Mapa: campo do ProcessoTrabalhista → (rule_id, campo_afetado)
#
# Cobre apenas as regras que definem um campo escalar em dados_finais (~7).
# As demais (~13) são de consistência ou atuam em verbas_deferidas — não têm
# "campo" único; a lista completa de IDs fica em regras_aplicadas_ids na memória.
# ---------------------------------------------------------------------------
_CAMPO_PARA_REGRA: list[tuple[str, str, str]] = [
    # campo em dados_finais          rule_id                    campo_afetado
    ("fgts_sobre_aviso_previo",      "SUMULA_305_TST",          "fgts_sobre_aviso_previo"),
    ("fgts_multa_40_aviso_previo",   "OJ_42_SDI1_TST",          "fgts_multa_40_aviso_previo"),
    ("fgts_sobre_ferias_indenizadas","OJ_195_SDI1_TST",         "fgts_sobre_ferias_indenizadas"),
    ("multa_art_467",                "ART_467_CLT",             "multa_art_467"),
    ("multa_art_477",                "ART_477_CLT",             "multa_art_477"),
    ("honorarios_sucumbenciais",     "ART_791A_CLT",            "honorarios_sucumbenciais"),
    ("aviso_previo_dias",            "ART_487_CLT_LEI_12506",   "aviso_previo_dias"),
]

# Campos que o pre_extractor tenta preencher (HIGH + MEDIUM confidence)
_CAMPOS_PRE_EXTRACTOR: tuple[str, ...] = (
    "numero_processo",
    "data_sentenca",
    "justica_gratuita",
    "tipo_rito",
    "data_ajuizamento",
    "data_admissao",
    "data_demissao",
    "salario_base",
    "indice_correcao",
    "juros_mora",
    "tipo_contrato",
    "motivo_rescisao",
)

# status_final que indicam verba INDEFERIDA
_STATUS_INDEFERIDO = frozenset([
    "indeferido",
    "improcedente",
    "não deferido",
    "nao deferido",
    "negado",
    "julgado improcedente",
])


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _derivar_regras_aplicadas(dados: dict) -> list[dict]:
    """
    Percorre os campos do ProcessoTrabalhista e mapeia os que têm valor
    para os IDs de regras do Legal Engine.
    """
    regras: list[dict] = []
    for campo, rule_id, campo_afetado in _CAMPO_PARA_REGRA:
        valor = dados.get(campo)
        if valor is not None:
            regras.append({
                "id": rule_id,
                "campo_afetado": campo_afetado,
                "resultado": valor,
            })
    return regras


def _contar_verbas(dados: dict) -> tuple[int, int]:
    """
    Retorna (deferidas, indeferidas).
    Verbas sem status_final são contadas como deferidas (default conservador).
    """
    verbas: list[dict] = dados.get("verbas_deferidas") or []
    indeferidas = sum(
        1 for v in verbas
        if (v.get("status_final") or "").lower().strip() in _STATUS_INDEFERIDO
    )
    deferidas = len(verbas) - indeferidas
    return deferidas, indeferidas


def _contar_campos_pre_extractor(dados: dict) -> int:
    """Conta quantos dos campos de alta/média confiança do pre_extractor foram preenchidos."""
    return sum(1 for campo in _CAMPOS_PRE_EXTRACTOR if dados.get(campo) not in (None, ""))


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def gerar_memoria(
    job_id: str,
    dados: dict,
    model_used: str,
    doc_type: str,
    avisos_dedup: list[str] | None = None,
    explicacoes: list | None = None,
) -> dict:
    """
    Gera e persiste a memória de cálculo de uma extração.

    Parâmetros
    ----------
    job_id       : identificador do job (usado no nome do arquivo)
    dados        : dados_finais do processor — resultado completo da extração
    model_used   : string do modelo Gemini utilizado ("gemini-2.0-flash" / "gemini-2.5-pro")
    doc_type     : tipo do documento ("sentenca", "acordao", etc.)
    avisos_dedup : lista de strings geradas pelo verba_deduplicator (pode ser vazia)

    Retorna
    -------
    dict com a memória gerada (mesmo conteúdo do JSON salvo em disco)
    """
    avisos_dedup = avisos_dedup or []
    ts = datetime.now(tz=timezone.utc).isoformat()

    verbas_def, verbas_indef = _contar_verbas(dados)
    campos_pre = _contar_campos_pre_extractor(dados)
    regras = _derivar_regras_aplicadas(dados)
    # Lista completa de IDs das regras executadas pelo engine (rastreabilidade total)
    regras_ids_raw = dados.get("regras_aplicadas")
    regras_aplicadas_ids: list[str] = (
        list(regras_ids_raw) if isinstance(regras_ids_raw, list) and regras_ids_raw and isinstance(regras_ids_raw[0], str) else []
    )

    # alertas_juridicos já inclui avisos_dedup (mesclados no passo 8 do processor)
    alertas: list[Any] = list(dados.get("alertas_juridicos") or [])

    memoria: dict = {
        "job_id": job_id,
        "numero_processo": dados.get("numero_processo"),
        "reclamante": dados.get("reclamante"),
        "reclamada": dados.get("reclamada"),
        "timestamp": ts,
        "doc_type": doc_type,
        "pipeline": {
            "pre_extractor": {
                "campos_extraidos": campos_pre,
                "total_monitorados": len(_CAMPOS_PRE_EXTRACTOR),
            },
            "ai_model_used": model_used,
            # Gemini SDK não expõe contagem de tokens diretamente — reservado para
            # quando o ai_client passar usage_metadata no resultado.
            "tokens_consumidos": dados.get("_meta_tokens_consumidos", 0),
        },
        "regras_aplicadas": regras,
        "regras_aplicadas_ids": regras_aplicadas_ids,
        "alertas": alertas,
        "verbas_deferidas": verbas_def,
        "verbas_indeferidas": verbas_indef,
        "deduplicacao": {
            "duplicatas_removidas": len(avisos_dedup),
            "avisos": avisos_dedup,
        },
        "explicacoes": explicacoes or [],
        "shadow_logs": list(dados.get("shadow_logs") or []),
    }

    # ── Persistência ──────────────────────────────────────────────────────────
    filename = f"memoria_{job_id}.json"
    out_path = os.path.join(_OUTPUT_DIR, filename)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(memoria, f, ensure_ascii=False, indent=2)
        print(f"[M1] Memória de cálculo salva → {filename}")
    except Exception as exc:
        # Nunca interrompe o pipeline por falha de persistência
        print(f"[M1] Aviso: falha ao salvar memória em disco: {exc}")

    return memoria
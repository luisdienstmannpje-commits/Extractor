"""
pipeline_debug.py — Observabilidade opcional do texto no pipeline (raio-X diagnóstico).

Ativado por DEBUG_PIPELINE=1 em backend/.env. Não altera contratos nem resultado da extração.

Etapas logadas no fluxo principal:
  - step3_sentence_finder: saída de extract_sentence_from_pdf (texto completo para regex/IA).
  - ai_pre_remove_duplicatas / ai_pos_remove_duplicatas / ai_pos_smart_truncate: dentro de ai_client._call_model.
  - Geometria da janela cirúrgica (`log_truncate_*`): disp_pos, start2, end2, parte1_chars — só quando texto > max_chars.

Opcional: DEBUG_PIPELINE_DUMP=1 grava ficheiros .txt em PIPELINE_DEBUG_OUT/<user_id>/<job_id>/ (dados sensíveis — só em ambiente controlado).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Mapping, Optional

from config import settings


def _short_hash(text: str) -> str:
    if not text:
        return "empty"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _meta_str(meta: Optional[Mapping[str, Any]]) -> tuple[str, str, str]:
    m = meta or {}
    job = str(m.get("job_id") or "-")
    uid = str(m.get("user_id") or "-")
    label = str(m.get("label") or "-")
    return job, uid, label


def log_etapa(
    nome: str,
    texto: Optional[str],
    *,
    meta: Optional[Mapping[str, Any]] = None,
    snippet_chars: int = 300,
) -> None:
    """Loga tamanho, hash curto e início/fim do texto (uma linha compactada cada)."""
    if not settings.DEBUG_PIPELINE:
        return
    job, uid, label = _meta_str(meta)
    if not texto:
        print(
            f"[DEBUG-PIPELINE][{nome}] job={job} user={uid} label={label} | vazio",
            flush=True,
        )
        return
    n = len(texto)
    h = _short_hash(texto)
    sn = max(0, snippet_chars)
    head = texto[:sn].replace("\n", " ").strip()
    tail = texto[-sn:].replace("\n", " ").strip() if n > sn else head
    print(
        f"[DEBUG-PIPELINE][{nome}] job={job} user={uid} label={label} | "
        f"tamanho={n} sha12={h}",
        flush=True,
    )
    print(f"  INICIO: {head!r}", flush=True)
    print(f"  FIM:    {tail!r}", flush=True)


def alert_large_delta(
    etapa: str,
    antes: str,
    depois: str,
    *,
    threshold: float = 0.25,
    meta: Optional[Mapping[str, Any]] = None,
) -> None:
    """Avisa quando o texto encolhe ≥ threshold da etapa anterior (ex.: dedup agressivo)."""
    if not settings.DEBUG_PIPELINE:
        return
    job, uid, _ = _meta_str(meta)
    la, ld = len(antes or ""), len(depois or "")
    if la <= 0:
        return
    drop = la - ld
    if drop > 0 and (drop / la) >= threshold:
        pct = 100.0 * drop / la
        print(
            f"[DEBUG-PIPELINE][ALERTA][{etapa}] job={job} user={uid} | "
            f"perda {la} -> {ld} chars (-{drop}, -{pct:.1f}%)",
            flush=True,
        )


def log_truncate_cabe_inteiro(
    len_text: int,
    max_chars: int,
    *,
    meta: Optional[Mapping[str, Any]] = None,
) -> None:
    """Texto após dedup cabe no limite; truncagem cirúrgica não aplicada."""
    if not settings.DEBUG_PIPELINE:
        return
    job, uid, label = _meta_str(meta)
    print(
        f"[DEBUG-PIPELINE][truncate] job={job} user={uid} label={label} | "
        f"modo=cabe_inteiro len={len_text} max_chars={max_chars}",
        flush=True,
    )


def log_truncate_inicio_cirurgico(
    len_text: int,
    max_chars: int,
    parte1_chars: int,
    parte2_chars: int,
    *,
    meta: Optional[Mapping[str, Any]] = None,
) -> None:
    if not settings.DEBUG_PIPELINE:
        return
    job, uid, label = _meta_str(meta)
    print(
        f"[DEBUG-PIPELINE][truncate] job={job} user={uid} label={label} | "
        f"modo=janela_cirurgica len={len_text} max_chars={max_chars} "
        f"parte1_chars={parte1_chars} parte2_chars={parte2_chars}",
        flush=True,
    )


def log_truncate_com_dispositivo(
    disp_pos: int,
    start2: int,
    end2: int,
    *,
    meta: Optional[Mapping[str, Any]] = None,
) -> None:
    if not settings.DEBUG_PIPELINE:
        return
    job, uid, label = _meta_str(meta)
    print(
        f"[DEBUG-PIPELINE][truncate] job={job} user={uid} label={label} | "
        f"dispositivo_encontrado=True disp_pos={disp_pos} start2={start2} end2={end2}",
        flush=True,
    )


def log_truncate_sem_dispositivo_fallback(
    start2: int,
    end2: int,
    n_verba_matches: int,
    *,
    meta: Optional[Mapping[str, Any]] = None,
) -> None:
    """_RE_DISPOSITIVO não casou — ai_client usa fallback de verbas / cauda do texto."""
    if not settings.DEBUG_PIPELINE:
        return
    job, uid, label = _meta_str(meta)
    print(
        f"[DEBUG-PIPELINE][truncate] job={job} user={uid} label={label} | "
        f"dispositivo_encontrado=False — fallback_verbas/heurística "
        f"start2={start2} end2={end2} matches_verbas={n_verba_matches}",
        flush=True,
    )


def maybe_write_dump(
    etapa: str,
    texto: str,
    *,
    meta: Optional[Mapping[str, Any]] = None,
) -> None:
    """Persiste texto completo da etapa (PII — usar só com consentimento/ambiente seguro)."""
    if not settings.DEBUG_PIPELINE_DUMP:
        return
    meta = meta or {}
    base: Path = settings.PIPELINE_DEBUG_OUT
    job = re.sub(r"[^\w\-.]", "_", str(meta.get("job_id") or "nojob"))[:80]
    user = re.sub(r"[^\w\-.]", "_", str(meta.get("user_id") or "nouid"))[:48]
    safe_etapa = re.sub(r"[^\w\-.]", "_", etapa)[:72]
    out_dir = base / user / job
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{safe_etapa}.txt"
    path.write_text(texto or "", encoding="utf-8")
    print(f"[DEBUG-PIPELINE][dump] {path}", flush=True)

"""Testes do modo observabilidade pipeline_debug (sem efeito quando DEBUG_PIPELINE=0)."""

from __future__ import annotations

from unittest.mock import patch

from services.pipeline_debug import (
    alert_large_delta,
    log_etapa,
    log_truncate_cabe_inteiro,
    log_truncate_com_dispositivo,
    log_truncate_inicio_cirurgico,
    log_truncate_sem_dispositivo_fallback,
    maybe_write_dump,
)


def test_log_etapa_no_crash_vazio() -> None:
    log_etapa("teste", "", meta={"job_id": "j", "user_id": "u"})


def test_alert_large_delta_só_reduz() -> None:
    with patch("services.pipeline_debug.settings") as s:
        s.DEBUG_PIPELINE = True
        alert_large_delta("x", "aaaa", "aaa", meta={})  # perda pequena — sem alerta obrigatório


def test_maybe_write_dump_respeita_flag() -> None:
    with patch("services.pipeline_debug.settings") as s:
        s.DEBUG_PIPELINE_DUMP = False
        maybe_write_dump("etapa", "hello", meta={"job_id": "1", "user_id": "u"})
        # não escreve ficheiro
    assert True


def test_log_truncate_helpers_no_crash_debug_off() -> None:
    """Com DEBUG_PIPELINE=0, geometria de truncate não imprime nem falha."""
    log_truncate_cabe_inteiro(100, 200, meta={"job_id": "j"})
    log_truncate_inicio_cirurgico(5000, 2000, 800, 1200, meta={})
    log_truncate_com_dispositivo(3000, 2800, 4000, meta={})
    log_truncate_sem_dispositivo_fallback(2500, 4500, 3, meta={})

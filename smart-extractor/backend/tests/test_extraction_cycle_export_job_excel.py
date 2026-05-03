"""Ciclos de extracao: GET /export-excel/{job_id} sem upload real."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import extractor as extractor_mod
import services.excel_exporter as excel_exporter


app_export_job_only = FastAPI()
app_export_job_only.include_router(extractor_mod.router)


def _put_job(job_id: str, payload: dict[str, Any]) -> None:
    with extractor_mod._jobs_lock:
        extractor_mod._jobs_mem[job_id] = payload


def _drop_job(job_id: str) -> None:
    with extractor_mod._jobs_lock:
        extractor_mod._jobs_mem.pop(job_id, None)


def test_export_excel_job_pronto_retorna_xlsx(
    monkeypatch: Any,
    tmp_path,
) -> None:
    """Job finalizado em memoria gera XLSX sob demanda com exporter mockado."""
    job_id = "job-export-excel-e2e"
    xlsx_path = tmp_path / "job.xlsx"
    xlsx_path.write_bytes(b"PK\x03\x04mock-job-xlsx")
    chamadas: list[tuple[dict[str, Any], str]] = []

    def fake_exportar_excel(dados: dict[str, Any], received_job_id: str) -> str:
        chamadas.append((dados, received_job_id))
        return str(xlsx_path)

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    job_payload = {
        "status": "done",
        "numero_processo": "1234567-89.2024.5.01.0001",
        "reclamante": "Autor Job",
        "verbas_deferidas": [{"nome": "Horas extras"}],
    }
    _put_job(job_id, job_payload)

    try:
        with TestClient(app_export_job_only) as client:
            response = client.get(f"/export-excel/{job_id}")
    finally:
        _drop_job(job_id)

    assert response.status_code == 200, response.text
    assert response.content == b"PK\x03\x04mock-job-xlsx"
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    cd = response.headers.get("content-disposition", "")
    assert "extrator_1234567-8920245010001.xlsx" in cd

    assert len(chamadas) == 1
    dados_limpos, received_job_id = chamadas[0]
    assert received_job_id == job_id
    assert "status" not in dados_limpos
    assert dados_limpos["numero_processo"] == "1234567-89.2024.5.01.0001"
    assert dados_limpos["verbas_deferidas"][0]["nome"] == "Horas extras"


def test_export_excel_job_ausente_retorna_404_sem_exporter(
    monkeypatch: Any,
) -> None:
    """Job inexistente retorna 404 antes de chamar o exporter."""
    job_id = "job-export-ausente-e2e"
    _drop_job(job_id)

    chamadas: list[Any] = []

    def fake_exportar_excel(*args: Any, **kwargs: Any) -> str:
        chamadas.append((args, kwargs))
        raise AssertionError("job ausente nao deve chamar exporter")

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    with TestClient(app_export_job_only) as client:
        response = client.get(f"/export-excel/{job_id}")

    assert response.status_code == 404
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert job_id in detail
    assert "não encontrado" in detail or "nao encontrado" in detail.lower()
    assert chamadas == []


def test_export_excel_job_processing_retorna_202_sem_exporter(
    monkeypatch: Any,
) -> None:
    """Job ainda em processamento retorna 202 antes de chamar exporter."""
    job_id = "job-export-processing-e2e"
    _put_job(job_id, {"status": "processing"})
    chamadas: list[Any] = []

    def fake_exportar_excel(*args: Any, **kwargs: Any) -> str:
        chamadas.append((args, kwargs))
        raise AssertionError("job processing nao deve chamar exporter")

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    try:
        with TestClient(app_export_job_only) as client:
            response = client.get(f"/export-excel/{job_id}")
    finally:
        _drop_job(job_id)

    assert response.status_code == 202
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert "processing" in detail
    assert chamadas == []


def test_export_excel_job_error_retorna_400_sem_exporter(
    monkeypatch: Any,
) -> None:
    """Job em erro retorna 400 antes de chamar exporter."""
    job_id = "job-export-error-e2e"
    _put_job(job_id, {"status": "error", "msg": "falha fake"})
    chamadas: list[Any] = []

    def fake_exportar_excel(*args: Any, **kwargs: Any) -> str:
        chamadas.append((args, kwargs))
        raise AssertionError("job error nao deve chamar exporter")

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    try:
        with TestClient(app_export_job_only) as client:
            response = client.get(f"/export-excel/{job_id}")
    finally:
        _drop_job(job_id)

    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert "erro" in detail.lower()
    assert "exportar" in detail.lower()
    assert chamadas == []


def test_export_excel_job_resultado_invalido_retorna_400_sem_exporter(
    monkeypatch: Any,
) -> None:
    """Job finalizado sem dict exportavel retorna 400 antes de chamar exporter."""
    job_id = "job-export-invalido-e2e"
    _put_job(job_id, {"status": "done", "result": []})
    chamadas: list[Any] = []

    def fake_exportar_excel(*args: Any, **kwargs: Any) -> str:
        chamadas.append((args, kwargs))
        raise AssertionError("resultado invalido nao deve chamar exporter")

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    try:
        with TestClient(app_export_job_only) as client:
            response = client.get(f"/export-excel/{job_id}")
    finally:
        _drop_job(job_id)

    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert "resultado" in detail.lower()
    assert "inv" in detail.lower()
    assert chamadas == []


def test_export_excel_job_falha_exporter_retorna_500_estavel(
    monkeypatch: Any,
) -> None:
    """Falha do exporter no endpoint por job_id vira 500 com mensagem estavel."""
    job_id = "job-export-falha-exporter-e2e"
    _put_job(
        job_id,
        {
            "status": "done",
            "numero_processo": "1234567-89.2024.5.01.0001",
            "verbas_deferidas": [{"nome": "Horas extras"}],
        },
    )

    def fake_exportar_excel(_dados: dict[str, Any], _job_id: str) -> str:
        raise RuntimeError("falha fake export job")

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    try:
        with TestClient(app_export_job_only) as client:
            response = client.get(f"/export-excel/{job_id}")
    finally:
        _drop_job(job_id)

    assert response.status_code == 500
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert "Erro ao gerar Excel" in detail
    assert "falha fake export job" in detail

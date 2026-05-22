"""Ciclos de extracao: contratos HTTP de exportacao sem gerar arquivos reais pesados."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import exports as exports_router
import services.excel_exporter as excel_exporter
import services.pjc_exporter as pjc_exporter


app_export_only = FastAPI()
app_export_only.include_router(exports_router.router)


def test_export_excel_sentenca_limpa_campos_e_retornaxlsx(
    monkeypatch: Any,
    tmp_path,
) -> None:
    """POST /api/export/excel limpa campos pesados e devolve XLSX com nome por CNJ."""
    xlsx_path = tmp_path / "mock.xlsx"
    xlsx_path.write_bytes(b"PK\x03\x04mock-xlsx")
    chamadas: list[tuple[dict[str, Any], str]] = []

    def fake_exportar_excel(dados: dict[str, Any], job_id: str) -> str:
        chamadas.append((dados, job_id))
        return str(xlsx_path)

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    body = {
        "numero_processo": "1234567-89.2024.5.01.0001",
        "reclamante": "Autor Export",
        "reclamada": "Re Export",
        "verbas_deferidas": [{"nome": "Horas extras"}],
        "memorial_juridico": [{"id": "m1"}],
        "explicacoes": ["muito grande"],
        "shadow_logs": [{"x": 1}],
        "raw": "texto bruto",
    }

    with TestClient(app_export_only) as client:
        response = client.post("/api/export/excel", json=body)

    assert response.status_code == 200, response.text
    assert response.content == b"PK\x03\x04mock-xlsx"
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    cd = response.headers.get("content-disposition", "")
    assert "Auditoria_Calculo" in cd
    assert "1234567-8920245010001.xlsx" in cd

    assert len(chamadas) == 1
    dados_limpos, job_id = chamadas[0]
    assert job_id == "1234567-89.2024.5.01.0001"
    assert dados_limpos["numero_processo"] == "1234567-89.2024.5.01.0001"
    assert dados_limpos["verbas_deferidas"][0]["nome"] == "Horas extras"
    assert "memorial_juridico" not in dados_limpos
    assert "explicacoes" not in dados_limpos
    assert "shadow_logs" not in dados_limpos
    assert "raw" not in dados_limpos


def test_export_excel_peticao_preserva_memorial_e_nome_especifico(
    monkeypatch: Any,
    tmp_path,
) -> None:
    """Peticao inicial preserva memorial_juridico para a aba Resumo e usa filename proprio."""
    xlsx_path = tmp_path / "peticao.xlsx"
    xlsx_path.write_bytes(b"PK\x03\x04mock-peticao-xlsx")
    chamadas: list[tuple[dict[str, Any], str]] = []

    def fake_exportar_excel(dados: dict[str, Any], job_id: str) -> str:
        chamadas.append((dados, job_id))
        return str(xlsx_path)

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    body = {
        "_meta_doc_type": "peticao_inicial",
        "numero_processo": "7654321-10.2024.5.02.0002",
        "verbas_pedidas": [{"nome": "Adicional noturno"}],
        "memorial_juridico": "Memorial da peticao deve ir ao Excel",
        "explicacoes": ["remover"],
        "shadow_logs": [{"remover": True}],
    }

    with TestClient(app_export_only) as client:
        response = client.post("/api/export/excel", json=body)

    assert response.status_code == 200, response.text
    assert response.content == b"PK\x03\x04mock-peticao-xlsx"
    cd = response.headers.get("content-disposition", "")
    assert "Pedidos_Inicial_7654321-1020245020002.xlsx" in cd

    assert len(chamadas) == 1
    dados_limpos, job_id = chamadas[0]
    assert job_id == "7654321-10.2024.5.02.0002"
    assert dados_limpos["_meta_doc_type"] == "peticao_inicial"
    assert dados_limpos["memorial_juridico"] == "Memorial da peticao deve ir ao Excel"
    assert dados_limpos["verbas_pedidas"][0]["nome"] == "Adicional noturno"
    assert "explicacoes" not in dados_limpos
    assert "shadow_logs" not in dados_limpos


def test_export_excel_contestacao_preserva_memorial_e_nome_especifico(
    monkeypatch: Any,
    tmp_path,
) -> None:
    """Contestacao preserva memorial_juridico para a aba Resumo e usa filename proprio."""
    xlsx_path = tmp_path / "contestacao.xlsx"
    xlsx_path.write_bytes(b"PK\x03\x04mock-contestacao-xlsx")
    chamadas: list[tuple[dict[str, Any], str]] = []

    def fake_exportar_excel(dados: dict[str, Any], job_id: str) -> str:
        chamadas.append((dados, job_id))
        return str(xlsx_path)

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    body = {
        "_meta_doc_type": "contestacao",
        "numero_processo": "7654321-10.2024.5.02.0002",
        "teses_defesa": [{"verba_alvo": "Horas extras", "tese_principal": "Nega"}],
        "memorial_juridico": "Memorial de defesa deve ir ao Excel",
        "explicacoes": ["remover"],
        "shadow_logs": [{"remover": True}],
    }

    with TestClient(app_export_only) as client:
        response = client.post("/api/export/excel", json=body)

    assert response.status_code == 200, response.text
    assert response.content == b"PK\x03\x04mock-contestacao-xlsx"
    cd = response.headers.get("content-disposition", "")
    assert "Contestacao_7654321-1020245020002.xlsx" in cd

    assert len(chamadas) == 1
    dados_limpos, job_id = chamadas[0]
    assert job_id == "7654321-10.2024.5.02.0002"
    assert dados_limpos["_meta_doc_type"] == "contestacao"
    assert dados_limpos["memorial_juridico"] == "Memorial de defesa deve ir ao Excel"
    assert dados_limpos["teses_defesa"][0]["verba_alvo"] == "Horas extras"
    assert "explicacoes" not in dados_limpos
    assert "shadow_logs" not in dados_limpos


def test_export_excel_corpo_vazio_retorna_400_sem_exporter(
    monkeypatch: Any,
) -> None:
    """Body vazio/invalido retorna 400 antes de chamar o exporter."""
    chamadas: list[Any] = []

    def fake_exportar_excel(*args: Any, **kwargs: Any) -> str:
        chamadas.append((args, kwargs))
        raise AssertionError("corpo vazio nao deve chamar exporter")

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    with TestClient(app_export_only) as client:
        response = client.post("/api/export/excel", json={})

    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert "corpo" in detail.lower()
    assert chamadas == []


def test_export_excel_falha_exporter_retorna_500_estavel(
    monkeypatch: Any,
) -> None:
    """Falha do exporter vira 500 com tipo e mensagem do erro."""

    def fake_exportar_excel(_dados: dict[str, Any], _job_id: str) -> str:
        raise RuntimeError("falha fake exporter")

    monkeypatch.setattr(excel_exporter, "exportar_excel", fake_exportar_excel)

    with TestClient(app_export_only) as client:
        response = client.post(
            "/api/export/excel",
            json={
                "numero_processo": "1234567-89.2024.5.01.0001",
                "verbas_deferidas": [{"nome": "Horas extras"}],
            },
        )

    assert response.status_code == 500
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert "Erro ao gerar Excel" in detail
    assert "RuntimeError" in detail
    assert "falha fake exporter" in detail


def test_export_pjc_happy_path_retorna_xml_com_headers(
    monkeypatch: Any,
) -> None:
    """POST /api/export/pjc devolve XML/PJC com filename e versao estaveis."""
    chamadas: list[dict[str, Any]] = []

    def fake_exportar_pjc(body: dict[str, Any]) -> bytes:
        chamadas.append(body)
        return b"<pjc>mock</pjc>"

    monkeypatch.setattr(pjc_exporter, "exportar_pjc", fake_exportar_pjc)
    monkeypatch.setattr(pjc_exporter, "gerar_nome_arquivo", lambda _body: "calculo_mock.pjc")

    body = {
        "numero_processo": "1234567-89.2024.5.01.0001",
        "verbas_deferidas": [{"nome": "Horas extras"}],
    }

    with TestClient(app_export_only) as client:
        response = client.post("/api/export/pjc", json=body)

    assert response.status_code == 200, response.text
    assert response.content == b"<pjc>mock</pjc>"
    assert response.headers["content-type"].startswith("application/xml")
    assert response.headers["x-pjc-version"] == "5.4"
    assert 'filename="calculo_mock.pjc"' in response.headers.get("content-disposition", "")
    assert chamadas == [body]


def test_export_pjc_corpo_vazio_retorna_400_sem_exporter(
    monkeypatch: Any,
) -> None:
    """Body vazio/invalido retorna 400 antes de chamar exportar_pjc."""
    chamadas: list[Any] = []

    def fake_exportar_pjc(*args: Any, **kwargs: Any) -> bytes:
        chamadas.append((args, kwargs))
        raise AssertionError("corpo vazio nao deve chamar exporter PJC")

    monkeypatch.setattr(pjc_exporter, "exportar_pjc", fake_exportar_pjc)

    with TestClient(app_export_only) as client:
        response = client.post("/api/export/pjc", json={})

    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert "corpo" in detail.lower()
    assert chamadas == []


def test_export_pjc_falha_exporter_retorna_500_estavel(
    monkeypatch: Any,
) -> None:
    """Falha do exporter PJC vira 500 com tipo e mensagem do erro."""

    def fake_exportar_pjc(_body: dict[str, Any]) -> bytes:
        raise RuntimeError("falha fake pjc")

    monkeypatch.setattr(pjc_exporter, "exportar_pjc", fake_exportar_pjc)
    monkeypatch.setattr(pjc_exporter, "gerar_nome_arquivo", lambda _body: "nao_usado.pjc")

    with TestClient(app_export_only) as client:
        response = client.post(
            "/api/export/pjc",
            json={
                "numero_processo": "1234567-89.2024.5.01.0001",
                "verbas_deferidas": [{"nome": "Horas extras"}],
            },
        )

    assert response.status_code == 500
    detail = response.json().get("detail", "")
    assert isinstance(detail, str)
    assert "Erro ao gerar PJC" in detail
    assert "RuntimeError" in detail
    assert "falha fake pjc" in detail

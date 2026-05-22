"""
Ciclo e2e HTTP enxuto: POST /upload → GET /status/{job_id} sem Gemini real.

- App mínima: só `api.routers.extractor` + `register_worker_event_loop` (igual necessidade
  do worker em thread; sem WebSocket neste teste).
- `process_lawsuit_pdf` mockado no módulo do router (processamento/IA não roda).
- PDF mínimo: ≥10 bytes (validação do upload), conteúdo opaco.

Borda HTTP: `cache_context=peticao_inicial` com **dois** arquivos → `400` por
`_should_run_process_lawsuit_pdf_upload` (alinhado a `test_upload_cache_context`).
Processadores não são enfileirados (sem `BackgroundTasks` para o worker).

WebSocket feliz: após `POST /upload`, `GET /ws/{job_id}` recebe JSON terminal igual ao
armazenado no job (`status` mapeado para `done`), sem campo `type: "result"` na rota atual
(ver `websocket_job` em `extractor.py`). Heartbeats `{"status": "processing"}` são ignorados.

WebSocket com `partial_update`: `push_ws_partial` só enfileira se já existir fila para o
`job_id` (`_enqueue_ws_message`). O fake de `process_lawsuit_pdf` espera um `threading.Event`
liberado **depois** de `websocket_connect`, para evitar corrida com o worker em thread.

Helpers locais: `_post_minimal_upload_queued`, `_cleanup_job`, `_recv_ws_json`,
`_read_ws_terminal_skipping_noise` — reduzem ruído; asserts de negócio ficam nos testes.

Erro no worker: exceção em `process_lawsuit_pdf` → `_run_job_with_timeout` grava
dict com status `erro` e `msg` prefixada com `Exceção não tratada:`, depois normaliza para
`status` HTTP/memória `error`. O mesmo dict é servido por `/status` e por `/ws/{job_id}`
(terminal imediato se o job já falhou antes do connect, ou via fila).
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from api.routers import extractor as extractor_mod


@asynccontextmanager
async def _lifespan_upload_api(app: FastAPI):
    extractor_mod.register_worker_event_loop(asyncio.get_running_loop())
    yield


app_upload_only = FastAPI(lifespan=_lifespan_upload_api)
app_upload_only.include_router(extractor_mod.router)

_MIN_PDF = b"%PDF-1.4\nminimal\n"  # ≥10 bytes


def _fake_process_lawsuit_pdf(
    user_id: str,
    file_bytes: bytes,
    job_id: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    assert len(file_bytes) >= 10
    return {
        "status": "sucesso",
        "source": "ai",
        "doc_type": "liquidacao",
        "model_used": "mock-upload-api",
        "qualidade_ok": True,
        "data": {
            "numero_processo": "0000000-00.0000.0.00.0000",
            "reclamante": "Autor Fixture API",
            "reclamada": None,
            "verbas_deferidas": [
                {"nome": "Horas extras", "status_final": "deferida"},
            ],
        },
        "alertas_juridicos": [],
        "regras_aplicadas": [],
        "explicacoes": [],
        "memorial_juridico": [],
        "raiox": {},
    }


def _poll_status(client: TestClient, job_id: str, timeout_s: float = 15.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        r = client.get(f"/status/{job_id}")
        assert r.status_code == 200, r.text
        last = r.json()
        if last.get("status") not in ("queued", "processing"):
            return last
        time.sleep(0.05)
    pytest.fail(f"timeout aguardando job finalizar; último={last}")


def _post_minimal_upload_queued(
    client: TestClient,
    *,
    user_id: str,
    filename: str,
    cache_context: str | None = None,
) -> str:
    """POST /upload com um PDF mínimo; confirma envelope inicial `queued` e devolve `job_id`."""
    files = [("files", (filename, _MIN_PDF, "application/pdf"))]
    data: dict[str, str] = {"user_id": user_id}
    if cache_context is not None:
        data["cache_context"] = cache_context
    up = client.post(
        "/upload",
        data=data,
        files=files,
        headers={"x-user-id": user_id},
    )
    assert up.status_code == 200, up.text
    body = up.json()
    assert body.get("status") == "queued"
    assert body.get("job_id")
    assert "timeout_seconds" in body
    return str(body["job_id"])


def _cleanup_job(client: TestClient, job_id: str) -> None:
    client.delete(f"/jobs/{job_id}")


def _recv_ws_json(websocket: Any) -> dict[str, Any]:
    return json.loads(websocket.receive_text())


def _read_ws_terminal_skipping_noise(websocket: Any, *, timeout_s: float = 30.0) -> dict[str, Any]:
    """Descarta heartbeat `processing` e `partial_update` até a primeira mensagem terminal."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        msg = _recv_ws_json(websocket)
        if msg.get("status") == "processing":
            continue
        if msg.get("type") == "partial_update":
            continue
        assert extractor_mod._ws_payload_is_terminal(msg), (
            f"mensagem WS não terminal: {list(msg.keys())}"
        )
        return msg
    pytest.fail("timeout aguardando mensagem terminal no WebSocket")


def test_upload_minimal_pdf_then_status_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", _fake_process_lawsuit_pdf)

    with TestClient(app_upload_only) as client:
        job_id = _post_minimal_upload_queued(
            client,
            user_id="user-upload-api-e2e",
            filename="minimal.pdf",
        )

        final = _poll_status(client, job_id)

        assert final.get("status") == "done"
        assert final.get("doc_type") == "liquidacao"
        assert final.get("source") == "ai"
        assert final.get("data") is not None
        assert final["data"].get("numero_processo") == "0000000-00.0000.0.00.0000"
        assert isinstance(final["data"].get("verbas_deferidas"), list)
        assert len(final["data"]["verbas_deferidas"]) >= 1

        _cleanup_job(client, job_id)


def test_upload_worker_exception_surfaces_error_on_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exceção no thread do worker → `/status` terminal com `error` e mensagem estável (sem Gemini)."""

    def _boom(
        user_id: str,
        file_bytes: bytes,
        job_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise RuntimeError("falha fake e2e")

    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", _boom)

    with TestClient(app_upload_only) as client:
        job_id = _post_minimal_upload_queued(
            client,
            user_id="user-upload-worker-err-e2e",
            filename="worker-fail.pdf",
        )

        final = _poll_status(client, job_id)

        assert final.get("status") == "error"
        msg = final.get("msg", "")
        assert isinstance(msg, str)
        assert "Exceção não tratada" in msg
        assert "falha fake e2e" in msg

        _cleanup_job(client, job_id)


def test_upload_worker_exception_websocket_terminal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falha no worker → mensagem WebSocket terminal com `status` `error` e `msg` estável."""

    def _boom_ws(
        user_id: str,
        file_bytes: bytes,
        job_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise RuntimeError("falha fake ws e2e")

    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", _boom_ws)

    with TestClient(app_upload_only) as client:
        job_id = _post_minimal_upload_queued(
            client,
            user_id="user-upload-ws-err-e2e",
            filename="ws-worker-fail.pdf",
        )

        with client.websocket_connect(f"/ws/{job_id}") as websocket:
            terminal = _read_ws_terminal_skipping_noise(websocket)

        assert extractor_mod._ws_payload_is_terminal(terminal)
        assert terminal.get("status") == "error"
        msg = terminal.get("msg", "")
        assert isinstance(msg, str)
        assert "Exceção não tratada" in msg
        assert "falha fake ws e2e" in msg

        _cleanup_job(client, job_id)


def test_upload_worker_timeout_surfaces_error_on_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout do runner -> `/status` terminal com `error` e mensagem estavel (sem esperar 300s)."""

    def _slow_processor(
        user_id: str,
        file_bytes: bytes,
        job_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        assert len(file_bytes) >= 10
        time.sleep(1.25)
        return _fake_process_lawsuit_pdf(user_id, file_bytes, job_id=job_id, **kwargs)

    monkeypatch.setattr(extractor_mod, "JOB_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", _slow_processor)

    with TestClient(app_upload_only) as client:
        job_id = _post_minimal_upload_queued(
            client,
            user_id="user-upload-timeout-e2e",
            filename="timeout.pdf",
        )

        final = _poll_status(client, job_id, timeout_s=5.0)

        assert final.get("status") == "error"
        msg = final.get("msg", "")
        assert isinstance(msg, str)
        assert "Timeout: processamento excedeu" in msg

        _cleanup_job(client, job_id)


def test_upload_worker_timeout_websocket_terminal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout do runner -> `/ws/{job_id}` terminal com `error` e mensagem estavel."""

    def _slow_processor_ws(
        user_id: str,
        file_bytes: bytes,
        job_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        assert len(file_bytes) >= 10
        time.sleep(1.25)
        return _fake_process_lawsuit_pdf(user_id, file_bytes, job_id=job_id, **kwargs)

    monkeypatch.setattr(extractor_mod, "JOB_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", _slow_processor_ws)

    with TestClient(app_upload_only) as client:
        job_id = _post_minimal_upload_queued(
            client,
            user_id="user-upload-ws-timeout-e2e",
            filename="ws-timeout.pdf",
        )

        with client.websocket_connect(f"/ws/{job_id}") as websocket:
            terminal = _read_ws_terminal_skipping_noise(websocket, timeout_s=5.0)

        assert extractor_mod._ws_payload_is_terminal(terminal)
        assert terminal.get("status") == "error"
        msg = terminal.get("msg", "")
        assert isinstance(msg, str)
        assert "Timeout: processamento excedeu" in msg

        _cleanup_job(client, job_id)


def test_upload_minimal_pdf_websocket_terminal_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lê o WebSocket até mensagem terminal; contrato espelha o payload final do job (não há `type: \"result\"`)."""
    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", _fake_process_lawsuit_pdf)

    with TestClient(app_upload_only) as client:
        job_id = _post_minimal_upload_queued(
            client,
            user_id="user-upload-ws-e2e",
            filename="ws-minimal.pdf",
        )

        with client.websocket_connect(f"/ws/{job_id}") as websocket:
            terminal = _read_ws_terminal_skipping_noise(websocket)

        assert terminal.get("status") == "done"
        assert terminal.get("doc_type") == "liquidacao"
        assert terminal.get("source") == "ai"
        assert terminal.get("data", {}).get("numero_processo") == "0000000-00.0000.0.00.0000"

        _cleanup_job(client, job_id)


def test_upload_minimal_pdf_websocket_partial_then_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Garante pelo menos um `partial_update` antes do payload terminal.
    Sincronização: worker bloqueia até o cliente registar a fila WS (Event).
    """
    ws_listener_ready = threading.Event()
    partial_numero = "1111111-11.1111.1.11.1111"

    def fake_with_partial(
        user_id: str,
        file_bytes: bytes,
        job_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        assert len(file_bytes) >= 10
        assert job_id, "job_id deve ser propagado ao processor para push_ws_partial"
        assert ws_listener_ready.wait(timeout=30.0), "timeout aguardando WS conectar"
        extractor_mod.push_ws_partial(
            job_id,
            {"numero_processo": partial_numero},
            "partial-e2e",
        )
        return _fake_process_lawsuit_pdf(user_id, file_bytes, job_id=job_id, **kwargs)

    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", fake_with_partial)

    with TestClient(app_upload_only) as client:
        job_id = _post_minimal_upload_queued(
            client,
            user_id="user-upload-ws-partial-e2e",
            filename="ws-partial.pdf",
        )

        saw_partial = False
        terminal: dict[str, Any] | None = None
        with client.websocket_connect(f"/ws/{job_id}") as websocket:
            ws_listener_ready.set()
            deadline = time.monotonic() + 30.0
            while time.monotonic() < deadline:
                msg = _recv_ws_json(websocket)
                if msg.get("status") == "processing":
                    continue
                if msg.get("type") == "partial_update":
                    assert msg.get("payload", {}).get("numero_processo") == partial_numero
                    assert msg.get("message") == "partial-e2e"
                    saw_partial = True
                    continue
                assert extractor_mod._ws_payload_is_terminal(msg), (
                    f"mensagem WS inesperada: {list(msg.keys())}"
                )
                terminal = msg
                break
            assert saw_partial, "esperado ao menos um partial_update antes do terminal"
            assert terminal is not None, "timeout sem mensagem terminal no WebSocket"

        assert terminal.get("status") == "done"
        assert terminal.get("doc_type") == "liquidacao"
        assert terminal.get("source") == "ai"
        assert terminal.get("data", {}).get("numero_processo") == "0000000-00.0000.0.00.0000"

        _cleanup_job(client, job_id)


def test_upload_peticao_inicial_dois_arquivos_retorna_400_sem_processador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Rejeição estável alinhada a `_should_run_process_lawsuit_pdf_upload`:
    petição inicial exige exatamente um arquivo (ver `test_peticao_multiplo_rejeita`).
    """
    pdf_mock = MagicMock()
    dossie_mock = MagicMock()
    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", pdf_mock)
    monkeypatch.setattr(extractor_mod, "process_lawsuit_dossie", dossie_mock)

    with TestClient(app_upload_only) as client:
        files = [
            ("files", ("primeiro.pdf", _MIN_PDF, "application/pdf")),
            ("files", ("segundo.pdf", _MIN_PDF, "application/pdf")),
        ]
        data = {
            "user_id": "user-upload-api-400",
            "cache_context": "peticao_inicial",
        }
        r = client.post(
            "/upload",
            data=data,
            files=files,
            headers={"x-user-id": "user-upload-api-400"},
        )

    assert r.status_code == 400
    payload = r.json()
    detail = payload.get("detail", "")
    assert isinstance(detail, str)
    assert "exatamente um" in detail.lower()
    pdf_mock.assert_not_called()
    dossie_mock.assert_not_called()


def test_upload_pdf_menor_que_10_bytes_retorna_400_sem_processador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arquivo abaixo do minimo do upload -> 400 antes de enfileirar worker."""
    pdf_mock = MagicMock()
    dossie_mock = MagicMock()
    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", pdf_mock)
    monkeypatch.setattr(extractor_mod, "process_lawsuit_dossie", dossie_mock)

    with TestClient(app_upload_only) as client:
        r = client.post(
            "/upload",
            data={"user_id": "user-upload-small-file-e2e"},
            files=[("files", ("vazio.pdf", b"%PDF", "application/pdf"))],
            headers={"x-user-id": "user-upload-small-file-e2e"},
        )

    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert isinstance(detail, str)
    assert "vazio ou invalido" in detail.lower() or "vazio ou inválido" in detail.lower()
    pdf_mock.assert_not_called()
    dossie_mock.assert_not_called()


def test_upload_extensao_nao_permitida_retorna_400_sem_processador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extensao fora da whitelist -> 400 antes de enfileirar worker."""
    pdf_mock = MagicMock()
    dossie_mock = MagicMock()
    monkeypatch.setattr(extractor_mod, "process_lawsuit_pdf", pdf_mock)
    monkeypatch.setattr(extractor_mod, "process_lawsuit_dossie", dossie_mock)

    with TestClient(app_upload_only) as client:
        r = client.post(
            "/upload",
            data={"user_id": "user-upload-extensao-e2e"},
            files=[("files", ("malicioso.exe", b"0123456789abc", "application/octet-stream"))],
            headers={"x-user-id": "user-upload-extensao-e2e"},
        )

    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert isinstance(detail, str)
    assert "tipo nao aceito" in detail.lower() or "tipo não aceito" in detail.lower()
    assert ".exe" in detail.lower()
    pdf_mock.assert_not_called()
    dossie_mock.assert_not_called()

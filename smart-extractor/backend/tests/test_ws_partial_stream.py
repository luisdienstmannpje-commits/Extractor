"""WebSocket incremental: partial_update e detecção de mensagem terminal."""

from api.routers.extractor import _ws_payload_is_terminal, push_ws_partial


def test_ws_payload_partial_never_terminal() -> None:
    assert not _ws_payload_is_terminal({"type": "partial_update", "payload": {"numero_processo": "x"}})


def test_ws_payload_terminal_statuses() -> None:
    assert _ws_payload_is_terminal({"status": "done"})
    assert _ws_payload_is_terminal({"status": "error"})
    assert _ws_payload_is_terminal({"status": "timeout"})
    assert _ws_payload_is_terminal({"status": "sucesso"})
    assert _ws_payload_is_terminal({"status": "erro"})


def test_push_ws_partial_no_queue_no_crash() -> None:
    """Sem cliente WS: enfileirar não levanta exceção para o chamador."""
    push_ws_partial("job-inexistente-000", {"numero_processo": "1"}, "msg")

import json
from http import HTTPStatus
from io import BytesIO

from ci_hunter.webhook_httpd import handle_request_bytes


def test_handle_request_bytes_returns_enqueued():
    payload = json.dumps({"ok": True}).encode("utf-8")
    status, body = handle_request_bytes(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body_bytes=payload,
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.OK
    assert body == b"enqueued"


def test_handle_request_bytes_rejects_missing_event():
    status, body = handle_request_bytes(
        method="POST",
        headers={},
        body_bytes=b"{}",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert body == b"missing event"


def test_handle_request_bytes_rejects_invalid_utf8():
    status, body = handle_request_bytes(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body_bytes=b"\xff\xfe",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert body == b"invalid utf-8"

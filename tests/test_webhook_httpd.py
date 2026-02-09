import hashlib
import hmac
import json
from http import HTTPStatus

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


def test_handle_request_bytes_rejects_payload_too_large():
    status, body = handle_request_bytes(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body_bytes=b"{}",
        enqueue_handler=lambda _event, _payload: True,
        max_body_bytes=1,
    )

    assert status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert body == b"payload too large"


def test_handle_request_bytes_rejects_invalid_signature():
    status, body = handle_request_bytes(
        method="POST",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=bad",
        },
        body_bytes=b"{}",
        enqueue_handler=lambda _event, _payload: True,
        shared_secret="secret",
    )

    assert status == HTTPStatus.UNAUTHORIZED
    assert body == b"invalid signature"


def test_handle_request_bytes_accepts_valid_signature():
    body_bytes = b"{}"
    signature = hmac.new(b"secret", body_bytes, hashlib.sha256).hexdigest()
    status, body = handle_request_bytes(
        method="POST",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": f"sha256={signature}",
        },
        body_bytes=body_bytes,
        enqueue_handler=lambda _event, _payload: True,
        shared_secret="secret",
    )

    assert status == HTTPStatus.OK
    assert body == b"enqueued"


def test_handle_request_bytes_rejects_missing_auth_token():
    status, body = handle_request_bytes(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body_bytes=b"{}",
        enqueue_handler=lambda _event, _payload: True,
        auth_token="token123",
    )

    assert status == HTTPStatus.UNAUTHORIZED
    assert body == b"unauthorized"


def test_handle_request_bytes_accepts_valid_auth_token():
    status, body = handle_request_bytes(
        method="POST",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-CI-HUNTER-TOKEN": "token123",
        },
        body_bytes=b"{}",
        enqueue_handler=lambda _event, _payload: True,
        auth_token="token123",
    )

    assert status == HTTPStatus.OK
    assert body == b"enqueued"


def test_handle_request_bytes_uses_constant_time_compare_for_auth_token(monkeypatch):
    import ci_hunter.webhook_httpd as webhook_httpd

    captured: dict[str, tuple[str | None, str]] = {}

    def fake_compare_digest(provided: str | None, expected: str) -> bool:
        captured["args"] = (provided, expected)
        return True

    monkeypatch.setattr(webhook_httpd.hmac, "compare_digest", fake_compare_digest)

    status, body = handle_request_bytes(
        method="POST",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-CI-HUNTER-TOKEN": "token123",
        },
        body_bytes=b"{}",
        enqueue_handler=lambda _event, _payload: True,
        auth_token="token123",
    )

    assert status == HTTPStatus.OK
    assert body == b"enqueued"
    assert captured["args"] == ("token123", "token123")

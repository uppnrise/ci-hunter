import json
from http import HTTPStatus

from ci_hunter.webhook_server import handle_webhook_request


def test_handle_webhook_request_enqueues_job():
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/repo"},
        "pull_request": {
            "number": 7,
            "head": {"sha": "abc123", "ref": "feature-x"},
        },
    }
    status, body = handle_webhook_request(
        event="pull_request",
        payload_text=json.dumps(payload),
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.OK
    assert body == "enqueued"


def test_handle_webhook_request_returns_ignored():
    status, body = handle_webhook_request(
        event="push",
        payload_text=json.dumps({"ref": "refs/heads/main"}),
        enqueue_handler=lambda _event, _payload: False,
    )

    assert status == HTTPStatus.ACCEPTED
    assert body == "ignored"


def test_handle_webhook_request_rejects_bad_json():
    status, body = handle_webhook_request(
        event="pull_request",
        payload_text="not-json",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert body == "invalid json"

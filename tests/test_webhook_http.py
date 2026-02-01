from http import HTTPStatus

from ci_hunter.webhook_http import handle_webhook_http


def test_handle_webhook_http_requires_event_header():
    status, body = handle_webhook_http(
        headers={},
        body_text="{}",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert body == "missing event"


def test_handle_webhook_http_handles_invalid_json():
    status, body = handle_webhook_http(
        headers={"X-GitHub-Event": "pull_request"},
        body_text="not-json",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert body == "invalid json"


def test_handle_webhook_http_enqueues_when_allowed():
    status, body = handle_webhook_http(
        headers={"X-GitHub-Event": "pull_request"},
        body_text="{}",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.OK
    assert body == "enqueued"


def test_handle_webhook_http_accepts_case_insensitive_header():
    status, body = handle_webhook_http(
        headers={"x-github-event": "pull_request"},
        body_text="{}",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.OK
    assert body == "enqueued"

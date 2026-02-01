import json
from http import HTTPStatus

from ci_hunter.webhook_http_server import handle_http_request


def test_handle_http_request_accepts_post_with_event_header():
    status, body = handle_http_request(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body_text=json.dumps({}),
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.OK
    assert body == "enqueued"


def test_handle_http_request_rejects_non_post():
    status, body = handle_http_request(
        method="GET",
        headers={"X-GitHub-Event": "pull_request"},
        body_text="{}",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.METHOD_NOT_ALLOWED
    assert body == "method not allowed"

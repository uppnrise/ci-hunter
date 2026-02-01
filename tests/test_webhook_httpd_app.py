from http import HTTPStatus

from ci_hunter.webhook_httpd_app import WebhookRequestHandler


def test_webhook_request_handler_writes_response():
    captured = {}

    def responder(status: HTTPStatus, body: bytes) -> None:
        captured["status"] = status
        captured["body"] = body

    handler = WebhookRequestHandler(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body=b"{}",
        enqueue_handler=lambda _event, _payload: True,
        respond=responder,
    )

    handler.handle()

    assert captured["status"] == HTTPStatus.OK
    assert captured["body"] == b"enqueued"

from http import HTTPStatus

from ci_hunter.webhook_httpd_app_factory import build_app_handler


def test_build_app_handler_returns_responder_callable():
    captured = {}

    def enqueue_handler(_event: str, _payload: dict) -> bool:
        return True

    handler = build_app_handler(enqueue_handler=enqueue_handler)

    handler(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body=b"{}",
        respond=lambda status, body: captured.update({"status": status, "body": body}),
    )

    assert captured["status"] == HTTPStatus.OK
    assert captured["body"] == b"enqueued"

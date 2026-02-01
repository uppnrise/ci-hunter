from http import HTTPStatus

from ci_hunter.webhook_httpd_cli import handle_incoming


def test_handle_incoming_returns_status_and_body():
    status, body = handle_incoming(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body=b"{}",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.OK
    assert body == b"enqueued"


def test_handle_incoming_returns_error_when_no_response(monkeypatch):
    import ci_hunter.webhook_httpd_cli as webhook_httpd_cli

    def fake_builder(*, enqueue_handler):
        def handler(*, method, headers, body, respond):
            return None

        return handler

    monkeypatch.setattr(webhook_httpd_cli, "build_app_handler", fake_builder)

    status, body = webhook_httpd_cli.handle_incoming(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body=b"{}",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert b"no response" in body.lower()

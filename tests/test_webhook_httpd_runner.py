from http import HTTPStatus

from ci_hunter.webhook_httpd_runner import handle_request


def test_handle_request_reads_body_and_headers():
    captured = {}

    def responder(status: HTTPStatus, body: bytes) -> None:
        captured["status"] = status
        captured["body"] = body

    handle_request(
        method="POST",
        headers={"X-GitHub-Event": "pull_request"},
        body=b"{}",
        enqueue_handler=lambda _event, _payload: True,
        respond=responder,
    )

    assert captured["status"] == HTTPStatus.OK
    assert captured["body"] == b"enqueued"

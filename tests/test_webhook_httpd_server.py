from http import HTTPStatus

from ci_hunter.webhook_httpd_server import handle_httpd_request


def test_handle_httpd_request_rejects_non_post():
    status, body = handle_httpd_request(
        method="GET",
        headers={},
        body_bytes=b"",
        enqueue_handler=lambda _event, _payload: True,
    )

    assert status == HTTPStatus.METHOD_NOT_ALLOWED
    assert body == b"method not allowed"

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Mapping, Tuple

from ci_hunter.webhook_httpd_app_factory import build_app_handler


def handle_incoming(
    *,
    method: str,
    headers: Mapping[str, str],
    body: bytes,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
    max_body_bytes: int = 1024 * 1024,
    shared_secret: str | None = None,
    auth_token: str | None = None,
) -> Tuple[HTTPStatus, bytes]:
    result: dict[str, object] = {}

    def respond(status: HTTPStatus, payload: bytes) -> None:
        result["status"] = status
        result["body"] = payload

    handler = build_app_handler(
        enqueue_handler=enqueue_handler,
        max_body_bytes=max_body_bytes,
        shared_secret=shared_secret,
        auth_token=auth_token,
    )
    handler(method=method, headers=headers, body=body, respond=respond)

    if "status" not in result or "body" not in result:
        return HTTPStatus.INTERNAL_SERVER_ERROR, b"no response set by handler"
    return result["status"], result["body"]

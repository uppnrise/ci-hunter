from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Mapping, Tuple

from ci_hunter.webhook_httpd import handle_request_bytes


def handle_httpd_request(
    *,
    method: str,
    headers: Mapping[str, str],
    body_bytes: bytes,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
) -> Tuple[HTTPStatus, bytes]:
    if method.upper() != "POST":
        return HTTPStatus.METHOD_NOT_ALLOWED, b"method not allowed"
    return handle_request_bytes(
        method=method,
        headers=headers,
        body_bytes=body_bytes,
        enqueue_handler=enqueue_handler,
    )

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Mapping, Tuple

from ci_hunter.webhook_http import handle_webhook_http


def handle_request_bytes(
    *,
    method: str,
    headers: Mapping[str, str],
    body_bytes: bytes,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
) -> Tuple[HTTPStatus, bytes]:
    try:
        body_text = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return HTTPStatus.BAD_REQUEST, b"invalid utf-8"
    status, body = handle_webhook_http(
        headers=headers,
        body_text=body_text,
        enqueue_handler=enqueue_handler,
    )
    return status, body.encode("utf-8")

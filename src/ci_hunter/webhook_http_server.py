from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Mapping, Tuple

from ci_hunter.webhook_http import handle_webhook_http


def handle_http_request(
    *,
    method: str,
    headers: Mapping[str, str],
    body_text: str,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
) -> Tuple[HTTPStatus, str]:
    if method.upper() != "POST":
        return HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed"
    return handle_webhook_http(
        headers=headers,
        body_text=body_text,
        enqueue_handler=enqueue_handler,
    )

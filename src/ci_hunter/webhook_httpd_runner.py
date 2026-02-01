from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Mapping

from ci_hunter.webhook_httpd_app import WebhookRequestHandler


def handle_request(
    *,
    method: str,
    headers: Mapping[str, str],
    body: bytes,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
    respond: Callable[[HTTPStatus, bytes], None],
) -> None:
    handler = WebhookRequestHandler(
        method=method,
        headers=headers,
        body=body,
        enqueue_handler=enqueue_handler,
        respond=respond,
    )
    handler.handle()

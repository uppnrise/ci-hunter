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
    max_body_bytes: int = 1024 * 1024,
    shared_secret: str | None = None,
    auth_token: str | None = None,
) -> None:
    handler = WebhookRequestHandler(
        method=method,
        headers=headers,
        body=body,
        enqueue_handler=enqueue_handler,
        respond=respond,
        max_body_bytes=max_body_bytes,
        shared_secret=shared_secret,
        auth_token=auth_token,
    )
    handler.handle()

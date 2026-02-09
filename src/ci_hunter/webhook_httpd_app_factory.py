from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Mapping

from ci_hunter.webhook_httpd_runner import handle_request


def build_app_handler(
    *,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
    max_body_bytes: int = 1024 * 1024,
    shared_secret: str | None = None,
    auth_token: str | None = None,
) -> Callable[..., None]:
    def handler(
        *,
        method: str,
        headers: Mapping[str, str],
        body: bytes,
        respond: Callable[[HTTPStatus, bytes], None],
    ) -> None:
        handle_request(
            method=method,
            headers=headers,
            body=body,
            enqueue_handler=enqueue_handler,
            respond=respond,
            max_body_bytes=max_body_bytes,
            shared_secret=shared_secret,
            auth_token=auth_token,
        )

    return handler

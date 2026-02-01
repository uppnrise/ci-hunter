from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Mapping

from ci_hunter.webhook_httpd_runner import handle_request


def build_app_handler(
    *,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
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
        )

    return handler

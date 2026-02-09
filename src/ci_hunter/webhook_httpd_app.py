from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Callable, Mapping

from ci_hunter.webhook_httpd_server import handle_httpd_request


@dataclass(frozen=True)
class WebhookRequestHandler:
    method: str
    headers: Mapping[str, str]
    body: bytes
    enqueue_handler: Callable[[str, dict[str, Any]], bool]
    respond: Callable[[HTTPStatus, bytes], None]
    max_body_bytes: int = 1024 * 1024
    shared_secret: str | None = None
    auth_token: str | None = None

    def handle(self) -> None:
        status, body = handle_httpd_request(
            method=self.method,
            headers=self.headers,
            body_bytes=self.body,
            enqueue_handler=self.enqueue_handler,
            max_body_bytes=self.max_body_bytes,
            shared_secret=self.shared_secret,
            auth_token=self.auth_token,
        )
        self.respond(status, body)

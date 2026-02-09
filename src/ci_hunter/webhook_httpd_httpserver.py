from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

from ci_hunter.webhook_httpd_cli import handle_incoming


def serve_http(
    *,
    host: str,
    port: int,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
    log_fn: Callable[[str], None],
    max_body_bytes: int = 1024 * 1024,
    shared_secret: str | None = None,
    auth_token: str | None = None,
) -> HTTPServer:
    class WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self._handle_with_method("POST")

        def do_GET(self) -> None:  # noqa: N802
            self._handle_with_method("GET")

        def log_message(self, format: str, *args: object) -> None:
            log_fn(format % args)

        def _handle_with_method(self, method: str) -> None:
            content_length = _parse_content_length(self.headers.get("Content-Length"))
            if content_length > max_body_bytes:
                payload = b"payload too large"
                self.send_response(413)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            body = self.rfile.read(content_length)
            status, payload = handle_incoming(
                method=method,
                headers=self.headers,
                body=body,
                enqueue_handler=enqueue_handler,
                max_body_bytes=max_body_bytes,
                shared_secret=shared_secret,
                auth_token=auth_token,
            )
            self.send_response(status.value)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return HTTPServer((host, port), WebhookHandler)


def _parse_content_length(value: str | None) -> int:
    if value is None:
        return 0
    try:
        length = int(value)
    except ValueError:
        return 0
    return max(length, 0)

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from http import HTTPStatus
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
    metrics = _RequestMetrics()

    class WebhookHTTPServer(HTTPServer):
        def server_close(self) -> None:
            log_fn(metrics.summary_line())
            super().server_close()

    class WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self._handle_with_method("POST")

        def do_GET(self) -> None:  # noqa: N802
            self._handle_with_method("GET")

        def log_message(self, format: str, *args: object) -> None:
            log_fn(format % args)

        def _handle_with_method(self, method: str) -> None:
            if method == "POST":
                transfer_encoding = self.headers.get("Transfer-Encoding")
                if _has_unsupported_transfer_encoding(transfer_encoding):
                    status = HTTPStatus.BAD_REQUEST
                    payload = b"unsupported transfer encoding"
                    log_fn(metrics.record_line(method=method, status=status, payload=payload))
                    self.send_response(status.value)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                content_length = _parse_content_length(self.headers.get("Content-Length"))
                if content_length is None:
                    status = HTTPStatus.LENGTH_REQUIRED
                    payload = b"missing content-length"
                    log_fn(metrics.record_line(method=method, status=status, payload=payload))
                    self.send_response(status.value)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                if content_length > max_body_bytes:
                    status = HTTPStatus.REQUEST_ENTITY_TOO_LARGE
                    payload = b"payload too large"
                    log_fn(metrics.record_line(method=method, status=status, payload=payload))
                    self.send_response(status.value)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                body = self.rfile.read(content_length) if content_length else b""
            else:
                body = b""
            status, payload = handle_incoming(
                method=method,
                headers=self.headers,
                body=body,
                enqueue_handler=enqueue_handler,
                max_body_bytes=max_body_bytes,
                shared_secret=shared_secret,
                auth_token=auth_token,
            )
            log_fn(metrics.record_line(method=method, status=status, payload=payload))
            self.send_response(status.value)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return WebhookHTTPServer((host, port), WebhookHandler)


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        length = int(value)
    except ValueError:
        return None
    if length < 0:
        return None
    return length


def _has_unsupported_transfer_encoding(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized not in {"", "identity"}


@dataclass
class _RequestMetrics:
    total_requests: int = 0
    accepted_requests: int = 0
    rejected_requests: int = 0
    reject_reason_counts: Counter[str] = field(default_factory=Counter)

    def record_line(self, *, method: str, status: HTTPStatus, payload: bytes) -> str:
        self.total_requests += 1
        status_code = status.value
        outcome = "accepted" if 200 <= status_code < 300 else "rejected"
        reason = "none"
        reject_count = 0
        if outcome == "accepted":
            self.accepted_requests += 1
        else:
            self.rejected_requests += 1
            reason = _normalize_reason(payload)
            self.reject_reason_counts[reason] += 1
            reject_count = self.reject_reason_counts[reason]
        return (
            "webhook_request "
            f"method={method} "
            f"status={status_code} "
            f"outcome={outcome} "
            f"reason={reason} "
            f"reject_count={reject_count} "
            f"total_count={self.total_requests}"
        )

    def summary_line(self) -> str:
        reject_parts = ",".join(
            f"{reason}:{count}"
            for reason, count in sorted(self.reject_reason_counts.items())
        )
        return (
            "webhook_metrics "
            f"total={self.total_requests} "
            f"accepted={self.accepted_requests} "
            f"rejected={self.rejected_requests} "
            f"reject_reasons={reject_parts or 'none'}"
        )


def _normalize_reason(payload: bytes) -> str:
    raw = payload.decode("utf-8", errors="ignore").strip().lower()
    if not raw:
        return "unknown"
    return "_".join(raw.split())

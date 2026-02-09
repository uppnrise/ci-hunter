from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from typing import TextIO

from ci_hunter.github.webhook_queue import enqueue_webhook_event
from ci_hunter.job_queue_file import append_job
from ci_hunter.queue import InMemoryJobQueue
from ci_hunter.webhook_httpd_httpserver import serve_http

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
ENV_HOST = "CI_HUNTER_WEBHOOK_HOST"
ENV_PORT = "CI_HUNTER_WEBHOOK_PORT"
ENV_SECRET = "CI_HUNTER_WEBHOOK_SECRET"
ENV_AUTH_TOKEN = "CI_HUNTER_WEBHOOK_AUTH_TOKEN"
ENV_MAX_BODY_BYTES = "CI_HUNTER_WEBHOOK_MAX_BODY_BYTES"
DEFAULT_MAX_BODY_BYTES = 1024 * 1024


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-hunter-webhook-listener")
    parser.add_argument("--queue-file", required=True)
    parser.add_argument("--host", default=os.environ.get(ENV_HOST, DEFAULT_HOST))
    parser.add_argument("--port", type=_port_value, default=_default_port())
    parser.add_argument("--once", action="store_true")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    server_factory: Callable[..., object] = serve_http,
    out: TextIO | None = None,
) -> int:
    args = _build_parser().parse_args(argv)
    out = out or os.sys.stdout

    def enqueue_handler(event: str, payload: dict[str, object]) -> bool:
        queue = InMemoryJobQueue()
        handled = enqueue_webhook_event(
            event,
            payload,
            queue=queue,
        )
        if not handled:
            return False
        job = queue.dequeue()
        if job is None:
            return False
        append_job(args.queue_file, job)
        return True

    server = server_factory(
        host=args.host,
        port=args.port,
        enqueue_handler=enqueue_handler,
        log_fn=lambda message: out.write(f"{message}\n"),
        shared_secret=os.environ.get(ENV_SECRET),
        auth_token=os.environ.get(ENV_AUTH_TOKEN),
        max_body_bytes=_default_max_body_bytes(),
    )
    host, port = server.server_address
    out.write(f"listening on {host}:{port}\n")
    try:
        if args.once:
            server.handle_request()
        else:
            server.serve_forever()
    except KeyboardInterrupt:
        out.write("shutting down\n")
    finally:
        server.server_close()
    return 0


def _default_port() -> int:
    raw_port = os.environ.get(ENV_PORT)
    if raw_port is None:
        return DEFAULT_PORT
    try:
        port = int(raw_port)
    except ValueError:
        return DEFAULT_PORT
    if _is_valid_port(port):
        return port
    return DEFAULT_PORT


def _default_max_body_bytes() -> int:
    raw_value = os.environ.get(ENV_MAX_BODY_BYTES)
    if raw_value is None:
        return DEFAULT_MAX_BODY_BYTES
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_MAX_BODY_BYTES
    if value <= 0:
        return DEFAULT_MAX_BODY_BYTES
    return value


def _port_value(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not _is_valid_port(port):
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _is_valid_port(port: int) -> bool:
    return 1 <= port <= 65535

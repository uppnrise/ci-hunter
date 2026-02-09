import io
import json
import os
from pathlib import Path

import pytest

from ci_hunter.webhook_listener_cmd import main


def test_webhook_listener_once_processes_single_request(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    captured = {}

    class FakeServer:
        def __init__(self, enqueue_handler):
            self.server_address = ("127.0.0.1", 9000)
            self._enqueue_handler = enqueue_handler
            self.handle_request_calls = 0
            self.serve_forever_calls = 0
            self.closed = False

        def handle_request(self):
            self.handle_request_calls += 1
            handled = self._enqueue_handler(
                "pull_request",
                {
                    "action": "opened",
                    "repository": {"full_name": "acme/repo"},
                    "pull_request": {
                        "number": 7,
                        "head": {"sha": "abc123", "ref": "feature-x"},
                    },
                },
            )
            captured["handled"] = handled

        def serve_forever(self):
            self.serve_forever_calls += 1

        def server_close(self):
            self.closed = True

    def factory(*, host, port, enqueue_handler, log_fn):
        captured["host"] = host
        captured["port"] = port
        captured["log_fn"] = log_fn
        server = FakeServer(enqueue_handler)
        captured["server"] = server
        return server

    output = io.StringIO()
    exit_code = main(
        [
            "--queue-file",
            str(queue_path),
            "--once",
            "--host",
            "127.0.0.1",
            "--port",
            "8081",
        ],
        server_factory=factory,
        out=output,
    )

    assert exit_code == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8081
    assert captured["handled"] is True
    server = captured["server"]
    assert server.handle_request_calls == 1
    assert server.serve_forever_calls == 0
    assert server.closed is True
    assert "listening on 127.0.0.1:9000" in output.getvalue()
    line = queue_path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["repo"] == "acme/repo"
    assert payload["pr_number"] == 7


def test_webhook_listener_serve_forever_and_graceful_shutdown(tmp_path):
    queue_path = tmp_path / "queue.jsonl"

    class FakeServer:
        server_address = ("127.0.0.1", 9001)

        def __init__(self):
            self.handle_request_calls = 0
            self.serve_forever_calls = 0
            self.closed = False

        def handle_request(self):
            self.handle_request_calls += 1

        def serve_forever(self):
            self.serve_forever_calls += 1
            raise KeyboardInterrupt

        def server_close(self):
            self.closed = True

    server = FakeServer()

    def factory(*, host, port, enqueue_handler, log_fn):
        return server

    output = io.StringIO()
    exit_code = main(
        [
            "--queue-file",
            str(queue_path),
            "--host",
            "127.0.0.1",
            "--port",
            "8082",
        ],
        server_factory=factory,
        out=output,
    )

    assert exit_code == 0
    assert server.handle_request_calls == 0
    assert server.serve_forever_calls == 1
    assert server.closed is True
    assert "shutting down" in output.getvalue()


def test_webhook_listener_uses_env_defaults(tmp_path, monkeypatch):
    queue_path = tmp_path / "queue.jsonl"
    monkeypatch.setenv("CI_HUNTER_WEBHOOK_HOST", "0.0.0.0")
    monkeypatch.setenv("CI_HUNTER_WEBHOOK_PORT", "9999")
    captured = {}

    class FakeServer:
        server_address = ("0.0.0.0", 9999)

        def handle_request(self):
            return None

        def serve_forever(self):
            return None

        def server_close(self):
            return None

    def factory(*, host, port, enqueue_handler, log_fn):
        captured["host"] = host
        captured["port"] = port
        return FakeServer()

    exit_code = main(
        ["--queue-file", str(queue_path), "--once"],
        server_factory=factory,
        out=io.StringIO(),
    )

    assert exit_code == 0
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9999


def test_webhook_listener_rejects_out_of_range_port(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    with pytest.raises(SystemExit):
        main(
            [
                "--queue-file",
                str(queue_path),
                "--once",
                "--port",
                "70000",
            ],
            server_factory=lambda **_kwargs: None,
            out=io.StringIO(),
        )


def test_webhook_listener_env_port_out_of_range_falls_back_default(tmp_path, monkeypatch):
    queue_path = tmp_path / "queue.jsonl"
    monkeypatch.setenv("CI_HUNTER_WEBHOOK_PORT", "70000")
    captured = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8000)

        def handle_request(self):
            return None

        def serve_forever(self):
            return None

        def server_close(self):
            return None

    def factory(*, host, port, enqueue_handler, log_fn):
        captured["host"] = host
        captured["port"] = port
        return FakeServer()

    exit_code = main(
        ["--queue-file", str(queue_path), "--once"],
        server_factory=factory,
        out=io.StringIO(),
    )

    assert exit_code == 0
    assert captured["port"] == 8000

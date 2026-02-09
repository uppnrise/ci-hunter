import http.client
import json
import socket
import threading

from ci_hunter.webhook_httpd_httpserver import serve_http


def _send_request(server, method, body, headers):
    port = server.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port)
    connection.request(method, "/", body=body, headers=headers)
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    return response.status, payload


def _send_raw_request(server, request_bytes):
    host, port = server.server_address
    with socket.create_connection((host, port), timeout=2) as sock:
        sock.sendall(request_bytes)
        sock.shutdown(socket.SHUT_WR)
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
    header_bytes, _, body = response.partition(b"\r\n\r\n")
    status_line = header_bytes.split(b"\r\n", maxsplit=1)[0]
    status = int(status_line.split()[1])
    return status, body


def test_httpserver_handles_post_and_enqueues():
    captured = {}

    def enqueue_handler(event, payload):
        captured["event"] = event
        captured["payload"] = payload
        return True

    server = serve_http(host="127.0.0.1", port=0, enqueue_handler=enqueue_handler, log_fn=lambda _msg: None)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    body = json.dumps({"ok": True})
    status, payload = _send_request(
        server,
        "POST",
        body=body,
        headers={"X-GitHub-Event": "pull_request"},
    )

    thread.join(timeout=1)
    server.server_close()

    assert status == 200
    assert payload == b"enqueued"
    assert captured["event"] == "pull_request"
    assert captured["payload"]["ok"] is True


def test_httpserver_rejects_get():
    server = serve_http(host="127.0.0.1", port=0, enqueue_handler=lambda _e, _p: True, log_fn=lambda _msg: None)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    status, payload = _send_request(server, "GET", body="", headers={})

    thread.join(timeout=1)
    server.server_close()

    assert status == 405
    assert payload == b"method not allowed"


def test_httpserver_requires_event_header():
    server = serve_http(host="127.0.0.1", port=0, enqueue_handler=lambda _e, _p: True, log_fn=lambda _msg: None)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    status, payload = _send_request(server, "POST", body="{}", headers={})

    thread.join(timeout=1)
    server.server_close()

    assert status == 400
    assert payload == b"missing event"


def test_httpserver_rejects_oversize_before_dispatch(monkeypatch):
    import ci_hunter.webhook_httpd_httpserver as webhook_httpd_httpserver

    called = {"count": 0}

    def fail_handle_incoming(**_kwargs):
        called["count"] += 1
        raise AssertionError("handle_incoming must not be called for oversized requests")

    monkeypatch.setattr(webhook_httpd_httpserver, "handle_incoming", fail_handle_incoming)
    server = serve_http(
        host="127.0.0.1",
        port=0,
        enqueue_handler=lambda _e, _p: True,
        log_fn=lambda _msg: None,
        max_body_bytes=1,
    )
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    status, payload = _send_request(
        server,
        "POST",
        body="{}",
        headers={"X-GitHub-Event": "pull_request"},
    )

    thread.join(timeout=1)
    server.server_close()

    assert status == 413
    assert payload == b"payload too large"
    assert called["count"] == 0


def test_httpserver_logs_structured_request_outcomes():
    logs: list[str] = []

    server = serve_http(
        host="127.0.0.1",
        port=0,
        enqueue_handler=lambda _e, _p: True,
        log_fn=logs.append,
    )
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    status_ok, _ = _send_request(
        server,
        "POST",
        body="{}",
        headers={"X-GitHub-Event": "pull_request"},
    )

    thread.join(timeout=1)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    status_bad, _ = _send_request(server, "POST", body="{}", headers={})

    thread.join(timeout=1)
    server.server_close()

    assert status_ok == 200
    assert status_bad == 400
    metric_lines = [line for line in logs if line.startswith("webhook_request ")]
    assert any("outcome=accepted" in line and "status=200" in line for line in metric_lines)
    assert any(
        "outcome=rejected" in line and "reason=missing_event" in line and "status=400" in line
        for line in metric_lines
    )


def test_httpserver_increments_reject_counters():
    logs: list[str] = []

    server = serve_http(
        host="127.0.0.1",
        port=0,
        enqueue_handler=lambda _e, _p: True,
        log_fn=logs.append,
    )

    for _ in range(2):
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        _send_request(server, "POST", body="{}", headers={})
        thread.join(timeout=1)

    server.server_close()

    metric_lines = [line for line in logs if line.startswith("webhook_request ")]
    reject_lines = [line for line in metric_lines if "reason=missing_event" in line]
    assert len(reject_lines) == 2
    assert "reject_count=1" in reject_lines[0]
    assert "reject_count=2" in reject_lines[1]


def test_httpserver_rejects_missing_content_length_before_dispatch(monkeypatch):
    import ci_hunter.webhook_httpd_httpserver as webhook_httpd_httpserver

    called = {"count": 0}

    def fail_handle_incoming(**_kwargs):
        called["count"] += 1
        raise AssertionError("handle_incoming must not be called without content-length")

    monkeypatch.setattr(webhook_httpd_httpserver, "handle_incoming", fail_handle_incoming)
    server = serve_http(
        host="127.0.0.1",
        port=0,
        enqueue_handler=lambda _e, _p: True,
        log_fn=lambda _msg: None,
        max_body_bytes=4,
    )
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    status, payload = _send_raw_request(
        server,
        (
            b"POST / HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"X-GitHub-Event: pull_request\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            b'{"ok":true}'
        ),
    )

    thread.join(timeout=1)
    server.server_close()

    assert status == 411
    assert payload == b"missing content-length"
    assert called["count"] == 0


def test_httpserver_rejects_chunked_transfer_encoding_before_dispatch(monkeypatch):
    import ci_hunter.webhook_httpd_httpserver as webhook_httpd_httpserver

    called = {"count": 0}

    def fail_handle_incoming(**_kwargs):
        called["count"] += 1
        raise AssertionError("handle_incoming must not be called for chunked requests")

    monkeypatch.setattr(webhook_httpd_httpserver, "handle_incoming", fail_handle_incoming)
    server = serve_http(
        host="127.0.0.1",
        port=0,
        enqueue_handler=lambda _e, _p: True,
        log_fn=lambda _msg: None,
        max_body_bytes=4,
    )
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    status, payload = _send_raw_request(
        server,
        (
            b"POST / HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"X-GitHub-Event: pull_request\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            b"a\r\n0123456789\r\n0\r\n\r\n"
        ),
    )

    thread.join(timeout=1)
    server.server_close()

    assert status == 400
    assert payload == b"unsupported transfer encoding"
    assert called["count"] == 0

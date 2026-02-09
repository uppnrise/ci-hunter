import http.client
import json
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

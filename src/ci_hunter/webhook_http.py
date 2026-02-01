from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Mapping, Tuple

from ci_hunter.webhook_server import handle_webhook_request


def handle_webhook_http(
    *,
    headers: Mapping[str, str],
    body_text: str,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
) -> Tuple[HTTPStatus, str]:
    event = None
    for key, value in headers.items():
        if key.lower() == "x-github-event":
            event = value
            break
    if not event:
        return HTTPStatus.BAD_REQUEST, "missing event"
    return handle_webhook_request(
        event=event,
        payload_text=body_text,
        enqueue_handler=enqueue_handler,
    )

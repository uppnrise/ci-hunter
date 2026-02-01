from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any, Callable, Tuple


def handle_webhook_request(
    *,
    event: str,
    payload_text: str,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
) -> Tuple[HTTPStatus, str]:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return HTTPStatus.BAD_REQUEST, "invalid json"
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, "invalid json"

    handled = enqueue_handler(event, payload)
    if handled:
        return HTTPStatus.OK, "enqueued"
    return HTTPStatus.ACCEPTED, "ignored"

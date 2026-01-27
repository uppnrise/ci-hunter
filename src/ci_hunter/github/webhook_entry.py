from __future__ import annotations

from collections.abc import Callable, Collection
from typing import Any

from ci_hunter.github.webhook import parse_pull_request_webhook
from ci_hunter.github.webhook_handler import DEFAULT_ALLOWED_ACTIONS, handle_pull_request_event


def handle_webhook_event(
    event: str,
    payload: dict[str, Any],
    *,
    callback: Callable[..., None],
    allowed_actions: Collection[str] = DEFAULT_ALLOWED_ACTIONS,
) -> bool:
    trigger = parse_pull_request_webhook(event, payload)
    if trigger is None:
        return False
    return handle_pull_request_event(
        trigger,
        callback=callback,
        allowed_actions=allowed_actions,
    )


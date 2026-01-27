from __future__ import annotations

from collections.abc import Callable, Collection, Sequence
from typing import Any

from ci_hunter.github.webhook import parse_pull_request_webhook
from ci_hunter.github.webhook_cli_bridge import run_cli_for_trigger
from ci_hunter.github.webhook_handler import DEFAULT_ALLOWED_ACTIONS


def process_webhook_event(
    event: str,
    payload: dict[str, Any],
    *,
    cli_main: Callable[[list[str]], int],
    allowed_actions: Collection[str] = DEFAULT_ALLOWED_ACTIONS,
    extra_args: Sequence[str] | None = None,
) -> bool:
    trigger = parse_pull_request_webhook(event, payload)
    if trigger is None or trigger.action not in allowed_actions:
        return False
    exit_code = run_cli_for_trigger(trigger, cli_main=cli_main, extra_args=extra_args)
    return exit_code == 0

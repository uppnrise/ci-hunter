from __future__ import annotations

from collections.abc import Callable, Sequence

from ci_hunter.github.webhook_io import load_webhook_payload
from ci_hunter.github.webhook_runner import run_webhook


def run_webhook_from_text(
    event: str,
    payload_text: str,
    *,
    cli_main: Callable[[list[str]], int],
    extra_args: Sequence[str] | None = None,
) -> tuple[bool, int | None]:
    payload = load_webhook_payload(payload_text)
    return run_webhook(event, payload, cli_main=cli_main, extra_args=extra_args)


from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from ci_hunter.github.webhook_pipeline import process_webhook_event


def run_webhook(
    event: str,
    payload: dict[str, Any],
    *,
    cli_main: Callable[[list[str]], int],
    extra_args: Sequence[str] | None = None,
) -> tuple[bool, int | None]:
    exit_code: int | None = None

    def _cli(argv: list[str]) -> int:
        nonlocal exit_code
        exit_code = cli_main(argv)
        return exit_code

    handled = process_webhook_event(
        event,
        payload,
        cli_main=_cli,
        extra_args=extra_args,
    )
    return handled, exit_code


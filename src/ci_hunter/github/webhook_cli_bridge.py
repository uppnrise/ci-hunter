from __future__ import annotations

from collections.abc import Callable, Sequence

from ci_hunter.github.webhook import WebhookTrigger


def run_cli_for_trigger(
    trigger: WebhookTrigger,
    *,
    cli_main: Callable[[list[str]], int],
    extra_args: Sequence[str] | None = None,
) -> int:
    argv: list[str] = [
        "--repo",
        trigger.repo,
        "--pr-number",
        str(trigger.pr_number),
    ]
    if trigger.commit:
        argv.extend(["--commit", trigger.commit])
    if trigger.branch:
        argv.extend(["--branch", trigger.branch])
    if extra_args:
        argv.extend(extra_args)
    return cli_main(argv)


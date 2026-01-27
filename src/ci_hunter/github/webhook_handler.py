from __future__ import annotations

from collections.abc import Callable, Collection

from ci_hunter.github.webhook import WebhookTrigger

DEFAULT_ALLOWED_ACTIONS: tuple[str, ...] = ("opened", "synchronize", "reopened")


def handle_pull_request_event(
    trigger: WebhookTrigger,
    *,
    callback: Callable[..., None],
    allowed_actions: Collection[str] = DEFAULT_ALLOWED_ACTIONS,
) -> bool:
    if trigger.action not in allowed_actions:
        return False

    callback(
        repo=trigger.repo,
        pr_number=trigger.pr_number,
        commit=trigger.commit,
        branch=trigger.branch,
    )
    return True


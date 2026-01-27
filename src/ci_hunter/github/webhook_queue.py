from __future__ import annotations

from collections.abc import Collection
from typing import Any

from ci_hunter.github.webhook import parse_pull_request_webhook
from ci_hunter.github.webhook_handler import DEFAULT_ALLOWED_ACTIONS
from ci_hunter.queue import AnalysisJob, InMemoryJobQueue


def enqueue_webhook_event(
    event: str,
    payload: dict[str, Any],
    *,
    queue: InMemoryJobQueue,
    allowed_actions: Collection[str] = DEFAULT_ALLOWED_ACTIONS,
) -> bool:
    trigger = parse_pull_request_webhook(event, payload)
    if trigger is None or trigger.action not in allowed_actions:
        return False
    queue.enqueue(
        AnalysisJob(
            repo=trigger.repo,
            pr_number=trigger.pr_number,
            commit=trigger.commit,
            branch=trigger.branch,
        )
    )
    return True


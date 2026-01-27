from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PULL_REQUEST_EVENT = "pull_request"


@dataclass(frozen=True)
class WebhookTrigger:
    repo: str
    pr_number: int
    commit: str | None
    branch: str | None
    action: str


def parse_pull_request_webhook(event: str, payload: dict[str, Any]) -> WebhookTrigger | None:
    if event != PULL_REQUEST_EVENT:
        return None

    repository = _as_dict(payload.get("repository"))
    repo = repository.get("full_name")
    pr = _as_dict(payload.get("pull_request"))
    pr_number = pr.get("number")
    head = _as_dict(pr.get("head"))
    commit = head.get("sha")
    branch = head.get("ref")
    action = payload.get("action")

    if not repo or not isinstance(pr_number, int) or not action:
        return None

    return WebhookTrigger(
        repo=repo,
        pr_number=pr_number,
        commit=commit,
        branch=branch,
        action=action,
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

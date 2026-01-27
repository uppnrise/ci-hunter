from ci_hunter.github.webhook import WebhookTrigger
from ci_hunter.github.webhook_handler import (
    DEFAULT_ALLOWED_ACTIONS,
    handle_pull_request_event,
)

REPO = "acme/repo"
PR_NUMBER = 7
COMMIT = "abc123"
BRANCH = "feature-x"


def test_handle_pull_request_event_invokes_callback_for_allowed_action():
    trigger = WebhookTrigger(
        repo=REPO,
        pr_number=PR_NUMBER,
        commit=COMMIT,
        branch=BRANCH,
        action="opened",
    )
    called = {}

    def callback(*, repo: str, pr_number: int, commit: str | None, branch: str | None) -> None:
        called.update(
            {
                "repo": repo,
                "pr_number": pr_number,
                "commit": commit,
                "branch": branch,
            }
        )

    handled = handle_pull_request_event(trigger, callback=callback)

    assert handled is True
    assert called == {
        "repo": REPO,
        "pr_number": PR_NUMBER,
        "commit": COMMIT,
        "branch": BRANCH,
    }


def test_handle_pull_request_event_skips_disallowed_action():
    trigger = WebhookTrigger(
        repo=REPO,
        pr_number=PR_NUMBER,
        commit=COMMIT,
        branch=BRANCH,
        action="closed",
    )

    handled = handle_pull_request_event(trigger, callback=lambda **_: None)

    assert handled is False
    assert "closed" not in DEFAULT_ALLOWED_ACTIONS


from ci_hunter.github.webhook_entry import handle_webhook_event

REPO = "acme/repo"
PR_NUMBER = 99
HEAD_SHA = "abc123"
HEAD_REF = "feature-x"


def _pr_payload(action: str) -> dict:
    return {
        "action": action,
        "repository": {"full_name": REPO},
        "pull_request": {
            "number": PR_NUMBER,
            "head": {"sha": HEAD_SHA, "ref": HEAD_REF},
        },
    }


def test_handle_webhook_event_parses_and_dispatches():
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

    handled = handle_webhook_event("pull_request", _pr_payload("opened"), callback=callback)

    assert handled is True
    assert called == {
        "repo": REPO,
        "pr_number": PR_NUMBER,
        "commit": HEAD_SHA,
        "branch": HEAD_REF,
    }


def test_handle_webhook_event_ignores_non_pull_request_events():
    handled = handle_webhook_event("push", {"ref": "refs/heads/main"}, callback=lambda **_: None)

    assert handled is False


def test_handle_webhook_event_respects_allowed_actions():
    handled = handle_webhook_event(
        "pull_request",
        _pr_payload("closed"),
        callback=lambda **_: None,
    )

    assert handled is False


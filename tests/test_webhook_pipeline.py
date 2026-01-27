from ci_hunter.github.webhook_pipeline import process_webhook_event

REPO = "acme/repo"
PR_NUMBER = 5
HEAD_SHA = "abc123"
HEAD_REF = "feature-x"


def _payload(action: str) -> dict:
    return {
        "action": action,
        "repository": {"full_name": REPO},
        "pull_request": {
            "number": PR_NUMBER,
            "head": {"sha": HEAD_SHA, "ref": HEAD_REF},
        },
    }


def test_process_webhook_event_runs_cli_for_allowed_action():
    calls: list[list[str]] = []

    def cli_main(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    handled = process_webhook_event("pull_request", _payload("opened"), cli_main=cli_main)

    assert handled is True
    assert calls == [
        [
            "--repo",
            REPO,
            "--pr-number",
            str(PR_NUMBER),
            "--commit",
            HEAD_SHA,
            "--branch",
            HEAD_REF,
        ]
    ]


def test_process_webhook_event_skips_disallowed_action():
    calls: list[list[str]] = []

    handled = process_webhook_event("pull_request", _payload("closed"), cli_main=calls.append)

    assert handled is False
    assert calls == []


def test_process_webhook_event_returns_false_on_nonzero_exit_code():
    calls: list[list[str]] = []

    def cli_main(argv: list[str]) -> int:
        calls.append(argv)
        return 2

    handled = process_webhook_event("pull_request", _payload("opened"), cli_main=cli_main)

    assert handled is False
    assert calls

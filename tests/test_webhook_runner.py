from ci_hunter.github.webhook_runner import run_webhook

REPO = "acme/repo"
PR_NUMBER = 3
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


def test_run_webhook_returns_exit_code_when_handled():
    called = {}

    def cli_main(argv: list[str]) -> int:
        called["argv"] = argv
        return 0

    handled, exit_code = run_webhook(
        "pull_request",
        _payload("opened"),
        cli_main=cli_main,
        extra_args=["--dry-run"],
    )

    assert handled is True
    assert exit_code == 0
    assert called["argv"] == [
        "--repo",
        REPO,
        "--pr-number",
        str(PR_NUMBER),
        "--commit",
        HEAD_SHA,
        "--branch",
        HEAD_REF,
        "--dry-run",
    ]


def test_run_webhook_returns_none_when_not_handled():
    calls = {"count": 0}

    def cli_main(argv: list[str]) -> int:
        calls["count"] += 1
        return 0

    handled, exit_code = run_webhook("pull_request", _payload("closed"), cli_main=cli_main)

    assert handled is False
    assert exit_code is None
    assert calls["count"] == 0


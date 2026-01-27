import json

import pytest

from ci_hunter.github.webhook_cli import run_webhook_from_text

REPO = "acme/repo"
PR_NUMBER = 8
HEAD_SHA = "abc123"
HEAD_REF = "feature-x"


def _payload(action: str) -> str:
    return json.dumps(
        {
            "action": action,
            "repository": {"full_name": REPO},
            "pull_request": {
                "number": PR_NUMBER,
                "head": {"sha": HEAD_SHA, "ref": HEAD_REF},
            },
        }
    )


def test_run_webhook_from_text_dispatches_to_cli():
    captured: dict[str, object] = {}

    def cli_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    handled, exit_code = run_webhook_from_text(
        "pull_request",
        _payload("opened"),
        cli_main=cli_main,
        extra_args=["--dry-run"],
    )

    assert handled is True
    assert exit_code == 0
    assert captured["argv"] == [
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


def test_run_webhook_from_text_rejects_invalid_payload():
    with pytest.raises(ValueError):
        run_webhook_from_text("pull_request", "[]", cli_main=lambda _: 0)


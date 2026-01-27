from ci_hunter.github.webhook import WebhookTrigger
from ci_hunter.github.webhook_cli_bridge import run_cli_for_trigger

REPO = "acme/repo"
PR_NUMBER = 12
COMMIT = "abc123"
BRANCH = "feature-x"


def test_run_cli_for_trigger_builds_expected_args():
    trigger = WebhookTrigger(
        repo=REPO,
        pr_number=PR_NUMBER,
        commit=COMMIT,
        branch=BRANCH,
        action="opened",
    )
    captured: dict[str, object] = {}

    def cli_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    exit_code = run_cli_for_trigger(trigger, cli_main=cli_main)

    assert exit_code == 0
    assert captured["argv"] == [
        "--repo",
        REPO,
        "--pr-number",
        str(PR_NUMBER),
        "--commit",
        COMMIT,
        "--branch",
        BRANCH,
    ]


def test_run_cli_for_trigger_skips_missing_commit_and_branch():
    trigger = WebhookTrigger(
        repo=REPO,
        pr_number=PR_NUMBER,
        commit=None,
        branch=None,
        action="opened",
    )
    captured: dict[str, object] = {}

    def cli_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    exit_code = run_cli_for_trigger(trigger, cli_main=cli_main)

    assert exit_code == 0
    assert captured["argv"] == [
        "--repo",
        REPO,
        "--pr-number",
        str(PR_NUMBER),
    ]


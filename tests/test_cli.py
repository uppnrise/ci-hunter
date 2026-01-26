import io
from dataclasses import dataclass

from ci_hunter.analyze import AnalysisResult
from ci_hunter.cli import main
from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN

REPO = "acme/repo"
MIN_DELTA_PCT = 0.2
TOKEN = "ghs_token"
PR_NUMBER = 7


@dataclass(frozen=True)
class InstallationToken:
    token: str
    expires_at: str


class DummyAuth:
    def get_installation_token(self) -> InstallationToken:
        return InstallationToken(token=TOKEN, expires_at="2024-01-01T00:10:00Z")


def test_cli_dry_run_outputs_report():
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_INSTALLATION_ID": "456",
        "GITHUB_PRIVATE_KEY_PEM": "test-key",
    }
    captured = {}
    output = io.StringIO()

    def runner(**kwargs):
        captured.update(kwargs)
        return AnalysisResult(
            repo=REPO,
            regressions=[],
            reason=None,
            step_regressions=[],
            test_regressions=[],
            step_reason=None,
            test_reason=None,
            step_timings_attempted=0,
            step_timings_failed=0,
            test_timings_attempted=0,
            test_timings_failed=0,
        )

    exit_code = main(
        [
            "--repo",
            REPO,
            "--min-delta-pct",
            str(MIN_DELTA_PCT),
            "--timings-run-limit",
            "5",
            "--dry-run",
        ],
        env=env,
        runner=runner,
        auth_factory=lambda _env: DummyAuth(),
        markdown_renderer=lambda _: "report",
        out=output,
    )

    assert exit_code == 0
    assert "report" in output.getvalue()
    assert captured["repo"] == REPO
    assert captured["min_delta_pct"] == MIN_DELTA_PCT
    assert captured["baseline_strategy"] == BASELINE_STRATEGY_MEDIAN
    assert captured["timings_run_limit"] == 5
    assert callable(captured["step_fetcher"])
    assert callable(captured["test_fetcher"])


def test_cli_posts_comment_when_pr_number_set():
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_INSTALLATION_ID": "456",
        "GITHUB_PRIVATE_KEY_PEM": "test-key",
    }
    posted = {}

    def runner(**kwargs):
        return AnalysisResult(
            repo=REPO,
            regressions=[],
            reason=None,
            step_regressions=[],
            test_regressions=[],
            step_reason=None,
            test_reason=None,
            step_timings_attempted=0,
            step_timings_failed=0,
            test_timings_attempted=0,
            test_timings_failed=0,
        )

    def comment_poster(token: str, repo: str, pr_number: int, body: str) -> int:
        posted.update(
            {
                "token": token,
                "repo": repo,
                "pr_number": pr_number,
                "body": body,
            }
        )
        return 1

    exit_code = main(
        [
            "--repo",
            REPO,
            "--min-delta-pct",
            str(MIN_DELTA_PCT),
            "--pr-number",
            str(PR_NUMBER),
        ],
        env=env,
        runner=runner,
        auth_factory=lambda _env: DummyAuth(),
        markdown_renderer=lambda _: "comment body",
        comment_poster=comment_poster,
    )

    assert exit_code == 0
    assert posted["token"] == TOKEN
    assert posted["repo"] == REPO
    assert posted["pr_number"] == PR_NUMBER
    assert posted["body"] == "comment body"

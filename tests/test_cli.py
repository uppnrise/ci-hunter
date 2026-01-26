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


def test_cli_infers_pr_number_when_missing():
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

    inferred = {"number": 99}

    def pr_infer(*, token: str, repo: str, commit: str | None, branch: str | None):
        return type("Inferred", (), {"number": inferred["number"], "multiple_matches": False})()

    exit_code = main(
        [
            "--repo",
            REPO,
            "--commit",
            "abc123",
        ],
        env=env,
        runner=runner,
        auth_factory=lambda _env: DummyAuth(),
        markdown_renderer=lambda _: "comment body",
        comment_poster=comment_poster,
        pr_infer=pr_infer,
    )

    assert exit_code == 0
    assert posted["pr_number"] == inferred["number"]


def test_cli_reuses_installation_token_for_inference_and_comment():
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_INSTALLATION_ID": "456",
        "GITHUB_PRIVATE_KEY_PEM": "test-key",
    }
    calls = {"count": 0}
    posted = {}

    @dataclass(frozen=True)
    class CountingAuth:
        def get_installation_token(self) -> InstallationToken:
            calls["count"] += 1
            return InstallationToken(token=TOKEN, expires_at="2024-01-01T00:10:00Z")

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

    def pr_infer(*, token: str, repo: str, commit: str | None, branch: str | None):
        assert token == TOKEN
        return type("Inferred", (), {"number": PR_NUMBER, "multiple_matches": False})()

    def comment_poster(token: str, repo: str, pr_number: int, body: str) -> int:
        posted.update({"token": token, "repo": repo, "pr_number": pr_number})
        return 1

    exit_code = main(
        [
            "--repo",
            REPO,
            "--commit",
            "abc123",
        ],
        env=env,
        runner=runner,
        auth_factory=lambda _env: CountingAuth(),
        pr_infer=pr_infer,
        markdown_renderer=lambda _: "comment body",
        comment_poster=comment_poster,
    )

    assert exit_code == 0
    assert calls["count"] == 1
    assert posted["token"] == TOKEN


def test_cli_merges_config_with_cli_overrides(tmp_path):
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        """
repo: acme/from-config
min_delta_pct: 0.9
baseline_strategy: mean
db: "ci_hunter.db"
timings_run_limit: 3
format: json
dry_run: false
"""
    )

    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_INSTALLATION_ID": "456",
        "GITHUB_PRIVATE_KEY_PEM": "test-key",
    }
    captured = {}

    def runner(**kwargs):
        captured.update(kwargs)
        return AnalysisResult(
            repo="acme/from-config",
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
            "--config",
            str(config_path),
            "--repo",
            REPO,
            "--min-delta-pct",
            str(MIN_DELTA_PCT),
            "--dry-run",
        ],
        env=env,
        runner=runner,
        auth_factory=lambda _env: DummyAuth(),
        markdown_renderer=lambda _: "report",
        out=io.StringIO(),
    )

    assert exit_code == 0
    assert captured["repo"] == REPO
    assert captured["min_delta_pct"] == MIN_DELTA_PCT
    assert captured["baseline_strategy"] == "mean"
    assert captured["timings_run_limit"] == 3


def test_cli_writes_report_to_output_file(tmp_path):
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_INSTALLATION_ID": "456",
        "GITHUB_PRIVATE_KEY_PEM": "test-key",
    }
    output_path = tmp_path / "report.md"

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

    exit_code = main(
        [
            "--repo",
            REPO,
            "--dry-run",
            "--output-file",
            str(output_path),
        ],
        env=env,
        runner=runner,
        auth_factory=lambda _env: DummyAuth(),
        markdown_renderer=lambda _: "report body",
        out=io.StringIO(),
    )

    assert exit_code == 0
    assert output_path.read_text() == "report body\n"


def test_cli_no_comment_skips_posting(tmp_path):
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_INSTALLATION_ID": "456",
        "GITHUB_PRIVATE_KEY_PEM": "test-key",
    }
    output_path = tmp_path / "report.md"
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
        posted.update({"token": token, "repo": repo, "pr_number": pr_number})
        return 1

    exit_code = main(
        [
            "--repo",
            REPO,
            "--pr-number",
            str(PR_NUMBER),
            "--output-file",
            str(output_path),
            "--no-comment",
        ],
        env=env,
        runner=runner,
        auth_factory=lambda _env: DummyAuth(),
        markdown_renderer=lambda _: "report body",
        comment_poster=comment_poster,
        out=io.StringIO(),
    )

    assert exit_code == 0
    assert output_path.read_text() == "report body\n"
    assert posted == {}

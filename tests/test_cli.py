from ci_hunter.analyze import AnalysisResult
from ci_hunter.cli import main
from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN
from ci_hunter.github.auth import GitHubAppAuth
from ci_hunter.storage import Storage

REPO = "acme/repo"
MIN_DELTA_PCT = 0.2


def test_cli_invokes_runner_with_env_config():
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_INSTALLATION_ID": "456",
        "GITHUB_PRIVATE_KEY_PEM": "test-key",
    }
    captured = {}

    def runner(**kwargs):
        captured.update(kwargs)
        return AnalysisResult(repo=REPO, regressions=[], reason=None)

    exit_code = main(
        ["--repo", REPO, "--min-delta-pct", str(MIN_DELTA_PCT)],
        env=env,
        runner=runner,
    )

    assert exit_code == 0
    assert isinstance(captured["auth"], GitHubAppAuth)
    assert isinstance(captured["storage"], Storage)
    assert callable(captured["client_factory"])
    assert captured["repo"] == REPO
    assert captured["min_delta_pct"] == MIN_DELTA_PCT
    assert captured["baseline_strategy"] == BASELINE_STRATEGY_MEDIAN

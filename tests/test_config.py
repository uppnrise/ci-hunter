from ci_hunter.config import AppConfig, load_config


def test_load_config_from_yaml(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text(
        """
repo: acme/repo
min_delta_pct: 0.3
baseline_strategy: mean
db: ":memory:"
timings_run_limit: 5
format: md
dry_run: true
commit: abc123
branch: feature-1
"""
    )

    config = load_config(path)

    assert config == AppConfig(
        repo="acme/repo",
        min_delta_pct=0.3,
        baseline_strategy="mean",
        db=":memory:",
        timings_run_limit=5,
        format="md",
        dry_run=True,
        commit="abc123",
        branch="feature-1",
    )

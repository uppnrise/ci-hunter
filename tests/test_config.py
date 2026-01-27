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
min_history: 2
history_window: 10
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
        min_history=2,
        history_window=10,
        format="md",
        dry_run=True,
        commit="abc123",
        branch="feature-1",
    )


def test_load_config_boolean_strings_are_parsed():
    config = load_config_from_text(
        """
dry_run: "false"
"""
    )

    assert config.dry_run is False


def test_load_config_boolean_ints_are_parsed():
    config = load_config_from_text(
        """
no_comment: 1
"""
    )

    assert config.no_comment is True


def load_config_from_text(text: str) -> AppConfig:
    path = _write_config(text)
    return load_config(path)


def _write_config(text: str):
    import tempfile
    from pathlib import Path

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".yml")
    Path(temp.name).write_text(text)
    return temp.name

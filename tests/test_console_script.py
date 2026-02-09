from pathlib import Path
import tomllib


def test_console_scripts_declared_in_pyproject():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    scripts = tomllib.loads(pyproject)["project"]["scripts"]

    assert scripts["ci-hunter"] == "ci_hunter.cli:main"
    assert scripts["ci-hunter-webhook"] == "ci_hunter.webhook_cmd:main"
    assert scripts["ci-hunter-webhook-listener"] == "ci_hunter.webhook_listener_cmd:main"
    assert scripts["ci-hunter-scheduler"] == "ci_hunter.scheduler_cmd:main"
    assert scripts["ci-hunter-worker"] == "ci_hunter.worker_cmd:main"

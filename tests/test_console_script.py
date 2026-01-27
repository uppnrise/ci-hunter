from pathlib import Path
import tomllib


def test_console_scripts_declared_in_pyproject():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    scripts = tomllib.loads(pyproject)["project"]["scripts"]

    assert scripts["ci-hunter"] == "ci_hunter.cli:main"
    assert scripts["ci-hunter-webhook"] == "ci_hunter.webhook_cmd:main"

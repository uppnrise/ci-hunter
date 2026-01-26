import importlib.metadata


def test_console_script_registered():
    dist = importlib.metadata.distribution("ci-hunter")
    entry_points = {ep.name: ep.value for ep in dist.entry_points if ep.group == "console_scripts"}

    assert entry_points["ci-hunter"] == "ci_hunter.cli:main"

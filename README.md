# CI Hunter

CI Hunter is a small Python codebase for detecting CI run slowdowns. It currently:

- fetches GitHub Actions workflow runs, logs, and artifacts (via a GitHub App installation token),
- parses step timings (job-prefixed) and JUnit test durations (for recent runs),
- stores runs in SQLite,
- computes run-duration regressions with configurable baselines,
- renders markdown/JSON reports (with per-run/step/test sections and missing-data counts) and can post PR comments.

This repo is early-stage but includes a packaged console script (`ci-hunter`) and a Python-level entrypoint.

## Requirements

- Python 3.11+

## Install

Create a virtual environment and install dev deps:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
```

## Quick usage (current API)

```python
import os

from ci_hunter.analyze import analyze_repo_runs
from ci_hunter.cli import DEFAULT_MIN_DELTA_PCT
from ci_hunter.github.auth import GitHubAppAuth
from ci_hunter.github.client import GitHubActionsClient
from ci_hunter.storage import Storage, StorageConfig

auth = GitHubAppAuth(
    app_id=os.environ["GITHUB_APP_ID"],
    installation_id=os.environ["GITHUB_INSTALLATION_ID"],
    private_key_pem=os.environ["GITHUB_PRIVATE_KEY_PEM"],
)
token = auth.get_installation_token().token
client = GitHubActionsClient(token=token)
runs = client.list_workflow_runs("owner/repo")

storage = Storage(StorageConfig(database_url=":memory:"))
storage.save_workflow_runs("owner/repo", runs)

result = analyze_repo_runs(
    storage,
    "owner/repo",
    min_delta_pct=DEFAULT_MIN_DELTA_PCT,
)
print(result)
```

## CLI

The console script is installed as `ci-hunter` and wraps `ci_hunter.cli.main`. It supports:

- `--repo` (required)
- `--pr-number` (required unless `--dry-run` is set)
- `--min-delta-pct`
- `--baseline-strategy`
- `--db`
- `--timings-run-limit`
- `--min-history`
- `--history-window`
- `--commit` or `--branch` (for PR inference when `--pr-number` is omitted)
- `--config` (YAML config file)
- `--format {md,json}`
- `--dry-run`
- `--output-file`
- `--no-comment`

Examples:

```bash
# Dry-run to stdout
ci-hunter --repo owner/repo --dry-run --format md

# Post a PR comment
ci-hunter --repo owner/repo --pr-number 123 --format md
```

Python-level invocation remains available:

```python
from ci_hunter.cli import main

main(["--repo", "owner/repo", "--dry-run", "--format", "md"])
```

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Docs

- Architecture guide: `docs/ARCHITECTURE.md`
- Planned work: `docs/ROADMAP.md`
- Config notes: `docs/CONFIG.md`

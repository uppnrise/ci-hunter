# CI Hunter

CI Hunter is a small Python codebase for detecting CI run slowdowns. It currently:

- fetches GitHub Actions workflow runs (via an installation token you provide),
- stores runs in SQLite,
- computes run-duration regressions with a simple baseline strategy.

This repo is early-stage and has no CLI or GitHub App auth flow yet.

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
from ci_hunter.github.client import GitHubActionsClient
from ci_hunter.storage import Storage, StorageConfig

token = os.environ["GITHUB_INSTALLATION_TOKEN"]
client = GitHubActionsClient(token=token)
runs = client.list_workflow_runs("owner/repo")

storage = Storage(StorageConfig(database_url=":memory:"))
storage.save_workflow_runs("owner/repo", runs)

result = analyze_repo_runs(
    storage,
    "owner/repo",
    min_delta_pct=0.2,
)
print(result)
```

## Tests

```bash
pytest -q
```

## Docs

- Architecture guide: `docs/ARCHITECTURE.md`
- Planned work: `docs/ROADMAP.md`
- Config notes: `docs/CONFIG.md`

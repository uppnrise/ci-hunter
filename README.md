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

Additional console scripts:
- `ci-hunter-webhook` (local webhook payload runner)
- `ci-hunter-scheduler` (append jobs to a JSONL queue file)
- `ci-hunter-worker` (process jobs from a JSONL queue file)

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

## Webhooks (local testing)

There is no HTTP webhook server yet, but you can run the webhook pipeline locally by
passing a GitHub-style payload file into the CLI bridge:

```bash
python -m ci_hunter.webhook_cmd \
  --event pull_request \
  --payload-file payload.json \
  --dry-run
```

Minimal `payload.json` example:

```json
{
  "action": "opened",
  "repository": {"full_name": "owner/repo"},
  "pull_request": {
    "number": 123,
    "head": {"sha": "abc123", "ref": "feature-branch"}
  }
}
```

## Queue/Worker (local flow)

There is now an in-process queue/worker path you can use in code to simulate a
future webhook + worker architecture without running any server:

```python
from ci_hunter.cli import main as cli_main
from ci_hunter.github.webhook_queue_worker import process_webhook_event_via_queue
from ci_hunter.queue import InMemoryJobQueue
from ci_hunter.worker import Worker

queue = InMemoryJobQueue()
worker = Worker(queue=queue, cli_main=cli_main)

handled, processed = process_webhook_event_via_queue(
    "pull_request",
    payload,  # GitHub-style dict payload
    queue=queue,
    worker=worker,
)
```

## Scheduler (local queue file)

There is a simple scheduler CLI that appends jobs to a JSONL file. This is a
stand-in for a future persistent queue:

```bash
python -m ci_hunter.scheduler_cmd \
  --repo owner/repo \
  --pr-number 123 \
  --queue-file queue.jsonl
```

## Worker (local queue file)

The worker CLI consumes jobs from the JSONL queue file and calls the main CLI
for each job. You can limit how many jobs it processes per run:

```bash
python -m ci_hunter.worker_cmd \
  --queue-file queue.jsonl \
  --max-jobs 5
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

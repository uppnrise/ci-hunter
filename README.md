# CI Hunter

CI Hunter is a small Python codebase for detecting CI run slowdowns. It currently:

- fetches GitHub Actions workflow runs, logs, and artifacts (via a GitHub App installation token),
- parses step timings (job-prefixed), JUnit test durations, and JUnit test outcomes (for recent runs),
- stores workflow runs, step timings, test timings, and test outcomes in SQLite (default) or PostgreSQL via `--db`/`database_url`,
- computes run-duration regressions with configurable baselines,
- detects step/test duration change points from recent window shifts,
- detects flaky tests from historical outcomes,
- renders markdown/JSON reports (with per-run/step/test regression sections, change-point sections, flaky-test section, and missing-data counts) and can post PR comments.

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

## Database backends

`Storage` supports:
- SQLite paths, `:memory:`, and `sqlite:///:memory:` (default local/dev)
- PostgreSQL URLs (for example `postgresql://user:pass@localhost:5432/ci_hunter`)

Migration scaffold is included via Alembic:

```bash
alembic upgrade head
```

Alembic URLs using `postgresql://...` are normalized to `postgresql+psycopg://...`
at migration runtime, so the configured `psycopg` driver is used.

For PostgreSQL deployments, run migrations before starting app flows that write/read storage.
Runtime storage does not auto-create PostgreSQL tables.

Local Postgres profile (for integration testing):

```bash
docker compose -f docker-compose.postgres.yml up -d
export CI_HUNTER_POSTGRES_TEST_URL=postgresql://postgres:postgres@127.0.0.1:5433/ci_hunter_test
CI_HUNTER_ALEMBIC_URL="$CI_HUNTER_POSTGRES_TEST_URL" alembic upgrade head
pytest -q tests/integration/test_postgres_integration.py
docker compose -f docker-compose.postgres.yml down
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
  - applies to run/step/test regression baselines, step/test change-point analysis window, and flaky-test analysis window
- `--commit` or `--branch` (for PR inference when `--pr-number` is omitted)
- `--config` (YAML config file)
- `--format {md,json}`
- `--dry-run`
- `--output-file`
- `--no-comment`

Additional console scripts:
- `ci-hunter-webhook` (local webhook payload runner)
- `ci-hunter-webhook-listener` (HTTP webhook listener that enqueues JSONL jobs)
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

You can run the webhook pipeline locally by passing a GitHub-style payload file into
the CLI bridge. You can also run a local HTTP listener that enqueues jobs into
the JSONL queue used by `ci-hunter-worker`.

```bash
python -m ci_hunter.webhook_cmd \
  --event pull_request \
  --payload-file payload.json \
  --dry-run
```

```bash
ci-hunter-webhook-listener \
  --queue-file queue.jsonl \
  --host 127.0.0.1 \
  --port 8000
```

Or process a single request and exit:

```bash
ci-hunter-webhook-listener \
  --queue-file queue.jsonl \
  --once
```

Listener defaults:
- `--host` defaults to `127.0.0.1` (or `CI_HUNTER_WEBHOOK_HOST`).
- `--port` defaults to `8000` (or `CI_HUNTER_WEBHOOK_PORT`).
- `--port` must be in range `1..65535`.
- Request hardening env vars:
  - `CI_HUNTER_WEBHOOK_SECRET` enables GitHub `X-Hub-Signature-256` validation.
  - `CI_HUNTER_WEBHOOK_AUTH_TOKEN` requires `X-CI-HUNTER-TOKEN` header match.
  - `CI_HUNTER_WEBHOOK_MAX_BODY_BYTES` caps request size (default `1048576`).
- Rejection behavior:
  - invalid/missing auth or signature returns `401`.
  - oversized request body returns `413`.
  - unsupported `Transfer-Encoding` returns `400`.
  - missing/invalid `Content-Length` on POST returns `411`.
  - when `Content-Length` exceeds the configured limit, the listener rejects early without dispatching to the webhook handler.
- Observability:
  - listener emits structured request logs with `method`, `status`, `outcome`, `reason`, and per-reason `reject_count`.
  - listener emits a summary line on shutdown with total/accepted/rejected counters.

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

Loop mode (for polling):

```bash
python -m ci_hunter.worker_cmd \
  --queue-file queue.jsonl \
  --loop \
  --max-loops 10 \
  --sleep-seconds 2
```

Note: queue file access uses best-effort OS-specific file locks (fcntl on Unix, msvcrt on Windows).

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Docs

- Architecture guide: `docs/ARCHITECTURE.md`
- Planned work: `docs/ROADMAP.md`
- Config notes: `docs/CONFIG.md`
- Queue schema: `docs/QUEUE.md`

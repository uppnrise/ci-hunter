# Queue File (JSONL) — Schema

The scheduler/worker CLIs use a newline-delimited JSON (JSONL) file as a simple
stand-in for a persistent queue. Each line is one job.

## Required fields

- `repo` (string, non-empty)
- `pr_number` (integer, > 0)

## Optional fields

- `commit` (string or null)
- `branch` (string or null)

## Example

```json
{"repo":"owner/repo","pr_number":123,"commit":"abc123","branch":"feature-x"}
{"repo":"owner/repo","pr_number":124,"commit":null,"branch":null}
```

## Processing behavior

- `ci-hunter-scheduler` appends one JSON object per line to the queue file.
- `ci-hunter-webhook-listener` appends jobs in the same JSONL format when it
  receives supported pull_request webhook events.
- `ci-hunter-worker` reads the file, processes up to `--max-jobs`, then rewrites
  the file with any remaining jobs.
- Invalid JSON lines are skipped with a warning.
- Lines missing required fields are skipped with a warning.
- File locking is best-effort and OS-specific (fcntl on Unix, msvcrt on Windows).

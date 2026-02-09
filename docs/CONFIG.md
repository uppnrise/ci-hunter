# Config Notes

Configuration can be supplied via CLI flags or a YAML file passed with `--config`.

Current parameters:

- `GitHubAppAuth(app_id=..., installation_id=..., private_key_pem=...)` generates an installation token.
- `GitHubActionsClient(token=...)` expects that installation token.
- `analyze_repo_runs(..., min_delta_pct=..., baseline_strategy=..., min_history=..., history_window=...)`
  - `baseline_strategy` accepted values: `median`, `mean`, `trimmed_mean`
  - `min_history` is the minimum baseline run count required to evaluate regressions
  - `history_window` limits how many baseline runs to consider (most recent N)
- CLI (console script `ci-hunter`, entrypoint `ci_hunter.cli.main`) uses:
  - `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, `GITHUB_PRIVATE_KEY_PEM`
  - `--config` (YAML config file)
  - `--repo`, `--pr-number` (unless `--dry-run`), `--commit`/`--branch` (PR inference),
    `--min-delta-pct`, `--baseline-strategy`, `--db`, `--timings-run-limit`,
    `--min-history`, `--history-window`
  - `--format {md,json}`, `--dry-run`, `--output-file`, `--no-comment`
- Webhook listener CLI (console script `ci-hunter-webhook-listener`, entrypoint
  `ci_hunter.webhook_listener_cmd.main`) uses:
  - `--queue-file` (required), `--host`, `--port`, `--once`
  - env defaults: `CI_HUNTER_WEBHOOK_HOST`, `CI_HUNTER_WEBHOOK_PORT`

This file lists the supported env vars, YAML keys, and CLI flags.

Notes:
- Step timings are prefixed with the job log filename (e.g., `build/Checkout`).
- JSON reports include timing fetch counts: `step_timings_attempted`, `step_timings_failed`,
  `test_timings_attempted`, `test_timings_failed`.
- Config precedence: CLI > config > defaults. Secrets remain env-only.
- Boolean values in config accept true/false (case-insensitive); invalid strings raise an error.
- `min_history` and `history_window` must be positive integers when set.
- GitHub API calls use a small retry/backoff policy for transient errors (5xx/429).
- Config supports `output_file` and `no_comment` if you prefer file output without posting.
- `CI_HUNTER_WEBHOOK_PORT` must be parseable as an integer in range `1..65535`;
  otherwise it falls back to default (`8000`).
- `--port` enforces range `1..65535`.

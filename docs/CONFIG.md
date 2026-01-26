# Config Notes

There is no central config file yet. Configuration is passed as function arguments.

Current parameters:

- `GitHubAppAuth(app_id=..., installation_id=..., private_key_pem=...)` generates an installation token.
- `GitHubActionsClient(token=...)` expects that installation token.
- `analyze_repo_runs(..., min_delta_pct=..., baseline_strategy=...)`
  - `baseline_strategy` accepted values: `median`, `mean`, `trimmed_mean`
- CLI (console script `ci-hunter`, entrypoint `ci_hunter.cli.main`) uses:
  - `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, `GITHUB_PRIVATE_KEY_PEM`
  - `--repo`, `--pr-number` (unless `--dry-run`), `--min-delta-pct`, `--baseline-strategy`, `--db`, `--timings-run-limit`
  - `--format {md,json}`, `--dry-run`

Once a config system is added, this file will list the supported env vars and YAML keys.

Notes:
- Step timings are prefixed with the job log filename (e.g., `build/Checkout`).
- JSON reports include timing fetch counts: `step_timings_attempted`, `step_timings_failed`,
  `test_timings_attempted`, `test_timings_failed`.

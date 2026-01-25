# Config Notes

There is no central config file yet. Configuration is passed as function arguments.

Current parameters:

- `GitHubActionsClient(token=...)` expects a GitHub App installation token.
- `analyze_repo_runs(..., min_delta_pct=..., baseline_strategy=...)`
  - `baseline_strategy` accepted values: `median`, `mean`, `trimmed_mean`

Once a config system is added, this file will list the supported env vars and YAML keys.


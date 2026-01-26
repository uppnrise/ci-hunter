# Roadmap

## Done

1) GitHub Actions client + GitHub App auth
2) SQLite storage for runs, step timings, and test timings (with FK enforcement)
3) Basic step duration parsing from GitHub Actions log text (job-prefixed)
4) JUnit test duration parsing (XML)
5) CI artifact download + JUnit test duration extraction
6) Run duration extraction helper
7) Markdown regression report rendering (run/step/test sections)
8) JSON regression report rendering (includes timing counts)
9) GitHub PR comment posting helper
10) CLI end-to-end flow with dry-run and PR posting
11) Missing timing counts (attempted/failed) in reports
12) Pagination for workflow runs

## Planned

### Near-term (next)
1) Infer PR from branch/commit
2) Config system (YAML + env overrides)
3) Minimal retry/backoff policy for GitHub API calls
4) Optional output destinations (file or stdout in addition to PR comment)

### Medium-term (from Architecture)
1) Webhook listener + scheduler + worker queue
2) Postgres storage + migrations
3) Provider abstraction + GitLab support
4) Step/test change-point detection + flake detection
5) Attribution to touched files (git diff integration)
6) LLM explainer/remediator (optional, toggleable)
7) Slack/Teams notifications + GitHub check-runs
8) Artifact/log storage in object storage (S3-compatible)
9) Observability: metrics/tracing, rate limit handling, and runbook

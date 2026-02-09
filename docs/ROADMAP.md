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
13) Infer PR from branch/commit
14) Config system (YAML + env overrides)
15) Minimal retry/backoff policy for GitHub API calls
16) Optional output destinations (file or stdout in addition to PR comment)
17) Webhook groundwork (pull_request parsing + CLI pipeline runner)
18) In-process queue/worker groundwork (enqueue + worker loop)
19) Scheduler CLI to enqueue jobs into JSONL queue
20) Worker CLI to process JSONL queue jobs
21) Cross-platform queue file locking (fcntl/msvcrt)
22) Webhook HTTP handler building blocks
23) Stdlib HTTP webhook adapter (`serve_http`) wired to webhook handler stack
24) Webhook listener CLI lifecycle (`--once`, `serve_forever`, graceful shutdown, host/port config)
25) Webhook listener hardening (signature verification, body size limit, auth token)

## Planned

### Near-term (next)
1) Postgres storage + migrations
2) Provider abstraction + GitLab support
3) Step/test change-point detection + flake detection
4) Webhook listener observability (structured request metrics + reject counters)
5) Webhook request-body hardening beyond `Content-Length` (streaming/chunked-body guard)

### Medium-term (from Architecture)
1) Attribution to touched files (git diff integration)
2) LLM explainer/remediator (optional, toggleable)
3) Slack/Teams notifications + GitHub check-runs
4) Artifact/log storage in object storage (S3-compatible)
5) Observability: metrics/tracing, rate limit handling, and runbook

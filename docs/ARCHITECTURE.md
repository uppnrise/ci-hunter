# CI/Test Slowdown Hunter — Architecture Guide

End-to-end blueprint for an agent that detects CI bottlenecks, attributes likely causes, and posts actionable remediation to developers. This document includes **target architecture** ideas that are not implemented yet.

## Status (Current Implementation)
- GitHub Actions client + GitHub App auth
- SQLite storage for workflow runs
- Run-duration regression detection (configurable baselines)
- Step timing parsing from run logs
- JUnit test duration parsing from artifacts
- Markdown/JSON report rendering
- CLI that can dry-run to stdout, write output files, or post PR comments
- YAML config support with CLI overrides
- GitHub API retry/backoff for transient errors

## 0) Scope and Modes
- **Use cases**: PR regression commenting, scheduled branch monitoring, ChatOps queries, local dry-runs.
- **CI targets**: GitHub Actions (first), GitLab CI (later). Input data: run metadata, step timings, logs, JUnit/XML test results, artifacts.
- **Outputs**: PR comments (markdown), Slack/Teams alerts, JSON/CLI reports, optional Git check-runs.
- **LLM**: Used only for explanation/remediation text; detection is deterministic/ML. Must be toggleable (on/off, model choice).

## 1) System Context
- **Inbound**: CI APIs/webhooks, git diff for touched files, test artifacts.
- **Processing**: Metrics + features → change-point/flakiness detection → attribution → LLM explanation → channel delivery.
- **Outbound**: GitHub/GitLab comments, chat notifications, CLI/JSON.
- **Storage**: Postgres for production run history + checkpoints (SQLite for dev); object storage for logs/artifacts. Stateless mode can fall back to CI-provider history only; persistent storage is preferred for consistent baselines.

## 2) Core Components
- **Orchestrator (LangGraph)**: StateGraph nodes/edges compiled with a checkpointer for durable execution; handles retries/guards; clean separation between detection (pure Python) and narrative (LLM).
- **Data layer**: Providers for CI (runs, steps, artifacts), VCS (diff), identity (authors), and storage (SQLite/JSON).
- **Execution plane**: Webhook listener + scheduler + worker pool, backed by a queue for rate-limited, retryable processing.
- **Detection engine**:
  - Change-point detection on step/test durations (e.g., `ruptures` or EWMA).
  - Flake detection from historical pass/fail (fail-rate thresholds + recency weighting).
  - Attribution by mapping regressed steps/tests to touched files and prior offenders.
- **Narration layer (LLM)**: Summaries and remediation playbooks; prompt templates parameterized by severity, suspects, and environment.
- **Delivery layer**: GitHub/GitLab comment/post, Slack/Teams message, CLI formatter.
- **Config**: YAML with thresholds, model selection, feature toggles, channel routing, label-based opt-out.

## 3) LangGraph Design
- **State (pydantic)**
  - `repo`, `pr_number`, `branch`, `commit`
  - `runs: list[RunSummary]` (id, sha, started_at, duration, steps[], tests[])
  - `regressions: list[Regression]` (entity, metric, baseline, current, delta_pct, p_value, severity, evidence)
  - `flakes: list[Flake]` (test_id, fail_rate, recent_failures)
  - `suspects: list[Suspect]` (file, weight, reason)
  - `actions: list[Action]` (message, targets, diffs/commands)
  - `outputs` (markdown, json)
- **Nodes**
  - `fetch_runs`: pull latest N runs for PR/branch; fetch steps + artifacts.
  - `featurize_metrics`: build timeseries for steps/tests, normalize durations, derive per-entity features.
  - `detect_change_points`: run change-point/EWMA; flag regressions with deltas + significance.
  - `detect_flakes`: compute fail-rate and volatility for tests; rank by impact.
  - `attribute_regressions`: map regressions to touched files/tests; include historical offenders.
  - `persist_history`: write runs, detections, and flakes to storage for future baselines.
  - `llm_explainer`: generate concise narrative; include suspects, confidence, and quick wins.
  - `llm_remediator`: draft PR comment/chat message with actionable bullets and links to evidence.
  - `post_comment` / `post_chat`: deliver to GitHub/GitLab/Slack; gated by config.
- **Control flow**
  - Triggered by webhook/cron/CLI → fetch → featurize → detect (parallel change-point + flake) → attribute → persist_history → LLM (optional) → deliver.
  - Short-circuit if no regressions/flakes; emit “clean” status and still persist run metadata for history growth.
  - Retries on external API calls with backoff; failure paths produce diagnostic output instead of breaking the graph.
  - Graph compiled with a checkpointer; use `thread_id` (per PR/run) to resume or re-run safely, and `checkpoint_id` when replaying a specific state.
  - Optional human-in-the-loop gate (LangGraph `interrupt` + `Command`) for high-severity notifications before posting.
  - Use `Send` for map-reduce style fan-out when per-test or per-step analysis is large.

## 4) Data & Storage
- **LangGraph checkpoints**: checkpointer persists graph state (InMemory for dev; Postgres recommended for prod) keyed by `thread_id` so runs can resume/replay.
- **History DB**: `runs`, `steps`, `tests`, `detections`, `flakes` tables; Postgres for prod, SQLite for dev; migrations via `alembic` or simple schema bootstrap.
- **Artifacts**: store raw logs/JUnit locally or S3-compatible; path recorded in state.
- **History policy**: keep rolling window (e.g., last 200 runs per branch) plus aggregates for baselines; prune old runs to cap size.
- **Caching**: memoize CI fetches per run id; cache prompts/results optionally for cost control.

## 5) Detection Logic (deterministic/ML)
- **Change-point**: per step/test duration series; require min history window; thresholds: min delta % (e.g., 15%), p-value or rank. If history < minimum, degrade to heuristic checks (e.g., absolute thresholds) and label output as low-confidence.
- **Flake**: rolling fail-rate + count; mark flaky if fail-rate > X% with at least Y failures across Z runs; decay older runs.
- **Attribution**: intersect regressed steps/tests with touched files (git diff) and known mappings (path heuristics); assign weights and confidence.
- **Learning cadence**: recompute baselines and flake rates every run; optional periodic recomputation over full window to avoid drift.

## 6) LLM Usage
- **Isolation**: only `llm_explainer` and `llm_remediator` call LLMs; the rest is pure Python.
- **Configurable**: model name, provider, temperature, max tokens; allow “off” mode to emit rule-based text.
- **Cost control**: truncate inputs (top K regressions/tests); cache outputs by (run_id, summary hash).
- **Prompts**: include run context, deltas, suspects, logs snippets; instruct to be concise and actionable.

## 7) Integration Points
- **GitHub**: PAT or GitHub App; APIs for runs, logs, artifacts, comments; check-run optional.
- **GitLab**: similar shape; abstract via provider interface.
- **Chat**: Slack/Teams via webhook; formatter for bullets and links.
- **CLI**: `ci-hunter --repo org/repo --pr-number 123 --format md` outputs markdown for local validation.

## 8) Deployment Topologies
- **GitHub App mode**: receives webhooks (check_suite, pull_request); runs analyzer; posts comment.
- **Cron/worker**: runs on schedule to monitor default branch; posts chat alerts.
- **Self-hosted runner**: containerized service; env vars for secrets; local SQLite volume.
- **Local dev**: `.env` for tokens; dry-run mode writes markdown to stdout.
- **Production (recommended)**: webhook service → queue (SQS/Redis) → worker pool; separate scheduler; Postgres + object storage; autoscaling workers.

## 9) Configuration (example)
```yaml
ci:
  provider: github
  repo: org/repo
  min_history: 15
thresholds:
  min_delta_pct: 15
  min_p_value: 0.05
  min_fail_count: 3
llm:
  enabled: true
  model: gpt-4o
  temperature: 0.2
delivery:
  github_comments: true
  slack_webhook: $SLACK_WEBHOOK
labels:
  disable: ["ci-bottleneck-disable"]
```

## 10) Observability & Reliability
- **Logging**: structured logs per node; include run_id, pr_number, regression count, provider request ids.
- **Metrics**: detection latency, API error rates, comments posted, LLM token usage, queue depth.
- **Tracing**: wrap LangGraph nodes with tracing (OTel); attach step durations and external call spans.
- **Retries**: external calls with capped backoff; idempotent writes (comment dedup by marker + run_id).
- **Rate limits**: adaptive backoff and token bucket per provider; cache CI responses to reduce load.
- **Circuit breakers**: disable LLM if provider errors spike; fallback to rule-based text.

## 11) Security
- **Secrets**: tokens via env/secret store; never log; scope minimal permissions; rotate regularly.
- **Data hygiene**: redact secrets from logs/prompts; cap log snippet size; encrypt data at rest in prod.
- **Permissions**: comments only on allowed repos; opt-out labels; audit log of actions; repo allowlist.
- **Multi-tenant controls**: per-repo config isolation, least-privilege tokens per installation, and data partitioning.

## 12) Testing Strategy
- **Unit**: detectors (change-point, flake), attribution, formatting.
- **Integration**: fake CI provider + git diff; golden markdown outputs.
- **E2E**: record/replay CI API (VCR-style) to validate the full graph without live tokens.
- **Load**: run against synthetic history to ensure latency acceptable (< few seconds per run).
- **Staging**: production-like environment with masked data and canary deploys for new detectors/prompts.

## 13) Extensibility Paths
- Add providers (CircleCI, Buildkite) by implementing provider interface.
- Swap detectors (Prophet, STL) without touching graph wiring.
- Add delivery channels (Teams, email) via pluggable notifier.
- Add “cost/perf right-sizing” mode by reusing graph skeleton.

## 14) Week-1 Build Plan (MVP)
1. Bootstrap repo, config loader, SQLite schema, provider interface + GitHub fetch.
2. Implement change-point + flake detectors with synthetic data; add unit tests; define minimum history policy and degraded mode messaging.
3. Wire LangGraph nodes; stub LLM with rule-based text; persist runs/detections after each execution. (CLI added.)
4. GitHub comment delivery with dedup marker; dry-run mode.
5. Add optional LLM explainer/remediator; prompt templates; token logging.

## 15) Developer Experience
- **Local loop**: `ci-hunter --repo org/repo --dry-run --format md` to view markdown.
- **Config-first**: single YAML; env-var overrides.
- **Docs**: quickstart, provider setup, config reference, prompt tuning.
- **Safeguards**: “no regressions found” message; respect disable labels; bounded outputs.

## 16) Production Readiness Checklist
- **Architecture**: webhook ingress, queue-backed workers, scheduler, Postgres, object storage, and autoscaling.
- **Reliability**: idempotency keys, deduped comments, dead-letter queue, replayable jobs.
- **Security**: secret rotation, least-privilege tokens, encryption at rest, audit logs, repo allowlists.
- **Operations**: SLOs/alerts, dashboards, runbook, backups, retention policies, schema migrations.
- **LLM governance**: cost caps, model fallback, prompt/version tracking, evals for regressions.

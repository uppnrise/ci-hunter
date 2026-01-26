from __future__ import annotations

from typing import Callable

from ci_hunter.analyze import AnalysisResult, analyze_repo_runs
from ci_hunter.github.auth import GitHubAppAuth
from ci_hunter.github.client import GitHubActionsClient
from ci_hunter.storage import Storage
from ci_hunter.steps import StepDuration
from ci_hunter.junit import TestDuration


def fetch_store_analyze(
    *,
    auth: GitHubAppAuth,
    client_factory: Callable[[str], GitHubActionsClient],
    storage: Storage,
    repo: str,
    min_delta_pct: float,
    baseline_strategy: str,
    step_fetcher: Callable[[str, str, int], list[StepDuration]] | None = None,
    test_fetcher: Callable[[str, str, int], list[TestDuration]] | None = None,
    timings_run_limit: int | None = None,
) -> AnalysisResult:
    installation = auth.get_installation_token()
    client = client_factory(installation.token)
    runs = client.list_workflow_runs(repo)
    storage.save_workflow_runs(repo, runs)
    timing_stats = _TimingStats()
    if step_fetcher or test_fetcher:
        timing_stats = _fetch_and_store_timings(
            token=installation.token,
            repo=repo,
            runs=runs,
            storage=storage,
            step_fetcher=step_fetcher,
            test_fetcher=test_fetcher,
            run_limit=timings_run_limit,
        )
    analysis = analyze_repo_runs(
        storage,
        repo,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
    )
    return AnalysisResult(
        repo=analysis.repo,
        regressions=analysis.regressions,
        reason=analysis.reason,
        step_regressions=analysis.step_regressions,
        test_regressions=analysis.test_regressions,
        step_reason=analysis.step_reason,
        test_reason=analysis.test_reason,
        step_timings_attempted=timing_stats.step_attempted,
        step_timings_failed=timing_stats.step_failed,
        test_timings_attempted=timing_stats.test_attempted,
        test_timings_failed=timing_stats.test_failed,
    )


class _TimingStats:
    def __init__(self) -> None:
        self.step_attempted = 0
        self.step_failed = 0
        self.test_attempted = 0
        self.test_failed = 0


def _fetch_and_store_timings(
    *,
    token: str,
    repo: str,
    runs: list,
    storage: Storage,
    step_fetcher: Callable[[str, str, int], list[StepDuration]] | None,
    test_fetcher: Callable[[str, str, int], list[TestDuration]] | None,
    run_limit: int | None,
) -> _TimingStats:
    stats = _TimingStats()
    runs_sorted = sorted(runs, key=lambda run: run.run_number)
    if run_limit is not None:
        runs_sorted = runs_sorted[-run_limit:]
    for run in runs_sorted:
        if step_fetcher is not None:
            stats.step_attempted += 1
            try:
                durations = step_fetcher(token, repo, run.id)
            except Exception:
                stats.step_failed += 1
                durations = []
            if durations:
                storage.save_step_durations(repo, run.id, durations)
        if test_fetcher is not None:
            stats.test_attempted += 1
            try:
                durations = test_fetcher(token, repo, run.id)
            except Exception:
                stats.test_failed += 1
                durations = []
            if durations:
                storage.save_test_durations(repo, run.id, durations)
    return stats

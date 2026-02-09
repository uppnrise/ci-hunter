from __future__ import annotations

import logging
from typing import Callable

from ci_hunter.analyze import AnalysisResult, analyze_repo_runs
from ci_hunter.github.auth import GitHubAppAuth
from ci_hunter.github.client import GitHubActionsClient
from ci_hunter.storage import Storage
from ci_hunter.steps import StepDuration
from ci_hunter.junit import TestDuration, TestOutcome

logger = logging.getLogger(__name__)

def fetch_store_analyze(
    *,
    auth: GitHubAppAuth,
    client_factory: Callable[[str], GitHubActionsClient],
    storage: Storage,
    repo: str,
    min_delta_pct: float,
    baseline_strategy: str,
    min_history: int = 1,
    history_window: int | None = None,
    step_fetcher: Callable[[str, str, int], list[StepDuration]] | None = None,
    test_fetcher: Callable[[str, str, int], list[TestDuration]] | None = None,
    test_outcome_fetcher: Callable[[str, str, int], list[TestOutcome]] | None = None,
    timings_run_limit: int | None = None,
) -> AnalysisResult:
    installation = auth.get_installation_token()
    client = client_factory(installation.token)
    runs = client.list_workflow_runs(repo)
    storage.save_workflow_runs(repo, runs)
    timing_stats = _TimingStats()
    if step_fetcher or test_fetcher or test_outcome_fetcher:
        timing_stats = _fetch_and_store_timings(
            token=installation.token,
            repo=repo,
            runs=runs,
            storage=storage,
            step_fetcher=step_fetcher,
            test_fetcher=test_fetcher,
            test_outcome_fetcher=test_outcome_fetcher,
            run_limit=timings_run_limit,
        )
    analysis = analyze_repo_runs(
        storage,
        repo,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
        min_history=min_history,
        history_window=history_window,
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
        step_change_points=analysis.step_change_points,
        test_change_points=analysis.test_change_points,
        flakes=analysis.flakes,
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
    test_outcome_fetcher: Callable[[str, str, int], list[TestOutcome]] | None,
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
                if durations:
                    storage.save_step_durations(repo, run.id, durations)
                else:
                    stats.step_failed += 1
                    logger.info(
                        "Step timings missing for repo=%s run_id=%s",
                        repo,
                        run.id,
                    )
            except Exception:
                stats.step_failed += 1
                logger.warning(
                    "Step timings fetch failed for repo=%s run_id=%s",
                    repo,
                    run.id,
                    exc_info=True,
                )
        if test_fetcher is not None:
            stats.test_attempted += 1
            try:
                durations = test_fetcher(token, repo, run.id)
                if durations:
                    storage.save_test_durations(repo, run.id, durations)
                else:
                    stats.test_failed += 1
                    logger.info(
                        "Test timings missing for repo=%s run_id=%s",
                        repo,
                        run.id,
                    )
            except Exception:
                stats.test_failed += 1
                logger.warning(
                    "Test timings fetch failed for repo=%s run_id=%s",
                    repo,
                    run.id,
                    exc_info=True,
                )
        if test_outcome_fetcher is not None:
            try:
                outcomes = test_outcome_fetcher(token, repo, run.id)
                if outcomes:
                    storage.save_test_outcomes(repo, run.id, outcomes)
            except Exception:
                logger.warning(
                    "Test outcomes fetch failed for repo=%s run_id=%s",
                    repo,
                    run.id,
                    exc_info=True,
                )
    return stats

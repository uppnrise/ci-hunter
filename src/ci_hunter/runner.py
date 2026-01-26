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
    if step_fetcher or test_fetcher:
        _fetch_and_store_timings(
            token=installation.token,
            repo=repo,
            runs=runs,
            storage=storage,
            step_fetcher=step_fetcher,
            test_fetcher=test_fetcher,
            run_limit=timings_run_limit,
        )
    return analyze_repo_runs(
        storage,
        repo,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
    )


def _fetch_and_store_timings(
    *,
    token: str,
    repo: str,
    runs: list,
    storage: Storage,
    step_fetcher: Callable[[str, str, int], list[StepDuration]] | None,
    test_fetcher: Callable[[str, str, int], list[TestDuration]] | None,
    run_limit: int | None,
) -> None:
    runs_sorted = sorted(runs, key=lambda run: run.run_number)
    if run_limit is not None:
        runs_sorted = runs_sorted[-run_limit:]
    for run in runs_sorted:
        if step_fetcher is not None:
            try:
                durations = step_fetcher(token, repo, run.id)
            except Exception:
                durations = []
            if durations:
                storage.save_step_durations(repo, run.id, durations)
        if test_fetcher is not None:
            try:
                durations = test_fetcher(token, repo, run.id)
            except Exception:
                durations = []
            if durations:
                storage.save_test_durations(repo, run.id, durations)

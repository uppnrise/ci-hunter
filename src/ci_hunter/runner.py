from __future__ import annotations

from typing import Callable

from ci_hunter.analyze import AnalysisResult, analyze_repo_runs
from ci_hunter.github.auth import GitHubAppAuth
from ci_hunter.github.client import GitHubActionsClient
from ci_hunter.storage import Storage


def fetch_store_analyze(
    *,
    auth: GitHubAppAuth,
    client_factory: Callable[[str], GitHubActionsClient],
    storage: Storage,
    repo: str,
    min_delta_pct: float,
    baseline_strategy: str,
) -> AnalysisResult:
    installation = auth.get_installation_token()
    client = client_factory(installation.token)
    runs = client.list_workflow_runs(repo)
    storage.save_workflow_runs(repo, runs)
    return analyze_repo_runs(
        storage,
        repo,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
    )

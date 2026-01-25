from __future__ import annotations

from dataclasses import dataclass
from typing import List

import httpx


@dataclass(frozen=True)
class WorkflowRun:
    id: int
    run_number: int
    status: str | None
    conclusion: str | None
    created_at: str
    updated_at: str
    head_sha: str


class GitHubActionsClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")

    def list_workflow_runs(self, repo: str, per_page: int = 30) -> List[WorkflowRun]:
        response = httpx.get(
            f"{self._base_url}/repos/{repo}/actions/runs",
            params={"per_page": per_page},
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()

        runs = []
        for run in payload.get("workflow_runs", []):
            runs.append(
                WorkflowRun(
                    id=run["id"],
                    run_number=run["run_number"],
                    status=run.get("status"),
                    conclusion=run.get("conclusion"),
                    created_at=run["created_at"],
                    updated_at=run["updated_at"],
                    head_sha=run["head_sha"],
                )
            )
        return runs

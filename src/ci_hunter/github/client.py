from __future__ import annotations

from dataclasses import dataclass
from typing import List

import httpx

from ci_hunter.github.http import request_with_retry


DEFAULT_BASE_URL = "https://api.github.com"
DEFAULT_TIMEOUT_SECONDS = 10.0
GITHUB_ACCEPT_HEADER = "application/vnd.github+json"
GITHUB_API_VERSION = "2022-11-28"
HEADER_ACCEPT = "Accept"
HEADER_AUTHORIZATION = "Authorization"
HEADER_API_VERSION = "X-GitHub-Api-Version"
AUTH_SCHEME = "Bearer"


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
    def __init__(self, token: str, base_url: str = DEFAULT_BASE_URL) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")

    def list_workflow_runs(self, repo: str, per_page: int = 30) -> List[WorkflowRun]:
        runs: list[WorkflowRun] = []
        page = 1
        while True:
            response = request_with_retry(
                "GET",
                f"{self._base_url}/repos/{repo}/actions/runs",
                params={"per_page": per_page, "page": page},
                headers={
                    HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {self._token}",
                    HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
                    HEADER_API_VERSION: GITHUB_API_VERSION,
                },
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()

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
            link_header = response.headers.get("Link", "")
            if 'rel="next"' not in link_header:
                break
            page += 1
        return runs

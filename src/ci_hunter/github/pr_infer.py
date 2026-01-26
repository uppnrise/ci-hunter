from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from ci_hunter.github.client import (
    AUTH_SCHEME,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    HEADER_ACCEPT,
    HEADER_API_VERSION,
    HEADER_AUTHORIZATION,
)
from ci_hunter.github.http import request_with_retry
from ci_hunter.time_utils import parse_iso_datetime


@dataclass(frozen=True)
class InferredPullRequest:
    number: int
    multiple_matches: bool


def infer_pr_number(
    *,
    token: str,
    repo: str,
    commit: Optional[str] = None,
    branch: Optional[str] = None,
    base_url: str = DEFAULT_BASE_URL,
) -> Optional[InferredPullRequest]:
    if commit:
        pulls = _list_pulls_for_commit(token, repo, commit, base_url)
    elif branch:
        pulls = _list_pulls_for_branch(token, repo, branch, base_url)
    else:
        raise ValueError("commit or branch is required for PR inference")

    if not pulls:
        return None

    open_pulls = [pull for pull in pulls if pull.get("state") == "open"]
    candidates = open_pulls or pulls
    candidates.sort(
        key=lambda item: parse_iso_datetime(item.get("updated_at", "1970-01-01T00:00:00Z")),
        reverse=True,
    )
    selected = candidates[0]
    return InferredPullRequest(
        number=selected["number"],
        multiple_matches=len(candidates) > 1,
    )


def _list_pulls_for_commit(
    token: str,
    repo: str,
    commit: str,
    base_url: str,
) -> list[dict]:
    response = request_with_retry(
        "GET",
        f"{base_url.rstrip('/')}/repos/{repo}/commits/{commit}/pulls",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {token}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _list_pulls_for_branch(
    token: str,
    repo: str,
    branch: str,
    base_url: str,
) -> list[dict]:
    owner = repo.split("/")[0]
    response = request_with_retry(
        "GET",
        f"{base_url.rstrip('/')}/repos/{repo}/pulls",
        params={"state": "open", "head": f"{owner}:{branch}"},
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {token}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()

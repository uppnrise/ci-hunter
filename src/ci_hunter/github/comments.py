from __future__ import annotations

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


def post_pr_comment(
    token: str,
    repo: str,
    pr_number: int,
    body: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
) -> int:
    response = request_with_retry(
        "POST",
        f"{base_url.rstrip('/')}/repos/{repo}/issues/{pr_number}/comments",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {token}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
        json={"body": body},
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return int(payload["id"])

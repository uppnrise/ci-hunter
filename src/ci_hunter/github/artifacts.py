from __future__ import annotations

import io
import zipfile
from typing import List

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
from ci_hunter.junit import TestDuration, parse_junit_durations


def fetch_junit_durations_from_artifacts(
    *,
    token: str,
    repo: str,
    run_id: int,
    base_url: str = DEFAULT_BASE_URL,
) -> List[TestDuration]:
    artifacts = _list_artifacts(token, repo, run_id, base_url)
    durations: list[TestDuration] = []
    for artifact_id in artifacts:
        zip_bytes = _download_artifact_zip(token, repo, artifact_id, base_url)
        durations.extend(_parse_junit_zip(zip_bytes))
    return durations


def _list_artifacts(token: str, repo: str, run_id: int, base_url: str) -> list[int]:
    response = request_with_retry(
        "GET",
        f"{base_url.rstrip('/')}/repos/{repo}/actions/runs/{run_id}/artifacts",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {token}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return [artifact["id"] for artifact in payload.get("artifacts", [])]


def _download_artifact_zip(
    token: str,
    repo: str,
    artifact_id: int,
    base_url: str,
) -> bytes:
    response = request_with_retry(
        "GET",
        f"{base_url.rstrip('/')}/repos/{repo}/actions/artifacts/{artifact_id}/zip",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {token}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.content


def _parse_junit_zip(zip_bytes: bytes) -> List[TestDuration]:
    durations: list[TestDuration] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zip_file:
        for name in zip_file.namelist():
            if name.endswith("/"):
                continue
            if not name.lower().endswith(".xml"):
                continue
            with zip_file.open(name) as handle:
                text = handle.read().decode("utf-8", errors="replace")
            durations.extend(parse_junit_durations(text))
    return durations

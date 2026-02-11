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
from ci_hunter.steps import StepDuration, parse_step_durations


def fetch_run_step_durations(
    token: str,
    repo: str,
    run_id: int,
    *,
    base_url: str = DEFAULT_BASE_URL,
) -> List[StepDuration]:
    response = request_with_retry(
        "GET",
        f"{base_url.rstrip('/')}/repos/{repo}/actions/runs/{run_id}/logs",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {token}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
        follow_redirects=True,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return _parse_zip_logs(response.content)


def _parse_zip_logs(zip_bytes: bytes) -> List[StepDuration]:
    durations: list[StepDuration] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zip_file:
        for name in zip_file.namelist():
            if name.endswith("/"):
                continue
            with zip_file.open(name) as handle:
                text = handle.read().decode("utf-8", errors="replace")
            job_name = _derive_job_name(name)
            durations.extend(_prefix_step_names(parse_step_durations(text), job_name))
    return durations


def _derive_job_name(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    if name.lower().endswith(".txt"):
        name = name[:-4]
    return name


def _prefix_step_names(steps: List[StepDuration], job_name: str) -> List[StepDuration]:
    if not job_name:
        return steps
    return [
        StepDuration(name=f"{job_name}/{step.name}", duration_seconds=step.duration_seconds)
        for step in steps
    ]

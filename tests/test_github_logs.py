import io
import zipfile

import httpx
import respx

from ci_hunter.github.logs import fetch_run_step_durations
from ci_hunter.github.client import (
    AUTH_SCHEME,
    DEFAULT_BASE_URL,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    HEADER_ACCEPT,
    HEADER_API_VERSION,
    HEADER_AUTHORIZATION,
)
from ci_hunter.steps import StepDuration

REPO = "acme/repo"
RUN_ID = 123
TOKEN = "ghs_token"


def _make_zip_bytes(filename: str, content: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(filename, content)
    return buffer.getvalue()


@respx.mock
def test_fetch_run_step_durations_from_logs_zip():
    log_text = """
2024-01-01T00:00:05.0000000Z  Step: Checkout
2024-01-01T00:00:15.0000000Z  Step: Install deps
2024-01-01T00:00:40.0000000Z  Step: Run tests
"""
    zip_bytes = _make_zip_bytes("logs/1_job.txt", log_text)

    route = respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/actions/runs/{RUN_ID}/logs",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {TOKEN}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
    ).mock(
        return_value=httpx.Response(
            200,
            content=zip_bytes,
            headers={"Content-Type": "application/zip"},
        )
    )

    durations = fetch_run_step_durations(TOKEN, REPO, RUN_ID)

    assert route.called
    assert durations == [
        StepDuration(name="Checkout", duration_seconds=10.0),
        StepDuration(name="Install deps", duration_seconds=25.0),
    ]

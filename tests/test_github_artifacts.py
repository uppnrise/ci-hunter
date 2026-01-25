import io
import zipfile

import httpx
import respx

from ci_hunter.github.artifacts import fetch_junit_durations_from_artifacts
from ci_hunter.github.client import (
    AUTH_SCHEME,
    DEFAULT_BASE_URL,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    HEADER_ACCEPT,
    HEADER_API_VERSION,
    HEADER_AUTHORIZATION,
)
from ci_hunter.junit import TestDuration

REPO = "acme/repo"
RUN_ID = 123
TOKEN = "ghs_token"
ARTIFACT_ID = 987


def _make_zip_bytes(filename: str, content: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(filename, content)
    return buffer.getvalue()


@respx.mock
def test_fetch_junit_durations_from_artifacts():
    list_route = respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/actions/runs/{RUN_ID}/artifacts",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {TOKEN}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "artifacts": [
                    {"id": ARTIFACT_ID, "name": "junit-report"},
                ]
            },
        )
    )

    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="suite" tests="1" time="1.5">
  <testcase classname="pkg.test_a" name="test_one" time="1.5" />
</testsuite>
"""
    zip_bytes = _make_zip_bytes("junit.xml", xml_text)

    download_route = respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/actions/artifacts/{ARTIFACT_ID}/zip",
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

    durations = fetch_junit_durations_from_artifacts(
        token=TOKEN,
        repo=REPO,
        run_id=RUN_ID,
    )

    assert list_route.called
    assert download_route.called
    assert durations == [
        TestDuration(name="pkg.test_a::test_one", duration_seconds=1.5)
    ]

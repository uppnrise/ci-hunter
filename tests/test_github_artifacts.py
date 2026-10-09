import io
import zipfile

import httpx
import pytest
import respx

from ci_hunter.github.artifacts import (
    fetch_junit_durations_from_artifacts,
    fetch_junit_test_outcomes_from_artifacts,
)
from ci_hunter.github.client import (
    AUTH_SCHEME,
    DEFAULT_BASE_URL,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    HEADER_ACCEPT,
    HEADER_API_VERSION,
    HEADER_AUTHORIZATION,
)
from ci_hunter.junit import TEST_OUTCOME_FAILED, TestDuration, TestOutcome

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


@respx.mock
def test_fetch_junit_test_outcomes_from_artifacts():
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
  <testcase classname="pkg.test_a" name="test_one" time="1.5">
    <failure message="boom">trace</failure>
  </testcase>
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

    outcomes = fetch_junit_test_outcomes_from_artifacts(
        token=TOKEN,
        repo=REPO,
        run_id=RUN_ID,
    )

    assert list_route.called
    assert download_route.called
    assert outcomes == [
        TestOutcome(name="pkg.test_a::test_one", outcome=TEST_OUTCOME_FAILED)
    ]


@pytest.mark.parametrize(
    ("fetcher", "expected"),
    [
        (
            fetch_junit_durations_from_artifacts,
            [TestDuration(name="pkg.test_a::test_one", duration_seconds=1.5)],
        ),
        (
            fetch_junit_test_outcomes_from_artifacts,
            [TestOutcome(name="pkg.test_a::test_one", outcome=TEST_OUTCOME_FAILED)],
        ),
    ],
)
@respx.mock
def test_fetch_junit_artifact_follows_download_redirect(fetcher, expected):
    respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/actions/runs/{RUN_ID}/artifacts"
    ).respond(200, json={"artifacts": [{"id": ARTIFACT_ID}]})
    download_url = "https://artifacts.example.test/report.zip"
    respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/actions/artifacts/{ARTIFACT_ID}/zip"
    ).respond(302, headers={"Location": download_url})
    xml_text = (
        '<testsuite><testcase classname="pkg.test_a" name="test_one" time="1.5">'
        '<failure message="boom" /></testcase></testsuite>'
    )
    signed_download = respx.get(download_url).respond(
        200, content=_make_zip_bytes("junit.xml", xml_text)
    )

    assert fetcher(token=TOKEN, repo=REPO, run_id=RUN_ID) == expected
    assert signed_download.called
    assert HEADER_AUTHORIZATION not in signed_download.calls.last.request.headers

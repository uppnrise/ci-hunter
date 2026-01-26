import httpx
import respx

from ci_hunter.github.client import (
    AUTH_SCHEME,
    DEFAULT_BASE_URL,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    HEADER_ACCEPT,
    HEADER_API_VERSION,
    HEADER_AUTHORIZATION,
)
from ci_hunter.github.pr_infer import InferredPullRequest, infer_pr_number

REPO = "acme/repo"
TOKEN = "test-token"
COMMIT_SHA = "abc123"
BRANCH = "feature-1"


@respx.mock
def test_infer_pr_number_from_commit_prefers_most_recent_open():
    route = respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/commits/{COMMIT_SHA}/pulls",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {TOKEN}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "number": 10,
                    "state": "open",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
                {
                    "number": 20,
                    "state": "closed",
                    "updated_at": "2024-01-02T00:00:00Z",
                },
                {
                    "number": 30,
                    "state": "open",
                    "updated_at": "2024-01-03T00:00:00Z",
                },
            ],
        )
    )

    inferred = infer_pr_number(token=TOKEN, repo=REPO, commit=COMMIT_SHA)

    assert route.called
    assert inferred == InferredPullRequest(number=30, multiple_matches=True)


@respx.mock
def test_infer_pr_number_from_branch_uses_head_owner():
    route = respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/pulls",
        params={"state": "open", "head": "acme:feature-1"},
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {TOKEN}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "number": 5,
                    "state": "open",
                    "updated_at": "2024-01-04T00:00:00Z",
                }
            ],
        )
    )

    inferred = infer_pr_number(token=TOKEN, repo=REPO, branch=BRANCH)

    assert route.called
    assert inferred == InferredPullRequest(number=5, multiple_matches=False)

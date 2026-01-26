import httpx
import respx

from ci_hunter.github.comments import post_pr_comment
from ci_hunter.github.client import (
    AUTH_SCHEME,
    DEFAULT_BASE_URL,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    HEADER_ACCEPT,
    HEADER_API_VERSION,
    HEADER_AUTHORIZATION,
)

REPO = "acme/repo"
PR_NUMBER = 42
TOKEN = "ghs_token"
BODY = "Hello from CI Hunter"


@respx.mock
def test_post_pr_comment():
    route = respx.post(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/issues/{PR_NUMBER}/comments",
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {TOKEN}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
        json={"body": BODY},
    ).mock(return_value=httpx.Response(201, json={"id": 1}))

    comment_id = post_pr_comment(TOKEN, REPO, PR_NUMBER, BODY)

    assert route.called
    assert comment_id == 1

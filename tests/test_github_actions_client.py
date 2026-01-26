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
    GitHubActionsClient,
    WorkflowRun,
)

PER_PAGE = 2
REPO = "acme/repo"
TOKEN = "test-token"
RUN_ID = 1
RUN_NUMBER = 42
STATUS_COMPLETED = "completed"
CONCLUSION_SUCCESS = "success"
CREATED_AT = "2024-01-01T00:00:00Z"
UPDATED_AT = "2024-01-01T00:00:10Z"
HEAD_SHA = "abc123"


@respx.mock
def test_list_workflow_runs_parses_response():
    # GitHub App flow should provide an installation token; this client assumes it is supplied.
    client = GitHubActionsClient(token=TOKEN)

    route = respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/actions/runs",
        params={"per_page": PER_PAGE},
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {TOKEN}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "workflow_runs": [
                    {
                        "id": RUN_ID,
                        "run_number": RUN_NUMBER,
                        "status": STATUS_COMPLETED,
                        "conclusion": CONCLUSION_SUCCESS,
                        "created_at": CREATED_AT,
                        "updated_at": UPDATED_AT,
                        "head_sha": HEAD_SHA,
                    }
                ]
            },
        )
    )

    runs = client.list_workflow_runs(REPO, per_page=PER_PAGE)

    assert route.called
    assert runs == [
        WorkflowRun(
            id=RUN_ID,
            run_number=RUN_NUMBER,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
            head_sha=HEAD_SHA,
        )
    ]


@respx.mock
def test_list_workflow_runs_follows_pagination():
    client = GitHubActionsClient(token=TOKEN)

    first_route = respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/actions/runs",
        params={"per_page": PER_PAGE, "page": 1},
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {TOKEN}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "workflow_runs": [
                    {
                        "id": RUN_ID,
                        "run_number": RUN_NUMBER,
                        "status": STATUS_COMPLETED,
                        "conclusion": CONCLUSION_SUCCESS,
                        "created_at": CREATED_AT,
                        "updated_at": UPDATED_AT,
                        "head_sha": HEAD_SHA,
                    }
                ]
            },
            headers={"Link": "<https://api.github.com/resource?page=2>; rel=\"next\""},
        )
    )
    second_route = respx.get(
        f"{DEFAULT_BASE_URL}/repos/{REPO}/actions/runs",
        params={"per_page": PER_PAGE, "page": 2},
        headers={
            HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {TOKEN}",
            HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
            HEADER_API_VERSION: GITHUB_API_VERSION,
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "workflow_runs": [
                    {
                        "id": RUN_ID + 1,
                        "run_number": RUN_NUMBER + 1,
                        "status": STATUS_COMPLETED,
                        "conclusion": CONCLUSION_SUCCESS,
                        "created_at": CREATED_AT,
                        "updated_at": UPDATED_AT,
                        "head_sha": HEAD_SHA,
                    }
                ]
            },
        )
    )

    runs = client.list_workflow_runs(REPO, per_page=PER_PAGE)

    assert first_route.called
    assert second_route.called
    assert [run.id for run in runs] == [RUN_ID, RUN_ID + 1]

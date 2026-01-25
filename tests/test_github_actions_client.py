import httpx
import respx

from ci_hunter.github.client import GitHubActionsClient, WorkflowRun


@respx.mock
def test_list_workflow_runs_parses_response():
    # GitHub App flow should provide an installation token; this client assumes it is supplied.
    client = GitHubActionsClient(token="test-token")

    route = respx.get(
        "https://api.github.com/repos/acme/repo/actions/runs",
        params={"per_page": 2},
        headers={
            "Authorization": "Bearer test-token",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "workflow_runs": [
                    {
                        "id": 1,
                        "run_number": 42,
                        "status": "completed",
                        "conclusion": "success",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:10Z",
                        "head_sha": "abc123",
                    }
                ]
            },
        )
    )

    runs = client.list_workflow_runs("acme/repo", per_page=2)

    assert route.called
    assert runs == [
        WorkflowRun(
            id=1,
            run_number=42,
            status="completed",
            conclusion="success",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:10Z",
            head_sha="abc123",
        )
    ]

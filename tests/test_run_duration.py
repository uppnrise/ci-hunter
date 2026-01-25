from ci_hunter.github.client import WorkflowRun
from ci_hunter.run_duration import run_duration_seconds


def test_run_duration_seconds_from_run():
    run = WorkflowRun(
        id=1,
        run_number=1,
        status="completed",
        conclusion="success",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:10Z",
        head_sha="abc123",
    )

    assert run_duration_seconds(run) == 10.0

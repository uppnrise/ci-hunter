from ci_hunter.github.client import WorkflowRun
from ci_hunter.storage import Storage


def test_save_and_list_workflow_runs():
    storage = Storage(":memory:")

    run = WorkflowRun(
        id=1,
        run_number=42,
        status="completed",
        conclusion="success",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:10Z",
        head_sha="abc123",
    )

    storage.save_workflow_runs("acme/repo", [run])

    assert storage.list_workflow_runs("acme/repo") == [run]


def test_save_workflow_runs_overwrites_existing_entry():
    storage = Storage(":memory:")

    original = WorkflowRun(
        id=1,
        run_number=42,
        status="completed",
        conclusion="success",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:10Z",
        head_sha="abc123",
    )
    updated = WorkflowRun(
        id=1,
        run_number=42,
        status="completed",
        conclusion="failure",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:01:00Z",
        head_sha="def456",
    )

    storage.save_workflow_runs("acme/repo", [original])
    storage.save_workflow_runs("acme/repo", [updated])

    assert storage.list_workflow_runs("acme/repo") == [updated]

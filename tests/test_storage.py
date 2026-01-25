from ci_hunter.github.client import WorkflowRun
from ci_hunter.storage import Storage

REPO = "acme/repo"
RUN_ID = 1
RUN_NUMBER = 42
STATUS_COMPLETED = "completed"
CONCLUSION_SUCCESS = "success"
CONCLUSION_FAILURE = "failure"
CREATED_AT = "2024-01-01T00:00:00Z"
UPDATED_AT = "2024-01-01T00:00:10Z"
UPDATED_AT_LATE = "2024-01-01T00:01:00Z"
HEAD_SHA_ORIGINAL = "abc123"
HEAD_SHA_UPDATED = "def456"


def test_save_and_list_workflow_runs():
    storage = Storage(":memory:")

    run = WorkflowRun(
        id=RUN_ID,
        run_number=RUN_NUMBER,
        status=STATUS_COMPLETED,
        conclusion=CONCLUSION_SUCCESS,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        head_sha=HEAD_SHA_ORIGINAL,
    )

    storage.save_workflow_runs(REPO, [run])

    assert storage.list_workflow_runs(REPO) == [run]


def test_save_workflow_runs_overwrites_existing_entry():
    storage = Storage(":memory:")

    original = WorkflowRun(
        id=RUN_ID,
        run_number=RUN_NUMBER,
        status=STATUS_COMPLETED,
        conclusion=CONCLUSION_SUCCESS,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        head_sha=HEAD_SHA_ORIGINAL,
    )
    updated = WorkflowRun(
        id=RUN_ID,
        run_number=RUN_NUMBER,
        status=STATUS_COMPLETED,
        conclusion=CONCLUSION_FAILURE,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT_LATE,
        head_sha=HEAD_SHA_UPDATED,
    )

    storage.save_workflow_runs(REPO, [original])
    storage.save_workflow_runs(REPO, [updated])

    assert storage.list_workflow_runs(REPO) == [updated]

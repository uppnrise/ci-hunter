from ci_hunter.github.client import WorkflowRun
from ci_hunter.junit import TestDuration
from ci_hunter.steps import StepDuration
from ci_hunter.storage import Storage, StorageConfig, StepDurationSample, TestDurationSample

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
RUN_ID_SECOND = 2
RUN_NUMBER_SECOND = 43
STEP_CHECKOUT = "Checkout"
STEP_TESTS = "Run tests"
DURATION_CHECKOUT_SHORT = 5.0
DURATION_CHECKOUT_LONG = 8.0
DURATION_TESTS = 30.0
TEST_ALPHA = "tests.test_alpha"
TEST_BETA = "tests.test_beta"
DURATION_TEST_ALPHA = 1.25
DURATION_TEST_BETA = 2.5


def test_save_and_list_workflow_runs():
    storage = Storage(StorageConfig(database_url=":memory:"))

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
    storage = Storage(StorageConfig(database_url=":memory:"))

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


def test_save_and_list_step_durations():
    storage = Storage(StorageConfig(database_url=":memory:"))

    first_run = WorkflowRun(
        id=RUN_ID,
        run_number=RUN_NUMBER,
        status=STATUS_COMPLETED,
        conclusion=CONCLUSION_SUCCESS,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        head_sha=HEAD_SHA_ORIGINAL,
    )
    second_run = WorkflowRun(
        id=RUN_ID_SECOND,
        run_number=RUN_NUMBER_SECOND,
        status=STATUS_COMPLETED,
        conclusion=CONCLUSION_SUCCESS,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        head_sha=HEAD_SHA_ORIGINAL,
    )
    storage.save_workflow_runs(REPO, [first_run, second_run])

    storage.save_step_durations(
        REPO,
        RUN_ID,
        [
            StepDuration(name=STEP_CHECKOUT, duration_seconds=DURATION_CHECKOUT_SHORT),
        ],
    )
    storage.save_step_durations(
        REPO,
        RUN_ID_SECOND,
        [
            StepDuration(name=STEP_CHECKOUT, duration_seconds=DURATION_CHECKOUT_LONG),
            StepDuration(name=STEP_TESTS, duration_seconds=DURATION_TESTS),
        ],
    )

    assert storage.list_step_durations(REPO) == [
        StepDurationSample(
            run_number=RUN_NUMBER,
            step_name=STEP_CHECKOUT,
            duration_seconds=DURATION_CHECKOUT_SHORT,
        ),
        StepDurationSample(
            run_number=RUN_NUMBER_SECOND,
            step_name=STEP_CHECKOUT,
            duration_seconds=DURATION_CHECKOUT_LONG,
        ),
        StepDurationSample(
            run_number=RUN_NUMBER_SECOND,
            step_name=STEP_TESTS,
            duration_seconds=DURATION_TESTS,
        ),
    ]


def test_save_and_list_test_durations():
    storage = Storage(StorageConfig(database_url=":memory:"))

    first_run = WorkflowRun(
        id=RUN_ID,
        run_number=RUN_NUMBER,
        status=STATUS_COMPLETED,
        conclusion=CONCLUSION_SUCCESS,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        head_sha=HEAD_SHA_ORIGINAL,
    )
    second_run = WorkflowRun(
        id=RUN_ID_SECOND,
        run_number=RUN_NUMBER_SECOND,
        status=STATUS_COMPLETED,
        conclusion=CONCLUSION_SUCCESS,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        head_sha=HEAD_SHA_ORIGINAL,
    )
    storage.save_workflow_runs(REPO, [first_run, second_run])

    storage.save_test_durations(
        REPO,
        RUN_ID,
        [
            TestDuration(name=TEST_ALPHA, duration_seconds=DURATION_TEST_ALPHA),
        ],
    )
    storage.save_test_durations(
        REPO,
        RUN_ID_SECOND,
        [
            TestDuration(name=TEST_ALPHA, duration_seconds=DURATION_TEST_BETA),
            TestDuration(name=TEST_BETA, duration_seconds=DURATION_TEST_BETA),
        ],
    )

    assert storage.list_test_durations(REPO) == [
        TestDurationSample(
            run_number=RUN_NUMBER,
            test_name=TEST_ALPHA,
            duration_seconds=DURATION_TEST_ALPHA,
        ),
        TestDurationSample(
            run_number=RUN_NUMBER_SECOND,
            test_name=TEST_ALPHA,
            duration_seconds=DURATION_TEST_BETA,
        ),
        TestDurationSample(
            run_number=RUN_NUMBER_SECOND,
            test_name=TEST_BETA,
            duration_seconds=DURATION_TEST_BETA,
        ),
    ]

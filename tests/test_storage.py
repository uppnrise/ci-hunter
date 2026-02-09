import sqlite3
import pytest

from ci_hunter.github.client import WorkflowRun
from ci_hunter.junit import TEST_OUTCOME_FAILED, TestDuration, TestOutcome
from ci_hunter.steps import StepDuration
from ci_hunter.storage import (
    StepDurationSample,
    Storage,
    StorageConfig,
    TestDurationSample,
    TestOutcomeSample,
)

REPO = "acme/repo"
POSTGRES_URL = "postgresql://user:pass@localhost:5432/ci_hunter"
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
TEST_OUTCOME_ALPHA = "tests.test_alpha::test_one"
TEST_OUTCOME_BETA = "tests.test_beta::test_two"


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


def test_storage_enforces_foreign_keys():
    storage = Storage(StorageConfig(database_url=":memory:"))

    with pytest.raises(sqlite3.IntegrityError):
        storage.save_step_durations(
            REPO,
            RUN_ID,
            [StepDuration(name=STEP_CHECKOUT, duration_seconds=DURATION_CHECKOUT_SHORT)],
        )


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


def test_save_and_list_test_outcomes():
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

    storage.save_test_outcomes(
        REPO,
        RUN_ID,
        [
            TestOutcome(name=TEST_OUTCOME_ALPHA, outcome=TEST_OUTCOME_FAILED),
        ],
    )
    storage.save_test_outcomes(
        REPO,
        RUN_ID_SECOND,
        [
            TestOutcome(name=TEST_OUTCOME_ALPHA, outcome="passed"),
            TestOutcome(name=TEST_OUTCOME_BETA, outcome="passed"),
        ],
    )

    assert storage.list_test_outcomes(REPO) == [
        TestOutcomeSample(
            run_number=RUN_NUMBER,
            test_name=TEST_OUTCOME_ALPHA,
            outcome=TEST_OUTCOME_FAILED,
        ),
        TestOutcomeSample(
            run_number=RUN_NUMBER_SECOND,
            test_name=TEST_OUTCOME_ALPHA,
            outcome="passed",
        ),
        TestOutcomeSample(
            run_number=RUN_NUMBER_SECOND,
            test_name=TEST_OUTCOME_BETA,
            outcome="passed",
        ),
    ]


def test_storage_exposes_sqlite_backend_name_for_memory_db():
    storage = Storage(StorageConfig(database_url=":memory:"))

    assert storage.backend_name == "sqlite"


def test_storage_supports_sqlite_memory_url_form():
    storage = Storage(StorageConfig(database_url="sqlite:///:memory:"))

    assert storage.backend_name == "sqlite"


def test_storage_rejects_unknown_database_scheme():
    with pytest.raises(ValueError, match="Unsupported database scheme"):
        Storage(StorageConfig(database_url="mysql://user:pass@localhost:3306/db"))


def test_storage_requires_postgres_driver(monkeypatch):
    import ci_hunter.storage as storage_module

    def fail_import_psycopg():
        raise ModuleNotFoundError("No module named 'psycopg'")

    monkeypatch.setattr(storage_module, "_import_psycopg", fail_import_psycopg)

    with pytest.raises(RuntimeError, match="psycopg"):
        Storage(StorageConfig(database_url=POSTGRES_URL))


def test_storage_does_not_bootstrap_schema_for_postgres(monkeypatch):
    import ci_hunter.storage as storage_module

    observed_queries: list[str] = []

    class FakePostgresBackend:
        name = "postgresql"
        placeholder = "%s"

        def __init__(self, database_url: str) -> None:
            self.database_url = database_url

        def execute(self, query: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
            observed_queries.append(query)
            return []

        def executemany(self, query: str, rows: list[tuple[object, ...]]) -> None:
            return None

        def commit(self) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(storage_module, "_PostgresBackend", FakePostgresBackend)

    storage = Storage(StorageConfig(database_url=POSTGRES_URL))
    storage.close()

    assert observed_queries == []


def test_resolve_sqlite_relative_url_path():
    import ci_hunter.storage as storage_module

    assert storage_module._resolve_sqlite_path("sqlite:///ci_hunter.db") == "ci_hunter.db"


def test_resolve_sqlite_absolute_url_path():
    import ci_hunter.storage as storage_module

    assert storage_module._resolve_sqlite_path("sqlite:////tmp/ci_hunter.db") == "/tmp/ci_hunter.db"

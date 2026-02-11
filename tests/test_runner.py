from dataclasses import dataclass

from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN
from ci_hunter.github.client import WorkflowRun
from ci_hunter.junit import TEST_OUTCOME_FAILED, TestDuration, TestOutcome
from ci_hunter.runner import fetch_store_analyze
from ci_hunter.steps import StepDuration
from ci_hunter.storage import Storage, StorageConfig

REPO = "acme/repo"
TOKEN = "ghs_token"
EXPIRES_AT = "2024-01-01T00:10:00Z"
MIN_DELTA_PCT = 0.2
RUN_ID_BASELINE = 1
RUN_ID_CURRENT = 2
RUN_NUMBER_BASELINE = 1
RUN_NUMBER_CURRENT = 2
STATUS_COMPLETED = "completed"
CONCLUSION_SUCCESS = "success"
CREATED_AT = "2024-01-01T00:00:00Z"
UPDATED_AT_BASELINE = "2024-01-01T00:00:10Z"
UPDATED_AT_CURRENT = "2024-01-01T00:00:20Z"
HEAD_SHA_BASELINE = "abc123"
HEAD_SHA_CURRENT = "def456"
RUN_ID_THIRD = 3
RUN_NUMBER_THIRD = 3
UPDATED_AT_THIRD = "2024-01-01T00:00:30Z"
HEAD_SHA_THIRD = "ghi789"


@dataclass(frozen=True)
class InstallationToken:
    token: str
    expires_at: str


class DummyAuth:
    def get_installation_token(self) -> InstallationToken:
        return InstallationToken(token=TOKEN, expires_at=EXPIRES_AT)


class DummyClient:
    def __init__(self, runs: list[WorkflowRun]) -> None:
        self._runs = runs

    def list_workflow_runs(self, repo: str) -> list[WorkflowRun]:
        assert repo == REPO
        return self._runs


def test_fetch_store_analyze_wires_components():
    storage = Storage(StorageConfig(database_url=":memory:"))
    runs = [
        WorkflowRun(
            id=RUN_ID_BASELINE,
            run_number=RUN_NUMBER_BASELINE,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_BASELINE,
            head_sha=HEAD_SHA_BASELINE,
        ),
        WorkflowRun(
            id=RUN_ID_CURRENT,
            run_number=RUN_NUMBER_CURRENT,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_CURRENT,
            head_sha=HEAD_SHA_CURRENT,
        ),
    ]
    token_used: list[str] = []

    def client_factory(token: str) -> DummyClient:
        token_used.append(token)
        return DummyClient(runs)

    result = fetch_store_analyze(
        auth=DummyAuth(),
        client_factory=client_factory,
        storage=storage,
        repo=REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
    )

    assert token_used == [TOKEN]
    assert len(storage.list_workflow_runs(REPO)) == 2
    assert result.repo == REPO
    assert result.reason is None
    assert len(result.regressions) == 1


def test_fetch_store_analyze_fetches_step_and_test_durations():
    storage = Storage(StorageConfig(database_url=":memory:"))
    runs = [
        WorkflowRun(
            id=RUN_ID_BASELINE,
            run_number=RUN_NUMBER_BASELINE,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_BASELINE,
            head_sha=HEAD_SHA_BASELINE,
        ),
        WorkflowRun(
            id=RUN_ID_CURRENT,
            run_number=RUN_NUMBER_CURRENT,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_CURRENT,
            head_sha=HEAD_SHA_CURRENT,
        ),
        WorkflowRun(
            id=RUN_ID_THIRD,
            run_number=RUN_NUMBER_THIRD,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_THIRD,
            head_sha=HEAD_SHA_THIRD,
        ),
    ]

    def client_factory(token: str) -> DummyClient:
        return DummyClient(runs)

    step_calls: list[int] = []
    test_calls: list[int] = []

    def step_fetcher(token: str, repo: str, run_id: int) -> list[StepDuration]:
        step_calls.append(run_id)
        return [StepDuration(name="Checkout", duration_seconds=float(run_id))]

    def test_fetcher(token: str, repo: str, run_id: int) -> list[TestDuration]:
        test_calls.append(run_id)
        return [TestDuration(name="tests.test_alpha", duration_seconds=float(run_id))]

    result = fetch_store_analyze(
        auth=DummyAuth(),
        client_factory=client_factory,
        storage=storage,
        repo=REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
        step_fetcher=step_fetcher,
        test_fetcher=test_fetcher,
        timings_run_limit=2,
    )

    assert step_calls == [RUN_ID_CURRENT, RUN_ID_THIRD]
    assert test_calls == [RUN_ID_CURRENT, RUN_ID_THIRD]
    assert [sample.run_number for sample in storage.list_step_durations(REPO)] == [
        RUN_NUMBER_CURRENT,
        RUN_NUMBER_THIRD,
    ]
    assert [sample.run_number for sample in storage.list_test_durations(REPO)] == [
        RUN_NUMBER_CURRENT,
        RUN_NUMBER_THIRD,
    ]


def test_fetch_store_analyze_skips_missing_timings():
    storage = Storage(StorageConfig(database_url=":memory:"))
    runs = [
        WorkflowRun(
            id=RUN_ID_BASELINE,
            run_number=RUN_NUMBER_BASELINE,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_BASELINE,
            head_sha=HEAD_SHA_BASELINE,
        ),
        WorkflowRun(
            id=RUN_ID_CURRENT,
            run_number=RUN_NUMBER_CURRENT,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_CURRENT,
            head_sha=HEAD_SHA_CURRENT,
        ),
    ]

    def client_factory(token: str) -> DummyClient:
        return DummyClient(runs)

    def step_fetcher(token: str, repo: str, run_id: int) -> list[StepDuration]:
        if run_id == RUN_ID_BASELINE:
            raise RuntimeError("log missing")
        return [StepDuration(name="Checkout", duration_seconds=5.0)]

    def test_fetcher(token: str, repo: str, run_id: int) -> list[TestDuration]:
        if run_id == RUN_ID_BASELINE:
            raise RuntimeError("artifact missing")
        return [TestDuration(name="tests.test_alpha", duration_seconds=1.0)]

    result = fetch_store_analyze(
        auth=DummyAuth(),
        client_factory=client_factory,
        storage=storage,
        repo=REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
        step_fetcher=step_fetcher,
        test_fetcher=test_fetcher,
    )

    assert [sample.run_number for sample in storage.list_step_durations(REPO)] == [
        RUN_NUMBER_CURRENT,
    ]
    assert [sample.run_number for sample in storage.list_test_durations(REPO)] == [
        RUN_NUMBER_CURRENT,
    ]
    assert result.step_timings_attempted == 2
    assert result.step_timings_failed == 1
    assert result.test_timings_attempted == 2
    assert result.test_timings_failed == 1


def test_fetch_store_analyze_counts_empty_timings_as_missing():
    storage = Storage(StorageConfig(database_url=":memory:"))
    runs = [
        WorkflowRun(
            id=RUN_ID_BASELINE,
            run_number=RUN_NUMBER_BASELINE,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_BASELINE,
            head_sha=HEAD_SHA_BASELINE,
        ),
    ]

    def client_factory(token: str) -> DummyClient:
        return DummyClient(runs)

    def step_fetcher(token: str, repo: str, run_id: int) -> list[StepDuration]:
        return []

    def test_fetcher(token: str, repo: str, run_id: int) -> list[TestDuration]:
        return []

    result = fetch_store_analyze(
        auth=DummyAuth(),
        client_factory=client_factory,
        storage=storage,
        repo=REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
        step_fetcher=step_fetcher,
        test_fetcher=test_fetcher,
    )

    assert result.step_timings_attempted == 1
    assert result.step_timings_failed == 1
    assert result.test_timings_attempted == 1
    assert result.test_timings_failed == 1


def test_fetch_store_analyze_fetches_outcomes_when_only_outcome_fetcher_set():
    storage = Storage(StorageConfig(database_url=":memory:"))
    runs = [
        WorkflowRun(
            id=RUN_ID_BASELINE,
            run_number=RUN_NUMBER_BASELINE,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_BASELINE,
            head_sha=HEAD_SHA_BASELINE,
        ),
        WorkflowRun(
            id=RUN_ID_CURRENT,
            run_number=RUN_NUMBER_CURRENT,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_CURRENT,
            head_sha=HEAD_SHA_CURRENT,
        ),
    ]

    def client_factory(token: str) -> DummyClient:
        return DummyClient(runs)

    outcome_calls: list[int] = []

    def outcome_fetcher(token: str, repo: str, run_id: int) -> list[TestOutcome]:
        outcome_calls.append(run_id)
        return [TestOutcome(name="tests.alpha::test_x", outcome=TEST_OUTCOME_FAILED)]

    fetch_store_analyze(
        auth=DummyAuth(),
        client_factory=client_factory,
        storage=storage,
        repo=REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
        test_outcome_fetcher=outcome_fetcher,
    )

    assert outcome_calls == [RUN_ID_BASELINE, RUN_ID_CURRENT]
    assert [sample.run_number for sample in storage.list_test_outcomes(REPO)] == [
        RUN_NUMBER_BASELINE,
        RUN_NUMBER_CURRENT,
    ]


def test_fetch_store_analyze_supports_keyword_only_fetchers():
    storage = Storage(StorageConfig(database_url=":memory:"))
    runs = [
        WorkflowRun(
            id=RUN_ID_BASELINE,
            run_number=RUN_NUMBER_BASELINE,
            status=STATUS_COMPLETED,
            conclusion=CONCLUSION_SUCCESS,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT_BASELINE,
            head_sha=HEAD_SHA_BASELINE,
        ),
    ]

    def client_factory(token: str) -> DummyClient:
        return DummyClient(runs)

    def keyword_only_step_fetcher(
        *,
        token: str,
        repo: str,
        run_id: int,
    ) -> list[StepDuration]:
        assert token == TOKEN
        assert repo == REPO
        assert run_id == RUN_ID_BASELINE
        return [StepDuration(name="Checkout", duration_seconds=5.0)]

    def keyword_only_test_fetcher(
        *,
        token: str,
        repo: str,
        run_id: int,
    ) -> list[TestDuration]:
        assert token == TOKEN
        assert repo == REPO
        assert run_id == RUN_ID_BASELINE
        return [TestDuration(name="tests.test_alpha", duration_seconds=1.0)]

    def keyword_only_outcome_fetcher(
        *,
        token: str,
        repo: str,
        run_id: int,
    ) -> list[TestOutcome]:
        assert token == TOKEN
        assert repo == REPO
        assert run_id == RUN_ID_BASELINE
        return [TestOutcome(name="tests.alpha::test_x", outcome=TEST_OUTCOME_FAILED)]

    fetch_store_analyze(
        auth=DummyAuth(),
        client_factory=client_factory,
        storage=storage,
        repo=REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
        step_fetcher=keyword_only_step_fetcher,
        test_fetcher=keyword_only_test_fetcher,
        test_outcome_fetcher=keyword_only_outcome_fetcher,
    )

    assert [sample.run_number for sample in storage.list_step_durations(REPO)] == [
        RUN_NUMBER_BASELINE,
    ]
    assert [sample.run_number for sample in storage.list_test_durations(REPO)] == [
        RUN_NUMBER_BASELINE,
    ]
    assert [sample.run_number for sample in storage.list_test_outcomes(REPO)] == [
        RUN_NUMBER_BASELINE,
    ]

from dataclasses import dataclass

from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN
from ci_hunter.github.client import WorkflowRun
from ci_hunter.runner import fetch_store_analyze
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

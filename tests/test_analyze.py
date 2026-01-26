from ci_hunter.analyze import AnalysisResult, analyze_repo_runs
from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN
from ci_hunter.github.client import WorkflowRun
from ci_hunter.junit import TestDuration
from ci_hunter.steps import StepDuration
from ci_hunter.storage import Storage

REPO = "acme/repo"
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


def test_analyze_repo_runs_detects_regression():
    storage = Storage(":memory:")
    storage.save_workflow_runs(
        REPO,
        [
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
        ],
    )

    result = analyze_repo_runs(
        storage,
        REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
    )

    assert result == AnalysisResult(
        repo=REPO,
        regressions=result.regressions,
        reason=None,
        step_regressions=[],
        test_regressions=[],
        step_reason="insufficient_history",
        test_reason="insufficient_history",
        step_data_missing=True,
        test_data_missing=True,
    )
    assert len(result.regressions) == 1
    regression = result.regressions[0]
    assert regression.baseline == 10.0
    assert regression.current == 20.0
    assert regression.delta_pct == 1.0


def test_analyze_repo_runs_detects_step_and_test_regressions():
    storage = Storage(":memory:")
    storage.save_workflow_runs(
        REPO,
        [
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
        ],
    )
    storage.save_step_durations(
        REPO,
        RUN_ID_BASELINE,
        [StepDuration(name="Checkout", duration_seconds=5.0)],
    )
    storage.save_step_durations(
        REPO,
        RUN_ID_CURRENT,
        [StepDuration(name="Checkout", duration_seconds=10.0)],
    )
    storage.save_test_durations(
        REPO,
        RUN_ID_BASELINE,
        [TestDuration(name="tests.test_alpha", duration_seconds=1.0)],
    )
    storage.save_test_durations(
        REPO,
        RUN_ID_CURRENT,
        [TestDuration(name="tests.test_alpha", duration_seconds=2.0)],
    )

    result = analyze_repo_runs(
        storage,
        REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
    )

    assert len(result.step_regressions) == 1
    step_regression = result.step_regressions[0]
    assert step_regression.metric == "Checkout"
    assert step_regression.baseline == 5.0
    assert step_regression.current == 10.0

    assert len(result.test_regressions) == 1
    test_regression = result.test_regressions[0]
    assert test_regression.metric == "tests.test_alpha"
    assert test_regression.baseline == 1.0
    assert test_regression.current == 2.0
    assert result.step_data_missing is False
    assert result.test_data_missing is False

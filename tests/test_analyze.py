from ci_hunter.analyze import AnalysisResult, analyze_repo_runs
from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN, ChangePoint, Flake
from ci_hunter.github.client import WorkflowRun
from ci_hunter.junit import TEST_OUTCOME_FAILED, TestDuration, TestOutcome
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
        step_timings_attempted=None,
        step_timings_failed=None,
        test_timings_attempted=None,
        test_timings_failed=None,
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
    assert result.step_timings_attempted is None
    assert result.step_timings_failed is None
    assert result.test_timings_attempted is None
    assert result.test_timings_failed is None


def test_analyze_repo_runs_step_reason_none_when_no_regression():
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
        [StepDuration(name="Checkout", duration_seconds=5.4)],
    )

    result = analyze_repo_runs(
        storage,
        REPO,
        min_delta_pct=1.0,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
    )

    assert result.step_regressions == []
    assert result.step_reason is None


def test_analyze_repo_runs_detects_flaky_tests():
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
            WorkflowRun(
                id=3,
                run_number=3,
                status=STATUS_COMPLETED,
                conclusion=CONCLUSION_SUCCESS,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT_CURRENT,
                head_sha="ghi789",
            ),
            WorkflowRun(
                id=4,
                run_number=4,
                status=STATUS_COMPLETED,
                conclusion=CONCLUSION_SUCCESS,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT_CURRENT,
                head_sha="jkl012",
            ),
            WorkflowRun(
                id=5,
                run_number=5,
                status=STATUS_COMPLETED,
                conclusion=CONCLUSION_SUCCESS,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT_CURRENT,
                head_sha="mno345",
            ),
        ],
    )
    test_name = "tests.alpha::test_x"
    storage.save_test_outcomes(
        REPO,
        RUN_ID_BASELINE,
        [TestOutcome(name=test_name, outcome=TEST_OUTCOME_FAILED)],
    )
    storage.save_test_outcomes(
        REPO,
        RUN_ID_CURRENT,
        [TestOutcome(name=test_name, outcome="passed")],
    )
    storage.save_test_outcomes(
        REPO,
        3,
        [TestOutcome(name=test_name, outcome=TEST_OUTCOME_FAILED)],
    )
    storage.save_test_outcomes(
        REPO,
        4,
        [TestOutcome(name=test_name, outcome="passed")],
    )
    storage.save_test_outcomes(
        REPO,
        5,
        [TestOutcome(name=test_name, outcome="passed")],
    )

    result = analyze_repo_runs(
        storage,
        REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
    )

    assert result.flakes == [
        Flake(
            test_name=test_name,
            fail_rate=0.4,
            failures=2,
            total_runs=5,
        )
    ]


def test_analyze_repo_runs_flake_detection_respects_history_window():
    storage = Storage(":memory:")
    test_name = "tests.alpha::test_window"
    runs = []
    for run_id in range(1, 7):
        runs.append(
            WorkflowRun(
                id=run_id,
                run_number=run_id,
                status=STATUS_COMPLETED,
                conclusion=CONCLUSION_SUCCESS,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT_CURRENT,
                head_sha=f"sha-{run_id}",
            )
        )
    storage.save_workflow_runs(REPO, runs)

    outcomes = [
        TEST_OUTCOME_FAILED,
        TEST_OUTCOME_FAILED,
        "passed",
        "passed",
        "passed",
        "passed",
    ]
    for run_id, outcome in enumerate(outcomes, start=1):
        storage.save_test_outcomes(
            REPO,
            run_id,
            [TestOutcome(name=test_name, outcome=outcome)],
        )

    result = analyze_repo_runs(
        storage,
        REPO,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
        history_window=5,
    )

    assert result.flakes == []


def test_analyze_repo_runs_detects_step_and_test_change_points():
    storage = Storage(":memory:")
    runs = []
    for run_id in range(1, 7):
        runs.append(
            WorkflowRun(
                id=run_id,
                run_number=run_id,
                status=STATUS_COMPLETED,
                conclusion=CONCLUSION_SUCCESS,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT_CURRENT,
                head_sha=f"sha-{run_id}",
            )
        )
    storage.save_workflow_runs(REPO, runs)

    for run_id in range(1, 4):
        storage.save_step_durations(
            REPO,
            run_id,
            [StepDuration(name="Checkout", duration_seconds=10.0)],
        )
        storage.save_test_durations(
            REPO,
            run_id,
            [TestDuration(name="tests.alpha", duration_seconds=2.0)],
        )
    for run_id in range(4, 7):
        storage.save_step_durations(
            REPO,
            run_id,
            [StepDuration(name="Checkout", duration_seconds=20.0)],
        )
        storage.save_test_durations(
            REPO,
            run_id,
            [TestDuration(name="tests.alpha", duration_seconds=4.0)],
        )

    result = analyze_repo_runs(
        storage,
        REPO,
        min_delta_pct=0.5,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
    )

    assert result.step_change_points == [
        ChangePoint(
            metric="Checkout",
            baseline=10.0,
            recent=20.0,
            delta_pct=1.0,
            window_size=3,
        )
    ]
    assert result.test_change_points == [
        ChangePoint(
            metric="tests.alpha",
            baseline=2.0,
            recent=4.0,
            delta_pct=1.0,
            window_size=3,
        )
    ]

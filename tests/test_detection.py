import pytest

from ci_hunter.detection import (
    BASELINE_STRATEGY_MEDIAN,
    BASELINE_STRATEGY_TRIMMED_MEAN,
    DetectionResult,
    Flake,
    METRIC_RUN_DURATION_SECONDS,
    REASON_INSUFFICIENT_HISTORY,
    REASON_NON_POSITIVE_BASELINE,
    Regression,
    detect_test_flakes,
    detect_run_duration_regressions,
)

DURATION_BASELINE = 10.0
DURATION_OUTLIER = 100.0
DURATION_CURRENT = 15.0
DURATION_CURRENT_SMALL = 12.0
MIN_DELTA_PCT = 0.2
DELTA_PCT = 0.5
DELTA_PCT_OUTLIER = 9.0
DELTA_PCT_SMALL = 0.2
TRIM_RATIO = 0.25


class _OutcomeSample:
    def __init__(self, run_number: int, test_name: str, outcome: str) -> None:
        self.run_number = run_number
        self.test_name = test_name
        self.outcome = outcome


def test_detects_run_duration_regression():
    durations = [DURATION_BASELINE, DURATION_BASELINE, DURATION_BASELINE, DURATION_CURRENT]

    result = detect_run_duration_regressions(
        durations,
        min_delta_pct=MIN_DELTA_PCT,
    )

    assert result == DetectionResult(
        regressions=[
            Regression(
                metric=METRIC_RUN_DURATION_SECONDS,
                baseline=DURATION_BASELINE,
                current=DURATION_CURRENT,
                delta_pct=DELTA_PCT,
            )
        ],
        reason=None,
    )


def test_median_baseline_ignores_outlier():
    durations = [DURATION_BASELINE, DURATION_BASELINE, DURATION_BASELINE, DURATION_OUTLIER]

    result = detect_run_duration_regressions(
        durations,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_MEDIAN,
    )

    assert result.regressions == [
        Regression(
            metric=METRIC_RUN_DURATION_SECONDS,
            baseline=DURATION_BASELINE,
            current=DURATION_OUTLIER,
            delta_pct=DELTA_PCT_OUTLIER,
        )
    ]
    assert result.reason is None


def test_trimmed_mean_baseline_removes_extremes():
    durations = [
        DURATION_BASELINE,
        DURATION_BASELINE,
        DURATION_BASELINE,
        DURATION_OUTLIER,
        DURATION_CURRENT_SMALL,
    ]

    result = detect_run_duration_regressions(
        durations,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy=BASELINE_STRATEGY_TRIMMED_MEAN,
        trim_ratio=TRIM_RATIO,
    )

    assert result.regressions == [
        Regression(
            metric=METRIC_RUN_DURATION_SECONDS,
            baseline=DURATION_BASELINE,
            current=DURATION_CURRENT_SMALL,
            delta_pct=DELTA_PCT_SMALL,
        )
    ]
    assert result.reason is None


def test_returns_reason_when_insufficient_history():
    result = detect_run_duration_regressions(
        [5.0],
        min_delta_pct=MIN_DELTA_PCT,
    )

    assert result == DetectionResult(regressions=[], reason=REASON_INSUFFICIENT_HISTORY)


def test_returns_reason_when_baseline_non_positive():
    result = detect_run_duration_regressions(
        [0.0, 0.0],
        min_delta_pct=MIN_DELTA_PCT,
    )

    assert result == DetectionResult(regressions=[], reason=REASON_NON_POSITIVE_BASELINE)


def test_respects_min_history():
    result = detect_run_duration_regressions(
        [DURATION_BASELINE, DURATION_BASELINE, DURATION_CURRENT],
        min_delta_pct=MIN_DELTA_PCT,
        min_history=3,
    )

    assert result == DetectionResult(regressions=[], reason=REASON_INSUFFICIENT_HISTORY)


def test_history_window_limits_baseline():
    durations = [100.0, 100.0, DURATION_BASELINE, DURATION_BASELINE, DURATION_CURRENT]

    result = detect_run_duration_regressions(
        durations,
        min_delta_pct=MIN_DELTA_PCT,
        baseline_strategy="mean",
        history_window=2,
    )

    assert result.regressions == [
        Regression(
            metric=METRIC_RUN_DURATION_SECONDS,
            baseline=DURATION_BASELINE,
            current=DURATION_CURRENT,
            delta_pct=DELTA_PCT,
        )
    ]
    assert result.reason is None


def test_min_history_must_be_positive():
    with pytest.raises(ValueError):
        detect_run_duration_regressions(
            [DURATION_BASELINE, DURATION_CURRENT],
            min_delta_pct=MIN_DELTA_PCT,
            min_history=0,
        )


def test_history_window_must_be_positive_when_set():
    with pytest.raises(ValueError):
        detect_run_duration_regressions(
            [DURATION_BASELINE, DURATION_CURRENT],
            min_delta_pct=MIN_DELTA_PCT,
            history_window=0,
        )


def test_detect_test_flakes_flags_intermittent_failures():
    samples = [
        _OutcomeSample(1, "tests.alpha::test_x", "failed"),
        _OutcomeSample(2, "tests.alpha::test_x", "passed"),
        _OutcomeSample(3, "tests.alpha::test_x", "failed"),
        _OutcomeSample(4, "tests.alpha::test_x", "passed"),
        _OutcomeSample(5, "tests.alpha::test_x", "passed"),
    ]

    flakes = detect_test_flakes(
        samples,
        min_fail_rate=0.3,
        min_failures=2,
        min_runs=5,
    )

    assert flakes == [
        Flake(
            test_name="tests.alpha::test_x",
            fail_rate=0.4,
            failures=2,
            total_runs=5,
        )
    ]


def test_detect_test_flakes_ignores_consistently_failing_tests():
    samples = [
        _OutcomeSample(1, "tests.alpha::test_x", "failed"),
        _OutcomeSample(2, "tests.alpha::test_x", "failed"),
        _OutcomeSample(3, "tests.alpha::test_x", "failed"),
        _OutcomeSample(4, "tests.alpha::test_x", "failed"),
        _OutcomeSample(5, "tests.alpha::test_x", "failed"),
    ]

    flakes = detect_test_flakes(
        samples,
        min_fail_rate=0.3,
        min_failures=2,
        min_runs=5,
    )

    assert flakes == []

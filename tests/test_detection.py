from ci_hunter.detection import (
    BASELINE_STRATEGY_MEDIAN,
    BASELINE_STRATEGY_TRIMMED_MEAN,
    DetectionResult,
    METRIC_RUN_DURATION_SECONDS,
    REASON_INSUFFICIENT_HISTORY,
    REASON_NON_POSITIVE_BASELINE,
    Regression,
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

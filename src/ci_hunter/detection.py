from __future__ import annotations

from dataclasses import dataclass
import statistics
from typing import Iterable, List, Optional

from ci_hunter.junit import TEST_OUTCOME_FAILED, TEST_OUTCOME_PASSED


@dataclass(frozen=True)
class Regression:
    metric: str
    baseline: float
    current: float
    delta_pct: float


METRIC_RUN_DURATION_SECONDS = "run_duration_seconds"
REASON_INSUFFICIENT_HISTORY = "insufficient_history"
REASON_NON_POSITIVE_BASELINE = "non_positive_baseline"
BASELINE_STRATEGY_MEAN = "mean"
BASELINE_STRATEGY_MEDIAN = "median"
BASELINE_STRATEGY_TRIMMED_MEAN = "trimmed_mean"
DEFAULT_BASELINE_STRATEGY = BASELINE_STRATEGY_MEDIAN
DEFAULT_TRIM_RATIO = 0.1


@dataclass(frozen=True)
class DetectionResult:
    regressions: List[Regression]
    reason: Optional[str]


@dataclass(frozen=True)
class Flake:
    test_name: str
    fail_rate: float
    failures: int
    total_runs: int


@dataclass(frozen=True)
class ChangePoint:
    metric: str
    baseline: float
    recent: float
    delta_pct: float
    window_size: int


def detect_run_duration_regressions(
    durations: Iterable[float],
    *,
    min_delta_pct: float,
    baseline_strategy: str = DEFAULT_BASELINE_STRATEGY,
    trim_ratio: float = DEFAULT_TRIM_RATIO,
    min_history: int = 1,
    history_window: int | None = None,
) -> DetectionResult:
    if min_history < 1:
        raise ValueError("min_history must be >= 1")
    if history_window is not None and history_window < 1:
        raise ValueError("history_window must be >= 1 when set")
    values = list(durations)
    if len(values) < 2:
        return DetectionResult(regressions=[], reason=REASON_INSUFFICIENT_HISTORY)

    baseline_values = values[:-1]
    if history_window is not None:
        baseline_values = baseline_values[-history_window:]
    if len(baseline_values) < min_history:
        return DetectionResult(regressions=[], reason=REASON_INSUFFICIENT_HISTORY)
    baseline = _compute_baseline(baseline_values, baseline_strategy, trim_ratio)
    if baseline is None:
        return DetectionResult(regressions=[], reason=REASON_INSUFFICIENT_HISTORY)

    current = values[-1]
    if baseline <= 0:
        return DetectionResult(regressions=[], reason=REASON_NON_POSITIVE_BASELINE)

    delta_pct = (current - baseline) / baseline
    if delta_pct < min_delta_pct:
        return DetectionResult(regressions=[], reason=None)

    return DetectionResult(
        regressions=[
            Regression(
                metric=METRIC_RUN_DURATION_SECONDS,
                baseline=baseline,
                current=current,
                delta_pct=delta_pct,
            )
        ],
        reason=None,
    )


def _compute_baseline(
    values: List[float],
    strategy: str,
    trim_ratio: float,
) -> Optional[float]:
    if not values:
        return None

    if strategy == BASELINE_STRATEGY_MEAN:
        return sum(values) / len(values)
    if strategy == BASELINE_STRATEGY_MEDIAN:
        return statistics.median(values)
    if strategy == BASELINE_STRATEGY_TRIMMED_MEAN:
        if not 0 <= trim_ratio < 0.5:
            raise ValueError("trim_ratio must be in [0, 0.5)")
        trim_count = int(len(values) * trim_ratio)
        if len(values) - 2 * trim_count <= 0:
            return None
        trimmed = sorted(values)[trim_count : len(values) - trim_count]
        return sum(trimmed) / len(trimmed)

    raise ValueError(f"Unknown baseline_strategy: {strategy}")


def detect_test_flakes(
    samples: Iterable[object],
    *,
    min_fail_rate: float = 0.2,
    min_failures: int = 2,
    min_runs: int = 5,
    history_window: int | None = None,
) -> list[Flake]:
    if not 0 <= min_fail_rate <= 1:
        raise ValueError("min_fail_rate must be in [0, 1]")
    if min_failures < 1:
        raise ValueError("min_failures must be >= 1")
    if min_runs < 1:
        raise ValueError("min_runs must be >= 1")
    if history_window is not None and history_window < 1:
        raise ValueError("history_window must be >= 1 when set")

    by_name: dict[str, list[tuple[int, str]]] = {}
    for sample in samples:
        test_name = getattr(sample, "test_name")
        run_number = getattr(sample, "run_number")
        outcome = str(getattr(sample, "outcome")).strip().lower()
        by_name.setdefault(test_name, []).append((run_number, outcome))

    flakes: list[Flake] = []
    for test_name, entries in by_name.items():
        entries.sort(key=lambda item: item[0])
        outcomes = [outcome for _, outcome in entries]
        if history_window is not None:
            outcomes = outcomes[-history_window:]

        considered = [
            outcome
            for outcome in outcomes
            if outcome in {TEST_OUTCOME_PASSED, TEST_OUTCOME_FAILED}
        ]
        if len(considered) < min_runs:
            continue

        failures = sum(1 for outcome in considered if outcome == TEST_OUTCOME_FAILED)
        passes = len(considered) - failures
        if failures < min_failures:
            continue
        if passes == 0:
            # A consistently failing test is deterministic, not flaky.
            continue

        fail_rate = failures / len(considered)
        if fail_rate < min_fail_rate:
            continue
        flakes.append(
            Flake(
                test_name=test_name,
                fail_rate=fail_rate,
                failures=failures,
                total_runs=len(considered),
            )
        )

    flakes.sort(key=lambda flake: (-flake.fail_rate, -flake.failures, flake.test_name))
    return flakes


def detect_run_duration_change_points(
    durations: Iterable[float],
    *,
    min_delta_pct: float,
    window_size: int = 3,
    history_window: int | None = None,
) -> list[ChangePoint]:
    if window_size < 1:
        raise ValueError("window_size must be >= 1")
    if history_window is not None and history_window < 1:
        raise ValueError("history_window must be >= 1 when set")

    values = list(durations)
    if history_window is not None:
        values = values[-history_window:]
    if len(values) < window_size * 2:
        return []

    baseline_window = values[-2 * window_size : -window_size]
    recent_window = values[-window_size:]
    baseline = sum(baseline_window) / len(baseline_window)
    if baseline <= 0:
        return []
    recent = sum(recent_window) / len(recent_window)
    delta_pct = (recent - baseline) / baseline
    if delta_pct < min_delta_pct:
        return []

    return [
        ChangePoint(
            metric=METRIC_RUN_DURATION_SECONDS,
            baseline=baseline,
            recent=recent,
            delta_pct=delta_pct,
            window_size=window_size,
        )
    ]

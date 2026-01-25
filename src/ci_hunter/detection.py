from __future__ import annotations

from dataclasses import dataclass
import statistics
from typing import Iterable, List, Optional


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


def detect_run_duration_regressions(
    durations: Iterable[float],
    *,
    min_delta_pct: float,
    baseline_strategy: str = DEFAULT_BASELINE_STRATEGY,
    trim_ratio: float = DEFAULT_TRIM_RATIO,
) -> DetectionResult:
    values = list(durations)
    if len(values) < 2:
        return DetectionResult(regressions=[], reason=REASON_INSUFFICIENT_HISTORY)

    baseline_values = values[:-1]
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

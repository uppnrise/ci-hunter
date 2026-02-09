from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ci_hunter.detection import (
    BASELINE_STRATEGY_MEDIAN,
    BASELINE_STRATEGY_MEAN,
    BASELINE_STRATEGY_TRIMMED_MEAN,
    ChangePoint,
    Flake,
    Regression,
    REASON_INSUFFICIENT_HISTORY,
    detect_run_duration_change_points,
    detect_test_flakes,
    detect_run_duration_regressions,
)
from ci_hunter.storage import Storage
from ci_hunter.time_utils import parse_iso_datetime


@dataclass(frozen=True)
class AnalysisResult:
    repo: str
    regressions: list[Regression]
    reason: Optional[str]
    step_regressions: list[Regression]
    test_regressions: list[Regression]
    step_reason: Optional[str]
    test_reason: Optional[str]
    step_timings_attempted: Optional[int]
    step_timings_failed: Optional[int]
    test_timings_attempted: Optional[int]
    test_timings_failed: Optional[int]
    step_change_points: list[ChangePoint] = field(default_factory=list)
    test_change_points: list[ChangePoint] = field(default_factory=list)
    flakes: list[Flake] = field(default_factory=list)


def analyze_repo_runs(
    storage: Storage,
    repo: str,
    *,
    min_delta_pct: float,
    baseline_strategy: str = BASELINE_STRATEGY_MEDIAN,
    min_history: int = 1,
    history_window: int | None = None,
) -> AnalysisResult:
    _validate_baseline_strategy(baseline_strategy)
    runs = storage.list_workflow_runs(repo)
    durations = []
    for run in runs:
        durations.append(_duration_seconds(run.created_at, run.updated_at))

    detection = detect_run_duration_regressions(
        durations,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
        min_history=min_history,
        history_window=history_window,
    )
    step_samples = storage.list_step_durations(repo)
    test_samples = storage.list_test_durations(repo)
    test_outcome_samples = storage.list_test_outcomes(repo)
    step_regressions = _detect_named_regressions(
        step_samples,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
        min_history=min_history,
        history_window=history_window,
    )
    test_regressions = _detect_named_regressions(
        test_samples,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
        min_history=min_history,
        history_window=history_window,
    )
    step_change_points = _detect_named_change_points(
        step_samples,
        min_delta_pct=min_delta_pct,
        history_window=history_window,
    )
    test_change_points = _detect_named_change_points(
        test_samples,
        min_delta_pct=min_delta_pct,
        history_window=history_window,
    )
    flakes = detect_test_flakes(
        test_outcome_samples,
        history_window=history_window,
    )
    return AnalysisResult(
        repo=repo,
        regressions=detection.regressions,
        reason=detection.reason,
        step_regressions=step_regressions.regressions,
        test_regressions=test_regressions.regressions,
        step_reason=step_regressions.reason,
        test_reason=test_regressions.reason,
        step_timings_attempted=None,
        step_timings_failed=None,
        test_timings_attempted=None,
        test_timings_failed=None,
        step_change_points=step_change_points,
        test_change_points=test_change_points,
        flakes=flakes,
    )


def _duration_seconds(start: str, end: str) -> float:
    start_dt = parse_iso_datetime(start)
    end_dt = parse_iso_datetime(end)
    return (end_dt - start_dt).total_seconds()


def _validate_baseline_strategy(strategy: str) -> None:
    allowed = {
        BASELINE_STRATEGY_MEDIAN,
        BASELINE_STRATEGY_MEAN,
        BASELINE_STRATEGY_TRIMMED_MEAN,
    }
    if strategy not in allowed:
        raise ValueError(f"Unknown baseline_strategy: {strategy}")


@dataclass(frozen=True)
class _NamedRegressionResult:
    regressions: list[Regression]
    reason: Optional[str]


def _detect_named_regressions(
    samples: list[object],
    *,
    min_delta_pct: float,
    baseline_strategy: str,
    min_history: int,
    history_window: int | None,
) -> _NamedRegressionResult:
    if not samples:
        return _NamedRegressionResult(regressions=[], reason=REASON_INSUFFICIENT_HISTORY)

    by_name: dict[str, list[tuple[int, float]]] = {}
    for sample in samples:
        run_number = getattr(sample, "run_number")
        name = getattr(sample, "step_name", None)
        if name is None:
            name = getattr(sample, "test_name")
        duration = getattr(sample, "duration_seconds")
        by_name.setdefault(name, []).append((run_number, duration))

    regressions: list[Regression] = []
    for name, entries in by_name.items():
        entries.sort(key=lambda item: item[0])
        durations = [duration for _, duration in entries]
        detection = detect_run_duration_regressions(
            durations,
            min_delta_pct=min_delta_pct,
            baseline_strategy=baseline_strategy,
            min_history=min_history,
            history_window=history_window,
        )
        for regression in detection.regressions:
            regressions.append(
                Regression(
                    metric=name,
                    baseline=regression.baseline,
                    current=regression.current,
                    delta_pct=regression.delta_pct,
                )
            )

    if regressions:
        return _NamedRegressionResult(regressions=regressions, reason=None)
    has_history = False
    for entries in by_name.values():
        baseline_len = len(entries) - 1
        if history_window is not None:
            baseline_len = min(baseline_len, history_window)
        if baseline_len >= min_history:
            has_history = True
            break
    if has_history:
        return _NamedRegressionResult(regressions=[], reason=None)
    return _NamedRegressionResult(regressions=[], reason=REASON_INSUFFICIENT_HISTORY)


def _detect_named_change_points(
    samples: list[object],
    *,
    min_delta_pct: float,
    history_window: int | None,
) -> list[ChangePoint]:
    by_name: dict[str, list[tuple[int, float]]] = {}
    for sample in samples:
        run_number = getattr(sample, "run_number")
        name = getattr(sample, "step_name", None)
        if name is None:
            name = getattr(sample, "test_name")
        duration = getattr(sample, "duration_seconds")
        by_name.setdefault(name, []).append((run_number, duration))

    change_points: list[ChangePoint] = []
    for name, entries in by_name.items():
        entries.sort(key=lambda item: item[0])
        durations = [duration for _, duration in entries]
        detected = detect_run_duration_change_points(
            durations,
            min_delta_pct=min_delta_pct,
            history_window=history_window,
        )
        for point in detected:
            change_points.append(
                ChangePoint(
                    metric=name,
                    baseline=point.baseline,
                    recent=point.recent,
                    delta_pct=point.delta_pct,
                    window_size=point.window_size,
                )
            )
    return change_points

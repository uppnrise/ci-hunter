from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ci_hunter.detection import (
    BASELINE_STRATEGY_MEDIAN,
    BASELINE_STRATEGY_MEAN,
    BASELINE_STRATEGY_TRIMMED_MEAN,
    Regression,
    REASON_INSUFFICIENT_HISTORY,
    detect_run_duration_regressions,
)
from ci_hunter.storage import Storage


@dataclass(frozen=True)
class AnalysisResult:
    repo: str
    regressions: list[Regression]
    reason: Optional[str]
    step_regressions: list[Regression]
    test_regressions: list[Regression]
    step_reason: Optional[str]
    test_reason: Optional[str]
    step_data_missing: bool
    test_data_missing: bool


def analyze_repo_runs(
    storage: Storage,
    repo: str,
    *,
    min_delta_pct: float,
    baseline_strategy: str = BASELINE_STRATEGY_MEDIAN,
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
    )
    step_samples = storage.list_step_durations(repo)
    test_samples = storage.list_test_durations(repo)
    step_regressions = _detect_named_regressions(
        step_samples,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
    )
    test_regressions = _detect_named_regressions(
        test_samples,
        min_delta_pct=min_delta_pct,
        baseline_strategy=baseline_strategy,
    )
    return AnalysisResult(
        repo=repo,
        regressions=detection.regressions,
        reason=detection.reason,
        step_regressions=step_regressions.regressions,
        test_regressions=test_regressions.regressions,
        step_reason=step_regressions.reason,
        test_reason=test_regressions.reason,
        step_data_missing=len(step_samples) == 0,
        test_data_missing=len(test_samples) == 0,
    )


def _duration_seconds(start: str, end: str) -> float:
    start_dt = _parse_iso_datetime(start)
    end_dt = _parse_iso_datetime(end)
    return (end_dt - start_dt).total_seconds()


def _parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _validate_baseline_strategy(strategy: str) -> None:
    allowed = {
        BASELINE_STRATEGY_MEDIAN,
        BASELINE_STRATEGY_MEAN,
        BASELINE_STRATEGY_TRIMMED_MEAN,
    }
    if strategy not in allowed:
        raise ValueError(f"Unknown baseline_strategy: {strategy}")


@dataclass(frozen=True)
class _NamedSample:
    name: str
    duration_seconds: float


@dataclass(frozen=True)
class _NamedRegressionResult:
    regressions: list[Regression]
    reason: Optional[str]


def _detect_named_regressions(
    samples: list[object],
    *,
    min_delta_pct: float,
    baseline_strategy: str,
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

    reason = None if regressions else REASON_INSUFFICIENT_HISTORY
    return _NamedRegressionResult(regressions=regressions, reason=reason)

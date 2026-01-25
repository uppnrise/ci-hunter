from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ci_hunter.detection import (
    BASELINE_STRATEGY_MEDIAN,
    BASELINE_STRATEGY_MEAN,
    BASELINE_STRATEGY_TRIMMED_MEAN,
    Regression,
    detect_run_duration_regressions,
)
from ci_hunter.storage import Storage


@dataclass(frozen=True)
class AnalysisResult:
    repo: str
    regressions: list[Regression]
    reason: Optional[str]


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
    return AnalysisResult(
        repo=repo,
        regressions=detection.regressions,
        reason=detection.reason,
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

from __future__ import annotations

from datetime import datetime, timezone

from ci_hunter.github.client import WorkflowRun


def run_duration_seconds(run: WorkflowRun) -> float:
    start_dt = _parse_iso_datetime(run.created_at)
    end_dt = _parse_iso_datetime(run.updated_at)
    return (end_dt - start_dt).total_seconds()


def _parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed

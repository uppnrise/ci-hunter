from __future__ import annotations

from ci_hunter.github.client import WorkflowRun
from ci_hunter.time_utils import parse_iso_datetime


def run_duration_seconds(run: WorkflowRun) -> float:
    start_dt = parse_iso_datetime(run.created_at)
    end_dt = parse_iso_datetime(run.updated_at)
    return (end_dt - start_dt).total_seconds()

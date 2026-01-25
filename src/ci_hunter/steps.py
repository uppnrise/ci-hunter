from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import List


@dataclass(frozen=True)
class StepDuration:
    name: str
    duration_seconds: float


STEP_PREFIX = "Step:"
TIMESTAMP_PATTERN = re.compile(r"^(?P<ts>\S+)\s+(?P<rest>.+)$")
MAX_FRACTIONAL_SECONDS = 6


def parse_step_durations(log_text: str) -> List[StepDuration]:
    """Parse GitHub Actions log lines and return per-step durations.

    This expects log lines that begin with an ISO-8601 timestamp and include
    the substring "Step:" followed by the step name.
    """
    steps: list[tuple[str, datetime]] = []
    for line in log_text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = TIMESTAMP_PATTERN.match(line)
        if not match:
            continue
        timestamp = _parse_iso_datetime(match.group("ts"))
        rest = match.group("rest")
        if STEP_PREFIX in rest:
            name = rest.split(STEP_PREFIX, 1)[1].strip()
            steps.append((name, timestamp))

    durations: list[StepDuration] = []
    for (name, start), (_, end) in zip(steps, steps[1:]):
        durations.append(
            StepDuration(
                name=name,
                duration_seconds=(end - start).total_seconds(),
            )
        )
    return durations


def _parse_iso_datetime(value: str) -> datetime:
    normalized = _normalize_iso_timestamp(value)
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize_iso_timestamp(value: str) -> str:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    if "T" not in value or "." not in value:
        return value

    date_part, time_part = value.split("T", 1)
    sign = ""
    offset = ""

    if "+" in time_part:
        time_main, offset = time_part.split("+", 1)
        sign = "+"
    elif "-" in time_part[1:]:
        time_main, offset = time_part.rsplit("-", 1)
        sign = "-"
    else:
        time_main = time_part

    if "." in time_main:
        hms, frac = time_main.split(".", 1)
        time_main = f"{hms}.{frac[:MAX_FRACTIONAL_SECONDS]}"

    suffix = f"{sign}{offset}" if sign else ""
    return f"{date_part}T{time_main}{suffix}"

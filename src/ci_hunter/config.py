from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class AppConfig:
    repo: Optional[str] = None
    min_delta_pct: Optional[float] = None
    baseline_strategy: Optional[str] = None
    db: Optional[str] = None
    timings_run_limit: Optional[int] = None
    format: Optional[str] = None
    dry_run: Optional[bool] = None
    pr_number: Optional[int] = None
    commit: Optional[str] = None
    branch: Optional[str] = None


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    data = _load_yaml(config_path)
    return AppConfig(
        repo=data.get("repo"),
        min_delta_pct=_get_float(data, "min_delta_pct"),
        baseline_strategy=data.get("baseline_strategy"),
        db=data.get("db"),
        timings_run_limit=_get_int(data, "timings_run_limit"),
        format=data.get("format"),
        dry_run=_get_bool(data, "dry_run"),
        pr_number=_get_int(data, "pr_number"),
        commit=data.get("commit"),
        branch=data.get("branch"),
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        return {}
    data = yaml.safe_load(content)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Config YAML must be a mapping")
    return data


def _get_float(data: dict[str, Any], key: str) -> Optional[float]:
    if key not in data or data[key] is None:
        return None
    return float(data[key])


def _get_int(data: dict[str, Any], key: str) -> Optional[int]:
    if key not in data or data[key] is None:
        return None
    return int(data[key])


def _get_bool(data: dict[str, Any], key: str) -> Optional[bool]:
    if key not in data or data[key] is None:
        return None
    value = data[key]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "on"}:
            return True
        if normalized in {"false", "no", "0", "off"}:
            return False
    raise ValueError(f"Invalid boolean value for {key}: {value!r}")

from __future__ import annotations

import os
from typing import Mapping


ENV_ALEMBIC_URL = "CI_HUNTER_ALEMBIC_URL"


def resolve_alembic_url(default_url: str, env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    raw_value = source.get(ENV_ALEMBIC_URL)
    if raw_value is None:
        return _normalize_alembic_url(default_url)
    value = raw_value.strip()
    if not value:
        return _normalize_alembic_url(default_url)
    return _normalize_alembic_url(value)


def _normalize_alembic_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

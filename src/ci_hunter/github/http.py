from __future__ import annotations

import random
import time
from typing import Iterable, Optional

import httpx


RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def request_with_retry(
    method: str,
    url: str,
    *,
    max_retries: int = 2,
    retry_statuses: Iterable[int] = RETRY_STATUS_CODES,
    backoff_seconds: float = 0.5,
    **kwargs,
) -> httpx.Response:
    attempts = 0
    retry_statuses_set = set(retry_statuses)
    while True:
        try:
            response = httpx.request(method, url, **kwargs)
            if response.status_code in retry_statuses_set and attempts < max_retries:
                attempts += 1
                time.sleep(_compute_backoff(response, attempts, backoff_seconds))
                continue
            response.raise_for_status()
            return response
        except httpx.RequestError:
            if attempts >= max_retries:
                raise
            attempts += 1
            time.sleep(_compute_backoff(None, attempts, backoff_seconds))


def _compute_backoff(
    response: Optional[httpx.Response],
    attempts: int,
    base: float,
) -> float:
    retry_after = _parse_retry_after(response)
    if retry_after is not None:
        return retry_after + _jitter(base)
    return base * (2 ** (attempts - 1)) + _jitter(base)


def _parse_retry_after(response: Optional[httpx.Response]) -> Optional[float]:
    if response is None:
        return None
    if response.status_code != 429:
        return None
    header = response.headers.get("Retry-After")
    if not header:
        return None
    try:
        return float(header)
    except ValueError:
        return None


def _jitter(base: float) -> float:
    return random.uniform(0, base * 0.1)

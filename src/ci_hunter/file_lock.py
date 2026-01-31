from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Iterator

try:
    import fcntl  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None

try:
    import msvcrt  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None


@contextmanager
def locked_file(
    path: Path,
    mode: str,
    *,
    timeout_seconds: float = 5.0,
    poll_interval: float = 0.05,
) -> Iterator[object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with open(path, mode, encoding="utf-8") as handle:
        lock_length = _lock_length(path)
        while True:
            try:
                _try_lock(handle, lock_length)
                break
            except BlockingIOError:
                if time.monotonic() - start >= timeout_seconds:
                    raise RuntimeError("file lock timed out")
                time.sleep(poll_interval)
        try:
            yield handle
        finally:
            _unlock(handle, lock_length)


def _try_lock(handle: IO[object], lock_length: int) -> None:
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return
    if msvcrt is not None:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, lock_length)
        return
    raise RuntimeError("No file locking backend available")


def _unlock(handle: IO[object], lock_length: int) -> None:
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_UN)
        return
    if msvcrt is not None:
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, lock_length)
        return


def _lock_length(path: Path) -> int:
    if not path.exists():
        return 1
    size = path.stat().st_size
    return max(1, size)

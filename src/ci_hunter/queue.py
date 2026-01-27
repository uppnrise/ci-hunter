from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisJob:
    repo: str
    pr_number: int
    commit: str | None
    branch: str | None


class InMemoryJobQueue:
    def __init__(self) -> None:
        self._jobs: deque[AnalysisJob] = deque()

    def enqueue(self, job: AnalysisJob) -> None:
        self._jobs.append(job)

    def dequeue(self) -> AnalysisJob | None:
        if not self._jobs:
            return None
        return self._jobs.popleft()


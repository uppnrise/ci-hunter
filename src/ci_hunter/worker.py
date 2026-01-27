from __future__ import annotations

from collections.abc import Callable

from ci_hunter.github.webhook_cli_bridge import run_cli_for_trigger
from ci_hunter.github.webhook import WebhookTrigger
from ci_hunter.queue import AnalysisJob, InMemoryJobQueue


class Worker:
    def __init__(self, *, queue: InMemoryJobQueue, cli_main: Callable[[list[str]], int]) -> None:
        self._queue = queue
        self._cli_main = cli_main

    @property
    def queue(self) -> InMemoryJobQueue:
        return self._queue

    def run_once(self) -> int | None:
        job = self._queue.dequeue()
        if job is None:
            return None
        return self._process_job(job)

    def _process_job(self, job: AnalysisJob) -> int:
        trigger = WebhookTrigger(
            repo=job.repo,
            pr_number=job.pr_number,
            commit=job.commit,
            branch=job.branch,
            action="queued",
        )
        return run_cli_for_trigger(trigger, cli_main=self._cli_main)

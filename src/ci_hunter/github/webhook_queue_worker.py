from __future__ import annotations

from typing import Any

from ci_hunter.github.webhook_queue import enqueue_webhook_event
from ci_hunter.queue import InMemoryJobQueue
from ci_hunter.worker import Worker


def process_webhook_event_via_queue(
    event: str,
    payload: dict[str, Any],
    *,
    queue: InMemoryJobQueue,
    worker: Worker,
) -> tuple[bool, int | None]:
    if worker.queue is not queue:
        raise ValueError("queue mismatch between provided queue and worker")
    handled = enqueue_webhook_event(event, payload, queue=queue)
    if not handled:
        return False, None
    return True, worker.run_once()

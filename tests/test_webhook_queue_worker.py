import pytest

from ci_hunter.github.webhook_queue_worker import process_webhook_event_via_queue
from ci_hunter.queue import InMemoryJobQueue
from ci_hunter.worker import Worker

REPO = "acme/repo"
PR_NUMBER = 13
HEAD_SHA = "abc123"
HEAD_REF = "feature-x"


def _payload(action: str) -> dict:
    return {
        "action": action,
        "repository": {"full_name": REPO},
        "pull_request": {
            "number": PR_NUMBER,
            "head": {"sha": HEAD_SHA, "ref": HEAD_REF},
        },
    }


def test_process_webhook_event_via_queue_enqueues_and_processes():
    queue = InMemoryJobQueue()
    calls: list[list[str]] = []

    def cli_main(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    worker = Worker(queue=queue, cli_main=cli_main)
    handled, processed = process_webhook_event_via_queue(
        "pull_request",
        _payload("opened"),
        queue=queue,
        worker=worker,
    )

    assert handled is True
    assert processed == 0
    assert calls == [
        [
            "--repo",
            REPO,
            "--pr-number",
            str(PR_NUMBER),
            "--commit",
            HEAD_SHA,
            "--branch",
            HEAD_REF,
        ]
    ]


def test_process_webhook_event_via_queue_skips_disallowed_action():
    queue = InMemoryJobQueue()
    calls: list[list[str]] = []
    worker = Worker(queue=queue, cli_main=lambda argv: calls.append(argv) or 0)

    handled, processed = process_webhook_event_via_queue(
        "pull_request",
        _payload("closed"),
        queue=queue,
        worker=worker,
    )

    assert handled is False
    assert processed is None
    assert calls == []


def test_process_webhook_event_via_queue_raises_on_queue_mismatch():
    queue = InMemoryJobQueue()
    different_queue = InMemoryJobQueue()
    worker = Worker(queue=different_queue, cli_main=lambda _argv: 0)

    with pytest.raises(ValueError, match="queue mismatch"):
        process_webhook_event_via_queue(
            "pull_request",
            _payload("opened"),
            queue=queue,
            worker=worker,
        )

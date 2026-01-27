from ci_hunter.github.webhook_queue import enqueue_webhook_event
from ci_hunter.queue import AnalysisJob, InMemoryJobQueue

REPO = "acme/repo"
PR_NUMBER = 101
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


def test_enqueue_webhook_event_adds_job_for_allowed_action():
    queue = InMemoryJobQueue()

    handled = enqueue_webhook_event("pull_request", _payload("opened"), queue=queue)

    assert handled is True
    assert queue.dequeue() == AnalysisJob(
        repo=REPO,
        pr_number=PR_NUMBER,
        commit=HEAD_SHA,
        branch=HEAD_REF,
    )


def test_enqueue_webhook_event_skips_disallowed_action():
    queue = InMemoryJobQueue()

    handled = enqueue_webhook_event("pull_request", _payload("closed"), queue=queue)

    assert handled is False
    assert queue.dequeue() is None


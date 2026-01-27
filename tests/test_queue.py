from ci_hunter.queue import AnalysisJob, InMemoryJobQueue

REPO = "acme/repo"
PR_NUMBER = 11
COMMIT = "abc123"
BRANCH = "feature-x"


def test_in_memory_queue_is_fifo():
    queue = InMemoryJobQueue()
    first = AnalysisJob(repo=REPO, pr_number=PR_NUMBER, commit=COMMIT, branch=BRANCH)
    second = AnalysisJob(repo=REPO, pr_number=PR_NUMBER + 1, commit=None, branch=None)

    queue.enqueue(first)
    queue.enqueue(second)

    assert queue.dequeue() == first
    assert queue.dequeue() == second
    assert queue.dequeue() is None


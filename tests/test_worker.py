from ci_hunter.queue import AnalysisJob, InMemoryJobQueue
from ci_hunter.worker import Worker

REPO = "acme/repo"
PR_NUMBER = 77


def test_worker_processes_one_job_and_stops():
    queue = InMemoryJobQueue()
    queue.enqueue(AnalysisJob(repo=REPO, pr_number=PR_NUMBER, commit="abc123", branch="feature-x"))
    calls: list[list[str]] = []

    def cli_main(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    worker = Worker(queue=queue, cli_main=cli_main)
    exit_code = worker.run_once()

    assert exit_code == 0
    assert calls == [
        [
            "--repo",
            REPO,
            "--pr-number",
            str(PR_NUMBER),
            "--commit",
            "abc123",
            "--branch",
            "feature-x",
        ]
    ]


def test_worker_returns_zero_when_queue_empty():
    worker = Worker(queue=InMemoryJobQueue(), cli_main=lambda _argv: 0)

    assert worker.run_once() is None


def test_worker_propagates_nonzero_exit_code():
    queue = InMemoryJobQueue()
    queue.enqueue(AnalysisJob(repo=REPO, pr_number=PR_NUMBER, commit=None, branch=None))
    worker = Worker(queue=queue, cli_main=lambda _argv: 3)

    assert worker.run_once() == 3

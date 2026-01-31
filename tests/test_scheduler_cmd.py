import io
import json

import pytest

from ci_hunter.queue import AnalysisJob, InMemoryJobQueue
from ci_hunter.scheduler_cmd import main

REPO = "acme/repo"
PR_NUMBER = 42
COMMIT = "abc123"
BRANCH = "feature-x"


def test_scheduler_cmd_enqueues_job():
    queue = InMemoryJobQueue()

    exit_code = main(
        [
            "--repo",
            REPO,
            "--pr-number",
            str(PR_NUMBER),
            "--commit",
            COMMIT,
            "--branch",
            BRANCH,
        ],
        queue=queue,
    )

    assert exit_code == 0
    assert queue.dequeue() == AnalysisJob(
        repo=REPO,
        pr_number=PR_NUMBER,
        commit=COMMIT,
        branch=BRANCH,
    )


def test_scheduler_cmd_writes_job_to_queue_file(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    output = io.StringIO()

    exit_code = main(
        [
            "--repo",
            REPO,
            "--pr-number",
            str(PR_NUMBER),
            "--commit",
            COMMIT,
            "--branch",
            BRANCH,
            "--queue-file",
            str(queue_path),
        ],
        out=output,
    )

    assert exit_code == 0
    assert str(queue_path) in output.getvalue()
    payload = json.loads(queue_path.read_text(encoding="utf-8").strip())
    assert payload == {
        "repo": REPO,
        "pr_number": PR_NUMBER,
        "commit": COMMIT,
        "branch": BRANCH,
    }


def test_scheduler_cmd_requires_queue_file_when_no_queue():
    with pytest.raises(SystemExit):
        main(
            [
                "--repo",
                REPO,
                "--pr-number",
                str(PR_NUMBER),
            ]
        )


def test_scheduler_cmd_rejects_queue_and_queue_file_together(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    with pytest.raises(SystemExit):
        main(
            [
                "--repo",
                REPO,
                "--pr-number",
                str(PR_NUMBER),
                "--queue-file",
                str(queue_path),
            ],
            queue=InMemoryJobQueue(),
        )


def test_scheduler_cmd_rejects_non_positive_pr_number():
    with pytest.raises(SystemExit):
        main(
            [
                "--repo",
                REPO,
                "--pr-number",
                "0",
                "--queue-file",
                "queue.jsonl",
            ]
        )


def test_scheduler_cmd_rejects_blank_repo():
    with pytest.raises(SystemExit):
        main(
            [
                "--repo",
                "   ",
                "--pr-number",
                str(PR_NUMBER),
                "--queue-file",
                "queue.jsonl",
            ]
        )

import io
from pathlib import Path

from ci_hunter.worker_cmd import main


def test_worker_cmd_processes_one_job_and_updates_queue(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    queue_path.write_text(
        "\n".join(
            [
                '{"repo":"acme/repo","pr_number":1,"commit":"abc","branch":"feature"}',
                '{"repo":"acme/repo","pr_number":2,"commit":null,"branch":null}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def cli_main(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    exit_code = main(
        [
            "--queue-file",
            str(queue_path),
            "--max-jobs",
            "1",
        ],
        cli_entry=cli_main,
    )

    assert exit_code == 0
    assert calls == [
        [
            "--repo",
            "acme/repo",
            "--pr-number",
            "1",
            "--commit",
            "abc",
            "--branch",
            "feature",
        ]
    ]
    remaining = queue_path.read_text(encoding="utf-8").strip().splitlines()
    assert remaining == ['{"repo":"acme/repo","pr_number":2,"commit":null,"branch":null}']


def test_worker_cmd_skips_invalid_json_lines(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    queue_path.write_text(
        "\n".join(
            [
                '{"repo":"acme/repo","pr_number":1,"commit":"abc","branch":"feature"}',
                "not-json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []
    output = io.StringIO()

    exit_code = main(
        ["--queue-file", str(queue_path)],
        cli_entry=lambda argv: calls.append(argv) or 0,
        out=output,
    )

    assert exit_code == 0
    assert calls
    assert f"{queue_path.name}:2" in output.getvalue()
    assert "skipping invalid queue line" in output.getvalue()


def test_worker_cmd_reports_when_no_jobs(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    output = io.StringIO()

    exit_code = main(
        ["--queue-file", str(queue_path)],
        cli_entry=lambda _argv: 0,
        out=output,
    )

    assert exit_code == 0
    assert "no jobs found" in output.getvalue()
    assert queue_path.name in output.getvalue()


def test_worker_cmd_skips_jobs_missing_required_fields(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    queue_path.write_text(
        "\n".join(
            [
                '{"repo":"acme/repo","pr_number":1,"commit":"abc","branch":"feature"}',
                '{"repo":"acme/repo","commit":"abc"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = io.StringIO()
    calls: list[list[str]] = []

    exit_code = main(
        ["--queue-file", str(queue_path)],
        cli_entry=lambda argv: calls.append(argv) or 0,
        out=output,
    )

    assert exit_code == 0
    assert len(calls) == 1
    assert "missing required fields" in output.getvalue()
    assert f"{queue_path.name}:2" in output.getvalue()


def test_worker_cmd_loop_runs_multiple_iterations(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    queue_path.write_text(
        "\n".join(
            [
                '{"repo":"acme/repo","pr_number":1,"commit":"abc","branch":"feature"}',
                '{"repo":"acme/repo","pr_number":2,"commit":null,"branch":null}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []
    slept: list[float] = []

    def cli_main(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    def sleeper(seconds: float) -> None:
        slept.append(seconds)

    exit_code = main(
        [
            "--queue-file",
            str(queue_path),
            "--max-jobs",
            "1",
            "--loop",
            "--max-loops",
            "2",
            "--sleep-seconds",
            "0.01",
        ],
        cli_entry=cli_main,
        sleep=sleeper,
    )

    assert exit_code == 0
    assert len(calls) == 2
    assert slept == []


def test_worker_cmd_loop_sleeps_only_when_no_jobs(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    queue_path.write_text(
        '{"repo":"acme/repo","pr_number":1,"commit":"abc","branch":"feature"}\n',
        encoding="utf-8",
    )
    slept: list[float] = []

    def sleeper(seconds: float) -> None:
        slept.append(seconds)

    exit_code = main(
        [
            "--queue-file",
            str(queue_path),
            "--loop",
            "--max-loops",
            "2",
            "--sleep-seconds",
            "0.01",
        ],
        cli_entry=lambda _argv: 0,
        sleep=sleeper,
    )

    assert exit_code == 0
    assert slept == [0.01]

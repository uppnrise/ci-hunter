from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Iterable, TextIO

from ci_hunter.cli import main as cli_main
from ci_hunter.queue import AnalysisJob


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-hunter-worker")
    parser.add_argument("--queue-file", required=True)
    parser.add_argument("--max-jobs", type=_positive_int, default=1)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    cli_entry: Callable[[list[str]], int] = cli_main,
    out: TextIO | None = None,
) -> int:
    args = _build_parser().parse_args(argv)
    out = out or os.sys.stdout
    path = Path(args.queue_file)
    jobs = _load_jobs(path, out=out)
    if not jobs:
        out.write(f"{path.name}: no jobs found\n")
        return 0
    processed: list[AnalysisJob] = []
    exit_code = 0
    for job in jobs[: args.max_jobs]:
        cli_argv = [
            "--repo",
            job.repo,
            "--pr-number",
            str(job.pr_number),
        ]
        if job.commit:
            cli_argv.extend(["--commit", job.commit])
        if job.branch:
            cli_argv.extend(["--branch", job.branch])
        exit_code = cli_entry(cli_argv)
        if exit_code != 0:
            break
        processed.append(job)
    remaining = jobs[len(processed) :]
    _write_jobs(path, remaining)
    return exit_code


def _load_jobs(path: Path, *, out: TextIO) -> list[AnalysisJob]:
    if not path.exists():
        return []
    lines = list(enumerate(path.read_text(encoding="utf-8").splitlines(), start=1))
    jobs: list[AnalysisJob] = []
    for line_number, line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            out.write(f"{path.name}:{line_number}: skipping invalid queue line\n")
            continue
        if not _has_required_fields(payload):
            out.write(f"{path.name}:{line_number}: skipping queue line missing required fields\n")
            continue
        jobs.append(
            AnalysisJob(
                repo=payload["repo"],
                pr_number=payload["pr_number"],
                commit=payload.get("commit"),
                branch=payload.get("branch"),
            )
        )
    return jobs


def _write_jobs(path: Path, jobs: Iterable[AnalysisJob]) -> None:
    lines = [
        json.dumps(
            {
                "repo": job.repo,
                "pr_number": job.pr_number,
                "commit": job.commit,
                "branch": job.branch,
            },
            separators=(",", ":"),
        )
        for job in jobs
    ]
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("max-jobs must be a positive integer")
    return number


def _has_required_fields(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    repo = payload.get("repo")
    pr_number = payload.get("pr_number")
    return isinstance(repo, str) and bool(repo.strip()) and isinstance(pr_number, int)

from __future__ import annotations

import argparse
import os
from typing import TextIO

from ci_hunter.job_queue_file import append_job
from ci_hunter.queue import AnalysisJob, InMemoryJobQueue


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-hunter-scheduler")
    parser.add_argument("--repo", type=_non_empty_string, required=True)
    parser.add_argument("--pr-number", type=_positive_int, required=True)
    parser.add_argument("--commit")
    parser.add_argument("--branch")
    parser.add_argument("--queue-file")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    queue: InMemoryJobQueue | None = None,
    out: TextIO | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if queue is not None and args.queue_file:
        parser.error("--queue-file cannot be used when a queue is provided")
    if queue is None and not args.queue_file:
        parser.error("--queue-file is required when no queue is provided")
    out = out or os.sys.stdout
    job = AnalysisJob(
        repo=args.repo,
        pr_number=args.pr_number,
        commit=args.commit,
        branch=args.branch,
    )
    if queue is not None:
        queue.enqueue(job)
    else:
        append_job(args.queue_file, job)
        out.write(f"enqueued job to {args.queue_file}\n")
    return 0


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("pr-number must be a positive integer")
    return number


def _non_empty_string(value: str) -> str:
    text = value.strip()
    if not text:
        raise argparse.ArgumentTypeError("repo must be a non-empty string")
    return text

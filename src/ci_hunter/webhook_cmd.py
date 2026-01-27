from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

from ci_hunter.cli import main as cli_main
from ci_hunter.github.webhook_cli import run_webhook_from_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-hunter-webhook")
    parser.add_argument("--event", required=True)
    parser.add_argument("--payload-file", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    run_webhook_from_text: Callable[..., tuple[bool, int | None]] = run_webhook_from_text,
    cli_entry: Callable[[list[str]], int] = cli_main,
) -> int:
    args = _build_parser().parse_args(argv)
    payload_text = _read_payload_file(args.payload_file)
    extra_args: list[str] = []
    if args.dry_run:
        extra_args.append("--dry-run")
    handled, exit_code = run_webhook_from_text(
        args.event,
        payload_text,
        cli_main=cli_entry,
        extra_args=extra_args,
    )
    if exit_code is not None:
        return exit_code
    if not handled:
        return 1
    return 0


def _read_payload_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()

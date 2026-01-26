from __future__ import annotations

import argparse
import os
from typing import Callable, Mapping, TextIO

from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN
from ci_hunter.github.auth import GitHubAppAuth
from ci_hunter.github.artifacts import fetch_junit_durations_from_artifacts
from ci_hunter.github.client import GitHubActionsClient
from ci_hunter.github.comments import post_pr_comment
from ci_hunter.github.logs import fetch_run_step_durations
from ci_hunter.runner import fetch_store_analyze
from ci_hunter.report import render_json_report, render_markdown_report
from ci_hunter.storage import Storage, StorageConfig


DEFAULT_MIN_DELTA_PCT = 0.2
DEFAULT_DB = ":memory:"
DEFAULT_TIMINGS_RUN_LIMIT = 10
FORMAT_MARKDOWN = "md"
FORMAT_JSON = "json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-hunter")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--min-delta-pct", type=float, default=DEFAULT_MIN_DELTA_PCT)
    parser.add_argument("--baseline-strategy", default=BASELINE_STRATEGY_MEDIAN)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--timings-run-limit", type=int, default=DEFAULT_TIMINGS_RUN_LIMIT)
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--format", choices=[FORMAT_MARKDOWN, FORMAT_JSON], default=FORMAT_MARKDOWN)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., object] = fetch_store_analyze,
    auth_factory: Callable[[Mapping[str, str]], GitHubAppAuth] | None = None,
    markdown_renderer: Callable[..., str] = render_markdown_report,
    json_renderer: Callable[..., str] = render_json_report,
    comment_poster: Callable[..., int] = post_pr_comment,
    out: TextIO | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    out = out or os.sys.stdout

    auth_factory = auth_factory or (lambda e: GitHubAppAuth(
        app_id=e["GITHUB_APP_ID"],
        installation_id=e["GITHUB_INSTALLATION_ID"],
        private_key_pem=e["GITHUB_PRIVATE_KEY_PEM"],
    ))
    auth = auth_factory(env)

    def client_factory(token: str) -> GitHubActionsClient:
        return GitHubActionsClient(token=token)

    storage = Storage(StorageConfig(database_url=args.db))

    result = runner(
        auth=auth,
        client_factory=client_factory,
        storage=storage,
        repo=args.repo,
        min_delta_pct=args.min_delta_pct,
        baseline_strategy=args.baseline_strategy,
        timings_run_limit=args.timings_run_limit,
        step_fetcher=fetch_run_step_durations,
        test_fetcher=fetch_junit_durations_from_artifacts,
    )
    if args.format == FORMAT_JSON:
        report = json_renderer(result)
    else:
        report = markdown_renderer(result)

    if args.dry_run:
        out.write(report)
        if not report.endswith("\n"):
            out.write("\n")
        return 0

    if args.pr_number is None:
        raise ValueError("--pr-number is required unless --dry-run is set")

    token = auth.get_installation_token().token
    comment_poster(token, args.repo, args.pr_number, report)
    return 0

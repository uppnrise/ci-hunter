from __future__ import annotations

import argparse
import os
from typing import Callable, Mapping, TextIO

from ci_hunter.config import AppConfig, load_config
from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN
from ci_hunter.github.auth import GitHubAppAuth
from ci_hunter.github.artifacts import fetch_junit_durations_from_artifacts
from ci_hunter.github.client import GitHubActionsClient
from ci_hunter.github.comments import post_pr_comment
from ci_hunter.github.logs import fetch_run_step_durations
from ci_hunter.github.pr_infer import InferredPullRequest, infer_pr_number
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
    parser.add_argument("--config")
    parser.add_argument("--repo")
    parser.add_argument("--min-delta-pct", type=float, default=None)
    parser.add_argument("--baseline-strategy", default=None)
    parser.add_argument("--db", default=None)
    parser.add_argument("--timings-run-limit", type=int, default=None)
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--commit")
    parser.add_argument("--branch")
    parser.add_argument("--format", choices=[FORMAT_MARKDOWN, FORMAT_JSON], default=None)
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument("--output-file")
    parser.add_argument("--no-comment", action="store_true", default=None)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., object] = fetch_store_analyze,
    auth_factory: Callable[[Mapping[str, str]], GitHubAppAuth] | None = None,
    pr_infer: Callable[..., InferredPullRequest | None] = infer_pr_number,
    markdown_renderer: Callable[..., str] = render_markdown_report,
    json_renderer: Callable[..., str] = render_json_report,
    comment_poster: Callable[..., int] = post_pr_comment,
    out: TextIO | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    out = out or os.sys.stdout

    config = _load_optional_config(args.config)
    args = _merge_config(args, config)
    _apply_defaults(args)

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
        _write_report(report, args.output_file, out)
        return 0
    if args.no_comment:
        _write_report(report, args.output_file, out)
        return 0

    pr_number = args.pr_number
    token = auth.get_installation_token().token
    if pr_number is None:
        inferred = pr_infer(token=token, repo=args.repo, commit=args.commit, branch=args.branch)
        if inferred is not None:
            pr_number = inferred.number
        else:
            raise ValueError("--pr-number is required unless --dry-run is set")

    _write_report(report, args.output_file, out)
    comment_poster(token, args.repo, pr_number, report)
    return 0


def _load_optional_config(path: str | None) -> AppConfig:
    if not path:
        return AppConfig()
    return load_config(path)


def _merge_config(args: argparse.Namespace, config: AppConfig) -> argparse.Namespace:
    merged = argparse.Namespace(**vars(args))
    _apply_if_missing(merged, "repo", config.repo)
    _apply_if_missing(merged, "min_delta_pct", config.min_delta_pct)
    _apply_if_missing(merged, "baseline_strategy", config.baseline_strategy)
    _apply_if_missing(merged, "db", config.db)
    _apply_if_missing(merged, "timings_run_limit", config.timings_run_limit)
    _apply_if_missing(merged, "format", config.format)
    _apply_if_missing(merged, "dry_run", config.dry_run)
    _apply_if_missing(merged, "pr_number", config.pr_number)
    _apply_if_missing(merged, "commit", config.commit)
    _apply_if_missing(merged, "branch", config.branch)
    _apply_if_missing(merged, "output_file", getattr(config, "output_file", None))
    _apply_if_missing(merged, "no_comment", getattr(config, "no_comment", None))
    return merged


def _apply_if_missing(args: argparse.Namespace, key: str, value: object | None) -> None:
    if value is None:
        return
    current = getattr(args, key)
    if current is None:
        setattr(args, key, value)
    elif isinstance(current, bool) and current is False:
        setattr(args, key, value)


def _apply_defaults(args: argparse.Namespace) -> None:
    if args.repo is None:
        raise ValueError("--repo is required")
    if args.min_delta_pct is None:
        args.min_delta_pct = DEFAULT_MIN_DELTA_PCT
    if args.baseline_strategy is None:
        args.baseline_strategy = BASELINE_STRATEGY_MEDIAN
    if args.db is None:
        args.db = DEFAULT_DB
    if args.timings_run_limit is None:
        args.timings_run_limit = DEFAULT_TIMINGS_RUN_LIMIT
    if args.format is None:
        args.format = FORMAT_MARKDOWN
    if args.dry_run is None:
        args.dry_run = False
    if args.no_comment is None:
        args.no_comment = False


def _write_report(report: str, output_file: str | None, out: TextIO) -> None:
    if not report.endswith("\n"):
        report = f"{report}\n"
    if output_file:
        with open(output_file, "w", encoding="utf-8") as handle:
            handle.write(report)
        return
    out.write(report)

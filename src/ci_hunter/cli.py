from __future__ import annotations

import argparse
import os
from typing import Callable, Mapping

from ci_hunter.detection import BASELINE_STRATEGY_MEDIAN
from ci_hunter.github.auth import GitHubAppAuth
from ci_hunter.github.client import GitHubActionsClient
from ci_hunter.runner import fetch_store_analyze
from ci_hunter.storage import Storage, StorageConfig


DEFAULT_MIN_DELTA_PCT = 0.2
DEFAULT_DB = ":memory:"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-hunter")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--min-delta-pct", type=float, default=DEFAULT_MIN_DELTA_PCT)
    parser.add_argument("--baseline-strategy", default=BASELINE_STRATEGY_MEDIAN)
    parser.add_argument("--db", default=DEFAULT_DB)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., object] = fetch_store_analyze,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    env = os.environ if env is None else env

    auth = GitHubAppAuth(
        app_id=env["GITHUB_APP_ID"],
        installation_id=env["GITHUB_INSTALLATION_ID"],
        private_key_pem=env["GITHUB_PRIVATE_KEY_PEM"],
    )

    def client_factory(token: str) -> GitHubActionsClient:
        return GitHubActionsClient(token=token)

    storage = Storage(StorageConfig(database_url=args.db))

    runner(
        auth=auth,
        client_factory=client_factory,
        storage=storage,
        repo=args.repo,
        min_delta_pct=args.min_delta_pct,
        baseline_strategy=args.baseline_strategy,
    )
    return 0

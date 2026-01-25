from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import threading
from typing import Iterable, List, Optional

from ci_hunter.github.client import WorkflowRun


WORKFLOW_RUNS_TABLE = "workflow_runs"


@dataclass(frozen=True)
class StorageConfig:
    database_url: str


class Storage:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self._database_url, check_same_thread=False)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return self._connection

    def _init_schema(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {WORKFLOW_RUNS_TABLE} (
                    repo TEXT NOT NULL,
                    run_id INTEGER NOT NULL,
                    run_number INTEGER NOT NULL,
                    status TEXT,
                    conclusion TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    head_sha TEXT NOT NULL,
                    PRIMARY KEY (repo, run_id)
                )
                """
            )

    def save_workflow_runs(self, repo: str, runs: Iterable[WorkflowRun]) -> None:
        with self._lock, self._connect() as connection:
            connection.executemany(
                f"""
                INSERT OR REPLACE INTO {WORKFLOW_RUNS_TABLE} (
                    repo,
                    run_id,
                    run_number,
                    status,
                    conclusion,
                    created_at,
                    updated_at,
                    head_sha
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        repo,
                        run.id,
                        run.run_number,
                        run.status,
                        run.conclusion,
                        run.created_at,
                        run.updated_at,
                        run.head_sha,
                    )
                    for run in runs
                ],
            )

    def list_workflow_runs(self, repo: str) -> List[WorkflowRun]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    run_id,
                    run_number,
                    status,
                    conclusion,
                    created_at,
                    updated_at,
                    head_sha
                FROM {WORKFLOW_RUNS_TABLE}
                WHERE repo = ?
                ORDER BY run_number
                """,
                (repo,),
            ).fetchall()

        return [
            WorkflowRun(
                id=row[0],
                run_number=row[1],
                status=row[2],
                conclusion=row[3],
                created_at=row[4],
                updated_at=row[5],
                head_sha=row[6],
            )
            for row in rows
        ]

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[object],
    ) -> None:
        self.close()

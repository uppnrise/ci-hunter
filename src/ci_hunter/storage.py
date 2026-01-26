from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import threading
from typing import Iterable, List, Optional

from ci_hunter.github.client import WorkflowRun
from ci_hunter.junit import TestDuration
from ci_hunter.steps import StepDuration


WORKFLOW_RUNS_TABLE = "workflow_runs"
STEP_DURATIONS_TABLE = "step_durations"
TEST_DURATIONS_TABLE = "test_durations"


@dataclass(frozen=True)
class StorageConfig:
    database_url: str


@dataclass(frozen=True)
class StepDurationSample:
    run_number: int
    step_name: str
    duration_seconds: float
    __test__ = False


@dataclass(frozen=True)
class TestDurationSample:
    run_number: int
    test_name: str
    duration_seconds: float
    __test__ = False


class Storage:
    def __init__(self, database_url: str | StorageConfig) -> None:
        if isinstance(database_url, StorageConfig):
            database_url = database_url.database_url
        self._database_url = database_url
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self._database_url, check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys = ON;")
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
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {STEP_DURATIONS_TABLE} (
                    repo TEXT NOT NULL,
                    run_id INTEGER NOT NULL,
                    step_name TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    PRIMARY KEY (repo, run_id, step_name),
                    FOREIGN KEY (repo, run_id)
                        REFERENCES {WORKFLOW_RUNS_TABLE}(repo, run_id)
                )
                """
            )
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TEST_DURATIONS_TABLE} (
                    repo TEXT NOT NULL,
                    run_id INTEGER NOT NULL,
                    test_name TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    PRIMARY KEY (repo, run_id, test_name),
                    FOREIGN KEY (repo, run_id)
                        REFERENCES {WORKFLOW_RUNS_TABLE}(repo, run_id)
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

    def save_step_durations(
        self,
        repo: str,
        run_id: int,
        durations: Iterable[StepDuration],
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.executemany(
                f"""
                INSERT OR REPLACE INTO {STEP_DURATIONS_TABLE} (
                    repo,
                    run_id,
                    step_name,
                    duration_seconds
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        repo,
                        run_id,
                        duration.name,
                        duration.duration_seconds,
                    )
                    for duration in durations
                ],
            )

    def list_step_durations(self, repo: str) -> List[StepDurationSample]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    runs.run_number,
                    steps.step_name,
                    steps.duration_seconds
                FROM {STEP_DURATIONS_TABLE} AS steps
                JOIN {WORKFLOW_RUNS_TABLE} AS runs
                  ON runs.repo = steps.repo
                 AND runs.run_id = steps.run_id
                WHERE steps.repo = ?
                ORDER BY runs.run_number, steps.step_name
                """,
                (repo,),
            ).fetchall()

        return [
            StepDurationSample(
                run_number=row[0],
                step_name=row[1],
                duration_seconds=row[2],
            )
            for row in rows
        ]

    def save_test_durations(
        self,
        repo: str,
        run_id: int,
        durations: Iterable[TestDuration],
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.executemany(
                f"""
                INSERT OR REPLACE INTO {TEST_DURATIONS_TABLE} (
                    repo,
                    run_id,
                    test_name,
                    duration_seconds
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        repo,
                        run_id,
                        duration.name,
                        duration.duration_seconds,
                    )
                    for duration in durations
                ],
            )

    def list_test_durations(self, repo: str) -> List[TestDurationSample]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    runs.run_number,
                    tests.test_name,
                    tests.duration_seconds
                FROM {TEST_DURATIONS_TABLE} AS tests
                JOIN {WORKFLOW_RUNS_TABLE} AS runs
                  ON runs.repo = tests.repo
                 AND runs.run_id = tests.run_id
                WHERE tests.repo = ?
                ORDER BY runs.run_number, tests.test_name
                """,
                (repo,),
            ).fetchall()

        return [
            TestDurationSample(
                run_number=row[0],
                test_name=row[1],
                duration_seconds=row[2],
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

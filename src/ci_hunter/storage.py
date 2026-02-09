from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterable, List, Optional
from urllib.parse import urlparse

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


def _import_psycopg() -> Any:
    import psycopg

    return psycopg


def _detect_database_scheme(database_url: str) -> str:
    if database_url == ":memory:" or "://" not in database_url:
        return "sqlite"
    scheme = urlparse(database_url).scheme.lower()
    if scheme in {"sqlite", "sqlite3"}:
        return "sqlite"
    if scheme in {"postgresql", "postgres"}:
        return "postgresql"
    raise ValueError(f"Unsupported database scheme: {scheme}")


def _resolve_sqlite_path(database_url: str) -> str:
    if database_url == ":memory:" or "://" not in database_url:
        return database_url
    parsed = urlparse(database_url)
    if parsed.scheme.lower() not in {"sqlite", "sqlite3"}:
        raise ValueError(f"Unsupported sqlite URL: {database_url}")
    if not parsed.path:
        raise ValueError("SQLite URL must include a database path")
    if parsed.path == "/:memory:":
        return ":memory:"
    if parsed.path.startswith("//"):
        normalized = parsed.path[1:]
    elif parsed.path.startswith("/"):
        normalized = parsed.path[1:]
    else:
        normalized = parsed.path
    return str(Path(normalized).expanduser())


class _SQLiteBackend:
    name = "sqlite"
    placeholder = "?"

    def __init__(self, database_url: str) -> None:
        self._connection = sqlite3.connect(database_url, check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys = ON;")

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        return self._connection.execute(query, params).fetchall()

    def executemany(self, query: str, rows: list[tuple[Any, ...]]) -> None:
        if rows:
            self._connection.executemany(query, rows)

    def commit(self) -> None:
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


class _PostgresBackend:
    name = "postgresql"
    placeholder = "%s"

    def __init__(self, database_url: str) -> None:
        psycopg = _import_psycopg()
        self._connection = psycopg.connect(database_url)

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description is None:
                return []
            return cursor.fetchall()

    def executemany(self, query: str, rows: list[tuple[Any, ...]]) -> None:
        if not rows:
            return
        with self._connection.cursor() as cursor:
            cursor.executemany(query, rows)

    def commit(self) -> None:
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


class Storage:
    def __init__(self, database_url: str | StorageConfig) -> None:
        if isinstance(database_url, StorageConfig):
            database_url = database_url.database_url
        self._database_url = database_url
        self._lock = threading.Lock()
        scheme = _detect_database_scheme(self._database_url)
        if scheme == "sqlite":
            self._backend = _SQLiteBackend(_resolve_sqlite_path(self._database_url))
        elif scheme == "postgresql":
            try:
                self._backend = _PostgresBackend(self._database_url)
            except ImportError as exc:
                raise RuntimeError(
                    "PostgreSQL backend requires 'psycopg'. Install it and retry."
                ) from exc
        else:
            raise ValueError(f"Unsupported database scheme: {scheme}")
        self._init_schema()

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def _placeholder(self) -> str:
        return self._backend.placeholder

    def _init_schema(self) -> None:
        if self.backend_name != "sqlite":
            # Postgres schema is owned by Alembic migrations.
            return
        run_id_type = "INTEGER" if self.backend_name == "sqlite" else "BIGINT"
        run_number_type = "INTEGER" if self.backend_name == "sqlite" else "BIGINT"
        duration_type = "REAL" if self.backend_name == "sqlite" else "DOUBLE PRECISION"
        with self._lock:
            self._backend.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {WORKFLOW_RUNS_TABLE} (
                    repo TEXT NOT NULL,
                    run_id {run_id_type} NOT NULL,
                    run_number {run_number_type} NOT NULL,
                    status TEXT,
                    conclusion TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    head_sha TEXT NOT NULL,
                    PRIMARY KEY (repo, run_id)
                )
                """
            )
            self._backend.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {STEP_DURATIONS_TABLE} (
                    repo TEXT NOT NULL,
                    run_id {run_id_type} NOT NULL,
                    step_name TEXT NOT NULL,
                    duration_seconds {duration_type} NOT NULL,
                    PRIMARY KEY (repo, run_id, step_name),
                    FOREIGN KEY (repo, run_id)
                        REFERENCES {WORKFLOW_RUNS_TABLE}(repo, run_id)
                )
                """
            )
            self._backend.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TEST_DURATIONS_TABLE} (
                    repo TEXT NOT NULL,
                    run_id {run_id_type} NOT NULL,
                    test_name TEXT NOT NULL,
                    duration_seconds {duration_type} NOT NULL,
                    PRIMARY KEY (repo, run_id, test_name),
                    FOREIGN KEY (repo, run_id)
                        REFERENCES {WORKFLOW_RUNS_TABLE}(repo, run_id)
                )
                """
            )
            self._backend.commit()

    def save_workflow_runs(self, repo: str, runs: Iterable[WorkflowRun]) -> None:
        placeholder = self._placeholder()
        values = [
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
        ]
        with self._lock:
            if self.backend_name == "sqlite":
                query = f"""
                    INSERT OR REPLACE INTO {WORKFLOW_RUNS_TABLE} (
                        repo,
                        run_id,
                        run_number,
                        status,
                        conclusion,
                        created_at,
                        updated_at,
                        head_sha
                    ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """
            else:
                query = f"""
                    INSERT INTO {WORKFLOW_RUNS_TABLE} (
                        repo,
                        run_id,
                        run_number,
                        status,
                        conclusion,
                        created_at,
                        updated_at,
                        head_sha
                    ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                    ON CONFLICT (repo, run_id) DO UPDATE SET
                        run_number = EXCLUDED.run_number,
                        status = EXCLUDED.status,
                        conclusion = EXCLUDED.conclusion,
                        created_at = EXCLUDED.created_at,
                        updated_at = EXCLUDED.updated_at,
                        head_sha = EXCLUDED.head_sha
                """
            self._backend.executemany(query, values)
            self._backend.commit()

    def list_workflow_runs(self, repo: str) -> List[WorkflowRun]:
        placeholder = self._placeholder()
        with self._lock:
            rows = self._backend.execute(
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
                WHERE repo = {placeholder}
                ORDER BY run_number
                """,
                (repo,),
            )

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
        placeholder = self._placeholder()
        values = [
            (
                repo,
                run_id,
                duration.name,
                duration.duration_seconds,
            )
            for duration in durations
        ]
        with self._lock:
            if self.backend_name == "sqlite":
                query = f"""
                    INSERT OR REPLACE INTO {STEP_DURATIONS_TABLE} (
                        repo,
                        run_id,
                        step_name,
                        duration_seconds
                    ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                """
            else:
                query = f"""
                    INSERT INTO {STEP_DURATIONS_TABLE} (
                        repo,
                        run_id,
                        step_name,
                        duration_seconds
                    ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                    ON CONFLICT (repo, run_id, step_name) DO UPDATE SET
                        duration_seconds = EXCLUDED.duration_seconds
                """
            self._backend.executemany(query, values)
            self._backend.commit()

    def list_step_durations(self, repo: str) -> List[StepDurationSample]:
        placeholder = self._placeholder()
        with self._lock:
            rows = self._backend.execute(
                f"""
                SELECT
                    runs.run_number,
                    steps.step_name,
                    steps.duration_seconds
                FROM {STEP_DURATIONS_TABLE} AS steps
                JOIN {WORKFLOW_RUNS_TABLE} AS runs
                  ON runs.repo = steps.repo
                 AND runs.run_id = steps.run_id
                WHERE steps.repo = {placeholder}
                ORDER BY runs.run_number, steps.step_name
                """,
                (repo,),
            )

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
        placeholder = self._placeholder()
        values = [
            (
                repo,
                run_id,
                duration.name,
                duration.duration_seconds,
            )
            for duration in durations
        ]
        with self._lock:
            if self.backend_name == "sqlite":
                query = f"""
                    INSERT OR REPLACE INTO {TEST_DURATIONS_TABLE} (
                        repo,
                        run_id,
                        test_name,
                        duration_seconds
                    ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                """
            else:
                query = f"""
                    INSERT INTO {TEST_DURATIONS_TABLE} (
                        repo,
                        run_id,
                        test_name,
                        duration_seconds
                    ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                    ON CONFLICT (repo, run_id, test_name) DO UPDATE SET
                        duration_seconds = EXCLUDED.duration_seconds
                """
            self._backend.executemany(query, values)
            self._backend.commit()

    def list_test_durations(self, repo: str) -> List[TestDurationSample]:
        placeholder = self._placeholder()
        with self._lock:
            rows = self._backend.execute(
                f"""
                SELECT
                    runs.run_number,
                    tests.test_name,
                    tests.duration_seconds
                FROM {TEST_DURATIONS_TABLE} AS tests
                JOIN {WORKFLOW_RUNS_TABLE} AS runs
                  ON runs.repo = tests.repo
                 AND runs.run_id = tests.run_id
                WHERE tests.repo = {placeholder}
                ORDER BY runs.run_number, tests.test_name
                """,
                (repo,),
            )

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
            self._backend.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[object],
    ) -> None:
        self.close()

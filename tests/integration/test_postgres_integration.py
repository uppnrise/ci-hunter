import os
import subprocess

import pytest

from ci_hunter.github.client import WorkflowRun
from ci_hunter.storage import Storage, StorageConfig


TEST_DB_ENV = "CI_HUNTER_POSTGRES_TEST_URL"
ALEMBIC_URL_ENV = "CI_HUNTER_ALEMBIC_URL"
DEFAULT_TEST_DB_URL = "postgresql://postgres:postgres@127.0.0.1:5433/ci_hunter_test"
REPO = "acme/repo"


def _test_db_url() -> str:
    return os.environ.get(TEST_DB_ENV, DEFAULT_TEST_DB_URL)


@pytest.mark.integration
def test_postgres_migration_and_storage_flow():
    if TEST_DB_ENV not in os.environ:
        pytest.skip(
            f"Set {TEST_DB_ENV} to run Postgres integration tests "
            "(for example with docker-compose.postgres.yml)."
        )

    env = os.environ.copy()
    env[ALEMBIC_URL_ENV] = _test_db_url()
    subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)

    storage = Storage(StorageConfig(database_url=_test_db_url()))
    run = WorkflowRun(
        id=1,
        run_number=1,
        status="completed",
        conclusion="success",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:05Z",
        head_sha="abc123",
    )
    storage.save_workflow_runs(REPO, [run])
    runs = storage.list_workflow_runs(REPO)
    storage.close()

    assert len(runs) == 1
    assert runs[0].head_sha == "abc123"

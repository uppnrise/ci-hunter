from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_postgres_compose_profile_exists():
    compose_file = REPO_ROOT / "docker-compose.postgres.yml"
    assert compose_file.exists()

    content = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
    services = content.get("services", {})
    postgres = services.get("postgres")

    assert postgres is not None
    assert postgres.get("image") == "postgres:16"
    assert "5433:5432" in postgres.get("ports", [])
    assert "healthcheck" in postgres


def test_postgres_integration_test_exists():
    integration_test = REPO_ROOT / "tests" / "integration" / "test_postgres_integration.py"
    assert integration_test.exists()

    text = integration_test.read_text(encoding="utf-8")
    assert "CI_HUNTER_POSTGRES_TEST_URL" in text
    assert "CI_HUNTER_ALEMBIC_URL" in text
    assert 'subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)' in text


def test_postgres_integration_workflow_exists():
    workflow = REPO_ROOT / ".github" / "workflows" / "postgres-integration.yml"
    assert workflow.exists()

    content = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    job = content["jobs"]["postgres-integration"]

    assert job["services"]["postgres"]["image"] == "postgres:16"
    assert "5433:5432" in job["services"]["postgres"]["ports"]

    step_names = [step.get("name") for step in job["steps"] if isinstance(step, dict)]
    assert "Run migration smoke test" in step_names
    assert "Run Postgres integration tests" in step_names

    migration_index = step_names.index("Run migration smoke test")
    integration_index = step_names.index("Run Postgres integration tests")
    assert migration_index < integration_index

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_postgres_compose_profile_exists():
    compose_file = REPO_ROOT / "docker-compose.postgres.yml"
    assert compose_file.exists()

    content = compose_file.read_text(encoding="utf-8")
    assert "services:" in content
    assert "postgres:" in content
    assert "5433:5432" in content


def test_postgres_integration_test_exists():
    integration_test = REPO_ROOT / "tests" / "integration" / "test_postgres_integration.py"
    assert integration_test.exists()

    text = integration_test.read_text(encoding="utf-8")
    assert "CI_HUNTER_POSTGRES_TEST_URL" in text
    assert "alembic" in text


def test_postgres_integration_workflow_exists():
    workflow = REPO_ROOT / ".github" / "workflows" / "postgres-integration.yml"
    assert workflow.exists()

    text = workflow.read_text(encoding="utf-8")
    assert "services:" in text
    assert "postgres:" in text
    assert "alembic upgrade head" in text
    assert "tests/integration/test_postgres_integration.py" in text

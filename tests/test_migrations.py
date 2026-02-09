from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_scaffold_files_exist():
    assert (REPO_ROOT / "alembic.ini").exists()
    assert (REPO_ROOT / "migrations" / "env.py").exists()
    assert (REPO_ROOT / "migrations" / "script.py.mako").exists()


def test_initial_migration_defines_core_tables():
    initial_migration = REPO_ROOT / "migrations" / "versions" / "0001_initial_schema.py"
    assert initial_migration.exists()

    initial_text = initial_migration.read_text(encoding="utf-8")
    assert "workflow_runs" in initial_text
    assert "step_durations" in initial_text
    assert "test_durations" in initial_text
    assert "test_outcomes" in initial_text

from ci_hunter.migration_config import ENV_ALEMBIC_URL
from ci_hunter.migration_config import resolve_alembic_url


DEFAULT_URL = "postgresql://user:pass@localhost:5432/ci_hunter"
OVERRIDE_URL = "postgresql://postgres:postgres@127.0.0.1:5433/ci_hunter_test"


def test_resolve_alembic_url_prefers_env_override():
    env = {ENV_ALEMBIC_URL: OVERRIDE_URL}

    assert (
        resolve_alembic_url(DEFAULT_URL, env=env)
        == "postgresql+psycopg://postgres:postgres@127.0.0.1:5433/ci_hunter_test"
    )


def test_resolve_alembic_url_falls_back_to_default():
    assert (
        resolve_alembic_url(DEFAULT_URL, env={})
        == "postgresql+psycopg://user:pass@localhost:5432/ci_hunter"
    )


def test_resolve_alembic_url_trims_whitespace():
    env = {ENV_ALEMBIC_URL: f"  {OVERRIDE_URL}  "}

    assert (
        resolve_alembic_url(DEFAULT_URL, env=env)
        == "postgresql+psycopg://postgres:postgres@127.0.0.1:5433/ci_hunter_test"
    )


def test_resolve_alembic_url_uses_process_env_by_default(monkeypatch):
    monkeypatch.setenv(ENV_ALEMBIC_URL, OVERRIDE_URL)
    try:
        assert (
            resolve_alembic_url(DEFAULT_URL)
            == "postgresql+psycopg://postgres:postgres@127.0.0.1:5433/ci_hunter_test"
        )
    finally:
        monkeypatch.delenv(ENV_ALEMBIC_URL, raising=False)


def test_resolve_alembic_url_adds_psycopg_driver_to_postgresql_url():
    assert resolve_alembic_url(DEFAULT_URL, env={}) == "postgresql+psycopg://user:pass@localhost:5432/ci_hunter"


def test_resolve_alembic_url_adds_psycopg_driver_for_env_override():
    env = {ENV_ALEMBIC_URL: OVERRIDE_URL}
    assert (
        resolve_alembic_url(DEFAULT_URL, env=env)
        == "postgresql+psycopg://postgres:postgres@127.0.0.1:5433/ci_hunter_test"
    )


def test_resolve_alembic_url_preserves_explicit_postgresql_driver():
    explicit = "postgresql+psycopg://postgres:postgres@127.0.0.1:5433/ci_hunter_test"
    assert resolve_alembic_url(explicit, env={}) == explicit

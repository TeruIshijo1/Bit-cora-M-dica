from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from testing.database_guards import (  # noqa: E402
    UnsafeTestDatabaseError,
    validate_postgres_test_database,
)


def _reset_public_schema(database_url: str) -> None:
    validate_postgres_test_database(os.getenv("APP_ENV"), database_url)
    engine = create_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


def _upgrade_to_head() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(config, "head")


def pytest_sessionstart(session: pytest.Session) -> None:
    app_env = os.getenv("APP_ENV")
    if app_env != "test":
        raise pytest.UsageError(
            'Suite abortada: APP_ENV debe ser "test" antes de preparar PostgreSQL.'
        )

    container = None
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        try:
            from testcontainers.community.postgres import PostgresContainer

            container = PostgresContainer(
                "postgres:17-alpine",
                username="hes_test",
                password="synthetic-tests-only",
                dbname="hospital_escandon_test",
            )
            container.start()
            database_url = container.get_connection_url()
        except Exception as exc:
            if container is not None:
                container.stop()
            raise pytest.UsageError(
                "No fue posible iniciar Testcontainers. Configure TEST_DATABASE_URL "
                "hacia una base PostgreSQL dedicada que termine en _test."
            ) from exc

    try:
        validate_postgres_test_database(app_env, database_url)
    except UnsafeTestDatabaseError as exc:
        if container is not None:
            container.stop()
        raise pytest.UsageError(f"Suite abortada por protección anti-destrucción: {exc}") from exc

    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault("SECRET_KEY", "synthetic-test-secret-not-for-production")
    os.environ.setdefault("ALGORITHM", "HS256")
    os.environ["KH_DATABASE"] = "KH_HE_test"
    os.environ["KH_SERVER"] = "127.0.0.1,1"
    session.config._hes_test_container = container
    session.config._hes_test_database_url = database_url

    _reset_public_schema(database_url)
    _upgrade_to_head()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    database_url = getattr(session.config, "_hes_test_database_url", None)
    container = getattr(session.config, "_hes_test_container", None)
    if database_url:
        _reset_public_schema(database_url)
    if container is not None:
        container.stop()


@pytest.fixture(autouse=True)
def isolated_postgres_test() -> None:
    """Every test starts and ends with empty migrated tables."""
    database_url = os.environ["DATABASE_URL"]
    validate_postgres_test_database(os.getenv("APP_ENV"), database_url)
    engine = create_engine(database_url)

    def truncate() -> None:
        table_names = [
            name for name in inspect(engine).get_table_names() if name != "alembic_version"
        ]
        if not table_names:
            return
        quoted = ", ".join(f'"{name}"' for name in table_names)
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))

    truncate()
    try:
        yield
    finally:
        truncate()
        engine.dispose()

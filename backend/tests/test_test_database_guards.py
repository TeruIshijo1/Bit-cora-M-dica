from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from testing.database_guards import (
    UnsafeTestDatabaseError,
    validate_postgres_test_database,
    validate_sql_server_test_database,
)


@pytest.mark.parametrize("app_env", [None, "", "development", "production", "TEST", " test "])
def test_postgres_guard_rejects_non_test_environment(app_env: str | None) -> None:
    with pytest.raises(UnsafeTestDatabaseError):
        validate_postgres_test_database(
            app_env,
            "postgresql://user:pass@localhost/hospital_escandon_test",
        )


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///critical.db",
        "postgresql://user:pass@localhost/hospital_escandon_db",
        "postgresql://user:pass@localhost/postgres",
    ],
)
def test_postgres_guard_rejects_sqlite_and_operational_databases(database_url: str) -> None:
    with pytest.raises(UnsafeTestDatabaseError):
        validate_postgres_test_database("test", database_url)


def test_postgres_guard_accepts_explicit_test_database() -> None:
    assert (
        validate_postgres_test_database(
            "test", "postgresql+psycopg2://user:pass@localhost/hospital_escandon_test"
        )
        == "hospital_escandon_test"
    )


def test_sql_server_guard_rejects_production_kh_he() -> None:
    with pytest.raises(UnsafeTestDatabaseError):
        validate_sql_server_test_database("test", "KH_HE")


def test_sql_server_guard_accepts_only_test_target() -> None:
    assert validate_sql_server_test_database("test", "KH_HE_test") == "KH_HE_test"


def test_database_module_aborts_before_engine_for_operational_name() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql://unused:unused@127.0.0.1/hospital_escandon_db",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "import database"],
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert "no termina en _test" in (result.stdout + result.stderr)

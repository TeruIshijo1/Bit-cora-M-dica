from __future__ import annotations

import os

import pytest

from testing.database_guards import validate_sql_server_test_database


@pytest.fixture(scope="session", autouse=True)
def guarded_sql_server_staging_target() -> None:
    """Future SQL Server integration tests must pass this gate before connecting."""
    database = validate_sql_server_test_database(
        os.getenv("APP_ENV"), os.getenv("SQLSERVER_TEST_DATABASE")
    )
    os.environ["KH_DATABASE"] = database

"""Fail-closed validation for databases used by integration tests."""

from __future__ import annotations

import re

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


_TEST_DATABASE_RE = re.compile(r"(?:^|_)test(?:_[a-z0-9_]+)?$", re.IGNORECASE)


class UnsafeTestDatabaseError(RuntimeError):
    """Raised before a test can write to a database that is not isolated."""


def validate_postgres_test_database(app_env: str | None, database_url: str | None) -> str:
    """Return the database name only when the PostgreSQL target is test-only."""
    if app_env != "test":
        raise UnsafeTestDatabaseError('APP_ENV debe ser exactamente "test".')
    if not database_url:
        raise UnsafeTestDatabaseError("DATABASE_URL/TEST_DATABASE_URL es obligatoria.")

    try:
        parsed = make_url(database_url)
    except ArgumentError as exc:
        raise UnsafeTestDatabaseError("La URL de PostgreSQL de pruebas no es válida.") from exc

    if not parsed.drivername.startswith("postgresql"):
        raise UnsafeTestDatabaseError("Las pruebas críticas requieren PostgreSQL; SQLite está prohibido.")

    database = (parsed.database or "").strip()
    if not _TEST_DATABASE_RE.search(database):
        raise UnsafeTestDatabaseError(
            f'La base "{database or "<vacía>"}" no termina en _test (o sufijo de worker aprobado).'
        )
    return database


def validate_sql_server_test_database(app_env: str | None, database_name: str | None) -> str:
    """Reject KH_HE and any SQL Server database that is not explicitly test-only."""
    if app_env != "test":
        raise UnsafeTestDatabaseError('APP_ENV debe ser exactamente "test".')

    database = (database_name or "").strip()
    if database.upper() == "KH_HE":
        raise UnsafeTestDatabaseError("KH_HE productivo nunca puede ser destino de pruebas.")
    if not _TEST_DATABASE_RE.search(database):
        raise UnsafeTestDatabaseError("La base SQL Server debe terminar en _test.")
    return database

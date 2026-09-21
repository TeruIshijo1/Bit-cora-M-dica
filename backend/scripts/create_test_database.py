"""Create the dedicated local PostgreSQL test database without touching app data."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql
from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from testing.database_guards import validate_postgres_test_database  # noqa: E402


def main() -> int:
    app_env = os.getenv("APP_ENV")
    target_url = os.getenv("TEST_DATABASE_URL")
    admin_url = os.getenv("TEST_DATABASE_ADMIN_URL")
    database_name = validate_postgres_test_database(app_env, target_url)
    if not admin_url:
        raise RuntimeError("TEST_DATABASE_ADMIN_URL es obligatoria para crear la base dedicada.")

    parsed_admin = make_url(admin_url)
    if not parsed_admin.drivername.startswith("postgresql"):
        raise RuntimeError("TEST_DATABASE_ADMIN_URL debe apuntar a PostgreSQL.")

    connection = psycopg2.connect(
        host=parsed_admin.host,
        port=parsed_admin.port or 5432,
        dbname=parsed_admin.database or "postgres",
        user=parsed_admin.username,
        password=parsed_admin.password,
    )
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
                print(f'Base de pruebas "{database_name}" creada.')
            else:
                print(f'Base de pruebas "{database_name}" ya existe.')
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


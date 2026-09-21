"""Upgrade the dedicated local TEST database and run ``alembic check`` safely."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


def main() -> int:
    backend = Path(__file__).resolve().parents[1]
    load_dotenv(backend / ".env")
    source = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not source:
        raise SystemExit("Falta TEST_DATABASE_URL o DATABASE_URL local.")
    url = make_url(source)
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Alembic check sólo puede usar PostgreSQL TEST local.")
    database = url.database or ""
    if not database.endswith("_test"):
        database = f"{database.removesuffix('_db')}_test"
    test_url = url.set(database=database).render_as_string(hide_password=False)
    env = {**os.environ, "APP_ENV": "test", "TEST_DATABASE_URL": test_url, "DATABASE_URL": test_url}
    config = str(backend / "alembic.ini")
    for action in (["upgrade", "head"], ["check"]):
        subprocess.run(
            [sys.executable, "-m", "alembic", "-c", config, *action],
            cwd=backend.parent,
            env=env,
            check=True,
        )
    print("Alembic clean upgrade/check PASS sobre PostgreSQL TEST local.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

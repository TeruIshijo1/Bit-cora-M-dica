"""Run the PostgreSQL suite using a derived *local* test database URL.

The production/development database name is never used. This helper is only a
convenience for workstations without Docker and refuses non-loopback hosts.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pytest_args", nargs="*")
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    load_dotenv(backend / ".env")
    source = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not source:
        raise SystemExit("Falta TEST_DATABASE_URL o DATABASE_URL local.")
    url = make_url(source)
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Se rechazó derivar una base TEST desde un host no local.")
    database = url.database or ""
    if not database.endswith("_test"):
        database = f"{database.removesuffix('_db')}_test"
    test_url = url.set(database=database).render_as_string(hide_password=False)
    os.environ.update(APP_ENV="test", TEST_DATABASE_URL=test_url, DATABASE_URL=test_url)
    scratch = backend.parent / "scratch" / "pytest"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hes-", dir=scratch) as base_temp:
        command = [
            sys.executable, "-m", "pytest", "-q",
            "-p", "no:cacheprovider", "--basetemp", base_temp,
            *(args.pytest_args or []),
        ]
        return subprocess.call(command, cwd=backend.parent)


if __name__ == "__main__":
    raise SystemExit(main())

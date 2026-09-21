"""Explicit bounded reconciliation command for clinical SQL Server writes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal  # noqa: E402
import clinical_sync  # noqa: E402
import clinical_sync_adapters  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 200:
        parser.error("--limit debe estar entre 1 y 200")

    with SessionLocal() as session:
        results = clinical_sync.reconcile(
            session,
            clinical_sync_adapters.dispatcher,
            limit=args.limit,
            session_factory=SessionLocal,
        )
    for result in results:
        print(f"{result.operation_id} {result.state}")
    return 1 if any(item.state == clinical_sync.FAILED for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

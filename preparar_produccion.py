"""Validate and assemble a production release without operational secrets."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEPLOY_DIR = ROOT / "pase_a_produccion"
PYTHON = ROOT / "backend" / "venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)
NPM = shutil.which("npm") or "npm"
NPX = shutil.which("npx") or "npx"
NODE = shutil.which("node") or "node"


def run_gate(label: str, command: list[str], cwd: Path = ROOT) -> None:
    print(f"[GATE] {label}")
    subprocess.run(command, cwd=cwd, check=True)


def ignored(_directory: str, names: list[str]) -> list[str]:
    excluded_names = {
        ".env", ".git", ".pytest_cache", "__pycache__", "node_modules", "venv",
        "generados", "private_storage", "static", "artifacts", ".expo",
        "android", "ios",
    }
    return [
        name for name in names
        if name in excluded_names or name.endswith((".db", ".sqlite", ".pyc"))
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remove_readonly(function, path: str, _exc_info) -> None:
    """Remove only read-only entries inside the already validated output path."""
    os.chmod(path, stat.S_IWRITE)
    function(path)


def write_manifest() -> None:
    entries = []
    for path in sorted(DEPLOY_DIR.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256.json":
            entries.append({"path": path.relative_to(DEPLOY_DIR).as_posix(), "sha256": sha256(path)})
    (DEPLOY_DIR / "MANIFEST.sha256.json").write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    print("Bitácora HES — validación y paquete productivo")
    run_gate("pytest PostgreSQL TEST", [str(PYTHON), "backend/scripts/run_local_postgres_tests.py"])
    run_gate("Alembic clean/check", [str(PYTHON), "backend/scripts/run_local_alembic_check.py"])
    run_gate("Python compileall", [str(PYTHON), "-m", "compileall", "-q", "backend"])
    run_gate("scanner de secretos", [str(PYTHON), "backend/scripts/scan_secrets.py"])
    run_gate("inventario de autorización", [str(PYTHON), "backend/scripts/audit_route_authorization.py"])
    run_gate("frontend runtime lint", [NPM, "run", "lint:runtime"], ROOT / "frontend")
    run_gate("frontend build", [NPM, "run", "build"], ROOT / "frontend")
    run_gate(
        "frontend runtime audit HIGH+",
        [NPM, "audit", "--omit=dev", "--audit-level=high"],
        ROOT / "frontend",
    )
    run_gate("mobile typecheck", [NPX, "tsc", "--noEmit"], ROOT / "mobile_app")
    run_gate(
        "mobile runtime audit HIGH+",
        [NPM, "audit", "--omit=dev", "--audit-level=high"],
        ROOT / "mobile_app",
    )
    run_gate("biometric-service syntax", [NODE, "--check", "server.js"], ROOT / "biometric-service")
    run_gate(
        "biometric-service runtime audit HIGH+",
        [NPM, "audit", "--omit=dev", "--audit-level=high"],
        ROOT / "biometric-service",
    )

    if DEPLOY_DIR.resolve().parent != ROOT.resolve():
        raise RuntimeError("Directorio de paquete fuera del workspace")
    if DEPLOY_DIR.exists():
        shutil.rmtree(DEPLOY_DIR, onexc=remove_readonly)
    DEPLOY_DIR.mkdir()

    shutil.copytree(ROOT / "frontend" / "dist", DEPLOY_DIR / "frontend" / "dist")
    shutil.copytree(ROOT / "backend", DEPLOY_DIR / "backend", ignore=ignored)
    logo = ROOT / "backend" / "static" / "logo.png"
    if logo.exists():
        (DEPLOY_DIR / "backend" / "static").mkdir(parents=True, exist_ok=True)
        shutil.copy(logo, DEPLOY_DIR / "backend" / "static" / "logo.png")
    shutil.copytree(ROOT / "biometric-service", DEPLOY_DIR / "biometric-service", ignore=ignored)
    shutil.copytree(ROOT / "deploy", DEPLOY_DIR / "deploy", ignore=ignored)
    shutil.copytree(ROOT / "scripts", DEPLOY_DIR / "scripts", ignore=ignored)
    shutil.copytree(ROOT / "Formatos VERTICAL", DEPLOY_DIR / "Formatos VERTICAL", ignore=ignored)
    if (ROOT / "plantillas").exists():
        shutil.copytree(ROOT / "plantillas", DEPLOY_DIR / "plantillas", ignore=ignored)
    shutil.copy(ROOT / "PREPRODUCCION_TECNICA_FINAL.md", DEPLOY_DIR)
    write_manifest()
    print(f"Paquete validado: {DEPLOY_DIR}")
    print("El paquete no contiene .env, datos clínicos, seeds automáticos ni servidor --reload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

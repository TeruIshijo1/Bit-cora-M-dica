"""Destructive restore drill restricted to two local databases ending in _test."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from psycopg2 import connect, sql

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _tool(name: str) -> str:
    configured = os.getenv("POSTGRES_BIN")
    candidates = [Path(configured) / f"{name}.exe"] if configured else []
    candidates += [Path(r"C:\Program Files\PostgreSQL\17\bin") / f"{name}.exe"]
    found = shutil.which(name)
    if found:
        return found
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError(f"No se encontró {name}.")


def _safe_urls() -> tuple[str, str]:
    backend = Path(__file__).resolve().parents[1]
    load_dotenv(backend / ".env")
    source = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not source:
        raise RuntimeError("Falta TEST_DATABASE_URL o DATABASE_URL local.")
    url = make_url(source)
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("El restore drill sólo permite PostgreSQL local.")
    source_db = url.database or ""
    if not source_db.endswith("_test"):
        source_db = f"{source_db.removesuffix('_db')}_test"
    restore_db = f"{source_db.removesuffix('_test')}_restore_test"
    source_url = url.set(database=source_db).render_as_string(hide_password=False)
    restore_url = url.set(database=restore_db).render_as_string(hide_password=False)
    return source_url, restore_url


def _prepare_synthetic_evidence(source_url: str) -> dict:
    os.environ.update(
        APP_ENV="test", DATABASE_URL=source_url, TEST_DATABASE_URL=source_url,
        SECRET_KEY=os.getenv("SECRET_KEY", "synthetic-test-secret-not-for-production"),
        HES_HMAC_SECRET="synthetic-restore-drill-hmac-secret-32chars",
    )
    import clinical_signing
    import crypto_fea
    import models

    Session = sessionmaker(bind=create_engine(source_url))
    with Session() as db:
        existing_doctor = db.query(models.Medico).filter_by(numero_empleado="RESTORE-SYNTHETIC").first()
        existing_operation = db.query(models.ClinicalSyncOperation).filter_by(idempotency_key="restore-drill-idempotency").first()
        if existing_doctor and existing_operation:
            existing_key = db.query(models.HistorialLlaveFEA).filter_by(medico_id=existing_doctor.id, activo=True).one()
            existing_signature = db.query(models.FirmaDocumentoClinico).filter_by(medico_id=existing_doctor.id, signature_schema_version="CANONICAL_V2").one()
            return {"signature_id": existing_signature.id, "key_id": existing_key.key_id, "public_key": existing_key.public_key_pem}
        doctor = models.Medico(
            numero_empleado="RESTORE-SYNTHETIC", nombre_completo="SYNTHETIC RESTORE DOCTOR",
            especialidad="TEST", cedula="SYNTHETIC-0001", huella_token=str(uuid.uuid4()),
            fmd_template="SYNTHETIC_FMD_NON_BIOMETRIC", biometric_status="FMD_VALIDO",
            activo_status=True,
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        crypto_fea.ensure_medico_keys(db, doctor)
        key = crypto_fea.get_active_key(db, doctor)
        signed_at = dt.datetime.now(dt.timezone.utc)
        document = clinical_signing.ClinicalDocument(
            tipo_documento="RESTORE_DRILL", contenido_clinico={"synthetic": True},
            version_documento="1", source_identifier="restore-drill-1",
        )
        _, payload_bytes, payload_hash, _ = clinical_signing.build_canonical_payload(
            document=document, codigo_formato="TEST-RESTORE", pt_num="SYNTHETIC-PT",
            expediente="SYNTHETIC-EXP", evolution_slot=0,
            patient_identity={"synthetic": True}, medico_id=doctor.id,
            nombre_medico=doctor.nombre_completo, cedula=doctor.cedula,
            proposito="RESTORE_DRILL", signed_at=signed_at, key_id=key.key_id,
        )
        signature_result = crypto_fea.firmar_documento_con_key_id(db, doctor, payload_bytes)
        signature = models.FirmaDocumentoClinico(
            tipo_documento="RESTORE_DRILL", codigo_formato="TEST-RESTORE",
            pt_num="SYNTHETIC-PT", expediente="SYNTHETIC-EXP", evolution_slot=0,
            medico_id=doctor.id, nombre_medico=doctor.nombre_completo,
            cedula_profesional=doctor.cedula, fecha_hora_firma=signed_at.replace(tzinfo=None),
            hash_sha256=payload_hash, sello_digital=signature_result.sello_digital,
            cadena_original=payload_bytes.decode("utf-8"), key_id=key.key_id,
            signature_schema_version="CANONICAL_V2", canonical_payload=payload_bytes.decode("utf-8"),
            payload_hash=payload_hash, document_version="1", tsa_status="SIN_TSA", estado="ACTIVA",
        )
        operation = models.ClinicalSyncOperation(
            idempotency_key="restore-drill-idempotency", operation_type="RESTORE_DRILL",
            aggregate_type="synthetic", aggregate_id="restore-drill-1",
            patient_ref="SYNTHETIC-PT", payload={"synthetic": True},
            request_fingerprint=clinical_sync.request_fingerprint(
                operation_type="RESTORE_DRILL", aggregate_type="synthetic",
                aggregate_id="restore-drill-1", patient_ref="SYNTHETIC-PT",
                payload={"synthetic": True},
            ),
            state="RETRYABLE_ERROR",
        )
        db.add_all([signature, operation])
        db.commit()
        return {"signature_id": signature.id, "key_id": key.key_id, "public_key": key.public_key_pem}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-destructive-test-restore", action="store_true", required=True)
    parser.add_argument("--output-dir", default="artifacts/restore-drill")
    args = parser.parse_args()
    source_url, restore_url = _safe_urls()
    os.environ.update(APP_ENV="test", DATABASE_URL=source_url, TEST_DATABASE_URL=source_url)
    backend_dir = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "-m", "alembic", "-c", str(backend_dir / "alembic.ini"), "upgrade", "head"], cwd=backend_dir, check=True)
    evidence = _prepare_synthetic_evidence(source_url)
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    dump_file = output / "hes_restore_drill.dump"
    pg_dump, pg_restore = _tool("pg_dump"), _tool("pg_restore")

    backup_started = time.perf_counter()
    subprocess.run([pg_dump, "--dbname", source_url, "--format=custom", "--compress=9", "--no-owner", "--no-acl", "--file", str(dump_file)], check=True)
    subprocess.run([pg_restore, "--list", str(dump_file)], check=True, stdout=subprocess.DEVNULL)
    backup_seconds = time.perf_counter() - backup_started
    dump_hash = hashlib.sha256(dump_file.read_bytes()).hexdigest()

    source = make_url(source_url)
    restore = make_url(restore_url)
    admin_dsn = source.set(database="postgres").render_as_string(hide_password=False)
    admin = connect(admin_dsn)
    try:
        admin.set_isolation_level(0)
        with admin.cursor() as cursor:
            cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (restore.database,))
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(restore.database)))
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(restore.database)))
    finally:
        admin.close()

    restore_started = time.perf_counter()
    subprocess.run([pg_restore, "--dbname", restore_url, "--no-owner", "--no-acl", str(dump_file)], check=True)
    restore_seconds = time.perf_counter() - restore_started

    os.environ["DATABASE_URL"] = restore_url
    import clinical_signing
    import models
    Session = sessionmaker(bind=create_engine(restore_url))
    with Session() as db:
        signature = db.query(models.FirmaDocumentoClinico).filter_by(id=evidence["signature_id"]).one()
        key = db.query(models.HistorialLlaveFEA).filter_by(key_id=evidence["key_id"]).one()
        operation = db.query(models.ClinicalSyncOperation).filter_by(idempotency_key="restore-drill-idempotency").one()
        verification = clinical_signing.verify_signature_record(db, signature)
        table_count = len(models.Base.metadata.tables)
        result = {
            "backup_seconds": round(backup_seconds, 3), "restore_seconds": round(restore_seconds, 3),
            "dump_sha256": dump_hash, "dump_bytes": dump_file.stat().st_size,
            "pg_restore_list_verified": True, "table_count_expected": table_count,
            "canonical_v2_verified": bool(verification["complete"]),
            "historical_public_key_verified": key.public_key_pem == evidence["public_key"],
            "clinical_sync_state_verified": operation.state == "RETRYABLE_ERROR",
            "synthetic_only": True,
        }
    if not all((result["canonical_v2_verified"], result["historical_public_key_verified"], result["clinical_sync_state_verified"])):
        raise RuntimeError(f"Restore drill inconsistente: {result}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

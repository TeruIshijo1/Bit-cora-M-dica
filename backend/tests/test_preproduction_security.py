from __future__ import annotations

import datetime
import io
import json
import os

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

import file_storage
import main
import models
import security
from app_config import ConfigurationError, load_settings
from database import SessionLocal
from services import pdf_service


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _user(db: Session) -> models.Usuario:
    user = models.Usuario(
        username="security-test",
        nombre_completo="Synthetic Security User",
        password_hash=security.get_password_hash("Valid-Temporary-123!"),
        rol="admin",
        activo=True,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_new_access_tokens_have_unique_jti_issuer_and_audience():
    first = security.create_access_token({"sub": "security-test", "rol": "admin"})
    second = security.create_access_token({"sub": "security-test", "rol": "admin"})
    first_claims = security.jwt.get_unverified_claims(first)
    second_claims = security.jwt.get_unverified_claims(second)
    assert first_claims["jti"] != second_claims["jti"]
    assert first_claims["iss"] == security.SETTINGS.jwt_issuer
    assert first_claims["aud"] == security.SETTINGS.jwt_audience


def test_revoked_token_is_rejected_immediately(db):
    user = _user(db)
    token = security.create_access_token({"sub": user.username, "rol": user.rol})
    claims = security.jwt.get_unverified_claims(token)
    db.add(models.RevokedToken(
        jti=claims["jti"], subject=user.username,
        expires_at=datetime.datetime.fromtimestamp(claims["exp"], tz=datetime.timezone.utc),
        reason="TEST",
    ))
    db.commit()
    with pytest.raises(HTTPException) as exc:
        security.authenticate_token(token, db)
    assert exc.value.status_code == 401


def test_audit_table_rejects_update_and_delete(db):
    user = _user(db)
    entry = models.AuditoriaLog(
        usuario_id=user.id, accion="SYNTHETIC_APPEND_ONLY", detalles_json="{}",
        request_id="test-request-append-only", actor_real=f"admin:{user.id}",
        actor_effective=f"admin:{user.id}", resultado="EXITO",
    )
    db.add(entry)
    db.commit()
    entry.accion = "MUTATED"
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()
    with pytest.raises(DBAPIError):
        db.query(models.AuditoriaLog).filter_by(id=entry.id).delete(synchronize_session=False)
        db.commit()
    db.rollback()


def test_production_configuration_fails_closed_on_wildcards(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "A-cryptographically-random-secret-123456789")
    monkeypatch.setenv("HES_HMAC_SECRET", "B-cryptographically-random-secret-123456789")
    monkeypatch.setenv("BIOMETRIC_ATTESTATION_SECRET", "C-cryptographically-random-secret-123456789")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db/hospital")
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("ALLOWED_HOSTS", "*")
    monkeypatch.setenv("PROXY_HTTPS_ENABLED", "true")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_upload_content_validation_rejects_active_and_spoofed_files():
    for payload in (b"<svg onload=alert(1)></svg>", b"%PDF-not-a-real-document", b"MZfake.exe"):
        with pytest.raises(HTTPException):
            file_storage.validate_document(payload)


def test_upload_validation_accepts_real_png_and_server_generates_name(tmp_path):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="white").save(buffer, format="PNG")
    validated = file_storage.validate_photo(buffer.getvalue())
    stored_name, stored_path = file_storage.store_private(str(tmp_path), "photos", validated)
    assert stored_name.endswith(".png")
    assert ".." not in stored_name
    assert os.path.isfile(stored_path)


def test_disk_failure_does_not_leave_partial_upload(monkeypatch, tmp_path):
    validated = file_storage.ValidatedUpload(b"synthetic", ".pdf", "application/pdf")
    monkeypatch.setattr(file_storage.os, "replace", lambda *_args: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        file_storage.store_private(str(tmp_path), "documents", validated)
    assert not list((tmp_path / "documents").glob("*.pdf"))


def test_readiness_fails_closed_when_postgresql_is_down(monkeypatch):
    class DownEngine:
        def connect(self):
            raise ConnectionError("synthetic PostgreSQL outage")

    class Disk:
        free = 10 * 1024 * 1024 * 1024

    monkeypatch.setattr(main, "engine", DownEngine())
    monkeypatch.setattr(main.kh_database, "check_tcp_reachable", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(main.requests, "get", lambda *_args, **_kwargs: (_ for _ in ()).throw(main.requests.RequestException("synthetic")))
    monkeypatch.setattr(main.shutil, "disk_usage", lambda _path: Disk())
    response = main.readiness()
    payload = json.loads(response.body)
    assert response.status_code == 503
    assert payload["status"] == "not_ready"
    assert payload["components"]["postgresql"]["status"] == "unavailable"
    assert "synthetic PostgreSQL outage" not in response.body.decode()


def test_pdf_generation_failure_never_returns_a_document(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_service, "STATIC_PDFS_DIR", str(tmp_path))
    monkeypatch.setattr(
        pdf_service.pdf_engine_32_01,
        "generate_consentimiento_32_01",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("synthetic renderer failure")),
    )
    with pytest.raises(OSError):
        pdf_service.generate_consentimiento_32_01_pdf("SYNTHETIC", {"nombre": "TEST"})
    assert not list(tmp_path.glob("*.pdf"))

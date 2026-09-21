from __future__ import annotations

import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from starlette.requests import Request

import clinical_sync
import database
import main
import models
import vertical_signer


pytestmark = pytest.mark.postgresql


def _request(path: str = "/test") -> Request:
    request = Request({"type": "http", "method": "POST", "path": path, "headers": []})
    request.state.request_id = "af-regression-request"
    return request


def _auth_headers(username: str, role: str) -> dict[str, str]:
    token = main.create_access_token({"sub": username, "rol": role})
    return {"Authorization": f"Bearer {token}"}


def test_af01_public_verification_rejects_enumerable_patient_folio(monkeypatch):
    monkeypatch.setattr(
        main.kh_database,
        "fetch_full_ehr_dashboard",
        lambda *_: {"patient": {"name": "NOMBRE CLINICO NO PUBLICO", "mrn": "7777", "age": "49"}},
    )
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.get("/verificar?pt=7777&doc=PLT-11")
    assert response.status_code in {400, 404}
    assert "NOMBRE CLINICO NO PUBLICO" not in response.text


def test_af01_non_clinical_role_cannot_read_ehr_or_signatures(monkeypatch):
    with database.SessionLocal() as db:
        db.add(models.Usuario(username="limpieza-af", password_hash="x", rol="limpieza", activo=True))
        patient = models.Paciente(nombre_completo="PACIENTE AF", codigo_barras="7777")
        db.add(patient)
        db.flush()
        db.add(
            models.FirmaDocumentoClinico(
                tipo_documento="AF",
                codigo_formato="AF-01",
                pt_num="7777",
                evolution_slot=1,
                rol_firmante="MEDICO",
                cadena_original="CONTENIDO-CLINICO-NO-PUBLICO",
                estado="ACTIVA",
            )
        )
        db.commit()
    monkeypatch.setattr(
        main.kh_database,
        "fetch_full_ehr_dashboard",
        lambda *_: {"patient": {"name": "PACIENTE AF"}, "timelineEvents": []},
    )
    headers = _auth_headers("limpieza-af", "limpieza")
    with TestClient(main.app, raise_server_exceptions=False) as client:
        ehr = client.get("/api/ehr/paciente/7777", headers=headers)
        signatures = client.get("/api/ehr/paciente/7777/firmas", headers=headers)
    assert ehr.status_code == 403
    assert signatures.status_code == 403
    assert "CONTENIDO-CLINICO-NO-PUBLICO" not in signatures.text


def test_af03_same_administrative_actor_cannot_reenrol_and_rotate_fea(monkeypatch):
    with database.SessionLocal() as db:
        actor = models.Usuario(username="rh-af03", password_hash="x", rol="rh", activo=True)
        doctor = models.Medico(
            numero_empleado="AF03",
            nombre_completo="MEDICO AF03",
            cedula="AF03-CED",
            activo_status=True,
            requiere_actualizacion_fea=True,
        )
        db.add_all([actor, doctor])
        db.commit()
        db.refresh(actor)
        db.refresh(doctor)
        # This is persisted by the remediation; assigning it here reproduces the
        # missing separation even against the pre-remediation ORM model.
        doctor.biometric_reenrolled_by_id = actor.id
        monkeypatch.setattr(main, "verificar_huella_medico", lambda **_: doctor)
        with pytest.raises(HTTPException) as exc:
            main.completar_actualizacion_fea(
                doctor.id,
                main.schemas.FEAKeyRotationRequest(
                    fmd_template="FMD-B",
                    challenge_id="challenge-b",
                    session_id="session-b",
                    motivo="Reenrolamiento AF-03",
                ),
                _request(),
                db,
                actor,
            )
    assert exc.value.status_code == 403


def test_af03_reenrol_rotation_and_login_require_two_administrative_actors(monkeypatch):
    with database.SessionLocal() as db:
        reenroller = models.Usuario(username="rh-af03-a", password_hash="x", rol="rh", activo=True)
        approver = models.Usuario(username="rh-af03-b", password_hash="x", rol="rh", activo=True)
        doctor = models.Medico(
            numero_empleado="AF03-E2E",
            nombre_completo="MEDICO AF03 E2E",
            cedula="AF03-E2E-CED",
            activo_status=True,
            biometric_status="FMD_VALIDO",
            fmd_template="old-template",
        )
        db.add_all([reenroller, approver, doctor])
        db.commit()
        db.refresh(reenroller)
        db.refresh(approver)
        db.refresh(doctor)

        capture = main.biometric_security.AttestedCapture(
            canonical="new-template",
            acquisition_id="acq_AF03_e2e_1234567890",
            acquisition_started_at=datetime.datetime.now(datetime.timezone.utc),
            captured_at=datetime.datetime.now(datetime.timezone.utc),
        )
        monkeypatch.setattr(
            main.biometric_security,
            "validate_attested_capture_evidence",
            lambda *_: capture,
        )
        monkeypatch.setattr(main, "validate_and_consume_challenge", lambda *_a, **_k: None)
        main.reenrolar_medico(
            doctor.id,
            main.schemas.BiometricEnrollmentRequest(
                fmd_template="attested-new-template",
                challenge_id="challenge-af03",
                session_id="session-af03",
                motivo="Reenrolamiento controlado AF03",
            ),
            _request(),
            db,
            reenroller,
        )
        assert doctor.requiere_actualizacion_fea is True
        assert doctor.biometric_reenrolled_by_id == reenroller.id

        monkeypatch.setattr(main, "verificar_huella_medico", lambda **_: doctor)
        login_request = main.schemas.LoginBiometricRequest(
            fmd_template="new-template",
            medico_id=doctor.id,
            challenge_id="login-af03",
            session_id="login-session-af03",
        )
        with pytest.raises(HTTPException) as blocked_login:
            main.login_biometric(_request(), login_request, db)
        assert blocked_login.value.status_code == 423

        rotation_request = main.schemas.FEAKeyRotationRequest(
            fmd_template="new-template",
            challenge_id="rotate-af03",
            session_id="rotate-session-af03",
            motivo="Rotación FEA posterior a reenrolamiento",
        )
        with pytest.raises(HTTPException) as same_actor:
            main.completar_actualizacion_fea(
                doctor.id, rotation_request, _request(), db, reenroller
            )
        assert same_actor.value.status_code == 403

        def _rotate(_db, target, **_kwargs):
            target.requiere_actualizacion_fea = False
            return "AF03-NEW-KEY"

        monkeypatch.setattr(main.crypto_fea, "rotate_medico_key", _rotate)
        result = main.completar_actualizacion_fea(
            doctor.id, rotation_request, _request(), db, approver
        )
        assert result["estado"] == "ROTACION_FEA_COMPLETADA"
        login = main.login_biometric(_request(), login_request, db)
        assert login["medico_id"] == doctor.id
        assert login["rol"] == "medico"


def test_af04_completed_signature_snapshot_is_database_immutable():
    with database.SessionLocal() as db:
        signature = models.FirmaDocumentoClinico(
            tipo_documento="AF04",
            codigo_formato="AF-04",
            pt_num="P-AF04",
            evolution_slot=1,
            rol_firmante="MEDICO",
            canonical_payload='{"signed":true}',
            payload_hash="a" * 64,
            hash_sha256="a" * 64,
            sello_digital="ECDSA:AF04",
            signature_schema_version="CANONICAL_V2",
            document_version="1",
            estado="ACTIVA",
        )
        db.add(signature)
        db.commit()
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE firmas_documentos_clinicos "
                    "SET canonical_payload = :payload WHERE id = :id"
                ),
                {"id": signature.id, "payload": '{"tampered":true}'},
            )
            db.commit()
        db.rollback()


def test_af04_firma_id_must_belong_to_requested_document(monkeypatch):
    with database.SessionLocal() as db:
        signature = models.FirmaDocumentoClinico(
            tipo_documento="OTRO",
            codigo_formato="OTRO-FORMATO",
            pt_num="OTRO-PACIENTE",
            evolution_slot=4,
            estado="ACTIVA",
        )
        db.add(signature)
        db.commit()
        db.refresh(signature)
        monkeypatch.setattr(main, "get_or_create_paciente_by_identifier", lambda *_a, **_k: None)
        with pytest.raises(HTTPException) as exc:
            main.verificar_integridad_documento(
                "PACIENTE-SOLICITADO",
                main.VerificarIntegridadInputSchema(
                    firma_id=signature.id,
                    codigo_formato="FORMATO-SOLICITADO",
                    slot=999,
                ),
                _request(),
                db,
            )
    assert exc.value.status_code in {404, 409}


def test_af04_public_slot_999_never_falls_back_to_slot_1():
    opaque_id = "v1_" + ("A" * 43)
    with database.SessionLocal() as db:
        db.add(
            models.DocumentoVerificacionQR(
                doc_uuid=opaque_id,
                pt_num="P-AF04-SLOT",
                expediente="PROTECTED",
                codigo_formato="AF-04-SLOT",
                tipo_documento="PRUEBA SLOT EXACTO",
                slot=999,
                pdf_path="unused.pdf",
                activo=True,
            )
        )
        db.add(
            models.FirmaDocumentoClinico(
                tipo_documento="AF04",
                codigo_formato="AF-04-SLOT",
                pt_num="P-AF04-SLOT",
                evolution_slot=1,
                rol_firmante="MEDICO",
                estado="ACTIVA",
            )
        )
        db.commit()
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/verificar/documento-estado?id={opaque_id}")
    assert response.status_code == 200, response.text
    assert response.json()["valido"] is False
    assert response.json()["estado"] == "SIN_FIRMA"
    assert response.json()["slot"] == 999


def test_af05_database_allows_only_one_active_signature_per_logical_document():
    with database.SessionLocal() as db:
        common = {
            "tipo_documento": "AF05",
            "codigo_formato": "AF-05",
            "pt_num": "P-AF05",
            "evolution_slot": 1,
            "rol_firmante": "MEDICO",
            "document_version": "1",
            "estado": "ACTIVA",
        }
        db.add_all([models.FirmaDocumentoClinico(**common), models.FirmaDocumentoClinico(**common)])
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_af05_two_concurrent_signatures_yield_one_active_record():
    barrier = threading.Barrier(2)

    def _sign(attempt: int) -> str:
        with database.SessionLocal() as db:
            db.add(
                models.FirmaDocumentoClinico(
                    tipo_documento="AF05-CONCURRENT",
                    codigo_formato="AF-05-CONCURRENT",
                    pt_num="P-AF05-CONCURRENT",
                    evolution_slot=1,
                    rol_firmante="MEDICO",
                    document_version="1",
                    cadena_original=f"attempt-{attempt}",
                    estado="ACTIVA",
                )
            )
            barrier.wait(timeout=5)
            try:
                db.commit()
                return "created"
            except IntegrityError:
                db.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(_sign, (1, 2)))
    assert sorted(outcomes) == ["conflict", "created"]
    with database.SessionLocal() as db:
        active = db.query(models.FirmaDocumentoClinico).filter_by(
            codigo_formato="AF-05-CONCURRENT",
            pt_num="P-AF05-CONCURRENT",
            evolution_slot=1,
            rol_firmante="MEDICO",
            document_version="1",
            estado="ACTIVA",
        ).count()
    assert active == 1


def test_af05_two_concurrent_http_signatures_with_distinct_keys_leave_one_active(monkeypatch):
    with database.SessionLocal() as db:
        doctor = models.Medico(
            numero_empleado="AF05-HTTP",
            nombre_completo="MEDICO AF05 HTTP",
            cedula="AF05-HTTP-CED",
            activo_status=True,
            biometric_status="FMD_VALIDO",
            fmd_template="FMD-AF05",
            huella_token="TOKEN-AF05-HTTP",
        )
        patient = models.Paciente(
            nombre_completo="PACIENTE AF05 HTTP",
            codigo_barras="P-AF05-HTTP",
            status_ingreso="Ingresado",
        )
        db.add_all([doctor, patient])
        db.commit()
        db.refresh(doctor)
        crypto_key = main.crypto_fea.get_active_key(db, doctor)
        doctor_id = doctor.id
        doctor_cedula = doctor.cedula
        assert crypto_key.activo is True

    load_barrier = threading.Barrier(2)
    document = main.clinical_signing.ClinicalDocument(
        tipo_documento="AF05 HTTP",
        contenido_clinico={"content": "same logical document"},
        version_documento="1",
        source_identifier="AF05:HTTP:1",
    )

    def _matched_doctor(**kwargs):
        return kwargs["db"].query(models.Medico).filter_by(id=doctor_id).one()

    def _load_document(*_args, **_kwargs):
        load_barrier.wait(timeout=10)
        return document, {"codigo_barras": "P-AF05-HTTP"}

    monkeypatch.setattr(main, "verificar_huella_medico", _matched_doctor)
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: None)
    monkeypatch.setattr(main.clinical_signing, "load_authoritative_document", _load_document)
    monkeypatch.setattr(main.tsa_client, "get_timestamp", lambda *_: None)
    monkeypatch.setattr(main, "_resolve_vertical_sign_target", lambda *_: ("AF05", 1))
    monkeypatch.setattr(main.clinical_sync_adapters, "dispatcher", lambda *_: (lambda: True))

    def _post(attempt: int):
        with TestClient(main.app, raise_server_exceptions=False) as client:
            return client.post(
                "/api/ehr/paciente/P-AF05-HTTP/firmar-biometrico",
                headers={
                    **_auth_headers(doctor_cedula, "medico"),
                    "Idempotency-Key": f"AF05-http-{attempt}",
                },
                json={
                    "codigo_formato": "AF-05-HTTP",
                    "tipo_documento": "AF05 HTTP",
                    "evolution_slot": 1,
                    "fmd_template": f"FMD-AF05-{attempt}",
                    "medico_id": doctor_id,
                    "challenge_id": f"challenge-af05-{attempt}",
                    "session_id": f"session-af05-{attempt}",
                },
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(_post, (1, 2)))
    assert all(response.status_code in {200, 409} for response in responses), [
        (response.status_code, response.text) for response in responses
    ]
    with database.SessionLocal() as db:
        active = db.query(models.FirmaDocumentoClinico).filter_by(
            codigo_formato="AF-05-HTTP",
            pt_num="P-AF05-HTTP",
            evolution_slot=1,
            rol_firmante="MEDICO",
            document_version="1",
            estado="ACTIVA",
        ).all()
    assert len(active) == 1


class _VerticalResponse:
    status_code = 200
    text = "{}"

    def json(self):
        return {}


class _VerticalSession:
    def post(self, *_args, **_kwargs):
        return _VerticalResponse()


class _VerticalCursor:
    def __init__(self, writes: list[str]):
        self.sql = ""
        self.writes = writes

    def execute(self, sql, *_args):
        self.sql = str(sql)
        if self.sql.lstrip().upper().startswith("UPDATE "):
            self.writes.append(self.sql)

    def fetchone(self):
        sql = self.sql.upper()
        if "FROM V_MRPT" in sql:
            return ("PC", 1, "00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002")
        if "FROM PC" in sql:
            return (1,)
        if "INFORMATION_SCHEMA.COLUMNS" in sql and "LIKE 'MRNUM%'" in sql:
            return ("MRNum_AF06",)
        if "SELECT SIGNEDBY" in sql:
            return (None, "RG")
        if "COLUMN_NAME = 'ESIGNATURE'" in sql:
            return ("ESignature",)
        return None

    def fetchall(self):
        row = self.fetchone()
        return [row] if row else []


class _VerticalConnection:
    def __init__(self, writes: list[str]):
        self.writes = writes

    def cursor(self):
        return _VerticalCursor(self.writes)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def test_af06_http_200_empty_json_never_confirms_vertical(monkeypatch):
    writes: list[str] = []
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: _VerticalConnection(writes))
    monkeypatch.setattr(vertical_signer, "get_vertical_session", lambda **_: _VerticalSession())
    with pytest.raises(RuntimeError):
        vertical_signer.sign_in_vertical_api(
            "MR_AF06",
            1,
            "7777",
            pr_num=1,
            auth_code="synthetic",
            doctor_name="MEDICO AF06",
            operation_id="af06-operation",
        )
    assert writes == []


def test_af08_same_idempotency_key_with_different_request_is_conflict():
    with database.SessionLocal() as db:
        first, created = clinical_sync.create_or_get_intent(
            db,
            idempotency_key="AF08:same-key",
            operation_type="AF08",
            aggregate_type="patient",
            aggregate_id="A",
            patient_ref="PATIENT-A",
            payload={"value": "A"},
        )
        assert created is True
        with pytest.raises(Exception) as exc:
            clinical_sync.create_or_get_intent(
                db,
                idempotency_key="AF08:same-key",
                operation_type="AF08",
                aggregate_type="patient",
                aggregate_id="B",
                patient_ref="PATIENT-B",
                payload={"value": "B"},
            )
    assert getattr(exc.value, "error_code", None) == "IDEMPOTENCY_KEY_CONFLICT"


def test_af08_http_layer_returns_409_for_different_request_same_key():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/af08",
        "headers": [(b"idempotency-key", b"same-http-key")],
    }
    request = Request(scope)
    with database.SessionLocal() as db:
        main._clinical_sync_intent(
            db,
            request,
            operation_type="AF08_HTTP",
            aggregate_type="patient",
            aggregate_id="A",
            patient_ref="PATIENT-A",
            payload={"value": "A"},
        )
        with pytest.raises(HTTPException) as exc:
            main._clinical_sync_intent(
                db,
                request,
                operation_type="AF08_HTTP",
                aggregate_type="patient",
                aggregate_id="B",
                patient_ref="PATIENT-B",
                payload={"value": "B"},
            )
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "IDEMPOTENCY_KEY_CONFLICT"


class _PatientCursor:
    def execute(self, *_args, **_kwargs):
        return None

    def fetchone(self):
        return (99991, "PACIENTE ERP AF09", "CAMA-9")


class _PatientConnection:
    def cursor(self):
        return _PatientCursor()

    def close(self):
        return None


def test_af09_allow_create_false_prevents_insert_and_update(monkeypatch):
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: _PatientConnection())
    with database.SessionLocal() as db:
        before = db.query(models.Paciente).count()
        patient = main.get_or_create_paciente_by_identifier(db, "99991", allow_create=False)
        db.expire_all()
        after = db.query(models.Paciente).count()
    assert patient is None
    assert after == before


def test_af09_get_signatures_does_not_create_erp_patient(monkeypatch):
    with database.SessionLocal() as db:
        db.add(models.Usuario(username="nurse-af09", password_hash="x", rol="enfermeria", activo=True))
        db.commit()
        before = db.query(models.Paciente).count()
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: _PatientConnection())
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/ehr/paciente/99991/firmas",
            headers=_auth_headers("nurse-af09", "enfermeria"),
        )
    assert response.status_code == 200, response.text
    with database.SessionLocal() as db:
        assert db.query(models.Paciente).count() == before


def test_af09_get_pdf_does_not_persist_qr_or_generated_file(monkeypatch):
    import pdf_engine_32_01

    pt_num = "99992"
    pdf_path = Path(main.__file__).resolve().parent / "static" / "pdfs" / f"consentimiento_32_01_{pt_num}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    monkeypatch.setattr(
        main.kh_database,
        "fetch_full_ehr_dashboard",
        lambda *_: {"patient": {"name": "PACIENTE AF09", "mrn": pt_num}},
    )

    def _generate(_data, output_path, **_kwargs):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"%PDF-1.4\n%%EOF\n")

    monkeypatch.setattr(pdf_engine_32_01, "generate_consentimiento_32_01", _generate)
    with database.SessionLocal() as db:
        db.add(models.Usuario(username="nurse-af09-pdf", password_hash="x", rol="enfermeria", activo=True))
        before = db.query(models.DocumentoVerificacionQR).count()
        db.commit()
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.get(
            f"/api/ehr/paciente/{pt_num}/pdf-consentimiento-32-01",
            headers=_auth_headers("nurse-af09-pdf", "enfermeria"),
        )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    with database.SessionLocal() as db:
        assert db.query(models.DocumentoVerificacionQR).count() == before
    assert not pdf_path.exists()


def test_af11_role_change_persists_exactly_one_audit_event():
    with database.SessionLocal() as db:
        admin = models.Usuario(username="admin-af11", password_hash="x", rol="admin", activo=True)
        target = models.Usuario(username="target-af11", password_hash="x", rol="limpieza", activo=True)
        db.add_all([admin, target])
        db.commit()
        target_id = target.id
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.put(
            f"/api/usuarios/{target_id}",
            json={"rol": "enfermeria"},
            headers=_auth_headers("admin-af11", "admin"),
        )
    assert response.status_code == 200, response.text
    with database.SessionLocal() as db:
        events = db.query(models.AuditoriaLog).filter(
            models.AuditoriaLog.accion == "USUARIO_ACTUALIZADO"
        ).all()
    assert len(events) == 1


def test_af11_patient_admission_and_bed_events_survive_session_close():
    with database.SessionLocal() as db:
        admin = models.Usuario(username="admin-af11b", password_hash="x", rol="admin", activo=True)
        db.add(admin)
        db.commit()
    headers = _auth_headers("admin-af11b", "admin")
    with TestClient(main.app, raise_server_exceptions=False) as client:
        admission = client.post(
            "/api/pacientes",
            json={
                "nombre_completo": "PACIENTE AUDITABLE",
                "num_habitacion": "AF11-CAMA",
                "area_hospitalaria": "TEST",
                "codigo_barras": "AF11-PATIENT",
            },
            headers=headers,
        )
        bed = client.put(
            "/api/camas/AF11-CAMA/limpieza",
            json={"estado_limpieza": "Limpia", "notas_limpieza": "AF11"},
            headers=headers,
        )
    assert admission.status_code == 200, admission.text
    assert bed.status_code == 200, bed.text
    with database.SessionLocal() as verification:
        assert verification.query(models.AuditoriaLog).filter(
            models.AuditoriaLog.accion == "Paciente Ingresado"
        ).count() == 1
        assert verification.query(models.AuditoriaLog).filter(
            models.AuditoriaLog.accion == "Actualización Limpieza Cama"
        ).count() == 1

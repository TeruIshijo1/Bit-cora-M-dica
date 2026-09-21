from __future__ import annotations

import base64
import datetime
import os
import json
import hashlib
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pytest
import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from starlette.requests import Request

os.environ.setdefault("BIOMETRIC_ATTESTATION_SECRET", "synthetic-biometric-attestation-secret-32chars")

import biometric_security
import main
import models


FMD_A = base64.b64encode(b"FMR\x00" + b"A" * 64).decode()
FMD_B = base64.b64encode(b"FMR\x00" + b"B" * 64).decode()


@dataclass
class MatcherResponse:
    payload: object
    status_code: int = 200
    invalid_json: bool = False

    def json(self):
        if self.invalid_json:
            raise ValueError("synthetic invalid json")
        return self.payload

    @property
    def text(self):
        return "synthetic matcher response"


@pytest.fixture
def db():
    session = main.SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def canonical(data=FMD_A):
    return biometric_security.detect_template_state(
        '{"data":"%s","format":"ANSI_378_2004","version":1}' % data
    ).canonical


@pytest.fixture
def enrollment(db):
    patient = models.Paciente(nombre_completo="PACIENTE A SINTETICO", codigo_barras="BIO-A", status_ingreso="Ingresado")
    other_patient = models.Paciente(nombre_completo="PACIENTE B SINTETICO", codigo_barras="BIO-B", status_ingreso="Ingresado")
    db.add_all([patient, other_patient])
    db.flush()
    signer = models.BiometriaFirmanteEpisodio(
        paciente_id=patient.id, pt_num=patient.codigo_barras, tipo_firmante="PACIENTE",
        nombre_completo="PACIENTE A SINTETICO", fmd_template=canonical(FMD_A),
        huella_token="TOKEN-A-SINTETICO", biometric_status="FMD_VALIDO",
        template_format="ANSI_378_2004", template_version=1, estado="ACTIVO",
    )
    db.add(signer)
    db.commit()
    db.refresh(patient)
    db.refresh(other_patient)
    db.refresh(signer)
    return patient, other_patient, signer


def issue(db, *, action="VERIFICACION_FIRMANTE", session_id="session-1", signer_id=None,
          patient_ref=None, document_code=None, document_ref=None, subject_ref=None):
    return biometric_security.create_challenge(
        db, action=action, session_id=session_id, subject_ref=subject_ref,
        expected_identity_ref=f"firmante:{signer_id}" if signer_id else None,
        patient_ref=patient_ref, document_code=document_code, document_ref=document_ref,
    )[0]


_fixture_match_override = None


def capture(data, challenge_id, session_id="session-1"):
    with main.SessionLocal() as authorization_db:
        row = authorization_db.query(models.BiometricChallenge).filter_by(token_hash=hashlib.sha256(challenge_id.encode()).hexdigest()).one_or_none()
        if row:
            authorization = biometric_security.issue_capture_authorization(authorization_db, challenge_id)
            required, candidates = biometric_security._match_job(authorization_db, row)
        else:
            now = datetime.datetime.now(datetime.timezone.utc)
            authorization = biometric_security._encode_authorization({
                "protocol_version": 2, "challenge_id": challenge_id, "session_id": session_id,
                "action": "VERIFICACION_FIRMANTE", "issued_at": now.isoformat(),
                "expires_at": (now + datetime.timedelta(seconds=120)).isoformat(), "match_required": True,
            })
            required, candidates = True, []
    matched = next((row for row in candidates if row["data"] == data), None)
    result = {"match_success": bool(matched) if required else None,
              "matched_identity": matched["identity"] if matched else None,
              "matched_template_hash": matched["template_hash"] if matched else None}
    if _fixture_match_override is not None:
        result.update(_fixture_match_override)
    return biometric_security.build_attested_capture(
        data, challenge_id, session_id, datetime.datetime.utcnow().isoformat(), authorization=authorization, match_result=result
    )

def test_af02_legacy_attestation_without_service_acquisition_is_rejected():
    challenge_id = "challenge-af02"
    session_id = "session-af02"
    captured_at = datetime.datetime.utcnow().isoformat()
    legacy = {
        "format": biometric_security.TEMPLATE_FORMAT,
        "version": biometric_security.TEMPLATE_VERSION,
        "data": FMD_A,
        "challenge_id": challenge_id,
        "session_id": session_id,
        "captured_at": captured_at,
    }
    import hashlib
    import hmac
    import json
    import os

    old_message = "|".join(str(legacy[key]) for key in (
        "format", "version", "data", "challenge_id", "session_id", "captured_at"
    ))
    legacy["attestation"] = hmac.new(
        os.environ["BIOMETRIC_ATTESTATION_SECRET"].encode(),
        old_message.encode(),
        hashlib.sha256,
    ).hexdigest()
    with pytest.raises(HTTPException) as exc:
        biometric_security.validate_attested_capture(
            json.dumps(legacy), challenge_id, session_id
        )
    assert exc.value.status_code == 401


def verify(db, patient, signer, challenge_id, *, data=FMD_A, role="PACIENTE", session_id="session-1"):
    return main.verificar_huella_firmante_episodio(
        db, patient.id, capture(data, challenge_id, session_id), firmante_id=signer.id,
        tipo_firmante=role, challenge_id=challenge_id, session_id=session_id,
        action="VERIFICACION_FIRMANTE", expected_identity_ref=f"firmante:{signer.id}",
        patient_ref=str(patient.id),
    )


def assert_no_side_effects(db, signer, original):
    db.expire_all()
    current = db.get(models.BiometriaFirmanteEpisodio, signer.id)
    assert (current.fmd_template, current.huella_token, current.tipo_firmante) == original
    assert db.query(models.FirmaDocumentoClinico).count() == 0


def test_fingerprint_a_against_a_succeeds(db, enrollment, monkeypatch):
    patient, _, signer = enrollment
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    assert verify(db, patient, signer, challenge).id == signer.id


def test_fingerprint_b_against_a_is_rejected_without_mutation(db, enrollment, monkeypatch):
    patient, _, signer = enrollment
    original = (signer.fmd_template, signer.huella_token, signer.tipo_firmante)
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    with pytest.raises(HTTPException) as exc:
        verify(db, patient, signer, challenge, data=FMD_B)
    assert exc.value.status_code == 403
    assert_no_side_effects(db, signer, original)


@pytest.mark.parametrize(("action", "expected_status"), [
    ("LOGIN", 401),
    ("FIRMA_MEDICA", 403),
    ("FIRMA_FIRMANTE", 403),
])
def test_mismatch_only_invalidates_session_during_login(action, expected_status):
    now = datetime.datetime.utcnow()
    attested = biometric_security.AttestedCapture(
        canonical=canonical(FMD_B),
        acquisition_id="synthetic-acquisition",
        acquisition_started_at=now,
        captured_at=now,
        context={"action": action, "match_required": True},
        match_result={"match_success": False, "matched_identity": None, "matched_template_hash": None},
    )
    with pytest.raises(HTTPException) as exc:
        biometric_security.verify_attested_match(
            attested,
            [{"id": 1, "fmd_template": canonical(FMD_A)}],
            "medico",
        )
    assert exc.value.status_code == expected_status


@pytest.mark.parametrize("failure", ["transport_down", "timeout"])
def test_unattested_matcher_failures_are_closed(db, enrollment, monkeypatch, failure):
    patient, _, signer = enrollment
    original = (signer.fmd_template, signer.huella_token, signer.tipo_firmante)
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    monkeypatch.setattr(__import__(__name__), "_fixture_match_override", {"match_success": failure})
    with pytest.raises(HTTPException) as exc:
        verify(db, patient, signer, challenge)
    assert exc.value.status_code == 502
    assert_no_side_effects(db, signer, original)


@pytest.mark.parametrize("response", [[], {}, None])
def test_invalid_matcher_responses_are_closed(db, enrollment, monkeypatch, response):
    patient, _, signer = enrollment
    original = (signer.fmd_template, signer.huella_token, signer.tipo_firmante)
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    monkeypatch.setattr(__import__(__name__), "_fixture_match_override", {"match_success": response})
    with pytest.raises(HTTPException) as exc:
        verify(db, patient, signer, challenge)
    assert exc.value.status_code == 502
    assert_no_side_effects(db, signer, original)


def test_signer_id_is_mandatory(db, enrollment):
    patient, _, _ = enrollment
    with pytest.raises(HTTPException) as exc:
        main.verificar_huella_firmante_episodio(db, patient.id, "synthetic", firmante_id=None)
    assert exc.value.status_code == 422


def test_signer_from_another_patient_is_rejected(db, enrollment):
    _, other_patient, signer = enrollment
    challenge = issue(db, signer_id=signer.id, patient_ref=str(other_patient.id))
    with pytest.raises(HTTPException) as exc:
        verify(db, other_patient, signer, challenge)
    assert exc.value.status_code == 404


def test_manipulated_signer_role_is_rejected(db, enrollment):
    patient, _, signer = enrollment
    original = (signer.fmd_template, signer.huella_token, signer.tipo_firmante)
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    with pytest.raises(HTTPException) as exc:
        verify(db, patient, signer, challenge, role="TESTIGO_1")
    assert exc.value.status_code == 409
    assert_no_side_effects(db, signer, original)


def test_missing_challenge_is_rejected(db, enrollment):
    patient, _, signer = enrollment
    with pytest.raises(HTTPException) as exc:
        main.verificar_huella_firmante_episodio(db, patient.id, "synthetic", firmante_id=signer.id, challenge_id=None, session_id="session-1")
    assert exc.value.status_code == 422


def test_unknown_challenge_is_rejected(db, enrollment):
    patient, _, signer = enrollment
    with pytest.raises(HTTPException) as exc:
        verify(db, patient, signer, "unknown-challenge")
    assert exc.value.status_code == 401


def test_expired_challenge_is_rejected(db, enrollment):
    patient, _, signer = enrollment
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    row = db.query(models.BiometricChallenge).one()
    row.expires_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        verify(db, patient, signer, challenge)
    assert exc.value.status_code == 401


def test_consumed_challenge_is_rejected(db, enrollment, monkeypatch):
    patient, _, signer = enrollment
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    verify(db, patient, signer, challenge)
    with pytest.raises(HTTPException) as exc:
        verify(db, patient, signer, challenge)
    assert exc.value.status_code == 401


@pytest.mark.parametrize("wrong", [{"action": "LOGIN"}, {"patient_ref": "OTHER-PATIENT"}, {"document_code": "OTHER-DOCUMENT"}])
def test_challenge_context_cannot_cross_action_patient_or_document(db, wrong):
    challenge = issue(db, action="FIRMA_MEDICA", patient_ref="PATIENT-A", document_code="FORMAT-A", document_ref="1")
    expected = {"action": "FIRMA_MEDICA", "patient_ref": "PATIENT-A", "document_code": "FORMAT-A", "document_ref": "1"}
    expected.update(wrong)
    with pytest.raises(HTTPException) as exc:
        biometric_security.consume_challenge(db, challenge_id=challenge, session_id="session-1", **expected)
    assert exc.value.status_code == 401


def test_twenty_simultaneous_consumers_exactly_one_wins(db):
    challenge = issue(db, action="LOGIN", session_id="concurrent")

    def consume():
        session = main.SessionLocal()
        try:
            biometric_security.consume_challenge(session, challenge_id=challenge, action="LOGIN", session_id="concurrent")
            return True
        except HTTPException:
            return False
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: consume(), range(20)))
    assert sum(results) == 1
    assert len(results) == 20


def test_capture_from_old_challenge_cannot_authorize_new_challenge(db, enrollment):
    patient, _, signer = enrollment
    old = issue(db, signer_id=signer.id, patient_ref=str(patient.id), session_id="old-session")
    stale = capture(FMD_A, old, "old-session")
    fresh = issue(db, signer_id=signer.id, patient_ref=str(patient.id), session_id="new-session")
    with pytest.raises(HTTPException) as exc:
        main.verificar_huella_firmante_episodio(
            db, patient.id, stale, firmante_id=signer.id, tipo_firmante="PACIENTE",
            challenge_id=fresh, session_id="new-session", expected_identity_ref=f"firmante:{signer.id}",
            patient_ref=str(patient.id),
        )
    assert exc.value.status_code == 401


def test_raw_payload_is_never_classified_as_valid_fmd():
    raw = '{"base64":"synthetic-image","metadata":{"width":100,"height":100,"resolution":500}}'
    assert biometric_security.detect_template_state(raw).state == "LEGACY_RAW"


def test_tampered_attestation_is_rejected():
    template = capture(FMD_A, "challenge-a")
    tampered = template.replace(FMD_A, FMD_B)
    with pytest.raises(HTTPException) as exc:
        biometric_security.validate_attested_capture(tampered, "challenge-a", "session-1")
    assert exc.value.status_code == 401


def make_request(role, identity_id):
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1)})
    request.state.user = {"rol": role, "id": identity_id}
    return request


def test_initial_enrollment_stores_fmd_not_raw_and_audits(db, enrollment):
    patient, _, signer = enrollment
    signer.fmd_template = None
    signer.huella_token = None
    signer.biometric_status = "SIN_BIOMETRIA"
    user = models.Usuario(username="nurse", password_hash="x", rol="enfermeria", activo=True)
    db.add(user)
    db.commit()
    request = make_request("enfermeria", user.id)
    challenge = issue(db, action="ENROLAMIENTO_FIRMANTE", signer_id=signer.id, patient_ref=str(patient.id), document_ref=str(signer.id), subject_ref=f"enfermeria:{user.id}")
    result = main._enrolar_firmante_controlado(
        paciente_id=str(patient.id), firmante_id=signer.id,
        req=main.schemas.BiometricEnrollmentRequest(fmd_template=capture(FMD_A, challenge), challenge_id=challenge, session_id="session-1"),
        request=request, db=db, current_user=user, reenrolamiento=False,
    )
    assert result.biometric_status == "FMD_VALIDO"
    assert '"metadata"' not in result.fmd_template and '"base64"' not in result.fmd_template
    assert db.query(models.AuditoriaLog).filter_by(accion="ENROLAMIENTO_FIRMANTE").count() == 1


def test_legacy_raw_is_detected_and_never_transformed_by_verification(db, enrollment):
    patient, _, signer = enrollment
    legacy = '{"base64":"synthetic-image","metadata":{"width":1,"height":1,"resolution":500}}'
    assert biometric_security.detect_template_state(legacy).state == "LEGACY_RAW"
    signer.fmd_template = legacy
    signer.biometric_status = "LEGACY_RAW"
    signer.requiere_reenrolamiento = True
    db.commit()
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    with pytest.raises(HTTPException) as exc:
        verify(db, patient, signer, challenge)
    assert exc.value.status_code == 409
    db.refresh(signer)
    assert signer.fmd_template == legacy and signer.biometric_status == "LEGACY_RAW"


def test_unauthorized_user_cannot_reenroll_doctor(db):
    nurse = models.Usuario(username="nurse", password_hash="x", rol="enfermeria", activo=True)
    doctor = models.Medico(numero_empleado="MED-1", nombre_completo="DOCTOR", especialidad="TEST", cedula="CED-1", huella_token="DOC-TOKEN", fmd_template=canonical(), biometric_status="FMD_VALIDO", activo_status=True)
    db.add_all([nurse, doctor])
    db.commit()
    token = jwt.encode({"sub": nurse.username, "rol": nurse.rol, "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=5)}, main.SECRET_KEY, algorithm=main.ALGORITHM)
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.post(f"/api/medicos/{doctor.id}/biometria/reenrolar", headers={"Authorization": f"Bearer {token}"}, json={})
    assert response.status_code == 403
    db.refresh(doctor)
    assert doctor.fmd_template == canonical()


def test_doctor_reenrollment_audits_and_blocks_existing_fea(db):
    admin = models.Usuario(username="admin", password_hash="x", rol="admin", activo=True)
    doctor = models.Medico(numero_empleado="MED-2", nombre_completo="DOCTOR DOS", especialidad="TEST", cedula="CED-2", huella_token="DOC-TOKEN-2", fmd_template=canonical(FMD_A), biometric_status="FMD_VALIDO", activo_status=True)
    db.add_all([admin, doctor])
    db.commit()
    request = make_request("admin", admin.id)
    challenge = biometric_security.create_challenge(
        db, action="REENROLAMIENTO_MEDICO", session_id="session-1", subject_ref=f"admin:{admin.id}",
        expected_identity_ref=f"medico:{doctor.id}", document_ref=str(doctor.id),
    )[0]
    main._enrolar_medico_controlado(
        medico_id=doctor.id,
        req=main.schemas.BiometricEnrollmentRequest(
            fmd_template=capture(FMD_B, challenge), challenge_id=challenge, session_id="session-1",
            motivo="Cambio controlado por deterioro de captura",
        ),
        request=request, db=db, current_user=admin, reenrolamiento=True,
    )
    db.refresh(doctor)
    assert doctor.requiere_actualizacion_fea is True
    assert db.query(models.AuditoriaLog).filter_by(accion="REENROLAMIENTO_MEDICO").count() == 1
    with pytest.raises(HTTPException) as exc:
        main._assert_fea_enabled(doctor)
    assert exc.value.status_code == 423

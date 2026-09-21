from __future__ import annotations

import base64
import datetime
import hashlib
import os
from types import SimpleNamespace

import pytest
from asn1crypto import cms, keys as asn1_keys, tsp, x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from fastapi import HTTPException
from pyhanko.sign.timestamps import DummyTimeStamper
from pyhanko_certvalidator.registry import SimpleCertificateStore
from sqlalchemy.exc import DBAPIError
from starlette.requests import Request

import clinical_signing
import crypto_fea
import main
import models
import tsa_client


os.environ.setdefault("HES_HMAC_SECRET", "synthetic-fea-secret-for-tests-only")


@pytest.fixture
def db():
    session = main.SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _doctor(db, *, employee: str = "FEA-001"):
    doctor = models.Medico(
        numero_empleado=employee,
        nombre_completo="DRA PRUEBA CRIPTOGRAFICA",
        especialidad="MEDICINA INTERNA",
        cedula=f"CED-{employee}",
        huella_token=f"TOKEN-{employee}",
        fmd_template="FMD-SINTETICO",
        biometric_status="FMD_VALIDO",
        activo_status=True,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def _request():
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )


def _signed_record(db, *, pdf_bytes: bytes | None = None):
    patient = models.Paciente(
        nombre_completo="PACIENTE CRIPTOGRAFICO",
        codigo_barras="FEA-PT-1",
        status_ingreso="Ingresado",
    )
    db.add(patient)
    db.commit()
    doctor = _doctor(db)
    active_key = crypto_fea.get_active_key(db, doctor)
    full_content = {
        "subjetivo": "A" * 100 + "BYTE-101-MUST-BE-SIGNED" + "B" * 200,
        "objetivo": {"ta": "120/80", "fc": 72},
        "analisis": "Contenido clínico completo",
        "plan": ["Tratamiento 1", "Tratamiento 2"],
    }
    document = clinical_signing.ClinicalDocument(
        tipo_documento="Nota de Evolución Médica",
        contenido_clinico=full_content,
        version_documento="7",
        source_identifier="MR_NE_URG:55:1",
        pdf_bytes=pdf_bytes,
        pdf_identifier="PDF-FEA-7" if pdf_bytes is not None else None,
    )
    signed_at = datetime.datetime(2026, 9, 17, 14, 0, tzinfo=clinical_signing.MEXICO_CITY)
    _, payload_bytes, payload_hash, pdf_hash = clinical_signing.build_canonical_payload(
        document=document,
        codigo_formato="HE-DIRMED-SINPRO-PLT-87/01",
        pt_num="FEA-PT-1",
        expediente="PT-FEA-PT-1",
        evolution_slot=1,
        patient_identity={
            "id": patient.id,
            "nombre_completo": patient.nombre_completo,
            "codigo_barras": patient.codigo_barras,
        },
        medico_id=doctor.id,
        nombre_medico=doctor.nombre_completo,
        cedula=doctor.cedula,
        proposito="CIERRE_Y_AUTORIA_CLINICA",
        signed_at=signed_at,
        key_id=active_key.key_id,
    )
    result = crypto_fea.firmar_documento_con_key_id(db, doctor, payload_bytes)
    signature = models.FirmaDocumentoClinico(
        tipo_documento=document.tipo_documento,
        codigo_formato="HE-DIRMED-SINPRO-PLT-87/01",
        pt_num="FEA-PT-1",
        expediente="PT-FEA-PT-1",
        evolution_slot=1,
        rol_firmante="MEDICO",
        medico_id=doctor.id,
        nombre_medico=doctor.nombre_completo,
        cedula_profesional=doctor.cedula,
        fecha_hora_firma=signed_at.replace(tzinfo=None),
        hash_sha256=payload_hash,
        sello_digital=result.sello_digital,
        cadena_original=payload_bytes.decode("utf-8"),
        key_id=result.key_id,
        signature_schema_version=clinical_signing.SCHEMA_VERSION,
        canonical_payload=payload_bytes.decode("utf-8"),
        payload_hash=payload_hash,
        document_version=document.version_documento,
        pdf_hash=pdf_hash,
        pdf_identifier=document.pdf_identifier,
        tsa_status=tsa_client.TSA_PENDIENTE,
        tsa_attempts=1,
    )
    db.add(signature)
    db.commit()
    db.refresh(signature)
    return doctor, signature, full_content


def _sign_with_private(private_pem: bytes, payload: bytes) -> str:
    key = serialization.load_pem_private_key(private_pem, password=None)
    raw = key.sign(payload, ec.ECDSA(hashes.SHA256()))
    return "ECDSA:" + base64.b64encode(raw).decode("ascii")


def test_01_signature_covers_complete_clinical_content(db):
    _, signature, content = _signed_record(db)
    assert content["subjetivo"] in signature.canonical_payload
    assert clinical_signing.verify_signature_record(db, signature)["complete"] is True


def test_02_one_byte_snapshot_change_fails(db):
    _, signature, _ = _signed_record(db)
    signature.canonical_payload = signature.canonical_payload.replace("Tratamiento 1", "Tratamiento X")
    result = clinical_signing.verify_signature_record(db, signature)
    assert result["snapshot"] is False and result["complete"] is False


def test_03_change_after_character_100_fails(db):
    _, signature, _ = _signed_record(db)
    marker = "BYTE-101-MUST-BE-SIGNED"
    assert signature.canonical_payload.index(marker) > 100
    signature.canonical_payload = signature.canonical_payload.replace(marker, "BYTE-101-TAMPERED------")
    assert clinical_signing.verify_signature_record(db, signature)["complete"] is False


def test_04_patient_change_fails(db):
    _, signature, _ = _signed_record(db)
    signature.pt_num = "OTRO-PACIENTE"
    assert clinical_signing.verify_signature_record(db, signature)["document_binding"] is False


def test_05_document_type_change_fails(db):
    _, signature, _ = _signed_record(db)
    signature.tipo_documento = "Otro documento"
    assert clinical_signing.verify_signature_record(db, signature)["document_binding"] is False


def test_06_document_version_change_fails(db):
    _, signature, _ = _signed_record(db)
    signature.document_version = "8"
    assert clinical_signing.verify_signature_record(db, signature)["document_binding"] is False


def test_07_evolution_slot_change_fails(db):
    _, signature, _ = _signed_record(db)
    signature.evolution_slot = 2
    assert clinical_signing.verify_signature_record(db, signature)["document_binding"] is False


def test_08_signer_change_fails(db):
    _, signature, _ = _signed_record(db)
    signature.nombre_medico = "OTRO MEDICO"
    assert clinical_signing.verify_signature_record(db, signature)["identity"] is False


def test_09_key_id_change_fails(db):
    _, signature, _ = _signed_record(db)
    other = _doctor(db, employee="FEA-OTHER")
    other_key = crypto_fea.get_active_key(db, other)
    signature.key_id = other_key.key_id
    result = clinical_signing.verify_signature_record(db, signature)
    assert result["identity"] is False and result["ecdsa"] is False


def test_10_modified_pdf_fails_when_pdf_is_primary_evidence(db):
    _, signature, _ = _signed_record(db, pdf_bytes=b"%PDF-1.7\nORIGINAL")
    assert clinical_signing.verify_signature_record(db, signature, pdf_bytes=b"%PDF-1.7\nORIGINAL")["pdf"] is True
    assert clinical_signing.verify_signature_record(db, signature, pdf_bytes=b"%PDF-1.7\nMODIFICADO")["pdf"] is False


def test_af04_current_operational_content_cannot_be_presented_as_signed_version(db, monkeypatch):
    _, signature, _ = _signed_record(db)
    changed = clinical_signing.ClinicalDocument(
        tipo_documento=signature.tipo_documento,
        contenido_clinico={"subjetivo": "CONTENIDO OPERATIVO CAMBIADO"},
        version_documento=signature.document_version,
        source_identifier="MR_NE_URG:55:1",
    )
    monkeypatch.setattr(
        clinical_signing,
        "load_authoritative_document",
        lambda *_a, **_k: (changed, {}),
    )
    assert clinical_signing.compare_current_document(db, signature) is False


class _VerticalCursor:
    def execute(self, *_args, **_kwargs):
        return None

    def fetchone(self):
        return ("FIRMADO_BIOMETRICAMENTE", "MEDICO VERTICAL", None)


class _VerticalConnection:
    def cursor(self):
        return _VerticalCursor()

    def close(self):
        return None


def test_11_vertical_text_marker_is_not_cryptographic_evidence(db, monkeypatch):
    monkeypatch.setattr(main, "get_or_create_paciente_by_identifier", lambda *_: None)
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: _VerticalConnection())
    result = main.verificar_integridad_documento(
        "PT-FEA-VERTICAL",
        main.VerificarIntegridadInputSchema(codigo_formato="HE-DIRMED-SINPRO-PLT-87/01", slot=1),
        _request(),
        db,
    )
    assert result["integro"] is False
    assert result["triada_seguridad"]["integridad"]["verificado"] is False
    assert result["triada_seguridad"]["autenticidad"]["verificado"] is False


def test_12_wrong_public_key_fails(db):
    _, signature, _ = _signed_record(db)
    wrong_private, _ = crypto_fea.generate_ecdsa_keypair()
    signature.sello_digital = _sign_with_private(wrong_private, signature.canonical_payload.encode())
    assert clinical_signing.verify_signature_record(db, signature)["ecdsa"] is False


def test_13_old_signature_verifies_only_with_historical_key_id(db):
    doctor, signature, _ = _signed_record(db)
    old_key_id = signature.key_id
    crypto_fea.rotate_medico_key(db, doctor, motivo="Reenrolamiento de prueba", actor_id=None)
    db.commit()
    assert clinical_signing.verify_signature_record(db, signature)["complete"] is True
    assert signature.key_id == old_key_id


def test_14_rotation_preserves_history_and_creates_one_active_key(db):
    doctor, signature, _ = _signed_record(db)
    old_key_id = signature.key_id
    new_key_id = crypto_fea.rotate_medico_key(db, doctor, motivo="Rotación controlada", actor_id=None)
    db.commit()
    rows = db.query(models.HistorialLlaveFEA).filter_by(medico_id=doctor.id).all()
    assert {row.key_id for row in rows} == {old_key_id, new_key_id}
    assert sum(bool(row.activo) for row in rows) == 1
    assert clinical_signing.verify_signature_record(db, signature)["complete"] is True


def test_15_private_key_decryption_failure_does_not_rotate(db):
    doctor = _doctor(db, employee="FEA-DEC")
    crypto_fea.ensure_medico_keys(db, doctor)
    original_public = doctor.public_key_pem
    original_key_id = crypto_fea.get_active_key(db, doctor).key_id
    doctor.private_key_enc = "ciphertext-corrupto"
    db.commit()
    with pytest.raises(crypto_fea.PrivateKeyDecryptionError):
        crypto_fea.firmar_documento_con_key_id(db, doctor, b"payload")
    db.refresh(doctor)
    assert doctor.public_key_pem == original_public
    assert crypto_fea.get_active_key(db, doctor).key_id == original_key_id


def test_16_requires_fea_update_blocks_signature_with_423(db, monkeypatch):
    doctor = _doctor(db, employee="FEA-LOCK")
    doctor.requiere_actualizacion_fea = True
    monkeypatch.setattr(main, "assert_paciente_no_de_alta", lambda *_: None)
    monkeypatch.setattr(main, "verificar_huella_medico", lambda **_: doctor)
    with pytest.raises(HTTPException) as exc:
        main.firmar_documento_biometrico(
            "FEA-PT-LOCK",
            main.FirmaBiometricaInputSchema(
                fmd_template="FMD",
                medico_id=doctor.id,
                challenge_id="challenge",
                session_id="session",
            ),
            _request(),
            db,
        )
    assert exc.value.status_code == 423


def test_17_explicit_fea_rotation_unblocks_signing(db, monkeypatch):
    doctor = _doctor(db, employee="FEA-UNLOCK")
    reenroller = models.Usuario(username="fea-reenroller", password_hash="x", rol="rh", activo=True)
    approver = models.Usuario(username="fea-approver", password_hash="x", rol="admin", activo=True)
    db.add_all([reenroller, approver])
    db.flush()
    crypto_fea.ensure_medico_keys(db, doctor)
    doctor.requiere_actualizacion_fea = True
    doctor.biometric_reenrolled_by_id = reenroller.id
    doctor.biometric_reenrolled_at = datetime.datetime.utcnow()
    db.commit()
    monkeypatch.setattr(main, "verificar_huella_medico", lambda **_: doctor)
    response = main.completar_actualizacion_fea(
        doctor.id,
        main.schemas.FEAKeyRotationRequest(
            fmd_template="FMD",
            challenge_id="challenge",
            session_id="session",
            motivo="Biometría reenrolada",
        ),
        _request(),
        db,
        SimpleNamespace(id=approver.id, rol="admin"),
    )
    new_key_id = response["key_id"]
    main._assert_fea_enabled(doctor)
    assert doctor.requiere_actualizacion_fea is False
    assert crypto_fea.firmar_documento_con_key_id(db, doctor, b"nuevo payload").key_id == new_key_id


def _cert_pair(*, tsa_eku: bool = True, common_name: str = "HES TSA TEST"):
    now = datetime.datetime.now(datetime.timezone.utc)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "HES TEST ROOT")])
    root_cert = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(
            x509.KeyUsage(True, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    tsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tsa_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    eku = ExtendedKeyUsageOID.TIME_STAMPING if tsa_eku else ExtendedKeyUsageOID.CLIENT_AUTH
    tsa_cert = (
        x509.CertificateBuilder()
        .subject_name(tsa_name)
        .issuer_name(root_name)
        .public_key(tsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(hours=1))
        .not_valid_after(now + datetime.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(True, False, False, False, False, False, False, False, False),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([eku]), critical=True)
        .sign(root_key, hashes.SHA256())
    )
    to_asn1 = lambda cert: asn1_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER))
    tsa_key_asn1 = asn1_keys.PrivateKeyInfo.load(
        tsa_key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return to_asn1(root_cert), to_asn1(tsa_cert), tsa_key_asn1


def _tsa_token(digest: bytes, *, nonce: int = 424242, tsa_eku: bool = True):
    root, cert, key = _cert_pair(tsa_eku=tsa_eku)
    store = SimpleCertificateStore()
    store.register(root)
    stamper = DummyTimeStamper(
        cert,
        key,
        certs_to_embed=store,
        fixed_dt=datetime.datetime.now(datetime.timezone.utc),
        include_nonce=True,
    )
    request = tsp.TimeStampReq(
        {
            "version": 1,
            "message_imprint": {
                "hash_algorithm": {"algorithm": "sha256"},
                "hashed_message": digest,
            },
            "nonce": nonce,
            "cert_req": True,
        }
    )
    response = stamper.request_tsa_response(request)
    token_b64 = base64.b64encode(response["time_stamp_token"].dump()).decode("ascii")
    return token_b64, root, nonce


def test_18_valid_tsa_is_cryptographically_verified():
    digest = hashlib.sha256(b"payload TSA").digest()
    token, root, nonce = _tsa_token(digest)
    result = tsa_client.verify_timestamp(
        token,
        digest.hex(),
        expected_nonce=nonce,
        trust_roots=[root],
        expected_subject="HES TSA TEST",
    )
    assert result["verificado"] is True
    assert result["status"] == tsa_client.TSA_VERIFICADO


class _TSAHttpResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def test_af10_complete_timestamp_response_with_granted_status_is_verified(monkeypatch):
    digest = hashlib.sha256(b"payload TSA end-to-end AF10").digest()
    nonce = 989898
    root, cert, key = _cert_pair()
    store = SimpleCertificateStore()
    store.register(root)
    stamper = DummyTimeStamper(
        cert,
        key,
        certs_to_embed=store,
        fixed_dt=datetime.datetime.now(datetime.timezone.utc),
        include_nonce=True,
    )
    request = tsp.TimeStampReq(
        {
            "version": 1,
            "message_imprint": {
                "hash_algorithm": {"algorithm": "sha256"},
                "hashed_message": digest,
            },
            "nonce": nonce,
            "cert_req": True,
        }
    )
    response = stamper.request_tsa_response(request)
    assert response["status"]["status"].native == "granted"
    monkeypatch.setattr(tsa_client, "_load_trust_roots", lambda *_: [root])
    monkeypatch.setattr(
        tsa_client.urllib.request,
        "urlopen",
        lambda *_a, **_k: _TSAHttpResponse(response.dump()),
    )
    result = tsa_client.get_timestamp(digest.hex(), nonce=nonce)
    assert result["status"] == tsa_client.TSA_VERIFICADO
    assert result["verificado"] is True


def test_af10_summary_exposes_pending_tsa_without_claiming_complete(db, monkeypatch):
    _, signature, _ = _signed_record(db)
    monkeypatch.setattr(main.clinical_signing, "compare_current_document", lambda *_: True)
    result = main.verificar_integridad_documento(
        signature.pt_num,
        main.VerificarIntegridadInputSchema(
            firma_id=signature.id,
            codigo_formato=signature.codigo_formato,
            slot=signature.evolution_slot,
        ),
        _request(),
        db,
    )
    assert result["tsa_status"] == tsa_client.TSA_PENDIENTE
    assert result["estado"] != "VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA"


def test_19_invalid_tsa_cms_signature_is_rejected():
    digest = hashlib.sha256(b"payload TSA").digest()
    token_b64, root, nonce = _tsa_token(digest)
    token = cms.ContentInfo.load(base64.b64decode(token_b64))
    signer_info = token["content"]["signer_infos"][0]
    corrupted = bytearray(signer_info["signature"].native)
    corrupted[-1] ^= 1
    signer_info["signature"] = bytes(corrupted)
    result = tsa_client.verify_timestamp(
        base64.b64encode(token.dump()).decode(),
        digest.hex(),
        expected_nonce=nonce,
        trust_roots=[root],
    )
    assert result["verificado"] is False


def test_20_untrusted_tsa_certificate_is_rejected():
    digest = hashlib.sha256(b"payload TSA").digest()
    token, _, nonce = _tsa_token(digest)
    other_root, _, _ = _cert_pair(common_name="OTHER TSA")
    result = tsa_client.verify_timestamp(
        token, digest.hex(), expected_nonce=nonce, trust_roots=[other_root]
    )
    assert result["verificado"] is False


def test_21_tsa_certificate_without_timestamping_eku_is_rejected():
    digest = hashlib.sha256(b"payload TSA").digest()
    token, root, nonce = _tsa_token(digest, tsa_eku=False)
    result = tsa_client.verify_timestamp(
        token, digest.hex(), expected_nonce=nonce, trust_roots=[root]
    )
    assert result["verificado"] is False


def test_22_wrong_tsa_imprint_is_rejected():
    digest = hashlib.sha256(b"payload TSA").digest()
    token, root, nonce = _tsa_token(digest)
    other = hashlib.sha256(b"otro payload").hexdigest()
    assert tsa_client.verify_timestamp(
        token, other, expected_nonce=nonce, trust_roots=[root]
    )["verificado"] is False


def test_23_wrong_tsa_nonce_is_rejected():
    digest = hashlib.sha256(b"payload TSA").digest()
    token, root, nonce = _tsa_token(digest)
    assert tsa_client.verify_timestamp(
        token, digest.hex(), expected_nonce=nonce + 1, trust_roots=[root]
    )["verificado"] is False


def test_24_tsa_outage_is_pending_not_verified(monkeypatch):
    monkeypatch.setattr(tsa_client.urllib.request, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(OSError("down")))
    result = tsa_client.get_timestamp(hashlib.sha256(b"payload").hexdigest())
    assert result["status"] == tsa_client.TSA_PENDIENTE
    assert result["verificado"] is False


def test_25_tsa_retry_does_not_modify_original_ecdsa(db, monkeypatch):
    _, signature, _ = _signed_record(db)
    original = signature.sello_digital
    monkeypatch.setattr(
        main.tsa_client,
        "get_timestamp",
        lambda *_: {
            "status": tsa_client.TSA_VERIFICADO,
            "verificado": True,
            "token_b64": "TEST-TOKEN",
            "nonce": "99",
            "error": None,
        },
    )
    result = main.reintentar_tsa_firma(
        signature.id,
        db=db,
        current_user=SimpleNamespace(id=1, rol="admin"),
    )
    db.refresh(signature)
    assert result["ecdsa_original_preservada"] is True
    assert signature.sello_digital == original


def test_client_summary_is_not_part_of_signing_contract():
    request = main.FirmaBiometricaInputSchema(
        codigo_formato="HE-DIRMED-SINPRO-PLT-87/01",
        tipo_documento="Etiqueta no autoritativa",
        evolution_slot=1,
        fmd_template="FMD",
        medico_id=1,
        challenge_id="challenge",
        session_id="session",
        contenido_resumen="TEXTO CONTROLADO POR CLIENTE",
    )
    assert not hasattr(request, "contenido_resumen")


def test_signing_endpoint_uses_only_authoritative_server_document(db, monkeypatch):
    doctor = _doctor(db, employee="FEA-SERVER-SOURCE")
    patient = models.Paciente(
        nombre_completo="PACIENTE FUENTE SERVIDOR",
        codigo_barras="FEA-SERVER-PT",
        status_ingreso="Ingresado",
    )
    db.add(patient)
    db.commit()
    server_document = clinical_signing.ClinicalDocument(
        tipo_documento="TIPO AUTORITATIVO DEL SERVIDOR",
        contenido_clinico={"nota": "CONTENIDO CLINICO COMPLETO DEL SERVIDOR"},
        version_documento="SERVER-V3",
        source_identifier="MR_NE_URG:3:1",
    )
    monkeypatch.setattr(main, "assert_paciente_no_de_alta", lambda *_: None)
    monkeypatch.setattr(main, "verificar_huella_medico", lambda **_: doctor)
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: None)
    monkeypatch.setattr(
        main.clinical_signing,
        "load_authoritative_document",
        lambda *_a, **_k: (
            server_document,
            {"id": patient.id, "nombre_completo": patient.nombre_completo, "codigo_barras": patient.codigo_barras},
        ),
    )
    monkeypatch.setattr(
        main.tsa_client,
        "get_timestamp",
        lambda *_: {
            "status": tsa_client.TSA_PENDIENTE,
            "verificado": False,
            "token_b64": None,
            "nonce": "1",
            "error": "TSA test offline",
        },
    )
    request_model = main.FirmaBiometricaInputSchema(
        codigo_formato="HE-DIRMED-SINPRO-PLT-87/01",
        tipo_documento="TIPO CONTROLADO POR CLIENTE",
        evolution_slot=1,
        fmd_template="FMD",
        medico_id=doctor.id,
        challenge_id="challenge",
        session_id="session",
        contenido_resumen="CONTENIDO CONTROLADO POR CLIENTE",
    )
    main.firmar_documento_biometrico(
        patient.codigo_barras, request_model, _request(), db
    )
    stored = db.query(models.FirmaDocumentoClinico).one()
    assert stored.tipo_documento == "TIPO AUTORITATIVO DEL SERVIDOR"
    assert "CONTENIDO CLINICO COMPLETO DEL SERVIDOR" in stored.canonical_payload
    assert "CONTENIDO CONTROLADO POR CLIENTE" not in stored.canonical_payload


def test_legacy_signature_is_never_promoted_to_complete(db):
    doctor = _doctor(db, employee="FEA-LEGACY")
    legacy = models.FirmaDocumentoClinico(
        tipo_documento="Legacy",
        codigo_formato="LEGACY",
        pt_num="LEGACY-PT",
        expediente="PT-LEGACY-PT",
        evolution_slot=0,
        medico_id=doctor.id,
        nombre_medico=doctor.nombre_completo,
        cedula_profesional=doctor.cedula,
        hash_sha256="abc",
        sello_digital="FIRMADO_BIOMETRICAMENTE",
        cadena_original="legacy",
        signature_schema_version=clinical_signing.LEGACY_SCHEMA_VERSION,
        tsa_status="TSA_LEGACY_NO_VERIFICADO",
    )
    db.add(legacy)
    db.commit()
    result = clinical_signing.verify_signature_record(db, legacy)
    assert result["complete"] is False
    assert result["errors"] == ["FIRMA_LEGACY_NO_CUBRE_DOCUMENTO_COMPLETO"]


def test_key_history_rejects_public_key_mutation(db):
    doctor = _doctor(db, employee="FEA-IMMUTABLE")
    row = crypto_fea.get_active_key(db, doctor)
    row.public_key_pem = "MUTATED"
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


def test_key_history_rejects_delete(db):
    doctor = _doctor(db, employee="FEA-NODELETE")
    row = crypto_fea.get_active_key(db, doctor)
    db.delete(row)
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()

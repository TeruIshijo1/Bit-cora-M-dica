"""Regressions for the existing biometric ceremony. Never access operational ERP."""
import datetime as dt
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import clinical_signing
import database
import main
import models
import vertical_signer
import biometric_security
import hashlib
import json
import os
from test_biometric_security import FMD_A, canonical


CODE = "HE-DIRMED-CONSUL-PLT-02"


def evidence(db, *, slot=7, role="PACIENTE", version="1"):
    patient = db.query(models.Paciente).filter_by(codigo_barras="WF-1").first()
    if not patient:
        patient = models.Paciente(nombre_completo="SYNTHETIC PATIENT", codigo_barras="WF-1")
        db.add(patient)
        db.flush()
    person = models.BiometriaFirmanteEpisodio(
        paciente_id=patient.id, pt_num="WF-1", tipo_firmante=role,
        nombre_completo="SYNTHETIC " + role, estado="ACTIVO",
    )
    db.add(person)
    db.flush()
    document = clinical_signing.ClinicalDocument("Consentimiento", {"acto": "A"}, version, "MR_02_CI_TRATAMIENTO_QUIRURGICO:7")
    _, raw, digest = clinical_signing.build_biometric_evidence_payload(
        document=document, codigo_formato=CODE, pt_num="WF-1", expediente="PT-WF-1",
        evolution_slot=slot, patient_identity={"id": patient.id}, firmante_id=person.id,
        rol_firmante=role, nombre_firmante=person.nombre_completo, identificacion=None,
        signed_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(models.FirmaDocumentoClinico(
        tipo_documento=document.tipo_documento, codigo_formato=CODE, pt_num="WF-1",
        expediente="PT-WF-1", evolution_slot=slot, rol_firmante=role,
        firmante_id=person.id, nombre_medico=person.nombre_completo,
        document_version=version, signature_schema_version="BIOMETRIC_EVIDENCE_V1",
        canonical_payload=raw.decode(), payload_hash=digest, hash_sha256=digest,
        sello_digital="EVIDENCIA_BIOMETRICA_NO_FEA:synthetic", estado="ACTIVA",
    ))
    db.commit()
    return document


def test_slot_zero_cannot_borrow_slot_seven(monkeypatch):
    with database.SessionLocal() as db:
        document = evidence(db)
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (document, {}))
        state = main.get_firmas_documento_estado("WF-1", CODE, 0, db)
        assert state["paciente_firmado"] is False


def test_changed_content_invalidates_current_patient_signature(monkeypatch):
    with database.SessionLocal() as db:
        evidence(db)
        changed = clinical_signing.ClinicalDocument("Consentimiento", {"acto": "B"}, "1", "MR_02_CI_TRATAMIENTO_QUIRURGICO:7")
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (changed, {}))
        assert main.get_firmas_documento_estado("WF-1", CODE, 7, db)["paciente_firmado"] is False


def test_consent_needs_both_witnesses_for_closure(monkeypatch):
    with database.SessionLocal() as db:
        document = evidence(db)
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (document, {}))
        assert main.get_firmas_documento_estado("WF-1", CODE, 7, db)["listo_para_cierre_medico"] is False
        evidence(db, role="TESTIGO_1")
        assert main.get_firmas_documento_estado("WF-1", CODE, 7, db)["listo_para_cierre_medico"] is False
        evidence(db, role="TESTIGO_2")
        assert main.get_firmas_documento_estado("WF-1", CODE, 7, db)["listo_para_cierre_medico"] is True


def test_unknown_format_must_not_become_an_urgent_note(monkeypatch):
    monkeypatch.setattr(vertical_signer, "get_all_clinical_tables", lambda: ["MR_NE_URG"])
    with pytest.raises(ValueError):
        vertical_signer.resolve_vertical_controller_and_pk("FUTURO-LAB-9999")


def test_medical_session_keeps_patient_signer_identity(monkeypatch):
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": []})
    request.state.user = {"id": 77, "rol": "medico"}
    captured = {}
    def create(db, **kwargs):
        captured.update(kwargs)
        return "synthetic-challenge", dt.datetime.now()
    monkeypatch.setattr(main.biometric_security, "create_challenge", create)
    monkeypatch.setattr(main.biometric_security, "issue_capture_authorization", lambda *a, **k: "synthetic")
    monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (
        clinical_signing.ClinicalDocument("Consentimiento", {}, "1", "MR_02_CI_TRATAMIENTO_QUIRURGICO:7"), {}))
    main.get_biometric_challenge(main.schemas.BiometricChallengeRequest(
        action="FIRMA_FIRMANTE", session_id="test", expected_identity_ref="firmante:3",
        patient_ref="WF-1", document_code=CODE, document_ref="7",
    ), request, None)
    assert captured["expected_identity_ref"] == "firmante:3"
    assert captured["subject_ref"] == "medico:77"


def test_urgent_sync_uses_selected_row_not_latest(monkeypatch):
    class Cursor:
        def execute(self, *args): return self
        def fetchone(self): return (99,)
    class Connection:
        def cursor(self): return Cursor()
        def close(self): pass
    monkeypatch.setattr(main.kh_database, "get_kh_connection", Connection)
    monkeypatch.setattr(main.kh_database, "fetch_full_ehr_dashboard", lambda *_: {
        "evoluciones": {"evolucion1": {"mrnum_ne_urg": 11, "slot_in_row": 1}}
    })
    assert main._resolve_vertical_sign_target("WF-1", "HE-DIRMED-SINPRO-PLT-87/01", 1) == ("MR_NE_URG", 11)


@pytest.mark.parametrize("role", ["PACIENTE", "TUTOR", "FAMILIAR", "TESTIGO_1", "TESTIGO_2"])
def test_real_challenge_capture_and_patient_signature_in_doctor_session(monkeypatch, role):
    monkeypatch.setenv("BIOMETRIC_ATTESTATION_SECRET", "synthetic-test-attestation-secret-123456789")
    with database.SessionLocal() as db:
        patient = models.Paciente(nombre_completo="SYNTHETIC", codigo_barras="WF-2", status_ingreso="Ingresado")
        db.add(patient)
        db.flush()
        signer = models.BiometriaFirmanteEpisodio(paciente_id=patient.id, pt_num="WF-2",
            nombre_completo="SYNTHETIC SIGNER", tipo_firmante=role, estado="ACTIVO",
            fmd_template=canonical(FMD_A), biometric_status="FMD_VALIDO")
        db.add(signer)
        db.commit()
        document = clinical_signing.ClinicalDocument("Consentimiento", {"acto": "A"}, "1", "MR_02_CI_TRATAMIENTO_QUIRURGICO:7")
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (document, {"id": patient.id}))
        request = Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1)})
        request.state.user = {"rol": "medico", "id": 777}
        challenge = main.get_biometric_challenge(main.schemas.BiometricChallengeRequest(
            action="FIRMA_FIRMANTE", session_id="wf-session", expected_identity_ref=f"firmante:{signer.id}",
            patient_ref="WF-2", document_code=CODE, document_ref="7"), request, db)
        envelope = biometric_security.build_attested_capture(FMD_A, challenge["challenge_id"], "wf-session",
            dt.datetime.now(dt.timezone.utc).isoformat(), authorization=challenge["capture_authorization"],
            match_result={"match_success": True, "matched_identity": f"firmante:{signer.id}",
                "matched_template_hash": hashlib.sha256(signer.fmd_template.encode()).hexdigest()})
        req = main.schemas.FirmaBiometricaFirmanteInputSchema(
            codigo_formato=CODE, tipo_documento="Consentimiento", evolution_slot=7,
            firmante_id=signer.id, rol_firmante=role, fmd_template=envelope,
            challenge_id=challenge["challenge_id"], session_id="wf-session")
        result = main.firmar_documento_biometrico_firmante("WF-2", req, request, db)
        assert result["success"] is True
        assert result["firma"]["rol_firmante"] == role
        audit = db.query(models.AuditoriaLog).filter_by(accion="EVIDENCIA_BIOMETRICA_ACTO_NO_FEA").one()
        assert audit.usuario_id is None and audit.actor_real == "medico:777"
        with pytest.raises(HTTPException):
            main.firmar_documento_biometrico_firmante("WF-2", req, request, db)
        assert db.query(models.FirmaDocumentoClinico).count() == 1


def test_changed_document_during_capture_rejected_before_consumption(monkeypatch):
    old = clinical_signing.ClinicalDocument("Nota", {"nota": "old"}, "1", "MR_NE_URG:1:1")
    changed = clinical_signing.ClinicalDocument("Nota", {"nota": "new"}, "1", "MR_NE_URG:1:1")
    monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (changed, {}))
    monkeypatch.setattr(biometric_security, "consume_challenge", lambda *a, **k: pytest.fail("must not consume changed document"))
    capture = SimpleNamespace(context={"document_digest": clinical_signing.document_digest(old)})
    with pytest.raises(HTTPException) as error:
        main.validate_and_consume_challenge(None, challenge_id="x", session_id="x", action="FIRMA_MEDICA", acquisition=capture)
    assert error.value.status_code == 409


def test_doctor_cannot_sign_as_another_profile():
    with database.SessionLocal() as db:
        with pytest.raises(HTTPException) as error:
            main.verificar_huella_medico(db, "synthetic", medico_id=2, expected_identity_ref="medico:1")
        assert error.value.status_code == 403


@pytest.mark.parametrize("rows", [[], [(1, "a"), (2, "b")], [(1, None)]])
def test_vertical_never_uses_default_doctor_or_pin(monkeypatch, rows):
    class Connection:
        def cursor(self): return self
        def execute(self, *args): pass
        def fetchall(self): return rows
        def close(self): pass
    monkeypatch.setattr(main.kh_database, "get_kh_connection", Connection)
    with pytest.raises(RuntimeError):
        vertical_signer.resolve_doctor_pr_and_pin("SYNTHETIC", "CED-EXACT")


@pytest.mark.parametrize("native_chain", [None, "FIRMADO_BIOMETRICAMENTE", "synthetic-native-chain"])
def test_vertical_retains_signrecord_protocol_and_never_fabricates_chain(monkeypatch, native_chain):
    queries, calls = [], []
    class Connection:
        def cursor(self): return self
        def execute(self, sql, params=()):
            self.sql = sql
            queries.append((sql, params))
        def fetchone(self):
            if "V_MRPT" in self.sql: return ("PC", 1, "parent-guid", "patient-guid")
            if "FROM PC" in self.sql: return (1,)
            if "SELECT SignedBy" in self.sql:
                return ("DRA SYNTHETIC", "SG", native_chain) if calls else (None, "RG", None)
            return None
        def fetchall(self): return [("MRNum_CI_CC",)]
        def rollback(self): pass
        def close(self): pass
    class Session:
        def post(self, url, **kwargs):
            calls.append(kwargs["json"])
            return SimpleNamespace(status_code=200, text="Document has been signed")
    monkeypatch.setattr(main.kh_database, "get_kh_connection", Connection)
    monkeypatch.setattr(vertical_signer, "get_vertical_session", lambda **k: Session())
    args = dict(controller_name="MR_CI_CC", mrnum=7, pt_num="101", pr_num=5,
        auth_code="synthetic", doctor_name="DRA SYNTHETIC", operation_id="synthetic")
    if native_chain == "synthetic-native-chain":
        assert vertical_signer.sign_in_vertical_api(**args) is True
    else:
        with pytest.raises(RuntimeError):
            vertical_signer.sign_in_vertical_api(**args)
    assert len(calls) == 1
    assert calls[0]["args"]["CommandArgument"] == "SignRecord"
    fields = {row["Name"]: row for row in calls[0]["args"]["Values"]}
    assert fields["Parameters_PRNum"]["NewValue"] == 5
    assert fields["DocumentNumber"]["OldValue"] == 7
    assert all(sql.lstrip().startswith("SELECT ") for sql, _ in queries)
    assert all(params == (7, "101") for sql, params in queries if "SELECT SignedBy" in sql)


def test_two_witness_roles_cannot_be_the_same_registered_person():
    info = {"sello_paciente": "p", "sello_testigo1": "a", "sello_testigo2": "b",
        "firmante_paciente_id": 1, "firmante_testigo1_id": 2, "firmante_testigo2_id": 2}
    assert clinical_signing.consent_signatures_complete(info) is False


def test_pending_sync_rejects_changed_document_without_contacting_vertical(monkeypatch):
    import clinical_sync_adapters
    import clinical_sync
    old = clinical_signing.ClinicalDocument("Nota", {"nota": "old"}, "1", "MR_NE_URG:1:1")
    changed = clinical_signing.ClinicalDocument("Nota", {"nota": "new"}, "1", "MR_NE_URG:1:1")
    monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (changed, {}))
    monkeypatch.setattr(vertical_signer, "sign_in_vertical_api", lambda **k: pytest.fail("No external signature for altered document"))
    operation = SimpleNamespace(operation_type="VERTICAL_SIGN", operation_id="synthetic", patient_ref="101", payload={
        "codigo_formato": "87/01", "document_digest": clinical_signing.document_digest(old), "target_slot": 1,
    })
    with pytest.raises(clinical_sync.ManualReconciliationRequired):
        clinical_sync_adapters.dispatcher(operation)()


def test_native_signature_metadata_does_not_change_clinical_version(monkeypatch):
    values = {"MRNum_CI_CC": 7, "PTNum": 101, "NOTA": "original", "ModifiedOn": "before",
        "ModifiedBy": "operator", "SignedBy": None, "SignedOn": None, "ESignature": None, "MR_ST": "RG"}
    class Connection:
        def cursor(self): return self
        def execute(self, *args):
            self.description = [(key,) for key in values]
        def fetchall(self): return [(key,) for key in reversed(values)]
        def fetchone(self): return tuple(values.values())
        def close(self): pass
    monkeypatch.setattr(main.kh_database, "get_kh_connection", Connection)
    before = clinical_signing._load_vertical_document("101", "MR_CI_CC", 7)
    values.update(ModifiedOn="after", ModifiedBy="doctor", SignedBy="doctor", SignedOn="after", ESignature="native", MR_ST="SG")
    after = clinical_signing._load_vertical_document("101", "MR_CI_CC", 7)
    assert before == after
    assert after["NOTA"] == "original" and after["__source_identifier__"] == "MR_CI_CC:7"
    values["NOTA"] = "changed"
    assert clinical_signing._load_vertical_document("101", "MR_CI_CC", 7)["__version_documento__"] != after["__version_documento__"]


def test_medical_note_does_not_require_patient_and_witnesses(monkeypatch):
    monkeypatch.setattr(main, "obtener_firmas_completas_documento", lambda *a: {"sello_digital": "synthetic"})
    state = main.get_firmas_documento_estado("101", "87/01", 1, None)
    assert state["requiere_testigos"] is False
    assert state["listo_para_cierre_medico"] is True
    assert state["firmas_completas"] is True


def test_legacy_sync_without_exact_row_requires_reconciliation(monkeypatch):
    import clinical_sync_adapters
    import clinical_sync
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: pytest.fail("must not choose latest row"))
    with pytest.raises(clinical_sync.ManualReconciliationRequired):
        clinical_sync_adapters._resolve_vertical_mr({"codigo_formato": "87/01", "target_slot": 1}, "101")


def test_historical_contact_evidence_does_not_authorize_consent(monkeypatch):
    with database.SessionLocal() as db:
        document = evidence(db, role="CONTACTO")
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (document, {}))
        state = main.get_firmas_documento_estado("WF-1", CODE, 7, db)
        assert state["paciente_firmado"] is False
        assert state["listo_para_cierre_medico"] is False

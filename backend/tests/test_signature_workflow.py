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
from services import pdf_service
import hashlib
import json
import os
from test_biometric_security import FMD_A, canonical


CODE = "HE-DIRMED-CONSUL-PLT-02"


def test_medical_signature_endpoint_has_vertical_signer_dependency_loaded():
    # SignRecord is dispatched through the durable sync adapter.
    assert main.clinical_sync_adapters.vertical_signer is vertical_signer


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


def test_consent_keeps_both_witness_places_but_one_allows_operational_closure(monkeypatch):
    with database.SessionLocal() as db:
        document = evidence(db)
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (document, {}))
        assert main.get_firmas_documento_estado("WF-1", CODE, 7, db)["listo_para_cierre_medico"] is False
        evidence(db, role="TESTIGO_1")
        state = main.get_firmas_documento_estado("WF-1", CODE, 7, db)
        assert state["listo_para_cierre_medico"] is True
        assert state["testigos_esperados"] == 2
        assert state["testigos_firmados"] == 1
        assert state["testigos_formato_completos"] is False
        assert state["cierre_excepcional_por_testigos"] is True
        evidence(db, role="TESTIGO_2")
        complete_state = main.get_firmas_documento_estado("WF-1", CODE, 7, db)
        assert complete_state["listo_para_cierre_medico"] is True
        assert complete_state["testigos_formato_completos"] is True
        assert complete_state["cierre_excepcional_por_testigos"] is False


def test_representative_authorization_can_close_with_no_witness(monkeypatch):
    with database.SessionLocal() as db:
        document = evidence(db, role="TUTOR")
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (document, {}))
        state = main.get_firmas_documento_estado("WF-1", CODE, 7, db)
        assert state["paciente_firmado"] is True
        assert state["testigos_esperados"] == 2
        assert state["testigos_requeridos"] == 0
        assert state["testigos_firmados"] == 0
        assert state["listo_para_cierre_medico"] is True
        assert state["cierre_excepcional_por_testigos"] is True


@pytest.mark.parametrize(("occupied_role", "new_role", "expected_detail"), [
    ("PACIENTE", "TUTOR", "ya tiene la firma de quien lo autoriza"),
    ("TESTIGO_1", "TESTIGO_1", "lugar de testigo ya tiene una firma"),
])
def test_document_does_not_replace_an_existing_authorizer_or_witness(
    monkeypatch, occupied_role, new_role, expected_detail,
):
    with database.SessionLocal() as db:
        document = evidence(db, role="PACIENTE")
        if occupied_role == "TESTIGO_1":
            evidence(db, role="TESTIGO_1")
        patient = db.query(models.Paciente).filter_by(codigo_barras="WF-1").one()
        newcomer = models.BiometriaFirmanteEpisodio(
            paciente_id=patient.id, pt_num="WF-1", tipo_firmante=new_role,
            nombre_completo="ANOTHER SYNTHETIC SIGNER", estado="ACTIVO",
        )
        db.add(newcomer)
        db.commit()
        existing_ids = {
            row.id for row in db.query(models.FirmaDocumentoClinico).all()
        }
        monkeypatch.setattr(main, "verificar_huella_firmante_episodio", lambda **_: newcomer)
        monkeypatch.setattr(
            clinical_signing, "load_document_after_capture",
            lambda *_, **__: (document, {"id": patient.id}),
        )
        request = Request({"type": "http", "method": "POST", "path": "/", "headers": []})
        request.state.user = {"rol": "medico", "id": 777}
        req = main.schemas.FirmaBiometricaFirmanteInputSchema(
            fmd_template="synthetic", firmante_id=newcomer.id, rol_firmante=new_role,
            codigo_formato=CODE, tipo_documento="Consentimiento", evolution_slot=7,
            challenge_id="synthetic", session_id="synthetic",
        )
        with pytest.raises(HTTPException) as error:
            main.firmar_documento_biometrico_firmante("WF-1", req, request, db)
        assert error.value.status_code == 409
        assert expected_detail in str(error.value.detail)
        assert {row.id for row in db.query(models.FirmaDocumentoClinico).all()} == existing_ids


def test_signed_representative_identity_overrides_form_name_even_if_capacity_flag_true():
    data = {"paciente_capaz": True, "pariente": "NOMBRE SIN FIRMA", "representante_legal": "NOMBRE SIN FIRMA"}
    evidence_data = {
        "sello_paciente": "synthetic-seal", "rol_firmante_paciente": "REPRESENTANTE_LEGAL",
        "firmante_paciente": "REPRESENTANTE QUE FIRMÓ", "parentesco_paciente": "Madre",
    }
    for apply_signatures in (main.aplicar_firmas_a_pt_data, pdf_service.aplicar_firmas_a_pt_data):
        output = dict(data)
        signature_output = {}
        apply_signatures(output, dict(evidence_data), signature_output, paciente_capaz=True)
        assert output["pariente"] == "REPRESENTANTE QUE FIRMÓ"
        assert output["representante_legal"] == "REPRESENTANTE QUE FIRMÓ"
        assert output["declarante"] == "REPRESENTANTE QUE FIRMÓ"
        assert output["parentesco_paciente"] == "Madre"
        assert output["firma_paciente_biometrica"] is True


def test_pdf_service_does_not_fill_unsigned_witnesses_from_form_or_directory():
    data = {"pt_num": "WF-1", "testigo1": "CONTACTO NO FIRMANTE",
        "testigo_2": "SEGUNDO CONTACTO NO FIRMANTE", "TESTIGO_2": "SEGUNDO CONTACTO NO FIRMANTE"}
    signatures = {}
    pdf_service.aplicar_firmas_a_pt_data(data, {}, signatures, paciente_capaz=True)
    assert data["testigo1"] == ""
    assert data["testigo_2"] == ""
    assert data["TESTIGO_2"] == ""
    assert signatures["sello_testigo1"] == ""
    assert signatures["sello_testigo2"] == ""


def test_vertical_technical_signed_by_is_not_attributed_as_doctor_or_fea():
    pdf_data = {"medico_tratante": "MÉDICO DEL CENSO ACTUAL"}
    signature_data = {"sello_digital": None, "hash_sha256": ""}
    pdf_service.aplicar_metadata_firma_vertical_nativa(
        pdf_data, signature_data,
        {"signed_by": "Bitacora_SIS", "medico_tratante": "DOCTORA DEL REGISTRO", "cedula": "12345"},
    )
    assert signature_data["usuario_tecnico_vertical"] == "Bitacora_SIS"
    assert signature_data["origen_firma"] == "VERTICAL_EHR"
    assert signature_data["nombre_medico"] == pdf_data["medico_tratante"] == "DOCTORA DEL REGISTRO"
    assert signature_data["cedula"] == "12345"
    assert signature_data["sello_digital"] is None
    assert not signature_data["hash_sha256"]

    without_clinician = {"signed_by": "Bitacora_SIS"}
    only_origin = {}
    pdf_service.aplicar_metadata_firma_vertical_nativa({}, only_origin, without_clinician)
    assert "nombre_medico" not in only_origin
    assert "sello_digital" not in only_origin


def test_pdf_09_uses_vertical_slot_and_does_not_overlay_another_version(monkeypatch):
    import pdf_engine_09

    with database.SessionLocal() as db:
        db.add(models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-09", tipo_documento="Consentimiento",
            pt_num="5704", evolution_slot=2,
            contenido_soap_json=json.dumps({
                "mrnum": 2, "slot": 2,
                "acepto_y_autorizo_transfusion_de": "OTRA VERSION",
            }),
        ))
        db.commit()

    monkeypatch.setattr(main.kh_database, "fetch_full_ehr_dashboard", lambda *_: {"patient": {"name": "SYNTHETIC"}})
    monkeypatch.setattr(main.kh_database, "fetch_consentimiento_09", lambda *_, **__: {
        "mrnum": 1, "acepto_y_autorizo_transfusion_de": "VERSION VERTICAL 1", "firmado": False,
    })
    monkeypatch.setattr(main, "obtener_firmas_completas_documento", lambda *_, **__: {})
    captured = {}

    class PDFIntercepted(Exception):
        pass

    def capture_pdf(data, *_args, **_kwargs):
        captured.update(data)
        raise PDFIntercepted

    monkeypatch.setattr(pdf_engine_09, "generate_consentimiento_09", capture_pdf)
    with pytest.raises(PDFIntercepted):
        main.get_pdf_consentimiento_09("5704")
    assert captured["mrnum"] == captured["slot"] == 1
    assert captured["acepto_y_autorizo_transfusion_de"] == "VERSION VERTICAL 1"


def test_pdf_09_rejects_missing_requested_vertical_version(monkeypatch):
    monkeypatch.setattr(main.kh_database, "fetch_full_ehr_dashboard", lambda *_: {"patient": {"name": "SYNTHETIC"}})
    monkeypatch.setattr(main.kh_database, "fetch_consentimiento_09", lambda *_, **__: {"error": "not found"})
    with pytest.raises(HTTPException) as error:
        main.get_pdf_consentimiento_09("5704", mrnum=1)
    assert error.value.status_code == 404


def test_pdf_16_uses_vertical_slot_and_does_not_overlay_another_version(monkeypatch):
    import pdf_engine_16

    with database.SessionLocal() as db:
        db.add(models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-SINPRO-PLT-16", tipo_documento="Egreso y Resumen Clínico",
            pt_num="5704", evolution_slot=2,
            contenido_soap_json=json.dumps({
                "mrnum": 2, "slot": 2,
                "reea": "OTRA VERSION REEA",
            }),
        ))
        db.commit()

    monkeypatch.setattr(main.kh_database, "fetch_full_ehr_dashboard", lambda *_: {"patient": {"name": "PACIENTE TEST"}})
    monkeypatch.setattr(main.kh_database, "fetch_egreso_resumen_16", lambda *_, **__: {
        "mrnum": 1, "reea": "VERSION VERTICAL 1 REEA", "firmado": False,
    })
    monkeypatch.setattr(main, "obtener_firmas_completas_documento", lambda *_, **__: {})
    captured = {}

    class PDFIntercepted(Exception):
        pass

    def capture_pdf(data, *_args, **_kwargs):
        captured.update(data)
        raise PDFIntercepted

    monkeypatch.setattr(pdf_engine_16, "generate_egreso_resumen_16", capture_pdf)
    with pytest.raises(PDFIntercepted):
        main.get_pdf_egreso_resumen_16("5704")
    assert captured["mrnum"] == captured["slot"] == 1
    assert captured["reea"] == "VERSION VERTICAL 1 REEA"


def test_pdf_16_rejects_missing_requested_vertical_version(monkeypatch):
    monkeypatch.setattr(main.kh_database, "fetch_full_ehr_dashboard", lambda *_: {"patient": {"name": "PACIENTE TEST"}})
    monkeypatch.setattr(main.kh_database, "fetch_egreso_resumen_16", lambda *_, **__: {"error": "not found"})
    with pytest.raises(HTTPException) as error:
        main.get_pdf_egreso_resumen_16("5704", mrnum=1)
    assert error.value.status_code == 404


def test_vertical_signer_resolves_format_16():
    table, pk = vertical_signer.resolve_vertical_controller_and_pk("HE-DIRMED-SINPRO-PLT-16")
    assert table == "MR_ERC_HOS"
    assert pk == "MRNum_ERC_HOS"


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


@pytest.mark.parametrize(("profile_role", "document_role"), [
    ("PACIENTE", "PACIENTE"),
    ("TUTOR", "TUTOR"),
    ("FAMILIAR", "FAMILIAR"),
    ("TESTIGO_1", "TESTIGO_1"),
    ("TESTIGO_2", "TESTIGO_2"),
    ("TUTOR", "TESTIGO_1"),
    ("REPRESENTANTE_LEGAL", "TESTIGO_2"),
])
def test_real_challenge_capture_and_patient_signature_in_doctor_session(monkeypatch, profile_role, document_role):
    monkeypatch.setenv("BIOMETRIC_ATTESTATION_SECRET", "synthetic-test-attestation-secret-123456789")
    with database.SessionLocal() as db:
        patient = models.Paciente(nombre_completo="SYNTHETIC", codigo_barras="WF-2", status_ingreso="Ingresado")
        db.add(patient)
        db.flush()
        signer = models.BiometriaFirmanteEpisodio(paciente_id=patient.id, pt_num="WF-2",
            nombre_completo="SYNTHETIC SIGNER", tipo_firmante=profile_role, estado="ACTIVO",
            fmd_template=canonical(FMD_A), biometric_status="FMD_VALIDO")
        db.add(signer)
        db.commit()
        document = clinical_signing.ClinicalDocument("Consentimiento", {"acto": "A"}, "1", "MR_02_CI_TRATAMIENTO_QUIRURGICO:7")
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (document, {"id": patient.id}))
        is_witness = document_role in {"TESTIGO_1", "TESTIGO_2"}
        if is_witness:
            authorizer = models.BiometriaFirmanteEpisodio(
                paciente_id=patient.id, pt_num="WF-2", nombre_completo="SYNTHETIC PATIENT",
                tipo_firmante="PACIENTE", estado="ACTIVO",
            )
            db.add(authorizer)
            db.flush()
            _, authorizer_raw, authorizer_hash = clinical_signing.build_biometric_evidence_payload(
                document=document, codigo_formato=CODE, pt_num="WF-2", expediente="PT-WF-2",
                evolution_slot=7, patient_identity={"id": patient.id}, firmante_id=authorizer.id,
                rol_firmante="PACIENTE", nombre_firmante=authorizer.nombre_completo,
                identificacion=None, signed_at=dt.datetime.now(dt.timezone.utc),
            )
            db.add(models.FirmaDocumentoClinico(
                tipo_documento=document.tipo_documento, codigo_formato=CODE, pt_num="WF-2",
                expediente="PT-WF-2", evolution_slot=7, rol_firmante="PACIENTE",
                firmante_id=authorizer.id, nombre_medico=authorizer.nombre_completo,
                document_version=document.version_documento,
                signature_schema_version=clinical_signing.BIOMETRIC_EVIDENCE_VERSION,
                canonical_payload=authorizer_raw.decode(), payload_hash=authorizer_hash,
                hash_sha256=authorizer_hash, sello_digital="EVIDENCIA_BIOMETRICA_NO_FEA:authorizer",
                estado="ACTIVA",
            ))
            db.commit()
        request = Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1)})
        request.state.user = {"rol": "medico", "id": 777}
        bound_identity = biometric_security.role_bound_signer_identity(signer.id, document_role)
        challenge = main.get_biometric_challenge(main.schemas.BiometricChallengeRequest(
            action="FIRMA_FIRMANTE", session_id="wf-session", expected_identity_ref=bound_identity,
            patient_ref="WF-2", document_code=CODE, document_ref="7"), request, db)
        envelope = biometric_security.build_attested_capture(FMD_A, challenge["challenge_id"], "wf-session",
            dt.datetime.now(dt.timezone.utc).isoformat(), authorization=challenge["capture_authorization"],
            match_result={"match_success": True, "matched_identity": bound_identity,
                "matched_template_hash": hashlib.sha256(signer.fmd_template.encode()).hexdigest()})
        req = main.schemas.FirmaBiometricaFirmanteInputSchema(
            codigo_formato=CODE, tipo_documento="Consentimiento", evolution_slot=7,
            firmante_id=signer.id, rol_firmante=document_role, fmd_template=envelope,
            challenge_id=challenge["challenge_id"], session_id="wf-session")
        result = main.firmar_documento_biometrico_firmante("WF-2", req, request, db)
        assert result["success"] is True
        assert result["firma"]["rol_firmante"] == document_role
        assert result["firma"]["perfil_firmante"] == profile_role
        assert db.get(models.BiometriaFirmanteEpisodio, signer.id).tipo_firmante == profile_role
        audit = db.query(models.AuditoriaLog).filter_by(accion="EVIDENCIA_BIOMETRICA_ACTO_NO_FEA").one()
        assert audit.usuario_id is None and audit.actor_real == "medico:777"
        with pytest.raises(HTTPException):
            main.firmar_documento_biometrico_firmante("WF-2", req, request, db)
        assert db.query(models.FirmaDocumentoClinico).count() == (2 if is_witness else 1)


def test_document_role_assignment_is_limited_by_enrolled_profile():
    assert main.resolve_document_signer_role("TUTOR", "TESTIGO_1", allow_document_assignment=True) == "TESTIGO_1"
    assert main.resolve_document_signer_role("TESTIGO_2", "TESTIGO_1", allow_document_assignment=True) == "TESTIGO_1"
    with pytest.raises(HTTPException):
        main.resolve_document_signer_role("PACIENTE", "TESTIGO_1", allow_document_assignment=True)
    with pytest.raises(HTTPException):
        main.resolve_document_signer_role("CONTACTO", "TESTIGO_1", allow_document_assignment=True)


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


def test_vertical_falls_back_to_one_exact_name_when_identification_differs(monkeypatch):
    class Connection:
        def __init__(self):
            self.query_count = 0
            self.queries = []
        def cursor(self): return self
        def execute(self, sql, *_args):
            self.query_count += 1
            self.queries.append(sql)
        def fetchall(self):
            return [] if self.query_count == 1 else [(257, "authorized-pin")]
        def close(self): pass
    connection = Connection()
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: connection)
    assert vertical_signer.resolve_doctor_pr_and_pin(
        "JOSE JOSE PRUEBA ENRIQUEZ", "PRUEBA-99281"
    ) == (257, "authorized-pin")
    assert connection.queries
    assert all("FROM V_MRPR" in query for query in connection.queries)


def test_initial_enrollment_configures_existing_vertical_doctor_without_insert(monkeypatch):
    class Connection:
        def __init__(self):
            self.queries = []
            self.commits = 0
            self.rollbacks = 0
            self.fetchone_calls = 0
        def cursor(self): return self
        def execute(self, sql, params=()): self.queries.append((sql, params))
        def fetchall(self): return [(88, None, True)]
        def fetchone(self):
            self.fetchone_calls += 1
            return None if self.fetchone_calls == 1 else ("654321",)
        def commit(self): self.commits += 1
        def rollback(self): self.rollbacks += 1
        def close(self): pass
    connection = Connection()
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: connection)
    monkeypatch.setattr(vertical_signer.secrets, "randbelow", lambda _limit: 654321)

    result = vertical_signer.configure_vertical_doctor_signature_profile(
        "DRA SYNTHETIC", "CED-SYNTHETIC", modified_by="tester"
    )

    assert result == {"pr_num": 88, "already_configured": False}
    assert connection.commits == 1
    assert any(query.lstrip().startswith("UPDATE PR SET") for query, _ in connection.queries)
    assert all("INSERT" not in query.upper() for query, _ in connection.queries)


def test_initial_enrollment_preserves_an_existing_vertical_code(monkeypatch):
    class Connection:
        def __init__(self):
            self.queries = []
            self.rollbacks = 0
        def cursor(self): return self
        def execute(self, sql, params=()): self.queries.append((sql, params))
        def fetchall(self): return [(88, "111111", True)]
        def rollback(self): self.rollbacks += 1
        def close(self): pass
    connection = Connection()
    monkeypatch.setattr(main.kh_database, "get_kh_connection", lambda: connection)

    result = vertical_signer.configure_vertical_doctor_signature_profile(
        "DRA SYNTHETIC", "CED-SYNTHETIC", "222222"
    )
    assert result == {"pr_num": 88, "already_configured": True}
    assert connection.rollbacks == 1
    assert all(not query.lstrip().startswith("UPDATE PR SET") for query, _ in connection.queries)


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
                return (
                    ("Bitacora_SIS", dt.datetime.now(), "SG", native_chain, "DRA SYNTHETIC", 5)
                    if calls else
                    (None, None, "RG", None, "DRA SYNTHETIC", None)
                )
            return None
        def fetchall(self): return [("MRNum_CI_CC",), ("N_MEDICO",), ("PRNum",)]
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


def test_acknowledged_vertical_signature_reconciliation_never_replays_signrecord(monkeypatch):
    class Connection:
        def cursor(self): return self
        def execute(self, sql, params=()): self.sql = sql
        def fetchone(self):
            if "V_MRPT" in self.sql: return ("PC", 1, "parent-guid", "patient-guid")
            if "FROM PC" in self.sql: return (1,)
            if "SELECT SignedBy" in self.sql:
                return ("Bitacora_SIS", dt.datetime.now(), "RG", None, "DRA SYNTHETIC", 5)
            return None
        def fetchall(self): return [("MRNum_CI_CC",), ("N_MEDICO",), ("PRNum",)]
        def close(self): pass
    monkeypatch.setattr(main.kh_database, "get_kh_connection", Connection)
    monkeypatch.setattr(vertical_signer, "get_vertical_session", lambda **_: pytest.fail("SignRecord no debe repetirse"))
    with pytest.raises(vertical_signer.VerticalSignatureConfirmationPending, match="NATIVE_STATUS_NOT_SIGNED"):
        vertical_signer.sign_in_vertical_api(
            "MR_CI_CC", 7, "101", pr_num=5, auth_code="synthetic",
            doctor_name="DRA SYNTHETIC", confirmation_only=True,
        )


def test_new_medical_signature_cannot_claim_a_preexisting_native_chain(monkeypatch):
    calls = []
    signed_on = dt.datetime.now()
    class Connection:
        def cursor(self): return self
        def execute(self, sql, params=()): self.sql = sql
        def fetchone(self):
            if "V_MRPT" in self.sql: return ("PC", 1, "parent-guid", "patient-guid")
            if "FROM PC" in self.sql: return (1,)
            if "SELECT SignedBy" in self.sql:
                return ("Bitacora_SIS", signed_on, "SG", "old-native-chain", "DRA SYNTHETIC", 5)
            return None
        def fetchall(self): return [("MRNum_CI_CC",), ("N_MEDICO",), ("PRNum",)]
        def close(self): pass
    class Session:
        def post(self, *_args, **_kwargs):
            calls.append(True)
            return SimpleNamespace(status_code=200, text="Document has been signed")
    monkeypatch.setattr(main.kh_database, "get_kh_connection", Connection)
    monkeypatch.setattr(vertical_signer, "get_vertical_session", lambda **_: Session())
    monkeypatch.setattr(vertical_signer, "_NATIVE_CONFIRMATION_DELAYS", ())
    with pytest.raises(vertical_signer.VerticalSignatureConfirmationPending, match="NATIVE_SIGNATURE_UNCHANGED"):
        vertical_signer.sign_in_vertical_api(
            "MR_CI_CC", 7, "101", pr_num=5, auth_code="synthetic",
            doctor_name="DRA SYNTHETIC",
        )
    assert len(calls) == 1


@pytest.mark.parametrize("error_class", [
    "VerticalSignatureConfirmationPending", "VerticalSignatureOutcomeUnknown",
])
def test_uncertain_vertical_sync_skips_new_write_digest_guard(monkeypatch, error_class):
    import clinical_sync_adapters
    call = {}
    monkeypatch.setattr(vertical_signer, "sign_in_vertical_api", lambda **kwargs: call.update(kwargs) or True)
    acknowledged_at = dt.datetime.now(dt.timezone.utc)
    operation = SimpleNamespace(
        operation_type="VERTICAL_SIGN", operation_id="synthetic", patient_ref="101",
        created_at=acknowledged_at - dt.timedelta(seconds=2), external_applied_at=None,
        attempts_log=[SimpleNamespace(error_class=error_class, finished_at=acknowledged_at)],
        payload={"codigo_formato": "HE-DIRMED-CONSUL-PLT-04", "target_slot": 7,
                 "controller_name": "MR_CI_CC", "mrnum": 7, "doctor_name": "DRA SYNTHETIC",
                 "document_digest": "previous-version"},
    )
    assert clinical_sync_adapters.dispatcher(operation)() is True
    assert call["confirmation_only"] is True
    assert call["not_after"] == acknowledged_at


def test_native_confirmation_requires_clinician_link_not_technical_account():
    row = ("DRA SYNTHETIC", dt.datetime.now(), "SG", "native-chain")
    assert vertical_signer._native_signature_confirmed(
        row, doctor_name="DRA SYNTHETIC", resolved_pr=5,
        identity_field=None, pr_field=None,
    ) is False
    assert vertical_signer._native_signature_confirmed(
        row + (5,), doctor_name="DRA SYNTHETIC", resolved_pr=5,
        identity_field="N_MEDICO", pr_field=None,
    ) is True


def test_two_witness_roles_cannot_be_the_same_registered_person():
    info = {"sello_paciente": "p", "sello_testigo1": "a", "sello_testigo2": "b",
        "firmante_paciente_id": 1, "firmante_testigo1_id": 2, "firmante_testigo2_id": 2}
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=2) is False


@pytest.mark.parametrize(("code", "requires_authorizer", "witnesses"), [
    ("HE-DIRMED-CONSUL-PLT-02", True, 2),
    ("HE-DIRMED-CONSUL-PLT-04", True, 1),
    ("HE-DIRMED-CONSUL-PLT-CC", True, 1),
    ("HE-DIRMED-CONSUL-PLT-06", True, 1),
    ("HE-DIRMED-CONSUL-PLT-15", True, 1),
    ("HE-DIRMED-CONSUL-PLT-EED", True, 0),
    ("HE-DIRMED-SINPRO-PLT-15", True, 2),
    ("HE-DIRMED-NOTAS-HOS-EV", False, 0),
    ("HE-DIRMED-SINPRO-PLT-87/01", False, 0),
])
def test_registered_format_has_explicit_signature_policy(code, requires_authorizer, witnesses):
    assert clinical_signing.consent_signature_policy(code) == (requires_authorizer, witnesses)


def test_new_clinical_source_requires_declared_signature_policy(monkeypatch):
    monkeypatch.setattr(vertical_signer, "resolve_vertical_controller_and_pk",
        lambda _code: ("MR_CI_FUTURO", "MRNum_CI_FUTURO"))
    with pytest.raises(clinical_signing.ClinicalDocumentUnavailable, match="regla de firmas"):
        clinical_signing.consent_signature_policy("HE-DIRMED-CONSUL-PLT-FUTURO")


@pytest.mark.parametrize(("source", "expected"), [
    ({"PACIENTE_CAPAZ": False}, False),
    ({"paciente_capaz": "no"}, False),
    ({"paciente_capaz": "sí"}, True),
    ({"paciente_capaz": 1}, True),
    ({"paciente_capaz": "indeterminado"}, None),
    ({"INTTYP": "INDIRECTO", "PARIENTE": "FAMILIAR"}, None),
    ({}, None),
])
def test_capacity_comes_only_from_explicit_document_field(source, expected):
    document = clinical_signing.ClinicalDocument("Consentimiento", source, "1", "MR_CI:1")
    assert clinical_signing.explicit_patient_capacity(document) is expected


def test_consent_keeps_two_witness_places_but_closes_with_operational_minimum():
    info = {"sello_paciente": "authorizer", "firmante_paciente_id": 1,
        "sello_testigo1": "witness", "firmante_testigo1_id": 2}
    assert clinical_signing.required_consent_witnesses(CODE) == 2
    patient_minimum = clinical_signing.minimum_consent_witnesses_for_closure(CODE, "PACIENTE")
    responsible_minimum = clinical_signing.minimum_consent_witnesses_for_closure(CODE, "TUTOR")
    assert patient_minimum == 1
    assert responsible_minimum == 0
    assert clinical_signing.signed_witness_count(info) == 1
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=patient_minimum) is True
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=responsible_minimum) is True
    del info["sello_testigo1"]
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=patient_minimum) is False
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=responsible_minimum) is True
    info["sello_testigo1"] = "witness"
    info["firmante_testigo1_id"] = 1
    assert clinical_signing.signed_witness_count(info) == 0
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=responsible_minimum) is False
    info["firmante_testigo1_id"] = 2
    info["sello_testigo2"] = "second witness"
    info["firmante_testigo2_id"] = 2
    assert clinical_signing.signed_witness_count(info) == 1
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=responsible_minimum) is False
    del info["firmante_testigo2_id"]
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=responsible_minimum) is False


@pytest.mark.parametrize(("code", "patient_minimum", "representative_minimum"), [
    ("HE-DIRMED-CONSUL-PLT-02", 1, 0),
    ("HE-DIRMED-CONSUL-PLT-04", 1, 0),
    ("HE-DIRMED-CONSUL-PLT-EED", 0, 0),
])
def test_minimum_for_closure_is_separate_from_template_places(code, patient_minimum, representative_minimum):
    assert clinical_signing.minimum_consent_witnesses_for_closure(code, "PACIENTE") == patient_minimum
    assert clinical_signing.minimum_consent_witnesses_for_closure(code, "FAMILIAR") == representative_minimum


def test_single_witness_format_and_authorization_without_witness():
    info = {"sello_paciente": "authorizer", "firmante_paciente_id": 1,
        "sello_testigo2": "legacy witness", "firmante_testigo2_id": 2}
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=1) is True
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=0) is True
    info["firmante_testigo2_id"] = 1
    assert clinical_signing.consent_signatures_complete(info, required_witnesses=1) is False
    with pytest.raises(ValueError):
        clinical_signing.consent_signatures_complete(info, required_witnesses=3)


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


@pytest.mark.parametrize("sync_state", ["REQUIRES_RECONCILIATION", "SYNCED"])
def test_medical_sync_stays_visible_when_vertical_document_cannot_be_read(monkeypatch, sync_state):
    with database.SessionLocal() as db:
        patient = models.Paciente(nombre_completo="SYNTHETIC PATIENT", codigo_barras="WF-1")
        db.add(patient)
        db.flush()
        operation = models.ClinicalSyncOperation(
            idempotency_key="synthetic-medical-offline",
            operation_type="VERTICAL_SIGN",
            aggregate_type="clinical_document",
            aggregate_id=f"WF-1:{CODE}:7",
            patient_ref="WF-1",
            payload={},
            request_fingerprint="a" * 64,
            state=sync_state,
            local_applied_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(operation)
        db.flush()
        db.add(models.FirmaDocumentoClinico(
            tipo_documento="Consentimiento", codigo_formato=CODE, pt_num="WF-1",
            expediente="PT-WF-1", evolution_slot=7, rol_firmante="MEDICO",
            nombre_medico="DRA SYNTHETIC", sello_digital="ECDSA:synthetic",
            document_version="old-version", estado="ACTIVA",
            clinical_sync_operation_id=operation.operation_id,
        ))
        db.commit()
        def offline(*_args, **_kwargs):
            raise clinical_signing.ClinicalDocumentUnavailable("Vertical temporalmente inaccesible")
        monkeypatch.setattr(clinical_signing, "load_authoritative_document", offline)
        state = main.get_firmas_documento_estado("WF-1", CODE, 7, db)
        assert state["medico_firmado"] is False
        assert state["medico_sync_state"] == sync_state
        assert state["medico_sync_operation_id"] == str(operation.operation_id)
        assert state["medico_sync_unverified"] is True


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

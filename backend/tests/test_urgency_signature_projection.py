"""Pure regression vectors; no ERP writes, biometric samples or test database."""

import datetime as dt
from types import SimpleNamespace
from unittest.mock import patch

import clinical_signing as cs
import clinical_sync_adapters
import vertical_signer


CODE = "HE-DIRMED-SINPRO-PLT-87/01"


def _document(content):
    return cs.ClinicalDocument(
        tipo_documento="Nota de evolución",
        contenido_clinico=content,
        version_documento="2026-09-24T10:00:00",
        source_identifier="MR_NE_URG:8:1",
    )


def _signature(document):
    _, raw, digest, _ = cs.build_canonical_payload(
        document=document,
        codigo_formato=CODE,
        pt_num="synthetic-1",
        expediente="PT-synthetic-1",
        evolution_slot=1,
        patient_identity={"id": 1},
        medico_id=1,
        nombre_medico="MEDICO SINTETICO",
        cedula="CED-SINTETICA",
        proposito="CIERRE_Y_AUTORIA_CLINICA",
        signed_at=dt.datetime(2026, 9, 24, 10, tzinfo=cs.MEXICO_CITY),
        key_id="synthetic-key",
    )
    return SimpleNamespace(
        canonical_payload=raw.decode(), payload_hash=digest,
        codigo_formato=CODE, pt_num="synthetic-1", evolution_slot=1,
        signature_schema_version=cs.SCHEMA_VERSION,
        document_version=document.version_documento,
        tipo_documento=document.tipo_documento,
    )


def test_urgency_native_signature_metadata_does_not_hide_original_evidence():
    original = _document({
        "mrnum_ne_urg": 8, "slot_in_row": 1, "subjetivo": "dolor",
        "signed_by": None, "signed_on": None, "es_signature": None,
        "mr_st": "RG", "firmado": False,
    })
    current = _document({
        "mrnum_ne_urg": 8, "slot_in_row": 1, "subjetivo": "dolor",
    })
    signature = _signature(original)
    with patch.object(cs, "verify_signature_record", return_value={"complete": True}), \
            patch.object(cs, "load_authoritative_document", return_value=(current, {})):
        assert cs.evidence_matches_current(None, signature, current)
        assert cs.compare_current_document(None, signature) is True


def test_urgency_clinical_edit_still_invalidates_signed_version():
    original = _document({"subjetivo": "dolor", "signed_by": None})
    edited = _document({"subjetivo": "dolor nuevo", "signed_by": "service"})
    signature = _signature(original)
    with patch.object(cs, "verify_signature_record", return_value={"complete": True}), \
            patch.object(cs, "load_authoritative_document", return_value=(edited, {})):
        assert not cs.evidence_matches_current(None, signature, edited)
        assert cs.compare_current_document(None, signature) is False


def test_urgency_loader_excludes_native_signature_metadata():
    evolution = {
        "mrnum_ne_urg": 8, "slot_in_row": 1, "date_iso": "2026-09-24T10:00:00",
        "subjetivo": "dolor", "signed_by": "service", "signed_on": "now",
        "es_signature": "native-chain", "mr_st": "RG", "firmado": True,
    }
    with patch("kh_database.fetch_full_ehr_dashboard", return_value={
        "evoluciones": {"evolucion1": evolution},
    }):
        loaded = cs._load_vertical_document("synthetic-1", CODE, 1)
    assert loaded["subjetivo"] == "dolor"
    assert loaded["__source_identifier__"] == "MR_NE_URG:8:1"
    assert not set(evolution).intersection(cs._URGENCY_NATIVE_SIGNATURE_FIELDS) & set(loaded)


def test_registered_urgency_needs_acknowledgement_fresh_chain_and_identity():
    signed_on = dt.datetime(2026, 9, 24, 10, 0, 5)
    row = ("service", signed_on, "RG", "native-chain", "MEDICO SINTETICO", 5)
    options = dict(
        doctor_name="MEDICO SINTETICO", resolved_pr=5,
        identity_field="N_MEDICO", pr_field="PRNum",
        not_before=dt.datetime(2026, 9, 24, 10),
        allow_registered_urgency_signature=True,
    )
    check = vertical_signer._native_signature_confirmation_issue
    assert check(row, **options) is None
    assert check(row, **{**options, "allow_registered_urgency_signature": False}) == "NATIVE_STATUS_NOT_SIGNED"
    assert check(row, **{**options, "not_before": None}) == "NATIVE_STATUS_NOT_SIGNED"
    assert check(row[:3] + (None,) + row[4:], **options) == "NATIVE_CHAIN_MISSING"
    assert check(row[:4] + ("OTRO MEDICO", 6), **options) == "NATIVE_PHYSICIAN_MISMATCH"
    assert check(row, **{**options, "not_before": dt.datetime(2026, 9, 24, 10, 1)}) == "NATIVE_SIGNATURE_PREDATES_OPERATION"


def test_acknowledged_urgency_rg_requires_new_native_evidence():
    signed_on = dt.datetime.now()
    native_reads = []
    posts = []

    class Connection:
        def cursor(self):
            return self

        def execute(self, sql, params=()):
            self.sql = sql

        def fetchone(self):
            if "V_MRPT" in self.sql:
                return ("PC", 1, "parent-guid", "patient-guid")
            if "FROM PC" in self.sql:
                return (1,)
            if "SELECT SignedBy" in self.sql:
                native_reads.append(True)
                if len(native_reads) == 1:
                    return (None, None, "RG", None, "MEDICO SINTETICO", 5)
                return ("service", signed_on, "RG", "new-native-chain", "MEDICO SINTETICO", 5)
            return None

        def fetchall(self):
            return [(name,) for name in (
                "MRNum_NE_URG", "N_MEDICO", "PRNum", "SignedBy", "SignedOn", "MR_ST", "ESignature",
            )]

        def rollback(self):
            pass

        def close(self):
            pass

    class Session:
        def post(self, url, **kwargs):
            posts.append(kwargs["json"])
            return SimpleNamespace(status_code=200, text="Document has been signed")

    with patch("kh_database.get_kh_connection", side_effect=Connection), \
            patch.object(vertical_signer, "get_vertical_session", return_value=Session()):
        assert vertical_signer.sign_in_vertical_api(
            "MR_NE_URG", 8, "101", pr_num=5, auth_code="synthetic",
            doctor_name="MEDICO SINTETICO", not_before=signed_on - dt.timedelta(seconds=2),
        ) is True
    assert len(posts) == 1
    assert len(native_reads) == 2


def test_urgency_rg_without_acknowledgement_cannot_reconcile():
    signed_on = dt.datetime.now()

    class Connection:
        def cursor(self):
            return self

        def execute(self, sql, params=()):
            self.sql = sql

        def fetchone(self):
            if "V_MRPT" in self.sql:
                return ("PC", 1, "parent-guid", "patient-guid")
            if "FROM PC" in self.sql:
                return (1,)
            if "SELECT SignedBy" in self.sql:
                return ("service", signed_on, "RG", "native-chain", "MEDICO SINTETICO", 5)
            return None

        def fetchall(self):
            return [(name,) for name in ("MRNum_NE_URG", "N_MEDICO", "PRNum")]

        def close(self):
            pass

    with patch("kh_database.get_kh_connection", side_effect=Connection), \
            patch.object(vertical_signer, "get_vertical_session", side_effect=AssertionError("No SignRecord")):
        try:
            vertical_signer.sign_in_vertical_api(
                "MR_NE_URG", 8, "101", pr_num=5, auth_code="synthetic",
                doctor_name="MEDICO SINTETICO", confirmation_only=True,
                not_before=signed_on - dt.timedelta(seconds=2),
            )
        except vertical_signer.VerticalSignatureConfirmationPending as exc:
            assert str(exc) == "NATIVE_STATUS_NOT_SIGNED"
        else:
            raise AssertionError("An unacknowledged RG row cannot confirm the operation")


def test_acknowledged_urgency_cannot_reuse_an_old_rg_chain():
    signed_on = dt.datetime.now()

    class Connection:
        def cursor(self):
            return self

        def execute(self, sql, params=()):
            self.sql = sql

        def fetchone(self):
            if "V_MRPT" in self.sql:
                return ("PC", 1, "parent-guid", "patient-guid")
            if "FROM PC" in self.sql:
                return (1,)
            if "SELECT SignedBy" in self.sql:
                return ("service", signed_on, "RG", "old-native-chain", "MEDICO SINTETICO", 5)
            return None

        def fetchall(self):
            return [(name,) for name in ("MRNum_NE_URG", "N_MEDICO", "PRNum")]

        def rollback(self):
            pass

        def close(self):
            pass

    class Session:
        def post(self, url, **kwargs):
            return SimpleNamespace(status_code=200, text="Document has been signed")

    with patch("kh_database.get_kh_connection", side_effect=Connection), \
            patch.object(vertical_signer, "get_vertical_session", return_value=Session()), \
            patch.object(vertical_signer, "_NATIVE_CONFIRMATION_DELAYS", ()):
        try:
            vertical_signer.sign_in_vertical_api(
                "MR_NE_URG", 8, "101", pr_num=5, auth_code="synthetic",
                doctor_name="MEDICO SINTETICO", not_before=signed_on - dt.timedelta(seconds=2),
            )
        except vertical_signer.VerticalSignatureConfirmationPending as exc:
            assert str(exc) == "NATIVE_SIGNATURE_UNCHANGED"
        else:
            raise AssertionError("An unchanged old native chain cannot confirm a new signature")


def test_reconciliation_never_promotes_an_uncertain_http_response_to_acknowledgement():
    now = dt.datetime.now(dt.timezone.utc)
    cases = [
        (["VerticalSignatureOutcomeUnknown"], False),
        (["VerticalSignatureOutcomeUnknown", "VerticalSignatureConfirmationPending"], False),
        (["VerticalSignatureConfirmationPending"], True),  # legacy first uncertainty
        (["VerticalSignatureAcknowledgedPending"], True),
    ]
    calls = []
    with patch.object(vertical_signer, "sign_in_vertical_api", side_effect=lambda **kw: calls.append(kw) or True):
        for classes, expected in cases:
            operation = SimpleNamespace(
                operation_type="VERTICAL_SIGN", operation_id="synthetic",
                patient_ref="101", created_at=now - dt.timedelta(seconds=2),
                external_applied_at=None,
                attempts_log=[
                    SimpleNamespace(error_class=kind, finished_at=now)
                    for kind in classes
                ],
                payload={
                    "codigo_formato": CODE, "controller_name": "MR_NE_URG",
                    "mrnum": 8, "target_slot": 1, "doctor_name": "MEDICO SINTETICO",
                },
            )
            assert clinical_sync_adapters.dispatcher(operation)() is True
            assert calls[-1]["confirmation_only"] is True
            assert calls[-1]["acknowledged_by_vertical"] is expected

"""Public QR verification regressions using only synthetic data and files."""

import datetime
import hashlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

import kh_database
import main


class _Query:
    def __init__(self, record):
        self.record = record

    def filter(self, *_args):
        return self

    def first(self):
        return self.record


class _Db:
    def __init__(self, record):
        self.record = record

    def query(self, *_args):
        return _Query(self.record)


def _request():
    return Request({"type": "http", "method": "GET", "path": "/verificar", "headers": []})


def _record(tmp_path, pdf_bytes=b"%PDF-1.4\nsynthetic PDF content"):
    pdf = tmp_path / "synthetic.pdf"
    pdf.write_bytes(pdf_bytes)
    return SimpleNamespace(
        doc_uuid="v1_" + "A" * 43,
        codigo_formato="HE-DIRMED-EXPEDIENTE-COMPLETO",
        pt_num="TEST-123",
        slot=1,
        expediente="PT-TEST-123",
        tipo_documento="Expediente clínico completo",
        pdf_path=str(pdf),
        hash_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
        fecha_generacion=datetime.datetime(2026, 9, 24, 15, 18, 49),
        medico_nombre="NO ES FIRMANTE DEL COMPILADO",
        medico_cedula="PRUEBA-1",
    )


def test_public_qr_shows_patient_and_only_proves_copy_integrity(tmp_path, monkeypatch):
    record = _record(tmp_path)
    monkeypatch.setattr(
        main, "_qr_patient_identity", lambda _db, _pt: ("PACIENTE DE PRUEBA", "46 años")
    )
    db = _Db(record)

    state = main.get_documento_estado_verificacion(_request(), id=record.doc_uuid, db=db)
    assert state["paciente"] == "PACIENTE DE PRUEBA"
    assert state["folio"] == "PT-TEST-123"
    assert state["edad"] == "46 años"
    assert state["estado"] == "COPIA_INTEGRA_VERIFICADA"
    assert state["medico"] is None
    assert state["fecha_generacion"] == "24/09/2026 15:18:49"
    spoofed = main.get_documento_estado_verificacion(
        _request(), id=record.doc_uuid, pt="OTHER-PATIENT", folio="PT-OTHER", doc="OTHER", db=db
    )
    assert spoofed["paciente"] == "PACIENTE DE PRUEBA"
    assert spoofed["folio"] == "PT-TEST-123"

    html = main.verificar_documento_publico(_request(), id=record.doc_uuid, db=db).body.decode()
    assert "PACIENTE DE PRUEBA" in html
    assert "PT-TEST-123" in html
    assert "COPIA ÍNTEGRA VERIFICADA" in html
    assert "AUTORIZADO Y FIRMADO" not in html
    assert "Sello Digital FEA" not in html
    assert "Atribución Criptográfica y Firma Médica FEA" not in html
    assert "&amp;pt=" not in html
    assert "no-store" in main.verificar_documento_publico(_request(), id=record.doc_uuid, db=db).headers["cache-control"]


def test_public_html_escapes_patient_name(tmp_path, monkeypatch):
    record = _record(tmp_path)
    monkeypatch.setattr(
        main, "_qr_patient_identity", lambda _db, _pt: ("<script>alert(1)</script>", "46 años")
    )
    html = main.verificar_documento_publico(_request(), id=record.doc_uuid, db=_Db(record)).body.decode()
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_altered_copy_never_reports_verified(tmp_path, monkeypatch):
    record = _record(tmp_path)
    (tmp_path / "synthetic.pdf").write_bytes(b"%PDF-1.4\naltered")
    monkeypatch.setattr(main, "_qr_patient_identity", lambda _db, _pt: ("PACIENTE", "46 años"))
    state = main.get_documento_estado_verificacion(_request(), id=record.doc_uuid, db=_Db(record))
    assert state["valido"] is False
    assert state["estado"] == "INTEGRIDAD_COMPROMETIDA"
    html = main.verificar_documento_publico(_request(), id=record.doc_uuid, db=_Db(record)).body.decode()
    assert "Abrir Documento PDF Oficial" not in html


def test_missing_copy_does_not_offer_a_broken_pdf_link(tmp_path, monkeypatch):
    record = _record(tmp_path)
    (tmp_path / "synthetic.pdf").unlink()
    monkeypatch.setattr(main, "_qr_patient_identity", lambda _db, _pt: ("PACIENTE", "46 años"))
    state = main.get_documento_estado_verificacion(_request(), id=record.doc_uuid, db=_Db(record))
    assert state["estado"] == "RECURSO_NO_DISPONIBLE"
    html = main.verificar_documento_publico(_request(), id=record.doc_uuid, db=_Db(record)).body.decode()
    assert "Abrir Documento PDF Oficial" not in html


def test_public_verification_requires_opaque_id(tmp_path):
    record = _record(tmp_path)
    with pytest.raises(HTTPException) as exc:
        main.get_documento_estado_verificacion(_request(), pt="TEST-123", db=_Db(record))
    assert exc.value.status_code == 404


def test_public_endpoint_needs_no_session_and_disables_caching(tmp_path, monkeypatch):
    record = _record(tmp_path)
    monkeypatch.setattr(main, "_qr_patient_identity", lambda _db, _pt: ("PACIENTE DE PRUEBA", "46 años"))
    main.app.dependency_overrides[main.get_db] = lambda: _Db(record)
    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            result = client.get(f"/api/verificar/documento-estado?id={record.doc_uuid}")
            page = client.get(f"/verificar?id={record.doc_uuid}")
        assert result.status_code == 200
        assert result.json()["paciente"] == "PACIENTE DE PRUEBA"
        assert result.headers["cache-control"] == "no-store"
        assert result.headers["referrer-policy"] == "no-referrer"
        assert page.status_code == 200
        assert "PACIENTE DE PRUEBA" in page.text
        assert "COPIA ÍNTEGRA VERIFICADA" in page.text
        assert page.headers["cache-control"] == "no-store"
    finally:
        main.app.dependency_overrides.pop(main.get_db, None)


def test_patient_lookup_uses_exact_pt_number_and_closes_connection(monkeypatch):
    calls = []

    class Cursor:
        def execute(self, statement, params):
            calls.append((statement, params))

        def fetchone(self):
            return ("PACIENTE DE PRUEBA", datetime.date(1980, 9, 24), 46)

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(kh_database, "get_kh_connection", Connection)
    identity = kh_database.fetch_patient_identity_for_qr("TEST-123")
    assert identity["nombre"] == "PACIENTE DE PRUEBA"
    assert identity["edad"].endswith("años")
    assert calls[0][1] == ("TEST-123",)
    assert calls[-1] == "closed"

"""Regression tests for signature evidence in specialized PDF renderers."""

from pypdf import PdfReader

import pdf_engine_32_01
import pdf_engine_24
import pdf_engine_v2
from services import pdf_service


def test_consentimiento_32_01_keeps_explicit_signature_payload(tmp_path):
    output = tmp_path / "consentimiento_32_01.pdf"
    patient_data = {
        "nombre": "PACIENTE DE PRUEBA",
        "dob": "01/01/1980",
        "mrn": "PT-TEST",
        "cama": "URGENCIAS",
        "edad": "46",
        "sexo": "M",
        "grupo_rh": "O+",
        "alergias": "NEGADAS",
        "diagnostico": "PRUEBA DE RENDERIZADO",
        "tipo_interrogatorio": "Directo",
        "medico_tratante": "MEDICO DE PRUEBA",
        "medico_autorizado": "MEDICO DE PRUEBA",
        "cedula": "CED-TEST",
        "paciente_o_representante": "PACIENTE DE PRUEBA",
        "testigo1": "TESTIGO UNO",
        "testigo2": "TESTIGO DOS",
        "paciente_capaz": True,
    }
    signature_data = {
        "sello_digital": "ECDSA:MEDICO-TEST",
        "hash_sha256": "HASH-TEST",
        "fecha_hora_firma": "24/09/2026 14:00:00",
        "nombre_medico": "MEDICO DE PRUEBA",
        "cedula": "CED-TEST",
        "sello_paciente": "BIO:PACIENTE-TEST",
        "sello_testigo1": "BIO:TESTIGO-1",
        "sello_testigo2": "BIO:TESTIGO-2",
    }

    pdf_engine_32_01.generate_consentimiento_32_01(
        patient_data,
        str(output),
        firma_data=signature_data,
    )
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(output)).pages)

    assert "AUTORIZADO CON HUELLA" in text
    assert "TESTIGO - HUELLA" in text
    assert "FIRMADO BIOMÉTRICAMENTE CON HUELLA" in text
    assert "ECDSA:MEDICO-TEST" in text


def test_consentimiento_32_01_labels_native_record_without_claiming_biometric_signature(tmp_path):
    output = tmp_path / "consentimiento_32_native.pdf"
    pdf_engine_32_01.generate_consentimiento_32_01(
        {
            "nombre": "PACIENTE DE PRUEBA", "mrn": "PT-TEST", "sexo": "M",
            "alergias": "NEGADAS", "edad": "46", "dob": "01/01/1980",
            "medico_tratante": "MEDICO DE PRUEBA",
        },
        str(output),
        firma_data={
            "firma_nativa_vertical": True,
            "usuario_tecnico_vertical": "USUARIO-VERTICAL",
            "fecha_hora_firma_vertical": "24/09/2026 10:00",
        },
    )
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(output)).pages)
    assert "REGISTRO NATIVO EN VERTICAL" in text
    assert "USUARIO-VERTICAL" in text
    assert "FIRMADO BIOMÉTRICAMENTE CON HUELLA" not in text


def test_general_evolution_pdfs_keep_each_signature_with_its_own_note(tmp_path):
    patient = {
        "nombre": "PACIENTE DE PRUEBA", "mrn": "PT-TEST", "sexo": "M",
        "alergias": "NEGADAS", "edad": "46", "dob": "01/01/1980",
    }
    evolutions = [
        {"num": 1, "fecha": "01/09/2026", "subjetivo": "Primera nota", "medico": "MEDICO UNO"},
        {"num": 2, "fecha": "02/09/2026", "subjetivo": "Segunda nota", "medico": "MEDICO DOS"},
    ]
    signatures = {
        1: {
            "sello_digital": "ECDSA:SLOT-UNO",
            "fecha_hora_firma": "01/09/2026 12:00:00",
        },
        2: {},
    }
    for engine in (pdf_engine_v2.generate_nota_urgencias, pdf_engine_24.generate_nota_hospitalizacion):
        output = tmp_path / f"{engine.__name__}_{engine.__module__}.pdf"
        engine(patient, output_path=str(output), evoluciones_list=evolutions, firma_data_by_slot=signatures)
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(output)).pages)
        assert text.count("FIRMADO BIOMÉTRICAMENTE CON HUELLA") == 1
        assert text.count("FIRMA MÉDICA NO REGISTRADA") == 1
        assert text.count("ECDSA:SLOT-UNO") == 1
        assert text.index("Primera nota") < text.index("ECDSA:SLOT-UNO") < text.index("Segunda nota")


def test_evolution_signatures_use_authoritative_slots(monkeypatch):
    requested = []

    def read_signature(_db, _pt, code, slot):
        requested.append((code, slot))
        return {"sello_digital": f"SEAL-{slot}"}

    monkeypatch.setattr(pdf_service, "obtener_firmas_completas_documento", read_signature)
    monkeypatch.setattr(pdf_service, "aplicar_metadata_firma_vertical_nativa", lambda *_: None)
    urgent = pdf_service.build_evolution_signature_map(None, "5704", "HE-DIRMED-SINPRO-PLT-87/01", [
        {"num": 1}, {"num": 2},
    ])
    hospital = pdf_service.build_evolution_signature_map(None, "5704", "HE-DIRMED-CONSUL-PLT-24", [
        {"num": 1, "mrnum_24_hoja_evol": 9},
    ])
    assert urgent[2]["sello_digital"] == "SEAL-2"
    assert hospital[1]["sello_digital"] == "SEAL-9"
    assert requested == [
        ("HE-DIRMED-SINPRO-PLT-87/01", 1),
        ("HE-DIRMED-SINPRO-PLT-87/01", 2),
        ("HE-DIRMED-CONSUL-PLT-24", 9),
    ]


def test_latest_clinical_record_wins_over_latest_signed_slot(monkeypatch):
    monkeypatch.setattr(pdf_service, "get_latest_format_slot", lambda *_args, **_kwargs: 29)
    record, slot = pdf_service.fetch_current_format_record(
        None, "5704", "34", lambda _pt: {"mrnum": 60, "conclusiones": "Versión actual"}
    )
    assert slot == 60
    assert record["conclusiones"] == "Versión actual"

import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import area_signatures
import biometric_security
import clinical_signing
import main
import models
from database import SessionLocal
from security import create_access_token
from test_biometric_security import canonical

CODE = "HE-DIRMED-CONSUL-PLT-09"
DOCUMENT = clinical_signing.ClinicalDocument("Consentimiento de transfusión", {"N_MEDICO": "MÉDICO SINTÉTICO", "TESTIGO_1": "TESTIGO SINTÉTICO"}, "1", "MR_CI_AUT_TRANS_HEMO:701")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(area_signatures, "fetch_candidates", lambda code, before=0, limit=100: [] if before else [
        {"pt_num": "90001", "slot": 701, "paciente": "PACIENTE SINTÉTICO", "creado": "2026-09-29T10:00:00"}])
    monkeypatch.setattr(clinical_signing, "load_authoritative_document", lambda *a, **k: (DOCUMENT, {"nombre_completo": "PACIENTE SINTÉTICO"}))
    with TestClient(main.app, raise_server_exceptions=False) as value:
        yield value


def user(name, role="banco_sangre", modules=None, signing=None):
    with SessionLocal() as db:
        value = models.Usuario(username=name, nombre_completo=name, rol=role, activo=True,
            password_hash="synthetic-unused", permisos_modulos=json.dumps(modules or {}),
            formatos_permitidos=json.dumps([CODE] if role == "enfermeria" else []),
            formatos_firma_permitidos=json.dumps([CODE] if signing is None else signing),
            biometric_status="FMD_VALIDO", fmd_template=canonical())
        db.add(value)
        db.commit()
        return value.id, {"Authorization": f"Bearer {create_access_token({'sub': name, 'rol': role})}"}


def evidence(signer_id, code=CODE, slot=701):
    with SessionLocal() as db:
        signer = db.get(models.Usuario, signer_id)
        _, raw, digest = clinical_signing.build_biometric_evidence_payload(
            document=DOCUMENT, codigo_formato=code, pt_num="90001", expediente="PT-90001", evolution_slot=slot,
            patient_identity={}, firmante_id=None, usuario_firmante_id=signer.id,
            rol_firmante="BANCO_SANGRE", nombre_firmante=signer.nombre_completo,
            identificacion=signer.username, signed_at=dt.datetime.now(clinical_signing.MEXICO_CITY))
        value = models.FirmaDocumentoClinico(tipo_documento=DOCUMENT.tipo_documento, codigo_formato=code,
            pt_num="90001", expediente="PT-90001", evolution_slot=slot, rol_firmante="BANCO_SANGRE",
            usuario_firmante_id=signer.id, nombre_medico=signer.nombre_completo, document_version="1",
            signature_schema_version=clinical_signing.BIOMETRIC_EVIDENCE_VERSION,
            canonical_payload=raw.decode(), payload_hash=digest, hash_sha256=digest,
            sello_digital="EVIDENCIA_BIOMETRICA_NO_FEA:synthetic", estado="ACTIVA")
        db.add(value)
        db.commit()
        return value.id


def challenge(signer_id, slot="701", role="BANCO_SANGRE", code=CODE):
    return {"action": "FIRMA_USUARIO_ESPECIAL", "session_id": "synthetic-session",
            "expected_identity_ref": f"usuario_especial:{signer_id}|role:{role}",
            "patient_ref": "90001", "document_code": code, "document_ref": slot}


def test_shared_existing_pending_and_history_identifies_signer(client):
    first, headers1 = user("BANCO UNO")
    _, headers2 = user("BANCO DOS")
    for headers in (headers1, headers2):
        session = client.get('/api/auth/me', headers=headers).json()
        assert json.loads(session['permisos_modulos'])['firmas_area'] is True
        assert client.get('/api/firmas-area', headers=headers).json()['items'][0]['slot'] == 701
    evidence(first)
    for headers in (headers1, headers2):
        assert client.get('/api/firmas-area', headers=headers).json()['items'] == []
        history = client.get('/api/firmas-area?estado=historial', headers=headers).json()['items'][0]
        assert history['firma']['firmante'] == 'BANCO UNO'
        assert history['firma']['fecha']
        preview = client.get('/api/firmas-area/documento', headers=headers, params={'pt_num': '90001', 'codigo_formato': CODE, 'slot': 701})
        assert preview.status_code == 200, preview.text
        assert preview.json()['firma']['usuario_firmante_id'] == first
        assert 'mrnum=701' in preview.json()['pdf_url']


@pytest.mark.parametrize('code,slot', [(CODE, 701), ('09', 701), (CODE, 0)])
def test_alias_and_legacy_slot_history_cannot_create_duplicate_task(client, code, slot):
    uid, headers = user('BANCO')
    evidence(uid, code, slot)
    assert client.get('/api/firmas-area', headers=headers).json()['items'] == []
    response = client.get('/api/ehr/paciente/90001/firmas-documento', headers=headers,
                          params={'codigo_formato': CODE, 'slot': 701})
    assert response.status_code == 200, response.text
    assert response.json()['firmas_especiales_estado']['BANCO_SANGRE']['firmado'] is True


def test_changed_document_becomes_pending_preserving_previous_signer(client, monkeypatch):
    uid, headers = user('BANCO')
    evidence(uid)
    changed = clinical_signing.ClinicalDocument(DOCUMENT.tipo_documento, {'N_MEDICO': 'OTRO DATO'}, '2', DOCUMENT.source_identifier)
    monkeypatch.setattr(clinical_signing, 'load_authoritative_document', lambda *a, **k: (changed, {}))
    item = client.get('/api/firmas-area', headers=headers).json()['items'][0]
    assert item['firma'] is None
    assert item['historial'][0]['firmante'] == 'BANCO'
    assert item['historial'][0]['vigente'] is False


@pytest.mark.parametrize('path', ['/api/ehr/paciente/90001', '/api/pacientes', '/api/ehr/paciente/90001/pdf-expediente-completo', '/api/ehr/paciente/90001/pdf-consentimiento-02?mrnum=701', '/api/firmas-area/documento?pt_num=90001&codigo_formato=02&slot=701'])
def test_area_does_not_gain_general_ehr_or_other_formats(client, path):
    _, headers = user('BANCO')
    assert client.get(path, headers=headers).status_code == 403


@pytest.mark.parametrize('modules,signing,role', [({}, [], 'banco_sangre'), ({'firmas_area': False}, [CODE], 'banco_sangre'), ({'firmas_area': True}, [CODE], 'laboratorio')])
def test_explicit_revocation_and_wrong_role_deny_queue(client, modules, signing, role):
    _, headers = user('ACCOUNT', role, modules, signing)
    assert client.get('/api/firmas-area', headers=headers).status_code == 403


def test_live_revocation_rejects_queue_and_capture(client):
    uid, headers = user('BANCO')
    assert client.get('/api/firmas-area', headers=headers).status_code == 200
    with SessionLocal() as db:
        db.get(models.Usuario, uid).formatos_firma_permitidos = '[]'
        db.commit()
    assert client.get('/api/firmas-area', headers=headers).status_code == 403
    assert client.post('/api/biometrics/challenge', headers=headers, json=challenge(uid)).status_code == 403


def test_outage_is_not_reported_as_empty_queue(client, monkeypatch):
    _, headers = user('BANCO')
    def unavailable(*a, **k):
        raise clinical_signing.ClinicalDocumentUnavailable('synthetic outage')
    monkeypatch.setattr(area_signatures, 'fetch_candidates', unavailable)
    assert client.get('/api/firmas-area', headers=headers).status_code == 503


def test_paging_keeps_older_pending_records_reachable(client, monkeypatch):
    _, headers = user('BANCO')
    candidates = [{'pt_num': '90001', 'slot': slot, 'paciente': 'SINTÉTICO', 'creado': ''} for slot in range(730, 700, -1)]
    monkeypatch.setattr(area_signatures, 'fetch_candidates', lambda code, before=0, limit=100:
                        [row for row in candidates if not before or row['slot'] < before][:limit])
    first = client.get('/api/firmas-area', headers=headers).json()
    assert len(first['items']) == 25
    second = client.get('/api/firmas-area', headers=headers, params={'cursor': first['next_cursor']}).json()
    assert len(second['items']) == 5
    assert second['next_cursor'] is None
    assert {row['slot'] for row in first['items'] + second['items']} == set(range(701, 731))


def test_signature_of_another_repeated_record_does_not_hide_pending(client, monkeypatch):
    uid, headers = user('BANCO')
    evidence(uid, slot=0)
    monkeypatch.setattr(area_signatures, 'fetch_candidates', lambda code, before=0, limit=100: [] if before else [
        {'pt_num': '90001', 'slot': 702, 'paciente': 'SINTÉTICO', 'creado': ''}])
    other = clinical_signing.ClinicalDocument(DOCUMENT.tipo_documento, DOCUMENT.contenido_clinico, '1', 'MR_CI_AUT_TRANS_HEMO:702')
    monkeypatch.setattr(clinical_signing, 'load_authoritative_document', lambda *a, **k: (other, {}))
    pending = client.get('/api/firmas-area', headers=headers).json()['items'][0]
    assert pending['slot'] == 702 and pending['historial'] == [] and pending['firma'] is None


@pytest.mark.parametrize('assisted', ['medico', 'enfermeria', None])
def test_capture_uses_selected_user_not_document_slot(client, assisted):
    uid, headers = user('BANCO')
    if assisted == 'medico':
        with SessionLocal() as db:
            db.add(models.Medico(nombre_completo='MÉDICO SINTÉTICO', cedula='MED-SYNTHETIC', activo_status=True,
                                 formatos_permitidos=json.dumps([CODE])))
            db.commit()
        headers = {'Authorization': f"Bearer {create_access_token({'sub': 'MED-SYNTHETIC', 'rol': 'medico'})}"}
    elif assisted:
        _, headers = user('OPERADOR', 'enfermeria', {'ehr': True}, [])
    assert uid != 701
    response = client.post('/api/biometrics/challenge', headers=headers, json=challenge(uid))
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        saved = db.query(models.BiometricChallenge).one()
        assert saved.document_ref == '701'
        assert saved.expected_identity_ref == f'usuario_especial:{uid}|role:BANCO_SANGRE'


def test_area_cannot_capture_as_someone_else_or_sign_medically(client):
    _, headers = user('BANCO UNO')
    second, _ = user('BANCO DOS')
    assert client.post('/api/biometrics/challenge', headers=headers, json=challenge(second)).status_code == 403
    assert client.post('/api/ehr/paciente/90001/firmar-biometrico', headers=headers, json={}).status_code == 403
    wrong = challenge(second, role='LABORATORIO')
    assert client.post('/api/biometrics/challenge', headers=headers, json=wrong).status_code == 409


def test_area_lists_only_self_but_clinical_operator_can_assist_all(client):
    uid, headers = user('BANCO UNO')
    second, _ = user('BANCO DOS')
    _, operator = user('OPERADOR', 'enfermeria', {'ehr': True}, [])
    params = {'codigo_formato': CODE, 'rol_firmante': 'BANCO_SANGRE'}
    assert [row['id'] for row in client.get('/api/ehr/firmantes-especiales', params=params, headers=headers).json()] == [uid]
    assert {row['id'] for row in client.get('/api/ehr/firmantes-especiales', params=params, headers=operator).json()} == {uid, second}


@pytest.mark.parametrize('assisted', [False, True])
def test_two_simultaneous_signers_only_one_signature_commits(client, monkeypatch, assisted):
    first, headers1 = user('BANCO UNO')
    second, headers2 = user('BANCO DOS')
    with SessionLocal() as db:
        db.add(models.Paciente(nombre_completo='SINTÉTICO', codigo_barras='90001', status_ingreso='Ingresado'))
        if assisted:
            db.add(models.Medico(id=53, nombre_completo='MÉDICO SINTÉTICO', cedula='MED-SYNTHETIC', activo_status=True,
                                 formatos_permitidos=json.dumps([CODE])))
        db.commit()
    if assisted:
        headers1 = headers2 = {'Authorization': f"Bearer {create_access_token({'sub': 'MED-SYNTHETIC', 'rol': 'medico'})}"}
    monkeypatch.setattr(main, 'assert_paciente_no_de_alta', lambda *a: None)
    monkeypatch.setattr(biometric_security, 'validate_attested_capture_evidence', lambda *a: SimpleNamespace())
    monkeypatch.setattr(main, 'validate_and_consume_challenge', lambda *a, **k: True)
    monkeypatch.setattr(biometric_security, 'verify_attested_match', lambda capture, candidates, role: candidates[0]['id'])
    barrier = Barrier(2)
    def load(*a, **k):
        barrier.wait(timeout=10)
        return DOCUMENT, {}
    monkeypatch.setattr(clinical_signing, 'load_document_after_capture', load)
    def sign(args):
        uid, headers, code, slot = args
        return client.post('/api/ehr/paciente/90001/firmar-biometrico-especial', headers=headers, json={
            'fmd_template': 'synthetic-attestation', 'usuario_firmante_id': uid, 'rol_firmante': 'BANCO_SANGRE',
            'codigo_formato': code, 'tipo_documento': DOCUMENT.tipo_documento, 'evolution_slot': slot,
            'challenge_id': f'synthetic-{uid}', 'session_id': f'synthetic-session-{uid}'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(sign, [(first, headers1, CODE, 701), (second, headers2, '09', 0)]))
    assert sorted(response.status_code for response in responses) == [200, 409], [r.text for r in responses]
    with SessionLocal() as db:
        assert db.query(models.FirmaDocumentoClinico).count() == 1
        if assisted:
            audit = db.query(models.AuditoriaLog).filter_by(accion='EVIDENCIA_BIOMETRICA_AREA_ESPECIAL_NO_FEA').one()
            assert audit.usuario_id is None
            assert audit.actor_real == 'medico:53'
    if assisted:
        assert client.get('/api/auth/me', headers=headers1).json()['rol'] == 'medico'


def test_pdf_requires_exact_slot_and_is_scoped_to_permitted_format(client, monkeypatch):
    _, headers = user('BANCO')
    assert client.get('/api/ehr/paciente/90001/pdf-consentimiento-09', headers=headers).status_code == 422
    from starlette.responses import Response
    route = next(route for route in main.app.routes if getattr(route, 'path', None) == '/api/ehr/paciente/{pt_num}/pdf-consentimiento-09')
    monkeypatch.setattr(route.dependant, 'call', lambda pt_num, mrnum=None: Response(b'%PDF-synthetic', media_type='application/pdf'))
    response = client.get('/api/ehr/paciente/90001/pdf-consentimiento-09?mrnum=701&area_preview=1', headers=headers)
    assert response.status_code == 200, response.text

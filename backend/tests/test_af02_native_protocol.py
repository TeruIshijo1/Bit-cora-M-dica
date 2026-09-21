"""Cross-language AF-02: real HTTP service with a device TEST adapter, PostgreSQL backend."""
import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess

import pytest
from fastapi import HTTPException
import biometric_security as bio
import main
import models
from test_biometric_security import db, enrollment, issue, FMD_A, FMD_B, canonical

ROOT = Path(__file__).resolve().parents[2]

def node_capture(db, challenge):
    authorization = bio.issue_capture_authorization(db, challenge)
    result = subprocess.run(['node', str(ROOT / 'biometric-service/testing/capture-fixture.cjs')],
        input=json.dumps({'authorization': authorization, 'data': FMD_A}), text=True,
        capture_output=True, timeout=15, env=os.environ.copy())
    assert result.returncode == 0, 'TEST device adapter failed'
    return result.stdout

def consume(db, patient, signer, challenge, envelope):
    return main.verificar_huella_firmante_episodio(db, patient.id, envelope,
        firmante_id=signer.id, tipo_firmante='PACIENTE', challenge_id=challenge,
        session_id='session-1', action='VERIFICACION_FIRMANTE',
        expected_identity_ref=f'firmante:{signer.id}', patient_ref=str(patient.id))

def test_node_attestation_accepted_once_without_central_matcher(db, enrollment, monkeypatch):
    patient, _, signer = enrollment
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    envelope = node_capture(db, challenge)
    monkeypatch.setattr(main.requests, 'post', lambda *a, **k: pytest.fail('Central server must not contact a USB/matching service'))
    assert consume(db, patient, signer, challenge, envelope).id == signer.id
    with pytest.raises(HTTPException) as caught:
        consume(db, patient, signer, challenge, envelope)
    assert caught.value.status_code == 401
    payload = json.loads(envelope)
    assert not ({'raw', 'samples', 'image'} & payload.keys())
    db.refresh(signer)
    assert signer.fmd_template == canonical(FMD_A)

@pytest.mark.parametrize('field,value', [('attestation','0'*64), ('data',FMD_B), ('session_id','other-session'), ('challenge_id','other-challenge')])
def test_forged_node_evidence_rejected(db, enrollment, field, value):
    patient, _, signer = enrollment
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    payload = json.loads(node_capture(db, challenge)); payload[field] = value
    with pytest.raises(HTTPException) as caught:
        consume(db, patient, signer, challenge, json.dumps(payload))
    assert caught.value.status_code == 401

def test_current_template_change_invalidates_attested_match(db, enrollment):
    patient, _, signer = enrollment
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    envelope = node_capture(db, challenge)
    signer.fmd_template = canonical(FMD_B); db.commit()
    with pytest.raises(HTTPException) as caught:
        consume(db, patient, signer, challenge, envelope)
    assert caught.value.status_code == 403

def test_acquisition_id_cannot_be_consumed_with_second_challenge(db, enrollment):
    patient, _, signer = enrollment
    first = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    payload = json.loads(node_capture(db, first))
    consume(db, patient, signer, first, json.dumps(payload))
    second = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    another = json.loads(node_capture(db, second)); another['acquisition_id'] = payload['acquisition_id']
    # Trusted-component fault: even a valid signature cannot bypass DB uniqueness.
    another['attestation'] = hmac.new(bio._secret(), bio._attestation_message(another), hashlib.sha256).hexdigest()
    with pytest.raises(HTTPException) as caught:
        consume(db, patient, signer, second, json.dumps(another))
    assert caught.value.status_code == 409

@pytest.mark.parametrize('field', ['acquisition_started_at','capture_started_at'])
def test_archived_device_event_cannot_be_relabelled(db, enrollment, field):
    patient, _, signer = enrollment
    challenge = issue(db, signer_id=signer.id, patient_ref=str(patient.id))
    payload = json.loads(node_capture(db, challenge))
    payload[field] = (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(minutes=3)).isoformat()
    payload['attestation'] = hmac.new(bio._secret(), bio._attestation_message(payload), hashlib.sha256).hexdigest()
    with pytest.raises(HTTPException) as caught:
        consume(db, patient, signer, challenge, json.dumps(payload))
    assert caught.value.status_code == 401

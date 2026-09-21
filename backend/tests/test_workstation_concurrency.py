"""50 synthetic stations; in-process HTTP + real isolated PostgreSQL, no ERP."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json
import base64

from fastapi.testclient import TestClient
from sqlalchemy import select, func
import main
import models
import security


def test_fifty_stations_receive_distinct_context_bound_challenges(monkeypatch):
    monkeypatch.setenv('BIOMETRIC_ATTESTATION_SECRET', 'synthetic-stations-secret-only-for-tests-50')
    barrier = Barrier(50)

    def station(index):
        with TestClient(main.app) as client:
            barrier.wait(timeout=30)
            response = client.post('/api/biometrics/challenge', json={
                'action': 'LOGIN', 'session_id': f'synthetic-station-{index}',
            })
            assert response.status_code == 200
            result = response.json()
            encoded = result['capture_authorization'].split('.')[0]
            context = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
            assert context['session_id'] == f'synthetic-station-{index}'
            assert context['challenge_id'] == result['challenge_id']
            return result['challenge_id']

    with ThreadPoolExecutor(max_workers=50) as pool:
        ids = list(pool.map(station, range(50)))
    assert len(set(ids)) == 50
    with main.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(models.BiometricChallenge)) == 50


def test_temporary_password_can_be_changed_before_entering_clinical_routes():
    old_password = 'Synthetic-Temporary-123!'
    new_password = 'Synthetic-Replacement-456!'
    with main.SessionLocal() as db:
        db.add(models.Usuario(username='station-nurse-test', rol='enfermeria', activo=True,
                              password_hash=security.get_password_hash(old_password), must_change_password=True))
        db.commit()
    with TestClient(main.app, client=('127.0.0.77', 50001)) as client:
        login = client.post('/api/auth/login/admin', json={'username':'station-nurse-test','password':old_password})
        assert login.status_code == 200
        assert login.json()['must_change_password'] is True
        headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
        blocked = client.get('/api/camas', headers=headers)
        assert blocked.status_code == 403
        assert blocked.json()['code'] == 'PASSWORD_CHANGE_REQUIRED'
        changed = client.post('/api/auth/change-password', headers=headers, json={'current_password':old_password,'new_password':new_password})
        assert changed.status_code == 200
        assert changed.json()['success'] is True
        assert client.post('/api/auth/logout',headers=headers).status_code == 200
        assert client.post('/api/auth/login/admin',json={'username':'station-nurse-test','password':old_password}).status_code == 401
        again = client.post('/api/auth/login/admin',json={'username':'station-nurse-test','password':new_password})
        assert again.status_code == 200
        assert again.json()['must_change_password'] is False

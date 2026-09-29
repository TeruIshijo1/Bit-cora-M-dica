import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
import models
from access_control import CATALOG, effective_modules, has_module, can_use_format
from database import SessionLocal
from format_catalog import clinical_formats
from security import create_access_token, get_password_hash


@pytest.fixture
def client():
    with TestClient(main.app, raise_server_exceptions=False) as value:
        yield value


def identity(role, modules=None, formats=None, name=None):
    with SessionLocal() as db:
        user = models.Usuario(username=name or role, rol=role, activo=True,
                              password_hash=get_password_hash("Abcdef1!"),
                              permisos_modulos=json.dumps(modules) if modules is not None else None,
                              formatos_permitidos=json.dumps(formats) if formats is not None else None)
        db.add(user)
        db.commit()
        return user.id, {"Authorization": f"Bearer {create_access_token({'sub': user.username, 'rol': role})}"}


def test_rh_defaults_and_legacy_grants_are_limited_to_five_areas():
    expected = {"dashboard", "historial", "alta", "directorio", "escaneos"}
    for saved in (None, '{"rh": true, "admin": true, "ehr": true, "usuarios": true}'):
        user = SimpleNamespace(rol="rh", permisos_modulos=saved)
        assert {key for key, value in effective_modules(user).items() if value} == expected


@pytest.mark.parametrize("path", ["/api/usuarios", "/api/auditoria", "/api/backup", "/api/pacientes", "/api/camas", "/api/agenda/citas", "/api/ehr/paciente/5704", "/ehr/paciente/5704/pdf-consentimiento-09", "/api/operational/metrics"])
def test_rh_cannot_read_other_areas_or_aliases(client, path):
    _, headers = identity("rh")
    with patch.object(main.kh_database, "fetch_full_ehr_dashboard") as external:
        assert client.get(path, headers=headers).status_code == 403
        external.assert_not_called()


def test_rh_can_read_each_authorized_area(client):
    _, headers = identity("rh")
    for path in ("/api/analytics", "/api/atenciones/todas", "/api/medicos", "/api/escaneos"):
        response = client.get(path, headers=headers)
        assert response.status_code == 200, (path, response.text)
    # Reaches multipart validation; no doctor or biometric data are created.
    assert client.post("/api/medicos", headers=headers).status_code == 422


def test_rh_cannot_create_users_or_change_permissions(client):
    _, headers = identity("rh")
    for method, path in (("POST", "/api/usuarios"), ("PUT", "/api/usuarios/1"), ("PUT", "/api/medicos/1/permisos"), ("POST", "/api/catalogos/formatos")):
        assert client.request(method, path, headers=headers, json={}).status_code == 403


def test_explicit_grants_override_role_and_live_revocation_applies(client):
    user_id, headers = identity("laboratorio", {"escaneos": True})
    assert client.get("/api/escaneos", headers=headers).status_code == 200
    assert client.get("/api/analytics", headers=headers).status_code == 403
    with SessionLocal() as db:
        db.get(models.Usuario, user_id).permisos_modulos = '{}'
        db.commit()
    assert client.get("/api/escaneos", headers=headers).status_code == 403


def test_explicit_empty_admin_has_no_implicit_privileges(client):
    _, headers = identity("admin", {})
    assert client.get("/api/usuarios", headers=headers).status_code == 403
    assert client.get("/api/auth/me", headers=headers).status_code == 200


@pytest.mark.parametrize("role", ["nutricion", "laboratorio", "banco_sangre", "director", "trabajo_social", "limpieza"])
def test_all_local_roles_can_change_password_and_logout(client, role):
    _, headers = identity(role, {})
    response = client.post('/api/auth/change-password', headers=headers, json={"current_password": "Abcdef1!", "new_password": "Zbcdef2@"})
    assert response.status_code == 200, response.text
    assert client.post('/api/auth/logout', headers=headers).status_code == 200


@pytest.mark.parametrize("password", ["Abcdef1!", "NuevaClave1!"])
def test_create_user_accepts_eight_character_complex_password(client, password):
    _, headers = identity("admin")
    response = client.post('/api/usuarios', headers=headers, json={"username": "new-test", "password": password, "rol": "rh", "permisos_modulos": '{"dashboard":true}', "formatos_permitidos": '[]'})
    assert response.status_code == 200, response.text
    assert response.json()["permisos_modulos"] == '{"dashboard":true}'


@pytest.mark.parametrize("password", ["Abcd1!", "abcdefgh1!", "ABCDEFGH1!", "Abcdefgh!", "Abcdefg1", "Abcdef1 "])
def test_create_and_reset_reject_incomplete_passwords(client, password):
    user_id, headers = identity("admin")
    response = client.post('/api/usuarios', headers=headers, json={"username": "new-test", "password": password, "rol": "rh"})
    assert response.status_code == 422
    assert client.put(f'/api/usuarios/{user_id}/password', headers=headers, json={"new_password": password}).status_code == 422


def test_permission_catalog_uses_active_ehr_formats_and_new_database_entries(client):
    _, headers = identity("admin")
    with SessionLocal() as db:
        db.add(models.CatalogoFormato(codigo="TEST-FUTURE", nombre="Nuevo formato", activo=True))
        db.commit()
    result = client.get('/api/catalogos/permisos', headers=headers).json()
    assert {item["id"] for item in result["modules"]} == {item["id"] for item in CATALOG["modules"]}
    assert {item["codigo"] for item in clinical_formats()} | {"TEST-FUTURE"} <= {item["codigo"] for item in result["formats"]}
    assert len(result["formats"]) > 10


@pytest.mark.parametrize("modules,role", [('{"inventado":true}', "enfermeria"), ('{"ehr":"false"}', "enfermeria"), ('[]', "enfermeria"), ('{"usuarios":true}', "rh"), ('{}', "inventado")])
def test_invalid_or_incompatible_assignments_are_rejected(client, modules, role):
    _, headers = identity("admin")
    response = client.post('/api/usuarios', headers=headers, json={"username": "new-test", "password": "Abcdef1!", "rol": role, "permisos_modulos": modules})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("method,path,payload", [
    ("GET", "/api/ehr/paciente/5704/pdf-consentimiento-09", None),
    ("GET", "/ehr/paciente/5704/pdf-consentimiento-09", None),
    ("POST", "/api/ehr/paciente/5704/consentimiento-09", {}),
    ("GET", "/api/ehr/paciente/5704/formato-historial?codigo=09", None),
    ("POST", "/api/ehr/paciente/5704/formato-guardar-registro", {"codigo_formato": "PLT-09"}),
    ("POST", "/api/ehr/paciente/5704/firmar-biometrico-firmante", {"codigo_formato": "HE-DIRMED-CONSUL-PLT-09"}),
    ("POST", "/api/biometrics/challenge", {"action": "FIRMA_FIRMANTE", "session_id": "test", "patient_ref": "5704", "document_code": "HE-DIRMED-CONSUL-PLT-09"}),
])
def test_empty_formats_deny_reads_writes_pdfs_and_challenges(client, method, path, payload):
    _, headers = identity("enfermeria", {"ehr": True}, [])
    response = client.request(method, path, headers=headers, json=payload)
    assert response.status_code == 403, response.text


def test_format_aliases_resolve_to_same_permission():
    user = SimpleNamespace(formatos_permitidos='["HE-DIRMED-CONSUL-PLT-09"]')
    for code in ('09', 'PLT-9', 'MR_CI_AUT_TRANS_HEMO'):
        assert can_use_format(user, code)
    assert not can_use_format(user, 'HE-DIRMED-CONSUL-PLT-02')


def test_composite_dashboard_redacts_disallowed_document_bodies(client):
    _, headers = identity("enfermeria", {"ehr": True}, ['HE-DIRMED-CONSUL-PLT-09'])
    data = {"consentimiento_02": {"secret": "hidden"}, "historial_02": [{"secret": "hidden"}], "consentimiento_43": {"secret": "hidden"}, "historial_43": [{"secret": "hidden"}], "consentimiento_futuro": {"secret": "hidden"}, "consentimiento_09": {"allowed": True}, "evoluciones_list": [{"secret": "hidden"}], "timelineEvents": [{"format_code": "HE-DIRMED-CONSUL-PLT-02", "desc": "hidden"}]}
    with patch.object(main.kh_database, 'fetch_full_ehr_dashboard', return_value=data):
        response = client.get('/api/ehr/paciente/5704', headers=headers)
    assert response.status_code == 200, response.text
    assert 'hidden' not in response.text
    assert response.json()['consentimiento_09'] == {"allowed": True}


def test_missing_and_malformed_permissions_fail_closed():
    for value in ('{}', '{"ehr":false}', 'invalid', '["ehr"]', '{"ehr":"false"}'):
        assert not has_module(SimpleNamespace(rol="admin", permisos_modulos=value), "ehr")
    assert not has_module(SimpleNamespace(rol="admin", permisos_modulos='{"ehr":"lectura"}'), "ehr", write=True)


def test_edit_permissions_updates_existing_session_and_preserves_other_fields(client):
    _, admin_headers = identity("admin")
    user_id, headers = identity("laboratorio", {"escaneos": True}, [])
    response = client.put(f'/api/usuarios/{user_id}', headers=admin_headers, json={
        "permisos_modulos": '{"dashboard":true,"ehr":true}',
        "formatos_permitidos": '["HE-DIRMED-CONSUL-PLT-09"]',
    })
    assert response.status_code == 200, response.text
    assert response.json()['rol'] == 'laboratorio'
    assert client.get('/api/escaneos', headers=headers).status_code == 403
    assert client.get('/api/analytics', headers=headers).status_code == 200
    session = client.get('/api/auth/me', headers=headers).json()
    assert json.loads(session['permisos_modulos'])['ehr'] is True
    assert json.loads(session['formatos_permitidos']) == ['HE-DIRMED-CONSUL-PLT-09']
    with SessionLocal() as db:
        assert db.query(models.AuditoriaLog).filter_by(accion='USUARIO_ACTUALIZADO').count() == 1


def test_reset_accepts_eight_characters_and_requires_password_change(client):
    _, admin_headers = identity("admin")
    user_id, headers = identity("rh")
    assert client.put(f'/api/usuarios/{user_id}/password', headers=admin_headers, json={'new_password': 'Zbcdef2@'}).status_code == 200
    assert client.get('/api/auth/me', headers=headers).json()['must_change_password'] is True
    assert client.get('/api/analytics', headers=headers).status_code == 403


def test_full_pdf_cannot_bypass_individual_format_limits(client):
    _, headers = identity("enfermeria", {"ehr": True}, ['HE-DIRMED-EXPEDIENTE-COMPLETO'])
    assert client.get('/api/ehr/paciente/5704/pdf-expediente-completo', headers=headers).status_code == 403


def test_new_catalogue_entry_does_not_grant_access_implicitly(client):
    _, headers = identity("enfermeria", {"ehr": True}, [])
    with SessionLocal() as db:
        db.add(models.CatalogoFormato(codigo='TEST-FUTURE', nombre='Nuevo formato', activo=True))
        db.commit()
    response = client.get('/api/ehr/paciente/5704/formato-historial?codigo=TEST-FUTURE', headers=headers)
    assert response.status_code == 403


def test_unregistered_endpoint_is_denied_even_for_admin(client, monkeypatch):
    _, headers = identity("admin")
    monkeypatch.setattr(main.GlobalAuthMiddleware, '_matched_route_template', lambda self, request: '/api/nueva-area/sin-politica')
    assert client.get('/api/analytics', headers=headers).status_code == 403

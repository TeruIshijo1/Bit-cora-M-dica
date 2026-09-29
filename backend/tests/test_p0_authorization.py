import datetime
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import Depends
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import func, select


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

_original_cwd = Path.cwd()
os.chdir(BACKEND_DIR)
try:
    import main
    import models
    from route_policy import (
        CLINICAL_PDF_ROUTE_TEMPLATES,
        MUTATING_METHODS,
        REQUIRES_FUNCTIONAL_DECISION,
        WRITE_ROLE_POLICIES,
    )
finally:
    os.chdir(_original_cwd)


SIDE_EFFECTS = {
    "postgresql": 0,
    "sql_server": 0,
    "pdf": 0,
    "firma": 0,
}


@main.app.get("/api/_p0/probe")
@main.app.get("/ehr/_p0/probe")
def authenticated_probe():
    return {"ok": True}


@main.app.post("/ehr/_p0/clinical-write")
@main.app.post("/api/_p0/pdf-clinical-write")
def clinical_side_effect_probe():
    for name in SIDE_EFFECTS:
        SIDE_EFFECTS[name] += 1
    return {"ok": True}


@main.app.get("/api/_p0/admin", dependencies=[Depends(main.require_role(["admin"]))])
def admin_probe():
    return {"ok": True}


@main.app.get("/api/_p0/rh", dependencies=[Depends(main.require_role(["rh"]))])
def rh_probe():
    return {"ok": True}


@main.app.get("/api/_p0/sistemas", dependencies=[Depends(main.require_role(["sistemas"]))])
def sistemas_probe():
    return {"ok": True}


# main.py registra al final un catch-all de la SPA. En producción las rutas se
# declaran antes de él; estos probes de prueba deben conservar ese mismo orden.
_probe_routes = [
    route
    for route in main.app.router.routes
    if getattr(route, "path", "").startswith(("/api/_p0/", "/ehr/_p0/"))
]
main.app.router.routes[:] = _probe_routes + [
    route for route in main.app.router.routes if route not in _probe_routes
]


class P0AuthorizationRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_cwd = Path.cwd()
        os.chdir(BACKEND_DIR)
        if main.engine.dialect.name != "postgresql":
            raise RuntimeError("La suite P0 crítica sólo puede ejecutarse contra PostgreSQL.")
        cls.client = TestClient(main.app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        main.engine.dispose()
        os.chdir(cls.original_cwd)

    def setUp(self):
        # The synthetic read probes explicitly opt into authentication-only
        # access. Production routes without a module policy now fail closed.
        original_policy = main.route_modules
        probe_paths = {"/api/_p0/probe", "/ehr/_p0/probe", "/api/_p0/admin", "/api/_p0/rh", "/api/_p0/sistemas"}
        policy_patch = patch.object(main, "route_modules", side_effect=lambda method, path: () if method == "GET" and path in probe_paths else original_policy(method, path))
        policy_patch.start()
        self.addCleanup(policy_patch.stop)
        for key in SIDE_EFFECTS:
            SIDE_EFFECTS[key] = 0

        db = main.SessionLocal()
        try:
            db.query(models.Usuario).delete()
            db.add_all(
                [
                    models.Usuario(username="admin", password_hash="x", rol="admin", activo=True),
                    models.Usuario(username="rh", password_hash="x", rol="rh", activo=True),
                    models.Usuario(username="sistemas", password_hash="x", rol="sistemas", activo=True),
                    models.Usuario(username="enfermeria", password_hash="x", rol="enfermeria", activo=True),
                    models.Usuario(username="basico", password_hash="x", rol="usuario", activo=True),
                    models.Usuario(username="desactivado", password_hash="x", rol="admin", activo=False),
                    models.Usuario(username="rol_inexistente", password_hash="x", rol="fantasma", activo=True),
                ]
            )
            db.commit()
        finally:
            db.close()

    def token(self, username, role, *, expired=False):
        now = datetime.datetime.now(datetime.timezone.utc)
        expiry = now - datetime.timedelta(minutes=1) if expired else now + datetime.timedelta(minutes=10)
        return jwt.encode(
            {"sub": username, "rol": role, "exp": expiry},
            main.SECRET_KEY,
            algorithm=main.ALGORITHM,
        )

    def headers(self, username, role):
        return {"Authorization": f"Bearer {self.token(username, role)}"}

    def database_snapshot(self):
        with main.engine.connect() as connection:
            return {
                table.name: connection.execute(
                    select(func.count()).select_from(table)
                ).scalar_one()
                for table in models.Base.metadata.sorted_tables
            }

    def test_expected_roles_are_permitted(self):
        cases = [
            ("/api/_p0/admin", "admin", "admin"),
            ("/api/_p0/rh", "rh", "rh"),
            ("/api/_p0/sistemas", "sistemas", "sistemas"),
        ]
        for path, username, role in cases:
            with self.subTest(path=path):
                response = self.client.get(path, headers=self.headers(username, role))
                self.assertEqual(response.status_code, 200, response.text)

    def test_admin_endpoint_denies_enfermeria_basic_and_unknown_roles(self):
        cases = [
            ("enfermeria", "enfermeria"),
            ("basico", "usuario"),
            ("rol_inexistente", "fantasma"),
        ]
        for username, role in cases:
            with self.subTest(role=role):
                response = self.client.get("/api/_p0/admin", headers=self.headers(username, role))
                self.assertEqual(response.status_code, 403, response.text)

    def test_missing_invalid_and_expired_tokens_are_rejected(self):
        invalid = self.client.get("/api/_p0/probe", headers={"Authorization": "Bearer no-es-jwt"})
        expired = self.client.get(
            "/api/_p0/probe",
            headers={"Authorization": f"Bearer {self.token('admin', 'admin', expired=True)}"},
        )
        missing = self.client.get("/api/_p0/probe")
        self.assertEqual(missing.status_code, 401, missing.text)
        self.assertEqual(invalid.status_code, 401, invalid.text)
        self.assertEqual(expired.status_code, 401, expired.text)

    def test_login_challenge_ignores_stale_token_but_clinical_challenge_does_not(self):
        headers = {"Authorization": "Bearer token-residual-invalido"}
        with patch.object(
            main.biometric_security,
            "issue_capture_authorization",
            return_value="synthetic-test-authorization",
        ):
            login = self.client.post(
                "/api/biometrics/challenge",
                headers=headers,
                json={"action": "LOGIN", "session_id": "stale-browser-login"},
            )
            clinical = self.client.post(
                "/api/biometrics/challenge",
                headers=headers,
                json={"action": "FIRMA_MEDICA", "session_id": "stale-browser-clinical"},
            )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(clinical.status_code, 401, clinical.text)

    def test_deactivated_user_is_rejected_before_endpoint(self):
        response = self.client.get(
            "/api/_p0/admin", headers=self.headers("desactivado", "admin")
        )
        self.assertIn(response.status_code, (401, 403), response.text)

    def test_ehr_alias_has_same_authentication_as_api_route(self):
        for path in ("/api/_p0/probe", "/ehr/_p0/probe"):
            with self.subTest(path=path):
                rejected = self.client.get(path)
                allowed = self.client.get(path, headers=self.headers("admin", "admin"))
                self.assertEqual(rejected.status_code, 401, rejected.text)
                self.assertEqual(allowed.status_code, 200, allowed.text)

    def test_pdf_text_in_path_does_not_bypass_auth_or_run_side_effects(self):
        response = self.client.post("/api/_p0/pdf-clinical-write", json={})
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(SIDE_EFFECTS, {name: 0 for name in SIDE_EFFECTS})

    def test_public_allowlist_does_not_accept_prefix_variants(self):
        login_prefix = self.client.post("/api/auth/login/admin-extra", json={})
        challenge_prefix = self.client.post("/api/biometrics/challenge-extra", json={})
        public_logo = self.client.get("/static/logo.png")
        self.assertEqual(login_prefix.status_code, 401, login_prefix.text)
        self.assertEqual(challenge_prefix.status_code, 401, challenge_prefix.text)
        self.assertEqual(public_logo.status_code, 200, public_logo.text)

    def test_rejected_ehr_write_has_no_clinical_side_effects(self):
        response = self.client.post("/ehr/_p0/clinical-write", json={})
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(SIDE_EFFECTS, {name: 0 for name in SIDE_EFFECTS})

    def test_clinical_write_denies_wrong_role_before_all_side_effects(self):
        before = self.database_snapshot()
        with (
            patch.object(main.kh_database, "save_or_update_nota_hospitalizacion") as sql_server,
            patch.object(main, "generate_pdf") as pdf,
            patch.object(main.crypto_fea, "firmar_documento") as firma,
        ):
            response = self.client.post(
                "/api/ehr/paciente/5704/nota-hospitalizacion",
                json={},
                headers=self.headers("rh", "rh"),
            )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(before, self.database_snapshot())
        sql_server.assert_not_called()
        pdf.assert_not_called()
        firma.assert_not_called()

    def test_clinical_write_allows_expected_role_to_reach_validation(self):
        response = self.client.post(
            "/api/ehr/paciente/5704/nota-hospitalizacion",
            json={"evolution_num": "valor-invalido"},
            headers=self.headers("enfermeria", "enfermeria"),
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_undetermined_write_is_closed_by_default(self):
        before = self.database_snapshot()
        response = self.client.post(
            "/api/ehr/paciente/5704/formato-guardar-registro",
            json={"codigo_formato": "INDETERMINADO"},
            headers=self.headers("sistemas", "sistemas"),
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(before, self.database_snapshot())

    def test_rh_file_controller_enforces_roles(self):
        denied = self.client.get(
            "/api/escaneos/999999/archivo",
            headers=self.headers("enfermeria", "enfermeria"),
        )
        authorized_not_found = self.client.get(
            "/api/escaneos/999999/archivo",
            headers=self.headers("rh", "rh"),
        )
        self.assertEqual(denied.status_code, 403, denied.text)
        self.assertEqual(authorized_not_found.status_code, 404, authorized_not_found.text)

    def test_every_declared_write_has_policy_or_explicit_functional_block(self):
        missing = []
        public = main.GlobalAuthMiddleware.PUBLIC_ROUTE_TEMPLATES
        for route in main.app.routes:
            path = getattr(route, "path", "")
            if path.startswith(("/api/_p0/", "/ehr/_p0/")):
                continue
            for method in getattr(route, "methods", set()) & MUTATING_METHODS:
                key = (method, path)
                if key not in public and key not in WRITE_ROLE_POLICIES and key not in REQUIRES_FUNCTIONAL_DECISION:
                    missing.append(key)
        self.assertEqual(missing, [])

    def test_clinical_static_files_are_not_directly_served(self):
        paths = (
            "/static/pdfs/HES-2026-00001.pdf",
            "/static/escaneos_rh/05bc8025-ae57-4f7c-b8ec-593a15568127.pdf",
        )
        for relative_path in paths:
            with self.subTest(path=relative_path):
                unauthenticated = self.client.get(relative_path)
                authenticated = self.client.get(relative_path, headers=self.headers("admin", "admin"))
                self.assertEqual(unauthenticated.status_code, 401, unauthenticated.text)
                self.assertEqual(authenticated.status_code, 404, authenticated.text)

    def test_clinical_pdf_endpoint_requires_clinical_role(self):
        path = "/api/ehr/paciente/5704/pdf-expediente-completo"
        missing = self.client.get(path)
        basic = self.client.get(path, headers=self.headers("basico", "usuario"))
        self.assertEqual(missing.status_code, 401, missing.text)
        self.assertEqual(basic.status_code, 403, basic.text)

    def test_all_declared_clinical_pdf_templates_are_registered(self):
        registered_gets = {
            getattr(route, "path", "")
            for route in main.app.routes
            if "GET" in getattr(route, "methods", set())
        }
        self.assertEqual(CLINICAL_PDF_ROUTE_TEMPLATES - registered_gets, frozenset())


if __name__ == "__main__":
    unittest.main(verbosity=2)

import re
import time
import secrets
import logging
import requests
import mimetypes

mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy.orm import Session
from sqlalchemy import func, text as sql_text
from sqlalchemy.exc import IntegrityError

from typing import List, Optional, Union, Dict, Any

import datetime

import base64

import uuid

import json

import hashlib

import hmac

import crypto_fea

import tsa_client

import clinical_signing
import clinical_sync
import clinical_sync_adapters

from PIL import Image

import io

import os

import shutil

import csv
from contextlib import nullcontext
from html import escape as html_escape

from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, FileResponse, Response

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match
from starlette.background import BackgroundTask

from slowapi import Limiter, _rate_limit_exceeded_handler

from slowapi.util import get_remote_address

from slowapi.errors import RateLimitExceeded



from database import engine, SessionLocal, get_db, Base
from pydantic import BaseModel, field_validator
import models
import schemas
import biometric_security
from security import SESSION_IDLE_TIMEOUT_MINUTES, authenticate_token, get_current_user, normalize_role, require_role
from route_policy import (
    MUTATING_METHODS,
    PUBLIC_ROUTE_TEMPLATES,
    PUBLIC_SPA_PATHS,
    PUBLIC_SPA_DYNAMIC_PREFIXES,
    READ_ROLE_POLICIES,
    WRITE_ROLE_POLICIES,
)
from seed import get_password_hash, pwd_context
from access_control import (CATALOG, effective_modules, has_module, route_modules, role_restricted_route, authorize_formats, require_format, validate_assignments, filter_ehr_formats, can_use_format, can_sign_format)
from access_control import require_special_signature_access, is_clinical_signature_operator
from password_policy import valid_password, PASSWORD_MESSAGE
from types import SimpleNamespace
from jose import JWTError, jwt
from pdf_generator import generate_pdf
from routers import catalogos
from services import pdf_service

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.drawing.image import Image as ExcelImage
from fastapi.responses import FileResponse
import kh_database
from dotenv import load_dotenv
from app_config import load_settings, _is_public_https_url
from urllib.parse import urlsplit, parse_qs, urlencode
from pdf_qr_context import current_qr_context, document_uuid, qr_render_context
import audit_context
import file_storage
from security import create_access_token as create_signed_access_token

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

# Config & Variables de Entorno
SETTINGS = load_settings()
SECRET_KEY = SETTINGS.secret_key
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = SETTINGS.access_token_minutes

# Orígenes CORS y Hosts Permitidos en Intranet Hospitalaria
ALLOWED_ORIGINS = list(SETTINGS.allowed_origins)
ALLOWED_HOSTS = list(SETTINGS.allowed_hosts)
PRIVATE_STORAGE_ROOT = SETTINGS.private_storage_root
GENERADOS_DIR = "generados"
PLANTILLAS_DIR = "plantillas"

os.makedirs(PRIVATE_STORAGE_ROOT, exist_ok=True)

os.makedirs(GENERADOS_DIR, exist_ok=True)

os.makedirs(PLANTILLAS_DIR, exist_ok=True)

# Auto-backfill huella_token para médicos que tienen huella registrada o faltaba token
try:
    with SessionLocal() as _db_init:
        _medicos_sin_token = _db_init.query(models.Medico).filter(models.Medico.huella_token == None).all()
        for _m in _medicos_sin_token:
            _m.huella_token = str(uuid.uuid4())
        if _medicos_sin_token:
            _db_init.commit()
except Exception:
    pass

app = FastAPI(title="MediReg API - Hospital Escandón")

audit_context.configure_structured_logging()
audit_context.install_audit_enrichment(models.AuditoriaLog)



limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        if SETTINGS.production and request.headers.get("x-forwarded-proto", "").lower() != "https":
            return JSONResponse(status_code=400, content={"detail": "HTTPS es obligatorio."})

        response = await call_next(request)

        response.headers["X-Frame-Options"] = "DENY"

        response.headers["X-Content-Type-Options"] = "nosniff"

        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "connect-src 'self' blob: http://127.0.0.1:8082 http://localhost:8082; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        )
        response.headers["Cache-Control"] = "no-store"
        if SETTINGS.production and SETTINGS.proxy_https_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response



app.add_middleware(SecurityHeadersMiddleware)



class GlobalAuthMiddleware(BaseHTTPMiddleware):
    PUBLIC_ROUTE_TEMPLATES = PUBLIC_ROUTE_TEMPLATES
    PUBLIC_SPA_PATHS = PUBLIC_SPA_PATHS
    PUBLIC_SPA_DYNAMIC_PREFIXES = PUBLIC_SPA_DYNAMIC_PREFIXES

    @classmethod
    def _is_public_route(cls, request: Request) -> bool:
        method = "GET" if request.method == "HEAD" else request.method
        if method == "GET" and request.url.path in cls.PUBLIC_SPA_PATHS:
            return True
        if method == "GET":
            for prefix in cls.PUBLIC_SPA_DYNAMIC_PREFIXES:
                remainder = request.url.path[len(prefix):] if request.url.path.startswith(prefix) else ""
                if remainder and "/" not in remainder.strip("/"):
                    return True

        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match not in (Match.FULL, Match.PARTIAL):
                continue
            route_path = getattr(route, "path", None)
            if (method, route_path) in cls.PUBLIC_ROUTE_TEMPLATES:
                return True
            if match == Match.FULL:
                return False
        return False

    @staticmethod
    def _matched_route_template(request: Request) -> Optional[str]:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                path = getattr(route, "path", None)
                if path is not None:
                    return path
                # FastAPI can retain included routers instead of flattening
                # app.routes. Its OpenAPI has the effective prefixed templates.
                from starlette.routing import compile_path
                for template, operations in request.app.openapi()["paths"].items():
                    if request.method.lower() not in operations:
                        continue
                    expression, _, _ = compile_path(template)
                    if expression.fullmatch(request.url.path):
                        return template
                return None
        return None

    async def dispatch(self, request: Request, call_next):

        # 1. Permitir peticiones preflight de CORS (OPTIONS)

        if request.method == "OPTIONS":

            return await call_next(request)



        # 2. Sólo las rutas/métodos declarados explícitamente son públicos.
        if self._is_public_route(request):
            return await call_next(request)

        # 3. Toda ruta restante, incluidos aliases /ehr y archivos, exige JWT.
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        elif request.query_params.get("token"):
            token = request.query_params.get("token").strip()

        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "No autenticado"}
            )
        activity_idle_seconds = None
        try:
            parsed_idle_seconds = int(request.headers.get("X-Session-Activity", ""))
            if 0 <= parsed_idle_seconds < SESSION_IDLE_TIMEOUT_MINUTES * 60:
                activity_idle_seconds = parsed_idle_seconds
        except (TypeError, ValueError):
            pass

        try:

            with SessionLocal() as db:
                identity = authenticate_token(token, db)
                request.state.user = {
                    "sub": getattr(identity, "username", None) or getattr(identity, "cedula", None),
                    "rol": getattr(identity, "rol", None),
                    "id": getattr(identity, "id", None),
                    "permisos_modulos": getattr(identity, "permisos_modulos", None),
                    "formatos_permitidos": getattr(identity, "formatos_permitidos", None),
                    "formatos_firma_permitidos": getattr(identity, "formatos_firma_permitidos", None),
                }
                claims = getattr(identity, "_auth_claims", {}) or {}
                request.state.auth_claims = claims
                effective = f"{request.state.user['rol']}:{request.state.user['id']}"
                audit_context.set_identity(
                    real=claims.get("actor_real") or effective,
                    effective=effective,
                    reason=claims.get("impersonation_reason"),
                )
                if getattr(identity, "must_change_password", False) and request.url.path not in {
                    "/api/auth/change-password", "/api/auth/logout", "/api/auth/me"
                }:
                    return JSONResponse(status_code=403, content={"detail": "Debe cambiar la contraseña temporal antes de continuar.", "code": "PASSWORD_CHANGE_REQUIRED"})
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        route_template = self._matched_route_template(request)
        current_role = normalize_role(request.state.user.get("rol"))
        required = route_modules(request.method, route_template)
        if required is None or (required and not has_module(identity, *required, write=request.method in MUTATING_METHODS)):
            return JSONResponse(status_code=403, content={"detail": "No tiene acceso a esta área de la plataforma."})
        restricted = role_restricted_route(request.method, route_template or "")
        request.state.permission_authorized = bool(required) and not restricted
        try:
            await authorize_formats(request, identity, route_template)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        if request.method in MUTATING_METHODS:
            allowed_roles = WRITE_ROLE_POLICIES.get((request.method, route_template))
            if not allowed_roles:
                return JSONResponse(status_code=403, content={"detail": "Política de escritura no definida; requiere decisión funcional"})
            if restricted and current_role != "admin" and current_role not in allowed_roles:
                return JSONResponse(status_code=403, content={"detail": "No tienes permisos para esta acción"})

        response = await call_next(request)
        claims = getattr(request.state, "auth_claims", {}) or {}
        response.headers["X-Session-Authenticated"] = "1"
        if activity_idle_seconds is not None and not claims.get("actor_real"):
            refreshed_claims = {
                key: value for key, value in claims.items()
                if key not in {"exp", "iat", "jti", "iss", "aud", "nbf", "last_activity"}
            }
            refreshed_claims["sub"] = request.state.user["sub"]
            refreshed_claims["rol"] = request.state.user["rol"]
            refreshed_claims["last_activity"] = int(time.time()) - activity_idle_seconds
            response.headers["X-Session-Token"] = create_access_token(
                refreshed_claims,
                expires_delta=datetime.timedelta(minutes=SESSION_IDLE_TIMEOUT_MINUTES),
            )
            exposed_headers = {
                header.strip()
                for header in response.headers.get("Access-Control-Expose-Headers", "").split(",")
                if header.strip()
            }
            exposed_headers.update({"X-Request-ID", "X-Session-Token", "X-Session-Authenticated"})
            response.headers["Access-Control-Expose-Headers"] = ", ".join(sorted(exposed_headers))
        return response



app.add_middleware(GlobalAuthMiddleware)



# No se monta el árbol static completo: contiene PDFs clínicos y escaneos RH.
# Los únicos recursos públicos se exponen mediante rutas exactas.
@app.get("/static/logo.png", include_in_schema=False)
def get_public_logo():
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    if not os.path.isfile(logo_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(logo_path, media_type="image/png")


@app.get("/static/hospital-logo.png", include_in_schema=False)
def get_public_hospital_logo():
    logo_path = os.path.join(
        os.path.dirname(__file__),
        "static",
        "official_extracted_assets",
        "official_logo_600dpi.png",
    )
    if not os.path.isfile(logo_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(logo_path, media_type="image/png")

# CORS & Trusted Hosts Middleware (Seguridad Intranet)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "Idempotency-Key", "X-Request-ID", "X-Session-Activity"],
    expose_headers=[
        "X-Request-ID",
        "X-Session-Token",
        "X-Session-Authenticated",
        "X-HES-Signature-Report",
        "Content-Disposition",
    ],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS
)


_operational_metrics = {
    "http_5xx": 0,
    "db_failures": 0,
    "biometric_failures": 0,
    "tsa_pending_or_failed": 0,
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token, request_id = audit_context.start_request(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started = time.perf_counter()
        response = None
        error_type = None
        try:
            response = await call_next(request)
            if response.status_code >= 500:
                _operational_metrics["http_5xx"] += 1
            return response
        except Exception as exc:
            _operational_metrics["http_5xx"] += 1
            error_type = type(exc).__name__
            raise
        finally:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            status_code = response.status_code if response is not None else 500
            logger.info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "status": status_code,
                    "latency_ms": latency_ms,
                    "error_type": error_type,
                },
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            audit_context.request_id_var.reset(token)


app.add_middleware(RequestContextMiddleware)

# === REGISTRO MODULAR DE ROUTERS ===
app.include_router(catalogos.router)

logger = logging.getLogger("hes.main")


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "alive"}


@app.get("/readiness", include_in_schema=False)
def readiness():
    components: Dict[str, Dict[str, Any]] = {}
    pg_ready = False
    try:
        with engine.connect() as connection:
            connection.execute(sql_text("SELECT 1"))
        components["postgresql"] = {"status": "ready", "required": True}
        pg_ready = True
    except Exception as exc:
        _operational_metrics["db_failures"] += 1
        components["postgresql"] = {"status": "unavailable", "required": True, "error_type": type(exc).__name__}

    kh_server = os.getenv("KH_SERVER", "")
    sql_ready = bool(kh_server and kh_database.check_tcp_reachable(kh_server, timeout=0.5))
    components["sql_server"] = {
        "status": "ready" if sql_ready else "unavailable",
        "required": False,
        "policy": "writes_remain_pending",
    }

    components["biometric_service"] = {
        "status": "client_station_agent", "required": False,
        "policy": "signed_capture_evidence_required",
    }

    trust_store = os.getenv("TSA_TRUST_STORE", "").strip()
    tsa_configured = bool(os.getenv("TSA_URL", "").strip() and trust_store and os.path.isfile(trust_store))
    components["tsa"] = {
        "status": "configured" if tsa_configured else "unavailable",
        "required": False,
        "policy": "TSA_PENDIENTE",
    }

    disk = shutil.disk_usage(PRIVATE_STORAGE_ROOT)
    minimum_free = int(os.getenv("MIN_FREE_DISK_BYTES", str(1024 * 1024 * 1024)))
    components["disk"] = {
        "status": "ready" if disk.free >= minimum_free else "low_capacity",
        "required": True,
        "free_bytes": disk.free,
    }
    ready = pg_ready and disk.free >= minimum_free
    return JSONResponse(status_code=200 if ready else 503, content={"status": "ready" if ready else "not_ready", "components": components})


@app.get("/api/operational/metrics")
def operational_metrics(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "sistemas"])),
):
    pending = db.query(models.ClinicalSyncOperation).filter(
        models.ClinicalSyncOperation.state.in_(["PENDING", "PROCESSING", "RETRYABLE_ERROR", "REQUIRES_RECONCILIATION"])
    ).count()
    failed = db.query(models.ClinicalSyncOperation).filter(models.ClinicalSyncOperation.state == "FAILED").count()
    disk = shutil.disk_usage(PRIVATE_STORAGE_ROOT)
    return {
        **_operational_metrics,
        "clinical_sync_pending": pending,
        "clinical_sync_failed": failed,
        "private_storage_free_bytes": disk.free,
    }

@app.post("/api/biometrics/challenge", response_model=schemas.BiometricChallengeResponse)
def get_biometric_challenge(
    req: schemas.BiometricChallengeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Emite un challenge persistido y ligado al contexto antes de iniciar captura."""
    action = req.action.strip().upper()
    state_user = getattr(request.state, "user", None)
    # LOGIN is deliberately anonymous. A stale browser token must not prevent
    # the workstation from starting a fresh biometric authentication.
    if action != "LOGIN" and state_user is None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            identity = authenticate_token(auth_header.split(" ", 1)[1].strip(), db)
            state_user = {
                "rol": getattr(identity, "rol", None),
                "id": getattr(identity, "id", None),
                "permisos_modulos": getattr(identity, "permisos_modulos", None),
                "formatos_permitidos": getattr(identity, "formatos_permitidos", None),
                "formatos_firma_permitidos": getattr(identity, "formatos_firma_permitidos", None),
            }
    if action != "LOGIN" and not state_user:
        raise HTTPException(status_code=401, detail="Autenticación requerida para este challenge biométrico.")

    if action != "LOGIN":
        # request.state is populated only by trusted authentication code; it
        # is not a client payload. Reuse it without a second identity lookup.
        challenge_user = SimpleNamespace(**state_user)
        challenge_user.rol = normalize_role(state_user["rol"])
        user_enrollment = action in {"ENROLAMIENTO_USUARIO", "REENROLAMIENTO_USUARIO", "ENROLAMIENTO_BANCO_SANGRE", "REENROLAMIENTO_BANCO_SANGRE"}
        special_signature = action in {"FIRMA_USUARIO_ESPECIAL", "FIRMA_BANCO_SANGRE"}
        if user_enrollment and challenge_user.rol not in {"admin", "sistemas"}:
            raise HTTPException(403, "Sólo administración o sistemas puede registrar huellas de usuarios.")
        required = (
            ("usuarios",) if user_enrollment else
            ("directorio", "alta") if action in {"ENROLAMIENTO_MEDICO", "REENROLAMIENTO_MEDICO", "ACTUALIZACION_FEA"} else
            ("ehr", "firmas_area") if special_signature else
            ("ehr", "captura_medica", "pacientes")
        )
        if not has_module(challenge_user, *required, write=True):
            raise HTTPException(403, "No tiene acceso a esta captura biométrica.")
        if req.document_code and not special_signature:
            require_format(challenge_user, req.document_code)
        if user_enrollment:
            try:
                target_user_id = int(req.document_ref or "")
            except (TypeError, ValueError) as exc:
                raise HTTPException(422, "Seleccione una cuenta válida.") from exc
            target_user = db.query(models.Usuario).filter(
                models.Usuario.id == target_user_id,
                models.Usuario.activo == True,
            ).first()
            if not target_user:
                raise HTTPException(404, "No se encontró una cuenta activa.")
            expected_target = f"usuario:{target_user_id}"
            # Older Banco de Sangre clients remain valid during migration.
            if action in {"ENROLAMIENTO_BANCO_SANGRE", "REENROLAMIENTO_BANCO_SANGRE"}:
                expected_target = f"banco_sangre:{target_user_id}"
            if req.expected_identity_ref != expected_target:
                raise HTTPException(422, "La identidad biométrica no coincide con la cuenta seleccionada.")
            initial_action = action in {"ENROLAMIENTO_USUARIO", "ENROLAMIENTO_BANCO_SANGRE"}
            if initial_action and target_user.biometric_status != "SIN_BIOMETRIA":
                raise HTTPException(409, "Esta cuenta ya tiene biometría. Use el reenrolamiento explícito.")
            if not initial_action and target_user.biometric_status == "SIN_BIOMETRIA":
                raise HTTPException(409, "Esta cuenta no tiene una huella que reenrolar.")
        if special_signature:
            if not req.patient_ref or not req.document_code:
                raise HTTPException(422, "Paciente y formato son obligatorios para la firma especial.")
            try:
                # document_ref identifies the clinical record, never the user.
                identity_subject = str(req.expected_identity_ref or "").split("|role:", 1)[0]
                prefix = "banco_sangre:" if action == "FIRMA_BANCO_SANGRE" else "usuario_especial:"
                if not identity_subject.startswith(prefix):
                    raise ValueError("invalid identity")
                target_user_id = int(identity_subject[len(prefix):])
            except (TypeError, ValueError) as exc:
                raise HTTPException(422, "Seleccione una cuenta válida.") from exc
            requirements = clinical_signing.special_signature_requirements(req.document_code)
            target_user = db.query(models.Usuario).filter(
                models.Usuario.id == target_user_id,
                models.Usuario.activo == True,
                models.Usuario.biometric_status == "FMD_VALIDO",
            ).first()
            role_marker = "|role:"
            requested_role = str(req.expected_identity_ref or "").split(role_marker, 1)[1].upper() if role_marker in str(req.expected_identity_ref or "") else (
                "BANCO_SANGRE" if action == "FIRMA_BANCO_SANGRE" else None
            )
            expected_target = (
                f"banco_sangre:{target_user_id}" if action == "FIRMA_BANCO_SANGRE"
                else f"usuario_especial:{target_user_id}{role_marker}{requested_role}"
            ) if requested_role else None
            if not requested_role or requested_role not in requirements:
                raise HTTPException(409, "El formato no solicita el área de firma seleccionada.")
            if req.expected_identity_ref != expected_target:
                raise HTTPException(422, "La identidad y área de firma no coinciden con la cuenta seleccionada.")
            require_special_signature_access(challenge_user, req.document_code, requested_role, target_user_id, write=True)
            if not target_user or not can_sign_format(target_user, req.document_code, requested_role) or not biometric_security.detect_template_state(target_user.fmd_template).canonical:
                raise HTTPException(409, "La cuenta seleccionada no tiene una huella vigente y autorización para este formato.")
    subject_ref = None
    expected_identity_ref = req.expected_identity_ref
    if state_user:
        subject_ref = f"{normalize_role(state_user.get('rol'))}:{state_user.get('id')}"
        if normalize_role(state_user.get("rol")) in {"medico", "ayudante"} and action not in {
            "FIRMA_FIRMANTE", "VERIFICACION_FIRMANTE", "ENROLAMIENTO_FIRMANTE", "REENROLAMIENTO_FIRMANTE", "FIRMA_BANCO_SANGRE", "FIRMA_USUARIO_ESPECIAL"
        }:
            expected_identity_ref = f"medico:{state_user.get('id')}"
    elif req.expected_medico_id is not None:
        subject_ref = f"medico:{req.expected_medico_id}"
        expected_identity_ref = f"medico:{req.expected_medico_id}"
    capture_document_digest = None
    if action in {"FIRMA_MEDICA", "FIRMA_FIRMANTE", "FIRMA_BANCO_SANGRE", "FIRMA_USUARIO_ESPECIAL"}:
        if not req.patient_ref or not req.document_code:
            raise HTTPException(status_code=422, detail="Paciente y documento son obligatorios para firmar")
        try:
            capture_document, _ = clinical_signing.load_authoritative_document(
                db, pt_num=req.patient_ref, codigo_formato=req.document_code,
                evolution_slot=int(req.document_ref or 0),
            )
            capture_document_digest = clinical_signing.document_digest(capture_document)
        except (ValueError, clinical_signing.ClinicalDocumentUnavailable) as exc:
            raise HTTPException(status_code=409, detail="No se pudo preparar el documento exacto para la captura") from exc
    challenge_id, expires_at = biometric_security.create_challenge(
        db,
        action=action,
        session_id=req.session_id,
        subject_ref=subject_ref,
        expected_identity_ref=expected_identity_ref,
        patient_ref=req.patient_ref,
        document_code=req.document_code,
        document_ref=req.document_ref,
    )
    return {
        "challenge_id": challenge_id,
        "capture_authorization": biometric_security.issue_capture_authorization(db, challenge_id, document_digest=capture_document_digest),
        "expires_in": biometric_security.CHALLENGE_TTL_SECONDS,
        "expires_at": expires_at,
    }


def validate_and_consume_challenge(
    db: Session,
    *,
    challenge_id: str,
    session_id: str,
    action: str,
    subject_ref: Optional[str] = None,
    expected_identity_ref: Optional[str] = None,
    patient_ref: Optional[str] = None,
    document_code: Optional[str] = None,
    document_ref: Optional[str] = None,
    acquisition: Optional[biometric_security.AttestedCapture] = None,
) -> bool:
    if action in {"FIRMA_MEDICA", "FIRMA_FIRMANTE", "FIRMA_BANCO_SANGRE", "FIRMA_USUARIO_ESPECIAL"}:
        expected_digest = (acquisition.context or {}).get("document_digest") if acquisition else None
        if not expected_digest:
            raise HTTPException(status_code=409, detail="La captura no está vinculada al contenido del documento. Inicie una nueva captura.")
        try:
            document, _ = clinical_signing.load_authoritative_document(
                db, pt_num=patient_ref, codigo_formato=document_code,
                evolution_slot=int(document_ref or 0),
            )
        except (ValueError, clinical_signing.ClinicalDocumentUnavailable) as exc:
            raise HTTPException(status_code=409, detail="No se pudo confirmar el documento antes de firmar") from exc
        if clinical_signing.document_digest(document) != expected_digest:
            raise HTTPException(status_code=409, detail="El documento cambió durante la captura. Revíselo y vuelva a firmar.")
        # Reuse these exact bytes downstream; no second load after successful match.
        db.info["biometric_document"] = (document, clinical_signing._patient_identity(db, patient_ref))
    biometric_security.consume_challenge(
        db,
        challenge_id=challenge_id,
        session_id=session_id,
        action=action,
        subject_ref=subject_ref,
        expected_identity_ref=expected_identity_ref,
        patient_ref=patient_ref,
        document_code=document_code,
        document_ref=document_ref,
        acquisition_id=acquisition.acquisition_id if acquisition else None,
        acquisition_started_at=acquisition.acquisition_started_at if acquisition else None,
        captured_at=acquisition.captured_at if acquisition else None,
        acquisition_context=acquisition.context if acquisition else None,
    )
    return True


def _biometric_subject_from_request(request: Request) -> Optional[str]:
    user = getattr(request.state, "user", None)
    if not user:
        return None
    return f"{normalize_role(user.get('rol'))}:{user.get('id')}"


def _biometric_identity_from_request(request: Request) -> Optional[str]:
    user = getattr(request.state, "user", None)
    if not user or normalize_role(user.get("rol")) not in {"medico", "ayudante"}:
        return None
    return f"medico:{user.get('id')}"


def _assert_fea_enabled(medico: models.Medico) -> None:
    if bool(getattr(medico, "requiere_actualizacion_fea", False)):
        raise HTTPException(
            status_code=423,
            detail="Firma criptográfica bloqueada: el reenrolamiento biométrico requiere actualización FEA en el Bloque B.",
        )

def verificar_huella_medico(
    db: Session,
    fmd_template: str,
    medico_id: Optional[int] = None,
    challenge_id: Optional[str] = None,
    session_id: Optional[str] = None,
    action: str = "LOGIN",
    subject_ref: Optional[str] = None,
    expected_identity_ref: Optional[str] = None,
    patient_ref: Optional[str] = None,
    document_code: Optional[str] = None,
    document_ref: Optional[str] = None,
) -> models.Medico:
    """
    Verifica evidencia de captura y matching del agente de la estación cliente.
    - Si se especifica medico_id: realiza matching 1:1 ultrarrápido y seguro.
    - Si no se especifica medico_id: realiza matching 1:N (para login biométrico).
    - Valida y consume el challenge obligatorio y la adquisición atestada.
    """
    db.info.pop("biometric_document", None)
    if not fmd_template:
        raise HTTPException(status_code=400, detail="No se recibió la huella biométrica (FMD).")
    
    if expected_identity_ref and expected_identity_ref.startswith("medico:"):
        try:
            bound_medico_id = int(expected_identity_ref.split(":", 1)[1])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=401, detail="Identidad biométrica esperada inválida.") from exc
        if medico_id is not None and medico_id != bound_medico_id:
            raise HTTPException(status_code=403, detail="El médico solicitado no coincide con la sesión autenticada.")
        medico_id = bound_medico_id
    capture = biometric_security.validate_attested_capture_evidence(
        fmd_template, challenge_id, session_id
    )
    validate_and_consume_challenge(
        db,
        challenge_id=challenge_id,
        session_id=session_id,
        action=action,
        subject_ref=subject_ref,
        expected_identity_ref=expected_identity_ref,
        patient_ref=patient_ref,
        document_code=document_code,
        document_ref=document_ref,
        acquisition=capture,
    )

    if medico_id is not None:
        medico = db.query(models.Medico).filter(
            models.Medico.id == medico_id,
            models.Medico.activo_status == True
        ).first()
        if not medico or not medico.fmd_template:
            raise HTTPException(status_code=400, detail="El médico seleccionado no cuenta con huella biométrica registrada en el sistema.")
        if medico.biometric_status != "FMD_VALIDO":
            raise HTTPException(status_code=409, detail="La biometría del médico es legacy y requiere reenrolamiento controlado.")
        medicos_data = [{"id": medico.id, "fmd_template": medico.fmd_template}]
    else:
        medicos = db.query(models.Medico).filter(
            models.Medico.activo_status == True,
            models.Medico.fmd_template.isnot(None),
            models.Medico.biometric_status == "FMD_VALIDO",
        ).all()
        if not medicos:
            raise HTTPException(status_code=400, detail="No hay médicos registrados con huella biométrica en el sistema.")
        medicos_data = [{"id": m.id, "fmd_template": m.fmd_template} for m in medicos]

    match_id = biometric_security.verify_attested_match(capture, medicos_data, "medico")
    if medico_id is not None:
        return medico
    return next(m for m in medicos if m.id == match_id)



def verificar_huella_firmante_episodio(
    db: Session,
    paciente_id: int,
    fmd_template: str,
    firmante_id: Optional[int] = None,
    tipo_firmante: Optional[str] = None,
    document_role: Optional[str] = None,
    challenge_id: Optional[str] = None,
    session_id: Optional[str] = None,
    action: str = "VERIFICACION_FIRMANTE",
    subject_ref: Optional[str] = None,
    expected_identity_ref: Optional[str] = None,
    patient_ref: Optional[str] = None,
    document_code: Optional[str] = None,
    document_ref: Optional[str] = None,
) -> models.BiometriaFirmanteEpisodio:
    """
    Verifica la huella dactilar de un paciente, familiar o testigo contra los firmantes biométricos
    activos registrados temporalmente para el episodio hospitalario de ese paciente.
    """
    db.info.pop("biometric_document", None)
    if not fmd_template:
        raise HTTPException(status_code=400, detail="No se recibió la huella biométrica (FMD).")
    
    if firmante_id is None:
        raise HTTPException(status_code=422, detail="firmante_id es obligatorio.")
    resolved_identity_ref = expected_identity_ref or f"firmante:{firmante_id}"
    if action == "FIRMA_FIRMANTE" and document_role:
        # The challenge binds both the selected record and its document role
        # (e.g. patient vs. witness). Consume exactly that same identity.
        resolved_identity_ref = biometric_security.role_bound_signer_identity(
            firmante_id, document_role
        )
    capture = biometric_security.validate_attested_capture_evidence(
        fmd_template, challenge_id, session_id
    )
    validate_and_consume_challenge(
        db,
        challenge_id=challenge_id,
        session_id=session_id,
        action=action,
        subject_ref=subject_ref,
        expected_identity_ref=resolved_identity_ref,
        patient_ref=patient_ref or str(paciente_id),
        document_code=document_code,
        document_ref=document_ref,
        acquisition=capture,
    )

    paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    if paciente.status_ingreso == "Alta":
        raise HTTPException(status_code=400, detail="El paciente ya fue dado de alta. El material biométrico del episodio ha sido inactivado conforme a la LFPDPPP.")

    target_firmante = db.query(models.BiometriaFirmanteEpisodio).filter(
        models.BiometriaFirmanteEpisodio.id == firmante_id,
        models.BiometriaFirmanteEpisodio.paciente_id == paciente.id,
        models.BiometriaFirmanteEpisodio.estado == "ACTIVO",
    ).first()
    if not target_firmante:
        raise HTTPException(status_code=404, detail="Firmante activo no encontrado para este paciente.")
    persisted_role = (target_firmante.tipo_firmante or "").strip().upper()
    if tipo_firmante and action != "FIRMA_FIRMANTE" and persisted_role != tipo_firmante.strip().upper():
        raise HTTPException(status_code=409, detail="El rol enviado no coincide con el rol persistido del firmante.")
    if action == "FIRMA_FIRMANTE" and document_role:
        document_role = document_role.strip().upper()
        allowed_roles = {
            "PACIENTE": {"PACIENTE"},
            "REPRESENTANTE_LEGAL": {"REPRESENTANTE_LEGAL", "TESTIGO_1", "TESTIGO_2"},
            "TUTOR": {"TUTOR", "TESTIGO_1", "TESTIGO_2"},
            "FAMILIAR": {"FAMILIAR", "TESTIGO_1", "TESTIGO_2"},
            "TESTIGO": {"TESTIGO_1", "TESTIGO_2"},
            "TESTIGO_1": {"TESTIGO_1", "TESTIGO_2"},
            "TESTIGO_2": {"TESTIGO_1", "TESTIGO_2"},
        }
        if document_role not in allowed_roles.get(persisted_role, set()):
            raise HTTPException(status_code=409, detail="Esta persona no puede ocupar el lugar seleccionado en este documento.")
    if target_firmante.biometric_status != "FMD_VALIDO" or not target_firmante.fmd_template:
        raise HTTPException(status_code=409, detail="La biometría del firmante requiere enrolamiento o reenrolamiento controlado.")

    biometric_security.verify_attested_match(
        capture, [{"id": target_firmante.id, "fmd_template": target_firmante.fmd_template}], "firmante"
    )
    return target_firmante



def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    if expires_delta is None:
        expires_delta = datetime.timedelta(
            minutes=max(ACCESS_TOKEN_EXPIRE_MINUTES, SESSION_IDLE_TIMEOUT_MINUTES)
        )
    return create_signed_access_token(data, expires_delta=expires_delta)



def log_auditoria(db: Session, usuario_id: Optional[int], accion: str, detalles_json: Optional[str] = None):
    """Add audit evidence to the caller transaction; never commit implicitly."""
    log = models.AuditoriaLog(
        usuario_id=usuario_id,
        accion=accion,
        detalles_json=detalles_json,
        ip_origen=None,
    )
    db.add(log)
    db.flush()


def _clinical_sync_intent(
    db: Session,
    request: Request,
    *,
    operation_type: str,
    aggregate_type: str,
    aggregate_id: str,
    patient_ref: Optional[str],
    payload: Dict[str, Any],
):
    key = clinical_sync.make_idempotency_key(
        operation_type,
        str(aggregate_id),
        payload,
        request.headers.get("Idempotency-Key"),
    )
    try:
        return clinical_sync.create_or_get_intent(
            db,
            idempotency_key=key,
            operation_type=operation_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            patient_ref=patient_ref,
            payload=payload,
        )
    except clinical_sync.IdempotencyKeyConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": exc.error_code,
                "message": "La Idempotency-Key ya corresponde a otra solicitud.",
            },
        ) from exc


def _existing_sync_response(operation: models.ClinicalSyncOperation):
    body = {
        "success": operation.state == clinical_sync.SYNCED,
        "operation_id": str(operation.operation_id),
        "state": operation.state,
        "idempotent": True,
        "local_applied": bool(operation.local_applied_at),
    }
    if operation.state == clinical_sync.SYNCED:
        body["message"] = "La operación ya estaba sincronizada."
        return JSONResponse(status_code=200, content=body)
    if operation.state in clinical_sync.RECOVERABLE_STATES or operation.state == clinical_sync.PROCESSING:
        body["message"] = "La operación existe y permanece pendiente de sincronización."
        return JSONResponse(status_code=202, content=body)
    body["message"] = "La operación falló y conserva evidencia auditable."
    return JSONResponse(status_code=502, content=body)


def _sync_result_response(
    result: clinical_sync.ExecutionResult,
    success_body: Dict[str, Any],
    *,
    local_applied: bool = True,
):
    local_state = {"local_applied": local_applied}
    if result.state == clinical_sync.SYNCED:
        return {
            **success_body,
            **local_state,
            "success": True,
            "operation_id": str(result.operation_id),
            "state": result.state,
        }
    if result.state in clinical_sync.RECOVERABLE_STATES or result.state == clinical_sync.PROCESSING:
        return JSONResponse(
            status_code=202,
            content={
                "success": False,
                **local_state,
                "operation_id": str(result.operation_id),
                "state": result.state,
                "message": "Cambio local guardado; sincronización con Vertical pendiente.",
            },
        )
    return JSONResponse(
        status_code=502,
        content={
            "success": False,
            **local_state,
            "operation_id": str(result.operation_id),
            "state": result.state,
            "message": "La operación externa falló y quedó registrada para auditoría.",
        },
    )


def _durable_kh_mutation(
    db: Session,
    request: Request,
    *,
    adapter: str,
    adapter_args: List[Any],
    adapter_kwargs: Optional[Dict[str, Any]],
    aggregate_type: str,
    aggregate_id: str,
    patient_ref: str,
    local_apply,
    success_body: Dict[str, Any],
):
    """Apply the shared PostgreSQL-first protocol for one KH_HE mutation."""
    persisted_payload = {
        "adapter": adapter,
        "args": adapter_args,
        "kwargs": adapter_kwargs or {},
        "retry_policy": (
            "manual" if adapter == "save_or_update_nota_urgencias" else "automatic"
        ),
    }
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="KH_MUTATION",
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        patient_ref=str(patient_ref),
        payload=persisted_payload,
    )
    if not created:
        return _existing_sync_response(operation)

    try:
        local_apply(operation)
        clinical_sync.mark_local_applied(db, operation)
    except Exception:
        db.rollback()
        raise
    result = clinical_sync.execute_external(
        db,
        operation,
        clinical_sync_adapters.dispatcher(operation),
        session_factory=SessionLocal,
    )
    external = result.value if isinstance(result.value, dict) else {}
    return _sync_result_response(result, {**external, **success_body})


def _durable_document_write(
    db: Session,
    request: Request,
    *,
    pt_num: str,
    adapter: str,
    data: Dict[str, Any],
    codigo_formato: str,
    tipo_documento: str,
    slot: int = 0,
    accion: str = "GUARDADO",
    motivo: str = "Captura institucional de documento clínico",
    medico: str = "",
    cedula: str = "",
    success_body: Optional[Dict[str, Any]] = None,
):
    """Persist evidence/revocations once, then deliver a consent or clinical note."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    def local_apply(operation):
        db.add(
            models.HistoricoNotaClinica(
                codigo_formato=codigo_formato,
                tipo_documento=tipo_documento,
                pt_num=str(pt_num),
                expediente=f"PT-{pt_num}",
                evolution_slot=int(slot or 0),
                nombre_medico=str(medico or ""),
                cedula_profesional=str(cedula or ""),
                contenido_soap_json=json.dumps(data, default=str, ensure_ascii=False),
                accion=accion,
                motivo=motivo,
                fecha_registro=datetime.datetime.now(),
                ip_origen=client_ip,
                clinical_sync_operation_id=operation.operation_id,
            )
        )
        active_signatures = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == codigo_formato,
            models.FirmaDocumentoClinico.estado == "ACTIVA",
        )
        if slot:
            active_signatures = active_signatures.filter(
                models.FirmaDocumentoClinico.evolution_slot == int(slot)
            )
        revoked = active_signatures.all()
        for signature in revoked:
            signature.estado = "REVOCADA_POR_MODIFICACION"
            signature.motivo_revocacion = "El documento fue modificado posteriormente."
            signature.fecha_revocacion = datetime.datetime.now()
        db.add(
            models.AuditoriaLog(
                usuario_id=None,
                accion="DOCUMENTO_CLINICO_PENDIENTE_SINCRONIZACION",
                detalles_json=json.dumps(
                    {
                        "operation_id": str(operation.operation_id),
                        "pt_num": str(pt_num),
                        "codigo_formato": codigo_formato,
                        "slot": int(slot or 0),
                        "firmas_revocadas_ids": [signature.id for signature in revoked],
                    }
                ),
                ip_origen=client_ip,
            )
        )

    aggregate_id = f"{pt_num}:{codigo_formato}:{int(slot or 0)}"
    return _durable_kh_mutation(
        db,
        request,
        adapter=adapter,
        adapter_args=[str(pt_num), data],
        adapter_kwargs={},
        aggregate_type="clinical_document",
        aggregate_id=aggregate_id,
        patient_ref=str(pt_num),
        local_apply=local_apply,
        success_body=success_body or {"message": f"{tipo_documento} guardado con éxito"},
    )


def _durable_audited_kh_write(
    db: Session,
    request: Request,
    *,
    pt_num: str,
    adapter: str,
    args: List[Any],
    kwargs: Optional[Dict[str, Any]],
    aggregate_id: str,
    audit_action: str,
    audit_details: Dict[str, Any],
    success_body: Optional[Dict[str, Any]] = None,
):
    client_ip = request.client.host if request.client else "127.0.0.1"

    def local_apply(operation):
        db.add(
            models.AuditoriaLog(
                usuario_id=None,
                accion=audit_action,
                detalles_json=json.dumps(
                    {**audit_details, "operation_id": str(operation.operation_id)},
                    default=str,
                    ensure_ascii=False,
                ),
                ip_origen=client_ip,
            )
        )

    return _durable_kh_mutation(
        db,
        request,
        adapter=adapter,
        adapter_args=args,
        adapter_kwargs=kwargs,
        aggregate_type="clinical_event",
        aggregate_id=aggregate_id,
        patient_ref=str(pt_num),
        local_apply=local_apply,
        success_body=success_body or {"message": "Cambio clínico guardado y sincronizado"},
    )


_CONSENT_DURABLE_METADATA = {
    "save_or_update_consentimiento_eed": ("HE-DIRMED-CONSUL-PLT-EED", "Consentimiento Informado EED"),
    "save_or_update_consentimiento_25": ("HE-DIRMED-CONSUL-PLT-25", "Consentimiento Informado 25"),
    "save_or_update_consentimiento_34_01": ("HE-DIRMED-CONSUL-PLT-34", "Consentimiento Informado 34/01"),
    "save_or_update_consentimiento_12": ("HE-DIRMED-CONSUL-PLT-12", "Consentimiento Informado 12"),
    "save_or_update_consentimiento_04": ("HE-DIRMED-CONSUL-PLT-04", "Consentimiento Informado 04"),
    "save_or_update_consentimiento_15": ("HE-DIRMED-CONSUL-PLT-15", "Consentimiento Informado 15"),
    "save_or_update_consentimiento_02": ("HE-DIRMED-CONSUL-PLT-02", "Consentimiento Informado 02"),
    "save_or_update_consentimiento_07": ("HE-DIRMED-CONSUL-PLT-07", "Consentimiento Informado 07"),
    "save_or_update_consentimiento_08": ("HE-DIRMED-CONSUL-PLT-08", "Consentimiento Informado 08"),
    "save_or_update_consentimiento_43": ("HE-DIRMED-SINPRO-PLT-43", "Orden de Intubación 43"),
    "save_or_update_consentimiento_11": ("HE-DIRMED-CONSUL-PLT-11", "Consentimiento de No Reanimación 11"),
    "save_or_update_consentimiento_19": ("HE-DIRMED-CONSUL-PLT-19", "Consentimiento Informado 19"),
    "save_or_update_egreso_voluntario_15": ("HE-DIRMED-SINPRO-PLT-15", "Egreso Voluntario 15-EV"),
    "save_or_update_consentimiento_06": ("HE-DIRMED-CONSUL-PLT-06", "Consentimiento Informado 06"),
    "save_or_update_consentimiento_09": ("HE-DIRMED-CONSUL-PLT-09", "Consentimiento Informado 09"),
    "save_or_update_egreso_resumen_16": ("HE-DIRMED-SINPRO-PLT-16", "Egreso y Resumen Clínico 16"),
}


def _durable_consent_write(
    db: Session,
    request: Request,
    *,
    pt_num: str,
    adapter: str,
    data: Dict[str, Any],
):
    codigo, title = _CONSENT_DURABLE_METADATA[adapter]
    slot = int(data.get("mrnum") or data.get("slot") or 0)
    return _durable_document_write(
        db,
        request,
        pt_num=pt_num,
        adapter=adapter,
        data=data,
        codigo_formato=codigo,
        tipo_documento=title,
        slot=slot,
        accion="EDICION" if slot else "CREACION",
        motivo="Captura institucional de consentimiento informado",
        medico=str(data.get("medico_tratante") or data.get("n_medico") or data.get("medico") or data.get("dr_elaboro") or data.get("dr_tratante") or ""),
        cedula=str(data.get("cedula") or data.get("cedula_profesional") or data.get("cedula_elaboro") or data.get("cedula_tratante") or ""),
        success_body={"message": f"{title} guardado con éxito", "status": "success"},
    )


def _durable_universal_format_write(
    db: Session,
    request: Request,
    *,
    pt_num: str,
    document: Dict[str, Any],
    create: bool,
):
    document = dict(document)
    operation_type = "UNIVERSAL_FORMAT_CREATE" if create else "UNIVERSAL_FORMAT_UPDATE"
    record_id = int(document.get("mrnum") or 0)
    codigo = str(document.get("codigo") or "")
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type=operation_type,
        aggregate_type="universal_clinical_document",
        aggregate_id=f"{pt_num}:{codigo}:{record_id}",
        patient_ref=str(pt_num),
        payload={
            "document": document,
            # The adapter blocks CREATE before INSERT when no safe GUID exists.
            # REQUIRES_RECONCILIATION is excluded from unattended delivery.
            "retry_policy": "automatic",
        },
    )
    if not created:
        return _existing_sync_response(operation)
    client_ip = request.client.host if request.client else "127.0.0.1"
    db.add(
        models.HistoricoNotaClinica(
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            codigo_formato=codigo,
            tipo_documento="Formato clínico universal",
            evolution_slot=record_id,
            nombre_medico=str(document.get("medico_tratante") or document.get("n_medico") or ""),
            cedula_profesional=str(document.get("cedula") or ""),
            fecha_registro=datetime.datetime.now(),
            ip_origen=client_ip,
            accion="CREACION" if create else "EDICION",
            motivo="CREACION_REGISTRO_FORMATO_UNIVERSAL" if create else "EDICION_REGISTRO_FORMATO_UNIVERSAL",
            contenido_soap_json=json.dumps(document, ensure_ascii=False, default=str),
            clinical_sync_operation_id=operation.operation_id,
        )
    )
    clinical_sync.mark_local_applied(db, operation)
    result = clinical_sync.execute_external(
        db,
        operation,
        clinical_sync_adapters.dispatcher(operation),
        session_factory=SessionLocal,
    )
    return _sync_result_response(
        result,
        {"status": "success", "message": "Formato clínico sincronizado"},
    )


def _resolve_vertical_sign_target(pt_num: str, codigo_formato: str, target_slot: int, document=None):
    from vertical_signer import resolve_vertical_controller_and_pk

    controller_name, pk_column = resolve_vertical_controller_and_pk(codigo_formato)
    if document is not None:
        parts = document.source_identifier.split(":")
        if len(parts) >= 2 and parts[0] == controller_name and parts[1].isdigit():
            return controller_name, int(parts[1])
        raise HTTPException(status_code=409, detail="El snapshot no identifica el registro Vertical exacto")
    if controller_name == "MR_NE_URG":
        dashboard = kh_database.fetch_full_ehr_dashboard(pt_num)
        evolution = (dashboard.get("evoluciones") or {}).get(f"evolucion{target_slot or 1}")
        if not evolution or not evolution.get("mrnum_ne_urg"):
            raise HTTPException(status_code=409, detail="La evolución seleccionada no tiene un registro Vertical exacto")
        return controller_name, int(evolution["mrnum_ne_urg"])
    if controller_name != "MR_NE_URG" and target_slot and target_slot > 0:
        return controller_name, target_slot
    conn = kh_database.get_kh_connection()
    if not conn:
        return controller_name, None
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT TOP 1 {pk_column} FROM {controller_name} WHERE PTNum = ? ORDER BY {pk_column} DESC",
            (pt_num,),
        )
        row = cursor.fetchone()
        return controller_name, int(row[0]) if row and row[0] else None
    finally:
        conn.close()


@app.get("/api/clinical-sync/operations/{operation_id}")
def get_clinical_sync_operation(
    operation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    operation = db.query(models.ClinicalSyncOperation).filter(
        models.ClinicalSyncOperation.operation_id == operation_id
    ).first()
    if not operation:
        raise HTTPException(status_code=404, detail="Operación no encontrada")
    return {
        "operation_id": str(operation.operation_id),
        "operation_type": operation.operation_type,
        "aggregate_type": operation.aggregate_type,
        "aggregate_id": operation.aggregate_id,
        "patient_ref": operation.patient_ref,
        "state": operation.state,
        "attempts": operation.attempts,
        "created_at": operation.created_at,
        "updated_at": operation.updated_at,
        "completed_at": operation.completed_at,
    }


@app.post("/api/clinical-sync/reconcile")
def reconcile_clinical_sync_operations(
    limit: int = Query(50, ge=1, le=200),
    operation_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "sistemas"])),
):
    selected_ids = None
    if operation_id is not None:
        operation = db.get(models.ClinicalSyncOperation, operation_id)
        if operation is None:
            raise HTTPException(status_code=404, detail="Operación no encontrada")
        native_outcome_requires_readback = bool(operation.external_applied_at) or any(
            attempt.error_class in {
                "VerticalSignatureConfirmationPending",
                "VerticalSignatureAcknowledgedPending",
                "VerticalSignatureOutcomeUnknown",
            }
            for attempt in operation.attempts_log
        )
        if (
            operation.operation_type != "VERTICAL_SIGN"
            or operation.state != clinical_sync.REQUIRES_RECONCILIATION
            or not native_outcome_requires_readback
        ):
            raise HTTPException(
                status_code=409,
                detail="Esta operación no admite confirmación nativa por lectura.",
            )
        selected_ids = [operation_id]
    results = clinical_sync.reconcile(
        db,
        clinical_sync_adapters.dispatcher,
        operation_ids=selected_ids,
        limit=limit,
        session_factory=SessionLocal,
    )
    return {
        "processed": len(results),
        "operations": [
            {"operation_id": str(item.operation_id), "state": item.state}
            for item in results
        ],
    }



import requests



@app.post("/api/auth/login/admin", response_model=schemas.Token)

@limiter.limit("5/minute")

def login_admin(request: Request, req: schemas.LoginAdminRequest, db: Session = Depends(get_db)):

    user = db.query(models.Usuario).filter(models.Usuario.username == req.username).first()

    if not user:

        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    if not user.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

        

    try:

        if not pwd_context.verify(req.password, user.password_hash):

            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    except HTTPException:
        raise
    except Exception:

        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    

    rol_efectivo = normalize_role(user.rol)

        

    access_token = create_access_token(data={"sub": user.username, "rol": rol_efectivo})

    return {

        "access_token": access_token, 

        "token_type": "bearer", 

        "rol": rol_efectivo,

        "permisos_modulos": json.dumps(effective_modules(user)),

        "formatos_permitidos": user.formatos_permitidos
        ,"must_change_password": bool(user.must_change_password)

    }



@app.post("/api/auth/login/biometric", response_model=schemas.Token)
@limiter.limit("15/minute")
def login_biometric(request: Request, req: schemas.LoginBiometricRequest, db: Session = Depends(get_db)):
    if not req.fmd_template:
        raise HTTPException(status_code=400, detail="No se recibió la huella biométrica (FMD).")

    match_found = verificar_huella_medico(
        db=db,
        fmd_template=req.fmd_template,
        medico_id=req.medico_id,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="LOGIN",
        subject_ref=f"medico:{req.medico_id}" if req.medico_id is not None else None,
        expected_identity_ref=f"medico:{req.medico_id}" if req.medico_id is not None else None,
    )
    _assert_fea_enabled(match_found)

    

    rol_asignado = "ayudante" if match_found.es_ayudante else "medico"

    access_token = create_access_token(data={"sub": match_found.cedula, "rol": rol_asignado})

    return {

        "access_token": access_token, 

        "token_type": "bearer", 

        "rol": rol_asignado,

        "medico_id": match_found.id,

        "nombre_completo": match_found.nombre_completo,

        "especialidad": match_found.especialidad,

        "cedula": match_found.cedula,

        "foto_url": match_found.foto_url,

        "formatos_permitidos": match_found.formatos_permitidos

    }



@app.post("/api/auth/impersonate")
def impersonate(
    req: schemas.ImpersonateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "sistemas"])),
):
    motivo = req.motivo.strip()
    if len(motivo) < 10:
        raise HTTPException(status_code=422, detail="El motivo de impersonación es obligatorio y debe ser específico.")
    started_at = datetime.datetime.now(datetime.timezone.utc)
    actor_real = f"{normalize_role(current_user.rol)}:{current_user.id}"

    if req.rol == "medico":

        medico = db.query(models.Medico).filter(models.Medico.id == req.target_id).first()

        if not medico or not medico.activo_status:

            raise HTTPException(status_code=404, detail="Médico activo no encontrado")

        effective = f"medico:{medico.id}"
        access_token = create_access_token(
            data={
                "sub": medico.cedula,
                "rol": "medico",
                "actor_real": actor_real,
                "actor_effective": effective,
                "impersonation_reason": motivo,
                "impersonation_started": started_at.isoformat(),
            },
            expires_delta=datetime.timedelta(minutes=15),
        )
        db.add(models.AuditoriaLog(
            usuario_id=current_user.id,
            accion="IMPERSONACION_INICIADA",
            detalles_json=json.dumps({"target": effective, "expira_en_minutos": 15}),
            ip_origen=request.client.host if request.client else None,
            request_id=request.state.request_id,
            actor_real=actor_real,
            actor_effective=effective,
            motivo_impersonacion=motivo,
            resultado="EXITO",
        ))
        db.commit()

        return {

            "access_token": access_token, 

            "token_type": "bearer", 

            "rol": "medico",

            "medico_id": medico.id,

            "nombre_completo": medico.nombre_completo,

            "especialidad": medico.especialidad,

            "cedula": medico.cedula,

            "foto_url": medico.foto_url

        }

    else:

        user = db.query(models.Usuario).filter(models.Usuario.id == req.target_id).first()

        if not user or not user.activo:

            raise HTTPException(status_code=404, detail="Usuario activo no encontrado")

        effective = f"{normalize_role(user.rol)}:{user.id}"
        access_token = create_access_token(
            data={
                "sub": user.username,
                "rol": normalize_role(user.rol),
                "actor_real": actor_real,
                "actor_effective": effective,
                "impersonation_reason": motivo,
                "impersonation_started": started_at.isoformat(),
            },
            expires_delta=datetime.timedelta(minutes=15),
        )
        db.add(models.AuditoriaLog(
            usuario_id=current_user.id,
            accion="IMPERSONACION_INICIADA",
            detalles_json=json.dumps({"target": effective, "expira_en_minutos": 15}),
            ip_origen=request.client.host if request.client else None,
            request_id=request.state.request_id,
            actor_real=actor_real,
            actor_effective=effective,
            motivo_impersonacion=motivo,
            resultado="EXITO",
        ))
        db.commit()

        return {

            "access_token": access_token, 

            "token_type": "bearer", 
            "rol": user.rol
        }


@app.get("/api/auth/me")
def auth_me(current_user=Depends(get_current_user)):
    return {"rol": current_user.rol, "username": getattr(current_user, "username", None),
            "id": current_user.id,
            "formatos_firma_permitidos": getattr(current_user, "formatos_firma_permitidos", None),
            "permisos_modulos": json.dumps(effective_modules(current_user)),
            "formatos_permitidos": getattr(current_user, "formatos_permitidos", None),
            "must_change_password": bool(getattr(current_user, "must_change_password", False))}


@app.get("/api/auth/session")
def refresh_active_session():
    """Small authenticated heartbeat; the auth middleware renews active sessions."""
    return {"active": True}


@app.post("/api/auth/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    claims = getattr(request.state, "auth_claims", {}) or getattr(current_user, "_auth_claims", {})
    jti = claims.get("jti")
    if not jti:
        raise HTTPException(status_code=400, detail="El token no admite revocación; inicie una sesión nueva.")
    expires_at = datetime.datetime.fromtimestamp(int(claims["exp"]), tz=datetime.timezone.utc)
    if not db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first():
        effective = f"{normalize_role(getattr(current_user, 'rol', ''))}:{getattr(current_user, 'id', '')}"
        db.add(models.RevokedToken(
            jti=jti,
            subject=str(claims.get("sub", "")),
            expires_at=expires_at,
            reason="IMPERSONATION_END" if claims.get("actor_real") else "LOGOUT",
            revoked_by=claims.get("actor_real") or effective,
        ))
        db.add(models.AuditoriaLog(
            usuario_id=getattr(current_user, "id", None) if normalize_role(getattr(current_user, "rol", "")) not in {"medico", "ayudante"} else None,
            accion="IMPERSONACION_FINALIZADA" if claims.get("actor_real") else "SESION_REVOCADA",
            detalles_json=json.dumps({"jti_hash": hashlib.sha256(jti.encode()).hexdigest()}),
            ip_origen=request.client.host if request.client else None,
            resultado="EXITO",
        ))
        db.commit()
    return {"success": True, "message": "Sesión revocada."}

# --- Pacientes ---

@app.post("/api/pacientes/sincronizar-kh", response_model=List[schemas.PacienteResponse])
def sincronizar_pacientes_kh(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "sistemas", "enfermeria"])),
):

    try:

        # Sincronizar pacientes desde KH_HE

        camas = kh_database.fetch_camas()

        

        # Ignorar si falla la conexión

        if isinstance(camas, list) and len(camas) > 0 and "Error" not in camas[0] and "Mensaje" not in camas[0]:

            # === SINCRONIZAR CAMAS ===

            processed_rooms = set()

            for cama in camas:

                room_name = cama.get("RoomName")

                

                # Evitar procesar duplicados en la misma consulta (común en camas virtuales)

                if room_name in processed_rooms:

                    continue

                processed_rooms.add(room_name)

                

                # Buscar si ya existe la cama en local

                cama_db = db.query(models.Cama).filter(models.Cama.numero_cama == room_name).first()

                

                # Determinar área básica para la cama

                area = "Otras Áreas"

                name_upper = room_name.upper()

                if "PB" in name_upper or "10" in name_upper: area = "PPB (Planta Baja)"

                elif "PA" in name_upper or "20" in name_upper: area = "PPA (Planta Alta)"

                elif "URGENCIA" in name_upper or "URG" in name_upper: area = "Urgencias"

                elif "QUIR" in name_upper: area = "Quirófano"

                elif "UTI" in name_upper or "TERAPIA" in name_upper or "CUBICULO" in name_upper: area = "Terapia Intensiva"



                if not cama_db:

                    cama_db = models.Cama(

                        numero_cama=room_name,

                        area=area,

                        estado="OCUPADA" if cama.get("Estatus") == "Ocupada" else "DISPONIBLE",

                        activo=True

                    )

                    db.add(cama_db)

                    db.flush() # Guardar de inmediato para evitar colisiones

                else:

                    # Actualizar estado si la cama está activa y no bloqueada/mantenimiento

                    if cama_db.activo and cama_db.estado not in ["MANTENIMIENTO", "BLOQUEADA"]:

                        cama_db.estado = "OCUPADA" if cama.get("Estatus") == "Ocupada" else "DISPONIBLE"

                        

            db.flush()

            

            # === SINCRONIZAR PACIENTES ===

            active_patient_names = [c.get("PatientName") for c in camas if c.get("Estatus") == "Ocupada"]

            

            # Dar de alta a los que ya no están ocupando cama en KH_HE

            local_active_patients = db.query(models.Paciente).filter(models.Paciente.status_ingreso == "Ingresado").all()

            for lp in local_active_patients:

                if lp.nombre_completo not in active_patient_names and lp.registrado_por_nombre == "Sincronización KH_HE":

                    lp.status_ingreso = "Alta"

                    lp.fecha_alta = datetime.datetime.utcnow()

                    lp.dado_de_alta_por_id = None # Sistema

                    

                    nuevo_log = models.AuditoriaLog(

                        usuario_id=None,

                        accion="Alta de Paciente",

                        detalles_json=f"Paciente {lp.nombre_completo} (ID: {lp.id}) fue dado de alta automáticamente por el sistema."

                    )

                    db.add(nuevo_log)

            

            # Agregar o actualizar pacientes ocupados
            for cama in camas:
                if cama.get("Estatus") == "Ocupada":
                    patient_name = cama.get("PatientName")
                    room_name = cama.get("RoomName")
                    pt_date_str = cama.get("pt_date")
                    pt_num_val = str(cama.get("PTNum") or "").strip()

                    paciente_db = None
                    if pt_num_val:
                        paciente_db = db.query(models.Paciente).filter(
                            (models.Paciente.codigo_barras == pt_num_val) |
                            (models.Paciente.codigo_barras == f"PT-{pt_num_val}")
                        ).first()
                    if not paciente_db:
                        paciente_db = db.query(models.Paciente).filter(
                            models.Paciente.nombre_completo == patient_name,
                            models.Paciente.status_ingreso == "Ingresado"
                        ).first()

                    # Determinar área básica
                    area = "Otras Áreas"
                    name_upper = room_name.upper()
                    if "PB" in name_upper or "10" in name_upper: area = "PPB (Planta Baja)"
                    elif "PA" in name_upper or "20" in name_upper: area = "PPA (Planta Alta)"
                    elif "URGENCIA" in name_upper or "URG" in name_upper: area = "Urgencias"
                    elif "QUIR" in name_upper: area = "Quirófano"
                    elif "UTI" in name_upper or "TERAPIA" in name_upper or "CUBICULO" in name_upper: area = "Terapia Intensiva"

                    if not paciente_db:
                        nuevo_paciente = models.Paciente(
                            nombre_completo=patient_name,
                            codigo_barras=pt_num_val if pt_num_val else None,
                            num_habitacion=room_name,
                            area_hospitalaria=area,
                            status_ingreso="Ingresado",
                            registrado_por_nombre="Sincronización KH_HE"
                        )
                        db.add(nuevo_paciente)
                        db.flush() # Evitar duplicados en el mismo bucle
                    else:
                        if pt_num_val and (not paciente_db.codigo_barras or paciente_db.codigo_barras != pt_num_val):
                            paciente_db.codigo_barras = pt_num_val
                        if paciente_db.num_habitacion != room_name:
                            dt_traslado = datetime.datetime.utcnow()
                            if pt_date_str and pt_date_str != "None":

                                try:

                                    dt_traslado = datetime.datetime.fromisoformat(pt_date_str.split(".")[0].replace(" ", "T"))

                                except:

                                    pass



                            nuevo_traslado = models.TrasladoPaciente(

                                paciente_id=paciente_db.id,

                                origen_area=paciente_db.area_hospitalaria,

                                origen_habitacion=paciente_db.num_habitacion,

                                destino_area=area,

                                destino_habitacion=room_name,

                                fecha_traslado=dt_traslado,

                                usuario_id=None # Sistema

                            )

                            db.add(nuevo_traslado)

                            paciente_db.num_habitacion = room_name

                            paciente_db.area_hospitalaria = area

            db.commit()

    except Exception as e:

        print(f"Error en sincronización de pacientes KH_HE: {e}")

        db.rollback()



    return db.query(models.Paciente).filter(
        models.Paciente.status_ingreso.in_(["Ingresado", "Activo"]),
        models.Paciente.status_ingreso != "Alta"
    ).all()


@app.get("/api/pacientes", response_model=List[schemas.PacienteResponse])
def get_pacientes(db: Session = Depends(get_db)):
    """Read-only patient list. Synchronization is an explicit POST operation."""
    return db.query(models.Paciente).filter(
        models.Paciente.status_ingreso.in_(["Ingresado", "Activo"]),
        models.Paciente.status_ingreso != "Alta",
    ).all()



@app.post("/api/pacientes", response_model=schemas.PacienteResponse)

def create_paciente(paciente: schemas.PacienteCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):

    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")

    registrado_por = None

    if is_medico:

        medico_db = db.query(models.Medico).filter(models.Medico.id == current_user.id).first()

        if medico_db:

            if medico_db.es_ayudante:

                med_titular = db.query(models.Medico).filter(models.Medico.id == medico_db.medico_asignado_id).first()

                titular_nombre = med_titular.nombre_completo if med_titular else "Desconocido"

                registrado_por = f"{medico_db.nombre_completo} (Ayudante del Dr. {titular_nombre})"

            else:

                registrado_por = f"Dr. {medico_db.nombre_completo}"

    else:

        registrado_por = current_user.nombre_completo or current_user.username



    nuevo_paciente = models.Paciente(

        nombre_completo=paciente.nombre_completo,

        num_habitacion=paciente.num_habitacion,

        area_hospitalaria=paciente.area_hospitalaria,

        codigo_barras=paciente.codigo_barras,

        status_ingreso="Ingresado",

        creado_por_id=None if is_medico else current_user.id,

        registrado_por_nombre=registrado_por

    )

    db.add(nuevo_paciente)
    db.flush()
    log_auditoria(db, current_user.id, f"Paciente Ingresado", f"Se ingresó al paciente {nuevo_paciente.nombre_completo} (Folio ID: {nuevo_paciente.id}) en {nuevo_paciente.area_hospitalaria} - Hab: {nuevo_paciente.num_habitacion}")
    db.commit()
    db.refresh(nuevo_paciente)

    

    return nuevo_paciente



@app.put("/api/pacientes/{paciente_id}", response_model=schemas.PacienteResponse)

def update_paciente(paciente_id: int, req: schemas.PacienteUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):

    paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente_id).first()

    if not paciente:

        raise HTTPException(status_code=404, detail="Paciente no encontrado")

        

    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")

    usuario_id_log = None if is_medico else current_user.id

        

    area_ant = paciente.area_hospitalaria

    hab_ant = paciente.num_habitacion

    cambio_traslado = False

    

    if req.nombre_completo != paciente.nombre_completo:

        log_auditoria(db, usuario_id_log, "Nombre Paciente Editado", f"De {paciente.nombre_completo} a {req.nombre_completo}")

        paciente.nombre_completo = req.nombre_completo

        

    if req.num_habitacion != paciente.num_habitacion:

        cambio_traslado = True

    if req.area_hospitalaria is not None and req.area_hospitalaria != paciente.area_hospitalaria:

        cambio_traslado = True



    paciente.num_habitacion = req.num_habitacion

    if req.area_hospitalaria is not None:

        paciente.area_hospitalaria = req.area_hospitalaria

    if req.codigo_barras is not None:

        paciente.codigo_barras = req.codigo_barras

        

    if cambio_traslado:

        traslado = models.TrasladoPaciente(

            paciente_id=paciente.id,

            origen_area=area_ant,

            origen_habitacion=hab_ant,

            destino_area=paciente.area_hospitalaria,

            destino_habitacion=paciente.num_habitacion,

            usuario_id=usuario_id_log

        )

        db.add(traslado)

        log_auditoria(db, usuario_id_log, "Traslado de Paciente", f"Paciente {paciente.nombre_completo} movido de {area_ant}({hab_ant}) a {paciente.area_hospitalaria}({paciente.num_habitacion})")

        

    db.commit()

    db.refresh(paciente)

    return paciente



def get_or_create_paciente_by_identifier(
    db: Session,
    identifier: str,
    *,
    allow_create: bool = True,
) -> Optional[models.Paciente]:
    """
    Resuelve flexiblemente un paciente ya sea por su ID interno de PostgreSQL, 
    su folio/MRN/código de barras (ej. PTNum), o sincronizándolo desde Vertical.
    """
    ident_str = str(identifier or "").strip()
    if not ident_str:
        return None
    
    clean_code = ident_str.upper().replace("PT-", "").strip()
    paciente = None

    # 1. Por código de barras / Folio / MRN / PTNum exacto
    paciente = db.query(models.Paciente).filter(
        (models.Paciente.codigo_barras == ident_str) | 
        (models.Paciente.codigo_barras == clean_code) |
        (models.Paciente.codigo_barras == f"PT-{clean_code}")
    ).first()
    
    # 2. Por ID directo de PostgreSQL (si coincide con registro local)
    if not paciente and ident_str.isdigit():
        paciente = db.query(models.Paciente).filter(models.Paciente.id == int(ident_str)).first()
        
    # 3. Por nombre completo exacto o aproximado
    if not paciente:
        paciente = db.query(models.Paciente).filter(models.Paciente.nombre_completo.ilike(f"%{ident_str}%")).first()

    # 4. Si no existe en PostgreSQL, consultar SQL Server (Vertical KH_HE)
    if not paciente:
        if not allow_create:
            return None
        try:
            from kh_database import get_kh_connection
            conn = get_kh_connection()
            if conn:
                cur = conn.cursor()
                sql_pt = """
                    SELECT TOP 1 p.PTNum, p.FullName, COALESCE(c.Habitacion, m.RoomName, 'Cama Virtual') as Habitacion
                    FROM PT p
                    OUTER APPLY (
                        SELECT TOP 1 Habitacion FROM UDR_AD_CENSO WHERE UDR_AD_CENSO.PCNum IN (
                            SELECT TOP 1 PCNum FROM PC WHERE PC.PTNum = p.PTNum ORDER BY EntryDate DESC
                        )
                    ) c
                    OUTER APPLY (
                        SELECT TOP 1 RoomName FROM V_MRPT WHERE V_MRPT.PTNum = p.PTNum
                    ) m
                    WHERE p.PTNum = ?
                """
                if clean_code.isdigit():
                    cur.execute(sql_pt, (int(clean_code),))
                else:
                    sql_name = sql_pt.replace("p.PTNum = ?", "p.FullName LIKE ?")
                    cur.execute(sql_name, (f"%{ident_str}%",))
                row = cur.fetchone()
                if row:
                    pt_folio = str(row[0])
                    nombre_pt = str(row[1] or f"PACIENTE {pt_folio}").strip().upper()
                    cama_pt = str(row[2] or "Cama Virtual").strip()
                    
                    paciente = db.query(models.Paciente).filter(
                        (models.Paciente.codigo_barras == pt_folio) |
                        (models.Paciente.codigo_barras == f"PT-{pt_folio}")
                    ).first()
                    if not paciente:
                        # Buscar si ya existía localmente sin código de barras asignado
                        paciente = db.query(models.Paciente).filter(
                            models.Paciente.nombre_completo == nombre_pt
                        ).first()
                        if paciente:
                            paciente.codigo_barras = pt_folio
                            if not paciente.num_habitacion or paciente.num_habitacion == "Cama Virtual":
                                paciente.num_habitacion = cama_pt
                            db.commit()
                            db.refresh(paciente)

                    if not paciente:
                        paciente = models.Paciente(
                            nombre_completo=nombre_pt,
                            codigo_barras=pt_folio,
                            num_habitacion=cama_pt if cama_pt else "Cama Virtual",
                            area_hospitalaria="Hospitalización",
                            status_ingreso="Ingresado"
                        )
                        db.add(paciente)
                        db.commit()
                        db.refresh(paciente)
                conn.close()
        except Exception as e:
            logger.warning(f"Aviso al sincronizar paciente desde Vertical: {e}")

    return paciente


@app.put("/api/pacientes/{paciente_id}/alta")
@app.put("/api/ehr/paciente/{paciente_id}/alta")
def alta_paciente(
    paciente_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    paciente = get_or_create_paciente_by_identifier(db, str(paciente_id))
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    latest_readmission = db.query(models.ClinicalSyncOperation).filter(
        models.ClinicalSyncOperation.operation_type == "PATIENT_READMISSION",
        models.ClinicalSyncOperation.aggregate_id == str(paciente.id),
        models.ClinicalSyncOperation.state == clinical_sync.SYNCED,
    ).order_by(models.ClinicalSyncOperation.completed_at.desc()).first()
    episode_token = (
        str(latest_readmission.operation_id)
        if latest_readmission
        else paciente.fecha_registro.isoformat()
    )
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="PATIENT_DISCHARGE",
        aggregate_type="patient_episode",
        aggregate_id=str(paciente.id),
        patient_ref=str(paciente.codigo_barras or paciente_id).replace("PT-", ""),
        payload={"episode_token": episode_token},
    )
    if not created:
        return _existing_sync_response(operation)

    paciente.status_ingreso = "Alta"
    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")
    if not is_medico and hasattr(current_user, "id"):
        paciente.dado_de_alta_por_id = current_user.id
    paciente.fecha_alta = datetime.datetime.utcnow()

    # Liberar cama en catálogo local de camas
    if paciente.num_habitacion:
        cama_db = db.query(models.Cama).filter(models.Cama.numero_cama == paciente.num_habitacion).first()
        if cama_db and cama_db.estado == "OCUPADA":
            cama_db.estado = "DISPONIBLE"

    usuario_id_log = None if is_medico else getattr(current_user, "id", None)
    log_auditoria(db, usuario_id_log, "Alta de Paciente", f"Paciente {paciente.nombre_completo} (ID: {paciente.id}, Folio: {paciente.codigo_barras}) fue dado de alta")

    # AUTO-PURGA Y DESTRUCCIÓN DE BIOMETRÍA TEMPORAL (LFPDPPP y NOM-004-SSA3-2012)
    firmantes_activos = db.query(models.BiometriaFirmanteEpisodio).filter(
        (models.BiometriaFirmanteEpisodio.paciente_id == paciente.id) |
        (models.BiometriaFirmanteEpisodio.pt_num == str(paciente.codigo_barras)) |
        (models.BiometriaFirmanteEpisodio.pt_num == f"PT-{paciente.codigo_barras}")
    ).all()

    purgados_count = len(firmantes_activos)
    for firmante in firmantes_activos:
        firmante.estado = "INACTIVO_POR_ALTA"
        firmante.fmd_template = None # Destrucción física de la plantilla dactilar en BD
        firmante.huella_token = None
        firmante.biometric_status = "SIN_BIOMETRIA"
        firmante.template_format = None
        firmante.template_version = None
        firmante.requiere_reenrolamiento = False
        firmante.fecha_inactivacion = datetime.datetime.utcnow()
        firmante.inactivado_por_usuario_id = usuario_id_log

    if purgados_count > 0:
        log_auditoria(
            db, usuario_id_log, "Purga Biometría por Alta",
            f"Se inactivaron y destruyeron {purgados_count} plantillas dactilares temporales del episodio del paciente {paciente.nombre_completo} (ID: {paciente.id})"
        )

    clinical_sync.mark_local_applied(db, operation)
    result = clinical_sync.execute_external(
        db,
        operation,
        clinical_sync_adapters.dispatcher(operation),
        session_factory=SessionLocal,
    )
    return _sync_result_response(result, {
        "message": "Paciente dado de alta y biometría temporal purgada exitosamente",
        "firmantes_inactivados": purgados_count,
    })


def is_paciente_de_alta(db: Session, identifier: str) -> bool:
    """
    Verifica si un paciente se encuentra de alta / egresado (en PostgreSQL o SQL Server).
    """
    if not identifier:
        return False
    ident_str = str(identifier).strip()
    clean_code = ident_str.upper().replace("PT-", "").strip()

    # 1. Resolver paciente local para obtener su Folio/PTNum exacto
    local_pt = get_or_create_paciente_by_identifier(db, ident_str)
    pt_num_val = None
    if local_pt and local_pt.codigo_barras and str(local_pt.codigo_barras).isdigit():
        pt_num_val = int(local_pt.codigo_barras)
    elif clean_code.isdigit():
        pt_num_val = int(clean_code)

    # 2. Primero verificar si en SQL Server (Vertical) tiene episodio activo o censo
    try:
        from kh_database import get_kh_connection
        conn = get_kh_connection()
        if conn and pt_num_val:
            cur = conn.cursor()
            cur.execute("""
                SELECT TOP 1
                    pc.PC_ST, pc.MedicalDischarge, pc.MedicalDischargeDate, pc.ExitDate, pc.ClosedOn,
                    c.Habitacion as CamaCenso
                FROM PC pc
                LEFT JOIN UDR_AD_CENSO c ON pc.PCNum = c.PCNum
                WHERE pc.PTNum = ?
                ORDER BY pc.EntryDate DESC, pc.PCNum DESC
            """, (pt_num_val,))
            r = cur.fetchone()
            if r:
                pc_st, med_dc, med_dc_date, exit_date, closed_on, cama_censo = r[0], r[1], r[2], r[3], r[4], r[5]
                has_active_censo = bool(cama_censo and str(cama_censo).strip())
                is_pc_closed = bool(closed_on or med_dc_date or bool(med_dc) or (pc_st in ('CL', 'PD', 'CA')))

                # Si tiene cama asignada en el censo activo o su episodio en PC está en OP (Abierto) sin alta médica:
                if has_active_censo or (pc_st == 'OP' and not is_pc_closed):
                    if local_pt and (local_pt.status_ingreso != "Ingresado" or local_pt.fecha_alta is not None):
                        local_pt.status_ingreso = "Ingresado"
                        local_pt.fecha_alta = None
                        local_pt.dado_de_alta_por_id = None
                        db.commit()
                    conn.close()
                    return False  # Paciente activo en Vertical
                elif is_pc_closed:
                    conn.close()
                    return True  # Paciente dado de alta en Vertical
            conn.close()
    except Exception as e:
        logger.warning(f"Aviso al verificar estatus de alta en SQL Server: {e}")

    # 3. Verificar registro local en PostgreSQL
    if local_pt and (local_pt.status_ingreso == "Alta" or local_pt.fecha_alta is not None):
        return True

    return False


def assert_paciente_no_de_alta(db: Session, identifier: str):
    """
    Lanza una excepción HTTP 400 si el paciente se encuentra de alta médica / egresado.
    """
    if is_paciente_de_alta(db, identifier):
        raise HTTPException(
            status_code=400,
            detail="El paciente se encuentra de ALTA / EGRESADO. Conforme a la normativa oficial (NOM-004-SSA3-2012 / NOM-024-SSA3-2012), el expediente clínico se encuentra en modo de solo lectura y no admite modificaciones ni nuevos formatos en un episodio cerrado."
        )


@app.put("/api/pacientes/{paciente_id}/reingresar")
@app.put("/api/ehr/paciente/{paciente_id}/reingresar")
def reingresar_paciente(
    paciente_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    paciente = get_or_create_paciente_by_identifier(db, str(paciente_id))
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    discharge = db.query(models.ClinicalSyncOperation).filter(
        models.ClinicalSyncOperation.operation_type == "PATIENT_DISCHARGE",
        models.ClinicalSyncOperation.aggregate_id == str(paciente.id),
    ).order_by(models.ClinicalSyncOperation.created_at.desc()).first()
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="PATIENT_READMISSION",
        aggregate_type="patient_episode",
        aggregate_id=str(paciente.id),
        patient_ref=str(paciente.codigo_barras or paciente_id).replace("PT-", ""),
        payload={"discharge_operation_id": str(discharge.operation_id) if discharge else None},
    )
    if not created:
        return _existing_sync_response(operation)

    paciente.status_ingreso = "Ingresado"
    paciente.fecha_alta = None
    paciente.dado_de_alta_por_id = None

    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")
    usuario_id_log = None if is_medico else getattr(current_user, "id", None)
    log_auditoria(db, usuario_id_log, "Reingreso de Paciente", f"Paciente {paciente.nombre_completo} (ID: {paciente.id}, Folio: {paciente.codigo_barras}) fue reingresado al sistema.")

    # Al reingresar al paciente, se rehabilitan los contactos del catálogo pero SIN huellas activas:
    # Las huellas previas fueron destruidas al alta y deben volverse a registrar/enrolar
    # para el nuevo episodio clínico (sin afectar las firmas y documentos ya sellados previamente).
    firmantes_existentes = db.query(models.BiometriaFirmanteEpisodio).filter(
        (models.BiometriaFirmanteEpisodio.paciente_id == paciente.id) |
        (models.BiometriaFirmanteEpisodio.pt_num == str(paciente.codigo_barras)) |
        (models.BiometriaFirmanteEpisodio.pt_num == f"PT-{paciente.codigo_barras}")
    ).all()
    for f in firmantes_existentes:
        f.estado = "ACTIVO"
        f.fmd_template = None  # Plantilla física purgada / destruida
        f.huella_token = None
        f.biometric_status = "SIN_BIOMETRIA"
        f.template_format = None
        f.template_version = None
        f.requiere_reenrolamiento = False
        f.fecha_inactivacion = None
        f.inactivado_por_usuario_id = None

    clinical_sync.mark_local_applied(db, operation)
    db.refresh(paciente)
    result = clinical_sync.execute_external(
        db,
        operation,
        clinical_sync_adapters.dispatcher(operation),
        session_factory=SessionLocal,
    )
    return _sync_result_response(result, {
        "message": f"Paciente {paciente.nombre_completo} reingresado exitosamente.",
        "paciente": paciente,
    })


@app.post("/api/pacientes/{paciente_id}/firmantes-biometricos", response_model=schemas.FirmanteBiometricoResponse)
@app.post("/api/ehr/paciente/{paciente_id}/firmantes-biometricos", response_model=schemas.FirmanteBiometricoResponse)
def registrar_firmante_biometrico(
    paciente_id: str,
    req: schemas.FirmanteBiometricoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Enrola o actualiza temporalmente la información y/o huella dactilar de un paciente, familiar o testigo.
    Sincroniza automáticamente los datos con la tabla PTCN de Vertical (KH_HE).
    """
    paciente = get_or_create_paciente_by_identifier(db, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    req_payload = req.model_dump()
    user_nom = getattr(current_user, "nombre_completo", None) or getattr(current_user, "username", "Usuario")
    pt_key = paciente.codigo_barras or paciente.nombre_completo
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="KH_MUTATION",
        aggregate_type="patient_contact",
        aggregate_id=f"{paciente.id}:{req.nombre_completo.strip().upper()}",
        patient_ref=str(pt_key),
        payload={
            "adapter": "sync_contact_to_ptcn",
            "args": [str(pt_key), req_payload],
            "kwargs": {"username": user_nom},
        },
    )
    if not created:
        return _existing_sync_response(operation)
    
    # Si el paciente estaba marcado en Alta, al enrolar biometría para el episodio se reactiva automáticamente
    if paciente.status_ingreso == "Alta":
        paciente.status_ingreso = "Ingresado"
        paciente.fecha_alta = None
        paciente.dado_de_alta_por_id = None

    req_name = req.nombre_completo.strip().upper()
    req_tipo = req.tipo_firmante.strip().upper()
    
    # Buscar si ya existe un registro activo con el mismo nombre para este paciente para actualizarlo sin duplicar
    firmante = db.query(models.BiometriaFirmanteEpisodio).filter(
        (models.BiometriaFirmanteEpisodio.paciente_id == paciente.id) |
        (models.BiometriaFirmanteEpisodio.pt_num == str(paciente.codigo_barras)) |
        (models.BiometriaFirmanteEpisodio.pt_num == f"PT-{paciente.codigo_barras}"),
        models.BiometriaFirmanteEpisodio.estado == "ACTIVO",
        func.upper(models.BiometriaFirmanteEpisodio.nombre_completo) == req_name
    ).first()

    if firmante:
        firmante.tipo_firmante = req_tipo
        firmante.parentesco = req.parentesco.strip() if req.parentesco else firmante.parentesco
        if req.identificacion_oficial is not None:
            firmante.identificacion_oficial = req.identificacion_oficial.strip() if req.identificacion_oficial else None
        if req.domicilio is not None:
            firmante.domicilio = req.domicilio.strip() if req.domicilio else None
        if req.telefono is not None:
            firmante.telefono = req.telefono.strip() if req.telefono else None
        if req.email is not None:
            firmante.email = req.email.strip() if req.email else None
    else:
        firmante = models.BiometriaFirmanteEpisodio(
            paciente_id=paciente.id,
            pt_num=paciente.codigo_barras or str(paciente.id),
            tipo_firmante=req_tipo,
            nombre_completo=req_name,
            parentesco=req.parentesco.strip() if req.parentesco else "Titular",
            identificacion_oficial=req.identificacion_oficial.strip() if req.identificacion_oficial else None,
            domicilio=req.domicilio.strip() if req.domicilio else None,
            telefono=req.telefono.strip() if req.telefono else None,
            email=req.email.strip() if req.email else None,
            fmd_template=None,
            huella_token=None,
            biometric_status="SIN_BIOMETRIA",
            estado="ACTIVO"
        )
        db.add(firmante)
    
    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")
    usuario_id_log = None if is_medico else getattr(current_user, "id", None)
    user_nom = getattr(current_user, "nombre_completo", None) or getattr(current_user, "username", "Usuario")
    user_rol = getattr(current_user, "rol", "general").upper()
    log_auditoria(
        db, usuario_id_log, "Enrolamiento Biométrico Episodio",
        f"Firmante {firmante.nombre_completo} ({firmante.tipo_firmante} - {firmante.parentesco}) enrolado por {user_nom} ({user_rol}) para paciente {paciente.nombre_completo} (ID: {paciente.id})"
    )
    
    db.commit()
    db.refresh(firmante)

    clinical_sync.mark_local_applied(db, operation)
    result = clinical_sync.execute_external(
        db, operation, clinical_sync_adapters.dispatcher(operation), session_factory=SessionLocal
    )
    if result.state == clinical_sync.SYNCED:
        return firmante
    return _sync_result_response(result, {})


@app.put("/api/pacientes/{paciente_id}/firmantes-biometricos/{firmante_id}", response_model=schemas.FirmanteBiometricoResponse)
@app.put("/api/ehr/paciente/{paciente_id}/firmantes-biometricos/{firmante_id}", response_model=schemas.FirmanteBiometricoResponse)
def actualizar_firmante_biometrico(
    paciente_id: str,
    firmante_id: int,
    req: schemas.FirmanteBiometricoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Actualiza los datos o captura/re-enrola la huella de un firmante/contacto existente.
    Sincroniza los cambios con la tabla PTCN en Vertical.
    """
    paciente = get_or_create_paciente_by_identifier(db, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    current_firmante = db.query(models.BiometriaFirmanteEpisodio).filter(
        models.BiometriaFirmanteEpisodio.id == firmante_id
    ).first()
    if not current_firmante:
        raise HTTPException(status_code=404, detail="Firmante biométrico no encontrado")
    incoming = req.model_dump(exclude_unset=True)
    user_nom = getattr(current_user, "nombre_completo", None) or getattr(current_user, "username", "Usuario")
    pt_key = paciente.codigo_barras or paciente.nombre_completo or str(paciente_id)
    external_payload = {
        "nombre_completo": incoming.get("nombre_completo") or current_firmante.nombre_completo,
        "parentesco": incoming.get("parentesco") or current_firmante.parentesco,
        "tipo_firmante": incoming.get("tipo_firmante") or current_firmante.tipo_firmante,
        "identificacion_oficial": incoming.get("identificacion_oficial", current_firmante.identificacion_oficial),
        "domicilio": incoming.get("domicilio", current_firmante.domicilio),
        "telefono": incoming.get("telefono", current_firmante.telefono),
        "email": incoming.get("email", current_firmante.email),
    }
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="KH_MUTATION",
        aggregate_type="patient_contact",
        aggregate_id=f"{paciente.id}:{firmante_id}",
        patient_ref=str(pt_key),
        payload={
            "adapter": "sync_contact_to_ptcn",
            "args": [str(pt_key), external_payload],
            "kwargs": {"username": user_nom},
        },
    )
    if not created:
        return _existing_sync_response(operation)

    # Si el paciente estaba marcado en Alta, al actualizar/enrolar su biometría se asegura como Ingresado
    if paciente.status_ingreso == "Alta":
        paciente.status_ingreso = "Ingresado"
        paciente.fecha_alta = None
        paciente.dado_de_alta_por_id = None

    firmante = db.query(models.BiometriaFirmanteEpisodio).filter(
        models.BiometriaFirmanteEpisodio.id == firmante_id,
        (models.BiometriaFirmanteEpisodio.paciente_id == paciente.id) | 
        (models.BiometriaFirmanteEpisodio.pt_num == str(paciente.codigo_barras)) |
        (models.BiometriaFirmanteEpisodio.pt_num == f"PT-{paciente.codigo_barras}") |
        (models.BiometriaFirmanteEpisodio.pt_num == str(paciente.id))
    ).first()
    if not firmante:
        # Fallback por ID si hubo desalineación de IDs
        firmante = db.query(models.BiometriaFirmanteEpisodio).filter(models.BiometriaFirmanteEpisodio.id == firmante_id).first()
        if firmante:
            firmante.paciente_id = paciente.id
            firmante.pt_num = paciente.codigo_barras or str(paciente.id)
        else:
            raise HTTPException(status_code=404, detail="Firmante biométrico no encontrado")

    if req.nombre_completo is not None and req.nombre_completo.strip():
        firmante.nombre_completo = req.nombre_completo.strip().upper()
    if req.parentesco is not None:
        firmante.parentesco = req.parentesco.strip() or "Titular"
    if req.tipo_firmante is not None and req.tipo_firmante.strip():
        firmante.tipo_firmante = req.tipo_firmante.strip().upper()
    if req.identificacion_oficial is not None:
        firmante.identificacion_oficial = req.identificacion_oficial.strip() if req.identificacion_oficial else None
    if req.domicilio is not None:
        firmante.domicilio = req.domicilio.strip() if req.domicilio else None
    if req.telefono is not None:
        firmante.telefono = req.telefono.strip() if req.telefono else None
    if req.email is not None:
        firmante.email = req.email.strip() if req.email else None
    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")
    usuario_id_log = None if is_medico else getattr(current_user, "id", None)
    user_nom = getattr(current_user, "nombre_completo", None) or getattr(current_user, "username", "Usuario")
    user_rol = getattr(current_user, "rol", "general").upper()
    
    log_auditoria(
        db, usuario_id_log, "Actualización Biometría Firmante",
        f"Datos del firmante {firmante.nombre_completo} ({firmante.tipo_firmante} - {firmante.parentesco}) actualizados por {user_nom} ({user_rol}) para paciente {paciente.nombre_completo} (ID: {paciente.id}); sin cambio biométrico"
    )

    db.commit()
    db.refresh(firmante)

    clinical_sync.mark_local_applied(db, operation)
    result = clinical_sync.execute_external(
        db, operation, clinical_sync_adapters.dispatcher(operation), session_factory=SessionLocal
    )
    if result.state == clinical_sync.SYNCED:
        return firmante
    return _sync_result_response(result, {})


def _enrolar_firmante_controlado(
    *,
    paciente_id: str,
    firmante_id: int,
    req: schemas.BiometricEnrollmentRequest,
    request: Request,
    db: Session,
    current_user,
    reenrolamiento: bool,
):
    paciente = get_or_create_paciente_by_identifier(db, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    if paciente.status_ingreso == "Alta":
        raise HTTPException(status_code=409, detail="No se enrola biometría en un episodio cerrado.")
    firmante = db.query(models.BiometriaFirmanteEpisodio).filter(
        models.BiometriaFirmanteEpisodio.id == firmante_id,
        models.BiometriaFirmanteEpisodio.paciente_id == paciente.id,
        models.BiometriaFirmanteEpisodio.estado == "ACTIVO",
    ).first()
    if not firmante:
        raise HTTPException(status_code=404, detail="Firmante activo no encontrado para este paciente.")
    if reenrolamiento and not (req.motivo or "").strip():
        raise HTTPException(status_code=422, detail="El motivo de reenrolamiento es obligatorio.")
    if not reenrolamiento and firmante.biometric_status != "SIN_BIOMETRIA":
        raise HTTPException(status_code=409, detail="El firmante ya tiene biometría; use reenrolamiento explícito.")

    action = "REENROLAMIENTO_FIRMANTE" if reenrolamiento else "ENROLAMIENTO_FIRMANTE"
    capture = biometric_security.validate_attested_capture_evidence(
        req.fmd_template, req.challenge_id, req.session_id
    )
    validate_and_consume_challenge(
        db,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action=action,
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=f"firmante:{firmante_id}",
        patient_ref=str(paciente_id),
        document_ref=str(firmante_id),
        acquisition=capture,
    )
    canonical = capture.canonical
    firmante.fmd_template = canonical
    firmante.huella_token = f"TOKEN-FIRM-{uuid.uuid4()}"
    firmante.biometric_status = "FMD_VALIDO"
    firmante.template_format = biometric_security.TEMPLATE_FORMAT
    firmante.template_version = biometric_security.TEMPLATE_VERSION
    firmante.fecha_enrolamiento = datetime.datetime.utcnow()
    firmante.requiere_reenrolamiento = False
    db.add(
        models.AuditoriaLog(
            usuario_id=None if isinstance(current_user, models.Medico) else current_user.id,
            accion=action,
            detalles_json=json.dumps(
                {
                    "paciente_id": paciente.id,
                    "firmante_id": firmante.id,
                    "tipo_firmante": firmante.tipo_firmante,
                    "motivo": (req.motivo or "ENROLAMIENTO_INICIAL").strip(),
                    "template_format": biometric_security.TEMPLATE_FORMAT,
                }
            ),
            ip_origen=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(firmante)
    return firmante


@app.post(
    "/api/pacientes/{paciente_id}/firmantes-biometricos/{firmante_id}/enrolar",
    response_model=schemas.FirmanteBiometricoResponse,
)
@app.post(
    "/api/ehr/paciente/{paciente_id}/firmantes-biometricos/{firmante_id}/enrolar",
    response_model=schemas.FirmanteBiometricoResponse,
)
def enrolar_firmante_biometrico(
    paciente_id: str,
    firmante_id: int,
    req: schemas.BiometricEnrollmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _enrolar_firmante_controlado(
        paciente_id=paciente_id,
        firmante_id=firmante_id,
        req=req,
        request=request,
        db=db,
        current_user=current_user,
        reenrolamiento=False,
    )


@app.post(
    "/api/pacientes/{paciente_id}/firmantes-biometricos/{firmante_id}/reenrolar",
    response_model=schemas.FirmanteBiometricoResponse,
)
@app.post(
    "/api/ehr/paciente/{paciente_id}/firmantes-biometricos/{firmante_id}/reenrolar",
    response_model=schemas.FirmanteBiometricoResponse,
)
def reenrolar_firmante_biometrico(
    paciente_id: str,
    firmante_id: int,
    req: schemas.BiometricEnrollmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _enrolar_firmante_controlado(
        paciente_id=paciente_id,
        firmante_id=firmante_id,
        req=req,
        request=request,
        db=db,
        current_user=current_user,
        reenrolamiento=True,
    )


@app.get("/api/pacientes/{paciente_id}/firmantes-biometricos", response_model=List[schemas.FirmanteBiometricoResponse])
@app.get("/api/ehr/paciente/{paciente_id}/firmantes-biometricos", response_model=List[schemas.FirmanteBiometricoResponse])
def listar_firmantes_biometricos(
    paciente_id: str,
    db: Session = Depends(get_db)
):
    """
    Lista todos los firmantes biométricos activos asociados al episodio hospitalario del paciente.
    Este GET es estrictamente de solo lectura.
    """
    paciente = get_or_create_paciente_by_identifier(db, paciente_id, allow_create=False)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    todos_firmantes_locales = db.query(models.BiometriaFirmanteEpisodio).filter(
        (models.BiometriaFirmanteEpisodio.paciente_id == paciente.id) |
        (models.BiometriaFirmanteEpisodio.pt_num == str(paciente.codigo_barras)) |
        (models.BiometriaFirmanteEpisodio.pt_num == f"PT-{paciente.codigo_barras}")
    ).all()

    firmantes = [f for f in todos_firmantes_locales if f.estado == "ACTIVO"]
    pac_name = (paciente.nombre_completo or "").strip()

    # Filtrar y deduplicar: El paciente va primero y nunca como testigo; contactos externos sin duplicidad
    pac_firmantes = [f for f in firmantes if f.tipo_firmante == "PACIENTE"]
    otros_firmantes = []
    vistos = set()
    for f in firmantes:
        n_up = f.nombre_completo.strip().upper()
        if f.tipo_firmante == "PACIENTE" or n_up == pac_name.strip().upper():
            continue
        if n_up not in vistos:
            vistos.add(n_up)
            otros_firmantes.append(f)

    return pac_firmantes + otros_firmantes


@app.post("/api/pacientes/{paciente_id}/firmantes-biometricos/verificar", response_model=schemas.VerificarHuellaFirmanteResponse)
@app.post("/api/ehr/paciente/{paciente_id}/firmantes-biometricos/verificar", response_model=schemas.VerificarHuellaFirmanteResponse)
def verificar_huella_firmante_endpoint(
    paciente_id: str,
    req: schemas.VerificarHuellaFirmanteRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verifica la huella dactilar de un paciente o testigo en tiempo real contra los firmantes
    activos del episodio hospitalario.
    """
    paciente = get_or_create_paciente_by_identifier(db, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    firmante = verificar_huella_firmante_episodio(
        db=db,
        paciente_id=paciente.id,
        fmd_template=req.fmd_template,
        firmante_id=req.firmante_id,
        tipo_firmante=req.tipo_firmante,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="VERIFICACION_FIRMANTE",
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=f"firmante:{req.firmante_id}",
        patient_ref=str(paciente_id),
    )

    now_iso = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    sello_raw = f"{firmante.id}-{firmante.huella_token}-{firmante.nombre_completo}-{now_iso}"
    sello_hash = hashlib.sha256(sello_raw.encode('utf-8')).hexdigest()

    return {
        "is_match": True,
        "firmante": firmante,
        "sello_biometrico": f"BIO-HES:{sello_hash[:32]}",
        "fecha_hora_verificacion": now_iso
    }


@app.delete("/api/pacientes/{paciente_id}/firmantes-biometricos/{firmante_id}")
@app.delete("/api/ehr/paciente/{paciente_id}/firmantes-biometricos/{firmante_id}")
def revocar_firmante_biometrico(
    paciente_id: str,
    firmante_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Revoca e inactiva manualmente a un firmante biométrico del paciente antes del alta médica.
    """
    paciente = get_or_create_paciente_by_identifier(db, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    firmante = db.query(models.BiometriaFirmanteEpisodio).filter(
        models.BiometriaFirmanteEpisodio.id == firmante_id,
        (models.BiometriaFirmanteEpisodio.paciente_id == paciente.id) | 
        (models.BiometriaFirmanteEpisodio.pt_num == str(paciente.codigo_barras)) |
        (models.BiometriaFirmanteEpisodio.pt_num == f"PT-{paciente.codigo_barras}") |
        (models.BiometriaFirmanteEpisodio.pt_num == str(paciente.id))
    ).first()
    if not firmante:
        firmante = db.query(models.BiometriaFirmanteEpisodio).filter(models.BiometriaFirmanteEpisodio.id == firmante_id).first()
    if not firmante:
        raise HTTPException(status_code=404, detail="Firmante biométrico no encontrado")

    pt_key = paciente.codigo_barras or paciente.nombre_completo
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="KH_MUTATION",
        aggregate_type="patient_contact",
        aggregate_id=f"{paciente.id}:{firmante_id}:revoked",
        patient_ref=str(pt_key),
        payload={
            "adapter": "delete_contact_from_ptcn",
            "args": [str(pt_key), firmante.nombre_completo],
            "kwargs": {},
        },
    )
    if not created:
        return _existing_sync_response(operation)

    firmante.estado = "REVOCADO"
    firmante.fmd_template = None
    firmante.huella_token = None
    firmante.biometric_status = "SIN_BIOMETRIA"
    firmante.template_format = None
    firmante.template_version = None
    firmante.requiere_reenrolamiento = False
    firmante.fecha_inactivacion = datetime.datetime.utcnow()
    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")
    firmante.inactivado_por_usuario_id = None if is_medico else getattr(current_user, "id", None)

    db.commit()

    clinical_sync.mark_local_applied(db, operation)
    result = clinical_sync.execute_external(
        db, operation, clinical_sync_adapters.dispatcher(operation), session_factory=SessionLocal
    )
    return _sync_result_response(
        result,
        {"message": f"Firmante {firmante.nombre_completo} revocado e inactivado exitosamente"},
    )




# --- Médicos ---

@app.get("/api/medicos", response_model=List[schemas.MedicoResponse])

def get_medicos(db: Session = Depends(get_db)):

    return db.query(models.Medico).filter(models.Medico.activo_status == True).all()



@app.post("/api/medicos", response_model=schemas.MedicoResponse)

async def create_medico(

    numero_empleado: str = Form(...),

    nombre_completo: str = Form(...),

    especialidad: str = Form(...),

    cedula: str = Form(...),

    fmd_template: Optional[str] = Form(None),

    foto: Optional[UploadFile] = File(None),

    bajo_contrato: bool = Form(False),

    horario_laboral: Optional[str] = Form(None),

    es_ayudante: bool = Form(False),

    medico_asignado_id: Optional[int] = Form(None),

    db: Session = Depends(get_db),

    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))

):

    # Ya no se genera numero empleado automáticamente

    if fmd_template and fmd_template.strip():

        raise HTTPException(
            status_code=422,
            detail="La biometría no se acepta al crear al médico; use el endpoint explícito de enrolamiento.",
        )

    if db.query(models.Medico).filter(models.Medico.numero_empleado == numero_empleado).first():

        raise HTTPException(status_code=400, detail="Ya existe un médico con ese número de empleado.")

    if db.query(models.Medico).filter(models.Medico.cedula == cedula).first():

        raise HTTPException(status_code=400, detail="Ya existe un médico con esa cédula.")

    

    huella_token_unique = str(uuid.uuid4())

    

    foto_url = None

    if foto:
        photo = file_storage.validate_photo(await file_storage.read_limited(foto, file_storage.PHOTO_LIMIT))
        filename, _ = file_storage.store_private(PRIVATE_STORAGE_ROOT, "photos", photo)
        foto_url = f"/api/files/photos/{filename}"



    nuevo_medico = models.Medico(

        numero_empleado=numero_empleado,

        nombre_completo=nombre_completo,

        especialidad=especialidad,

        cedula=cedula,

        huella_token=huella_token_unique,

        fmd_template=None,

        biometric_status="SIN_BIOMETRIA",

        foto_url=foto_url,

        bajo_contrato=bajo_contrato,

        horario_laboral=horario_laboral,

        es_ayudante=es_ayudante,

        medico_asignado_id=medico_asignado_id

    )

    db.add(nuevo_medico)
    log_auditoria(
        db,
        current_user.id,
        "MEDICO_CREADO",
        json.dumps({"numero_empleado": numero_empleado, "cedula": cedula}),
    )
    db.commit()

    db.refresh(nuevo_medico)

    return nuevo_medico



# --- Atenciones ---

@app.post("/api/atenciones/pre-captura", response_model=schemas.AtencionResponse)

def pre_captura(req: schemas.PreCapturaRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):

    hoy = datetime.date.today()

    

    if getattr(current_user, "rol", "") not in ("sistemas", "admin"):

        if req.fecha_realizacion:

            req.fecha_realizacion = datetime.datetime.combine(hoy, req.fecha_realizacion.time())

        else:

            req.fecha_realizacion = datetime.datetime.now()

    # Admin/sistemas: pueden elegir cualquier fecha sin restricción

    

    dias_semana = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

    

    rol_usuario = getattr(current_user, "rol", "")

    medico = db.query(models.Medico).filter(models.Medico.id == req.medico_id).first()

    if medico and medico.bajo_contrato and medico.horario_laboral and rol_usuario not in ("sistemas", "admin"):

        try:

            horario = json.loads(medico.horario_laboral)

            def is_in_shift(dt_to_check):

                hora_str = dt_to_check.strftime("%H:%M")

                dia_idx = dt_to_check.weekday()

                dia_actual = dias_semana[dia_idx]

                dia_previo = dias_semana[(dia_idx - 1) % 7]

                

                # Check today's shift

                shift_hoy = horario.get(dia_actual)

                if shift_hoy and shift_hoy.get("activo"):

                    inicio = shift_hoy.get("inicio", "")

                    fin = shift_hoy.get("fin", "")

                    if inicio and fin:

                        if inicio <= fin:

                            if inicio <= hora_str <= fin:

                                return True

                        else:

                            if hora_str >= inicio:

                                return True

                

                # Check yesterday's shift for overnight

                shift_ayer = horario.get(dia_previo)

                if shift_ayer and shift_ayer.get("activo"):

                    inicio = shift_ayer.get("inicio", "")

                    fin = shift_ayer.get("fin", "")

                    if inicio and fin and inicio > fin:

                        if hora_str <= fin:

                            return True

                return False



            dt_sistema = datetime.datetime.now()

            dt_registro = req.fecha_realizacion or dt_sistema

            

            if is_in_shift(dt_sistema):

                raise HTTPException(status_code=400, detail="El médico está actualmente dentro de su jornada laboral base. No puede realizar registros.")

                

            if is_in_shift(dt_registro):

                raise HTTPException(status_code=400, detail="La hora reportada del procedimiento cae dentro de la jornada laboral del médico. Solo puede registrar procedimientos realizados fuera de turno.")

        except Exception as e:

            if isinstance(e, HTTPException): raise e

            pass # Ignore JSON parsing errors

            

    # One record per patient per day per doctor

    exact_match = db.query(models.AtencionMedica).filter(

        models.AtencionMedica.paciente_id == req.paciente_id,

        models.AtencionMedica.medico_id == req.medico_id,

        func.date(models.AtencionMedica.fecha_realizacion) == (req.fecha_realizacion.date() if req.fecha_realizacion else hoy)

    ).first()

    

    nuevo_estatus_pago = "Pendiente de Firma"

    if exact_match:

        nuevo_estatus_pago = "Pendiente Autorización"

    

    # Use max folio number instead of count to avoid collisions after cleanup

    from sqlalchemy import text

    max_row = db.execute(text("SELECT MAX(CAST(SUBSTR(folio, 10) AS INTEGER)) FROM atenciones_medicas")).fetchone()

    next_num = (max_row[0] or 0) + 1

    year = datetime.date.today().year

    folio = f"HES-{year}-{next_num:05d}"

    

    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")

    

    registrado_por = None

    if is_medico:

        medico_db = db.query(models.Medico).filter(models.Medico.id == current_user.id).first()

        if medico_db:

            if medico_db.es_ayudante:

                med_titular = db.query(models.Medico).filter(models.Medico.id == medico_db.medico_asignado_id).first()

                titular_nombre = med_titular.nombre_completo if med_titular else "Desconocido"

                registrado_por = f"{medico_db.nombre_completo} (Ayudante del Dr. {titular_nombre})"

            else:

                registrado_por = f"Dr. {medico_db.nombre_completo}"

    else:

        registrado_por = current_user.nombre_completo or current_user.username

    

    paciente_db = db.query(models.Paciente).filter(models.Paciente.id == req.paciente_id).first()

    area_hosp = req.area_hospitalaria or (paciente_db.area_hospitalaria if paciente_db else "No asignada")

    

    nueva_atencion = models.AtencionMedica(

        folio=folio,

        fecha_realizacion=req.fecha_realizacion,

        medico_id=req.medico_id,

        paciente_id=req.paciente_id,

        area_hospitalaria=area_hosp,

        tipo_atencion=req.tipo_atencion,

        nombre_procedimiento=req.nombre_procedimiento,

        habitacion_capturada=req.habitacion_capturada,

        procedimiento_detalle=req.procedimiento_detalle,

        creado_por_id=None if is_medico else current_user.id,

        estatus_pago=nuevo_estatus_pago,

        registrado_por_nombre=registrado_por

    )

    

    db.add(nueva_atencion)

    

    # Update frequent procedures

    proc_frec = db.query(models.ProcedimientoFrecuente).filter(

        models.ProcedimientoFrecuente.medico_id == req.medico_id,

        func.lower(models.ProcedimientoFrecuente.nombre_procedimiento) == req.nombre_procedimiento.lower().strip()

    ).first()

    

    if proc_frec:

        proc_frec.frecuencia += 1

    else:

        nuevo_proc = models.ProcedimientoFrecuente(

            medico_id=req.medico_id,

            nombre_procedimiento=req.nombre_procedimiento.strip(),

            frecuencia=1

        )

        db.add(nuevo_proc)

        

    db.commit()

    db.refresh(nueva_atencion)

    return nueva_atencion



@app.get("/api/medicos/{medico_id}/procedimientos_frecuentes")

def get_procedimientos_frecuentes(medico_id: int, db: Session = Depends(get_db)):

    """Obtiene el top 5 de procedimientos más usados por este médico"""

    procs = db.query(models.ProcedimientoFrecuente).filter(

        models.ProcedimientoFrecuente.medico_id == medico_id

    ).order_by(models.ProcedimientoFrecuente.frecuencia.desc()).limit(5).all()

    

    return [{"nombre": p.nombre_procedimiento, "frecuencia": p.frecuencia} for p in procs]



@app.get("/api/atenciones/pendientes/{medico_id}", response_model=List[schemas.AtencionResponse])

def pendientes_medico(medico_id: int, db: Session = Depends(get_db)):

    return db.query(models.AtencionMedica).filter(

        models.AtencionMedica.medico_id == medico_id,

        models.AtencionMedica.estatus_pago == "Pendiente de Firma"

    ).all()



@app.get("/api/atenciones/historial/{medico_id}", response_model=List[schemas.AtencionResponse])

def historial_medico(medico_id: int, db: Session = Depends(get_db)):

    return db.query(models.AtencionMedica).filter(

        models.AtencionMedica.medico_id == medico_id,

        models.AtencionMedica.estatus_pago != "Pendiente de Firma"

    ).order_by(models.AtencionMedica.fecha_firma.desc()).all()



@app.get("/api/atenciones/mis-registros", response_model=List[schemas.AtencionResponse])

def mis_registros(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):

    return db.query(models.AtencionMedica).filter(models.AtencionMedica.creado_por_id == current_user.id).order_by(models.AtencionMedica.fecha_registro.desc()).all()



@app.get("/api/atenciones/global", response_model=List[schemas.AtencionResponse])

def global_registros(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):

    return db.query(models.AtencionMedica).order_by(models.AtencionMedica.fecha_registro.desc()).all()



@app.get("/api/atenciones/todas", response_model=List[schemas.AtencionResponse])

def get_todas_atenciones(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):

    return db.query(models.AtencionMedica).order_by(models.AtencionMedica.fecha_realizacion.desc()).all()



@app.get("/api/atenciones/exportar")

def exportar_atenciones(

    start_date: Optional[str] = None,

    end_date: Optional[str] = None,

    db: Session = Depends(get_db), 

    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))

):

    query = db.query(models.AtencionMedica)

    

    if start_date:

        query = query.filter(func.date(models.AtencionMedica.fecha_realizacion) >= start_date)

    if end_date:

        query = query.filter(func.date(models.AtencionMedica.fecha_realizacion) <= end_date)

        

    atenciones = query.order_by(models.AtencionMedica.fecha_realizacion.desc()).all()

    wb = Workbook()

    ws = wb.active

    ws.title = "Atenciones"

    

    # Insertar Logo

    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist", "logo.png")

    if not os.path.exists(logo_path):

        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "public", "logo.png")

    if os.path.exists(logo_path):

        img = ExcelImage(logo_path)

        img.width = 100

        img.height = 35

        ws.add_image(img, "A1")

        

    # Metadata Header

    ws.merge_cells("C1:G1")

    ws["C1"] = "HOSPITAL ESCANDÓN - REPORTE DE ATENCIONES MÉDICAS"

    ws["C1"].font = Font(bold=True, size=14, color="003870")

    ws["C1"].alignment = Alignment(horizontal="center", vertical="center")

    

    ws["I1"] = "Generado por:"

    ws["I1"].font = Font(bold=True)

    ws["J1"] = current_user.username

    ws["I2"] = "Fecha:"

    ws["I2"].font = Font(bold=True)

    ws["J2"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    

    # Headers

    headers = ["Folio", "Fecha Realización", "Médico", "Especialidad", "Paciente", "Habitación", "Área Hospitalaria", "Tipo Atención", "Procedimiento", "Estatus Pago", "Fecha Firma", "Hash"]

    header_fill = PatternFill(start_color="003870", end_color="003870", fill_type="solid")

    header_font = Font(color="FFFFFF", bold=True)

    

    for col_num, header in enumerate(headers, 1):

        cell = ws.cell(row=4, column=col_num, value=header)

        cell.fill = header_fill

        cell.font = header_font

        cell.alignment = Alignment(horizontal="center")

        

    row_idx = 5

    for a in atenciones:

        medico_nombre = a.medico.nombre_completo if a.medico else "N/A"

        medico_esp = a.medico.especialidad if a.medico else "N/A"

        paciente_nombre = a.paciente.nombre_completo if a.paciente else "N/A"

        f_firma = a.fecha_firma.strftime("%Y-%m-%d %H:%M:%S") if a.fecha_firma else ""

        

        ws.cell(row=row_idx, column=1, value=a.folio)

        ws.cell(row=row_idx, column=2, value=a.fecha_realizacion.strftime("%Y-%m-%d %H:%M:%S") if a.fecha_realizacion else "")

        ws.cell(row=row_idx, column=3, value=medico_nombre)

        ws.cell(row=row_idx, column=4, value=medico_esp)

        ws.cell(row=row_idx, column=5, value=paciente_nombre)

        ws.cell(row=row_idx, column=6, value=a.habitacion_capturada)

        ws.cell(row=row_idx, column=7, value=a.area_hospitalaria)

        ws.cell(row=row_idx, column=8, value=a.tipo_atencion)

        ws.cell(row=row_idx, column=9, value=a.nombre_procedimiento)

        ws.cell(row=row_idx, column=10, value=a.estatus_pago)

        ws.cell(row=row_idx, column=11, value=f_firma)

        ws.cell(row=row_idx, column=12, value=a.hash_seguridad or "")

        row_idx += 1

        

    from openpyxl.utils import get_column_letter

    for col_idx in range(1, ws.max_column + 1):

        column = get_column_letter(col_idx)

        max_length = 0

        for cell in ws[column]:

            try:

                if len(str(cell.value)) > max_length:

                    max_length = len(str(cell.value))

            except:

                pass

        adjusted_width = (max_length + 2)

        ws.column_dimensions[column].width = adjusted_width if adjusted_width < 50 else 50

        

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    

    response = StreamingResponse(iter([output.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    response.headers["Content-Disposition"] = "attachment; filename=atenciones_export.xlsx"

    return response



@app.post("/api/atenciones/firmar-lote")
def firmar_lote(req: schemas.FirmaLoteRequest, request: Request, db: Session = Depends(get_db)):
    if not req.fmd_template:
        raise HTTPException(status_code=400, detail="No se recibió la huella dactilar (FMD).")

    match_found = verificar_huella_medico(
        db=db,
        fmd_template=req.fmd_template,
        medico_id=req.medico_id,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="FIRMA_LOTE",
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=_biometric_identity_from_request(request),
    )
    _assert_fea_enabled(match_found)

    firmados = []

    ahora = datetime.datetime.utcnow()

    

    for folio in req.folios:

        atencion = db.query(models.AtencionMedica).filter(

            models.AtencionMedica.folio == folio,

            models.AtencionMedica.medico_id == match_found.id

        ).first()

        

        if atencion:

            if atencion.is_caducado:

                continue # No se puede firmar registro caducado

            paciente = db.query(models.Paciente).filter(models.Paciente.id == atencion.paciente_id).first()

            raw_text = f"{atencion.folio}{atencion.fecha_realizacion.isoformat()}{match_found.nombre_completo}{paciente.nombre_completo}{atencion.habitacion_capturada}"

            hash_str = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()

            

            atencion.hash_seguridad = hash_str

            atencion.estatus_pago = "Validado para Pago"

            atencion.fecha_firma = ahora

            

            # Generar PDF

            try:

                pdf_path = generate_pdf(atencion, match_found, paciente)

                atencion.ruta_archivo_firmado = pdf_path

            except Exception as e:

                print("Error al generar PDF:", e)

                

            firmados.append(folio)

            

    db.commit()

    return {"message": f"{len(firmados)} atenciones firmadas", "firmados": firmados}



@app.put("/api/atenciones/{folio}")

def update_atencion(folio: str, tipo_atencion: str, db: Session = Depends(get_db)):

    atencion = db.query(models.AtencionMedica).filter(models.AtencionMedica.folio == folio).first()

    if not atencion:

        raise HTTPException(status_code=404, detail="Atención no encontrada")

    atencion.tipo_atencion = tipo_atencion

    db.commit()

    return {"message": "Actualizado"}



@app.get("/api/atenciones/{folio}/pdf")
def generar_comprobante_pdf(folio: str, db: Session = Depends(get_db)):
    atencion = db.query(models.AtencionMedica).filter(models.AtencionMedica.folio == folio).first()
    if not atencion:
        raise HTTPException(status_code=404, detail="Atención no encontrada")
        
    pdf_rel_path = generate_pdf(atencion, atencion.medico, atencion.paciente)
    pdf_full_path = os.path.join(os.path.dirname(__file__), "static", "pdfs", f"{folio}.pdf")
    
    if not os.path.exists(pdf_full_path):
        raise HTTPException(status_code=500, detail="Error al generar el comprobante PDF")
        
    return FileResponse(pdf_full_path, media_type="application/pdf", filename=f"Comprobante_{folio}.pdf")



# === ENDPOINTS RH ===

@app.get("/api/usuarios", response_model=List[schemas.UsuarioResponse])

def get_usuarios(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):

    return db.query(models.Usuario).all()



@app.post("/api/usuarios", response_model=schemas.UsuarioResponse)

def create_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):

    _validate_new_password(usuario.password)
    validate_assignments(normalize_role(usuario.rol), usuario.permisos_modulos, usuario.formatos_permitidos, usuario.formatos_firma_permitidos)
    usuario.rol = normalize_role(usuario.rol)
    existing = db.query(models.Usuario).filter(models.Usuario.username == usuario.username).first()

    if existing:

        raise HTTPException(status_code=400, detail="Usuario ya existe")

    nuevo_usuario = models.Usuario(

        username=usuario.username,

        password_hash=pwd_context.hash(usuario.password),

        rol=usuario.rol,

        nombre_completo=usuario.nombre_completo,

        permisos_modulos=usuario.permisos_modulos,

        formatos_permitidos=usuario.formatos_permitidos if usuario.formatos_permitidos is not None else "[]",
        formatos_firma_permitidos=usuario.formatos_firma_permitidos if usuario.formatos_firma_permitidos is not None else "[]"

    )

    db.add(nuevo_usuario)
    db.flush()
    log_auditoria(
        db,
        current_user.id,
        "USUARIO_CREADO",
        json.dumps({"usuario_id": nuevo_usuario.id, "username": nuevo_usuario.username, "rol": nuevo_usuario.rol}),
    )
    db.commit()

    db.refresh(nuevo_usuario)

    return nuevo_usuario



@app.put("/api/usuarios/{usuario_id}", response_model=schemas.UsuarioResponse)

def update_usuario(usuario_id: int, payload: schemas.UsuarioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))):

    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

    if not usuario:

        raise HTTPException(status_code=404, detail="Usuario no encontrado")

        

    validate_assignments(
        normalize_role(payload.rol or usuario.rol), payload.permisos_modulos,
        payload.formatos_permitidos if payload.formatos_permitidos is not None else usuario.formatos_permitidos,
        payload.formatos_firma_permitidos if payload.formatos_firma_permitidos is not None else usuario.formatos_firma_permitidos,
    )
    previous = {
        "rol": usuario.rol,
        "nombre_completo": usuario.nombre_completo,
        "permisos_modulos": usuario.permisos_modulos,
        "formatos_permitidos": usuario.formatos_permitidos,
        "formatos_firma_permitidos": usuario.formatos_firma_permitidos,
    }
    if payload.rol is not None:

        usuario.rol = normalize_role(payload.rol)

    if payload.nombre_completo is not None:

        usuario.nombre_completo = payload.nombre_completo

    if payload.permisos_modulos is not None:

        usuario.permisos_modulos = payload.permisos_modulos

    if payload.formatos_permitidos is not None:

        usuario.formatos_permitidos = payload.formatos_permitidos

    if payload.formatos_firma_permitidos is not None:

        usuario.formatos_firma_permitidos = payload.formatos_firma_permitidos

        

    current = {
        "rol": usuario.rol,
        "nombre_completo": usuario.nombre_completo,
        "permisos_modulos": usuario.permisos_modulos,
        "formatos_permitidos": usuario.formatos_permitidos,
        "formatos_firma_permitidos": usuario.formatos_firma_permitidos,
    }
    log_auditoria(
        db,
        current_user.id,
        "USUARIO_ACTUALIZADO",
        json.dumps({"usuario_id": usuario.id, "antes": previous, "despues": current}, ensure_ascii=False),
    )
    db.commit()

    db.refresh(usuario)

    return usuario



@app.put("/api/usuarios/{usuario_id}/password")

def update_usuario_password(usuario_id: int, payload: schemas.UsuarioPasswordUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))):

    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

    if not usuario:

        raise HTTPException(status_code=404, detail="Usuario no encontrado")

        

    _validate_new_password(payload.new_password)
    usuario.password_hash = pwd_context.hash(payload.new_password)
    usuario.must_change_password = True
    log_auditoria(
        db,
        current_user.id,
        "CONTRASENA_USUARIO_RESTABLECIDA",
        json.dumps({"usuario_id": usuario.id, "must_change_password": True}),
    )
    db.commit()

    return {"message": "Contraseña actualizada exitosamente"}


def _validate_new_password(password: str) -> None:
    if not valid_password(password):
        raise HTTPException(status_code=422, detail=PASSWORD_MESSAGE)


@app.post("/api/auth/change-password")
def change_own_password(
    payload: schemas.UsuarioSelfPasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if normalize_role(getattr(current_user, "rol", "")) in {"medico", "ayudante"}:
        raise HTTPException(status_code=403, detail="Este tipo de identidad no usa contraseña local.")
    if not pwd_context.verify(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="La contraseña actual es incorrecta.")
    _validate_new_password(payload.new_password)
    if pwd_context.verify(payload.new_password, current_user.password_hash):
        raise HTTPException(status_code=422, detail="La nueva contraseña debe ser distinta.")
    current_user.password_hash = pwd_context.hash(payload.new_password)
    current_user.must_change_password = False
    db.add(models.AuditoriaLog(
        usuario_id=current_user.id,
        accion="CAMBIO_CONTRASENA_PROPIA",
        detalles_json=json.dumps({"forced_change_completed": True}),
        ip_origen=request.client.host if request.client else None,
        resultado="EXITO",
    ))
    db.commit()
    return {"success": True, "message": "Contraseña actualizada. Inicie sesión nuevamente."}



@app.delete("/api/usuarios/{usuario_id}")

def delete_usuario(usuario_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["sistemas"]))):

    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

    if not usuario:

        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario.username == current_user.username:

        raise HTTPException(status_code=400, detail="No te puedes eliminar a ti mismo")

    log_auditoria(
        db,
        current_user.id,
        "USUARIO_ELIMINADO",
        json.dumps({"usuario_id": usuario.id, "username": usuario.username, "rol": usuario.rol}, ensure_ascii=False),
    )
    db.delete(usuario)

    db.commit()

    return {"message": "Usuario eliminado"}



@app.put("/api/medicos/{medico_id}")

def update_medico(medico_id: int, activo: bool, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):

    medico = db.query(models.Medico).filter(models.Medico.id == medico_id).first()

    medico.activo_status = activo
    log_auditoria(
        db,
        current_user.id,
        "ESTADO_MEDICO_ACTUALIZADO",
        json.dumps({"medico_id": medico.id, "activo": activo}),
    )
    db.commit()

    return {"message": "Actualizado"}



@app.put("/api/medicos/{medico_id}/permisos", response_model=schemas.MedicoResponse)

def update_medico_permisos(medico_id: int, payload: schemas.MedicoUpdatePermisos, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))):

    medico = db.query(models.Medico).filter(models.Medico.id == medico_id).first()

    if not medico:

        raise HTTPException(status_code=404, detail="Médico no encontrado")

        

    validate_assignments(current_user.rol, None, payload.formatos_permitidos)
    previous_permissions = medico.formatos_permitidos
    medico.formatos_permitidos = payload.formatos_permitidos
    log_auditoria(
        db,
        current_user.id,
        "PERMISOS_MEDICO_ACTUALIZADOS",
        json.dumps({"medico_id": medico.id, "antes": previous_permissions, "despues": medico.formatos_permitidos}, ensure_ascii=False),
    )
    db.commit()

    db.refresh(medico)

    return medico



@app.put("/api/medicos/{medico_id}/datos", response_model=schemas.MedicoResponse)

async def update_medico_datos(

    medico_id: int,

    numero_empleado: str = Form(...),

    nombre_completo: str = Form(...),

    especialidad: str = Form(...),

    cedula: str = Form(...),

    foto: Optional[UploadFile] = File(None),

    bajo_contrato: bool = Form(False),

    horario_laboral: Optional[str] = Form(None),

    es_ayudante: bool = Form(False),

    medico_asignado_id: Optional[int] = Form(None),

    formatos_permitidos: Optional[str] = Form(None),

    db: Session = Depends(get_db),

    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))

):

    medico = db.query(models.Medico).filter(models.Medico.id == medico_id).first()

    if not medico:

        raise HTTPException(status_code=404, detail="Médico no encontrado")

        

    medico.numero_empleado = numero_empleado

    medico.nombre_completo = nombre_completo

    medico.especialidad = especialidad

    medico.cedula = cedula

    medico.bajo_contrato = bajo_contrato

    medico.horario_laboral = horario_laboral

    medico.es_ayudante = es_ayudante

    medico.medico_asignado_id = medico_asignado_id

    if formatos_permitidos is not None:
        if not has_module(current_user, "usuarios", write=True):
            raise HTTPException(403, "Sólo la gestión de usuarios puede asignar formatos.")
        validate_assignments(current_user.rol, None, formatos_permitidos)
        medico.formatos_permitidos = formatos_permitidos

    

    if foto:
        photo = file_storage.validate_photo(await file_storage.read_limited(foto, file_storage.PHOTO_LIMIT))
        filename, _ = file_storage.store_private(PRIVATE_STORAGE_ROOT, "photos", photo)
        medico.foto_url = f"/api/files/photos/{filename}"

    log_auditoria(
        db,
        current_user.id,
        "DATOS_MEDICO_ACTUALIZADOS",
        json.dumps({"medico_id": medico.id, "numero_empleado": medico.numero_empleado, "cedula": medico.cedula}),
    )
    db.commit()

    db.refresh(medico)

    return medico



@app.put("/api/medicos/{medico_id}/huella", response_model=schemas.MedicoResponse)

def update_medico_huella(

    medico_id: int,

    fmd_template: str = Form(...),

    db: Session = Depends(get_db),

    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))

):
    raise HTTPException(
        status_code=410,
        detail="Endpoint retirado: use enrolamiento o reenrolamiento biométrico explícito y auditado.",
    )


def _enrolar_medico_controlado(
    *,
    medico_id: int,
    req: schemas.BiometricEnrollmentRequest,
    request: Request,
    db: Session,
    current_user: models.Usuario,
    reenrolamiento: bool,
):
    medico = db.query(models.Medico).filter(
        models.Medico.id == medico_id,
        models.Medico.activo_status == True,
    ).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico activo no encontrado")
    if reenrolamiento and not (req.motivo or "").strip():
        raise HTTPException(status_code=422, detail="El motivo de reenrolamiento es obligatorio.")
    if not reenrolamiento and medico.biometric_status != "SIN_BIOMETRIA":
        raise HTTPException(status_code=409, detail="El médico ya tiene biometría; use reenrolamiento explícito.")

    action = "REENROLAMIENTO_MEDICO" if reenrolamiento else "ENROLAMIENTO_MEDICO"
    capture = biometric_security.validate_attested_capture_evidence(
        req.fmd_template, req.challenge_id, req.session_id
    )
    validate_and_consume_challenge(
        db,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action=action,
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=f"medico:{medico_id}",
        document_ref=str(medico_id),
        acquisition=capture,
    )
    canonical = capture.canonical
    medico.fmd_template = canonical
    medico.huella_token = medico.huella_token or str(uuid.uuid4())
    medico.biometric_status = "FMD_VALIDO"
    medico.template_format = biometric_security.TEMPLATE_FORMAT
    medico.template_version = biometric_security.TEMPLATE_VERSION
    medico.fecha_enrolamiento = datetime.datetime.utcnow()
    medico.requiere_reenrolamiento = False
    if reenrolamiento:
        # La llave existente queda intacta pero inutilizable hasta el Bloque B.
        medico.requiere_actualizacion_fea = True
        medico.biometric_reenrolled_by_id = current_user.id
        medico.biometric_reenrolled_at = datetime.datetime.utcnow()
    db.add(
        models.AuditoriaLog(
            usuario_id=current_user.id,
            accion=action,
            detalles_json=json.dumps(
                {
                    "medico_id": medico.id,
                    "motivo": (req.motivo or "ENROLAMIENTO_INICIAL").strip(),
                    "template_format": biometric_security.TEMPLATE_FORMAT,
                    "firma_fea_bloqueada": bool(medico.requiere_actualizacion_fea),
                }
            ),
            ip_origen=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(medico)
    return medico


@app.post("/api/medicos/{medico_id}/biometria/enrolar", response_model=schemas.MedicoResponse)
def enrolar_medico(
    medico_id: int,
    req: schemas.BiometricEnrollmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"])),
):
    return _enrolar_medico_controlado(
        medico_id=medico_id,
        req=req,
        request=request,
        db=db,
        current_user=current_user,
        reenrolamiento=False,
    )


@app.post("/api/medicos/{medico_id}/biometria/reenrolar", response_model=schemas.MedicoResponse)
def reenrolar_medico(
    medico_id: int,
    req: schemas.BiometricEnrollmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"])),
):
    return _enrolar_medico_controlado(
        medico_id=medico_id,
        req=req,
        request=request,
        db=db,
        current_user=current_user,
        reenrolamiento=True,
    )


def _enrolar_usuario_biometria_controlado(
    *, usuario_id: int, req: schemas.BiometricEnrollmentRequest, request: Request,
    db: Session, current_user: models.Usuario, reenrolamiento: bool,
):
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id,
        models.Usuario.activo == True,
    ).first()
    if not usuario:
        raise HTTPException(404, "No se encontró una cuenta activa.")
    if reenrolamiento and not (req.motivo or "").strip():
        raise HTTPException(422, "El motivo de reenrolamiento es obligatorio.")
    if not reenrolamiento and usuario.biometric_status != "SIN_BIOMETRIA":
        raise HTTPException(409, "Esta cuenta ya tiene biometría; use el reenrolamiento explícito.")
    if reenrolamiento and usuario.biometric_status == "SIN_BIOMETRIA":
        raise HTTPException(409, "Esta cuenta no tiene una huella que reenrolar.")

    action = "REENROLAMIENTO_USUARIO" if reenrolamiento else "ENROLAMIENTO_USUARIO"
    capture = biometric_security.validate_attested_capture_evidence(
        req.fmd_template, req.challenge_id, req.session_id,
    )
    validate_and_consume_challenge(
        db,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action=action,
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=f"usuario:{usuario_id}",
        document_ref=str(usuario_id),
        acquisition=capture,
    )
    db.execute(sql_text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {
        "key": f"biometric-user|{usuario_id}",
    })
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id,
        models.Usuario.activo == True,
    ).with_for_update().first()
    if not usuario:
        raise HTTPException(409, "La cuenta cambió durante el enrolamiento.")
    if not reenrolamiento and usuario.biometric_status != "SIN_BIOMETRIA":
        raise HTTPException(409, "La cuenta ya tiene una huella registrada; inicie reenrolamiento explícito.")
    if reenrolamiento and usuario.biometric_status == "SIN_BIOMETRIA":
        raise HTTPException(409, "La huella de la cuenta cambió durante el reenrolamiento.")
    usuario.fmd_template = capture.canonical
    usuario.biometric_status = "FMD_VALIDO"
    usuario.template_format = biometric_security.TEMPLATE_FORMAT
    usuario.template_version = biometric_security.TEMPLATE_VERSION
    usuario.fecha_enrolamiento = datetime.datetime.utcnow()
    usuario.biometric_updated_by_id = current_user.id
    db.add(models.AuditoriaLog(
        usuario_id=current_user.id,
        accion=action,
        detalles_json=json.dumps({
            "usuario_id": usuario.id,
            "rol": usuario.rol,
            "motivo": (req.motivo or "ENROLAMIENTO_INICIAL").strip(),
            "template_format": biometric_security.TEMPLATE_FORMAT,
        }, ensure_ascii=False),
        ip_origen=request.client.host if request.client else None,
    ))
    db.commit()
    db.refresh(usuario)
    return usuario


@app.post("/api/usuarios/{usuario_id}/biometria/enrolar", response_model=schemas.UsuarioResponse)
def enrolar_usuario_biometria(
    usuario_id: int,
    req: schemas.BiometricEnrollmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "sistemas"])),
):
    return _enrolar_usuario_biometria_controlado(
        usuario_id=usuario_id, req=req, request=request, db=db,
        current_user=current_user, reenrolamiento=False,
    )


@app.post("/api/usuarios/{usuario_id}/biometria/reenrolar", response_model=schemas.UsuarioResponse)
def reenrolar_usuario_biometria(
    usuario_id: int,
    req: schemas.BiometricEnrollmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "sistemas"])),
):
    return _enrolar_usuario_biometria_controlado(
        usuario_id=usuario_id, req=req, request=request, db=db,
        current_user=current_user, reenrolamiento=True,
    )


@app.post("/api/medicos/{medico_id}/fea/completar-actualizacion")
def completar_actualizacion_fea(
    medico_id: int,
    req: schemas.FEAKeyRotationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"])),
):
    """Complete the explicit post-reenrollment FEA key ceremony."""
    medico = db.query(models.Medico).filter(
        models.Medico.id == medico_id,
        models.Medico.activo_status == True,
    ).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico activo no encontrado")
    if not medico.requiere_actualizacion_fea:
        raise HTTPException(status_code=409, detail="El médico no tiene una actualización FEA pendiente")
    if not req.motivo.strip():
        raise HTTPException(status_code=422, detail="El motivo de rotación FEA es obligatorio")
    if medico.biometric_reenrolled_by_id is None:
        raise HTTPException(
            status_code=409,
            detail="No existe evidencia de la ceremonia administrativa de reenrolamiento.",
        )
    if medico.biometric_reenrolled_by_id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Separación de funciones: quien reenroló la biometría no puede aprobar la rotación FEA.",
        )

    verified = verificar_huella_medico(
        db=db,
        fmd_template=req.fmd_template,
        medico_id=medico_id,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="ACTUALIZACION_FEA",
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=f"medico:{medico_id}",
        document_ref=str(medico_id),
    )
    if verified.id != medico.id:
        raise HTTPException(status_code=403, detail="La biometría no corresponde al médico")
    try:
        new_key_id = crypto_fea.rotate_medico_key(
            db,
            medico,
            motivo=req.motivo,
            actor_id=current_user.id,
        )
        medico.biometric_reenrolled_by_id = None
        medico.biometric_reenrolled_at = None
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "success": True,
        "medico_id": medico.id,
        "key_id": new_key_id,
        "requiere_actualizacion_fea": False,
        "estado": "ROTACION_FEA_COMPLETADA",
    }



# === ESCANEOS RH ===

ESCANEOS_DIR = os.path.join(PRIVATE_STORAGE_ROOT, "escaneos_rh")

os.makedirs(ESCANEOS_DIR, exist_ok=True)



@app.get("/api/escaneos", response_model=List[schemas.EscaneoRHResponse])

def get_escaneos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):
    escaneos = db.query(models.EscaneoRH).order_by(models.EscaneoRH.fecha_subida.desc()).all()
    for escaneo in escaneos:
        # La ruta física permanece privada; el cliente recibe el controlador RBAC.
        escaneo.ruta_archivo = f"/api/escaneos/{escaneo.id}/archivo"
    return escaneos


@app.get("/api/escaneos/{escaneo_id}/archivo")
def download_escaneo(
    escaneo_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"])),
):
    escaneo = db.query(models.EscaneoRH).filter(models.EscaneoRH.id == escaneo_id).first()
    if not escaneo:
        raise HTTPException(status_code=404, detail="Escaneo no encontrado")

    stored_name = os.path.basename(escaneo.ruta_archivo or "")
    try:
        file_path = file_storage.resolve_private(PRIVATE_STORAGE_ROOT, "escaneos_rh", stored_name)
    except HTTPException as private_error:
        # Read-only compatibility for historical files; all new files use private_storage.
        legacy_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "static", "escaneos_rh"))
        legacy_path = os.path.realpath(os.path.join(legacy_root, stored_name))
        if not stored_name or os.path.commonpath([legacy_root, legacy_path]) != legacy_root or not os.path.isfile(legacy_path):
            raise private_error
        file_path = legacy_path

    return FileResponse(
        file_path,
        filename=escaneo.nombre_archivo,
        media_type="application/octet-stream",
        content_disposition_type="attachment",
    )



@app.post("/api/escaneos", response_model=schemas.EscaneoRHResponse)

async def upload_escaneo(

    titulo: str = Form(...),

    archivo: UploadFile = File(...),

    db: Session = Depends(get_db),

    current_user: models.Usuario = Depends(require_role(["admin", "rh"]))

):

    contents = await file_storage.read_limited(archivo, file_storage.DOCUMENT_LIMIT)
    validated = file_storage.validate_document(contents)
    unique_filename, _ = file_storage.store_private(PRIVATE_STORAGE_ROOT, "escaneos_rh", validated)
    ruta_archivo = unique_filename

    

    nuevo_escaneo = models.EscaneoRH(

        titulo=titulo,

        nombre_archivo=os.path.basename(archivo.filename or f"documento{validated.extension}"),

        ruta_archivo=ruta_archivo,

        subido_por_id=current_user.id

    )

    db.add(nuevo_escaneo)

    db.commit()

    db.refresh(nuevo_escaneo)

    nuevo_escaneo.ruta_archivo = f"/api/escaneos/{nuevo_escaneo.id}/archivo"

    return nuevo_escaneo


@app.get("/api/files/photos/{filename}")
def download_profile_photo(filename: str, current_user=Depends(get_current_user)):
    path = file_storage.resolve_private(PRIVATE_STORAGE_ROOT, "photos", filename)
    media_type = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return FileResponse(path, media_type=media_type, filename=os.path.basename(path), content_disposition_type="inline")



@app.put("/api/escaneos/{escaneo_id}", response_model=schemas.EscaneoRHResponse)

def rename_escaneo(escaneo_id: int, req: schemas.EscaneoRHUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh"]))):

    escaneo = db.query(models.EscaneoRH).filter(models.EscaneoRH.id == escaneo_id).first()

    if not escaneo:

        raise HTTPException(status_code=404, detail="Escaneo no encontrado")

    escaneo.titulo = req.titulo

    db.commit()

    db.refresh(escaneo)

    return escaneo



@app.delete("/api/escaneos/{escaneo_id}")

def delete_escaneo(escaneo_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh"]))):

    escaneo = db.query(models.EscaneoRH).filter(models.EscaneoRH.id == escaneo_id).first()

    if not escaneo:

        raise HTTPException(status_code=404, detail="Escaneo no encontrado")

    

    # Try to delete the physical file

    try:

        filename = os.path.basename(escaneo.ruta_archivo)

        filepath = os.path.join(ESCANEOS_DIR, filename)

        if os.path.exists(filepath):

            os.remove(filepath)

    except Exception as e:

        print(f"Error al eliminar el archivo fisico: {e}")

        

    db.delete(escaneo)

    db.commit()

    return {"message": "Escaneo eliminado correctamente"}



# === DASHBOARD, ANALYTICS & AUDITORÍA ===

@app.get("/api/analytics", response_model=schemas.AnalyticsDashboardResponse)

def get_analytics(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "sistemas", "rh", "director"]))):

    # Total pacientes activos

    pacientes_activos = db.query(models.Paciente).filter(models.Paciente.status_ingreso == "Ingresado").count()

    

    # Atenciones del mes

    hoy = datetime.date.today()

    primer_dia = datetime.date(hoy.year, hoy.month, 1)

    atenciones_mes = db.query(models.AtencionMedica).filter(func.date(models.AtencionMedica.fecha_realizacion) >= primer_dia).count()

    

    # Visitas por área (todas las atenciones agrupadas)

    areas_db = db.query(

        models.AtencionMedica.area_hospitalaria, func.count(models.AtencionMedica.folio).label("total")

    ).group_by(models.AtencionMedica.area_hospitalaria).all()

    visitas_area = [{"area": a[0] or "Sin Área", "cantidad": a[1]} for a in areas_db]

    

    # Actividad reciente (últimos 7 días)

    hace_7_dias = hoy - datetime.timedelta(days=7)

    actividad_db = db.query(

        func.date(models.AtencionMedica.fecha_realizacion).label("fecha"), func.count(models.AtencionMedica.folio).label("total")

    ).filter(func.date(models.AtencionMedica.fecha_realizacion) >= hace_7_dias).group_by(func.date(models.AtencionMedica.fecha_realizacion)).order_by("fecha").all()

    actividad = [{"fecha": str(a[0]), "cantidad": a[1]} for a in actividad_db]

    

    # SLA Médico (tiempo entre fecha_registro y fecha_firma)

    atenciones_firmadas = db.query(models.AtencionMedica).filter(models.AtencionMedica.fecha_firma.isnot(None), models.AtencionMedica.medico_id.isnot(None)).all()

    sla_dict = {}

    for a in atenciones_firmadas:

        m_name = a.medico.nombre_completo if a.medico else "Desconocido"

        delta = (a.fecha_firma - a.fecha_registro).total_seconds() / 60.0

        if delta < 0:

            delta = 0

        if m_name not in sla_dict:

            sla_dict[m_name] = {"sum": 0, "count": 0}

        sla_dict[m_name]["sum"] += delta

        sla_dict[m_name]["count"] += 1

        

    sla_medicos = []

    for m_name, stats in sla_dict.items():

        sla_medicos.append({

            "medico": m_name,

            "tiempo_promedio_minutos": round(stats["sum"] / stats["count"], 1),

            "total_atenciones": stats["count"]

        })

    sla_medicos = sorted(sla_medicos, key=lambda x: x["tiempo_promedio_minutos"])[:10] # Top 10 más rápidos



    return {

        "total_pacientes_activos": pacientes_activos,

        "total_atenciones_mes": atenciones_mes,

        "visitas_por_area": visitas_area,

        "sla_por_medico": sla_medicos,

        "actividad_reciente": actividad

    }



@app.get("/api/auditoria", response_model=List[schemas.AuditoriaLogResponse])

def get_auditoria(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))):

    return db.query(models.AuditoriaLog).order_by(models.AuditoriaLog.fecha_hora.desc()).limit(200).all()



@app.get("/api/pacientes/{paciente_id}/traslados", response_model=List[schemas.TrasladoPacienteResponse])

def get_traslados(paciente_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):

    return db.query(models.TrasladoPaciente).filter(models.TrasladoPaciente.paciente_id == paciente_id).order_by(models.TrasladoPaciente.fecha_traslado.desc()).all()



@app.get("/api/pacientes/{paciente_id}/journey")

def get_paciente_journey(paciente_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):

    paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente_id).first()

    if not paciente:

        raise HTTPException(status_code=404, detail="Paciente no encontrado")

        

    eventos = []

    

    # 1. Ingreso

    eventos.append({

        "tipo": "INGRESO",

        "fecha": paciente.fecha_registro.isoformat() + "Z" if paciente.fecha_registro else None,

        "descripcion": f"Ingreso a Hospital. Área inicial: {paciente.area_hospitalaria or 'No asignada'}, Hab: {paciente.num_habitacion}",

        "usuario": paciente.creador.nombre_completo if paciente.creador else "Sistema"

    })

    

    # 2. Traslados

    traslados = db.query(models.TrasladoPaciente).filter(models.TrasladoPaciente.paciente_id == paciente_id).all()

    for t in traslados:

        eventos.append({

            "tipo": "TRASLADO",

            "fecha": t.fecha_traslado.isoformat() + "Z" if t.fecha_traslado else None,

            "descripcion": f"Traslado a {t.destino_area or 'No asignada'}, Hab: {t.destino_habitacion}",

            "usuario": t.usuario.nombre_completo if t.usuario else "Sistema"

        })

        

    # 3. Atenciones y Firmas

    atenciones = db.query(models.AtencionMedica).filter(models.AtencionMedica.paciente_id == paciente_id).all()

    for a in atenciones:

        # Solicitud de Atención

        eventos.append({

            "tipo": "ATENCION",

            "fecha": a.fecha_registro.isoformat() + "Z" if a.fecha_registro else None,

            "descripcion": f"Solicitud de atención: {a.nombre_procedimiento}",

            "usuario": a.creador.nombre_completo if a.creador else "Sistema"

        })

        # Firma Médica

        if a.fecha_firma and a.medico:

            eventos.append({

                "tipo": "FIRMA_MEDICA",

                "fecha": a.fecha_firma.isoformat() + "Z" if a.fecha_firma else None,

                "descripcion": f"Firma médica completada por {a.medico.nombre_completo}",

                "usuario": a.medico.nombre_completo

            })

            

    # 4. Alta

    if paciente.status_ingreso == "Alta" and paciente.fecha_alta:

        eventos.append({

            "tipo": "ALTA",

            "fecha": paciente.fecha_alta.isoformat() + "Z" if paciente.fecha_alta else None,

            "descripcion": "Alta del paciente",

            "usuario": paciente.dado_de_alta_por.nombre_completo if paciente.dado_de_alta_por else "Sistema"

        })

        

    # Filtrar eventos sin fecha y ordenar por fecha ascendente

    eventos = [e for e in eventos if e["fecha"] is not None]

    eventos.sort(key=lambda x: x["fecha"])

    

    return eventos



# === BACKUP ===

@app.get("/api/backup")

def get_backup(current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))):

    db_path = "hospital_escandon.db"

    if not os.path.exists(db_path):

        raise HTTPException(status_code=404, detail="Base de datos no encontrada")

    hoy = datetime.date.today().strftime("%Y%m%d")

    return FileResponse(path=db_path, filename=f"backup_hes_{hoy}.db", media_type="application/octet-stream")



@app.post("/api/atenciones/{folio}/notas", response_model=schemas.NotaResponse)

def agregar_nota(folio: str, req: schemas.NotaCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):

    atencion = db.query(models.AtencionMedica).filter(models.AtencionMedica.folio == folio).first()

    if not atencion:

        raise HTTPException(status_code=404, detail="Atención no encontrada")

    if atencion.is_caducado and getattr(current_user, "rol", "") != "sistemas":

        raise HTTPException(status_code=400, detail="Fuera de tiempo permitido para captura (registro caducado)")

    

    # Medico objects don't map to usuarios table; only store id for Usuario rows

    is_medico = getattr(current_user, "rol", "") in ("medico", "ayudante")

    nueva_nota = models.NotaEnfermeria(

        atencion_folio=folio,

        nota=req.nota,

        creada_por_id=None if is_medico else current_user.id

    )

    db.add(nueva_nota)

    db.commit()

    db.refresh(nueva_nota)

    return nueva_nota



@app.put("/api/atenciones/{folio}/reaperturar")

def reaperturar_registro(folio: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["sistemas"]))):

    atencion = db.query(models.AtencionMedica).filter(models.AtencionMedica.folio == folio).first()

    if not atencion:

        raise HTTPException(status_code=404, detail="Atención no encontrada")

    atencion.reaperturado = True

    db.commit()

    return {"message": "Registro reaperturado exitosamente"}



@app.put("/api/atenciones/{folio}/autorizar")

def autorizar_registro(folio: str, req: schemas.AutorizarRequest, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["sistemas"]))):

    atencion = db.query(models.AtencionMedica).filter(models.AtencionMedica.folio == folio).first()

    if not atencion:

        raise HTTPException(status_code=404, detail="Atención no encontrada")

    if atencion.estatus_pago != "Pendiente Autorización":

        raise HTTPException(status_code=400, detail="El registro no está pendiente de autorización.")

        

    if req.aceptado:

        atencion.estatus_pago = "Pendiente de Firma"

    else:

        atencion.estatus_pago = "Denegado"

    db.commit()

    return {"message": f"Registro {'autorizado' if req.aceptado else 'denegado'} exitosamente"}



@app.get("/api/pacientes/altas", response_model=List[schemas.PacienteResponse])

def get_pacientes_altas(db: Session = Depends(get_db), current_user = Depends(get_current_user)):

    return db.query(models.Paciente).filter(models.Paciente.status_ingreso == "Alta").order_by(models.Paciente.fecha_alta.desc()).all()




# === MÓDULO CAMAS ===

@app.get("/api/camas")

def get_camas(db: Session = Depends(get_db)):

    """Obtiene el listado de camas desde el hospital cruzado con el estado de limpieza local."""

    kh_camas = kh_database.fetch_camas()

    if not isinstance(kh_camas, list) or len(kh_camas) == 0 or "Error" in kh_camas[0] or "Mensaje" in kh_camas[0]:

        return kh_camas

        

    local_camas = {c.numero_cama: c for c in db.query(models.Cama).all()}

    

    for cama in kh_camas:

        room_name = cama.get("RoomName")

        if room_name in local_camas:

            c = local_camas[room_name]

            cama["estado_limpieza"] = c.estado_limpieza or "Disponible"

            cama["notas_limpieza"] = c.notas_limpieza

        else:

            cama["estado_limpieza"] = "Disponible"

            cama["notas_limpieza"] = None

            

    return kh_camas



@app.put("/api/camas/{numero_cama}/limpieza")

def update_cama_limpieza(numero_cama: str, payload: dict, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["Mantenimiento/Limpieza", "limpieza", "admin", "sistemas"]))):

    cama_db = db.query(models.Cama).filter(models.Cama.numero_cama == numero_cama).first()

    if not cama_db:

        cama_db = models.Cama(numero_cama=numero_cama, area="Otras Áreas")

        db.add(cama_db)

    

    cama_db.estado_limpieza = payload.get("estado_limpieza", "Disponible")

    cama_db.notas_limpieza = payload.get("notas_limpieza", None)

    log_auditoria(db, current_user.id, "Actualización Limpieza Cama", f"Cama {numero_cama} -> {cama_db.estado_limpieza}")
    db.commit()

    

    return {"status": "ok", "message": "Estado de limpieza actualizado"}



@app.get("/api/camas/paciente/{pt_num}")

def get_patient_timeline(pt_num: str):

    """Obtiene la Ficha Rápida (demográficos) y la Línea de Tiempo del paciente."""

    return kh_database.fetch_patient_info_and_timeline(pt_num)



@app.get("/api/ehr/paciente/{pt_num}")
def get_full_ehr_dashboard(pt_num: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Obtiene el dashboard completo del expediente (Fase 1)."""
    local_pt = get_or_create_paciente_by_identifier(db, str(pt_num), allow_create=False)
    target_kh_pt = str(pt_num).replace("PT-", "").strip()
    if local_pt and local_pt.codigo_barras:
        target_kh_pt = str(local_pt.codigo_barras).replace("PT-", "").strip()

    data = kh_database.fetch_full_ehr_dashboard(target_kh_pt)

    if isinstance(data, dict) and "error" not in data:
        # Read-only enrichment. State transitions/purges belong to explicit
        # alta/reingreso/synchronization commands, never to a GET request.
        if local_pt and "patient" in data:
            is_vert_active = data["patient"].get("is_active") is True
            is_vert_alta = (
                data["patient"].get("status") == "Alta"
                or data["patient"].get("is_alta") is True
            )
            if is_vert_active:
                data["patient"].update(
                    status="Activo",
                    is_active=True,
                    is_alta=False,
                    fecha_egreso="___/___/___",
                    hora_egreso="__:__",
                )
            elif is_vert_alta or local_pt.status_ingreso == "Alta" or local_pt.fecha_alta:
                data["patient"].update(status="Alta", is_active=False, is_alta=True)
                if local_pt.fecha_alta and not data["patient"].get("fecha_egreso"):
                    data["patient"]["fecha_egreso"] = local_pt.fecha_alta.strftime("%d/%m/%Y")
                    data["patient"]["hora_egreso"] = local_pt.fecha_alta.strftime("%H:%M")

        # 1. Enriquecer Formato 15 (Cesárea / Disentimiento)
        try:
            hists_15 = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-15"
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_15" in data and isinstance(data["historial_15"], list) and data["historial_15"]:
                for idx, item in enumerate(data["historial_15"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_15 if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_15:
                        matched = hists_15[0]
                    elif not matched and len(hists_15) > idx:
                        matched = hists_15[idx]
                    
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k in ("no_autorizo", "tipo", "motivo_no_acepto", "diagnostico", "pariente", "paciente_capaz", "testigo1", "testigo2", "identificacion_testigo", "parentesco_testigo", "domicilio_testigo", "procedimiento_consiste", "beneficios", "alternativas"):
                                    item[k] = v
                                elif k not in item or item[k] is None or item[k] == "":
                                    item[k] = v
                        except Exception as e_p:
                            print(f"Error parsing json for hist 15 item: {e_p}")

                data["consentimiento_15"] = data["historial_15"][0]
            elif hists_15 and hists_15[0].contenido_soap_json:
                try:
                    c15_data = json.loads(hists_15[0].contenido_soap_json)
                    c15_data["mrnum"] = hists_15[0].evolution_slot or 1
                    data["consentimiento_15"] = c15_data
                    data["historial_15"] = [c15_data]
                except Exception:
                    pass
        except Exception as e_h15:
            print(f"Error enriching Formato 15: {e_h15}")

        # 2. Enriquecer Formato 04 (Catéter Central)
        try:
            hists_04 = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-04"
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_04" in data and isinstance(data["historial_04"], list) and data["historial_04"]:
                for idx, item in enumerate(data["historial_04"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_04 if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_04:
                        matched = hists_04[0]
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k not in item or not item[k]:
                                    item[k] = v
                        except Exception:
                            pass
                data["consentimiento_04"] = data["historial_04"][0]
        except Exception as e_h04:
            print(f"Error enriching Formato 04: {e_h04}")

        # 3. Enriquecer Formato 32/01
        try:
            last_hist_32 = db.query(models.HistoricoNotaClinica).filter(
                models.HistoricoNotaClinica.pt_num == str(pt_num),
                models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-32/01"
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist_32 and last_hist_32.contenido_soap_json:
                hist_data = json.loads(last_hist_32.contenido_soap_json)
                if not data.get("consentimiento_32_01"):
                    data["consentimiento_32_01"] = {}
                for k, v in hist_data.items():
                    data["consentimiento_32_01"][k] = v
        except Exception as e_h32:
            print(f"Error parsing historic consent 32: {e_h32}")

        # 4. Enriquecer Formato 02 (Tratamiento Quirúrgico / Disentimiento)
        try:
            hists_02 = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-02"
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_02" in data and isinstance(data["historial_02"], list) and data["historial_02"]:
                for idx, item in enumerate(data["historial_02"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_02 if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_02:
                        matched = hists_02[0]
                    elif not matched and len(hists_02) > idx:
                        matched = hists_02[idx]
                    
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k in ("no_autorizo", "tipo", "motivo_de_no_autorizacion", "motivo_no_acepto", "diagnostico", "pariente", "paciente_capaz", "testigo1", "testigo2", "domicilio_testigo1", "identificacion_testigo1", "parentesco_testigo1", "proced_para_confirmar_diagnost", "beneficio_de_dicho_procedimiento", "tratamientos_medicos", "tratamientos_quirurgicos", "tratamientos_endoscopicos", "tratamientos_de_rehabilitacion", "anestesia", "tipo_de_anestesia", "principales_riesgos", "alternativas"):
                                    item[k] = v
                                elif k not in item or item[k] is None or item[k] == "":
                                    item[k] = v
                        except Exception as e_p:
                            print(f"Error parsing json for hist 02 item: {e_p}")

                data["consentimiento_02"] = data["historial_02"][0]
            elif hists_02 and hists_02[0].contenido_soap_json:
                try:
                    c02_data = json.loads(hists_02[0].contenido_soap_json)
                    c02_data["mrnum"] = hists_02[0].evolution_slot or 1
                    data["consentimiento_02"] = c02_data
                    data["historial_02"] = [c02_data]
                except Exception:
                    pass
        except Exception as e_h02:
            print(f"Error enriching Formato 02: {e_h02}")

        # Enriquecer Formato 08 (Admisión Continua / Diagnóstico) con Snapshots de Auditoría
        try:
            hists_08 = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-08"
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_08" in data and isinstance(data["historial_08"], list) and data["historial_08"]:
                for idx, item in enumerate(data["historial_08"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_08 if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_08:
                        matched = hists_08[0]
                    elif not matched and len(hists_08) > idx:
                        matched = hists_08[idx]
                    
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k in ("diagnostico", "procedimientos", "riesgos_inherentes_a_procedimien", "riesgos", "prob_proced_y_alts", "alternativas", "beneficios", "testigo1", "testigo_1", "testigo2", "testigo_2", "pariente", "yo_autorizo", "parentesco", "parentesco_paciente", "paciente_capaz"):
                                    item[k] = v
                                elif k not in item or item[k] is None or item[k] == "":
                                    item[k] = v
                        except Exception as e_p:
                            print(f"Error parsing json for hist 08 item: {e_p}")

                data["consentimiento_08"] = data["historial_08"][0]
            elif hists_08 and hists_08[0].contenido_soap_json:
                try:
                    c08_data = json.loads(hists_08[0].contenido_soap_json)
                    c08_data["mrnum"] = hists_08[0].evolution_slot or 1
                    data["consentimiento_08"] = c08_data
                    data["historial_08"] = [c08_data]
                except Exception:
                    pass
        except Exception as e_h08:
            print(f"Error enriching Formato 08: {e_h08}")

        # Enriquecer Formato 43 (Orden de Intubación Endotraqueal) con Snapshots de Auditoría
        try:
            hists_43 = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-43") | (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-43") | (models.HistoricoNotaClinica.codigo_formato == "43")
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_43" in data and isinstance(data["historial_43"], list) and data["historial_43"]:
                for idx, item in enumerate(data["historial_43"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_43 if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_43:
                        matched = hists_43[0]
                    elif not matched and len(hists_43) > idx:
                        matched = hists_43[idx]
                    
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k in ("diagnostico", "diagnosticos", "servicio", "beneficios", "riesgos", "principales_riesgos", "alternativas", "declarante", "paciente_o_representante", "representante_legal", "parentesco", "parentesco_declarante", "domicilio_declarante", "identificacion_declarante", "testigo1", "testigo_1", "testigo2", "testigo_2", "domicilio_testigo1", "identificacion_testigo1", "domicilio_testigo2", "identificacion_testigo2", "paciente_capaz"):
                                    item[k] = v
                                elif k not in item or item[k] is None or item[k] == "":
                                    item[k] = v
                        except Exception as e_p:
                            print(f"Error parsing json for hist 43 item: {e_p}")

                data["consentimiento_43"] = data["historial_43"][0]
            elif hists_43 and hists_43[0].contenido_soap_json:
                try:
                    c43_data = json.loads(hists_43[0].contenido_soap_json)
                    c43_data["mrnum"] = hists_43[0].evolution_slot or 1
                    data["consentimiento_43"] = c43_data
                    data["historial_43"] = [c43_data]
                except Exception:
                    pass
        except Exception as e_h43:
            print(f"Error enriching Formato 43: {e_h43}")

        # Enriquecer Formato 06 (Procedimiento Anestésico)
        try:
            hists_06 = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-06") | (models.HistoricoNotaClinica.codigo_formato == "06")
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_06" in data and isinstance(data["historial_06"], list) and data["historial_06"]:
                for idx, item in enumerate(data["historial_06"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_06 if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_06:
                        matched = hists_06[0]
                    elif not matched and len(hists_06) > idx:
                        matched = hists_06[idx]
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k in ("tipo_cirugia", "magnitud_cirugia", "asa", "tipo_anestesia", "beneficios_anestesia", "alternativas_anestesia", "diagnostico", "servicio", "testigo_1", "testigo1", "testigo_2", "testigo2", "paciente_capaz", "pariente", "parentesco", "medico_anestesiologo"):
                                    item[k] = v
                                elif k not in item or item[k] is None or item[k] == "":
                                    item[k] = v
                        except Exception as e_p:
                            print(f"Error parsing json for hist 06 item: {e_p}")
                data["consentimiento_06"] = data["historial_06"][0]
            elif hists_06 and hists_06[0].contenido_soap_json:
                try:
                    c06_data = json.loads(hists_06[0].contenido_soap_json)
                    c06_data["mrnum"] = hists_06[0].evolution_slot or 1
                    data["consentimiento_06"] = c06_data
                    data["historial_06"] = [c06_data]
                except Exception:
                    pass
        except Exception as e_h06:
            print(f"Error enriching Formato 06: {e_h06}")

        # Enriquecer Formato 11 (Consentimiento de No Reanimación)
        try:
            hists_11 = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-11") | (models.HistoricoNotaClinica.codigo_formato == "11")
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_11" in data and isinstance(data["historial_11"], list) and data["historial_11"]:
                for idx, item in enumerate(data["historial_11"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_11 if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_11:
                        matched = hists_11[0]
                    elif not matched and len(hists_11) > idx:
                        matched = hists_11[idx]
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k in ("beneficios_y_riesgos_de_nr", "riesgos_de_no_aplicar", "alternativa_nr", "diagnostico", "servicio", "testigo_1", "testigo1", "testigo_2", "testigo2", "paciente_capaz", "pariente", "parentesco", "medico_tratante"):
                                    item[k] = v
                                elif k not in item or item[k] is None or item[k] == "":
                                    item[k] = v
                        except Exception as e_p:
                            print(f"Error parsing json for hist 11 item: {e_p}")
                data["consentimiento_11"] = data["historial_11"][0]
            elif hists_11 and hists_11[0].contenido_soap_json:
                try:
                    c11_data = json.loads(hists_11[0].contenido_soap_json)
                    c11_data["mrnum"] = hists_11[0].evolution_slot or 1
                    data["consentimiento_11"] = c11_data
                    data["historial_11"] = [c11_data]
                except Exception:
                    pass
        except Exception as e_h11:
            print(f"Error enriching Formato 11: {e_h11}")

        # Enriquecer Formato 19 (Consentimiento para Histerectomía)
        try:
            hists_19 = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-19") | (models.HistoricoNotaClinica.codigo_formato == "19")
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_19" in data and isinstance(data["historial_19"], list) and data["historial_19"]:
                for idx, item in enumerate(data["historial_19"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_19 if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_19:
                        matched = hists_19[0]
                    elif not matched and len(hists_19) > idx:
                        matched = hists_19[idx]
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k in ("diagnostico", "explicacion_de_proceso", "beneficios_de_procedimiento", "intervencion_complementaria", "alternativas_terapeuticas", "motivo_de_no_autorizacion", "tipo", "no_autorizo", "testigo_1", "testigo1", "testigo_2", "testigo2", "paciente_capaz", "pariente", "parentesco", "medico_tratante"):
                                    item[k] = v
                                elif k not in item or item[k] is None or item[k] == "":
                                    item[k] = v
                        except Exception as e_p:
                            print(f"Error parsing json for hist 19 item: {e_p}")
                data["consentimiento_19"] = data["historial_19"][0]
            elif hists_19 and hists_19[0].contenido_soap_json:
                try:
                    c19_data = json.loads(hists_19[0].contenido_soap_json)
                    c19_data["mrnum"] = hists_19[0].evolution_slot or 1
                    data["consentimiento_19"] = c19_data
                    data["historial_19"] = [c19_data]
                except Exception:
                    pass
        except Exception as e_h19:
            print(f"Error enriching Formato 19: {e_h19}")

        # Enriquecer Formato 15 (Egreso Voluntario)
        try:
            hists_15_ev = db.query(models.HistoricoNotaClinica).filter(
                (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
                (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-15") | (models.HistoricoNotaClinica.codigo_formato == "PLT-EV-15")
            ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()

            if "historial_15_ev" in data and isinstance(data["historial_15_ev"], list) and data["historial_15_ev"]:
                for idx, item in enumerate(data["historial_15_ev"]):
                    item_mr = item.get("mrnum")
                    matched = next((h for h in hists_15_ev if h.evolution_slot == item_mr), None)
                    if not matched and idx == 0 and hists_15_ev:
                        matched = hists_15_ev[0]
                    elif not matched and len(hists_15_ev) > idx:
                        matched = hists_15_ev[idx]
                    if matched and matched.contenido_soap_json:
                        try:
                            h_json = json.loads(matched.contenido_soap_json)
                            for k, v in h_json.items():
                                if k in ("diagnostico_ingreso", "diagnostico_egreso", "diagnostico", "medidas_recomendadas", "factores_riesgo", "motivo_egreso", "paciente_capaz", "declarante", "n_replegal", "parentesco", "identificacion", "domicilio_declarante", "testigo_1", "testigo1", "testigo_2", "testigo2", "medico_tratante"):
                                    item[k] = v
                                elif k not in item or item[k] is None or item[k] == "":
                                    item[k] = v
                        except Exception as e_p:
                            print(f"Error parsing json for hist 15 EV item: {e_p}")
                data["egreso_voluntario_15"] = data["historial_15_ev"][0]
            elif hists_15_ev and hists_15_ev[0].contenido_soap_json:
                try:
                    c15_data = json.loads(hists_15_ev[0].contenido_soap_json)
                    c15_data["mrnum"] = hists_15_ev[0].evolution_slot or 1
                    data["egreso_voluntario_15"] = c15_data
                    data["historial_15_ev"] = [c15_data]
                except Exception:
                    pass
        except Exception as e_h15:
            print(f"Error enriching Formato 15 EV: {e_h15}")

        # 5. Enriquecer Línea de Tiempo (Timeline) con Traslados Hospitalarios y Formatos Locales
        try:
            tl_list = data.get("timelineEvents", [])
            existing_keys = {
                (evt.get("type"), evt.get("date"), evt.get("time"))
                for evt in tl_list
            }

            # 5a. Traslados locales registrados en PostgreSQL
            if local_pt:
                traslados = db.query(models.TrasladoPaciente).filter(
                    models.TrasladoPaciente.paciente_id == local_pt.id
                ).all()
                for tr in traslados:
                    if tr.fecha_traslado:
                        f_tr = tr.fecha_traslado.strftime('%d/%m/%Y')
                        h_tr = tr.fecha_traslado.strftime('%H:%M')
                        t_type = f"Traslado Hospitalario: {tr.area_origen or 'Origen'} ➔ {tr.area_destino or 'Destino'}"
                        t_key = (t_type, f_tr, h_tr)
                        if t_key not in existing_keys:
                            existing_keys.add(t_key)
                            tl_list.append({
                                "id": f"tl_tr_{tr.id}",
                                "date": f_tr,
                                "time": h_tr,
                                "timestamp": tr.fecha_traslado.isoformat(),
                                "type": t_type,
                                "category": "Admisión y Traslado",
                                "badge": "Traslado",
                                "format_code": "",
                                "desc": f"Traslado interno de cama/área. De: {tr.area_origen or 'Área Previa'} hacia: {tr.area_destino or 'Nueva Área'}. Motivo: {tr.motivo_traslado or 'Reubicación clínica del paciente'}.",
                                "doctor": tr.nombre_usuario_traslado or "",
                                "action_type": "none"
                            })

            # Reordenar cronológicamente descendente
            def get_dt_key(evt):
                if evt.get("timestamp"):
                    try:
                        return datetime.datetime.fromisoformat(evt["timestamp"])
                    except Exception:
                        pass
                if evt.get("date"):
                    try:
                        t_str = evt.get("time") or "00:00"
                        return datetime.datetime.strptime(f"{evt['date']} {t_str}", "%d/%m/%Y %H:%M")
                    except Exception:
                        pass
                return datetime.datetime.min

            tl_list.sort(key=get_dt_key, reverse=True)
            for idx, evt in enumerate(tl_list):
                evt["id"] = f"tl_{idx + 1}"

            data["timelineEvents"] = tl_list
        except Exception as e_tl_sync:
            print(f"Error sincronizando timeline en main.py: {e_tl_sync}")

        # 6. Próximas Citas y Consultas Programadas desde PostgreSQL (models.CitaMedica)
        try:
            proximas_citas_list = []
            clean_digits = re.sub(r'[^0-9]', '', str(pt_num))
            citas_objs = []
            if local_pt:
                citas_objs = db.query(models.CitaMedica).filter(
                    (models.CitaMedica.paciente_id == local_pt.id) |
                    (models.CitaMedica.nombre_paciente_manual.ilike(f"%{clean_digits}%") if clean_digits else False)
                ).order_by(models.CitaMedica.fecha_hora.asc()).all()
            elif clean_digits:
                citas_objs = db.query(models.CitaMedica).filter(
                    models.CitaMedica.nombre_paciente_manual.ilike(f"%{clean_digits}%")
                ).order_by(models.CitaMedica.fecha_hora.asc()).all()

            for c in citas_objs:
                med_nom = c.medico.nombre_completo if c.medico else "Médico Especialista HES"
                med_esp = c.medico.especialidad if c.medico else "Consulta Externa"
                dt_str = c.fecha_hora.strftime("%d/%m/%Y") if c.fecha_hora else ""
                hr_str = c.fecha_hora.strftime("%H:%M") if c.fecha_hora else ""
                proximas_citas_list.append({
                    "id": f"cita_{c.id}",
                    "fecha": dt_str,
                    "hora": hr_str,
                    "especialidad": med_esp,
                    "medico": med_nom,
                    "tipo": c.motivo or "Consulta de Seguimiento",
                    "consultorio": c.lugar or "Consultorio HES",
                    "estatus": c.estatus or "Programada",
                    "notas": c.notas or ""
                })
            data["proximas_citas"] = proximas_citas_list
        except Exception as e_citas:
            print(f"Error cargando citas para dashboard: {e_citas}")
            data["proximas_citas"] = []

    return filter_ehr_formats(data, current_user)


def _normalize_study_pdf_filename(filename: Optional[str], ptmt_num: int) -> str:
    """Devuelve un nombre seguro y descriptivo para el PDF de un estudio."""
    raw_name = str(filename or "").strip().replace("\\", "/")
    base_name = os.path.basename(raw_name)
    stem, _extension = os.path.splitext(base_name)
    generic_name = bool(
        re.fullmatch(
            r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|[0-9a-f]{24,})",
            stem,
            flags=re.IGNORECASE,
        )
    )

    if not base_name or generic_name:
        return f"Resultado_Estudio_PTMT_{ptmt_num}.pdf"

    # Evita que el encabezado Content-Disposition pueda inyectar separadores,
    # comillas o saltos de línea provenientes de SQL Server.
    safe_stem = re.sub(r"[\x00-\x1f\x7f\"']", "", stem)
    safe_stem = re.sub(r"[^0-9A-Za-zÀ-ÿ._() -]+", "_", safe_stem)
    safe_stem = re.sub(r"\s+", " ", safe_stem).strip(" ._")
    if not safe_stem:
        return f"Resultado_Estudio_PTMT_{ptmt_num}.pdf"

    return f"{safe_stem}.pdf"


@app.get("/api/kh/estudios/{ptmt_num}/pdf")
@app.get("/kh/estudios/{ptmt_num}/pdf")
@app.get("/api/api/kh/estudios/{ptmt_num}/pdf")
def get_kh_study_pdf(ptmt_num: int):
    """
    Descarga o visualiza en línea el PDF del estudio de laboratorio o imagenología
    directamente desde dbo.PTMT (Vertical Medsys / KingHero).
    """
    blob, filename, content_type = kh_database.get_study_document_binary(ptmt_num)
    if not blob:
        raise HTTPException(status_code=404, detail="Documento de estudio no encontrado en la base de datos de Vertical")
    
    clean_filename = _normalize_study_pdf_filename(filename, ptmt_num)
    if blob and blob.startswith(b"%PDF"):
        try:
            import io
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(blob))
            title_stem = os.path.splitext(clean_filename)[0]
            existing_title = (reader.metadata.title or "").strip() if reader.metadata else ""
            if not existing_title or bool(
                re.fullmatch(
                    r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|[0-9a-f]{24,})",
                    existing_title,
                    flags=re.IGNORECASE,
                )
            ):
                writer = pypdf.PdfWriter()
                writer.append(reader)
                writer.add_metadata({
                    "/Title": title_stem,
                    "/Author": "Hospital Escandón - Laboratorio e Imagenología",
                })
                out_buf = io.BytesIO()
                writer.write(out_buf)
                blob = out_buf.getvalue()
        except Exception as e_meta:
            logging.getLogger(__name__).warning(
                "No se pudo enriquecer metadata de PDF de estudio",
                extra={"ptmt_num": ptmt_num, "error": str(e_meta)},
            )

    media_t = content_type or "application/pdf"
    headers = {
        "Content-Disposition": f'inline; filename="{clean_filename}"'
    }
    return Response(content=blob, media_type=media_t, headers=headers)



def registrar_documento_para_qr(
    pt_num: str,
    codigo_formato: str,
    tipo_documento: str,
    pdf_path: str,
    pdf_filename: str = None,
    slot: int = 1,
    medico_nombre: str = None,
    medico_cedula: str = None,
    doc_uuid: str = None,
    persist: bool = False,
) -> str:
    """
    Registra de forma inmutable el archivo PDF generado en la base de datos para su recuperación y apertura 100% exacta por código QR.
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num)) or str(pt_num)
    code_clean = re.sub(r'[^A-Za-z0-9_-]', '_', str(codigo_formato))
    target_uuid = doc_uuid or f"v1_{secrets.token_urlsafe(32)}"
    if not persist:
        # GET renderers may build a transient representation, but may not
        # create/update verification evidence. Registration belongs to an
        # explicit mutating workflow.
        return target_uuid
    
    file_hash = None
    if pdf_path and os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
        except Exception:
            pass

    try:
        db = SessionLocal()
        existing = db.query(models.DocumentoVerificacionQR).filter_by(doc_uuid=target_uuid).first()
        if existing:
            existing.pdf_path = os.path.abspath(pdf_path)
            existing.pdf_filename = pdf_filename or os.path.basename(pdf_path)
            existing.hash_sha256 = file_hash or existing.hash_sha256
            existing.fecha_generacion = datetime.datetime.now()
            if medico_nombre: existing.medico_nombre = medico_nombre
            if medico_cedula: existing.medico_cedula = medico_cedula
            existing.activo = True
        else:
            new_reg = models.DocumentoVerificacionQR(
                doc_uuid=target_uuid,
                pt_num=str(clean_pt),
                expediente=f"PT-{clean_pt}",
                codigo_formato=str(codigo_formato),
                tipo_documento=str(tipo_documento),
                slot=int(slot or 1),
                pdf_path=os.path.abspath(pdf_path),
                pdf_filename=pdf_filename or os.path.basename(pdf_path),
                hash_sha256=file_hash,
                fecha_generacion=datetime.datetime.now(),
                medico_nombre=medico_nombre,
                medico_cedula=medico_cedula,
                activo=True
            )
            db.add(new_reg)
        db.commit()
        db.close()
    except Exception as e:
        print(f"Error registrando documento para QR: {e}")

    return target_uuid


def _remove_transient_file(path: str) -> None:
    """Best-effort cleanup after a generated GET response is fully sent."""
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        logging.getLogger(__name__).warning(
            "No fue posible eliminar un PDF clínico transitorio",
            extra={"path": os.path.basename(path or "")},
        )


def transient_pdf_response(
    path: str,
    filename: str,
    media_type: str = "application/pdf",
    content_disposition_type: str = "attachment",
    headers: Optional[Dict[str, str]] = None,
) -> FileResponse:
    """Serve a generated PDF and remove the scratch artifact afterwards."""
    return FileResponse(
        path=path,
        filename=filename,
        media_type=media_type,
        content_disposition_type=content_disposition_type,
        headers=headers,
        background=BackgroundTask(_remove_transient_file, path),
    )

def find_doc_verificacion(db, target_id: str):
    """
    Busca de forma tolerante a fallos el registro de verificación por doc_uuid exacto o normalizado.
    """
    if not target_id:
        return None
    target_str = str(target_id).strip()
    if not re.fullmatch(r"v1_[A-Za-z0-9_-]{40,64}", target_str):
        return None
    return db.query(models.DocumentoVerificacionQR).filter(
        models.DocumentoVerificacionQR.doc_uuid == target_str,
        models.DocumentoVerificacionQR.activo == True,
    ).first()


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-32-01")
def get_pdf_consentimiento_32_01(
    pt_num: str, 
    tipo_interrogatorio: str = "Directo",
    testigo1: str = "",
    testigo2: str = "",
    paciente_o_representante: str = "",
    representante_legal: str = "",
    paciente_capaz: bool = True
):
    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_num)
    if "error" in dashboard_data:
        raise HTTPException(status_code=404, detail=dashboard_data["error"])

    patient_info = dashboard_data.get("patient", {})
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    hora_hoy = datetime.datetime.now().strftime("%H:%M")

    raw_capaz = paciente_capaz
    if str(tipo_interrogatorio).strip().lower() == "indirecto":
        p_capaz = False
    elif isinstance(raw_capaz, str):
        p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
    else:
        p_capaz = bool(raw_capaz)

    pt_data = {
        "nombre": patient_info.get("name", ""),
        "dob": patient_info.get("dob", ""),
        "mrn": patient_info.get("mrn", ""),
        "cama": patient_info.get("cama", "URGENCIAS"),
        "edad": patient_info.get("age", ""),
        "sexo": "M" if patient_info.get("gender") == "Masculino" else "F",
        "grupo_rh": patient_info.get("grupo_rh", "O+"),
        "alergias": patient_info.get("allergies", "NEGADAS"),
        "fecha_ingreso": patient_info.get("fecha_ingreso", fecha_hoy),
        "hora_ingreso": patient_info.get("hora_ingreso", hora_hoy),
        "tipo_interrogatorio": tipo_interrogatorio,
        "diagnostico": patient_info.get("diagnostico", "VALORACIÓN CARDIOLÓGICA"),
        "medico_tratante": patient_info.get("attending", ""),
        "cedula": patient_info.get("cedula", ""),
        "paciente_o_representante": paciente_o_representante or patient_info.get("name", ""),
        "representante_legal": representante_legal,
        "medico_autorizado": patient_info.get("attending", ""),
        "testigo1": testigo1,
        "testigo2": testigo2,
        "paciente_capaz": p_capaz,
        "fecha_documento": fecha_hoy
    }
    source_32 = dashboard_data.get("consentimiento_32_01") or {}
    if isinstance(source_32, dict):
        pt_data.update({key: value for key, value in source_32.items() if value not in (None, "")})

    # Consultar firma biométrica ACTIVA para el consentimiento
    firma_data = None
    db = SessionLocal()
    try:
        sig_info = pdf_service.obtener_firmas_completas_documento(
            db, pt_num, "HE-DIRMED-CONSUL-PLT-32/01", 0, paciente_capaz=p_capaz
        )
        firma_data = dict(sig_info)
        pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, source_32)
        pt_data["firma_data"] = firma_data
        pdf_service.aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz, db=db)
        if sig_info.get("nombre_medico"):
            pt_data["medico_autorizado"] = sig_info["nombre_medico"]
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
    except Exception as e:
        print(f"Error querying signature for 32/01 PDF: {e}")
    finally:
        db.close()

    

    import pdf_engine_32_01
    pdf_filename = f"consentimiento_32_01_{pt_num}.pdf"
    pdf_path = os.path.join(os.path.dirname(__file__), "static", "pdfs", pdf_filename)
    pdf_engine_32_01.generate_consentimiento_32_01(pt_data, pdf_path, firma_data=firma_data)

    

    try:
        medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
        medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
        registrar_documento_para_qr(
            pt_num=pt_num,
            codigo_formato="HE-DIRMED-SINPRO-PLT-32/01",
            tipo_documento="Consentimiento Informado para Ecocardiograma Transesofágico",
            pdf_path=pdf_path,
            pdf_filename=pdf_filename,
            slot=1,
            medico_nombre=medico_n,
            medico_cedula=medico_c
        )
    except Exception as e_reg:
        print(f"Nota: Error registrando PDF 32/01 para QR: {e_reg}")

    from fastapi.responses import FileResponse
    return transient_pdf_response(path=pdf_path, filename=pdf_filename, media_type='application/pdf')



@app.get("/api/ehr/paciente/{pt_num}/pdf-nota-urgencias")

def get_pdf_nota_urgencias(pt_num: str, evolucion: Optional[int] = None):

    """

    Genera y descarga el PDF de la Nota de Urgencias:

    - evolucion=None / 0: Formato general con todas las notas y su firma individual.

    - evolucion=1, 2, 3: Nota individual específica (con su propia firma).

    """

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_num)

    

    if "error" in dashboard_data:

        raise HTTPException(status_code=404, detail=dashboard_data["error"])

        

    patient_info = dashboard_data.get("patient", {})

    notes = dashboard_data.get("clinicalNotes", [])

    

    if not notes:

        raise HTTPException(status_code=404, detail="No hay notas clínicas para generar PDF")

        

    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")

    hora_hoy = datetime.datetime.now().strftime("%H:%M")

    

    pt_data = {

        "nombre": patient_info.get("name", ""),

        "dob": patient_info.get("dob", ""),

        "mrn": patient_info.get("mrn", ""),

        "cama": patient_info.get("cama", "Urgencias"),

        "edad": patient_info.get("age", ""),

        "sexo": "M" if patient_info.get("gender") == "Masculino" else "F",

        "grupo_rh": "O+",

        "alergias": patient_info.get("allergies", ""),

        "fecha_ingreso": patient_info.get("fecha_ingreso", fecha_hoy),

        "hora_ingreso": patient_info.get("hora_ingreso", hora_hoy),

        "diagnostico": patient_info.get("diagnostico", ""),

        "destino": patient_info.get("destino", "DOMICILIO"),

        "fecha_egreso": patient_info.get("fecha_egreso", "___/___/___"),

        "hora_egreso": patient_info.get("hora_egreso", "__:__")

    }

    

    evols = dashboard_data.get("evoluciones", {})

    e1 = evols.get("evolucion1")

    e2 = evols.get("evolucion2")

    e3 = evols.get("evolucion3")

    

    import pdf_engine_v2

    import importlib

    importlib.reload(pdf_engine_v2)

    

    evoluciones_list = dashboard_data.get("evoluciones_list", [])
    db = SessionLocal()
    try:
        firmas_por_evolucion = pdf_service.build_evolution_signature_map(
            db, pt_num, "HE-DIRMED-SINPRO-PLT-87/01", evoluciones_list
        )
    finally:
        db.close()

    if evolucion and int(evolucion) > 0:
        evol_int = int(evolucion)
        # Impresión individual de una sola nota
        target_evol = evols.get(f"evolucion{evol_int}")
        if not target_evol and evoluciones_list:
            target_evol = next((e for e in evoluciones_list if e.get("num") == evol_int), None)

        if not target_evol:
            raise HTTPException(status_code=404, detail=f"No se encontró información para la Evolución {evol_int}")

        firma_data = firmas_por_evolucion.get(evol_int, {})
        pdf_filename = f"nota_urgencias_{pt_num}_evolucion_{evol_int}.pdf"
        pdf_path = os.path.join(os.path.dirname(__file__), "static", "pdfs", pdf_filename)
        pdf_engine_v2.generate_nota_urgencias(pt_data, target_evol, None, None, pdf_path, is_general=False, firma_data=firma_data)

    else:
        # Impresión del formato general (todas las notas consecutivas en 1 documento ordenadas por antigüedad)
        pdf_filename = f"nota_urgencias_{pt_num}_general.pdf"
        pdf_path = os.path.join(os.path.dirname(__file__), "static", "pdfs", pdf_filename)
        pdf_engine_v2.generate_nota_urgencias(
            pt_data, e1, e2, e3, pdf_path, is_general=True,
            evoluciones_list=evoluciones_list, firma_data_by_slot=firmas_por_evolucion,
        )
        firma_data = firmas_por_evolucion.get(int(evoluciones_list[-1].get("num") or 0), {}) if evoluciones_list else {}

    try:
        slot_val = int(evolucion) if (evolucion and int(evolucion) > 0) else 1
        medico_n = firma_data.get("nombre_medico") if firma_data else None
        medico_c = firma_data.get("cedula") if firma_data else None
        registrar_documento_para_qr(
            pt_num=pt_num,
            codigo_formato="HE-DIRMED-SINPRO-PLT-87/01",
            tipo_documento="Nota Médica de Evolución de Urgencias",
            pdf_path=pdf_path,
            pdf_filename=pdf_filename,
            slot=slot_val,
            medico_nombre=medico_n,
            medico_cedula=medico_c
        )
    except Exception as e_reg:
        print(f"Nota: Error registrando PDF Nota Urgencias para QR: {e_reg}")

    from fastapi.responses import FileResponse
    return transient_pdf_response(path=pdf_path, filename=pdf_filename, media_type='application/pdf')


@app.get("/api/ehr/paciente/{pt_num}/pdf-expediente-completo")
@app.get("/ehr/paciente/{pt_num}/pdf-expediente-completo")
def get_pdf_expediente_completo(pt_num: str):
    """
    Genera y descarga el EXPEDIENTE CLÍNICO COMPLETO oficial (NOM-004-SSA3-2012 / NOM-024-SSA3-2012).
    Compilado integral con Carátula foliada, notas médicas de urgencias/hospitalización, consentimientos informados,
    anexo farmacoterapéutico/dietas y estudios paraclínicos.
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num)) or str(pt_num)
    db = SessionLocal()
    qr_doc_uuid = None
    qr_verify_url = None
    qr_scope = nullcontext(None)
    try:
        public_base = (
            os.getenv("PUBLIC_VERIFICATION_BASE_URL", "").strip()
            or os.getenv("VERIFICATION_BASE_URL", "").strip()
        ).rstrip("/")
        if _is_public_https_url(public_base):
            qr_doc_uuid = f"v1_{secrets.token_urlsafe(32)}"
            verify_root = public_base if public_base.endswith("/verificar") else f"{public_base}/verificar"
            qr_verify_url = f"{verify_root}?id={qr_doc_uuid}"
            qr_scope = qr_render_context(
                doc_uuid=qr_doc_uuid,
                verification_url=qr_verify_url,
                pt_num=clean_pt,
                codigo_formato="HE-DIRMED-EXPEDIENTE-COMPLETO",
                slot=1,
                persist=True,
            )

        with qr_scope:
            pdf_path, pdf_filename, signature_report = pdf_service.generate_expediente_completo_pdf(
                clean_pt,
                db_session=db,
                verification_url=qr_verify_url,
                return_metadata=True,
            )

        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="No se pudo compilar el archivo PDF del expediente completo.")

        # Un QR público debe recuperar exactamente estos bytes, incluso después
        # de que el artefacto temporal de la respuesta autenticada sea eliminado.
        if qr_doc_uuid:
            verified_dir = os.path.join(PRIVATE_STORAGE_ROOT, "verified_pdfs")
            os.makedirs(verified_dir, exist_ok=True)
            durable_path = os.path.join(verified_dir, f"{qr_doc_uuid}.pdf")
            shutil.copyfile(pdf_path, durable_path)
            registrar_documento_para_qr(
                pt_num=clean_pt,
                codigo_formato="HE-DIRMED-EXPEDIENTE-COMPLETO",
                tipo_documento="Expediente Clínico Integrado y Compilado NOM-004",
                pdf_path=durable_path,
                pdf_filename=pdf_filename,
                slot=1,
                doc_uuid=qr_doc_uuid,
                persist=True,
            )
            db.expire_all()
            if not find_doc_verificacion(db, qr_doc_uuid):
                raise HTTPException(status_code=500, detail="No se pudo guardar la copia verificable del expediente completo.")

        signature_report_header = base64.urlsafe_b64encode(
            json.dumps(signature_report or {}, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        ).decode("ascii").rstrip("=")
        return transient_pdf_response(
            path=pdf_path,
            filename=pdf_filename,
            media_type='application/pdf',
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="{pdf_filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-HES-Signature-Report": signature_report_header
            }
        )
    except pdf_service.ExpedienteSignatureReconciliationRequired as exc:
        report = exc.report or {}
        blocked_codes = {
            str(item.get("codigo") or "").strip()
            for item in report.get("bloqueos", [])
            if item.get("codigo")
        }
        repair_formats = []
        seen_repair_codes = set()
        for item in report.get("pendientes", []):
            code = str(item.get("codigo") or "").strip()
            if code not in blocked_codes or code in seen_repair_codes:
                continue
            seen_repair_codes.add(code)
            repair_formats.append({
                "codigo": code,
                "nombre": item.get("nombre") or code,
                "slot": int(item.get("slot") or 0),
                "firmas_pendientes": item.get("firmas_pendientes") or [],
            })
        report_header = base64.urlsafe_b64encode(
            json.dumps(report, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        ).decode("ascii").rstrip("=")
        raise HTTPException(
            status_code=409,
            detail={
                "code": "EXPEDIENTE_REQUIERE_REVISION_DE_FIRMAS",
                "action": "REVISAR_Y_REFIRMAR",
                "message": (
                    "Encontramos firmas que pertenecen a una versión anterior o que "
                    "no pudieron comprobarse en la versión actual. No se borró ni se "
                    "sustituyó ninguna evidencia."
                ),
                "question": "¿Desea revisar esos formatos y volver a firmar la versión vigente?",
                "formatos": repair_formats,
                "report": report,
            },
            headers={"X-HES-Signature-Report": report_header},
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generando expediente completo para {pt_num}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando expediente completo: {str(e)}")
    finally:
        db.close()


@app.get("/api/ehr/paciente/{pt_num}/evoluciones-hospitalizacion")
def get_evoluciones_hospitalizacion(pt_num: str):
    """
    Retorna la lista de evoluciones de hospitalización del paciente ordenadas por antigüedad (MR_24_HOJA_EVOL).
    """
    return kh_database.fetch_evoluciones_hospitalizacion(pt_num)


@app.get("/api/ehr/paciente/{pt_num}/pdf-nota-hospitalizacion")
def get_pdf_nota_hospitalizacion(pt_num: str, evolucion: Optional[int] = None):
    """
    Genera y descarga el PDF de la Nota de Evolución de Hospitalización (HE-DIRMED-CONSUL-PLT-24):
    - evolucion=None / 0: Formato general con todas las notas y su firma individual.
    - evolucion=1..N: Nota individual específica (con su propia firma).
    """
    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_num)
    if "error" in dashboard_data:
        raise HTTPException(status_code=404, detail=dashboard_data["error"])
        
    patient_info = dashboard_data.get("patient", {})
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    hora_hoy = datetime.datetime.now().strftime("%H:%M")
    
    pt_data = {
        "pt_num": str(pt_num),
        "nombre": patient_info.get("name", ""),
        "dob": patient_info.get("dob", ""),
        "mrn": patient_info.get("mrn", ""),
        "cama": patient_info.get("cama", "Piso Hospitalización"),
        "habitacion": patient_info.get("cama", "Piso Hospitalización"),
        "edad": patient_info.get("age", ""),
        "sexo": "M" if patient_info.get("gender") == "Masculino" else "F",
        "grupo_rh": "O+",
        "alergias": patient_info.get("allergies", ""),
        "fecha_ingreso": patient_info.get("fecha_ingreso", fecha_hoy),
        "hora_ingreso": patient_info.get("hora_ingreso", hora_hoy),
        "diagnostico": patient_info.get("diagnostico", ""),
        "servicio": "HOSPITALIZACIÓN / MEDICINA INTERNA"
    }
    
    import pdf_engine_24
    import importlib
    importlib.reload(pdf_engine_24)
    
    evoluciones_hosp = dashboard_data.get("evoluciones_hospitalizacion_list", [])
    if not evoluciones_hosp:
        evoluciones_hosp = kh_database.fetch_evoluciones_hospitalizacion(pt_num)
    db = SessionLocal()
    try:
        firmas_por_evolucion = pdf_service.build_evolution_signature_map(
            db, pt_num, "HE-DIRMED-CONSUL-PLT-24", evoluciones_hosp
        )
    finally:
        db.close()

    if evolucion and int(evolucion) > 0:
        evol_int = int(evolucion)
        target_evol = next((e for e in evoluciones_hosp if e.get("num") == evol_int), None)
        if not target_evol:
            raise HTTPException(status_code=404, detail=f"No se encontró información para la Evolución {evol_int} de Hospitalización")

        firma_data = firmas_por_evolucion.get(evol_int, {})
        pdf_filename = f"nota_hospitalizacion_{pt_num}_evolucion_{evol_int}.pdf"
        pdf_path = os.path.join(os.path.dirname(__file__), "static", "pdfs", pdf_filename)
        pdf_engine_24.generate_nota_hospitalizacion(pt_data, target_evol, None, None, pdf_path, is_general=False, firma_data=firma_data)
    else:
        pdf_filename = f"nota_hospitalizacion_{pt_num}_general.pdf"
        pdf_path = os.path.join(os.path.dirname(__file__), "static", "pdfs", pdf_filename)
        pdf_engine_24.generate_nota_hospitalizacion(
            pt_data, None, None, None, pdf_path, is_general=True,
            evoluciones_list=evoluciones_hosp, firma_data_by_slot=firmas_por_evolucion,
        )
        firma_data = firmas_por_evolucion.get(int(evoluciones_hosp[-1].get("num") or 0), {}) if evoluciones_hosp else {}

    try:
        slot_val = int(target_evol.get("mrnum_24_hoja_evol") or 0) if evolucion else 0
        medico_n = firma_data.get("nombre_medico") if firma_data else None
        medico_c = firma_data.get("cedula") if firma_data else None
        registrar_documento_para_qr(
            pt_num=pt_num,
            codigo_formato="HE-DIRMED-CONSUL-PLT-24",
            tipo_documento="Nota Médica de Evolución de Hospitalización",
            pdf_path=pdf_path,
            pdf_filename=pdf_filename,
            slot=slot_val,
            medico_nombre=medico_n,
            medico_cedula=medico_c
        )
    except Exception as e_reg:
        print(f"Nota: Error registrando PDF Nota Hospitalizacion para QR: {e_reg}")

    from fastapi.responses import FileResponse
    return transient_pdf_response(path=pdf_path, filename=pdf_filename, media_type='application/pdf')


class NotaHospitalizacionInputSchema(BaseModel):
    evolution_num: Optional[int] = None
    mrnum_24_hoja_evol: Optional[int] = None
    mrnum: Optional[int] = None
    isEdit: Optional[bool] = False
    fecha: Optional[str] = None
    hora: Optional[str] = None
    turno: Optional[str] = "Matutino"
    vitals_ta: Optional[str] = ""
    vitals_fc: Optional[str] = ""
    vitals_fr: Optional[str] = ""
    vitals_sato2: Optional[str] = ""
    vitals_peso: Optional[str] = ""
    vitals_talla: Optional[str] = ""
    vitals_temp: Optional[str] = ""
    subjetivo: Optional[str] = ""
    objetivo: Optional[str] = ""
    analisis: Optional[str] = ""
    plan: Optional[str] = ""
    medico: Optional[str] = ""
    cedula: Optional[str] = ""
    mip: Optional[str] = ""
    cama: Optional[str] = None
    servicio: Optional[str] = None


@app.post("/api/ehr/paciente/{pt_num}/nota-hospitalizacion")
def save_nota_hospitalizacion(
    pt_num: str, 
    nota: NotaHospitalizacionInputSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Guarda o actualiza una nota de evolución de hospitalización en SQL Server (MR_24_HOJA_EVOL)
    y preserva el histórico inmutable de versiones y revocación de firmas en PostgreSQL conforme a la NOM-024.
    """
    assert_paciente_no_de_alta(db, pt_num)
    nota_data = nota.model_dump()
    slot_requested = int(nota.evolution_num or 0)
    return _durable_document_write(
        db,
        request,
        pt_num=pt_num,
        adapter="save_or_update_nota_hospitalizacion",
        data=nota_data,
        codigo_formato="HE-DIRMED-CONSUL-PLT-24",
        tipo_documento="Nota de Evolución de Hospitalización",
        slot=slot_requested,
        accion="EDICION" if nota.isEdit else "CREACION",
        motivo="Actualización clínica hospitalaria desde Bitácora HES",
        medico=nota.medico or "",
        cedula=nota.cedula or "",
        success_body={"message": "Nota de hospitalización guardada correctamente", "slot": slot_requested},
    )
        
    slot_affected = int(nota.evolution_num or res.get("evolution_num") or res.get("slot") or 1)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-24",
            tipo_documento=f"Nota de Evolución de Hospitalización (Evolución {slot_affected})",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=slot_affected,
            nombre_medico=nota.medico or "",
            cedula_profesional=nota.cedula or "",
            contenido_soap_json=json.dumps(nota.model_dump(), default=str),
            accion="EDICION" if nota.isEdit else "CREACION",
            motivo="Actualización clínica hospitalaria desde Bitácora HES",
            fecha_registro=datetime.datetime.now(),
            ip_origen=client_ip
        )
        db.add(historico_entry)
    except Exception as e:
        print(f"Nota de auditoría Hosp: No se pudo registrar en HistoricoNotaClinica: {e}")

    # 2. Si es edición, revocar firmas activas previas
    if nota.isEdit:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-24",
            models.FirmaDocumentoClinico.evolution_slot == slot_affected,
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()

        for f in firmas_activas:
            f.estado = "REVOCADA_POR_MODIFICACION"
            f.motivo_revocacion = "El documento hospitalario fue modificado posteriormente."
            f.fecha_revocacion = datetime.datetime.now()

        try:
            log_auditoria = models.AuditoriaLog(
                usuario_id=None,
                accion="MODIFICACION_NOTA_HOSPITALIZACION_Y_REVOCACION_FIRMA",
                detalles_json=json.dumps({
                    "pt_num": str(pt_num),
                    "slot": slot_affected,
                    "medico": nota.medico,
                    "cedula": nota.cedula,
                    "firmas_revocadas_ids": [f.id for f in firmas_activas],
                    "usuario_servicio": "BITACORA_HES"
                }),
                fecha_hora=datetime.datetime.now(),
                ip_origen=client_ip
            )
            db.add(log_auditoria)
        except Exception as e:
            print(f"Error registrando auditoria log hosp: {e}")

    db.commit()

    return {
        "success": True, 
        "message": f"Evolución {slot_affected} de Hospitalización guardada correctamente.",
        "mrnum_24_hoja_evol": res.get("mrnum_24_hoja_evol"),
        "evolution_num": slot_affected,
        "slot": slot_affected
    }


class NotaUrgenciasInputSchema(BaseModel):

    evolution_num: Optional[int] = None

    fecha: Optional[str] = None

    hora: Optional[str] = None

    turno: Optional[str] = "Matutino"

    vitals_ta: Optional[str] = ""

    vitals_fc: Optional[str] = ""

    vitals_fr: Optional[str] = ""

    vitals_sato2: Optional[str] = ""

    vitals_peso: Optional[str] = ""

    vitals_talla: Optional[str] = ""

    vitals_temp: Optional[str] = ""

    subjetivo: Optional[str] = ""

    objetivo: Optional[str] = ""

    analisis: Optional[str] = ""

    plan: Optional[str] = ""

    medico: Optional[str] = ""

    cedula: Optional[str] = ""

    mip: Optional[str] = ""

    alergias: Optional[str] = None

    diagnostico: Optional[str] = None

    destino: Optional[str] = None

    cama: Optional[str] = None



class ConsentimientoInputSchema(BaseModel):

    tipo_interrogatorio: Optional[str] = "Directo"

    testigo1: Optional[str] = ""

    testigo2: Optional[str] = ""

    paciente_o_representante: Optional[str] = ""

    representante_legal: Optional[str] = ""

    medico_tratante: Optional[str] = ""

    cedula: Optional[str] = ""

    alergias: Optional[str] = "NEGADAS"

    diagnostico: Optional[str] = ""



@app.post("/api/ehr/paciente/{pt_num}/consentimiento-32-01")
def save_consentimiento_32_01(
    pt_num: str, 
    consent_data: ConsentimientoInputSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    data = consent_data.model_dump()
    return _durable_document_write(
        db,
        request,
        pt_num=pt_num,
        adapter="save_or_update_consentimiento_32_01",
        data=data,
        codigo_formato="HE-DIRMED-CONSUL-PLT-32/01",
        tipo_documento="Consentimiento Informado para Ecocardiograma Transesofágico",
        accion="GUARDADO",
        medico=consent_data.medico_tratante or "",
        cedula=consent_data.cedula or "",
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-32/01",
            tipo_documento="Consentimiento Informado para Ecocardiograma Transesofágico",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=0,
            nombre_medico=consent_data.medico_tratante,
            cedula_profesional=consent_data.cedula,
            contenido_soap_json=json.dumps(consent_data.model_dump(), default=str),
            accion="EDICION" if not consent_data.is_new else "CREACION",
            motivo="Captura institucional de consentimiento informado",
            fecha_registro=datetime.datetime.now(),
            ip_origen=client_ip
        )
        db.add(historico_entry)
    except Exception as e:
        print(f"Error guardando HistoricoNotaClinica 32_01: {e}")

    # 2. Revocar firmas anteriores activas si se modificó
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-32/01",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()

        for f in firmas_activas:
            f.estado = "REVOCADA_POR_MODIFICACION"
            f.motivo_revocacion = "El documento fue modificado posteriormente."
            f.fecha_revocacion = datetime.datetime.now()
            f.motivo_revocacion = "Modificación y edición de los datos del consentimiento informado 32/01"

        db.commit()
    except Exception as e:
        print(f"Error revoking active signatures for Consentimiento 32_01: {e}")
        db.rollback()

    return res



@app.post("/api/ehr/paciente/{pt_num}/nota-urgencias")
def create_or_update_nota_urgencias(
    pt_num: str, 
    nota: NotaUrgenciasInputSchema, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Guarda o actualiza una nota de evolución en SQL Server (con usuario de servicio institucional BITACORA_HES)
    y preserva el histórico inmutable de versiones y revocación de firmas en PostgreSQL conforme a la NOM-024.
    """
    assert_paciente_no_de_alta(db, pt_num)
    nota_data = nota.model_dump()
    slot_requested = int(nota.evolution_num or 0)
    return _durable_document_write(
        db,
        request,
        pt_num=pt_num,
        adapter="save_or_update_nota_urgencias",
        data=nota_data,
        codigo_formato="HE-DIRMED-SINPRO-PLT-87/01",
        tipo_documento="Nota de Evolución de Urgencias",
        slot=slot_requested,
        accion="EDICION" if nota.evolution_num else "CREACION",
        motivo="Actualización clínica desde Bitácora HES",
        medico=nota.medico or "",
        cedula=nota.cedula or "",
        success_body={"message": "Nota de urgencias guardada correctamente", "slot": slot_requested},
    )

        

    slot_affected = int(nota.evolution_num or res.get("slot") or 1)

    client_ip = request.client.host if request.client else "127.0.0.1"



    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)

    try:

        historico_entry = models.HistoricoNotaClinica(

            codigo_formato="HE-DIRMED-SINPRO-PLT-87/01",

            tipo_documento=f"Nota de Evolución de Urgencias (Evolución {slot_affected})",

            pt_num=str(pt_num),

            expediente=f"PT-{pt_num}",

            evolution_slot=slot_affected,

            nombre_medico=nota.medico or "",

            cedula_profesional=nota.cedula or "",

            contenido_soap_json=json.dumps(nota.model_dump(), default=str),

            accion="EDICION" if nota.evolution_num else "CREACION",

            motivo="Actualización clínica desde Bitácora HES",

            fecha_registro=datetime.datetime.now(),

            ip_origen=client_ip

        )

        db.add(historico_entry)

    except Exception as e:

        print(f"Nota de auditoría: No se pudo registrar en HistoricoNotaClinica: {e}")



    # 2. INTEGRIDAD NOM-024 / NOM-004: Soft-Revocation (NUNCA BORRAR FÍSICAMENTE DE LA BD)

    firmas_activas = db.query(models.FirmaDocumentoClinico).filter(

        models.FirmaDocumentoClinico.pt_num == str(pt_num),

        models.FirmaDocumentoClinico.evolution_slot == slot_affected,

        models.FirmaDocumentoClinico.estado == "ACTIVA"

    ).all()



    for f in firmas_activas:

        f.estado = "REVOCADA_POR_MODIFICACION"
        f.motivo_revocacion = "El documento fue modificado posteriormente."

        f.fecha_revocacion = datetime.datetime.now()

        f.motivo_revocacion = f"Modificación y edición del contenido clínico en slot {slot_affected}"



    # 3. Registrar evento en AuditoriaLog Central

    try:

        log_auditoria = models.AuditoriaLog(

            usuario_id=None,

            accion="MODIFICACION_NOTA_CLINICA_Y_REVOCACION_FIRMA",

            detalles_json=json.dumps({

                "pt_num": str(pt_num),

                "slot": slot_affected,

                "medico": nota.medico,

                "cedula": nota.cedula,

                "firmas_revocadas_ids": [f.id for f in firmas_activas],

                "usuario_servicio": "BITACORA_HES"

            }),

            fecha_hora=datetime.datetime.now(),

            ip_origen=client_ip

        )

        db.add(log_auditoria)

    except Exception as e:

        print(f"Error registrando auditoria log: {e}")



    db.commit()

    print(f"Aviso NOM-024: Se preservó histórico y se marcaron {len(firmas_activas)} firmas como REVOCADAS (sin borrado físico).")



    return res



class SignosVitalesInputSchema(BaseModel):

    systolic: Optional[Union[int, str]] = None

    diastolic: Optional[Union[int, str]] = None

    ta: Optional[str] = None

    pulse: Optional[Union[int, str]] = None

    respiratory: Optional[Union[int, str]] = None

    oxygen_saturation: Optional[Union[int, str]] = None

    temperature: Optional[Union[float, str]] = None

    weight: Optional[Union[float, str]] = None

    height: Optional[Union[float, str]] = None

    procedure_date: Optional[str] = None



@app.get("/api/ehr/paciente/{pt_num}/signos-vitales")
def get_paciente_signos_vitales(pt_num: str):
    """Consulta los signos vitales más recientes desde la tabla maestra PTVS en SQL Server."""
    return kh_database.fetch_patient_vitals_ptvs(pt_num)


@app.get("/api/ehr/paciente/{pt_num}/historial-signos-vitales")
def get_paciente_historial_signos_vitales(pt_num: str):
    """Consulta todo el historial cronológico de tomas de signos vitales (PTVS) en SQL Server."""
    return kh_database.fetch_patient_vitals_history_ptvs(pt_num)



@app.post("/api/ehr/paciente/{pt_num}/signos-vitales")
def save_paciente_signos_vitales(
    pt_num: str, 
    vitals: SignosVitalesInputSchema, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Registra o actualiza la toma de signos vitales en la tabla [KH_HE].[dbo].[PTVS] de SQL Server
    y asienta el evento en la auditoría inmutable de la Bitácora.
    """
    assert_paciente_no_de_alta(db, pt_num)
    vital_data = vitals.model_dump()
    return _durable_audited_kh_write(
        db,
        request,
        pt_num=pt_num,
        adapter="save_patient_vitals_ptvs",
        args=[str(pt_num), vital_data],
        kwargs={},
        aggregate_id=f"{pt_num}:vitals:{vital_data.get('procedure_date') or 'current'}",
        audit_action="CAPTURA_SIGNOS_VITALES_PTVS",
        audit_details={"pt_num": str(pt_num), "vitals": vital_data},
        success_body={"message": "Signos vitales guardados correctamente"},
    )



    # Registrar en AuditoriaLog Central

    try:

        client_ip = request.client.host if request.client else "127.0.0.1"

        log = models.AuditoriaLog(

            usuario_id=None,

            accion="CAPTURA_SIGNOS_VITALES_PTVS",

            detalles_json=json.dumps({

                "pt_num": str(pt_num),

                "vitals": vitals.model_dump(),

                "ptvs_id": res.get("ptvs_id")

            }, default=str),

            fecha_hora=datetime.datetime.now(),

            ip_origen=client_ip

        )

        db.add(log)

        db.commit()

    except Exception as e:

        print(f"Error registrando auditoría de signos vitales: {e}")



    return res



class PrescribirMedicamentoInputSchema(BaseModel):

    name: str

    amount: float # Debe ser numérico positivo

    uom: Optional[str] = "mg"

    route: Optional[str] = "Oral"

    frequency: Optional[str] = "Cada 8 horas"

    prn: Optional[bool] = False

    why: Optional[str] = ""

    dispense: Optional[str] = ""
    refills: Optional[int] = 0
    instruction: Optional[str] = ""
    fmd_template: str # Huella dactilar obligatoria del médico tratante
    medico_id: Optional[int] = None
    challenge_id: str
    session_id: str

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            raise ValueError("La dosis (amount) es obligatoria y debe ser un número positivo mayor a 0.")
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("La dosis (amount) debe ser un valor numérico válido (int o float).")
        if val <= 0:
            raise ValueError("La dosis (amount) debe ser un número positivo mayor a 0.")
        return val

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v):
        if v is not None:
            if len(v) > 100:
                raise ValueError("La frecuencia no puede tener más de 100 caracteres.")
            caracteres_prohibidos = [";", "--", "<", ">", "/*", "*/"]
            for patron in caracteres_prohibidos:
                if patron in v:
                    raise ValueError(f"La frecuencia contiene caracteres especiales no permitidos ('{patron}').")
        return v

class DiscontinuarMedicamentoInputSchema(BaseModel):
    ptdg_num: int
    reason: Optional[str] = "Discontinuado por evolución clínica"
    fmd_template: str # Huella dactilar para suspender
    medico_id: Optional[int] = None
    challenge_id: str
    session_id: str



@app.get("/api/ehr/paciente/{pt_num}/medicamentos")

def get_paciente_medicamentos(pt_num: str):

    """Consulta la lista de medicamentos prescritos desde la tabla maestra PTDG en SQL Server."""

    return kh_database.fetch_patient_medications_ptdg(pt_num)



@app.post("/api/ehr/paciente/{pt_num}/medicamentos/prescribir-biometrico")
def prescribir_medicamento_biometrico(
    pt_num: str,
    req: PrescribirMedicamentoInputSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Prescribe formalmente un fármaco en SQL Server (PTDG) requiriendo validación biométrica dactilar
    del médico conforme a la NOM-004-SSA3-2012 y NOM-024-SSA3-2012.
    """
    assert_paciente_no_de_alta(db, pt_num)
    # 1. Validar huella dactilar mediante motor biométrico (1:1 si viene medico_id)
    match_found = verificar_huella_medico(
        db=db,
        fmd_template=req.fmd_template,
        medico_id=req.medico_id,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="PRESCRIPCION",
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=_biometric_identity_from_request(request),
        patient_ref=str(pt_num),
        document_code="HE-DIRMED-SINPRO-REC-01",
    )
    _assert_fea_enabled(match_found)

    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="MEDICATION_PRESCRIBE",
        aggregate_type="patient_medication",
        aggregate_id=f"{pt_num}:{req.name}:{req.challenge_id}",
        patient_ref=str(pt_num),
        payload={
            "act_id": hashlib.sha256(req.challenge_id.encode()).hexdigest(),
            "medication": req.model_dump(),
        },
    )
    if not created:
        return _existing_sync_response(operation)



    # 2. Generar Firma Criptográfica de la Prescripción

    now = datetime.datetime.now()

    cadena_original = f"||{pt_num}|PT-{pt_num}|RECETA-PTDG|{req.name}|{req.amount} {req.uom}|{req.route}|{req.frequency}|{now.isoformat()}|{match_found.id}|{match_found.cedula}||"

    hash_sha256 = hashlib.sha256(cadena_original.encode('utf-8')).hexdigest()



    sello_digital = crypto_fea.firmar_documento(db, match_found, cadena_original)



    # 3. Guardar evidencia local antes de entregar a SQL Server.

    client_ip = request.client.host if request.client else "127.0.0.1"

    firma_registro = models.FirmaDocumentoClinico(

        tipo_documento="Prescripción Médica de Farmacoterapia (PTDG)",

        codigo_formato="HE-DIRMED-SINPRO-REC-01",

        pt_num=str(pt_num),

        expediente=f"PT-{pt_num}",

        evolution_slot=None,

        medico_id=match_found.id,

        nombre_medico=match_found.nombre_completo,

        cedula_profesional=match_found.cedula,

        fecha_hora_firma=now,

        metodo_autenticacion="Biometría Dactilar DigitalPersona (NOM-004/NOM-024)",

        hash_sha256=hash_sha256,

        sello_digital=sello_digital,

        cadena_original=cadena_original,

        ip_origen=client_ip,

        estado="ACTIVA",
        clinical_sync_operation_id=operation.operation_id,
    )

    db.add(firma_registro)



    log_auditoria = models.AuditoriaLog(

        usuario_id=None,

        accion="PRESCRIPCION_MEDICAMENTO_PTDG",

        detalles_json=json.dumps({

            "pt_num": str(pt_num),

            "medication": req.name,

            "dose": f"{req.amount} {req.uom}",

            "route": req.route,

            "freq": req.frequency,

            "medico": match_found.nombre_completo,

            "cedula": match_found.cedula,

            "operation_id": str(operation.operation_id)

        }),

        fecha_hora=now,

        ip_origen=client_ip

    )

    db.add(log_auditoria)

    clinical_sync.mark_local_applied(db, operation)
    result = clinical_sync.execute_external(
        db,
        operation,
        clinical_sync_adapters.dispatcher(operation),
        session_factory=SessionLocal,
    )
    external = result.value or {}
    return _sync_result_response(result, {

        "success": True,

        "message": f"Fármaco '{req.name}' prescrito y firmado exitosamente por {match_found.nombre_completo}.",

        "medico": match_found.nombre_completo,

        "cedula": match_found.cedula,

        "ptdg_id": external.get("ptdg_id"),

        "sello": sello_digital[:32] + "..."

    })



@app.post("/api/ehr/paciente/{pt_num}/medicamentos/discontinuar-biometrico")
def discontinuar_medicamento_biometrico(
    pt_num: str,
    req: DiscontinuarMedicamentoInputSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """Suspende un fármaco activo en PTDG requiriendo huella biométrica del médico."""
    assert_paciente_no_de_alta(db, pt_num)
    # Validar huella dactilar mediante motor biométrico (1:1 si viene medico_id)
    match_found = verificar_huella_medico(
        db=db,
        fmd_template=req.fmd_template,
        medico_id=req.medico_id,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="SUSPENSION",
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=_biometric_identity_from_request(request),
        patient_ref=str(pt_num),
        document_code="HE-DIRMED-SINPRO-SUSP-01",
    )
    _assert_fea_enabled(match_found)

    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="MEDICATION_DISCONTINUE",
        aggregate_type="patient_medication",
        aggregate_id=f"{pt_num}:{req.ptdg_num}",
        patient_ref=str(pt_num),
        payload={
            "act_id": hashlib.sha256(req.challenge_id.encode()).hexdigest(),
            "ptdg_num": req.ptdg_num,
            "reason": req.reason or "Indicación médica",
        },
    )
    if not created:
        return _existing_sync_response(operation)

    client_ip = request.client.host if request.client else "127.0.0.1"

    log = models.AuditoriaLog(

        usuario_id=None,

        accion="SUSPENSION_MEDICAMENTO_PTDG",

        detalles_json=json.dumps({

            "pt_num": str(pt_num),

            "ptdg_num": req.ptdg_num,

            "motivo": req.reason,

            "medico": match_found.nombre_completo,

            "cedula": match_found.cedula

        }),

        fecha_hora=datetime.datetime.now(),

        ip_origen=client_ip

    )

    db.add(log)

    clinical_sync.mark_local_applied(db, operation)
    result = clinical_sync.execute_external(
        db,
        operation,
        clinical_sync_adapters.dispatcher(operation),
        session_factory=SessionLocal,
    )
    return _sync_result_response(result, {

        "success": True,

        "message": f"Medicamento suspendido por {match_found.nombre_completo}."

    })



class PrescribirDietaInputSchema(BaseModel):
    tipo_dieta: str
    horario: Optional[str] = "Continuo"
    fase_clinica: Optional[str] = ""
    indicaciones_nutricionales: Optional[str] = ""
    inicio_ayuno_dieta: Optional[str] = ""
    nutriologo_responsable: Optional[str] = "Nutrición Clínica HES"
    alergias_alimentarias: Optional[str] = ""
    tolerancia_via_oral: Optional[str] = "Adecuada"
    cuidados_enfermeria: Optional[List[Dict[str, Any]]] = []
    fmd_template: str # Huella dactilar obligatoria
    medico_id: Optional[int] = None
    challenge_id: str
    session_id: str



@app.get("/api/ehr/paciente/{pt_num}/dieta-cuidados")

def get_paciente_dieta_cuidados(pt_num: str, db: Session = Depends(get_db)):

    """Consulta la prescripción dietética y cuidados de enfermería (PostgreSQL + Fallback SQL Server)."""

    # 1. Buscar en PostgreSQL (registro extendido con firma)

    dieta_pg = db.query(models.DietaCuidadosPrescripcion).filter(

        models.DietaCuidadosPrescripcion.pt_num == str(pt_num),

        models.DietaCuidadosPrescripcion.activo == True

    ).order_by(models.DietaCuidadosPrescripcion.fecha_hora_prescripcion.desc()).first()



    if dieta_pg:

        cuidados = []

        if dieta_pg.cuidados_enfermeria_json:

            try:

                cuidados = json.loads(dieta_pg.cuidados_enfermeria_json)

            except Exception:

                cuidados = []

        return {

            "source": "PostgreSQL (Bitácora HES)",

            "tipo": dieta_pg.tipo_dieta,

            "horario": dieta_pg.horario,

            "fase": dieta_pg.fase_clinica,

            "indicaciones": dieta_pg.indicaciones_nutricionales,

            "inicio": dieta_pg.inicio_ayuno_dieta,

            "nutriologo": dieta_pg.nutriologo_responsable,

            "alergias_alimentarias": dieta_pg.alergias_alimentarias,

            "tolerancia_via_oral": dieta_pg.tolerancia_via_oral,

            "cuidados_enfermeria": cuidados,

            "medico": dieta_pg.medico_nombre,

            "cedula": dieta_pg.medico_cedula,

            "fecha_prescripcion": dieta_pg.fecha_hora_prescripcion.strftime("%d/%m/%Y %H:%M") if dieta_pg.fecha_hora_prescripcion else "",

            "sello": dieta_pg.sello_digital[:32] + "..." if dieta_pg.sello_digital else ""

        }



    # 2. Fallback a SQL Server MR_SOL_DIET

    dieta_sql = kh_database.fetch_patient_diet_mr_sol_diet(pt_num)

    if dieta_sql and (dieta_sql.get("tipo") or dieta_sql.get("mrnum_sol_diet")):

        return {

            "source": "SQL Server (MR_SOL_DIET)",

            "tipo": dieta_sql.get("tipo", "Dieta Hospitalaria"),

            "horario": dieta_sql.get("horario", "--"),

            "fase": "--",

            "indicaciones": dieta_sql.get("detalle") or "Sin indicaciones registradas.",

            "inicio": dieta_sql.get("created_on") or "--",

            "nutriologo": dieta_sql.get("created_by") or "--",

            "alergias_alimentarias": dieta_sql.get("intolerancia") or "Ninguna registrada",

            "tolerancia_via_oral": "--",

            "cuidados_enfermeria": []

        }



    return {

        "source": "Ninguna",

        "tipo": "Sin dieta asignada",

        "horario": "--",

        "fase": "--",

        "indicaciones": "No se ha registrado régimen dietético para este paciente.",

        "inicio": "--",

        "nutriologo": "--",

        "alergias_alimentarias": "--",

        "tolerancia_via_oral": "--",

        "cuidados_enfermeria": []

    }



@app.post("/api/ehr/paciente/{pt_num}/dieta-cuidados/prescribir-biometrico")
def prescribir_dieta_cuidados_biometrico(
    pt_num: str,
    req: PrescribirDietaInputSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Prescribe formalmente el régimen dietético en SQL Server (MR_SOL_DIET) y almacena el plan de cuidados
    enriquecido en PostgreSQL con validación biométrica dactilar (NOM-004 / NOM-024).
    """
    assert_paciente_no_de_alta(db, pt_num)
    # 1. Validar huella dactilar mediante motor biométrico (1:1 si viene medico_id)
    match_found = verificar_huella_medico(
        db=db,
        fmd_template=req.fmd_template,
        medico_id=req.medico_id,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="DIETA",
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=_biometric_identity_from_request(request),
        patient_ref=str(pt_num),
        document_code="HE-DIRMED-SINPRO-DIETA-01",
    )
    _assert_fea_enabled(match_found)

    diet_payload = {
        "tipo": req.tipo_dieta,
        "horario": req.horario,
        "detalle": req.indicaciones_nutricionales or req.fase_clinica,
        "intolerancia": req.alergias_alimentarias,
    }
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="DIET_PRESCRIBE",
        aggregate_type="patient_diet",
        aggregate_id=f"{pt_num}:{req.challenge_id}",
        patient_ref=str(pt_num),
        payload={
            "act_id": hashlib.sha256(req.challenge_id.encode()).hexdigest(),
            "diet": diet_payload,
        },
    )
    if not created:
        return _existing_sync_response(operation)



    # 2. Generar Sello Digital HMAC-SHA512

    now = datetime.datetime.now()

    cadena_original = f"||{pt_num}|PT-{pt_num}|DIETA-MR_SOL_DIET|{req.tipo_dieta}|{req.fase_clinica}|{req.horario}|{now.isoformat()}|{match_found.id}|{match_found.cedula}||"

    hash_sha256 = hashlib.sha256(cadena_original.encode('utf-8')).hexdigest()



    sello_digital = crypto_fea.firmar_documento(db, match_found, cadena_original)



    # 3. Aplicar el estado clínico local antes de entregar a SQL Server.

    db.query(models.DietaCuidadosPrescripcion).filter(

        models.DietaCuidadosPrescripcion.pt_num == str(pt_num)

    ).update({"activo": False})



    # 5. Insertar en PostgreSQL (Bitácora HES)

    nueva_dieta = models.DietaCuidadosPrescripcion(

        pt_num=str(pt_num),

        expediente=f"PT-{pt_num}",

        tipo_dieta=req.tipo_dieta,

        horario=req.horario,

        fase_clinica=req.fase_clinica,

        indicaciones_nutricionales=req.indicaciones_nutricionales,

        inicio_ayuno_dieta=req.inicio_ayuno_dieta or now.strftime("%d/%m/%Y %H:%M"),

        nutriologo_responsable=req.nutriologo_responsable or "Nutrición Clínica HES",

        alergias_alimentarias=req.alergias_alimentarias,

        tolerancia_via_oral=req.tolerancia_via_oral,

        cuidados_enfermeria_json=json.dumps(req.cuidados_enfermeria or [], ensure_ascii=False),

        medico_id=match_found.id,

        medico_nombre=match_found.nombre_completo,

        medico_cedula=match_found.cedula,

        hash_sha256=hash_sha256,

        sello_digital=sello_digital,

        cadena_original=cadena_original,

        fecha_hora_prescripcion=now,

        activo=True,
        clinical_sync_operation_id=operation.operation_id,

    )

    db.add(nueva_dieta)



    # 6. Registrar en auditoría

    client_ip = request.client.host if request.client else "127.0.0.1"

    log = models.AuditoriaLog(

        usuario_id=None,

        accion="PRESCRIPCION_DIETA_Y_CUIDADOS",

        detalles_json=json.dumps({

            "pt_num": str(pt_num),

            "tipo_dieta": req.tipo_dieta,

            "horario": req.horario,

            "fase": req.fase_clinica,

            "medico": match_found.nombre_completo,

            "cedula": match_found.cedula,

            "operation_id": str(operation.operation_id)

        }),

        fecha_hora=now,

        ip_origen=client_ip

    )

    db.add(log)

    clinical_sync.mark_local_applied(db, operation)
    result = clinical_sync.execute_external(
        db,
        operation,
        clinical_sync_adapters.dispatcher(operation),
        session_factory=SessionLocal,
    )
    return _sync_result_response(result, {

        "success": True,

        "message": f"Régimen dietético '{req.tipo_dieta}' prescrito y firmado por {match_found.nombre_completo}.",

        "medico": match_found.nombre_completo,

        "cedula": match_found.cedula,

        "sello": sello_digital[:32] + "..."

    })



@app.get("/api/ehr/pacientes/buscar")

def buscar_pacientes_universal(q: str = "", limit: int = 30):

    """

    Buscador universal de pacientes (activos, hospitalizados y egresados/de alta) en Vertical SQL Server.

    Permite buscar por nombre, apellido, folio/expediente (PTNum) o CURP.

    """

    # Una consulta vacía no debe exponer el catálogo completo. El acceso
    # inicial a expedientes se resuelve desde el censo de camas físicas; este
    # endpoint se reserva para una búsqueda explícita por nombre/folio/CURP.
    if not str(q or "").strip():
        return []
    return kh_database.search_patients_kh(query_text=q, limit=limit)



# ==========================================

# ENDPOINTS ALERGIAS (PTAL + DIS_AL)

# ==========================================



class RegistrarAlergiaInputSchema(BaseModel):

    allergy_num: str

    allergic_since: Optional[str] = None

    notes: Optional[str] = ""

    user: Optional[str] = None



class InactivarAlergiaInputSchema(BaseModel):

    ptal_num: int

    user: Optional[str] = None



@app.get("/api/ehr/alergias/catalogo")

def obtener_catalogo_alergias(q: str = "", limit: int = 50):

    """

    Consulta el catálogo maestro de alergias de Vertical (DIS_AL).

    """

    return kh_database.fetch_allergy_catalog(search_query=q, limit=limit)



@app.get("/api/ehr/paciente/{pt_num}/alergias")

def obtener_alergias_paciente(pt_num: str):

    """

    Consulta las alergias activas del paciente registradas en SQL Server (PTAL).

    """

    return kh_database.fetch_patient_allergies_ptal(pt_num)



@app.post("/api/ehr/paciente/{pt_num}/alergias/registrar")
def registrar_alergia_paciente(
    pt_num: str, 
    req: RegistrarAlergiaInputSchema, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Registra una nueva alergia para el paciente en Vertical (PTAL).
    """
    assert_paciente_no_de_alta(db, pt_num)
    if not req.allergy_num:
        raise HTTPException(status_code=400, detail="Debe seleccionar una alergia del catálogo.")
    
    usuario = req.user or "jose_prueba"
    return _durable_audited_kh_write(
        db,
        request,
        pt_num=pt_num,
        adapter="save_patient_allergy_ptal",
        args=[],
        kwargs={
            "pt_num": str(pt_num),
            "allergy_num": req.allergy_num,
            "allergic_since": req.allergic_since,
            "notes": req.notes or "",
            "user": usuario,
        },
        aggregate_id=f"{pt_num}:allergy:{req.allergy_num}:{req.allergic_since or ''}",
        audit_action="CREACION_ALERGIA_PTAL",
        audit_details={
            "pt_num": str(pt_num),
            "allergy_num": req.allergy_num,
            "allergic_since": req.allergic_since,
            "notes": req.notes,
        },
        success_body={"message": "Alergia registrada correctamente"},
    )

    # Auditoría Forense
    auditoria = models.AuditoriaLog(
        tipo_accion="CREACION",
        modulo="ALERGIAS_PTAL",
        usuario=usuario,
        paciente_id=str(pt_num),
        ip_origen=request.client.host if request.client else "127.0.0.1",
        detalles_json={
            "accion": "Registro de alergia en PTAL",
            "allergy_num": req.allergy_num,
            "allergic_since": req.allergic_since,
            "notes": req.notes,
            "ptal_id": res.get("ptal_id")
        }
    )
    db.add(auditoria)
    db.commit()

    return res


@app.post("/api/ehr/paciente/{pt_num}/alergias/inactivar")
def inactivar_alergia_paciente(
    pt_num: str, 
    req: InactivarAlergiaInputSchema, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Inactiva una alergia del paciente en Vertical (PTAL).
    """
    assert_paciente_no_de_alta(db, pt_num)
    usuario = req.user or "jose_prueba"
    return _durable_audited_kh_write(
        db,
        request,
        pt_num=pt_num,
        adapter="inactivate_patient_allergy_ptal",
        args=[],
        kwargs={"pt_num": str(pt_num), "ptal_num": req.ptal_num, "user": usuario},
        aggregate_id=f"{pt_num}:allergy:{req.ptal_num}:inactive",
        audit_action="INACTIVACION_ALERGIA_PTAL",
        audit_details={"pt_num": str(pt_num), "ptal_num": req.ptal_num},
        success_body={"message": "Alergia inactivada correctamente"},
    )

    # Auditoría Forense
    auditoria = models.AuditoriaLog(
        tipo_accion="ELIMINACION",
        modulo="ALERGIAS_PTAL",
        usuario=usuario,
        paciente_id=str(pt_num),
        ip_origen=request.client.host if request.client else "127.0.0.1",
        detalles_json={
            "accion": "Inactivación de alergia en PTAL",
            "ptal_num": req.ptal_num
        }
    )
    db.add(auditoria)
    db.commit()

    return res


class ActualizarTextoAlergiasInputSchema(BaseModel):
    allergies_text: str
    user: Optional[str] = None


@app.post("/api/ehr/paciente/{pt_num}/alergias/actualizar-texto")
def actualizar_texto_alergias_paciente(
    pt_num: str, 
    req: ActualizarTextoAlergiasInputSchema, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Actualiza el texto consolidado de ALERGIAS en MR_NE_URG y MR_SOL_DIET de Vertical.
    """
    assert_paciente_no_de_alta(db, pt_num)
    usuario = req.user or "jose_prueba"
    return _durable_audited_kh_write(
        db,
        request,
        pt_num=pt_num,
        adapter="update_patient_allergies_text",
        args=[],
        kwargs={
            "pt_num": str(pt_num),
            "allergies_text": req.allergies_text,
            "user": usuario,
        },
        aggregate_id=f"{pt_num}:allergy-text:{hashlib.sha256(req.allergies_text.encode()).hexdigest()}",
        audit_action="ACTUALIZACION_TEXTO_ALERGIAS",
        audit_details={"pt_num": str(pt_num), "allergies_text": req.allergies_text},
        success_body={"message": "Texto de alergias actualizado correctamente"},
    )

    # Auditoría Forense
    auditoria = models.AuditoriaLog(
        tipo_accion="ACTUALIZACION",
        modulo="ALERGIAS_TEXTO",
        usuario=usuario,
        paciente_id=str(pt_num),
        ip_origen=request.client.host if request.client else "127.0.0.1",
        detalles_json={
            "accion": "Actualización manual de texto de alergias en MR_NE_URG / MR_SOL_DIET",
            "allergies_text": req.allergies_text
        }
    )
    db.add(auditoria)
    db.commit()

    return res


class FirmaBiometricaInputSchema(BaseModel):
    codigo_formato: str = "HE-DIRMED-SINPRO-PLT-87/01"
    tipo_documento: str = "Nota de Evolución de Urgencias (87/01)"
    evolution_slot: Optional[int] = 1
    fmd_template: str
    medico_id: Optional[int] = None
    challenge_id: str
    session_id: str

@app.post("/api/ehr/paciente/{pt_num}/firmar-biometrico")
def firmar_documento_biometrico(
    pt_num: str, 
    req: FirmaBiometricaInputSchema, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    """
    Firma electrónicamente una nota o consentimiento mediante Biometría Dactilar DigitalPersona,
    generando sello digital y registro con FECHA Y HORA LOCAL EXACTA conforme a la NOM-004-SSA3-2012 y NOM-024-SSA3-2012.
    """
    # 1. Validar huella dactilar mediante motor biométrico (1:1 si viene medico_id)
    match_found = verificar_huella_medico(
        db=db,
        fmd_template=req.fmd_template,
        medico_id=req.medico_id,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="FIRMA_MEDICA",
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=_biometric_identity_from_request(request),
        patient_ref=str(pt_num),
        document_code=req.codigo_formato,
        document_ref=str(req.evolution_slot or 0),
    )
    require_format(match_found, req.codigo_formato)
    _assert_fea_enabled(match_found)

        

    # 2. Fecha y hora exacta local (sin desfase UTC)

    target_slot = int(req.evolution_slot) if req.evolution_slot is not None else 0

    # El servidor obtiene el documento completo y construye los bytes firmados.
    # Ningún resumen, texto o hash enviado por el navegador participa.
    signed_at = datetime.datetime.now(clinical_signing.MEXICO_CITY)
    now = signed_at.replace(tzinfo=None)
    fecha_legible = signed_at.strftime("%d/%m/%Y %H:%M:%S %z")
    try:
        document, patient_identity = clinical_signing.load_document_after_capture(
            db,
            pt_num=str(pt_num),
            codigo_formato=req.codigo_formato,
            evolution_slot=target_slot,
            requested_type=req.tipo_documento,
        )
    except clinical_signing.ClinicalDocumentUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    clinical_signing.assert_document_author(document, match_found)
    document_lock_key = "|".join((
        "signature-document",
        str(pt_num).removeprefix("PT-"),
        req.codigo_formato,
        str(target_slot),
    ))
    db.execute(
        sql_text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": document_lock_key},
    )
    try:
        requires_authorization = clinical_signing.requires_consent_signers(req.codigo_formato)
    except clinical_signing.ClinicalDocumentUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if requires_authorization:
        consent = obtener_firmas_completas_documento(
            db, str(pt_num), req.codigo_formato, target_slot, current_document=document,
        )
        required_witnesses = clinical_signing.required_consent_witnesses_for_authorizer(
            req.codigo_formato, consent.get("rol_firmante_paciente")
        )
        if not clinical_signing.consent_signatures_complete(
            consent, required_witnesses=required_witnesses
        ):
            witness_text = {
                0: "",
                1: " y un testigo",
                2: " y dos testigos",
            }[required_witnesses]
            raise HTTPException(
                status_code=409,
                detail=f"Complete la autorización del paciente o representante{witness_text} de esta versión antes del cierre médico.",
            )

    def existing_unsynced_medical_signature():
        patient_number = str(pt_num).removeprefix("PT-")
        active_signatures = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num.in_((patient_number, f"PT-{patient_number}")),
            models.FirmaDocumentoClinico.codigo_formato == req.codigo_formato,
            models.FirmaDocumentoClinico.evolution_slot == target_slot,
            models.FirmaDocumentoClinico.rol_firmante == "MEDICO",
            models.FirmaDocumentoClinico.estado == "ACTIVA",
        ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()
        for previous in active_signatures:
            if not previous.clinical_sync_operation_id:
                continue
            if str(previous.document_version) != str(document.version_documento):
                continue
            try:
                previous_payload, _ = clinical_signing.parse_and_validate_snapshot(
                    previous.canonical_payload, previous.payload_hash
                )
            except (clinical_signing.CanonicalPayloadError, AttributeError, TypeError):
                # An existing unconfirmed signature with damaged evidence still
                # needs review; do not replace it by capturing the doctor again.
                previous_payload = None
            if previous_payload is not None and (
                previous_payload.get("source_identifier") != document.source_identifier
            ):
                continue
            previous_operation = db.get(
                models.ClinicalSyncOperation, previous.clinical_sync_operation_id
            )
            if previous_operation and previous_operation.state != clinical_sync.SYNCED:
                return previous_operation
        return None

    previous_operation = existing_unsynced_medical_signature()
    if previous_operation is not None:
        return _existing_sync_response(previous_operation)

    active_key = crypto_fea.get_active_key(db, match_found)
    payload, payload_bytes, hash_sha256, pdf_hash = clinical_signing.build_canonical_payload(
        document=document,
        codigo_formato=req.codigo_formato,
        pt_num=str(pt_num),
        expediente=f"PT-{str(pt_num).removeprefix('PT-')}",
        evolution_slot=target_slot,
        patient_identity=patient_identity,
        medico_id=match_found.id,
        nombre_medico=match_found.nombre_completo,
        cedula=match_found.cedula,
        proposito="CIERRE_Y_AUTORIA_CLINICA",
        signed_at=signed_at,
        key_id=active_key.key_id,
    )
    canonical_payload = payload_bytes.decode("utf-8")
    signature_result = crypto_fea.firmar_documento_con_key_id(db, match_found, payload_bytes)
    if signature_result.key_id != active_key.key_id:
        raise HTTPException(status_code=409, detail="La llave FEA activa cambió durante la firma")
    sello_digital = signature_result.sello_digital
    tsa_info = tsa_client.get_timestamp(hash_sha256) or {
        "status": tsa_client.TSA_PENDIENTE,
        "token_b64": None,
        "nonce": None,
        "error": "TSA no disponible",
        "verificado": False,
    }

    controller_name, target_mr = _resolve_vertical_sign_target(
        str(pt_num), req.codigo_formato, target_slot, document
    )
    operation, created = _clinical_sync_intent(
        db,
        request,
        operation_type="VERTICAL_SIGN",
        aggregate_type="clinical_document",
        aggregate_id=f"{pt_num}:{req.codigo_formato}:{target_slot}",
        patient_ref=str(pt_num),
        payload={
            "act_id": hashlib.sha256(req.challenge_id.encode()).hexdigest(),
            "controller_name": controller_name,
            "mrnum": target_mr,
            "codigo_formato": req.codigo_formato,
            "target_slot": target_slot,
            "doctor_name": match_found.nombre_completo,
            "doctor_cedula": match_found.cedula,
            "document_digest": clinical_signing.document_digest(document),
        },
    )
    if not created:
        return _existing_sync_response(operation)

    # Serialize the logical document independently of challenge/idempotency key.
    # The partial unique index remains the final database invariant.
    db.execute(
        sql_text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": document_lock_key},
    )

    previous_operation = existing_unsynced_medical_signature()
    if previous_operation is not None:
        operation.state = clinical_sync.FAILED
        operation.last_error = "DUPLICATE_PENDING_SIGNATURE"
        operation.completed_at = clinical_sync.utcnow()
        operation.updated_at = operation.completed_at
        db.commit()
        return _existing_sync_response(previous_operation)
    closure_evidence = None
    if requires_authorization:
        current_consent = obtener_firmas_completas_documento(
            db, str(pt_num), req.codigo_formato, target_slot, current_document=document,
        )
        current_witnesses = clinical_signing.required_consent_witnesses_for_authorizer(
            req.codigo_formato, current_consent.get("rol_firmante_paciente")
        )
        if not clinical_signing.consent_signatures_complete(
            current_consent, required_witnesses=current_witnesses
        ):
            operation.state = clinical_sync.FAILED
            operation.last_error = "CONSENT_CHANGED_BEFORE_MEDICAL_CLOSURE"
            operation.completed_at = clinical_sync.utcnow()
            operation.updated_at = operation.completed_at
            db.commit()
            raise HTTPException(
                status_code=409,
                detail="Las firmas de autorización cambiaron. Revise este documento antes del cierre médico.",
            )
        expected_witnesses = clinical_signing.required_consent_witnesses(req.codigo_formato)
        signed_witnesses = clinical_signing.signed_witness_count(current_consent)
        closure_evidence = {
            "pt_num": str(pt_num),
            "codigo_formato": req.codigo_formato,
            "evolution_slot": target_slot,
            "document_digest": clinical_signing.document_digest(document),
            "medico_id": match_found.id,
            "autorizante_id": current_consent.get("firmante_paciente_id"),
            "autorizante_rol": current_consent.get("rol_firmante_paciente"),
            "testigo_1_id": current_consent.get("firmante_testigo1_id"),
            "testigo_2_id": current_consent.get("firmante_testigo2_id"),
            "testigos_esperados": expected_witnesses,
            "testigos_firmados": signed_witnesses,
            "testigos_minimos_cierre": current_witnesses,
            "cierre_excepcional_por_testigos": signed_witnesses < expected_witnesses,
        }

    # 2.5 Revocar firmas médicas previas activas para este mismo formato y slot (NOM-024)
    # IMPORTANTE: Preservar firmas activas del Paciente, Tutor y Testigos conforme a la NOM-004-SSA3-2012
    firmas_antiguas_medico = db.query(models.FirmaDocumentoClinico).filter(
        (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_num}"),
        models.FirmaDocumentoClinico.codigo_formato == req.codigo_formato,
        models.FirmaDocumentoClinico.evolution_slot == target_slot,
        (models.FirmaDocumentoClinico.rol_firmante == "MEDICO") | (models.FirmaDocumentoClinico.rol_firmante == None),
        models.FirmaDocumentoClinico.estado == "ACTIVA"
    ).all()
    for fa in firmas_antiguas_medico:
        fa.estado = "REVOCADA"
        fa.fecha_revocacion = now
        fa.motivo_revocacion = "Refirma del documento por el médico"

    # 3. Guardar en PostgreSQL
    client_ip = request.client.host if request.client else "127.0.0.1"
    firma_registro = models.FirmaDocumentoClinico(
        tipo_documento=document.tipo_documento,
        codigo_formato=req.codigo_formato,
        pt_num=str(pt_num),
        expediente=f"PT-{pt_num}",
        evolution_slot=target_slot,
        rol_firmante="MEDICO",
        medico_id=match_found.id,
        nombre_medico=match_found.nombre_completo,
        cedula_profesional=match_found.cedula,
        fecha_hora_firma=now,
        metodo_autenticacion="Biometría Dactilar DigitalPersona (NOM-004/NOM-024-SSA3)",
        hash_sha256=hash_sha256,
        sello_digital=sello_digital,
        cadena_original=canonical_payload,
        ip_origen=client_ip,
        tsa_token=tsa_info.get('token_b64'),
        key_id=signature_result.key_id,
        signature_schema_version=clinical_signing.SCHEMA_VERSION,
        canonical_payload=canonical_payload,
        payload_hash=hash_sha256,
        document_version=document.version_documento,
        pdf_hash=pdf_hash,
        pdf_identifier=document.pdf_identifier,
        tsa_status=tsa_info.get("status", tsa_client.TSA_PENDIENTE),
        tsa_nonce=tsa_info.get("nonce"),
        tsa_attempts=1,
        tsa_last_error=tsa_info.get("error"),
        tsa_verified_at=now if tsa_info.get("verificado") else None,
        clinical_sync_operation_id=operation.operation_id,
    )
    db.add(firma_registro)
    try:
        db.flush()
        if closure_evidence is not None:
            actor = _biometric_subject_from_request(request) or f"medico:{match_found.id}"
            db.add(models.AuditoriaLog(
                usuario_id=None,
                accion="CIERRE_MEDICO_CONSENTIMIENTO",
                detalles_json=json.dumps(
                    {**closure_evidence, "firma_id": firma_registro.id},
                    ensure_ascii=False,
                ),
                request_id=getattr(request.state, "request_id", None) or str(uuid.uuid4()),
                operation_id=str(operation.operation_id),
                actor_real=actor,
                actor_effective=actor,
                ip_origen=client_ip,
            ))
        clinical_sync.mark_local_applied(db, operation)
    except IntegrityError as exc:
        db.rollback()
        pending = db.query(models.ClinicalSyncOperation).filter(
            models.ClinicalSyncOperation.operation_id == operation.operation_id
        ).one()
        pending.state = clinical_sync.FAILED
        pending.last_error = "ACTIVE_SIGNATURE_CONFLICT"
        pending.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="Ya existe una firma activa para el mismo documento lógico.",
        ) from exc
    db.refresh(firma_registro)

    result = clinical_sync.execute_external(
        db,
        operation,
        clinical_sync_adapters.dispatcher(operation),
        session_factory=SessionLocal,
    )
    return _sync_result_response(result, {
        "success": True,
        "message": "Firma médica registrada para el documento seleccionado. Consulte por separado el estado TSA y la sincronización con Vertical.",
        "firma": {
            "id": firma_registro.id,
            "nombre_medico": match_found.nombre_completo,
            "cedula": match_found.cedula,
            "fecha_hora": now.strftime("%d/%m/%Y %H:%M:%S"),
            "hash_sha256": hash_sha256,
            "sello_digital": sello_digital,
            "key_id": signature_result.key_id,
            "signature_schema_version": clinical_signing.SCHEMA_VERSION,
            "tsa_status": tsa_info.get("status"),
            "tsa_gen_time": tsa_info.get('gen_time'),
            "normativa": "NOM-004-SSA3-2012 / NOM-024-SSA3-2012"
        }
    })


@app.post("/api/firmas/{firma_id}/tsa/reintentar")
def reintentar_tsa_firma(
    firma_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "medico", "ayudante"])),
):
    """Idempotently countersign the existing payload hash without changing ECDSA."""
    firma = db.query(models.FirmaDocumentoClinico).filter(
        models.FirmaDocumentoClinico.id == firma_id
    ).with_for_update().first()
    if not firma:
        raise HTTPException(status_code=404, detail="Firma no encontrada")
    require_format(current_user, firma.codigo_formato)
    if firma.signature_schema_version != clinical_signing.SCHEMA_VERSION or not firma.payload_hash:
        raise HTTPException(status_code=409, detail="La firma legacy no admite sellado TSA CANONICAL_V2")
    if firma.tsa_status == tsa_client.TSA_VERIFICADO:
        return {
            "firma_id": firma.id,
            "tsa_status": firma.tsa_status,
            "idempotent": True,
        }

    original_signature = firma.sello_digital
    tsa_info = tsa_client.get_timestamp(firma.payload_hash)
    firma.tsa_attempts = int(firma.tsa_attempts or 0) + 1
    firma.tsa_status = tsa_info.get("status", tsa_client.TSA_PENDIENTE)
    firma.tsa_token = tsa_info.get("token_b64")
    firma.tsa_nonce = tsa_info.get("nonce")
    firma.tsa_last_error = tsa_info.get("error")
    firma.tsa_verified_at = (
        datetime.datetime.now() if tsa_info.get("verificado") else None
    )
    if firma.sello_digital != original_signature:
        db.rollback()
        raise HTTPException(status_code=500, detail="La ECDSA original no puede modificarse durante el reintento TSA")
    db.commit()
    return {
        "firma_id": firma.id,
        "tsa_status": firma.tsa_status,
        "tsa_attempts": firma.tsa_attempts,
        "ecdsa_original_preservada": True,
    }


@app.post("/api/ehr/paciente/{pt_num}/firmar-biometrico-firmante")
@app.post("/ehr/paciente/{pt_num}/firmar-biometrico-firmante")
@app.post("/api/pacientes/{pt_num}/firmar-biometrico-firmante")
@app.post("/pacientes/{pt_num}/firmar-biometrico-firmante")
def firmar_documento_biometrico_firmante(
    pt_num: str,
    req: schemas.FirmaBiometricaFirmanteInputSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Firma electrónicamente un consentimiento o formato clínico mediante la biometría dactilar 
    del paciente, tutor/representante legal o testigo presencial conforme a la NOM-004-SSA3-2012.
    """
    assert_paciente_no_de_alta(db, pt_num)
    paciente = get_or_create_paciente_by_identifier(db, pt_num)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    document_role = (req.rol_firmante or "").strip().upper()
    if document_role not in {"PACIENTE", "REPRESENTANTE_LEGAL", "TUTOR", "FAMILIAR", "TESTIGO_1", "TESTIGO_2"}:
        raise HTTPException(status_code=422, detail="Seleccione el lugar que ocupará esta persona en el documento.")

    # 1. Validar la huella dactilar del firmante contra las plantillas enroladas del episodio
    firmante = verificar_huella_firmante_episodio(
        db=db,
        paciente_id=paciente.id,
        fmd_template=req.fmd_template,
        firmante_id=req.firmante_id,
        document_role=document_role,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action="FIRMA_FIRMANTE",
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=f"firmante:{req.firmante_id}",
        patient_ref=str(pt_num),
        document_code=req.codigo_formato,
        document_ref=str(req.evolution_slot or 0),
    )

    signed_at = datetime.datetime.now(clinical_signing.MEXICO_CITY)
    now = signed_at.replace(tzinfo=None)
    fecha_legible = signed_at.strftime("%d/%m/%Y %H:%M:%S %z")

    # 2. Evidencia de autenticación biométrica del acto. No es una FEA
    # personal del paciente/tutor/testigo y no se presenta como tal.
    # Persist the role selected for this document, not the person's permanent
    # episode profile (a family member may act as a witness without changing it).
    rol_desc = document_role
    target_slot = int(req.evolution_slot) if req.evolution_slot is not None else 0
    try:
        document, patient_identity = clinical_signing.load_document_after_capture(
            db,
            pt_num=str(pt_num),
            codigo_formato=req.codigo_formato,
            evolution_slot=target_slot,
            requested_type=req.tipo_documento,
        )
    except clinical_signing.ClinicalDocumentUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if clinical_signing.explicit_patient_capacity(document) is False and document_role == "PACIENTE":
        raise HTTPException(status_code=409, detail="Este documento indica que debe autorizar un familiar, tutor o representante.")
    db.execute(sql_text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {
        "key": f"signature-document|{str(pt_num).removeprefix('PT-')}|{req.codigo_formato}|{target_slot}",
    })
    try:
        requires_authorization = clinical_signing.requires_consent_signers(req.codigo_formato)
    except clinical_signing.ClinicalDocumentUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not requires_authorization:
        raise HTTPException(status_code=409, detail="Este formato no tiene un circuito de firma de paciente o testigos configurado.")
    current_signatures = obtener_firmas_completas_documento(
        db, str(pt_num), req.codigo_formato, target_slot, current_document=document,
    )
    witness_slots = clinical_signing.required_consent_witnesses(req.codigo_formato)
    authorizer_id = current_signatures.get("firmante_paciente_id")
    first_witness_id = current_signatures.get("firmante_testigo1_id")
    second_witness_id = current_signatures.get("firmante_testigo2_id")
    if document_role in {"TESTIGO_1", "TESTIGO_2"}:
        if not authorizer_id:
            raise HTTPException(status_code=409, detail="Primero debe firmar el paciente o su representante.")
        if (document_role == "TESTIGO_1" and witness_slots < 1) or (
            document_role == "TESTIGO_2" and witness_slots < 2
        ):
            raise HTTPException(status_code=409, detail="Este documento no requiere ese lugar de testigo.")
        occupied_id = first_witness_id if document_role == "TESTIGO_1" else second_witness_id
        if occupied_id:
            raise HTTPException(status_code=409, detail="Este lugar de testigo ya tiene una firma registrada.")
        other_witness_id = second_witness_id if document_role == "TESTIGO_1" else first_witness_id
        if firmante.id in {authorizer_id, other_witness_id}:
            raise HTTPException(status_code=409, detail="Una persona no puede firmar dos veces con papeles distintos en el mismo documento.")
    else:
        if authorizer_id:
            raise HTTPException(status_code=409, detail="Este documento ya tiene la firma de quien lo autoriza.")
        if firmante.id in {first_witness_id, second_witness_id}:
            raise HTTPException(status_code=409, detail="Quien autoriza el documento no puede figurar también como testigo.")
    _, evidence_bytes, hash_sha256 = clinical_signing.build_biometric_evidence_payload(
        document=document,
        codigo_formato=req.codigo_formato,
        pt_num=str(pt_num),
        expediente=f"PT-{str(pt_num).removeprefix('PT-')}",
        evolution_slot=target_slot,
        patient_identity=patient_identity,
        firmante_id=firmante.id,
        rol_firmante=rol_desc,
        nombre_firmante=firmante.nombre_completo,
        identificacion=firmante.identificacion_oficial,
        signed_at=signed_at,
    )
    cadena_original = evidence_bytes.decode("utf-8")
    sello_biometrico = f"EVIDENCIA_BIOMETRICA_NO_FEA:{uuid.uuid4()}"
    # 3. Revocar firmas previas activas de este mismo rol/firmante para este formato y slot
    firmas_antiguas = db.query(models.FirmaDocumentoClinico).filter(
        (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | (models.FirmaDocumentoClinico.pt_num == str(paciente.codigo_barras)),
        models.FirmaDocumentoClinico.codigo_formato == req.codigo_formato,
        models.FirmaDocumentoClinico.evolution_slot == target_slot,
        models.FirmaDocumentoClinico.rol_firmante == rol_desc,
        models.FirmaDocumentoClinico.estado == "ACTIVA"
    ).all()
    for fa in firmas_antiguas:
        fa.estado = "REVOCADA"
        fa.fecha_revocacion = now
        fa.motivo_revocacion = f"Refirma por {firmante.nombre_completo}"

    # 4. Guardar en PostgreSQL
    client_ip = request.client.host if (request and getattr(request, 'client', None)) else "127.0.0.1"
    firma_registro = models.FirmaDocumentoClinico(
        tipo_documento=document.tipo_documento,
        codigo_formato=req.codigo_formato,
        pt_num=str(paciente.codigo_barras or pt_num),
        expediente=f"PT-{paciente.codigo_barras or pt_num}",
        evolution_slot=target_slot,
        rol_firmante=rol_desc,
        firmante_id=firmante.id,
        medico_id=None,
        nombre_medico=firmante.nombre_completo,
        cedula_profesional=firmante.identificacion_oficial or "IDENTIFICACION OFICIAL",
        fecha_hora_firma=now,
        metodo_autenticacion=f"Biometría Dactilar Firmante ({rol_desc} - NOM-004-SSA3)",
        hash_sha256=hash_sha256,
        sello_digital=sello_biometrico,
        cadena_original=cadena_original,
        ip_origen=client_ip,
        signature_schema_version=clinical_signing.BIOMETRIC_EVIDENCE_VERSION,
        canonical_payload=cadena_original,
        payload_hash=hash_sha256,
        document_version=document.version_documento,
        tsa_status=tsa_client.SIN_TSA,
    )
    db.add(firma_registro)
    db.flush()
    state_user = getattr(request.state, "user", None) if request else None
    db.add(
        models.AuditoriaLog(
            usuario_id=(state_user or {}).get("id") if isinstance(state_user, dict)
                and normalize_role(state_user.get("rol")) not in {"medico", "ayudante"} else None,
            actor_real=_biometric_subject_from_request(request) or "sistema",
            actor_effective=_biometric_subject_from_request(request) or "sistema",
            accion="EVIDENCIA_BIOMETRICA_ACTO_NO_FEA",
            detalles_json=json.dumps(
                {
                    "firma_id": firma_registro.id,
                    "pt_num": str(paciente.codigo_barras or pt_num),
                    "codigo_formato": req.codigo_formato,
                    "evolution_slot": target_slot,
                    "firmante_id": firmante.id,
                    "rol_firmante": rol_desc,
                    "payload_hash": hash_sha256,
                    "naturaleza": "AUTENTICACION_BIOMETRICA_Y_EVIDENCIA_DE_ACTO_NO_FEA_PERSONAL",
                },
                ensure_ascii=False,
            ),
            ip_origen=client_ip,
        )
    )
    db.commit()
    db.refresh(firma_registro)

    return {
        "success": True,
        "message": f"Autenticación biométrica y evidencia de acto de {firmante.nombre_completo} ({rol_desc}) registrada; no equivale a FEA personal.",
        "firma": {
            "id": firma_registro.id,
            "rol_firmante": rol_desc,
            "firmante_id": firmante.id,
            "nombre_firmante": firmante.nombre_completo,
            "parentesco": firmante.parentesco,
            "identificacion": firmante.identificacion_oficial,
            "domicilio": firmante.domicilio,
            "fecha_hora": fecha_legible,
            "hash_sha256": hash_sha256,
            "sello_digital": sello_biometrico,
            "signature_schema_version": clinical_signing.BIOMETRIC_EVIDENCE_VERSION,
            "naturaleza": "AUTENTICACION_BIOMETRICA_Y_EVIDENCIA_DE_ACTO_NO_FEA_PERSONAL",
            "normativa": "NOM-004-SSA3-2012 / NOM-024-SSA3-2012"
        }
    }


@app.get("/api/ehr/banco-sangre/firmantes")
def listar_firmantes_banco_sangre(
    codigo_formato: str = Query(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """Compatibilidad con la lista anterior de Banco de Sangre."""
    require_format(current_user, codigo_formato)
    if "BANCO_SANGRE" not in clinical_signing.special_signature_requirements(codigo_formato):
        raise HTTPException(409, "Este formato no solicita firma de Banco de Sangre.")
    return listar_firmantes_especiales(codigo_formato, "BANCO_SANGRE", db, current_user)


@app.get("/api/ehr/firmantes-especiales")
def listar_firmantes_especiales(
    codigo_formato: str = Query(...),
    rol_firmante: str = Query(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """Lista sólo cuentas enroladas y autorizadas para el área declarada por el formato."""
    role = str(rol_firmante or "").strip().upper()
    require_special_signature_access(current_user, codigo_formato, role)
    if role not in clinical_signing.special_signature_requirements(codigo_formato):
        raise HTTPException(409, "Este formato no solicita el área de firma seleccionada.")
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.activo == True,
        models.Usuario.biometric_status == "FMD_VALIDO",
    ).order_by(models.Usuario.nombre_completo, models.Usuario.username).all()
    return [
        {
            "id": usuario.id,
            "username": usuario.username,
            "nombre_completo": usuario.nombre_completo or usuario.username,
            "biometric_status": usuario.biometric_status,
            "tiene_huella": True,
        }
        for usuario in usuarios
        if is_clinical_signature_operator(current_user) or usuario.id == current_user.id
        if can_sign_format(usuario, codigo_formato, role)
        and biometric_security.detect_template_state(usuario.fmd_template).canonical
    ]


@app.get("/api/firmas-area")
def get_area_signature_queue(
    estado: str = Query("pendientes", pattern="^(pendientes|historial)$"),
    cursor: str = Query("", max_length=80),
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    import area_signatures
    try:
        return area_signatures.queue(db, current_user, estado, cursor)
    except clinical_signing.ClinicalDocumentUnavailable as exc:
        raise HTTPException(503, "No se pudo actualizar la bandeja. Reintente para confirmar los pendientes.") from exc


@app.get("/api/firmas-area/documento")
def get_area_signature_document(
    pt_num: str = Query(..., pattern="^(PT-)?[0-9]+$"),
    codigo_formato: str = Query(...), slot: int = Query(..., gt=0),
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    import area_signatures
    try:
        return area_signatures.document_detail(db, current_user, pt_num.removeprefix("PT-"), codigo_formato, slot)
    except clinical_signing.ClinicalDocumentUnavailable as exc:
        raise HTTPException(503, "No se pudo comprobar el documento actual. Reintente antes de firmar.") from exc


@app.post("/api/ehr/paciente/{pt_num}/firmar-biometrico-especial")
@app.post("/api/ehr/paciente/{pt_num}/firmar-biometrico-banco-sangre")
def firmar_documento_biometrico_especial(
    pt_num: str,
    req: schemas.FirmaBiometricaEspecialInputSchema,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """Guarda evidencia biométrica de un área requerida por el formato; no es FEA."""
    legacy_bank = request.url.path.endswith("firmar-biometrico-banco-sangre")
    role = str(req.rol_firmante or ("BANCO_SANGRE" if legacy_bank else "")).strip().upper()
    require_special_signature_access(current_user, req.codigo_formato, role, req.usuario_firmante_id, write=True)
    assert_paciente_no_de_alta(db, pt_num)
    if role not in clinical_signing.special_signature_requirements(req.codigo_formato):
        raise HTTPException(409, "Este formato no solicita el área de firma seleccionada.")
    paciente = get_or_create_paciente_by_identifier(db, pt_num)
    if not paciente:
        raise HTTPException(404, "Paciente no encontrado.")
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == req.usuario_firmante_id,
        models.Usuario.activo == True,
        models.Usuario.biometric_status == "FMD_VALIDO",
    ).first()
    if not usuario or not can_sign_format(usuario, req.codigo_formato, role) or not biometric_security.detect_template_state(usuario.fmd_template).canonical:
        raise HTTPException(409, "La cuenta seleccionada no tiene una huella vigente y autorización para este formato.")

    identity_ref = f"banco_sangre:{usuario.id}" if legacy_bank else f"usuario_especial:{usuario.id}|role:{role}"
    action = "FIRMA_BANCO_SANGRE" if legacy_bank else "FIRMA_USUARIO_ESPECIAL"

    capture = biometric_security.validate_attested_capture_evidence(
        req.fmd_template, req.challenge_id, req.session_id,
    )
    validate_and_consume_challenge(
        db,
        challenge_id=req.challenge_id,
        session_id=req.session_id,
        action=action,
        subject_ref=_biometric_subject_from_request(request),
        expected_identity_ref=identity_ref,
        patient_ref=str(pt_num),
        document_code=req.codigo_formato,
        document_ref=str(req.evolution_slot or 0),
        acquisition=capture,
    )
    matched_id = biometric_security.verify_attested_match(
        capture, [{"id": usuario.id, "fmd_template": usuario.fmd_template}],
        "banco_sangre" if legacy_bank else "usuario_especial",
    )
    if matched_id != usuario.id:
        raise HTTPException(403, "La huella no corresponde al usuario seleccionado.")

    target_slot = int(req.evolution_slot or 0)
    try:
        document, patient_identity = clinical_signing.load_document_after_capture(
            db,
            pt_num=str(pt_num),
            codigo_formato=req.codigo_formato,
            evolution_slot=target_slot,
            requested_type=req.tipo_documento,
        )
    except clinical_signing.ClinicalDocumentUnavailable as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    # Lock the source record even if another caller used a code alias or the
    # legacy slot=0 (latest record). Recheck under the lock before inserting.
    import area_signatures
    db.execute(sql_text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {
        "key": f"signature-area|{str(pt_num).removeprefix('PT-')}|{document.source_identifier}|{role}",
    })
    previous_rows = area_signatures.signature_rows(db, pt_num, req.codigo_formato, role)
    previous_history = area_signatures.signature_history(db, previous_rows, document)
    if any(row["vigente"] for row in previous_history):
        raise HTTPException(409, "El área seleccionada ya tiene una firma vigente para este documento.")

    signed_at = datetime.datetime.now(clinical_signing.MEXICO_CITY)
    now = signed_at.replace(tzinfo=None)
    _, evidence_bytes, payload_hash = clinical_signing.build_biometric_evidence_payload(
        document=document,
        codigo_formato=req.codigo_formato,
        pt_num=str(pt_num),
        expediente=f"PT-{str(pt_num).removeprefix('PT-')}",
        evolution_slot=target_slot,
        patient_identity=patient_identity,
        firmante_id=None,
        usuario_firmante_id=usuario.id,
        rol_firmante=role,
        nombre_firmante=usuario.nombre_completo or usuario.username,
        identificacion=usuario.username,
        signed_at=signed_at,
    )
    canonical_payload = evidence_bytes.decode("utf-8")
    seal = f"EVIDENCIA_BIOMETRICA_NO_FEA:{uuid.uuid4()}"
    patient_number = str(paciente.codigo_barras or pt_num)
    previous_ids = {row["id"] for row in previous_history}
    for previous in previous_rows:
        if previous.id not in previous_ids or previous.estado != "ACTIVA":
            continue
        previous.estado = "REVOCADA"
        previous.fecha_revocacion = now
        previous.motivo_revocacion = "Nueva evidencia para la versión documental vigente"

    client_ip = request.client.host if request.client else "127.0.0.1"
    signature = models.FirmaDocumentoClinico(
        tipo_documento=document.tipo_documento,
        codigo_formato=req.codigo_formato,
        pt_num=patient_number,
        expediente=f"PT-{patient_number.removeprefix('PT-')}",
        evolution_slot=target_slot,
        rol_firmante=role,
        firmante_id=None,
        usuario_firmante_id=usuario.id,
        medico_id=None,
        nombre_medico=usuario.nombre_completo or usuario.username,
        cedula_profesional="NO APLICA",
        fecha_hora_firma=now,
        metodo_autenticacion=f"Biometría dactilar {role} (evidencia no FEA)",
        hash_sha256=payload_hash,
        sello_digital=seal,
        cadena_original=canonical_payload,
        ip_origen=client_ip,
        signature_schema_version=clinical_signing.BIOMETRIC_EVIDENCE_VERSION,
        canonical_payload=canonical_payload,
        payload_hash=payload_hash,
        document_version=document.version_documento,
        tsa_status=tsa_client.SIN_TSA,
    )
    db.add(signature)
    db.flush()
    db.add(models.AuditoriaLog(
        usuario_id=current_user.id if normalize_role(current_user.rol) not in {"medico", "ayudante"} else None,
        actor_real=_biometric_subject_from_request(request) or "sistema",
        actor_effective=_biometric_subject_from_request(request) or "sistema",
        accion="EVIDENCIA_BIOMETRICA_AREA_ESPECIAL_NO_FEA",
        detalles_json=json.dumps({
            "firma_id": signature.id,
            "pt_num": patient_number,
            "codigo_formato": req.codigo_formato,
            "evolution_slot": target_slot,
            "usuario_firmante_id": usuario.id,
            "rol_firmante": role,
            "payload_hash": payload_hash,
            "naturaleza": "AUTENTICACION_BIOMETRICA_Y_EVIDENCIA_DE_ACTO_NO_FEA_PERSONAL",
        }, ensure_ascii=False),
        ip_origen=client_ip,
    ))
    db.commit()
    db.refresh(signature)
    return {
        "success": True,
        "message": f"Evidencia biométrica de {usuario.nombre_completo or usuario.username} ({role}) registrada; no equivale a FEA.",
        "firma": {
            "id": signature.id,
            "rol_firmante": role,
            "usuario_firmante_id": usuario.id,
            "nombre_firmante": usuario.nombre_completo or usuario.username,
            "username": usuario.username,
            "fecha_hora": signed_at.strftime("%d/%m/%Y %H:%M:%S %z"),
            "hash_sha256": payload_hash,
            "sello_digital": seal,
            "signature_schema_version": clinical_signing.BIOMETRIC_EVIDENCE_VERSION,
            "naturaleza": "AUTENTICACION_BIOMETRICA_Y_EVIDENCIA_DE_ACTO_NO_FEA_PERSONAL",
        },
    }


@app.get("/api/ehr/paciente/{pt_num}/firmas")
@app.get("/api/pacientes/{pt_num}/firmas")
def get_firmas_paciente(pt_num: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Obtiene las firmas biométricas activas y vigentes para el paciente (Médicos, Pacientes, Testigos)."""
    paciente = get_or_create_paciente_by_identifier(db, pt_num, allow_create=False)
    pt_key = paciente.codigo_barras if paciente else pt_num

    firmas = db.query(models.FirmaDocumentoClinico).filter(
        models.FirmaDocumentoClinico.pt_num.in_((
            str(pt_num), str(pt_key), f"PT-{str(pt_key).removeprefix('PT-')}",
        )),
        models.FirmaDocumentoClinico.estado == "ACTIVA"
    ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()

    # This endpoint drives current-document badges. Historical evidence remains
    # available from historial-auditoria, never deleted or promoted to current.
    documents = {}
    current_signatures = []
    for signature in firmas:
        if not can_use_format(current_user, signature.codigo_formato):
            continue
        key = (signature.codigo_formato, int(signature.evolution_slot or 0))
        if key not in documents:
            try:
                documents[key], _ = clinical_signing.load_authoritative_document(
                    db, pt_num=str(pt_num), codigo_formato=key[0], evolution_slot=key[1],
                )
            except Exception:
                documents[key] = None
        if documents[key] and clinical_signing.evidence_matches_current(db, signature, documents[key]):
            current_signatures.append(signature)
    firmas = current_signatures

    # Historic signatures can outlive the current catalog. Preserve the list
    # even when one older format has no signature policy configured yet.
    signature_policies = {}
    for code in {f.codigo_formato for f in firmas}:
        try:
            signature_policies[code] = clinical_signing.consent_signature_policy(code)
        except clinical_signing.ClinicalDocumentUnavailable:
            signature_policies[code] = None

    # One read for all native-delivery states; the presence of an HES signature
    # never implies that Vertical has confirmed the same operation.
    operation_ids = {f.clinical_sync_operation_id for f in firmas if f.clinical_sync_operation_id}
    sync_states = {
        operation.operation_id: operation.state
        for operation in db.query(models.ClinicalSyncOperation).filter(
            models.ClinicalSyncOperation.operation_id.in_(operation_ids)
        ).all()
    } if operation_ids else {}

    return [
        {
            "id": f.id,
            "tipo_documento": f.tipo_documento,
            "codigo_formato": f.codigo_formato,
            "evolution_slot": f.evolution_slot,
            "rol_firmante": f.rol_firmante or "MEDICO",
            "firmante_id": f.firmante_id,
            "usuario_firmante_id": f.usuario_firmante_id,
            "usuario_firmante": f.usuario_firmante.username if f.usuario_firmante else None,
            "nombre_medico": f.nombre_medico,
            "cedula_profesional": f.cedula_profesional,
            "fecha_hora_firma": f.fecha_hora_firma.strftime("%d/%m/%Y %H:%M:%S") if f.fecha_hora_firma else "",
            "metodo_autenticacion": f.metodo_autenticacion,
            "hash_sha256": f.hash_sha256,
            "sello_digital": f.sello_digital or "",
            "cadena_original": f.cadena_original or "",
            "estado": f.estado,
            "signature_schema_version": f.signature_schema_version,
            "key_id": f.key_id,
            "naturaleza_evidencia": (
                "FEA_MEDICA_ECDSA"
                if f.signature_schema_version == clinical_signing.SCHEMA_VERSION
                else "AUTENTICACION_BIOMETRICA_Y_EVIDENCIA_DE_ACTO_NO_FEA_PERSONAL"
                if f.signature_schema_version == clinical_signing.BIOMETRIC_EVIDENCE_VERSION
                else "FIRMA_LEGACY_NO_CUBRE_DOCUMENTO_COMPLETO"
            ),
            "tsa_status": f.tsa_status,
            "medico_sync_state": sync_states.get(f.clinical_sync_operation_id) if f.clinical_sync_operation_id else None,
            "medico_sync_operation_id": str(f.clinical_sync_operation_id) if f.clinical_sync_operation_id else None,
            "vigente": True,
            "requiere_autorizacion": signature_policies[f.codigo_formato][0] if signature_policies[f.codigo_formato] else None,
            "requiere_testigos": bool(signature_policies[f.codigo_formato][1]) if signature_policies[f.codigo_formato] else None,
            "testigos_requeridos": signature_policies[f.codigo_formato][1] if signature_policies[f.codigo_formato] else None,
            "politica_firma_pendiente": signature_policies[f.codigo_formato] is None,
        }
        for f in firmas
    ]


def obtener_firmas_completas_documento(db: Session, pt_num: str, codigo_formato: str, evolution_slot: int = 0, paciente_capaz: bool = None, current_document=None) -> dict:
    """
    Recupera todas las firmas biométricas activas para un documento clínico:
    - Firma del Médico tratante
    - Firma del Paciente o Tutor / Representante Legal (según si paciente_capaz es True/False)
    - Firma del Testigo 1
    - Firma del Testigo 2
    """
    paciente = get_or_create_paciente_by_identifier(db, pt_num, allow_create=False)
    pt_key = paciente.codigo_barras if paciente else pt_num
    
    base_query = db.query(models.FirmaDocumentoClinico).filter(
        (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | (models.FirmaDocumentoClinico.pt_num == str(pt_key)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_key}"),
        models.FirmaDocumentoClinico.codigo_formato == str(codigo_formato),
        models.FirmaDocumentoClinico.estado == "ACTIVA"
    )
    resolved_slot = int(evolution_slot or 0)
    firmas = base_query.filter(
        models.FirmaDocumentoClinico.evolution_slot == resolved_slot
    ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()
    # Area evidence from older clients may use a short code or slot=0. Only
    # that area's evidence can be resolved by its signed source identifier;
    # medical/patient/witness slots retain their existing exact-slot policy.
    import area_signatures
    known_ids = {row.id for row in firmas}
    for role in clinical_signing.special_signature_requirements(codigo_formato):
        for row in area_signatures.signature_rows(db, pt_num, codigo_formato, role, resolved_slot or None):
            if row.estado == "ACTIVA" and row.id not in known_ids:
                firmas.append(row)
                known_ids.add(row.id)
    firmas.sort(key=lambda row: row.fecha_hora_firma, reverse=True)
    raw_signature_count = len(firmas)
    source_unverified = False
    if firmas:
        try:
            if current_document is None:
                current_document, _ = clinical_signing.load_authoritative_document(
                    db, pt_num=str(pt_num), codigo_formato=codigo_formato,
                    evolution_slot=int(evolution_slot or 0),
                )
            if paciente_capaz is None:
                paciente_capaz = clinical_signing.explicit_patient_capacity(current_document)
            firmas = [f for f in firmas if clinical_signing.evidence_matches_current(db, f, current_document)]
        except Exception:
            # Source unavailable is not proof of current signatures. Historic rows remain intact.
            firmas = []
            source_unverified = True
    
    verified_signature_count = len(firmas)
    from format_catalog import special_signature_role_label
    res = {
        "sello_digital": None,
        "source_unverified": source_unverified,
        "evidencia_firmas_vigente": (
            not source_unverified and (
                raw_signature_count == 0 or verified_signature_count > 0
            )
        ),
        "evidencia_historica_preservada": (
            not source_unverified and raw_signature_count > verified_signature_count > 0
        ),
        "medico_sync_operation_id": None,
        "fecha_hora_firma": None,
        "nombre_medico": None,
        "cedula": None,
        "sello_paciente": None,
        "fecha_paciente": None,
        "firmante_paciente": None,
        "parentesco_paciente": None,
        "rol_firmante_paciente": None,
        "firma_paciente_biometrica": False,
        "sello_testigo1": None,
        "fecha_testigo1": None,
        "firmante_testigo1": None,
        "parentesco_testigo1": None,
        "firma_testigo1_biometrica": False,
        "sello_testigo2": None,
        "fecha_testigo2": None,
        "firmante_testigo2": None,
        "parentesco_testigo2": None,
        "firma_testigo2_biometrica": False,
        "sello_banco_sangre": None,
        "fecha_banco_sangre": None,
        "firmante_banco_sangre": None,
        "usuario_firmante_banco_sangre_id": None,
        "usuario_firmante_banco_sangre": None,
        "firma_banco_sangre_biometrica": False,
        "firmas_especiales_requeridas": clinical_signing.special_signature_requirements(codigo_formato),
        "firmas_especiales": {
            role: {
                "rol_firmante": role,
                "etiqueta": special_signature_role_label(role),
                "firmado": False,
                "firmante": None,
                "username": None,
                "fecha": None,
                "usuario_firmante_id": None,
                "sello": None,
                "firma_biometrica": False,
            }
            for role in clinical_signing.special_signature_requirements(codigo_formato)
        },
    }
    
    for f in firmas:
        rol = (f.rol_firmante or "MEDICO").upper()
        f_date = f.fecha_hora_firma.strftime("%d/%m/%Y %H:%M:%S") if f.fecha_hora_firma else ""
        clean_name = re.sub(r'\s*\([^)]*\)', '', f.nombre_medico or '').strip()
        
        firmante_obj = None
        if f.firmante_id:
            firmante_obj = db.query(models.BiometriaFirmanteEpisodio).filter(models.BiometriaFirmanteEpisodio.id == f.firmante_id).first()
        
        if rol == "MEDICO" and not res["sello_digital"]:
            res["sello_digital"] = f.sello_digital
            res["medico_sync_operation_id"] = str(f.clinical_sync_operation_id) if f.clinical_sync_operation_id else None
            res["hash_sha256"] = f.hash_sha256
            res["fecha_hora_firma"] = f_date
            res["nombre_medico"] = f.nombre_medico
            res["cedula"] = f.cedula_profesional
        elif rol in ("PACIENTE", "REPRESENTANTE_LEGAL", "TUTOR", "FAMILIAR") and not res["sello_paciente"]:
            # Si el documento declara explícitamente que el paciente NO puede firmar, solo aceptar firmas de tutor/familiar
            if paciente_capaz is False and rol == "PACIENTE":
                continue
            # Si el documento declara que el paciente SÍ puede firmar pero hay firma de tutor, se permite si no hay otra
            res["sello_paciente"] = f.sello_digital
            res["firmante_paciente_id"] = f.firmante_id
            res["fecha_paciente"] = f_date
            res["firmante_paciente"] = clean_name
            if rol == "PACIENTE" and (paciente_capaz is not False):
                res["parentesco_paciente"] = "Paciente"
                res["rol_firmante_paciente"] = "PACIENTE"
            else:
                p_text = firmante_obj.parentesco if (firmante_obj and firmante_obj.parentesco and firmante_obj.parentesco.upper() not in ('PACIENTE', 'TITULAR')) else "Tutor / Representante Legal"
                res["parentesco_paciente"] = p_text
                res["rol_firmante_paciente"] = rol
            res["domicilio_paciente"] = firmante_obj.domicilio if firmante_obj and firmante_obj.domicilio else None
            res["identificacion_paciente"] = firmante_obj.identificacion_oficial if firmante_obj and firmante_obj.identificacion_oficial else None
            res["firma_paciente_biometrica"] = True
        elif rol in ("TESTIGO_1", "TESTIGO") and not res["sello_testigo1"]:
            res["sello_testigo1"] = f.sello_digital
            res["firmante_testigo1_id"] = f.firmante_id
            res["fecha_testigo1"] = f_date
            res["firmante_testigo1"] = clean_name
            res["parentesco_testigo1"] = firmante_obj.parentesco if firmante_obj else "Testigo Presencial"
            res["domicilio_testigo1"] = firmante_obj.domicilio if firmante_obj and firmante_obj.domicilio else None
            res["identificacion_testigo1"] = firmante_obj.identificacion_oficial if firmante_obj and firmante_obj.identificacion_oficial else None
            res["firma_testigo1_biometrica"] = True
        elif rol == "TESTIGO_2" and not res["sello_testigo2"]:
            res["sello_testigo2"] = f.sello_digital
            res["firmante_testigo2_id"] = f.firmante_id
            res["fecha_testigo2"] = f_date
            res["firmante_testigo2"] = clean_name
            res["parentesco_testigo2"] = firmante_obj.parentesco if firmante_obj else "Testigo Presencial"
            res["domicilio_testigo2"] = firmante_obj.domicilio if firmante_obj and firmante_obj.domicilio else None
            res["identificacion_testigo2"] = firmante_obj.identificacion_oficial if firmante_obj and firmante_obj.identificacion_oficial else None
            res["firma_testigo2_biometrica"] = True
        elif rol in res["firmas_especiales"] and f.usuario_firmante_id:
            user = db.get(models.Usuario, f.usuario_firmante_id)
            res["firmas_especiales"][rol] = {
                "rol_firmante": rol,
                "etiqueta": res["firmas_especiales"][rol]["etiqueta"],
                "firmado": True,
                "firmante": clean_name,
                "username": user.username if user else None,
                "fecha": f_date,
                "usuario_firmante_id": f.usuario_firmante_id,
                "sello": f.sello_digital,
                "firma_biometrica": True,
            }
            if rol == "BANCO_SANGRE" and not res["sello_banco_sangre"]:
                res["sello_banco_sangre"] = f.sello_digital
                res["fecha_banco_sangre"] = f_date
                res["firmante_banco_sangre"] = clean_name
                res["usuario_firmante_banco_sangre_id"] = f.usuario_firmante_id
                res["usuario_firmante_banco_sangre"] = user.username if user else None
                res["firma_banco_sangre_biometrica"] = True

    return res


def aplicar_firmas_a_pt_data(pt_data: dict, sig_info: dict, firma_data: dict, paciente_capaz: bool, db: Session = None):
    """
    Inyecta únicamente los datos de personas que firmaron esta versión.
    El directorio de personas enroladas no acredita participación en un acto.
    """
    if sig_info.get("sello_paciente"):
        signed_as_representative = sig_info.get("rol_firmante_paciente") != "PACIENTE"
        if signed_as_representative:
            # Documento firmado por Tutor / Representante Legal
            tutor_nom = sig_info.get("firmante_paciente")
            tutor_parentesco = (sig_info.get("parentesco_paciente") if sig_info.get("parentesco_paciente") not in ("Paciente", "PACIENTE", "Titular") else None) or "Tutor / Representante Legal"
            if str(tutor_parentesco).upper() in ("PACIENTE", "TITULAR", "DIRECTO"):
                tutor_parentesco = "Tutor / Representante Legal"
            
            pt_data["sello_paciente"] = sig_info.get("sello_paciente")
            pt_data["firma_paciente_biometrica"] = True
            pt_data["pariente"] = tutor_nom
            pt_data["representante_legal"] = tutor_nom
            pt_data["declarante"] = tutor_nom
            pt_data["responsable"] = tutor_nom
            pt_data["parentesco"] = tutor_parentesco
            pt_data["parentesco_declarante"] = tutor_parentesco
            pt_data["parentesco_paciente"] = tutor_parentesco
        else:
            # Documento firmado por el Paciente Titular
            pt_data["sello_paciente"] = sig_info.get("sello_paciente")
            pt_data["firma_paciente_biometrica"] = True
            pt_data["declarante"] = sig_info.get("firmante_paciente") or pt_data.get("paciente_nombre") or pt_data.get("nombre")
            pt_data["parentesco_paciente"] = "Paciente"
            pt_data["parentesco"] = "Paciente"

        if sig_info.get("domicilio_paciente"):
            pt_data["domicilio_paciente"] = sig_info.get("domicilio_paciente")
            pt_data["domicilio_declarante"] = sig_info.get("domicilio_paciente")
        if sig_info.get("identificacion_paciente"):
            pt_data["identificacion_paciente"] = sig_info.get("identificacion_paciente")
            pt_data["identificacion_declarante"] = sig_info.get("identificacion_paciente")

    if sig_info.get("sello_testigo1"):
        pt_data["sello_testigo1"] = sig_info.get("sello_testigo1")
        pt_data["firma_testigo1_biometrica"] = True
        if sig_info.get("firmante_testigo1"):
            pt_data["testigo1"] = sig_info.get("firmante_testigo1")
            pt_data["testigo_1"] = sig_info.get("firmante_testigo1")
            pt_data["testigo1_nombre"] = sig_info.get("firmante_testigo1")
        if sig_info.get("parentesco_testigo1"):
            pt_data["parentesco_testigo1"] = sig_info.get("parentesco_testigo1")
            pt_data["parentesco_testigo"] = sig_info.get("parentesco_testigo1")
        if sig_info.get("domicilio_testigo1"):
            pt_data["domicilio_testigo1"] = sig_info.get("domicilio_testigo1")
            pt_data["domicilio_testigo"] = sig_info.get("domicilio_testigo1")
        if sig_info.get("identificacion_testigo1"):
            pt_data["identificacion_testigo1"] = sig_info.get("identificacion_testigo1")
            pt_data["identificacion_testigo"] = sig_info.get("identificacion_testigo1")

    if sig_info.get("sello_testigo2"):
        pt_data["sello_testigo2"] = sig_info.get("sello_testigo2")
        pt_data["firma_testigo2_biometrica"] = True
        if sig_info.get("firmante_testigo2"):
            pt_data["testigo2"] = sig_info.get("firmante_testigo2")
            pt_data["testigo_2"] = sig_info.get("firmante_testigo2")
            pt_data["testigo2_nombre"] = sig_info.get("firmante_testigo2")
        if sig_info.get("parentesco_testigo2"):
            pt_data["parentesco_testigo2"] = sig_info.get("parentesco_testigo2")
        if sig_info.get("domicilio_testigo2"):
            pt_data["domicilio_testigo2"] = sig_info.get("domicilio_testigo2")
        if sig_info.get("identificacion_testigo2"):
            pt_data["identificacion_testigo2"] = sig_info.get("identificacion_testigo2")

    if sig_info.get("sello_banco_sangre"):
        for target in (pt_data, firma_data):
            if not isinstance(target, dict):
                continue
            target["verifico_firma_biometrica"] = True
            target["verifico_nombre"] = "PERSONAL DE SALUD / BANCO DE SANGRE"
            target["nombre_personal_banco_sangre"] = sig_info.get("firmante_banco_sangre")
            target["usuario_personal_banco_sangre"] = sig_info.get("usuario_firmante_banco_sangre")
            target["fecha_firma_banco_sangre"] = sig_info.get("fecha_banco_sangre")
            target["sello_banco_sangre"] = sig_info.get("sello_banco_sangre")
            target["firma_banco_sangre_biometrica"] = True

    special_roles = sig_info.get("firmas_especiales_requeridas") or []
    if special_roles:
        for target in (pt_data, firma_data):
            if isinstance(target, dict):
                target["firmas_especiales_requeridas"] = list(special_roles)
                target["firmas_especiales"] = {
                    role: {
                        "rol_firmante": role,
                        "etiqueta": (sig_info.get("firmas_especiales") or {}).get(role, {}).get("etiqueta") or role.replace("_", " ").title(),
                        "firmado": bool((sig_info.get("firmas_especiales") or {}).get(role, {}).get("firmado")),
                        "firmante": (sig_info.get("firmas_especiales") or {}).get(role, {}).get("firmante"),
                        "username": (sig_info.get("firmas_especiales") or {}).get(role, {}).get("username"),
                        "fecha": (sig_info.get("firmas_especiales") or {}).get(role, {}).get("fecha"),
                        "firma_biometrica": bool((sig_info.get("firmas_especiales") or {}).get(role, {}).get("firma_biometrica")),
                    }
                    for role in special_roles
                }

    source_has_native_signature = bool(
        pt_data.get("firmado")
        or pt_data.get("signed_by")
        or pt_data.get("signed_on")
        or str(pt_data.get("mr_st") or "").strip().upper() == "SG"
    )
    # Names entered in a draft are not evidence that those people signed.
    # Preserve them only when the source itself is already marked signed by
    # Vertical; otherwise leave unsigned witness places blank.
    for index, fields in (
        (1, ("testigo1", "testigo_1", "testigo1_nombre", "parentesco_testigo1", "parentesco_testigo", "domicilio_testigo1", "domicilio_testigo", "identificacion_testigo1", "identificacion_testigo")),
        (2, ("testigo2", "testigo_2", "testigo2_nombre", "parentesco_testigo2", "domicilio_testigo2", "identificacion_testigo2")),
    ):
        if not sig_info.get(f"sello_testigo{index}") and not source_has_native_signature:
            for field in fields:
                pt_data[field] = ""
            pt_data[f"sello_testigo{index}"] = None
            pt_data[f"firma_testigo{index}_biometrica"] = False


@app.get("/api/ehr/paciente/{pt_num}/firmas-documento")
@app.get("/ehr/paciente/{pt_num}/firmas-documento")
def get_firmas_documento_estado(pt_num: str, codigo_formato: str, slot: int = 0, db: Session = Depends(get_db)):
    """Devuelve el estado de firmas de un documento para el flujo secuencial NOM-004."""
    info = obtener_firmas_completas_documento(db, pt_num, codigo_formato, slot)
    try:
        requires_authorization = clinical_signing.requires_consent_signers(codigo_formato)
        expected_witnesses = clinical_signing.required_consent_witnesses(codigo_formato)
        required_witnesses = clinical_signing.required_consent_witnesses_for_authorizer(
            codigo_formato, info.get("rol_firmante_paciente")
        )
    except clinical_signing.ClinicalDocumentUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    special_requirements = clinical_signing.special_signature_requirements(codigo_formato)
    signed_witnesses = clinical_signing.signed_witness_count(info)
    ready = not requires_authorization or clinical_signing.consent_signatures_complete(
        info, required_witnesses=required_witnesses
    )
    special_state = info.get("firmas_especiales") or {}
    special_signatures_complete = all(
        bool((special_state.get(role) or {}).get("firmado"))
        for role in special_requirements
    )
    document_operatively_complete = bool(
        ready and info.get("sello_digital") and special_signatures_complete
    )
    medico_sync_operation_id = info.get("medico_sync_operation_id")
    medico_sync_operation = (
        db.get(models.ClinicalSyncOperation, uuid.UUID(medico_sync_operation_id))
        if medico_sync_operation_id else None
    )
    medico_sync_unverified = False
    if not medico_sync_operation and info.get("source_unverified") and db is not None:
        # The ERP source could not be read. Preserve visibility of a local
        # pending medical signature without claiming it is current/verified.
        patient = get_or_create_paciente_by_identifier(db, pt_num, allow_create=False)
        patient_key = str(patient.codigo_barras) if patient else str(pt_num)
        candidates = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num.in_(
                (str(pt_num), patient_key, f"PT-{patient_key}")
            ),
            models.FirmaDocumentoClinico.codigo_formato == str(codigo_formato),
            models.FirmaDocumentoClinico.evolution_slot == int(slot or 0),
            models.FirmaDocumentoClinico.rol_firmante == "MEDICO",
            models.FirmaDocumentoClinico.estado == "ACTIVA",
            models.FirmaDocumentoClinico.clinical_sync_operation_id.isnot(None),
        ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()
        for candidate in candidates:
            local_operation = db.get(
                models.ClinicalSyncOperation, candidate.clinical_sync_operation_id
            )
            if local_operation:
                medico_sync_operation = local_operation
                medico_sync_operation_id = str(local_operation.operation_id)
                medico_sync_unverified = True
                break
    return {
        "codigo_formato": codigo_formato,
        "slot": slot,
        "paciente_firmado": bool(info.get("sello_paciente")),
        "testigo1_firmado": bool(info.get("sello_testigo1")),
        "testigo2_firmado": bool(info.get("sello_testigo2")),
        "medico_firmado": bool(info.get("sello_digital")),
        "firmas_especiales_requeridas": special_requirements,
        "firmas_especiales_estado": special_state,
        "firmas_especiales_pendientes": [
            role for role in special_requirements
            if not bool((special_state.get(role) or {}).get("firmado"))
        ],
        "firmas_especiales_completas": special_signatures_complete,
        "banco_sangre_firmado": bool(info.get("sello_banco_sangre")),
        "documento_operativamente_completo": document_operatively_complete,
        "medico_sync_operation_id": medico_sync_operation_id,
        "medico_sync_state": medico_sync_operation.state if medico_sync_operation else None,
        "medico_sync_unverified": medico_sync_unverified,
        "requiere_autorizacion": requires_authorization,
        "requiere_testigos": expected_witnesses > 0,
        "testigos_esperados": expected_witnesses,
        "testigos_requeridos": required_witnesses,
        "testigos_firmados": signed_witnesses,
        "testigos_pendientes": max(0, expected_witnesses - signed_witnesses),
        "testigos_formato_completos": signed_witnesses >= expected_witnesses,
        "cierre_excepcional_por_testigos": (
            requires_authorization and ready and signed_witnesses < expected_witnesses
        ),
        "listo_para_cierre_medico": ready,
        "firmas_completas": document_operatively_complete,
        "evidencia_firmas_vigente": bool(
            info.get("evidencia_firmas_vigente", not info.get("source_unverified"))
        ),
        "evidencia_historica_preservada": bool(info.get("evidencia_historica_preservada")),
        "detalles": info
    }



@app.get("/api/ehr/paciente/{pt_num}/historial-auditoria")

def get_historial_auditoria_paciente(pt_num: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):

    """

    Entrega el expediente forense inmutable de auditoría (NOM-024-SSA3-2012):

    Todas las versiones de notas, firmas históricas, firmas revocadas y eventos de seguridad.

    """

    historico_notas = db.query(models.HistoricoNotaClinica).filter(

        models.HistoricoNotaClinica.pt_num == str(pt_num)

    ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()



    firmas_todas = db.query(models.FirmaDocumentoClinico).filter(

        models.FirmaDocumentoClinico.pt_num == str(pt_num)

    ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()



    historico_notas = [item for item in historico_notas if can_use_format(current_user, item.codigo_formato)]
    firmas_todas = [item for item in firmas_todas if can_use_format(current_user, item.codigo_formato)]

    return {

        "pt_num": pt_num,

        "expediente": f"PT-{pt_num}",

        "total_versiones_clinicas": len(historico_notas),

        "total_firmas_registradas": len(firmas_todas),

        "firmas": [

            {

                "id": f.id,

                "slot": f.evolution_slot,

                "documento": f.tipo_documento,

                "medico": f.nombre_medico,

                "cedula": f.cedula_profesional,

                "fecha_firma": f.fecha_hora_firma.strftime("%d/%m/%Y %H:%M:%S") if f.fecha_hora_firma else "",

                "estado": f.estado,

                "fecha_revocacion": f.fecha_revocacion.strftime("%d/%m/%Y %H:%M:%S") if f.fecha_revocacion else None,

                "motivo_revocacion": f.motivo_revocacion,

                "hash_sha256": f.hash_sha256,

                "sello_hmac": f.sello_digital,

                "ip_origen": f.ip_origen

            }

            for f in firmas_todas

        ],

        "versiones_clinicas": [

            {

                "id": h.id,

                "slot": h.evolution_slot,

                "accion": h.accion,

                "medico": h.nombre_medico,

                "cedula": h.cedula_profesional,

                "fecha": h.fecha_registro.strftime("%d/%m/%Y %H:%M:%S") if h.fecha_registro else "",

                "ip_origen": h.ip_origen,

                "motivo": h.motivo,

                "contenido_soap": json.loads(h.contenido_soap_json) if h.contenido_soap_json else {}

            }

            for h in historico_notas

        ],

        "marco_normativo": "NOM-004-SSA3-2012 / NOM-024-SSA3-2012 (Inmutabilidad y No Repudio)"

    }



class VerificarIntegridadInputSchema(BaseModel):
    firma_id: Optional[int] = None
    codigo_formato: Optional[str] = None
    slot: Optional[int] = 0
    document_version: Optional[str] = None
    tipo_documento: Optional[str] = None
    incluir_historico: bool = False


@app.post("/api/ehr/paciente/{pt_num}/verificar-integridad")
@app.post("/ehr/paciente/{pt_num}/verificar-integridad")
def verificar_integridad_documento(
    pt_num: str,
    req: VerificarIntegridadInputSchema,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Recalcula en vivo el Hash SHA-256 y Sello HMAC-SHA512 desde los datos actuales de la base de datos
    y los compara contra el registro original firmado, proporcionando evidencia de la Tríada de Seguridad.
    """
    pt_clean = str(pt_num).replace("PT-", "").strip()
    pt_pt = f"PT-{pt_clean}"
    paciente = db.query(models.Paciente).filter(
        models.Paciente.codigo_barras.in_({str(pt_num), pt_clean, pt_pt})
    ).first()
    pt_key = paciente.codigo_barras if paciente else pt_clean

    firma = None
    patient_variants = {str(pt_num), str(pt_clean), str(pt_pt), str(pt_key)}
    allowed_states = ["ACTIVA", "REVOCADA", "HISTORICA"] if req.incluir_historico else ["ACTIVA"]
    if req.firma_id:
        q = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.id == req.firma_id,
            models.FirmaDocumentoClinico.pt_num.in_(patient_variants),
            models.FirmaDocumentoClinico.estado.in_(allowed_states),
        )
        if req.codigo_formato:
            q = q.filter(models.FirmaDocumentoClinico.codigo_formato == req.codigo_formato)
        if req.slot is not None:
            q = q.filter(models.FirmaDocumentoClinico.evolution_slot == int(req.slot))
        if req.document_version is not None:
            q = q.filter(models.FirmaDocumentoClinico.document_version == req.document_version)
        if req.tipo_documento is not None:
            q = q.filter(models.FirmaDocumentoClinico.tipo_documento == req.tipo_documento)
        firma = q.one_or_none()
        if not firma:
            raise HTTPException(
                status_code=409,
                detail="firma_id no pertenece exactamente al paciente/documento/slot solicitado.",
            )

    if not firma and req.codigo_formato:
        q = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num.in_(patient_variants),
            models.FirmaDocumentoClinico.codigo_formato == req.codigo_formato,
            models.FirmaDocumentoClinico.estado.in_(allowed_states),
        )
        if req.slot is not None:
            q = q.filter(models.FirmaDocumentoClinico.evolution_slot == int(req.slot))
        if req.document_version is not None:
            q = q.filter(models.FirmaDocumentoClinico.document_version == req.document_version)
        if req.tipo_documento is not None:
            q = q.filter(models.FirmaDocumentoClinico.tipo_documento == req.tipo_documento)
        firma = q.order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()

    if not req.firma_id and not req.codigo_formato:
        raise HTTPException(
            status_code=422,
            detail="Debe especificar firma_id o codigo_formato para una selección exacta.",
        )

    if firma:
        require_format(current_user, firma.codigo_formato)

    if not firma:
        # Intento de verificar directamente desde Vertical (SQL Server) si no existe registro local en PostgreSQL
        try:
            from vertical_signer import resolve_vertical_controller_and_pk
            fmt_key = req.codigo_formato or ''
            c_name, pk_col = resolve_vertical_controller_and_pk(fmt_key)
            conn_v = kh_database.get_kh_connection()
            v_row = None
            if conn_v:
                c_v = conn_v.cursor()
                c_v.execute(f"SELECT TOP 1 ESignature, SignedBy, SignedOn FROM {c_name} WHERE PTNum = ? ORDER BY {pk_col} DESC", (pt_clean,))
                v_row = c_v.fetchone()
                conn_v.close()
            if v_row and (v_row[0] or v_row[1]):
                sig_str = str(v_row[0] or f"VERTICAL-FEA-{pt_clean}")
                import qrcode, io, base64
                qr = qrcode.QRCode(box_size=5, border=2)
                qr.add_data(sig_str)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
                f_por = str(v_row[1] or "Médico Tratante HES")
                f_fecha = v_row[2].strftime("%d/%m/%Y %H:%M:%S") if v_row[2] else datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                v_hash = hashlib.sha256(sig_str.encode('utf-8')).hexdigest()
                return {
                    "integro": False,
                    "classification": "METADATA_VERTICAL_NO_CRIPTOGRAFICA",
                    "firma_vertical": {
                        "disponible": True,
                        "cadena_firma": sig_str,
                        "qr_data_url": qr_b64,
                        "firmado_por": f_por,
                        "fecha_firma": f_fecha,
                        "controlador": c_name,
                        "estado": "Metadata declarativa de Vertical; no es evidencia criptográfica"
                    },
                    "estado": "Marcador Vertical sin ECDSA: no válido criptográficamente",
                    "triada_seguridad": {
                        "identidad": {
                            "verificado": False,
                            "pilar": "Identidad del Firmante",
                            "metodo": "Biometría Dactilar DigitalPersona / Firma Electrónica Vertical",
                            "firmante": f_por,
                            "cedula": "REGISTRADA",
                            "estado": "Identidad declarada por Vertical, no comprobada criptográficamente"
                        },
                        "integridad": {
                            "verificado": False,
                            "pilar": "Integridad del Documento",
                            "metodo": "Función Criptográfica SHA-256",
                            "hash_sha256": v_hash,
                            "hash_calculado_en_vivo": v_hash,
                            "estado": "No existe snapshot canónico firmado para comparar"
                        },
                        "autenticidad": {
                            "verificado": False,
                            "pilar": "Autenticidad y No Repudio",
                            "metodo": "Firma Electrónica Avanzada Vertical EHR (Host)",
                            "sello_hmac_sha512": sig_str,
                            "estado": "El marcador textual no es una firma ECDSA"
                        }
                    },
                    "sellado_tiempo": {"verificado": False, "status": "SIN_TSA"},
                    "cadena_original": sig_str,
                    "fecha_hora_firma": f_fecha,
                    "sello_digital": sig_str,
                    "hash_sha256": v_hash
                }
        except Exception as v_err:
            print(f"Error en fallback Vertical: {v_err}")

        raise HTTPException(status_code=404, detail="Registro de firma no encontrado para este paciente y formato.")

    verification = clinical_signing.verify_signature_record(db, firma)
    if verification["classification"] == clinical_signing.SCHEMA_VERSION:
        current_match = clinical_signing.compare_current_document(db, firma)
        tsa_status = (verification.get("tsa") or {}).get("status", tsa_client.SIN_TSA)
        cryptographic_complete = bool(
            verification["complete"] and tsa_status == tsa_client.TSA_VERIFICADO
        )
        if not verification["complete"]:
            summary_state = "INTEGRIDAD_CRIPTOGRÁFICA_INVALIDADA"
        elif current_match is False:
            summary_state = "FIRMA_HISTORICA_VALIDA_DOCUMENTO_VIGENTE_DIFERENTE"
        elif current_match is None:
            summary_state = "FIRMA_HISTORICA_VALIDA_VIGENCIA_NO_CONFIRMADA"
        elif not cryptographic_complete:
            summary_state = f"FIRMA_ECDSA_VALIDA_{tsa_status}"
        else:
            summary_state = "VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA"
        return {
            "integro": verification["complete"],
            "classification": verification["classification"],
            "estado": summary_state,
            "tsa_status": tsa_status,
            "documento_vigente": current_match,
            "vigencia_firma": firma.estado,
            "firma_vertical": {
                "disponible": False,
                "estado": "Metadata Vertical no utilizada como prueba criptográfica",
            },
            "triada_seguridad": {
                "identidad": {"verificado": verification["identity"]},
                "integridad": {
                    "verificado": verification["snapshot"] and verification["document_binding"],
                    "hash_sha256": firma.payload_hash,
                },
                "autenticidad": {
                    "verificado": verification["ecdsa"],
                    "metodo": "ECDSA P-256 / SHA-256 con key_id exacta",
                    "key_id": firma.key_id,
                },
            },
            "pdf": {
                "verificado": verification["pdf"],
                "sha256": firma.pdf_hash,
                "identificador": firma.pdf_identifier,
                "estado": (
                    "PDF_VERIFICADO"
                    if verification["pdf"] is True
                    else "REPRESENTACION_SECUNDARIA_NO_FIRMADA"
                    if verification["pdf"] is None
                    else "PDF_NO_VERIFICADO"
                ),
            },
            "sellado_tiempo": verification["tsa"],
            "signature_schema_version": firma.signature_schema_version,
            "payload_hash": firma.payload_hash,
            "key_id": firma.key_id,
            "errores": verification["errors"],
        }

    return {
        "integro": False,
        "classification": clinical_signing.LEGACY_SCHEMA_VERSION,
        "estado": "FIRMA_LEGACY_NO_CUBRE_DOCUMENTO_COMPLETO",
        "firma_vertical": {"disponible": False},
        "triada_seguridad": {
            "identidad": {"verificado": False},
            "integridad": {"verificado": False},
            "autenticidad": {"verificado": False},
        },
        "pdf": {"verificado": False, "estado": "NO_CUBIERTO_POR_FIRMA_LEGACY"},
        "sellado_tiempo": {
            "verificado": False,
            "status": getattr(firma, "tsa_status", "TSA_LEGACY_NO_VERIFICADO"),
        },
        "signature_schema_version": clinical_signing.LEGACY_SCHEMA_VERSION,
        "errores": verification["errors"],
    }

    # 1. Obtener la cadena original a verificar (soporta notas de evolución, consentimientos, recetas, dietas)
    if firma.cadena_original:
        cadena_to_verify = firma.cadena_original
    else:
        dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_num)
        evols = dashboard_data.get("evoluciones", {})

        slot_key = f"evolucion{firma.evolution_slot or 1}"

        evol_data = evols.get(slot_key)

        live_subjetivo = (evol_data.get("subjetivo") if evol_data else "") or ""

        fecha_iso = firma.fecha_hora_firma.isoformat() if firma.fecha_hora_firma else ""

        cadena_to_verify = f"||{pt_num}|PT-{pt_num}|{firma.codigo_formato}|{firma.evolution_slot or 'GRAL'}|{fecha_iso}|{firma.medico_id}|{firma.cedula_profesional}|{live_subjetivo}||"

    

    recalculated_hash = hashlib.sha256(cadena_to_verify.encode('utf-8')).hexdigest()

    

    # Obtener el médico firmante

    medico = db.query(models.Medico).filter(models.Medico.id == firma.medico_id).first()

    huella_token = (medico.huella_token or medico.cedula) if medico else firma.cedula_profesional

    is_hash_valid = (recalculated_hash == firma.hash_sha256)

    

    fecha_iso = firma.fecha_hora_firma.isoformat() if firma.fecha_hora_firma else ""

    legacy_sha512 = hashlib.sha512(f"{recalculated_hash}-{huella_token}-{fecha_iso}".encode('utf-8')).hexdigest()

    cutoff_date = datetime.datetime(2027, 1, 1)

    fecha_firma_dt = firma.fecha_hora_firma or datetime.datetime.min

    legacy_is_valid = (legacy_sha512 == firma.sello_digital) and (fecha_firma_dt < cutoff_date)

    is_sello_valid = crypto_fea.verificar_firma(
        medico,
        cadena_to_verify,
        firma.sello_digital,
        firma.fecha_hora_firma,
        db,
        key_id=getattr(firma, "key_id", None),
    ) or legacy_is_valid

    

    is_integro = is_hash_valid and is_sello_valid

    

    if not is_integro:

        log_entry = models.AuditoriaLog(

            usuario_id=None,

            accion="INTEGRIDAD_DOCUMENTAL_COMPROMETIDA",

            detalles_json=json.dumps({

                "pt_num": pt_num,

                "firma_id": firma.id,

                "hash_esperado": firma.hash_sha256,

                "hash_calculado": recalculated_hash,

                "slot": firma.evolution_slot,

                "ip": request.client.host if request.client else "127.0.0.1"

            }),

            ip_origen=request.client.host if request.client else "127.0.0.1"

        )

        db.add(log_entry)

        db.commit()

        

    # 4. Obtener la firma nativa registrada en Vertical (SQL Server) y generar su Código QR
    firma_vertical_info = {
        "disponible": False,
        "cadena_firma": None,
        "qr_data_url": None,
        "firmado_por": None,
        "fecha_firma": None,
        "controlador": None,
        "estado": "No registrado en Vertical"
    }
    try:
        from vertical_signer import resolve_vertical_controller_and_pk
        fmt_key = firma.codigo_formato or ''
        c_name, pk_col = resolve_vertical_controller_and_pk(fmt_key)
        conn_v = kh_database.get_kh_connection()
        v_row = None
        if conn_v:
            c_v = conn_v.cursor()
            c_v.execute(f"SELECT TOP 1 ESignature, SignedBy, SignedOn FROM {c_name} WHERE PTNum = ? ORDER BY {pk_col} DESC", (pt_num,))
            v_row = c_v.fetchone()
            conn_v.close()

        sig_str = str(v_row[0]) if (v_row and v_row[0]) else str(firma.sello_digital or firma.hash_sha256)
        qr_b64 = None
        try:
            import qrcode
            import io
            import base64
            qr = qrcode.QRCode(box_size=5, border=2)
            qr.add_data(sig_str)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
        except Exception as qe:
            print(f"Error generando QR de Vertical: {qe}")

        f_por = (v_row[1] if v_row and v_row[1] else firma.nombre_medico) or firma.nombre_medico
        f_fecha = (v_row[2].strftime("%d/%m/%Y %H:%M:%S") if (v_row and v_row[2]) else (firma.fecha_hora_firma.strftime("%d/%m/%Y %H:%M:%S") if firma.fecha_hora_firma else ""))

        firma_vertical_info = {
            "disponible": True,
            "cadena_firma": sig_str,
            "qr_data_url": qr_b64,
            "firmado_por": f_por,
            "fecha_firma": f_fecha,
            "controlador": c_name,
            "estado": "Validado y Sincronizado en Vertical (EHR Host)"
        }
    except Exception as ev:
        print(f"Error consultando firma de Vertical para auditoria: {ev}")

    return {
        "integro": is_integro,
        "firma_vertical": firma_vertical_info,

        "integro": is_integro,

        "estado": "Firma íntegra y verificable" if is_integro else "Integridad invalidada - El documento fue modificado posterior a la firma",

        "triada_seguridad": {

            "identidad": {

                "verificado": True,

                "pilar": "Identidad del Firmante",

                "metodo": "Biometría Dactilar DigitalPersona (FMD ANSI/NIST 378-2004)",

                "firmante": firma.nombre_medico,

                "cedula": firma.cedula_profesional,

                "estado": "Autenticación biométrica comprobada fehacientemente"

            },

            "integridad": {

                "verificado": is_hash_valid,

                "pilar": "Integridad del Documento",

                "metodo": "Función Criptográfica SHA-256",

                "hash_sha256": firma.hash_sha256,

                "hash_calculado_en_vivo": recalculated_hash,

                "estado": "Documento íntegro sin alteraciones posteriores" if is_hash_valid else "Discrepancia detectada: el contenido actual no coincide con la versión firmada"

            },

            "autenticidad": {

                "verificado": is_sello_valid,

                "pilar": "Autenticidad y No Repudio",

                "metodo": "Firma Electrónica Avanzada ECDSA P-256 (asimétrica)" if (firma.sello_digital or '').startswith('ECDSA:') else "Sello Criptográfico HMAC-SHA512 (legacy)",

                "sello_hmac_sha512": firma.sello_digital,

                "estado": "Sello criptográfico auténtico garantizado con clave privada del firmante" if is_sello_valid else "Sello inválido o alterado"

            }

        },

        "sellado_tiempo": tsa_client.verify_timestamp(getattr(firma, 'tsa_token', None), firma.hash_sha256 or ''),

        "cadena_original": firma.cadena_original,

        "fecha_hora_firma": firma.fecha_hora_firma.strftime("%d/%m/%Y %H:%M:%S") if firma.fecha_hora_firma else "",
        "marco_normativo": "NOM-004-SSA3-2012 / NOM-024-SSA3-2012"
    }


def _qr_patient_identity(db: Session, pt_num: str) -> tuple[str, str]:
    """Identify only the patient bound to an already resolved opaque QR."""
    identity = {}
    try:
        identity = kh_database.fetch_patient_identity_for_qr(pt_num)
    except Exception:
        logging.getLogger(__name__).warning("Demografía ERP no disponible para cotejo QR")
    name = (identity.get("nombre") or "").strip()
    if not name:
        # Local records have no birth date; use them only when their barcode
        # matches the QR's patient number exactly, never by an integer ID.
        local_patient = db.query(models.Paciente).filter(
            models.Paciente.codigo_barras == str(pt_num)
        ).order_by(models.Paciente.fecha_registro.desc()).first()
        name = (local_patient.nombre_completo or "").strip() if local_patient else ""
    return name or "Nombre no disponible", identity.get("edad") or "No disponible"


@app.get("/api/verificar/documento-estado")
@app.get("/api/ehr/paciente/{pt_num}/verificar-documento-estado")
def get_documento_estado_verificacion(
    request: Request,
    id: Optional[str] = None,
    doc_uuid: Optional[str] = None,
    doc: Optional[str] = None,
    pt: Optional[str] = None,
    pt_num: Optional[str] = None,
    folio: Optional[str] = None,
    slot: Optional[int] = None,
    mrnum: Optional[int] = None,
    db: Session = Depends(get_db),
    response: Response = None,
):
    """
    Motor criptográfico oficial de verificación de autenticidad documental y cotejo NOM-004 / NOM-024.
    Evalúa en tiempo real si la firma está ACTIVA, REVOCADA por re-firma, SIN FIRMA o con INTEGRIDAD COMPROMETIDA.
    """
    target_id = id or doc_uuid
    doc_reg = find_doc_verificacion(db, target_id) if target_id else None
    if not doc_reg:
        raise HTTPException(
            status_code=404,
            detail="Documento verificable no encontrado; se requiere el identificador opaco del QR.",
        )
    if response is not None:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
    target_id = doc_reg.doc_uuid
    doc_target = doc_reg.codigo_formato
    pt_target = doc_reg.pt_num
    clean_pt = doc_reg.pt_num
    slot_target = doc_reg.slot or 1
    folio_target = doc_reg.expediente or f"PT-{clean_pt}"
    registered_title = doc_reg.tipo_documento

    FORMAT_NAMES = {
        "HE-DIRMED-EXPEDIENTE-COMPLETO": "Expediente Clínico Integrado y Compilado NOM-004",
        "HE-DIRMED-CONSUL-PLT-02": "Consentimiento Informado para Tratamiento Quirúrgico / Disentimiento",
        "02": "Consentimiento Informado para Tratamiento Quirúrgico / Disentimiento",
        "PLT-02": "Consentimiento Informado para Tratamiento Quirúrgico / Disentimiento",
        "HE-DIRMED-CONSUL-PLT-04": "Consentimiento Informado para Colocación de Catéter Venoso Central",
        "04": "Consentimiento Informado para Colocación de Catéter Venoso Central",
        "PLT-24": "Nota Médica de Evolución de Hospitalización",
        "HE-DIRMED-CONSUL-PLT-25": "Consentimiento Informado Revisión Ginecológica, Obstétrica y Consulta Externa",
        "25": "Consentimiento Informado Revisión Ginecológica, Obstétrica y Consulta Externa",
        "PLT-25": "Consentimiento Informado Revisión Ginecológica, Obstétrica y Consulta Externa",
        "HE-DIRMED-CONSUL-PLT-32/01": "Consentimiento Informado para Ecocardiograma Transesofágico",
        "32/01": "Consentimiento Informado para Ecocardiograma Transesofágico",
        "HE-DIRMED-CONSUL-PLT-34/01": "Consentimiento Informado para Estudio de Mesa Inclinada (Tilt Test)",
        "34/01": "Consentimiento Informado para Estudio de Mesa Inclinada (Tilt Test)",
        "HE-DIRMED-CONSUL-PLT-EED": "Consentimiento Informado Ecocardiograma de Estrés con Dobutamina",
        "EED": "Consentimiento Informado Ecocardiograma de Estrés con Dobutamina",
        "HE-DIRMED-SINPRO-PLT-87/01": "Nota Médica de Evolución de Urgencias",
        "87/01": "Nota Médica de Evolución de Urgencias",
        "HE-DIRMED-SINPRO-PLT-43": "Orden de Intubación Endotraqueal / Soporte Ventilatorio",
        "43": "Orden de Intubación Endotraqueal / Soporte Ventilatorio",
        "PLT-43": "Orden de Intubación Endotraqueal / Soporte Ventilatorio",
        "HE-DIRMED-CONSUL-PLT-11": "Consentimiento de No Reanimación (Voluntad Anticipada)",
        "11": "Consentimiento de No Reanimación (Voluntad Anticipada)",
        "PLT-11": "Consentimiento de No Reanimación (Voluntad Anticipada)",
        "HE-DIRMED-CONSUL-PLT-19": "Consentimiento Informado para Histerectomía",
        "19": "Consentimiento Informado para Histerectomía",
        "PLT-19": "Consentimiento Informado para Histerectomía",
        "HE-DIRMED-SINPRO-PLT-15": "Egreso Voluntario",
        "SINPRO-PLT-15": "Egreso Voluntario",
        "PLT-EV-15": "Egreso Voluntario",
        "HE-DIRMED-CONSUL-PLT-06": "Consentimiento Informado para Procedimiento Anestésico",
        "06": "Consentimiento Informado para Procedimiento Anestésico",
        "PLT-06": "Consentimiento Informado para Procedimiento Anestésico"
    }

    doc_title = registered_title or FORMAT_NAMES.get(doc_target, None)
    if not doc_title:
        for k, v in FORMAT_NAMES.items():
            if k in doc_target or doc_target in k:
                doc_title = v
                break
    if not doc_title:
        doc_title = f"Documento Clínico Oficial ({doc_target})"

    # Quien posee el QR opaco puede consultar la identidad y el PDF exactos.
    # No existe búsqueda pública por nombre o folio.
    pt_nombre, pt_edad = _qr_patient_identity(db, clean_pt)

    # El expediente compilado no tiene una sola firma clínica individual:
    # su evidencia es la copia exacta resguardada para ese QR. Verificar sus
    # bytes aquí permite que el portal público confirme el expediente completo
    # sin inventar una firma de formato que no existe.
    if doc_target == "HE-DIRMED-EXPEDIENTE-COMPLETO":
        registered_pdf = doc_reg.pdf_path if doc_reg else None
        if not registered_pdf or not os.path.isfile(registered_pdf):
            return {
                "valido": False,
                "estado": "RECURSO_NO_DISPONIBLE",
                "mensaje": "La copia verificable del expediente completo no está disponible.",
                "color": "rose",
                "paciente": pt_nombre,
                "folio": folio_target,
                "edad": pt_edad,
                "formato": doc_title,
                "codigo": doc_target,
                "slot": slot_target,
                "id": doc_reg.doc_uuid,
                "doc_uuid": doc_reg.doc_uuid,
                "pdf_path": None,
                "medico": None,
                "firmante": None,
                "testigos": [],
                "hash_sha256": None,
                "sello_digital": None,
                "tsa_status": tsa_client.SIN_TSA,
            }
        with open(registered_pdf, "rb") as registered_file:
            current_hash = hashlib.sha256(registered_file.read()).hexdigest()
        if not doc_reg.hash_sha256 or not hmac.compare_digest(current_hash, doc_reg.hash_sha256):
            return {
                "valido": False,
                "estado": "INTEGRIDAD_COMPROMETIDA",
                "mensaje": "La copia del expediente completo no coincide con su hash resguardado.",
                "color": "rose",
                "paciente": pt_nombre,
                "folio": folio_target,
                "edad": pt_edad,
                "formato": doc_title,
                "codigo": doc_target,
                "slot": slot_target,
                "id": doc_reg.doc_uuid,
                "doc_uuid": doc_reg.doc_uuid,
                "pdf_path": None,
                "medico": None,
                "firmante": None,
                "testigos": [],
                "hash_sha256": doc_reg.hash_sha256,
                "sello_digital": None,
                "tsa_status": tsa_client.SIN_TSA,
            }
        return {
            "valido": True,
            "estado": "COPIA_INTEGRA_VERIFICADA",
            "mensaje": "El expediente completo coincide exactamente con la copia institucional resguardada.",
            "color": "emerald",
            "paciente": pt_nombre,
            "folio": folio_target,
            "edad": pt_edad,
            "formato": doc_title,
            "codigo": doc_target,
            "slot": slot_target,
            "id": doc_reg.doc_uuid,
            "doc_uuid": doc_reg.doc_uuid,
            "pdf_path": None,
            "medico": None,
            "fecha_generacion": doc_reg.fecha_generacion.strftime("%d/%m/%Y %H:%M:%S") if doc_reg.fecha_generacion else None,
            "firmante": None,
            "testigos": [],
            "hash_sha256": doc_reg.hash_sha256,
            "sello_digital": None,
            "tsa_status": tsa_client.SIN_TSA,
        }

    # Consultar todas las firmas del documento
    firmas_query = db.query(models.FirmaDocumentoClinico).filter(
        (models.FirmaDocumentoClinico.pt_num == str(pt_target)) |
        (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) |
        (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}")
    )
    if doc_target:
        firmas_query = firmas_query.filter(models.FirmaDocumentoClinico.codigo_formato == doc_target)
    
    todas_firmas = firmas_query.order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()
    
    # Filtrar por slot si aplica
    if slot_target is not None:
        todas_firmas = [f for f in todas_firmas if f.evolution_slot == slot_target]

    firmas_activas = [f for f in todas_firmas if f.estado == "ACTIVA"]
    firmas_revocadas = [f for f in todas_firmas if f.estado == "REVOCADA"]

    # CASO 1: NO HAY REGISTROS DE FIRMA
    if not todas_firmas:
        return {
            "valido": False,
            "estado": "SIN_FIRMA",
            "mensaje": "Documento Pendiente de Firma (No cuenta con registro de firma electrónica ni biométrica en el ECE)",
            "color": "slate",
            "paciente": pt_nombre,
            "folio": folio_target,
            "edad": pt_edad,
            "formato": doc_title,
            "codigo": doc_target,
            "slot": slot_target,
            "id": doc_reg.doc_uuid if doc_reg else target_id,
            "doc_uuid": doc_reg.doc_uuid if doc_reg else target_id,
            "pdf_path": None,
            "medico": None,
            "firmante": None,
            "testigos": [],
            "hash_sha256": None,
            "sello_digital": None
            ,"tsa_status": tsa_client.SIN_TSA
        }

    # CASO 2: NO HAY FIRMAS ACTIVAS, TODAS FUERON REVOCADAS (RE-FIRMA O SUSTITUCIÓN)
    if not firmas_activas and firmas_revocadas:
        latest_rev = firmas_revocadas[0]
        rev_date = latest_rev.fecha_revocacion.strftime("%d/%m/%Y a las %H:%M:%S hrs") if latest_rev.fecha_revocacion else "reciente"
        rev_motivo = latest_rev.motivo_revocacion or "Sustitución documental o re-firma"
        return {
            "valido": False,
            "estado": "REVOCADA",
            "mensaje": f"Firma Formalmente Revocada / No Vigente (Sustituida el {rev_date}. Motivo: {rev_motivo})",
            "color": "amber",
            "paciente": pt_nombre,
            "folio": folio_target,
            "edad": pt_edad,
            "formato": doc_title,
            "codigo": doc_target,
            "slot": slot_target,
            "id": doc_reg.doc_uuid if doc_reg else target_id,
            "doc_uuid": doc_reg.doc_uuid if doc_reg else target_id,
            "pdf_path": None,
            "fecha_revocacion": rev_date,
            "motivo_revocacion": rev_motivo,
            "medico": {
                "nombre": latest_rev.nombre_medico,
                "cedula": latest_rev.cedula_profesional,
                "fecha": latest_rev.fecha_hora_firma.strftime("%d/%m/%Y %H:%M:%S") if latest_rev.fecha_hora_firma else ""
            },
            "firmante": None,
            "testigos": [],
            "hash_sha256": latest_rev.hash_sha256,
            "sello_digital": latest_rev.sello_digital
            ,"tsa_status": latest_rev.tsa_status or tsa_client.SIN_TSA
        }

    # CASO 3: EVALUAR INTEGRIDAD CRIPTOGRÁFICA DE LAS FIRMAS ACTIVAS
    med_firma = next((f for f in firmas_activas if (f.rol_firmante or 'MEDICO').upper() == 'MEDICO'), None)
    firmante_firma = next((f for f in firmas_activas if (f.rol_firmante or '').upper() in ('PACIENTE', 'REPRESENTANTE_LEGAL', 'TUTOR', 'FAMILIAR', 'CONTACTO')), None)
    testigos_firmas = [f for f in firmas_activas if (f.rol_firmante or '').upper() in ('TESTIGO_1', 'TESTIGO_2', 'TESTIGO')]

    integridad_valida = True
    razon_invalidez = []

    # Validar firma del médico
    if med_firma:
        crypto_result = clinical_signing.verify_signature_record(db, med_firma)
        if not crypto_result["complete"]:
            integridad_valida = False
            razon_invalidez.extend(crypto_result["errors"] or ["Firma médica sin verificación criptográfica completa"])
    else:
        integridad_valida = False
        razon_invalidez.append("No existe firma médica ECDSA CANONICAL_V2")

    # Validar firma del tutor / paciente
    if firmante_firma:
        if firmante_firma.canonical_payload and firmante_firma.payload_hash:
            calc_hash = hashlib.sha256(firmante_firma.canonical_payload.encode('utf-8')).hexdigest()
            if calc_hash != firmante_firma.payload_hash:
                integridad_valida = False
                razon_invalidez.append("Discrepancia en snapshot de evidencia biométrica presencial")

    if not integridad_valida:
        return {
            "valido": False,
            "estado": "INTEGRIDAD_COMPROMETIDA",
            "mensaje": "¡Alerta de Seguridad! Integridad Documental Comprometida (" + "; ".join(razon_invalidez) + ")",
            "color": "rose",
            "paciente": pt_nombre,
            "folio": folio_target,
            "edad": pt_edad,
            "formato": doc_title,
            "codigo": doc_target,
            "slot": slot_target,
            "id": doc_reg.doc_uuid if doc_reg else target_id,
            "doc_uuid": doc_reg.doc_uuid if doc_reg else target_id,
            "pdf_path": None,
            "medico": {
                "nombre": med_firma.nombre_medico if med_firma else "Sin registro",
                "cedula": med_firma.cedula_profesional if med_firma else ""
            },
            "firmante": None,
            "testigos": [],
            "hash_sha256": med_firma.hash_sha256 if med_firma else None,
            "sello_digital": med_firma.sello_digital if med_firma else None
            ,"tsa_status": med_firma.tsa_status if med_firma else tsa_client.SIN_TSA
        }

    # CASO 4: FIRMA ÍNTEGRA, AUTÉNTICA Y ACTIVA
    firmante_info = None
    if firmante_firma:
        f_obj = db.query(models.BiometriaFirmanteEpisodio).filter(models.BiometriaFirmanteEpisodio.id == firmante_firma.firmante_id).first() if firmante_firma.firmante_id else None
        firmante_info = {
            "nombre": firmante_firma.nombre_medico,
            "rol": firmante_firma.rol_firmante,
            "parentesco": f_obj.parentesco if f_obj else (firmante_firma.rol_firmante or "Tutor / Representante"),
            "identificacion": f_obj.identificacion_oficial if f_obj else firmante_firma.cedula_profesional,
            "fecha": firmante_firma.fecha_hora_firma.strftime("%d/%m/%Y a las %H:%M:%S hrs") if firmante_firma.fecha_hora_firma else "",
            "hash_sha256": firmante_firma.hash_sha256,
            "sello_digital": firmante_firma.sello_digital
        }

    testigos_info = []
    for tf in testigos_firmas:
        t_obj = db.query(models.BiometriaFirmanteEpisodio).filter(models.BiometriaFirmanteEpisodio.id == tf.firmante_id).first() if tf.firmante_id else None
        testigos_info.append({
            "nombre": tf.nombre_medico,
            "rol": tf.rol_firmante,
            "parentesco": t_obj.parentesco if t_obj else "Testigo Presencial",
            "fecha": tf.fecha_hora_firma.strftime("%d/%m/%Y a las %H:%M:%S hrs") if tf.fecha_hora_firma else "",
            "sello_digital": tf.sello_digital
        })

    primary_signature = med_firma or firmante_firma or firmas_activas[0]

    tsa_status = getattr(primary_signature, "tsa_status", None) or tsa_client.SIN_TSA
    public_state = (
        "VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA"
        if tsa_status == tsa_client.TSA_VERIFICADO
        else f"FIRMA_ECDSA_VALIDA_{tsa_status}"
    )
    return {
        "valido": True,
        "estado": public_state,
        "mensaje": (
            "Snapshot clínico CANONICAL_V2 íntegro, firma ECDSA verificada y TSA verificada."
            if tsa_status == tsa_client.TSA_VERIFICADO
            else f"Firma ECDSA válida; sellado de tiempo no completo ({tsa_status})."
        ),
        "tsa_status": tsa_status,
        "color": "emerald",
        "paciente": pt_nombre,
        "folio": folio_target,
        "edad": pt_edad,
        "formato": doc_title,
        "codigo": doc_target,
        "slot": slot_target,
        "id": doc_reg.doc_uuid if doc_reg else target_id,
        "doc_uuid": doc_reg.doc_uuid if doc_reg else target_id,
        "pdf_path": None,
        "medico": {
            "nombre": med_firma.nombre_medico if med_firma else None,
            "cedula": med_firma.cedula_profesional if med_firma else None,
            "fecha": med_firma.fecha_hora_firma.strftime("%d/%m/%Y a las %H:%M:%S hrs") if med_firma and med_firma.fecha_hora_firma else None,
            "hash_sha256": med_firma.hash_sha256 if med_firma else None,
            "sello_digital": med_firma.sello_digital if med_firma else None
        } if med_firma else None,
        "firmante": firmante_info,
        "naturaleza_firma_firmante": (
            "AUTENTICACION_BIOMETRICA_Y_EVIDENCIA_DE_ACTO_NO_FEA_PERSONAL"
            if firmante_firma else None
        ),
        "testigos": testigos_info,
        "hash_sha256": primary_signature.hash_sha256,
        "sello_digital": primary_signature.sello_digital,
        "fecha_hora_firma": primary_signature.fecha_hora_firma.strftime("%d/%m/%Y a las %H:%M:%S hrs") if primary_signature.fecha_hora_firma else ""
    }


@app.get("/verificar", response_class=HTMLResponse)
@app.get("/verificar/documento", response_class=HTMLResponse)
@app.get("/verificar/expediente", response_class=HTMLResponse)
@app.get("/verificar/expediente/{pt_num}", response_class=HTMLResponse)
@app.get("/api/verificar", response_class=HTMLResponse)
@app.get("/api/verificar/documento", response_class=HTMLResponse)
@app.get("/api/verificar/expediente", response_class=HTMLResponse)
@app.get("/api/verificar/expediente/{pt_num}", response_class=HTMLResponse)
def verificar_documento_publico(
    request: Request,
    id: Optional[str] = None,
    doc_uuid: Optional[str] = None,
    doc: Optional[str] = None,
    pt: Optional[str] = None,
    pt_num: Optional[str] = None,
    folio: Optional[str] = None,
    slot: Optional[int] = None,
    mrnum: Optional[int] = None,
    t: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Portal institucional de cotejo y verificación de autenticidad documental (NOM-004-SSA3-2012 / NOM-024-SSA3-2012).
    Se accede de forma pública e instantánea al escanear el código QR impreso desde cualquier smartphone.
    """
    if any(value is not None for value in (pt, pt_num, folio, doc, slot, mrnum)) and not (id or doc_uuid):
        raise HTTPException(
            status_code=404,
            detail="La verificación pública requiere el identificador opaco del QR.",
        )
    estado_data = get_documento_estado_verificacion(
        request=request,
        id=id,
        doc_uuid=doc_uuid,
        doc=doc,
        pt=pt,
        pt_num=pt_num,
        folio=folio,
        slot=slot,
        mrnum=mrnum,
        db=db
    )

    pt_nombre = estado_data.get("paciente") or "Nombre no disponible"
    pt_expediente = estado_data.get("folio") or "No disponible"
    pt_edad = estado_data.get("edad") or "No disponible"
    if pt_edad and "años años" in str(pt_edad):
        pt_edad = str(pt_edad).replace("años años", "años")
    doc_title = estado_data.get("formato") or "Documento Clínico Oficial"
    doc_target = estado_data.get("codigo") or "PLT-02"
    
    estado = estado_data.get("estado")
    is_valido = estado_data.get("valido", False)

    med_info = estado_data.get("medico") or {}
    medico_nombre = med_info.get("nombre") or "Pendiente de Asignación / Firma"
    medico_cedula = med_info.get("cedula") or "—"
    fecha_firma_str = med_info.get("fecha") or estado_data.get("fecha_hora_firma") or "—"
    hash_str = estado_data.get("hash_sha256") or "—"
    sello_str = estado_data.get("sello_digital") or "—"

    # Configuración visual según el estado.
    #
    # `get_documento_estado_verificacion` devuelve `valido=True` para una
    # firma activa cuya evidencia se verificó correctamente. El campo
    # `estado` es más descriptivo (por ejemplo,
    # `FIRMA_ECDSA_VALIDA_TSA_PENDIENTE`) y no es literalmente `ACTIVA`.
    # Comparar contra ese texto hacía que una firma válida se mostrara como
    # "pendiente" en el portal público del QR.
    if is_valido:
        badge_bg = "var(--success-bg)"
        badge_border = "var(--success-border)"
        badge_color = "var(--success)"
        badge_icon = "✓"
        badge_title = (
            "Copia del expediente íntegra"
            if estado == "COPIA_INTEGRA_VERIFICADA"
            else "Documento firmado y verificado"
        )
        badge_desc = estado_data.get("mensaje") or (
            "La hoja impresa coincide exactamente con el registro original "
            "resguardado en el Expediente Clínico Electrónico (ECE)."
        )
        status_text = "✓ COPIA ÍNTEGRA VERIFICADA" if estado == "COPIA_INTEGRA_VERIFICADA" else "✓ AUTORIZADO Y FIRMADO"
        status_tag = f'<span style="color: var(--success); font-weight: 800;">{status_text}</span>'
    elif estado == "REVOCADA":
        badge_bg = "#fef3c7"
        badge_border = "#fcd34d"
        badge_color = "#b45309"
        badge_icon = "⚠"
        badge_title = "Firma Revocada / No Vigente"
        badge_desc = estado_data.get("mensaje") or "Este documento fue formalmente sustituido o re-firmado."
        status_tag = '<span style="color: #b45309; font-weight: 800;">⚠ FIRMA REVOCADA</span>'
    elif estado == "INTEGRIDAD_COMPROMETIDA":
        badge_bg = "#ffe4e6"
        badge_border = "#fda4af"
        badge_color = "#be123c"
        badge_icon = "✕"
        badge_title = "¡Alerta de Seguridad! Integridad Comprometida"
        badge_desc = estado_data.get("mensaje") or "El contenido actual no coincide con el registro resguardado."
        status_tag = '<span style="color: #be123c; font-weight: 800;">✕ ALTERACIÓN DETECTADA</span>'
    elif estado == "RECURSO_NO_DISPONIBLE":
        badge_bg = "#f1f5f9"
        badge_border = "#cbd5e1"
        badge_color = "#475569"
        badge_icon = "!"
        badge_title = "Copia no disponible"
        badge_desc = estado_data.get("mensaje") or "No se encontró la copia resguardada del expediente."
        status_tag = '<span style="color: #64748b; font-weight: 800;">COPIA NO DISPONIBLE</span>'
    else: # SIN_FIRMA
        badge_bg = "#f1f5f9"
        badge_border = "#cbd5e1"
        badge_color = "#475569"
        badge_icon = "⏱"
        badge_title = "Documento Pendiente de Firma"
        badge_desc = "Este formato aún no cuenta con firma electrónica ni biométrica asentada en el ECE."
        status_tag = '<span style="color: #64748b; font-weight: 800;">PENDIENTE DE FIRMA</span>'

    import time
    t_now = int(time.time())
    resolved_id = estado_data.get("doc_uuid") or estado_data.get("id")
    pdf_url = f"/api/verificar/pdf/documento?{urlencode({'id': resolved_id, 't': t_now})}"

    pt_nombre = html_escape(str(pt_nombre))
    pt_expediente = html_escape(str(pt_expediente))
    pt_edad = html_escape(str(pt_edad))
    doc_title = html_escape(str(doc_title))
    doc_target = html_escape(str(doc_target))
    medico_nombre = html_escape(str(medico_nombre))
    medico_cedula = html_escape(str(medico_cedula))
    fecha_firma_str = html_escape(str(fecha_firma_str))
    hash_str = html_escape(str(hash_str))
    sello_str = html_escape(str(sello_str))
    badge_desc = html_escape(str(badge_desc))
    pdf_url = html_escape(pdf_url, quote=True)
    pdf_action_html = (
        f'<a href="{pdf_url}" class="btn-action" target="_blank" rel="noopener noreferrer">📄 Abrir Documento PDF Oficial</a>'
        if estado not in {"RECURSO_NO_DISPONIBLE", "INTEGRIDAD_COMPROMETIDA"}
        else ""
    )

    # Cargar logo oficial
    logo_b64 = ""
    try:
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Formatos VERTICAL", "Encabezado, pie, lateral", "logo_hes_oficial.png"))
        if not os.path.exists(logo_path):
            logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "logo.png"))
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as lf:
                logo_b64 = base64.b64encode(lf.read()).decode("ascii")
    except Exception:
        pass

    logo_img_tag = f'<img src="data:image/png;base64,{logo_b64}" alt="Hospital Escandón" style="height: 50px; max-width: 240px; object-fit: contain; margin: 0 auto 6px auto; display: block;" />' if logo_b64 else '<div class="hospital-title"><span>🏥</span> Hospital Escandón</div>'

    if estado_data.get("codigo") == "HE-DIRMED-EXPEDIENTE-COMPLETO":
        generated_at = html_escape(str(estado_data.get("fecha_generacion") or "—"))
        medical_card_html = f"""
        <div class="card">
            <div class="card-header">📄 Integridad de la copia institucional</div>
            <div class="data-row">
                <span class="data-label">Fecha de generación</span>
                <span class="data-val">{generated_at}</span>
            </div>
            <div class="data-row" style="margin-top: 12px;">
                <span class="data-label">Huella SHA-256 del PDF resguardado</span>
                <div class="hash-box">{hash_str}</div>
            </div>
            <div class="data-row" style="margin-top: 12px;">
                <span class="data-label">Alcance del cotejo</span>
                <span class="data-val">Confirma la integridad de esta copia; no constituye una firma FEA del expediente compilado. Las firmas de cada formato se conservan en el PDF.</span>
            </div>
        </div>
        """
    elif is_valido and med_info.get("nombre"):
        medical_card_html = f"""
        <div class="card">
            <div class="card-header">🔐 Atribución Criptográfica y Firma Médica FEA</div>
            <div class="data-row">
                <span class="data-label">Médico Tratante / Firmante</span>
                <span class="data-val">{medico_nombre}</span>
            </div>
            <div class="data-grid" style="margin-top: 10px;">
                <div class="data-row">
                    <span class="data-label">Cédula Profesional</span>
                    <span class="data-val">{medico_cedula}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Fecha y Hora de Firma</span>
                    <span class="data-val">{fecha_firma_str}</span>
                </div>
            </div>
            <div class="data-row" style="margin-top: 12px;">
                <span class="data-label">Método de Autenticación</span>
                <span class="data-val" style="font-size: 12.5px; color: #0f766e;">✓ Firma Electrónica Avanzada (FEA ECDSA P-256 / NOM-024-SSA3)</span>
            </div>
            <div class="data-row" style="margin-top: 12px;">
                <span class="data-label">Huella Digital del Documento (Hash SHA-256)</span>
                <div class="hash-box">{hash_str}</div>
            </div>
            <div class="data-row" style="margin-top: 10px;">
                <span class="data-label">Sello Digital FEA</span>
                <div class="hash-box" style="color: #4ade80;">{sello_str}</div>
            </div>
        </div>
        """
    else:
        medical_card_html = ""

    # Sección adicional de firmante presencial si existe
    firmante_data = estado_data.get("firmante")
    firmante_card_html = ""
    if firmante_data:
        firmante_card_html = f"""
        <div class="card">
            <div class="card-header">✍️ Tutor / Representante Legal / Testigos</div>
            <div class="data-row">
                <span class="data-label">Nombre del Firmante Presencial</span>
                <span class="data-val">{html_escape(str(firmante_data.get('nombre') or ''))}</span>
            </div>
            <div class="data-grid" style="margin-top: 10px;">
                <div class="data-row">
                    <span class="data-label">Parentesco / Rol</span>
                    <span class="data-val">{html_escape(str(firmante_data.get('parentesco') or ''))}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Fecha y Hora</span>
                    <span class="data-val">{html_escape(str(firmante_data.get('fecha') or ''))}</span>
                </div>
            </div>
            <div class="data-row" style="margin-top: 10px;">
                <span class="data-label">Sello Biométrico Dactilar</span>
                <div class="hash-box" style="color: #38bdf8;">{html_escape(str(firmante_data.get('sello_digital') or ''))}</div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cotejo de Expediente Clínico • Hospital Escandón</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #0056b3;
            --primary-dark: #003d80;
            --success: #0d8a4f;
            --success-bg: #eafaf1;
            --success-border: #a3e6be;
            --bg-page: #f4f7fb;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        body {{
            background-color: var(--bg-page);
            color: var(--text-main);
            line-height: 1.5;
            padding: 16px 12px 32px;
            margin: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            -webkit-text-size-adjust: 100%;
        }}
        .container {{
            width: 100%;
            max-width: 560px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
        }}
        .header {{
            background: #ffffff;
            border-radius: 16px 16px 0 0;
            padding: 24px 20px 18px;
            text-align: center;
            border-bottom: 3px solid var(--primary);
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        }}
        .hospital-sub {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-top: 3px;
        }}
        .verified-badge {{
            background: {badge_bg};
            border: 1.5px solid {badge_border};
            border-radius: 14px;
            padding: 16px 14px;
            margin: 16px 0;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }}
        .badge-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 44px;
            height: 44px;
            background: {badge_color};
            color: white;
            border-radius: 50%;
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .badge-title {{
            font-size: 15px;
            font-weight: 800;
            color: {badge_color};
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        .badge-desc {{
            font-size: 12px;
            color: #334155;
            margin-top: 4px;
            line-height: 1.4;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 14px;
            padding: 18px 20px;
            margin-bottom: 14px;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        }}
        .card-header {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: var(--primary);
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            border-bottom: 1px solid #f1f5f9;
            padding-bottom: 8px;
        }}
        .data-row {{
            display: flex;
            flex-direction: column;
            margin-bottom: 12px;
        }}
        .data-row:last-child {{
            margin-bottom: 0;
        }}
        .data-label {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }}
        .data-val {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-main);
            margin-top: 2px;
            word-break: break-word;
        }}
        .data-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
        .hash-box {{
            background: #0f172a;
            color: #38bdf8;
            font-family: 'Courier New', Courier, monospace;
            font-size: 10.5px;
            padding: 10px 12px;
            border-radius: 8px;
            word-break: break-all;
            margin-top: 4px;
            border: 1px solid #1e293b;
        }}
        .tag {{
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            background: #e0f2fe;
            color: #0369a1;
            margin-top: 4px;
        }}
        .btn-action {{
            display: block;
            width: 100%;
            background: var(--primary);
            color: white;
            text-decoration: none;
            text-align: center;
            padding: 14px 20px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 14px;
            box-shadow: 0 4px 10px rgba(0,86,179,0.25);
            transition: all 0.2s;
            margin-top: 8px;
        }}
        .btn-action:hover {{
            background: var(--primary-dark);
        }}
        .footer {{
            text-align: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 24px;
            padding: 16px 10px 24px;
            line-height: 1.5;
            width: 100%;
        }}
        .norma-badge {{
            display: inline-block;
            background: #f1f5f9;
            color: #475569;
            font-size: 10px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 4px;
            margin-top: 6px;
        }}
        @media (max-width: 480px) {{
            body {{
                padding: 10px 8px 24px;
            }}
            .card {{
                padding: 14px 12px;
            }}
            .header {{
                padding: 18px 14px 14px;
            }}
            .data-grid {{
                grid-template-columns: 1fr 1fr;
                gap: 8px;
            }}
            .data-val {{
                font-size: 13px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            {logo_img_tag}
            <div class="hospital-sub">Fundación María Ana Mier de Escandón, I.A.P.</div>
            <div class="norma-badge">NOM-004-SSA3-2012 • NOM-024-SSA3-2012</div>
        </div>

        <div class="verified-badge">
            <div class="badge-icon">{badge_icon}</div>
            <div class="badge-title">{badge_title}</div>
            <div class="badge-desc">{badge_desc}</div>
        </div>

        <!-- 1. Datos del Paciente -->
        <div class="card">
            <div class="card-header">👤 Datos de Identificación del Paciente</div>
            <div class="data-row">
                <span class="data-label">Nombre del Paciente</span>
                <span class="data-val">{pt_nombre}</span>
            </div>
            <div class="data-grid" style="margin-top: 10px;">
                <div class="data-row">
                    <span class="data-label">Expediente / Folio</span>
                    <span class="data-val" style="color: var(--primary);">{pt_expediente}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Edad Registrada</span>
                    <span class="data-val">{pt_edad}</span>
                </div>
            </div>
        </div>

        <!-- 2. Formato Clínico -->
        <div class="card">
            <div class="card-header">📋 Consentimiento Informado / Acto Médico</div>
            <div class="data-row">
                <span class="data-label">Formato Oficial</span>
                <span class="data-val">{doc_title}</span>
            </div>
            <div class="data-grid" style="margin-top: 10px;">
                <div class="data-row">
                    <span class="data-label">Código Institucional</span>
                    <span class="data-val"><span class="tag">{doc_target}</span></span>
                </div>
                <div class="data-row">
                    <span class="data-label">Estado en ECE</span>
                    <div style="margin-top: 2px;">{status_tag}</div>
                </div>
            </div>
        </div>

        <!-- 3. Evidencia verificable del documento exacto -->
        {medical_card_html}

        {firmante_card_html}

        {pdf_action_html}

        <!-- Redes Sociales Oficiales y Canales de Contacto -->
        <div style="display: flex; justify-content: center; align-items: center; gap: 10px; margin: 24px 0 12px; flex-wrap: wrap;">
            <a href="https://www.facebook.com/hospitalescandoniap" target="_blank" rel="noopener" style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 10px; background: #1877F2; color: white; text-decoration: none; box-shadow: 0 2px 6px rgba(24,119,242,0.3);" title="Facebook">
                <svg style="width: 20px; height: 20px; fill: white;" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
            </a>
            <a href="https://www.instagram.com/hospital_escandon" target="_blank" rel="noopener" style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 10px; background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%); color: white; text-decoration: none; box-shadow: 0 2px 6px rgba(214,36,159,0.3);" title="Instagram">
                <svg style="width: 20px; height: 20px; fill: white;" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
            </a>
            <a href="https://www.tiktok.com/@hospitalescandon" target="_blank" rel="noopener" style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 10px; background: #000000; color: white; text-decoration: none; box-shadow: 0 2px 6px rgba(0,0,0,0.3);" title="TikTok">
                <svg style="width: 20px; height: 20px; fill: white;" viewBox="0 0 24 24"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.24 1.07-.14 1.61.24 1.64 1.82 2.89 3.5 2.75 1.51-.04 2.87-1.07 3.25-2.52.12-.51.15-1.05.15-1.58.02-4.98.01-9.97.01-14.96z"/></svg>
            </a>
            <a href="https://x.com/hospescandon" target="_blank" rel="noopener" style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 10px; background: #0f1419; color: white; text-decoration: none; box-shadow: 0 2px 6px rgba(15,20,25,0.3);" title="X (Twitter)">
                <svg style="width: 18px; height: 18px; fill: white;" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </a>
            <a href="https://www.youtube.com/@hospitalescandoniap" target="_blank" rel="noopener" style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 10px; background: #FF0000; color: white; text-decoration: none; box-shadow: 0 2px 6px rgba(255,0,0,0.3);" title="YouTube">
                <svg style="width: 22px; height: 22px; fill: white;" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
            </a>
            <a href="https://hospitalescandon.org/contacto.html" target="_blank" rel="noopener" style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 10px; background: #0056b3; color: white; text-decoration: none; box-shadow: 0 2px 6px rgba(0,86,179,0.3);" title="Sitio Web y Contacto">
                <svg style="width: 20px; height: 20px; fill: white;" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
            </a>
        </div>

        <div class="footer">
            <strong>Hospital Escandón • Calidad Médica a tu Alcance</strong><br/>
            Gral. Salvador Alvarado 7, Col. Escandón, Miguel Hidalgo, CDMX<br/>
            Tels. 55-5516-8020 / 55-5515-8167 • Licencia Sanitaria No. 07 AM 09 011 163<br/>
            <span style="font-size: 9.5px; color: #94a3b8; display: inline-block; margin-top: 6px;">
                Verificación en tiempo real procesada por el Servidor Seguro de Bitácora HES.
            </span>
            <div style="margin-top: 10px;">
                <a href="https://github.com/TeruIshijo1" target="_blank" rel="noopener" style="font-family: monospace; font-size: 10px; color: #94a3b8; text-decoration: none; opacity: 0.65; transition: opacity 0.2s;" onmouseover="this.style.opacity='1'; this.style.color='#0056b3';" onmouseout="this.style.opacity='0.65'; this.style.color='#94a3b8';">
                    Autor: Ing. Alberto García M.
                </a>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(
        content=html_content,
        status_code=200,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/api/verificar/pdf/documento")
@app.get("/verificar/pdf/documento")
@app.get("/api/verificar/pdf")
@app.get("/verificar/pdf")
@app.get("/api/verificar/pdf/{pt_num}")
@app.get("/verificar/pdf/{pt_num}")
def descargar_pdf_verificado(
    id: Optional[str] = None,
    doc_uuid: Optional[str] = None,
    pt_num: Optional[str] = None,
    doc: Optional[str] = None,
    pt: Optional[str] = None,
    folio: Optional[str] = None,
    slot: Optional[int] = None,
    mrnum: Optional[int] = None,
    evolucion: Optional[int] = None,
    t: Optional[int] = None
):
    """
    Ruta universal para entrega y visualización directa de PDFs verificados por QR (NOM-004 / NOM-024).
    NORMA GLOBAL INSTITUCIONAL: La entrega es 100% fiel al registro del código QR (DocumentoVerificacionQR).
    Localiza el PDF generado y firmado vinculado al QR y lo entrega con Content-Disposition: inline.
    """
    target_id = id or doc_uuid
    if not target_id:
        raise HTTPException(
            status_code=404,
            detail="La descarga pública requiere el identificador opaco del QR.",
        )
    doc_reg = None

    # FASE 1: BÚSQUEDA DIRECTA EN DocumentoVerificacionQR POR IDENTIFICADOR DE QR (id / doc_uuid)
    if target_id:
        try:
            db_s = SessionLocal()
            doc_reg = find_doc_verificacion(db_s, target_id)
            db_s.close()
        except Exception as e_id:
            print(f"Error consultando DocumentoVerificacionQR por id '{target_id}': {e_id}")

    if not doc_reg:
        raise HTTPException(status_code=404, detail="Documento verificable no encontrado.")
    raw_pt = doc_reg.pt_num
    clean_pt = re.sub(r'[^0-9]', '', str(raw_pt)) if raw_pt else ""
    doc_target = (doc_reg.codigo_formato or "").upper().strip()
    target_mr = doc_reg.slot

    # FASE 3: ENTREGA DEL ARCHIVO FÍSICO ASOCIADO AL REGISTRO QR (PRIORIDAD GLOBAL)
    if doc_reg:
        file_to_serve = None
        # A) Ruta absoluta exacta registrada en BD
        if doc_reg.pdf_path and os.path.exists(doc_reg.pdf_path) and os.path.getsize(doc_reg.pdf_path) > 1024:
            file_to_serve = doc_reg.pdf_path
        # B) Búsqueda por nombre de archivo en directorios físicos estándar
        elif doc_reg.pdf_filename:
            candidate_dirs = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scratch")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "pdfs")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            ]
            for c_dir in candidate_dirs:
                c_path = os.path.join(c_dir, doc_reg.pdf_filename)
                if os.path.exists(c_path) and os.path.getsize(c_path) > 1024:
                    file_to_serve = c_path
                    break

        if file_to_serve:
            if doc_reg.hash_sha256:
                with open(file_to_serve, "rb") as registered_file:
                    current_hash = hashlib.sha256(registered_file.read()).hexdigest()
                if not hmac.compare_digest(current_hash, doc_reg.hash_sha256):
                    raise HTTPException(status_code=409, detail="La integridad del PDF verificable no pudo ser confirmada.")
            filename = doc_reg.pdf_filename or os.path.basename(file_to_serve)
            return FileResponse(
                path=file_to_serve,
                media_type="application/pdf",
                filename=filename,
                content_disposition_type="inline",
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Disposition": f'inline; filename="{filename}"',
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )

    raise HTTPException(status_code=404, detail="El recurso PDF verificable no está disponible.")

    # FASE 4: SI NO ESTÁ EN BD PERO EXISTE EL ARCHIVO GENERADO EN DISCO, SERVIRLO DIRECTAMENTE
    try:
        from services import pdf_service
        db_s = SessionLocal()
        existing_disk_pdf = pdf_service.find_existing_valid_pdf(
            db_session=db_s,
            clean_pt=clean_pt,
            format_codes=[doc_target] if doc_target else [],
            filename_patterns=[
                f"*{clean_pt}*{target_mr}*.pdf" if target_mr else f"*{clean_pt}*.pdf",
                f"CI_*_{clean_pt}_*.pdf",
                f"*urgencias_{clean_pt}_*.pdf",
                f"*hospitalizacion_{clean_pt}_*.pdf",
                f"expediente_completo_{clean_pt}.pdf"
            ]
        )
        db_s.close()
        if existing_disk_pdf and os.path.exists(existing_disk_pdf) and os.path.getsize(existing_disk_pdf) > 1024:
            filename = os.path.basename(existing_disk_pdf)
            return FileResponse(
                path=existing_disk_pdf,
                media_type="application/pdf",
                filename=filename,
                content_disposition_type="inline",
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Disposition": f'inline; filename="{filename}"',
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    except Exception as e_srv:
        print(f"Error comprobando PDF en disco: {e_srv}")

    # FASE 5: RECONSTRUCCIÓN DINÁMICA ÚNICAMENTE EN CASO DE QUE EL DOCUMENTO AÚN NO HAYA SIDO GENERADO EN DISCO
    doc_norm = doc_target.replace("_", "-").replace(" ", "").replace("/", "-")
    try:
        # 0. EXPEDIENTE CLÍNICO COMPLETO (HE-DIRMED-EXPEDIENTE-COMPLETO)
        if "EXPEDIENTE" in doc_norm or "COMPLETO" in doc_norm or "INTEGRAL" in doc_norm:
            return get_pdf_expediente_completo(clean_pt)

        # 1. NOTA DE HOSPITALIZACIÓN (PLT-24 / 24_HOJA_EVOL)
        elif "PLT-24" in doc_norm or "HOJA-EVOL" in doc_norm or "HOSPITALIZACION" in doc_norm or doc_norm.endswith("-24") or doc_norm == "24":
            return get_pdf_nota_hospitalizacion(clean_pt, evolucion=target_mr)

        # 2. NOTA DE URGENCIAS (PLT-87 / 87-01 / NE-URG / SINPRO)
        elif "PLT-87" in doc_norm or "87-01" in doc_norm or "NE-URG" in doc_norm or "SINPRO" in doc_norm or "URGENCIAS" in doc_norm or doc_norm.endswith("-87") or doc_norm == "87":
            return get_pdf_nota_urgencias(clean_pt, evolucion=target_mr)

        # 3. CONSENTIMIENTO 32/01 (Ecocardiograma Transesofágico)
        elif "PLT-32" in doc_norm or "32-01" in doc_norm or "TRANSESOFAGICO" in doc_norm or "ETE" in doc_norm or doc_norm.endswith("-32") or doc_norm == "32":
            return get_pdf_consentimiento_32_01(clean_pt)

        # 4. CONSENTIMIENTO 34/01 (Mesa Inclinada / Tilt Test)
        elif "PLT-34" in doc_norm or "34-01" in doc_norm or "INCLINADA" in doc_norm or "TILT" in doc_norm or "EMI" in doc_norm or doc_norm.endswith("-34") or doc_norm == "34":
            return get_pdf_consentimiento_34_01(clean_pt, mrnum=target_mr)

        # 5. CONSENTIMIENTO 43 (Intubación Endotraqueal / Soporte Ventilatorio)
        elif "PLT-43" in doc_norm or "INTUBACION" in doc_norm or "VENTILATORIO" in doc_norm or doc_norm.endswith("-43") or doc_norm == "43":
            return get_pdf_consentimiento_43(clean_pt, mrnum=target_mr)

        # 6. CONSENTIMIENTO EED (Ecocardiograma de Estrés con Dobutamina)
        elif "PLT-EED" in doc_norm or "EED" in doc_norm or "DOBUTAMINA" in doc_norm:
            return get_pdf_consentimiento_eed(clean_pt)

        # 7. CONSENTIMIENTO 25 (Revisión Gineco-Obstétrica Consulta Externa)
        elif "PLT-25" in doc_norm or "RGO-CE" in doc_norm or doc_norm.endswith("-25") or doc_norm == "25":
            return get_pdf_consentimiento_25(clean_pt, mrnum=target_mr)

        # 8a. EGRESO VOLUNTARIO (HE-DIRMED-SINPRO-PLT-15)
        elif "EGRESO" in doc_norm or "VOLUNTARIO" in doc_norm or "SINPRO-PLT-15" in doc_norm or "PLT-EV-15" in doc_norm or "EV-HOSP" in doc_norm:
            return get_pdf_egreso_voluntario_15(clean_pt, mrnum=target_mr)

        # 8b. CONSENTIMIENTO 15 (Cesárea)
        elif "PLT-15" in doc_norm or "CESAREA" in doc_norm or doc_norm.endswith("-15") or doc_norm == "15":
            return get_pdf_consentimiento_15(clean_pt, mrnum=target_mr)

        # 8c. CONSENTIMIENTO 11 (No Reanimación / Voluntad Anticipada)
        elif "PLT-11" in doc_norm or "REANIMACION" in doc_norm or "NO-REANIMACION" in doc_norm or doc_norm.endswith("-11") or doc_norm == "11":
            return get_pdf_consentimiento_11(clean_pt, mrnum=target_mr)

        # 8d. CONSENTIMIENTO 19 (Histerectomía)
        elif "PLT-19" in doc_norm or "HISTERECTOMIA" in doc_norm or doc_norm.endswith("-19") or doc_norm == "19":
            return get_pdf_consentimiento_19(clean_pt, mrnum=target_mr)

        # 8e. CONSENTIMIENTO 06 (Procedimiento Anestésico)
        elif "PLT-06" in doc_norm or "ANESTESICO" in doc_norm or "ANESTESIA" in doc_norm or "CI-APA" in doc_norm or doc_norm.endswith("-06") or doc_norm == "06":
            return get_pdf_consentimiento_06(clean_pt, mrnum=target_mr)

        # 8f. CONSENTIMIENTO 09 (Transfusión de Hemocomponentes)
        elif "PLT-09" in doc_norm or "PLT-9" in doc_norm or "TRANSFUSION" in doc_norm or "HEMOCOMPONENTES" in doc_norm or "AUT-TRANS-HEMO" in doc_norm or doc_norm.endswith("-09") or doc_norm.endswith("-9") or doc_norm in ("09", "9"):
            return get_pdf_consentimiento_09(clean_pt, mrnum=target_mr)

        # 9. CONSENTIMIENTO 12 (Hospitalización Gineco-Obstétrica)
        elif "PLT-12" in doc_norm or "RGO-HU" in doc_norm or doc_norm.endswith("-12") or doc_norm == "12":
            return get_pdf_consentimiento_12(clean_pt, mrnum=target_mr)

        # 10. CONSENTIMIENTO 04 (Catéter Venoso Central)
        elif "PLT-04" in doc_norm or "CATETER" in doc_norm or "CVC" in doc_norm or doc_norm.endswith("-04") or doc_norm == "04":
            return get_pdf_consentimiento_04(clean_pt, mrnum=target_mr)

        # 11. CONSENTIMIENTO 08 (Admisión Continua / Procedimientos Diagnósticos)
        elif "PLT-08" in doc_norm or "ADMISION" in doc_norm or doc_norm.endswith("-08") or doc_norm == "08":
            return get_pdf_consentimiento_08(clean_pt, mrnum=target_mr)

        # 12. CONSENTIMIENTO 02 (Tratamiento Quirúrgico / Disentimiento)
        elif "PLT-02" in doc_norm or "QUIRURGICO" in doc_norm or "DISENTIMIENTO" in doc_norm or doc_norm.endswith("-02") or doc_norm == "02":
            return get_pdf_consentimiento_02(clean_pt, mrnum=target_mr)

        # Fallback según texto genérico
        else:
            return get_pdf_consentimiento_02(clean_pt, mrnum=target_mr)
    except Exception as e:
        print(f"Error en descargar_pdf_verificado para doc={doc_target}, pt={clean_pt}: {e}")
        return get_pdf_consentimiento_02(clean_pt, mrnum=target_mr)



@app.get("/api/camas/ocupacion", response_model=List[schemas.OcupacionArea])

def get_ocupacion_camas(db: Session = Depends(get_db)):

    """Calcula y devuelve la ocupación de camas por área siguiendo la lógica del Dashboard Directivo."""

    camas_activas = db.query(models.Cama).filter(models.Cama.activo == True).all()

    

    areas = {}

    for cama in camas_activas:

        if cama.area not in areas:

            areas[cama.area] = {

                "total": 0,

                "ocupadas": 0,

                "disponibles": 0,

                "mantenimiento": 0

            }

        

        areas[cama.area]["total"] += 1

        if cama.estado == "OCUPADA":

            areas[cama.area]["ocupadas"] += 1

        elif cama.estado == "DISPONIBLE":

            areas[cama.area]["disponibles"] += 1

        elif cama.estado == "MANTENIMIENTO":

            areas[cama.area]["mantenimiento"] += 1

            

    resultado = []

    for area, stats in areas.items():

        total = stats["total"]

        ocupadas = stats["ocupadas"]

        porcentaje = round((ocupadas * 100.0) / total, 2) if total > 0 else 0.0

        

        resultado.append({

            "area": area,

            "total_camas": total,

            "camas_ocupadas": ocupadas,

            "camas_disponibles": stats["disponibles"],

            "camas_mantenimiento": stats["mantenimiento"],

            "porcentaje_ocupacion": porcentaje

        })

        

    return resultado



# === AGENDA MEDICA Y CITAS ===



class CitaCreateSchema(BaseModel):
    medico_id: Optional[int] = None
    paciente_id: Optional[int] = None
    pt_num: Optional[str] = None
    expediente: Optional[str] = None
    nombre_paciente_manual: Optional[str] = None
    fecha_hora: str # ISO string o YYYY-MM-DD HH:MM
    motivo: str
    lugar: Optional[str] = "Consultorio - Consulta Externa"
    notas: Optional[str] = None

@app.get("/api/medicos/list")
def get_medicos_list(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Obtiene la lista de médicos activos para asignación en agenda."""
    query = db.query(models.Medico).filter(models.Medico.activo_status == True)
    if normalize_role(getattr(current_user, "rol", "")) in {"medico", "ayudante"}:
        query = query.filter(models.Medico.id == current_user.id)
    medicos = query.all()
    return [
        {
            "id": m.id,
            "nombre": m.nombre_completo,
            "especialidad": m.especialidad or "Medicina General",
            "cedula": m.cedula,
            "numero_empleado": m.numero_empleado,
            "horario": m.horario_laboral or "Lunes a Viernes 08:00 - 16:00"
        }
        for m in medicos
    ]

@app.get("/api/agenda/citas")
def get_agenda_citas(
    medico_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Obtiene las citas programadas de la agenda médica con resolución determinística del expediente clínico (PTNum)."""
    query = db.query(models.CitaMedica)
    if normalize_role(getattr(current_user, "rol", "")) in {"medico", "ayudante"}:
        # Un médico sólo puede consultar su propia agenda, aunque manipule el
        # parámetro de filtro desde el navegador.
        query = query.filter(models.CitaMedica.medico_id == current_user.id)
    elif medico_id:
        query = query.filter(models.CitaMedica.medico_id == medico_id)
    
    citas = query.order_by(models.CitaMedica.fecha_hora.asc()).all()
    
    resultado = []
    for c in citas:
        medico_nom = c.medico.nombre_completo if c.medico else "Médico de Guardia"
        medico_esp = c.medico.especialidad if c.medico else "Medicina General"
        paciente_nom = c.paciente.nombre_completo if c.paciente else (c.nombre_paciente_manual or "Paciente no especificado")
        
        # Resolución determinística del PTNum / Expediente Hospitalario
        resolved_pt = None
        
        # 1. Extraer desde el texto del paciente si contiene (PT-XXXX) o similar
        if c.nombre_paciente_manual:
            m = re.search(r'(?:PT-?|EXP-?|#|\()(\d+)\)?', c.nombre_paciente_manual, re.IGNORECASE)
            if m:
                resolved_pt = m.group(1)
        
        # 2. Si no se encontró en el texto, extraer desde el paciente asociado (c.paciente.codigo_barras)
        if not resolved_pt and c.paciente and c.paciente.codigo_barras:
            m = re.search(r'(\d+)', str(c.paciente.codigo_barras))
            if m:
                resolved_pt = m.group(1)
            else:
                resolved_pt = str(c.paciente.codigo_barras).strip()
        
        # 3. Si aún no se encontró y hay paciente_id, verificar si coincide con un paciente en Postgres
        if not resolved_pt and c.paciente_id:
            p_obj = c.paciente or db.query(models.Paciente).filter(models.Paciente.id == c.paciente_id).first()
            if p_obj and p_obj.codigo_barras:
                m = re.search(r'(\d+)', str(p_obj.codigo_barras))
                if m:
                    resolved_pt = m.group(1)
                else:
                    resolved_pt = str(p_obj.codigo_barras).strip()
            elif p_obj:
                resolved_pt = str(p_obj.id)
            else:
                resolved_pt = str(c.paciente_id)
        
        # Fallback de seguridad
        if not resolved_pt and c.paciente_id:
            resolved_pt = str(c.paciente_id)

        resultado.append({
            "id": c.id,
            "medico_id": c.medico_id,
            "medico_nombre": medico_nom,
            "medico_especialidad": medico_esp,
            "paciente_id": c.paciente_id,
            "pt_num": resolved_pt,
            "expediente": resolved_pt,
            "paciente_nombre": paciente_nom,
            "fecha_hora": c.fecha_hora.isoformat() if c.fecha_hora else "",
            "fecha": c.fecha_hora.strftime("%d/%m/%Y") if c.fecha_hora else "",
            "hora": c.fecha_hora.strftime("%H:%M") if c.fecha_hora else "",
            "motivo": c.motivo,
            "lugar": c.lugar,
            "estatus": c.estatus,
            "notas": c.notas
        })
    return resultado

@app.post("/api/agenda/citas")
def create_agenda_cita(
    cita: CitaCreateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Registra una nueva cita médica programada vinculándola al expediente clínico hospitalario."""
    current_role = normalize_role(getattr(current_user, "rol", ""))
    if current_role in {"medico", "ayudante"}:
        # La UI lo muestra como un campo fijo; esta validación evita que una
        # petición alterada asigne la cita a otro médico.
        cita.medico_id = current_user.id

    if not cita.medico_id:
        raise HTTPException(status_code=422, detail="Debe seleccionar un médico para la cita.")

    assigned_medico = db.query(models.Medico).filter(
        models.Medico.id == cita.medico_id,
        models.Medico.activo_status == True,
    ).first()
    if not assigned_medico:
        raise HTTPException(status_code=404, detail="El médico asignado no está disponible.")

    try:
        dt = datetime.datetime.fromisoformat(cita.fecha_hora.replace('Z', '+00:00'))
    except Exception:
        try:
            dt = datetime.datetime.strptime(cita.fecha_hora, "%Y-%m-%d %H:%M")
        except Exception:
            dt = datetime.datetime.now() + datetime.timedelta(days=1)
            
    # Validar y resolver FK paciente_id seguro para PostgreSQL
    resolved_paciente_id = None
    if cita.paciente_id:
        p_match = db.query(models.Paciente).filter(models.Paciente.id == cita.paciente_id).first()
        if p_match:
            resolved_paciente_id = p_match.id
        else:
            p_by_code = db.query(models.Paciente).filter(
                (models.Paciente.codigo_barras == str(cita.paciente_id)) |
                (models.Paciente.codigo_barras == f"PT-{cita.paciente_id}")
            ).first()
            if p_by_code:
                resolved_paciente_id = p_by_code.id

    if not resolved_paciente_id and (cita.pt_num or cita.expediente):
        pt_val = str(cita.pt_num or cita.expediente).replace("PT-", "").strip()
        p_by_code = db.query(models.Paciente).filter(
            (models.Paciente.codigo_barras == pt_val) |
            (models.Paciente.codigo_barras == f"PT-{pt_val}")
        ).first()
        if p_by_code:
            resolved_paciente_id = p_by_code.id

    if not resolved_paciente_id and cita.nombre_paciente_manual:
        m = re.search(r'(?:PT-?|EXP-?|#|\()(\d+)\)?', cita.nombre_paciente_manual, re.IGNORECASE)
        if m:
            pt_num_extracted = m.group(1)
            p_by_code = db.query(models.Paciente).filter(
                (models.Paciente.codigo_barras == pt_num_extracted) |
                (models.Paciente.codigo_barras == f"PT-{pt_num_extracted}")
            ).first()
            if p_by_code:
                resolved_paciente_id = p_by_code.id

    nueva_cita = models.CitaMedica(
        medico_id=cita.medico_id,
        paciente_id=resolved_paciente_id,
        nombre_paciente_manual=cita.nombre_paciente_manual,
        fecha_hora=dt,
        motivo=cita.motivo,

        lugar=cita.lugar or "Consultorio - Consulta Externa",

        notas=cita.notas,

        estatus="Programada"

    )

    db.add(nueva_cita)

    db.commit()

    db.refresh(nueva_cita)

    return {"message": "Cita programada con éxito", "id": nueva_cita.id}



# === FRONTEND (PRODUCCION) ===

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-eed")

def get_pdf_consentimiento_eed(pt_num: str):

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_num)

    if "error" in dashboard_data:

        raise HTTPException(status_code=404, detail=dashboard_data["error"])

    patient_info = dashboard_data.get("patient", {})

    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")

    hora_hoy = datetime.datetime.now().strftime("%H:%M")

    pt_data = {
        "nombre": patient_info.get("name", ""),
        "expediente": pt_num,
        "fecha_nacimiento": patient_info.get("dob", ""),
        "sexo": patient_info.get("sex", "M"),
        "cama": patient_info.get("room", "Urgencias"),
        "fecha": fecha_hoy,
        "hora": hora_hoy,
        "alergias": patient_info.get("allergies", ""),
        "fecha_ingreso": patient_info.get("fecha_ingreso", fecha_hoy),
        "hora_ingreso": patient_info.get("hora_ingreso", hora_hoy)
    }

    eed_data = dashboard_data.get("consentimiento_eed", {})

    pt_data.update(eed_data)

    

    import pdf_engine_eed
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_num, "HE-DIRMED-CONSUL-PLT-EED", 0, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        pt_data["firma_data"] = firma_data
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
    finally:
        db.close()

    pdf_path = pdf_engine_eed.generar_pdf_eed(pt_data, firma_data=firma_data)

    

    if os.path.exists(pdf_path):
        try:
            medico_n = (pt_data.get("firma_data", {}).get("nombre_medico") if pt_data.get("firma_data") else None) or pt_data.get("medico") or pt_data.get("medico_tratante")
            medico_c = (pt_data.get("firma_data", {}).get("cedula") if pt_data.get("firma_data") else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_num,
                codigo_formato="HE-DIRMED-CONSUL-PLT-EED",
                tipo_documento="Consentimiento Informado para Ecocardiograma de Estrés con Dobutamina",
                pdf_path=pdf_path,
                pdf_filename=f"CI_EED_{pt_num}.pdf",
                slot=1,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF EED para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"CI_EED_{pt_num}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="CI_EED_{pt_num}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF")



@app.post("/api/ehr/paciente/{pt_num}/consentimiento-eed")
def save_consentimiento_eed(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_eed", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-EED",
            tipo_documento="Consentimiento Informado para Ecocardiograma de Estrés con Dobutamina",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=0,
            nombre_medico=str(request_data.get("medico") or request_data.get("medico_tratante") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento EED: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024: se rompe la firma al modificar)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-EED",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA_POR_MODIFICACION"
            f.motivo_revocacion = "El documento fue modificado posteriormente."
        db.commit()
    except Exception as e:
        print(f"Error revoking signatures for Consentimiento EED: {e}")
        db.rollback()

    return {"message": "Consentimiento EED guardado con éxito", "status": "success"}


@app.get("/api/ehr/paciente/{pt_num}/consentimiento-25")
def get_consentimiento_25(pt_num: str, db: Session = Depends(get_db)):
    data = kh_database.fetch_consentimiento_25(pt_num)
    if isinstance(data, dict) and "error" not in data:
        last_hist = db.query(models.HistoricoNotaClinica).filter(
            models.HistoricoNotaClinica.pt_num == str(pt_num),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-25"
        ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                data["testigo1"] = hist_data.get("testigo1", "")
                data["testigo2"] = hist_data.get("testigo2", "")
                data["representante_legal"] = hist_data.get("representante_legal", "")
                data["paciente_o_representante"] = hist_data.get("paciente_o_representante", "")
            except Exception as e:
                print(f"Error parsing historic consent 25: {e}")
    return data


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-25")
def get_pdf_consentimiento_25(pt_num: str, mrnum: Optional[int] = None):
    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_num)
    if "error" in dashboard_data:
        raise HTTPException(status_code=404, detail=dashboard_data["error"])

    patient_info = dashboard_data.get("patient", {})
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    hora_hoy = datetime.datetime.now().strftime("%H:%M")

    pt_data = {
        "paciente_nombre": patient_info.get("name", ""),
        "expediente": patient_info.get("mrn", f"PT-{pt_num}"),
        "pt_num": str(pt_num),
        "fecha_nacimiento": patient_info.get("dob", ""),
        "edad": patient_info.get("age", ""),
        "medico_tratante": patient_info.get("attending_doctor") or "",
        "cedula": patient_info.get("cedula") or "",
        "fecha_ingreso": patient_info.get("fecha_ingreso", fecha_hoy),
        "hora_ingreso": patient_info.get("hora_ingreso", hora_hoy),
        "fecha_atencion": fecha_hoy,
        "hora_atencion": hora_hoy,
        "patient": patient_info
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c25_data = kh_database.fetch_consentimiento_25(pt_num, mrnum=effective_slot)
    if not effective_slot and isinstance(c25_data, dict) and "error" not in c25_data and c25_data.get("mrnum"):
        effective_slot = int(c25_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-25"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_num}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-25",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 25 for PDF: {e_hist}")
    finally:
        db.close()

    if c25_data and (not isinstance(c25_data, dict) or "error" not in c25_data):
        for k, v in c25_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v
        if c25_data.get("medico_tratante"):
            pt_data["medico_tratante"] = c25_data["medico_tratante"]
        if c25_data.get("created_on"):
            parts = c25_data["created_on"].split(" ")
            if len(parts) >= 1:
                pt_data["fecha_atencion"] = parts[0]
            if len(parts) >= 2:
                pt_data["hora_atencion"] = parts[1]

    is_doc_signed = bool(c25_data.get("signed_by") or c25_data.get("signed_on"))

    import pdf_engine_25
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_num, "HE-DIRMED-CONSUL-PLT-25", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c25_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c25_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_25_{pt_num}_{effective_slot}.pdf")
    pdf_engine_25.generate_consentimiento_25(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_num,
                codigo_formato="HE-DIRMED-CONSUL-PLT-25",
                tipo_documento="Consentimiento Informado para Revisión Ginecológica, Obstétrica y Consulta Externa",
                pdf_path=pdf_path,
                pdf_filename=f"CI_25_{pt_num}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 25 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"CI_25_{pt_num}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="CI_25_{pt_num}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 25")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-25")
def save_consentimiento_25_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_25", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-25",
            tipo_documento="Consentimiento Informado para Revisión Ginecológica, Obstétrica y Consulta Externa",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=0,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("n_medico") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 25: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-25",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 25: {e}")
        db.rollback()

    return res


# ─────────────────────────────────────────────────────────────
# ENDPOINTS FORMATO 34/01: ESTUDIO DE MESA INCLINADA (TILT TEST)
# ─────────────────────────────────────────────────────────────

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-34-01")
def get_consentimiento_34_01(pt_num: str, db: Session = Depends(get_db)):
    data = kh_database.fetch_consentimiento_34_01(pt_num)
    if isinstance(data, dict) and "error" not in data:
        last_hist = db.query(models.HistoricoNotaClinica).filter(
            models.HistoricoNotaClinica.pt_num == str(pt_num),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-34"
        ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k not in data or not data[k]:
                        data[k] = v
            except Exception as e:
                print(f"Error parsing historic consent 34_01: {e}")
    return data


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-34-01")
def get_pdf_consentimiento_34_01(pt_num: str, mrnum: Optional[int] = None):
    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_num)
    if "error" in dashboard_data:
        raise HTTPException(status_code=404, detail=dashboard_data["error"])

    patient_info = dashboard_data.get("patient", {})
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    hora_hoy = datetime.datetime.now().strftime("%H:%M")

    pt_data = {
        "paciente_nombre": patient_info.get("name", ""),
        "nombre": patient_info.get("name", ""),
        "expediente": patient_info.get("mrn", f"PT-{pt_num}"),
        "pt_num": str(pt_num),
        "fecha_nacimiento": patient_info.get("dob", ""),
        "edad": patient_info.get("age", ""),
        "sexo": patient_info.get("sex", "M"),
        "grupo_rh": "O POSITIVO",
        "alergias": "NEGADAS",
        "tipo_interrogatorio": "DIRECTO",
        "medico_tratante": patient_info.get("attending_doctor") or "",
        "cedula": patient_info.get("cedula") or "",
        "fecha_ingreso": patient_info.get("fecha_ingreso", fecha_hoy),
        "hora_ingreso": patient_info.get("hora_ingreso", hora_hoy),
        "fecha_atencion": fecha_hoy,
        "hora_atencion": hora_hoy,
        "patient": patient_info
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c34_data = kh_database.fetch_consentimiento_34_01(pt_num, mrnum=effective_slot)
    if not effective_slot and isinstance(c34_data, dict) and "error" not in c34_data and c34_data.get("mrnum"):
        effective_slot = int(c34_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            models.HistoricoNotaClinica.codigo_formato.ilike("%34%")
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_num}"),
                models.FirmaDocumentoClinico.codigo_formato.ilike("%34%"),
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 34_01 for PDF: {e_hist}")
    finally:
        db.close()

    if c34_data and (not isinstance(c34_data, dict) or "error" not in c34_data):
        for k, v in c34_data.items():
            if v:
                pt_data[k] = v
        if c34_data.get("medico_tratante") or c34_data.get("nombre_medico_mi"):
            pt_data["medico_tratante"] = c34_data.get("medico_tratante") or c34_data.get("nombre_medico_mi")
        if c34_data.get("created_on"):
            parts = c34_data["created_on"].split(" ")
            if len(parts) >= 1:
                pt_data["fecha_atencion"] = parts[0]
            if len(parts) >= 2:
                pt_data["hora_atencion"] = parts[1]

    is_doc_signed = bool(c34_data.get("signed_by") or c34_data.get("signed_on"))

    import pdf_engine_34_01
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_num, "HE-DIRMED-CONSUL-PLT-34", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c34_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c34_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_34_01_{pt_num}_{effective_slot}.pdf")
    pdf_engine_34_01.generate_consentimiento_34_01(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_num,
                codigo_formato="HE-DIRMED-CONSUL-PLT-34/01",
                tipo_documento="Consentimiento Informado para Estudio de Mesa Inclinada (Tilt Test)",
                pdf_path=pdf_path,
                pdf_filename=f"CI_34_01_{pt_num}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 34/01 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"CI_34_01_{pt_num}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="CI_34_01_{pt_num}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 34/01")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-34-01")
def save_consentimiento_34_01_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_34_01", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-34",
            tipo_documento="Consentimiento Informado para Estudio de Mesa Inclinada (Tilt Test)",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=0,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("nombre_medico_mi") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 34/01: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-34",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 34/01: {e}")
        db.rollback()

    return res


# ─────────────────────────────────────────────────────────────
# ENDPOINTS FORMATO 12: CONSENTIMIENTO GINECO Y OBSTETRICIA (HOSP/URG)
# ─────────────────────────────────────────────────────────────

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-12")
def get_consentimiento_12(pt_num: str, db: Session = Depends(get_db)):
    data = kh_database.fetch_consentimiento_12(pt_num)
    if isinstance(data, dict) and "error" not in data:
        last_hist = db.query(models.HistoricoNotaClinica).filter(
            models.HistoricoNotaClinica.pt_num == str(pt_num),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-12"
        ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k not in data or not data[k]:
                        data[k] = v
            except Exception as e:
                print(f"Error parsing historic consent 12: {e}")
    return data


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-12")
def get_pdf_consentimiento_12(pt_num: str, mrnum: Optional[int] = None):
    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_num)
    if "error" in dashboard_data:
        raise HTTPException(status_code=404, detail=dashboard_data["error"])

    patient_info = dashboard_data.get("patient", {})
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    hora_hoy = datetime.datetime.now().strftime("%H:%M")

    pt_data = {
        "paciente_nombre": patient_info.get("name", ""),
        "nombre": patient_info.get("name", ""),
        "expediente": patient_info.get("mrn", f"PT-{pt_num}"),
        "pt_num": str(pt_num),
        "fecha_nacimiento": patient_info.get("dob", ""),
        "edad": patient_info.get("age", ""),
        "sexo": patient_info.get("sex", "F"),
        "medico_tratante": patient_info.get("attending_doctor") or "",
        "cedula": patient_info.get("cedula") or "",
        "fecha_ingreso": patient_info.get("fecha_ingreso", fecha_hoy),
        "hora_ingreso": patient_info.get("hora_ingreso", hora_hoy),
        "fecha_atencion": fecha_hoy,
        "hora_atencion": hora_hoy,
        "diagnostico": patient_info.get("diagnostico") or "REVISIÓN GINECOLÓGICA Y OBSTÉTRICA",
        "servicio": "URGENCIAS",
        "beneficios": "Evaluación integral de la condición materno-fetal, resolución adecuada del evento obstétrico.",
        "alternativas": "Manejo médico expectante, tratamiento farmacológico alternativo o diferimiento según evolución clínica.",
        "patient": patient_info
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c12_data = kh_database.fetch_consentimiento_12(pt_num, mrnum=effective_slot)
    if not effective_slot and isinstance(c12_data, dict) and "error" not in c12_data and c12_data.get("mrnum"):
        effective_slot = int(c12_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-12"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_num}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-12",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 12 for PDF: {e_hist}")
    finally:
        db.close()

    if c12_data and (not isinstance(c12_data, dict) or "error" not in c12_data):
        for k, v in c12_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v

    is_doc_signed = bool(c12_data.get("signed_by") or c12_data.get("firmado"))

    import pdf_engine_12
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_num, "HE-DIRMED-CONSUL-PLT-12", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c12_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c12_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_12_{pt_num}_{effective_slot}.pdf")
    pdf_engine_12.generate_consentimiento_12(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_num,
                codigo_formato="HE-DIRMED-CONSUL-PLT-12",
                tipo_documento="Carta de Consentimiento Informado para Revisión Ginecológica y Obstétrica Hospitalización / Urgencias",
                pdf_path=pdf_path,
                pdf_filename=f"CI_12_{pt_num}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 12 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"CI_12_{pt_num}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="CI_12_{pt_num}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 12")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-12")
def save_consentimiento_12_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_12", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-12",
            tipo_documento="Carta de Consentimiento Informado para Revisión Ginecológica y Obstétrica Hospitalización / Urgencias",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=0,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("n_medico") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 12: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-12",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 12: {e}")
        db.rollback()

    return res


# ─────────────────────────────────────────────────────────────
# FORMATO 04: CONSENTIMIENTO INFORMADO PARA COLOCACIÓN DE CATÉTER VENOSO CENTRAL
# ─────────────────────────────────────────────────────────────

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-04")
def get_consentimiento_04(pt_num: str, db: Session = Depends(get_db)):
    data = kh_database.fetch_consentimiento_04(pt_num)
    if isinstance(data, dict) and "error" not in data:
        last_hist = db.query(models.HistoricoNotaClinica).filter(
            models.HistoricoNotaClinica.pt_num == str(pt_num),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-04"
        ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k not in data or not data[k]:
                        data[k] = v
            except Exception as e:
                print(f"Error parsing historic consent 04: {e}")
    return data


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-04")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-04")
def get_pdf_consentimiento_04(pt_num: str, mrnum: Optional[int] = None):
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if "error" in dashboard_data:
        raise HTTPException(status_code=404, detail=dashboard_data["error"])

    patient_info = dashboard_data.get("patient", {})
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    hora_hoy = datetime.datetime.now().strftime("%H:%M")

    pt_data = {
        "paciente_nombre": patient_info.get("name", ""),
        "nombre": patient_info.get("name", ""),
        "expediente": patient_info.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": patient_info.get("dob", ""),
        "edad": patient_info.get("age", ""),
        "sexo": patient_info.get("sex", "M"),
        "medico_tratante": patient_info.get("attending_doctor") or "",
        "cedula": patient_info.get("cedula") or "",
        "fecha_ingreso": patient_info.get("fecha_ingreso", fecha_hoy),
        "hora_ingreso": patient_info.get("hora_ingreso", hora_hoy),
        "fecha_atencion": fecha_hoy,
        "hora_atencion": hora_hoy,
        "paciente_capaz": True,
        "pariente": "",
        "testigo1": "",
        "patient": patient_info
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c04_data = kh_database.fetch_consentimiento_04(pt_query, mrnum=effective_slot)
    if not effective_slot and isinstance(c04_data, dict) and "error" not in c04_data and c04_data.get("mrnum"):
        effective_slot = int(c04_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) |
            (models.HistoricoNotaClinica.pt_num == str(pt_num)),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-04"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_query)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_query}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-04",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 04 for PDF: {e_hist}")
    finally:
        db.close()

    if c04_data and (not isinstance(c04_data, dict) or "error" not in c04_data):
        for k, v in c04_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v

    is_doc_signed = bool(c04_data.get("signed_by") or c04_data.get("firmado"))

    import pdf_engine_04
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-04", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("sello_testigo2"):
            pt_data["sello_testigo2"] = sig_info.get("sello_testigo2")
            pt_data["firma_testigo2_biometrica"] = True
            if sig_info.get("firmante_testigo2"):
                pt_data["testigo2"] = sig_info.get("firmante_testigo2")
            if sig_info.get("parentesco_testigo2"):
                pt_data["parentesco_testigo2"] = sig_info.get("parentesco_testigo2")
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c04_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c04_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_04_{pt_query}_{effective_slot}.pdf")
    pdf_engine_04.generate_consentimiento_04(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-04",
                tipo_documento="Carta de Consentimiento Informado para Colocación de Catéter Venoso Central",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_04_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 04 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_04_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_04_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 04")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-04")
def save_consentimiento_04_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_04", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-04",
            tipo_documento="Carta de Consentimiento Informado para Colocación de Catéter Venoso Central",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=0,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("n_medico") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 04: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-04",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 04: {e}")
        db.rollback()

    return res


# =========================================================================
# ENDPOINTS FORMATO 15: CONSENTIMIENTO INFORMADO PARA CESÁREA / DISENTIMIENTO
# =========================================================================

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-15")
def get_consentimiento_15(pt_num: str, mrnum: int = None, db: Session = Depends(get_db)):
    """
    Obtiene los datos del Formato 15 (Cesárea / Disentimiento) desde SQL Server e histórico PostgreSQL.
    """
    c15 = kh_database.fetch_consentimiento_15(pt_num, mrnum=mrnum)
    if not c15 or "error" in c15:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-15"
        )
        if mrnum:
            hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if hist and hist.contenido_soap_json:
            try:
                data = json.loads(hist.contenido_soap_json)
                data["source"] = "historico_local"
                data["firmado"] = False
                data["no_autorizo"] = bool(data.get("no_autorizo") or data.get("tipo") == "no_autorizo")
                return data
            except Exception:
                pass
        return {"pt_num": pt_num, "medico_tratante": "", "firmado": False, "no_autorizo": False}

    # Mezclar con el snapshot JSON de auditoría correspondiente
    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-15"
    )
    if mrnum:
        last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
    else:
        last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k in ("no_autorizo", "tipo", "motivo_no_acepto", "diagnostico", "pariente", "paciente_capaz", "testigo1", "testigo2", "identificacion_testigo", "parentesco_testigo", "domicilio_testigo", "procedimiento_consiste", "beneficios", "alternativas"):
                    c15[k] = v
                elif k not in c15 or not c15[k]:
                    c15[k] = v
            c15["no_autorizo"] = bool(extra_data.get("no_autorizo") or extra_data.get("tipo") == "no_autorizo")
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 15: {e_parse}")

    return c15


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-15")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-15")
def get_pdf_consentimiento_15(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 15 (Cesárea / Disentimiento).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": ""
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "diagnostico": pt.get("diagnostico", ""),
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "paciente_capaz": True,
        "pariente": "",
        "testigo1": "",
        "testigo2": "",
        "no_autorizo": False,
        "motivo_no_acepto": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c15_data = kh_database.fetch_consentimiento_15(pt_query, mrnum=effective_slot) or {}
    if not effective_slot and isinstance(c15_data, dict) and "error" not in c15_data and c15_data.get("mrnum"):
        effective_slot = int(c15_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) |
            (models.HistoricoNotaClinica.pt_num == str(pt_num)),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-15"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_query)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_query}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-15",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
                pt_data["no_autorizo"] = bool(hist_data.get("no_autorizo") or hist_data.get("tipo") == "no_autorizo")
            except Exception as e_hist:
                print(f"Error parsing historic consent 15 for PDF: {e_hist}")
    finally:
        db.close()

    if c15_data and isinstance(c15_data, dict) and "error" not in c15_data:
        for k, v in c15_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v

    is_doc_signed = bool(c15_data.get("signed_by") or c15_data.get("firmado"))

    import pdf_engine_15
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-15", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c15_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c15_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_15_{pt_query}_{effective_slot}.pdf")
    pdf_engine_15.generate_consentimiento_15(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-15",
                tipo_documento="Carta de Consentimiento Informado para Cesárea / Disentimiento",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_15_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 15 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_15_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_15_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 15")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-15")
def save_consentimiento_15_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_15", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-15",
            tipo_documento="Carta de Consentimiento Informado para Cesárea / Disentimiento",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=target_mr,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("n_medico") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 15: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-15",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 15: {e}")
        db.rollback()

    return res


# =========================================================================
# ENDPOINTS FORMATO 02: CONSENTIMIENTO QUIRÚRGICO / DISENTIMIENTO
# =========================================================================

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-02")
def get_consentimiento_02(pt_num: str, mrnum: int = None, db: Session = Depends(get_db)):
    """
    Obtiene los datos del Formato 02 (Tratamiento Quirúrgico / Disentimiento) desde SQL Server e histórico PostgreSQL.
    """
    c02 = kh_database.fetch_consentimiento_02(pt_num, mrnum=mrnum)
    if not c02 or "error" in c02:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-02"
        )
        if mrnum:
            hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if hist and hist.contenido_soap_json:
            try:
                data = json.loads(hist.contenido_soap_json)
                data["source"] = "historico_local"
                data["firmado"] = False
                data["no_autorizo"] = bool(data.get("no_autorizo") or data.get("tipo") == "no_autorizo" or data.get("motivo_de_no_autorizacion"))
                return data
            except Exception:
                pass
        return {"pt_num": pt_num, "medico_tratante": "", "firmado": False, "no_autorizo": False}

    # Mezclar con el snapshot JSON de auditoría correspondiente
    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-02"
    )
    if mrnum:
        last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
    else:
        last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k in ("no_autorizo", "tipo", "motivo_de_no_autorizacion", "motivo_no_acepto", "diagnostico", "pariente", "paciente_capaz", "testigo1", "testigo2", "domicilio_testigo1", "identificacion_testigo1", "parentesco_testigo1", "proced_para_confirmar_diagnost", "beneficio_de_dicho_procedimiento", "tratamientos_medicos", "tratamientos_quirurgicos", "tratamientos_endoscopicos", "tratamientos_de_rehabilitacion", "anestesia", "tipo_de_anestesia", "principales_riesgos", "alternativas"):
                    c02[k] = v
                elif k not in c02 or not c02[k]:
                    c02[k] = v
            c02["no_autorizo"] = bool(extra_data.get("no_autorizo") or extra_data.get("tipo") == "no_autorizo" or extra_data.get("motivo_de_no_autorizacion"))
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 02: {e_parse}")

    return c02


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-02")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-02")
def get_pdf_consentimiento_02(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 02 (Tratamiento Quirúrgico / Disentimiento).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": ""
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "diagnostico": pt.get("diagnostico", ""),
        "proced_para_confirmar_diagnost": "Estudios preoperatorios, valoración de riesgo quirúrgico y protocolo anestésico",
        "beneficio_de_dicho_procedimiento": "Resolución terapéutica de la patología de base, preservación funcional y mejora en la calidad de vida",
        "tratamientos_medicos": "Manejo farmacológico perioperatorio, analgesia y antibioticoterapia profiláctica",
        "tratamientos_quirurgicos": "Intervención quirúrgica protocolizada bajo técnica aséptica",
        "tratamientos_endoscopicos": "No requeridos en este tiempo quirúrgico / según hallazgos transoperatorios",
        "tratamientos_de_rehabilitacion": "Deambulación temprana asistida y cuidados postoperatorios de herida quirúrgica",
        "alternativas": "Tratamiento médico expectante o diferimiento según evolución clínica",
        "anestesia": "SI",
        "tipo_de_anestesia": "General balanceada / Bloqueo neuroaxial según valoración anestesiológica",
        "principales_riesgos": "Hemorragia, infección de sitio quirúrgico, lesión de órganos o estructuras vecinas, reacciones adversas a medicamentos o anestésicos, eventos tromboembólicos",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "paciente_capaz": True,
        "pariente": "",
        "testigo1": "",
        "testigo2": "",
        "no_autorizo": False,
        "motivo_de_no_autorizacion": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    # Cargar datos desde SQL Server
    c02_data = kh_database.fetch_consentimiento_02(pt_query, mrnum=effective_slot) or {}
    if c02_data and isinstance(c02_data, dict) and "error" not in c02_data:
        if not effective_slot and c02_data.get("mrnum"):
            effective_slot = int(c02_data["mrnum"])
        for k, v in c02_data.items():
            if v:
                pt_data[k] = v

    # Mezclar con Snapshot de Auditoría
    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) |
            (models.HistoricoNotaClinica.pt_num == str(pt_num)),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-02"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_query)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_query}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-02",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    if v is not None and v != "":
                        pt_data[k] = v
                pt_data["no_autorizo"] = bool(hist_data.get("no_autorizo") or hist_data.get("tipo") == "no_autorizo" or hist_data.get("motivo_de_no_autorizacion"))
            except Exception as e_hist:
                print(f"Error parsing historic consent 02 for PDF: {e_hist}")
    finally:
        db.close()

    is_doc_signed = bool(c02_data.get("signed_by") or c02_data.get("firmado"))

    import pdf_engine_02
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-02", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)

        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c02_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c02_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_02_{pt_query}_{effective_slot}.pdf")
    pdf_engine_02.generate_consentimiento_02(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-02",
                tipo_documento="Carta de Consentimiento Informado para Tratamiento Quirúrgico / Disentimiento",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_02_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 02 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_02_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_02_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 02")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-02")
def save_consentimiento_02_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_02", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-02",
            tipo_documento="Carta de Consentimiento Informado para Tratamiento Quirúrgico / Disentimiento",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=target_mr,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("n_medico") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 02: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-02",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 02: {e}")
        db.rollback()

    return res


# =========================================================================
# ENDPOINTS FORMATO 07: CONSENTIMIENTO INFORMADO PARA PROCEDIMIENTOS QUIRÚRGICOS
# =========================================================================

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-07")
@app.get("/ehr/paciente/{pt_num}/consentimiento-07")
def get_consentimiento_07(pt_num: str, mrnum: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene los datos estructurados del Consentimiento 07 (Procedimientos Quirúrgicos)."""
    c07 = kh_database.fetch_consentimiento_07(pt_num, mrnum=mrnum)
    if not c07 or "error" in c07:
        c07 = {
            "mrnum": None,
            "pt_num": str(pt_num),
            "medico_tratante": "",
            "n_medico": "",
            "expediente": f"PT-{pt_num}",
            "procedimiento_quirurgico": "INTERVENCIÓN QUIRÚRGICA PROGRAMADA",
            "descripcion_procedimiento": "procedimiento quirúrgico bajo técnica aséptica protocolizada y monitoreo continuo",
            "riesgos_inherentes": "sangrado transoperatorio, infección de herida quirúrgica, dehiscencia, reacciones medicamentosas",
            "beneficios": "resolución del cuadro clínico de base, preservación funcional y mejora de salud",
            "alternativas": "tratamiento médico conservador o diferimiento según valoración",
            "paciente_capaz": True,
            "representante_legal": "",
            "parentesco": "",
            "testigo1": "",
            "testigo2": "",
            "created_by": "",
            "created_on": "",
            "signed_by": "",
            "signed_on": "",
            "firmado": False,
            "mr_st": "RG"
        }

    target_mr = mrnum or c07.get("mrnum")
    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-07"
    )
    if target_mr:
        last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == target_mr).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
    else:
        last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k in ("procedimiento_quirurgico", "descripcion_procedimiento", "riesgos_inherentes", "beneficios", "alternativas", "paciente_capaz", "representante_legal", "parentesco", "testigo1", "testigo2"):
                    c07[k] = v
                elif k not in c07 or not c07[k]:
                    c07[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 07: {e_parse}")

    return c07


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-07")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-07")
def get_pdf_consentimiento_07(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 07 (Consentimiento Informado para Procedimientos Quirúrgicos).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "INTERVENCIÓN QUIRÚRGICA PROGRAMADA"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "procedimiento_quirurgico": "INTERVENCIÓN QUIRÚRGICA PROGRAMADA",
        "descripcion_procedimiento": "procedimiento quirúrgico bajo técnica aséptica protocolizada y monitoreo continuo",
        "riesgos_inherentes": "sangrado transoperatorio, infección de herida quirúrgica, dehiscencia, reacciones medicamentosas",
        "beneficios": "resolución del cuadro clínico de base, preservación funcional y mejora de salud",
        "alternativas": "tratamiento médico conservador o diferimiento según valoración",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "paciente_capaz": True,
        "representante_legal": "",
        "parentesco": "",
        "testigo1": "",
        "testigo2": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    # Cargar datos desde SQL Server
    c07_data = kh_database.fetch_consentimiento_07(pt_query, mrnum=effective_slot) or {}
    if c07_data and isinstance(c07_data, dict) and "error" not in c07_data:
        if not effective_slot and c07_data.get("mrnum"):
            effective_slot = int(c07_data["mrnum"])
        for k, v in c07_data.items():
            if v:
                pt_data[k] = v

    # Mezclar con Snapshot de Auditoría
    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) |
            (models.HistoricoNotaClinica.pt_num == str(pt_num)),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-07"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_query)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_query}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-07",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    if v is not None and v != "":
                        pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 07 for PDF: {e_hist}")
    finally:
        db.close()

    is_doc_signed = bool(c07_data.get("signed_by") or c07_data.get("firmado"))

    import pdf_engine_07
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-07", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if pt_data.get("representante_legal"):
            pt_data["yo_autorizo"] = pt_data.get("representante_legal")

        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c07_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c07_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_07_{pt_query}_{effective_slot}.pdf")
    pdf_engine_07.generate_consentimiento_07(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-07",
                tipo_documento="Consentimiento Informado para Procedimientos Quirúrgicos",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_07_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 07 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_07_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_07_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 07")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-07")
@app.post("/ehr/paciente/{pt_num}/consentimiento-07")
def save_consentimiento_07_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_07", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-07",
            tipo_documento="Consentimiento Informado para Procedimientos Quirúrgicos",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=target_mr,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("n_medico") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 07: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-07",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 07: {e}")
        db.rollback()

    return res


@app.get("/api/ehr/paciente/{pt_num}/consentimiento-08")
def get_consentimiento_08(pt_num: str, mrnum: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene los datos estructurados del Consentimiento 08 (Admisión Continua y Procedimientos Diagnósticos)."""
    c08 = kh_database.fetch_consentimiento_08(pt_num, mrnum=mrnum)
    if not c08 or "error" in c08:
        c08 = {
            "mrnum": None,
            "pt_num": str(pt_num),
            "medico_tratante": "",
            "n_medico": "",
            "expediente": f"PT-{pt_num}",
            "diagnostico": "VALORACIÓN Y TRATAMIENTO EN ADMISIÓN CONTINUA",
            "procedimientos": "Instalación de accesos vasculares venosos/arteriales, toma de muestras de laboratorio, monitorización hemodinámica continua, administración de soluciones parenterales y farmacoterapia requerida según evolución clínica.",
            "riesgos_inherentes_a_procedimien": "Medios",
            "riesgos": "Medios",
            "prob_proced_y_alts": "Estudios complementarios de laboratorio y gabinete (Rayos X, Ultrasonografía POCUS, TAC), observación clínica estrecha, interconsultas especializadas y tratamiento conservador.",
            "alternativas": "Estudios complementarios de laboratorio y gabinete (Rayos X, Ultrasonografía POCUS, TAC), observación clínica estrecha, interconsultas especializadas y tratamiento conservador.",
            "beneficios": "Estabilización de signos vitales, mitigación de síntomas agudos, confirmación diagnóstica oportuna, restitución hemodinámica y prevención de complicaciones graves.",
            "testigo1": "",
            "testigo_1": "",
            "testigo2": "",
            "testigo_2": "",
            "created_by": "",
            "created_on": "",
            "signed_by": "",
            "signed_on": "",
            "firmado": False,
            "mr_st": "RG"
        }

    target_mr = mrnum or c08.get("mrnum")
    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-08"
    )
    if target_mr:
        last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == target_mr).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
    else:
        last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k in ("diagnostico", "procedimientos", "riesgos_inherentes_a_procedimien", "riesgos", "prob_proced_y_alts", "alternativas", "beneficios", "testigo1", "testigo_1", "testigo2", "testigo_2", "pariente", "yo_autorizo", "parentesco", "parentesco_paciente", "paciente_capaz"):
                    c08[k] = v
                elif k not in c08 or not c08[k]:
                    c08[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 08: {e_parse}")

    return c08


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-08")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-08")
def get_pdf_consentimiento_08(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 08 (Admisión Continua y Procedimientos Diagnósticos).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "VALORACIÓN Y TRATAMIENTO EN ADMISIÓN CONTINUA"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "diagnostico": pt.get("diagnostico", "VALORACIÓN Y TRATAMIENTO EN ADMISIÓN CONTINUA"),
        "procedimientos": "Instalación de accesos vasculares venosos/arteriales, toma de muestras de laboratorio, monitorización hemodinámica continua, administración de soluciones parenterales y farmacoterapia requerida según evolución clínica.",
        "riesgos_inherentes_a_procedimien": "Medios",
        "riesgos": "Medios",
        "prob_proced_y_alts": "Estudios complementarios de laboratorio y gabinete (Rayos X, Ultrasonografía POCUS, TAC), observación clínica estrecha, interconsultas especializadas y tratamiento conservador.",
        "alternativas": "Estudios complementarios de laboratorio y gabinete (Rayos X, Ultrasonografía POCUS, TAC), observación clínica estrecha, interconsultas especializadas y tratamiento conservador.",
        "beneficios": "Estabilización de signos vitales, mitigación de síntomas agudos, confirmación diagnóstica oportuna, restitución hemodinámica y prevención de complicaciones graves.",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "paciente_capaz": True,
        "pariente": "",
        "yo_autorizo": pt.get("name", ""),
        "parentesco": "Paciente",
        "testigo1": "",
        "testigo_1": "",
        "testigo2": "",
        "testigo_2": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    # Cargar datos desde SQL Server
    c08_data = kh_database.fetch_consentimiento_08(pt_query, mrnum=effective_slot) or {}
    if c08_data and isinstance(c08_data, dict) and "error" not in c08_data:
        if not effective_slot and c08_data.get("mrnum"):
            effective_slot = int(c08_data["mrnum"])
        for k, v in c08_data.items():
            if v:
                pt_data[k] = v

    # Mezclar con Snapshot de Auditoría
    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) |
            (models.HistoricoNotaClinica.pt_num == str(pt_num)),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-08"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_query)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_query}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-08",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    if v is not None and v != "":
                        pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 08 for PDF: {e_hist}")
    finally:
        db.close()

    is_doc_signed = bool(c08_data.get("signed_by") or c08_data.get("firmado"))

    import pdf_engine_08
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-08", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if pt_data.get("pariente"):
            pt_data["yo_autorizo"] = pt_data.get("pariente")

        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c08_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c08_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_08_{pt_query}_{effective_slot}.pdf")
    pdf_engine_08.generate_consentimiento_08(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-08",
                tipo_documento="Consentimiento Informado para Tratamiento, Procedimiento(s) de Diagnóstico en Admisión Continua",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_08_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 08 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_08_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_08_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 08")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-08")
def save_consentimiento_08_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_08", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-CONSUL-PLT-08",
            tipo_documento="Consentimiento Informado para Tratamiento, Procedimiento(s) de Diagnóstico en Admisión Continua",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=target_mr,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("n_medico") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 08: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-08",
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 08: {e}")
        db.rollback()

    return res


# =========================================================================
# ENDPOINTS FORMATO 43: ORDEN DE INTUBACIÓN ENDOTRAQUEAL / SOPORTE VENTILATORIO
# =========================================================================

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-43")
def get_consentimiento_43(pt_num: str, mrnum: int = None, db: Session = Depends(get_db)):
    """
    Obtiene los datos del Formato 43 (Orden de Intubación Endotraqueal) desde SQL Server e histórico PostgreSQL.
    """
    c43 = kh_database.fetch_consentimiento_43(pt_num, mrnum=mrnum)
    if not c43 or "error" in c43:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-43") | (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-43") | (models.HistoricoNotaClinica.codigo_formato == "43")
        )
        if mrnum:
            hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if hist and hist.contenido_soap_json:
            try:
                data = json.loads(hist.contenido_soap_json)
                data["source"] = "historico_local"
                data["firmado"] = False
                return data
            except Exception:
                pass
        return {"pt_num": pt_num, "medico_tratante": "", "firmado": False}

    # Mezclar con el snapshot JSON de auditoría correspondiente
    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-43") | (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-43") | (models.HistoricoNotaClinica.codigo_formato == "43")
    )
    if mrnum:
        last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
    else:
        last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k in ("diagnostico", "diagnosticos", "servicio", "beneficios", "riesgos", "principales_riesgos", "alternativas", "declarante", "paciente_o_representante", "representante_legal", "parentesco", "parentesco_declarante", "domicilio_declarante", "identificacion_declarante", "testigo1", "testigo_1", "testigo2", "testigo_2", "domicilio_testigo1", "identificacion_testigo1", "domicilio_testigo2", "identificacion_testigo2", "paciente_capaz"):
                    c43[k] = v
                elif k not in c43 or not c43[k]:
                    c43[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 43: {e_parse}")

    return c43


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-43")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-43")
def get_pdf_consentimiento_43(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 43 (Orden de Intubación Endotraqueal / Soporte Ventilatorio).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "INSUFICIENCIA RESPIRATORIA AGUDA / COMPROMISO DE VÍA AÉREA",
            "cama": "URGENCIAS / TERAPIA INTENSIVA"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "diagnostico": pt.get("diagnostico", "INSUFICIENCIA RESPIRATORIA AGUDA / COMPROMISO DE VÍA AÉREA"),
        "servicio": pt.get("cama", "URGENCIAS / TERAPIA INTENSIVA"),
        "beneficios": "Aseguramiento de la vía aérea permeable, soporte ventilatorio mecánico invasivo, optimización de la oxigenación tisular y prevención del paro respiratorio o colapso hemodinámico.",
        "riesgos": "Traumatismo de la vía aérea (laringe, cuerdas vocales, tráquea), broncoaspiración, intubación esofágica o selectiva, broncoespasmo, arritmias, hipotensión, neumotórax o necesidad de ventilación mecánica prolongada.",
        "alternativas": "Oxigenoterapia de alto flujo, ventilación mecánica no invasiva (según indicación y estabilidad clínica) o manejo médico conservador.",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "declarante": pt.get("name", ""),
        "paciente_capaz": True,
        "parentesco": "PACIENTE",
        "testigo1": "",
        "testigo2": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c43_data = kh_database.fetch_consentimiento_43(pt_query, mrnum=effective_slot) or {}
    if not effective_slot and isinstance(c43_data, dict) and "error" not in c43_data and c43_data.get("mrnum"):
        effective_slot = int(c43_data["mrnum"])

    # Cargar datos desde HistoricoNotaClinica si existe
    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_query}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-43") | (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-43") | (models.HistoricoNotaClinica.codigo_formato == "43")
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                models.FirmaDocumentoClinico.pt_num == str(pt_query),
                (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-SINPRO-PLT-43") | (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-43") | (models.FirmaDocumentoClinico.codigo_formato == "43"),
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 43 for PDF: {e_hist}")
    finally:
        db.close()

    if c43_data and isinstance(c43_data, dict) and "error" not in c43_data:
        for k, v in c43_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v

    is_doc_signed = bool(c43_data.get("signed_by") or c43_data.get("firmado"))

    import pdf_engine_43
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-SINPRO-PLT-43", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c43_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c43_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_43_{pt_query}_{effective_slot}.pdf")
    pdf_engine_43.generate_consentimiento_43(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-SINPRO-PLT-43",
                tipo_documento="Orden de Intubación Endotraqueal / Soporte Ventilatorio",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_43_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 43 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_43_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_43_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 43")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-43")
def save_consentimiento_43_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_43", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Guardar Snapshot Inmutable en HistoricoNotaClinica (NOM-024)
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            codigo_formato="HE-DIRMED-SINPRO-PLT-43",
            tipo_documento="Orden de Intubación Endotraqueal / Soporte Ventilatorio",
            pt_num=str(pt_num),
            expediente=f"PT-{pt_num}",
            evolution_slot=target_mr,
            nombre_medico=str(request_data.get("medico_tratante") or request_data.get("n_medico") or ""),
            cedula_profesional=str(request_data.get("cedula") or request_data.get("cedula_profesional") or ""),
            contenido_soap_json=json.dumps(request_data, default=str),
            accion="GUARDADO",
            ip_origen=client_ip
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 43: {e}")
        db.rollback()

    # 2. Soft-Revocation de firmas activas en PostgreSQL (NOM-024)
    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-SINPRO-PLT-43") | (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-43") | (models.FirmaDocumentoClinico.codigo_formato == "43"),
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 43: {e}")
        db.rollback()

    return res


# =========================================================================
# ENDPOINTS FORMATO 11: CONSENTIMIENTO DE NO REANIMACIÓN (VOLUNTAD ANTICIPADA)
# =========================================================================

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-11")
@app.get("/ehr/paciente/{pt_num}/consentimiento-11")
def get_consentimiento_11(pt_num: str, mrnum: int = None, db: Session = Depends(get_db)):
    """
    Obtiene los datos del Formato 11 (No Reanimación) desde SQL Server e histórico local.
    """
    c11 = kh_database.fetch_consentimiento_11(pt_num, mrnum=mrnum)
    if not c11 or "error" in c11:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-11") | (models.HistoricoNotaClinica.codigo_formato == "11")
        )
        if mrnum:
            hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if hist and hist.contenido_soap_json:
            try:
                data = json.loads(hist.contenido_soap_json)
                data["source"] = "historico_local"
                data["firmado"] = False
                return data
            except Exception:
                pass
        return {"pt_num": pt_num, "medico_tratante": "", "firmado": False}

    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-11") | (models.HistoricoNotaClinica.codigo_formato == "11")
    )
    last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first() if mrnum else query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k not in c11 or not c11[k]:
                    c11[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 11: {e_parse}")

    return c11


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-11")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-11")
def get_pdf_consentimiento_11(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 11 (Consentimiento de No Reanimación / Voluntad Anticipada).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "ENFERMEDAD EN ETAPA AVANZADA / PRONÓSTICO GRAVE Y LIMITADO",
            "cama": "URGENCIAS / MEDICINA INTERNA"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "diagnostico": pt.get("diagnostico", "ENFERMEDAD EN ETAPA AVANZADA / PRONÓSTICO GRAVE Y LIMITADO"),
        "servicio": pt.get("cama", "URGENCIAS / MEDICINA INTERNA"),
        "beneficios_y_riesgos_de_nr": "Evitar encarnizamiento terapéutico y maniobras invasivas desproporcionadas en fase terminal, garantizando confort y dignidad.",
        "riesgos_de_no_aplicar": "Cese irreversible de las funciones cardiorrespiratorias y sobreveniencia de la muerte natural sin soporte artificial.",
        "alternativa_nr": "Manejo médico conservador integral, analgesia multimodal, sedación paliativa y medidas de confort bioético.",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "declarante": pt.get("name", ""),
        "paciente_capaz": True,
        "parentesco": "El Paciente",
        "identificacion": "INE / IDENTIFICACIÓN OFICIAL",
        "testigo_1": "",
        "testigo_2": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c11_data = kh_database.fetch_consentimiento_11(pt_query, mrnum=effective_slot) or {}
    if not effective_slot and isinstance(c11_data, dict) and "error" not in c11_data and c11_data.get("mrnum"):
        effective_slot = int(c11_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_query}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-11") | (models.HistoricoNotaClinica.codigo_formato == "11")
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                models.FirmaDocumentoClinico.pt_num == str(pt_query),
                (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-11") | (models.FirmaDocumentoClinico.codigo_formato == "11"),
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 11 for PDF: {e_hist}")
    finally:
        db.close()

    if c11_data and isinstance(c11_data, dict) and "error" not in c11_data:
        for k, v in c11_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v

    is_doc_signed = bool(c11_data.get("signed_by") or c11_data.get("firmado"))

    import pdf_engine_11
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-11", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c11_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c11_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_11_{pt_query}_{effective_slot}.pdf")
    pdf_engine_11.generate_consentimiento_11(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-11",
                tipo_documento="Consentimiento de No Reanimación",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_11_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 11 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_11_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_11_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 11")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-11")
@app.post("/ehr/paciente/{pt_num}/consentimiento-11")
def save_consentimiento_11_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_11", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            pt_num=str(pt_num),
            codigo_formato="HE-DIRMED-CONSUL-PLT-11",
            evolution_slot=target_mr,
            fecha_registro=datetime.datetime.now(),
            ip_origen=client_ip,
            motivo="ACTUALIZACION_CONSENTIMIENTO_11",
            contenido_soap_json=json.dumps(request_data, ensure_ascii=False)
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 11: {e}")
        db.rollback()

    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-11") | (models.FirmaDocumentoClinico.codigo_formato == "11"),
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 11: {e}")
        db.rollback()

    return res


# =========================================================================
# ENDPOINTS FORMATO 19: CONSENTIMIENTO INFORMADO PARA HISTERECTOMÍA
# =========================================================================

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-19")
@app.get("/ehr/paciente/{pt_num}/consentimiento-19")
def get_consentimiento_19(pt_num: str, mrnum: int = None, db: Session = Depends(get_db)):
    """
    Obtiene los datos del Formato 19 (Histerectomía) desde SQL Server e histórico local.
    """
    c19 = kh_database.fetch_consentimiento_19(pt_num, mrnum=mrnum)
    if not c19 or "error" in c19:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-19") | (models.HistoricoNotaClinica.codigo_formato == "19")
        )
        if mrnum:
            hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if hist and hist.contenido_soap_json:
            try:
                data = json.loads(hist.contenido_soap_json)
                data["source"] = "historico_local"
                data["firmado"] = False
                return data
            except Exception:
                pass
        return {"pt_num": pt_num, "medico_tratante": "", "firmado": False}

    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-19") | (models.HistoricoNotaClinica.codigo_formato == "19")
    )
    last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first() if mrnum else query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k not in c19 or not c19[k]:
                    c19[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 19: {e_parse}")

    return c19


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-19")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-19")
def get_pdf_consentimiento_19(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 19 (Consentimiento Informado para Histerectomía).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "MIOMATOSIS UTERINA / HEMORRAGIA UTERINA ANORMAL",
            "cama": "GINECOLOGÍA Y OBSTETRICIA"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "diagnostico": pt.get("diagnostico", "MIOMATOSIS UTERINA / HEMORRAGIA UTERINA ANORMAL"),
        "servicio": pt.get("cama", "GINECOLOGÍA Y OBSTETRICIA"),
        "explicacion_de_proceso": "Extirpación quirúrgica total o subtotal del útero con técnica aséptica protocolizada.",
        "beneficios_de_procedimiento": "Resolución definitiva del sangrado uterino anormal, eliminación de dolor pélvico y prevención de complicaciones miomatosas.",
        "intervencion_complementaria": "Salpingooforectomía uni/bilateral o lisis de adherencias pélvicas según hallazgos.",
        "alternativas_terapeuticas": "Manejo farmacológico hormonal, colocación de dispositivo intrauterino liberador o miomectomía.",
        "motivo_de_no_autorizacion": "",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "declarante": pt.get("name", ""),
        "paciente_capaz": True,
        "parentesco": "La Paciente",
        "identificacion": "INE / CREDENCIAL OFICIAL",
        "testigo_1": "",
        "testigo_2": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c19_data = kh_database.fetch_consentimiento_19(pt_query, mrnum=effective_slot) or {}
    if not effective_slot and isinstance(c19_data, dict) and "error" not in c19_data and c19_data.get("mrnum"):
        effective_slot = int(c19_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_query}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-19") | (models.HistoricoNotaClinica.codigo_formato == "19")
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                models.FirmaDocumentoClinico.pt_num == str(pt_query),
                (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-19") | (models.FirmaDocumentoClinico.codigo_formato == "19"),
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 19 for PDF: {e_hist}")
    finally:
        db.close()

    if c19_data and isinstance(c19_data, dict) and "error" not in c19_data:
        for k, v in c19_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v

    is_doc_signed = bool(c19_data.get("signed_by") or c19_data.get("firmado"))

    import pdf_engine_19
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-19", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c19_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c19_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_19_{pt_query}_{effective_slot}.pdf")
    pdf_engine_19.generate_consentimiento_19(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-19",
                tipo_documento="Consentimiento Informado para Histerectomía",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_19_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 19 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_19_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_19_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 19")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-19")
@app.post("/ehr/paciente/{pt_num}/consentimiento-19")
def save_consentimiento_19_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_19", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            pt_num=str(pt_num),
            codigo_formato="HE-DIRMED-CONSUL-PLT-19",
            evolution_slot=target_mr,
            fecha_registro=datetime.datetime.now(),
            ip_origen=client_ip,
            motivo="ACTUALIZACION_CONSENTIMIENTO_19",
            contenido_soap_json=json.dumps(request_data, ensure_ascii=False)
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 19: {e}")
        db.rollback()

    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-19") | (models.FirmaDocumentoClinico.codigo_formato == "19"),
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 19: {e}")
        db.rollback()

    return res


# =========================================================================
# ENDPOINTS FORMATO 15: EGRESO VOLUNTARIO (HE-DIRMED-SINPRO-PLT-15)
# =========================================================================

@app.get("/api/ehr/paciente/{pt_num}/egreso-voluntario-15")
@app.get("/ehr/paciente/{pt_num}/egreso-voluntario-15")
@app.get("/api/ehr/paciente/{pt_num}/consentimiento-15-ev")
@app.get("/ehr/paciente/{pt_num}/consentimiento-15-ev")
def get_egreso_voluntario_15(pt_num: str, mrnum: int = None, db: Session = Depends(get_db)):
    """
    Obtiene los datos del Formato 15 (Egreso Voluntario) desde SQL Server e histórico local.
    """
    c15ev = kh_database.fetch_egreso_voluntario_15(pt_num, mrnum=mrnum)
    if not c15ev or "error" in c15ev:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-15") | (models.HistoricoNotaClinica.codigo_formato == "PLT-EV-15")
        )
        if mrnum:
            hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if hist and hist.contenido_soap_json:
            try:
                data = json.loads(hist.contenido_soap_json)
                data["source"] = "historico_local"
                data["firmado"] = False
                return data
            except Exception:
                pass
        return {"pt_num": pt_num, "medico_tratante": "", "firmado": False}

    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-15") | (models.HistoricoNotaClinica.codigo_formato == "PLT-EV-15")
    )
    last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first() if mrnum else query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k not in c15ev or not c15ev[k]:
                    c15ev[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for EV 15: {e_parse}")

    return c15ev


@app.get("/api/ehr/paciente/{pt_num}/pdf-egreso-voluntario-15")
@app.get("/ehr/paciente/{pt_num}/pdf-egreso-voluntario-15")
def get_pdf_egreso_voluntario_15(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 15 (Egreso Voluntario).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "ENFERMEDAD EN RESOLUCIÓN CON SOLICITUD DE EGRESO VOLUNTARIO",
            "cama": "HOSPITALIZACIÓN"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "diagnostico_ingreso": pt.get("diagnostico", "PATOLOGÍA EN TRATAMIENTO HOSPITALARIO"),
        "diagnostico_egreso": pt.get("diagnostico", "PATOLOGÍA EN TRATAMIENTO CON ALTA VOLUNTARIA"),
        "servicio": pt.get("cama", "HOSPITALIZACIÓN"),
        "medidas_recomendadas": "Apego puntual a la receta médica de egreso, reposo relativo en domicilio y acudir de inmediato a urgencias si presenta signos de alarma.",
        "factores_riesgo": "Deterioro clínico agudo, complicaciones no detectadas a tiempo por omisión de vigilancia intrahospitalaria.",
        "motivo_egreso": "Decisión personal para continuar tratamiento en domicilio.",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "declarante": pt.get("name", ""),
        "n_replegal": pt.get("name", ""),
        "paciente_capaz": True,
        "parentesco": "El Paciente",
        "identificacion": "INE / CREDENCIAL OFICIAL",
        "domicilio_declarante": "Ciudad de México",
        "testigo_1": "",
        "testigo_2": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c15_data = kh_database.fetch_egreso_voluntario_15(pt_query, mrnum=effective_slot) or {}
    if not effective_slot and isinstance(c15_data, dict) and "error" not in c15_data and c15_data.get("mrnum"):
        effective_slot = int(c15_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_query}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-15") | (models.HistoricoNotaClinica.codigo_formato == "PLT-EV-15")
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                models.FirmaDocumentoClinico.pt_num == str(pt_query),
                (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-SINPRO-PLT-15") | (models.FirmaDocumentoClinico.codigo_formato == "PLT-EV-15"),
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic EV 15 for PDF: {e_hist}")
    finally:
        db.close()

    if c15_data and isinstance(c15_data, dict) and "error" not in c15_data:
        for k, v in c15_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v

    is_doc_signed = bool(c15_data.get("signed_by") or c15_data.get("firmado"))

    import pdf_engine_15_ev
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-SINPRO-PLT-15", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c15_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c15_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"EV_15_{pt_query}_{effective_slot}.pdf")
    pdf_engine_15_ev.generate_egreso_voluntario_15(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-SINPRO-PLT-15",
                tipo_documento="Egreso Voluntario",
                pdf_path=pdf_path,
                pdf_filename=f"Egreso_Voluntario_15_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 15 EV para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Egreso_Voluntario_15_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Egreso_Voluntario_15_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 15 EV")


@app.post("/api/ehr/paciente/{pt_num}/egreso-voluntario-15")
@app.post("/ehr/paciente/{pt_num}/egreso-voluntario-15")
@app.post("/api/ehr/paciente/{pt_num}/consentimiento-15-ev")
@app.post("/ehr/paciente/{pt_num}/consentimiento-15-ev")
def save_egreso_voluntario_15_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_egreso_voluntario_15", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            pt_num=str(pt_num),
            codigo_formato="HE-DIRMED-SINPRO-PLT-15",
            evolution_slot=target_mr,
            fecha_registro=datetime.datetime.now(),
            ip_origen=client_ip,
            motivo="ACTUALIZACION_EGRESO_VOLUNTARIO_15",
            contenido_soap_json=json.dumps(request_data, ensure_ascii=False)
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Egreso Voluntario 15: {e}")
        db.rollback()

    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-SINPRO-PLT-15") | (models.FirmaDocumentoClinico.codigo_formato == "PLT-EV-15"),
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para EV 15: {e}")
        db.rollback()

    return res


# =========================================================================
# ENDPOINTS FORMATO 06: PROCEDIMIENTO ANESTÉSICO (MR_CI_APA)
# =========================================================================

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-06")
@app.get("/ehr/paciente/{pt_num}/consentimiento-06")
def get_consentimiento_06(pt_num: str, mrnum: int = None, db: Session = Depends(get_db)):
    """
    Obtiene los datos del Formato 06 (Procedimiento Anestésico) desde SQL Server e histórico local.
    """
    c06 = kh_database.fetch_consentimiento_06(pt_num, mrnum=mrnum)
    if not c06 or "error" in c06:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-06") | (models.HistoricoNotaClinica.codigo_formato == "06")
        )
        if mrnum:
            hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if hist and hist.contenido_soap_json:
            try:
                data = json.loads(hist.contenido_soap_json)
                data["source"] = "historico_local"
                data["firmado"] = False
                return data
            except Exception:
                pass
        return {"pt_num": pt_num, "medico_tratante": "", "firmado": False}

    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-06") | (models.HistoricoNotaClinica.codigo_formato == "06")
    )
    last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == mrnum).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first() if mrnum else query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k not in c06 or not c06[k]:
                    c06[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 06: {e_parse}")

    return c06


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-06")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-06")
def get_pdf_consentimiento_06(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 06 (Consentimiento para Procedimiento Anestésico).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "01/01/1985",
            "age": "39 años",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "PROGRAMACIÓN QUIRÚRGICA / VALORACIÓN ANESTESIOLÓGICA",
            "cama": "QUIRÓFANO"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_anestesiologo": pt.get("attending_doctor", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "cedula_especialidad": "",
        "diagnostico": pt.get("diagnostico", "PROGRAMACIÓN QUIRÚRGICA / VALORACIÓN ANESTESIOLÓGICA"),
        "cama": pt.get("cama", "QUIRÓFANO"),
        "servicio": pt.get("cama", "QUIRÓFANO"),
        "sexo": pt.get("gender") or "MASCULINO",
        "tipo_cirugia": "PROGRAMADA",
        "magnitud_cirugia": "MAYOR",
        "asa": "II",
        "tipo_anestesia": "ANESTESIA GENERAL BALANCEADA CON INTUBACIÓN OROTRAQUEAL / BLOQUEO NEUROAXIAL REGIONAL",
        "beneficios_anestesia": "Abolición del dolor y sensibilidad táctil, estabilidad hemodinámica y relajación muscular transoperatoria.",
        "alternativas_anestesia": "Anestesia neuroaxial pura, sedación consciente monitoreada o anestesia local infiltrativa según técnica.",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "declarante": pt.get("name", ""),
        "paciente_capaz": True,
        "parentesco": "El Paciente",
        "identificacion": "INE / CREDENCIAL OFICIAL",
        "testigo_1": "",
        "testigo_2": ""
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    c06_data = kh_database.fetch_consentimiento_06(pt_query, mrnum=effective_slot) or {}
    if not effective_slot and isinstance(c06_data, dict) and "error" not in c06_data and c06_data.get("mrnum"):
        effective_slot = int(c06_data["mrnum"])

    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_query}"),
            (models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-06") | (models.HistoricoNotaClinica.codigo_formato == "06")
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                models.FirmaDocumentoClinico.pt_num == str(pt_query),
                (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-06") | (models.FirmaDocumentoClinico.codigo_formato == "06"),
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 06 for PDF: {e_hist}")
    finally:
        db.close()

    if c06_data and isinstance(c06_data, dict) and "error" not in c06_data:
        for k, v in c06_data.items():
            if v and (k not in pt_data or not pt_data[k]):
                pt_data[k] = v

    is_doc_signed = bool(c06_data.get("signed_by") or c06_data.get("firmado"))

    import pdf_engine_06
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-06", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_anestesiologo"] = sig_info["nombre_medico"]
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c06_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c06_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_06_{pt_query}_{effective_slot}.pdf")
    pdf_engine_06.generate_consentimiento_06(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_anestesiologo")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-06",
                tipo_documento="Consentimiento para Procedimiento Anestésico",
                pdf_path=pdf_path,
                pdf_filename=f"Consentimiento_06_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 06 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_06_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_06_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 06")


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-06")
@app.post("/ehr/paciente/{pt_num}/consentimiento-06")
def save_consentimiento_06_endpoint(
    pt_num: str, 
    request_data: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_06", data=request_data,
    )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    try:
        target_mr = int(res.get("mrnum") or request_data.get("mrnum") or 0)
        historico_entry = models.HistoricoNotaClinica(
            pt_num=str(pt_num),
            codigo_formato="HE-DIRMED-CONSUL-PLT-06",
            evolution_slot=target_mr,
            fecha_registro=datetime.datetime.now(),
            ip_origen=client_ip,
            motivo="ACTUALIZACION_CONSENTIMIENTO_06",
            contenido_soap_json=json.dumps(request_data, ensure_ascii=False)
        )
        db.add(historico_entry)
        db.commit()
    except Exception as e:
        print(f"Error creating audit history for Consentimiento 06: {e}")
        db.rollback()

    try:
        firmas_activas = db.query(models.FirmaDocumentoClinico).filter(
            models.FirmaDocumentoClinico.pt_num == str(pt_num),
            (models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-06") | (models.FirmaDocumentoClinico.codigo_formato == "06"),
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()
        for f in firmas_activas:
            f.estado = "REVOCADA"
            f.motivo_revocacion = "MODIFICACION_DOCUMENTO_CLINICO"
        db.commit()
    except Exception as e:
        print(f"Error revocando firma previa para CI 06: {e}")
        db.rollback()

    return res


# -------------------------------------------------------------------------
# FORMATO 09: CONSENTIMIENTO INFORMADO PARA TRANSFUSIÓN DE HEMOCOMPONENTES
# HE-DIRMED-CONSUL-PLT-09
# -------------------------------------------------------------------------

@app.get("/api/ehr/paciente/{pt_num}/consentimiento-09")
def get_consentimiento_09(pt_num: str, mrnum: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene los datos estructurados del Consentimiento 09 (Transfusión de Hemocomponentes)."""
    c09 = kh_database.fetch_consentimiento_09(pt_num, mrnum=mrnum)
    if mrnum and (not c09 or "error" in c09):
        raise HTTPException(status_code=404, detail="No se encontró esta versión del consentimiento 09.")
    if not c09 or "error" in c09:
        c09 = {
            "mrnum": None,
            "pt_num": str(pt_num),
            "medico_tratante": "",
            "n_medico": "",
            "expediente": f"PT-{pt_num}",
            "acepto_y_autorizo_transfusion_de": "PAQUETE GLOBULAR / CONCENTRADO ERITROCITARIO / PLASMA FRESCO CONGELADO / PLAQUETAS",
            "paciente_capaz": True,
            "representante_legal": "",
            "parentesco": "",
            "testigo1": "",
            "testigo2": "",
            "verifico_nombre": "PERSONAL DE SALUD / BANCO DE SANGRE",
            "created_by": "",
            "created_on": "",
            "signed_by": "",
            "signed_on": "",
            "firmado": False,
            "mr_st": "RG"
        }

    target_mr = mrnum or c09.get("mrnum")
    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-09"
    )
    if target_mr:
        last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == target_mr).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
    else:
        last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k in ("acepto_y_autorizo_transfusion_de", "paciente_capaz", "representante_legal", "parentesco", "testigo1", "testigo2", "verifico_nombre", "fecha_atencion", "hora_atencion"):
                    c09[k] = v
                elif k not in c09 or not c09[k]:
                    c09[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for CI 09: {e_parse}")

    return c09


@app.get("/api/ehr/paciente/{pt_num}/pdf-consentimiento-09")
@app.get("/ehr/paciente/{pt_num}/pdf-consentimiento-09")
def get_pdf_consentimiento_09(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 09 (Transfusión de Hemocomponentes).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "TRANSFUSIÓN DE HEMOCOMPONENTES"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "medico_tratante": pt.get("attending_doctor", ""),
        "cedula": pt.get("cedula", ""),
        "acepto_y_autorizo_transfusion_de": "PAQUETE GLOBULAR / CONCENTRADO ERITROCITARIO / PLASMA FRESCO CONGELADO / PLAQUETAS",
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "paciente_capaz": True,
        "representante_legal": "",
        "parentesco": "",
        "testigo1": "",
        "testigo2": "",
        "verifico_nombre": "PERSONAL DE SALUD / BANCO DE SANGRE"
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    # Cargar datos desde SQL Server
    c09_data = kh_database.fetch_consentimiento_09(pt_query, mrnum=effective_slot) or {}
    if effective_slot and (not c09_data or "error" in c09_data):
        raise HTTPException(status_code=404, detail="No se encontró esta versión del consentimiento 09.")
    if c09_data and isinstance(c09_data, dict) and "error" not in c09_data:
        if not effective_slot and c09_data.get("mrnum"):
            effective_slot = int(c09_data["mrnum"])
        for k, v in c09_data.items():
            if v:
                pt_data[k] = v

    # Mezclar con Snapshot de Auditoría
    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) |
            (models.HistoricoNotaClinica.pt_num == str(pt_num)),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-CONSUL-PLT-09"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_query)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_query}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-CONSUL-PLT-09",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    if v is not None and v != "":
                        pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic consent 09 for PDF: {e_hist}")
    finally:
        db.close()

    is_doc_signed = bool(c09_data.get("signed_by") or c09_data.get("firmado"))

    import pdf_engine_09
    firma_data = None
    db = SessionLocal()
    try:
        raw_capaz = pt_data.get("paciente_capaz", True)
        if isinstance(raw_capaz, str):
            p_capaz = raw_capaz.lower() in ("true", "1", "si", "yes")
        elif isinstance(raw_capaz, (int, float)):
            p_capaz = bool(raw_capaz)
        else:
            p_capaz = bool(raw_capaz)
        pt_data["paciente_capaz"] = p_capaz

        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-CONSUL-PLT-09", effective_slot, paciente_capaz=p_capaz)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "sello_paciente": sig_info.get("sello_paciente"),
            "sello_testigo1": sig_info.get("sello_testigo1"),
            "sello_testigo2": sig_info.get("sello_testigo2")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, p_capaz)
        if pt_data.get("representante_legal"):
            pt_data["yo_autorizo"] = pt_data.get("representante_legal")

        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_atencion"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_atencion"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            pt_data["medico_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            pt_data["cedula"] = sig_info["cedula"]
        elif is_doc_signed and c09_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c09_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"CI_09_{pt_query}_{effective_slot}_{uuid.uuid4().hex}.pdf")

    # El pie institucional sólo puede imprimir un QR que tenga un registro
    # verificable. Cuando el PDF se abre directamente (fuera de POST
    # /pdf-preparar), crea el mismo contexto público estable y resguarda una
    # copia privada antes de entregar el archivo temporal.
    qr_context = current_qr_context()
    qr_scope = nullcontext(qr_context)
    if not qr_context:
        public_base = (
            os.getenv("PUBLIC_VERIFICATION_BASE_URL", "").strip()
            or os.getenv("VERIFICATION_BASE_URL", "").strip()
        ).rstrip("/")
        if _is_public_https_url(public_base):
            qr_id = document_uuid(pt_query, "HE-DIRMED-CONSUL-PLT-09", effective_slot)
            verify_root = public_base if public_base.endswith("/verificar") else f"{public_base}/verificar"
            qr_scope = qr_render_context(
                doc_uuid=qr_id,
                verification_url=f"{verify_root}?id={qr_id}",
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-09",
                slot=effective_slot,
                persist=True,
            )

    with qr_scope as active_qr_context:
        pdf_engine_09.generate_consentimiento_09(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("medico_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula")
            qr_pdf_path = pdf_path
            qr_doc_uuid = None
            if active_qr_context and active_qr_context.get("doc_uuid"):
                qr_doc_uuid = active_qr_context["doc_uuid"]
                verified_dir = os.path.join(PRIVATE_STORAGE_ROOT, "verified_pdfs")
                os.makedirs(verified_dir, exist_ok=True)
                qr_pdf_path = os.path.join(verified_dir, f"{qr_doc_uuid}.pdf")
                shutil.copyfile(pdf_path, qr_pdf_path)
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-CONSUL-PLT-09",
                tipo_documento="Consentimiento Informado para Transfusión de Hemocomponentes",
                pdf_path=qr_pdf_path,
                pdf_filename=f"Consentimiento_09_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c,
                doc_uuid=qr_doc_uuid,
                persist=bool(qr_doc_uuid),
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 09 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Consentimiento_09_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Consentimiento_09_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 09")


@app.post("/api/ehr/paciente/{pt_num}/pdf-preparar")
def preparar_pdf_clinico(pt_num: str, source: str = Query(...), db: Session = Depends(get_db)):
    """Emite el PDF 09 exacto con QR público, sin admitir URLs arbitrarias."""
    parsed = urlsplit(source)
    expected_path = f"/ehr/paciente/{pt_num}/pdf-consentimiento-09"
    params = parse_qs(parsed.query, keep_blank_values=True)
    if parsed.scheme or parsed.netloc or parsed.fragment or parsed.path != expected_path or set(params) != {"mrnum"}:
        raise HTTPException(status_code=422, detail="La ruta del documento no está permitida para preparar el PDF.")
    slot_values = params.get("mrnum", [])
    if len(slot_values) != 1 or not re.fullmatch(r"[1-9][0-9]*", slot_values[0]):
        raise HTTPException(status_code=422, detail="Seleccione una versión guardada del documento.")
    slot = int(slot_values[0])
    public_base = (
        os.getenv("PUBLIC_VERIFICATION_BASE_URL", "").strip()
        or os.getenv("VERIFICATION_BASE_URL", "").strip()
    ).rstrip("/")
    if not _is_public_https_url(public_base):
        raise HTTPException(
            status_code=503,
            detail="Configure una dirección pública HTTPS para que el QR pueda abrirse fuera del hospital.",
        )

    doc_uuid = f"v1_{secrets.token_urlsafe(32)}"
    verify_root = public_base if public_base.endswith("/verificar") else f"{public_base}/verificar"
    verify_url = f"{verify_root}?id={doc_uuid}"
    with qr_render_context(
        doc_uuid=doc_uuid,
        verification_url=verify_url,
        pt_num=pt_num,
        codigo_formato="HE-DIRMED-CONSUL-PLT-09",
        slot=slot,
        persist=True,
    ):
        rendered = get_pdf_consentimiento_09(pt_num, mrnum=slot)

    transient_path = rendered.path
    durable_path = None
    try:
        if not os.path.isfile(transient_path):
            raise HTTPException(status_code=500, detail="No se pudo preparar el PDF del documento.")
        durable_dir = os.path.join(PRIVATE_STORAGE_ROOT, "verified_pdfs")
        os.makedirs(durable_dir, exist_ok=True)
        durable_path = os.path.join(durable_dir, f"{doc_uuid}.pdf")
        shutil.copyfile(transient_path, durable_path)
        registrar_documento_para_qr(
            pt_num=pt_num,
            codigo_formato="HE-DIRMED-CONSUL-PLT-09",
            tipo_documento="Consentimiento Informado para Transfusión de Hemocomponentes",
            pdf_path=durable_path,
            pdf_filename=f"Consentimiento_09_HES_{pt_num}_{slot}.pdf",
            slot=slot,
            doc_uuid=doc_uuid,
            persist=True,
        )
        db.expire_all()
        if not find_doc_verificacion(db, doc_uuid):
            raise HTTPException(status_code=500, detail="No se pudo guardar el PDF verificable.")
        with open(durable_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="Consentimiento_09_HES_{pt_num}_{slot}.pdf"'},
        )
    except Exception:
        if durable_path and not find_doc_verificacion(db, doc_uuid) and os.path.isfile(durable_path):
            os.remove(durable_path)
        raise
    finally:
        _remove_transient_file(transient_path)


@app.post("/api/ehr/paciente/{pt_num}/consentimiento-09")
@app.post("/ehr/paciente/{pt_num}/consentimiento-09")
def save_consentimiento_09_endpoint(
    pt_num: str,
    request_data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_consentimiento_09", data=request_data,
    )





# -------------------------------------------------------------------------
# FORMATO 16: EGRESO Y RESUMEN CLÍNICO (HE-DIRMED-SINPRO-PLT-16)
# -------------------------------------------------------------------------

@app.get("/api/ehr/paciente/{pt_num}/egreso-resumen-16")
@app.get("/ehr/paciente/{pt_num}/egreso-resumen-16")
def get_egreso_resumen_16(pt_num: str, mrnum: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene los datos estructurados del Formato 16 (Egreso y Resumen Clínico)."""
    c16 = kh_database.fetch_egreso_resumen_16(pt_num, mrnum=mrnum)
    if mrnum and (not c16 or "error" in c16):
        raise HTTPException(status_code=404, detail="No se encontró esta versión del formato de egreso y resumen clínico.")
    if not c16 or "error" in c16:
        c16 = {
            "mrnum": None,
            "pt_num": str(pt_num),
            "expediente": f"PT-{pt_num}",
            "diagnostico_ingreso": "",
            "diagnostico_egreso": "",
            "ta": "",
            "ta_dis": "",
            "pulso": "",
            "fr_respi": "",
            "temperatura": "",
            "sat_oxi": "",
            "reingreso": "NO",
            "reea": "",
            "mdeh": "",
            "pmq": "",
            "elg": "",
            "pmt": "",
            "complicaciones": "NINGUNA",
            "meg": "MEJORADO",
            "df": "",
            "pcpcpe": "",
            "rvais": "SE DA DE ALTA CON CITA ABIERTA A URGENCIAS Y CONSULTA EXTERNA",
            "afr": "",
            "edu_pact": "CUIDADOS GENERALES DE LA SALUD, HIGIENE Y NUTRICIÓN",
            "cmep": "",
            "c_muerte": "",
            "enecropsia": "NO",
            "dr_elaboro": "",
            "dr_tratante": "",
            "cedula_elaboro": "",
            "cedula_tratante": "",
            "created_by": "",
            "created_on": "",
            "signed_by": "",
            "signed_on": "",
            "firmado": False,
            "mr_st": "RG"
        }

    target_mr = mrnum or c16.get("mrnum")
    query = db.query(models.HistoricoNotaClinica).filter(
        (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
        models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-16"
    )
    if target_mr:
        last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == target_mr).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
    else:
        last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()

    if last_hist and last_hist.contenido_soap_json:
        try:
            extra_data = json.loads(last_hist.contenido_soap_json)
            for k, v in extra_data.items():
                if k not in c16 or not c16[k]:
                    c16[k] = v
        except Exception as e_parse:
            print(f"Error parsing historical data for Egreso Resumen 16: {e_parse}")

    return c16


@app.get("/api/ehr/paciente/{pt_num}/pdf-egreso-resumen-16")
@app.get("/ehr/paciente/{pt_num}/pdf-egreso-resumen-16")
def get_pdf_egreso_resumen_16(pt_num: str, mrnum: int = None):
    """
    Genera y descarga el PDF oficial del Formato 16 (Egreso y Resumen Clínico).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num))
    pt_query = clean_pt or pt_num

    dashboard_data = kh_database.fetch_full_ehr_dashboard(pt_query)
    if not dashboard_data or "error" in dashboard_data or not isinstance(dashboard_data, dict):
        pt = {
            "name": "PACIENTE REGISTRADO EN ECE",
            "mrn": f"PT-{pt_query}",
            "dob": "",
            "age": "",
            "attending_doctor": "",
            "cedula": "",
            "diagnostico": "EGRESO Y RESUMEN CLÍNICO"
        }
    else:
        pt = dashboard_data.get("patient", {})

    pt_data = {
        "paciente_nombre": pt.get("name", ""),
        "nombre": pt.get("name", ""),
        "expediente": pt.get("mrn", f"PT-{pt_query}"),
        "pt_num": str(pt_query),
        "fecha_nacimiento": pt.get("dob", ""),
        "edad": pt.get("age", ""),
        "sexo": pt.get("gender", ""),
        "cama": pt.get("cama", "HOSPITALIZACIÓN"),
        "fecha_ingreso": pt.get("admission_date", datetime.datetime.now().strftime("%d/%m/%Y")),
        "hora_ingreso": pt.get("admission_time", "08:00"),
        "fecha_egreso": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_egreso": datetime.datetime.now().strftime("%H:%M"),
        "diagnostico_ingreso": pt.get("diagnostico", ""),
        "diagnostico_egreso": pt.get("diagnostico", ""),
        "ta": "",
        "ta_dis": "",
        "pulso": "",
        "fr_respi": "",
        "temperatura": "",
        "sat_oxi": "",
        "reingreso": "NO",
        "reea": "",
        "mdeh": "",
        "pmq": "",
        "elg": "",
        "pmt": "",
        "complicaciones": "NINGUNA",
        "meg": "MEJORADO",
        "df": "",
        "pcpcpe": "",
        "rvais": "SE DA DE ALTA CON CITA ABIERTA A URGENCIAS Y CONSULTA EXTERNA",
        "afr": "",
        "edu_pact": "CUIDADOS GENERALES DE LA SALUD, HIGIENE Y NUTRICIÓN",
        "cmep": "",
        "c_muerte": "",
        "enecropsia": "NO",
        "dr_elaboro": pt.get("attending_doctor", ""),
        "dr_tratante": pt.get("attending_doctor", ""),
        "cedula_elaboro": pt.get("cedula", ""),
        "cedula_tratante": pt.get("cedula", ""),
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
    }

    effective_slot = int(mrnum) if (mrnum and int(mrnum) > 0) else None

    # Cargar datos desde SQL Server
    c16_data = kh_database.fetch_egreso_resumen_16(pt_query, mrnum=effective_slot) or {}
    if effective_slot and (not c16_data or "error" in c16_data):
        raise HTTPException(status_code=404, detail="No se encontró esta versión del formato 16.")
    if c16_data and isinstance(c16_data, dict) and "error" not in c16_data:
        if not effective_slot and c16_data.get("mrnum"):
            effective_slot = int(c16_data["mrnum"])
        for k, v in c16_data.items():
            if v:
                pt_data[k] = v

    # Mezclar con Snapshot de Auditoría
    db = SessionLocal()
    try:
        query = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_query)) |
            (models.HistoricoNotaClinica.pt_num == str(pt_num)),
            models.HistoricoNotaClinica.codigo_formato == "HE-DIRMED-SINPRO-PLT-16"
        )
        if effective_slot:
            last_hist = query.filter(models.HistoricoNotaClinica.evolution_slot == effective_slot).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        else:
            last_hist = query.order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
            if last_hist and last_hist.evolution_slot:
                effective_slot = last_hist.evolution_slot

        if not effective_slot:
            last_sig = db.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_query)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_query}"),
                models.FirmaDocumentoClinico.codigo_formato == "HE-DIRMED-SINPRO-PLT-16",
                models.FirmaDocumentoClinico.estado == "ACTIVA"
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if last_sig and last_sig.evolution_slot:
                effective_slot = last_sig.evolution_slot

        if not effective_slot:
            effective_slot = 1

        pt_data["slot"] = effective_slot
        pt_data["mrnum"] = effective_slot

        if last_hist and last_hist.contenido_soap_json:
            try:
                hist_data = json.loads(last_hist.contenido_soap_json)
                for k, v in hist_data.items():
                    if k in {"pt_num", "mrnum", "slot"}:
                        continue
                    if v is not None and v != "":
                        pt_data[k] = v
            except Exception as e_hist:
                print(f"Error parsing historic egreso resumen 16 for PDF: {e_hist}")
    finally:
        db.close()

    is_doc_signed = bool(c16_data.get("signed_by") or c16_data.get("firmado"))

    import pdf_engine_16
    firma_data = None
    db = SessionLocal()
    try:
        sig_info = obtener_firmas_completas_documento(db, pt_query, "HE-DIRMED-SINPRO-PLT-16", effective_slot)
        firma_data = {
            "sello_digital": sig_info.get("sello_digital"),
            "hash_sha256": sig_info.get("hash_sha256", ""),
            "fecha_hora_firma": sig_info.get("fecha_hora_firma", ""),
            "nombre_medico": sig_info.get("nombre_medico"),
            "cedula": sig_info.get("cedula"),
            "curp": sig_info.get("curp"),
            "cadena_original": sig_info.get("cadena_original")
        }
        aplicar_firmas_a_pt_data(pt_data, sig_info, firma_data, True)

        if sig_info.get("fecha_hora_firma"):
            try:
                parts_f = str(sig_info["fecha_hora_firma"]).split(" ")
                if len(parts_f) >= 1:
                    pt_data["fecha_egreso"] = parts_f[0]
                if len(parts_f) >= 2:
                    pt_data["hora_egreso"] = parts_f[1][:5]
            except Exception:
                pass

        if sig_info.get("nombre_medico"):
            if not pt_data.get("dr_elaboro"):
                pt_data["dr_elaboro"] = sig_info["nombre_medico"]
            if not pt_data.get("dr_tratante"):
                pt_data["dr_tratante"] = sig_info["nombre_medico"]
        if sig_info.get("cedula"):
            if not pt_data.get("cedula_elaboro"):
                pt_data["cedula_elaboro"] = sig_info["cedula"]
            if not pt_data.get("cedula_tratante"):
                pt_data["cedula_tratante"] = sig_info["cedula"]
        elif is_doc_signed and c16_data.get("signed_by") and not (sig_info.get("sello_digital") or sig_info.get("hash_sha256")):
            pdf_service.aplicar_metadata_firma_vertical_nativa(pt_data, firma_data, c16_data)
    finally:
        db.close()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "scratch")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"EGRESO_RESUMEN_16_{pt_query}_{effective_slot}_{uuid.uuid4().hex}.pdf")

    qr_context = current_qr_context()
    qr_scope = nullcontext(qr_context)
    if not qr_context:
        public_base = (
            os.getenv("PUBLIC_VERIFICATION_BASE_URL", "").strip()
            or os.getenv("VERIFICATION_BASE_URL", "").strip()
        ).rstrip("/")
        if _is_public_https_url(public_base):
            qr_id = document_uuid(pt_query, "HE-DIRMED-SINPRO-PLT-16", effective_slot)
            verify_root = public_base if public_base.endswith("/verificar") else f"{public_base}/verificar"
            qr_scope = qr_render_context(
                doc_uuid=qr_id,
                verification_url=f"{verify_root}?id={qr_id}",
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-SINPRO-PLT-16",
                slot=effective_slot,
                persist=True,
            )

    with qr_scope as active_qr_context:
        pdf_engine_16.generate_egreso_resumen_16(pt_data, pdf_path, firma_data=firma_data)

    if os.path.exists(pdf_path):
        try:
            medico_n = (firma_data.get("nombre_medico") if firma_data else None) or pt_data.get("dr_elaboro") or pt_data.get("dr_tratante")
            medico_c = (firma_data.get("cedula") if firma_data else None) or pt_data.get("cedula_elaboro") or pt_data.get("cedula_tratante")
            qr_pdf_path = pdf_path
            qr_doc_uuid = None
            if active_qr_context and active_qr_context.get("doc_uuid"):
                qr_doc_uuid = active_qr_context["doc_uuid"]
                verified_dir = os.path.join(PRIVATE_STORAGE_ROOT, "verified_pdfs")
                os.makedirs(verified_dir, exist_ok=True)
                qr_pdf_path = os.path.join(verified_dir, f"{qr_doc_uuid}.pdf")
                shutil.copyfile(pdf_path, qr_pdf_path)
            registrar_documento_para_qr(
                pt_num=pt_query,
                codigo_formato="HE-DIRMED-SINPRO-PLT-16",
                tipo_documento="Egreso y Resumen Clínico",
                pdf_path=qr_pdf_path,
                pdf_filename=f"Egreso_Resumen_16_HES_{pt_query}.pdf",
                slot=effective_slot,
                medico_nombre=medico_n,
                medico_cedula=medico_c,
                doc_uuid=qr_doc_uuid,
                persist=bool(qr_doc_uuid),
            )
        except Exception as e_reg:
            print(f"Nota: Error registrando PDF 16 para QR: {e_reg}")

        return transient_pdf_response(
            pdf_path,
            media_type="application/pdf",
            filename=f"Egreso_Resumen_16_HES_{pt_query}.pdf",
            content_disposition_type="inline",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="Egreso_Resumen_16_HES_{pt_query}.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    raise HTTPException(status_code=500, detail="Error generating PDF 16")


@app.post("/api/ehr/paciente/{pt_num}/egreso-resumen-16")
@app.post("/ehr/paciente/{pt_num}/egreso-resumen-16")
def save_egreso_resumen_16_endpoint(
    pt_num: str,
    request_data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    assert_paciente_no_de_alta(db, pt_num)
    return _durable_consent_write(
        db, request, pt_num=pt_num,
        adapter="save_or_update_egreso_resumen_16", data=request_data,
    )


@app.get("/api/ehr/paciente/{pt_num}/formato-historial")
def get_universal_formato_historial(
    pt_num: str,
    codigo: str = Query(..., description="Código oficial o abreviado del formato institucional"),
    db: Session = Depends(get_db)
):
    """
    ENDPOINT UNIVERSAL DE CONSULTA DE HISTORIAL Y VERSIONES PARA CUALQUIERA DE LOS 100+ FORMATOS.
    Consulta SQL Server (Vertical EHR) y enriquece con firmas médicas vigentes de PostgreSQL.
    """
    historial = kh_database.fetch_generic_format_history(codigo, pt_num)

    # Enriquecer con firmas biométricas activas de PostgreSQL
    try:
        from vertical_signer import resolve_vertical_controller_and_pk
        c_name, _ = resolve_vertical_controller_and_pk(codigo)

        firmas = db.query(models.FirmaDocumentoClinico).filter(
            (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_num}"),
            (models.FirmaDocumentoClinico.codigo_formato == codigo) | (models.FirmaDocumentoClinico.codigo_formato == c_name),
            (models.FirmaDocumentoClinico.rol_firmante == "MEDICO") | (models.FirmaDocumentoClinico.rol_firmante.is_(None)),
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        ).all()

        firmas_por_slot = {}
        for firma in firmas:
            firma_slot = int(firma.evolution_slot or 0)
            previous = firmas_por_slot.get(firma_slot)
            if previous is None or (firma.fecha_hora_firma or datetime.datetime.min) > (previous.fecha_hora_firma or datetime.datetime.min):
                firmas_por_slot[firma_slot] = firma

        for doc in historial:
            try:
                slot = int(doc.get("mrnum") or 0)
            except (TypeError, ValueError):
                continue
            f = firmas_por_slot.get(slot)
            if f is None:
                continue
            try:
                current_document, _ = clinical_signing.load_authoritative_document(
                    db, pt_num=str(pt_num), codigo_formato=codigo, evolution_slot=slot,
                )
                if not clinical_signing.evidence_matches_current(db, f, current_document):
                    continue
            except clinical_signing.ClinicalDocumentUnavailable:
                continue
            doc["firmado"] = True
            doc["signed_by"] = f.nombre_medico
            doc["signed_on"] = f.fecha_hora_firma.strftime("%d/%m/%Y %H:%M") if f.fecha_hora_firma else ""
            doc["sello_digital"] = f.sello_digital
            doc["cedula"] = f.cedula_profesional
    except Exception as e:
        print(f"Nota enriqueciendo firmas en get_universal_formato_historial: {e}")

    # Enriquecer con campos guardados en HistoricoNotaClinica (PostgreSQL)
    try:
        from vertical_signer import resolve_vertical_controller_and_pk
        c_ctrl, _ = resolve_vertical_controller_and_pk(codigo)
        hists_gen = db.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(pt_num)) | (models.HistoricoNotaClinica.pt_num == f"PT-{pt_num}"),
            (models.HistoricoNotaClinica.codigo_formato == codigo) | (models.HistoricoNotaClinica.codigo_formato == c_ctrl) |
            (models.HistoricoNotaClinica.codigo_formato == str(codigo).replace("HE-DIRMED-CONSUL-PLT-", "").replace("HE-DIRMED-SINPRO-PLT-", ""))
        ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).all()
        for doc in historial:
            slot = doc.get("mrnum")
            matched = next((h for h in hists_gen if h.evolution_slot == slot), None)
            # Legacy records may have a single slot-less HES snapshot. Never
            # merge the latest snapshot into a different Vertical document.
            if not matched and len(historial) == 1 and len(hists_gen) == 1 and not hists_gen[0].evolution_slot:
                matched = hists_gen[0]
            if matched and matched.contenido_soap_json:
                try:
                    extra_data = json.loads(matched.contenido_soap_json)
                    for k, v in extra_data.items():
                        if k not in doc or not doc[k]:
                            doc[k] = v
                except Exception:
                    pass
    except Exception as e_hgen:
        print(f"Nota enriqueciendo historico en get_universal_formato_historial: {e_hgen}")
        
    return historial


@app.post("/api/ehr/paciente/{pt_num}/formato-crear-registro")
def create_universal_format_record(
    pt_num: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea un formato universal mediante la coordinación durable PostgreSQL -> SQL Server."""
    assert_paciente_no_de_alta(db, pt_num)
    codigo = payload.get("codigo", "")
    from vertical_signer import resolve_vertical_controller_and_pk

    controller_name, pk_column = resolve_vertical_controller_and_pk(codigo)
    if not controller_name or not pk_column:
        raise HTTPException(status_code=400, detail="Formato no reconocido en el catálogo institucional")
    return _durable_universal_format_write(
        db, request, pt_num=pt_num, document=payload, create=True
    )


@app.post("/api/ehr/paciente/{pt_num}/formato-guardar-registro")
@app.post("/ehr/paciente/{pt_num}/formato-guardar-registro")
def update_or_save_universal_format_record(
    pt_num: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    """Actualiza un formato universal mediante la coordinación durable existente."""
    assert_paciente_no_de_alta(db, pt_num)
    codigo = payload.get("codigo", "")
    mrnum = payload.get("mrnum")
    if not mrnum:
        return _durable_universal_format_write(
            db, request, pt_num=pt_num, document=payload, create=True
        )

    firma_existente = db.query(models.FirmaDocumentoClinico).filter(
        (models.FirmaDocumentoClinico.pt_num == str(pt_num))
        | (models.FirmaDocumentoClinico.pt_num == f"PT-{pt_num}"),
        models.FirmaDocumentoClinico.codigo_formato == codigo,
        models.FirmaDocumentoClinico.evolution_slot == int(mrnum),
        models.FirmaDocumentoClinico.estado == "ACTIVA",
    ).first()
    if firma_existente:
        raise HTTPException(
            status_code=403,
            detail=(
                "Candado de Inmutabilidad NOM-004 / NOM-024: "
                f"el documento #{mrnum} ya fue firmado biométricamente."
            ),
        )

    from vertical_signer import resolve_vertical_controller_and_pk

    controller_name, pk_column = resolve_vertical_controller_and_pk(codigo)
    if not controller_name or not pk_column:
        raise HTTPException(status_code=400, detail="Formato no reconocido en el catálogo institucional")
    return _durable_universal_format_write(
        db, request, pt_num=pt_num, document=payload, create=False
    )


if os.path.exists(frontend_dist):

    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    

    @app.get("/{full_path:path}")

    async def serve_frontend(full_path: str):

        # Ignorar si es una ruta de backend o estática principal o verificación QR
        if full_path.startswith("api/") or full_path.startswith("static/") or full_path.startswith("generados/") or full_path.startswith("verificar") or full_path == "verificar":
            raise HTTPException(status_code=404, detail="Not found")

            

        # Si el archivo existe físicamente en dist/, servirlo (ej. logo.png, websdk.client.min.js)

        file_path = os.path.join(frontend_dist, full_path)

        if os.path.exists(file_path) and os.path.isfile(file_path):

            return FileResponse(file_path)

        

        # De lo contrario, devolver index.html para el React Router

        index_path = os.path.join(frontend_dist, "index.html")

        if os.path.exists(index_path):

            return FileResponse(index_path)

        return {"message": "Frontend no construido. Por favor corre 'npm run build' en la carpeta frontend."}




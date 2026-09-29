"""Shared module catalogue and live, deny-by-default per-user permissions.

None retains the documented role defaults for pre-existing accounts. An explicit
object is a complete allowlist: missing/new keys never inherit role privileges.
"""
import json
from pathlib import Path

from fastapi import HTTPException

CATALOG = json.loads(Path(__file__).with_name("access_catalog.json").read_text(encoding="utf-8"))
MODULES = {item["id"]: item for item in CATALOG["modules"]}
LOCAL_ROLES = {item["id"] for item in CATALOG["roles"]}


def decode_permissions(value, kind):
    if value is None:
        return None
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError):
        return kind()
    return parsed if isinstance(parsed, kind) else kind()


def role_can_access(role, key):
    module = MODULES.get(key)
    if not module:
        return False
    limit = CATALOG["role_limits"].get(role)
    return (limit is None or key in limit) and ("roles" not in module or role in module["roles"])


def effective_modules(user):
    role = getattr(user, "rol", "")
    permissions = decode_permissions(getattr(user, "permisos_modulos", None), dict)
    result = {}
    for key, module in MODULES.items():
        if permissions is None:
            enabled = role in module["defaults"]
        elif key in permissions:
            enabled = permissions[key] is True or permissions[key] in ("lectura", "escritura")
        else:
            enabled = any(permissions.get(old) is True and key in children
                          for old, children in CATALOG["legacy_groups"].items())
        if key == "firmas_area":
            # Existing signing grants also expose their shared work queue. An
            # explicit module revocation still wins; no EHR access is implied.
            allowed = decode_permissions(getattr(user, "formatos_firma_permitidos", None), list) or []
            eligible = any(can_sign_format(user, code) for code in allowed)
            enabled = eligible and (enabled if permissions is not None and key in permissions else True)
        result[key] = bool(enabled and role_can_access(role, key))
    return result


def has_module(user, *keys, write=False):
    effective = effective_modules(user)
    stored = decode_permissions(getattr(user, "permisos_modulos", None), dict) or {}
    return any(effective.get(key, False) and (not write or stored.get(key) != "lectura") for key in keys)


def validate_assignments(role, modules, formats, signature_formats=None):
    if role not in LOCAL_ROLES:
        raise HTTPException(422, "Seleccione un rol válido del catálogo.")
    if modules is not None:
        try:
            value = json.loads(modules)
        except (ValueError, TypeError):
            raise HTTPException(422, "Los permisos deben ser un objeto JSON válido.")
        if not isinstance(value, dict) or any(key not in MODULES or type(enabled) is not bool for key, enabled in value.items()):
            raise HTTPException(422, "Seleccione permisos válidos del catálogo vigente.")
        if any(enabled and not role_can_access(role, key) for key, enabled in value.items()):
            raise HTTPException(422, "Uno de los permisos no está disponible para este rol.")
    if formats is not None:
        try:
            value = json.loads(formats)
        except (ValueError, TypeError):
            raise HTTPException(422, "Los formatos deben ser una lista JSON válida.")
        if not isinstance(value, list) or any(not isinstance(code, str) or not code.strip() for code in value):
            raise HTTPException(422, "Seleccione una lista válida de formatos.")
        if role == "banco_sangre" and value:
            raise HTTPException(422, "Banco de Sangre consulta sus formatos desde Firmas del área, mediante los permisos de firma.")
    if signature_formats is not None:
        try:
            value = json.loads(signature_formats)
        except (ValueError, TypeError):
            raise HTTPException(422, "Los formatos de firma deben ser una lista JSON válida.")
        if not isinstance(value, list) or any(not isinstance(code, str) or not code.strip() for code in value):
            raise HTTPException(422, "Seleccione una lista válida de formatos para firma.")
        from format_catalog import clinical_formats, canonical_format_code, special_signature_requirements, signature_role_for_account_role
        known = {canonical_format_code(item.get("codigo")) for item in clinical_formats()}
        account_role = signature_role_for_account_role(role)
        for code in value:
            canonical = canonical_format_code(code)
            required = special_signature_requirements(code)
            if canonical not in known or not required:
                raise HTTPException(422, f"El formato {code} no tiene un área de firma biométrica configurada.")
            if account_role not in required:
                raise HTTPException(422, f"El rol {role} no puede firmar el formato {code}.")


def can_sign_format(user, code, required_role=None):
    from format_catalog import canonical_format_code, special_signature_requirements, signature_role_for_account_role
    if not code:
        return False
    required = special_signature_requirements(code)
    role = str(required_role or "").strip().upper()
    if role and role not in required:
        return False
    user_role = signature_role_for_account_role(getattr(user, "rol", ""))
    if user_role not in required or (role and user_role != role):
        return False
    allowed = decode_permissions(getattr(user, "formatos_firma_permitidos", None), list) or []
    canonical = canonical_format_code(code)
    return canonical in {canonical_format_code(item) for item in allowed}


def can_use_format(user, code):
    allowed = decode_permissions(getattr(user, "formatos_permitidos", None), list)
    if allowed is None:
        return True  # Legacy accounts; new accounts persist an explicit list.
    from format_catalog import canonical_format_code
    return canonical_format_code(code) in {canonical_format_code(item) for item in allowed}


def require_format(user, code):
    if not code or not can_use_format(user, code):
        raise HTTPException(403, "No tiene acceso a este formato clínico.")


def is_clinical_signature_operator(user):
    return getattr(user, "rol", "") in {"admin", "sistemas", "medico", "ayudante", "enfermeria"} and has_module(user, "ehr", write=True)


def require_special_signature_access(user, code, role=None, signer_id=None, write=False):
    """Clinical operators may assist another identity; area users act as self."""
    if is_clinical_signature_operator(user):
        require_format(user, code)
        return
    if not has_module(user, "firmas_area", write=write) or not can_sign_format(user, code, role):
        raise HTTPException(403, "No tiene permiso de firma para este formato y área.")
    if signer_id is not None and int(signer_id) != int(getattr(user, "id", -1)):
        raise HTTPException(403, "Desde la bandeja del área debe firmar con su propia cuenta y huella.")


SPECIAL_SIGNATURE_ROUTES = (
    "/firmantes-especiales", "/banco-sangre/firmantes", "/firmas-documento",
    "/firmar-biometrico-especial", "/firmar-biometrico-banco-sangre",
)


def route_modules(method, path):
    """Aliases share a policy. Unknown endpoints fail closed in middleware.

    New endpoints in a known domain inherit its permission. A new domain needs
    one catalogue entry and one explicit mapping here, never another UI list.
    """
    path = path or ""
    while path.startswith("/api/"):
        path = path[4:]
    read = method in {"GET", "HEAD"}
    if path.startswith("/firmas-area"):
        return ("firmas_area",)
    if path.startswith("/ehr/") and path.endswith(SPECIAL_SIGNATURE_ROUTES):
        return ("ehr", "firmas_area")
    if read and "/pdf-" in path:
        from format_catalog import format_for_route, special_signature_requirements
        code = format_for_route(path)
        if code and special_signature_requirements(code):
            return ("ehr", "firmas_area")
    if path in {"/auth/me", "/auth/session", "/auth/logout", "/auth/change-password", "/catalogos/permisos"}:
        return ()
    if path == "/{full_path:path}":
        return ()  # SPA fallback; backend/static paths return 404 in its handler.
    if path.startswith("/usuarios") or path == "/auth/impersonate" or path.endswith("/permisos"):
        return ("usuarios",)
    if path == "/analytics":
        return ("dashboard",)
    if path == "/auditoria" or path.startswith("/operational/") or path == "/clinical-sync/reconcile":
        return ("auditoria",)
    if path == "/backup":
        return ("respaldos",)
    if path.startswith("/escaneos"):
        return ("escaneos",)
    if path.startswith("/catalogos/"):
        return tuple(MODULES) if read else ("catalogos",)
    if path.startswith("/medicos") or path.startswith("/files/photos/"):
        if read:
            return ("alta", "directorio", "agenda", "captura_enfermeria", "captura_medica", "ehr")
        return ("alta",) if path == "/medicos" else ("directorio",)
    if path.startswith("/agenda/"):
        return ("agenda", "ehr")
    if path.startswith("/camas"):
        return ("camas", "ehr", "captura_enfermeria") if read else ("camas",)
    if path in {"/atenciones/todas", "/atenciones/exportar"}:
        return ("historial",)
    if path.startswith("/atenciones/"):
        if path.endswith("/pdf"):
            return ("historial", "captura_enfermeria", "captura_medica")
        if path.endswith(("/reaperturar", "/autorizar")):
            return ("historial",)
        if path.endswith("/notas"):
            return ("captura_enfermeria", "captura_medica")
        if path == "/atenciones/pre-captura" or path == "/atenciones/mis-registros":
            return ("captura_enfermeria",)
        if "/pendientes/" in path or "/historial/" in path or path.endswith("/firmar-lote"):
            return ("captura_medica",)
        return ("captura_enfermeria", "captura_medica")
    if "firmantes-biometricos" in path:
        return ("ehr", "pacientes")
    if path.startswith("/ehr/") or path.startswith("/kh/") or path.startswith("/firmas/"):
        if path == "/ehr/pacientes/buscar":
            return ("ehr", "agenda", "camas")
        return ("ehr",)
    if path.startswith("/pacientes"):
        if path.endswith(("/firmas", "/firmar-biometrico-firmante")):
            return ("ehr",)
        return ("pacientes", "captura_enfermeria", "camas", "ehr")
    if path.startswith("/clinical-sync/operations/"):
        return ("ehr", "pacientes", "captura_enfermeria", "captura_medica")
    return None


def role_restricted_route(method, path):
    """Permission assignment cannot grant medical identity or impersonation."""
    return path == "/api/auth/impersonate" or (method not in {"GET", "HEAD"} and (
        path.endswith(("/firmar-biometrico", "/firmar-biometrico-banco-sangre", "/firmar-biometrico-especial", "/prescribir-biometrico", "/discontinuar-biometrico", "/firmar-lote", "/tsa/reintentar", "/reaperturar", "/autorizar"))
    ))


async def authorize_formats(request, user, route_template):
    """Check PDF/read/write/sign aliases before fetching any clinical content."""
    from format_catalog import clinical_formats, format_for_route
    code = format_for_route(route_template or "")
    params = request.query_params
    if "/ehr/" in (route_template or "") or "firmar-biometrico" in (route_template or ""):
        requested = params.get("codigo_formato") or params.get("codigo")
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.json()
            except (ValueError, TypeError):
                body = {}
            if isinstance(body, dict):
                requested = body.get("codigo_formato") or body.get("codigo") or requested
        if requested:
            if (route_template or "").endswith(SPECIAL_SIGNATURE_ROUTES) and not has_module(user, "ehr"):
                require_special_signature_access(user, requested)
            else:
                require_format(user, requested)
        if (route_template or "").endswith(("/formato-crear-registro", "/formato-guardar-registro", "/formato-historial")):
            from database import SessionLocal
            from routers.catalogos import available_formats
            from format_catalog import canonical_format_code
            with SessionLocal() as db:
                known = {canonical_format_code(item["codigo"]) for item in available_formats(db)}
            if not requested or canonical_format_code(requested) not in known:
                raise HTTPException(403, "Formato no registrado en el catálogo activo.")
        if (route_template or "").endswith("/pdf-preparar"):
            code = format_for_route(params.get("source", "").split("?", 1)[0])
            if not code:
                raise HTTPException(403, "Formato no autorizado para preparación.")
    if code:
        if request.method in {"GET", "HEAD"} and "/pdf-" in (route_template or "") and not has_module(user, "ehr"):
            require_special_signature_access(user, code)
            if not str(params.get("mrnum", "")).isdigit() or int(params["mrnum"]) <= 0:
                raise HTTPException(422, "Seleccione un registro exacto para consultar el formato.")
        else:
            require_format(user, code)
    if code == "HE-DIRMED-EXPEDIENTE-COMPLETO" and any(not can_use_format(user, item["codigo"]) for item in clinical_formats()):
        raise HTTPException(403, "El expediente completo requiere acceso a todos los formatos que contiene.")


def filter_ehr_formats(data, user):
    """The composite dashboard must not leak the bodies hidden by its cards."""
    if not isinstance(data, dict) or getattr(user, "formatos_permitidos", None) is None:
        return data
    groups = data.get("formatos_disponibles", [])
    data["formatos_disponibles"] = [dict(group, formatos=[item for item in group.get("formatos", []) if can_use_format(user, item["codigo"])]) for group in groups]
    from format_catalog import format_for_route
    special_keys = {
        "egreso_voluntario_15": "HE-DIRMED-SINPRO-PLT-15",
        "historial_15_ev": "HE-DIRMED-SINPRO-PLT-15",
        "egreso_resumen_16": "HE-DIRMED-SINPRO-PLT-16",
        "historial_16": "HE-DIRMED-SINPRO-PLT-16",
    }
    for key in list(data):
        # The same catalogue controls cards, endpoints and document payloads.
        # New consent/history keys stay hidden until their format is registered.
        if key in special_keys:
            code = special_keys[key]
        elif key.startswith(("consentimiento_", "historial_")):
            suffix = key.split("_", 1)[1].replace("_", "-")
            code = format_for_route(f"pdf-consentimiento-{suffix}")
        else:
            continue
        if not code or not can_use_format(user, code):
            data.pop(key, None)
    if not can_use_format(user, "HE-DIRMED-SINPRO-PLT-87/01"):
        data["clinicalNotes"] = []
        data["evoluciones"] = {}
        data["evoluciones_list"] = []
        data["total_evoluciones"] = 0
    if not can_use_format(user, "HE-DIRMED-CONSUL-PLT-24"):
        data["evoluciones_hospitalizacion_list"] = []
        data["total_evoluciones_hosp"] = 0
    data["timelineEvents"] = [item for item in data.get("timelineEvents", []) if not item.get("format_code") or can_use_format(user, item["format_code"])]
    return data

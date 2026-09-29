"""Generate the complete FastAPI authorization inventory without importing main.

Usage from the repository root:
    python backend/scripts/audit_route_authorization.py
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from route_policy import (  # noqa: E402
    MUTATING_METHODS,
    PUBLIC_ROUTE_TEMPLATES,
    PUBLIC_SPA_PATHS,
    READ_ROLE_POLICIES,
    REQUIRES_FUNCTIONAL_DECISION,
    WRITE_ROLE_POLICIES,
)
from access_control import route_modules, role_restricted_route


@dataclass(frozen=True)
class RouteEntry:
    method: str
    path: str
    function: str
    source: str
    line: int
    declared_roles: tuple[str, ...]
    explicit_identity_dependency: bool


def _literal_roles(node: ast.AST) -> tuple[str, ...]:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not isinstance(child.func, ast.Name) or child.func.id != "require_role" or not child.args:
            continue
        try:
            values = ast.literal_eval(child.args[0])
        except (ValueError, TypeError):
            continue
        if isinstance(values, (list, tuple, set)):
            return tuple(sorted(str(value) for value in values))
    return ()


def _has_identity_dependency(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Name) and child.id == "get_current_user"
        for child in ast.walk(node)
    )


def _router_prefix(tree: ast.AST) -> str:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        for keyword in node.value.keywords:
            if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                return str(keyword.value.value)
    return ""


def parse_routes(source_path: Path) -> list[RouteEntry]:
    tree = ast.parse(source_path.read_text(encoding="utf-8-sig"), filename=str(source_path))
    prefix = _router_prefix(tree)
    entries: list[RouteEntry] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        roles = _literal_roles(node)
        identity = _has_identity_dependency(node)
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.upper()
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "API_ROUTE"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            paths = [prefix + str(decorator.args[0].value)]
            methods = [method]
            if method == "API_ROUTE":
                methods = []
                for keyword in decorator.keywords:
                    if keyword.arg == "methods":
                        try:
                            methods = [str(value).upper() for value in ast.literal_eval(keyword.value)]
                        except (ValueError, TypeError):
                            methods = []
            for route_method in methods:
                for path in paths:
                    entries.append(
                        RouteEntry(
                            method=route_method,
                            path=path,
                            function=node.name,
                            source=str(source_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                            line=node.lineno,
                            declared_roles=roles,
                            explicit_identity_dependency=identity,
                        )
                    )
    return entries


def current_policy(entry: RouteEntry) -> str:
    if entry.declared_roles:
        return ", ".join(entry.declared_roles)
    if entry.explicit_identity_dependency:
        return "JWT autenticado (sin rol local)"
    return "middleware global"


def expected_policy(entry: RouteEntry) -> tuple[str, str, str]:
    key = (entry.method, entry.path)
    if key in PUBLIC_ROUTE_TEMPLATES or (entry.method == "GET" and entry.path in PUBLIC_SPA_PATHS):
        return "PUBLICA", "—", "allowlist exacta método+ruta"
    if key in REQUIRES_FUNCTIONAL_DECISION:
        return "ROL_ESPECIFICO", "REQUIERE_DECISION_FUNCIONAL", "bloqueada por defecto (403)"
    required = route_modules(entry.method, entry.path)
    if required is None:
        return "ROL_ESPECIFICO", "SIN_POLITICA", "bloqueada por defecto (403)"
    if not required:
        return "AUTENTICADA", "identidad activa", "sesión / catálogo de permisos / shell SPA"
    extra = ""
    if role_restricted_route(entry.method, entry.path):
        extra = "; además rol: " + ", ".join(sorted(WRITE_ROLE_POLICIES.get(key, entry.declared_roles)))
    return "ROL_ESPECIFICO", "áreas: " + ", ".join(required) + extra, "permisos vigentes por usuario + formatos; nuevas escrituras requieren allowlist"


def main() -> int:
    routes = parse_routes(BACKEND_DIR / "main.py")
    routes.extend(parse_routes(BACKEND_DIR / "routers" / "catalogos.py"))

    existing = {(entry.method, entry.path) for entry in routes}
    for method, path in sorted(PUBLIC_ROUTE_TEMPLATES):
        if (method, path) not in existing:
            routes.append(RouteEntry(method, path, "framework/public_asset", "route_policy.py", 0, (), False))
    for path in sorted(PUBLIC_SPA_PATHS):
        if ("GET", path) not in existing:
            routes.append(RouteEntry("GET", path, "frontend_shell", "route_policy.py", 0, (), False))

    routes = sorted(set(routes), key=lambda item: (item.path, item.method, item.function))
    missing_writes = []
    for entry in routes:
        key = (entry.method, entry.path)
        if (
            entry.method in MUTATING_METHODS
            and key not in PUBLIC_ROUTE_TEMPLATES
            and key not in WRITE_ROLE_POLICIES
            and key not in REQUIRES_FUNCTIONAL_DECISION
        ):
            missing_writes.append(key)

    if missing_writes:
        for key in missing_writes:
            print(f"ERROR: escritura sin política: {key[0]} {key[1]}", file=sys.stderr)
        return 1

    counts = {"PUBLICA": 0, "AUTENTICADA": 0, "ROL_ESPECIFICO": 0}
    rows = []
    for entry in routes:
        classification, expected, protection = expected_policy(entry)
        counts[classification] += 1
        action = {
            "GET": "lectura",
            "POST": "creación/acción",
            "PUT": "actualización",
            "PATCH": "actualización parcial",
            "DELETE": "eliminación lógica/física",
        }.get(entry.method, "acción")
        rows.append(
            "| {method} `{path}` | {action} | {current} | {expected} | {classification} | {protection} | `{source}:{line}` |".format(
                method=entry.method,
                path=entry.path,
                action=action,
                current=current_policy(entry),
                expected=expected,
                classification=classification,
                protection=protection,
                source=entry.source,
                line=entry.line,
            )
        )

    output = REPO_ROOT / "INVENTARIO_RUTAS_AUTORIZACION.md"
    output.write_text(
        "\n".join(
            [
                "# Inventario de rutas y autorización",
                "",
                "Generado automáticamente por `backend/scripts/audit_route_authorization.py`.",
                "",
                f"- Total: **{len(routes)}**",
                f"- PUBLICA: **{counts['PUBLICA']}**",
                f"- AUTENTICADA: **{counts['AUTENTICADA']}**",
                f"- ROL_ESPECIFICO: **{counts['ROL_ESPECIFICO']}**",
                "",
                "La columna “roles actuales/locales” refleja dependencias heredadas. La autorización efectiva usa access_catalog.json + access_control.py: permisos vigentes por usuario, límite RH y formatos. Las dependencias de rol aceptan el permiso de área validado, excepto operaciones médicas y suplantación que conservan su restricción de rol.",
                "",
                "| Endpoint | Acción | Roles actuales/locales | Roles esperados | Clase | Protección existente/faltante | Fuente |",
                "|---|---|---|---|---|---|---|",
                *rows,
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Inventario generado: {output}")
    print(f"Total={len(routes)} PUBLICA={counts['PUBLICA']} AUTENTICADA={counts['AUTENTICADA']} ROL_ESPECIFICO={counts['ROL_ESPECIFICO']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

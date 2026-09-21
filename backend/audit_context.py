"""Request-scoped audit identity and safe structured logging helpers."""

from __future__ import annotations

import contextvars
import json
import logging
import re
import uuid
from typing import Any, Optional

from sqlalchemy import event


request_id_var = contextvars.ContextVar("hes_request_id", default=None)
operation_id_var = contextvars.ContextVar("hes_operation_id", default=None)
actor_real_var = contextvars.ContextVar("hes_actor_real", default=None)
actor_effective_var = contextvars.ContextVar("hes_actor_effective", default=None)
impersonation_reason_var = contextvars.ContextVar("hes_impersonation_reason", default=None)

_SENSITIVE_KEY = re.compile(r"(password|token|secret|private|fmd|raw|connection|string|authorization)", re.I)


def safe_json(value: Any) -> str:
    if not isinstance(value, dict):
        value = {"value": str(value)}
    clean = {key: "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else item for key, item in value.items()}
    return json.dumps(clean, default=str, ensure_ascii=False, separators=(",", ":"))


def start_request(request_id: Optional[str] = None):
    normalized = (request_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", normalized):
        normalized = str(uuid.uuid4())
    return request_id_var.set(normalized), normalized


def set_identity(*, real: Optional[str], effective: Optional[str], reason: Optional[str] = None) -> None:
    actor_real_var.set(real)
    actor_effective_var.set(effective)
    impersonation_reason_var.set(reason)


def set_operation(operation_id: Optional[str]) -> None:
    operation_id_var.set(str(operation_id) if operation_id else None)


def install_audit_enrichment(AuditoriaLog) -> None:
    """Populate mandatory evidence for all ORM audit inserts, including legacy call sites."""

    @event.listens_for(AuditoriaLog, "before_insert", propagate=True)
    def _enrich(_mapper, _connection, target) -> None:
        target.request_id = target.request_id or request_id_var.get() or str(uuid.uuid4())
        target.operation_id = target.operation_id or operation_id_var.get()
        target.actor_real = target.actor_real or actor_real_var.get()
        target.actor_effective = target.actor_effective or actor_effective_var.get()
        target.motivo_impersonacion = target.motivo_impersonacion or impersonation_reason_var.get()
        target.resultado = target.resultado or "EXITO"
        if target.actor_effective is None and target.usuario_id is not None:
            target.actor_effective = f"usuario:{target.usuario_id}"
        if target.actor_real is None:
            target.actor_real = target.actor_effective or "sistema"
        if target.actor_effective is None:
            target.actor_effective = target.actor_real
        if target.operation_id is None and target.detalles_json:
            try:
                details = json.loads(target.detalles_json)
                if isinstance(details, dict) and details.get("operation_id"):
                    target.operation_id = str(details["operation_id"])
            except (TypeError, ValueError):
                pass


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
            "operation_id": getattr(record, "operation_id", None) or operation_id_var.get(),
        }
        for field in ("endpoint", "status", "latency_ms", "error_type"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return safe_json(payload)


def configure_structured_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

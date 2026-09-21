"""Durable, idempotent coordination for PostgreSQL -> SQL Server writes.

This module deliberately does not pretend that both databases share a
transaction.  PostgreSQL stores the intent and local evidence first; the
external adapter is then invoked and the durable state records the outcome.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import socket
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

import models


PENDING = "PENDING"
PROCESSING = "PROCESSING"
SYNCED = "SYNCED"
RETRYABLE_ERROR = "RETRYABLE_ERROR"
FAILED = "FAILED"
REQUIRES_RECONCILIATION = "REQUIRES_RECONCILIATION"

RECOVERABLE_STATES = frozenset({PENDING, RETRYABLE_ERROR, REQUIRES_RECONCILIATION})
TERMINAL_STATES = frozenset({SYNCED, FAILED})
_SECRET_PATTERN = re.compile(
    r"(?i)(password|pwd|secret|token|authorization|user\s*id|uid)\s*=\s*[^;\s]+"
)
_CONNECTION_PATTERN = re.compile(
    r"(?i)(postgres(?:ql)?|mssql|sqlserver|odbc)\+?[a-z0-9_]*://[^\s]+"
)


class ClinicalSyncError(RuntimeError):
    """Base error carrying a safe classification for the state machine."""

    retryable = False


class RetryableExternalError(ClinicalSyncError):
    retryable = True


class PermanentExternalError(ClinicalSyncError):
    retryable = False


class ManualReconciliationRequired(ClinicalSyncError):
    """The external outcome cannot be established safely by an automatic retry."""

    retryable = False
    requires_reconciliation = True


class OperationAlreadyProcessing(ClinicalSyncError):
    retryable = True


class IdempotencyKeyConflict(ClinicalSyncError):
    """A client key was already bound to materially different request data."""

    retryable = False
    error_code = "IDEMPOTENCY_KEY_CONFLICT"


@dataclass(frozen=True)
class ExecutionResult:
    operation_id: uuid.UUID
    state: str
    value: Any = None
    idempotent: bool = False


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def sanitize_error(error: BaseException | str | None) -> Optional[str]:
    """Return useful evidence without credentials, URLs, or biometric payloads."""
    if error is None:
        return None
    value = str(error).replace("\x00", " ")
    value = _CONNECTION_PATTERN.sub("[connection-redacted]", value)
    value = _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}=[redacted]", value)
    value = re.sub(r"(?i)bearer\s+[a-z0-9._~+/-]+", "Bearer [redacted]", value)
    value = re.sub(r"(?i)(fmd_template|event\.samples)\s*[:=]\s*\S+", r"\1=[redacted]", value)
    return value[:1000]


def minimal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop request-only secrets/biometrics before persisting reconciliation data."""
    forbidden = {
        "fmd_template",
        "challenge_id",
        "session_id",
        "authorization",
        "jwt",
        "token",
        "password",
        "private_key",
    }
    clean: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in forbidden:
            continue
        if isinstance(value, dict):
            clean[key] = minimal_payload(value)
        elif isinstance(value, list):
            clean[key] = [minimal_payload(v) if isinstance(v, dict) else v for v in value]
        else:
            clean[key] = value
    return clean


def make_idempotency_key(
    operation_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    supplied_key: Optional[str] = None,
) -> str:
    """Build a bounded stable key. Clients should send ``Idempotency-Key``."""
    if supplied_key:
        normalized = supplied_key.strip()
        if not normalized or len(normalized) > 180:
            raise ValueError("Idempotency-Key inválida")
        return f"{operation_type}:{normalized}"
    safe = minimal_payload(payload)
    material = json.dumps(safe, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(f"{operation_type}|{aggregate_id}|{material}".encode()).hexdigest()
    return f"{operation_type}:{digest}"


def request_fingerprint(
    *,
    operation_type: str,
    aggregate_type: str,
    aggregate_id: str,
    patient_ref: Optional[str],
    payload: dict[str, Any],
) -> str:
    material = json.dumps(
        {
            "operation_type": operation_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": str(aggregate_id),
            "patient_ref": str(patient_ref) if patient_ref is not None else None,
            "payload": minimal_payload(payload),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _assert_matching_fingerprint(
    operation: models.ClinicalSyncOperation,
    expected: str,
) -> None:
    if operation.request_fingerprint != expected:
        raise IdempotencyKeyConflict(
            "La Idempotency-Key ya está ligada a una solicitud diferente"
        )


def create_or_get_intent(
    db: Session,
    *,
    idempotency_key: str,
    operation_type: str,
    aggregate_type: str,
    aggregate_id: str,
    patient_ref: Optional[str],
    payload: dict[str, Any],
    max_attempts: int = 5,
) -> tuple[models.ClinicalSyncOperation, bool]:
    """Persist the intent before any local or external clinical mutation."""
    fingerprint = request_fingerprint(
        operation_type=operation_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        patient_ref=patient_ref,
        payload=payload,
    )
    existing = db.query(models.ClinicalSyncOperation).filter(
        models.ClinicalSyncOperation.idempotency_key == idempotency_key
    ).first()
    if existing:
        _assert_matching_fingerprint(existing, fingerprint)
        return existing, False

    operation = models.ClinicalSyncOperation(
        idempotency_key=idempotency_key,
        operation_type=operation_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        patient_ref=str(patient_ref) if patient_ref is not None else None,
        payload=minimal_payload(payload),
        request_fingerprint=fingerprint,
        state=PENDING,
        max_attempts=max_attempts,
    )
    db.add(operation)
    try:
        db.commit()
        db.refresh(operation)
        return operation, True
    except IntegrityError:
        db.rollback()
        existing = db.query(models.ClinicalSyncOperation).filter(
            models.ClinicalSyncOperation.idempotency_key == idempotency_key
        ).one()
        _assert_matching_fingerprint(existing, fingerprint)
        return existing, False


def claim_operation(
    db: Session,
    operation_id: uuid.UUID,
    *,
    force: bool = False,
    lease_seconds: int = 300,
) -> models.ClinicalSyncOperation:
    """Atomically claim one delivery; concurrent requests cannot both deliver it."""
    operation = db.query(models.ClinicalSyncOperation).filter(
        models.ClinicalSyncOperation.operation_id == operation_id
    ).with_for_update().one()
    now = utcnow()
    updated = operation.updated_at
    if updated is not None and updated.tzinfo is None:
        updated = updated.replace(tzinfo=dt.timezone.utc)
    if operation.state == SYNCED:
        return operation
    if operation.state == FAILED and not force:
        return operation
    if operation.state == PROCESSING and updated and (now - updated).total_seconds() < lease_seconds:
        raise OperationAlreadyProcessing("La operación ya está siendo procesada")
    if operation.next_attempt_at and not force:
        next_attempt = operation.next_attempt_at
        if next_attempt.tzinfo is None:
            next_attempt = next_attempt.replace(tzinfo=dt.timezone.utc)
        if next_attempt > now:
            raise OperationAlreadyProcessing("La operación está en backoff")
    operation.state = PROCESSING
    operation.attempts = int(operation.attempts or 0) + 1
    operation.updated_at = now
    operation.last_error = None
    db.commit()
    db.refresh(operation)
    return operation


def mark_local_applied(db: Session, operation: models.ClinicalSyncOperation) -> None:
    operation.local_applied_at = operation.local_applied_at or utcnow()
    operation.updated_at = utcnow()
    db.commit()


def _append_attempt(
    db: Session,
    operation: models.ClinicalSyncOperation,
    *,
    outcome: str,
    started_at: dt.datetime,
    error: BaseException | str | None = None,
) -> None:
    db.add(
        models.ClinicalSyncAttempt(
            operation_id=operation.operation_id,
            attempt_number=operation.attempts,
            outcome=outcome,
            error_class=type(error).__name__ if isinstance(error, BaseException) else None,
            error_message=sanitize_error(error),
            started_at=started_at,
            finished_at=utcnow(),
        )
    )


def mark_synced(
    db: Session,
    operation: models.ClinicalSyncOperation,
    *,
    started_at: dt.datetime,
) -> None:
    now = utcnow()
    operation.external_applied_at = operation.external_applied_at or now
    operation.state = SYNCED
    operation.last_error = None
    operation.next_attempt_at = None
    operation.completed_at = now
    operation.updated_at = now
    _append_attempt(db, operation, outcome=SYNCED, started_at=started_at)
    db.commit()


def classify_external_error(error: BaseException | str) -> type[ClinicalSyncError]:
    text = str(error).lower()
    if isinstance(error, (TimeoutError, ConnectionError, socket.timeout, OperationalError)):
        return RetryableExternalError
    retryable_tokens = (
        "timeout",
        "timed out",
        "deadlock",
        "connection",
        "network",
        "temporar",
        "unavailable",
        "08s01",
        "40001",
        "1205",
    )
    if any(token in text for token in retryable_tokens):
        return RetryableExternalError
    return PermanentExternalError


def ensure_external_success(value: Any) -> Any:
    """Normalize legacy adapters while making every hidden failure explicit."""
    if value is False or value is None:
        raise RetryableExternalError("El adaptador externo no confirmó la operación")
    if isinstance(value, dict):
        error = value.get("error") or value.get("Error")
        if error:
            raise classify_external_error(str(error))(str(error))
        if value.get("success") is False:
            raise classify_external_error(value.get("message", "Fallo externo"))(
                value.get("message", "Fallo externo")
            )
        if value.get("success") is not True and str(value.get("status", "")).lower() != "success":
            raise RetryableExternalError("Respuesta externa inesperada sin confirmación explícita")
    elif value is not True:
        raise RetryableExternalError("Respuesta externa inesperada sin confirmación explícita")
    return value


def mark_failed(
    db: Session,
    operation: models.ClinicalSyncOperation,
    error: BaseException | str,
    *,
    started_at: dt.datetime,
    retryable: Optional[bool] = None,
) -> str:
    if getattr(error, "requires_reconciliation", False):
        operation.state = REQUIRES_RECONCILIATION
        operation.next_attempt_at = None
        operation.updated_at = utcnow()
        _append_attempt(
            db,
            operation,
            outcome=REQUIRES_RECONCILIATION,
            started_at=started_at,
            error=error,
        )
        db.commit()
        return operation.state
    if retryable is None:
        retryable = classify_external_error(error) is RetryableExternalError
    operation.last_error = sanitize_error(error)
    if retryable and operation.attempts < operation.max_attempts:
        operation.state = RETRYABLE_ERROR
        delay = min(300, 2 ** max(0, operation.attempts - 1))
        operation.next_attempt_at = utcnow() + dt.timedelta(seconds=delay)
    else:
        operation.state = FAILED
        operation.next_attempt_at = None
        operation.completed_at = utcnow()
    operation.updated_at = utcnow()
    _append_attempt(db, operation, outcome=operation.state, started_at=started_at, error=error)
    db.commit()
    return operation.state


def mark_requires_reconciliation(
    session_factory: sessionmaker,
    operation_id: uuid.UUID,
    error: BaseException | str,
    *,
    started_at: dt.datetime,
) -> None:
    """Best-effort evidence when external success cannot be confirmed in PostgreSQL."""
    db = session_factory()
    try:
        operation = db.query(models.ClinicalSyncOperation).filter(
            models.ClinicalSyncOperation.operation_id == operation_id
        ).with_for_update().one()
        operation.state = REQUIRES_RECONCILIATION
        operation.external_applied_at = operation.external_applied_at or utcnow()
        operation.last_error = sanitize_error(error)
        operation.next_attempt_at = utcnow()
        operation.updated_at = utcnow()
        _append_attempt(
            db,
            operation,
            outcome=REQUIRES_RECONCILIATION,
            started_at=started_at,
            error=error,
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def execute_external(
    db: Session,
    operation: models.ClinicalSyncOperation,
    callback: Callable[[], Any],
    *,
    session_factory: Optional[sessionmaker] = None,
) -> ExecutionResult:
    """Deliver one already-local operation and persist an unambiguous result."""
    if operation.local_applied_at is None:
        raise ManualReconciliationRequired(
            "La operación local no quedó confirmada; no se ejecutará el write externo"
        )
    operation = claim_operation(db, operation.operation_id)
    if operation.state in TERMINAL_STATES:
        return ExecutionResult(operation.operation_id, operation.state, idempotent=True)
    started_at = utcnow()
    try:
        value = ensure_external_success(callback())
    except OperationAlreadyProcessing:
        raise
    except Exception as exc:
        state = mark_failed(
            db,
            operation,
            exc,
            started_at=started_at,
            retryable=getattr(exc, "retryable", None),
        )
        return ExecutionResult(operation.operation_id, state)

    try:
        mark_synced(db, operation, started_at=started_at)
    except Exception as exc:
        db.rollback()
        if session_factory is not None:
            mark_requires_reconciliation(
                session_factory,
                operation.operation_id,
                exc,
                started_at=started_at,
            )
        return ExecutionResult(operation.operation_id, REQUIRES_RECONCILIATION, value=value)
    return ExecutionResult(operation.operation_id, SYNCED, value=value)


def pending_operations(db: Session, *, limit: int = 50) -> list[models.ClinicalSyncOperation]:
    now = utcnow()
    return (
        db.query(models.ClinicalSyncOperation)
        # REQUIRES_RECONCILIATION is intentionally excluded from unattended
        # delivery. An operator may target it explicitly after reviewing the
        # recorded attempt and the external idempotency strategy.
        .filter(models.ClinicalSyncOperation.state.in_({PENDING, RETRYABLE_ERROR}))
        .filter(
            (models.ClinicalSyncOperation.next_attempt_at.is_(None))
            | (models.ClinicalSyncOperation.next_attempt_at <= now)
        )
        .order_by(models.ClinicalSyncOperation.created_at)
        .limit(limit)
        .all()
    )


def reconcile(
    db: Session,
    dispatcher: Callable[[models.ClinicalSyncOperation], Callable[[], Any]],
    *,
    operation_ids: Optional[Iterable[uuid.UUID]] = None,
    limit: int = 50,
    session_factory: Optional[sessionmaker] = None,
) -> list[ExecutionResult]:
    query = db.query(models.ClinicalSyncOperation)
    if operation_ids is not None:
        query = query.filter(models.ClinicalSyncOperation.operation_id.in_(list(operation_ids)))
        operations = query.all()
    else:
        operations = pending_operations(db, limit=limit)
    results: list[ExecutionResult] = []
    for operation in operations:
        if operation.local_applied_at is None:
            started_at = utcnow()
            state = mark_failed(
                db,
                operation,
                ManualReconciliationRequired(
                    "Intención recuperada sin confirmación de la operación local"
                ),
                started_at=started_at,
            )
            results.append(ExecutionResult(operation.operation_id, state))
            continue
        if (
            operation.state == REQUIRES_RECONCILIATION
            and (operation.payload or {}).get("retry_policy") == "manual"
        ):
            results.append(
                ExecutionResult(
                    operation.operation_id,
                    REQUIRES_RECONCILIATION,
                    idempotent=True,
                )
            )
            continue
        try:
            callback = dispatcher(operation)
            results.append(
                execute_external(
                    db,
                    operation,
                    callback,
                    session_factory=session_factory,
                )
            )
        except OperationAlreadyProcessing:
            continue
        except Exception as exc:
            started_at = utcnow()
            state = mark_failed(db, operation, exc, started_at=started_at)
            results.append(ExecutionResult(operation.operation_id, state))
    return results

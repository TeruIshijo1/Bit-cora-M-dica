"""Controles biométricos comunes: plantillas, attestation y anti-replay."""

from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import and_, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models


TEMPLATE_FORMAT = "ANSI_378_2004"
TEMPLATE_VERSION = 1
CHALLENGE_TTL_SECONDS = 120

ALLOWED_ACTIONS = frozenset(
    {
        "LOGIN",
        "FIRMA_MEDICA",
        "FIRMA_FIRMANTE",
        "FIRMA_LOTE",
        "PRESCRIPCION",
        "SUSPENSION",
        "DIETA",
        "VERIFICACION_FIRMANTE",
        "ENROLAMIENTO_MEDICO",
        "REENROLAMIENTO_MEDICO",
        "ACTUALIZACION_FEA",
        "ENROLAMIENTO_FIRMANTE",
        "REENROLAMIENTO_FIRMANTE",
        "FIRMA_BANCO_SANGRE",
        "ENROLAMIENTO_BANCO_SANGRE",
        "REENROLAMIENTO_BANCO_SANGRE",
        "FIRMA_USUARIO_ESPECIAL",
        "ENROLAMIENTO_USUARIO",
        "REENROLAMIENTO_USUARIO",
    }
)


@dataclass(frozen=True)
class TemplateInfo:
    state: str
    canonical: Optional[str] = None


@dataclass(frozen=True)
class AttestedCapture:
    canonical: str
    acquisition_id: str
    acquisition_started_at: datetime.datetime
    captured_at: datetime.datetime
    context: Optional[dict] = None
    match_result: Optional[dict] = None


def _clean(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def detect_template_state(value: Optional[str]) -> TemplateInfo:
    """Clasifica sin convertir ni reconstruir material legacy."""
    if not value or not value.strip():
        return TemplateInfo("SIN_BIOMETRIA")
    try:
        payload = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return TemplateInfo("LEGACY_RAW")

    if isinstance(payload, dict) and payload.get("metadata") and payload.get("base64"):
        return TemplateInfo("LEGACY_RAW")
    if not isinstance(payload, dict):
        return TemplateInfo("LEGACY_RAW")
    if payload.get("format") != TEMPLATE_FORMAT or payload.get("version") != TEMPLATE_VERSION:
        return TemplateInfo("LEGACY_RAW")
    data = payload.get("data")
    if not isinstance(data, str) or not data or len(data) > 256_000:
        return TemplateInfo("LEGACY_RAW")
    try:
        decoded = base64.b64decode(data, validate=True)
    except (ValueError, TypeError):
        return TemplateInfo("LEGACY_RAW")
    if len(decoded) < 16 or not decoded.startswith(b"FMR\x00"):
        return TemplateInfo("LEGACY_RAW")
    canonical = json.dumps(
        {"format": TEMPLATE_FORMAT, "version": TEMPLATE_VERSION, "data": data},
        separators=(",", ":"),
        sort_keys=True,
    )
    return TemplateInfo("FMD_VALIDO", canonical)


def _secret() -> bytes:
    secret = os.getenv("BIOMETRIC_ATTESTATION_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="Attestation biométrica no configurada.")
    return secret.encode("utf-8")


SIGNER_ROLE_MARKER = "|role:"


def identity_subject(identity_ref: Optional[str]) -> Optional[str]:
    """Return the enrolled identity portion of a role-bound document identity."""
    if not identity_ref:
        return identity_ref
    return str(identity_ref).split(SIGNER_ROLE_MARKER, 1)[0]


def role_bound_signer_identity(signer_id: int, role: str) -> str:
    return f"firmante:{int(signer_id)}{SIGNER_ROLE_MARKER}{str(role or '').strip().upper()}"


def _match_job(db: Session, row) -> tuple[bool, list[dict]]:
    if row.action in {"ENROLAMIENTO_MEDICO", "REENROLAMIENTO_MEDICO", "ENROLAMIENTO_FIRMANTE", "REENROLAMIENTO_FIRMANTE", "ENROLAMIENTO_BANCO_SANGRE", "REENROLAMIENTO_BANCO_SANGRE", "ENROLAMIENTO_USUARIO", "REENROLAMIENTO_USUARIO"}:
        return False, []
    if row.action == "FIRMA_USUARIO_ESPECIAL":
        from access_control import can_sign_format
        users = db.query(models.Usuario).filter(
            models.Usuario.activo == True,
            models.Usuario.biometric_status == "FMD_VALIDO",
        ).all()
        expected = row.expected_identity_ref
        expected_subject = identity_subject(expected)
        role = str(expected or "").split(SIGNER_ROLE_MARKER, 1)[1].upper() if SIGNER_ROLE_MARKER in str(expected or "") else None
        candidates = []
        for user in users:
            identity = f"usuario_especial:{user.id}"
            if expected_subject and identity != expected_subject:
                continue
            if not can_sign_format(user, row.document_code, role):
                continue
            info = detect_template_state(user.fmd_template)
            if not info.canonical:
                continue
            candidates.append({
                "id": user.id,
                "identity": expected,
                "data": json.loads(info.canonical)["data"],
                "template_hash": hashlib.sha256(info.canonical.encode()).hexdigest(),
            })
        return True, candidates
    if row.action == "FIRMA_BANCO_SANGRE":
        users = db.query(models.Usuario).filter(
            models.Usuario.rol == "banco_sangre",
            models.Usuario.activo == True,
            models.Usuario.biometric_status == "FMD_VALIDO",
        ).all()
        candidates = []
        expected = row.expected_identity_ref
        expected_subject = identity_subject(expected)
        for user in users:
            identity = f"banco_sangre:{user.id}"
            if expected_subject and identity != expected_subject:
                continue
            info = detect_template_state(user.fmd_template)
            if not info.canonical:
                continue
            candidates.append({
                "id": user.id,
                "identity": expected if expected_subject == identity else identity,
                "data": json.loads(info.canonical)["data"],
                "template_hash": hashlib.sha256(info.canonical.encode()).hexdigest(),
            })
        return True, candidates
    kind = (
        "banco_sangre" if row.action == "FIRMA_BANCO_SANGRE"
        else "firmante" if row.action in {"FIRMA_FIRMANTE", "VERIFICACION_FIRMANTE"}
        else "medico"
    )
    expected = row.expected_identity_ref
    expected_subject = identity_subject(expected)
    if kind == "firmante":
        records = db.query(models.BiometriaFirmanteEpisodio).filter_by(estado="ACTIVO", biometric_status="FMD_VALIDO").all()
    elif kind == "banco_sangre":
        records = db.query(models.Usuario).filter_by(
            rol="banco_sangre", activo=True, biometric_status="FMD_VALIDO",
        ).all()
    else:
        records = db.query(models.Medico).filter_by(activo_status=True, biometric_status="FMD_VALIDO").all()
    candidates = []
    for record in records:
        identity = f"{kind}:{record.id}"
        if expected_subject and identity != expected_subject:
            continue
        info = detect_template_state(record.fmd_template)
        if not info.canonical:
            continue
        candidates.append({"id": record.id, "identity": expected if expected_subject == identity else identity,
                           "data": json.loads(info.canonical)["data"],
                           "template_hash": hashlib.sha256(info.canonical.encode()).hexdigest()})
    return True, candidates


def _encode_authorization(context: dict) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(context, ensure_ascii=False, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_secret(), ("HES-CAPTURE-REQUEST-V2\n" + encoded).encode(), hashlib.sha256).hexdigest()
    return encoded + "." + signature


def issue_capture_authorization(db: Session, challenge_id: str, *, document_digest: Optional[str] = None) -> str:
    row = db.query(models.BiometricChallenge).filter_by(
        token_hash=hashlib.sha256(challenge_id.encode()).hexdigest()
    ).one()
    context = {
        "protocol_version": 2,
        "challenge_id": challenge_id,
        "session_id": row.session_id,
        "action": row.action,
        "subject_ref": row.subject_ref,
        "expected_identity_ref": row.expected_identity_ref,
        "patient_ref": row.patient_ref,
        "document_code": row.document_code,
        "document_ref": row.document_ref,
        "document_digest": document_digest,
        "issued_at": row.created_at.isoformat(timespec="milliseconds") + "Z",
        "expires_at": row.expires_at.isoformat(timespec="milliseconds") + "Z",
    }
    required, candidates = _match_job(db, row)
    context["match_required"] = required
    key = hmac.new(_secret(), b"HES-MATCH-KEY-V2", hashlib.sha256).digest()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, json.dumps(candidates, separators=(",", ":")).encode(), challenge_id.encode())
    context["match_job"] = base64.urlsafe_b64encode(nonce + ciphertext).decode().rstrip("=")
    return _encode_authorization(context)


def _authorization_context(ticket: object) -> dict:
    if not isinstance(ticket, str) or len(ticket) > 2_000_000:
        raise HTTPException(status_code=401, detail="Autorización de captura inválida.")
    try:
        encoded, supplied = ticket.split(".")
        expected = hmac.new(_secret(), ("HES-CAPTURE-REQUEST-V2\n" + encoded).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            raise ValueError()
        context = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if not isinstance(context, dict) or context.get("protocol_version") != 2:
            raise ValueError()
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Autorización de captura inválida.") from exc
    issued = _parse_attested_time(context.get("issued_at"), "issued_at")
    expires = _parse_attested_time(context.get("expires_at"), "expires_at")
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if issued > now or expires <= now or not (0 < (expires - issued).total_seconds() <= 120):
        raise HTTPException(status_code=401, detail="Autorización de captura vencida.")
    return context


def _attestation_message(payload: dict) -> bytes:
    fields = ("protocol_version", "format", "version", "fmd_hash", "challenge_id",
              "session_id", "acquisition_id", "acquisition_started_at", "capture_started_at",
              "captured_at", "device_id", "authorization", "match_success", "matched_identity", "matched_template_hash")
    material = json.dumps([payload.get(key) for key in fields], ensure_ascii=False, separators=(",", ":"))
    return ("HES-CAPTURE-ATTESTATION-V2\n" + material).encode("utf-8")


def _parse_attested_time(value: object, field: str) -> datetime.datetime:
    if not isinstance(value, str):
        raise HTTPException(status_code=401, detail=f"{field} biométrico inválido.")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"{field} biométrico inválido.") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed


def validate_attested_capture_evidence(
    template: str, challenge_id: str, session_id: str
) -> AttestedCapture:
    """Validate service-controlled acquisition evidence bound to this challenge."""
    try:
        payload = json.loads(template)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Plantilla biométrica inválida.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Plantilla biométrica inválida.")
    if payload.get("protocol_version") != 2:
        raise HTTPException(status_code=401, detail="Se requiere captura confiable protocolo V2.")
    if payload.get("challenge_id") != challenge_id or payload.get("session_id") != session_id:
        raise HTTPException(status_code=401, detail="La captura no pertenece al challenge o sesión actuales.")
    context = _authorization_context(payload.get("authorization"))
    if context.get("challenge_id") != challenge_id or context.get("session_id") != session_id:
        raise HTTPException(status_code=401, detail="Autorización ajena al challenge o sesión.")
    acquisition_id = payload.get("acquisition_id")
    if not isinstance(acquisition_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", acquisition_id):
        raise HTTPException(status_code=401, detail="Identificador de adquisición inválido.")
    acquisition_started_at = _parse_attested_time(payload.get("acquisition_started_at"), "acquisition_started_at")
    capture_started_at = _parse_attested_time(payload.get("capture_started_at"), "capture_started_at")
    captured_at = _parse_attested_time(payload.get("captured_at"), "captured_at")
    issued = _parse_attested_time(context.get("issued_at"), "issued_at")
    expires = _parse_attested_time(context.get("expires_at"), "expires_at")
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if not (issued <= acquisition_started_at <= capture_started_at <= captured_at <= now and captured_at < expires):
        raise HTTPException(status_code=401, detail="La captura está fuera de su adquisición/challenge.")
    if not isinstance(payload.get("device_id"), str) or not re.fullmatch(r"[a-f0-9]{64}", payload["device_id"]):
        raise HTTPException(status_code=401, detail="Origen de dispositivo inválido.")
    supplied = payload.get("attestation")
    expected = hmac.new(_secret(), _attestation_message(payload), hashlib.sha256).hexdigest()
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Attestation biométrica inválida.")

    info = detect_template_state(json.dumps(payload))
    if info.state != "FMD_VALIDO" or not info.canonical:
        raise HTTPException(status_code=422, detail="La captura no contiene una plantilla FMD ANSI válida.")
    decoded = base64.b64decode(payload["data"], validate=True)
    if payload.get("fmd_hash") != hashlib.sha256(decoded).hexdigest():
        raise HTTPException(status_code=401, detail="Hash FMD no corresponde a la captura.")
    return AttestedCapture(
        canonical=info.canonical,
        acquisition_id=acquisition_id,
        acquisition_started_at=acquisition_started_at,
        captured_at=captured_at,
        context=context,
        match_result={key: payload.get(key) for key in ("match_success", "matched_identity", "matched_template_hash")},
    )


def validate_attested_capture(template: str, challenge_id: str, session_id: str) -> str:
    return validate_attested_capture_evidence(template, challenge_id, session_id).canonical


def build_attested_capture(
    data: str,
    challenge_id: str,
    session_id: str,
    captured_at: str,
    *,
    acquisition_id: Optional[str] = None,
    acquisition_started_at: Optional[str] = None,
    authorization: str,
    match_result: Optional[dict] = None,
) -> str:
    """Helper para fixtures sintéticos; no recibe ni produce RAW."""
    payload = {
        "protocol_version": 2,
        "format": TEMPLATE_FORMAT,
        "version": TEMPLATE_VERSION,
        "data": data,
        "fmd_hash": hashlib.sha256(base64.b64decode(data)).hexdigest(),
        "authorization": authorization,
        "device_id": "0" * 64,
        "capture_started_at": captured_at,
        "challenge_id": challenge_id,
        "session_id": session_id,
        "acquisition_id": acquisition_id or secrets.token_urlsafe(32),
        "acquisition_started_at": acquisition_started_at or captured_at,
        "captured_at": captured_at,
    }
    payload.update(match_result or {"match_success": None, "matched_identity": None, "matched_template_hash": None})
    secret = os.getenv("BIOMETRIC_ATTESTATION_SECRET", "")
    payload["attestation"] = hmac.new(
        secret.encode("utf-8"), _attestation_message(payload), hashlib.sha256
    ).hexdigest()
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def verify_attested_match(capture: AttestedCapture, candidates: list[dict], kind: str) -> int:
    """Verify station matching evidence against the CURRENT enrolled template.

    The central server never contacts the clinician PC's localhost or USB.
    Reference templates travel only in the AES-GCM encrypted, signed job.
    """
    proof = capture.match_result or {}
    if not capture.context or capture.context.get("match_required") is not True or not isinstance(proof.get("match_success"), bool):
        raise HTTPException(status_code=502, detail="Resultado de matching atestado inválido.")
    if proof["match_success"] is not True:
        action = str(capture.context.get("action") or "").strip().upper()
        status_code = 401 if action == "LOGIN" else 403
        raise HTTPException(
            status_code=status_code,
            detail=(
                "La huella no coincide con la registrada para esta persona. No se guardó la firma. Use el mismo dedo que se registró e inténtelo de nuevo."
                if action != "LOGIN"
                else "La huella no corresponde al usuario seleccionado. Intente nuevamente."
            ),
        )
    for row in candidates:
        template = detect_template_state(row["fmd_template"]).canonical
        enrolled_identity = f"{kind}:{row['id']}"
        expected_identity = (capture.context or {}).get("expected_identity_ref")
        attested_identity = expected_identity if identity_subject(expected_identity) == enrolled_identity else enrolled_identity
        if template and proof.get("matched_identity") == attested_identity and proof.get("matched_template_hash") == hashlib.sha256(template.encode()).hexdigest():
            return row["id"]
    action = str(capture.context.get("action") or "").strip().upper()
    raise HTTPException(
        status_code=401 if action == "LOGIN" else 409,
        detail=(
            "No se pudo confirmar que la huella corresponda al usuario seleccionado. Intente nuevamente."
            if action == "LOGIN"
            else "La huella sí fue reconocida, pero el registro asociado cambió durante la lectura. Cierre esta ventana, vuelva a abrirla e intente de nuevo."
        ),
    )


def create_challenge(
    db: Session,
    *,
    action: str,
    session_id: str,
    subject_ref: Optional[str] = None,
    expected_identity_ref: Optional[str] = None,
    patient_ref: Optional[str] = None,
    document_code: Optional[str] = None,
    document_ref: Optional[str] = None,
) -> tuple[str, datetime.datetime]:
    action = (action or "").strip().upper()
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=422, detail="Acción biométrica no permitida.")
    session_id = _clean(session_id)
    if not session_id or len(session_id) > 128:
        raise HTTPException(status_code=422, detail="session_id biométrico obligatorio o inválido.")
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(seconds=CHALLENGE_TTL_SECONDS)
    challenge_id = secrets.token_urlsafe(32)
    db.add(
        models.BiometricChallenge(
            token_hash=hashlib.sha256(challenge_id.encode("utf-8")).hexdigest(),
            action=action,
            session_id=session_id,
            subject_ref=_clean(subject_ref),
            expected_identity_ref=_clean(expected_identity_ref),
            patient_ref=_clean(patient_ref),
            document_code=_clean(document_code),
            document_ref=_clean(document_ref),
            created_at=now,
            expires_at=expires_at,
        )
    )
    db.commit()
    return challenge_id, expires_at


def consume_challenge(
    db: Session,
    *,
    challenge_id: str,
    action: str,
    session_id: str,
    subject_ref: Optional[str] = None,
    expected_identity_ref: Optional[str] = None,
    patient_ref: Optional[str] = None,
    document_code: Optional[str] = None,
    document_ref: Optional[str] = None,
    acquisition_id: Optional[str] = None,
    acquisition_started_at: Optional[datetime.datetime] = None,
    captured_at: Optional[datetime.datetime] = None,
    acquisition_context: Optional[dict] = None,
) -> None:
    if not challenge_id:
        raise HTTPException(status_code=422, detail="challenge_id biométrico obligatorio.")
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id biométrico obligatorio.")

    if acquisition_context is not None:
        expected_context = {
            "action": (action or "").strip().upper(), "session_id": _clean(session_id),
            "subject_ref": _clean(subject_ref), "expected_identity_ref": _clean(expected_identity_ref),
            "patient_ref": _clean(patient_ref), "document_code": _clean(document_code), "document_ref": _clean(document_ref),
        }
        if any(acquisition_context.get(key) != value for key, value in expected_context.items()):
            raise HTTPException(status_code=401, detail="La captura no corresponde al contexto autorizado.")
    now = datetime.datetime.utcnow()
    filters = [
        models.BiometricChallenge.token_hash == hashlib.sha256(challenge_id.encode("utf-8")).hexdigest(),
        models.BiometricChallenge.action == (action or "").strip().upper(),
        models.BiometricChallenge.session_id == _clean(session_id),
        models.BiometricChallenge.consumed_at.is_(None),
        models.BiometricChallenge.expires_at >= now,
    ]
    for column, expected in (
        (models.BiometricChallenge.subject_ref, _clean(subject_ref)),
        (models.BiometricChallenge.expected_identity_ref, _clean(expected_identity_ref)),
        (models.BiometricChallenge.patient_ref, _clean(patient_ref)),
        (models.BiometricChallenge.document_code, _clean(document_code)),
        (models.BiometricChallenge.document_ref, _clean(document_ref)),
    ):
        filters.append(column.is_(None) if expected is None else column == expected)
    if acquisition_id:
        filters.extend(
            [
                models.BiometricChallenge.created_at <= acquisition_started_at,
                models.BiometricChallenge.expires_at >= captured_at,
            ]
        )

    try:
        result = db.execute(
            update(models.BiometricChallenge)
            .where(and_(*filters))
            .values(consumed_at=now, acquisition_id=acquisition_id)
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Adquisición biométrica ya consumida.") from exc
    if result.rowcount != 1:
        raise HTTPException(
            status_code=401,
            detail="Challenge inexistente, expirado, consumido o ajeno al contexto de la operación.",
        )

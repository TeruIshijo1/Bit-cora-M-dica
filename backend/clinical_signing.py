"""Canonical, versioned evidence for clinical signatures.

The browser selects a document; it never supplies the bytes protected by the
medical ECDSA signature.  This module obtains the current clinical record from
the server-side data sources and serialises it deterministically.
"""

from __future__ import annotations

import base64
import datetime as dt
import decimal
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional
from zoneinfo import ZoneInfo


SCHEMA_VERSION = "CANONICAL_V2"
LEGACY_SCHEMA_VERSION = "LEGACY_V1"
BIOMETRIC_EVIDENCE_VERSION = "BIOMETRIC_EVIDENCE_V1"
PDF_PRIMARY = "EVIDENCIA_PRIMARIA"
PDF_SECONDARY = "REPRESENTACION_SECUNDARIA_NO_FIRMADA"
MEXICO_CITY = ZoneInfo("America/Mexico_City")


class ClinicalDocumentUnavailable(RuntimeError):
    """The authoritative clinical document could not be obtained."""


class CanonicalPayloadError(ValueError):
    """The stored canonical snapshot is malformed or internally inconsistent."""


ONE_WITNESS_CONSENT_TABLES = frozenset({"MR_CI_CC", "MR_CI_APA", "MR_CI_CES"})
NO_WITNESS_CONSENT_TABLES = frozenset({"MR_CI_EED"})
TWO_WITNESS_CONSENT_TABLES = frozenset({
    "MR_02_CI_TRATAMIENTO_QUIRURGICO", "MR_08_CI_DIAGNOSTICO_ADMISION_CONTI",
    "MR_MR_CI_HOSP", "MR_CI_AUT_TRANS_HEMO", "MR_CI_EMI", "MR_CI_ETE_CARD",
    "MR_CI_HISTERECTOMIA", "MR_CI_NO_REANIMACION", "MR_CI_OI", "MR_CI_PQ",
    "MR_CI_REANIMACION", "MR_CI_RGO_CE", "MR_CI_RGO_HU", "MR_CI_TINA",
})
MEDICAL_ONLY_TABLES = frozenset({
    "MR_24_HOJA_EVOL", "MR_26_01", "MR_ERC_HOS", "MR_EV_HOSP", "MR_HC_HOS",
    "MR_HC_URG", "MR_LV_SPI", "MR_N_POST_OP", "MR_NE_URG", "MR_PLT_79",
    "MR_RCE_Q", "MR_RPS_FQ", "MR_RTOE_PACE", "MR_RTOE_RPA", "MR_SOL_DIET",
    "MR_SOL_OP", "MR_TERM_EMB", "MR_URGENCIAS", "MR_VRA_HOS",
})
EVOLUTION_CONSENT_CODES = frozenset({
    # This authorization form shares MR_EV_HOSP with ordinary progress notes.
    "HE-DIRMED-SINPRO-PLT-15", "SINPRO-PLT-15", "PLT-EV-15",
})


def consent_signature_policy(code: str) -> tuple[bool, int]:
    """Return (authorizer required, witness count) for a registered format.

    Every resolvable clinical source needs an explicit policy. New modules must
    declare one before signing; an unknown source cannot silently become a
    medical-only note and bypass a patient authorization.
    """
    from vertical_signer import resolve_vertical_controller_and_pk

    normalized = str(code or "").strip().upper()
    try:
        table, _ = resolve_vertical_controller_and_pk(normalized)
    except ValueError as exc:
        raise ClinicalDocumentUnavailable(str(exc)) from exc
    if normalized in EVOLUTION_CONSENT_CODES:
        return True, 2
    if table in ONE_WITNESS_CONSENT_TABLES:
        return True, 1
    if table in NO_WITNESS_CONSENT_TABLES:
        return True, 0
    if table in TWO_WITNESS_CONSENT_TABLES:
        return True, 2
    if table in MEDICAL_ONLY_TABLES:
        return False, 0
    raise ClinicalDocumentUnavailable(
        "Este formato todavía no tiene definida su regla de firmas. Solicite su configuración antes de firmar."
    )


def special_signature_requirements(code: str) -> list[str]:
    """Return additional signer roles declared by the active format catalog."""
    from format_catalog import special_signature_requirements as catalog_requirements

    return catalog_requirements(code)


def required_consent_witnesses(code: str) -> int:
    """Witness places in the registered document, before authorizer adjustment."""
    return consent_signature_policy(code)[1]


def minimum_consent_witnesses_for_closure(code: str, authorizer_role: str | None) -> int:
    """Return the operational minimum; all template witness places remain open.

    This threshold describes workflow completion only. It must not be used as
    a declaration that the document meets NOM witness requirements.
    """
    expected = required_consent_witnesses(code)
    role = str(authorizer_role or "").strip().upper()
    if role in {"REPRESENTANTE_LEGAL", "TUTOR", "FAMILIAR"}:
        return 0
    return min(1, expected)


def required_consent_witnesses_for_authorizer(code: str, authorizer_role: str | None) -> int:
    """Compatibility name for the operational closure minimum."""
    return minimum_consent_witnesses_for_closure(code, authorizer_role)


def requires_consent_signers(code: str) -> bool:
    """Whether the patient/representative authorization is part of the flow.

    A zero witness count does not mean that the patient signature is optional:
    EED, for example, has an authorization block but no witness line.
    """
    return consent_signature_policy(code)[0]


def consent_signatures_complete(info, *, required_witnesses: int) -> bool:
    """Validate the authorizer, signed identities and minimum for closure."""
    if required_witnesses not in (0, 1, 2):
        raise ValueError("La política de firmas debe requerir entre cero y dos testigos")
    if not info.get("firmante_paciente_id") or not info.get("sello_paciente"):
        return False
    witness_ids = []
    for index in (1, 2):
        if not info.get(f"sello_testigo{index}"):
            continue
        witness_id = info.get(f"firmante_testigo{index}_id")
        if not witness_id:
            return False
        witness_ids.append(witness_id)
    all_ids = [info["firmante_paciente_id"], *witness_ids]
    return len(set(all_ids)) == len(all_ids) and len(witness_ids) >= required_witnesses


def signed_witness_count(info) -> int:
    """Count distinct signed witnesses, excluding the authorizer."""
    authorizer_id = info.get("firmante_paciente_id")
    return len({
        info.get(f"firmante_testigo{index}_id")
        for index in (1, 2)
        if info.get(f"sello_testigo{index}")
        and info.get(f"firmante_testigo{index}_id")
        and info.get(f"firmante_testigo{index}_id") != authorizer_id
    })


def explicit_patient_capacity(document: ClinicalDocument) -> bool | None:
    """Read only an explicit capacity decision from the signed source snapshot.

    Legacy Vertical records often omit this field. Interrogation type, age,
    representative name and PDF defaults are not proof of patient capacity.
    In those cases return None, never invent a clinical decision.
    """
    content = getattr(document, "contenido_clinico", None)
    if not isinstance(content, Mapping):
        return None
    value = next(
        (item for key, item in content.items() if str(key).strip().lower() == "paciente_capaz"),
        None,
    )
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "si", "sí", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None


def load_document_after_capture(db, **kwargs):
    """Reuse the snapshot checked by the biometric validator in this session."""
    prepared = db.info.pop("biometric_document", None)
    return prepared if prepared is not None else load_authoritative_document(db, **kwargs)


def assert_document_author(document, doctor):
    """Check the selected snapshot, not the latest patient's row or SignedBy."""
    import re
    import unicodedata
    from fastapi import HTTPException
    content = document.contenido_clinico
    if not isinstance(content, dict):
        return
    def normal(value):
        text = unicodedata.normalize("NFD", str(value).upper())
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = re.sub(r"^DR(A)?\.?\s+", "", text)
        return re.sub(r"[^A-Z0-9]", "", text)
    fields = {str(key).upper(): value for key, value in content.items()}
    assigned = next((fields[k] for k in ("N_MEDICO", "MEDICO_N", "NOMBRE_MEDICO", "MEDICO", "MEDICO_TRATANTE") if fields.get(k)), None)
    if assigned and normal(assigned) not in {"BITACORASIS", "DESCONOCIDO", "MEDICOTRATANTEHES", "ND"}:
        if normal(assigned) != normal(doctor.nombre_completo):
            raise HTTPException(status_code=403, detail="El médico verificado no es el autor asignado al documento seleccionado.")


@dataclass(frozen=True)
class ClinicalDocument:
    tipo_documento: str
    contenido_clinico: Any
    version_documento: str
    source_identifier: str
    pdf_bytes: Optional[bytes] = None
    pdf_identifier: Optional[str] = None


def _normalise(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalPayloadError("NaN e infinitos no son serializables canónicamente")
        return value
    if isinstance(value, decimal.Decimal):
        return format(value, "f")
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        if isinstance(value, dt.datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=MEXICO_CITY)
        return value.isoformat()
    if isinstance(value, bytes):
        return {"$bytes_base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Mapping):
        return {str(key): _normalise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalise(item) for item in value]
    return str(value)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """RFC 8259 JSON profile: UTF-8, sorted keys, fixed separators, no NaN."""
    return json.dumps(
        _normalise(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def document_digest(document: ClinicalDocument) -> str:
    return sha256_hex(canonical_json_bytes({
        "tipo_documento": document.tipo_documento,
        "contenido_clinico": document.contenido_clinico,
        "version_documento": str(document.version_documento),
        "source_identifier": document.source_identifier,
    }))


_URGENCY_NATIVE_SIGNATURE_FIELDS = frozenset({
    "signed_by", "signed_on", "es_signature", "mr_st", "firmado",
})


def _clinical_content_for_comparison(source_identifier: str, content: Mapping[str, Any]) -> dict[str, Any]:
    """Ignore native-signature metadata, but only for the MR_NE_URG source.

    Older 87/01 snapshots retain their original signed bytes. We verify those
    bytes first and compare only clinical fields with the current source.
    """
    normalized = _normalise(content)
    if str(source_identifier).startswith("MR_NE_URG:"):
        return {
            key: value for key, value in normalized.items()
            if key.lower() not in _URGENCY_NATIVE_SIGNATURE_FIELDS
        }
    return normalized


def evidence_matches_current(db, signature, document: ClinicalDocument) -> bool:
    """Do not stamp an operational PDF using stale, legacy or misbound evidence."""
    try:
        raw = signature.canonical_payload.encode("utf-8")
        if sha256_hex(raw) != signature.payload_hash:
            return False
        payload = json.loads(raw)
        if canonical_json_bytes(payload) != raw:
            return False
        if not all((
            payload.get("codigo_formato") == signature.codigo_formato,
            str(payload.get("pt_num")).removeprefix("PT-") == str(signature.pt_num).removeprefix("PT-"),
            int(payload.get("evolution_slot", -1)) == int(signature.evolution_slot or 0),
            payload.get("schema_version") == signature.signature_schema_version,
            payload.get("tipo_documento") == document.tipo_documento,
            str(payload.get("version_documento")) == str(document.version_documento) == str(signature.document_version),
            payload.get("source_identifier") == document.source_identifier,
            _clinical_content_for_comparison(
                document.source_identifier, payload.get("contenido_clinico") or {},
            ) == _clinical_content_for_comparison(
                document.source_identifier, document.contenido_clinico,
            ),
        )):
            return False
        if signature.signature_schema_version == SCHEMA_VERSION:
            return bool(verify_signature_record(db, signature)["complete"])
        signer = payload.get("firmante") or {}
        common_identity_matches = all((
            signer.get("rol") == signature.rol_firmante,
            signer.get("nombre") == signature.nombre_medico,
        ))
        if signature.usuario_firmante_id is not None:
            signer_identity_matches = all((
                signer.get("firmante_id") is None,
                signature.firmante_id is None,
                signer.get("usuario_firmante_id") == signature.usuario_firmante_id,
            ))
        else:
            signer_identity_matches = signer.get("firmante_id") == signature.firmante_id
        return signature.signature_schema_version == BIOMETRIC_EVIDENCE_VERSION and common_identity_matches and signer_identity_matches
    except (AttributeError, TypeError, ValueError, KeyError):
        return False


def build_canonical_payload(
    *,
    document: ClinicalDocument,
    codigo_formato: str,
    pt_num: str,
    expediente: str,
    evolution_slot: int,
    patient_identity: Mapping[str, Any],
    medico_id: int,
    nombre_medico: str,
    cedula: str,
    proposito: str,
    signed_at: dt.datetime,
    key_id: str,
) -> tuple[dict[str, Any], bytes, str, Optional[str]]:
    if signed_at.tzinfo is None or signed_at.utcoffset() is None:
        raise CanonicalPayloadError("fecha_hora_firma debe incluir zona horaria")
    pdf_hash = sha256_hex(document.pdf_bytes) if document.pdf_bytes is not None else None
    payload = {
        "schema_version": SCHEMA_VERSION,
        "tipo_documento": document.tipo_documento,
        "codigo_formato": codigo_formato,
        "paciente": _normalise(dict(patient_identity)),
        "pt_num": str(pt_num),
        "expediente": str(expediente),
        "evolution_slot": int(evolution_slot),
        "version_documento": str(document.version_documento),
        "source_identifier": str(document.source_identifier),
        "contenido_clinico": _normalise(document.contenido_clinico),
        "firmante": {
            "medico_id": int(medico_id),
            "nombre": nombre_medico,
            "cedula": cedula,
        },
        "proposito_firma": proposito,
        "fecha_hora_firma": signed_at.isoformat(),
        "key_id": key_id,
        "pdf": {
            "evidence_role": PDF_PRIMARY if pdf_hash else PDF_SECONDARY,
            "identifier": document.pdf_identifier,
            "sha256": pdf_hash,
        },
    }
    encoded = canonical_json_bytes(payload)
    return payload, encoded, sha256_hex(encoded), pdf_hash


def build_biometric_evidence_payload(
    *,
    document: ClinicalDocument,
    codigo_formato: str,
    pt_num: str,
    expediente: str,
    evolution_slot: int,
    patient_identity: Mapping[str, Any],
    firmante_id: Optional[int],
    rol_firmante: str,
    nombre_firmante: str,
    identificacion: Optional[str],
    signed_at: dt.datetime,
    usuario_firmante_id: Optional[int] = None,
) -> tuple[dict[str, Any], bytes, str]:
    if signed_at.tzinfo is None or signed_at.utcoffset() is None:
        raise CanonicalPayloadError("fecha_hora_firma debe incluir zona horaria")
    payload = {
        "schema_version": BIOMETRIC_EVIDENCE_VERSION,
        "tipo_documento": document.tipo_documento,
        "codigo_formato": codigo_formato,
        "paciente": _normalise(dict(patient_identity)),
        "pt_num": str(pt_num),
        "expediente": str(expediente),
        "evolution_slot": int(evolution_slot),
        "version_documento": str(document.version_documento),
        "source_identifier": document.source_identifier,
        "contenido_clinico": _normalise(document.contenido_clinico),
        "firmante": {
            "firmante_id": int(firmante_id) if firmante_id is not None else None,
            "usuario_firmante_id": int(usuario_firmante_id) if usuario_firmante_id is not None else None,
            "rol": rol_firmante,
            "nombre": nombre_firmante,
            "identificacion": identificacion,
        },
        "resultado_biometrico": "MATCH_1_A_1_VERIFICADO",
        "naturaleza_evidencia": "AUTENTICACION_BIOMETRICA_Y_EVIDENCIA_DE_ACTO_NO_FEA_PERSONAL",
        "fecha_hora_firma": signed_at.isoformat(),
    }
    encoded = canonical_json_bytes(payload)
    return payload, encoded, sha256_hex(encoded)


def parse_and_validate_snapshot(snapshot: str, expected_hash: str) -> tuple[dict[str, Any], bytes]:
    raw = snapshot.encode("utf-8")
    if not expected_hash or sha256_hex(raw) != expected_hash:
        raise CanonicalPayloadError("El SHA-256 del snapshot canónico no coincide")
    try:
        payload = json.loads(snapshot)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CanonicalPayloadError("El snapshot canónico no es JSON válido") from exc
    canonical = canonical_json_bytes(payload)
    if canonical != raw:
        raise CanonicalPayloadError("El snapshot almacenado no usa serialización canónica")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise CanonicalPayloadError("Versión de esquema de firma no soportada")
    return payload, raw


def verify_pdf_hash(payload: Mapping[str, Any], pdf_bytes: Optional[bytes]) -> Optional[bool]:
    expected = (payload.get("pdf") or {}).get("sha256")
    if not expected:
        return None
    if pdf_bytes is None:
        return False
    return sha256_hex(pdf_bytes) == expected


def verify_signature_record(db, signature, *, pdf_bytes: Optional[bytes] = None) -> dict[str, Any]:
    """Verify snapshot hash, exact key, identity/document binding, PDF and TSA."""
    if getattr(signature, "signature_schema_version", None) != SCHEMA_VERSION:
        return {
            "classification": LEGACY_SCHEMA_VERSION,
            "complete": False,
            "snapshot": False,
            "ecdsa": False,
            "identity": False,
            "document_binding": False,
            "pdf": None,
            "tsa": {"status": "TSA_LEGACY_NO_VERIFICADO", "verificado": False},
            "errors": ["FIRMA_LEGACY_NO_CUBRE_DOCUMENTO_COMPLETO"],
        }

    errors: list[str] = []
    try:
        payload, raw = parse_and_validate_snapshot(
            signature.canonical_payload, signature.payload_hash
        )
        snapshot_ok = True
    except CanonicalPayloadError as exc:
        payload, raw, snapshot_ok = {}, b"", False
        errors.append(str(exc))

    document_ok = snapshot_ok and all(
        (
            payload.get("codigo_formato") == signature.codigo_formato,
            str(payload.get("pt_num")) == str(signature.pt_num),
            str(payload.get("expediente")) == str(signature.expediente),
            int(payload.get("evolution_slot", -1)) == int(signature.evolution_slot or 0),
            str(payload.get("version_documento")) == str(signature.document_version),
            payload.get("tipo_documento") == signature.tipo_documento,
            payload.get("schema_version") == signature.signature_schema_version,
        )
    )
    if snapshot_ok and not document_ok:
        errors.append("Los metadatos del documento no coinciden con el snapshot firmado")

    signer = payload.get("firmante") or {}
    identity_ok = snapshot_ok and all(
        (
            signer.get("medico_id") == signature.medico_id,
            signer.get("nombre") == signature.nombre_medico,
            signer.get("cedula") == signature.cedula_profesional,
            payload.get("key_id") == signature.key_id,
        )
    )
    if snapshot_ok and not identity_ok:
        errors.append("La identidad o key_id no coincide con el snapshot firmado")

    import crypto_fea
    import models
    import tsa_client

    medico = db.query(models.Medico).filter(models.Medico.id == signature.medico_id).first()
    ecdsa_ok = snapshot_ok and crypto_fea.verificar_firma(
        medico,
        raw,
        signature.sello_digital,
        signature.fecha_hora_firma,
        db,
        key_id=signature.key_id,
    )
    if snapshot_ok and not ecdsa_ok:
        errors.append("La firma ECDSA no verifica con la key_id registrada")

    pdf_ok = verify_pdf_hash(payload, pdf_bytes) if snapshot_ok else False
    if pdf_ok is False and (payload.get("pdf") or {}).get("sha256"):
        errors.append("El PDF oficial no está disponible o su SHA-256 no coincide")

    if getattr(signature, "tsa_status", None) == tsa_client.TSA_VERIFICADO:
        tsa_result = tsa_client.verify_timestamp(
            signature.tsa_token,
            signature.payload_hash,
            expected_nonce=signature.tsa_nonce,
        )
    else:
        tsa_result = {
            "status": getattr(signature, "tsa_status", tsa_client.SIN_TSA),
            "verificado": False,
        }

    complete = bool(snapshot_ok and document_ok and identity_ok and ecdsa_ok and pdf_ok is not False)
    return {
        "classification": SCHEMA_VERSION,
        "complete": complete,
        "snapshot": snapshot_ok,
        "ecdsa": bool(ecdsa_ok),
        "identity": bool(identity_ok and ecdsa_ok),
        "document_binding": bool(document_ok and ecdsa_ok),
        "pdf": pdf_ok,
        "tsa": tsa_result,
        "errors": errors,
    }


def compare_current_document(db, signature) -> Optional[bool]:
    """Return whether the current operational record is the signed version.

    ``None`` deliberately means that the current source could not be loaded; it
    must never be presented as confirmation that the signed snapshot is current.
    """
    try:
        payload, _ = parse_and_validate_snapshot(
            signature.canonical_payload, signature.payload_hash
        )
        document, _ = load_authoritative_document(
            db,
            pt_num=signature.pt_num,
            codigo_formato=signature.codigo_formato,
            evolution_slot=int(signature.evolution_slot or 0),
            requested_type=signature.tipo_documento,
        )
    except Exception:
        return None
    return all(
        (
            _clinical_content_for_comparison(
                document.source_identifier, document.contenido_clinico,
            ) == _clinical_content_for_comparison(
                document.source_identifier, payload.get("contenido_clinico") or {},
            ),
            str(document.version_documento) == str(payload.get("version_documento")),
            str(document.source_identifier) == str(payload.get("source_identifier")),
            document.tipo_documento == payload.get("tipo_documento"),
        )
    )


def _catalog_name(db, codigo_formato: str, requested_type: Optional[str]) -> str:
    try:
        import models

        row = db.query(models.CatalogoFormato).filter(
            models.CatalogoFormato.codigo == codigo_formato,
            models.CatalogoFormato.activo == True,
        ).first()
        if row and row.nombre:
            return row.nombre
    except Exception:
        pass
    # The document code, not a browser-supplied label, is the fallback identity.
    return codigo_formato


def _patient_identity(db, pt_num: str) -> dict[str, Any]:
    try:
        import models

        variants = {str(pt_num), str(pt_num).removeprefix("PT-")}
        patient = db.query(models.Paciente).filter(
            models.Paciente.codigo_barras.in_(variants)
        ).first()
        if patient:
            return {
                "id": patient.id,
                "nombre_completo": patient.nombre_completo,
                "codigo_barras": patient.codigo_barras,
            }
    except Exception:
        pass
    return {"id": None, "nombre_completo": None, "codigo_barras": str(pt_num)}


def load_authoritative_document(
    db,
    *,
    pt_num: str,
    codigo_formato: str,
    evolution_slot: int,
    requested_type: Optional[str] = None,
    source_loader: Optional[Callable[[str, str, int], Mapping[str, Any]]] = None,
) -> tuple[ClinicalDocument, dict[str, Any]]:
    """Load the full current record from PostgreSQL metadata + Vertical TEST/ERP.

    ``source_loader`` exists for deterministic test vectors. Production callers
    omit it; no request body field can reach this parameter.
    """
    patient = _patient_identity(db, pt_num)
    tipo = _catalog_name(db, codigo_formato, requested_type)
    slot = int(evolution_slot or 0)

    if source_loader is not None:
        source = dict(source_loader(str(pt_num), codigo_formato, slot))
    else:
        source = _load_vertical_document(str(pt_num), codigo_formato, slot)
    if not source:
        raise ClinicalDocumentUnavailable("No se encontró contenido clínico autoritativo para firmar")

    version = source.pop("__version_documento__", None)
    source_id = source.pop("__source_identifier__", None)
    if version is None:
        version = source.get("ModifiedOn") or source.get("modified_on") or source.get("CreatedOn") or source.get("created_on") or 1
    if source_id is None:
        source_id = source.get("mrnum") or source.get("MRNum_NE_URG") or f"{codigo_formato}:{slot}"
    return (
        ClinicalDocument(
            tipo_documento=tipo,
            contenido_clinico=source,
            version_documento=str(_normalise(version)),
            source_identifier=str(source_id),
        ),
        patient,
    )


def _load_vertical_document(pt_num: str, codigo_formato: str, slot: int) -> dict[str, Any]:
    import kh_database
    from vertical_signer import resolve_vertical_controller_and_pk

    try:
        table, pk_column = resolve_vertical_controller_and_pk(codigo_formato)
    except ValueError as exc:
        raise ClinicalDocumentUnavailable(str(exc)) from exc
    if table == "MR_NE_URG":
        dashboard = kh_database.fetch_full_ehr_dashboard(pt_num)
        evolution = (dashboard.get("evoluciones") or {}).get(f"evolucion{slot or 1}")
        if not evolution:
            raise ClinicalDocumentUnavailable("La evolución solicitada no existe")
        # SignRecord mutates these fields on the same Vertical row, without
        # changing the medical note. Keep them outside new signed snapshots.
        source = _clinical_content_for_comparison(
            f"MR_NE_URG:{evolution.get('mrnum_ne_urg')}:{evolution.get('slot_in_row')}",
            evolution,
        )
        source["__version_documento__"] = source.get("date_iso") or source.get("created_on") or 1
        source["__source_identifier__"] = f"MR_NE_URG:{source.get('mrnum_ne_urg')}:{source.get('slot_in_row')}"
        return source

    conn = kh_database.get_kh_connection()
    if not conn:
        raise ClinicalDocumentUnavailable("Vertical EHR no está disponible")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?", (table,))
        columns = [row[0] for row in cursor.fetchall()]
        if not columns or pk_column not in columns:
            raise ClinicalDocumentUnavailable("El formato clínico no tiene un esquema resoluble")
        if slot > 0:
            cursor.execute(f"SELECT * FROM {table} WHERE PTNum = ? AND {pk_column} = ?", (pt_num, slot))
            row = cursor.fetchone()
        else:
            cursor.execute(f"SELECT TOP 1 * FROM {table} WHERE PTNum = ? ORDER BY {pk_column} DESC", (pt_num,))
            row = cursor.fetchone()
        if not row:
            raise ClinicalDocumentUnavailable("El documento clínico solicitado no existe")
        # SELECT * follows cursor.description, not an unordered metadata query.
        selected_columns = [item[0] for item in cursor.description]
        values = dict(zip(selected_columns, row))
        # SignRecord can update audit timestamps along with its native signature.
        # Version the clinical snapshot itself so this administrative transition
        # cannot invalidate the patient's preceding signature or a safe retry.
        administrative_fields = {"ESIGNATURE", "SIGNEDBY", "SIGNEDON", "MR_ST", "MODIFIEDON", "MODIFIEDBY"}
        values = {key: value for key, value in values.items() if key.upper() not in administrative_fields}
        values["__version_documento__"] = sha256_hex(canonical_json_bytes(values))
        values["__source_identifier__"] = f"{table}:{values.get(pk_column)}"
        return values
    finally:
        conn.close()

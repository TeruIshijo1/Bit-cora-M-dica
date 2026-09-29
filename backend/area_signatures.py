"""Shared, live work queue for explicitly permitted non-medical signatures.

Discover existing records in Vertical, rather than assigning copies to users.
Signature evidence remains in its original append-only history.
"""
import re

from fastapi import HTTPException

import clinical_signing
import kh_database
import models
from access_control import can_sign_format, has_module
from format_catalog import clinical_formats, canonical_format_code, signature_role_for_account_role, special_signature_role_label
from vertical_signer import resolve_vertical_controller_and_pk


def permitted_formats(user):
    if not has_module(user, "firmas_area"):
        raise HTTPException(403, "No tiene acceso a Firmas del área.")
    return [item for item in clinical_formats() if can_sign_format(user, item["codigo"])]


def require_document(user, code):
    item = next((item for item in permitted_formats(user)
                 if canonical_format_code(item["codigo"]) == canonical_format_code(code)), None)
    if not item:
        raise HTTPException(403, "No tiene permiso de firma para este formato.")
    return item


def fetch_candidates(code, before=0, limit=100):
    """Keyset page of existing documents; identifiers only come from catalog."""
    table, pk = resolve_vertical_controller_and_pk(code)
    if not re.fullmatch(r"MR_[A-Z0-9_]+", table) or not re.fullmatch(r"MRNum_[A-Za-z0-9_]+", pk):
        raise clinical_signing.ClinicalDocumentUnavailable("Formato sin origen válido")
    conn = kh_database.get_kh_connection()
    if not conn:
        raise clinical_signing.ClinicalDocumentUnavailable("Vertical no está disponible")
    try:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT TOP (?) d.[{pk}], d.PTNum, p.FullName, d.CreatedOn
            FROM [{table}] d LEFT JOIN PT p ON p.PTNum = d.PTNum
            WHERE (? = 0 OR d.[{pk}] < ?) AND d.PTNum IS NOT NULL
            ORDER BY d.[{pk}] DESC
        """, (limit, before, before))
        return [{"slot": int(row[0]), "pt_num": str(row[1]),
                 "paciente": row[2] or f"PT-{row[1]}",
                 "creado": row[3].isoformat() if hasattr(row[3], "isoformat") else str(row[3] or "")}
                for row in cur.fetchall()]
    except Exception as exc:
        raise clinical_signing.ClinicalDocumentUnavailable("No se pudieron consultar los formatos del área") from exc
    finally:
        conn.close()


def signature_rows(db, pt_num, code, role, slot=None):
    clean = str(pt_num).removeprefix("PT-")
    query = db.query(models.FirmaDocumentoClinico).filter(
        models.FirmaDocumentoClinico.pt_num.in_((clean, f"PT-{clean}")),
        models.FirmaDocumentoClinico.rol_firmante == role,
    )
    if slot is not None:
        query = query.filter(models.FirmaDocumentoClinico.evolution_slot.in_((0, slot)))
    return [row for row in query.order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()
            if canonical_format_code(row.codigo_formato) == canonical_format_code(code)]


def signature_history(db, rows, document):
    history = []
    for row in rows:
        # Older clients used slot=0. Bind history to the saved source row, not
        # the latest document of the patient and not another repeated consent.
        try:
            import json
            source = json.loads(row.canonical_payload or "{}").get("source_identifier")
        except (ValueError, TypeError):
            source = None
        if source != document.source_identifier:
            continue
        history.append({
            "id": row.id, "usuario_firmante_id": row.usuario_firmante_id,
            "firmante": row.nombre_medico, "fecha": row.fecha_hora_firma.isoformat(),
            "vigente": row.estado == "ACTIVA" and clinical_signing.evidence_matches_current(db, row, document),
        })
    return history


def queue(db, user, state="pendientes", cursor="", limit=25):
    formats = permitted_formats(user)
    role = signature_role_for_account_role(user.rol)
    try:
        index, before = map(int, cursor.split(":")) if cursor else (0, 0)
        if index < 0 or index > len(formats) or before < 0:
            raise ValueError()
    except ValueError as exc:
        raise HTTPException(422, "Página inválida. Actualice la bandeja.") from exc
    items, scanned = [], 0
    # A bounded scan can end with an empty page and a continuation. The client
    # keeps that explicit instead of incorrectly claiming there are no tasks.
    while index < len(formats) and len(items) < limit and scanned < 200:
        item = formats[index]
        candidates = fetch_candidates(item["codigo"], before, min(100, 200 - scanned))
        if not candidates:
            index, before = index + 1, 0
            continue
        for candidate in candidates:
            before = candidate["slot"]
            scanned += 1
            rows = signature_rows(db, candidate["pt_num"], item["codigo"], role, candidate["slot"])
            history = []
            if rows:
                document, _ = clinical_signing.load_authoritative_document(
                    db, pt_num=candidate["pt_num"], codigo_formato=item["codigo"], evolution_slot=candidate["slot"])
                history = signature_history(db, rows, document)
            current = next((row for row in history if row["vigente"]), None)
            if (state == "pendientes" and not current) or (state == "historial" and history):
                items.append(dict(candidate, codigo_formato=item["codigo"], titulo=item["nombre"],
                                  rol_firmante=role, firma=current, historial=history))
            if len(items) >= limit or scanned >= 200:
                break
    return {"items": items, "next_cursor": f"{index}:{before}" if index < len(formats) else None,
            "area": special_signature_role_label(role), "rol_firmante": role}


def document_detail(db, user, pt_num, code, slot):
    item = require_document(user, code)
    document, patient = clinical_signing.load_authoritative_document(
        db, pt_num=pt_num, codigo_formato=item["codigo"], evolution_slot=slot)
    role = signature_role_for_account_role(user.rol)
    history = signature_history(db, signature_rows(db, pt_num, item["codigo"], role, slot), document)
    # Full clinical content is reviewed in the official PDF. This compact
    # preview excludes database IDs, audit data and internal signature bytes.
    excluded = {"PTNUM", "PTID", "CONTROLLERNAME", "CONTROLLERKEY", "CONTROLLERID", "CREATEDBY", "CREATEDON", "MODIFIEDBY", "MODIFIEDON", "SIGNEDBY", "SIGNEDON", "ESIGNATURE", "MR_ST"}
    labels = {"N_MEDICO": "Médico tratante", "EXPEDIENTE": "Expediente clínico",
              "ACEPTO_Y_AUTORIZO_TRANSFUSION_DE": "Hemocomponentes autorizados",
              "TESTIGO_1": "Testigo 1", "TESTIGO_2": "Testigo 2"}
    fields = [{"label": labels.get(key.upper(), key.replace("_", " ").capitalize()), "value": str(value)}
              for key, value in document.contenido_clinico.items()
              if key.upper() not in excluded and not key.upper().startswith(("MRNUM", "MRID", "MR_"))
              and value is not None and str(value).strip() and not isinstance(value, bytes)]
    return {"pt_num": pt_num, "paciente": patient.get("nombre_completo"), "slot": slot,
            "codigo_formato": item["codigo"], "titulo": item["nombre"], "campos": fields,
            "rol_firmante": role, "area": special_signature_role_label(role),
            "firma": next((row for row in history if row["vigente"]), None), "historial": history,
            "pdf_url": item["url_pdf"].replace("{pt_num}", str(pt_num)) + f"?mrnum={slot}&area_preview=1"}

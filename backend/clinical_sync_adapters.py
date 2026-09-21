"""Allowlisted SQL Server/Vertical dispatch for durable clinical retries."""

from __future__ import annotations

import datetime as dt
import re
import uuid
from typing import Any, Callable

import clinical_sync
import kh_database
import vertical_signer


_KH_MUTATORS: dict[str, Callable[..., Any]] = {
    "save_or_update_nota_urgencias": kh_database.save_or_update_nota_urgencias,
    "save_or_update_nota_hospitalizacion": kh_database.save_or_update_nota_hospitalizacion,
    "save_or_update_consentimiento_32_01": kh_database.save_or_update_consentimiento_32_01,
    "save_patient_vitals_ptvs": kh_database.save_patient_vitals_ptvs,
    "save_patient_allergy_ptal": kh_database.save_patient_allergy_ptal,
    "inactivate_patient_allergy_ptal": kh_database.inactivate_patient_allergy_ptal,
    "update_patient_allergies_text": kh_database.update_patient_allergies_text,
    "save_or_update_consentimiento_eed": kh_database.save_or_update_consentimiento_eed,
    "save_or_update_consentimiento_25": kh_database.save_or_update_consentimiento_25,
    "save_or_update_consentimiento_34_01": kh_database.save_or_update_consentimiento_34_01,
    "save_or_update_consentimiento_12": kh_database.save_or_update_consentimiento_12,
    "save_or_update_consentimiento_04": kh_database.save_or_update_consentimiento_04,
    "save_or_update_consentimiento_15": kh_database.save_or_update_consentimiento_15,
    "save_or_update_consentimiento_02": kh_database.save_or_update_consentimiento_02,
    "save_or_update_consentimiento_08": kh_database.save_or_update_consentimiento_08,
    "save_or_update_consentimiento_43": kh_database.save_or_update_consentimiento_43,
    "save_or_update_consentimiento_11": kh_database.save_or_update_consentimiento_11,
    "save_or_update_consentimiento_19": kh_database.save_or_update_consentimiento_19,
    "save_or_update_egreso_voluntario_15": kh_database.save_or_update_egreso_voluntario_15,
    "save_or_update_consentimiento_06": kh_database.save_or_update_consentimiento_06,
    "save_or_update_consentimiento_07": kh_database.save_or_update_consentimiento_07,
    "sync_contact_to_ptcn": kh_database.sync_contact_to_ptcn,
    "delete_contact_from_ptcn": kh_database.delete_contact_from_ptcn,
}


# Structural coverage contract: every SQL Server clinical mutator must have a
# declared durable/idempotent strategy. Tests compare this registry with the
# allowlist and the decorated mutator inventory in kh_database.
MUTATOR_STRATEGIES: dict[str, str] = {
    **{name: "GUID_OR_REPEATABLE_UPDATE" for name in _KH_MUTATORS},
    "save_or_update_nota_urgencias": "GUID_INSERT_OR_MANUAL_SLOT_RECONCILIATION",
    "save_patient_medication_ptdg": "DETERMINISTIC_GUID",
    "discontinue_patient_medication_ptdg": "REPEATABLE_UPDATE",
    "save_patient_diet_mr_sol_diet": "DETERMINISTIC_GUID",
    "PATIENT_DISCHARGE": "REPEATABLE_UPDATE",
    "PATIENT_READMISSION": "REPEATABLE_UPDATE",
    "VERTICAL_SIGN": "OPERATION_ID",
    "UNIVERSAL_FORMAT_CREATE": "DISCOVERED_GUID_OR_MANUAL_BLOCK",
    "UNIVERSAL_FORMAT_UPDATE": "PRIMARY_KEY_REPEATABLE_UPDATE",
}


def _safe_identifier(value: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise kh_database.KHPermanentMutationError("Identificador SQL Server no permitido")
    return value


def _universal_columns(cursor, table_name: str) -> tuple[list[str], dict[str, str]]:
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?",
        (table_name,),
    )
    columns = [str(row[0]) for row in cursor.fetchall()]
    return columns, {column.upper(): column for column in columns}


def _universal_format_create(
    patient_ref: str,
    payload: dict[str, Any],
    operation_id: str,
) -> dict[str, Any]:
    controller, pk_column = vertical_signer.resolve_vertical_controller_and_pk(payload["codigo"])
    controller = _safe_identifier(controller)
    pk_column = _safe_identifier(pk_column)
    conn = kh_database.get_kh_connection()
    if not conn:
        raise kh_database.KHRetryableMutationError("SQL Server no disponible")
    try:
        cursor = conn.cursor()
        columns, columns_upper = _universal_columns(cursor, controller)
        expected_guid = f"{controller}ID".upper()
        guid_column = columns_upper.get(expected_guid)
        if not guid_column:
            raise clinical_sync.ManualReconciliationRequired(
                f"{controller} no expone GUID seguro; INSERT universal bloqueado"
            )
        operation_guid = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"clinical-sync:{operation_id}:universal:{controller}")
        ).upper()
        cursor.execute(
            f"SELECT TOP 1 {pk_column} FROM {controller} WHERE {guid_column} = ?",
            (operation_guid,),
        )
        existing = cursor.fetchone()
        if existing:
            return {
                "status": "success",
                "mrnum": int(existing[0]),
                "controller": controller,
                "idempotent": True,
            }

        cursor.execute(
            "SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?",
            (patient_ref,),
        )
        metadata = cursor.fetchone()
        pt_id = str(metadata[3]) if metadata and metadata[3] else str(uuid.uuid4()).upper()
        parent = str(metadata[0]) if metadata and metadata[0] else "PC"
        parent_key = str(metadata[1]) if metadata and metadata[1] else str(patient_ref)
        parent_id = str(metadata[2]) if metadata and metadata[2] else str(uuid.uuid4()).upper()
        doctor = payload.get("medico_tratante") or payload.get("n_medico") or "MÉDICO TRATANTE HES"
        now = dt.datetime.now()
        insert_columns = [
            "PTNum", "PTID", "ControllerName", "ControllerKey", "ControllerID",
            "MR_ST", "CreatedBy", "CreatedOn", "ModifiedBy", "ModifiedOn", guid_column,
        ]
        insert_values: list[Any] = [
            int(patient_ref) if str(patient_ref).isdigit() else patient_ref,
            pt_id,
            parent,
            int(parent_key) if parent_key.isdigit() else parent_key,
            parent_id,
            "RG",
            doctor,
            now,
            doctor,
            now,
            operation_guid,
        ]

        candidate_values = [
            (["N_MEDICO", "NOMBRE_MEDICO", "MEDICO_TRATANTE", "MEDICO"], doctor),
            (["DIAGNOSTICO", "DIAGNOSTICOS", "DIAG_PREOP"], payload.get("diagnostico")),
            (["EXPEDIENTE"], str(patient_ref)),
            (["TESTIGO1", "TESTIGO_1", "N_TESTIGO1", "TESTIGO1_NOMBRE", "TESTIGO"], payload.get("testigo1") or payload.get("testigo_1")),
            (["TESTIGO2", "TESTIGO_2", "N_TESTIGO2", "TESTIGO2_NOMBRE"], payload.get("testigo2") or payload.get("testigo_2")),
            (["PARIENTE", "REPRESENTANTE_LEGAL", "N_REPLEGAL", "TUTOR", "NOMBRE_TUTOR", "FAMILIAR", "RESPONSABLE", "DECLARANTE"], payload.get("tutor") or payload.get("pariente") or payload.get("representante_legal")),
        ]
        for candidates, value in candidate_values:
            if value in (None, ""):
                continue
            for candidate in candidates:
                actual = columns_upper.get(candidate)
                if actual and actual not in insert_columns:
                    insert_columns.append(actual)
                    insert_values.append(value)
                    break

        placeholders = ", ".join("?" for _ in insert_values)
        cursor.execute(
            f"INSERT INTO {controller} ({', '.join(insert_columns)}) VALUES ({placeholders})",
            tuple(insert_values),
        )
        cursor.execute("SELECT @@IDENTITY")
        row = cursor.fetchone()
        new_id = int(row[0]) if row and row[0] is not None else None
        conn.commit()
        if new_id is None:
            raise kh_database.KHRetryableMutationError("SQL Server no confirmó el identificador creado")
        return {"status": "success", "mrnum": new_id, "controller": controller, "pk": pk_column}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _universal_format_update(patient_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
    controller, pk_column = vertical_signer.resolve_vertical_controller_and_pk(payload["codigo"])
    controller = _safe_identifier(controller)
    pk_column = _safe_identifier(pk_column)
    record_id = int(payload["mrnum"])
    conn = kh_database.get_kh_connection()
    if not conn:
        raise kh_database.KHRetryableMutationError("SQL Server no disponible")
    try:
        cursor = conn.cursor()
        _columns, columns_upper = _universal_columns(cursor, controller)
        clauses: list[str] = []
        values: list[Any] = []
        doctor = payload.get("medico_tratante") or payload.get("n_medico") or ""
        candidate_values = [
            (["MODIFIEDBY"], doctor or "BITACORA_HES"),
            (["MODIFIEDON"], dt.datetime.now()),
            (["N_MEDICO", "NOMBRE_MEDICO", "MEDICO_TRATANTE", "MEDICO"], doctor),
            (["DIAGNOSTICO", "DIAGNOSTICOS", "DIAG_PREOP"], payload.get("diagnostico")),
            (["OBSERVACIONES", "RESUMEN_CLINICO", "PLAN", "TRATAMIENTO", "DESCRIPCION"], payload.get("observaciones") or payload.get("contenido") or payload.get("resumen")),
            (["TESTIGO1", "TESTIGO_1", "N_TESTIGO1", "TESTIGO1_NOMBRE", "TESTIGO"], payload.get("testigo1") or payload.get("testigo_1")),
            (["TESTIGO2", "TESTIGO_2", "N_TESTIGO2", "TESTIGO2_NOMBRE"], payload.get("testigo2") or payload.get("testigo_2")),
            (["PARIENTE", "REPRESENTANTE_LEGAL", "N_REPLEGAL", "TUTOR", "NOMBRE_TUTOR", "FAMILIAR", "RESPONSABLE", "DECLARANTE"], payload.get("tutor") or payload.get("pariente") or payload.get("representante_legal")),
        ]
        used: set[str] = set()
        for candidates, value in candidate_values:
            if value in (None, ""):
                continue
            for candidate in candidates:
                actual = columns_upper.get(candidate)
                if actual and actual not in used:
                    clauses.append(f"{actual} = ?")
                    values.append(value)
                    used.add(actual)
                    break
        where = f"{pk_column} = ?"
        values.append(record_id)
        clean_patient = re.sub(r"[^0-9]", "", str(patient_ref))
        if columns_upper.get("PTNUM") and clean_patient:
            where += f" AND {columns_upper['PTNUM']} = ?"
            values.append(int(clean_patient))
        if clauses:
            cursor.execute(
                f"UPDATE {controller} SET {', '.join(clauses)} WHERE {where}",
                tuple(values),
            )
        cursor.execute(f"SELECT TOP 1 {pk_column} FROM {controller} WHERE {where}", tuple(values[-2:] if "PTNUM" in columns_upper and clean_patient else values[-1:]))
        if not cursor.fetchone():
            raise kh_database.KHPermanentMutationError("Registro universal no encontrado")
        conn.commit()
        return {"status": "success", "mrnum": record_id, "controller": controller}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _patient_discharge(patient_ref: str) -> dict[str, Any]:
    conn = kh_database.get_kh_connection()
    if not conn:
        raise kh_database.KHRetryableMutationError("SQL Server no disponible")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE PC
               SET MedicalDischarge = 'MEJ', MedicalDischargeDate = COALESCE(MedicalDischargeDate, GETDATE()),
                   PC_ST = 'PD', ModifiedOn = GETDATE()
             WHERE PTNum = ? AND (MedicalDischargeDate IS NULL OR PC_ST = 'OP')
            """,
            (int(patient_ref),),
        )
        conn.commit()
        return {"success": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _patient_readmission(patient_ref: str) -> dict[str, Any]:
    conn = kh_database.get_kh_connection()
    if not conn:
        raise kh_database.KHRetryableMutationError("SQL Server no disponible")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE PC
               SET MedicalDischarge = NULL, MedicalDischargeDate = NULL, ExitDate = NULL,
                   ClosedOn = NULL, PC_ST = 'OP', ModifiedOn = GETDATE()
             WHERE PTNum = ? AND PCNum = (
                 SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY EntryDate DESC, PCNum DESC
             )
            """,
            (int(patient_ref), int(patient_ref)),
        )
        conn.commit()
        return {"success": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _resolve_vertical_mr(payload: dict[str, Any], patient_ref: str) -> int:
    if payload.get("mrnum") is not None:
        return int(payload["mrnum"])
    controller_name, pk_column = vertical_signer.resolve_vertical_controller_and_pk(
        payload["codigo_formato"]
    )
    target_slot = int(payload.get("target_slot") or 0)
    if controller_name != "MR_NE_URG" and target_slot > 0:
        return target_slot
    raise clinical_sync.ManualReconciliationRequired(
        "La operación histórica no identifica la fila exacta; no se sustituye por el último documento del paciente"
    )


def dispatcher(operation) -> Callable[[], Any]:
    """Return an allowlisted idempotent callback for a persisted operation."""
    payload = operation.payload or {}
    operation_id = str(operation.operation_id)

    if operation.operation_type == "MEDICATION_PRESCRIBE":
        return lambda: kh_database.save_patient_medication_ptdg(
            operation.patient_ref,
            payload["medication"],
            operation_id=operation_id,
        )
    if operation.operation_type == "MEDICATION_DISCONTINUE":
        return lambda: kh_database.discontinue_patient_medication_ptdg(
            operation.patient_ref,
            int(payload["ptdg_num"]),
            payload.get("reason", ""),
            operation_id=operation_id,
        )
    if operation.operation_type == "DIET_PRESCRIBE":
        return lambda: kh_database.save_patient_diet_mr_sol_diet(
            operation.patient_ref,
            payload["diet"],
            operation_id=operation_id,
        )
    if operation.operation_type == "PATIENT_DISCHARGE":
        return lambda: _patient_discharge(operation.patient_ref)
    if operation.operation_type == "PATIENT_READMISSION":
        return lambda: _patient_readmission(operation.patient_ref)
    if operation.operation_type == "VERTICAL_SIGN":
        def sign_exact_document():
            if payload.get("document_digest"):
                import clinical_signing
                from database import SessionLocal
                with SessionLocal() as db:
                    document, _ = clinical_signing.load_authoritative_document(
                        db, pt_num=operation.patient_ref, codigo_formato=payload["codigo_formato"],
                        evolution_slot=int(payload.get("target_slot") or 0),
                    )
                if clinical_signing.document_digest(document) != payload["document_digest"]:
                    raise clinical_sync.ManualReconciliationRequired("El documento cambió después de la firma; no se firma automáticamente otra versión en Vertical")
            return vertical_signer.sign_in_vertical_api(
                controller_name=payload["controller_name"],
                mrnum=_resolve_vertical_mr(payload, operation.patient_ref),
                pt_num=operation.patient_ref,
                doctor_name=payload["doctor_name"],
                doctor_cedula=payload.get("doctor_cedula"),
                operation_id=operation_id,
            )
        return sign_exact_document
    if operation.operation_type == "UNIVERSAL_FORMAT_CREATE":
        return lambda: _universal_format_create(
            operation.patient_ref,
            payload["document"],
            operation_id,
        )
    if operation.operation_type == "UNIVERSAL_FORMAT_UPDATE":
        return lambda: _universal_format_update(
            operation.patient_ref,
            payload["document"],
        )
    if operation.operation_type == "KH_MUTATION":
        adapter_name = payload.get("adapter")
        adapter = _KH_MUTATORS.get(adapter_name)
        if adapter is None:
            raise ValueError("Adaptador de reconciliación no permitido")
        args = payload.get("args", [])
        kwargs = payload.get("kwargs", {})
        if adapter_name == "save_or_update_nota_urgencias":
            def deliver_urgency_note():
                try:
                    return adapter(*args, **kwargs, operation_id=operation_id)
                except Exception as exc:
                    if getattr(exc, "retryable", False) or isinstance(
                        exc, (TimeoutError, ConnectionError)
                    ):
                        raise clinical_sync.ManualReconciliationRequired(
                            "Resultado ambiguo en slot MR_NE_URG; requiere verificación controlada"
                        ) from exc
                    raise

            return deliver_urgency_note
        return lambda: adapter(*args, **kwargs, operation_id=operation_id)
    raise ValueError(f"Tipo de operación no reconciliable: {operation.operation_type}")

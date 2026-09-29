import os
import sys
import json
import re
import datetime
import hashlib
import uuid
from typing import Optional, Dict, Any, Tuple, List
import pypdf

# Import engines
try:
    import pdf_generator
    import pdf_engine_v2
    import pdf_engine_24
    import pdf_engine_02
    import pdf_engine_04
    import pdf_engine_06
    import pdf_engine_07
    import pdf_engine_08
    import pdf_engine_09
    import pdf_engine_11
    import pdf_engine_12
    import pdf_engine_15
    import pdf_engine_15_ev
    import pdf_engine_19
    import pdf_engine_16
    import pdf_engine_25
    import pdf_engine_32_01
    import pdf_engine_34_01
    import pdf_engine_eed
    import pdf_engine_43
    import pdf_engine_expediente
    import kh_database
except ImportError:
    from backend import pdf_generator
    from backend import pdf_engine_v2
    from backend import pdf_engine_24
    from backend import pdf_engine_02
    from backend import pdf_engine_04
    from backend import pdf_engine_06
    from backend import pdf_engine_07
    from backend import pdf_engine_08
    from backend import pdf_engine_09
    from backend import pdf_engine_11
    from backend import pdf_engine_12
    from backend import pdf_engine_15
    from backend import pdf_engine_15_ev
    from backend import pdf_engine_19
    from backend import pdf_engine_16
    from backend import pdf_engine_25
    from backend import pdf_engine_32_01
    from backend import pdf_engine_34_01
    from backend import pdf_engine_eed
    from backend import pdf_engine_43
    from backend import pdf_engine_expediente
    from backend import kh_database

try:
    from pdf_qr_context import current_qr_context
except ImportError:
    from backend.pdf_qr_context import current_qr_context

import glob

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
STATIC_PDFS_DIR = os.path.join(BACKEND_DIR, "static", "pdfs")
CACHE_PDFS_DIR = os.path.join(STATIC_PDFS_DIR, "cache_expedientes")
SCRATCH_DIR = os.path.join(PROJECT_ROOT, "scratch")

os.makedirs(STATIC_PDFS_DIR, exist_ok=True)
os.makedirs(CACHE_PDFS_DIR, exist_ok=True)
os.makedirs(SCRATCH_DIR, exist_ok=True)


class ExpedienteSignatureReconciliationRequired(ValueError):
    """El expediente requiere revisar una versión firmada antes de compilarse."""

    def __init__(self, report: dict):
        self.report = report or {}
        unique_codes = []
        for item in self.report.get("bloqueos", []):
            code = str(item.get("codigo") or "").strip()
            if code and code not in unique_codes:
                unique_codes.append(code)
        codes = ", ".join(unique_codes) or "formato clínico"
        super().__init__(
            "No se generó el expediente porque existe evidencia de firma que no "
            "pudo vincularse de forma segura a la versión actual "
            f"({codes}). ¿Desea revisar y refirmar ahora esos formatos? "
            "Las firmas anteriores permanecen conservadas en el historial."
        )


def get_pdf_page_count(pdf_path: str) -> int:
    """Retorna el número de páginas de un PDF."""
    try:
        if not os.path.exists(pdf_path):
            return 0
        reader = pypdf.PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        print(f"Error reading page count for {pdf_path}: {e}")
        return 1


def _format_code_candidates(codigo_formato: str) -> list[str]:
    """Acepta códigos históricos cortos y códigos institucionales completos."""
    raw = str(codigo_formato or "").strip()
    if not raw:
        return []
    candidates = {raw}
    short = raw
    was_full_code = False
    matched_prefix = None
    for prefix in ("HE-DIRMED-CONSUL-PLT-", "HE-DIRMED-SINPRO-PLT-"):
        if short.upper().startswith(prefix):
            short = short[len(prefix):]
            was_full_code = True
            matched_prefix = prefix
            break
    candidates.add(short)
    if "/" in short:
        short_base = short.split("/", 1)[0]
        candidates.add(short_base)
        # Vertical and PostgreSQL have used both ``34`` and ``34/01`` for
        # the same institutional form. Keep the complete alias too.
        if matched_prefix:
            candidates.add(f"{matched_prefix}{short_base}")
    if short == "15" and "SINPRO" in raw.upper():
        candidates.add("PLT-EV-15")
        if was_full_code:
            candidates.discard("15")
    if not was_full_code:
        for area in ("CONSUL", "SINPRO"):
            candidates.add(f"HE-DIRMED-{area}-PLT-{short}")
            if short in {"32", "34", "87"}:
                candidates.add(f"HE-DIRMED-{area}-PLT-{short}/01")
    elif matched_prefix and short in {"32", "34", "87"}:
        candidates.add(f"{matched_prefix}{short}/01")
    return sorted(candidates)


def get_latest_format_slot(db_session, clean_pt: str, codigo_formato: str, default: int = 0) -> int:
    """Devuelve la ranura vigente más reciente de un formato clínico."""
    if not db_session:
        return default
    try:
        try:
            import models
        except ImportError:
            from backend import models
        candidates = _format_code_candidates(codigo_formato)
        filters = [
            models.FirmaDocumentoClinico.codigo_formato.in_(candidates),
            models.FirmaDocumentoClinico.estado == "ACTIVA",
        ]
        firma = db_session.query(models.FirmaDocumentoClinico).filter(
            (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) |
            (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}"),
            *filters,
        ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
        if firma and firma.evolution_slot is not None:
            return int(firma.evolution_slot)

        historico = db_session.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(clean_pt)) |
            (models.HistoricoNotaClinica.pt_num == f"PT-{clean_pt}"),
            models.HistoricoNotaClinica.codigo_formato.in_(candidates),
        ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
        if historico and historico.evolution_slot is not None:
            return int(historico.evolution_slot)
    except Exception as exc:
        print(f"Nota: no se pudo resolver la ranura de {codigo_formato}: {exc}")
    return default


def fetch_current_format_record(db_session, clean_pt: str, codigo_formato: str, fetcher=None) -> tuple[dict, int]:
    """Read the latest clinical record first; its identity chooses the signature.

    Choosing the latest *signed* slot instead hides newer unsigned versions and
    can attach the evidence to a different form than the one being printed.
    """
    slot = get_latest_format_slot(db_session, clean_pt, codigo_formato, default=0)
    if not fetcher:
        return {}, slot
    try:
        record = fetcher(clean_pt) or {}
        if not isinstance(record, dict):
            return {}, slot
        if record.get("error"):
            return record, slot
        return record, int(record.get("mrnum") or slot or 0)
    except Exception as exc:
        # Do not silently fall back to a different version. The caller can
        # still render the immutable local snapshot, but it will know that the
        # live source could not be refreshed.
        return {"error": f"No se pudo leer la versión actual de {codigo_formato}: {exc}"}, slot


def _short_signature_evidence(value: Any, limit: int = 28) -> str | None:
    """Identificador corto para trazabilidad impresa; nunca expone el sello completo."""
    if value in (None, ""):
        return None
    text = str(value).strip()
    return (text[:limit] + "…") if len(text) > limit else text


def _signature_history_entry(signature, status: str) -> dict:
    """Proyección segura de una evidencia para conservarla en el expediente."""
    name = re.sub(r"\s*\([^)]*\)", "", str(signature.nombre_medico or "")).strip()
    fecha = signature.fecha_hora_firma.strftime("%d/%m/%Y %H:%M:%S") if signature.fecha_hora_firma else ""
    return {
        "id": signature.id,
        "rol": str(signature.rol_firmante or "MEDICO").upper(),
        "nombre": name,
        "fecha": fecha,
        "esquema": str(signature.signature_schema_version or "LEGACY_V1"),
        "version_documento": str(signature.document_version or "") or None,
        "estado_evidencia": status,
        "sello_corto": _short_signature_evidence(signature.sello_digital or signature.hash_sha256),
    }


def obtener_firmas_completas_documento(db_session, pt_num: str, codigo_formato: str, evolution_slot: int = 0, paciente_capaz: bool = None) -> dict:
    """
    Recupera todas las firmas biométricas activas para un documento clínico:
    - Firma del Médico tratante
    - Firma del Paciente o Tutor / Representante Legal
    - Firma del Testigo 1
    - Firma del Testigo 2
    """
    if not db_session:
        return {}
    try:
        try:
            import models
        except ImportError:
            from backend import models
        try:
            import clinical_signing
        except ImportError:
            from backend import clinical_signing

        clean_pt = re.sub(r'[^0-9]', '', str(pt_num)) or str(pt_num)
        code_candidates = _format_code_candidates(codigo_formato)
        query = db_session.query(models.FirmaDocumentoClinico).filter(
            (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | 
            (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) | 
            (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}"),
            models.FirmaDocumentoClinico.codigo_formato.in_(code_candidates),
            models.FirmaDocumentoClinico.evolution_slot == int(evolution_slot or 0),
            models.FirmaDocumentoClinico.estado == "ACTIVA",
        )
        firmas = query.order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()
        # Los formatos capturados desde Vertical suelen conservar la ranura en
        # evolution_slot, mientras que los formatos generales usan 0. Si no
        # existe una firma general, tomar la última versión activa evita dejar
        # fuera un consentimiento firmado sólo por tener mrnum > 0.
        if not firmas and int(evolution_slot or 0) == 0:
            latest_signature = db_session.query(models.FirmaDocumentoClinico).filter(
                (models.FirmaDocumentoClinico.pt_num == str(pt_num)) |
                (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) |
                (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}"),
                models.FirmaDocumentoClinico.codigo_formato.in_(code_candidates),
                models.FirmaDocumentoClinico.estado == "ACTIVA",
            ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).first()
            if latest_signature:
                evolution_slot = int(latest_signature.evolution_slot or 0)
                firmas = db_session.query(models.FirmaDocumentoClinico).filter(
                    (models.FirmaDocumentoClinico.pt_num == str(pt_num)) |
                    (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) |
                    (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}"),
                    models.FirmaDocumentoClinico.codigo_formato.in_(code_candidates),
                    models.FirmaDocumentoClinico.evolution_slot == evolution_slot,
                    models.FirmaDocumentoClinico.estado == "ACTIVA",
                ).order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()
        raw_firmas = list(firmas)
        raw_firmas_count = len(raw_firmas)
        raw_firma_roles = sorted({str(f.rol_firmante or "MEDICO").upper() for f in raw_firmas})
        signature_verification_issue = None
        verified_firma_ids = set()
        if raw_firmas:
            try:
                import clinical_signing
            except ImportError:
                from backend import clinical_signing
            try:
                evidence_code = str(firmas[0].codigo_formato or codigo_formato)
                current_document, _ = clinical_signing.load_authoritative_document(
                    db_session, pt_num=str(pt_num), codigo_formato=evidence_code,
                    evolution_slot=int(evolution_slot or 0),
                )
                if paciente_capaz is None:
                    paciente_capaz = clinical_signing.explicit_patient_capacity(current_document)
                firmas = [
                    firma for firma in raw_firmas
                    if clinical_signing.evidence_matches_current(db_session, firma, current_document)
                ]
                verified_firma_ids = {firma.id for firma in firmas}
                if raw_firmas_count and not firmas:
                    signature_verification_issue = "FIRMA_NO_CORRESPONDE_VERSION_ACTUAL"
            except Exception:
                # Never silently turn an existing signature into an unsigned
                # PDF when the authoritative version cannot be loaded.
                signature_verification_issue = "NO_SE_PUDO_VERIFICAR_VERSION"
                firmas = []

        from format_catalog import special_signature_role_label
        required_special_roles = clinical_signing.special_signature_requirements(codigo_formato)
        res = {
            "sello_digital": None,
            "hash_sha256": None,
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
            "firmas_especiales_requeridas": required_special_roles,
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
                for role in required_special_roles
            },
            "_signature_records_found": raw_firmas_count,
            "_signature_records_verified": len(firmas),
            "_signature_roles_found": raw_firma_roles,
            "_signature_verification_issue": signature_verification_issue,
            # La evidencia no desaparece cuando ya no puede cubrir la versión
            # actual: queda visible como histórica y exige refirma, sin
            # promoverse a una firma vigente.
            "_signature_history": [
                _signature_history_entry(
                    firma,
                    "VIGENTE" if firma.id in verified_firma_ids else (
                        "HISTORICA_NO_VINCULADA" if signature_verification_issue else "NO_VERIFICADA"
                    ),
                )
                for firma in raw_firmas
                if firma.id not in verified_firma_ids
            ],
        }

        for f in firmas:
            rol = (f.rol_firmante or "MEDICO").upper()
            f_date = f.fecha_hora_firma.strftime("%d/%m/%Y %H:%M:%S") if f.fecha_hora_firma else ""
            clean_name = re.sub(r'\s*\([^)]*\)', '', f.nombre_medico or '').strip()

            firmante_obj = None
            if f.firmante_id:
                firmante_obj = db_session.query(models.BiometriaFirmanteEpisodio).filter(
                    models.BiometriaFirmanteEpisodio.id == f.firmante_id
                ).first()

            if rol == "MEDICO" and not res["sello_digital"]:
                res["sello_digital"] = f.sello_digital
                res["hash_sha256"] = f.hash_sha256
                res["fecha_hora_firma"] = f_date
                res["nombre_medico"] = f.nombre_medico
                res["cedula"] = f.cedula_profesional
            elif rol in ("PACIENTE", "REPRESENTANTE_LEGAL", "TUTOR", "FAMILIAR") and not res["sello_paciente"]:
                if paciente_capaz is False and rol == "PACIENTE":
                    continue
                res["sello_paciente"] = f.sello_digital
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
                res["fecha_testigo1"] = f_date
                res["firmante_testigo1"] = clean_name
                res["parentesco_testigo1"] = firmante_obj.parentesco if firmante_obj else "Testigo Presencial"
                res["domicilio_testigo1"] = firmante_obj.domicilio if firmante_obj and firmante_obj.domicilio else None
                res["identificacion_testigo1"] = firmante_obj.identificacion_oficial if firmante_obj and firmante_obj.identificacion_oficial else None
                res["firma_testigo1_biometrica"] = True
            elif rol == "TESTIGO_2" and not res["sello_testigo2"]:
                res["sello_testigo2"] = f.sello_digital
                res["fecha_testigo2"] = f_date
                res["firmante_testigo2"] = clean_name
                res["parentesco_testigo2"] = firmante_obj.parentesco if firmante_obj else "Testigo Presencial"
                res["domicilio_testigo2"] = firmante_obj.domicilio if firmante_obj and firmante_obj.domicilio else None
                res["identificacion_testigo2"] = firmante_obj.identificacion_oficial if firmante_obj and firmante_obj.identificacion_oficial else None
                res["firma_testigo2_biometrica"] = True
            elif rol in res["firmas_especiales"] and f.usuario_firmante_id:
                user = db_session.get(models.Usuario, f.usuario_firmante_id)
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
    except Exception as e:
        print(f"Error fetching signatures in pdf_service: {e}")
        return {
            "_signature_records_found": -1,
            "_signature_roles_found": [],
            "_signature_verification_issue": "NO_SE_PUDO_CONSULTAR_FIRMAS",
        }


def aplicar_metadata_firma_vertical_nativa(pt_data: dict, firma_data: dict, source_data: dict) -> None:
    """Keep Vertical's technical SignedBy separate from clinical doctor attribution.

    Native status is not an HES FEA seal; only a real local signature may fill
    ``sello_digital``/``hash_sha256`` in the PDF evidence block.
    """
    if not isinstance(source_data, dict) or not _source_has_native_signature(source_data):
        return
    firma_data["origen_firma"] = "VERTICAL_EHR"
    firma_data["firma_nativa_vertical"] = True
    firma_data["usuario_tecnico_vertical"] = source_data.get("signed_by") or source_data.get("created_by") or "Vertical EHR"
    firma_data["fecha_hora_firma_vertical"] = source_data.get("signed_on")
    firma_data["sello_nativo_vertical_corto"] = _short_signature_evidence(source_data.get("es_signature"))
    native_doctor = source_data.get("medico_tratante") or source_data.get("n_medico")
    if native_doctor:
        pt_data["medico_tratante"] = native_doctor
        firma_data["nombre_medico"] = native_doctor
    native_license = source_data.get("cedula") or source_data.get("cedula_profesional")
    if native_license:
        pt_data["cedula"] = native_license
        firma_data["cedula"] = native_license


def _source_has_native_signature(source_data: dict) -> bool:
    """Indica que Vertical confirmó una firma, aunque no exista FEA HES local."""
    if not isinstance(source_data, dict):
        return False
    return bool(
        source_data.get("firmado")
        or source_data.get("signed_by")
        or source_data.get("signed_on")
        or str(source_data.get("mr_st") or "").strip().upper() == "SG"
    )


def build_evolution_signature_map(db_session, pt_num: str, codigo_formato: str, evolutions: list[dict]) -> dict[int, dict]:
    """Bind each rendered evolution to evidence for its own authoritative slot.

    Urgencias signs the ordinal evolution within MR_NE_URG; hospitalización
    signs MRNum_24_HOJA_EVOL, which is *not* the displayed ordinal number.
    """
    is_hospitalization = codigo_formato.endswith("-24")
    result = {}
    for index, evolution in enumerate(evolutions or [], 1):
        if not isinstance(evolution, dict):
            continue
        try:
            display_num = int(evolution.get("num") or index)
            slot = int(
                evolution.get("mrnum_24_hoja_evol") if is_hospitalization
                else display_num
            )
        except (TypeError, ValueError):
            # Do not attach evidence to an evolution whose identity is unknown.
            continue
        if slot <= 0:
            continue
        signature = obtener_firmas_completas_documento(db_session, pt_num, codigo_formato, slot)
        aplicar_metadata_firma_vertical_nativa({}, signature, evolution)
        result[display_num] = signature
    return result


def aplicar_firmas_a_pt_data(pt_data: dict, sig_info: dict, firma_data: dict, paciente_capaz: bool = True, db: Any = None):
    """
    Apply only signers with evidence for this exact document to the PDF data.

    Registration in a patient's contact directory does not prove participation
    in this act. Unused witness places stay blank even if the form named someone.
    """
    sig_info = sig_info if isinstance(sig_info, dict) else {}
    source_has_native_signature = _source_has_native_signature(pt_data)
    if source_has_native_signature:
        # Never erase names/roles that belong to a document already marked as
        # signed by Vertical. They are not promoted to HES FEA; they remain
        # native evidence and are reported separately to the operator.
        firma_data.setdefault("origen_firma", "VERTICAL_EHR")
        firma_data.setdefault("firma_nativa_vertical", True)
        firma_data.setdefault("usuario_tecnico_vertical", pt_data.get("signed_by") or pt_data.get("created_by") or "Vertical EHR")
        firma_data.setdefault("fecha_hora_firma_vertical", pt_data.get("signed_on"))
        firma_data.setdefault("sello_nativo_vertical_corto", _short_signature_evidence(pt_data.get("es_signature")))
    for index in (1, 2):
        if sig_info.get(f"sello_testigo{index}"):
            continue
        if source_has_native_signature:
            continue
        for target in (pt_data, firma_data):
            if not isinstance(target, dict):
                continue
            for key in (
                f"testigo{index}", f"testigo_{index}", f"TESTIGO_{index}",
                f"testigo{index}_nombre",
                f"parentesco_testigo{index}", f"domicilio_testigo{index}",
                f"identificacion_testigo{index}", f"sello_testigo{index}",
            ):
                target[key] = ""
            if index == 1:
                for key in ("parentesco_testigo", "domicilio_testigo", "identificacion_testigo"):
                    target[key] = ""
            target[f"firma_testigo{index}_biometrica"] = False
    if sig_info and isinstance(sig_info, dict):
        if sig_info.get("sello_paciente"):
            if sig_info.get("rol_firmante_paciente") != "PACIENTE":
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
            pt_data["verifico_firma_biometrica"] = True
            pt_data["verifico_nombre"] = "PERSONAL DE SALUD / BANCO DE SANGRE"
            pt_data["nombre_personal_banco_sangre"] = sig_info.get("firmante_banco_sangre")
            pt_data["usuario_personal_banco_sangre"] = sig_info.get("usuario_firmante_banco_sangre")
            pt_data["fecha_firma_banco_sangre"] = sig_info.get("fecha_banco_sangre")
            pt_data["sello_banco_sangre"] = sig_info.get("sello_banco_sangre")
            pt_data["firma_banco_sangre_biometrica"] = True
        special_roles = sig_info.get("firmas_especiales_requeridas") or []
        if special_roles:
            pt_data["firmas_especiales_requeridas"] = list(special_roles)
            pt_data["firmas_especiales"] = {
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

    if isinstance(firma_data, dict):
        for k, v in pt_data.items():
            if k == "firma_data":
                continue
            if k not in firma_data or not firma_data[k]:
                firma_data[k] = v
        # Some legacy/specialized renderers read the signature payload from
        # ``pt_data`` instead of their explicit argument. Keep one canonical
        # reference so every renderer receives the same verified evidence and
        # cannot silently fall back to a name-only clinical snapshot.
        pt_data["firma_data"] = firma_data


def _build_signed_format_snapshot(
    db_session,
    clean_pt: str,
    patient_info: dict,
    codigo_formato: str,
    fetcher=None,
    defaults: dict | None = None,
):
    """Carga una versión exacta de un formato antes de regenerarlo en el compilado."""
    source_data, slot = fetch_current_format_record(db_session, clean_pt, codigo_formato, fetcher)
    slot = slot or 1

    pt_data = {
        "paciente_nombre": patient_info.get("name", ""),
        "nombre": patient_info.get("name", ""),
        "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
        "mrn": patient_info.get("mrn", f"PT-{clean_pt}"),
        "pt_num": str(clean_pt),
        "fecha_nacimiento": patient_info.get("dob", ""),
        "edad": patient_info.get("age", ""),
        "sexo": patient_info.get("gender", ""),
        "cama": patient_info.get("cama", ""),
        "servicio": patient_info.get("cama", ""),
        "diagnostico": patient_info.get("diagnostico", ""),
        "medico_tratante": patient_info.get("attending_doctor", ""),
        "cedula": patient_info.get("cedula", ""),
        "fecha_atencion": datetime.datetime.now().strftime("%d/%m/%Y"),
        "hora_atencion": datetime.datetime.now().strftime("%H:%M"),
        "fecha_ingreso": patient_info.get("fecha_ingreso", ""),
        "hora_ingreso": patient_info.get("hora_ingreso", ""),
        "paciente_capaz": True,
        "paciente_o_representante": patient_info.get("name", ""),
        "declarante": patient_info.get("name", ""),
        "mrnum": slot,
        "slot": slot,
    }
    if isinstance(defaults, dict):
        pt_data.update(defaults)
    if isinstance(source_data, dict) and "error" not in source_data:
        pt_data.update({key: value for key, value in source_data.items() if value not in (None, "")})

    historico = get_latest_historic_record(db_session, clean_pt, codigo_formato)
    if historico and historico.contenido_soap_json and (
        not source_data or source_data.get("error") or int(historico.evolution_slot or 0) == slot
    ):
        try:
            historico_data = json.loads(historico.contenido_soap_json)
            pt_data.update({
                key: value for key, value in historico_data.items()
                if key not in {"pt_num", "mrnum", "slot"} and value not in (None, "")
            })
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            print(f"Nota: no se pudo leer el snapshot de {codigo_formato}: {exc}")

    paciente_capaz = pt_data.get("paciente_capaz", True)
    if isinstance(paciente_capaz, str):
        paciente_capaz = paciente_capaz.lower() in ("true", "1", "si", "yes")
    else:
        paciente_capaz = bool(paciente_capaz)
    pt_data["paciente_capaz"] = paciente_capaz
    signature_data = obtener_firmas_completas_documento(
        db_session, clean_pt, codigo_formato, slot, paciente_capaz=paciente_capaz
    )
    firma_data = dict(signature_data or {})
    aplicar_firmas_a_pt_data(pt_data, signature_data, firma_data, paciente_capaz, db=db_session)
    if signature_data.get("nombre_medico"):
        pt_data["medico_tratante"] = signature_data["nombre_medico"]
    if signature_data.get("cedula"):
        pt_data["cedula"] = signature_data["cedula"]

    has_evidence = bool(
        historico or
        signature_data.get("sello_digital") or
        signature_data.get("sello_paciente") or
        (isinstance(source_data, dict) and "error" not in source_data and source_data)
    )
    return pt_data, firma_data, slot, has_evidence


def _format_codes_overlap(left: str, right: str) -> bool:
    """Compara códigos institucionales y sus alias históricos sin mezclar formatos."""
    left_candidates = set(_format_code_candidates(left))
    right_candidates = set(_format_code_candidates(right))
    return bool(left_candidates.intersection(right_candidates))


def _registered_patient_format_codes(db_session, clean_pt: str, dashboard_data: dict) -> list[dict]:
    """Devuelve sólo formatos que tienen un registro real para el paciente.

    ``catalogo_formatos`` es el catálogo de qué puede capturarse; no significa
    que el formato pertenezca al paciente. La pertenencia se confirma leyendo
    la historia del controlador Vertical. También se consideran códigos que ya
    tienen evidencia HES o snapshots históricos para no perder registros
    antiguos que todavía no estén catalogados.
    """
    candidates: dict[str, str] = {}

    def add(code, title=None):
        normalized = str(code or "").strip()
        if not normalized or "EXPEDIENTE-COMPLETO" in normalized.upper():
            return
        candidates.setdefault(normalized, str(title or normalized).strip())

    try:
        try:
            import models
        except ImportError:
            from backend import models
        for row in db_session.query(models.CatalogoFormato).filter(
            models.CatalogoFormato.activo == True
        ).all():
            add(row.codigo, row.nombre)
        for row in db_session.query(models.FirmaDocumentoClinico.codigo_formato).filter(
            (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) |
            (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}"),
            models.FirmaDocumentoClinico.estado == "ACTIVA",
        ).distinct().all():
            add(row[0])
        for row in db_session.query(models.HistoricoNotaClinica.codigo_formato).filter(
            (models.HistoricoNotaClinica.pt_num == str(clean_pt)) |
            (models.HistoricoNotaClinica.pt_num == f"PT-{clean_pt}"),
        ).distinct().all():
            add(row[0])
    except Exception as exc:
        print(f"Nota: no se pudo leer el catálogo de formatos para expediente universal: {exc}")

    # El dashboard también es una fuente válida para instalaciones que aún no
    # han sincronizado todos sus formatos al catálogo PostgreSQL.
    for category in dashboard_data.get("formatos_disponibles", []) or []:
        for item in category.get("formatos", []) or []:
            if item.get("activo"):
                add(item.get("codigo"), item.get("nombre"))

    return [
        {"codigo": code, "nombre": title}
        for code, title in candidates.items()
    ]


def _append_universal_patient_formats(
    db_session,
    clean_pt: str,
    dashboard_data: dict,
    generated_docs: list[dict],
    patient_cache_dir: str,
    verification_url: str | None = None,
) -> list[dict]:
    """Integra automáticamente los formatos registrados con datos del paciente.

    Los motores especializados tienen prioridad. Todo formato restante pasa al
    renderer universal, que imprime cada campo devuelto por Vertical y deja
    trazabilidad de firmas. Si existe una evidencia HES para un código que no
    puede resolverse, se detiene la compilación: es preferible no entregar un
    expediente incompleto a ocultar una firma o un documento.
    """
    generated = list(generated_docs or [])
    unresolved = []
    seen_sources = set()

    def has_local_evidence(code: str) -> bool:
        try:
            try:
                import models
            except ImportError:
                from backend import models
            code_candidates = _format_code_candidates(code)
            firma = db_session.query(models.FirmaDocumentoClinico.id).filter(
                (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) |
                (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}"),
                models.FirmaDocumentoClinico.codigo_formato.in_(code_candidates),
                models.FirmaDocumentoClinico.estado == "ACTIVA",
            ).first()
            if firma:
                return True
            historic = db_session.query(models.HistoricoNotaClinica.id).filter(
                (models.HistoricoNotaClinica.pt_num == str(clean_pt)) |
                (models.HistoricoNotaClinica.pt_num == f"PT-{clean_pt}"),
                models.HistoricoNotaClinica.codigo_formato.in_(code_candidates),
            ).first()
            return historic is not None
        except Exception:
            return False

    try:
        try:
            from vertical_signer import resolve_vertical_controller_and_pk
        except ImportError:
            from backend.vertical_signer import resolve_vertical_controller_and_pk
    except Exception:
        resolve_vertical_controller_and_pk = None

    for candidate in _registered_patient_format_codes(db_session, clean_pt, dashboard_data):
        code = candidate["codigo"]
        try:
            source_identity = resolve_vertical_controller_and_pk(code) if resolve_vertical_controller_and_pk else None
        except Exception as exc:
            source_identity = None
            # Sólo se vuelve bloqueo si el paciente sí tiene evidencia en HES;
            # un elemento de catálogo sin registro se ignora correctamente.
            try:
                import models
                evidence_exists = db_session.query(models.FirmaDocumentoClinico.id).filter(
                    (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) |
                    (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}"),
                    models.FirmaDocumentoClinico.codigo_formato == code,
                    models.FirmaDocumentoClinico.estado == "ACTIVA",
                ).first() is not None
            except Exception:
                evidence_exists = False
            if evidence_exists:
                unresolved.append({"codigo": code, "motivo": str(exc)})
            continue

        already_generated = False
        for doc in generated:
            doc_code = str(doc.get("codigo") or "")
            if doc_code.upper() == code.upper():
                already_generated = True
                break
            try:
                doc_identity = resolve_vertical_controller_and_pk(doc_code) if resolve_vertical_controller_and_pk else None
            except Exception:
                doc_identity = None
            if source_identity and doc_identity and source_identity == doc_identity:
                already_generated = True
                break
            # Sólo usar alias textual como último recurso: algunos números
            # cortos son ambiguos entre CONSUL y SINPRO (por ejemplo, 15).
            if not source_identity and _format_codes_overlap(code, doc_code):
                already_generated = True
                break
        if already_generated:
            continue

        if source_identity and source_identity in seen_sources:
            continue

        try:
            history = kh_database.fetch_generic_format_history(code, clean_pt)
        except Exception as exc:
            print(f"Nota: no se pudo consultar el formato universal {code}: {exc}")
            history = []
        if not history:
            if has_local_evidence(code):
                unresolved.append({
                    "codigo": code,
                    "motivo": "Existe evidencia HES, pero no se pudo leer el registro Vertical actual.",
                })
            continue

        if source_identity:
            seen_sources.add(source_identity)
        # The generic history is sorted by Vertical's clinical PK descending.
        # Its current record, not the most recently signed older record,
        # determines the slot summarized in the expediente preflight.
        try:
            slot = int(history[0].get("mrnum") or 0)
        except (TypeError, ValueError):
            slot = 0
        signature_data = obtener_firmas_completas_documento(db_session, clean_pt, code, slot)
        # El formato universal puede contener varias versiones. Conservamos
        # el estado HES de cada ranura, no sólo el de la última, para que una
        # firma histórica nunca desaparezca al compilar el expediente.
        for record in history:
            try:
                record_slot = int(record.get("mrnum") or 0)
            except (TypeError, ValueError):
                record_slot = 0
            record["_firma_hes"] = obtener_firmas_completas_documento(
                db_session, clean_pt, code, record_slot
            )
        safe_code = re.sub(r"[^0-9A-Za-z_-]+", "_", code).strip("_").lower() or "formato"
        universal_path = os.path.join(patient_cache_dir, f"doc_universal_{safe_code}_{clean_pt}.pdf")
        pdf_engine_expediente.generate_formato_universal(
            dashboard_data,
            universal_path,
            codigo=code,
            nombre=candidate["nombre"],
            historial=history,
            firma_data=signature_data,
            verification_url=verification_url,
        )
        if os.path.exists(universal_path):
            generated.append({
                "codigo": code,
                "nombre": candidate["nombre"],
                "path": universal_path,
                "pages": get_pdf_page_count(universal_path),
                "estatus": "Firmado" if any(record.get("firmado") for record in history) else "Registrado",
                "firma": "Trazabilidad universal Vertical / HES",
                "slot": slot,
                "universal": True,
            })

    if unresolved:
        codes = ", ".join(item["codigo"] for item in unresolved)
        raise ValueError(
            "No se generó el expediente porque hay formatos con evidencia de firma "
            f"que no tienen una fuente Vertical resoluble ({codes}). Configure el "
            "controlador del formato antes de imprimir o entregar el expediente."
        )
    return generated


def _build_signature_ledger_items(
    db_session,
    clean_pt: str,
    dashboard_data: dict,
    generated_docs: list[dict],
) -> list[dict]:
    """Construye la vista consolidada de firmas para el anexo del expediente."""
    items = []
    seen = set()

    def add_native(records, target):
        for record in records or []:
            if not isinstance(record, dict) or not _source_has_native_signature(record):
                continue
            identity = (
                str(record.get("mrnum") or record.get("mrnum_ne_urg") or record.get("mrnum_24_hoja_evol") or ""),
                str(record.get("signed_by") or record.get("created_by") or ""),
                str(record.get("signed_on") or ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            target.append({
                "usuario": record.get("signed_by") or record.get("created_by") or "Vertical EHR",
                "fecha": record.get("signed_on") or "",
                "sello_corto": _short_signature_evidence(record.get("es_signature")),
            })

    ledger_documents = []
    for document in generated_docs or []:
        evolution_slots = document.get("evolution_signature_slots") or []
        if evolution_slots:
            ledger_documents.extend({
                **document,
                "slot": evolution["slot"],
                "nombre": f'{document.get("nombre") or document.get("codigo")} · evolución {evolution["num"]}',
            } for evolution in evolution_slots)
        else:
            ledger_documents.append(document)

    for document in ledger_documents:
        code = str(document.get("codigo") or "")
        if not code or "ANEXO" in code or "EXPEDIENTE-COMPLETO" in code:
            continue
        slot = int(document.get("slot") or 0)
        signature_data = obtener_firmas_completas_documento(db_session, clean_pt, code, slot) or {}
        native_records = []
        if "87" in code:
            add_native(
                [record for record in dashboard_data.get("evoluciones_list", [])
                 if int(record.get("num") or 0) == slot], native_records
            )
        elif code.endswith("-24") or "CONSUL-PLT-24" in code:
            add_native(
                [record for record in dashboard_data.get("evoluciones_hospitalizacion_list", [])
                 if int(record.get("mrnum_24_hoja_evol") or 0) == slot], native_records
            )
        else:
            try:
                add_native(kh_database.fetch_generic_format_history(code, clean_pt), native_records)
            except Exception:
                pass
        items.append({
            "codigo": code,
            "nombre": document.get("nombre") or code,
            "slot": slot,
            "actuales": {
                "medico": bool(signature_data.get("sello_digital") or signature_data.get("hash_sha256")),
                "paciente": bool(signature_data.get("sello_paciente")),
                "testigo1": bool(signature_data.get("sello_testigo1")),
                "testigo2": bool(signature_data.get("sello_testigo2")),
            },
            "historicas": signature_data.get("_signature_history") or [],
            "nativas": native_records,
        })
    return items


def build_expediente_signature_report(db_session, clean_pt: str, generated_docs: list[dict]) -> dict:
    """Resume las firmas que el expediente compilado pudo comprobar.

    Este resumen no contiene sellos, hashes ni nombres sensibles. Se usa para
    avisar en la interfaz qué documento requiere atención y para distinguir una
    firma ausente de una evidencia histórica que no pudo vincularse a la versión
    clínica actual.
    """
    try:
        try:
            import clinical_signing
        except ImportError:
            from backend import clinical_signing

        report = {"version": 1, "total_formatos": 0, "pendientes": [], "bloqueos": []}
        report_documents = []
        for document in generated_docs or []:
            evolution_slots = document.get("evolution_signature_slots") or []
            if evolution_slots:
                for evolution in evolution_slots:
                    report_documents.append({
                        **document,
                        "slot": evolution["slot"],
                        "nombre": f'{document.get("nombre") or document.get("codigo")} · evolución {evolution["num"]}',
                    })
            else:
                report_documents.append(document)
        for document in report_documents:
            code = str(document.get("codigo") or "")
            if not code or "ANEXO" in code or "EXPEDIENTE-COMPLETO" in code:
                continue

            report["total_formatos"] += 1
            slot = int(document.get("slot") or 0)
            signature_data = obtener_firmas_completas_documento(
                db_session, clean_pt, code, slot
            ) or {}
            medical_signed = bool(
                signature_data.get("sello_digital") or signature_data.get("hash_sha256")
            )
            patient_signed = bool(signature_data.get("sello_paciente"))
            witness_signed = {
                1: bool(signature_data.get("sello_testigo1")),
                2: bool(signature_data.get("sello_testigo2")),
            }

            required_roles = ["Médico"]
            policy_error = None
            try:
                requires_authorization, expected_witnesses = clinical_signing.consent_signature_policy(code)
            except Exception:
                requires_authorization, expected_witnesses = False, 0
                policy_error = "Formato sin política de firmas resoluble"

            if requires_authorization:
                required_roles.append("Paciente o representante")
                required_roles.extend(
                    f"Testigo {index}" for index in range(1, expected_witnesses + 1)
                )
            special_requirements = clinical_signing.special_signature_requirements(code)
            from format_catalog import special_signature_role_label
            special_state = signature_data.get("firmas_especiales") or {}
            required_roles.extend(special_signature_role_label(role) for role in special_requirements)

            signed_roles = []
            if medical_signed:
                signed_roles.append("Médico")
            if patient_signed:
                signed_roles.append("Paciente o representante")
            signed_roles.extend(
                f"Testigo {index}" for index in (1, 2) if witness_signed[index]
            )
            signed_roles.extend(
                special_signature_role_label(role)
                for role in special_requirements
                if bool((special_state.get(role) or {}).get("firmado"))
            )

            pending_roles = [role for role in required_roles if role not in signed_roles]
            issue = signature_data.get("_signature_verification_issue")
            raw_records = signature_data.get("_signature_records_found", 0)
            verified_records = signature_data.get("_signature_records_verified", 0)
            # Las evidencias antiguas se conservan para auditoría. Si ya existe
            # al menos una evidencia vigente de la versión actual, las antiguas
            # no deben seguir bloqueando el expediente: sólo se consideran
            # bloqueantes cuando no hay ninguna firma actual verificable.
            if raw_records > 0 and verified_records == 0:
                pending_roles.append("Evidencia histórica no vinculada")
                report["bloqueos"].append({
                    "codigo": code,
                    "nombre": document.get("nombre") or code,
                    "motivo": "Hay registros de firma que no pudieron vincularse a la versión clínica compilada.",
                })
            if issue:
                pending_roles.append("Verificación de evidencia")
                if signature_data.get("_signature_records_found"):
                    reason = (
                        "No se pudo consultar la evidencia de firmas."
                        if signature_data.get("_signature_records_found") == -1
                        else "Existe una firma activa, pero no pudo vincularse a la versión clínica actual."
                    )
                    report["bloqueos"].append({
                        "codigo": code,
                        "nombre": document.get("nombre") or code,
                        "motivo": reason,
                    })

            if policy_error:
                pending_roles.append("Política de firmas")

            entry = {
                "codigo": code,
                "nombre": document.get("nombre") or code,
                "slot": slot,
                "estado": "completo" if not pending_roles else "requiere_atencion",
                "firmas_presentes": signed_roles,
                "firmas_pendientes": pending_roles,
            }
            if pending_roles:
                report["pendientes"].append(entry)

        # Un mismo registro puede activar las dos comprobaciones de integridad
        # (conteo de evidencias y error de carga). No repetirlo al usuario: una
        # sola acción de revisión basta para cada formato.
        unique_blocks = []
        seen_blocks = set()
        for block in report["bloqueos"]:
            block_key = (
                str(block.get("codigo") or ""),
                str(block.get("motivo") or ""),
            )
            if block_key in seen_blocks:
                continue
            seen_blocks.add(block_key)
            unique_blocks.append(block)
        report["bloqueos"] = unique_blocks
        report["requiere_atencion"] = bool(report["pendientes"])
        return report
    except Exception as exc:
        # La generación no debe ocultar una falla de consulta de firmas.
        return {
            "version": 1,
            "total_formatos": len(generated_docs or []),
            "requiere_atencion": True,
            "pendientes": [{
                "codigo": "EXPEDIENTE",
                "nombre": "Verificación de firmas del expediente",
                "estado": "requiere_atencion",
                "firmas_presentes": [],
                "firmas_pendientes": ["No se pudo consultar el estado de firmas"],
            }],
            "bloqueos": [],
            "error_consulta": "CONSULTA_FIRMAS_NO_DISPONIBLE",
        }


def find_existing_valid_pdf(
    db_session,
    clean_pt: str,
    format_codes: List[str],
    filename_patterns: List[str] = None
) -> Optional[str]:
    """
    Busca el PDF oficial y validado más reciente:
    1. Base de datos: DocumentoVerificacionQR (para el paciente y formatos indicados).
    2. Directorios físicos: scratch/, static/pdfs/, etc.
    Verifica que el archivo exista físicamente en disco y tenga un tamaño válido (> 1024 bytes).
    """
    # 1. Buscar en BD DocumentoVerificacionQR
    if db_session:
        try:
            try:
                import models
            except ImportError:
                from backend import models

            qr_query = db_session.query(models.DocumentoVerificacionQR).filter(
                (models.DocumentoVerificacionQR.pt_num == str(clean_pt)) | 
                (models.DocumentoVerificacionQR.expediente == f"PT-{clean_pt}"),
                models.DocumentoVerificacionQR.activo == True
            )
            
            or_conditions = []
            for code in format_codes:
                or_conditions.append(models.DocumentoVerificacionQR.codigo_formato.ilike(f"%{code}%"))
            if or_conditions:
                from sqlalchemy import or_
                qr_query = qr_query.filter(or_(*or_conditions))
            
            qr_records = qr_query.order_by(models.DocumentoVerificacionQR.fecha_generacion.desc(), models.DocumentoVerificacionQR.id.desc()).all()
            for r in qr_records:
                if r.pdf_path and os.path.exists(r.pdf_path) and os.path.getsize(r.pdf_path) > 1024:
                    return r.pdf_path
                if r.pdf_filename:
                    for search_dir in [SCRATCH_DIR, STATIC_PDFS_DIR, PROJECT_ROOT]:
                        candidate = os.path.join(search_dir, r.pdf_filename)
                        if os.path.exists(candidate) and os.path.getsize(candidate) > 1024:
                            return candidate
        except Exception as e_qr:
            print(f"Error querying DocumentoVerificacionQR in find_existing_valid_pdf: {e_qr}")

    # 2. Buscar en directorios físicos (scratch, static/pdfs)
    candidates = []
    if filename_patterns:
        for s_dir in [SCRATCH_DIR, STATIC_PDFS_DIR]:
            if not os.path.exists(s_dir):
                continue
            for pat in filename_patterns:
                full_pattern = os.path.join(s_dir, pat)
                matched = glob.glob(full_pattern)
                for m in matched:
                    if os.path.exists(m) and os.path.getsize(m) > 1024:
                        candidates.append((os.path.getmtime(m), m))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None


def get_latest_historic_record(db_session, clean_pt: str, format_code: str):
    """Obtiene el último registro de HistoricoNotaClinica para un formato clínico."""
    if not db_session:
        return None
    try:
        try:
            import models
        except ImportError:
            from backend import models
        return db_session.query(models.HistoricoNotaClinica).filter(
            (models.HistoricoNotaClinica.pt_num == str(clean_pt)) | (models.HistoricoNotaClinica.pt_num == f"PT-{clean_pt}"),
            models.HistoricoNotaClinica.codigo_formato.in_(_format_code_candidates(format_code))
        ).order_by(models.HistoricoNotaClinica.fecha_registro.desc()).first()
    except Exception as e:
        print(f"Error fetching HistoricoNotaClinica for {format_code}: {e}")
        return None


def generate_comprobante_atencion_pdf(atencion: Any, match_found: Any, paciente: Any) -> str:
    """Genera el PDF del comprobante de atención médica con firma digital."""
    return pdf_generator.generate_pdf(atencion, match_found, paciente)


def generate_consentimiento_32_01_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF oficial para el consentimiento informado 32/01."""
    pdf_filename = f"consentimiento_32_01_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_32_01.generate_consentimiento_32_01(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_nota_urgencias_pdf(
    pt_num: str, 
    pt_data: dict, 
    evolucion: Optional[int] = None, 
    target_evol: Optional[dict] = None,
    e1: Optional[dict] = None,
    e2: Optional[dict] = None,
    e3: Optional[dict] = None,
    firma_data: Optional[dict] = None,
    evoluciones_list: Optional[list] = None
) -> Tuple[str, str]:
    """Genera el PDF oficial de Nota de Evolución de Urgencias (Formato 87/01)."""
    if evolucion is not None and int(evolucion) > 0:
        pdf_filename = f"nota_urgencias_{pt_num}_evolucion_{evolucion}.pdf"
        pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
        pdf_engine_v2.generate_nota_urgencias(
            pt_data, target_evol, None, None, pdf_path, is_general=False, firma_data=firma_data
        )
    else:
        pdf_filename = f"nota_urgencias_{pt_num}_general.pdf"
        pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
        pdf_engine_v2.generate_nota_urgencias(
            pt_data, e1, e2, e3, pdf_path, is_general=True, firma_data=firma_data, evoluciones_list=evoluciones_list
        )
    return pdf_path, pdf_filename


def generate_nota_hospitalizacion_pdf(
    pt_num: str,
    pt_data: dict,
    evolucion: Optional[int] = None,
    target_evol: Optional[dict] = None,
    firma_data: Optional[dict] = None,
    evoluciones_list: Optional[list] = None
) -> Tuple[str, str]:
    """Genera el PDF oficial de Nota de Evolución de Hospitalización (Formato 24)."""
    if evolucion is not None and int(evolucion) > 0:
        pdf_filename = f"nota_hospitalizacion_{pt_num}_evolucion_{evolucion}.pdf"
        pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
        pdf_engine_24.generate_nota_hospitalizacion(
            pt_data, target_evol, None, None, pdf_path, is_general=False, firma_data=firma_data
        )
    else:
        pdf_filename = f"nota_hospitalizacion_{pt_num}_general.pdf"
        pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
        pdf_engine_24.generate_nota_hospitalizacion(
            pt_data, None, None, None, pdf_path, is_general=True, firma_data=firma_data, evoluciones_list=evoluciones_list
        )
    return pdf_path, pdf_filename


def generate_consentimiento_eed_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Ecocardiograma de Estrés con Dobutamina."""
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_path = pdf_engine_eed.generar_pdf_eed(pt_data, firma_data=firma_data)
    pdf_filename = f"CI_EED_{pt_num}.pdf"
    return pdf_path, pdf_filename


def generate_consentimiento_34_01_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Estudio de Mesa Inclinada (Tilt Test)."""
    pdf_filename = f"CI_34_01_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_34_01.generate_consentimiento_34_01(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_consentimiento_12_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Revisión Ginecológica y Obstétrica (Hosp/Urg)."""
    pdf_filename = f"CI_12_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_12.generate_consentimiento_12(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_consentimiento_04_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Catéter Venoso Central."""
    pdf_filename = f"CI_04_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_04.generate_consentimiento_04(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_consentimiento_08_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Admisión Continua y Procedimientos Diagnósticos (Formato 08)."""
    pdf_filename = f"CI_08_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_08.generate_consentimiento_08(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_consentimiento_09_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Transfusión de Hemocomponentes (Formato 09)."""
    pdf_filename = f"CI_09_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_09.generate_consentimiento_09(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_consentimiento_15_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Cesárea / Disentimiento."""
    pdf_filename = f"CI_15_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_15.generate_consentimiento_15(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_egreso_resumen_16_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de Egreso y Resumen Clínico (Formato 16 - HE-DIRMED-SINPRO-PLT-16)."""
    pdf_filename = f"EGRESO_RESUMEN_16_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_16.generate_egreso_resumen_16(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_consentimiento_25_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Revisión Ginecológica y Obstétrica (Consulta Externa)."""
    pdf_filename = f"CI_25_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_25.generate_consentimiento_25(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_consentimiento_02_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Tratamiento Quirúrgico (Formato 02)."""
    pdf_filename = f"CI_02_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_02.generate_consentimiento_02(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_consentimiento_43_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Orden de Intubación Endotraqueal (Formato 43)."""
    pdf_filename = f"CI_43_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_43.generate_consentimiento_43(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename


def generate_expediente_completo_pdf(
    pt_num: str,
    db_session=None,
    verification_url: str | None = None,
    return_metadata: bool = False,
) -> Tuple[str, str] | Tuple[str, str, dict]:
    """
    Genera el EXPEDIENTE CLÍNICO COMPLETO oficial (NOM-004-SSA3-2012 / NOM-024-SSA3-2012).
    Ensambla y concatena en un único archivo PDF institucional de alta fidelidad:
      1. Carátula y Portada Oficial del Expediente Clínico con Ficha de Identificación e Índice Foliado.
      2. Formato 87/01 (Nota de Urgencias - General con todas las evoluciones y firmas biométricas).
      3. Formato 24 (Nota de Hospitalización - General con todas las evoluciones y firmas biométricas).
      4. Consentimientos Informados Oficiales Registrados (02, 04, 08, 12, 15, 25, 32/01, 34/01, EED).
      5. Anexo Farmacoterapéutico (PTDG), Régimen Dietético (MR_SOL_DIET) y Cuidados Clínicos.
      6. Anexo de Estudios Paraclínicos (Laboratorios Clínicos e Imagenología Diagnóstica).
    """
    clean_pt = re.sub(r'[^0-9]', '', str(pt_num)) or str(pt_num)
    final_output_path = os.path.join(STATIC_PDFS_DIR, f"expediente_completo_{clean_pt}.pdf")
    # Nunca dejar que una solicitud fallida entregue accidentalmente el PDF de
    # una compilación anterior. El expediente final es un artefacto generado y
    # puede volver a producirse una vez resuelta la reconciliación.
    if os.path.exists(final_output_path):
        try:
            os.remove(final_output_path)
        except OSError as exc:
            raise RuntimeError(
                "No se pudo invalidar el expediente generado anteriormente; "
                "se detuvo la compilación para evitar entregar información desactualizada."
            ) from exc
    dashboard_data = kh_database.fetch_full_ehr_dashboard(clean_pt)
    if not dashboard_data or "error" in dashboard_data:
        raise ValueError(f"No se pudo recuperar información para el paciente {pt_num}: {dashboard_data.get('error', 'Desconocido')}")

    own_db = False
    if db_session is None:
        try:
            try:
                import database
            except ImportError:
                from backend import database
            db_session = database.SessionLocal()
            own_db = True
        except Exception:
            db_session = None

    try:
        if not verification_url:
            qr_context = current_qr_context()
            verification_url = qr_context.get("verification_url") if qr_context else None
        patient_info = dashboard_data.get("patient", {})
        fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
        hora_hoy = datetime.datetime.now().strftime("%H:%M")
        fecha_ingreso = patient_info.get("fecha_ingreso", fecha_hoy) or fecha_hoy
        hora_ingreso = patient_info.get("hora_ingreso", hora_hoy) or hora_hoy

        # Cada compilación usa una corrida aislada. Así, un archivo de una
        # generación anterior nunca puede colarse en el expediente actual si
        # un formato cambia de versión o deja de estar disponible.
        run_id = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:10]}"
        patient_cache_dir = os.path.join(CACHE_PDFS_DIR, f"pt_{clean_pt}", f"run_{run_id}")
        os.makedirs(patient_cache_dir, exist_ok=True)

        generated_docs = []

        # =========================================================================
        # A) FORMATO 87/01 (Nota de Urgencias)
        # =========================================================================
        evoluciones_urg = dashboard_data.get("evoluciones_list", [])
        evols = dashboard_data.get("evoluciones", {})
        e1 = evols.get("evolucion1")
        e2 = evols.get("evolucion2")
        e3 = evols.get("evolucion3")
        hist_urg = get_latest_historic_record(db_session, clean_pt, "87")

        if evoluciones_urg or e1 or e2 or e3 or hist_urg:
            pt_data_urg = {
                "nombre": patient_info.get("name", ""),
                "dob": patient_info.get("dob", ""),
                "mrn": patient_info.get("mrn", f"PT-{clean_pt}"),
                "cama": patient_info.get("cama", "Urgencias"),
                "edad": patient_info.get("age", ""),
                "sexo": "M" if patient_info.get("gender") == "Masculino" else "F",
                "grupo_rh": "O+",
                "alergias": patient_info.get("allergies", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "diagnostico": patient_info.get("diagnostico", ""),
                "destino": patient_info.get("destino", "DOMICILIO"),
                "fecha_egreso": patient_info.get("fecha_egreso", "___/___/___"),
                "hora_egreso": patient_info.get("hora_egreso", "__:__")
            }
            firmas_urg = build_evolution_signature_map(
                db_session, clean_pt, "HE-DIRMED-SINPRO-PLT-87/01", evoluciones_urg or []
            )
            urg_path = os.path.join(patient_cache_dir, f"doc_urgencias_{clean_pt}.pdf")
            pdf_engine_v2.generate_nota_urgencias(
                pt_data_urg, e1, e2, e3, urg_path, is_general=True,
                evoluciones_list=evoluciones_urg, firma_data_by_slot=firmas_urg,
            )
            if os.path.exists(urg_path):
                p_count = get_pdf_page_count(urg_path)
                generated_docs.append({
                    "codigo": "HE-DIRMED-SINPRO-PLT-87/01",
                    "nombre": f"Nota Médica de Evolución de Urgencias ({len(evoluciones_urg)} evoluciones)" if evoluciones_urg else "Nota Médica de Evolución de Urgencias",
                    "path": urg_path,
                    "pages": p_count,
                    "estatus": "Integrado",
                    "firma": "Firma Biométrica" if any(s.get("sello_digital") for s in firmas_urg.values()) else "Sin firma HES",
                    "evolution_signature_slots": [
                        {"num": int(ev.get("num") or index), "slot": int(ev.get("num") or index)}
                        for index, ev in enumerate(evoluciones_urg or [], 1)
                    ],
                })

        # =========================================================================
        # B) FORMATO 24 (Nota de Hospitalización)
        # =========================================================================
        evoluciones_hosp = dashboard_data.get("evoluciones_hospitalizacion_list", [])
        hist_hosp = get_latest_historic_record(db_session, clean_pt, "24")
        if evoluciones_hosp or hist_hosp:
            pt_data_hosp = {
                "pt_num": str(clean_pt),
                "nombre": patient_info.get("name", ""),
                "dob": patient_info.get("dob", ""),
                "mrn": patient_info.get("mrn", f"PT-{clean_pt}"),
                "cama": patient_info.get("cama", "Piso Hospitalización"),
                "habitacion": patient_info.get("cama", "Piso Hospitalización"),
                "edad": patient_info.get("age", ""),
                "sexo": "M" if patient_info.get("gender") == "Masculino" else "F",
                "grupo_rh": "O+",
                "alergias": patient_info.get("allergies", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "diagnostico": patient_info.get("diagnostico", ""),
                "servicio": "HOSPITALIZACIÓN / MEDICINA INTERNA"
            }
            firmas_hosp = build_evolution_signature_map(
                db_session, clean_pt, "HE-DIRMED-CONSUL-PLT-24", evoluciones_hosp or []
            )
            hosp_path = os.path.join(patient_cache_dir, f"doc_hospitalizacion_{clean_pt}.pdf")
            pdf_engine_24.generate_nota_hospitalizacion(
                pt_data_hosp, None, None, None, hosp_path, is_general=True,
                evoluciones_list=evoluciones_hosp, firma_data_by_slot=firmas_hosp,
            )
            if os.path.exists(hosp_path):
                p_count = get_pdf_page_count(hosp_path)
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-24",
                    "nombre": f"Nota Médica de Evolución de Hospitalización ({len(evoluciones_hosp)} evoluciones)" if evoluciones_hosp else "Nota Médica de Evolución de Hospitalización",
                    "path": hosp_path,
                    "pages": p_count,
                    "estatus": "Integrado",
                    "firma": "Firma Biométrica" if any(s.get("sello_digital") for s in firmas_hosp.values()) else "Sin firma HES",
                    "evolution_signature_slots": [
                        {"num": int(ev.get("num") or index), "slot": int(ev.get("mrnum_24_hoja_evol") or 0)}
                        for index, ev in enumerate(evoluciones_hosp or [], 1)
                    ],
                })

        # =========================================================================
        # C) CONSENTIMIENTOS INFORMADOS OFICIALES (Regeneración fresca con firmas activas)
        # =========================================================================

        # 1. CI 02 (Tratamiento Quirúrgico / Disentimiento)
        hist_02 = get_latest_historic_record(db_session, clean_pt, "02")
        c02_sql, c02_slot = fetch_current_format_record(
            db_session, clean_pt, "02", getattr(kh_database, "fetch_consentimiento_02", None)
        )
        sig_02 = obtener_firmas_completas_documento(db_session, clean_pt, "02", c02_slot)
        has_real_02 = bool(hist_02 or sig_02.get("sello_digital") or sig_02.get("sello_paciente") or (c02_sql and not c02_sql.get("error") and (c02_sql.get("diagnostico") or c02_sql.get("mrnum"))))
        if has_real_02:
            pt_data_02 = {
                "paciente_nombre": patient_info.get("name", ""),
                "nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "patient": patient_info
            }
            if hist_02 and hist_02.contenido_soap_json:
                try:
                    pt_data_02.update(json.loads(hist_02.contenido_soap_json))
                except Exception:
                    pass
            if c02_sql and isinstance(c02_sql, dict):
                pt_data_02.update({k: v for k, v in c02_sql.items() if v})
            c02_path = os.path.join(patient_cache_dir, f"doc_ci_02_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_02, sig_02, sig_02, pt_data_02.get("paciente_capaz", True), db=db_session)
            pdf_engine_02.generate_consentimiento_02(pt_data_02, c02_path, firma_data=sig_02)
            if os.path.exists(c02_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-02",
                    "slot": c02_slot,
                    "nombre": "Consentimiento Informado para Tratamiento Quirúrgico",
                    "path": c02_path,
                    "pages": get_pdf_page_count(c02_path),
                    "estatus": "Firmado" if sig_02.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 2. CI 04 (Catéter Venoso Central)
        hist_04 = get_latest_historic_record(db_session, clean_pt, "04")
        c04_sql, c04_slot = fetch_current_format_record(
            db_session, clean_pt, "04", getattr(kh_database, "fetch_consentimiento_04", None)
        )
        sig_04 = obtener_firmas_completas_documento(db_session, clean_pt, "04", c04_slot)
        has_real_04 = bool(hist_04 or sig_04.get("sello_digital") or sig_04.get("sello_paciente") or (c04_sql and not c04_sql.get("error") and (c04_sql.get("procedimiento") or c04_sql.get("mrnum"))))
        if has_real_04:
            pt_data_04 = {
                "paciente_nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "patient": patient_info
            }
            if hist_04 and hist_04.contenido_soap_json:
                try:
                    pt_data_04.update(json.loads(hist_04.contenido_soap_json))
                except Exception:
                    pass
            if c04_sql and isinstance(c04_sql, dict):
                pt_data_04.update({k: v for k, v in c04_sql.items() if v})
            c04_path = os.path.join(patient_cache_dir, f"doc_ci_04_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_04, sig_04, sig_04, pt_data_04.get("paciente_capaz", True), db=db_session)
            pdf_engine_04.generate_consentimiento_04(pt_data_04, c04_path, firma_data=sig_04)
            if os.path.exists(c04_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-04",
                    "slot": c04_slot,
                    "nombre": "Consentimiento Informado: Catéter Venoso Central",
                    "path": c04_path,
                    "pages": get_pdf_page_count(c04_path),
                    "estatus": "Firmado" if sig_04.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 3. CI 08 (Admisión Continua y Procedimientos Diagnósticos)
        hist_08 = get_latest_historic_record(db_session, clean_pt, "08")
        c08_sql, c08_slot = fetch_current_format_record(
            db_session, clean_pt, "08", getattr(kh_database, "fetch_consentimiento_08", None)
        )
        sig_08 = obtener_firmas_completas_documento(db_session, clean_pt, "08", c08_slot)
        has_real_08 = bool(hist_08 or sig_08.get("sello_digital") or sig_08.get("sello_paciente") or (c08_sql and not c08_sql.get("error") and (c08_sql.get("diagnostico") or c08_sql.get("mrnum"))))
        if has_real_08:
            pt_data_08 = {
                "paciente_nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "patient": patient_info
            }
            if hist_08 and hist_08.contenido_soap_json:
                try:
                    pt_data_08.update(json.loads(hist_08.contenido_soap_json))
                except Exception:
                    pass
            if c08_sql and isinstance(c08_sql, dict):
                pt_data_08.update({k: v for k, v in c08_sql.items() if v})
            c08_path = os.path.join(patient_cache_dir, f"doc_ci_08_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_08, sig_08, sig_08, pt_data_08.get("paciente_capaz", True), db=db_session)
            pdf_engine_08.generate_consentimiento_08(pt_data_08, c08_path, firma_data=sig_08)
            if os.path.exists(c08_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-08",
                    "slot": c08_slot,
                    "nombre": "Consentimiento Informado: Admisión Continua y Diagnóstico",
                    "path": c08_path,
                    "pages": get_pdf_page_count(c08_path),
                    "estatus": "Firmado" if sig_08.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 3b. CI 09 (Transfusión de Hemocomponentes)
        hist_09 = get_latest_historic_record(db_session, clean_pt, "09")
        c09_sql, c09_slot = fetch_current_format_record(
            db_session, clean_pt, "09", getattr(kh_database, "fetch_consentimiento_09", None)
        )
        sig_09 = obtener_firmas_completas_documento(db_session, clean_pt, "09", c09_slot)
        has_real_09 = bool(hist_09 or sig_09.get("sello_digital") or sig_09.get("sello_paciente") or (c09_sql and not c09_sql.get("error") and (c09_sql.get("hemocomponentes") or c09_sql.get("mrnum"))))
        if has_real_09:
            pt_data_09 = {
                "paciente_nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "medico_tratante": patient_info.get("attending_doctor", ""),
                "patient": patient_info
            }
            if hist_09 and hist_09.contenido_soap_json:
                try:
                    pt_data_09.update(json.loads(hist_09.contenido_soap_json))
                except Exception:
                    pass
            if c09_sql and isinstance(c09_sql, dict):
                pt_data_09.update({k: v for k, v in c09_sql.items() if v})
            c09_path = os.path.join(patient_cache_dir, f"doc_ci_09_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_09, sig_09, sig_09, pt_data_09.get("paciente_capaz", True), db=db_session)
            pdf_engine_09.generate_consentimiento_09(pt_data_09, c09_path, firma_data=sig_09)
            if os.path.exists(c09_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-09",
                    "slot": c09_slot,
                    "nombre": "Consentimiento Informado: Transfusión de Hemocomponentes",
                    "path": c09_path,
                    "pages": get_pdf_page_count(c09_path),
                    "estatus": "Firmado" if sig_09.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 4. CI 12 (Revisión Gineco-Obstétrica Hosp/Urg)
        hist_12 = get_latest_historic_record(db_session, clean_pt, "12")
        c12_sql, c12_slot = fetch_current_format_record(
            db_session, clean_pt, "12", getattr(kh_database, "fetch_consentimiento_12", None)
        )
        sig_12 = obtener_firmas_completas_documento(db_session, clean_pt, "12", c12_slot)
        has_real_12 = bool(hist_12 or sig_12.get("sello_digital") or sig_12.get("sello_paciente") or (c12_sql and not c12_sql.get("error") and (c12_sql.get("diagnostico") or c12_sql.get("mrnum"))))
        if has_real_12:
            pt_data_12 = {
                "paciente_nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "patient": patient_info
            }
            if hist_12 and hist_12.contenido_soap_json:
                try:
                    pt_data_12.update(json.loads(hist_12.contenido_soap_json))
                except Exception:
                    pass
            if c12_sql and isinstance(c12_sql, dict):
                pt_data_12.update({k: v for k, v in c12_sql.items() if v})
            c12_path = os.path.join(patient_cache_dir, f"doc_ci_12_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_12, sig_12, sig_12, pt_data_12.get("paciente_capaz", True), db=db_session)
            pdf_engine_12.generate_consentimiento_12(pt_data_12, c12_path, firma_data=sig_12)
            if os.path.exists(c12_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-12",
                    "slot": c12_slot,
                    "nombre": "Consentimiento Informado: Revisión Gineco-Obstétrica (Hosp/Urg)",
                    "path": c12_path,
                    "pages": get_pdf_page_count(c12_path),
                    "estatus": "Firmado" if sig_12.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 5. CI 15 (Cesárea / Procedimientos Obstétricos)
        hist_15 = get_latest_historic_record(db_session, clean_pt, "HE-DIRMED-CONSUL-PLT-15")
        c15_sql, c15_slot = fetch_current_format_record(
            db_session, clean_pt, "HE-DIRMED-CONSUL-PLT-15", getattr(kh_database, "fetch_consentimiento_15", None)
        )
        sig_15 = obtener_firmas_completas_documento(db_session, clean_pt, "HE-DIRMED-CONSUL-PLT-15", c15_slot)
        has_real_15 = bool(hist_15 or sig_15.get("sello_digital") or sig_15.get("sello_paciente") or (c15_sql and not c15_sql.get("error") and (c15_sql.get("diagnostico") or c15_sql.get("mrnum"))))
        if has_real_15:
            pt_data_15 = {
                "paciente_nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "patient": patient_info
            }
            if hist_15 and hist_15.contenido_soap_json:
                try:
                    pt_data_15.update(json.loads(hist_15.contenido_soap_json))
                except Exception:
                    pass
            if c15_sql and isinstance(c15_sql, dict):
                pt_data_15.update({k: v for k, v in c15_sql.items() if v})
            c15_path = os.path.join(patient_cache_dir, f"doc_ci_15_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_15, sig_15, sig_15, pt_data_15.get("paciente_capaz", True), db=db_session)
            pdf_engine_15.generate_consentimiento_15(pt_data_15, c15_path, firma_data=sig_15)
            if os.path.exists(c15_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-15",
                    "slot": c15_slot,
                    "nombre": "Consentimiento Informado para Procedimiento de Cesárea",
                    "path": c15_path,
                    "pages": get_pdf_page_count(c15_path),
                    "estatus": "Firmado" if sig_15.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 6. CI 25 (Revisión Ginecológica Consulta Externa)
        hist_25 = get_latest_historic_record(db_session, clean_pt, "25")
        c25_sql, c25_slot = fetch_current_format_record(
            db_session, clean_pt, "25", getattr(kh_database, "fetch_consentimiento_25", None)
        )
        sig_25 = obtener_firmas_completas_documento(db_session, clean_pt, "25", c25_slot)
        has_real_25 = bool(hist_25 or sig_25.get("sello_digital") or sig_25.get("sello_paciente") or (c25_sql and not c25_sql.get("error") and (c25_sql.get("diagnostico") or c25_sql.get("mrnum"))))
        if has_real_25:
            pt_data_25 = {
                "paciente_nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "patient": patient_info
            }
            if hist_25 and hist_25.contenido_soap_json:
                try:
                    pt_data_25.update(json.loads(hist_25.contenido_soap_json))
                except Exception:
                    pass
            if c25_sql and isinstance(c25_sql, dict):
                pt_data_25.update({k: v for k, v in c25_sql.items() if v})
            c25_path = os.path.join(patient_cache_dir, f"doc_ci_25_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_25, sig_25, sig_25, pt_data_25.get("paciente_capaz", True), db=db_session)
            pdf_engine_25.generate_consentimiento_25(pt_data_25, c25_path, firma_data=sig_25)
            if os.path.exists(c25_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-25",
                    "slot": c25_slot,
                    "nombre": "Consentimiento Informado: Revisión Ginecológica (Consulta Externa)",
                    "path": c25_path,
                    "pages": get_pdf_page_count(c25_path),
                    "estatus": "Firmado" if sig_25.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 7. CI 32/01 (Ecocardiograma Transesofágico)
        hist_32 = get_latest_historic_record(db_session, clean_pt, "32")
        sig_32 = obtener_firmas_completas_documento(db_session, clean_pt, "32", 0)
        c32_data = dashboard_data.get("consentimiento_32_01")
        has_real_32 = bool(hist_32 or sig_32.get("sello_digital") or sig_32.get("sello_paciente") or c32_data)
        if has_real_32:
            pt_data_32 = {
                "nombre": patient_info.get("name", ""),
                "dob": patient_info.get("dob", ""),
                "mrn": patient_info.get("mrn", f"PT-{clean_pt}"),
                "cama": patient_info.get("cama", "URGENCIAS"),
                "edad": patient_info.get("age", ""),
                "sexo": "M" if patient_info.get("gender") == "Masculino" else "F",
                "grupo_rh": "O+",
                "alergias": patient_info.get("allergies", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "diagnostico": patient_info.get("diagnostico", ""),
                "tipo_interrogatorio": "Directo",
                "medico_tratante": patient_info.get("attending_doctor", ""),
                "cedula": patient_info.get("cedula", ""),
                "testigo1": "",
                "testigo2": "",
                "paciente_o_representante": patient_info.get("name", "")
            }
            if hist_32 and hist_32.contenido_soap_json:
                try:
                    pt_data_32.update(json.loads(hist_32.contenido_soap_json))
                except Exception:
                    pass
            if c32_data and isinstance(c32_data, dict):
                pt_data_32.update({k: v for k, v in c32_data.items() if v})
            c32_path = os.path.join(patient_cache_dir, f"doc_ci_32_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_32, sig_32, sig_32, pt_data_32.get("paciente_capaz", True), db=db_session)
            pdf_engine_32_01.generate_consentimiento_32_01(pt_data_32, c32_path, firma_data=sig_32)
            if os.path.exists(c32_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-32/01",
                    "nombre": "Consentimiento Informado: Ecocardiograma Transesofágico",
                    "path": c32_path,
                    "pages": get_pdf_page_count(c32_path),
                    "estatus": "Firmado" if sig_32.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 8. CI 34/01 (Mesa Inclinada / Tilt Test)
        hist_34 = get_latest_historic_record(db_session, clean_pt, "34")
        c34_sql, c34_slot = fetch_current_format_record(
            db_session, clean_pt, "34", getattr(kh_database, "fetch_consentimiento_34_01", None)
        )
        sig_34 = obtener_firmas_completas_documento(db_session, clean_pt, "34", c34_slot)
        c34_data = dashboard_data.get("consentimiento_34_01")
        has_real_34 = bool(hist_34 or sig_34.get("sello_digital") or sig_34.get("sello_paciente") or (c34_sql and not c34_sql.get("error") and (c34_sql.get("conclusiones") or c34_sql.get("mrnum"))) or c34_data)
        if has_real_34:
            pt_data_34 = {
                "nombre": patient_info.get("name", ""),
                "paciente_nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "sexo": "M" if patient_info.get("gender") == "Masculino" else "F",
                "gruporh": "O+",
                "alergias": patient_info.get("allergies", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "tipo_interrogatorio": "DIRECTO",
                "medico_tratante": patient_info.get("attending_doctor", ""),
                "cedula": patient_info.get("cedula", ""),
                "patient": patient_info
            }
            if hist_34 and hist_34.contenido_soap_json:
                try:
                    pt_data_34.update(json.loads(hist_34.contenido_soap_json))
                except Exception:
                    pass
            if c34_data and isinstance(c34_data, dict):
                pt_data_34.update({k: v for k, v in c34_data.items() if v})
            if c34_sql and isinstance(c34_sql, dict):
                pt_data_34.update({k: v for k, v in c34_sql.items() if v})
            c34_path = os.path.join(patient_cache_dir, f"doc_ci_34_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_34, sig_34, sig_34, pt_data_34.get("paciente_capaz", True), db=db_session)
            pdf_engine_34_01.generate_consentimiento_34_01(pt_data_34, c34_path, firma_data=sig_34)
            if os.path.exists(c34_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-34/01",
                    "slot": c34_slot,
                    "nombre": "Consentimiento Informado: Estudio de Mesa Inclinada (Tilt Test)",
                    "path": c34_path,
                    "pages": get_pdf_page_count(c34_path),
                    "estatus": "Firmado" if sig_34.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 9. CI EED (Ecocardiograma Estrés con Dobutamina)
        hist_eed = get_latest_historic_record(db_session, clean_pt, "EED")
        sig_eed = obtener_firmas_completas_documento(db_session, clean_pt, "EED", 0)
        ceed_data = dashboard_data.get("consentimiento_eed")
        has_real_eed = bool(hist_eed or sig_eed.get("sello_digital") or sig_eed.get("sello_paciente") or ceed_data)
        if has_real_eed:
            pt_data_eed = {
                "nombre": patient_info.get("name", ""),
                "expediente": clean_pt,
                "fecha_nacimiento": patient_info.get("dob", ""),
                "sexo": "M" if patient_info.get("gender") == "Masculino" else "F",
                "cama": patient_info.get("cama", "Urgencias"),
                "fecha": fecha_hoy,
                "hora": hora_hoy,
                "alergias": patient_info.get("allergies", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "medico": patient_info.get("attending_doctor", ""),
                "cedula": patient_info.get("cedula", "")
            }
            if hist_eed and hist_eed.contenido_soap_json:
                try:
                    pt_data_eed.update(json.loads(hist_eed.contenido_soap_json))
                except Exception:
                    pass
            if ceed_data and isinstance(ceed_data, dict):
                pt_data_eed.update(ceed_data)
            ceed_path = os.path.join(patient_cache_dir, f"doc_ci_eed_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_eed, sig_eed, sig_eed, pt_data_eed.get("paciente_capaz", True), db=db_session)
            pdf_engine_eed.generar_pdf_eed(
                pt_data_eed,
                force_output_path=ceed_path,
                firma_data=sig_eed,
            )
            if os.path.exists(ceed_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-EED",
                    "nombre": "Consentimiento Informado: Ecocardiograma Estrés con Dobutamina",
                    "path": ceed_path,
                    "pages": get_pdf_page_count(ceed_path),
                    "estatus": "Firmado" if sig_eed.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 10. CI 43 (Orden de Intubación Endotraqueal / Soporte Ventilatorio)
        hist_43 = get_latest_historic_record(db_session, clean_pt, "43")
        c43_sql, c43_slot = fetch_current_format_record(
            db_session, clean_pt, "43", getattr(kh_database, "fetch_consentimiento_43", None)
        )
        sig_43 = obtener_firmas_completas_documento(db_session, clean_pt, "43", c43_slot)
        has_real_43 = bool(hist_43 or sig_43.get("sello_digital") or sig_43.get("sello_paciente") or (c43_sql and not c43_sql.get("error") and (c43_sql.get("medico_tratante") or c43_sql.get("mrnum"))))
        if has_real_43:
            pt_data_43 = {
                "paciente_nombre": patient_info.get("name", ""),
                "nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_atencion": fecha_hoy,
                "hora_atencion": hora_hoy,
                "diagnostico": patient_info.get("diagnostico", "INSUFICIENCIA RESPIRATORIA AGUDA / COMPROMISO DE VÍA AÉREA"),
                "servicio": patient_info.get("cama", "URGENCIAS / TERAPIA INTENSIVA"),
                "medico_tratante": patient_info.get("attending_doctor", ""),
                "cedula": patient_info.get("cedula", ""),
                "beneficios": "Aseguramiento de la vía aérea permeable, soporte ventilatorio mecánico invasivo, optimización de la oxigenación tisular y prevención del paro respiratorio o colapso hemodinámico.",
                "riesgos": "Traumatismo de la vía aérea (laringe, cuerdas vocales, tráquea), broncoaspiración, intubación esofágica o selectiva, broncoespasmo, arritmias, hipotensión, neumotórax o necesidad de ventilación mecánica prolongada.",
                "alternativas": "Oxigenoterapia de alto flujo, ventilación mecánica no invasiva (según indicación y estabilidad clínica) o manejo médico conservador.",
                "declarante": patient_info.get("name", ""),
                "paciente_capaz": True,
                "testigo1": "",
                "testigo2": "",
                "patient": patient_info
            }
            if hist_43 and hist_43.contenido_soap_json:
                try:
                    pt_data_43.update(json.loads(hist_43.contenido_soap_json))
                except Exception:
                    pass
            if c43_sql and isinstance(c43_sql, dict):
                pt_data_43.update({k: v for k, v in c43_sql.items() if v})
            c43_path = os.path.join(patient_cache_dir, f"doc_ci_43_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_43, sig_43, sig_43, pt_data_43.get("paciente_capaz", True), db=db_session)
            pdf_engine_43.generate_consentimiento_43(pt_data_43, c43_path, firma_data=sig_43)
            if os.path.exists(c43_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-SINPRO-PLT-43",
                    "slot": c43_slot,
                    "nombre": "Orden de Intubación Endotraqueal / Soporte Ventilatorio",
                    "path": c43_path,
                    "pages": get_pdf_page_count(c43_path),
                    "estatus": "Firmado" if sig_43.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 11. Egreso y Resumen Clínico (Formato 16 - HE-DIRMED-SINPRO-PLT-16)
        hist_16 = get_latest_historic_record(db_session, clean_pt, "16")
        c16_sql, c16_slot = fetch_current_format_record(
            db_session, clean_pt, "16", getattr(kh_database, "fetch_egreso_resumen_16", None)
        )
        sig_16 = obtener_firmas_completas_documento(db_session, clean_pt, "16", c16_slot)
        has_real_16 = bool(hist_16 or sig_16.get("sello_digital") or (c16_sql and not c16_sql.get("error") and (c16_sql.get("diagnostico") or c16_sql.get("mrnum"))))
        if has_real_16:
            pt_data_16 = {
                "paciente_nombre": patient_info.get("name", ""),
                "nombre": patient_info.get("name", ""),
                "expediente": patient_info.get("mrn", f"PT-{clean_pt}"),
                "pt_num": str(clean_pt),
                "fecha_nacimiento": patient_info.get("dob", ""),
                "edad": patient_info.get("age", ""),
                "sexo": patient_info.get("gender", ""),
                "cama": patient_info.get("cama", "HOSPITALIZACIÓN"),
                "fecha_ingreso": fecha_ingreso,
                "hora_ingreso": hora_ingreso,
                "fecha_egreso": fecha_hoy,
                "hora_egreso": hora_hoy,
                "diagnostico_ingreso": patient_info.get("diagnostico", ""),
                "diagnostico_egreso": patient_info.get("diagnostico", ""),
                "dr_elaboro": patient_info.get("attending_doctor", ""),
                "dr_tratante": patient_info.get("attending_doctor", ""),
                "cedula_elaboro": patient_info.get("cedula", ""),
                "cedula_tratante": patient_info.get("cedula", ""),
                "patient": patient_info
            }
            if hist_16 and hist_16.contenido_soap_json:
                try:
                    pt_data_16.update(json.loads(hist_16.contenido_soap_json))
                except Exception:
                    pass
            if c16_sql and isinstance(c16_sql, dict):
                pt_data_16.update({k: v for k, v in c16_sql.items() if v})
            c16_path = os.path.join(patient_cache_dir, f"doc_egreso_resumen_16_{clean_pt}.pdf")
            aplicar_firmas_a_pt_data(pt_data_16, sig_16, sig_16, pt_data_16.get("paciente_capaz", True), db=db_session)
            pdf_engine_16.generate_egreso_resumen_16(pt_data_16, c16_path, firma_data=sig_16)
            if os.path.exists(c16_path):
                generated_docs.append({
                    "codigo": "HE-DIRMED-SINPRO-PLT-16",
                    "slot": c16_slot,
                    "nombre": "Egreso y Resumen Clínico",
                    "path": c16_path,
                    "pages": get_pdf_page_count(c16_path),
                    "estatus": "Firmado" if sig_16.get("sello_digital") else "Registrado",
                    "firma": "Firma Electrónica / FEA"
                })

        # 12. Formatos firmados que también forman parte del catálogo clínico.
        # Se resuelven por ranura para no mezclar una firma con otra versión del ERP.
        formatos_adicionales = [
            (
                "HE-DIRMED-CONSUL-PLT-06",
                pdf_engine_06.generate_consentimiento_06,
                getattr(kh_database, "fetch_consentimiento_06", None),
                "Consentimiento para Procedimiento Anestésico",
                {"medico_anestesiologo": patient_info.get("attending_doctor", "")},
            ),
            (
                "HE-DIRMED-CONSUL-PLT-07",
                pdf_engine_07.generate_consentimiento_07,
                getattr(kh_database, "fetch_consentimiento_07", None),
                "Consentimiento Informado para Procedimientos Quirúrgicos",
                {"procedimiento_quirurgico": "INTERVENCIÓN QUIRÚRGICA PROGRAMADA"},
            ),
            (
                "HE-DIRMED-CONSUL-PLT-11",
                pdf_engine_11.generate_consentimiento_11,
                getattr(kh_database, "fetch_consentimiento_11", None),
                "Consentimiento de No Reanimación / Voluntad Anticipada",
                {"servicio": patient_info.get("cama", "URGENCIAS / MEDICINA INTERNA")},
            ),
            (
                "HE-DIRMED-CONSUL-PLT-19",
                pdf_engine_19.generate_consentimiento_19,
                getattr(kh_database, "fetch_consentimiento_19", None),
                "Consentimiento Informado para Histerectomía",
                {"servicio": patient_info.get("cama", "GINECOLOGÍA Y OBSTETRICIA")},
            ),
            (
                "HE-DIRMED-SINPRO-PLT-15",
                pdf_engine_15_ev.generate_egreso_voluntario_15,
                getattr(kh_database, "fetch_egreso_voluntario_15", None),
                "Egreso Voluntario",
                {"servicio": patient_info.get("cama", "HOSPITALIZACIÓN")},
            ),
        ]
        for code, generator, fetcher, title, defaults in formatos_adicionales:
            pt_data_extra, firma_extra, slot_extra, has_extra = _build_signed_format_snapshot(
                db_session,
                clean_pt,
                patient_info,
                code,
                fetcher=fetcher,
                defaults=defaults,
            )
            if not has_extra:
                continue
            extra_path = os.path.join(
                patient_cache_dir,
                f"doc_{code.rsplit('-', 1)[-1].replace('/', '_').lower()}_{clean_pt}.pdf",
            )
            generator(pt_data_extra, extra_path, firma_data=firma_extra)
            if os.path.exists(extra_path):
                generated_docs.append({
                    "codigo": code,
                    "nombre": title,
                    "path": extra_path,
                    "pages": get_pdf_page_count(extra_path),
                    "estatus": "Firmado" if firma_extra.get("sello_digital") else "Registrado",
                    "firma": "Firma biométrica / FEA",
                    "slot": slot_extra,
                })

        # 12 bis. Cualquier formato registrado para el paciente que todavía no
        # tenga motor visual especializado se integra por el renderer
        # universal. La ruta especializada sigue teniendo prioridad.
        generated_docs = _append_universal_patient_formats(
            db_session,
            clean_pt,
            dashboard_data,
            generated_docs,
            patient_cache_dir,
            verification_url=verification_url,
        )

        # =========================================================================
        # D) ANEXO FARMACOTERAPÉUTICO Y RÉGIMEN NUTRICIONAL
        # =========================================================================
        farmaco_path = os.path.join(patient_cache_dir, f"doc_anexo_farmaco_{clean_pt}.pdf")
        pdf_engine_expediente.generate_anexo_farmaco_dietas(dashboard_data, farmaco_path)
        if os.path.exists(farmaco_path):
            generated_docs.append({
                "codigo": "HE-DIRMED-ANEXO-FARMACO-DIET",
                "nombre": "Anexo Farmacoterapéutico, Régimen Dietético y Cuidados Clínicos",
                "path": farmaco_path,
                "pages": get_pdf_page_count(farmaco_path),
                "estatus": "Integrado",
                "firma": "Médico Tratante"
            })

        # =========================================================================
        # E) ANEXO DE ESTUDIOS PARACLÍNICOS (Laboratorio e Imagenología)
        # =========================================================================
        estudios_path = os.path.join(patient_cache_dir, f"doc_anexo_estudios_{clean_pt}.pdf")
        pdf_engine_expediente.generate_anexo_estudios(dashboard_data, estudios_path)
        if os.path.exists(estudios_path):
            generated_docs.append({
                "codigo": "HE-DIRMED-ANEXO-PARACLINICOS",
                "nombre": "Anexo de Estudios Paraclínicos (Laboratorio e Imagenología)",
                "path": estudios_path,
                "pages": get_pdf_page_count(estudios_path),
                "estatus": "Integrado",
                "firma": "Laboratorio / Gabinete"
            })

        # Incorporar también el reporte original de cada estudio cuando Vertical
        # conserva un PDF adjunto. El anexo anterior sólo mostraba el resumen.
        study_attachments = []
        seen_study_ids = set()
        for study in [
            *(dashboard_data.get("laboratorios", []) or []),
            *(dashboard_data.get("imagenologia", []) or []),
        ]:
            ptmt_num = study.get("ptmt_num") if isinstance(study, dict) else None
            if not ptmt_num or str(ptmt_num) in seen_study_ids:
                continue
            seen_study_ids.add(str(ptmt_num))
            try:
                blob, original_name, content_type = kh_database.get_study_document_binary(int(ptmt_num))
                raw_pdf = bytes(blob) if blob is not None else b""
                if not raw_pdf.startswith(b"%PDF"):
                    continue
                attachment_path = os.path.join(
                    patient_cache_dir,
                    f"doc_estudio_{re.sub(r'[^0-9A-Za-z_-]', '_', str(ptmt_num))}.pdf",
                )
                with open(attachment_path, "wb") as attachment_file:
                    attachment_file.write(raw_pdf)
                if os.path.exists(attachment_path):
                    try:
                        if not pypdf.PdfReader(attachment_path).pages:
                            continue
                    except Exception as exc:
                        print(f"Nota: se omitió un reporte PDF inválido del estudio {ptmt_num}: {exc}")
                        continue
                    study_attachments.append({
                        "codigo": "HE-DIRMED-ANEXO-ESTUDIO",
                        "nombre": (
                            f"Reporte original de {'laboratorio' if study.get('tipo') == 'Laboratorio' else 'imagenología'}: "
                            f"{study.get('estudio') or original_name or ptmt_num}"
                        ),
                        "path": attachment_path,
                        "pages": get_pdf_page_count(attachment_path),
                        "estatus": "Integrado",
                        "firma": "Documento emitido por Vertical",
                    })
            except (TypeError, ValueError, OSError) as exc:
                print(f"Nota: no se pudo integrar el PDF del estudio {ptmt_num}: {exc}")

        generated_docs.extend(study_attachments)

        signature_report = build_expediente_signature_report(
            db_session, clean_pt, generated_docs
        )
        if signature_report.get("bloqueos"):
            raise ExpedienteSignatureReconciliationRequired(signature_report)

        # El anexo se genera en esta misma corrida y consulta cada formato que
        # terminó integrado. Así la trazabilidad no depende de PDFs guardados
        # de una compilación anterior y conserva evidencia histórica o nativa
        # que no debe confundirse con una FEA vigente.
        signature_ledger_items = _build_signature_ledger_items(
            db_session, clean_pt, dashboard_data, generated_docs
        )
        signature_ledger_path = os.path.join(
            patient_cache_dir, f"doc_anexo_trazabilidad_firmas_{clean_pt}.pdf"
        )
        pdf_engine_expediente.generate_anexo_trazabilidad_firmas(
            patient_info,
            signature_ledger_path,
            signature_ledger_items,
        )
        if os.path.exists(signature_ledger_path):
            generated_docs.append({
                "codigo": "HE-DIRMED-ANEXO-TRAZABILIDAD-FIRMAS",
                "nombre": "Anexo de Trazabilidad y Conservación de Firmas",
                "path": signature_ledger_path,
                "pages": get_pdf_page_count(signature_ledger_path),
                "estatus": "Integrado",
                "firma": "Trazabilidad clínica",
            })

        # =========================================================================
        # F) FOLIACIÓN DINÁMICA, ÍNDICE Y CARÁTULA OFICIAL
        # =========================================================================
        def build_docs_summary(cover_pages: int):
            cover_folios = f"1 - {cover_pages}" if cover_pages > 1 else "1"
            summary = [{
                "num": 1,
                "codigo": "HE-DIRMED-EXPEDIENTE-COMPLETO",
                "nombre": "Carátula y Portada de Identificación del Expediente",
                "folios": cover_folios,
                "estatus": "Integrado",
                "firma": "Institucional"
            }]
            current = cover_pages + 1
            for idx, doc in enumerate(generated_docs):
                p_cnt = doc.get("pages", 1)
                start_p = current
                end_p = current + p_cnt - 1
                folio_str = f"{start_p} - {end_p}" if start_p != end_p else str(start_p)
                current += p_cnt
                summary.append({
                    "num": idx + 2,
                    "codigo": doc.get("codigo", ""),
                    "nombre": doc.get("nombre", ""),
                    "folios": folio_str,
                    "estatus": doc.get("estatus", "Integrado"),
                    "firma": doc.get("firma", "Certificado")
                })
            return summary, current

        # La carátula puede ocupar dos páginas cuando el índice es largo. Se
        # genera una primera vez, se mide y se vuelve a generar sólo si hace
        # falta, para que folios e índice coincidan con el PDF final.
        docs_summary_for_cover, current_page = build_docs_summary(1)

        firma_urg = obtener_firmas_completas_documento(db_session, clean_pt, "87", 0)
        caratula_path = os.path.join(patient_cache_dir, f"doc_caratula_{clean_pt}.pdf")
        pdf_engine_expediente.generate_caratula_expediente(
            dashboard_data,
            caratula_path,
            docs_summary=docs_summary_for_cover,
            firma_data=firma_urg,
            verification_url=verification_url,
        )
        cover_pages = get_pdf_page_count(caratula_path)
        if cover_pages != 1:
            docs_summary_for_cover, current_page = build_docs_summary(cover_pages)
            pdf_engine_expediente.generate_caratula_expediente(
                dashboard_data,
                caratula_path,
                docs_summary=docs_summary_for_cover,
                firma_data=firma_urg,
                verification_url=verification_url,
            )
            cover_pages = get_pdf_page_count(caratula_path)

        # =========================================================================
        # G) FUSIÓN MAESTRA CON pypdf.PdfWriter
        # =========================================================================
        writer = pypdf.PdfWriter()
        # 1. Carátula
        writer.append(caratula_path)
        # 2. Documentos en orden clínico
        for doc in generated_docs:
            writer.append(doc["path"])

        final_filename = f"expediente_completo_{clean_pt}.pdf"
        writer.add_metadata({
            "/Title": f"Expediente_Completo_PT_{clean_pt}",
            "/Author": "Hospital Escandón",
            "/Subject": "Expediente Clínico Integrado NOM-004 / NOM-024",
            "/Creator": "Bitácora Médica HES",
        })
        
        with open(final_output_path, "wb") as f_out:
            writer.write(f_out)
        writer.close()

        print(f"Expediente Clínico Completo generado exitosamente en: {final_output_path} (Total páginas: {current_page - 1})")
        if return_metadata:
            return final_output_path, final_filename, signature_report
        return final_output_path, final_filename
    finally:
        if own_db and db_session:
            db_session.close()

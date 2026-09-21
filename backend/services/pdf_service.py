import os
import sys
import json
import re
import datetime
import hashlib
from typing import Optional, Dict, Any, Tuple, List
import pypdf

# Import engines
try:
    import pdf_generator
    import pdf_engine_v2
    import pdf_engine_24
    import pdf_engine_02
    import pdf_engine_04
    import pdf_engine_08
    import pdf_engine_12
    import pdf_engine_15
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
    from backend import pdf_engine_08
    from backend import pdf_engine_12
    from backend import pdf_engine_15
    from backend import pdf_engine_25
    from backend import pdf_engine_32_01
    from backend import pdf_engine_34_01
    from backend import pdf_engine_eed
    from backend import pdf_engine_43
    from backend import pdf_engine_expediente
    from backend import kh_database

import glob

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
STATIC_PDFS_DIR = os.path.join(BACKEND_DIR, "static", "pdfs")
CACHE_PDFS_DIR = os.path.join(STATIC_PDFS_DIR, "cache_expedientes")
SCRATCH_DIR = os.path.join(PROJECT_ROOT, "scratch")

os.makedirs(STATIC_PDFS_DIR, exist_ok=True)
os.makedirs(CACHE_PDFS_DIR, exist_ok=True)
os.makedirs(SCRATCH_DIR, exist_ok=True)


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

        clean_pt = re.sub(r'[^0-9]', '', str(pt_num)) or str(pt_num)
        query = db_session.query(models.FirmaDocumentoClinico).filter(
            (models.FirmaDocumentoClinico.pt_num == str(pt_num)) | 
            (models.FirmaDocumentoClinico.pt_num == str(clean_pt)) | 
            (models.FirmaDocumentoClinico.pt_num == f"PT-{clean_pt}"),
            models.FirmaDocumentoClinico.codigo_formato.ilike(f"%{codigo_formato}%"),
            models.FirmaDocumentoClinico.estado == "ACTIVA"
        )
        if evolution_slot is not None and int(evolution_slot) > 0:
            query = query.filter(
                (models.FirmaDocumentoClinico.evolution_slot == int(evolution_slot)) | 
                (models.FirmaDocumentoClinico.evolution_slot == 0) | 
                (models.FirmaDocumentoClinico.evolution_slot == None)
            )
        firmas = query.order_by(models.FirmaDocumentoClinico.fecha_hora_firma.desc()).all()

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
            elif rol in ("PACIENTE", "REPRESENTANTE_LEGAL", "TUTOR", "FAMILIAR", "CONTACTO") and not res["sello_paciente"]:
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
                    res["rol_firmante_paciente"] = "REPRESENTANTE_LEGAL"
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

        return res
    except Exception as e:
        print(f"Error fetching signatures in pdf_service: {e}")
        return {}


def aplicar_firmas_a_pt_data(pt_data: dict, sig_info: dict, firma_data: dict, paciente_capaz: bool = True, db: Any = None):
    """
    Inyecta de forma segura los sellos y datos de firmantes presenciales en pt_data y firma_data,
    garantizando que:
    1. Si hay sellos biométricos firmados en sig_info, se inyectan con su respectivo sello.
    2. Si los campos de Testigo 1, Testigo 2 o Tutor/Representante están vacíos, se RELLENAN AUTOMÁTICAMENTE
       desde el catálogo de firmantes registrados para este paciente (BiometriaFirmanteEpisodio / Trabajo Social PTCN).
    """
    if sig_info and isinstance(sig_info, dict):
        if sig_info.get("sello_paciente"):
            if not paciente_capaz:
                tutor_nom = pt_data.get("pariente") or pt_data.get("representante_legal") or pt_data.get("responsable") or sig_info.get("firmante_paciente") or "TUTOR RESPONSABLE"
                tutor_parentesco = pt_data.get("parentesco") or (sig_info.get("parentesco_paciente") if sig_info.get("parentesco_paciente") not in ("Paciente", "PACIENTE", "Titular") else None) or "Tutor / Representante Legal"
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

    # AUTO-LLAMADO DE CONTACTOS / TESTIGOS / TUTORES REGISTRADOS (Fallback Automático):
    needs_t1 = not bool(pt_data.get("testigo1") or pt_data.get("testigo_1"))
    needs_t2 = not bool(pt_data.get("testigo2") or pt_data.get("testigo_2"))
    needs_tutor = not paciente_capaz and not bool(pt_data.get("pariente") or pt_data.get("representante_legal") or pt_data.get("responsable"))

    if needs_t1 or needs_t2 or needs_tutor:
        close_db = False
        local_db = db
        if not local_db:
            try:
                try:
                    import database
                except ImportError:
                    from backend import database
                local_db = database.SessionLocal()
                close_db = True
            except Exception:
                local_db = None

        if local_db:
            try:
                try:
                    import models
                except ImportError:
                    from backend import models
                pt_num_val = pt_data.get("pt_num") or pt_data.get("mrn") or pt_data.get("expediente") or ""
                clean_pt = re.sub(r'[^0-9]', '', str(pt_num_val)) or str(pt_num_val)
                firmantes_ep = local_db.query(models.BiometriaFirmanteEpisodio).filter(
                    (models.BiometriaFirmanteEpisodio.pt_num == str(pt_num_val)) |
                    (models.BiometriaFirmanteEpisodio.pt_num == str(clean_pt)) |
                    (models.BiometriaFirmanteEpisodio.pt_num == f"PT-{clean_pt}"),
                    models.BiometriaFirmanteEpisodio.estado == "ACTIVO"
                ).all()

                # Buscar Testigo 1
                if needs_t1:
                    t1_cand = next((f for f in firmantes_ep if f.tipo_firmante in ("TESTIGO_1", "TESTIGO")), None)
                    if not t1_cand:
                        t1_cand = next((f for f in firmantes_ep if f.tipo_firmante not in ("PACIENTE", "TITULAR")), None)
                    if t1_cand:
                        pt_data["testigo1"] = t1_cand.nombre_completo
                        pt_data["testigo_1"] = t1_cand.nombre_completo
                        pt_data["testigo1_nombre"] = t1_cand.nombre_completo
                        pt_data["parentesco_testigo1"] = t1_cand.parentesco or "Familiar / Testigo Presencial"
                        pt_data["parentesco_testigo"] = t1_cand.parentesco or "Familiar / Testigo Presencial"
                        pt_data["domicilio_testigo1"] = t1_cand.domicilio or "Conocido en expediente clínico"
                        pt_data["domicilio_testigo"] = t1_cand.domicilio or "Conocido en expediente clínico"
                        pt_data["identificacion_testigo1"] = t1_cand.identificacion_oficial or "INE / Identificación Oficial"
                        pt_data["identificacion_testigo"] = t1_cand.identificacion_oficial or "INE / Identificación Oficial"

                # Buscar Testigo 2
                if needs_t2:
                    t2_cand = next((f for f in firmantes_ep if f.tipo_firmante == "TESTIGO_2"), None)
                    if t2_cand:
                        pt_data["testigo2"] = t2_cand.nombre_completo
                        pt_data["testigo_2"] = t2_cand.nombre_completo
                        pt_data["testigo2_nombre"] = t2_cand.nombre_completo
                        pt_data["parentesco_testigo2"] = t2_cand.parentesco or "Familiar / Testigo Presencial"
                        pt_data["domicilio_testigo2"] = t2_cand.domicilio or "Conocido en expediente clínico"
                        pt_data["identificacion_testigo2"] = t2_cand.identificacion_oficial or "INE / Identificación Oficial"

                # Buscar Tutor / Representante Legal si el paciente no es capaz
                if needs_tutor:
                    tut_cand = next((f for f in firmantes_ep if f.tipo_firmante in ("REPRESENTANTE_LEGAL", "TUTOR", "FAMILIAR", "CONTACTO")), None)
                    if not tut_cand:
                        tut_cand = next((f for f in firmantes_ep if f.tipo_firmante != "PACIENTE"), None)
                    if tut_cand:
                        tut_parent = tut_cand.parentesco if tut_cand.parentesco and str(tut_cand.parentesco).upper() not in ("PACIENTE", "TITULAR", "DIRECTO") else "Tutor / Representante Legal"
                        pt_data["pariente"] = tut_cand.nombre_completo
                        pt_data["representante_legal"] = tut_cand.nombre_completo
                        pt_data["declarante"] = tut_cand.nombre_completo
                        pt_data["responsable"] = tut_cand.nombre_completo
                        pt_data["parentesco"] = tut_parent
                        pt_data["parentesco_declarante"] = tut_parent
                        pt_data["parentesco_paciente"] = tut_parent
                        pt_data["domicilio_paciente"] = tut_cand.domicilio or "Conocido en expediente clínico"
                        pt_data["domicilio_declarante"] = tut_cand.domicilio or "Conocido en expediente clínico"
                        pt_data["identificacion_paciente"] = tut_cand.identificacion_oficial or "INE / Identificación Oficial"
                        pt_data["identificacion_declarante"] = tut_cand.identificacion_oficial or "INE / Identificación Oficial"

            finally:
                if close_db and local_db:
                    local_db.close()

    if isinstance(firma_data, dict):
        for k, v in pt_data.items():
            if k not in firma_data or not firma_data[k]:
                firma_data[k] = v


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
            models.HistoricoNotaClinica.codigo_formato.ilike(f"%{format_code}%")
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
    pdf_path = pdf_engine_eed.generar_pdf_eed(pt_data)
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


def generate_consentimiento_15_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Cesárea / Disentimiento."""
    pdf_filename = f"CI_15_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    if firma_data is None:
        firma_data = {}
    aplicar_firmas_a_pt_data(pt_data, firma_data, firma_data, pt_data.get("paciente_capaz", True))
    pdf_engine_15.generate_consentimiento_15(pt_data, pdf_path, firma_data=firma_data)
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


def generate_expediente_completo_pdf(pt_num: str, db_session=None) -> Tuple[str, str]:
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
        patient_info = dashboard_data.get("patient", {})
        fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
        hora_hoy = datetime.datetime.now().strftime("%H:%M")
        fecha_ingreso = patient_info.get("fecha_ingreso", fecha_hoy) or fecha_hoy
        hora_ingreso = patient_info.get("hora_ingreso", hora_hoy) or hora_hoy

        # Directorio temporal de partes para este paciente
        patient_cache_dir = os.path.join(CACHE_PDFS_DIR, f"pt_{clean_pt}")
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
            firma_urg = obtener_firmas_completas_documento(db_session, clean_pt, "87", 0)
            urg_path = os.path.join(patient_cache_dir, f"doc_urgencias_{clean_pt}.pdf")
            pdf_engine_v2.generate_nota_urgencias(
                pt_data_urg, e1, e2, e3, urg_path, is_general=True, firma_data=firma_urg, evoluciones_list=evoluciones_urg
            )
            if os.path.exists(urg_path):
                p_count = get_pdf_page_count(urg_path)
                generated_docs.append({
                    "codigo": "HE-DIRMED-SINPRO-PLT-87/01",
                    "nombre": f"Nota Médica de Evolución de Urgencias ({len(evoluciones_urg)} evoluciones)" if evoluciones_urg else "Nota Médica de Evolución de Urgencias",
                    "path": urg_path,
                    "pages": p_count,
                    "estatus": "Integrado",
                    "firma": "Firma Biométrica" if firma_urg.get("sello_digital") else "Validado"
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
            firma_hosp = obtener_firmas_completas_documento(db_session, clean_pt, "24", 0)
            hosp_path = os.path.join(patient_cache_dir, f"doc_hospitalizacion_{clean_pt}.pdf")
            pdf_engine_24.generate_nota_hospitalizacion(
                pt_data_hosp, None, None, None, hosp_path, is_general=True, firma_data=firma_hosp, evoluciones_list=evoluciones_hosp
            )
            if os.path.exists(hosp_path):
                p_count = get_pdf_page_count(hosp_path)
                generated_docs.append({
                    "codigo": "HE-DIRMED-CONSUL-PLT-24",
                    "nombre": f"Nota Médica de Evolución de Hospitalización ({len(evoluciones_hosp)} evoluciones)" if evoluciones_hosp else "Nota Médica de Evolución de Hospitalización",
                    "path": hosp_path,
                    "pages": p_count,
                    "estatus": "Integrado",
                    "firma": "Firma Biométrica" if firma_hosp.get("sello_digital") else "Validado"
                })

        # =========================================================================
        # C) CONSENTIMIENTOS INFORMADOS OFICIALES (Regeneración fresca con firmas activas)
        # =========================================================================

        # 1. CI 02 (Tratamiento Quirúrgico / Disentimiento)
        hist_02 = get_latest_historic_record(db_session, clean_pt, "02")
        sig_02 = obtener_firmas_completas_documento(db_session, clean_pt, "02", 0)
        c02_sql = kh_database.fetch_consentimiento_02(clean_pt) if hasattr(kh_database, 'fetch_consentimiento_02') else None
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
                    "nombre": "Consentimiento Informado para Tratamiento Quirúrgico",
                    "path": c02_path,
                    "pages": get_pdf_page_count(c02_path),
                    "estatus": "Firmado" if sig_02.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 2. CI 04 (Catéter Venoso Central)
        hist_04 = get_latest_historic_record(db_session, clean_pt, "04")
        sig_04 = obtener_firmas_completas_documento(db_session, clean_pt, "04", 0)
        c04_sql = kh_database.fetch_consentimiento_04(clean_pt) if hasattr(kh_database, 'fetch_consentimiento_04') else None
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
                    "nombre": "Consentimiento Informado: Catéter Venoso Central",
                    "path": c04_path,
                    "pages": get_pdf_page_count(c04_path),
                    "estatus": "Firmado" if sig_04.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 3. CI 08 (Admisión Continua y Procedimientos Diagnósticos)
        hist_08 = get_latest_historic_record(db_session, clean_pt, "08")
        sig_08 = obtener_firmas_completas_documento(db_session, clean_pt, "08", 0)
        c08_sql = kh_database.fetch_consentimiento_08(clean_pt) if hasattr(kh_database, 'fetch_consentimiento_08') else None
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
                    "nombre": "Consentimiento Informado: Admisión Continua y Diagnóstico",
                    "path": c08_path,
                    "pages": get_pdf_page_count(c08_path),
                    "estatus": "Firmado" if sig_08.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 4. CI 12 (Revisión Gineco-Obstétrica Hosp/Urg)
        hist_12 = get_latest_historic_record(db_session, clean_pt, "12")
        sig_12 = obtener_firmas_completas_documento(db_session, clean_pt, "12", 0)
        c12_sql = kh_database.fetch_consentimiento_12(clean_pt) if hasattr(kh_database, 'fetch_consentimiento_12') else None
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
                    "nombre": "Consentimiento Informado: Revisión Gineco-Obstétrica (Hosp/Urg)",
                    "path": c12_path,
                    "pages": get_pdf_page_count(c12_path),
                    "estatus": "Firmado" if sig_12.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 5. CI 15 (Cesárea / Procedimientos Obstétricos)
        hist_15 = get_latest_historic_record(db_session, clean_pt, "15")
        sig_15 = obtener_firmas_completas_documento(db_session, clean_pt, "15", 0)
        c15_sql = kh_database.fetch_consentimiento_15(clean_pt) if hasattr(kh_database, 'fetch_consentimiento_15') else None
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
                    "nombre": "Consentimiento Informado para Procedimiento de Cesárea",
                    "path": c15_path,
                    "pages": get_pdf_page_count(c15_path),
                    "estatus": "Firmado" if sig_15.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

        # 6. CI 25 (Revisión Ginecológica Consulta Externa)
        hist_25 = get_latest_historic_record(db_session, clean_pt, "25")
        sig_25 = obtener_firmas_completas_documento(db_session, clean_pt, "25", 0)
        c25_sql = kh_database.fetch_consentimiento_25(clean_pt) if hasattr(kh_database, 'fetch_consentimiento_25') else None
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
        sig_34 = obtener_firmas_completas_documento(db_session, clean_pt, "34", 0)
        c34_sql = kh_database.fetch_consentimiento_34_01(clean_pt) if hasattr(kh_database, 'fetch_consentimiento_34_01') else None
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
            pdf_engine_eed.generar_pdf_eed(pt_data_eed, force_output_path=ceed_path)
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
        sig_43 = obtener_firmas_completas_documento(db_session, clean_pt, "43", 0)
        c43_sql = kh_database.fetch_consentimiento_43(clean_pt) if hasattr(kh_database, 'fetch_consentimiento_43') else None
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
                    "nombre": "Orden de Intubación Endotraqueal / Soporte Ventilatorio",
                    "path": c43_path,
                    "pages": get_pdf_page_count(c43_path),
                    "estatus": "Firmado" if sig_43.get("sello_digital") else "Registrado",
                    "firma": "Dactilar / Sello"
                })

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

        # =========================================================================
        # F) FOLIACIÓN DINÁMICA, ÍNDICE Y CARÁTULA OFICIAL
        # =========================================================================
        docs_summary_for_cover = [
            {
                "num": 1,
                "codigo": "HE-DIRMED-EXPEDIENTE-COMPLETO",
                "nombre": "Carátula y Portada de Identificación del Expediente",
                "folios": "1",
                "estatus": "Integrado",
                "firma": "Institucional"
            }
        ]

        current_page = 2
        for idx, doc in enumerate(generated_docs):
            p_cnt = doc.get("pages", 1)
            start_p = current_page
            end_p = current_page + p_cnt - 1
            folio_str = f"{start_p} - {end_p}" if start_p != end_p else str(start_p)
            current_page += p_cnt

            docs_summary_for_cover.append({
                "num": idx + 2,
                "codigo": doc.get("codigo", ""),
                "nombre": doc.get("nombre", ""),
                "folios": folio_str,
                "estatus": doc.get("estatus", "Integrado"),
                "firma": doc.get("firma", "Certificado")
            })

        firma_urg = obtener_firmas_completas_documento(db_session, clean_pt, "87", 0)
        caratula_path = os.path.join(patient_cache_dir, f"doc_caratula_{clean_pt}.pdf")
        pdf_engine_expediente.generate_caratula_expediente(
            dashboard_data, caratula_path, docs_summary=docs_summary_for_cover, firma_data=firma_urg
        )

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
        final_output_path = os.path.join(STATIC_PDFS_DIR, final_filename)
        
        with open(final_output_path, "wb") as f_out:
            writer.write(f_out)
        writer.close()

        print(f"Expediente Clínico Completo generado exitosamente en: {final_output_path} (Total páginas: {current_page - 1})")
        return final_output_path, final_filename
    finally:
        if own_db and db_session:
            db_session.close()


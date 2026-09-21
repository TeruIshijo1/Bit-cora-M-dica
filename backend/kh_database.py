import pyodbc
import os
import functools
import re
import datetime
import uuid
import socket
import time
import json
from dotenv import load_dotenv
from fastapi import HTTPException


class KHMutationError(RuntimeError):
    """Explicit SQL Server mutation failure; never convert this to success."""

    retryable = False


class KHRetryableMutationError(KHMutationError):
    retryable = True


class KHPermanentMutationError(KHMutationError):
    retryable = False


_IDEMPOTENT_GUID_TARGETS = {
    "save_or_update_nota_urgencias": ("MR_NE_URG", "MR_NE_URGID", "MRNum_NE_URG"),
    "save_or_update_nota_hospitalizacion": ("MR_24_HOJA_EVOL", "MR_24_HOJA_EVOLID", "MRNum_24_HOJA_EVOL"),
    "save_or_update_consentimiento_32_01": ("MR_CI_ETE_CARD", "MR_CI_ETE_CARDID", "MRNum_CI_ETE_CARD"),
    "save_patient_vitals_ptvs": ("PTVS", "PTVSID", "PTVSNum"),
    "save_patient_allergy_ptal": ("PTAL", "PTALID", "PTALNum"),
    "save_or_update_consentimiento_eed": ("MR_CI_EED", "MR_CI_EEDID", "MRNum_CI_EED"),
    "save_or_update_consentimiento_25": ("MR_CI_RGO_CE", "MR_CI_RGO_CEID", "MRNum_CI_RGO_CE"),
    "save_or_update_consentimiento_34_01": ("MR_CI_EMI", "MR_CI_EMIID", "MRNum_CI_EMI"),
    "save_or_update_consentimiento_12": ("MR_CI_RGO_HU", "MR_CI_RGO_HUID", "MRNum_CI_RGO_HU"),
    "save_or_update_consentimiento_04": ("MR_CI_CC", "MR_CI_CCID", "MRNum_CI_CC"),
    "save_or_update_consentimiento_15": ("MR_CI_CES", "MR_CI_CESID", "MRNum_CI_CES"),
    "save_or_update_consentimiento_02": ("MR_02_CI_TRATAMIENTO_QUIRURGICO", "MR_02_CI_TRATAMIENTO_QUIRURGICOID", "MRNum_02_CI_TRATAMIENTO_QUIRURGICO"),
    "save_or_update_consentimiento_08": ("MR_08_CI_DIAGNOSTICO_ADMISION_CONTI", "MR_08_CI_DIAGNOSTICO_ADMISION_CONTIID", "MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI"),
    "save_or_update_consentimiento_43": ("MR_CI_OI", "MR_CI_OIID", "MRNum_CI_OI"),
    "save_or_update_consentimiento_11": ("MR_CI_NO_REANIMACION", "MR_CI_NO_REANIMACIONID", "MRNum_CI_NO_REANIMACION"),
    "save_or_update_consentimiento_19": ("MR_CI_HISTERECTOMIA", "MR_CI_HISTERECTOMIAID", "MRNum_CI_HISTERECTOMIA"),
    "save_or_update_egreso_voluntario_15": ("MR_EV_HOSP", "MR_EV_HOSPID", "MRNum_EV_HOSP"),
    "save_or_update_consentimiento_06": ("MR_CI_APA", "MR_CI_APAID", "MRNum_CI_APA"),
    "save_or_update_consentimiento_07": ("MR_CI_PQ", "MR_CI_PQID", "MRNum_CI_PQ"),
}


def _kh_error_type(message: str):
    lowered = message.lower()
    retryable = (
        "timeout", "timed out", "deadlock", "connection", "network",
        "temporar", "unavailable", "08s01", "40001", "1205",
    )
    return KHRetryableMutationError if any(token in lowered for token in retryable) else KHPermanentMutationError


def explicit_kh_mutation(func):
    """Make legacy mutators fail explicitly and accept a correlation id."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        operation_id = kwargs.pop("operation_id", None)
        operation_guid = None
        guid_target = _IDEMPOTENT_GUID_TARGETS.get(func.__name__)
        if operation_id and guid_target:
            operation_guid = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"clinical-sync:{operation_id}:{func.__name__}")
            ).upper()
            conn = get_kh_connection()
            if not conn:
                raise KHRetryableMutationError("SQL Server no disponible para comprobar idempotencia")
            try:
                cursor = conn.cursor()
                table_name, guid_column, pk_column = guid_target
                cursor.execute(
                    f"SELECT TOP 1 {pk_column} FROM {table_name} WHERE {guid_column} = ?",
                    (operation_guid,),
                )
                existing = cursor.fetchone()
                if existing:
                    return {
                        "success": True,
                        "idempotent": True,
                        "external_id": existing[0],
                    }
            except Exception as exc:
                error_type = _kh_error_type(str(exc))
                raise error_type(
                    f"SQL Server idempotency check failed [{operation_id}]: {exc}"
                ) from exc
            finally:
                conn.close()
        if operation_id and len(args) >= 2 and isinstance(args[1], dict):
            mutable_args = list(args)
            mutable_args[1] = dict(args[1])
            mutable_args[1]["_operation_id"] = str(operation_id)
            if operation_guid:
                mutable_args[1]["_operation_guid"] = operation_guid
            args = tuple(mutable_args)
        elif operation_guid:
            kwargs["_operation_guid"] = operation_guid
        try:
            result = func(*args, **kwargs)
        except KHMutationError:
            raise
        except Exception as exc:
            error_type = _kh_error_type(str(exc))
            raise error_type(
                f"SQL Server mutation failed [{operation_id or 'uncorrelated'}]: {exc}"
            ) from exc
        if result is False or result is None:
            raise KHRetryableMutationError(
                f"SQL Server did not confirm mutation [{operation_id or 'uncorrelated'}]"
            )
        if isinstance(result, dict) and (result.get("error") or result.get("Error")):
            message = str(result.get("error") or result.get("Error"))
            error_type = _kh_error_type(message)
            raise error_type(
                f"SQL Server mutation failed [{operation_id or 'uncorrelated'}]: {message}"
            )
        return result
    return wrapper

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

def raise_kh_unavailable():
    """Lanza excepción HTTP 503 cuando la base de datos central de SQL Server no responde."""
    raise HTTPException(
        status_code=503,
        detail="Sistema hospitalario central no disponible, intente más tarde"
    )

_LAST_CONN_FAIL_TIME = 0

def check_tcp_reachable(server_str, timeout=1.0):
    """Verifica en < 1s si el servidor y puerto de SQL Server responden."""
    try:
        if ',' in server_str:
            parts = server_str.split(',')
            host = parts[0].strip()
            port = int(parts[1].strip())
        elif ':' in server_str:
            parts = server_str.split(':')
            host = parts[0].strip()
            port = int(parts[1].strip())
        else:
            host = server_str.strip()
            port = 1433
            
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def get_kh_connection():
    """Establece una conexión directa con SQL Server (KH_HE) con pre-chequeo ultra rápido."""
    global _LAST_CONN_FAIL_TIME
    load_dotenv()
    server = os.getenv('KH_SERVER')
    database = os.getenv('KH_DATABASE', 'KH_HE')
    username = os.getenv('KH_USERNAME')
    password = os.getenv('KH_PASSWORD')

    if os.getenv('APP_ENV', '').strip().lower() == 'test':
        from testing.database_guards import validate_sql_server_test_database
        validate_sql_server_test_database(os.getenv('APP_ENV'), database)

    if not server:
        return None

    # Limpiar espacios o comillas en el servidor
    server = server.strip().strip('"').strip("'")

    # Si falló hace menos de 8 segundos, evitar reintentos bloqueantes
    if time.time() - _LAST_CONN_FAIL_TIME < 8:
        return None

    # Pre-chequeo TCP rápido de 1 segundo para no congelar la app si el túnel está cerrado
    if not check_tcp_reachable(server, timeout=1.0):
        _LAST_CONN_FAIL_TIME = time.time()
        print(f"[SQL_SERVER] Servidor {server} no responde en TCP (puerto cerrado o tunel inactivo).")
        return None

    installed_drivers = pyodbc.drivers()
    drivers_to_try = []
    
    if os.getenv('KH_ODBC_DRIVER'):
        drivers_to_try.append(os.getenv('KH_ODBC_DRIVER'))
    
    preferred_drivers = [
        'ODBC Driver 18 for SQL Server',
        'ODBC Driver 17 for SQL Server',
        'SQL Server Native Client 11.0',
        'SQL Server'
    ]
    for d in preferred_drivers:
        if d in installed_drivers and d not in drivers_to_try:
            drivers_to_try.append(d)
    
    for d in installed_drivers:
        if 'SQL' in d and d not in drivers_to_try:
            drivers_to_try.append(d)

    if not drivers_to_try:
        drivers_to_try = ['SQL Server']

    last_error = None
    for drv in drivers_to_try:
        driver_str = drv if (drv.startswith('{') and drv.endswith('}')) else f'{{{drv}}}'
        
        conn_strings = [
            f'DRIVER={driver_str};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;Encrypt=no;',
            f'DRIVER={driver_str};SERVER={server};DATABASE={database};UID={username};PWD={password};Network=DBMSSOCN;'
        ]
        
        for cs in conn_strings:
            try:
                conn = pyodbc.connect(cs, timeout=3)
                return conn
            except Exception as e:
                last_error = e
                continue

    _LAST_CONN_FAIL_TIME = time.time()
    print(f"Error conectando a KH_HE (Servidor intentado: '{server}'): {last_error}")
    return None

def fetch_camas():
    """Obtiene el estatus actual de las camas desde KH_HE cruzando V_MRPT, PC y PR."""
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()
    
    try:
        cursor = conn.cursor()
        query = """
        WITH MasterCamas AS (
            SELECT MIN(RoomCode) AS RoomCode, RoomName 
            FROM V_MRPT 
            WHERE (RoomName LIKE '%CAMA%' OR RoomName LIKE '%QUIR%' OR RoomCode LIKE '%UTI%' OR RoomName LIKE '%TERAPIA%' OR RoomName LIKE '%CUBICULO%' OR RoomCode = 'CONSCUR')
              AND RoomName NOT LIKE '%VIRTUAL%'
              AND RoomName NOT LIKE '%VIRT%'
              AND RoomName NOT LIKE '%CV%'
            GROUP BY RoomName
        ),
        ActiveBeds AS (
            SELECT 
                c.Habitacion as RoomName,
                MAX(r.PTNum) as PTNum,
                c.Paciente as PatientName,
                c.MedicoTratante as DoctorName,
                MAX(r.EntryDate) as pt_date
            FROM UDR_AD_CENSO c
            LEFT JOIN UDR_RPT_HABITACION r 
                ON c.PCNum = r.PCNum AND c.Habitacion = r.FRName
            GROUP BY c.Habitacion, c.Paciente, c.MedicoTratante
        )
        SELECT 
            m.RoomCode,
            m.RoomName,
            u.PTNum,
            u.PatientName,
            u.DoctorName,
            u.pt_date,
            CASE 
                WHEN u.PatientName IS NOT NULL THEN 'Ocupada'
                ELSE 'Libre'
            END as Estatus
        FROM MasterCamas m
        LEFT JOIN ActiveBeds u ON m.RoomName = u.RoomName
        ORDER BY m.RoomName
        """
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            row_dict = {}
            for i, value in enumerate(row):
                row_dict[columns[i]] = str(value) if value is not None else ""
            results.append(row_dict)
        return results
    except Exception as e:
        print(f"Error consultando camas: {e}")
        return [{"Error": str(e)}]
    finally:
        conn.close()

def fetch_patient_info_and_timeline(pt_num: str):
    """
    Fetches the patient's demographic information and their movement timeline.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()
    try:
        cursor = conn.cursor()
        
        # 1. Fetch Demographics
        demo_query = """
        SELECT TOP 1 
            FullName, BirthDate, Gender, BloodType, MaritalStatus, Religion
        FROM V_MRPT
        WHERE PTNum = ?
        """
        cursor.execute(demo_query, (pt_num,))
        demo_row = cursor.fetchone()
        
        demographics = {}
        if demo_row:
            demographics = {
                "Paciente": str(demo_row[0]) if demo_row[0] else "",
                "BirthDate": str(demo_row[1]) if demo_row[1] else "",
                "Gender": str(demo_row[2]) if demo_row[2] else "",
                "BloodType": str(demo_row[3]) if demo_row[3] else "",
                "MaritalStatus": str(demo_row[4]) if demo_row[4] else "",
                "Religion": str(demo_row[5]) if demo_row[5] else "",
            }
            
        # 2. Fetch Timeline
        timeline_query = """
        SELECT FRName as RoomName, EntryDate, ClosedOn as ExitDate
        FROM UDR_RPT_HABITACION
        WHERE PTNum = ?
        ORDER BY EntryDate ASC
        """
        cursor.execute(timeline_query, (pt_num,))
        
        timeline = []
        for row in cursor.fetchall():
            timeline.append({
                "RoomName": str(row[0]) if row[0] else "",
                "EntryDate": str(row[1]) if row[1] else "",
                "ExitDate": str(row[2]) if row[2] else ""
            })
            
        return {
            "demographics": demographics,
            "timeline": timeline
        }
        
    except Exception as e:
        print(f"Error fetching patient info: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

_STUDY_ABBREV_MAP = {
    'BH': ['BIOMETRIA', 'HEMATICA', 'PLAQUETAS'],
    'QSA': ['QUIMICA', 'SANGUINEA', 'GLUCOSA', 'UREA', 'CREATININA', 'BIOQUIMICO'],
    'QS': ['QUIMICA', 'SANGUINEA'],
    'ES': ['ELECTROLITOS', 'SERICOS', 'SODIO', 'POTASIO', 'CLORO'],
    'ELEC': ['ELECTROLITOS'],
    'TP': ['TIEMPO DE PROTROMBINA', 'PROTROMBINA'],
    'TTPA': ['TIEMPO DE TROMBOPLASTINA', 'TROMBOPLASTINA'],
    'TPA': ['TIEMPO DE TROMBOPLASTINA', 'TROMBOPLASTINA'],
    'TT': ['TIEMPO DE TROMBINA'],
    'GASO': ['GASOMETRIA', 'BICARBONATO', 'GASES'],
    'PROCA': ['PROCALCITONINA'],
    'EGO': ['EXAMEN GENERAL DE ORINA', 'ORINA'],
    'URO': ['UROCULTIVO', 'CULTIVO'],
    'PCR': ['PROTEINA C REACTIVA'],
    'VSG': ['VELOCIDAD DE SEDIMENTACION'],
    'PIE': ['PERFIL', 'BIOQUIMICO'],
    'CA': ['CALCIO'],
    'P': ['FOSFORO'],
    'MG': ['MAGNESIO'],
    'US': ['ULTRASONIDO', 'ECOGRAFIA', 'TRANSVAGINAL', 'RENAL'],
    'USG': ['ULTRASONIDO', 'ECOGRAFIA'],
    'RX': ['RAYOS X', 'RADIOGRAFIA', 'RX', 'TORAX'],
    'TC': ['TOMOGRAFIA', 'TAC', 'ABDOMEN'],
    'TAC': ['TOMOGRAFIA', 'TAC'],
    'RM': ['RESONANCIA', 'COLANGIORESONANCIA'],
    'ECO': ['ECOCARDIOGRAMA'],
    'ECOTT': ['ECOCARDIOGRAMA']
}

def _normalize_study_text(text):
    if not text:
        return ''
    t = text.upper()
    for c in [',', ';', '.', '/', '-', '(', ')', '_', '"', "'", ':']:
        t = t.replace(c, ' ')
    return ' '.join(t.split())

def _match_study_request_with_report(pcit_name, ptmt_desc, ptmt_file=''):
    norm_pcit = _normalize_study_text(pcit_name)
    norm_ptmt = _normalize_study_text(ptmt_desc or '')
    norm_file = _normalize_study_text(ptmt_file or '')
    
    if norm_pcit and (norm_pcit in norm_ptmt or norm_pcit in norm_file):
        return True
        
    ptmt_tokens = norm_ptmt.split() + norm_file.split()
    for tok in ptmt_tokens:
        tok_clean = re.sub(r'\d+', '', tok).strip()
        keywords = _STUDY_ABBREV_MAP.get(tok, []) or _STUDY_ABBREV_MAP.get(tok_clean, [])
        for kw in keywords:
            if kw in norm_pcit:
                return True
                
    pcit_words = [w for w in norm_pcit.split() if len(w) > 4 and w not in ['PERFIL', 'COMPLETO', 'SIMPLE', 'CONTRASTE']]
    for w in pcit_words:
        if w in norm_ptmt or w in norm_file:
            return True
            
    return False

def fetch_full_ehr_dashboard(pt_num: str):
    """
    Obtiene toda la información necesaria para llenar el Expediente Electrónico (Dashboard).
    Cruza información de V_MRPT (demográficos), MR_NE_URG (notas, signos, alergias) y UDR_RPT_HABITACION (línea de tiempo).
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()
        
    try:
        cursor = conn.cursor()
        
        # 1. Datos Demográficos (V_MRPT)
        cursor.execute("""
            SELECT TOP 1 
                FullName, BirthDate, Gender, BloodType, MaritalStatus, Religion, Age
            FROM V_MRPT
            WHERE PTNum = ?
        """, (pt_num,))
        demo_row = cursor.fetchone()
        
        # 1b. Datos del Último Episodio Clínico (PC) y Censo Activo (UDR_AD_CENSO)
        pc_dict = {}
        try:
            cursor.execute("""
                SELECT TOP 1
                    pc.PCNum, pc.PC_ST, pc.MedicalDischarge, pc.MedicalDischargeDate,
                    pc.EntryDate, pc.ExitDate, pc.ClosedOn, pc.UDF_FYH_DE_INGRESO, pc.UDF_FYH_DE_EGRESO,
                    pc.UDF_Diagnostico_presuntivo, pc.MedicalDischargeDX,
                    c.Habitacion as CamaCenso
                FROM PC pc
                LEFT JOIN UDR_AD_CENSO c ON pc.PCNum = c.PCNum
                WHERE pc.PTNum = ?
                ORDER BY pc.EntryDate DESC, pc.PCNum DESC
            """, (pt_num,))
            pc_row = cursor.fetchone()
            if pc_row:
                pc_cols = [c[0] for c in cursor.description]
                pc_dict = dict(zip(pc_cols, pc_row))
        except Exception as e_pc:
            print(f"Nota: No se pudo consultar PC/UDR_AD_CENSO en EHR dashboard: {e_pc}")

        # 2. Notas de Urgencias (con todas las evoluciones consecutivas sin límite)
        cursor.execute("""
            SELECT
                -- General
                ALERGIAS, DIAGNOSTICO, EXPEDIENTE, CAMA, DESTINO, FHINGRESO, FYH_EGRESO, CreatedOn, MRNum_NE_URG,
                -- Evolución 1
                FECHANOTA1, TURNO1, TA1, FC1, FR1, SAT_O2_1, PESO1, TALLA, NOTAS,
                S_SUBJETIVO1, O_OBJETIVO, A_ANALISIS1, P_PLAN1, N_MEDICO, CEDPROF, NMIP,
                -- Evolución 2
                FECHANOTA2, TURNO2, TA2, FC2, FR2, SAT_O2_2, PESO2, TALLA2, NOTAS2,
                S_SUBJETIVO2, O_OBJETIVO2, A_ANALISIS2, P_PLAN2, MEDICO3, CEDULA2, N_MIP2,
                -- Evolución 3
                FECHANOTA3, TURNO33, TA3, FC3, FR3, SAT_O2_3, PESO3, TALLA3, NOTAS3,
                S_SUBJETIVO3, O_OBJETIVO3, A_ANALISIS3, P_PLAN3, MEDICO4, CEDULA3, N_MIP3
            FROM MR_NE_URG
            WHERE PTNum = ?
            ORDER BY CreatedOn ASC, MRNum_NE_URG ASC
        """, (pt_num,))
        nota_cols = [c[0] for c in cursor.description]
        n_rows = cursor.fetchall()
        
        last_nota_dict = {}
        evoluciones_raw = []
        e1, e2, e3 = None, None, None
        if n_rows:
            for n_row in n_rows:
                row_dict = dict(zip(nota_cols, n_row))
                last_nota_dict = row_dict
                
                def parse_evol_row(r_dict, slot_idx, date_col, turno_col, ta_col, fc_col, fr_col, sat_col, peso_col, talla_col, temp_col, s_col, o_col, a_col, p_col, med_col, ced_col, mip_col):
                    dt = r_dict.get(date_col)
                    sub = str(r_dict.get(s_col) or "").strip()
                    if not dt and not sub:
                        return None
                    return {
                        "mrnum_ne_urg": r_dict.get("MRNum_NE_URG"),
                        "slot_in_row": slot_idx,
                        "created_on": r_dict.get("CreatedOn"),
                        "fecha": dt.strftime('%d/%m/%Y') if dt else "",
                        "hora": dt.strftime('%H:%M') if dt else "",
                        "date_iso": dt.isoformat() if dt else "",
                        "dt_obj": dt or r_dict.get("CreatedOn") or datetime.datetime.min,
                        "turno": str(r_dict.get(turno_col) or "Matutino"),
                        "vitals_ta": str(r_dict.get(ta_col) or "--"),
                        "vitals_fc": str(r_dict.get(fc_col) or "--"),
                        "vitals_fr": str(r_dict.get(fr_col) or "--"),
                        "vitals_sato2": str(r_dict.get(sat_col) or "--"),
                        "vitals_peso": str(r_dict.get(peso_col) or "--"),
                        "vitals_talla": str(r_dict.get(talla_col) or "--"),
                        "vitals_temp": str(r_dict.get(temp_col) or "--").replace("FEBRIL ", ""),
                        "subjetivo": sub,
                        "objetivo": str(r_dict.get(o_col) or "").strip(),
                        "analisis": str(r_dict.get(a_col) or "").strip(),
                        "plan": str(r_dict.get(p_col) or "").strip(),
                        "medico": str(r_dict.get(med_col) or "Desconocido"),
                        "cedula": str(r_dict.get(ced_col) or "N/D"),
                        "mip": str(r_dict.get(mip_col) or "")
                    }
                
                e1 = parse_evol_row(row_dict, 1, 'FECHANOTA1', 'TURNO1', 'TA1', 'FC1', 'FR1', 'SAT_O2_1', 'PESO1', 'TALLA', 'NOTAS', 'S_SUBJETIVO1', 'O_OBJETIVO', 'A_ANALISIS1', 'P_PLAN1', 'N_MEDICO', 'CEDPROF', 'NMIP')
                e2 = parse_evol_row(row_dict, 2, 'FECHANOTA2', 'TURNO2', 'TA2', 'FC2', 'FR2', 'SAT_O2_2', 'PESO2', 'TALLA2', 'NOTAS2', 'S_SUBJETIVO2', 'O_OBJETIVO2', 'A_ANALISIS2', 'P_PLAN2', 'MEDICO3', 'CEDULA2', 'N_MIP2')
                e3 = parse_evol_row(row_dict, 3, 'FECHANOTA3', 'TURNO33', 'TA3', 'FC3', 'FR3', 'SAT_O2_3', 'PESO3', 'TALLA3', 'NOTAS3', 'S_SUBJETIVO3', 'O_OBJETIVO3', 'A_ANALISIS3', 'P_PLAN3', 'MEDICO4', 'CEDULA3', 'N_MIP3')
                
                if e1: evoluciones_raw.append(e1)
                if e2: evoluciones_raw.append(e2)
                if e3: evoluciones_raw.append(e3)

        # Ordenar por orden de antigüedad (cronológico / fecha de atención)
        evoluciones_raw.sort(key=lambda x: x.get("dt_obj") or datetime.datetime.min)

        evol_dict = {}
        evoluciones_list = []
        for idx, ev in enumerate(evoluciones_raw):
            num = idx + 1
            ev["num"] = num
            ev["title"] = f"Evolución y Observaciones {num}"
            if "dt_obj" in ev:
                del ev["dt_obj"]
            evol_dict[f"evolucion{num}"] = ev
            evoluciones_list.append(ev)

        # Claves base aseguradas
        for k in range(1, 4):
            if f"evolucion{k}" not in evol_dict:
                evol_dict[f"evolucion{k}"] = None

        nota_dict = last_nota_dict

        # 3. Línea de Tiempo (Habitaciones)
        cursor.execute("""
            SELECT FRName, EntryDate, ClosedOn
            FROM UDR_RPT_HABITACION
            WHERE PTNum = ?
            ORDER BY EntryDate DESC
        """, (pt_num,))
        timeline_rows = cursor.fetchall()

        # 0. Consultar Alergias Activas en PTAL (SQL Server)
        allergies_list = []
        try:
            cursor.execute("""
                SELECT 
                    p.PTALNum,
                    p.PTNum,
                    p.PTAL_ST,
                    p.AllergyNum,
                    COALESCE(d.AllergyName, 'Alergia no catalogada (' + CAST(p.AllergyNum AS VARCHAR) + ')') as AllergyName,
                    p.AllergicSince,
                    p.Notes,
                    p.Reference,
                    p.CreatedBy,
                    p.CreatedOn
                FROM PTAL p
                LEFT JOIN DIS_AL d ON p.AllergyNum = d.AllergyId
                WHERE p.PTNum = ? AND p.PTAL_ST = 'RG'
                ORDER BY p.CreatedOn DESC, p.PTALNum DESC
            """, (int(pt_num),))
            al_rows = cursor.fetchall()
            al_cols = [c[0] for c in cursor.description]
            for al_r in al_rows:
                al_d = dict(zip(al_cols, al_r))
                since_dt = al_d.get("AllergicSince")
                cr_dt = al_d.get("CreatedOn")
                allergies_list.append({
                    "ptal_num": al_d.get("PTALNum"),
                    "pt_num": al_d.get("PTNum"),
                    "allergy_num": str(al_d.get("AllergyNum") or "").strip(),
                    "allergy_name": str(al_d.get("AllergyName") or "").strip(),
                    "allergic_since": since_dt.strftime("%d/%m/%Y") if since_dt else "",
                    "notes": str(al_d.get("Notes") or "").strip(),
                    "reference": str(al_d.get("Reference") or "").strip(),
                    "created_by": str(al_d.get("CreatedBy") or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else ""
                })
        except Exception as e_al:
            print(f"Nota: No se pudo consultar PTAL: {e_al}")

        allergies_summary = ", ".join([a["allergy_name"] for a in allergies_list]) if allergies_list else str(nota_dict.get('ALERGIAS') or "Sin alergias reportadas")
        
        # Consultar Evoluciones de Hospitalización (MR_24_HOJA_EVOL)
        evoluciones_hosp_list = []
        try:
            cursor.execute("""
                SELECT
                    MRNum_24_HOJA_EVOL, PTNum, ControllerName, ControllerKey, MR_ST,
                    CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature, FECHA, NOTA, MEDICO_N
                FROM MR_24_HOJA_EVOL
                WHERE PTNum = ?
                ORDER BY FECHA ASC, CreatedOn ASC, MRNum_24_HOJA_EVOL ASC
            """, (pt_num,))
            h_cols = [c[0] for c in cursor.description]
            for h_idx, h_r in enumerate(cursor.fetchall()):
                hr_dict = dict(zip(h_cols, h_r))
                h_dt = hr_dict.get("FECHA") or hr_dict.get("CreatedOn")
                h_raw = str(hr_dict.get("NOTA") or "").strip()
                h_med = str(hr_dict.get("MEDICO_N") or hr_dict.get("SignedBy") or hr_dict.get("CreatedBy") or "").strip()

                h_turno = "Matutino"
                h_ta, h_fc, h_fr, h_sat, h_peso, h_talla, h_temp = "--", "--", "--", "--", "--", "--", "--"
                h_subjetivo, h_objetivo, h_analisis, h_plan = "", "", "", ""
                h_cedula = ""
                h_mip = ""

                if "[TURNO:" in h_raw:
                    try:
                        m_meta = re.search(r'\[TURNO:\s*([^\|]+)\s*\|\s*TA:\s*([^\|]+)\s*\|\s*FC:\s*([^\|]+)\s*\|\s*FR:\s*([^\|]+)\s*\|\s*SatO2:\s*([^\|]+)\s*\|\s*Temp:\s*([^\|]+)\s*\|\s*Peso:\s*([^\|]+)\s*\|\s*Talla:\s*([^\]]+)\]', h_raw)
                        if m_meta:
                            h_turno = m_meta.group(1).strip()
                            h_ta = m_meta.group(2).strip()
                            h_fc = m_meta.group(3).strip()
                            h_fr = m_meta.group(4).strip()
                            h_sat = m_meta.group(5).strip().replace("%", "")
                            h_temp = m_meta.group(6).strip().replace("°C", "")
                            h_peso = m_meta.group(7).strip().replace("kg", "")
                            h_talla = m_meta.group(8).strip()
                    except Exception:
                        pass

                if "[MÉDICO:" in h_raw or "[MEDICO:" in h_raw:
                    try:
                        m_med = re.search(r'\[M[EÉ]DICO:\s*([^\|]+)\s*\|\s*C[EÉ]DULA:\s*([^\|]+)(?:\s*\|\s*MIP:\s*([^\]]*))?\]', h_raw)
                        if m_med:
                            if m_med.group(1).strip(): h_med = m_med.group(1).strip()
                            if m_med.group(2).strip(): h_cedula = m_med.group(2).strip()
                            if m_med.group(3): h_mip = m_med.group(3).strip()
                    except Exception:
                        pass

                s_m = re.search(r'\(S\)\s*Subjetivo:\s*(.*?)(?=\(O\)\s*Objetivo:|\(A\)\s*Análisis:|\(P\)\s*Plan:|\[M[EÉ]DICO:|$)', h_raw, re.DOTALL | re.IGNORECASE)
                o_m = re.search(r'\(O\)\s*Objetivo:\s*(.*?)(?=\(A\)\s*Análisis:|\(P\)\s*Plan:|\[M[EÉ]DICO:|$)', h_raw, re.DOTALL | re.IGNORECASE)
                a_m = re.search(r'\(A\)\s*Análisis:\s*(.*?)(?=\(P\)\s*Plan:|\[M[EÉ]DICO:|$)', h_raw, re.DOTALL | re.IGNORECASE)
                p_m = re.search(r'\(P\)\s*Plan(?:\s*\(laboratorios solicitados y tratamientos a establecer\))?:\s*(.*?)(?=\[M[EÉ]DICO:|$)', h_raw, re.DOTALL | re.IGNORECASE)

                if s_m: h_subjetivo = s_m.group(1).strip()
                if o_m: h_objetivo = o_m.group(1).strip()
                if a_m: h_analisis = a_m.group(1).strip()
                if p_m: h_plan = p_m.group(1).strip()

                if not h_subjetivo and not h_objetivo and not h_analisis and not h_plan:
                    clean_b = re.sub(r'\[TURNO:[^\]]+\]', '', h_raw)
                    clean_b = re.sub(r'\[M[EÉ]DICO:[^\]]+\]', '', clean_b).strip()
                    h_subjetivo = clean_b or h_raw

                h_num = h_idx + 1
                evoluciones_hosp_list.append({
                    "num": h_num,
                    "mrnum_24_hoja_evol": hr_dict.get("MRNum_24_HOJA_EVOL"),
                    "slot": hr_dict.get("MRNum_24_HOJA_EVOL"),
                    "title": f"Evolución y Observaciones de Hospitalización {h_num}",
                    "fecha": h_dt.strftime('%d/%m/%Y') if h_dt else "",
                    "hora": h_dt.strftime('%H:%M') if h_dt else "",
                    "date_iso": h_dt.isoformat() if h_dt else "",
                    "turno": h_turno,
                    "vitals_ta": h_ta,
                    "vitals_fc": h_fc,
                    "vitals_fr": h_fr,
                    "vitals_sato2": h_sat,
                    "vitals_peso": h_peso,
                    "vitals_talla": h_talla,
                    "vitals_temp": h_temp,
                    "subjetivo": h_subjetivo,
                    "objetivo": h_objetivo,
                    "analisis": h_analisis,
                    "plan": h_plan,
                    "nota": h_raw,
                    "medico": h_med,
                    "cedula": h_cedula,
                    "mip": h_mip,
                    "signed_by": hr_dict.get("SignedBy"),
                    "signed_on": hr_dict.get("SignedOn").strftime('%d/%m/%Y %H:%M') if hr_dict.get("SignedOn") else None
                })
        except Exception as e_hosp_fetch:
            print(f"Nota: No se pudo consultar MR_24_HOJA_EVOL en dashboard: {e_hosp_fetch}")

        # Determinar estatus de ingreso vs alta clínica
        # Si el paciente tiene cama en el censo activo (UDR_AD_CENSO) o su episodio en PC está en OP (Abierto) sin alta médica registrada
        has_active_censo = bool(pc_dict and pc_dict.get('CamaCenso') and str(pc_dict.get('CamaCenso')).strip())
        is_pc_closed = bool(
            pc_dict and (
                pc_dict.get('ClosedOn') or
                pc_dict.get('MedicalDischargeDate') or
                pc_dict.get('UDF_FYH_DE_EGRESO') or
                bool(pc_dict.get('MedicalDischarge')) or
                (pc_dict.get('PC_ST') in ('CL', 'PD', 'CA'))
            )
        )

        if has_active_censo or (pc_dict and pc_dict.get('PC_ST') == 'OP' and not is_pc_closed):
            has_discharge = False
            is_active = True
            entry_dt = pc_dict.get('UDF_FYH_DE_INGRESO') or pc_dict.get('EntryDate') or nota_dict.get('FHINGRESO')
            exit_dt = None
        else:
            has_discharge = bool(
                is_pc_closed or
                (nota_dict.get('FYH_EGRESO') and str(nota_dict.get('FYH_EGRESO')).strip() not in ('', '___/___/___', 'None'))
            )
            is_active = not has_discharge and (not pc_dict or pc_dict.get('PC_ST') is None)
            entry_dt = nota_dict.get('FHINGRESO') or (pc_dict.get('UDF_FYH_DE_INGRESO') if pc_dict else None) or (pc_dict.get('EntryDate') if pc_dict else None)
            exit_dt = (
                (pc_dict.get('MedicalDischargeDate') if pc_dict else None) or
                (pc_dict.get('UDF_FYH_DE_EGRESO') if pc_dict else None) or
                (pc_dict.get('ClosedOn') if pc_dict else None) or
                nota_dict.get('FYH_EGRESO') or
                (pc_dict.get('ExitDate') if pc_dict else None)
            )

        cama_str = (pc_dict.get('CamaCenso') if pc_dict else None) or (str(nota_dict.get('CAMA') or "Sin cama asignada") if is_active else "Alta / Egresado")
        diag_str = str((pc_dict.get('MedicalDischargeDX') or pc_dict.get('UDF_Diagnostico_presuntivo') if pc_dict else None) or nota_dict.get('DIAGNOSTICO') or "Sin diagnóstico especificado")

        # Construir objeto de respuesta
        dashboard_data = {
            "patient": {
                "name": str(demo_row[0]) if demo_row and demo_row[0] else "Desconocido",
                "age": f"{demo_row[6]} años" if demo_row and len(demo_row)>6 and demo_row[6] else "",
                "gender": "Masculino" if demo_row and demo_row[2] == 'M' else "Femenino" if demo_row and demo_row[2] == 'F' else "",
                "mrn": f"PT-{pt_num}",
                "dob": demo_row[1].strftime('%d %b %Y') if demo_row and demo_row[1] else "",
                "phone": "N/D",
                "email": "N/D",
                "allergies": allergies_summary,
                "cama": cama_str,
                "diagnostico": diag_str,
                "destino": str(nota_dict.get('DESTINO') or "N/D"),
                "status": "Activo" if is_active else "Alta",
                "is_active": is_active,
                "is_alta": not is_active,
                "fecha_ingreso": entry_dt.strftime('%d/%m/%Y') if entry_dt else "",
                "hora_ingreso": entry_dt.strftime('%H:%M') if entry_dt else "",
                "fecha_egreso": exit_dt.strftime('%d/%m/%Y') if exit_dt else "___/___/___",
                "hora_egreso": exit_dt.strftime('%H:%M') if exit_dt else "__:__"
            },
            "allergies_list": allergies_list,
            "vitals": [],
            "timelineEvents": [],
            "clinicalNotes": [],
            "evoluciones": evol_dict,
            "evoluciones_list": evoluciones_list,
            "total_evoluciones": len(evoluciones_list),
            "evoluciones_hospitalizacion_list": evoluciones_hosp_list,
            "total_evoluciones_hosp": len(evoluciones_hosp_list),
            "medications": []
        }
        
        # 3.5. Signos Vitales Maestros desde tabla PTVS de SQL Server
        try:
            cursor.execute("""
                SELECT TOP 1
                    ProcedureDate, Age, Height, Weight, Temperature, PulseRate,
                    SystolicPressure, DiastolicPressure, RespiratroryRAte, OxygenSaturation,
                    PTVSNum, PTVSID
                FROM PTVS
                WHERE PTNum = ?
                ORDER BY ProcedureDate DESC, CreatedOn DESC
            """, (pt_num,))
            ptvs_r = cursor.fetchone()
            ptvs_dict = dict(zip([c[0] for c in cursor.description], ptvs_r)) if ptvs_r else {}
        except Exception as e_ptvs_fetch:
            print(f"Nota: No se pudo consultar PTVS en dashboard: {e_ptvs_fetch}")
            ptvs_dict = {}

        # Extraer valores de PTVS o fallback a latest_e
        latest_e = evoluciones_list[-1] if evoluciones_list else None
        
        sys_val = ptvs_dict.get("SystolicPressure")
        dia_val = ptvs_dict.get("DiastolicPressure")
        if sys_val and dia_val:
            ta_val = f"{sys_val}/{dia_val}"
        elif latest_e and latest_e.get("vitals_ta") and latest_e.get("vitals_ta") != "--":
            ta_val = latest_e.get("vitals_ta")
        else:
            ta_val = "--"

        fc_val = str(ptvs_dict.get("PulseRate") or (latest_e.get("vitals_fc") if latest_e and latest_e.get("vitals_fc") != "--" else "--"))
        fr_val = str(ptvs_dict.get("RespiratroryRAte") or (latest_e.get("vitals_fr") if latest_e and latest_e.get("vitals_fr") != "--" else "--"))
        sat_val = str(ptvs_dict.get("OxygenSaturation") or (latest_e.get("vitals_sato2") if latest_e and latest_e.get("vitals_sato2") != "--" else "--"))
        def format_num_str(val):
            if val is None or val == "" or val == "--":
                return "--"
            try:
                f = float(val)
                if f.is_integer():
                    return str(int(f))
                return f"{f:.1f}"
            except Exception:
                return str(val)

        temp_raw = ptvs_dict.get("Temperature") or (latest_e.get("vitals_temp") if latest_e and latest_e.get("vitals_temp") != "--" else None)
        peso_raw = ptvs_dict.get("Weight") or (latest_e.get("vitals_peso") if latest_e and latest_e.get("vitals_peso") != "--" else None)
        talla_raw = ptvs_dict.get("Height") or (latest_e.get("vitals_talla") if latest_e and latest_e.get("vitals_talla") != "--" else None)

        temp_val = format_num_str(temp_raw)
        peso_val = format_num_str(peso_raw)
        talla_val = format_num_str(talla_raw)

        has_vitals_recorded = bool(
            ptvs_dict or 
            (latest_e and any(latest_e.get(k) and latest_e.get(k) != "--" for k in ["vitals_ta", "vitals_fc", "vitals_fr", "vitals_sato2", "vitals_temp", "vitals_peso"]))
        )
        vitals_source = "PTVS" if ptvs_dict else ("Evolución" if has_vitals_recorded else "Sin registro")

        dashboard_data["ptvs"] = {
            "systolic": str(sys_val) if sys_val else "--",
            "diastolic": str(dia_val) if dia_val else "--",
            "ta": ta_val,
            "fc": fc_val,
            "fr": fr_val,
            "sat_o2": sat_val,
            "temp": temp_val,
            "peso": peso_val,
            "talla": talla_val,
            "procedure_date": ptvs_dict.get("ProcedureDate").strftime("%d/%m/%Y %H:%M") if ptvs_dict.get("ProcedureDate") else (datetime.datetime.now().strftime("%d/%m/%Y %H:%M") if has_vitals_recorded else None),
            "source": vitals_source
        }

        dashboard_data["vitals"] = [
            {"label": "Presión Arterial", "value": ta_val, "unit": "mmHg", "status": "Normal" if ta_val != "--" else "Sin registro"},
            {"label": "Frec. Cardíaca", "value": fc_val, "unit": "lpm", "status": "Normal" if fc_val != "--" else "Sin registro"},
            {"label": "Frec. Respiratoria", "value": fr_val, "unit": "rpm", "status": "Normal" if fr_val != "--" else "Sin registro"},
            {"label": "Saturación O2", "value": sat_val, "unit": "%", "status": "Normal" if sat_val != "--" else "Sin registro"},
            {"label": "Temperatura", "value": temp_val, "unit": "°C", "status": "Normal" if temp_val != "--" else "Sin registro"},
            {"label": "Peso", "value": peso_val, "unit": "kg", "status": "Normal" if peso_val != "--" else "Sin registro"}
        ]

        # Si PTVS tiene signos vitales registrados, actualizar la primera evolución para que los formatos y PDF tomen siempre la tabla maestra
        if ptvs_dict and evoluciones_list:
            evoluciones_list[0]["vitals_ta"] = ta_val
            evoluciones_list[0]["vitals_fc"] = fc_val
            evoluciones_list[0]["vitals_fr"] = fr_val
            evoluciones_list[0]["vitals_sato2"] = sat_val
            evoluciones_list[0]["vitals_temp"] = temp_val
            evoluciones_list[0]["vitals_peso"] = peso_val
            evoluciones_list[0]["vitals_talla"] = talla_val
            evol_dict["evolucion1"] = evoluciones_list[0]
        
        dashboard_data["evoluciones"] = evol_dict
        dashboard_data["evoluciones_list"] = evoluciones_list
        dashboard_data["total_evoluciones"] = len(evoluciones_list)
                
        # Obtener Consentimiento 32/01 si existe
        cursor.execute("SELECT TOP 1 INTETYPE, N_MEDICO, CEDULA, ALERGIAS, DIAGNOSTICO FROM MR_CI_ETE_CARD WHERE PTNum = ? ORDER BY CreatedOn DESC", (pt_num,))
        c32_row = cursor.fetchone()
        if c32_row:
            dashboard_data["consentimiento_32_01"] = {
                "tipo_interrogatorio": c32_row[0] or "Directo",
                "medico_tratante": c32_row[1] or "",
                "cedula": c32_row[2] or "",
                "alergias": c32_row[3] or "",
                "diagnostico": c32_row[4] or "",
            }
        else:
            dashboard_data["consentimiento_32_01"] = None

        # Obtener Consentimiento EED si existe
        cursor.execute("SELECT TOP 1 NOMBRE_MEDICO, CEDULA_PROFESIONAL, INTERROGATORIO, RESPONSABLE, COMENTARIOS, TA, FC_META, FR, TALLA, PESO, TA_BASAL, FC_BASAL, SO2_BASAL, S_BASAL, TA_5MCG, FC_5MCG, SO2_5MCG, S_5MCG, TA_10MCG, FC_10MCG, SO2_10MCG, S_10MCG, TA_20MCG, FC_20MCG, SO2_20MCG, S_20MCG, TA_30MCG, FC_30MCG, SO2_30MCG, S_30MCG, TA_40MCG, FC_40MCG, SO2_40MCG, S_40MCG, TA_ANTROPINA, FC_ANTROPINA, SO2_ANTROPINA, S_ANTROPINA, TA_2MIN, FC_2MIN, SO2_2MIN, SINTOMAS_2MIN, TA_4MIN, FC_4MIN, SO2_4MIN, SINTOMAS_4MIN FROM MR_CI_EED WHERE PTNum = ? ORDER BY CreatedOn DESC", (pt_num,))
        c_eed_row = cursor.fetchone()
        if c_eed_row:
            dashboard_data["consentimiento_eed"] = {
                "medico": c_eed_row[0] or "",
                "cedula": c_eed_row[1] or "",
                "tipo_interrogatorio": c_eed_row[2] or "Directo",
                "responsable": c_eed_row[3] or "",
                "comentarios": c_eed_row[4] or "",
                "ta": c_eed_row[5] or "",
                "fc_meta": c_eed_row[6] or "",
                "fr": c_eed_row[7] or "",
                "talla": c_eed_row[8] or "",
                "peso": c_eed_row[9] or "",
                "ta_basal": c_eed_row[10] or "", "fc_basal": c_eed_row[11] or "", "so2_basal": c_eed_row[12] or "", "s_basal": c_eed_row[13] or "",
                "ta_5mcg": c_eed_row[14] or "", "fc_5mcg": c_eed_row[15] or "", "so2_5mcg": c_eed_row[16] or "", "s_5mcg": c_eed_row[17] or "",
                "ta_10mcg": c_eed_row[18] or "", "fc_10mcg": c_eed_row[19] or "", "so2_10mcg": c_eed_row[20] or "", "s_10mcg": c_eed_row[21] or "",
                "ta_20mcg": c_eed_row[22] or "", "fc_20mcg": c_eed_row[23] or "", "so2_20mcg": c_eed_row[24] or "", "s_20mcg": c_eed_row[25] or "",
                "ta_30mcg": c_eed_row[26] or "", "fc_30mcg": c_eed_row[27] or "", "so2_30mcg": c_eed_row[28] or "", "s_30mcg": c_eed_row[29] or "",
                "ta_40mcg": c_eed_row[30] or "", "fc_40mcg": c_eed_row[31] or "", "so2_40mcg": c_eed_row[32] or "", "s_40mcg": c_eed_row[33] or "",
                "ta_atropina": c_eed_row[34] or "", "fc_atropina": c_eed_row[35] or "", "so2_atropina": c_eed_row[36] or "", "s_atropina": c_eed_row[37] or "",
                "ta_2min": c_eed_row[38] or "", "fc_2min": c_eed_row[39] or "", "so2_2min": c_eed_row[40] or "", "sintomas_2min": c_eed_row[41] or "",
                "ta_4min": c_eed_row[42] or "", "fc_4min": c_eed_row[43] or "", "so2_4min": c_eed_row[44] or "", "sintomas_4min": c_eed_row[45] or "",
            }
        else:
            dashboard_data["consentimiento_eed"] = None

        # Historial de Registros de Consentimiento 32/01
        historial_32_01 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_ETE_CARD, INTETYPE, N_MEDICO, CEDULA, ALERGIAS, DIAGNOSTICO,
                       CreatedBy, CreatedOn, SignedBy, SignedOn
                FROM MR_CI_ETE_CARD 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_ETE_CARD DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[7]
                sg_dt = r[9]
                historial_32_01.append({
                    "mrnum": r[0],
                    "tipo_interrogatorio": r[1] or "Directo",
                    "medico_tratante": str(r[2] or "").strip(),
                    "cedula": str(r[3] or "").strip(),
                    "alergias": str(r[4] or "").strip(),
                    "diagnostico": str(r[5] or "").strip(),
                    "created_by": str(r[6] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[8] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[8] or sg_dt)
                })
        except Exception as e_h32:
            print(f"Nota: Error consultando historial 32/01: {e_h32}")
        dashboard_data["historial_32_01"] = historial_32_01

        # Historial de Registros de Consentimiento EED
        historial_eed = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_EED, NOMBRE_MEDICO, CEDULA_PROFESIONAL, INTERROGATORIO, RESPONSABLE,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, FC_META, COMENTARIOS,
                       TA, FR, TALLA, PESO, TA_BASAL, FC_BASAL, SO2_BASAL, S_BASAL,
                       TA_5MCG, FC_5MCG, SO2_5MCG, S_5MCG, TA_10MCG, FC_10MCG, SO2_10MCG, S_10MCG,
                       TA_20MCG, FC_20MCG, SO2_20MCG, S_20MCG, TA_30MCG, FC_30MCG, SO2_30MCG, S_30MCG,
                       TA_40MCG, FC_40MCG, SO2_40MCG, S_40MCG, TA_ANTROPINA, FC_ANTROPINA, SO2_ANTROPINA, S_ANTROPINA,
                       TA_2MIN, FC_2MIN, SO2_2MIN, SINTOMAS_2MIN, TA_4MIN, FC_4MIN, SO2_4MIN, SINTOMAS_4MIN
                FROM MR_CI_EED 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_EED DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[6]
                sg_dt = r[8]
                historial_eed.append({
                    "mrnum": r[0],
                    "medico": str(r[1] or "").strip(),
                    "cedula": str(r[2] or "").strip(),
                    "tipo_interrogatorio": str(r[3] or "Directo").strip(),
                    "responsable": str(r[4] or "").strip(),
                    "created_by": str(r[5] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[7] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[7] or sg_dt),
                    "fc_meta": str(r[9] or "").strip(),
                    "comentarios": str(r[10] or "").strip(),
                    "ta": str(r[11] or "").strip(),
                    "fr": str(r[12] or "").strip(),
                    "talla": str(r[13] or "").strip(),
                    "peso": str(r[14] or "").strip(),
                    "ta_basal": str(r[15] or "").strip(), "fc_basal": str(r[16] or "").strip(), "so2_basal": str(r[17] or "").strip(), "s_basal": str(r[18] or "").strip(),
                    "ta_5mcg": str(r[19] or "").strip(), "fc_5mcg": str(r[20] or "").strip(), "so2_5mcg": str(r[21] or "").strip(), "s_5mcg": str(r[22] or "").strip(),
                    "ta_10mcg": str(r[23] or "").strip(), "fc_10mcg": str(r[24] or "").strip(), "so2_10mcg": str(r[25] or "").strip(), "s_10mcg": str(r[26] or "").strip(),
                    "ta_20mcg": str(r[27] or "").strip(), "fc_20mcg": str(r[28] or "").strip(), "so2_20mcg": str(r[29] or "").strip(), "s_20mcg": str(r[30] or "").strip(),
                    "ta_30mcg": str(r[31] or "").strip(), "fc_30mcg": str(r[32] or "").strip(), "so2_30mcg": str(r[33] or "").strip(), "s_30mcg": str(r[34] or "").strip(),
                    "ta_40mcg": str(r[35] or "").strip(), "fc_40mcg": str(r[36] or "").strip(), "so2_40mcg": str(r[37] or "").strip(), "s_40mcg": str(r[38] or "").strip(),
                    "ta_atropina": str(r[39] or "").strip(), "fc_atropina": str(r[40] or "").strip(), "so2_atropina": str(r[41] or "").strip(), "s_atropina": str(r[42] or "").strip(),
                    "ta_2min": str(r[43] or "").strip(), "fc_2min": str(r[44] or "").strip(), "so2_2min": str(r[45] or "").strip(), "sintomas_2min": str(r[46] or "").strip(),
                    "ta_4min": str(r[47] or "").strip(), "fc_4min": str(r[48] or "").strip(), "so2_4min": str(r[49] or "").strip(), "sintomas_4min": str(r[50] or "").strip()
                })
        except Exception as e_heed:
            print(f"Nota: Error consultando historial EED: {e_heed}")
        dashboard_data["historial_eed"] = historial_eed

        # Historial de Registros de Consentimiento 25
        historial_25 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_RGO_CE, N_MEDICO, CreatedBy, CreatedOn, SignedBy, SignedOn
                FROM MR_CI_RGO_CE 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_RGO_CE DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[3]
                sg_dt = r[5]
                historial_25.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "created_by": str(r[2] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[4] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[4] or sg_dt)
                })
        except Exception as e_h25:
            print(f"Nota: Error consultando historial 25: {e_h25}")
        dashboard_data["historial_25"] = historial_25

        # Obtener Consentimiento 25 (MR_CI_RGO_CE) si existe
        try:
            cursor.execute("SELECT TOP 1 N_MEDICO, CreatedBy, CreatedOn, SignedBy, SignedOn, MRNum_CI_RGO_CE FROM MR_CI_RGO_CE WHERE PTNum = ? ORDER BY MRNum_CI_RGO_CE DESC", (pt_num,))
            c25_row = cursor.fetchone()
            if c25_row:
                dashboard_data["consentimiento_25"] = {
                    "mrnum": c25_row[5],
                    "medico_tratante": c25_row[0] or "",
                    "n_medico": c25_row[0] or "",
                    "created_by": str(c25_row[1] or ""),
                    "created_on": c25_row[2].strftime("%d/%m/%Y %H:%M") if c25_row[2] else "",
                    "signed_by": str(c25_row[3] or ""),
                    "signed_on": c25_row[4].strftime("%d/%m/%Y %H:%M") if c25_row[4] else ""
                }
            else:
                dashboard_data["consentimiento_25"] = None
        except Exception as e_c25:
            print(f"Nota: No se pudo consultar consentimiento 25: {e_c25}")
            dashboard_data["consentimiento_25"] = None

        # Historial de Registros de Consentimiento 34/01 (Mesa Inclinada)
        historial_34_01 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_EMI, NOMBRE_MEDICO_MI, CreatedBy, CreatedOn, SignedBy, SignedOn,
                       EXPEDIENTE, GRUPORH, ALERGIAS, INTTYP, PARIENTE, CEDULA, TA, FC_META, F_RESP,
                       TEMPERATURA, PESO, TALLA, IRM, FBPR, FPR, CONCLUSIONES, CONCLUSIONES_2, CONCLUSIONES_3
                FROM MR_CI_EMI 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_EMI DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[3]
                sg_dt = r[5]
                historial_34_01.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "nombre_medico_mi": str(r[1] or "").strip(),
                    "created_by": str(r[2] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[4] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[4] or sg_dt),
                    "expediente": str(r[6] or "").strip(),
                    "gruporh": str(r[7] or "").strip(),
                    "alergias": str(r[8] or "").strip(),
                    "tipo_interrogatorio": str(r[9] or "DIRECTO").strip(),
                    "pariente": str(r[10] or "").strip(),
                    "cedula": str(r[11] or "").strip(),
                    "ta": str(r[12] or "").strip(),
                    "fc_meta": str(r[13] or "").strip(),
                    "f_resp": str(r[14] or "").strip(),
                    "temperatura": str(r[15] or "").strip(),
                    "peso": str(r[16] or "").strip(),
                    "talla": str(r[17] or "").strip(),
                    "irm": str(r[18] or "").strip(),
                    "fbpr": str(r[19] or "").strip(),
                    "fpr": str(r[20] or "").strip(),
                    "conclusiones": str(r[21] or "").strip(),
                    "conclusiones_2": str(r[22] or "").strip(),
                    "conclusiones_3": str(r[23] or "").strip()
                })
        except Exception as e_h34:
            print(f"Nota: Error consultando historial 34/01: {e_h34}")
        dashboard_data["historial_34_01"] = historial_34_01

        # Obtener Consentimiento 34/01 (MR_CI_EMI - Mesa Inclinada) si existe
        try:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_EMI, NOMBRE_MEDICO_MI, EXPEDIENTE, GRUPORH, ALERGIAS, INTTYP,
                    PARIENTE, CEDULA, TA, FC_META, F_RESP, TEMPERATURA, PESO, TALLA,
                    IRM, FBPR, FPR, CONCLUSIONES, CONCLUSIONES_2, CONCLUSIONES_3,
                    CreatedBy, CreatedOn, SignedBy, SignedOn
                FROM MR_CI_EMI 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_EMI DESC
            """, (pt_num,))
            c34_row = cursor.fetchone()
            if c34_row:
                dashboard_data["consentimiento_34_01"] = {
                    "mrnum": c34_row[0],
                    "nombre_medico_mi": str(c34_row[1] or "").strip(),
                    "medico_tratante": str(c34_row[1] or "").strip(),
                    "expediente": str(c34_row[2] or "").strip(),
                    "gruporh": str(c34_row[3] or "").strip(),
                    "alergias": str(c34_row[4] or "").strip(),
                    "tipo_interrogatorio": str(c34_row[5] or "DIRECTO").strip(),
                    "pariente": str(c34_row[6] or "").strip(),
                    "cedula": str(c34_row[7] or "").strip(),
                    "ta": str(c34_row[8] or "").strip(),
                    "fc_meta": str(c34_row[9] or "").strip(),
                    "f_resp": str(c34_row[10] or "").strip(),
                    "temperatura": str(c34_row[11] or "").strip(),
                    "peso": str(c34_row[12] or "").strip(),
                    "talla": str(c34_row[13] or "").strip(),
                    "irm": str(c34_row[14] or "").strip(),
                    "fbpr": str(c34_row[15] or "").strip(),
                    "fpr": str(c34_row[16] or "").strip(),
                    "conclusiones": str(c34_row[17] or "").strip(),
                    "conclusiones_2": str(c34_row[18] or "").strip(),
                    "conclusiones_3": str(c34_row[19] or "").strip(),
                    "created_by": str(c34_row[20] or "").strip(),
                    "created_on": c34_row[21].strftime("%d/%m/%Y %H:%M") if c34_row[21] else "",
                    "signed_by": str(c34_row[22] or "").strip(),
                    "signed_on": c34_row[23].strftime("%d/%m/%Y %H:%M") if c34_row[23] else ""
                }
            else:
                dashboard_data["consentimiento_34_01"] = None
        except Exception as e_c34:
            print(f"Nota: No se pudo consultar consentimiento 34_01: {e_c34}")
            dashboard_data["consentimiento_34_01"] = None

        # Historial de Registros de Consentimiento 12 (MR_CI_RGO_HU - Gineco Hosp/Urg)
        historial_12 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_RGO_HU, N_MEDICO, DIAGNOSTICO, EXPEDIENTE,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_RGO_HU 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_RGO_HU DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[5]
                sg_dt = r[7]
                historial_12.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "diagnostico": str(r[2] or "").strip(),
                    "expediente": str(r[3] or "").strip(),
                    "created_by": str(r[4] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[6] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[6] or sg_dt or r[8] == 'SG'),
                    "mr_st": r[8]
                })
        except Exception as e_h12:
            print(f"Nota: Error consultando historial 12: {e_h12}")
        dashboard_data["historial_12"] = historial_12
        dashboard_data["consentimiento_12"] = historial_12[0] if historial_12 else None

        # Historial de Registros de Consentimiento 04 (MR_CI_CC - Catéter Venoso Central)
        historial_04 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_CC, N_MEDICO,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_CC 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_CC DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[3]
                sg_dt = r[5]
                historial_04.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "created_by": str(r[2] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[4] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[4] or sg_dt or r[6] == 'SG'),
                    "mr_st": r[6]
                })
        except Exception as e_h04:
            print(f"Nota: Error consultando historial 04: {e_h04}")
        dashboard_data["historial_04"] = historial_04
        dashboard_data["consentimiento_04"] = historial_04[0] if historial_04 else None

        # Historial de Registros de Consentimiento 15 (MR_CI_CES - Cesárea / Disentimiento)
        historial_15 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_CES, N_MEDICO,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_CES 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_CES DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[3]
                sg_dt = r[5]
                historial_15.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "created_by": str(r[2] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[4] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[4] or sg_dt or r[6] == 'SG'),
                    "mr_st": r[6]
                })
        except Exception as e_h15:
            print(f"Nota: Error consultando historial 15: {e_h15}")
        dashboard_data["historial_15"] = historial_15
        dashboard_data["consentimiento_15"] = historial_15[0] if historial_15 else None

        # Historial de Registros de Consentimiento 02 (MR_02_CI_TRATAMIENTO_QUIRURGICO)
        historial_02 = []
        try:
            cursor.execute("""
                SELECT MRNum_02_CI_TRATAMIENTO_QUIRURGICO, N_MEDICO, DIAGNOSTICO,
                       ANESTESIA, TIPO_DE_ANESTESIA, MOTIVO_DE_NO_AUTORIZACION,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_02_CI_TRATAMIENTO_QUIRURGICO 
                WHERE PTNum = ? 
                ORDER BY MRNum_02_CI_TRATAMIENTO_QUIRURGICO DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[7]
                sg_dt = r[9]
                motivo = str(r[5] or "").strip()
                historial_02.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "diagnostico": str(r[2] or "").strip(),
                    "anestesia": str(r[3] or "").strip(),
                    "tipo_de_anestesia": str(r[4] or "").strip(),
                    "motivo_de_no_autorizacion": motivo,
                    "no_autorizo": bool(motivo),
                    "created_by": str(r[6] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[8] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[8] or sg_dt or r[10] == 'SG'),
                    "mr_st": r[10]
                })
        except Exception as e_h02:
            print(f"Nota: Error consultando historial 02: {e_h02}")
        dashboard_data["historial_02"] = historial_02
        dashboard_data["consentimiento_02"] = historial_02[0] if historial_02 else None

        # Historial de Registros de Consentimiento 08 (MR_08_CI_DIAGNOSTICO_ADMISION_CONTI)
        historial_08 = []
        try:
            cursor.execute("""
                SELECT MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI, N_MEDICO, DIAGNOSTICO,
                       PROCEDIMIENTOS, RIESGOS_INHERENTES_A_PROCEDIMIEN,
                       PROB_PROCED_Y_ALTS, BENEFICIOS,
                       TESTIGO_1, TESTIGO_2,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_08_CI_DIAGNOSTICO_ADMISION_CONTI 
                WHERE PTNum = ? 
                ORDER BY MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[10]
                sg_dt = r[12]
                historial_08.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "diagnostico": str(r[2] or "").strip(),
                    "procedimientos": str(r[3] or "").strip(),
                    "riesgos_inherentes_a_procedimien": str(r[4] or "").strip(),
                    "riesgos": str(r[4] or "").strip(),
                    "prob_proced_y_alts": str(r[5] or "").strip(),
                    "alternativas": str(r[5] or "").strip(),
                    "beneficios": str(r[6] or "").strip(),
                    "testigo_1": str(r[7] or "").strip(),
                    "testigo1": str(r[7] or "").strip(),
                    "testigo_2": str(r[8] or "").strip(),
                    "testigo2": str(r[8] or "").strip(),
                    "created_by": str(r[9] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[11] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[11] or sg_dt or r[13] == 'SG'),
                    "mr_st": r[13]
                })
        except Exception as e_h08:
            print(f"Nota: Error consultando historial 08: {e_h08}")
        dashboard_data["historial_08"] = historial_08
        dashboard_data["consentimiento_08"] = historial_08[0] if historial_08 else None

        # Historial de Registros de Formato 43 (MR_CI_OI - Orden de Intubación / Soporte Ventilatorio)
        historial_43 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_OI, N_MEDICO,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_OI 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_OI DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[3]
                sg_dt = r[5]
                historial_43.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "created_by": str(r[2] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[4] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[4] or sg_dt or r[6] == 'SG'),
                    "mr_st": r[6]
                })
        except Exception as e_h43:
            print(f"Nota: Error consultando historial 43: {e_h43}")
        dashboard_data["historial_43"] = historial_43
        dashboard_data["consentimiento_43"] = historial_43[0] if historial_43 else None

        # Historial de Registros de Formato 11 (MR_CI_NO_REANIMACION - Consentimiento de No Reanimación)
        historial_11 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_NO_REANIMACION, N_MEDICO, DIAGNOSTICO, BENEFICIOS_Y_RIESGOS_DE_NR, ALTERNATIVA_NR,
                       TESTIGO_1, TESTIGO_2, CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_NO_REANIMACION
                WHERE PTNum = ?
                ORDER BY MRNum_CI_NO_REANIMACION DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[8]
                sg_dt = r[10]
                historial_11.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "diagnostico": str(r[2] or "").strip(),
                    "beneficios_y_riesgos_de_nr": str(r[3] or "").strip(),
                    "beneficios": str(r[3] or "").strip(),
                    "alternativa_nr": str(r[4] or "").strip(),
                    "alternativas": str(r[4] or "").strip(),
                    "testigo_1": str(r[5] or "").strip(),
                    "testigo1": str(r[5] or "").strip(),
                    "testigo_2": str(r[6] or "").strip(),
                    "testigo2": str(r[6] or "").strip(),
                    "created_by": str(r[7] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[9] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[9] or sg_dt or r[11] == 'SG'),
                    "mr_st": r[11]
                })
        except Exception as e_h11:
            print(f"Nota: Error consultando historial 11: {e_h11}")
        dashboard_data["historial_11"] = historial_11
        dashboard_data["consentimiento_11"] = historial_11[0] if historial_11 else None

        # Historial de Registros de Formato 19 (MR_CI_HISTERECTOMIA - Consentimiento Informado para Histerectomía)
        historial_19 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_HISTERECTOMIA, N_MEDICO, DIAGNOSTICO, EXPLICACION_DE_PROCESO,
                       BENEFICIOS_DE_PROCEDIMIENTO, INTERVENCION_COMPLEMENTARIA, ALTERNATIVAS_TERAPEUTICAS,
                       TESTIGO_1, TESTIGO_2, MOTIVO_DE_NO_AUTORIZACION,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_HISTERECTOMIA
                WHERE PTNum = ?
                ORDER BY MRNum_CI_HISTERECTOMIA DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[11]
                sg_dt = r[13]
                motivo = str(r[9] or "").strip()
                historial_19.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "diagnostico": str(r[2] or "").strip(),
                    "explicacion_de_proceso": str(r[3] or "").strip(),
                    "beneficios_de_procedimiento": str(r[4] or "").strip(),
                    "beneficios": str(r[4] or "").strip(),
                    "intervencion_complementaria": str(r[5] or "").strip(),
                    "alternativas_terapeuticas": str(r[6] or "").strip(),
                    "alternativas": str(r[6] or "").strip(),
                    "testigo_1": str(r[7] or "").strip(),
                    "testigo1": str(r[7] or "").strip(),
                    "testigo_2": str(r[8] or "").strip(),
                    "testigo2": str(r[8] or "").strip(),
                    "motivo_de_no_autorizacion": motivo,
                    "no_autorizo": bool(motivo),
                    "created_by": str(r[10] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[12] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[12] or sg_dt or r[14] == 'SG'),
                    "mr_st": r[14]
                })
        except Exception as e_h19:
            print(f"Nota: Error consultando historial 19: {e_h19}")
        dashboard_data["historial_19"] = historial_19
        dashboard_data["consentimiento_19"] = historial_19[0] if historial_19 else None

        # Historial de Registros de Formato 15 (MR_EV_HOSP - Egreso Voluntario)
        historial_15_ev = []
        try:
            cursor.execute("""
                SELECT MRNum_EV_HOSP, N_MEDICO, N_REPLEGAL,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_EV_HOSP
                WHERE PTNum = ?
                ORDER BY MRNum_EV_HOSP DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[4]
                sg_dt = r[6]
                historial_15_ev.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "n_replegal": str(r[2] or "").strip(),
                    "representante_legal": str(r[2] or "").strip(),
                    "created_by": str(r[3] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[5] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[5] or sg_dt or r[7] == 'SG'),
                    "mr_st": r[7]
                })
        except Exception as e_h15ev:
            print(f"Nota: Error consultando historial 15 EV: {e_h15ev}")
        dashboard_data["historial_15_ev"] = historial_15_ev
        dashboard_data["egreso_voluntario_15"] = historial_15_ev[0] if historial_15_ev else None

        # Historial de Registros de Formato 06 (MR_CI_APA - Procedimiento Anestésico)
        historial_06 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_APA, N_MEDICO,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_APA
                WHERE PTNum = ?
                ORDER BY MRNum_CI_APA DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[3]
                sg_dt = r[5]
                historial_06.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "created_by": str(r[2] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[4] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[4] or sg_dt or r[6] == 'SG'),
                    "mr_st": r[6]
                })
        except Exception as e_h06:
            print(f"Nota: Error consultando historial 06: {e_h06}")
        dashboard_data["historial_06"] = historial_06
        dashboard_data["consentimiento_06"] = historial_06[0] if historial_06 else None

        # Historial de Registros de Formato 07 (MR_CI_PQ - Procedimientos Quirúrgicos)
        historial_07 = []
        try:
            cursor.execute("""
                SELECT MRNum_CI_PQ, N_MEDICO,
                       CreatedBy, CreatedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_PQ
                WHERE PTNum = ?
                ORDER BY MRNum_CI_PQ DESC
            """, (pt_num,))
            for r in cursor.fetchall():
                cr_dt = r[3]
                sg_dt = r[5]
                historial_07.append({
                    "mrnum": r[0],
                    "medico_tratante": str(r[1] or "").strip(),
                    "n_medico": str(r[1] or "").strip(),
                    "created_by": str(r[2] or "").strip(),
                    "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                    "signed_by": str(r[4] or "").strip(),
                    "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                    "firmado": bool(r[4] or sg_dt or r[6] == 'SG'),
                    "mr_st": r[6]
                })
        except Exception as e_h07:
            print(f"Nota: Error consultando historial 07: {e_h07}")
        dashboard_data["historial_07"] = historial_07
        dashboard_data["consentimiento_07"] = historial_07[0] if historial_07 else None
                
        # 1. Medicamentos Prescritos (Consultar tabla maestra PTDG en SQL Server)
        ptdg_meds = []
        try:
            cursor.execute("""
                SELECT
                    PTDGNum, QTNum, PCType, PCNum, PCFRNum, PTNum,
                    ControllerName, ControllerKey, PTDG_ST, PrescriptionDate,
                    MedicationNumber, Amount, UOM, Route, Frequency,
                    PRN, Why, Dispense, Refills, Notes, Reference,
                    CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    PTDGID, PTID, ControllerID
                FROM PTDG
                WHERE PTNum = ?
                ORDER BY PrescriptionDate DESC, CreatedOn DESC
            """, (pt_num,))
            p_rows = cursor.fetchall()
            p_cols = [c[0] for c in cursor.description]
            for r in p_rows:
                d = dict(zip(p_cols, r))
                med_name = str(d.get("Reference") or d.get("MedicationNumber") or "Fármaco").strip()
                amount_val = str(d.get("Amount") or "").strip()
                uom_val = str(d.get("UOM") or "").strip()
                dose_str = f"{amount_val} {uom_val}".strip() if (amount_val or uom_val) else ""
                p_date = d.get("PrescriptionDate")
                is_active = (str(d.get("PTDG_ST") or "").strip().upper() == "RG")
                status_text = "Activo" if is_active else "Suspendido"
                
                ptdg_meds.append({
                    "ptdg_num": d.get("PTDGNum"),
                    "name": med_name,
                    "dose": dose_str,
                    "amount": amount_val,
                    "uom": uom_val,
                    "route": str(d.get("Route") or "Oral").strip(),
                    "freq": str(d.get("Frequency") or "Cada 8 horas").strip(),
                    "prn": bool(d.get("PRN")),
                    "why": str(d.get("Why") or "").strip(),
                    "dispense": str(d.get("Dispense") or "").strip(),
                    "refills": d.get("Refills") or 0,
                    "instruction": str(d.get("Notes") or "").strip(),
                    "date": p_date.strftime("%d/%m/%Y %H:%M") if p_date else "",
                    "date_iso": p_date.isoformat() if p_date else "",
                    "status": status_text,
                    "ptdg_st": str(d.get("PTDG_ST") or "").strip(),
                    "created_by": str(d.get("CreatedBy") or "Bitacora_SIS").strip(),
                    "ptdg_id": d.get("PTDGID")
                })
        except Exception as e_ptdg_dash:
            print(f"Nota: No se pudo consultar PTDG en dashboard: {e_ptdg_dash}")

        dashboard_data["medications"] = ptdg_meds

        # 2. Dietas y Cuidados de Enfermería (Consultar MR_SOL_DIET)
        diet_row = None
        try:
            cursor.execute("""
                SELECT TOP 1 HORARIO, TIPO, DETALLE, INTOLERANCIA, CreatedOn, CreatedBy, MRNum_SOL_DIET
                FROM MR_SOL_DIET
                WHERE PTNum = ?
                ORDER BY CreatedOn DESC, MRNum_SOL_DIET DESC
            """, (pt_num,))
            diet_r = cursor.fetchone()
            if diet_r:
                diet_cols = [c[0] for c in cursor.description]
                diet_row = dict(zip(diet_cols, diet_r))
        except Exception as e_diet:
            print(f"Nota: No se pudo consultar MR_SOL_DIET: {e_diet}")

        if diet_row and (diet_row.get("TIPO") or diet_row.get("MRNum_SOL_DIET")):
            tipo_map = {
                "A": "Ayuno Estricto", "B": "Dieta Blanda", "N": "Dieta Normal / Hospitalaria",
                "L": "Dieta Líquida", "LC": "Dieta Líquida Clara", "H": "Dieta Hiposódica",
                "D": "Dieta Diabética", "AST": "Dieta Astringente", "SNG": "Dieta Licuada por Sonda"
            }
            raw_t = str(diet_row.get("TIPO") or "").strip()
            tipo_d = tipo_map.get(raw_t.upper(), raw_t) if raw_t in tipo_map else (raw_t or "Dieta Hospitalaria")
            indicaciones_d = str(diet_row.get("DETALLE") or "Sin indicaciones nutricionales específicas.").strip()
            alergias_d = str(diet_row.get("INTOLERANCIA") or "Ninguna registrada").strip()
            inicio_d = diet_row.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if diet_row.get("CreatedOn") else "--"
            horario_d = str(diet_row.get("HORARIO") or "Continuo").strip()
            nutriologo_d = str(diet_row.get("CreatedBy") or "--").strip()

            dashboard_data["dietas"] = {
                "tipo": tipo_d,
                "fase": "--",
                "inicio": inicio_d,
                "indicaciones": indicaciones_d,
                "nutriologo": nutriologo_d,
                "alergias_alimentarias": alergias_d,
                "tolerancia_via_oral": "--",
                "horario": horario_d
            }
        else:
            dashboard_data["dietas"] = {
                "tipo": "Sin dieta asignada",
                "fase": "--",
                "inicio": "--",
                "indicaciones": "No se ha registrado régimen dietético para este paciente.",
                "nutriologo": "--",
                "alergias_alimentarias": "--",
                "tolerancia_via_oral": "--",
                "horario": "--"
            }
        
        # Plan de cuidados clínicos (vacío por defecto hasta que enfermería / médico lo asigne)
        dashboard_data["cuidados_enfermeria"] = []

        # 3. Laboratorios e Imagenología desde dbo.PCIT (solicitudes reales en ERP) y dbo.PTMT (resultados y documentos)
        all_labs = []
        all_imgs = []
        try:
            # 3.1 Consultar resultados y documentos digitalizados en dbo.PTMT
            cursor.execute("""
                SELECT PTMTNum, QTNum, PCType, PCNum, PTNum, MedicalTestDate, MedicalTestType,
                       Description, TestCode, ProcedureDocumentFileName, ProcedureDocumentContentType,
                       ProcedureDocumentLength, Results, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn
                FROM dbo.PTMT
                WHERE PTNum = ?
                ORDER BY CreatedOn DESC, PTMTNum DESC
            """, (pt_num,))
            ptmt_rows = cursor.fetchall()
            ptmt_cols = [c[0] for c in cursor.description]
            ptmt_list = [dict(zip(ptmt_cols, r)) for r in ptmt_rows]

            # 3.2 Consultar solicitudes y órdenes de servicio en dbo.PCIT (con catálogo V_IT y médicos PR)
            cursor.execute("""
                SELECT pcit.PCITNum, pcit.PCType, pcit.PCNum, pcit.PTNum, pcit.SUCode, pcit.ItemCode,
                       COALESCE(it.ItemName, pcit.ItemDescription, pcit.ItemCode) AS Estudio,
                       pcit.Quantity, pcit.PCIT_ST, pcit.CreatedOn, pcit.CreatedBy,
                       COALESCE(pr_rq.FullName, pr_pc.FullName, pcit.CreatedBy, 'MÉDICO TRATANTE') AS SolicitadoPor
                FROM dbo.PCIT pcit
                LEFT JOIN dbo.V_IT it ON pcit.ItemCode = it.ItemCode
                LEFT JOIN dbo.PR pr_rq ON pcit.PR_RQ = pr_rq.PRNum
                LEFT JOIN dbo.PR pr_pc ON pcit.PR_PC = pr_pc.PRNum
                WHERE pcit.PTNum = ? AND pcit.SUCode IN ('ACL', 'IMG', 'GBC') AND pcit.PCIT_ST != 'CA'
                ORDER BY pcit.CreatedOn DESC, pcit.PCITNum DESC
            """, (pt_num,))
            pcit_rows = cursor.fetchall()
            pcit_cols = [c[0] for c in cursor.description]
            pcit_list = [dict(zip(pcit_cols, r)) for r in pcit_rows]

            # 3.3 Correlación inteligente: asociar solicitudes en PCIT con resultados en PTMT
            pcit_matches = {}
            matched_ptmt_ids = set()

            for mt in ptmt_list:
                m_type = str(mt.get("MedicalTestType") or "").upper()
                is_lab_doc = (m_type not in ["RADIOLOGY", "IMAGING", "CARDIOLOGY"])
                mt_on = mt.get("CreatedOn") or mt.get("MedicalTestDate")

                candidates_by_study = {}
                for p in pcit_list:
                    if p["PCITNum"] in pcit_matches:
                        continue
                    p_sucode = str(p.get("SUCode") or "").strip().upper()
                    p_is_lab = (p_sucode == "ACL")
                    if p_is_lab != is_lab_doc:
                        continue

                    p_on = p.get("CreatedOn")
                    diff = abs((mt_on - p_on).total_seconds()) if (mt_on and p_on) else 999999
                    time_ok = (diff <= 86400 * 1.5) or (mt.get("PCNum") and p.get("PCNum") and mt.get("PCNum") == p.get("PCNum"))

                    if time_ok and _match_study_request_with_report(p.get("Estudio", ""), mt.get("Description"), mt.get("ProcedureDocumentFileName")):
                        study_key = p.get("ItemCode") or p.get("Estudio")
                        if study_key not in candidates_by_study or diff < candidates_by_study[study_key][0]:
                            candidates_by_study[study_key] = (diff, p)

                for diff, p in candidates_by_study.values():
                    pcit_matches[p["PCITNum"]] = mt
                    matched_ptmt_ids.add(mt["PTMTNum"])

            # 3.4 Construir lista estructurada de estudios desde solicitudes PCIT
            for p in pcit_list:
                estudio_nom = (p.get("Estudio") or "Estudio Clínico").strip()
                cr_on = p.get("CreatedOn")
                fecha_str = cr_on.strftime("%d/%m/%Y %H:%M") if cr_on else "--"
                sucode = str(p.get("SUCode") or "").strip().upper()
                is_lab = (sucode == "ACL")

                matched_ptmt = pcit_matches.get(p["PCITNum"])
                if matched_ptmt:
                    doc_name = matched_ptmt.get("ProcedureDocumentFileName")
                    doc_len = matched_ptmt.get("ProcedureDocumentLength")
                    has_doc = bool(doc_name or (doc_len and doc_len > 0))
                    study_item = {
                        "id": f"PCIT-{p.get('PCITNum')}",
                        "pcit_num": p.get("PCITNum"),
                        "ptmt_num": matched_ptmt.get("PTMTNum"),
                        "estudio": estudio_nom,
                        "fecha_solicitud": fecha_str,
                        "created_on": cr_on.isoformat() if cr_on else None,
                        "estatus": "Completado" if has_doc else "En Proceso",
                        "solicitado_por": str(p.get("SolicitadoPor") or "MÉDICO TRATANTE").strip(),
                        "resultado_resumen": matched_ptmt.get("Results") or (f"Documento adjunto: {doc_name}" if doc_name else "Estudio procesado en laboratorio"),
                        "valores_criticos": f"Documento oficial digitalizado ({doc_name})" if doc_name else None,
                        "nombre_archivo": doc_name,
                        "content_type": matched_ptmt.get("ProcedureDocumentContentType") or "application/pdf",
                        "tamanio_bytes": doc_len,
                        "tiene_documento": has_doc,
                        "url_pdf": f"/kh/estudios/{matched_ptmt.get('PTMTNum')}/pdf" if has_doc else None,
                        "tipo": "Laboratorio" if is_lab else "Imagenología"
                    }
                else:
                    study_item = {
                        "id": f"PCIT-{p.get('PCITNum')}",
                        "pcit_num": p.get("PCITNum"),
                        "ptmt_num": None,
                        "estudio": estudio_nom,
                        "fecha_solicitud": fecha_str,
                        "created_on": cr_on.isoformat() if cr_on else None,
                        "estatus": "En Proceso",
                        "solicitado_por": str(p.get("SolicitadoPor") or "MÉDICO TRATANTE").strip(),
                        "resultado_resumen": "Estudio solicitado en ERP Medsys. Toma de muestra o procesamiento en curso." if is_lab else "Estudio solicitado en ERP Medsys. Toma de placa o reporte radiológico en curso.",
                        "valores_criticos": None,
                        "nombre_archivo": None,
                        "content_type": None,
                        "tamanio_bytes": None,
                        "tiene_documento": False,
                        "url_pdf": None,
                        "tipo": "Laboratorio" if is_lab else "Imagenología"
                    }

                if is_lab:
                    all_labs.append(study_item)
                else:
                    all_imgs.append(study_item)

            # 3.5 Incorporar documentos PTMT independientes o no asociados directamente a un PCIT
            for mt in ptmt_list:
                if mt.get("PTMTNum") in matched_ptmt_ids:
                    continue
                test_type = str(mt.get("MedicalTestType") or "LABORATORY").upper()
                is_img_doc = test_type in ["RADIOLOGY", "IMAGING", "ULTRASOUND", "XRAY", "GABINETE", "CARDIOLOGY"]
                doc_name = mt.get("ProcedureDocumentFileName")
                doc_len = mt.get("ProcedureDocumentLength")
                has_doc = bool(doc_name or (doc_len and doc_len > 0))
                cr_on = mt.get("CreatedOn") or mt.get("MedicalTestDate")
                fecha_str = cr_on.strftime("%d/%m/%Y %H:%M") if cr_on else "--"
                nombre_estudio = mt.get("Description") or doc_name or f"Estudio de {test_type.capitalize()} #{mt.get('PTMTNum')}"
                if doc_name and doc_name.lower().endswith(".pdf") and not mt.get("Description"):
                    nombre_estudio = doc_name[:-4].replace("_", " ").title()

                study_item = {
                    "id": f"PTMT-{mt.get('PTMTNum')}",
                    "pcit_num": None,
                    "ptmt_num": mt.get("PTMTNum"),
                    "estudio": nombre_estudio,
                    "fecha_solicitud": fecha_str,
                    "created_on": cr_on.isoformat() if cr_on else None,
                    "estatus": "Completado" if has_doc else "En Proceso",
                    "solicitado_por": str(mt.get("CreatedBy") or "MÉDICO TRATANTE").strip(),
                    "resultado_resumen": mt.get("Results") or (f"Documento adjunto: {doc_name}" if doc_name else "Estudio procesado"),
                    "valores_criticos": f"Documento oficial digitalizado ({doc_name})" if doc_name else None,
                    "nombre_archivo": doc_name,
                    "content_type": mt.get("ProcedureDocumentContentType") or "application/pdf",
                    "tamanio_bytes": doc_len,
                    "tiene_documento": has_doc,
                    "url_pdf": f"/kh/estudios/{mt.get('PTMTNum')}/pdf" if has_doc else None,
                    "tipo": "Imagenología" if is_img_doc else "Laboratorio"
                }

                if is_img_doc:
                    all_imgs.append(study_item)
                else:
                    all_labs.append(study_item)

            # 3.6 Ordenar por fecha descendente
            all_labs.sort(key=lambda x: x.get("created_on") or "", reverse=True)
            all_imgs.sort(key=lambda x: x.get("created_on") or "", reverse=True)

        except Exception as e_studies:
            print(f"Nota: Error consultando solicitudes y estudios en EHR dashboard: {e_studies}")

        dashboard_data["laboratorios"] = all_labs
        dashboard_data["imagenologia"] = all_imgs

        # 5. Próximas Citas y Seguimiento (Se alimenta de citas reales en PostgreSQL)
        dashboard_data["proximas_citas"] = []

        # 6. Catálogo Maestro de Formatos Clínicos (+100 Formatos Categorizados)
        dashboard_data["formatos_disponibles"] = [
            {
                "area": "Expediente Integral",
                "icono": "FiLayers",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-EXPEDIENTE-COMPLETO",
                        "nombre": "Expediente Clínico Completo (Compilado NOM-004)",
                        "subtitulo": "Documento maestro integral con carátula foliada, notas de evolución, consentimientos, recetas y paraclínicos",
                        "tipo": "Compilado",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-expediente-completo",
                        "paginas": "Integral",
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Urgencias",
                "icono": "FiAlertCircle",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-87/01",
                        "nombre": "Nota de Evolución de Urgencias",
                        "subtitulo": "Documento general con hasta 3 notas consecutivas y firmas normadas",
                        "tipo": "Evolución",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-nota-urgencias",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-01/01",
                        "nombre": "Historia Clínica de Admisión Urgencias",
                        "subtitulo": "Interrogatorio, antecedentes, examen físico inicial y motivo de urgencia",
                        "tipo": "Admisión",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-12/01",
                        "nombre": "Hoja de Clasificación Triage",
                        "subtitulo": "Evaluación rápida de gravedad, signos vitales y asignación de prioridad (Código)",
                        "tipo": "Triage",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-43",
                        "nombre": "Orden de Intubación Endotraqueal / Soporte Ventilatorio",
                        "subtitulo": "Consentimiento informado y orden médica para intubación orotraqueal y ventilación mecánica",
                        "tipo": "Procedimiento",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-43",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Hospitalización",
                "icono": "FiHome",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-24",
                        "nombre": "Nota de Evolución de Hospitalización",
                        "subtitulo": "Seguimiento médico integral continuo en piso / hospitalización",
                        "tipo": "Evolución",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-nota-hospitalizacion",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-88/01",
                        "nombre": "Nota de Ingreso Hospitalario",
                        "subtitulo": "Registro de pase a piso, indicaciones iniciales y plan de hospitalización",
                        "tipo": "Ingreso",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-89/01",
                        "nombre": "Nota de Evolución en Piso",
                        "subtitulo": "Pase de visita matutino y vespertino por médico adscrito",
                        "tipo": "Evolución",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-95/01",
                        "nombre": "Resumen Clínico de Egreso / Alta",
                        "subtitulo": "Epicrisis, diagnóstico de egreso, tratamiento ambulatorio y citas",
                        "tipo": "Alta",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Cirugía y Quirófano",
                "icono": "FiScissors",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-07",
                        "nombre": "Consentimiento Informado para Procedimientos Quirúrgicos",
                        "subtitulo": "Consentimiento informado oficial para procedimientos quirúrgicos, riesgos y alternativas",
                        "tipo": "Legal y Quirúrgico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-07",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-02",
                        "nombre": "Consentimiento Informado para Tratamiento Quirúrgico / Disentimiento",
                        "subtitulo": "Autorización médica y quirúrgica con registro de tratamientos, anestesia y disentimiento",
                        "tipo": "Legal",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-02",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-40/01",
                        "nombre": "Consentimiento Informado Quirúrgico",
                        "subtitulo": "Autorización de procedimiento con firma de paciente, testigo y cirujano",
                        "tipo": "Legal",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-42/01",
                        "nombre": "Nota Preoperatoria",
                        "subtitulo": "Diagnóstico prequirúrgico, plan operatorio y riesgo anestésico",
                        "tipo": "Quirúrgico",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-45/01",
                        "nombre": "Reporte Quirúrgico y Postoperatorio",
                        "subtitulo": "Descripción de la técnica, hallazgos, sangrado y cuenta de gasas",
                        "tipo": "Quirúrgico",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Consulta Externa e Interconsultas",
                "icono": "FiUsers",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-02/01",
                        "nombre": "Historia Clínica de Consulta Externa",
                        "subtitulo": "Expediente ambulatorio por especialidad médica",
                        "tipo": "Consulta",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-55/01",
                        "nombre": "Nota de Interconsulta Especializada",
                        "subtitulo": "Solicitud y respuesta de valoración por médico especialista",
                        "tipo": "Interconsulta",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Servicios Auxiliares y Diagnóstico",
                "icono": "FiActivity",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-70/01",
                        "nombre": "Solicitud de Exámenes de Laboratorio",
                        "subtitulo": "Orden electrónica de análisis clínicos y pruebas especiales",
                        "tipo": "Laboratorio",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-72/01",
                        "nombre": "Solicitud de Gabinete e Imagenología",
                        "subtitulo": "Orden de estudios radiológicos, ultrasonidos y tomografías",
                        "tipo": "Imagen",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-32/01",
                        "nombre": "Consentimiento Informado para Ecocardiograma Transesofágico",
                        "subtitulo": "Autorización para realización de estudio bajo sedación con apoyo de anestesiólogo cardiovascular",
                        "tipo": "Legal",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-32-01",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-EED",
                        "nombre": "Ecocardiograma de Estrés con Dobutamina",
                        "subtitulo": "Consentimiento informado y hoja de monitoreo hemodinámico",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-eed",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-25",
                        "nombre": "Consentimiento Informado para Revisión Ginecológica, Obstétrica y Consulta Externa",
                        "subtitulo": "Autorización para revisión ginecológica u obstétrica, estudios y procedimientos en consulta externa",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-25",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-34",
                        "nombre": "Consentimiento Informado para Estudio de Mesa Inclinada (Tilt Test)",
                        "subtitulo": "Consentimiento informado y hoja de monitoreo hemodinámico protocolo INICICH",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-34-01",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-12",
                        "nombre": "Consentimiento Revisión Gineco y Obstetricia (Hosp. / Urg.)",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-12 • Consentimiento Informado Hospitalización y Urgencias",
                        "area": "Ginecología y Obstetricia / Urgencias",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-12",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-04",
                        "nombre": "Consentimiento Colocación de Catéter Venoso Central",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-04 • Consentimiento Informado Procedimientos y Cirugía",
                        "area": "Procedimientos / Cirugía",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-04",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-15",
                        "nombre": "Consentimiento Informado para Cesárea / Disentimiento",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-15 • Consentimiento o Negativa Informada",
                        "area": "Ginecología y Obstetricia",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-15",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-08",
                        "nombre": "Consentimiento Diagnóstico en Admisión Continua",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-08 • Tratamiento y procedimientos diagnósticos en admisión continua",
                        "area": "Admisión Continua / Urgencias",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-08",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-11",
                        "nombre": "Consentimiento de No Reanimación (Voluntad Anticipada)",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-11 • Voluntad anticipada y limitación del esfuerzo terapéutico",
                        "area": "Medicina Interna / Urgencias / UCI",
                        "tipo": "Legal y Bioético",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-11",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-19",
                        "nombre": "Consentimiento Informado para Histerectomía",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-19 • Autorización o negativa para intervención quirúrgica de histerectomía",
                        "area": "Ginecología y Obstetricia",
                        "tipo": "Quirúrgico y Legal",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-19",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-15",
                        "nombre": "Egreso Voluntario",
                        "subtitulo": "HE-DIRMED-SINPRO-PLT-15 • Documento formal de alta voluntaria contra opinión médica",
                        "area": "Hospitalización y Urgencias",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-egreso-voluntario-15",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-06",
                        "nombre": "Consentimiento para Autorizar Procedimiento Anestésico",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-06 • Evaluación anestesiológica, riesgos y autorización del acto anestésico",
                        "area": "Anestesiología y Quirófano",
                        "tipo": "Legal y Anestésico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-06",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            }
        ]

        # Filtrar solo los formatos activos para que solo salgan los que ya tenemos hechos
        for categoria in dashboard_data["formatos_disponibles"]:
            categoria["formatos"] = [f for f in categoria["formatos"] if f.get("activo")]
        dashboard_data["formatos_disponibles"] = [c for c in dashboard_data["formatos_disponibles"] if len(c["formatos"]) > 0]

        # 6.5 CONSTRUCCIÓN INTEGRAL Y CRONOLÓGICA DE LA LÍNEA DE TIEMPO (TIMELINE)
        raw_timeline = []

        # A. Formatos de Evolución (MR_NE_URG)
        for ev in evoluciones_list:
            if ev:
                dashboard_data["clinicalNotes"].append({
                    "evolution_num": ev["num"],
                    "title": ev["title"],
                    "date": ev["fecha"],
                    "time": ev["hora"],
                    "turno": ev["turno"],
                    "doctor": ev["medico"],
                    "diagnosis": dashboard_data["patient"]["diagnostico"],
                    "soap": {
                        "s": ev["subjetivo"],
                        "o": ev["objetivo"],
                        "a": ev["analisis"],
                        "p": ev["plan"]
                    }
                })
                # Determinar fecha/hora exacta
                ev_dt = None
                date_col_map = {1: 'FECHANOTA1', 2: 'FECHANOTA2', 3: 'FECHANOTA3'}
                if nota_dict.get(date_col_map.get(ev["num"])):
                    ev_dt = nota_dict.get(date_col_map.get(ev["num"]))
                elif nota_dict.get('ModifiedOn'):
                    ev_dt = nota_dict.get('ModifiedOn')
                elif nota_dict.get('CreatedOn'):
                    ev_dt = nota_dict.get('CreatedOn')

                raw_timeline.append({
                    "_dt": ev_dt,
                    "date": ev["fecha"],
                    "time": ev["hora"],
                    "type": f"Nota de Evolución {ev['num']}",
                    "category": "Evolución Clínica",
                    "badge": "Formato 87/01",
                    "format_code": "HE-DIRMED-SINPRO-PLT-87/01",
                    "desc": f"El Dr(a). {ev['medico']} registró la Evolución {ev['num']} (Turno {ev['turno']}).",
                    "doctor": ev["medico"],
                    "pdf_url": f"/ehr/paciente/{pt_num}/pdf-nota-urgencias",
                    "action_type": "format"
                })

        # A.2. Notas de Evolución de Hospitalización (MR_24_HOJA_EVOL)
        if evoluciones_hosp_list:
            for ev_h in evoluciones_hosp_list:
                h_dt = None
                try:
                    if ev_h.get("date_iso"):
                        h_dt = datetime.datetime.fromisoformat(ev_h["date_iso"])
                except Exception:
                    pass

                raw_timeline.append({
                    "_dt": h_dt,
                    "date": ev_h["fecha"],
                    "time": ev_h["hora"],
                    "type": f"Nota de Evolución Hosp. {ev_h['num']}",
                    "category": "Evolución Clínica Hospitalaria",
                    "badge": "Formato 24",
                    "format_code": "HE-DIRMED-CONSUL-PLT-24",
                    "desc": f"El Dr(a). {ev_h['medico']} registró la Evolución {ev_h['num']} (Turno {ev_h['turno']}).",
                    "doctor": ev_h["medico"],
                    "pdf_url": f"/ehr/paciente/{pt_num}/pdf-nota-hospitalizacion?evolucion={ev_h['num']}",
                    "action_type": "format"
                })

        # B. Consentimiento 32/01 - Ecocardiograma Transesofágico (MR_CI_ETE_CARD)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_ETE_CARD, INTETYPE, N_MEDICO, DIAGNOSTICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, ESignature
                FROM MR_CI_ETE_CARD 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r32 in cursor.fetchall():
                if r32[1] or r32[2] or r32[3] or r32[6]:
                    dt32 = r32[5] or r32[4] or r32[7]
                    med32 = str(r32[2] or r32[6] or "Médico Tratante HES")
                    diag32 = str(r32[3] or "Valoración Cardiológica")
                    raw_timeline.append({
                        "_dt": dt32,
                        "date": dt32.strftime('%d/%m/%Y') if dt32 else "",
                        "time": dt32.strftime('%H:%M') if dt32 else "",
                        "type": "Consentimiento Informado: Ecocardiograma Transesofágico (32/01)",
                        "category": "Consentimiento Informado",
                        "badge": "Formato 32/01",
                        "format_code": "HE-DIRMED-CONSUL-PLT-32/01",
                        "desc": f"El Dr(a). {med32} registró el Consentimiento Informado (32/01) para Ecocardiograma Transesofágico. Diagnóstico: {diag32}.",
                        "doctor": med32,
                        "signed": bool(r32[6] or r32[8]),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-32-01",
                        "action_type": "format"
                    })
        except Exception as e_c32_tl:
            print(f"Nota: Error agregando consentimiento 32/01 a timeline: {e_c32_tl}")

        # C. Ecocardiograma de Estrés con Dobutamina (MR_CI_EED)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_EED, NOMBRE_MEDICO, RESPONSABLE, FC_META, COMENTARIOS,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, ESignature
                FROM MR_CI_EED 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for reed in cursor.fetchall():
                if reed[1] or reed[2] or reed[4] or reed[7]:
                    dted = reed[6] or reed[5] or reed[8]
                    med_ed = str(reed[1] or reed[7] or "Médico Tratante HES")
                    resp_ed = str(reed[2] or "Paciente")
                    fc_ed = str(reed[3] or "145")
                    raw_timeline.append({
                        "_dt": dted,
                        "date": dted.strftime('%d/%m/%Y') if dted else "",
                        "time": dted.strftime('%H:%M') if dted else "",
                        "type": "Ecocardiograma de Estrés con Dobutamina (EED)",
                        "category": "Consentimiento y Monitoreo",
                        "badge": "Formato EED",
                        "format_code": "HE-DIRMED-CONSUL-PLT-EED",
                        "desc": f"Registro y protocolo de Ecocardiograma de Estrés con Dobutamina (FC Meta: {fc_ed} lpm). Responsable: {resp_ed}.",
                        "doctor": med_ed,
                        "signed": bool(reed[7] or reed[9]),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-eed",
                        "action_type": "format"
                    })
        except Exception as e_eed_tl:
            print(f"Nota: Error agregando EED a timeline: {e_eed_tl}")

        # C2. Consentimiento 12 - Gineco Hosp / Urg (MR_CI_RGO_HU)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_RGO_HU, N_MEDICO, DIAGNOSTICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_RGO_HU 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r12 in cursor.fetchall():
                if r12[1] or r12[2] or r12[5]:
                    dt12 = r12[4] or r12[3] or r12[6]
                    med12 = str(r12[1] or r12[5] or "Médico Tratante HES")
                    diag12 = str(r12[2] or "Revisión Gineco-Obstétrica")
                    raw_timeline.append({
                        "_dt": dt12,
                        "date": dt12.strftime('%d/%m/%Y') if dt12 else "",
                        "time": dt12.strftime('%H:%M') if dt12 else "",
                        "type": "Consentimiento Informado: Revisión Gineco y Obstetricia (12)",
                        "category": "Consentimiento Informado",
                        "badge": "Formato 12",
                        "format_code": "HE-DIRMED-CONSUL-PLT-12",
                        "desc": f"El Dr(a). {med12} registró el Consentimiento Gineco y Obstetricia (Hosp/Urg). Diagnóstico: {diag12}.",
                        "doctor": med12,
                        "signed": bool(r12[5] or r12[7] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-12",
                        "action_type": "format"
                    })
        except Exception as e_c12_tl:
            print(f"Nota: Error agregando consentimiento 12 a timeline: {e_c12_tl}")

        # C3. Consentimiento 04 - Catéter Venoso Central (MR_CI_CC)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_CC, N_MEDICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_CC 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r04 in cursor.fetchall():
                if r04[1] or r04[4]:
                    dt04 = r04[3] or r04[2] or r04[5]
                    med04 = str(r04[1] or r04[4] or "Médico Tratante HES")
                    raw_timeline.append({
                        "_dt": dt04,
                        "date": dt04.strftime('%d/%m/%Y') if dt04 else "",
                        "time": dt04.strftime('%H:%M') if dt04 else "",
                        "type": "Consentimiento Informado: Colocación de Catéter Venoso Central (04)",
                        "category": "Consentimiento Informado",
                        "badge": "Formato 04",
                        "format_code": "HE-DIRMED-CONSUL-PLT-04",
                        "desc": f"El Dr(a). {med04} registró el Consentimiento Informado para Colocación de Catéter Venoso Central.",
                        "doctor": med04,
                        "signed": bool(r04[4] or r04[6] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-04",
                        "action_type": "format"
                    })
        except Exception as e_c04_tl:
            print(f"Nota: Error agregando consentimiento 04 a timeline: {e_c04_tl}")

        # C4. Consentimiento 15 - Cesárea / Disentimiento (MR_CI_CES)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_CES, N_MEDICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_CES 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r15 in cursor.fetchall():
                if r15[1] or r15[4]:
                    dt15 = r15[3] or r15[2] or r15[5]
                    med15 = str(r15[1] or r15[4] or "Médico Tratante HES")
                    raw_timeline.append({
                        "_dt": dt15,
                        "date": dt15.strftime('%d/%m/%Y') if dt15 else "",
                        "time": dt15.strftime('%H:%M') if dt15 else "",
                        "type": "Consentimiento Informado: Cesárea / Disentimiento (15)",
                        "category": "Consentimiento Informado",
                        "badge": "Formato 15",
                        "format_code": "HE-DIRMED-CONSUL-PLT-15",
                        "desc": f"El Dr(a). {med15} registró el Consentimiento / Disentimiento Informado para Cesárea.",
                        "doctor": med15,
                        "signed": bool(r15[4] or r15[6] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-15",
                        "action_type": "format"
                    })
        except Exception as e_c15_tl:
            print(f"Nota: Error agregando consentimiento 15 a timeline: {e_c15_tl}")

        # C5. Consentimiento 08 - Admisión Continua y Diagnóstico (MR_08_CI_DIAGNOSTICO_ADMISION_CONTI)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI, N_MEDICO, DIAGNOSTICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_08_CI_DIAGNOSTICO_ADMISION_CONTI 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r08 in cursor.fetchall():
                if r08[1] or r08[5] or r08[2]:
                    dt08 = r08[4] or r08[3] or r08[6]
                    med08 = str(r08[1] or r08[5] or "Médico Tratante HES")
                    diag08 = str(r08[2] or "Admisión Continua y Diagnóstico")
                    raw_timeline.append({
                        "_dt": dt08,
                        "date": dt08.strftime('%d/%m/%Y') if dt08 else "",
                        "time": dt08.strftime('%H:%M') if dt08 else "",
                        "type": "Consentimiento Informado: Admisión Continua y Diagnóstico (08)",
                        "category": "Consentimiento Informado",
                        "badge": "Formato 08",
                        "format_code": "HE-DIRMED-CONSUL-PLT-08",
                        "desc": f"El Dr(a). {med08} registró el Consentimiento Informado para Admisión Continua y Diagnóstico. Diagnóstico: {diag08}.",
                        "doctor": med08,
                        "signed": bool(r08[5] or r08[7] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-08",
                        "action_type": "format"
                    })
        except Exception as e_c08_tl:
            print(f"Nota: Error agregando consentimiento 08 a timeline: {e_c08_tl}")

        # C6. Formato 43 - Orden de Intubación Endotraqueal / Soporte Ventilatorio (MR_CI_OI)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_OI, N_MEDICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_OI 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r43 in cursor.fetchall():
                if r43[1] or r43[4]:
                    dt43 = r43[3] or r43[2] or r43[5]
                    med43 = str(r43[1] or r43[4] or "Médico Tratante HES")
                    raw_timeline.append({
                        "_dt": dt43,
                        "date": dt43.strftime('%d/%m/%Y') if dt43 else "",
                        "time": dt43.strftime('%H:%M') if dt43 else "",
                        "type": "Orden de Intubación Endotraqueal / Soporte Ventilatorio (43)",
                        "category": "Consentimiento / Procedimiento",
                        "badge": "Formato 43",
                        "format_code": "HE-DIRMED-SINPRO-PLT-43",
                        "desc": f"El Dr(a). {med43} registró la Orden y Consentimiento Informado para Intubación Endotraqueal.",
                        "doctor": med43,
                        "signed": bool(r43[4] or r43[6] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-43",
                        "action_type": "format"
                    })
        except Exception as e_c43_tl:
            print(f"Nota: Error agregando consentimiento 43 a timeline: {e_c43_tl}")

        # C7. Formato 11 - Consentimiento de No Reanimación (MR_CI_NO_REANIMACION)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_NO_REANIMACION, N_MEDICO, DIAGNOSTICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_NO_REANIMACION 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r11 in cursor.fetchall():
                if r11[1] or r11[5]:
                    dt11 = r11[4] or r11[3] or r11[6]
                    med11 = str(r11[1] or r11[5] or "Médico Tratante HES")
                    raw_timeline.append({
                        "_dt": dt11,
                        "date": dt11.strftime('%d/%m/%Y') if dt11 else "",
                        "time": dt11.strftime('%H:%M') if dt11 else "",
                        "type": "Consentimiento de No Reanimación / Voluntad Anticipada (11)",
                        "category": "Voluntad Anticipada / Legal",
                        "badge": "Formato 11",
                        "format_code": "HE-DIRMED-CONSUL-PLT-11",
                        "desc": f"El Dr(a). {med11} registró el Consentimiento de No Reanimación. Diagnóstico: {r11[2] or 'Etapa avanzada'}.",
                        "doctor": med11,
                        "signed": bool(r11[5] or r11[7] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-11?mrnum={r11[0]}",
                        "action_type": "format"
                    })
        except Exception as e_c11_tl:
            print(f"Nota: Error agregando consentimiento 11 a timeline: {e_c11_tl}")

        # C8. Formato 19 - Consentimiento Informado para Histerectomía (MR_CI_HISTERECTOMIA)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_HISTERECTOMIA, N_MEDICO, DIAGNOSTICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_HISTERECTOMIA 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r19 in cursor.fetchall():
                if r19[1] or r19[5]:
                    dt19 = r19[4] or r19[3] or r19[6]
                    med19 = str(r19[1] or r19[5] or "Médico Tratante HES")
                    raw_timeline.append({
                        "_dt": dt19,
                        "date": dt19.strftime('%d/%m/%Y') if dt19 else "",
                        "time": dt19.strftime('%H:%M') if dt19 else "",
                        "type": "Consentimiento Informado para Histerectomía (19)",
                        "category": "Consentimiento Quirúrgico",
                        "badge": "Formato 19",
                        "format_code": "HE-DIRMED-CONSUL-PLT-19",
                        "desc": f"El Dr(a). {med19} registró el Consentimiento para Histerectomía. Diagnóstico: {r19[2] or 'Ginecología'}.",
                        "doctor": med19,
                        "signed": bool(r19[5] or r19[7] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-19?mrnum={r19[0]}",
                        "action_type": "format"
                    })
        except Exception as e_c19_tl:
            print(f"Nota: Error agregando consentimiento 19 a timeline: {e_c19_tl}")

        # C9. Formato 15 - Egreso Voluntario (MR_EV_HOSP)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_EV_HOSP, N_MEDICO, N_REPLEGAL,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_EV_HOSP 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r15ev in cursor.fetchall():
                if r15ev[1] or r15ev[5]:
                    dt15ev = r15ev[4] or r15ev[3] or r15ev[6]
                    med15ev = str(r15ev[1] or r15ev[5] or "Médico Tratante HES")
                    raw_timeline.append({
                        "_dt": dt15ev,
                        "date": dt15ev.strftime('%d/%m/%Y') if dt15ev else "",
                        "time": dt15ev.strftime('%H:%M') if dt15ev else "",
                        "type": "Egreso Voluntario / Alta Disentida (15)",
                        "category": "Egreso / Legal",
                        "badge": "Formato 15 EV",
                        "format_code": "HE-DIRMED-SINPRO-PLT-15",
                        "desc": f"El Dr(a). {med15ev} registró el Egreso Voluntario. Representante/Declarante: {r15ev[2] or 'Paciente'}.",
                        "doctor": med15ev,
                        "signed": bool(r15ev[5] or r15ev[7] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-egreso-voluntario-15?mrnum={r15ev[0]}",
                        "action_type": "format"
                    })
        except Exception as e_c15ev_tl:
            print(f"Nota: Error agregando egreso voluntario 15 a timeline: {e_c15ev_tl}")

        # C10. Formato 06 - Consentimiento para Autorizar Procedimiento Anestésico (MR_CI_APA)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_APA, N_MEDICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_APA 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r06 in cursor.fetchall():
                if r06[1] or r06[4]:
                    dt06 = r06[3] or r06[2] or r06[5]
                    med06 = str(r06[1] or r06[4] or "Médico Anestesiólogo")
                    raw_timeline.append({
                        "_dt": dt06,
                        "date": dt06.strftime('%d/%m/%Y') if dt06 else "",
                        "time": dt06.strftime('%H:%M') if dt06 else "",
                        "type": "Consentimiento para Procedimiento Anestésico (06)",
                        "category": "Anestesiología / Quirófano",
                        "badge": "Formato 06",
                        "format_code": "HE-DIRMED-CONSUL-PLT-06",
                        "desc": f"El Dr(a). {med06} registró el Consentimiento para Procedimiento Anestésico.",
                        "doctor": med06,
                        "signed": bool(r06[4] or r06[6] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-06?mrnum={r06[0]}",
                        "action_type": "format"
                    })
        except Exception as e_c06_tl:
            print(f"Nota: Error agregando consentimiento 06 a timeline: {e_c06_tl}")

        # D. Prescripciones Médicas de Fármacos (PTDG)
        for med in ptdg_meds:
            med_dt = None
            if med.get("date_iso"):
                try:
                    med_dt = datetime.datetime.fromisoformat(med["date_iso"])
                except Exception:
                    pass
            raw_timeline.append({
                "_dt": med_dt,
                "date": med.get("date", "").split(" ")[0] if " " in med.get("date", "") else med.get("date", ""),
                "time": med.get("date", "").split(" ")[1] if " " in med.get("date", "") else "",
                "type": f"Prescripción Médica: {med['name']}",
                "category": "Farmacoterapia",
                "badge": "Medicamento",
                "format_code": "",
                "desc": f"{med['dose']} vía {med['route']} ({med['freq']}). {med['instruction'] or med['why']}".strip(),
                "doctor": med.get("created_by", ""),
                "action_type": "tab_medications"
            })

        # E. Prescripciones Nutricionales / Dietas (MR_SOL_DIET)
        try:
            cursor.execute("""
                SELECT TOP 5 MRNum_SOL_DIET, HORARIO, TIPO, DETALLE, INTOLERANCIA, CreatedOn, CreatedBy 
                FROM MR_SOL_DIET 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for dr in cursor.fetchall():
                if dr[2] or dr[3]:
                    dt_diet = dr[5]
                    t_str = tipo_map.get(str(dr[2] or "").upper(), str(dr[2] or "Hospitalaria")) if 'tipo_map' in locals() else str(dr[2] or "Dieta")
                    raw_timeline.append({
                        "_dt": dt_diet,
                        "date": dt_diet.strftime('%d/%m/%Y') if dt_diet else "",
                        "time": dt_diet.strftime('%H:%M') if dt_diet else "",
                        "type": f"Prescripción de Dieta: {t_str}",
                        "category": "Nutrición y Cuidados",
                        "badge": "Dieta",
                        "format_code": "",
                        "desc": f"Régimen: {t_str} ({dr[1] or 'Continuo'}). {dr[3] or ''}".strip(),
                        "doctor": str(dr[6] or ""),
                        "action_type": "tab_diets"
                    })
        except Exception as e_diet_tl:
            print(f"Nota: Error agregando dietas a timeline: {e_diet_tl}")

        # F. Signos Vitales (PTVS)
        try:
            cursor.execute("""
                SELECT TOP 3 
                    PTVSNum, ProcedureDate, SystolicPressure, DiastolicPressure, 
                    PulseRate, RespiratroryRAte, OxygenSaturation, Temperature, Weight, 
                    CreatedBy, CreatedOn 
                FROM PTVS 
                WHERE PTNum = ? 
                ORDER BY ProcedureDate DESC, CreatedOn DESC
            """, (pt_num,))
            for pv in cursor.fetchall():
                dt_vs = pv[1] or pv[10]
                sys_p = pv[2] or "--"
                dia_p = pv[3] or "--"
                fc_p = pv[4] or "--"
                fr_p = pv[5] or "--"
                sat_p = pv[6] or "--"
                raw_timeline.append({
                    "_dt": dt_vs,
                    "date": dt_vs.strftime('%d/%m/%Y') if dt_vs else "",
                    "time": dt_vs.strftime('%H:%M') if dt_vs else "",
                    "type": "Registro de Signos Vitales",
                    "category": "Monitoreo Clínico",
                    "badge": "Signos Vitales",
                    "format_code": "",
                    "desc": f"TA: {sys_p}/{dia_p} mmHg • FC: {fc_p} lpm • FR: {fr_p} rpm • SpO2: {sat_p}% • Temp: {pv[7] or '--'}°C • Peso: {pv[8] or '--'} kg",
                    "doctor": str(pv[9] or ""),
                    "action_type": "vitals_modal"
                })
        except Exception as e_vs_tl:
            print(f"Nota: Error agregando signos vitales a timeline: {e_vs_tl}")

        # G. Movimientos de Cama (UDR_RPT_HABITACION)
        seen_rooms = set()
        for r in timeline_rows:
            if r[1]:
                room_key = (str(r[0]), r[1].strftime('%Y-%m-%d %H:%M'))
                if room_key in seen_rooms:
                    continue
                seen_rooms.add(room_key)
                raw_timeline.append({
                    "_dt": r[1],
                    "date": r[1].strftime('%d/%m/%Y'),
                    "time": r[1].strftime('%H:%M'),
                    "type": "Asignación de Cama",
                    "category": "Admisión y Traslado",
                    "badge": "Ubicación",
                    "format_code": "",
                    "desc": f"Paciente asignado a {str(r[0] or 'Urgencias')}",
                    "doctor": "",
                    "action_type": "none"
                })

        # H. Formato 02 - Tratamiento Quirúrgico / Disentimiento (MR_02_CI_TRATAMIENTO_QUIRURGICO)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_02_CI_TRATAMIENTO_QUIRURGICO, N_MEDICO, DIAGNOSTICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_02_CI_TRATAMIENTO_QUIRURGICO 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r02 in cursor.fetchall():
                if r02[1] or r02[5]:
                    dt02 = r02[4] or r02[3] or r02[6]
                    med02 = str(r02[1] or r02[5] or "Médico Tratante HES")
                    diag02 = str(r02[2] or "Procedimiento Quirúrgico")
                    raw_timeline.append({
                        "_dt": dt02,
                        "date": dt02.strftime('%d/%m/%Y') if dt02 else "",
                        "time": dt02.strftime('%H:%M') if dt02 else "",
                        "type": "Consentimiento Informado: Tratamiento Quirúrgico / Disentimiento (02)",
                        "category": "Consentimiento Informado",
                        "badge": "Formato 02",
                        "format_code": "HE-DIRMED-CONSUL-PLT-02",
                        "desc": f"El Dr(a). {med02} registró el Consentimiento para Procedimiento Quirúrgico / Anestesia. Diagnóstico: {diag02}.",
                        "doctor": med02,
                        "signed": bool(r02[5] or r02[7] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-02?mrnum={r02[0] or 1}",
                        "action_type": "format"
                    })
        except Exception as e_c02_tl:
            print(f"Nota: Error agregando consentimiento 02 a timeline: {e_c02_tl}")

        # I. Formato 25 - Revisión Gineco Consulta Externa (MR_CI_RGO_CE)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_RGO_CE, N_MEDICO,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_RGO_CE 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r25 in cursor.fetchall():
                if r25[1] or r25[4]:
                    dt25 = r25[3] or r25[2] or r25[5]
                    med25 = str(r25[1] or r25[4] or "Médico Tratante HES")
                    raw_timeline.append({
                        "_dt": dt25,
                        "date": dt25.strftime('%d/%m/%Y') if dt25 else "",
                        "time": dt25.strftime('%H:%M') if dt25 else "",
                        "type": "Consentimiento Informado: Revisión Gineco Consulta Externa (25)",
                        "category": "Consentimiento Informado",
                        "badge": "Formato 25",
                        "format_code": "HE-DIRMED-CONSUL-PLT-25",
                        "desc": f"El Dr(a). {med25} registró el Consentimiento para Revisión Gineco y Obstétrica en Consulta Externa.",
                        "doctor": med25,
                        "signed": bool(r25[4] or r25[6] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-25?mrnum={r25[0] or 1}",
                        "action_type": "format"
                    })
        except Exception as e_c25_tl:
            print(f"Nota: Error agregando consentimiento 25 a timeline: {e_c25_tl}")

        # J. Formato 34/01 - Mesa Inclinada (MR_CI_EMI)
        try:
            cursor.execute("""
                SELECT TOP 5 
                    MRNum_CI_EMI, NOMBRE_MEDICO_MI,
                    CreatedOn, ModifiedOn, SignedBy, SignedOn, MR_ST
                FROM MR_CI_EMI 
                WHERE PTNum = ? 
                ORDER BY CreatedOn DESC
            """, (pt_num,))
            for r34 in cursor.fetchall():
                if r34[1] or r34[4]:
                    dt34 = r34[3] or r34[2] or r34[5]
                    med34 = str(r34[1] or r34[4] or "Médico Tratante HES")
                    raw_timeline.append({
                        "_dt": dt34,
                        "date": dt34.strftime('%d/%m/%Y') if dt34 else "",
                        "time": dt34.strftime('%H:%M') if dt34 else "",
                        "type": "Consentimiento Informado: Estudio de Mesa Inclinada (34/01)",
                        "category": "Consentimiento Informado",
                        "badge": "Formato 34/01",
                        "format_code": "HE-DIRMED-CONSUL-PLT-34",
                        "desc": f"El Dr(a). {med34} registró el Consentimiento / Protocolo de Mesa Inclinada (Tilt Test).",
                        "doctor": med34,
                        "signed": bool(r34[4] or r34[6] == 'SG'),
                        "pdf_url": f"/ehr/paciente/{pt_num}/pdf-consentimiento-34-01?mrnum={r34[0] or 1}",
                        "action_type": "format"
                    })
        except Exception as e_c34_tl:
            print(f"Nota: Error agregando consentimiento 34 a timeline: {e_c34_tl}")

        # K. Laboratorios Clínicos
        for lab in dashboard_data.get("laboratorios", []):
            lab_dt = None
            f_sol = lab.get("fecha_solicitud", "")
            if f_sol:
                try:
                    lab_dt = datetime.datetime.strptime(f_sol, "%d/%m/%Y %H:%M")
                except Exception:
                    pass
            raw_timeline.append({
                "_dt": lab_dt,
                "date": f_sol.split(" ")[0] if " " in f_sol else (dashboard_data['patient'].get('fecha_ingreso') or ""),
                "time": f_sol.split(" ")[1] if " " in f_sol else "12:00",
                "type": f"Laboratorio: {lab.get('estudio', 'Estudio de Laboratorio')}",
                "category": "Laboratorio Clínico",
                "badge": "Laboratorio",
                "format_code": "HE-DIRMED-SINPRO-PLT-70/01",
                "desc": f"Estudio {lab.get('estudio')} ({lab.get('estatus', 'Completado')}). {lab.get('resultado_resumen', '')} {lab.get('valores_criticos', '')}".strip(),
                "doctor": lab.get("solicitado_por", ""),
                "action_type": "tab_labs"
            })

        # L. Imagenología y Gabinete
        for img in dashboard_data.get("imagenologia", []):
            img_dt = None
            f_sol_img = img.get("fecha_solicitud", "")
            if f_sol_img:
                try:
                    img_dt = datetime.datetime.strptime(f_sol_img, "%d/%m/%Y %H:%M")
                except Exception:
                    pass
            raw_timeline.append({
                "_dt": img_dt,
                "date": f_sol_img.split(" ")[0] if " " in f_sol_img else (dashboard_data['patient'].get('fecha_ingreso') or ""),
                "time": f_sol_img.split(" ")[1] if " " in f_sol_img else "13:00",
                "type": f"Imagenología: {img.get('estudio', 'Estudio de Gabinete')}",
                "category": "Imagenología y Gabinete",
                "badge": "Imagenología",
                "format_code": "HE-DIRMED-SINPRO-PLT-72/01",
                "desc": f"Estudio {img.get('estudio')} ({img.get('estatus', 'Completado')}). Hallazgos: {img.get('hallazgos', '')}. Conclusión: {img.get('conclusion', '')}".strip(),
                "doctor": img.get("solicitado_por", ""),
                "action_type": "tab_imaging"
            })

        # M. Evento de Ingreso
        if entry_dt:
            raw_timeline.append({
                "_dt": entry_dt,
                "date": entry_dt.strftime('%d/%m/%Y') if hasattr(entry_dt, 'strftime') else "",
                "time": entry_dt.strftime('%H:%M') if hasattr(entry_dt, 'strftime') else "",
                "type": "Ingreso Hospitalario y Apertura de Episodio",
                "category": "Admisión Hospitalaria",
                "badge": "Ingreso",
                "format_code": "",
                "desc": f"Ingreso del paciente a {dashboard_data['patient'].get('cama') or 'Urgencias'}. Diagnóstico de Ingreso: {dashboard_data['patient'].get('diagnostico', 'N/D')}.",
                "doctor": "",
                "action_type": "none"
            })

        # N. Evento de Egreso / Alta (si aplica)
        if has_discharge and exit_dt:
            raw_timeline.append({
                "_dt": exit_dt,
                "date": exit_dt.strftime('%d/%m/%Y') if hasattr(exit_dt, 'strftime') else "",
                "time": exit_dt.strftime('%H:%M') if hasattr(exit_dt, 'strftime') else "",
                "type": "Alta Médica y Cierre de Episodio Clínico",
                "category": "Egreso Clínico",
                "badge": "Alta Médica",
                "format_code": "",
                "desc": f"Episodio clínico cerrado formalmente. Paciente egresado del hospital conforme a la NOM-004-SSA3-2012 / NOM-024-SSA3-2012.",
                "doctor": "",
                "action_type": "none"
            })

        # ORDENAMIENTO CRONOLÓGICO DESCENDENTE ESTRICTO
        def event_sort_comparator(item):
            d = item.get("_dt")
            if isinstance(d, datetime.datetime):
                return d
            elif isinstance(d, datetime.date):
                return datetime.datetime.combine(d, datetime.time.min)
            return datetime.datetime.min

        raw_timeline.sort(key=event_sort_comparator, reverse=True)

        # Limpiar clave temporal y asignar
        for idx, evt in enumerate(raw_timeline):
            dt_obj = evt.pop("_dt", None)
            if dt_obj and not evt.get("date"):
                evt["date"] = dt_obj.strftime('%d/%m/%Y')
                evt["time"] = dt_obj.strftime('%H:%M')
            if dt_obj:
                evt["timestamp"] = dt_obj.isoformat()
            evt["id"] = f"tl_{idx+1}"

        dashboard_data["timelineEvents"] = raw_timeline

        # 7. Resumen de Cargos y Solicitudes en Vivo (Para el Sidebar Derecho)
        solicitudes_pendientes = []
        for lab in dashboard_data.get("laboratorios", []):
            if lab.get("estatus") != "Completado":
                solicitudes_pendientes.append({
                    "titulo": lab.get("estudio"),
                    "estado": lab.get("estatus", "En Proceso"),
                    "tipo": "Laboratorio"
                })
        for img in dashboard_data.get("imagenologia", []):
            if img.get("estatus") != "Completado":
                solicitudes_pendientes.append({
                    "titulo": img.get("estudio"),
                    "estado": img.get("estatus", "En Proceso"),
                    "tipo": "Imagenología"
                })

        dashboard_data["cargos_solicitudes"] = {
            "dieta_activa": dashboard_data.get("dietas", {}).get("tipo", "Sin dieta asignada"),
            "medicamentos_activos_count": len(dashboard_data.get("medications", [])),
            "laboratorios_count": len(dashboard_data.get("laboratorios", [])),
            "imagenologia_count": len(dashboard_data.get("imagenologia", [])),
            "proxima_cita": dashboard_data["proximas_citas"][0] if dashboard_data.get("proximas_citas") else None,
            "solicitudes_pendientes": solicitudes_pendientes[:6]
        }
        
        return dashboard_data
        
    except Exception as e:
        print(f"Error fetching full EHR data: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@explicit_kh_mutation
def save_or_update_nota_urgencias(pt_num: str, nota_data: dict) -> dict:
    """
    Crea o actualiza una evolución consecutiva (sin límite: 1, 2, 3, 4, 5... N) en MR_NE_URG de SQL Server,
    preservando el orden cronológico / antigüedad.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        # 1. Consultar todos los registros de MR_NE_URG para este paciente ordenados por antigüedad
        cursor.execute("""
            SELECT MRNum_NE_URG, FECHANOTA1, FECHANOTA2, FECHANOTA3,
                   S_SUBJETIVO1, S_SUBJETIVO2, S_SUBJETIVO3, CreatedOn
            FROM MR_NE_URG 
            WHERE PTNum = ? 
            ORDER BY CreatedOn ASC, MRNum_NE_URG ASC
        """, (pt_num,))
        existing_rows = cursor.fetchall()

        occupied_slots = [] # list of (mrnum_ne_urg, slot_in_row, dt)
        empty_slot_candidate = None # (mrnum_ne_urg, slot_in_row)

        for r in existing_rows:
            r_id = r[0]
            # slot 1
            if r[1] or (r[4] and str(r[4]).strip()):
                occupied_slots.append((r_id, 1, r[1] or r[7]))
            elif not empty_slot_candidate:
                empty_slot_candidate = (r_id, 1)
            # slot 2
            if r[2] or (r[5] and str(r[5]).strip()):
                occupied_slots.append((r_id, 2, r[2] or r[7]))
            elif not empty_slot_candidate:
                empty_slot_candidate = (r_id, 2)
            # slot 3
            if r[3] or (r[6] and str(r[6]).strip()):
                occupied_slots.append((r_id, 3, r[3] or r[7]))
            elif not empty_slot_candidate:
                empty_slot_candidate = (r_id, 3)

        # Ordenar occupied_slots por antigüedad
        occupied_slots.sort(key=lambda x: x[2] or datetime.datetime.min)

        req_num = int(nota_data.get("evolution_num") or 0)
        is_edit = bool(nota_data.get("isEdit"))

        target_mrnum = None
        target_slot_in_row = 1
        final_global_num = req_num

        if is_edit and req_num > 0 and req_num <= len(occupied_slots):
            # Edición de evolución existente
            target_mrnum, target_slot_in_row, _ = occupied_slots[req_num - 1]
            final_global_num = req_num
        elif req_num > 0 and req_num <= len(occupied_slots):
            # Sobrescritura específica de slot existente
            target_mrnum, target_slot_in_row, _ = occupied_slots[req_num - 1]
            final_global_num = req_num
        else:
            # Creación de NUEVA evolución consecutiva
            final_global_num = len(occupied_slots) + 1
            if empty_slot_candidate:
                target_mrnum, target_slot_in_row = empty_slot_candidate
            else:
                target_mrnum = None # Disparará INSERT de nueva fila
                target_slot_in_row = 1

        # Parsear fecha y hora
        fecha_str = nota_data.get("fecha") or datetime.datetime.now().strftime("%Y-%m-%d")
        hora_str = nota_data.get("hora") or datetime.datetime.now().strftime("%H:%M")
        try:
            nota_datetime = datetime.datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
        except Exception:
            try:
                nota_datetime = datetime.datetime.strptime(f"{fecha_str} {hora_str}", "%d/%m/%Y %H:%M")
            except Exception:
                nota_datetime = datetime.datetime.now()

        turno = str(nota_data.get("turno") or "Matutino")
        ta = str(nota_data.get("vitals_ta") or "")
        fc = str(nota_data.get("vitals_fc") or "")
        fr = str(nota_data.get("vitals_fr") or "")
        sat = str(nota_data.get("vitals_sato2") or "")
        peso = str(nota_data.get("vitals_peso") or "")
        talla = str(nota_data.get("vitals_talla") or "")
        temp = str(nota_data.get("vitals_temp") or "")
        
        subjetivo = str(nota_data.get("subjetivo") or "")
        objetivo = str(nota_data.get("objetivo") or "")
        analisis = str(nota_data.get("analisis") or "")
        plan = str(nota_data.get("plan") or "")
        
        medico = str(nota_data.get("medico") or "").strip()
        cedula = str(nota_data.get("cedula") or "").strip()
        mip = str(nota_data.get("mip") or "")

        # Obtener metadatos del paciente y episodio activo para compatibilidad total con Vertical
        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        # Buscar el episodio más reciente en la tabla PC (Patient Care)
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')

        if target_mrnum:
            # ACTUALIZAR EL SLOT CORRESPONDIENTE EN LA FILA OBJETIVO
            if target_slot_in_row == 1:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA1 = ?, TURNO1 = ?, TA1 = ?, FC1 = ?, FR1 = ?, SAT_O2_1 = ?, PESO1 = ?, TALLA = ?, NOTAS = ?,
                    S_SUBJETIVO1 = ?, O_OBJETIVO = ?, A_ANALISIS1 = ?, P_PLAN1 = ?, N_MEDICO = ?, CEDPROF = ?, NMIP = ?,
                    SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                    MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                    ModifiedBy = ?, ModifiedOn = GETDATE()
                WHERE MRNum_NE_URG = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, c_name, c_key, c_id, pt_id, v_user, target_mrnum))
            elif target_slot_in_row == 2:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA2 = ?, TURNO2 = ?, TA2 = ?, FC2 = ?, FR2 = ?, SAT_O2_2 = ?, PESO2 = ?, TALLA2 = ?, NOTAS2 = ?,
                    S_SUBJETIVO2 = ?, O_OBJETIVO2 = ?, A_ANALISIS2 = ?, P_PLAN2 = ?, MEDICO3 = ?, CEDULA2 = ?, N_MIP2 = ?,
                    SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                    MR_ST = 'RG', ModifiedBy = ?, ModifiedOn = GETDATE()
                WHERE MRNum_NE_URG = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, v_user, target_mrnum))
            elif target_slot_in_row == 3:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA3 = ?, TURNO33 = ?, TA3 = ?, FC3 = ?, FR3 = ?, SAT_O2_3 = ?, PESO3 = ?, TALLA3 = ?, NOTAS3 = ?,
                    S_SUBJETIVO3 = ?, O_OBJETIVO3 = ?, A_ANALISIS3 = ?, P_PLAN3 = ?, MEDICO4 = ?, CEDULA3 = ?, N_MIP3 = ?,
                    SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                    MR_ST = 'RG', ModifiedBy = ?, ModifiedOn = GETDATE()
                WHERE MRNum_NE_URG = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, v_user, target_mrnum))
        else:
            # INSERTAR NUEVO REGISTRO EN MR_NE_URG (100% COMPATIBLE CON VERTICAL)
            guid_nota = nota_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_NE_URG (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_NE_URGID,
                EXPEDIENTE, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                FHINGRESO, ALERGIAS, DIAGNOSTICO, DESTINO, CAMA,
                FECHANOTA1, TURNO1, TA1, FC1, FR1, SAT_O2_1, PESO1, TALLA, NOTAS,
                S_SUBJETIVO1, O_OBJETIVO, A_ANALISIS1, P_PLAN1, N_MEDICO, CEDPROF, NMIP
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, ?, GETDATE(), ?, GETDATE(),
                GETDATE(), ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            )
            """
            expediente = f"PT-{pt_num}"
            alergias = str(nota_data.get("alergias") or "NEGADAS")
            diagnostico = str(nota_data.get("diagnostico") or "VALORACIÓN DE URGENCIAS")
            destino = str(nota_data.get("destino") or "OBSERVACIÓN URGENCIAS")
            cama = str(nota_data.get("cama") or "CAMA URGENCIAS 1 (VIRTUAL)")

            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                expediente, v_user, v_user,
                alergias, diagnostico, destino, cama,
                nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp,
                subjetivo, objetivo, analisis, plan, medico, cedula, mip
            ))

        conn.commit()
        
        # Sincronizar también con la tabla maestra de signos vitales PTVS si hay signos capturados
        try:
            if ta or fc or fr or sat or temp or peso or talla:
                vitals_sync = {
                    "ta": ta,
                    "fc": fc,
                    "fr": fr,
                    "sat_o2": sat,
                    "temp": temp,
                    "peso": peso,
                    "talla": talla,
                    "procedure_date": nota_datetime
                }
                # La nota conserva sus signos en MR_NE_URG. La toma maestra PTVS
                # es un acto clínico separado y usa su propio endpoint durable.
                pass
        except Exception as e_ptvs:
            print(f"Nota: No se pudo auto-sincronizar PTVS desde nota de urgencias: {e_ptvs}")

        return {"success": True, "message": f"Evolución {final_global_num} guardada con éxito en SQL Server", "slot": final_global_num, "evolution_num": final_global_num}

    except Exception as e:
        print(f"Error saving/updating nota urgencias: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

def fetch_evoluciones_hospitalizacion(pt_num: str) -> list:
    """
    Obtiene todas las notas de evolución de hospitalización del paciente desde la tabla MR_24_HOJA_EVOL de SQL Server,
    ordenadas por orden de antigüedad (cronológico: FECHA ASC, CreatedOn ASC, MRNum_24_HOJA_EVOL ASC).
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                MRNum_24_HOJA_EVOL,
                PTNum,
                ControllerName,
                ControllerKey,
                MR_ST,
                CreatedBy,
                CreatedOn,
                ModifiedBy,
                ModifiedOn,
                SignedBy,
                SignedOn,
                ESignature,
                FECHA,
                NOTA,
                MEDICO_N,
                PDFFileName
            FROM MR_24_HOJA_EVOL
            WHERE PTNum = ?
            ORDER BY FECHA ASC, CreatedOn ASC, MRNum_24_HOJA_EVOL ASC
        """, (pt_num,))
        
        cols = [c[0] for c in cursor.description]
        rows = cursor.fetchall()

        evoluciones_list = []
        for idx, r in enumerate(rows):
            r_dict = dict(zip(cols, r))
            dt = r_dict.get("FECHA") or r_dict.get("CreatedOn")
            raw_nota = str(r_dict.get("NOTA") or "").strip()
            medico_nom = str(r_dict.get("MEDICO_N") or r_dict.get("SignedBy") or r_dict.get("CreatedBy") or "").strip()

            turno = "Matutino"
            ta, fc, fr, sat, peso, talla, temp = "--", "--", "--", "--", "--", "--", "--"
            subjetivo, objetivo, analisis, plan = "", "", "", ""
            cedula = ""
            mip = ""

            if "[TURNO:" in raw_nota:
                try:
                    meta_match = re.search(r'\[TURNO:\s*([^\|]+)\s*\|\s*TA:\s*([^\|]+)\s*\|\s*FC:\s*([^\|]+)\s*\|\s*FR:\s*([^\|]+)\s*\|\s*SatO2:\s*([^\|]+)\s*\|\s*Temp:\s*([^\|]+)\s*\|\s*Peso:\s*([^\|]+)\s*\|\s*Talla:\s*([^\]]+)\]', raw_nota)
                    if meta_match:
                        turno = meta_match.group(1).strip()
                        ta = meta_match.group(2).strip()
                        fc = meta_match.group(3).strip()
                        fr = meta_match.group(4).strip()
                        sat = meta_match.group(5).strip().replace("%", "")
                        temp = meta_match.group(6).strip().replace("°C", "")
                        peso = meta_match.group(7).strip().replace("kg", "")
                        talla = meta_match.group(8).strip()
                except Exception:
                    pass

            if "[MÉDICO:" in raw_nota or "[MEDICO:" in raw_nota:
                try:
                    med_match = re.search(r'\[M[EÉ]DICO:\s*([^\|]+)\s*\|\s*C[EÉ]DULA:\s*([^\|]+)(?:\s*\|\s*MIP:\s*([^\]]*))?\]', raw_nota)
                    if med_match:
                        if med_match.group(1).strip():
                            medico_nom = med_match.group(1).strip()
                        if med_match.group(2).strip():
                            cedula = med_match.group(2).strip()
                        if med_match.group(3):
                            mip = med_match.group(3).strip()
                except Exception:
                    pass

            s_match = re.search(r'\(S\)\s*Subjetivo:\s*(.*?)(?=\(O\)\s*Objetivo:|\(A\)\s*Análisis:|\(P\)\s*Plan:|\[M[EÉ]DICO:|$)', raw_nota, re.DOTALL | re.IGNORECASE)
            o_match = re.search(r'\(O\)\s*Objetivo:\s*(.*?)(?=\(A\)\s*Análisis:|\(P\)\s*Plan:|\[M[EÉ]DICO:|$)', raw_nota, re.DOTALL | re.IGNORECASE)
            a_match = re.search(r'\(A\)\s*Análisis:\s*(.*?)(?=\(P\)\s*Plan:|\[M[EÉ]DICO:|$)', raw_nota, re.DOTALL | re.IGNORECASE)
            p_match = re.search(r'\(P\)\s*Plan(?:\s*\(laboratorios solicitados y tratamientos a establecer\))?:\s*(.*?)(?=\[M[EÉ]DICO:|$)', raw_nota, re.DOTALL | re.IGNORECASE)

            if s_match: subjetivo = s_match.group(1).strip()
            if o_match: objetivo = o_match.group(1).strip()
            if a_match: analisis = a_match.group(1).strip()
            if p_match: plan = p_match.group(1).strip()

            if not subjetivo and not objetivo and not analisis and not plan:
                clean_body = re.sub(r'\[TURNO:[^\]]+\]', '', raw_nota)
                clean_body = re.sub(r'\[M[EÉ]DICO:[^\]]+\]', '', clean_body).strip()
                subjetivo = clean_body or raw_nota

            num = idx + 1
            evol_obj = {
                "num": num,
                "mrnum_24_hoja_evol": r_dict.get("MRNum_24_HOJA_EVOL"),
                "slot": r_dict.get("MRNum_24_HOJA_EVOL"),
                "title": f"Evolución y Observaciones de Hospitalización {num}",
                "fecha": dt.strftime('%d/%m/%Y') if dt else "",
                "hora": dt.strftime('%H:%M') if dt else "",
                "date_iso": dt.isoformat() if dt else "",
                "turno": turno,
                "vitals_ta": ta,
                "vitals_fc": fc,
                "vitals_fr": fr,
                "vitals_sato2": sat,
                "vitals_peso": peso,
                "vitals_talla": talla,
                "vitals_temp": temp,
                "subjetivo": subjetivo,
                "objetivo": objetivo,
                "analisis": analisis,
                "plan": plan,
                "nota": raw_nota,
                "medico": medico_nom,
                "cedula": cedula,
                "mip": mip,
                "signed_by": r_dict.get("SignedBy"),
                "signed_on": r_dict.get("SignedOn").strftime('%d/%m/%Y %H:%M') if r_dict.get("SignedOn") else None
            }
            evoluciones_list.append(evol_obj)

        return evoluciones_list
    except Exception as e:
        print(f"Error fetching evoluciones hospitalizacion: {e}")
        return []
    finally:
        conn.close()

@explicit_kh_mutation
def save_or_update_nota_hospitalizacion(pt_num: str, nota_data: dict) -> dict:
    """
    Crea o actualiza una nota de evolución de hospitalización en la tabla MR_24_HOJA_EVOL de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()

        fecha_str = nota_data.get("fecha") or datetime.datetime.now().strftime("%Y-%m-%d")
        hora_str = nota_data.get("hora") or datetime.datetime.now().strftime("%H:%M")
        try:
            nota_datetime = datetime.datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
        except Exception:
            try:
                nota_datetime = datetime.datetime.strptime(f"{fecha_str} {hora_str}", "%d/%m/%Y %H:%M")
            except Exception:
                nota_datetime = datetime.datetime.now()

        turno = str(nota_data.get("turno") or "Matutino")
        ta = str(nota_data.get("vitals_ta") or "")
        fc = str(nota_data.get("vitals_fc") or "")
        fr = str(nota_data.get("vitals_fr") or "")
        sat = str(nota_data.get("vitals_sato2") or "")
        peso = str(nota_data.get("vitals_peso") or "")
        talla = str(nota_data.get("vitals_talla") or "")
        temp = str(nota_data.get("vitals_temp") or "")
        
        subjetivo = str(nota_data.get("subjetivo") or "").strip()
        objetivo = str(nota_data.get("objetivo") or "").strip()
        analisis = str(nota_data.get("analisis") or "").strip()
        plan = str(nota_data.get("plan") or "").strip()
        
        medico = str(nota_data.get("medico") or "").strip()
        cedula = str(nota_data.get("cedula") or "").strip()
        mip = str(nota_data.get("mip") or "").strip()

        nota_text_parts = [
            f"[TURNO: {turno} | TA: {ta or '--'} | FC: {fc or '--'} | FR: {fr or '--'} | SatO2: {sat or '--'}% | Temp: {temp or '--'} | Peso: {peso or '--'} | Talla: {talla or '--'}]"
        ]
        if subjetivo: nota_text_parts.append(f"(S) Subjetivo:\n{subjetivo}")
        if objetivo: nota_text_parts.append(f"(O) Objetivo:\n{objetivo}")
        if analisis: nota_text_parts.append(f"(A) Análisis:\n{analisis}")
        if plan: nota_text_parts.append(f"(P) Plan:\n{plan}")
        nota_text_parts.append(f"[MÉDICO: {medico} | CÉDULA: {cedula}{f' | MIP: {mip}' if mip else ''}]")

        full_nota_text = "\n\n".join(nota_text_parts)

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()

        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()

        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')

        mrnum_edit = nota_data.get("mrnum_24_hoja_evol") or nota_data.get("mrnum")
        is_edit = bool(nota_data.get("isEdit") and mrnum_edit)

        if is_edit:
            sql = """
            UPDATE MR_24_HOJA_EVOL
            SET FECHA = ?, NOTA = ?, MEDICO_N = ?,
                SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_24_HOJA_EVOL = ?
            """
            cursor.execute(sql, (nota_datetime, full_nota_text, medico, c_name, c_key, c_id, pt_id, v_user, mrnum_edit))
            final_mrnum = mrnum_edit
        else:
            guid_nota = nota_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_24_HOJA_EVOL (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_24_HOJA_EVOLID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                FECHA, NOTA, MEDICO_N
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user,
                nota_datetime, full_nota_text, medico
            ))
            cursor.execute("SELECT @@IDENTITY")
            row_id = cursor.fetchone()
            final_mrnum = int(row_id[0]) if row_id and row_id[0] else None

        conn.commit()

        try:
            if ta or fc or fr or sat or temp or peso or talla:
                vitals_sync = {
                    "ta": ta, "fc": fc, "fr": fr, "sat_o2": sat, "temp": temp, "peso": peso, "talla": talla,
                    "procedure_date": nota_datetime
                }
                # La nota conserva sus signos en MR_24_HOJA_EVOL. La toma PTVS
                # se registra únicamente mediante su operación durable dedicada.
                pass
        except Exception as e_ptvs:
            print(f"Nota: No se pudo auto-sincronizar PTVS desde nota hospitalización: {e_ptvs}")

        return {
            "success": True,
            "message": "Evolución de hospitalización guardada con éxito en SQL Server",
            "mrnum_24_hoja_evol": final_mrnum,
            "mrnum": final_mrnum,
            "slot": final_mrnum,
            "evolution_num": nota_data.get("evolution_num") or 1
        }
    except Exception as e:
        print(f"Error saving nota hospitalizacion: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

@explicit_kh_mutation
def save_or_update_consentimiento_32_01(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento 32/01 en la tabla MR_CI_ETE_CARD de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        # Buscar si ya existe un registro creado hoy para este paciente y episodio
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_ETE_CARD, CreatedOn 
            FROM MR_CI_ETE_CARD 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_ETE_CARD DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        # Verificar si el último registro fue creado hoy para actualizarlo, o crear uno nuevo
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or "").strip()
        cedula = str(consent_data.get("cedula") or "").strip()
        alergias = str(consent_data.get("alergias") or "NEGADAS")
        intetype = str(consent_data.get("tipo_interrogatorio") or "Directo")
        diagnostico = str(consent_data.get("diagnostico") or "VALORACIÓN CARDIOLÓGICA")
        expediente = f"PT-{pt_num}"

        # Obtener metadatos del paciente y episodio activo
        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')

        if existing_row and is_today:
            # ACTUALIZAR Y REVOCAR FIRMAS PREVIAS EN VERTICAL (NOM-024) EN EL REGISTRO ACTIVO
            sql = """
            UPDATE MR_CI_ETE_CARD
            SET N_MEDICO = ?, CEDULA = ?, ALERGIAS = ?, INTETYPE = ?, DIAGNOSTICO = ?, EXPEDIENTE = ?,
                SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_ETE_CARD = ?
            """
            cursor.execute(sql, (medico, cedula, alergias, intetype, diagnostico, expediente, c_name, c_key, c_id, pt_id, v_user, latest_mrnum))
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_ETE_CARD (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_ETE_CARDID,
                EXPEDIENTE, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO, CEDULA, ALERGIAS, INTETYPE, DIAGNOSTICO
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                expediente, v_user, v_user,
                medico, cedula, alergias, intetype, diagnostico
            ))
            
        conn.commit()
        return {"success": True, "message": "Consentimiento 32/01 registrado correctamente en SQL Server (Vertical)."}
        
    except Exception as e:
        print(f"Error saving Consentimiento 32_01: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


def fetch_patient_vitals_ptvs(pt_num: str) -> dict:
    """
    Consulta los signos vitales más recientes y el historial desde la tabla maestra PTVS en SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1
                PTVSNum, ProcedureDate, Age, Height, Weight, Temperature, PulseRate,
                SystolicPressure, DiastolicPressure, RespiratroryRAte, OxygenSaturation,
                CreatedBy, CreatedOn, PTID, ControllerID, PTVSID
            FROM PTVS
            WHERE PTNum = ?
            ORDER BY ProcedureDate DESC, CreatedOn DESC
        """, (pt_num,))
        
        row = cursor.fetchone()
        if not row:
            return {}

        cols = [c[0] for c in cursor.description]
        d = dict(zip(cols, row))
        
        sys_p = str(d.get("SystolicPressure") or "")
        dia_p = str(d.get("DiastolicPressure") or "")
        ta_str = f"{sys_p}/{dia_p}" if (sys_p or dia_p) else ""

        dt = d.get("ProcedureDate")
        dt_str = dt.strftime("%d/%m/%Y %H:%M") if dt else ""

        return {
            "ptvs_num": d.get("PTVSNum"),
            "systolic": sys_p,
            "diastolic": dia_p,
            "ta": ta_str,
            "pulse": str(d.get("PulseRate") or ""),
            "respiratory": str(d.get("RespiratroryRAte") or ""),
            "oxygen_saturation": str(d.get("OxygenSaturation") or ""),
            "temperature": str(d.get("Temperature") or ""),
            "weight": str(d.get("Weight") or ""),
            "height": str(d.get("Height") or ""),
            "procedure_date": dt_str,
            "procedure_date_iso": dt.isoformat() if dt else "",
            "source": "PTVS"
        }
    except Exception as e:
        print(f"Error fetching PTVS vitals for pt {pt_num}: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


def fetch_patient_vitals_history_ptvs(pt_num: str) -> list:
    """
    Consulta todo el historial cronologico de tomas de signos vitales de la tabla PTVS en SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                PTVSNum, ProcedureDate, Age, Height, Weight, Temperature, PulseRate,
                SystolicPressure, DiastolicPressure, RespiratroryRAte, OxygenSaturation,
                CreatedBy, CreatedOn
            FROM PTVS
            WHERE PTNum = ?
            ORDER BY ProcedureDate DESC, CreatedOn DESC, PTVSNum DESC
        """, (pt_num,))
        
        rows = cursor.fetchall()
        if not rows:
            return []

        cols = [c[0] for c in cursor.description]
        history = []
        for row in rows:
            d = dict(zip(cols, row))
            sys_p = str(d.get("SystolicPressure") or "").strip()
            dia_p = str(d.get("DiastolicPressure") or "").strip()
            ta_str = f"{sys_p}/{dia_p}" if (sys_p and dia_p) else (sys_p or dia_p or "--")

            dt = d.get("ProcedureDate") or d.get("CreatedOn")
            dt_str = dt.strftime("%d/%m/%Y %H:%M") if dt else "--"

            weight_val = d.get("Weight")
            height_val = d.get("Height")
            w_disp = "--"
            h_disp = "--"
            imc_str = "--"
            try:
                if weight_val:
                    w = float(weight_val)
                    w_disp = f"{w:.1f}" if (w % 1 != 0) else f"{int(w)}"
                if height_val:
                    h_raw = float(height_val)
                    if h_raw > 3:
                        h_m = h_raw / 100.0
                    else:
                        h_m = h_raw
                    h_disp = f"{h_m:.2f}"
                if weight_val and height_val:
                    w = float(weight_val)
                    h_raw = float(height_val)
                    h_m = h_raw / 100.0 if h_raw > 3 else h_raw
                    if h_m > 0:
                        imc_str = f"{(w / (h_m * h_m)):.1f}"
            except Exception:
                pass

            history.append({
                "id": d.get("PTVSNum"),
                "fecha_hora": dt_str,
                "fecha_hora_iso": dt.isoformat() if dt else "",
                "ta": ta_str,
                "sistolica": sys_p,
                "diastolica": dia_p,
                "fc": str(d.get("PulseRate") or "--"),
                "fr": str(d.get("RespiratroryRAte") or "--"),
                "sat_o2": str(d.get("OxygenSaturation") or "--"),
                "temperatura": str(d.get("Temperature") or "--"),
                "peso": w_disp,
                "talla": h_disp,
                "imc": imc_str,
                "capturado_por": str(d.get("CreatedBy") or "Personal de Salud").strip()
            })
        return history
    except Exception as e:
        print(f"Error fetching PTVS vitals history for pt {pt_num}: {e}")
        return []
    finally:
        conn.close()


@explicit_kh_mutation
def save_patient_vitals_ptvs(pt_num: str, vitals_data: dict, connection_existing=None) -> dict:
    """
    Inserta o actualiza un registro formal en la tabla [KH_HE].[dbo].[PTVS].
    Convierte automáticamente los valores y vincula con el episodio activo (PC / PCNum).
    """
    conn = connection_existing or get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    should_close = (connection_existing is None)
    try:
        cursor = conn.cursor()

        # Parsear Presión Arterial si viene combinada (ej: "120/80")
        sys_p = vitals_data.get("systolic") or vitals_data.get("vitals_ta_sys")
        dia_p = vitals_data.get("diastolic") or vitals_data.get("vitals_ta_dia")
        ta_raw = str(vitals_data.get("ta") or vitals_data.get("vitals_ta") or "").strip()
        if (not sys_p or not dia_p) and "/" in ta_raw:
            parts = ta_raw.split("/")
            sys_p = parts[0].strip()
            dia_p = parts[1].strip()

        # Helper para convertir a float/int seguro
        def safe_num(val):
            if val is None or val == "" or val == "--":
                return None
            try:
                # Quitar unidades si vienen incluidas
                cleaned = str(val).replace("mmHg", "").replace("lpm", "").replace("rpm", "").replace("%", "").replace("°C", "").replace("kg", "").replace("m", "").strip()
                if "." in cleaned:
                    return float(cleaned)
                return int(cleaned)
            except Exception:
                return None

        systolic = safe_num(sys_p)
        diastolic = safe_num(dia_p)
        pulse = safe_num(vitals_data.get("pulse") or vitals_data.get("fc") or vitals_data.get("vitals_fc"))
        respiratory = safe_num(vitals_data.get("respiratory") or vitals_data.get("fr") or vitals_data.get("vitals_fr"))
        oxygen_sat = safe_num(vitals_data.get("oxygen_saturation") or vitals_data.get("sat_o2") or vitals_data.get("vitals_sato2"))
        temp = safe_num(vitals_data.get("temperature") or vitals_data.get("temp") or vitals_data.get("vitals_temp"))
        weight = safe_num(vitals_data.get("weight") or vitals_data.get("peso") or vitals_data.get("vitals_peso"))
        height_raw = safe_num(vitals_data.get("height") or vitals_data.get("talla") or vitals_data.get("vitals_talla"))
        height = None
        if height_raw is not None:
            if height_raw <= 3.0:
                height = int(round(height_raw * 100))
            else:
                height = int(round(height_raw))

        # Parsear fecha de toma
        p_date = vitals_data.get("procedure_date")
        if isinstance(p_date, str) and p_date:
            try:
                procedure_date = datetime.datetime.strptime(p_date, "%Y-%m-%d %H:%M")
            except Exception:
                try:
                    procedure_date = datetime.datetime.strptime(p_date, "%d/%m/%Y %H:%M")
                except Exception:
                    procedure_date = datetime.datetime.now()
        elif isinstance(p_date, datetime.datetime):
            procedure_date = p_date
        else:
            procedure_date = datetime.datetime.now()

        # Obtener datos del paciente y episodio activo
        cursor.execute("SELECT TOP 1 ControllerName, ControllerKey, ControllerID, PTID, Age FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()

        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        age_val = safe_num(meta_row[4]) if meta_row and len(meta_row) > 4 else None

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        guid_ptvs = vitals_data.get("_operation_guid") or str(uuid.uuid4()).upper()

        sql = """
        INSERT INTO PTVS (
            PTNum, PCType, PCNum, ControllerName, ControllerKey, PTVS_ST,
            ProcedureDate, Age, Height, Weight, Temperature, PulseRate,
            SystolicPressure, DiastolicPressure, RespiratroryRAte, OxygenSaturation,
            CreatedBy, CreatedOn, ModifiedBy, ModifiedOn, PTID, ControllerID, PTVSID
        ) VALUES (
            ?, 'PC', ?, 'PC', ?, 'RG',
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, GETDATE(), ?, GETDATE(), ?, ?, ?
        )
        """
        cursor.execute(sql, (
            pt_num, c_key, c_key,
            procedure_date, age_val, height, weight, temp, pulse,
            systolic, diastolic, respiratory, oxygen_sat,
            v_user, v_user, pt_id, c_id, guid_ptvs
        ))

        # Actualizar también MR_NE_URG para que el formato 87/01 y Vertical tengan los signos sincronizados de inmediato
        try:
            ta_formatted = f"{systolic}/{diastolic}" if (systolic and diastolic) else ""
            cursor.execute("""
                UPDATE MR_NE_URG
                SET TA1 = COALESCE(?, TA1),
                    FC1 = COALESCE(?, FC1),
                    FR1 = COALESCE(?, FR1),
                    SAT_O2_1 = COALESCE(?, SAT_O2_1),
                    PESO1 = COALESCE(?, PESO1),
                    TALLA = COALESCE(?, TALLA),
                    NOTAS = COALESCE(?, NOTAS),
                    ModifiedBy = ?,
                    ModifiedOn = GETDATE()
                WHERE PTNum = ?
            """, (
                ta_formatted or None,
                str(pulse) if pulse else None,
                str(respiratory) if respiratory else None,
                str(oxygen_sat) if oxygen_sat else None,
                str(weight) if weight else None,
                str(height) if height else None,
                str(temp) if temp else None,
                v_user,
                pt_num
            ))
        except Exception as e_ne:
            raise KHRetryableMutationError(
                f"No se pudo sincronizar MR_NE_URG al guardar PTVS: {e_ne}"
            ) from e_ne

        if should_close:
            conn.commit()

        return {
            "success": True,
            "message": "Signos vitales registrados con éxito",
            "ptvs_id": guid_ptvs,
            "ta": f"{systolic}/{diastolic}" if (systolic and diastolic) else ""
        }

    except Exception as e:
        print(f"Error saving PTVS vitals: {e}")
        return {"error": str(e)}
    finally:
        if should_close and conn:
            conn.close()


def fetch_patient_medications_ptdg(pt_num: str) -> list:
    """
    Consulta todos los medicamentos y prescripciones de la tabla maestra PTDG en SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                PTDGNum, QTNum, PCType, PCNum, PCFRNum, PTNum,
                ControllerName, ControllerKey, PTDG_ST, PrescriptionDate,
                MedicationNumber, Amount, UOM, Route, Frequency,
                PRN, Why, Dispense, Refills, Notes, Reference,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                PTDGID, PTID, ControllerID
            FROM PTDG
            WHERE PTNum = ?
            ORDER BY PrescriptionDate DESC, CreatedOn DESC
        """, (pt_num,))
        
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]
        meds = []
        for r in rows:
            d = dict(zip(cols, r))
            med_name = str(d.get("Reference") or d.get("MedicationNumber") or "Fármaco").strip()
            amount_val = str(d.get("Amount") or "").strip()
            uom_val = str(d.get("UOM") or "").strip()
            dose_str = f"{amount_val} {uom_val}".strip() if (amount_val or uom_val) else ""
            
            p_date = d.get("PrescriptionDate")
            date_str = p_date.strftime("%d/%m/%Y %H:%M") if p_date else ""

            is_active = (str(d.get("PTDG_ST") or "").strip().upper() == "RG")
            status_text = "Activo" if is_active else "Suspendido"

            meds.append({
                "ptdg_num": d.get("PTDGNum"),
                "name": med_name,
                "dose": dose_str,
                "amount": amount_val,
                "uom": uom_val,
                "route": str(d.get("Route") or "Oral").strip(),
                "freq": str(d.get("Frequency") or "Cada 8 horas").strip(),
                "prn": bool(d.get("PRN")),
                "why": str(d.get("Why") or "").strip(),
                "dispense": str(d.get("Dispense") or "").strip(),
                "refills": d.get("Refills") or 0,
                "instruction": str(d.get("Notes") or "").strip(),
                "date": date_str,
                "date_iso": p_date.isoformat() if p_date else "",
                "status": status_text,
                "ptdg_st": str(d.get("PTDG_ST") or "").strip(),
                "created_by": str(d.get("CreatedBy") or "Bitacora_SIS").strip(),
                "ptdg_id": str(d.get("PTDGID") or "")
            })
        return meds
    except Exception as e:
        print(f"Error fetching PTDG medications for pt {pt_num}: {e}")
        return []
    finally:
        conn.close()


@explicit_kh_mutation
def save_patient_medication_ptdg(pt_num: str, med_data: dict, connection_existing=None) -> dict:
    """
    Inserta una nueva prescripción médica en la tabla [KH_HE].[dbo].[PTDG] de SQL Server.
    """
    conn = connection_existing or get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    should_close = (connection_existing is None)
    try:
        import re
        cursor = conn.cursor()

        med_name = str(med_data.get("name") or med_data.get("reference") or "").strip()
        if not med_name:
            return {"error": "El nombre del medicamento es obligatorio."}

        def parse_int_digits(val, default=1):
            if val is None or val == '':
                return default
            try:
                if isinstance(val, int):
                    return val
                nums = re.findall(r'\d+', str(val))
                if nums:
                    return int(nums[0])
                return default
            except Exception:
                return default

        amount_val = parse_int_digits(med_data.get("amount") or med_data.get("dose"), 1)
        dispense_val = parse_int_digits(med_data.get("dispense"), 1)
        refills_val = parse_int_digits(med_data.get("refills"), 0)
        med_num_val = parse_int_digits(med_data.get("medication_number"), 1)

        uom_val = str(med_data.get("uom") or "mg").strip()
        route_val = str(med_data.get("route") or "Oral").strip()
        freq_val = str(med_data.get("frequency") or med_data.get("freq") or "Cada 8 horas").strip()
        prn_val = 1 if med_data.get("prn") else 0
        why_val = str(med_data.get("why") or "").strip()
        notes_val = str(med_data.get("instruction") or med_data.get("notes") or "").strip()

        # Parsear fecha de prescripción
        p_date = med_data.get("prescription_date")
        if isinstance(p_date, str) and p_date:
            try:
                prescription_date = datetime.datetime.strptime(p_date, "%Y-%m-%d %H:%M")
            except Exception:
                try:
                    prescription_date = datetime.datetime.strptime(p_date, "%d/%m/%Y %H:%M")
                except Exception:
                    prescription_date = datetime.datetime.now()
        elif isinstance(p_date, datetime.datetime):
            prescription_date = p_date
        else:
            prescription_date = datetime.datetime.now()

        # Obtener datos del paciente y episodio activo
        cursor.execute("SELECT TOP 1 ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()

        c_name = 'PC'
        c_key_raw = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_key = parse_int_digits(c_key_raw, int(pt_num))
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        operation_id = med_data.get("_operation_id")
        guid_ptdg = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"hes:ptdg:{operation_id}")
            if operation_id else uuid.uuid4()
        ).upper()

        cursor.execute("SELECT TOP 1 PTDGNum FROM PTDG WHERE PTDGID = ?", (guid_ptdg,))
        existing = cursor.fetchone()
        if existing:
            return {
                "success": True,
                "message": "Medicamento ya sincronizado en PTDG",
                "ptdg_id": guid_ptdg,
                "ptdg_num": existing[0],
                "idempotent": True,
            }

        sql = """
        INSERT INTO PTDG (
            PTNum, PCType, PCNum, ControllerName, ControllerKey, PTDG_ST,
            PrescriptionDate, MedicationNumber, Amount, UOM, Route, Frequency,
            PRN, Why, Dispense, Refills, Notes, Reference,
            CreatedBy, CreatedOn, ModifiedBy, ModifiedOn, PTID, ControllerID, PTDGID
        ) VALUES (
            ?, 'PC', ?, 'PC', ?, 'RG',
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, GETDATE(), ?, GETDATE(), ?, ?, ?
        )
        """
        cursor.execute(sql, (
            int(pt_num), c_key, c_key,
            prescription_date, med_num_val, amount_val, uom_val, route_val, freq_val,
            prn_val, why_val, dispense_val, refills_val, notes_val, med_name,
            v_user, v_user, pt_id, c_id, guid_ptdg
        ))

        if should_close:
            conn.commit()

        return {
            "success": True,
            "message": "Medicamento prescrito con éxito en PTDG",
            "ptdg_id": guid_ptdg,
            "medication": med_name
        }

    except Exception as e:
        print(f"Error saving PTDG medication: {e}")
        return {"error": str(e)}
    finally:
        if should_close and conn:
            conn.close()


@explicit_kh_mutation
def discontinue_patient_medication_ptdg(pt_num: str, ptdg_num: int, reason: str = "") -> dict:
    """
    Suspende / Discontinua un fármaco en la tabla PTDG (PTDG_ST = 'DC').
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        
        cursor.execute("""
            UPDATE PTDG
            SET PTDG_ST = 'DC',
                Notes = CASE WHEN Notes IS NULL OR Notes = '' THEN ? ELSE Notes + ' ' + ? END,
                ModifiedBy = ?,
                ModifiedOn = GETDATE()
            WHERE PTNum = ? AND PTDGNum = ? AND PTDG_ST <> 'DC'
        """, (f"[SUSPENDIDO: {reason}]", f"[SUSPENDIDO: {reason}]", v_user, pt_num, ptdg_num))

        conn.commit()
        return {"success": True, "message": "Medicamento suspendido con éxito en PTDG."}
    except Exception as e:
        print(f"Error discontinuing PTDG medication: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


def fetch_patient_diet_mr_sol_diet(pt_num: str) -> dict:
    """
    Consulta la solicitud de dieta más reciente desde la tabla MR_SOL_DIET de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1
                MRNum_SOL_DIET, PTNum, PTID, ControllerName, ControllerKey,
                MR_ST, MR_SOL_DIETID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                HORARIO, TIPO, DETALLE, INTOLERANCIA
            FROM MR_SOL_DIET
            WHERE PTNum = ?
            ORDER BY CreatedOn DESC, MRNum_SOL_DIET DESC
        """, (pt_num,))
        row = cursor.fetchone()
        if not row:
            return {}
        cols = [c[0] for c in cursor.description]
        d = dict(zip(cols, row))
        
        tipo_raw = str(d.get("TIPO") or "").strip()
        tipo_map = {
            "A": "Ayuno Estricto",
            "B": "Dieta Blanda",
            "N": "Dieta Normal / Hospitalaria",
            "L": "Dieta Líquida",
            "LC": "Dieta Líquida Clara",
            "H": "Dieta Hiposódica",
            "D": "Dieta Diabética",
            "AST": "Dieta Astringente",
            "SNG": "Dieta Licuada por Sonda"
        }
        tipo_nombre = tipo_map.get(tipo_raw.upper(), tipo_raw) if tipo_raw in tipo_map else (tipo_raw or "Dieta Prescrita")

        return {
            "mrnum_sol_diet": d.get("MRNum_SOL_DIET"),
            "tipo": tipo_nombre,
            "tipo_code": tipo_raw,
            "horario": str(d.get("HORARIO") or "Continuo").strip(),
            "detalle": str(d.get("DETALLE") or "").strip(),
            "intolerancia": str(d.get("INTOLERANCIA") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "created_by": str(d.get("CreatedBy") or "Bitacora_SIS").strip(),
            "mr_sol_diet_id": str(d.get("MR_SOL_DIETID") or "")
        }
    except Exception as e:
        print(f"Error fetching MR_SOL_DIET for pt {pt_num}: {e}")
        return {}
    finally:
        conn.close()


@explicit_kh_mutation
def save_patient_diet_mr_sol_diet(pt_num: str, diet_data: dict, connection_existing=None) -> dict:
    """
    Inserta una solicitud de dieta en la tabla [KH_HE].[dbo].[MR_SOL_DIET] de SQL Server.
    """
    conn = connection_existing or get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    should_close = (connection_existing is None)
    try:
        import re
        cursor = conn.cursor()

        tipo_val = str(diet_data.get("tipo") or diet_data.get("tipo_dieta") or "Ayuno Estricto").strip()
        horario_val = str(diet_data.get("horario") or "Continuo").strip()
        detalle_val = str(diet_data.get("detalle") or diet_data.get("indicaciones") or diet_data.get("indicaciones_nutricionales") or "").strip()
        intolerancia_val = str(diet_data.get("intolerancia") or diet_data.get("alergias_alimentarias") or "").strip()

        # Obtener datos del paciente y episodio activo
        cursor.execute("SELECT TOP 1 ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()

        c_name = 'PC'
        c_key_raw = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        digits = re.findall(r'\d+', str(c_key_raw))
        c_key = int(digits[0]) if digits else int(pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        operation_id = diet_data.get("_operation_id")
        guid_diet = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"hes:mr-sol-diet:{operation_id}")
            if operation_id else uuid.uuid4()
        ).upper()

        cursor.execute(
            "SELECT TOP 1 MRNum_SOL_DIET FROM MR_SOL_DIET WHERE MR_SOL_DIETID = ?",
            (guid_diet,),
        )
        existing = cursor.fetchone()
        if existing:
            return {
                "success": True,
                "message": "Dieta ya sincronizada en MR_SOL_DIET",
                "diet_id": guid_diet,
                "mrnum_sol_diet": existing[0],
                "idempotent": True,
            }

        sql = """
        INSERT INTO MR_SOL_DIET (
            PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST,
            MR_SOL_DIETID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
            HORARIO, TIPO, DETALLE, INTOLERANCIA
        ) VALUES (
            ?, ?, 'PC', ?, ?, 'RG',
            ?, ?, GETDATE(), ?, GETDATE(),
            ?, ?, ?, ?
        )
        """
        cursor.execute(sql, (
            int(pt_num), pt_id, c_key, c_id,
            guid_diet, v_user, v_user,
            horario_val, tipo_val, detalle_val, intolerancia_val
        ))

        if should_close:
            conn.commit()

        return {
            "success": True,
            "message": "Dieta registrada con éxito en MR_SOL_DIET",
            "diet_id": guid_diet
        }
    except Exception as e:
        print(f"Error saving MR_SOL_DIET: {e}")
        return {"error": str(e)}
    finally:
        if should_close and conn:
            conn.close()


def search_patients_kh(query_text: str = "", limit: int = 30) -> list:
    """
    Buscador universal de pacientes (activos, hospitalizados e históricos/de alta) en SQL Server (PT, PC, V_MRPT).
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        q = f"%{query_text.strip()}%" if (query_text and query_text.strip()) else "%"
        
        sql = f"""
            SELECT TOP {limit}
                p.PTNum,
                p.FullName,
                p.BirthDate,
                DATEDIFF(YEAR, p.BirthDate, GETDATE()) - 
                    CASE WHEN (MONTH(p.BirthDate) > MONTH(GETDATE())) OR 
                              (MONTH(p.BirthDate) = MONTH(GETDATE()) AND DAY(p.BirthDate) > DAY(GETDATE())) 
                         THEN 1 ELSE 0 END as Age,
                p.Gender,
                p.Identification as CURP,
                cama.Habitacion as CamaActual,
                pc.PCNum as UltimoEpisodio,
                pc.EntryDate,
                pc.ExitDate,
                pc.ClosedOn,
                pc.MedicalDischarge,
                pc.MedicalDischargeDate,
                pc.PC_ST as EstadoEpisodio,
                pc.UDF_Diagnostico_presuntivo as DiagnosticoPresuntivo,
                pc.MedicalDischargeDX as DiagnosticoEgreso
            FROM PT p
            OUTER APPLY (
                SELECT TOP 1 *
                FROM PC 
                WHERE PC.PTNum = p.PTNum
                ORDER BY PC.EntryDate DESC, PC.PCNum DESC
            ) pc
            OUTER APPLY (
                SELECT TOP 1 Habitacion
                FROM UDR_AD_CENSO
                WHERE UDR_AD_CENSO.PCNum = pc.PCNum
            ) cama
            WHERE p.FullName LIKE ? OR CAST(p.PTNum AS VARCHAR) LIKE ? OR p.Identification LIKE ?
            ORDER BY 
                CASE 
                    WHEN CAST(p.PTNum AS VARCHAR) = ? THEN 0
                    WHEN p.FullName LIKE ? THEN 1
                    WHEN p.FullName LIKE ? THEN 2
                    ELSE 3 
                END,
                COALESCE(pc.EntryDate, p.CreatedOn) DESC, 
                p.PTNum DESC
        """
        clean_q = query_text.strip()
        cursor.execute(sql, (q, q, q, clean_q, f"{clean_q}%", f"%{clean_q}%"))
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]
        
        results = []
        for r in rows:
            d = dict(zip(cols, r))
            entry_d = d.get("EntryDate")
            exit_d = d.get("MedicalDischargeDate") or d.get("ExitDate") or d.get("ClosedOn")
            
            has_discharge = bool(
                d.get("MedicalDischarge") or
                d.get("MedicalDischargeDate") or
                d.get("ExitDate") or
                d.get("ClosedOn") or
                (d.get("EstadoEpisodio") in ("CL", "PD", "CA"))
            )
            is_active = bool(d.get("CamaActual")) and (d.get("EstadoEpisodio") == "OP") and not has_discharge
            status_label = "Hospitalizado / Activo" if is_active else "Alta / Histórico"
            
            diag = d.get("DiagnosticoEgreso") or d.get("DiagnosticoPresuntivo") or "Sin diagnóstico especificado"

            results.append({
                "pt_num": str(d.get("PTNum")),
                "name": str(d.get("FullName") or "Paciente").strip(),
                "age": d.get("Age") if d.get("Age") is not None else "--",
                "gender": "M" if d.get("Gender") in ["M", "1"] else "F",
                "curp": str(d.get("CURP") or "").strip(),
                "cama": str(d.get("CamaActual") or "").strip() if (is_active and d.get("CamaActual")) else None,
                "pc_num": d.get("UltimoEpisodio"),
                "entry_date": entry_d.strftime("%d/%m/%Y %H:%M") if entry_d else "",
                "exit_date": exit_d.strftime("%d/%m/%Y %H:%M") if exit_d else "",
                "status": status_label,
                "is_active": is_active,
                "diagnostico": str(diag).strip()
            })
        return results
    except Exception as e:
        print(f"Error searching patients in SQL Server: {e}")
        return []
    finally:
        conn.close()


def fetch_allergy_catalog(search_query: str = "", limit: int = 50) -> list:
    """
    Consulta el catálogo maestro de alergias estandarizadas de Vertical en SQL Server (DIS_AL).
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()
    try:
        cursor = conn.cursor()
        q = f"%{search_query.strip()}%" if (search_query and search_query.strip()) else "%"
        sql = f"""
            SELECT TOP {limit}
                AllergyId as allergy_id,
                AllergyName as name,
                Reference as reference
            FROM DIS_AL
            WHERE AllergyName LIKE ? OR AllergyId LIKE ?
            ORDER BY 
                CASE 
                    WHEN AllergyId = '00' THEN 1
                    WHEN AllergyName LIKE ? THEN 0
                    ELSE 2
                END,
                AllergyName ASC
        """
        clean_q = search_query.strip() if search_query else ""
        cursor.execute(sql, (q, q, f"{clean_q}%"))
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"Error fetching allergy catalog from DIS_AL: {e}")
        return []
    finally:
        conn.close()


def fetch_patient_allergies_ptal(pt_num: str) -> list:
    """
    Consulta las alergias activas del paciente en SQL Server (PTAL) unidas con su nombre en DIS_AL.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.PTALNum,
                p.PTNum,
                p.PTAL_ST,
                p.AllergyNum,
                COALESCE(d.AllergyName, 'Alergia no catalogada (' + CAST(p.AllergyNum AS VARCHAR) + ')') as AllergyName,
                p.AllergicSince,
                p.Notes,
                p.Reference,
                p.CreatedBy,
                p.CreatedOn,
                p.ModifiedBy,
                p.ModifiedOn,
                p.PTALID
            FROM PTAL p
            LEFT JOIN DIS_AL d ON p.AllergyNum = d.AllergyId
            WHERE p.PTNum = ? AND p.PTAL_ST = 'RG'
            ORDER BY p.CreatedOn DESC, p.PTALNum DESC
        """, (int(pt_num),))
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]
        results = []
        for r in rows:
            d = dict(zip(cols, r))
            since_d = d.get("AllergicSince")
            created_d = d.get("CreatedOn")
            results.append({
                "ptal_num": d.get("PTALNum"),
                "pt_num": d.get("PTNum"),
                "allergy_num": str(d.get("AllergyNum") or "").strip(),
                "allergy_name": str(d.get("AllergyName") or "").strip(),
                "allergic_since": since_d.strftime("%d/%m/%Y") if since_d else "",
                "notes": str(d.get("Notes") or "").strip(),
                "reference": str(d.get("Reference") or "").strip(),
                "created_by": str(d.get("CreatedBy") or "").strip(),
                "created_on": created_d.strftime("%d/%m/%Y %H:%M") if created_d else "",
                "ptal_id": str(d.get("PTALID") or "").strip()
            })
        return results
    except Exception as e:
        print(f"Error fetching patient allergies from PTAL: {e}")
        return []
    finally:
        conn.close()


@explicit_kh_mutation
def save_patient_allergy_ptal(pt_num: str, allergy_num: str, allergic_since: str = None, notes: str = "", user: str = None, _operation_guid: str = None) -> dict:
    """
    Registra una nueva alergia en SQL Server (PTAL) vinculada al catálogo DIS_AL.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT PTID FROM PT WHERE PTNum = ?", (int(pt_num),))
        r_pt = cursor.fetchone()
        pt_id = r_pt[0] if r_pt and r_pt[0] else str(uuid.uuid4()).upper()

        guid_ptal = _operation_guid or str(uuid.uuid4()).upper()
        v_user = user or os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        ref = f"vidal://allergy/{allergy_num}"

        since_dt = None
        if allergic_since and allergic_since.strip():
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    since_dt = datetime.datetime.strptime(allergic_since.strip(), fmt)
                    break
                except Exception:
                    pass

        sql = """
            INSERT INTO PTAL (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                PTAL_ST, AllergyNum, AllergicSince, Notes, Reference,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn, PTALID
            ) VALUES (
                ?, ?, NULL, NULL, NULL,
                'RG', ?, ?, ?, ?,
                ?, GETDATE(), ?, GETDATE(), ?
            )
        """
        cursor.execute(sql, (
            int(pt_num), pt_id, str(allergy_num), since_dt, str(notes or "").strip(), ref,
            v_user, v_user, guid_ptal
        ))
        
        # Sincronización automática con MR_NE_URG (ALERGIAS) y MR_SOL_DIET (INTOLERANCIA)
        _sync_allergies_to_notes(cursor, int(pt_num), v_user)

        conn.commit()
        return {
            "success": True,
            "message": "Alergia registrada y sincronizada en Vertical (PTAL, MR_NE_URG, MR_SOL_DIET).",
            "ptal_id": guid_ptal
        }
    except Exception as e:
        print(f"Error saving PTAL allergy: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@explicit_kh_mutation
def inactivate_patient_allergy_ptal(pt_num: str, ptal_num: int, user: str = None) -> dict:
    """
    Inactiva (elimina lógicamente) una alergia en SQL Server (PTAL) y sincroniza MR_NE_URG y MR_SOL_DIET.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()
    try:
        cursor = conn.cursor()
        v_user = user or os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        cursor.execute("""
            UPDATE PTAL
            SET PTAL_ST = 'CL', ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE PTNum = ? AND PTALNum = ?
        """, (v_user, int(pt_num), int(ptal_num)))

        # Sincronización automática con MR_NE_URG y MR_SOL_DIET
        _sync_allergies_to_notes(cursor, int(pt_num), v_user)

        conn.commit()
        return {
            "success": True,
            "message": "Alergia inactivada y sincronizada en Vertical (PTAL, MR_NE_URG, MR_SOL_DIET)."
        }
    except Exception as e:
        print(f"Error inactivating PTAL allergy: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


def _sync_allergies_to_notes(cursor, pt_num: int, user: str = 'Bitacora_SIS'):
    """
    Helper interno: consolida las alergias activas de PTAL y las escribe en MR_NE_URG (ALERGIAS) y MR_SOL_DIET (INTOLERANCIA).
    """
    try:
        cursor.execute("""
            SELECT COALESCE(d.AllergyName, 'Alergia (' + CAST(p.AllergyNum AS VARCHAR) + ')')
            FROM PTAL p
            LEFT JOIN DIS_AL d ON p.AllergyNum = d.AllergyId
            WHERE p.PTNum = ? AND p.PTAL_ST = 'RG'
            ORDER BY p.CreatedOn ASC, p.PTALNum ASC
        """, (pt_num,))
        names = [r[0] for r in cursor.fetchall() if r[0]]
        al_text = ", ".join(names) if names else "NEGADAS"

        cursor.execute("""
            UPDATE MR_NE_URG
            SET ALERGIAS = ?, ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE PTNum = ?
        """, (al_text, user, pt_num))

        cursor.execute("""
            UPDATE MR_SOL_DIET
            SET INTOLERANCIA = ?, ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE PTNum = ?
        """, (al_text, user, pt_num))
    except Exception as e_sync:
        print(f"Error syncing allergies to notes: {e_sync}")


@explicit_kh_mutation
def update_patient_allergies_text(pt_num: str, allergies_text: str, user: str = None) -> dict:
    """
    Actualiza directamente el texto consolidado de ALERGIAS en MR_NE_URG y MR_SOL_DIET.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()
    try:
        cursor = conn.cursor()
        v_user = user or os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        al_val = str(allergies_text or "NEGADAS").strip()

        cursor.execute("""
            UPDATE MR_NE_URG
            SET ALERGIAS = ?, ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE PTNum = ?
        """, (al_val, v_user, int(pt_num)))

        cursor.execute("""
            UPDATE MR_SOL_DIET
            SET INTOLERANCIA = ?, ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE PTNum = ?
        """, (al_val, v_user, int(pt_num)))

        conn.commit()
        return {
            "success": True,
            "message": "Texto de alergias actualizado en todas las notas de Vertical.",
            "allergies": al_val
        }
    except Exception as e:
        print(f"Error updating allergies text in SQL Server: {e}")
        return {"error": str(e)}
    finally:
        conn.close()







import uuid, datetime, os
@explicit_kh_mutation
def save_or_update_consentimiento_eed(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento de Ecocardiograma de Estrés con Dobutamina en MR_CI_EED.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_EED, CreatedOn 
            FROM MR_CI_EED 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_EED DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico") or consent_data.get("medico_tratante") or "")
        cedula = str(consent_data.get("cedula") or consent_data.get("cedula_profesional") or "")
        interrogatorio = str(consent_data.get("tipo_interrogatorio") or consent_data.get("interrogatorio") or "Directo")
        responsable = str(consent_data.get("responsable") or "")
        comentarios = str(consent_data.get("comentarios") or "")
        ta = str(consent_data.get("ta") or "")
        fc_meta = str(consent_data.get("fc_meta") or "")
        fr = str(consent_data.get("fr") or "")
        talla = str(consent_data.get("talla") or "")
        peso = str(consent_data.get("peso") or "")
        expediente = f"PT-{pt_num}"
        
        # Recuperar alergias y tipo de sangre si no vienen en consent_data
        alergias = str(consent_data.get("alergias") or "").strip()
        tsangre = str(consent_data.get("tsangre") or consent_data.get("tipo_sangre") or "").strip()
        
        if not alergias or not tsangre:
            try:
                cursor.execute("SELECT BloodType FROM V_MRPT WHERE PTNum = ?", (pt_num,))
                b_row = cursor.fetchone()
                if b_row and b_row[0] and not tsangre:
                    tsangre = str(b_row[0])
                
                cursor.execute("""
                    SELECT COALESCE(d.AllergyName, 'Alergia (' + CAST(p.AllergyNum AS VARCHAR) + ')')
                    FROM PTAL p
                    LEFT JOIN DIS_AL d ON p.AllergyNum = d.AllergyId
                    WHERE p.PTNum = ? AND p.PTAL_ST = 'RG'
                """, (int(pt_num),))
                al_rows = cursor.fetchall()
                if al_rows and not alergias:
                    alergias = ", ".join([r[0] for r in al_rows])
            except Exception as e_demo:
                print(f"Nota: No se pudo auto-completar demograficos para EED: {e_demo}")

        if not alergias:
            alergias = "NEGADAS"
        if not tsangre:
            tsangre = "O+"

        ta_basal, fc_basal, so2_basal, s_basal = str(consent_data.get("ta_basal") or ""), str(consent_data.get("fc_basal") or ""), str(consent_data.get("so2_basal") or ""), str(consent_data.get("s_basal") or "")
        ta_5mcg, fc_5mcg, so2_5mcg, s_5mcg = str(consent_data.get("ta_5mcg") or ""), str(consent_data.get("fc_5mcg") or ""), str(consent_data.get("so2_5mcg") or ""), str(consent_data.get("s_5mcg") or "")
        ta_10mcg, fc_10mcg, so2_10mcg, s_10mcg = str(consent_data.get("ta_10mcg") or ""), str(consent_data.get("fc_10mcg") or ""), str(consent_data.get("so2_10mcg") or ""), str(consent_data.get("s_10mcg") or "")
        ta_20mcg, fc_20mcg, so2_20mcg, s_20mcg = str(consent_data.get("ta_20mcg") or ""), str(consent_data.get("fc_20mcg") or ""), str(consent_data.get("so2_20mcg") or ""), str(consent_data.get("s_20mcg") or "")
        ta_30mcg, fc_30mcg, so2_30mcg, s_30mcg = str(consent_data.get("ta_30mcg") or ""), str(consent_data.get("fc_30mcg") or ""), str(consent_data.get("so2_30mcg") or ""), str(consent_data.get("s_30mcg") or "")
        ta_40mcg, fc_40mcg, so2_40mcg, s_40mcg = str(consent_data.get("ta_40mcg") or ""), str(consent_data.get("fc_40mcg") or ""), str(consent_data.get("so2_40mcg") or ""), str(consent_data.get("s_40mcg") or "")
        ta_antropina, fc_antropina, so2_antropina, s_antropina = str(consent_data.get("ta_antropina") or consent_data.get("ta_atropina") or ""), str(consent_data.get("fc_antropina") or consent_data.get("fc_atropina") or ""), str(consent_data.get("so2_antropina") or consent_data.get("so2_atropina") or ""), str(consent_data.get("s_antropina") or consent_data.get("s_atropina") or "")
        ta_2min, fc_2min, so2_2min, sintomas_2min = str(consent_data.get("ta_2min") or ""), str(consent_data.get("fc_2min") or ""), str(consent_data.get("so2_2min") or ""), str(consent_data.get("sintomas_2min") or "")
        ta_4min, fc_4min, so2_4min, sintomas_4min = str(consent_data.get("ta_4min") or ""), str(consent_data.get("fc_4min") or ""), str(consent_data.get("so2_4min") or ""), str(consent_data.get("sintomas_4min") or "")

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')

        if existing_row:
            sql = """
            UPDATE MR_CI_EED
            SET NOMBRE_MEDICO = ?, CEDULA_PROFESIONAL = ?, INTERROGATORIO = ?, RESPONSABLE = ?, COMENTARIOS = ?,
                EXPEDIENTE = ?, TSANGRE = ?, ALERGIAS = ?,
                TA = ?, FC_META = ?, FR = ?, TALLA = ?, PESO = ?,
                TA_BASAL = ?, FC_BASAL = ?, SO2_BASAL = ?, S_BASAL = ?,
                TA_5MCG = ?, FC_5MCG = ?, SO2_5MCG = ?, S_5MCG = ?,
                TA_10MCG = ?, FC_10MCG = ?, SO2_10MCG = ?, S_10MCG = ?,
                TA_20MCG = ?, FC_20MCG = ?, SO2_20MCG = ?, S_20MCG = ?,
                TA_30MCG = ?, FC_30MCG = ?, SO2_30MCG = ?, S_30MCG = ?,
                TA_40MCG = ?, FC_40MCG = ?, SO2_40MCG = ?, S_40MCG = ?,
                TA_ANTROPINA = ?, FC_ANTROPINA = ?, SO2_ANTROPINA = ?, S_ANTROPINA = ?,
                TA_2MIN = ?, FC_2MIN = ?, SO2_2MIN = ?, SINTOMAS_2MIN = ?,
                TA_4MIN = ?, FC_4MIN = ?, SO2_4MIN = ?, SINTOMAS_4MIN = ?,
                SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG',
                ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_EED = ?
            """
            cursor.execute(sql, (
                medico, cedula, interrogatorio, responsable, comentarios,
                expediente, tsangre, alergias,
                ta, fc_meta, fr, talla, peso,
                ta_basal, fc_basal, so2_basal, s_basal,
                ta_5mcg, fc_5mcg, so2_5mcg, s_5mcg,
                ta_10mcg, fc_10mcg, so2_10mcg, s_10mcg,
                ta_20mcg, fc_20mcg, so2_20mcg, s_20mcg,
                ta_30mcg, fc_30mcg, so2_30mcg, s_30mcg,
                ta_40mcg, fc_40mcg, so2_40mcg, s_40mcg,
                ta_antropina, fc_antropina, so2_antropina, s_antropina,
                ta_2min, fc_2min, so2_2min, sintomas_2min,
                ta_4min, fc_4min, so2_4min, sintomas_4min,
                c_name, c_key, c_id, pt_id,
                v_user, latest_mrnum
            ))
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_EED (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_EEDID,
                EXPEDIENTE, TSANGRE, ALERGIAS, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                NOMBRE_MEDICO, CEDULA_PROFESIONAL, INTERROGATORIO, RESPONSABLE, COMENTARIOS,
                TA, FC_META, FR, TALLA, PESO,
                TA_BASAL, FC_BASAL, SO2_BASAL, S_BASAL,
                TA_5MCG, FC_5MCG, SO2_5MCG, S_5MCG,
                TA_10MCG, FC_10MCG, SO2_10MCG, S_10MCG,
                TA_20MCG, FC_20MCG, SO2_20MCG, S_20MCG,
                TA_30MCG, FC_30MCG, SO2_30MCG, S_30MCG,
                TA_40MCG, FC_40MCG, SO2_40MCG, S_40MCG,
                TA_ANTROPINA, FC_ANTROPINA, SO2_ANTROPINA, S_ANTROPINA,
                TA_2MIN, FC_2MIN, SO2_2MIN, SINTOMAS_2MIN,
                TA_4MIN, FC_4MIN, SO2_4MIN, SINTOMAS_4MIN
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, ?, ?, ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                expediente, tsangre, alergias, v_user, v_user,
                medico, cedula, interrogatorio, responsable, comentarios,
                ta, fc_meta, fr, talla, peso,
                ta_basal, fc_basal, so2_basal, s_basal,
                ta_5mcg, fc_5mcg, so2_5mcg, s_5mcg,
                ta_10mcg, fc_10mcg, so2_10mcg, s_10mcg,
                ta_20mcg, fc_20mcg, so2_20mcg, s_20mcg,
                ta_30mcg, fc_30mcg, so2_30mcg, s_30mcg,
                ta_40mcg, fc_40mcg, so2_40mcg, s_40mcg,
                ta_antropina, fc_antropina, so2_antropina, s_antropina,
                ta_2min, fc_2min, so2_2min, sintomas_2min,
                ta_4min, fc_4min, so2_4min, sintomas_4min
            ))

        conn.commit()
        return {"status": "success", "message": "Consentimiento EED guardado correctamente en SQL Server"}
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_eed: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()



def fetch_consentimiento_25(pt_num: str, mrnum: int = None) -> dict:
    """
    Consulta la información del Consentimiento 25 (MR_CI_RGO_CE) en SQL Server.
    Permite filtrar por un mrnum específico o devolver el más reciente.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_RGO_CE, PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST,
                    N_MEDICO, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature
                FROM MR_CI_RGO_CE 
                WHERE MRNum_CI_RGO_CE = ?
            """, (mrnum,))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_RGO_CE, PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST,
                    N_MEDICO, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature
                FROM MR_CI_RGO_CE 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_RGO_CE DESC
            """, (pt_num,))
        row = cursor.fetchone()
        if not row:
            return {}

        cols = [c[0] for c in cursor.description]
        d = dict(zip(cols, row))
        
        cr_date = d.get("CreatedOn")
        sg_date = d.get("SignedOn")
        
        return {
            "mrnum": d.get("MRNum_CI_RGO_CE"),
            "pt_num": str(d.get("PTNum")),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": cr_date.strftime("%d/%m/%Y %H:%M") if cr_date else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": sg_date.strftime("%d/%m/%Y %H:%M") if sg_date else "",
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 25: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_25(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento 25 en la tabla MR_CI_RGO_CE de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_RGO_CE, CreatedOn 
            FROM MR_CI_RGO_CE 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_RGO_CE DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')

        if existing_row and is_today:
            sql = """
            UPDATE MR_CI_RGO_CE
            SET N_MEDICO = ?,
                SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_RGO_CE = ?
            """
            cursor.execute(sql, (medico, c_name, c_key, c_id, pt_id, v_user, latest_mrnum))
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_RGO_CE (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_RGO_CEID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn, N_MEDICO
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(), ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user, medico
            ))

        conn.commit()
        return {"status": "success", "message": "Consentimiento 25 guardado correctamente en SQL Server"}
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_25: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def fetch_consentimiento_34_01(pt_num: str, mrnum: int = None) -> dict:
    """
    Consulta la información del Consentimiento 34/01 (Mesa Inclinada - MR_CI_EMI) en SQL Server.
    Permite filtrar por un mrnum específico o devolver el más reciente.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_EMI, PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST,
                    NOMBRE_MEDICO_MI, EXPEDIENTE, GRUPORH, ALERGIAS, INTTYP, PARIENTE, CEDULA,
                    TA, FC_META, F_RESP, TEMPERATURA, PESO, TALLA, IRM, FBPR, FPR,
                    CONCLUSIONES, CONCLUSIONES_2, CONCLUSIONES_3,
                    CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature
                FROM MR_CI_EMI 
                WHERE MRNum_CI_EMI = ?
            """, (mrnum,))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_EMI, PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST,
                    NOMBRE_MEDICO_MI, EXPEDIENTE, GRUPORH, ALERGIAS, INTTYP, PARIENTE, CEDULA,
                    TA, FC_META, F_RESP, TEMPERATURA, PESO, TALLA, IRM, FBPR, FPR,
                    CONCLUSIONES, CONCLUSIONES_2, CONCLUSIONES_3,
                    CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature
                FROM MR_CI_EMI 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_EMI DESC
            """, (pt_num,))
        row = cursor.fetchone()
        if not row:
            return {}

        cols = [c[0] for c in cursor.description]
        d = dict(zip(cols, row))
        
        cr_date = d.get("CreatedOn")
        sg_date = d.get("SignedOn")
        
        return {
            "mrnum": d.get("MRNum_CI_EMI"),
            "pt_num": str(d.get("PTNum")),
            "nombre_medico_mi": str(d.get("NOMBRE_MEDICO_MI") or "").strip(),
            "medico_tratante": str(d.get("NOMBRE_MEDICO_MI") or "").strip(),
            "expediente": str(d.get("EXPEDIENTE") or "").strip(),
            "gruporh": str(d.get("GRUPORH") or "").strip(),
            "alergias": str(d.get("ALERGIAS") or "").strip(),
            "tipo_interrogatorio": str(d.get("INTTYP") or "DIRECTO").strip(),
            "pariente": str(d.get("PARIENTE") or "").strip(),
            "cedula": str(d.get("CEDULA") or "").strip(),
            "ta": str(d.get("TA") or "").strip(),
            "fc_meta": str(d.get("FC_META") or "").strip(),
            "f_resp": str(d.get("F_RESP") or "").strip(),
            "temperatura": str(d.get("TEMPERATURA") or "").strip(),
            "peso": str(d.get("PESO") or "").strip(),
            "talla": str(d.get("TALLA") or "").strip(),
            "irm": str(d.get("IRM") or "").strip(),
            "fbpr": str(d.get("FBPR") or "").strip(),
            "fpr": str(d.get("FPR") or "").strip(),
            "conclusiones": str(d.get("CONCLUSIONES") or "").strip(),
            "conclusiones_2": str(d.get("CONCLUSIONES_2") or "").strip(),
            "conclusiones_3": str(d.get("CONCLUSIONES_3") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": cr_date.strftime("%d/%m/%Y %H:%M") if cr_date else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": sg_date.strftime("%d/%m/%Y %H:%M") if sg_date else "",
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 34_01: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_34_01(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento 34/01 en la tabla MR_CI_EMI de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_EMI, CreatedOn 
            FROM MR_CI_EMI 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_EMI DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("nombre_medico_mi") or "").strip()
        expediente = str(consent_data.get("expediente") or f"PT-{pt_num}").strip()
        gruporh = str(consent_data.get("gruporh") or consent_data.get("grupo_rh") or "").strip()
        alergias = str(consent_data.get("alergias") or "NEGADAS").strip()
        inttyp = str(consent_data.get("tipo_interrogatorio") or consent_data.get("inttyp") or "DIRECTO").strip()
        pariente = str(consent_data.get("pariente") or consent_data.get("representante_legal") or "").strip()
        cedula = str(consent_data.get("cedula") or "").strip()
        ta = str(consent_data.get("ta") or "").strip()
        fc_meta = str(consent_data.get("fc_meta") or "").strip()
        f_resp = str(consent_data.get("f_resp") or "").strip()
        temperatura = str(consent_data.get("temperatura") or "").strip()
        peso = str(consent_data.get("peso") or "").strip()
        talla = str(consent_data.get("talla") or "").strip()
        irm = str(consent_data.get("irm") or "").strip()
        fbpr = str(consent_data.get("fbpr") or "").strip()
        fpr = str(consent_data.get("fpr") or "").strip()
        conclusiones = str(consent_data.get("conclusiones") or consent_data.get("conclusion_1") or "").strip()
        conclusiones_2 = str(consent_data.get("conclusiones_2") or consent_data.get("conclusion_2") or "").strip()
        conclusiones_3 = str(consent_data.get("conclusiones_3") or consent_data.get("conclusion_3") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        is_new = bool(consent_data.get("is_new", False))

        if existing_row and is_today and not is_new:
            sql = """
            UPDATE MR_CI_EMI
            SET NOMBRE_MEDICO_MI = ?, EXPEDIENTE = ?, GRUPORH = ?, ALERGIAS = ?, INTTYP = ?,
                PARIENTE = ?, CEDULA = ?, TA = ?, FC_META = ?, F_RESP = ?, TEMPERATURA = ?,
                PESO = ?, TALLA = ?, IRM = ?, FBPR = ?, FPR = ?,
                CONCLUSIONES = ?, CONCLUSIONES_2 = ?, CONCLUSIONES_3 = ?,
                SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_EMI = ?
            """
            cursor.execute(sql, (
                medico, expediente, gruporh, alergias, inttyp,
                pariente, cedula, ta, fc_meta, f_resp, temperatura,
                peso, talla, irm, fbpr, fpr,
                conclusiones, conclusiones_2, conclusiones_3,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_EMI (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_EMIID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                NOMBRE_MEDICO_MI, EXPEDIENTE, GRUPORH, ALERGIAS, INTTYP,
                PARIENTE, CEDULA, TA, FC_META, F_RESP, TEMPERATURA,
                PESO, TALLA, IRM, FBPR, FPR,
                CONCLUSIONES, CONCLUSIONES_2, CONCLUSIONES_3
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user,
                medico, expediente, gruporh, alergias, inttyp,
                pariente, cedula, ta, fc_meta, f_resp, temperatura,
                peso, talla, irm, fbpr, fpr,
                conclusiones, conclusiones_2, conclusiones_3
            ))

        conn.commit()
        return {"status": "success", "message": "Consentimiento 34/01 (Mesa Inclinada) guardado correctamente en SQL Server"}
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_34_01: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def fetch_consentimiento_12(pt_num: str, mrnum: Optional[int] = None) -> dict:
    """
    Obtiene los datos del Consentimiento 12 (MR_CI_RGO_HU - Gineco Hosp/Urg) desde SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_RGO_HU, PTNum, PTID, N_MEDICO, DIAGNOSTICO, EXPEDIENTE,
                    CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature, MR_ST
                FROM MR_CI_RGO_HU 
                WHERE MRNum_CI_RGO_HU = ?
            """, (mrnum,))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_RGO_HU, PTNum, PTID, N_MEDICO, DIAGNOSTICO, EXPEDIENTE,
                    CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature, MR_ST
                FROM MR_CI_RGO_HU 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_RGO_HU DESC
            """, (pt_num,))
            
        row = cursor.fetchone()
        if not row:
            return {}

        cols = [column[0] for column in cursor.description]
        d = dict(zip(cols, row))
        
        return {
            "mrnum": d.get("MRNum_CI_RGO_HU"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "diagnostico": str(d.get("DIAGNOSTICO") or "").strip(),
            "expediente": str(d.get("EXPEDIENTE") or f"PT-{pt_num}").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 12: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_12(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento 12 en la tabla MR_CI_RGO_HU de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_RGO_HU, CreatedOn 
            FROM MR_CI_RGO_HU 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_RGO_HU DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()
        diagnostico = str(consent_data.get("diagnostico") or consent_data.get("diagnosticos") or "REVISIÓN GINECOLÓGICA Y OBSTÉTRICA").strip()
        expediente = str(consent_data.get("expediente") or f"PT-{pt_num}").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        is_new = bool(consent_data.get("is_new", False))

        if existing_row and is_today and not is_new:
            sql = """
            UPDATE MR_CI_RGO_HU
            SET N_MEDICO = ?, DIAGNOSTICO = ?, EXPEDIENTE = ?,
                SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_RGO_HU = ?
            """
            cursor.execute(sql, (
                medico, diagnostico, expediente,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_RGO_HU (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_RGO_HUID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO, DIAGNOSTICO, EXPEDIENTE
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user,
                medico, diagnostico, expediente
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success", 
            "message": "Consentimiento 12 (Gineco Hosp/Urg) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_12: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def fetch_consentimiento_04(pt_num: str, mrnum: Optional[int] = None) -> dict:
    """
    Obtiene los datos del Consentimiento 04 (MR_CI_CC - Catéter Venoso Central) desde SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_CC, PTNum, PTID, N_MEDICO,
                    CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature, MR_ST
                FROM MR_CI_CC 
                WHERE MRNum_CI_CC = ?
            """, (mrnum,))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_CC, PTNum, PTID, N_MEDICO,
                    CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, ESignature, MR_ST
                FROM MR_CI_CC 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_CC DESC
            """, (pt_num,))
            
        row = cursor.fetchone()
        if not row:
            return {}

        cols = [column[0] for column in cursor.description]
        d = dict(zip(cols, row))
        
        return {
            "mrnum": d.get("MRNum_CI_CC"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 04: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_04(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento 04 en la tabla MR_CI_CC de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_CC, CreatedOn 
            FROM MR_CI_CC 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_CC DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
        is_new = bool(consent_data.get("is_new", False))

        if existing_row and is_today and not is_new:
            sql = """
            UPDATE MR_CI_CC
            SET N_MEDICO = ?,
                SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_CC = ?
            """
            cursor.execute(sql, (
                medico,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_CC (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_CCID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user,
                medico
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success", 
            "message": "Consentimiento 04 (Catéter Venoso Central) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_04: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def fetch_consentimiento_15(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 15 (Consentimiento Cesárea / Disentimiento) desde la tabla MR_CI_CES de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_CES, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_CESID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO
                FROM MR_CI_CES 
                WHERE PTNum = ? AND MRNum_CI_CES = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_CES, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_CESID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO
                FROM MR_CI_CES 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_CES DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        
        if not row:
            return None
            
        d = dict(zip(columns, row))
        return {
            "mrnum": d.get("MRNum_CI_CES"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 15: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_15(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento 15 en la tabla MR_CI_CES de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_CES, CreatedOn 
            FROM MR_CI_CES 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_CES DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        # Revocación de firmas previas para obligar a nueva firma biométrica al editar
        revoke_sql = """
        UPDATE MR_CI_CES 
        SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
        WHERE PTNum = ?
        """
        cursor.execute(revoke_sql, (pt_num,))

        target_mr = None
        if is_today and latest_mrnum:
            sql = """
            UPDATE MR_CI_CES
            SET N_MEDICO = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_CES = ?
            """
            cursor.execute(sql, (
                medico,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_CES (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_CESID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user,
                medico
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success", 
            "message": "Consentimiento 15 (Cesárea / Disentimiento) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_15: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def fetch_consentimiento_02(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 02 (Consentimiento Diagnóstico y Tratamiento Quirúrgico / Disentimiento)
    desde la tabla MR_02_CI_TRATAMIENTO_QUIRURGICO de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_02_CI_TRATAMIENTO_QUIRURGICO, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_02_CI_TRATAMIENTO_QUIRURGICOID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, EXPEDIENTE, DIAGNOSTICO,
                    PROCED_PARA_CONFIRMAR_DIAGNOST, BENEFICIO_DE_DICHO_PROCEDIMIENTO,
                    TRATAMIENTOS_MEDICOS, TRATAMIENTOS_QUIRURGICOS, TRATAMIENTOS_ENDOSCOPICOS,
                    TRATAMIENTOS_DE_REHABILITACION, ANESTESIA, TIPO_DE_ANESTESIA,
                    PRINCIPALES_RIESGOS, TESTIGO_1, TESTIGO_2, MOTIVO_DE_NO_AUTORIZACION
                FROM MR_02_CI_TRATAMIENTO_QUIRURGICO 
                WHERE PTNum = ? AND MRNum_02_CI_TRATAMIENTO_QUIRURGICO = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_02_CI_TRATAMIENTO_QUIRURGICO, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_02_CI_TRATAMIENTO_QUIRURGICOID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, EXPEDIENTE, DIAGNOSTICO,
                    PROCED_PARA_CONFIRMAR_DIAGNOST, BENEFICIO_DE_DICHO_PROCEDIMIENTO,
                    TRATAMIENTOS_MEDICOS, TRATAMIENTOS_QUIRURGICOS, TRATAMIENTOS_ENDOSCOPICOS,
                    TRATAMIENTOS_DE_REHABILITACION, ANESTESIA, TIPO_DE_ANESTESIA,
                    PRINCIPALES_RIESGOS, TESTIGO_1, TESTIGO_2, MOTIVO_DE_NO_AUTORIZACION
                FROM MR_02_CI_TRATAMIENTO_QUIRURGICO 
                WHERE PTNum = ? 
                ORDER BY MRNum_02_CI_TRATAMIENTO_QUIRURGICO DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        
        if not row:
            return None
            
        d = dict(zip(columns, row))
        motivo = str(d.get("MOTIVO_DE_NO_AUTORIZACION") or "").strip()
        return {
            "mrnum": d.get("MRNum_02_CI_TRATAMIENTO_QUIRURGICO"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "expediente": str(d.get("EXPEDIENTE") or f"PT-{pt_num}").strip(),
            "diagnostico": str(d.get("DIAGNOSTICO") or "").strip(),
            "proced_para_confirmar_diagnost": str(d.get("PROCED_PARA_CONFIRMAR_DIAGNOST") or "").strip(),
            "beneficio_de_dicho_procedimiento": str(d.get("BENEFICIO_DE_DICHO_PROCEDIMIENTO") or "").strip(),
            "tratamientos_medicos": str(d.get("TRATAMIENTOS_MEDICOS") or "").strip(),
            "tratamientos_quirurgicos": str(d.get("TRATAMIENTOS_QUIRURGICOS") or "").strip(),
            "tratamientos_endoscopicos": str(d.get("TRATAMIENTOS_ENDOSCOPICOS") or "").strip(),
            "tratamientos_de_rehabilitacion": str(d.get("TRATAMIENTOS_DE_REHABILITACION") or "").strip(),
            "anestesia": str(d.get("ANESTESIA") or "SI").strip(),
            "tipo_de_anestesia": str(d.get("TIPO_DE_ANESTESIA") or "").strip(),
            "principales_riesgos": str(d.get("PRINCIPALES_RIESGOS") or "").strip(),
            "testigo1": str(d.get("TESTIGO_1") or "").strip(),
            "testigo2": str(d.get("TESTIGO_2") or "").strip(),
            "motivo_de_no_autorizacion": motivo,
            "no_autorizo": bool(motivo),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 02: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_02(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento 02 en la tabla MR_02_CI_TRATAMIENTO_QUIRURGICO de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        req_mrnum = consent_data.get("mrnum")
        latest_mrnum = None
        is_today = False
        
        if req_mrnum:
            cursor.execute("""
                SELECT TOP 1 MRNum_02_CI_TRATAMIENTO_QUIRURGICO, CreatedOn
                FROM MR_02_CI_TRATAMIENTO_QUIRURGICO
                WHERE PTNum = ? AND MRNum_02_CI_TRATAMIENTO_QUIRURGICO = ?
            """, (pt_num, req_mrnum))
            r = cursor.fetchone()
            if r:
                latest_mrnum = r[0]
                created_date = r[1]
                if created_date and hasattr(created_date, 'date'):
                    is_today = (created_date.date() == datetime.datetime.now().date())
        else:
            cursor.execute("""
                SELECT TOP 1 MRNum_02_CI_TRATAMIENTO_QUIRURGICO, CreatedOn 
                FROM MR_02_CI_TRATAMIENTO_QUIRURGICO 
                WHERE PTNum = ? 
                ORDER BY MRNum_02_CI_TRATAMIENTO_QUIRURGICO DESC
            """, (pt_num,))
            existing_row = cursor.fetchone()
            if existing_row:
                latest_mrnum = existing_row[0]
                created_date = existing_row[1]
                if created_date and hasattr(created_date, 'date'):
                    is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()
        expediente = str(consent_data.get("expediente") or pt_num).strip()
        diagnostico = str(consent_data.get("diagnostico") or "").strip()
        proced_conf = str(consent_data.get("proced_para_confirmar_diagnost") or consent_data.get("proced_confirmar") or "").strip()
        beneficio = str(consent_data.get("beneficio_de_dicho_procedimiento") or consent_data.get("beneficios") or "").strip()
        t_medicos = str(consent_data.get("tratamientos_medicos") or "").strip()
        t_quirurgicos = str(consent_data.get("tratamientos_quirurgicos") or "").strip()
        t_endoscopicos = str(consent_data.get("tratamientos_endoscopicos") or "").strip()
        t_rehab = str(consent_data.get("tratamientos_de_rehabilitacion") or "").strip()
        anestesia = str(consent_data.get("anestesia") or "SI").strip()
        t_anestesia = str(consent_data.get("tipo_de_anestesia") or consent_data.get("tipo_anestesia") or "").strip()
        p_riesgos = str(consent_data.get("principales_riesgos") or "").strip()
        testigo1 = str(consent_data.get("testigo1") or consent_data.get("testigo_1") or "").strip()
        testigo2 = str(consent_data.get("testigo2") or consent_data.get("testigo_2") or "").strip()
        
        is_no_aut = bool(consent_data.get("no_autorizo") or consent_data.get("tipo") == "no_autorizo")
        motivo_no = str(consent_data.get("motivo_de_no_autorizacion") or consent_data.get("motivo_no_acepto") or "").strip() if is_no_aut else ""

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        # Revocar firma previa al editar
        if latest_mrnum:
            revoke_sql = """
            UPDATE MR_02_CI_TRATAMIENTO_QUIRURGICO 
            SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
            WHERE MRNum_02_CI_TRATAMIENTO_QUIRURGICO = ?
            """
            cursor.execute(revoke_sql, (latest_mrnum,))

        target_mr = None
        if is_today and latest_mrnum and not consent_data.get("isNew"):
            sql = """
            UPDATE MR_02_CI_TRATAMIENTO_QUIRURGICO
            SET N_MEDICO = ?, EXPEDIENTE = ?, DIAGNOSTICO = ?,
                PROCED_PARA_CONFIRMAR_DIAGNOST = ?, BENEFICIO_DE_DICHO_PROCEDIMIENTO = ?,
                TRATAMIENTOS_MEDICOS = ?, TRATAMIENTOS_QUIRURGICOS = ?,
                TRATAMIENTOS_ENDOSCOPICOS = ?, TRATAMIENTOS_DE_REHABILITACION = ?,
                ANESTESIA = ?, TIPO_DE_ANESTESIA = ?, PRINCIPALES_RIESGOS = ?,
                TESTIGO_1 = ?, TESTIGO_2 = ?, MOTIVO_DE_NO_AUTORIZACION = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_02_CI_TRATAMIENTO_QUIRURGICO = ?
            """
            cursor.execute(sql, (
                medico, expediente, diagnostico,
                proced_conf, beneficio,
                t_medicos, t_quirurgicos,
                t_endoscopicos, t_rehab,
                anestesia, t_anestesia, p_riesgos,
                testigo1, testigo2, motivo_no,
                c_name, c_key, c_id, pt_id,
                v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_02_CI_TRATAMIENTO_QUIRURGICO (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_02_CI_TRATAMIENTO_QUIRURGICOID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO, EXPEDIENTE, DIAGNOSTICO,
                PROCED_PARA_CONFIRMAR_DIAGNOST, BENEFICIO_DE_DICHO_PROCEDIMIENTO,
                TRATAMIENTOS_MEDICOS, TRATAMIENTOS_QUIRURGICOS,
                TRATAMIENTOS_ENDOSCOPICOS, TRATAMIENTOS_DE_REHABILITACION,
                ANESTESIA, TIPO_DE_ANESTESIA, PRINCIPALES_RIESGOS,
                TESTIGO_1, TESTIGO_2, MOTIVO_DE_NO_AUTORIZACION
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user,
                medico, expediente, diagnostico,
                proced_conf, beneficio,
                t_medicos, t_quirurgicos,
                t_endoscopicos, t_rehab,
                anestesia, t_anestesia, p_riesgos,
                testigo1, testigo2, motivo_no
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success", 
            "message": "Consentimiento 02 (Tratamiento Quirúrgico / Disentimiento) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_02: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def fetch_consentimiento_08(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 08 (Consentimiento Diagnóstico y Tratamiento en Admisión Continua)
    desde la tabla MR_08_CI_DIAGNOSTICO_ADMISION_CONTI de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_08_CI_DIAGNOSTICO_ADMISION_CONTIID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, EXPEDIENTE, DIAGNOSTICO,
                    TESTIGO_1, PROCEDIMIENTOS, RIESGOS_INHERENTES_A_PROCEDIMIEN,
                    PROB_PROCED_Y_ALTS, BENEFICIOS, TESTIGO_2
                FROM MR_08_CI_DIAGNOSTICO_ADMISION_CONTI 
                WHERE PTNum = ? AND MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_08_CI_DIAGNOSTICO_ADMISION_CONTIID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, EXPEDIENTE, DIAGNOSTICO,
                    TESTIGO_1, PROCEDIMIENTOS, RIESGOS_INHERENTES_A_PROCEDIMIEN,
                    PROB_PROCED_Y_ALTS, BENEFICIOS, TESTIGO_2
                FROM MR_08_CI_DIAGNOSTICO_ADMISION_CONTI 
                WHERE PTNum = ? 
                ORDER BY MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        
        if not row:
            return None
            
        d = dict(zip(columns, row))
        riesgos_val = str(d.get("RIESGOS_INHERENTES_A_PROCEDIMIEN") or "").strip()
        return {
            "mrnum": d.get("MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "expediente": str(d.get("EXPEDIENTE") or f"PT-{pt_num}").strip(),
            "diagnostico": str(d.get("DIAGNOSTICO") or "").strip(),
            "procedimientos": str(d.get("PROCEDIMIENTOS") or "").strip(),
            "riesgos_inherentes_a_procedimien": riesgos_val,
            "riesgos": riesgos_val,
            "prob_proced_y_alts": str(d.get("PROB_PROCED_Y_ALTS") or "").strip(),
            "alternativas": str(d.get("PROB_PROCED_Y_ALTS") or "").strip(),
            "beneficios": str(d.get("BENEFICIOS") or "").strip(),
            "testigo1": str(d.get("TESTIGO_1") or "").strip(),
            "testigo_1": str(d.get("TESTIGO_1") or "").strip(),
            "testigo2": str(d.get("TESTIGO_2") or "").strip(),
            "testigo_2": str(d.get("TESTIGO_2") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 08: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_08(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento 08 en la tabla MR_08_CI_DIAGNOSTICO_ADMISION_CONTI de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        req_mrnum = consent_data.get("mrnum")
        latest_mrnum = None
        is_today = False
        
        if req_mrnum:
            cursor.execute("""
                SELECT TOP 1 MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI, CreatedOn
                FROM MR_08_CI_DIAGNOSTICO_ADMISION_CONTI
                WHERE PTNum = ? AND MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI = ?
            """, (pt_num, req_mrnum))
            r = cursor.fetchone()
            if r:
                latest_mrnum = r[0]
                created_date = r[1]
                if created_date and hasattr(created_date, 'date'):
                    is_today = (created_date.date() == datetime.datetime.now().date())
        else:
            cursor.execute("""
                SELECT TOP 1 MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI, CreatedOn 
                FROM MR_08_CI_DIAGNOSTICO_ADMISION_CONTI 
                WHERE PTNum = ? 
                ORDER BY MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI DESC
            """, (pt_num,))
            existing_row = cursor.fetchone()
            if existing_row:
                latest_mrnum = existing_row[0]
                created_date = existing_row[1]
                if created_date and hasattr(created_date, 'date'):
                    is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()
        expediente = str(consent_data.get("expediente") or pt_num).strip()
        diagnostico = str(consent_data.get("diagnostico") or "").strip()
        procedimientos = str(consent_data.get("procedimientos") or "").strip()
        riesgos = str(consent_data.get("riesgos_inherentes_a_procedimien") or consent_data.get("riesgos") or "").strip()
        prob_proced = str(consent_data.get("prob_proced_y_alts") or consent_data.get("alternativas") or "").strip()
        beneficios = str(consent_data.get("beneficios") or "").strip()
        testigo1 = str(consent_data.get("testigo1") or consent_data.get("testigo_1") or "").strip()
        testigo2 = str(consent_data.get("testigo2") or consent_data.get("testigo_2") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        # Revocar firma previa al editar
        if latest_mrnum:
            revoke_sql = """
            UPDATE MR_08_CI_DIAGNOSTICO_ADMISION_CONTI 
            SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
            WHERE MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI = ?
            """
            cursor.execute(revoke_sql, (latest_mrnum,))

        target_mr = None
        if is_today and latest_mrnum and not consent_data.get("isNew"):
            sql = """
            UPDATE MR_08_CI_DIAGNOSTICO_ADMISION_CONTI
            SET N_MEDICO = ?, EXPEDIENTE = ?, DIAGNOSTICO = ?,
                PROCEDIMIENTOS = ?, RIESGOS_INHERENTES_A_PROCEDIMIEN = ?,
                PROB_PROCED_Y_ALTS = ?, BENEFICIOS = ?,
                TESTIGO_1 = ?, TESTIGO_2 = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI = ?
            """
            cursor.execute(sql, (
                medico, expediente, diagnostico,
                procedimientos, riesgos,
                prob_proced, beneficios,
                testigo1, testigo2,
                c_name, c_key, c_id, pt_id,
                v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_08_CI_DIAGNOSTICO_ADMISION_CONTI (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_08_CI_DIAGNOSTICO_ADMISION_CONTIID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO, EXPEDIENTE, DIAGNOSTICO,
                PROCEDIMIENTOS, RIESGOS_INHERENTES_A_PROCEDIMIEN,
                PROB_PROCED_Y_ALTS, BENEFICIOS,
                TESTIGO_1, TESTIGO_2
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user,
                medico, expediente, diagnostico,
                procedimientos, riesgos,
                prob_proced, beneficios,
                testigo1, testigo2
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success", 
            "message": "Consentimiento 08 (Admisión Continua / Diagnóstico) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_08: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def fetch_generic_format_history(codigo_o_tabla: str, pt_num: str) -> list[dict]:
    """
    MOTOR UNIVERSAL DE CONSULTA DE HISTORIAL PARA CUALQUIERA DE LOS 100+ FORMATOS CLÍNICOS.
    Consulta dinámicamente SQL Server reflejando registros creados, modificados y firmados.
    """
    try:
        from .vertical_signer import resolve_vertical_controller_and_pk
    except Exception:
        from vertical_signer import resolve_vertical_controller_and_pk

    c_name, pk_col = resolve_vertical_controller_and_pk(codigo_o_tabla)
    if not c_name or not pk_col:
        return []

    conn = get_kh_connection()
    if not conn:
        return []

    results = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?", (c_name,))
        cols = [r[0] for r in cur.fetchall()]
        cols_upper = {c.upper(): c for c in cols}

        doc_col = None
        for candidate in ['N_MEDICO', 'NOMBRE_MEDICO', 'MEDICO_TRATANTE', 'MEDICO', 'SignedBy']:
            if candidate.upper() in cols_upper:
                doc_col = cols_upper[candidate.upper()]
                break

        diag_col = None
        for candidate in ['DIAGNOSTICO', 'DIAGNOSTICOS', 'DIAG_PREOP', 'DIAG_POSTOP', 'DIAG']:
            if candidate.upper() in cols_upper:
                diag_col = cols_upper[candidate.upper()]
                break

        motivo_col = None
        for candidate in ['MOTIVO_DE_NO_AUTORIZACION', 'MOTIVO_NO_AUTORIZACION', 'MOTIVO']:
            if candidate.upper() in cols_upper:
                motivo_col = cols_upper[candidate.upper()]
                break

        query = f"SELECT {pk_col}, PTNum, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn, SignedBy, SignedOn, MR_ST"
        if doc_col: query += f", {doc_col}"
        if diag_col: query += f", {diag_col}"
        if motivo_col: query += f", {motivo_col}"
        query += f" FROM {c_name} WHERE PTNum = ? ORDER BY {pk_col} DESC"

        cur.execute(query, (pt_num,))
        for row in cur.fetchall():
            cr_dt = row[3]
            mo_dt = row[5]
            sg_dt = row[7]
            signed_by = str(row[6] or "").strip()
            mr_st = str(row[8] or "").strip()
            
            idx = 9
            medico = ""
            if doc_col:
                medico = str(row[idx] or "").strip()
                idx += 1
            diag = ""
            if diag_col:
                diag = str(row[idx] or "").strip()
                idx += 1
            motivo = ""
            if motivo_col:
                motivo = str(row[idx] or "").strip()
                idx += 1

            is_signed = bool(signed_by or sg_dt or mr_st == 'SG')

            results.append({
                "mrnum": row[0],
                "controller_name": c_name,
                "pk_col": pk_col,
                "medico_tratante": medico or signed_by or "",
                "diagnostico": diag,
                "motivo_de_no_autorizacion": motivo,
                "no_autorizo": bool(motivo),
                "created_by": str(row[2] or "").strip(),
                "created_on": cr_dt.strftime("%d/%m/%Y %H:%M") if cr_dt else "",
                "modified_by": str(row[4] or "").strip(),
                "modified_on": mo_dt.strftime("%d/%m/%Y %H:%M") if mo_dt else "",
                "signed_by": signed_by,
                "signed_on": sg_dt.strftime("%d/%m/%Y %H:%M") if sg_dt else "",
                "firmado": is_signed,
                "mr_st": mr_st or ("SG" if is_signed else "RG")
            })
    except Exception as e:
        print(f"Error en fetch_generic_format_history para {c_name}: {e}")
    finally:
        conn.close()

    return results


def get_ptcn_contacts(pt_identifier: str) -> list:
    """
    Obtiene los contactos/familiares/testigos registrados en la tabla PTCN de Vertical (KH_HE).
    """
    conn = get_kh_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        pt_str = str(pt_identifier or "").strip()
        if pt_str.isdigit():
            cursor.execute("SELECT TOP 1 PTID FROM PT WHERE PTNum = ?", (int(pt_str),))
        else:
            cursor.execute("SELECT TOP 1 PTID FROM PT WHERE PTNum = ? OR FullName LIKE ?", (-1, f"%{pt_str}%"))
        pt_row = cursor.fetchone()
        if not pt_row:
            return []
        ptid = pt_row[0]
        cursor.execute("""
            SELECT CTCNNum, PTID, ContactRelationship, ContactRelationshipOther,
                   ContactType, ContactName, IdType, Identification, Address,
                   ContactTelephones, ContactEMail, CreatedBy, CreatedOn
            FROM PTCN
            WHERE PTID = ?
            ORDER BY CTCNNum ASC
        """, (ptid,))
        contacts = []
        for r in cursor.fetchall():
            contacts.append({
                "ctcn_num": r[0],
                "ptid": str(r[1]),
                "contact_relationship": str(r[2] or "").strip(),
                "contact_relationship_other": str(r[3] or "").strip(),
                "contact_type": str(r[4] or "").strip(),
                "contact_name": str(r[5] or "").strip(),
                "id_type": str(r[6] or "").strip(),
                "identification": str(r[7] or "").strip(),
                "address": str(r[8] or "").strip(),
                "phone": str(r[9] or "").strip(),
                "email": str(r[10] or "").strip(),
                "created_by": str(r[11] or "").strip(),
                "created_on": r[12].strftime("%d/%m/%Y %H:%M") if r[12] else ""
            })
        return contacts
    except Exception as e:
        print(f"Error consultando PTCN: {e}")
        return []
    finally:
        conn.close()


@explicit_kh_mutation
def sync_contact_to_ptcn(pt_identifier: str, contact_data: dict, username: str = "sistema") -> bool:
    """
    Sincroniza un contacto/tutor/testigo hacia la tabla PTCN en SQL Server (Vertical KH_HE).
    """
    conn = get_kh_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        pt_str = str(pt_identifier or "").strip()
        if pt_str.isdigit():
            cursor.execute("SELECT TOP 1 PTID FROM PT WHERE PTNum = ?", (int(pt_str),))
        else:
            cursor.execute("SELECT TOP 1 PTID FROM PT WHERE PTNum = ? OR FullName LIKE ?", (-1, f"%{pt_str}%"))
        pt_row = cursor.fetchone()
        if not pt_row:
            return False
        ptid = pt_row[0]
        
        name = (contact_data.get("nombre_completo") or contact_data.get("contact_name") or "").strip().upper()
        rel_other = (contact_data.get("parentesco") or contact_data.get("contact_relationship_other") or "OTRO").strip().upper()
        c_type = (contact_data.get("tipo_firmante") or contact_data.get("contact_type") or "RESPONSABLE").strip().upper()
        id_type = (contact_data.get("id_type") or "INE").strip().upper()
        id_num = (contact_data.get("identificacion_oficial") or contact_data.get("identification") or "").strip()
        address = (contact_data.get("domicilio") or contact_data.get("address") or "").strip()
        phone = (contact_data.get("telefono") or contact_data.get("phone") or "").strip()
        email = (contact_data.get("email") or "").strip()

        rel_code = "OT"
        if "PADRE" in rel_other or "MADRE" in rel_other:
            rel_code = "PA"
        elif "ESPOS" in rel_other or "CONYUGE" in rel_other:
            rel_code = "SP"

        cursor.execute("""
            SELECT CTCNNum FROM PTCN WHERE PTID = ? AND ContactName = ?
        """, (ptid, name))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE PTCN
                SET ContactRelationship = ?, ContactRelationshipOther = ?,
                    ContactType = ?, IdType = ?, Identification = ?, Address = ?,
                    ContactTelephones = ?, ContactEMail = ?, ModifiedBy = ?, ModifiedOn = GETDATE()
                WHERE CTCNNum = ?
            """, (rel_code, rel_other, c_type, id_type, id_num, address, phone, email, username, existing[0]))
        else:
            cursor.execute("""
                INSERT INTO PTCN (
                    PTID, ContactRelationship, ContactRelationshipOther,
                    ContactType, ContactName, IdType, Identification, Address,
                    ContactTelephones, ContactEMail, CreatedBy, CreatedOn
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
            """, (ptid, rel_code, rel_other, c_type, name, id_type, id_num, address, phone, email, username))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error sincronizando con PTCN: {e}")
        return False
    finally:
        conn.close()


@explicit_kh_mutation
def delete_contact_from_ptcn(pt_identifier: str, contact_name: str) -> bool:
    """
    Elimina un contacto/testigo de la tabla PTCN en SQL Server (Vertical KH_HE).
    """
    conn = get_kh_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        pt_str = str(pt_identifier or "").strip()
        if pt_str.isdigit():
            cursor.execute("SELECT TOP 1 PTID FROM PT WHERE PTNum = ?", (int(pt_str),))
        else:
            cursor.execute("SELECT TOP 1 PTID FROM PT WHERE PTNum = ? OR FullName LIKE ?", (-1, f"%{pt_str}%"))
        pt_row = cursor.fetchone()
        if not pt_row:
            return False
        ptid = pt_row[0]
        
        name = str(contact_name or "").strip().upper()
        cursor.execute("DELETE FROM PTCN WHERE PTID = ? AND UPPER(ContactName) = ?", (ptid, name))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error eliminando de PTCN: {e}")
        return False
    finally:
        conn.close()


def fetch_consentimiento_43(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 43 (Orden de Intubación Endotraqueal / Soporte Ventilatorio)
    desde la tabla MR_CI_OI de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_OI, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_OIID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO
                FROM MR_CI_OI 
                WHERE PTNum = ? AND MRNum_CI_OI = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_OI, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_OIID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO
                FROM MR_CI_OI 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_OI DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        
        if not row:
            return None
            
        d = dict(zip(columns, row))
        return {
            "mrnum": d.get("MRNum_CI_OI"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 43: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_43(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza la Orden de Intubación (Formato 43) en la tabla MR_CI_OI de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_OI, CreatedOn 
            FROM MR_CI_OI 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_OI DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        # Revocación de firmas previas en SQL Server para obligar a nueva firma biométrica al editar
        revoke_sql = """
        UPDATE MR_CI_OI 
        SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
        WHERE PTNum = ?
        """
        cursor.execute(revoke_sql, (pt_num,))

        target_mr = None
        if is_today and latest_mrnum:
            sql = """
            UPDATE MR_CI_OI
            SET N_MEDICO = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_OI = ?
            """
            cursor.execute(sql, (
                medico,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_nota = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_OI (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_OIID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_nota,
                v_user, v_user,
                medico
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success", 
            "message": "Formato 43 (Orden de Intubación Endotraqueal) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_43: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


# ==============================================================================
# FORMATO 11: CONSENTIMIENTO DE NO REANIMACIÓN (MR_CI_NO_REANIMACION)
# ==============================================================================

def fetch_consentimiento_11(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 11: Consentimiento de No Reanimación (Voluntad Anticipada)
    desde la tabla MR_CI_NO_REANIMACION de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_NO_REANIMACION, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_NO_REANIMACIONID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, EXPEDIENTE, BENEFICIOS_Y_RIESGOS_DE_NR,
                    ALTERNATIVA_NR, TESTIGO_1, TESTIGO_2, DIAGNOSTICO
                FROM MR_CI_NO_REANIMACION 
                WHERE PTNum = ? AND MRNum_CI_NO_REANIMACION = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_NO_REANIMACION, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_NO_REANIMACIONID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, EXPEDIENTE, BENEFICIOS_Y_RIESGOS_DE_NR,
                    ALTERNATIVA_NR, TESTIGO_1, TESTIGO_2, DIAGNOSTICO
                FROM MR_CI_NO_REANIMACION 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_NO_REANIMACION DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if not row:
            return None
            
        d = dict(zip(columns, row))
        return {
            "mrnum": d.get("MRNum_CI_NO_REANIMACION"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "expediente": str(d.get("EXPEDIENTE") or "").strip(),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "diagnostico": str(d.get("DIAGNOSTICO") or "").strip(),
            "beneficios_y_riesgos_de_nr": str(d.get("BENEFICIOS_Y_RIESGOS_DE_NR") or "").strip(),
            "alternativa_nr": str(d.get("ALTERNATIVA_NR") or "").strip(),
            "testigo_1": str(d.get("TESTIGO_1") or "").strip(),
            "testigo_2": str(d.get("TESTIGO_2") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 11: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_11(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento de No Reanimación (Formato 11) en MR_CI_NO_REANIMACION.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_NO_REANIMACION, CreatedOn 
            FROM MR_CI_NO_REANIMACION 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_NO_REANIMACION DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()
        expediente = str(consent_data.get("expediente") or consent_data.get("mrn") or f"PT-{pt_num}").strip()
        diag = str(consent_data.get("diagnostico") or "").strip()
        benef_riesg = str(consent_data.get("beneficios_y_riesgos_de_nr") or consent_data.get("beneficios") or "").strip()
        alt = str(consent_data.get("alternativa_nr") or consent_data.get("alternativas") or "").strip()
        t1 = str(consent_data.get("testigo_1") or consent_data.get("testigo1") or "").strip()
        t2 = str(consent_data.get("testigo_2") or consent_data.get("testigo2") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        is_new_requested = bool(consent_data.get("is_new"))
        explicit_mrnum = consent_data.get("mrnum")

        # Revocación de firmas previas para obligar a nueva firma al editar
        if explicit_mrnum and not is_new_requested:
            cursor.execute("""
                UPDATE MR_CI_NO_REANIMACION 
                SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
                WHERE PTNum = ? AND MRNum_CI_NO_REANIMACION = ?
            """, (pt_num, explicit_mrnum))
        elif not is_new_requested:
            cursor.execute("""
                UPDATE MR_CI_NO_REANIMACION 
                SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
                WHERE PTNum = ?
            """, (pt_num,))

        target_mr = None
        if not is_new_requested and explicit_mrnum:
            sql = """
            UPDATE MR_CI_NO_REANIMACION
            SET N_MEDICO = ?, EXPEDIENTE = ?, DIAGNOSTICO = ?, BENEFICIOS_Y_RIESGOS_DE_NR = ?,
                ALTERNATIVA_NR = ?, TESTIGO_1 = ?, TESTIGO_2 = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_NO_REANIMACION = ?
            """
            cursor.execute(sql, (
                medico, expediente, diag, benef_riesg, alt, t1, t2,
                c_name, c_key, c_id, pt_id, v_user, explicit_mrnum
            ))
            target_mr = explicit_mrnum
        elif not is_new_requested and is_today and latest_mrnum:
            sql = """
            UPDATE MR_CI_NO_REANIMACION
            SET N_MEDICO = ?, EXPEDIENTE = ?, DIAGNOSTICO = ?, BENEFICIOS_Y_RIESGOS_DE_NR = ?,
                ALTERNATIVA_NR = ?, TESTIGO_1 = ?, TESTIGO_2 = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_NO_REANIMACION = ?
            """
            cursor.execute(sql, (
                medico, expediente, diag, benef_riesg, alt, t1, t2,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_doc = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_NO_REANIMACION (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_NO_REANIMACIONID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO, EXPEDIENTE, DIAGNOSTICO, BENEFICIOS_Y_RIESGOS_DE_NR, ALTERNATIVA_NR, TESTIGO_1, TESTIGO_2
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?, ?, ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_doc,
                v_user, v_user,
                medico, expediente, diag, benef_riesg, alt, t1, t2
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success",
            "message": "Formato 11 (Consentimiento de No Reanimación) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_11: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


# ==============================================================================
# FORMATO 19: CONSENTIMIENTO INFORMADO HISTERECTOMÍA (MR_CI_HISTERECTOMIA)
# ==============================================================================

def fetch_consentimiento_19(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 19: Consentimiento Informado para Histerectomía
    desde la tabla MR_CI_HISTERECTOMIA de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_HISTERECTOMIA, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_HISTERECTOMIAID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, EXPEDIENTE, DIAGNOSTICO,
                    EXPLICACION_DE_PROCESO, BENEFICIOS_DE_PROCEDIMIENTO, INTERVENCION_COMPLEMENTARIA,
                    ALTERNATIVAS_TERAPEUTICAS, TESTIGO_1, TESTIGO_2, MOTIVO_DE_NO_AUTORIZACION
                FROM MR_CI_HISTERECTOMIA 
                WHERE PTNum = ? AND MRNum_CI_HISTERECTOMIA = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_HISTERECTOMIA, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_HISTERECTOMIAID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, EXPEDIENTE, DIAGNOSTICO,
                    EXPLICACION_DE_PROCESO, BENEFICIOS_DE_PROCEDIMIENTO, INTERVENCION_COMPLEMENTARIA,
                    ALTERNATIVAS_TERAPEUTICAS, TESTIGO_1, TESTIGO_2, MOTIVO_DE_NO_AUTORIZACION
                FROM MR_CI_HISTERECTOMIA 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_HISTERECTOMIA DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if not row:
            return None
            
        d = dict(zip(columns, row))
        return {
            "mrnum": d.get("MRNum_CI_HISTERECTOMIA"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "expediente": str(d.get("EXPEDIENTE") or "").strip(),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "diagnostico": str(d.get("DIAGNOSTICO") or "").strip(),
            "explicacion_de_proceso": str(d.get("EXPLICACION_DE_PROCESO") or "").strip(),
            "beneficios_de_procedimiento": str(d.get("BENEFICIOS_DE_PROCEDIMIENTO") or "").strip(),
            "intervencion_complementaria": str(d.get("INTERVENCION_COMPLEMENTARIA") or "").strip(),
            "alternativas_terapeuticas": str(d.get("ALTERNATIVAS_TERAPEUTICAS") or "").strip(),
            "testigo_1": str(d.get("TESTIGO_1") or "").strip(),
            "testigo_2": str(d.get("TESTIGO_2") or "").strip(),
            "motivo_de_no_autorizacion": str(d.get("MOTIVO_DE_NO_AUTORIZACION") or "").strip(),
            "no_autorizo": bool(d.get("MOTIVO_DE_NO_AUTORIZACION")),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 19: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_19(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento de Histerectomía (Formato 19) en MR_CI_HISTERECTOMIA.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_HISTERECTOMIA, CreatedOn 
            FROM MR_CI_HISTERECTOMIA 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_HISTERECTOMIA DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()
        expediente = str(consent_data.get("expediente") or consent_data.get("mrn") or f"PT-{pt_num}").strip()
        diag = str(consent_data.get("diagnostico") or "MIOMATOSIS UTERINA / HEMORRAGIA UTERINA ANORMAL").strip()
        exp_proc = str(consent_data.get("explicacion_de_proceso") or consent_data.get("explicacion") or "Histerectomía total abdominal con hemostasia y técnica quirúrgica normada").strip()
        benef = str(consent_data.get("beneficios_de_procedimiento") or consent_data.get("beneficios") or "Resolución del sangrado uterino y dolor pélvico crónico").strip()
        interv_comp = str(consent_data.get("intervencion_complementaria") or "Salpingocromatoscopía o lisis de adherencias pélvicas según hallazgos").strip()
        alt = str(consent_data.get("alternativas_terapeuticas") or consent_data.get("alternativas") or "Tratamiento hormonal o colocación de dispositivo intrauterino").strip()
        t1 = str(consent_data.get("testigo_1") or consent_data.get("testigo1") or "").strip()
        t2 = str(consent_data.get("testigo_2") or consent_data.get("testigo2") or "").strip()
        motivo_no = str(consent_data.get("motivo_de_no_autorizacion") or consent_data.get("motivo_no_acepto") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        is_new_requested = bool(consent_data.get("is_new"))
        explicit_mrnum = consent_data.get("mrnum")

        # Revocación de firmas previas al editar
        if explicit_mrnum and not is_new_requested:
            cursor.execute("""
                UPDATE MR_CI_HISTERECTOMIA 
                SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
                WHERE PTNum = ? AND MRNum_CI_HISTERECTOMIA = ?
            """, (pt_num, explicit_mrnum))
        elif not is_new_requested:
            cursor.execute("""
                UPDATE MR_CI_HISTERECTOMIA 
                SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
                WHERE PTNum = ?
            """, (pt_num,))

        target_mr = None
        if not is_new_requested and explicit_mrnum:
            sql = """
            UPDATE MR_CI_HISTERECTOMIA
            SET N_MEDICO = ?, EXPEDIENTE = ?, DIAGNOSTICO = ?, EXPLICACION_DE_PROCESO = ?,
                BENEFICIOS_DE_PROCEDIMIENTO = ?, INTERVENCION_COMPLEMENTARIA = ?,
                ALTERNATIVAS_TERAPEUTICAS = ?, TESTIGO_1 = ?, TESTIGO_2 = ?,
                MOTIVO_DE_NO_AUTORIZACION = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_HISTERECTOMIA = ?
            """
            cursor.execute(sql, (
                medico, expediente, diag, exp_proc, benef, interv_comp, alt, t1, t2, motivo_no,
                c_name, c_key, c_id, pt_id, v_user, explicit_mrnum
            ))
            target_mr = explicit_mrnum
        elif not is_new_requested and is_today and latest_mrnum:
            sql = """
            UPDATE MR_CI_HISTERECTOMIA
            SET N_MEDICO = ?, EXPEDIENTE = ?, DIAGNOSTICO = ?, EXPLICACION_DE_PROCESO = ?,
                BENEFICIOS_DE_PROCEDIMIENTO = ?, INTERVENCION_COMPLEMENTARIA = ?,
                ALTERNATIVAS_TERAPEUTICAS = ?, TESTIGO_1 = ?, TESTIGO_2 = ?,
                MOTIVO_DE_NO_AUTORIZACION = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_HISTERECTOMIA = ?
            """
            cursor.execute(sql, (
                medico, expediente, diag, exp_proc, benef, interv_comp, alt, t1, t2, motivo_no,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_doc = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_HISTERECTOMIA (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_HISTERECTOMIAID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO, EXPEDIENTE, DIAGNOSTICO, EXPLICACION_DE_PROCESO,
                BENEFICIOS_DE_PROCEDIMIENTO, INTERVENCION_COMPLEMENTARIA,
                ALTERNATIVAS_TERAPEUTICAS, TESTIGO_1, TESTIGO_2, MOTIVO_DE_NO_AUTORIZACION
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_doc,
                v_user, v_user,
                medico, expediente, diag, exp_proc, benef, interv_comp, alt, t1, t2, motivo_no
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success",
            "message": "Formato 19 (Consentimiento para Histerectomía) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_19: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


# ==============================================================================
# FORMATO 15: EGRESO VOLUNTARIO (MR_EV_HOSP)
# ==============================================================================

def fetch_egreso_voluntario_15(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 15: Egreso Voluntario desde la tabla MR_EV_HOSP de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_EV_HOSP, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_EV_HOSPID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, N_REPLEGAL, EXPEDIENTE
                FROM MR_EV_HOSP 
                WHERE PTNum = ? AND MRNum_EV_HOSP = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_EV_HOSP, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_EV_HOSPID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO, N_REPLEGAL, EXPEDIENTE
                FROM MR_EV_HOSP 
                WHERE PTNum = ? 
                ORDER BY MRNum_EV_HOSP DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if not row:
            return None
            
        d = dict(zip(columns, row))
        return {
            "mrnum": d.get("MRNum_EV_HOSP"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "expediente": str(d.get("EXPEDIENTE") or "").strip(),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "n_replegal": str(d.get("N_REPLEGAL") or "").strip(),
            "declarante": str(d.get("N_REPLEGAL") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching egreso voluntario 15: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_egreso_voluntario_15(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Egreso Voluntario (Formato 15) en la tabla MR_EV_HOSP de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 MRNum_EV_HOSP, CreatedOn 
            FROM MR_EV_HOSP 
            WHERE PTNum = ? 
            ORDER BY MRNum_EV_HOSP DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()
        replegal = str(consent_data.get("n_replegal") or consent_data.get("declarante") or consent_data.get("paciente_o_representante") or "").strip()
        expediente = str(consent_data.get("expediente") or consent_data.get("mrn") or f"PT-{pt_num}").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        # Revocación de firmas previas
        cursor.execute("""
            UPDATE MR_EV_HOSP 
            SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
            WHERE PTNum = ?
        """, (pt_num,))

        req_mrnum = consent_data.get("mrnum")
        is_new_flag = bool(consent_data.get("is_new") or consent_data.get("isNew"))

        target_mr = None
        if req_mrnum and not is_new_flag:
            sql = """
            UPDATE MR_EV_HOSP
            SET N_MEDICO = ?, N_REPLEGAL = ?, EXPEDIENTE = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_EV_HOSP = ?
            """
            cursor.execute(sql, (
                medico, replegal, expediente,
                c_name, c_key, c_id, pt_id, v_user, int(req_mrnum)
            ))
            target_mr = int(req_mrnum)
        elif is_today and latest_mrnum and not is_new_flag:
            sql = """
            UPDATE MR_EV_HOSP
            SET N_MEDICO = ?, N_REPLEGAL = ?, EXPEDIENTE = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_EV_HOSP = ?
            """
            cursor.execute(sql, (
                medico, replegal, expediente,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_doc = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_EV_HOSP (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_EV_HOSPID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO, N_REPLEGAL, EXPEDIENTE
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?, ?, ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_doc,
                v_user, v_user,
                medico, replegal, expediente
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success",
            "message": "Formato 15 (Egreso Voluntario) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_egreso_voluntario_15: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


# ==============================================================================
# FORMATO 06: PROCEDIMIENTO ANESTÉSICO (MR_CI_APA)
# ==============================================================================

def fetch_consentimiento_06(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 06: Consentimiento para Autorizar Procedimiento Anestésico
    desde la tabla MR_CI_APA de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_APA, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_APAID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO
                FROM MR_CI_APA 
                WHERE PTNum = ? AND MRNum_CI_APA = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_APA, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_APAID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO
                FROM MR_CI_APA 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_APA DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if not row:
            return None
            
        d = dict(zip(columns, row))
        return {
            "mrnum": d.get("MRNum_CI_APA"),
            "pt_num": str(d.get("PTNum") or pt_num),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "medico_anestesiologo": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST")
        }
    except Exception as e:
        print(f"Error fetching consentimiento 06: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_06(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento para Procedimiento Anestésico (Formato 06) en MR_CI_APA.
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_APA, CreatedOn 
            FROM MR_CI_APA 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_APA DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_anestesiologo") or consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        is_new_requested = bool(consent_data.get("is_new"))
        explicit_mrnum = consent_data.get("mrnum")

        # Revocación de firmas previas
        if explicit_mrnum and not is_new_requested:
            cursor.execute("""
                UPDATE MR_CI_APA 
                SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
                WHERE PTNum = ? AND MRNum_CI_APA = ?
            """, (pt_num, explicit_mrnum))
        elif not is_new_requested:
            cursor.execute("""
                UPDATE MR_CI_APA 
                SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
                WHERE PTNum = ?
            """, (pt_num,))

        target_mr = None
        if not is_new_requested and explicit_mrnum:
            sql = """
            UPDATE MR_CI_APA
            SET N_MEDICO = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_APA = ?
            """
            cursor.execute(sql, (
                medico,
                c_name, c_key, c_id, pt_id, v_user, explicit_mrnum
            ))
            target_mr = explicit_mrnum
        elif not is_new_requested and is_today and latest_mrnum:
            sql = """
            UPDATE MR_CI_APA
            SET N_MEDICO = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_APA = ?
            """
            cursor.execute(sql, (
                medico,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_doc = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_APA (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_APAID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_doc,
                v_user, v_user,
                medico
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()
        return {
            "status": "success",
            "message": "Formato 06 (Procedimiento Anestésico) guardado correctamente en SQL Server",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_06: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def fetch_consentimiento_07(pt_num: str, mrnum: int = None) -> dict:
    """
    Obtiene los datos del Formato 07: Consentimiento Informado para Procedimientos Quirúrgicos
    desde la tabla MR_CI_PQ de SQL Server y PostgreSQL (HistoricoNotaClinica).
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        if mrnum:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_PQ, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_PQID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO
                FROM MR_CI_PQ 
                WHERE PTNum = ? AND MRNum_CI_PQ = ?
            """, (pt_num, mrnum))
        else:
            cursor.execute("""
                SELECT TOP 1 
                    MRNum_CI_PQ, PTNum, PTID, ControllerName, ControllerKey, ControllerID,
                    MR_ST, MR_CI_PQID, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                    SignedBy, SignedOn, N_MEDICO
                FROM MR_CI_PQ 
                WHERE PTNum = ? 
                ORDER BY MRNum_CI_PQ DESC
            """, (pt_num,))
            
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if not row:
            return None
            
        d = dict(zip(columns, row))
        active_mrnum = d.get("MRNum_CI_PQ")

        res = {
            "mrnum": active_mrnum,
            "pt_num": str(d.get("PTNum") or pt_num),
            "medico_tratante": str(d.get("N_MEDICO") or "").strip(),
            "n_medico": str(d.get("N_MEDICO") or "").strip(),
            "created_by": str(d.get("CreatedBy") or "").strip(),
            "created_on": d.get("CreatedOn").strftime("%d/%m/%Y %H:%M") if d.get("CreatedOn") else "",
            "modified_by": str(d.get("ModifiedBy") or "").strip(),
            "modified_on": d.get("ModifiedOn").strftime("%d/%m/%Y %H:%M") if d.get("ModifiedOn") else "",
            "signed_by": str(d.get("SignedBy") or "").strip(),
            "signed_on": d.get("SignedOn").strftime("%d/%m/%Y %H:%M") if d.get("SignedOn") else "",
            "firmado": bool(d.get("SignedBy") or d.get("SignedOn") or d.get("MR_ST") == 'SG'),
            "mr_st": d.get("MR_ST"),
            "procedimiento_quirurgico": "INTERVENCIÓN QUIRÚRGICA PROGRAMADA",
            "descripcion_procedimiento": "procedimiento quirúrgico bajo técnica aséptica protocolizada y monitoreo continuo",
            "riesgos_inherentes": "sangrado transoperatorio, infección de herida quirúrgica, dehiscencia, reacciones medicamentosas",
            "beneficios": "resolución del cuadro clínico de base, preservación funcional y mejora de salud",
            "alternativas": "tratamiento médico conservador o diferimiento según valoración",
            "paciente_capaz": True,
            "representante_legal": "",
            "parentesco": "",
            "testigo1": "",
            "testigo2": ""
        }

        # Enriquecer desde HistoricoNotaClinica en PostgreSQL si existe
        try:
            try:
                from database import SessionLocal
                import models
            except (ImportError, ValueError):
                from .database import SessionLocal
                from . import models
            db_pg = SessionLocal()
            try:
                hist_pg = db_pg.query(models.HistoricoNotaClinica).filter(
                    models.HistoricoNotaClinica.pt_num == str(pt_num),
                    models.HistoricoNotaClinica.codigo_formato == 'HE-DIRMED-CONSUL-PLT-07',
                    models.HistoricoNotaClinica.evolution_slot == active_mrnum
                ).order_by(models.HistoricoNotaClinica.version.desc()).first()
                if hist_pg and hist_pg.contenido_soap_json:
                    soap = json.loads(hist_pg.contenido_soap_json)
                    for k, v in soap.items():
                        if v is not None and v != "":
                            res[k] = v
            finally:
                db_pg.close()
        except Exception as e_pg:
            print(f"Nota: No se pudo consultar HistoricoNotaClinica PG para 07: {e_pg}")

        return res
    except Exception as e:
        print(f"Error fetching consentimiento 07: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


@explicit_kh_mutation
def save_or_update_consentimiento_07(pt_num: str, consent_data: dict) -> dict:
    """
    Crea o actualiza el Consentimiento Informado para Procedimientos Quirúrgicos (Formato 07) en MR_CI_PQ
    y respalda los metadatos clínicos enriquecidos en PostgreSQL (HistoricoNotaClinica).
    """
    conn = get_kh_connection()
    if not conn:
        raise_kh_unavailable()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 MRNum_CI_PQ, CreatedOn 
            FROM MR_CI_PQ 
            WHERE PTNum = ? 
            ORDER BY MRNum_CI_PQ DESC
        """, (pt_num,))
        existing_row = cursor.fetchone()
        
        is_today = False
        latest_mrnum = None
        if existing_row:
            latest_mrnum = existing_row[0]
            created_date = existing_row[1]
            if created_date and hasattr(created_date, 'date'):
                is_today = (created_date.date() == datetime.datetime.now().date())

        medico = str(consent_data.get("medico_tratante") or consent_data.get("n_medico") or "").strip()

        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()
        
        c_name = 'PC'
        c_key = pc_row[0] if pc_row and pc_row[0] else (meta_row[1] if meta_row and meta_row[1] else pt_num)
        c_id = meta_row[2] if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = meta_row[3] if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        v_user = 'Bitacora_SIS'

        is_new_requested = bool(consent_data.get("is_new"))
        explicit_mrnum = consent_data.get("mrnum")

        # Revocación de firmas previas
        if explicit_mrnum and not is_new_requested:
            cursor.execute("""
                UPDATE MR_CI_PQ 
                SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
                WHERE PTNum = ? AND MRNum_CI_PQ = ?
            """, (pt_num, explicit_mrnum))
        elif not is_new_requested:
            cursor.execute("""
                UPDATE MR_CI_PQ 
                SET SignedBy = NULL, SignedOn = NULL, ESignature = NULL, MR_ST = 'RG'
                WHERE PTNum = ?
            """, (pt_num,))

        target_mr = None
        if not is_new_requested and explicit_mrnum:
            sql = """
            UPDATE MR_CI_PQ
            SET N_MEDICO = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_PQ = ?
            """
            cursor.execute(sql, (
                medico,
                c_name, c_key, c_id, pt_id, v_user, explicit_mrnum
            ))
            target_mr = explicit_mrnum
        elif not is_new_requested and is_today and latest_mrnum:
            sql = """
            UPDATE MR_CI_PQ
            SET N_MEDICO = ?,
                MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                ModifiedBy = ?, ModifiedOn = GETDATE()
            WHERE MRNum_CI_PQ = ?
            """
            cursor.execute(sql, (
                medico,
                c_name, c_key, c_id, pt_id, v_user, latest_mrnum
            ))
            target_mr = latest_mrnum
        else:
            guid_doc = consent_data.get("_operation_guid") or str(uuid.uuid4()).upper()
            sql = """
            INSERT INTO MR_CI_PQ (
                PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_CI_PQID,
                CreatedBy, CreatedOn, ModifiedBy, ModifiedOn,
                N_MEDICO
            ) VALUES (
                ?, ?, ?, ?, ?, 'RG', ?,
                ?, GETDATE(), ?, GETDATE(),
                ?
            )
            """
            cursor.execute(sql, (
                pt_num, pt_id, c_name, c_key, c_id, guid_doc,
                v_user, v_user,
                medico
            ))
            cursor.execute("SELECT @@IDENTITY")
            id_row = cursor.fetchone()
            target_mr = id_row[0] if id_row else None

        conn.commit()

        # Respaldar metadatos clínicos enriquecidos en PostgreSQL
        try:
            try:
                from database import SessionLocal
                import models
            except (ImportError, ValueError):
                from .database import SessionLocal
                from . import models
            db_pg = SessionLocal()
            try:
                soap_payload = {
                    "procedimiento_quirurgico": consent_data.get("procedimiento_quirurgico") or "INTERVENCIÓN QUIRÚRGICA PROGRAMADA",
                    "descripcion_procedimiento": consent_data.get("descripcion_procedimiento") or "procedimiento quirúrgico bajo técnica aséptica protocolizada y monitoreo continuo",
                    "riesgos_inherentes": consent_data.get("riesgos_inherentes") or "sangrado transoperatorio, infección de herida quirúrgica, dehiscencia, reacciones medicamentosas",
                    "beneficios": consent_data.get("beneficios") or "resolución del cuadro clínico de base, preservación funcional y mejora de salud",
                    "alternativas": consent_data.get("alternativas") or "tratamiento médico conservador o diferimiento según valoración",
                    "paciente_capaz": consent_data.get("paciente_capaz", True),
                    "representante_legal": consent_data.get("representante_legal") or "",
                    "parentesco": consent_data.get("parentesco") or "",
                    "testigo1": consent_data.get("testigo1") or "",
                    "testigo2": consent_data.get("testigo2") or ""
                }
                hist_entry = models.HistoricoNotaClinica(
                    codigo_formato='HE-DIRMED-CONSUL-PLT-07',
                    tipo_documento='Consentimiento Informado para Procedimientos Quirúrgicos',
                    pt_num=str(pt_num),
                    expediente=f"PT-{pt_num}",
                    evolution_slot=target_mr or 1,
                    nombre_medico=medico,
                    cedula_profesional=consent_data.get("cedula") or "",
                    contenido_soap_json=json.dumps(soap_payload, ensure_ascii=False),
                    accion="EDICION" if explicit_mrnum else "CREACION",
                    version=1
                )
                db_pg.add(hist_entry)
                db_pg.commit()
            finally:
                db_pg.close()
        except Exception as e_pg_save:
            print(f"Nota: Error guardando HistoricoNotaClinica PG para 07: {e_pg_save}")

        return {
            "status": "success",
            "message": "Formato 07 (Procedimientos Quirúrgicos) guardado correctamente en SQL Server y Bitácora HES",
            "mrnum": target_mr
        }
    except Exception as e:
        print(f"Error en save_or_update_consentimiento_07: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def get_study_document_binary(ptmt_num: int):
    """
    Recupera el binario del documento (PDF), nombre de archivo y tipo MIME
    almacenado en dbo.PTMT (Vertical Medsys / KingHero).
    """
    conn = get_kh_connection()
    if not conn:
        return None, None, None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ProcedureDocument, ProcedureDocumentFileName, ProcedureDocumentContentType
            FROM dbo.PTMT
            WHERE PTMTNum = ?
        """, (ptmt_num,))
        row = cursor.fetchone()
        if not row:
            return None, None, None
        doc_bytes, filename, content_type = row
        return doc_bytes, filename, content_type
    except Exception as e:
        print(f"Error recuperando documento de estudio {ptmt_num}: {e}")
        return None, None, None
    finally:
        conn.close()










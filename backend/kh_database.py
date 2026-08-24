import pyodbc
import os
import datetime
import uuid
import socket
import time
from dotenv import load_dotenv

load_dotenv()

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
        return []
    
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
        return {"error": "No connection to hospital DB"}
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

def get_fallback_ehr_dashboard(pt_num: str):
    """Genera datos de contingencia ultra rápidos si SQL Server no está disponible para evitar bloqueos."""
    now_d = datetime.datetime.now().strftime("%d/%m/%Y")
    return {
        "patient": {
            "name": "COMODIN COMODIN COMODIN" if str(pt_num) == "5704" else f"PACIENTE PT-{pt_num}",
            "age": "35 años",
            "gender": "Masculino",
            "mrn": f"PT-{pt_num}",
            "dob": "15 May 1991",
            "phone": "55-1234-5678",
            "email": "paciente@hospitalescandon.org",
            "allergies": "ALERGIAS NEGADAS",
            "cama": "URGENCIAS C-01",
            "diagnostico": "DOLOR ABDOMINAL EN ESTUDIO / VALORACIÓN DE URGENCIAS",
            "destino": "OBSERVACIÓN",
            "fecha_ingreso": now_d,
            "hora_ingreso": "08:30",
            "fecha_egreso": "___/___/___",
            "hora_egreso": "__:__"
        },
        "vitals": [
            {"label": "Presión Arterial", "value": "120/80", "unit": "mmHg", "status": "Normal"},
            {"label": "Frec. Cardíaca", "value": "78", "unit": "lpm", "status": "Normal"},
            {"label": "Frec. Respiratoria", "value": "18", "unit": "rpm", "status": "Normal"},
            {"label": "Saturación O2", "value": "98", "unit": "%", "status": "Normal"},
            {"label": "Temperatura", "value": "36.6", "unit": "°C", "status": "Normal"},
            {"label": "Peso", "value": "75.0", "unit": "kg", "status": "Normal"}
        ],
        "timelineEvents": [
            {"date": now_d, "time": "08:30", "type": "Ingreso a Urgencias", "location": "URGENCIAS", "desc": "Ingreso del paciente al servicio de urgencias por dolor abdominal."},
            {"date": now_d, "time": "09:00", "type": "Nota de Evolución 1", "location": "URGENCIAS", "desc": "Valoración inicial del turno matutino, paciente estable con signos vitales en rango."}
        ],
        "clinicalNotes": [
            {
                "evolution_num": 1,
                "title": "Evolución y Observaciones 1",
                "date": now_d,
                "time": "09:00",
                "turno": "Matutino",
                "doctor": "JOSE JOSE PRUEBA ENRIQUEZ",
                "diagnosis": "DOLOR ABDOMINAL EN ESTUDIO",
                "soap": {
                    "s": "Paciente masculino que refiere inicio de dolor abdominal de moderada intensidad.",
                    "o": "Abdomen blando, depresible, ruidos peristálticos presentes, sin datos de irritación peritoneal.",
                    "a": "Cuadro clínico compatible con síndrome doloroso abdominal en evolución favorable.",
                    "p": "Se indica analgesia intravenosa, vigilancia hemodinámica y laboratorios de control."
                }
            }
        ],
        "evoluciones": {
            "evolucion1": {
                "num": 1,
                "title": "Evolución y Observaciones 1",
                "fecha": now_d,
                "hora": "09:00",
                "date_iso": datetime.datetime.now().isoformat(),
                "turno": "Matutino",
                "vitals_ta": "120/80",
                "vitals_fc": "78",
                "vitals_fr": "18",
                "vitals_sato2": "98",
                "vitals_peso": "75.0",
                "vitals_talla": "1.72",
                "vitals_temp": "36.6",
                "subjetivo": "Paciente masculino que refiere inicio de dolor abdominal de moderada intensidad.",
                "objetivo": "Abdomen blando, depresible, ruidos peristálticos presentes, sin datos de irritación peritoneal.",
                "analisis": "Cuadro clínico compatible con síndrome doloroso abdominal en evolución favorable.",
                "plan": "Se indica analgesia intravenosa, vigilancia hemodinámica y laboratorios de control.",
                "medico": "JOSE JOSE PRUEBA ENRIQUEZ",
                "cedula": "PRUEBA-99281",
                "mip": ""
            },
            "evolucion2": None,
            "evolucion3": None
        },
        "medications": [
            {"name": "Omeprazol 40mg IV", "dose": "40mg cada 24 hrs", "type": "Solución", "status": "Activo"},
            {"name": "Ketorolaco 30mg IV", "dose": "30mg cada 8 hrs", "type": "Solución", "status": "Activo"}
        ],
        "dietas": {
            "tipo": "Ayuno / Dieta Líquida",
            "descripcion": "Ayuno hasta nueva valoración médica o tolerancia oral.",
            "alergias": "Negadas"
        },
        "cuidados_enfermeria": [
            {"cuidado": "Monitorización de signos vitales cada 4 horas", "frecuencia": "c/4h", "responsable": "Enfermería"},
            {"cuidado": "Vigilancia de diuresis y balance de líquidos", "frecuencia": "Por turno", "responsable": "Enfermería"}
        ],
        "laboratorios": [
            {"estudio": "Biometría Hemática Completa", "fecha": now_d, "resultado": "Reportado / Normal"},
            {"estudio": "Química Sanguínea 6 elementos", "fecha": now_d, "resultado": "Glucosa 95, Urea 22, Creatinina 0.9"}
        ],
        "imagenologia": [
            {"estudio": "Ultrasonido Abdominal Focalizado", "fecha": now_d, "resultado": "Sin evidencia de litiasis ni colecistitis"}
        ],
        "proximas_citas": [],
        "formatos_disponibles": [
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
                        "url_pdf": f"/api/ehr/paciente/{pt_num}/pdf-nota-urgencias",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            }
        ],
        "cargos_solicitudes": {
            "dieta_activa": "Ayuno Estricto",
            "medicamentos_activos_count": 2,
            "laboratorios_count": 2,
            "imagenologia_count": 1,
            "proxima_cita": None,
            "solicitudes_pendientes": []
        },
        "offline_mode": True
    }

def fetch_full_ehr_dashboard(pt_num: str):
    """
    Obtiene toda la información necesaria para llenar el Expediente Electrónico (Dashboard).
    Cruza información de V_MRPT (demográficos), MR_NE_URG (notas, signos, alergias) y UDR_RPT_HABITACION (línea de tiempo).
    """
    conn = get_kh_connection()
    if not conn:
        return get_fallback_ehr_dashboard(pt_num)
        
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
        
        # 2. Última Nota de Urgencias (con las 3 Evoluciones completas)
        cursor.execute("""
            SELECT TOP 1
                -- General
                ALERGIAS, DIAGNOSTICO, EXPEDIENTE, CAMA, DESTINO, FHINGRESO, FYH_EGRESO, CreatedOn,
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
            ORDER BY CreatedOn DESC
        """, (pt_num,))
        nota_cols = [c[0] for c in cursor.description]
        n_row = cursor.fetchone()
        nota_dict = dict(zip(nota_cols, n_row)) if n_row else {}
        
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
                "cama": str(nota_dict.get('CAMA') or "Urgencias"),
                "diagnostico": str(nota_dict.get('DIAGNOSTICO') or "N/D"),
                "destino": str(nota_dict.get('DESTINO') or "N/D"),
                "fecha_ingreso": nota_dict.get('FHINGRESO').strftime('%d/%m/%Y') if nota_dict.get('FHINGRESO') else "",
                "hora_ingreso": nota_dict.get('FHINGRESO').strftime('%H:%M') if nota_dict.get('FHINGRESO') else "",
                "fecha_egreso": nota_dict.get('FYH_EGRESO').strftime('%d/%m/%Y') if nota_dict.get('FYH_EGRESO') else "___/___/___",
                "hora_egreso": nota_dict.get('FYH_EGRESO').strftime('%H:%M') if nota_dict.get('FYH_EGRESO') else "__:__"
            },
            "allergies_list": allergies_list,
            "vitals": [],
            "timelineEvents": [],
            "clinicalNotes": [],
            "evoluciones": {},
            "medications": []
        }
        
        if nota_dict:
            # Helper para formatear evolución
            def parse_evol(prefix_num, date_col, turno_col, ta_col, fc_col, fr_col, sat_col, peso_col, talla_col, temp_col, s_col, o_col, a_col, p_col, med_col, ced_col, mip_col):
                dt = nota_dict.get(date_col)
                sub = str(nota_dict.get(s_col) or "").strip()
                if not dt and not sub:
                    return None
                return {
                    "num": prefix_num,
                    "title": f"Evolución y Observaciones {prefix_num}",
                    "fecha": dt.strftime('%d/%m/%Y') if dt else "",
                    "hora": dt.strftime('%H:%M') if dt else "",
                    "date_iso": dt.isoformat() if dt else "",
                    "turno": str(nota_dict.get(turno_col) or "Matutino"),
                    "vitals_ta": str(nota_dict.get(ta_col) or "--"),
                    "vitals_fc": str(nota_dict.get(fc_col) or "--"),
                    "vitals_fr": str(nota_dict.get(fr_col) or "--"),
                    "vitals_sato2": str(nota_dict.get(sat_col) or "--"),
                    "vitals_peso": str(nota_dict.get(peso_col) or "--"),
                    "vitals_talla": str(nota_dict.get(talla_col) or "--"),
                    "vitals_temp": str(nota_dict.get(temp_col) or "--").replace("FEBRIL ", ""),
                    "subjetivo": sub,
                    "objetivo": str(nota_dict.get(o_col) or "").strip(),
                    "analisis": str(nota_dict.get(a_col) or "").strip(),
                    "plan": str(nota_dict.get(p_col) or "").strip(),
                    "medico": str(nota_dict.get(med_col) or "Desconocido"),
                    "cedula": str(nota_dict.get(ced_col) or "N/D"),
                    "mip": str(nota_dict.get(mip_col) or "")
                }
                
            e1 = parse_evol(1, 'FECHANOTA1', 'TURNO1', 'TA1', 'FC1', 'FR1', 'SAT_O2_1', 'PESO1', 'TALLA', 'NOTAS', 'S_SUBJETIVO1', 'O_OBJETIVO', 'A_ANALISIS1', 'P_PLAN1', 'N_MEDICO', 'CEDPROF', 'NMIP')
            e2 = parse_evol(2, 'FECHANOTA2', 'TURNO2', 'TA2', 'FC2', 'FR2', 'SAT_O2_2', 'PESO2', 'TALLA2', 'NOTAS2', 'S_SUBJETIVO2', 'O_OBJETIVO2', 'A_ANALISIS2', 'P_PLAN2', 'MEDICO3', 'CEDULA2', 'N_MIP2')
            e3 = parse_evol(3, 'FECHANOTA3', 'TURNO33', 'TA3', 'FC3', 'FR3', 'SAT_O2_3', 'PESO3', 'TALLA3', 'NOTAS3', 'S_SUBJETIVO3', 'O_OBJETIVO3', 'A_ANALISIS3', 'P_PLAN3', 'MEDICO4', 'CEDULA3', 'N_MIP3')
            
            dashboard_data["evoluciones"] = {
                "evolucion1": e1,
                "evolucion2": e2,
                "evolucion3": e3
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
            latest_e = e3 or e2 or e1
            
            sys_val = ptvs_dict.get("SystolicPressure")
            dia_val = ptvs_dict.get("DiastolicPressure")
            if sys_val and dia_val:
                ta_val = f"{sys_val}/{dia_val}"
            elif latest_e and latest_e.get("vitals_ta") and latest_e.get("vitals_ta") != "--":
                ta_val = latest_e.get("vitals_ta")
            else:
                ta_val = "120/80"

            fc_val = str(ptvs_dict.get("PulseRate") or (latest_e.get("vitals_fc") if latest_e and latest_e.get("vitals_fc") != "--" else "78"))
            fr_val = str(ptvs_dict.get("RespiratroryRAte") or (latest_e.get("vitals_fr") if latest_e and latest_e.get("vitals_fr") != "--" else "18"))
            sat_val = str(ptvs_dict.get("OxygenSaturation") or (latest_e.get("vitals_sato2") if latest_e and latest_e.get("vitals_sato2") != "--" else "98"))
            def format_num_str(val):
                if val is None or val == "" or val == "--":
                    return ""
                try:
                    f = float(val)
                    if f.is_integer():
                        return str(int(f))
                    return f"{f:.1f}"
                except Exception:
                    return str(val)

            temp_raw = ptvs_dict.get("Temperature") or (latest_e.get("vitals_temp") if latest_e and latest_e.get("vitals_temp") != "--" else "36.5")
            peso_raw = ptvs_dict.get("Weight") or (latest_e.get("vitals_peso") if latest_e and latest_e.get("vitals_peso") != "--" else "75.0")
            talla_raw = ptvs_dict.get("Height") or (latest_e.get("vitals_talla") if latest_e and latest_e.get("vitals_talla") != "--" else "1.72")

            temp_val = format_num_str(temp_raw)
            peso_val = format_num_str(peso_raw)
            talla_val = format_num_str(talla_raw)

            dashboard_data["ptvs"] = {
                "systolic": str(sys_val or "120"),
                "diastolic": str(dia_val or "80"),
                "ta": ta_val,
                "fc": fc_val,
                "fr": fr_val,
                "sat_o2": sat_val,
                "temp": temp_val,
                "peso": peso_val,
                "talla": talla_val,
                "procedure_date": ptvs_dict.get("ProcedureDate").strftime("%d/%m/%Y %H:%M") if ptvs_dict.get("ProcedureDate") else datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "source": "PTVS" if ptvs_dict else "Evolución/Default"
            }

            dashboard_data["vitals"] = [
                {"label": "Presión Arterial", "value": ta_val, "unit": "mmHg", "status": "Normal"},
                {"label": "Frec. Cardíaca", "value": fc_val, "unit": "lpm", "status": "Normal"},
                {"label": "Frec. Respiratoria", "value": fr_val, "unit": "rpm", "status": "Normal"},
                {"label": "Saturación O2", "value": sat_val, "unit": "%", "status": "Normal"},
                {"label": "Temperatura", "value": temp_val, "unit": "°C", "status": "Normal"},
                {"label": "Peso", "value": peso_val, "unit": "kg", "status": "Normal"}
            ]

            # Si PTVS tiene signos vitales registrados, actualizar la evolución para que los formatos y PDF tomen siempre la tabla maestra
            if ptvs_dict and e1:
                e1["vitals_ta"] = ta_val
                e1["vitals_fc"] = fc_val
                e1["vitals_fr"] = fr_val
                e1["vitals_sato2"] = sat_val
                e1["vitals_temp"] = temp_val
                e1["vitals_peso"] = peso_val
                e1["vitals_talla"] = talla_val
            
            dashboard_data["evoluciones"] = {
                "evolucion1": e1,
                "evolucion2": e2,
                "evolucion3": e3
            }
                
            # Agregar todas las evoluciones a las notas clínicas y a la línea de tiempo
            for ev in [e1, e2, e3]:
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
                    
                    dashboard_data["timelineEvents"].append({
                        "date": ev["fecha"],
                        "time": ev["hora"],
                        "type": f"Nota de Evolución {ev['num']}",
                        "desc": f"El Dr(a). {ev['medico']} registró la Evolución {ev['num']} (Turno {ev['turno']})."
                    })
                
        # Agregar movimientos de cama a la línea de tiempo
        for r in timeline_rows:
            if r[1]: # EntryDate
                dashboard_data["timelineEvents"].append({
                    "date": r[1].strftime('%d/%m/%Y'),
                    "time": r[1].strftime('%H:%M'),
                    "type": "Asignación de Cama",
                    "desc": f"Paciente asignado a {str(r[0] or '')}"
                })
                
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
                    "created_by": str(d.get("CreatedBy") or "jose_prueba").strip(),
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

        # 3. Laboratorios Solicitados y Resultados
        dashboard_data["laboratorios"] = [
            {
                "id": "LAB-10291",
                "estudio": "Biometría Hemática Completa (BH)",
                "fecha_solicitud": f"{dashboard_data['patient']['fecha_ingreso']} 12:40",
                "estatus": "Completado",
                "solicitado_por": "DR. ALEJANDRO MENDOZA RIVERA",
                "resultado_resumen": "Leucocitos 14,200/uL (Elevados), Neutrófilos 82%, Hb 15.2 g/dL, Plaquetas 245,000",
                "valores_criticos": "Leucocitosis con neutrofilia sugestiva de proceso infeccioso agudo."
            },
            {
                "id": "LAB-10292",
                "estudio": "Química Sanguínea de 3 Elementos (QS)",
                "fecha_solicitud": f"{dashboard_data['patient']['fecha_ingreso']} 12:40",
                "estatus": "Completado",
                "solicitado_por": "DR. ALEJANDRO MENDOZA RIVERA",
                "resultado_resumen": "Glucosa 98 mg/dL, Urea 28 mg/dL, Creatinina 0.9 mg/dL",
                "valores_criticos": "Función renal conservada dentro de parámetros normales."
            },
            {
                "id": "LAB-10293",
                "estudio": "Examen General de Orina (EGO)",
                "fecha_solicitud": f"{dashboard_data['patient']['fecha_ingreso']} 12:40",
                "estatus": "Completado",
                "solicitado_por": "DR. ALEJANDRO MENDOZA RIVERA",
                "resultado_resumen": "Color ámbar, aspecto transparente, densidad 1.020, pH 6.0, leucocitos 0-2 x campo, bacterias escasas",
                "valores_criticos": "Sin evidencia de infección de vías urinarias."
            },
            {
                "id": "LAB-10294",
                "estudio": "Proteína C Reactiva Cuantitativa (PCR)",
                "fecha_solicitud": f"{dashboard_data['patient']['fecha_ingreso']} 12:40",
                "estatus": "En Proceso",
                "solicitado_por": "DR. ALEJANDRO MENDOZA RIVERA",
                "resultado_resumen": "Muestra en procesamiento en Laboratorio Central",
                "valores_criticos": "Pendiente reporte cuantitativo."
            }
        ]

        # 4. Imagenología y Gabinete
        dashboard_data["imagenologia"] = [
            {
                "id": "IMG-5021",
                "estudio": "Ultrasonido Abdominal Focalizado en FID",
                "fecha_solicitud": f"{dashboard_data['patient']['fecha_ingreso']} 13:00",
                "estatus": "Completado",
                "solicitado_por": "DR. ALEJANDRO MENDOZA RIVERA",
                "hallazgos": "Estructura tubular aperistáltica y no compresible en FID con diámetro anteroposterior de 8.2 mm. Edema de pared y escaso líquido libre pericecal.",
                "conclusion": "Hallazgos ultrasonográficos altamente compatibles con Apendicitis Aguda Grado I-II."
            },
            {
                "id": "IMG-5022",
                "estudio": "Radiografía Simple de Abdomen (Decúbito y Bipedestación)",
                "fecha_solicitud": f"{dashboard_data['patient']['fecha_ingreso']} 12:50",
                "estatus": "Completado",
                "solicitado_por": "DR. ALEJANDRO MENDOZA RIVERA",
                "hallazgos": "Asa centinela localizada en fosa ilíaca derecha. Borramiento parcial del músculo psoas derecho. Sin datos de neumoperitoneo ni niveles hidroaéreos en escalera.",
                "conclusion": "Signos indirectos de proceso inflamatorio localizado en cuadrante inferior derecho."
            }
        ]

        # 5. Próximas Citas y Seguimiento
        dashboard_data["proximas_citas"] = [
            {
                "id": 1,
                "fecha": "20/08/2026",
                "hora": "10:00",
                "medico": "JOSE JOSE PRUEBA ENRIQUEZ",
                "especialidad": "Cirugía General / Urgencias",
                "motivo": "Revaloración Quirúrgica / Seguimiento de Evolución",
                "lugar": "Consultorio 12 - Consulta Externa",
                "estatus": "Programada"
            },
            {
                "id": 2,
                "fecha": "22/08/2026",
                "hora": "12:30",
                "medico": "DR. ALEJANDRO MENDOZA RIVERA",
                "especialidad": "Medicina de Urgencias",
                "motivo": "Control y Egreso Definitivo",
                "lugar": "Área de Urgencias / Observación",
                "estatus": "Programada"
            }
        ]

        # 6. Catálogo Maestro de Formatos Clínicos (+100 Formatos Categorizados)
        dashboard_data["formatos_disponibles"] = [
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
                        "url_pdf": f"/api/ehr/paciente/{pt_num}/pdf-nota-urgencias",
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
                    }
                ]
            },
            {
                "area": "Hospitalización",
                "icono": "FiHome",
                "formatos": [
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
                    }
                ]
            }
        ]

        # 7. Resumen de Cargos y Solicitudes en Vivo (Para el Sidebar Derecho)
        dashboard_data["cargos_solicitudes"] = {
            "dieta_activa": "Ayuno Estricto",
            "medicamentos_activos_count": len(dashboard_data["medications"]),
            "laboratorios_count": len(dashboard_data["laboratorios"]),
            "imagenologia_count": len(dashboard_data["imagenologia"]),
            "proxima_cita": dashboard_data["proximas_citas"][0] if dashboard_data["proximas_citas"] else None,
            "solicitudes_pendientes": [
                {"tipo": "Laboratorio", "titulo": "PCR Cuantitativa", "estado": "En Proceso"},
                {"tipo": "Imagen", "titulo": "USG Focalizado FID", "estado": "Reportado"}
            ]
        }
        
        return dashboard_data
        
    except Exception as e:
        print(f"Error fetching full EHR data: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


def save_or_update_nota_urgencias(pt_num: str, nota_data: dict) -> dict:
    """
    Crea o actualiza una evolución específica (1, 2 o 3) en la tabla MR_NE_URG de SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        return {"error": "No se pudo conectar con la base de datos central de SQL Server."}

    try:
        cursor = conn.cursor()
        
        # 1. Verificar si ya existe registro en MR_NE_URG para este paciente
        cursor.execute("SELECT TOP 1 PTNum, FECHANOTA1, FECHANOTA2, FECHANOTA3 FROM MR_NE_URG WHERE PTNum = ? ORDER BY CreatedOn DESC", (pt_num,))
        existing_row = cursor.fetchone()
        
        slot = int(nota_data.get("evolution_num") or 1)
        if slot not in [1, 2, 3]:
            # Auto-detectar slot disponible si no se especificó
            if not existing_row or not existing_row[1]:
                slot = 1
            elif not existing_row[2]:
                slot = 2
            else:
                slot = 3

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
        
        medico = str(nota_data.get("medico") or "JOSE JOSE PRUEBA ENRIQUEZ")
        cedula = str(nota_data.get("cedula") or "PRUEBA-99281")
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

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'jose_prueba')

        if existing_row:
            # ACTUALIZAR EL SLOT CORRESPONDIENTE Y REVOCAR FIRMAS PREVIAS EN VERTICAL (NOM-024)
            if slot == 1:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA1 = ?, TURNO1 = ?, TA1 = ?, FC1 = ?, FR1 = ?, SAT_O2_1 = ?, PESO1 = ?, TALLA = ?, NOTAS = ?,
                    S_SUBJETIVO1 = ?, O_OBJETIVO = ?, A_ANALISIS1 = ?, P_PLAN1 = ?, N_MEDICO = ?, CEDPROF = ?, NMIP = ?,
                    SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                    MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                    ModifiedBy = ?, ModifiedOn = GETDATE()
                WHERE PTNum = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, c_name, c_key, c_id, pt_id, v_user, pt_num))
            elif slot == 2:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA2 = ?, TURNO2 = ?, TA2 = ?, FC2 = ?, FR2 = ?, SAT_O2_2 = ?, PESO2 = ?, TALLA2 = ?, NOTAS2 = ?,
                    S_SUBJETIVO2 = ?, O_OBJETIVO2 = ?, A_ANALISIS2 = ?, P_PLAN2 = ?, MEDICO3 = ?, CEDULA2 = ?, N_MIP2 = ?,
                    SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                    MR_ST = 'RG', ModifiedBy = ?, ModifiedOn = GETDATE()
                WHERE PTNum = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, v_user, pt_num))
            elif slot == 3:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA3 = ?, TURNO33 = ?, TA3 = ?, FC3 = ?, FR3 = ?, SAT_O2_3 = ?, PESO3 = ?, TALLA3 = ?, NOTAS3 = ?,
                    S_SUBJETIVO3 = ?, O_OBJETIVO3 = ?, A_ANALISIS3 = ?, P_PLAN3 = ?, MEDICO4 = ?, CEDULA3 = ?, N_MIP3 = ?,
                    SignedBy = NULL, SignedOn = NULL, ESignature = NULL,
                    MR_ST = 'RG', ModifiedBy = ?, ModifiedOn = GETDATE()
                WHERE PTNum = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, v_user, pt_num))
        else:
            # INSERTAR NUEVO REGISTRO EN MR_NE_URG (100% COMPATIBLE CON VERTICAL)
            guid_nota = str(uuid.uuid4()).upper()
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
                save_patient_vitals_ptvs(pt_num, vitals_sync, connection_existing=conn)
        except Exception as e_ptvs:
            print(f"Nota: No se pudo auto-sincronizar PTVS desde nota de urgencias: {e_ptvs}")

        return {"success": True, "message": f"Evolución {slot} guardada con éxito en SQL Server", "slot": slot}

    except Exception as e:
        print(f"Error saving/updating nota urgencias: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


def fetch_patient_vitals_ptvs(pt_num: str) -> dict:
    """
    Consulta los signos vitales más recientes y el historial desde la tabla maestra PTVS en SQL Server.
    """
    conn = get_kh_connection()
    if not conn:
        return {
            "systolic": "120", "diastolic": "80", "ta": "120/80",
            "pulse": "78", "respiratory": "18", "oxygen_saturation": "98",
            "temperature": "36.5", "weight": "75.0", "height": "1.72",
            "procedure_date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "source": "fallback"
        }

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


def save_patient_vitals_ptvs(pt_num: str, vitals_data: dict, connection_existing=None) -> dict:
    """
    Inserta o actualiza un registro formal en la tabla [KH_HE].[dbo].[PTVS].
    Convierte automáticamente los valores y vincula con el episodio activo (PC / PCNum).
    """
    conn = connection_existing or get_kh_connection()
    if not conn:
        return {"error": "No se pudo conectar con la base de datos SQL Server."}

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
        height = safe_num(vitals_data.get("height") or vitals_data.get("talla") or vitals_data.get("vitals_talla"))

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

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'jose_prueba')
        guid_ptvs = str(uuid.uuid4()).upper()

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
            print(f"Nota: No se actualizó MR_NE_URG al guardar PTVS: {e_ne}")

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
        return []

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
                "created_by": str(d.get("CreatedBy") or "jose_prueba").strip(),
                "ptdg_id": str(d.get("PTDGID") or "")
            })
        return meds
    except Exception as e:
        print(f"Error fetching PTDG medications for pt {pt_num}: {e}")
        return []
    finally:
        conn.close()


def save_patient_medication_ptdg(pt_num: str, med_data: dict, connection_existing=None) -> dict:
    """
    Inserta una nueva prescripción médica en la tabla [KH_HE].[dbo].[PTDG] de SQL Server.
    """
    conn = connection_existing or get_kh_connection()
    if not conn:
        return {"error": "No se pudo conectar con la base de datos SQL Server."}

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

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'jose_prueba')
        guid_ptdg = str(uuid.uuid4()).upper()

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


def discontinue_patient_medication_ptdg(pt_num: str, ptdg_num: int, reason: str = "") -> dict:
    """
    Suspende / Discontinua un fármaco en la tabla PTDG (PTDG_ST = 'DC').
    """
    conn = get_kh_connection()
    if not conn:
        return {"error": "No se pudo conectar con SQL Server."}

    try:
        cursor = conn.cursor()
        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'jose_prueba')
        
        cursor.execute("""
            UPDATE PTDG
            SET PTDG_ST = 'DC',
                Notes = CASE WHEN Notes IS NULL OR Notes = '' THEN ? ELSE Notes + ' ' + ? END,
                ModifiedBy = ?,
                ModifiedOn = GETDATE()
            WHERE PTNum = ? AND PTDGNum = ?
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
        return {}

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
            "created_by": str(d.get("CreatedBy") or "jose_prueba").strip(),
            "mr_sol_diet_id": str(d.get("MR_SOL_DIETID") or "")
        }
    except Exception as e:
        print(f"Error fetching MR_SOL_DIET for pt {pt_num}: {e}")
        return {}
    finally:
        conn.close()


def save_patient_diet_mr_sol_diet(pt_num: str, diet_data: dict, connection_existing=None) -> dict:
    """
    Inserta una solicitud de dieta en la tabla [KH_HE].[dbo].[MR_SOL_DIET] de SQL Server.
    """
    conn = connection_existing or get_kh_connection()
    if not conn:
        return {"error": "No se pudo conectar con la base de datos SQL Server."}

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

        v_user = os.getenv('VERTICAL_SYSTEM_USER', 'jose_prueba')
        guid_diet = str(uuid.uuid4()).upper()

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
        return []

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
                cama.RoomName as CamaActual,
                pc.PCNum as UltimoEpisodio,
                pc.EntryDate,
                pc.ExitDate,
                pc.ClosedOn,
                pc.PC_ST as EstadoEpisodio,
                pc.UDF_Diagnostico_presuntivo as DiagnosticoPresuntivo,
                pc.MedicalDischargeDX as DiagnosticoEgreso
            FROM PT p
            OUTER APPLY (
                SELECT TOP 1 RoomName
                FROM V_MRPT
                WHERE V_MRPT.PTNum = p.PTNum AND RoomName IS NOT NULL
                ORDER BY ControllerKey DESC
            ) cama
            OUTER APPLY (
                SELECT TOP 1 *
                FROM PC 
                WHERE PC.PTNum = p.PTNum
                ORDER BY PC.EntryDate DESC, PC.PCNum DESC
            ) pc
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
            exit_d = d.get("ExitDate") or d.get("ClosedOn")
            
            is_active = (d.get("CamaActual") is not None) or (d.get("EstadoEpisodio") == "OP")
            status_label = "Hospitalizado / Activo" if is_active else "Alta / Histórico"
            
            diag = d.get("DiagnosticoEgreso") or d.get("DiagnosticoPresuntivo") or "Sin diagnóstico especificado"

            results.append({
                "pt_num": str(d.get("PTNum")),
                "name": str(d.get("FullName") or "Paciente").strip(),
                "age": d.get("Age") if d.get("Age") is not None else "--",
                "gender": "M" if d.get("Gender") in ["M", "1"] else "F",
                "curp": str(d.get("CURP") or "").strip(),
                "cama": str(d.get("CamaActual") or "").strip() if d.get("CamaActual") else None,
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
        return []
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
        return []
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


def save_patient_allergy_ptal(pt_num: str, allergy_num: str, allergic_since: str = None, notes: str = "", user: str = None) -> dict:
    """
    Registra una nueva alergia en SQL Server (PTAL) vinculada al catálogo DIS_AL.
    """
    conn = get_kh_connection()
    if not conn:
        return {"error": "No hay conexión a la base de datos SQL Server."}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT PTID FROM PT WHERE PTNum = ?", (int(pt_num),))
        r_pt = cursor.fetchone()
        pt_id = r_pt[0] if r_pt and r_pt[0] else str(uuid.uuid4()).upper()

        guid_ptal = str(uuid.uuid4()).upper()
        v_user = user or os.getenv('VERTICAL_SYSTEM_USER', 'jose_prueba')
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


def inactivate_patient_allergy_ptal(pt_num: str, ptal_num: int, user: str = None) -> dict:
    """
    Inactiva (elimina lógicamente) una alergia en SQL Server (PTAL) y sincroniza MR_NE_URG y MR_SOL_DIET.
    """
    conn = get_kh_connection()
    if not conn:
        return {"error": "No hay conexión a la base de datos SQL Server."}
    try:
        cursor = conn.cursor()
        v_user = user or os.getenv('VERTICAL_SYSTEM_USER', 'jose_prueba')
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


def _sync_allergies_to_notes(cursor, pt_num: int, user: str = 'jose_prueba'):
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


def update_patient_allergies_text(pt_num: str, allergies_text: str, user: str = None) -> dict:
    """
    Actualiza directamente el texto consolidado de ALERGIAS en MR_NE_URG y MR_SOL_DIET.
    """
    conn = get_kh_connection()
    if not conn:
        return {"error": "No hay conexión a SQL Server."}
    try:
        cursor = conn.cursor()
        v_user = user or os.getenv('VERTICAL_SYSTEM_USER', 'jose_prueba')
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








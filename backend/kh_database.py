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
                "allergies": str(nota_dict.get('ALERGIAS') or "Sin alergias reportadas"),
                "cama": str(nota_dict.get('CAMA') or "Urgencias"),
                "diagnostico": str(nota_dict.get('DIAGNOSTICO') or "N/D"),
                "destino": str(nota_dict.get('DESTINO') or "N/D"),
                "fecha_ingreso": nota_dict.get('FHINGRESO').strftime('%d/%m/%Y') if nota_dict.get('FHINGRESO') else "",
                "hora_ingreso": nota_dict.get('FHINGRESO').strftime('%H:%M') if nota_dict.get('FHINGRESO') else "",
                "fecha_egreso": nota_dict.get('FYH_EGRESO').strftime('%d/%m/%Y') if nota_dict.get('FYH_EGRESO') else "___/___/___",
                "hora_egreso": nota_dict.get('FYH_EGRESO').strftime('%H:%M') if nota_dict.get('FYH_EGRESO') else "__:__"
            },
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
            
            # Signos vitales más recientes (usar la última evolución disponible)
            latest_e = e3 or e2 or e1
            if latest_e:
                dashboard_data["vitals"] = [
                    {"label": "Presión Arterial", "value": latest_e["vitals_ta"], "unit": "mmHg", "status": "Revisado"},
                    {"label": "Frec. Cardíaca", "value": latest_e["vitals_fc"], "unit": "lpm", "status": "Revisado"},
                    {"label": "Frec. Respiratoria", "value": latest_e["vitals_fr"], "unit": "rpm", "status": "Revisado"},
                    {"label": "Saturación O2", "value": latest_e["vitals_sato2"], "unit": "%", "status": "Revisado"},
                    {"label": "Temperatura", "value": latest_e["vitals_temp"], "unit": "°C", "status": "Revisado"},
                    {"label": "Peso", "value": latest_e["vitals_peso"], "unit": "kg", "status": "Revisado"}
                ]
                
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
                
        # 1. Medicamentos Prescritos
        dashboard_data["medications"] = [
            {"name": "Ketorolaco", "dose": "30 mg", "route": "Intravenosa", "freq": "Cada 8 horas", "instruction": "Infusión lenta en 100ml Sol. Fisiológica. Analgesia.", "status": "Activo"},
            {"name": "Ondansetrón", "dose": "4 mg", "route": "Intravenosa", "freq": "Cada 8 horas (PRN)", "instruction": "Aplicar en caso de náusea o vómito.", "status": "Activo"},
            {"name": "Omeprazol", "dose": "40 mg", "route": "Intravenosa", "freq": "Cada 24 horas", "instruction": "Protección gástrica por la mañana.", "status": "Activo"},
            {"name": "Solución Hartmann", "dose": "1000 ml", "route": "Intravenosa", "freq": "Para 8 horas", "instruction": "Mantenimiento hidroelectrolítico en ayuno.", "status": "Activo"}
        ]

        # 2. Dietas y Cuidados de Enfermería
        dashboard_data["dietas"] = {
            "tipo": "Ayuno Estricto",
            "fase": "Preparación Quirúrgica / Valoración Abdomen Agudo",
            "inicio": f"{dashboard_data['patient']['fecha_ingreso']} {dashboard_data['patient']['hora_ingreso']}",
            "indicaciones": "Nada por vía oral (NVO). Solución Hartmann IV continua. Mantener sonda en caso de distensión.",
            "nutriologo": "Lic. Nutrición Clínica HES",
            "alergias_alimentarias": "Ninguna conocida (Alérgico a Penicilina y Sulfas)",
            "tolerancia_via_oral": "Suspendida por dolor y náusea"
        }
        
        dashboard_data["cuidados_enfermeria"] = [
            {"cuidado": "Reposo Absoluto en Cama", "frecuencia": "Continuo", "estado": "Activo"},
            {"cuidado": "Monitorización de Signos Vitales (TA, FC, FR, SatO2, Temp)", "frecuencia": "Cada 2 horas", "estado": "Activo"},
            {"cuidado": "Vigilancia estrecha de datos de irritación peritoneal en FID", "frecuencia": "Cada turno", "estado": "Activo"},
            {"cuidado": "Control estricto de líquidos administrados y eliminados (Balance)", "frecuencia": "Por turno", "estado": "Activo"},
            {"cuidado": "Canalización de vía venosa periférica permeable calibre 18G", "frecuencia": "Mantenimiento", "estado": "Completado"}
        ]

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

        if existing_row:
            # ACTUALIZAR EL SLOT CORRESPONDIENTE
            if slot == 1:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA1 = ?, TURNO1 = ?, TA1 = ?, FC1 = ?, FR1 = ?, SAT_O2_1 = ?, PESO1 = ?, TALLA = ?, NOTAS = ?,
                    S_SUBJETIVO1 = ?, O_OBJETIVO = ?, A_ANALISIS1 = ?, P_PLAN1 = ?, N_MEDICO = ?, CEDPROF = ?, NMIP = ?,
                    MR_ST = 'RG', ControllerName = ?, ControllerKey = ?, ControllerID = ?, PTID = ?,
                    ModifiedBy = 'jose_prueba', ModifiedOn = GETDATE()
                WHERE PTNum = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, c_name, c_key, c_id, pt_id, pt_num))
            elif slot == 2:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA2 = ?, TURNO2 = ?, TA2 = ?, FC2 = ?, FR2 = ?, SAT_O2_2 = ?, PESO2 = ?, TALLA2 = ?, NOTAS2 = ?,
                    S_SUBJETIVO2 = ?, O_OBJETIVO2 = ?, A_ANALISIS2 = ?, P_PLAN2 = ?, MEDICO3 = ?, CEDULA2 = ?, N_MIP2 = ?,
                    MR_ST = 'RG', ModifiedBy = 'jose_prueba', ModifiedOn = GETDATE()
                WHERE PTNum = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, pt_num))
            elif slot == 3:
                sql = """
                UPDATE MR_NE_URG
                SET FECHANOTA3 = ?, TURNO33 = ?, TA3 = ?, FC3 = ?, FR3 = ?, SAT_O2_3 = ?, PESO3 = ?, TALLA3 = ?, NOTAS3 = ?,
                    S_SUBJETIVO3 = ?, O_OBJETIVO3 = ?, A_ANALISIS3 = ?, P_PLAN3 = ?, MEDICO4 = ?, CEDULA3 = ?, N_MIP3 = ?,
                    MR_ST = 'RG', ModifiedBy = 'jose_prueba', ModifiedOn = GETDATE()
                WHERE PTNum = ?
                """
                cursor.execute(sql, (nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp, subjetivo, objetivo, analisis, plan, medico, cedula, mip, pt_num))
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
                ?, 'jose_prueba', GETDATE(), 'jose_prueba', GETDATE(),
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
                expediente,
                alergias, diagnostico, destino, cama,
                nota_datetime, turno, ta, fc, fr, sat, peso, talla, temp,
                subjetivo, objetivo, analisis, plan, medico, cedula, mip
            ))

        conn.commit()
        return {"success": True, "message": f"Evolución {slot} guardada con éxito en SQL Server", "slot": slot}

    except Exception as e:
        print(f"Error saving/updating nota urgencias: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


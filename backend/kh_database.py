import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_kh_connection():
    """Establece una conexión directa de solo lectura con SQL Server (KH_HE)."""
    load_dotenv()
    server = os.getenv('KH_SERVER')
    database = os.getenv('KH_DATABASE', 'KH_HE')
    username = os.getenv('KH_USERNAME')
    password = os.getenv('KH_PASSWORD')

    if not server:
        print("Error conectando a KH_HE: La variable de entorno 'KH_SERVER' no está definida en .env")
        return None

    # Limpiar espacios o comillas en el servidor
    server = server.strip().strip('"').strip("'")

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
        
        # Probar con Network=DBMSSOCN (fuerza uso de TCP/IP Sockets en el driver legacy de Windows)
        conn_strings = [
            f'DRIVER={driver_str};SERVER={server};DATABASE={database};UID={username};PWD={password};Network=DBMSSOCN;TrustServerCertificate=yes;Encrypt=no;',
            f'DRIVER={driver_str};SERVER={server};DATABASE={database};UID={username};PWD={password};Network=DBMSSOCN;',
            f'DRIVER={driver_str};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;Encrypt=no;',
            f'DRIVER={driver_str};SERVER={server};DATABASE={database};UID={username};PWD={password};'
        ]
        
        for cs in conn_strings:
            try:
                conn = pyodbc.connect(cs, timeout=10)
                return conn
            except Exception as e:
                last_error = e
                continue

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

def fetch_full_ehr_dashboard(pt_num: str):
    """
    Obtiene toda la información necesaria para llenar el Expediente Electrónico (Dashboard).
    Cruza información de V_MRPT (demográficos), MR_NE_URG (notas, signos, alergias) y UDR_RPT_HABITACION (línea de tiempo).
    """
    conn = get_kh_connection()
    if not conn:
        return {"error": "No connection to hospital DB"}
        
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
        
        # 2. Última Nota de Urgencias (para obtener Signos Vitales, Alergias y Diagnóstico actual)
        cursor.execute("""
            SELECT TOP 1
                ALERGIAS, DIAGNOSTICO, TA1, FC1, FR1, SAT_O2_1, PESO1, TALLA, NOTAS as TEMP,
                S_SUBJETIVO1, O_OBJETIVO, A_ANALISIS1, P_PLAN1, CreatedOn, N_MEDICO
            FROM MR_NE_URG
            WHERE PTNum = ?
            ORDER BY CreatedOn DESC
        """, (pt_num,))
        nota_row = cursor.fetchone()
        
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
                "allergies": str(nota_row[0]) if nota_row and nota_row[0] else "Sin alergias reportadas"
            },
            "vitals": [],
            "timelineEvents": [],
            "clinicalNotes": [],
            "medications": [] # Pendiente de cruzar con otra tabla
        }
        
        if nota_row:
            # Mapear signos vitales
            dashboard_data["vitals"] = [
                {"label": "Presión Arterial", "value": str(nota_row[2] or "--"), "unit": "mmHg", "status": "Revisado"},
                {"label": "Frec. Cardíaca", "value": str(nota_row[3] or "--"), "unit": "lpm", "status": "Revisado"},
                {"label": "Frec. Respiratoria", "value": str(nota_row[4] or "--"), "unit": "rpm", "status": "Revisado"},
                {"label": "Saturación O2", "value": str(nota_row[5] or "--"), "unit": "%", "status": "Revisado"},
                {"label": "Temperatura", "value": str(nota_row[8] or "--").replace("FEBRIL ", ""), "unit": "°C", "status": "Revisado"},
                {"label": "Peso", "value": str(nota_row[6] or "--"), "unit": "kg", "status": "Revisado"}
            ]
            
            # Mapear nota como el evento clínico principal
            fecha_nota = nota_row[13]
            dashboard_data["clinicalNotes"].append({
                "date": fecha_nota.strftime('%d/%m/%Y') if fecha_nota else "",
                "doctor": str(nota_row[14] or ""),
                "diagnosis": str(nota_row[1] or ""),
                "soap": {
                    "s": str(nota_row[9] or ""),
                    "o": str(nota_row[10] or ""),
                    "a": str(nota_row[11] or ""),
                    "p": str(nota_row[12] or "")
                }
            })
            
            # Agregar la nota a la línea de tiempo
            if fecha_nota:
                dashboard_data["timelineEvents"].append({
                    "date": fecha_nota.strftime('%d %b %Y'),
                    "time": fecha_nota.strftime('%H:%M'),
                    "type": "Nota de Evolución",
                    "desc": f"El Dr(a). {str(nota_row[14] or '')} agregó una nota de urgencias."
                })
                
        # Agregar movimientos de cama a la línea de tiempo
        for r in timeline_rows:
            if r[1]: # EntryDate
                dashboard_data["timelineEvents"].append({
                    "date": r[1].strftime('%d %b %Y'),
                    "time": r[1].strftime('%H:%M'),
                    "type": "Asignación de Cama",
                    "desc": f"Paciente ingresado a {str(r[0] or '')}"
                })
                
        # Ordenar timeline (simplificado asumiendo que ya vienen más o menos ordenados o se ordenan en frontend)
        
        return dashboard_data
        
    except Exception as e:
        print(f"Error fetching full EHR data: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

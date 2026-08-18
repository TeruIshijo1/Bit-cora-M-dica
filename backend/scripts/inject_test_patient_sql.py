import os
import pyodbc
from dotenv import load_dotenv

# Cargar variables de entorno del backend
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

def get_kh_connection():
    server = os.getenv('KH_SERVER')
    database = os.getenv('KH_DATABASE', 'KH_HE')
    username = os.getenv('KH_USERNAME')
    password = os.getenv('KH_PASSWORD')

    if not server:
        raise ValueError("No se encontro KH_SERVER en .env")

    drivers = [
        'ODBC Driver 18 for SQL Server',
        'ODBC Driver 17 for SQL Server',
        'SQL Server Native Client 11.0',
        'SQL Server'
    ]

    for drv in drivers:
        try:
            conn_str = f"DRIVER={{{drv}}};SERVER={server};DATABASE={database};UID={username};PWD={password};Network=DBMSSOCN;TrustServerCertificate=yes;Encrypt=no;"
            return pyodbc.connect(conn_str, timeout=5)
        except:
            continue
    raise ConnectionError("No se pudo conectar a SQL Server KH_HE con ningun driver")

def inject_test_patient(pt_num="5704"):
    print(f"[*] Inyectando / actualizando paciente de prueba PTNum: {pt_num} en KH_HE...")
    conn = get_kh_connection()
    cursor = conn.cursor()

    # 1. Verificar si existe la tabla MR_NE_URG e insertar la nota clinica
    cursor.execute("SELECT COUNT(*) FROM MR_NE_URG WHERE PTNum = ?", (pt_num,))
    exists = cursor.fetchone()[0] > 0

    if exists:
        print(" -> Actualizando nota clinica en MR_NE_URG...")
        cursor.execute("""
            UPDATE MR_NE_URG
            SET ALERGIAS = ?, DIAGNOSTICO = ?, TA1 = ?, FC1 = ?, FR1 = ?, SAT_O2_1 = ?, PESO1 = ?, TALLA = ?, NOTAS = ?,
                S_SUBJETIVO1 = ?, O_OBJETIVO = ?, A_ANALISIS1 = ?, P_PLAN1 = ?, CreatedOn = GETDATE(), N_MEDICO = ?
            WHERE PTNum = ?
        """, (
            "PENICILINA, SULFAS",
            "DOLOR ABDOMINAL AGUDO EN FOSA ILIACA DERECHA. SOSPECHA DE APENDICITIS AGUDA.",
            "130/85", "92", "20", "96", "78.5", "1.74", "38.2",
            "Paciente masculino de 35 anos que acude por dolor abdominal de 12 hrs de evolucion en fosa iliaca derecha con vomito.",
            "EXPLORACION FISICA:\nConsciente, doloroso en FID. McBurney (+), Rovsing (+), Rebote (+). TA 130/85, FC 92, FR 20, Temp 38.2 C.",
            "ANALISIS / VALORACION:\nCuadro clinico compatible con Apendicitis Aguda. Escala de Alvarado: 8 puntos.",
            "PLAN TERAPEUTICO:\n1. Ayuno.\n2. Solucion Hartmann 1000ml.\n3. Ketorolaco 30mg IV.\n4. Laboratorios y USG Abdominal.",
            "DR. ALEJANDRO MENDOZA RIVERA",
            pt_num
        ))
    else:
        print(" -> Insertando nueva nota clinica en MR_NE_URG...")
        cursor.execute("""
            INSERT INTO MR_NE_URG (
                PTNum, ALERGIAS, DIAGNOSTICO, TA1, FC1, FR1, SAT_O2_1, PESO1, TALLA, NOTAS,
                S_SUBJETIVO1, O_OBJETIVO, A_ANALISIS1, P_PLAN1, CreatedOn, N_MEDICO
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)
        """, (
            pt_num,
            "PENICILINA, SULFAS",
            "DOLOR ABDOMINAL AGUDO EN FOSA ILIACA DERECHA. SOSPECHA DE APENDICITIS AGUDA.",
            "130/85", "92", "20", "96", "78.5", "1.74", "38.2",
            "Paciente masculino de 35 anos que acude por dolor abdominal de 12 hrs de evolucion en fosa iliaca derecha con vomito.",
            "EXPLORACION FISICA:\nConsciente, doloroso en FID. McBurney (+), Rovsing (+), Rebote (+). TA 130/85, FC 92, FR 20, Temp 38.2 C.",
            "ANALISIS / VALORACION:\nCuadro clinico compatible con Apendicitis Aguda. Escala de Alvarado: 8 puntos.",
            "PLAN TERAPEUTICO:\n1. Ayuno.\n2. Solucion Hartmann 1000ml.\n3. Ketorolaco 30mg IV.\n4. Laboratorios y USG Abdominal.",
            "DR. ALEJANDRO MENDOZA RIVERA"
        ))

    # 2. Insertar movimiento en UDR_RPT_HABITACION si no existe
    cursor.execute("SELECT COUNT(*) FROM UDR_RPT_HABITACION WHERE PTNum = ?", (pt_num,))
    if cursor.fetchone()[0] == 0:
        print(" -> Insertando movimiento de habitacion en UDR_RPT_HABITACION...")
        cursor.execute("""
            INSERT INTO UDR_RPT_HABITACION (PCNum, PTNum, FRName, EntryDate, ClosedOn)
            VALUES (?, ?, ?, GETDATE(), NULL)
        """, ("PC-" + pt_num, pt_num, "URGENCIAS C-01"))

    conn.commit()
    conn.close()
    print(f"[OK] Inyeccion completada con exito para PTNum: {pt_num}")

if __name__ == '__main__':
    inject_test_patient("5704")

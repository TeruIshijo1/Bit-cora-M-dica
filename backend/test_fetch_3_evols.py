import pyodbc
from dotenv import load_dotenv
import os

load_dotenv('backend/.env')
server = os.getenv('KH_SERVER').strip().strip('"').strip("'")
database = os.getenv('KH_DATABASE', 'KH_HE')
username = os.getenv('KH_USERNAME')
password = os.getenv('KH_PASSWORD')

drivers = ['ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server', 'SQL Server']
conn = None
for d in drivers:
    try:
        cs = f'DRIVER={{{d}}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;Encrypt=no;'
        conn = pyodbc.connect(cs, timeout=5)
        break
    except Exception as e:
        continue

if not conn:
    print("Could not connect")
    exit(1)

cursor = conn.cursor()
cursor.execute("""
    SELECT TOP 1
        -- General
        PTNum, ALERGIAS, DIAGNOSTICO, EXPEDIENTE, CAMA, DESTINO, FHINGRESO, FYH_EGRESO, CreatedOn,
        -- Evol 1
        FECHANOTA1, TURNO1, TA1, FC1, FR1, SAT_O2_1, PESO1, TALLA, NOTAS,
        S_SUBJETIVO1, O_OBJETIVO, A_ANALISIS1, P_PLAN1, N_MEDICO, CEDPROF, NMIP,
        -- Evol 2
        FECHANOTA2, TURNO2, TA2, FC2, FR2, SAT_O2_2, PESO2, TALLA2, NOTAS2,
        S_SUBJETIVO2, O_OBJETIVO2, A_ANALISIS2, P_PLAN2, MEDICO3, CEDULA2, N_MIP2,
        -- Evol 3
        FECHANOTA3, TURNO33, TA3, FC3, FR3, SAT_O2_3, PESO3, TALLA3, NOTAS3,
        S_SUBJETIVO3, O_OBJETIVO3, A_ANALISIS3, P_PLAN3, MEDICO4, CEDULA3, N_MIP3
    FROM MR_NE_URG
    WHERE PTNum = 5704
    ORDER BY CreatedOn DESC
""")

cols = [c[0] for c in cursor.description]
row = cursor.fetchone()
if row:
    d = dict(zip(cols, row))
    print("=== GENERAL ===")
    print("Diagnostico:", d['DIAGNOSTICO'])
    print("Alergias:", d['ALERGIAS'])
    print("Destino:", d['DESTINO'])
    print("Ingreso:", d['FHINGRESO'])
    print("Egreso:", d['FYH_EGRESO'])
    
    print("\n=== EVOLUCIÓN 1 ===")
    print("Fecha:", d['FECHANOTA1'], "Turno:", d['TURNO1'])
    print("Signos:", f"TA:{d['TA1']} FC:{d['FC1']} FR:{d['FR1']} Sat:{d['SAT_O2_1']} Peso:{d['PESO1']} Talla:{d['TALLA']} Temp:{d['NOTAS']}")
    print("Subjetivo 1:", d['S_SUBJETIVO1'][:60] if d['S_SUBJETIVO1'] else "Vacio")
    print("Médico 1:", d['N_MEDICO'], "Cedula 1:", d['CEDPROF'])
    
    print("\n=== EVOLUCIÓN 2 ===")
    print("Fecha:", d['FECHANOTA2'], "Turno:", d['TURNO2'])
    print("Signos:", f"TA:{d['TA2']} FC:{d['FC2']} FR:{d['FR2']} Sat:{d['SAT_O2_2']} Peso:{d['PESO2']} Talla:{d['TALLA2']} Temp:{d['NOTAS2']}")
    print("Subjetivo 2:", d['S_SUBJETIVO2'][:60] if d['S_SUBJETIVO2'] else "Vacio")
    print("Médico 2:", d['MEDICO3'], "Cedula 2:", d['CEDULA2'])
    
    print("\n=== EVOLUCIÓN 3 ===")
    print("Fecha:", d['FECHANOTA3'], "Turno:", d['TURNO33'])
    print("Signos:", f"TA:{d['TA3']} FC:{d['FC3']} FR:{d['FR3']} Sat:{d['SAT_O2_3']} Peso:{d['PESO3']} Talla:{d['TALLA3']} Temp:{d['NOTAS3']}")
    print("Subjetivo 3:", d['S_SUBJETIVO3'][:60] if d['S_SUBJETIVO3'] else "Vacio")
    print("Médico 3:", d['MEDICO4'], "Cedula 3:", d['CEDULA3'])

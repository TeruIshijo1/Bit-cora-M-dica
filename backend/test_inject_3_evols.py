import pyodbc
from dotenv import load_dotenv
import os
import datetime

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

cursor = conn.cursor()

# Actualizar paciente 5704 con las 3 evoluciones
cursor.execute("""
    UPDATE MR_NE_URG
    SET 
        -- Evolución 2
        FECHANOTA2 = '2026-08-18 16:30:00',
        TURNO2 = 'VESPERTINO',
        TA2 = '125/80',
        FC2 = '84',
        FR2 = '18',
        SAT_O2_2 = '98',
        PESO2 = '78.5',
        TALLA2 = '1.72',
        NOTAS2 = '37.1 C',
        S_SUBJETIVO2 = 'Paciente refiere disminucion del dolor abdominal tras analgesia con ketorolaco. Tolerando liquidos via oral. No refiere nausea ni vomito.',
        O_OBJETIVO2 = 'Abdomen blando, depresible, levemente doloroso en FID a la palpacion media. Ruidos hidroaereos normoactivos. Signos apendiculares negativos en esta revaloracion.',
        A_ANALISIS2 = 'Evolucion clinica favorable con adecuada respuesta a tratamiento analgesico. Se descarta abdomen agudo quirurgico por el momento.',
        P_PLAN2 = '1. Dieta blanda.\n2. Continuar analgesia VO.\n3. Vigilancia de signos de alarma.\n4. Revaloracion en 4 hrs.',
        MEDICO3 = 'DR. ALEJANDRO MENDOZA RIVERA',
        CEDULA2 = '12345678',
        N_MIP2 = 'MIP JAVIER CRESPO',
        
        -- Evolución 3
        FECHANOTA3 = '2026-08-18 21:00:00',
        TURNO33 = 'NOCTURNO',
        TA3 = '120/80',
        FC3 = '78',
        FR3 = '18',
        SAT_O2_3 = '99',
        PESO3 = '78.5',
        TALLA3 = '1.72',
        NOTAS3 = '36.8 C',
        S_SUBJETIVO3 = 'Paciente asintomatico, sin dolor, tolerando dieta y deambulando sin molestias.',
        O_OBJETIVO3 = 'Abdomen plano, blando, indoloro a la palpacion. Sin datos de irritacion peritoneal.',
        A_ANALISIS3 = 'Cuadro de dolor abdominal resuelto. Paciente en condiciones de egreso hospitalario.',
        P_PLAN3 = '1. Alta a domicilio.\n2. Cita abierta a urgencias ante datos de alarma.\n3. Cita de control en consulta externa en 48 hrs.',
        MEDICO4 = 'DR. ALEJANDRO MENDOZA RIVERA',
        CEDULA3 = '12345678',
        N_MIP3 = 'MIP JAVIER CRESPO'
    WHERE PTNum = 5704
""")
conn.commit()
print("Evoluciones 2 y 3 inyectadas con éxito en MR_NE_URG para paciente 5704!")

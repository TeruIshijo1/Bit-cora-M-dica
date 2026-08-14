import pyodbc
import uuid
import datetime
import getpass
import sys

# Configuración del servidor
SERVER = 'bore.pub,37368'  # SQL Server usa coma para el puerto
DATABASE = 'KH_HE'
USERNAME = 'escandon_bi_user'

def obtener_driver_sql():
    """Encuentra el driver de SQL Server instalado en tu PC"""
    drivers = [driver for driver in pyodbc.drivers() if 'SQL Server' in driver]
    if not drivers:
        print("Error: No se encontró ningún driver ODBC para SQL Server en este equipo.")
        sys.exit(1)
    # Preferimos versiones más recientes (ej. ODBC Driver 17)
    drivers.sort(reverse=True)
    return drivers[0]

def main():
    print(f"=== PRUEBA DE INYECCIÓN A MEDICAL SUITE (VERTICAL) ===")
    print(f"Servidor: {SERVER}")
    print(f"Base de datos: {DATABASE}")
    print(f"Usuario: {USERNAME}")
    
    # 1. Pon la contraseña aquí directamente para la prueba
    password = "Bi_Escandon_2026!#" # <-- ¡CAMBIA ESTO!
    
    driver = obtener_driver_sql()
    print(f"\nUsando driver: {driver}")
    
    connection_string = f'DRIVER={{{driver}}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={password}'
    
    try:
        print("\nConectando a la base de datos...")
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        print("¡Conexión exitosa a la base de datos de la Vertical!\n")
        
        # 2. Buscar al paciente COMODIN
        print("Buscando al paciente 'COMODIN' en la base de datos...")
        # Buscamos en las tablas comunes de pacientes de Medical Suite.
        # Generalmente la tabla se llama MD_PT, PT, o similar.
        
        # Primero buscamos cuál es la tabla de pacientes analizando las columnas
        cursor.execute("""
            SELECT c.TABLE_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.COLUMN_NAME = 'PTNum' AND c.TABLE_NAME NOT LIKE 'MR_%'
            GROUP BY c.TABLE_NAME
        """)
        tablas_posibles = [row[0] for row in cursor.fetchall()]
        
        if not tablas_posibles:
            pt_num = input("No se pudo autodetectar la tabla de pacientes. Por favor ingresa el PTNum (ID) del paciente COMODIN manualmente: ")
        else:
            # Pedimos el ID manualmente para no equivocarnos en la prueba
            print("Inyectando para el paciente COMODIN COMODIN COMODIN (PTNum: 5704, PCNum: 1301)...")
            pt_num = "5704"

        # 3. Preparar los datos falsos para engañar a la Vertical
        mr_ne_urgid = str(uuid.uuid4()).upper() # Genera un GUID único de 36 caracteres
        fecha_actual = datetime.datetime.now()
        
        # 4. Construir el INSERT
        # Usamos los datos de control que vimos en tu captura:
        # ControllerName = 'PC', ControllerKey = 1301, MR_ST = 'RG'
        
        insert_query = """
            INSERT INTO [KH_HE].[dbo].[MR_NE_URG] (
                [PTNum], 
                [ControllerName], 
                [ControllerKey], 
                [MR_ST], 
                [MR_NE_URGID], 
                [CreatedBy], 
                [CreatedOn], 
                [ModifiedBy], 
                [ModifiedOn],
                [DIAGNOSTICO],
                [NOTAS],
                [S_SUBJETIVO1],
                [P_PLAN1]
            ) 
            VALUES (
                ?, 
                'PC', 
                '1301', 
                'RG', 
                ?, 
                'api', 
                ?, 
                'api', 
                ?,
                'PRUEBA',
                'PRUEBA',
                'ESTA ES UNA PRUEBA DESDE LA BITACORA, AQUI SI CABE EL TEXTO LARGO Y PODEMOS PONER MUCHA MAS INFORMACION.',
                'PRUEBA'
            )
        """
        
        print("\nEjecutando la inyección de datos...")
        cursor.execute(insert_query, (
            pt_num, 
            mr_ne_urgid, 
            fecha_actual, 
            fecha_actual
        ))
        
        conn.commit() # Guardar los cambios
        print("¡INYECCIÓN COMPLETADA CON ÉXITO!")
        print(f"-> Se creó una Nota de Evolución de Urgencias para el paciente con PTNum: {pt_num}")
        print("VUELVE A LA VERTICAL, BUSCA AL PACIENTE Y REVISA SUS NOTAS DE URGENCIAS.")
        
    except pyodbc.Error as e:
        print(f"Error de Base de Datos: {e}")
    except Exception as e:
        print(f"Error Inesperado: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            print("\nConexión cerrada.")

if __name__ == "__main__":
    main()

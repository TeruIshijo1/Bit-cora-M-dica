from kh_database import get_kh_connection

def update_doctor_records():
    conn = get_kh_connection()
    if not conn:
        print("No se pudo conectar a SQL Server.")
        return
    try:
        cursor = conn.cursor()
        sql = """
        UPDATE MR_NE_URG 
        SET N_MEDICO = 'JOSE JOSE PRUEBA ENRIQUEZ', 
            CEDPROF = 'PRUEBA-99281',
            MEDICO3 = 'JOSE JOSE PRUEBA ENRIQUEZ', 
            CEDULA2 = 'PRUEBA-99281',
            MEDICO4 = 'JOSE JOSE PRUEBA ENRIQUEZ', 
            CEDULA3 = 'PRUEBA-99281'
        WHERE PTNum = '5704'
        """
        cursor.execute(sql)
        conn.commit()
        print("OK: Registros de notas de evolución en SQL Server actualizados a JOSE JOSE PRUEBA ENRIQUEZ!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    update_doctor_records()

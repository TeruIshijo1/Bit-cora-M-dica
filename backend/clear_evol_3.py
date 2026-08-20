from kh_database import get_kh_connection

def clear_evolution_3(pt_num="5704"):
    conn = get_kh_connection()
    if not conn:
        print("No se pudo conectar a SQL Server.")
        return
    try:
        cursor = conn.cursor()
        sql = """
        UPDATE MR_NE_URG
        SET FECHANOTA3 = NULL,
            TURNO33 = NULL,
            TA3 = NULL,
            FC3 = NULL,
            FR3 = NULL,
            SAT_O2_3 = NULL,
            PESO3 = NULL,
            TALLA3 = NULL,
            NOTAS3 = NULL,
            S_SUBJETIVO3 = NULL,
            O_OBJETIVO3 = NULL,
            A_ANALISIS3 = NULL,
            P_PLAN3 = NULL,
            MEDICO4 = NULL,
            CEDULA3 = NULL,
            N_MIP3 = NULL
        WHERE PTNum = ?
        """
        cursor.execute(sql, (pt_num,))
        conn.commit()
        print(f"OK: Evolución 3 del paciente {pt_num} borrada exitosamente de SQL Server.")
    except Exception as e:
        print(f"Error al limpiar evolución 3: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    clear_evolution_3()

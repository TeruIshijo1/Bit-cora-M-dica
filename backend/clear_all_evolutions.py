from kh_database import get_kh_connection

def clear_all_evolutions_for_patient(pt_num="5704"):
    conn = get_kh_connection()
    if not conn:
        print("No se pudo conectar a SQL Server.")
        return
    try:
        cursor = conn.cursor()
        
        # Eliminar registro previo de notas de urgencias para este paciente de prueba
        cursor.execute("DELETE FROM MR_NE_URG WHERE PTNum = ?", (pt_num,))
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"OK: Registro de notas de urgencias para paciente {pt_num} eliminado de SQL Server ({deleted_count} fila(s) eliminada(s)). Listo para crear desde cero!")
    except Exception as e:
        print(f"Error al eliminar notas de urgencias: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    clear_all_evolutions_for_patient()

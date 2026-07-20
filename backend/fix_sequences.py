from database import engine
from sqlalchemy import text
import sys

def fix_all():
    tables = [
        "usuarios", "medicos", "pacientes", "camas", 
        "auditoria_logs", "atenciones_medicas", 
        "catalogo_areas", "catalogo_tipos_atencion",
        "escaneos_rh", "traslados_pacientes", "notas_enfermeria", "procedimientos_frecuentes"
    ]
    with engine.connect() as conn:
        for table in tables:
            # Empezar una transacción por tabla para que no se envenene todo el bloque
            trans = conn.begin()
            try:
                # Revisar si existe la secuencia para esa tabla en Postgres
                seq_name = f"{table}_id_seq"
                res = conn.execute(text(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table}), 1));")).fetchone()
                trans.commit()
                print(f"Fixed {table}, new val: {res}")
            except Exception as e:
                trans.rollback()
                print(f"Error on {table} (skipping): {e}")

if __name__ == '__main__':
    fix_all()

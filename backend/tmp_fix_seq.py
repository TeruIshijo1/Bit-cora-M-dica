from database import engine
from sqlalchemy import text
import sys

def fix_all():
    with engine.begin() as conn:
        for table in ["traslados_pacientes", "atenciones_medicas", "catalogo_areas", "catalogo_tipos_atencion", "escaneos_rh", "notas_enfermeria", "procedimientos_frecuentes"]:
            try:
                res = conn.execute(text(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 1));")).fetchone()
                print(f"Fixed {table}, new val: {res}")
            except Exception as e:
                print(f"Error on {table}: {e}")

if __name__ == '__main__':
    fix_all()

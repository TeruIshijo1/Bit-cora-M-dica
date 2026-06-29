import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'backend', 'hospital_escandon.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE pacientes ADD COLUMN registrado_por_nombre TEXT")
except Exception as e:
    print(f"pacientes: {e}")

try:
    cursor.execute("ALTER TABLE atenciones_medicas ADD COLUMN registrado_por_nombre TEXT")
except Exception as e:
    print(f"atenciones: {e}")

conn.commit()
conn.close()
print("Migration completed")

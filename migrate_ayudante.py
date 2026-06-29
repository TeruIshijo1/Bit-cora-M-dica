import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'backend', 'hospital_escandon.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE medicos ADD COLUMN es_ayudante BOOLEAN DEFAULT 0")
except sqlite3.OperationalError as e:
    print(f"es_ayudante: {e}")

try:
    cursor.execute("ALTER TABLE medicos ADD COLUMN medico_asignado_id INTEGER REFERENCES medicos(id)")
except sqlite3.OperationalError as e:
    print(f"medico_asignado_id: {e}")

conn.commit()
conn.close()
print("Migration completed.")

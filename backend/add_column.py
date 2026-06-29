import sqlite3

try:
    conn = sqlite3.connect("hospital_escandon.db")
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE pacientes ADD COLUMN codigo_barras VARCHAR")
    cursor.execute("CREATE INDEX ix_pacientes_codigo_barras ON pacientes (codigo_barras)")
    conn.commit()
    print("Column added successfully.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()

import sqlite3

try:
    conn = sqlite3.connect('hospital_escandon.db')
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(pacientes)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "fecha_registro" not in columns:
        cursor.execute("ALTER TABLE pacientes ADD COLUMN fecha_registro DATETIME")
        print("Agregada columna fecha_registro")
        
    if "creado_por_id" not in columns:
        cursor.execute("ALTER TABLE pacientes ADD COLUMN creado_por_id INTEGER REFERENCES usuarios(id)")
        print("Agregada columna creado_por_id")
        
    conn.commit()
    conn.close()
    print("Migración completada.")
except Exception as e:
    print("Error en migración:", e)

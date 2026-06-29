import sqlite3
import sys
import os

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    return column in columns

def migrate():
    # Make sure we use the correct db path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hospital_escandon.db")
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}. Run seed.py first.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if not column_exists(cursor, "usuarios", "nombre_completo"):
            print("Adding nombre_completo to usuarios...")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN nombre_completo VARCHAR")
        
        if not column_exists(cursor, "pacientes", "dado_de_alta_por_id"):
            print("Adding dado_de_alta_por_id to pacientes...")
            cursor.execute("ALTER TABLE pacientes ADD COLUMN dado_de_alta_por_id INTEGER")
            
        if not column_exists(cursor, "pacientes", "fecha_alta"):
            print("Adding fecha_alta to pacientes...")
            cursor.execute("ALTER TABLE pacientes ADD COLUMN fecha_alta DATETIME")
            
        if not column_exists(cursor, "atenciones_medicas", "reaperturado"):
            print("Adding reaperturado to atenciones_medicas...")
            cursor.execute("ALTER TABLE atenciones_medicas ADD COLUMN reaperturado BOOLEAN DEFAULT 0")

        conn.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Error migrating DB: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

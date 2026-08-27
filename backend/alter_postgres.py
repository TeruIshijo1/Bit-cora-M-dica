import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/hospital_escandon_db") 

print(f"Conectando a la base de datos: {SQLALCHEMY_DATABASE_URL}")
engine = create_engine(SQLALCHEMY_DATABASE_URL)

try:
    with engine.begin() as conn:
        print("Ejecutando ALTER TABLE usuarios...")
        try:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN permisos_modulos TEXT;"))
            print("Columna permisos_modulos agregada a usuarios.")
        except Exception as e:
            print(f"No se pudo agregar permisos_modulos a usuarios: {e}")
            
        try:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN formatos_permitidos TEXT;"))
            print("Columna formatos_permitidos agregada a usuarios.")
        except Exception as e:
            print(f"No se pudo agregar formatos_permitidos a usuarios: {e}")
            
        print("Ejecutando ALTER TABLE medicos...")
        try:
            conn.execute(text("ALTER TABLE medicos ADD COLUMN formatos_permitidos TEXT;"))
            print("Columna formatos_permitidos agregada a medicos.")
        except Exception as e:
            print(f"No se pudo agregar formatos_permitidos a medicos: {e}")
            
        print("Modificaciones completadas!")
except Exception as e:
    print(f"Error general: {e}")

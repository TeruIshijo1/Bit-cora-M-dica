from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from sqlalchemy.engine import Engine

import os
from dotenv import load_dotenv

load_dotenv()

# SQLALCHEMY_DATABASE_URL = "sqlite:///./hospital_escandon.db"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost/hospital_escandon_db")

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.close()
        except Exception:
            pass

def check_and_add_columns(eng):
    from sqlalchemy import text
    try:
        with eng.begin() as conn:
            if eng.name == 'postgresql':
                queries = [
                    "ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS dado_de_alta_por_id INTEGER;",
                    "ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS fecha_alta TIMESTAMP;",
                    "ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS registrado_por_nombre VARCHAR;",
                    "ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS codigo_barras VARCHAR;",
                    "ALTER TABLE atenciones_medicas ADD COLUMN IF NOT EXISTS reaperturado BOOLEAN DEFAULT FALSE;",
                    "ALTER TABLE atenciones_medicas ADD COLUMN IF NOT EXISTS registrado_por_nombre VARCHAR;",
                    "ALTER TABLE medicos ADD COLUMN IF NOT EXISTS bajo_contrato BOOLEAN DEFAULT FALSE;",
                    "ALTER TABLE medicos ADD COLUMN IF NOT EXISTS horario_laboral VARCHAR;",
                    "ALTER TABLE medicos ADD COLUMN IF NOT EXISTS es_ayudante BOOLEAN DEFAULT FALSE;",
                    "ALTER TABLE medicos ADD COLUMN IF NOT EXISTS medico_asignado_id INTEGER;",
                    "ALTER TABLE medicos ADD COLUMN IF NOT EXISTS public_key_pem TEXT;",
                    "ALTER TABLE medicos ADD COLUMN IF NOT EXISTS private_key_enc TEXT;",
                    "ALTER TABLE camas ADD COLUMN IF NOT EXISTS estado_limpieza VARCHAR DEFAULT 'Limpia';",
                    "ALTER TABLE camas ADD COLUMN IF NOT EXISTS notas_limpieza VARCHAR;",
                    "ALTER TABLE firmas_documentos_clinicos ADD COLUMN IF NOT EXISTS tsa_token TEXT;"
                ]
                for q in queries:
                    conn.execute(text(q))
            elif eng.name == 'sqlite':
                # Intentar anadir columnas una por una e ignorar error si ya existen
                columnas = [
                    ("pacientes", "dado_de_alta_por_id INTEGER"),
                    ("pacientes", "fecha_alta DATETIME"),
                    ("pacientes", "registrado_por_nombre VARCHAR"),
                    ("pacientes", "codigo_barras VARCHAR"),
                    ("atenciones_medicas", "reaperturado BOOLEAN DEFAULT 0"),
                    ("atenciones_medicas", "registrado_por_nombre VARCHAR"),
                    ("medicos", "bajo_contrato BOOLEAN DEFAULT 0"),
                    ("medicos", "horario_laboral VARCHAR"),
                    ("medicos", "es_ayudante BOOLEAN DEFAULT 0"),
                    ("medicos", "medico_asignado_id INTEGER"),
                    ("medicos", "public_key_pem TEXT"),
                    ("medicos", "private_key_enc TEXT"),
                    ("camas", "estado_limpieza VARCHAR DEFAULT 'Limpia'"),
                    ("camas", "notas_limpieza VARCHAR"),
                    ("firmas_documentos_clinicos", "tsa_token TEXT")
                ]
                for tabla, col in columnas:
                    try:
                        conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col}"))
                    except Exception:
                        pass
    except Exception as e:
        print(f"Aviso de auto-migracion: {e}")

check_and_add_columns(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

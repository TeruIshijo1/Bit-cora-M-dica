import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData, select, text
import datetime

# Importamos los modelos (esto es crucial para que SQLAlchemy sepa cómo crear las tablas)
from models import Base
from models import (
    CatalogoArea, CatalogoTipoAtencion, Cama, Usuario, Medico, Paciente, 
    AtencionMedica, NotaEnfermeria, EscaneoRH, TrasladoPaciente, AuditoriaLog, ProcedimientoFrecuente
)

# 1. Configuración de Conexiones
# Usaremos la base de datos de producción recién copiada como fuente
SQLITE_URL = "sqlite:///./hospital_escandon.db"

# Obtener URL de Postgres desde variable de entorno o usar uno por defecto para solicitar
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres@localhost/hospital_escandon_db")

print("Conectando a SQLite (Origen)...")
sqlite_engine = create_engine(SQLITE_URL)

print("Conectando a PostgreSQL (Destino)...")
postgres_engine = create_engine(POSTGRES_URL)

def migrar_datos():
    # 2. Crear las tablas en PostgreSQL si no existen
    print("Creando esquema en PostgreSQL...")
    Base.metadata.create_all(bind=postgres_engine)
    
    # 3. Iterar sobre todas las tablas en orden (para respetar llaves foráneas)
    tablas = Base.metadata.sorted_tables
    
    with sqlite_engine.connect() as sqlite_conn:
        with postgres_engine.begin() as postgres_conn: # begin() asegura commit automático al final del with
            # Deshabilitar triggers (incluyendo llaves foráneas) para permitir migración de datos huérfanos de SQLite
            postgres_conn.execute(text("SET session_replication_role = 'replica';"))
            for tabla in tablas:
                nombre_tabla = tabla.name
                print(f"--- Migrando tabla: {nombre_tabla} ---")
                
                # Leemos todos los registros de esta tabla en SQLite
                try:
                    resultado_sqlite = sqlite_conn.execute(tabla.select())
                    registros_sqlite = resultado_sqlite.mappings().all()
                except Exception as e:
                    if "no such table" in str(e).lower():
                        print(f"WARNING: La tabla '{nombre_tabla}' NO existe en la base de datos de origen (SQLite). Saltando.")
                        continue
                    raise e
                
                if not registros_sqlite:
                    print(f"La tabla {nombre_tabla} está vacía. Saltando.")
                    continue
                    
                print(f"Encontrados {len(registros_sqlite)} registros en {nombre_tabla}.")
                
                # Limpiamos la tabla en Postgres antes de insertar
                postgres_conn.execute(tabla.delete())
                
                # Insertamos
                datos_a_insertar = [dict(r) for r in registros_sqlite]
                
                try:
                    postgres_conn.execute(tabla.insert(), datos_a_insertar)
                    print(f"OK: {len(datos_a_insertar)} registros insertados exitosamente en PostgreSQL ({nombre_tabla}).")
                except Exception as e:
                    print(f"ERROR al insertar en {nombre_tabla}: {e}")
                    raise e
                    
    print("\n¡Migración completada con éxito!")

if __name__ == "__main__":
    migrar_datos()

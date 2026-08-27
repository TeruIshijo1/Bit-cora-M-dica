import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/hospital_escandon_db") 

engine = create_engine(SQLALCHEMY_DATABASE_URL)

try:
    with engine.begin() as conn:
        print("Ejecutando creacion de tabla catalogo_formatos...")
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS catalogo_formatos (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR NOT NULL,
                nombre VARCHAR NOT NULL,
                activo BOOLEAN DEFAULT TRUE
            );
        '''))
        print("Tabla catalogo_formatos creada.")
        
        # Insertar algunos por defecto si no existen
        conn.execute(text('''
            INSERT INTO catalogo_formatos (codigo, nombre) 
            SELECT 'HE-DIRMED-SINPRO-PLT-87/01', 'Nota de Evolucion de Urgencias'
            WHERE NOT EXISTS (SELECT 1 FROM catalogo_formatos WHERE codigo = 'HE-DIRMED-SINPRO-PLT-87/01');
        '''))
        
        conn.execute(text('''
            INSERT INTO catalogo_formatos (codigo, nombre) 
            SELECT 'CONSENTIMIENTO', 'Consentimiento Informado General'
            WHERE NOT EXISTS (SELECT 1 FROM catalogo_formatos WHERE codigo = 'CONSENTIMIENTO');
        '''))
        
        conn.execute(text('''
            INSERT INTO catalogo_formatos (codigo, nombre) 
            SELECT 'HE-DIRMED-RECETA', 'Receta Medica'
            WHERE NOT EXISTS (SELECT 1 FROM catalogo_formatos WHERE codigo = 'HE-DIRMED-RECETA');
        '''))
        print("Datos insertados.")
except Exception as e:
    print(f"Error: {e}")

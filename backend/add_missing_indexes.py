# ==============================================================================
# SCRIPT DE MIGRACIÓN: CREACIÓN DE ÍNDICES COMPUESTOS EN BASE DE DATOS
# MediReg HES - Hospital Escandón
# ==============================================================================

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text

# Cargar variables de entorno relativas al archivo y al cwd
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)
load_dotenv()

from database import engine

INDEXES = [
    {
        'name': 'idx_atenciones_med_fecha_pago',
        'table': 'atenciones_medicas',
        'columns': ['medico_id', 'fecha_realizacion', 'estatus_pago'],
        'sql': 'CREATE INDEX IF NOT EXISTS idx_atenciones_med_fecha_pago ON atenciones_medicas (medico_id, fecha_realizacion, estatus_pago);'
    },
    {
        'name': 'idx_firmas_pt_formato_slot_estado',
        'table': 'firmas_documentos_clinicos',
        'columns': ['pt_num', 'codigo_formato', 'evolution_slot', 'estado'],
        'sql': 'CREATE INDEX IF NOT EXISTS idx_firmas_pt_formato_slot_estado ON firmas_documentos_clinicos (pt_num, codigo_formato, evolution_slot, estado);'
    },
    {
        'name': 'idx_historico_pt_formato_fecha',
        'table': 'historico_notas_clinicas',
        'columns': ['pt_num', 'codigo_formato', 'fecha_registro'],
        'sql': 'CREATE INDEX IF NOT EXISTS idx_historico_pt_formato_fecha ON historico_notas_clinicas (pt_num, codigo_formato, fecha_registro);'
    }
]

def check_and_create_indexes():
    print(f'[*] Iniciando migracion de indices en motor: {engine.name.upper()}...')
    
    with engine.begin() as conn:
        for idx in INDEXES:
            name = idx['name']
            table = idx['table']
            cols = ', '.join(idx['columns'])
            print(f'[*] Procesando indice [{name}] en tabla [{table}] ({cols})...')
            
            try:
                conn.execute(text(idx['sql']))
                print(f'    [OK] Indice [{name}] verificado / creado exitosamente.')
            except Exception as e:
                print(f'    [ERROR] Error al procesar indice [{name}]: {e}')
                raise e

    print('[OK] Migracion de indices completada exitosamente sin conflictos.')

if __name__ == '__main__':
    check_and_create_indexes()

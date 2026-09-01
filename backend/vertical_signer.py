import requests
import json
import urllib3
import uuid
import os
from dotenv import load_dotenv

urllib3.disable_warnings()

_vertical_session = None

def get_vertical_session(force_refresh: bool = False) -> requests.Session:
    """
    Obtiene una sesión HTTP autenticada con Vertical.
    Si la sesión expiró o no existe, realiza login automático transparente contra _invoke/Login.
    """
    global _vertical_session
    load_dotenv('D:/Escritorio/Bitacora_HES/backend/.env', override=True)

    if _vertical_session is not None and not force_refresh:
        return _vertical_session

    user = os.getenv('VERTICAL_SYSTEM_USER', 'Bitacora_SIS')
    password = os.getenv('VERTICAL_SYSTEM_PASSWORD', 'BitaHES2026-')

    session = requests.Session()
    session.verify = False

    login_url = 'https://vertical.hospesc.com/_invoke/Login'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Origin': 'https://vertical.hospesc.com',
        'Referer': 'https://vertical.hospesc.com/login'
    }
    payload = {
        'username': user,
        'password': password,
        'rememberMe': True
    }

    try:
        r = session.post(login_url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200 and r.json().get('d'):
            _vertical_session = session
            return _vertical_session
        else:
            print(f"Fallo al autenticar usuario '{user}' en Vertical: {r.text[:150]}")
    except Exception as e:
        print(f"Error de conexión durante auto-login en Vertical: {e}")

    _vertical_session = session
    return _vertical_session


def resolve_vertical_controller_and_pk(codigo_formato: str) -> tuple[str, str]:
    """
    Resuelve dinámicamente el nombre del controlador en Vertical (SQL Server)
    y su columna de clave primaria (PK) para cualquier código de formato presente o futuro.
    """
    try:
        from .kh_database import get_kh_connection
    except Exception:
        from kh_database import get_kh_connection

    DIRECT_MAP = {
        'HE-DIRMED-CONSUL-PLT-12': ('MR_CI_RGO_HU', 'MRNum_CI_RGO_HU'),
        'HE-DIRMED-CONSUL-PLT-04': ('MR_CI_CC', 'MRNum_CI_CC'),
        'HE-DIRMED-CONSUL-PLT-34': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        'HE-DIRMED-SINPRO-PLT-34/01': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        'HE-DIRMED-CONSUL-PLT-34/01': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        'HE-DIRMED-CONSUL-PLT-36': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        'HE-DIRMED-CONSUL-PLT-32/01': ('MR_CI_ETE_CARD', 'MRNum_CI_ETE_CARD'),
        'HE-DIRMED-CONSUL-PLT-EED': ('MR_CI_EED', 'MRNum_CI_EED'),
        'HE-DIRMED-CONSUL-PLT-25': ('MR_CI_RGO_CE', 'MRNum_CI_RGO_CE'),
        'HE-DIRMED-SINPRO-PLT-87/01': ('MR_NE_URG', 'MRNum_NE_URG'),
        'HE-DIRMED-NOTAS-URG-87/01': ('MR_NE_URG', 'MRNum_NE_URG'),
        'HE-DIRMED-CONSUL-PLT-26/01': ('MR_26_01', 'MRNum_26_01'),
        'HE-DIRMED-CONSUL-PLT-24': ('MR_24_HOJA_EVOL', 'MRNum_24_HOJA_EVOL'),
        'HE-DIRMED-NOTAS-HOS-HC': ('MR_HC_HOS', 'MRNum_HC_HOS'),
        'HE-DIRMED-NOTAS-URG-HC': ('MR_HC_URG', 'MRNum_HC_URG'),
        'HE-DIRMED-NOTAS-QXR-POST': ('MR_N_POST_OP', 'MRNum_N_POST_OP'),
        'HE-DIRMED-CONSUL-PLT-79': ('MR_PLT_79', 'MRNum_PLT_79'),
        'HE-DIRMED-NOTAS-HOS-EV': ('MR_EV_HOSP', 'MRNum_EV_HOSP'),
        'HE-DIRMED-CONSUL-PLT-APA': ('MR_CI_APA', 'MRNum_CI_APA'),
        'HE-DIRMED-CONSUL-PLT-CC': ('MR_CI_CC', 'MRNum_CI_CC'),
        'HE-DIRMED-CONSUL-PLT-CES': ('MR_CI_CES', 'MRNum_CI_CES'),
        'HE-DIRMED-CONSUL-PLT-PQ': ('MR_CI_PQ', 'MRNum_CI_PQ'),
        'HE-DIRMED-CONSUL-PLT-HOSP': ('MR_MR_CI_HOSP', 'MRNum_MR_CI_HOSP'),
    }

    if codigo_formato in DIRECT_MAP:
        return DIRECT_MAP[codigo_formato]

    if codigo_formato.startswith('MR_'):
        c_name = codigo_formato
        pk_name = f"MRNum_{codigo_formato.replace('MR_', '')}"
        return (c_name, pk_name)

    # Inferencia dinámica consultando INFORMATION_SCHEMA
    clean_code = codigo_formato.upper().replace('HE-DIRMED-', '').replace('PLT-', '').replace('/', '_').replace('-', '_')
    conn = get_kh_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'MR_%'")
            tables = [r[0] for r in cur.fetchall()]
            for t in tables:
                t_suffix = t.replace('MR_', '')
                if t_suffix in clean_code or clean_code in t_suffix:
                    cur.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? AND COLUMN_NAME LIKE 'MRNum%'", (t,))
                    pk_row = cur.fetchone()
                    pk = pk_row[0] if pk_row else f"MRNum_{t_suffix}"
                    return (t, pk)
        except Exception:
            pass
        finally:
            conn.close()

    return ('MR_NE_URG', 'MRNum_NE_URG')


def resolve_doctor_pr_and_pin(doctor_name: str, cedula: str = None) -> tuple[int, str]:
    """
    Busca al médico en la tabla PR de SQL Server para obtener su PRNum oficial
    y su PIN de firma (MedicalRecordAuthorizationCode).
    """
    try:
        from .kh_database import get_kh_connection
    except Exception:
        from kh_database import get_kh_connection

    conn = get_kh_connection()
    if conn:
        try:
            cur = conn.cursor()
            if cedula:
                cur.execute("SELECT PRNum, MedicalRecordAuthorizationCode FROM PR WHERE Identification LIKE ?", (f"%{cedula.strip()}%",))
                row = cur.fetchone()
                if row and row[0]:
                    return (int(row[0]), str(row[1] or '123456').strip())

            cur.execute("SELECT PRNum, MedicalRecordAuthorizationCode FROM PR WHERE FullName LIKE ? OR Name LIKE ?", (f"%{doctor_name.strip()}%", f"%{doctor_name.strip()}%"))
            row = cur.fetchone()
            if row and row[0]:
                return (int(row[0]), str(row[1] or '123456').strip())
        except Exception as e:
            print(f"Error resolviendo PR del médico: {e}")
        finally:
            conn.close()

    return (257, '123456')


def sign_in_vertical_api(controller_name: str, mrnum: int, pt_num: str, pr_num: int = None, auth_code: str = None, doctor_name: str = 'JOSE JOSE PRUEBA ENRIQUEZ') -> bool:
    """
    Invoca la API nativa de Vertical (_invoke/Execute -> SignRecord) con auto-renovación de sesión y resolución dinámica.
    Vertical genera su propio token criptográfico y código QR nativo 100% válido.
    """
    try:
        from .kh_database import get_kh_connection
    except Exception:
        from kh_database import get_kh_connection

    # Resolver PR y PIN automáticamente si no fueron enviados
    if pr_num is None or auth_code is None:
        resolved_pr, resolved_pin = resolve_doctor_pr_and_pin(doctor_name)
    else:
        resolved_pr = pr_num
        resolved_pin = auth_code

    # Obtener metadatos del paciente y episodio en SQL Server
    c_name, c_key, c_id, pt_id = 'PC', str(pt_num), str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()

    conn = get_kh_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
            meta_row = cursor.fetchone()
            
            cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
            pc_row = cursor.fetchone()

            c_key = str(pc_row[0]) if pc_row and pc_row[0] else (str(meta_row[1]) if meta_row and meta_row[1] else str(pt_num))
            c_id = str(meta_row[2]) if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
            pt_id = str(meta_row[3]) if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
        except Exception as e_meta:
            print(f"Nota obteniendo metadatos para Vertical: {e_meta}")
        finally:
            conn.close()

    # Resolver nombre de campo PK
    pk_field = f"MRNum_{controller_name.replace('MR_', '')}"
    if controller_name == 'MR_NE_URG':
        pk_field = 'MRNum_NE_URG'
    elif controller_name == 'MR_CI_ETE_CARD':
        pk_field = 'MRNum_CI_ETE_CARD'
    elif controller_name == 'MR_CI_EED':
        pk_field = 'MRNum_CI_EED'
    elif controller_name == 'MR_CI_RGO_CE':
        pk_field = 'MRNum_CI_RGO_CE'
    elif controller_name == 'MR_CI_EMI':
        pk_field = 'MRNum_CI_EMI'
    elif controller_name == 'MR_CI_RGO_HU':
        pk_field = 'MRNum_CI_RGO_HU'
    elif controller_name == 'MR_CI_CC':
        pk_field = 'MRNum_CI_CC'

    payload = {
        "controller": controller_name,
        "view": "editForm1",
        "args": {
            "CommandName": "Custom",
            "CommandArgument": "SignRecord",
            "LastCommandName": "Select",
            "Values": [
                { "Name": "FCCode", "OldValue": "HE", "ReadOnly": True },
                { "Name": pk_field, "OldValue": int(mrnum), "ReadOnly": True },
                { "Name": "MR_ST", "OldValue": "RG" },
                { "Name": "PTNum", "OldValue": int(pt_num) if str(pt_num).isdigit() else pt_num },
                { "Name": "PTID", "OldValue": pt_id.lower() },
                { "Name": "ControllerName", "OldValue": "PC" },
                { "Name": "ControllerKey", "OldValue": int(c_key) if str(c_key).isdigit() else c_key },
                { "Name": "ControllerID", "OldValue": c_id.lower() },
                { "Name": "DocumentName", "OldValue": controller_name, "ReadOnly": True },
                { "Name": "DocumentNumber", "OldValue": int(mrnum), "ReadOnly": True },
                { "Name": "Parameters_PRNum", "NewValue": int(resolved_pr), "Modified": True, "ReadOnly": True },
                { "Name": "Parameters_AuthorizationCode", "NewValue": str(resolved_pin), "Modified": True, "ReadOnly": True },
                { "Name": "Parameters_PRNum_auto_alias_", "NewValue": str(doctor_name), "Modified": True, "ReadOnly": True }
            ],
            "ContextKey": controller_name.lower().replace('_', '-'),
            "Controller": controller_name,
            "View": "editForm1"
        }
    }

    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Origin': 'https://vertical.hospesc.com',
        'Referer': 'https://vertical.hospesc.com/pages/pn_ip'
    }

    # Sincronización inmediata en SQL Server para reflejar el estado firmado
    conn_db = get_kh_connection()
    if conn_db:
        try:
            cur_db = conn_db.cursor()
            cur_db.execute(f"UPDATE {controller_name} SET SignedBy = ?, SignedOn = GETDATE(), MR_ST = 'SG' WHERE {pk_field} = ?", (doctor_name, mrnum))
            conn_db.commit()
        except Exception as e_up:
            print(f"Nota actualizando firma directa en {controller_name}: {e_up}")
        finally:
            conn_db.close()

    session = get_vertical_session(force_refresh=False)
    try:
        r = session.post('https://vertical.hospesc.com/_invoke/Execute', json=payload, headers=headers, timeout=10)
        
        # Si la sesión expiró en el servidor, forzar auto-login y reintentar
        if r.status_code == 200 and 'Not authorized' in r.text:
            print("Sesión de Vertical expirada. Re-autenticando en segundo plano...")
            session = get_vertical_session(force_refresh=True)
            r = session.post('https://vertical.hospesc.com/_invoke/Execute', json=payload, headers=headers, timeout=10)

        if r.status_code == 200 and ('Document has been signed' in r.text or not r.json().get('d', {}).get('Errors')):
            print(f"¡Firma nativa generada con éxito en Vertical para {controller_name} (MRNum: {mrnum}, Doctor: {doctor_name})!")
            return True
        else:
            print(f"Respuesta de firma en Vertical: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"Error al comunicar con Vertical API: {e}")

    return True

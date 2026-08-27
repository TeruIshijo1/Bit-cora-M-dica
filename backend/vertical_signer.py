import requests
import json
import urllib3
import uuid
import os
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv()

def get_vertical_credentials():
    cookie = os.getenv('VERTICAL_ASPXAUTH')
    session_id = os.getenv('VERTICAL_SESSION_ID')
    if not cookie or not session_id:
        raise ValueError("Faltan credenciales de Vertical (VERTICAL_ASPXAUTH o VERTICAL_SESSION_ID) en el archivo .env.")
    return cookie, session_id

def sign_in_vertical_api(controller_name: str, mrnum: int, pt_num: str, pr_num: int = 257, auth_code: str = '123456', doctor_name: str = 'JOSE JOSE PRUEBA ENRIQUEZ') -> bool:
    """
    Invoca la API de Vertical (_invoke/Execute) para generar la firma nativa, token y código QR en SQL Server.
    """
    try:
        from .kh_database import get_kh_connection
    except Exception:
        from kh_database import get_kh_connection

    conn = get_kh_connection()
    if not conn:
        return False

    c_name, c_key, c_id, pt_id = 'PC', pt_num, str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = ?", (pt_num,))
        meta_row = cursor.fetchone()
        
        cursor.execute("SELECT TOP 1 PCNum FROM PC WHERE PTNum = ? ORDER BY PCNum DESC", (pt_num,))
        pc_row = cursor.fetchone()

        c_key = str(pc_row[0]) if pc_row and pc_row[0] else (str(meta_row[1]) if meta_row and meta_row[1] else str(pt_num))
        c_id = str(meta_row[2]) if meta_row and meta_row[2] else str(uuid.uuid4()).upper()
        pt_id = str(meta_row[3]) if meta_row and meta_row[3] else str(uuid.uuid4()).upper()
    except Exception as e:
        print(f"Error fetching metadata for Vertical sign: {e}")
    finally:
        conn.close()

    pk_field = f"MRNum_{controller_name.replace('MR_', '')}" if controller_name != 'MR_NE_URG' else 'MRNum_NE_URG'
    if controller_name == 'MR_CI_ETE_CARD':
        pk_field = 'MRNum_CI_ETE_CARD'
    elif controller_name == 'MR_CI_EED':
        pk_field = 'MRNum_CI_EED'

    cookie, session_id = get_vertical_credentials()
    cookies = {
        'ASP.NET_SessionId': session_id,
        '.ASPXAUTH': cookie
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': 'https://vertical.hospesc.com',
        'Referer': 'https://vertical.hospesc.com/pages/pn_ip'
    }

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
                { "Name": "Parameters_PRNum", "NewValue": int(pr_num), "Modified": True, "ReadOnly": True },
                { "Name": "Parameters_AuthorizationCode", "NewValue": str(auth_code), "Modified": True, "ReadOnly": True },
                { "Name": "Parameters_PRNum_auto_alias_", "NewValue": str(doctor_name), "Modified": True, "ReadOnly": True }
            ],
            "ContextKey": controller_name.lower().replace('_', '-'),
            "Controller": controller_name,
            "View": "editForm1"
        }
    }

    try:
        r = requests.post('https://vertical.hospesc.com/_invoke/Execute', json=payload, cookies=cookies, headers=headers, verify=False, timeout=10)
        if r.status_code == 200 and 'Document has been signed' in r.text:
            print(f"Vertical API successfully signed {controller_name} row {mrnum}!")
            return True
        else:
            print(f"Vertical API response: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"Error calling Vertical API: {e}")

    return False

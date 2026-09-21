import requests
import json
import urllib3
import uuid
import os
import re
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


_TABLES_CACHE = None

def get_all_clinical_tables() -> list[str]:
    """
    Retorna la lista en caché de todas las tablas clínicas de expediente (MR_...) en SQL Server.
    """
    global _TABLES_CACHE
    if _TABLES_CACHE is not None:
        return _TABLES_CACHE

    try:
        from .kh_database import get_kh_connection
    except Exception:
        from kh_database import get_kh_connection

    conn = get_kh_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME LIKE 'MR_%' 
                  AND TABLE_NAME NOT LIKE 'MRDS%' 
                  AND TABLE_NAME NOT LIKE 'MRLY%' 
                  AND TABLE_NAME NOT IN ('MRFP', 'MRUS')
                ORDER BY TABLE_NAME
            """)
            _TABLES_CACHE = [r[0] for r in cur.fetchall()]
            return _TABLES_CACHE
        except Exception as e:
            print(f"Error consultando tablas clínicas de SQL Server: {e}")
        finally:
            conn.close()

    _TABLES_CACHE = [
        'MR_02_CI_TRATAMIENTO_QUIRURGICO',
        'MR_08_CI_DIAGNOSTICO_ADMISION_CONTI',
        'MR_24_HOJA_EVOL',
        'MR_26_01',
        'MR_CI_APA',
        'MR_CI_AUT_TRANS_HEMO',
        'MR_CI_CC',
        'MR_CI_CES',
        'MR_CI_EED',
        'MR_CI_EMI',
        'MR_CI_ETE_CARD',
        'MR_CI_HISTERECTOMIA',
        'MR_CI_NO_REANIMACION',
        'MR_CI_OI',
        'MR_CI_PQ',
        'MR_CI_REANIMACION',
        'MR_CI_RGO_CE',
        'MR_CI_RGO_HU',
        'MR_CI_TINA',
        'MR_ERC_HOS',
        'MR_EV_HOSP',
        'MR_HC_HOS',
        'MR_HC_URG',
        'MR_LV_SPI',
        'MR_MR_CI_HOSP',
        'MR_N_POST_OP',
        'MR_NE_URG',
        'MR_PLT_79',
        'MR_RCE_Q',
        'MR_RPS_FQ',
        'MR_RTOE_PACE',
        'MR_RTOE_RPA',
        'MR_SOL_DIET',
        'MR_SOL_OP',
        'MR_TERM_EMB',
        'MR_URGENCIAS',
        'MR_VRA_HOS'
    ]
    return _TABLES_CACHE


def resolve_vertical_controller_and_pk(codigo_formato: str) -> tuple[str, str]:
    """
    MOTOR UNIVERSAL DE RESOLUCIÓN DE CONTROLADORES PARA CUALQUIER FORMATO CLÍNICO (PRESENTE O FUTURO).
    Resuelve el nombre exacto de tabla/controlador en SQL Server y su Primary Key (PK).
    """
    import re
    c = (codigo_formato or "").strip().upper()
    if not c:
        raise ValueError("Código de formato obligatorio")

    DIRECT_MAP = {
        'HE-DIRMED-CONSUL-PLT-02': ('MR_02_CI_TRATAMIENTO_QUIRURGICO', 'MRNum_02_CI_TRATAMIENTO_QUIRURGICO'),
        '02': ('MR_02_CI_TRATAMIENTO_QUIRURGICO', 'MRNum_02_CI_TRATAMIENTO_QUIRURGICO'),
        'HE-DIRMED-CONSUL-PLT-04': ('MR_CI_CC', 'MRNum_CI_CC'),
        '04': ('MR_CI_CC', 'MRNum_CI_CC'),
        'HE-DIRMED-CONSUL-PLT-08': ('MR_08_CI_DIAGNOSTICO_ADMISION_CONTI', 'MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI'),
        '08': ('MR_08_CI_DIAGNOSTICO_ADMISION_CONTI', 'MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI'),
        'HE-DIRMED-CONSUL-PLT-12': ('MR_CI_RGO_HU', 'MRNum_CI_RGO_HU'),
        '12': ('MR_CI_RGO_HU', 'MRNum_CI_RGO_HU'),
        'HE-DIRMED-CONSUL-PLT-15': ('MR_CI_CES', 'MRNum_CI_CES'),
        '15': ('MR_CI_CES', 'MRNum_CI_CES'),
        'HE-DIRMED-CONSUL-PLT-24': ('MR_24_HOJA_EVOL', 'MRNum_24_HOJA_EVOL'),
        '24': ('MR_24_HOJA_EVOL', 'MRNum_24_HOJA_EVOL'),
        'HE-DIRMED-CONSUL-PLT-25': ('MR_CI_RGO_CE', 'MRNum_CI_RGO_CE'),
        '25': ('MR_CI_RGO_CE', 'MRNum_CI_RGO_CE'),
        'HE-DIRMED-CONSUL-PLT-26/01': ('MR_26_01', 'MRNum_26_01'),
        '26/01': ('MR_26_01', 'MRNum_26_01'),
        '26': ('MR_26_01', 'MRNum_26_01'),
        'HE-DIRMED-CONSUL-PLT-32/01': ('MR_CI_ETE_CARD', 'MRNum_CI_ETE_CARD'),
        '32/01': ('MR_CI_ETE_CARD', 'MRNum_CI_ETE_CARD'),
        '32': ('MR_CI_ETE_CARD', 'MRNum_CI_ETE_CARD'),
        'HE-DIRMED-CONSUL-PLT-34/01': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        'HE-DIRMED-CONSUL-PLT-34': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        'HE-DIRMED-SINPRO-PLT-34/01': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        '34/01': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        '34': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        'HE-DIRMED-CONSUL-PLT-36': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        '36': ('MR_CI_EMI', 'MRNum_CI_EMI'),
        'HE-DIRMED-CONSUL-PLT-79': ('MR_PLT_79', 'MRNum_PLT_79'),
        '79': ('MR_PLT_79', 'MRNum_PLT_79'),
        'HE-DIRMED-CONSUL-PLT-24': ('MR_24_HOJA_EVOL', 'MRNum_24_HOJA_EVOL'),
        'HE-DIRMED-NOTAS-HOS-24': ('MR_24_HOJA_EVOL', 'MRNum_24_HOJA_EVOL'),
        'PLT-24': ('MR_24_HOJA_EVOL', 'MRNum_24_HOJA_EVOL'),
        '24': ('MR_24_HOJA_EVOL', 'MRNum_24_HOJA_EVOL'),
        'HE-DIRMED-SINPRO-PLT-87/01': ('MR_NE_URG', 'MRNum_NE_URG'),
        'HE-DIRMED-NOTAS-URG-87/01': ('MR_NE_URG', 'MRNum_NE_URG'),
        '87/01': ('MR_NE_URG', 'MRNum_NE_URG'),
        '87': ('MR_NE_URG', 'MRNum_NE_URG'),
        'HE-DIRMED-CONSUL-PLT-EED': ('MR_CI_EED', 'MRNum_CI_EED'),
        'EED': ('MR_CI_EED', 'MRNum_CI_EED'),
        'HE-DIRMED-NOTAS-HOS-HC': ('MR_HC_HOS', 'MRNum_HC_HOS'),
        'HE-DIRMED-NOTAS-URG-HC': ('MR_HC_URG', 'MRNum_HC_URG'),
        'HE-DIRMED-NOTAS-QXR-POST': ('MR_N_POST_OP', 'MRNum_N_POST_OP'),
        'HE-DIRMED-NOTAS-HOS-EV': ('MR_EV_HOSP', 'MRNum_EV_HOSP'),
        'HE-DIRMED-CONSUL-PLT-APA': ('MR_CI_APA', 'MRNum_CI_APA'),
        'HE-DIRMED-CONSUL-PLT-CC': ('MR_CI_CC', 'MRNum_CI_CC'),
        'HE-DIRMED-CONSUL-PLT-CES': ('MR_CI_CES', 'MRNum_CI_CES'),
        'HE-DIRMED-CONSUL-PLT-PQ': ('MR_CI_PQ', 'MRNum_CI_PQ'),
        'HE-DIRMED-CONSUL-PLT-HOSP': ('MR_MR_CI_HOSP', 'MRNum_MR_CI_HOSP'),
        'HE-DIRMED-SINPRO-PLT-43': ('MR_CI_OI', 'MRNum_CI_OI'),
        'HE-DIRMED-CONSUL-PLT-43': ('MR_CI_OI', 'MRNum_CI_OI'),
        '43': ('MR_CI_OI', 'MRNum_CI_OI'),
        'PLT-43': ('MR_CI_OI', 'MRNum_CI_OI'),
        'HE-DIRMED-CONSUL-PLT-11': ('MR_CI_NO_REANIMACION', 'MRNum_CI_NO_REANIMACION'),
        '11': ('MR_CI_NO_REANIMACION', 'MRNum_CI_NO_REANIMACION'),
        'PLT-11': ('MR_CI_NO_REANIMACION', 'MRNum_CI_NO_REANIMACION'),
        'HE-DIRMED-CONSUL-PLT-19': ('MR_CI_HISTERECTOMIA', 'MRNum_CI_HISTERECTOMIA'),
        '19': ('MR_CI_HISTERECTOMIA', 'MRNum_CI_HISTERECTOMIA'),
        'PLT-19': ('MR_CI_HISTERECTOMIA', 'MRNum_CI_HISTERECTOMIA'),
        'HE-DIRMED-SINPRO-PLT-15': ('MR_EV_HOSP', 'MRNum_EV_HOSP'),
        'SINPRO-PLT-15': ('MR_EV_HOSP', 'MRNum_EV_HOSP'),
        'PLT-EV-15': ('MR_EV_HOSP', 'MRNum_EV_HOSP'),
        'HE-DIRMED-CONSUL-PLT-06': ('MR_CI_APA', 'MRNum_CI_APA'),
        '06': ('MR_CI_APA', 'MRNum_CI_APA'),
        'PLT-06': ('MR_CI_APA', 'MRNum_CI_APA'),
        'HE-DIRMED-CONSUL-PLT-07': ('MR_CI_PQ', 'MRNum_CI_PQ'),
        '07': ('MR_CI_PQ', 'MRNum_CI_PQ'),
        'PLT-07': ('MR_CI_PQ', 'MRNum_CI_PQ'),
        'CI_PQ': ('MR_CI_PQ', 'MRNum_CI_PQ'),
    }

    # 1. Búsqueda directa en diccionario rápido
    if c in DIRECT_MAP:
        return DIRECT_MAP[c]

    # Preserve documented historical aliases, never infer a different clinical act.
    alias = re.fullmatch(r"(?:HE-DIRMED-(?:SINPRO|CONSUL)-)?PLT-([A-Z0-9/]+)", c)
    if alias and alias.group(1) in DIRECT_MAP:
        return DIRECT_MAP[alias.group(1)]
    known_tables = {table: pk for table, pk in DIRECT_MAP.values()}
    if c in known_tables:
        return c, known_tables[c]
    # Exact schema-discovered names retain the existing universal-format route.
    # Invalid identifiers never reach SQL interpolation.
    if re.fullmatch(r"MR_[A-Z0-9_]+", c) and c in get_all_clinical_tables():
        return c, f"MRNum_{c[3:]}"
    raise ValueError("Formato no registrado: no se puede determinar su documento Vertical")


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
            if cedula and cedula.strip():
                cur.execute("SELECT PRNum, MedicalRecordAuthorizationCode FROM PR WHERE LTRIM(RTRIM(Identification)) = ?", (cedula.strip(),))
            elif doctor_name and doctor_name.strip():
                cur.execute("SELECT PRNum, MedicalRecordAuthorizationCode FROM PR WHERE LTRIM(RTRIM(FullName)) = ? OR LTRIM(RTRIM(Name)) = ?", (doctor_name.strip(), doctor_name.strip()))
            else:
                raise RuntimeError("Identidad médica no especificada para Vertical")
            rows = cur.fetchall()
            if len(rows) != 1 or not rows[0][0] or not str(rows[0][1] or "").strip():
                raise RuntimeError("Médico Vertical inexistente, ambiguo o sin autorización de firma; revisar su perfil")
            return int(rows[0][0]), str(rows[0][1]).strip()
        finally:
            conn.close()

    raise RuntimeError("Vertical no disponible para confirmar la identidad del médico")


def sign_in_vertical_api(
    controller_name: str,
    mrnum: int,
    pt_num: str,
    pr_num: int = None,
    auth_code: str = None,
    doctor_name: str = None,
    operation_id: str = None,
    doctor_cedula: str = None,
) -> bool:
    """
    Invoca la API nativa de Vertical (_invoke/Execute -> SignRecord) con auto-renovación de sesión y resolución dinámica.
    Vertical genera su propia cadena/QR; se confirma su persistencia nativa.
    """
    try:
        from .kh_database import get_kh_connection
    except Exception:
        from kh_database import get_kh_connection

    if not re.fullmatch(r"MR_[A-Z0-9_]+", controller_name or "") or int(mrnum) <= 0:
        raise ValueError("Destino clínico de firma inválido")

    # Resolver PR y PIN automáticamente si no fueron enviados
    if pr_num is None or auth_code is None:
        resolved_pr, resolved_pin = resolve_doctor_pr_and_pin(doctor_name, doctor_cedula)
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

    # Resolver nombre de campo PK de forma universal
    pk_field = f"MRNum_{controller_name.replace('MR_', '')}"
    conn_chk = get_kh_connection()
    if conn_chk:
        try:
            cur_chk = conn_chk.cursor()
            cur_chk.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? AND COLUMN_NAME LIKE 'MRNum%'", (controller_name,))
            pk_candidates = [r[0] for r in cur_chk.fetchall() if r[0] != 'MRNum_']
            if pk_candidates:
                pk_field = pk_candidates[0]
        except Exception:
            pass
        finally:
            conn_chk.close()

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

    # Idempotency check happens before calling Vertical. The SQL status is only
    # changed after the native API confirms the signature.
    conn_db = get_kh_connection()
    if not conn_db:
        raise RuntimeError(f"Vertical no disponible [{operation_id or 'uncorrelated'}]")
    try:
        cur_db = conn_db.cursor()
        cur_db.execute(
            f"SELECT SignedBy, MR_ST, ESignature FROM {controller_name} WHERE {pk_field} = ? AND PTNum = ?",
            (mrnum, pt_num),
        )
        signed_row = cur_db.fetchone()
        if (
            signed_row
            and str(signed_row[0] or "").strip() == str(doctor_name or "").strip()
            and str(signed_row[1] or "").strip() == "SG"
            and len(signed_row) > 2 and signed_row[2]
            and str(signed_row[2]) != "FIRMADO_BIOMETRICAMENTE"
        ):
            return True
        conn_db.rollback()
    except Exception:
        conn_db.rollback()
        raise
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

        # The only confirmed success in the observed Vertical contract is its
        # explicit SignRecord acknowledgement. Empty/unknown JSON is ambiguous
        # and must remain retryable/reconcilable upstream.
        vertical_confirmed = (
            r.status_code == 200
            and isinstance(r.text, str)
            and "Document has been signed" in r.text
        )
        if vertical_confirmed:
            conn_confirm = get_kh_connection()
            if not conn_confirm:
                raise RuntimeError(
                    f"Vertical confirmó pero SQL Server no permitió registrar confirmación [{operation_id or 'uncorrelated'}]"
                )
            try:
                cur_confirm = conn_confirm.cursor()
                # Vertical owns its native signature and QR chain. Read it back;
                # never replace it with a marker or copy a cached signature.
                cur_confirm.execute(
                    f"SELECT SignedBy, MR_ST, ESignature FROM {controller_name} WHERE {pk_field} = ? AND PTNum = ?",
                    (mrnum, pt_num),
                )
                confirmed = cur_confirm.fetchone()
                if not (confirmed and len(confirmed) > 2
                        and str(confirmed[0] or "").strip() == str(doctor_name or "").strip()
                        and str(confirmed[1] or "").strip() == "SG"
                        and confirmed[2] and str(confirmed[2]) != "FIRMADO_BIOMETRICAMENTE"):
                    raise RuntimeError("Vertical respondió pero aún no confirma su firma nativa para este médico y documento")
            except Exception:
                conn_confirm.rollback()
                raise
            finally:
                conn_confirm.close()
            print(f"¡Firma nativa generada con éxito en Vertical para {controller_name} (MRNum: {mrnum}, Doctor: {doctor_name})!")
            return True
        raise RuntimeError(f"Vertical rechazó la firma [{operation_id or 'uncorrelated'}]")
    except Exception:
        raise

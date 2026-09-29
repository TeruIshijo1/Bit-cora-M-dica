import requests
import datetime as dt
import json
import urllib3
import uuid
import os
import re
import hmac
import secrets
import threading
import time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

urllib3.disable_warnings()

_vertical_session = threading.local()


class VerticalDoctorProfileError(RuntimeError):
    """The HES doctor cannot be mapped unambiguously to an authorized Vertical profile."""


class VerticalSignatureConfirmationPending(RuntimeError):
    """Vertical acknowledged SignRecord but its native row is not yet verifiable."""

    requires_reconciliation = True
    retryable = False


class VerticalSignatureOutcomeUnknown(VerticalSignatureConfirmationPending):
    """The request may have reached Vertical, so only native readback is safe."""


class VerticalSignatureAcknowledgedPending(VerticalSignatureConfirmationPending):
    """SignRecord explicitly succeeded; only the exact native row is pending."""


# Vertical's HTTP acknowledgement may precede visibility of its SQL row.
# Keep the request bounded, then reconcile by reading only that exact row.
_NATIVE_CONFIRMATION_DELAYS = (0.2, 0.4, 0.8, 1.2, 1.6)
_NATIVE_CLOCK_SKEW = dt.timedelta(seconds=5)


def _normalized_identity(value) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _native_signature_confirmed(
    row,
    *,
    doctor_name: str,
    resolved_pr: int,
    identity_field: str | None,
    pr_field: str | None,
    not_before: dt.datetime | None = None,
    not_after: dt.datetime | None = None,
    allow_registered_urgency_signature: bool = False,
) -> bool:
    """Validate Vertical's native signature without treating its service user as the physician.

    ``SignedBy`` records the authenticated Vertical account (for this integration,
    ``Bitacora_SIS``).  The physician belongs to the clinical record's doctor
    field or, when populated, ``PRNum``.  HES still provides the cryptographic
    identity evidence; this check only confirms delivery to Vertical.
    """
    return _native_signature_confirmation_issue(
        row,
        doctor_name=doctor_name,
        resolved_pr=resolved_pr,
        identity_field=identity_field,
        pr_field=pr_field,
        not_before=not_before,
        not_after=not_after,
        allow_registered_urgency_signature=allow_registered_urgency_signature,
    ) is None


def _native_signature_confirmation_issue(
    row,
    *,
    doctor_name: str,
    resolved_pr: int,
    identity_field: str | None,
    pr_field: str | None,
    not_before: dt.datetime | None = None,
    not_after: dt.datetime | None = None,
    allow_registered_urgency_signature: bool = False,
) -> str | None:
    """Return a non-sensitive reason when the exact native row is not confirmed."""
    if not row or len(row) < 4:
        return "NATIVE_ROW_NOT_FOUND"
    signed_by, signed_on, status, native_chain = row[:4]
    if not str(signed_by or "").strip():
        return "NATIVE_SIGNED_BY_MISSING"
    if signed_on is None:
        return "NATIVE_SIGNED_ON_MISSING"
    if isinstance(signed_on, dt.datetime):
        comparable_signed_on = signed_on
        if comparable_signed_on.tzinfo is not None:
            comparable_signed_on = comparable_signed_on.astimezone(ZoneInfo("America/Mexico_City"))
        comparable_signed_on = comparable_signed_on.replace(tzinfo=None)
        comparison_start = not_before
        if comparison_start is not None and comparison_start.tzinfo is not None:
            comparison_start = comparison_start.astimezone(ZoneInfo("America/Mexico_City")).replace(tzinfo=None)
        comparison_end = not_after
        if comparison_end is not None and comparison_end.tzinfo is not None:
            comparison_end = comparison_end.astimezone(ZoneInfo("America/Mexico_City")).replace(tzinfo=None)
        # SQL Server stores local timestamps without an offset.  Permit small
        # clock/transport skew, but never reconcile against an older signature.
        if comparison_start is not None and comparable_signed_on < comparison_start - _NATIVE_CLOCK_SKEW:
            return "NATIVE_SIGNATURE_PREDATES_OPERATION"
        if comparison_end is not None and comparable_signed_on > comparison_end + _NATIVE_CLOCK_SKEW:
            return "NATIVE_SIGNATURE_POSTDATES_ACKNOWLEDGEMENT"
    native_status = str(status or "").strip().upper()
    # MR_NE_URG has been observed to retain RG after an acknowledged
    # SignRecord while persisting a new SignedOn and native ESignature. Only
    # that controller, an explicit acknowledgement and a bounded operation
    # timestamp may use this exception; the other proof checks still apply.
    registered_urgency = (
        allow_registered_urgency_signature
        and native_status == "RG"
        and not_before is not None
        and isinstance(signed_on, dt.datetime)
    )
    if native_status != "SG" and not registered_urgency:
        return "NATIVE_STATUS_NOT_SIGNED"
    chain = str(native_chain or "").strip()
    if not chain or chain == "FIRMADO_BIOMETRICAMENTE":
        return "NATIVE_CHAIN_MISSING"

    offset = 4
    identity_matches: list[bool] = []
    if identity_field:
        record_doctor = row[offset] if len(row) > offset else None
        offset += 1
        if str(record_doctor or "").strip():
            matches_name = _normalized_identity(record_doctor) == _normalized_identity(doctor_name)
            try:
                matches_pr = int(record_doctor) == int(resolved_pr)
            except (TypeError, ValueError):
                matches_pr = False
            identity_matches.append(matches_name or matches_pr)
    if pr_field:
        record_pr = row[offset] if len(row) > offset else None
        if record_pr not in (None, ""):
            try:
                identity_matches.append(int(record_pr) == int(resolved_pr))
            except (TypeError, ValueError):
                identity_matches.append(False)

    if identity_matches:
        return None if any(identity_matches) else "NATIVE_PHYSICIAN_MISMATCH"
    # SignedBy is the technical Vertical account, not the medical identity.
    return "NATIVE_PHYSICIAN_LINK_MISSING"


def configure_vertical_doctor_signature_profile(
    doctor_name: str,
    cedula: str,
    authorization_code: str | None = None,
    *,
    modified_by: str = "Bitacora_HES",
) -> dict:
    """Enable signing for one existing PR row without creating catalog records.

    ``V_MRPR`` is a view backed by ``PR``. The physician must already exist in
    Vertical; initial biometric enrollment only establishes/verifies the
    six-digit authorization code used by the native ``SignRecord`` command.
    The secret is never returned.
    """
    code = str(authorization_code or "").strip()
    if code and not re.fullmatch(r"\d{6}", code):
        raise VerticalDoctorProfileError(
            "El código de autorización de Vertical debe tener exactamente 6 dígitos"
        )

    try:
        from .kh_database import get_kh_connection
    except Exception:
        from kh_database import get_kh_connection

    conn = get_kh_connection()
    if not conn:
        raise RuntimeError("Vertical no disponible para preparar la firma del médico")
    try:
        cur = conn.cursor()
        rows = []
        if cedula and cedula.strip():
            cur.execute(
                "SELECT PRNum, MedicalRecordAuthorizationCode, Active FROM PR WITH (UPDLOCK, HOLDLOCK) "
                "WHERE LTRIM(RTRIM(Identification)) = ?",
                (cedula.strip(),),
            )
            rows = cur.fetchall()
            if len(rows) > 1:
                raise VerticalDoctorProfileError(
                    "La cédula corresponde a más de un médico en Vertical"
                )

        if not rows and doctor_name and doctor_name.strip():
            normalized_name = doctor_name.strip()
            cur.execute(
                "SELECT PRNum, MedicalRecordAuthorizationCode, Active FROM PR WITH (UPDLOCK, HOLDLOCK) "
                "WHERE LTRIM(RTRIM(FullName)) = ? OR LTRIM(RTRIM(Name)) = ?",
                (normalized_name, normalized_name),
            )
            rows = cur.fetchall()

        if len(rows) != 1 or not rows[0][0]:
            raise VerticalDoctorProfileError(
                "No se encontró un único médico ya registrado en Vertical; revise nombre y cédula"
            )
        pr_num, existing_code, active = rows[0]
        if not bool(active):
            raise VerticalDoctorProfileError(
                "El médico existe en Vertical, pero su registro está inactivo"
            )

        configured = str(existing_code or "").strip()
        if configured:
            conn.rollback()
            return {"pr_num": int(pr_num), "already_configured": True}

        if not code:
            for _ in range(20):
                candidate = f"{secrets.randbelow(1_000_000):06d}"
                cur.execute(
                    "SELECT TOP 1 PRNum FROM PR WITH (UPDLOCK, HOLDLOCK) "
                    "WHERE MedicalRecordAuthorizationCode = ? AND PRNum <> ?",
                    (candidate, int(pr_num)),
                )
                if cur.fetchone() is None:
                    code = candidate
                    break
            if not code:
                raise RuntimeError("No fue posible generar una autorización única para Vertical")

        cur.execute(
            "UPDATE PR SET MedicalRecordAuthorizationCode = ?, ModifiedBy = ?, ModifiedOn = GETDATE() "
            "WHERE PRNum = ? AND NULLIF(LTRIM(RTRIM(MedicalRecordAuthorizationCode)), '') IS NULL",
            (code, str(modified_by or "Bitacora_HES")[:100], int(pr_num)),
        )
        cur.execute(
            "SELECT MedicalRecordAuthorizationCode FROM PR WHERE PRNum = ?",
            (int(pr_num),),
        )
        confirmed = cur.fetchone()
        if not confirmed or not hmac.compare_digest(str(confirmed[0] or "").strip(), code):
            raise RuntimeError("Vertical no confirmó la configuración de firma del médico")
        conn.commit()
        return {"pr_num": int(pr_num), "already_configured": False}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_vertical_session(force_refresh: bool = False) -> requests.Session:
    """
    Obtiene una sesión HTTP autenticada con Vertical.
    Si la sesión expiró o no existe, realiza login automático transparente contra _invoke/Login.
    """
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    cached_session = getattr(_vertical_session, "session", None)
    if cached_session is not None and not force_refresh:
        return cached_session

    user = os.getenv('VERTICAL_SYSTEM_USER')
    password = os.getenv('VERTICAL_SYSTEM_PASSWORD')
    if not user or not password:
        raise RuntimeError("Faltan credenciales de la cuenta técnica de Vertical")

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
            _vertical_session.session = session
            return session
    except requests.RequestException as exc:
        raise ConnectionError("Vertical no disponible para autenticar la sesión técnica") from exc
    except Exception as exc:
        raise RuntimeError("Vertical devolvió una respuesta de autenticación inválida") from exc

    raise RuntimeError("Vertical rechazó la sesión técnica de firma")


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
        'HE-DIRMED-CONSUL-PLT-09': ('MR_CI_AUT_TRANS_HEMO', 'MRNum_CI_AUT_TRANS_HEMO'),
        'HE-DIRMED-CONSUL-PLT-9': ('MR_CI_AUT_TRANS_HEMO', 'MRNum_CI_AUT_TRANS_HEMO'),
        '09': ('MR_CI_AUT_TRANS_HEMO', 'MRNum_CI_AUT_TRANS_HEMO'),
        '9': ('MR_CI_AUT_TRANS_HEMO', 'MRNum_CI_AUT_TRANS_HEMO'),
        'PLT-09': ('MR_CI_AUT_TRANS_HEMO', 'MRNum_CI_AUT_TRANS_HEMO'),
        'PLT-9': ('MR_CI_AUT_TRANS_HEMO', 'MRNum_CI_AUT_TRANS_HEMO'),
        'CI_AUT_TRANS_HEMO': ('MR_CI_AUT_TRANS_HEMO', 'MRNum_CI_AUT_TRANS_HEMO'),
        'AUT_TRANS_HEMO': ('MR_CI_AUT_TRANS_HEMO', 'MRNum_CI_AUT_TRANS_HEMO'),
        'HE-DIRMED-SINPRO-PLT-16': ('MR_ERC_HOS', 'MRNum_ERC_HOS'),
        'HE-DIRMED-SINPRO-PLT-16/01': ('MR_ERC_HOS', 'MRNum_ERC_HOS'),
        'SINPRO-PLT-16': ('MR_ERC_HOS', 'MRNum_ERC_HOS'),
        '16': ('MR_ERC_HOS', 'MRNum_ERC_HOS'),
        'PLT-16': ('MR_ERC_HOS', 'MRNum_ERC_HOS'),
        'MR_ERC_HOS': ('MR_ERC_HOS', 'MRNum_ERC_HOS'),
        'ERC_HOS': ('MR_ERC_HOS', 'MRNum_ERC_HOS'),
        'EGRESO_RESUMEN_16': ('MR_ERC_HOS', 'MRNum_ERC_HOS'),
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

    # Los formatos futuros de Vertical suelen conservar el contrato
    # institucional ``...-PLT-XX[/YY]`` y su tabla ``MR_XX[_YY]``.  No es
    # seguro adivinar cualquier identificador, pero sí podemos resolver este
    # patrón contra el catálogo real de tablas: de esa forma un formato nuevo
    # no depende de editar una lista Python para poder consultarse e
    # integrarse al expediente universal.
    format_match = re.search(
        r"(?:^|-)PLT-([A-Z0-9]+)(?:/([A-Z0-9]+))?$",
        c,
    )
    if format_match:
        base, variant = format_match.groups()
        table_candidates = [
            f"MR_{base}_{variant}" if variant else "",
            f"MR_{base}",
        ]
        available_tables = {str(table).upper(): str(table) for table in get_all_clinical_tables()}
        for candidate in table_candidates:
            if candidate and candidate.upper() in available_tables:
                table = available_tables[candidate.upper()]
                return table, f"MRNum_{table[3:]}"

    # Exact schema-discovered names retain the existing universal-format route.
    # Invalid identifiers never reach SQL interpolation.
    if re.fullmatch(r"MR_[A-Z0-9_]+", c) and c in get_all_clinical_tables():
        return c, f"MRNum_{c[3:]}"
    raise ValueError("Formato no registrado: no se puede determinar su documento Vertical")


def resolve_doctor_pr_and_pin(doctor_name: str, cedula: str = None) -> tuple[int, str]:
    """
    Busca al médico en el catálogo V_MRPR de Vertical para obtener su PRNum
    oficial y el código que Vertical exige al ejecutar SignRecord.

    El código se utiliza sólo en memoria para completar la solicitud nativa de
    Vertical: no se persiste en HES, no se incluye en auditoría y no se registra.
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
                cur.execute(
                    "SELECT PRNum, MedicalRecordAuthorizationCode FROM V_MRPR "
                    "WHERE LTRIM(RTRIM(Identification)) = ?",
                    (cedula.strip(),),
                )
                rows = cur.fetchall()
                if len(rows) == 1:
                    if not rows[0][0] or not str(rows[0][1] or "").strip():
                        raise VerticalDoctorProfileError(
                            "El perfil médico de Vertical no tiene autorización de firma"
                        )
                    return int(rows[0][0]), str(rows[0][1]).strip()
                if len(rows) > 1:
                    raise VerticalDoctorProfileError(
                        "La cédula corresponde a más de un perfil médico en Vertical"
                    )

            # Algunas instalaciones históricas de Vertical guardan una clave
            # interna (o varias cédulas) en Identification. El nombre sólo es
            # un respaldo seguro cuando la coincidencia es exacta y única.
            if doctor_name and doctor_name.strip():
                normalized_name = doctor_name.strip()
                cur.execute(
                    "SELECT PRNum, MedicalRecordAuthorizationCode FROM V_MRPR "
                    "WHERE LTRIM(RTRIM(FullName)) = ? OR LTRIM(RTRIM(Name)) = ?",
                    (normalized_name, normalized_name),
                )
                rows = cur.fetchall()
                if len(rows) == 1 and rows[0][0] and str(rows[0][1] or "").strip():
                    return int(rows[0][0]), str(rows[0][1]).strip()

            if not (cedula and cedula.strip()) and not (doctor_name and doctor_name.strip()):
                raise VerticalDoctorProfileError("Identidad médica no especificada para Vertical")
            raise VerticalDoctorProfileError(
                "Médico Vertical inexistente, ambiguo o sin autorización de firma; revisar su perfil"
            )
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
    not_before: dt.datetime | None = None,
    not_after: dt.datetime | None = None,
    confirmation_only: bool = False,
    acknowledged_by_vertical: bool = False,
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
        try:
            resolved_pr, resolved_pin = resolve_doctor_pr_and_pin(doctor_name, doctor_cedula)
        except Exception as exc:
            if confirmation_only:
                raise VerticalSignatureConfirmationPending("NATIVE_PHYSICIAN_LOOKUP_UNAVAILABLE") from exc
            raise
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

    # Resolver nombre de campo PK y vínculo de identidad de forma universal.
    pk_field = f"MRNum_{controller_name.replace('MR_', '')}"
    identity_field = None
    pr_field = None
    conn_chk = get_kh_connection()
    if conn_chk:
        try:
            cur_chk = conn_chk.cursor()
            cur_chk.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?",
                (controller_name,),
            )
            table_columns = [str(r[0]) for r in cur_chk.fetchall()]
            pk_candidates = [name for name in table_columns if name.upper().startswith("MRNUM") and name.upper() != "MRNUM_"]
            exact_pk = next((name for name in pk_candidates if name.upper() == pk_field.upper()), None)
            if exact_pk:
                pk_field = exact_pk
            elif len(pk_candidates) == 1:
                pk_field = pk_candidates[0]
            else:
                raise ValueError("NATIVE_PRIMARY_KEY_UNRESOLVED")
            column_map = {name.upper(): name for name in table_columns}
            for candidate in ("N_MEDICO", "NOMBRE_MEDICO", "MEDICO_TRATANTE", "MEDICO"):
                if candidate in column_map:
                    identity_field = column_map[candidate]
                    break
            pr_field = column_map.get("PRNUM")
        except Exception as exc:
            issue = (
                "NATIVE_PRIMARY_KEY_UNRESOLVED"
                if isinstance(exc, ValueError) and str(exc) == "NATIVE_PRIMARY_KEY_UNRESOLVED"
                else "NATIVE_SCHEMA_UNAVAILABLE"
            )
            if confirmation_only:
                raise VerticalSignatureConfirmationPending(issue) from exc
            raise RuntimeError(issue) from exc
        finally:
            conn_chk.close()

    signature_fields = ["SignedBy", "SignedOn", "MR_ST", "ESignature"]
    if identity_field:
        signature_fields.append(identity_field)
    if pr_field:
        signature_fields.append(pr_field)
    signature_select = ", ".join(signature_fields)

    def read_native_signature():
        connection = get_kh_connection()
        if not connection:
            raise RuntimeError(
                f"Vertical no disponible para confirmar su firma [{operation_id or 'uncorrelated'}]"
            )
        try:
            cursor = connection.cursor()
            cursor.execute(
                f"SELECT {signature_select} FROM {controller_name} "
                f"WHERE {pk_field} = ? AND PTNum = ?",
                (mrnum, pt_num),
            )
            return cursor.fetchone()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    native_acknowledged = bool(confirmation_only and acknowledged_by_vertical)

    def confirmation_issue(row) -> str | None:
        return _native_signature_confirmation_issue(
            row,
            doctor_name=doctor_name,
            resolved_pr=resolved_pr,
            identity_field=identity_field,
            pr_field=pr_field,
            not_before=not_before,
            not_after=not_after,
            allow_registered_urgency_signature=(
                controller_name == "MR_NE_URG" and native_acknowledged
            ),
        )

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

    # Only reconciliation of an acknowledged operation may accept a native
    # signature already present before this call.
    try:
        native_before = read_native_signature()
        issue = confirmation_issue(native_before)
    except Exception as exc:
        if confirmation_only:
            raise VerticalSignatureConfirmationPending("NATIVE_READ_UNAVAILABLE") from exc
        raise
    if confirmation_only:
        if issue is None:
            return True
        raise VerticalSignatureConfirmationPending(issue)

    # A previous signature on this row is not proof that this newly captured
    # medical act was delivered. SignRecord must acknowledge this operation and
    # produce a new native signature timestamp or chain.
    prior_signature = (
        (native_before[1], native_before[3])
        if native_before and len(native_before) >= 4
        and native_before[1] is not None and str(native_before[3] or "").strip()
        else None
    )

    session = get_vertical_session(force_refresh=False)
    try:
        try:
            r = session.post('https://vertical.hospesc.com/_invoke/Execute', json=payload, headers=headers, timeout=10)
        except requests.RequestException as exc:
            raise VerticalSignatureOutcomeUnknown("VERTICAL_RESPONSE_UNCERTAIN") from exc
        
        # Si la sesión expiró en el servidor, forzar auto-login y reintentar
        response_text = str(getattr(r, "text", "") or "")
        if r.status_code in (401, 403) or (r.status_code == 200 and 'Not authorized' in response_text):
            print("Sesión de Vertical expirada. Re-autenticando en segundo plano...")
            session = get_vertical_session(force_refresh=True)
            try:
                r = session.post('https://vertical.hospesc.com/_invoke/Execute', json=payload, headers=headers, timeout=10)
            except requests.RequestException as exc:
                raise VerticalSignatureOutcomeUnknown("VERTICAL_RESPONSE_UNCERTAIN") from exc
            response_text = str(getattr(r, "text", "") or "")
        if r.status_code in (401, 403) or "Not authorized" in response_text:
            raise RuntimeError("Vertical rechazó la sesión técnica de firma")

        # The only confirmed success in the observed Vertical contract is its
        # explicit SignRecord acknowledgement. Empty/unknown JSON is ambiguous
        # and must remain retryable/reconcilable upstream.
        vertical_confirmed = (
            r.status_code == 200
            and "Document has been signed" in response_text
        )
        if vertical_confirmed:
            native_acknowledged = True
            # Vertical owns the native signature and QR chain.  Allow a brief
            # read-after-write propagation window, opening a fresh SQL session
            # each time; never replace the native chain with a local marker.
            for delay in (0, *_NATIVE_CONFIRMATION_DELAYS):
                if delay:
                    time.sleep(delay)
                try:
                    native_after = read_native_signature()
                    issue = confirmation_issue(native_after)
                    if issue is None and prior_signature == (native_after[1], native_after[3]):
                        issue = "NATIVE_SIGNATURE_UNCHANGED"
                except Exception as exc:
                    raise VerticalSignatureAcknowledgedPending("NATIVE_READ_UNAVAILABLE") from exc
                if issue is None:
                    break
            else:
                raise VerticalSignatureAcknowledgedPending(issue or "NATIVE_CONFIRMATION_PENDING")
            print(f"¡Firma nativa generada con éxito en Vertical para {controller_name} (MRNum: {mrnum}, Doctor: {doctor_name})!")
            return True
        if r.status_code == 200 or r.status_code >= 500:
            raise VerticalSignatureOutcomeUnknown("VERTICAL_RESPONSE_UNCONFIRMED")
        raise RuntimeError(f"Vertical rechazó la firma [{operation_id or 'uncorrelated'}]")
    except Exception:
        raise

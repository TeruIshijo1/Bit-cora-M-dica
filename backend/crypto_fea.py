"""ECDSA P-256 key custody and exact-key verification for HES FEA."""

from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


logger = logging.getLogger("hes.crypto_fea")
CIPHER_VERSION = "FERNET_HKDF_SHA256_V1"


class PrivateKeyDecryptionError(RuntimeError):
    """The encrypted private key cannot be opened; automatic rotation is forbidden."""


class FEAKeyStateError(RuntimeError):
    """The physician does not have one unambiguous active FEA key."""


@dataclass(frozen=True)
class SignatureResult:
    sello_digital: str
    key_id: str


class PrivateKeyCustodian:
    """Versioned custody boundary, replaceable by a future KMS/HSM adapter."""

    version = CIPHER_VERSION

    def encrypt(self, private_pem: bytes, huella_token: str) -> str:
        return Fernet(get_kdf_fernet_key(huella_token)).encrypt(private_pem).decode("ascii")

    def decrypt(self, ciphertext: str, huella_token: str) -> bytes:
        if not ciphertext:
            raise PrivateKeyDecryptionError("La llave privada FEA cifrada no existe")
        try:
            return Fernet(get_kdf_fernet_key(huella_token)).decrypt(ciphertext.encode("ascii"))
        except (InvalidToken, ValueError, TypeError) as exc:
            raise PrivateKeyDecryptionError(
                "No fue posible descifrar la llave privada FEA; se requiere intervención explícita y auditada"
            ) from exc


custodian = PrivateKeyCustodian()


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def get_hes_secret() -> str:
    secret = os.getenv("HES_HMAC_SECRET")
    if not secret:
        raise RuntimeError(
            "FATAL: HES_HMAC_SECRET no está configurado en el entorno (.env). "
            "El sistema debe fallar duro por seguridad."
        )
    return secret


def get_kdf_fernet_key(huella_token: str) -> bytes:
    if not huella_token:
        raise FEAKeyStateError("El médico no tiene huella_token para custodiar su llave FEA")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"hes-fea-salt-nom004",
        info=b"FEA_KEK_DERIVATION",
    )
    derived = hkdf.derive(huella_token.encode("utf-8") + get_hes_secret().encode("utf-8"))
    return base64.urlsafe_b64encode(derived)


def generate_ecdsa_keypair() -> tuple[bytes, bytes]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    return (
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
    )


def _new_key_id() -> str:
    return str(uuid.uuid4())


def _active_key_rows(db_session, medico_id: int):
    import models

    return db_session.query(models.HistorialLlaveFEA).filter(
        models.HistorialLlaveFEA.medico_id == medico_id,
        models.HistorialLlaveFEA.activo == True,
    ).all()


def _ensure_history_for_existing_key(db_session, medico):
    """Associate a pre-migration active public key without changing its keypair."""
    import models

    rows = _active_key_rows(db_session, medico.id)
    matching = [row for row in rows if row.public_key_pem == medico.public_key_pem]
    if len(matching) == 1:
        return matching[0]
    if rows:
        raise FEAKeyStateError("Existen llaves activas ambiguas para el médico")
    entry = models.HistorialLlaveFEA(
        key_id=_new_key_id(),
        medico_id=medico.id,
        public_key_pem=medico.public_key_pem,
        fecha_creacion=utcnow(),
        activo=True,
        estado="ACTIVA",
    )
    db_session.add(entry)
    db_session.flush()
    return entry


def ensure_medico_keys(db_session, medico):
    """Create the first key once; never rotate as error recovery."""
    import models

    locked = db_session.query(type(medico)).filter_by(id=medico.id).with_for_update().first() or medico
    has_public = bool(getattr(locked, "public_key_pem", None))
    has_private = bool(getattr(locked, "private_key_enc", None))
    if has_public != has_private:
        raise FEAKeyStateError("El par de llaves FEA está incompleto")
    if not has_public:
        token = getattr(locked, "huella_token", None)
        if not token or not getattr(locked, "fmd_template", None):
            raise FEAKeyStateError("Debe existir biometría válida antes de generar llaves FEA")
        private_pem, public_pem = generate_ecdsa_keypair()
        locked.public_key_pem = public_pem.decode("ascii")
        locked.private_key_enc = custodian.encrypt(private_pem, token)
        locked.private_key_cipher_version = CIPHER_VERSION
        entry = models.HistorialLlaveFEA(
            key_id=_new_key_id(),
            medico_id=locked.id,
            public_key_pem=locked.public_key_pem,
            fecha_creacion=utcnow(),
            activo=True,
            estado="ACTIVA",
        )
        db_session.add(entry)
        db_session.flush()
        db_session.commit()
        medico.public_key_pem = locked.public_key_pem
        medico.private_key_enc = locked.private_key_enc
        medico.private_key_cipher_version = CIPHER_VERSION
    else:
        _ensure_history_for_existing_key(db_session, locked)
        if getattr(locked, "private_key_cipher_version", None) is None:
            locked.private_key_cipher_version = CIPHER_VERSION
        db_session.commit()
        medico.public_key_pem = locked.public_key_pem
        medico.private_key_enc = locked.private_key_enc
        medico.private_key_cipher_version = locked.private_key_cipher_version
    return medico.public_key_pem, medico.private_key_enc


def get_active_key(db_session, medico):
    ensure_medico_keys(db_session, medico)
    rows = _active_key_rows(db_session, medico.id)
    if len(rows) != 1 or rows[0].public_key_pem != medico.public_key_pem:
        raise FEAKeyStateError("No existe una única llave FEA activa asociada al médico")
    return rows[0]


def firmar_documento_con_key_id(db_session, medico, canonical_payload: str | bytes) -> SignatureResult:
    key_row = get_active_key(db_session, medico)
    token = getattr(medico, "huella_token", None)
    if not token:
        raise FEAKeyStateError("El médico no tiene token de custodia FEA")
    if getattr(medico, "private_key_cipher_version", CIPHER_VERSION) != CIPHER_VERSION:
        raise FEAKeyStateError("Versión de cifrado de llave privada no soportada")
    private_pem = custodian.decrypt(getattr(medico, "private_key_enc", ""), token)
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    data = canonical_payload.encode("utf-8") if isinstance(canonical_payload, str) else canonical_payload
    signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))
    return SignatureResult(
        sello_digital="ECDSA:" + base64.b64encode(signature).decode("ascii"),
        key_id=key_row.key_id,
    )


def firmar_documento(db_session, medico, cadena_original: str | bytes) -> str:
    """Compatibility wrapper. New code must persist ``key_id`` from the result API."""
    return firmar_documento_con_key_id(db_session, medico, cadena_original).sello_digital


def _verify_single_ecdsa(public_key_pem_str: str, signature_bytes: bytes, payload: str | bytes) -> bool:
    try:
        public_key = serialization.load_pem_public_key(public_key_pem_str.encode("utf-8"))
        data = payload.encode("utf-8") if isinstance(payload, str) else payload
        public_key.verify(signature_bytes, data, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def verificar_firma(
    medico,
    cadena_original: str | bytes,
    sello_digital: str,
    fecha_firma: Optional[datetime.datetime] = None,
    db_session=None,
    *,
    key_id: Optional[str] = None,
) -> bool:
    if not sello_digital:
        return False
    if sello_digital.startswith("ECDSA:"):
        if medico is None or not key_id:
            return False
        key_row = None
        if db_session is not None and getattr(medico, "id", None) is not None:
            import models

            key_row = db_session.query(models.HistorialLlaveFEA).filter(
                models.HistorialLlaveFEA.medico_id == medico.id,
                models.HistorialLlaveFEA.key_id == key_id,
            ).one_or_none()
        if key_row is None:
            for candidate in getattr(medico, "historial_llaves", ()) or ():
                if getattr(candidate, "key_id", None) == key_id:
                    key_row = candidate
                    break
        if key_row is None:
            return False
        try:
            signature = base64.b64decode(sello_digital.split("ECDSA:", 1)[1], validate=True)
        except (ValueError, TypeError):
            return False
        return _verify_single_ecdsa(key_row.public_key_pem, signature, cadena_original)

    if medico is None or not fecha_firma or fecha_firma >= datetime.datetime(2027, 1, 1):
        return False
    try:
        token = medico.huella_token or medico.cedula
        data = cadena_original.encode("utf-8") if isinstance(cadena_original, str) else cadena_original
        expected = hmac.new(
            f"{token}-{get_hes_secret()}".encode("utf-8"), data, hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, sello_digital)
    except Exception:
        return False


def rotate_medico_key(db_session, medico, *, motivo: str, actor_id: Optional[int]) -> str:
    """Explicit, audited, transactional FEA key rotation."""
    if not (motivo or "").strip():
        raise ValueError("El motivo de rotación FEA es obligatorio")
    if not getattr(medico, "huella_token", None) or not getattr(medico, "fmd_template", None):
        raise FEAKeyStateError("El médico no tiene biometría vigente para completar la rotación FEA")

    import json
    import models

    locked = db_session.query(type(medico)).filter_by(id=medico.id).with_for_update().one()
    now = utcnow()
    old_rows = _active_key_rows(db_session, locked.id)
    old_ids = [row.key_id for row in old_rows]
    for row in old_rows:
        row.activo = False
        row.estado = "INACTIVA"
        row.fecha_inactivacion = now

    private_pem, public_pem = generate_ecdsa_keypair()
    new_key_id = _new_key_id()
    locked.public_key_pem = public_pem.decode("ascii")
    locked.private_key_enc = custodian.encrypt(private_pem, locked.huella_token)
    locked.private_key_cipher_version = CIPHER_VERSION
    locked.requiere_actualizacion_fea = False
    db_session.add(
        models.HistorialLlaveFEA(
            key_id=new_key_id,
            medico_id=locked.id,
            public_key_pem=locked.public_key_pem,
            fecha_creacion=now,
            activo=True,
            estado="ACTIVA",
        )
    )
    db_session.add(
        models.AuditoriaLog(
            usuario_id=actor_id,
            accion="ROTACION_EXPLICITA_LLAVE_FEA",
            detalles_json=json.dumps(
                {
                    "medico_id": locked.id,
                    "motivo": motivo.strip(),
                    "key_ids_inactivadas": old_ids,
                    "nueva_key_id": new_key_id,
                    "mecanismo_cifrado": CIPHER_VERSION,
                },
                ensure_ascii=False,
            ),
        )
    )
    db_session.flush()
    medico.public_key_pem = locked.public_key_pem
    medico.private_key_enc = locked.private_key_enc
    medico.private_key_cipher_version = CIPHER_VERSION
    medico.requiere_actualizacion_fea = False
    return new_key_id

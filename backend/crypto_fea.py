import os
import hashlib
import hmac
import base64
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import datetime
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger('hes.crypto_fea')

def get_hes_secret():
    secret = os.getenv('HES_HMAC_SECRET')
    if not secret:
        raise RuntimeError('FATAL: HES_HMAC_SECRET no está configurado en el entorno (.env). El sistema debe fallar duro por seguridad.')
    return secret

def get_kdf_fernet_key(huella_token: str) -> bytes:
    secret = get_hes_secret().encode('utf-8')
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'hes-fea-salt-nom004',
        info=b'FEA_KEK_DERIVATION',
    )
    derived = hkdf.derive(huella_token.encode('utf-8') + secret)
    return base64.urlsafe_b64encode(derived)

def generate_ecdsa_keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return priv_pem, pub_pem

def ensure_medico_keys(db_session, medico):
    if getattr(medico, 'public_key_pem', None) is None:
        # LOCK de fila + double-checked
        try:
            medico_locked = db_session.query(type(medico)).filter_by(id=medico.id).with_for_update().first()
        except Exception:
            medico_locked = None
        if medico_locked is None:
            medico_locked = medico
        if getattr(medico_locked, 'public_key_pem', None) is None:
            priv_pem, pub_pem = generate_ecdsa_keypair()
            
            token = medico_locked.huella_token or medico_locked.cedula
            if not token:
                raise ValueError('El medico no tiene huella_token ni cedula para derivar la llave KEK.')
                
            f = Fernet(get_kdf_fernet_key(token))
            priv_enc = f.encrypt(priv_pem)
            
            medico_locked.public_key_pem = pub_pem.decode('utf-8')
            medico_locked.private_key_enc = priv_enc.decode('utf-8')
            
            # Registrar llave en el historial de llaves publicas
            try:
                import models
                historial_entry = models.HistorialLlaveFEA(
                    medico_id=medico_locked.id,
                    public_key_pem=medico_locked.public_key_pem,
                    fecha_creacion=datetime.datetime.utcnow(),
                    activo=True
                )
                db_session.add(historial_entry)
            except Exception:
                pass # Si no hay modelo SQLAlchemy o estamos en test simple
                
            db_session.add(medico_locked)
            db_session.commit()
            
            medico.public_key_pem = medico_locked.public_key_pem
            medico.private_key_enc = medico_locked.private_key_enc
        else:
            medico.public_key_pem = medico_locked.public_key_pem
            medico.private_key_enc = medico_locked.private_key_enc

    return medico.public_key_pem, medico.private_key_enc

def firmar_documento(db_session, medico, cadena_original: str) -> str:
    ensure_medico_keys(db_session, medico)
    
    token = medico.huella_token or medico.cedula
    f = Fernet(get_kdf_fernet_key(token))
    
    priv_enc = medico.private_key_enc.encode('utf-8')
    try:
        priv_pem = f.decrypt(priv_enc)
    except InvalidToken:
        # La KEK cambió (ej. re-registro de huella).
        # Inactivamos la llave anterior en el historial (pero NO la borramos)
        try:
            import models
            try:
                db_session.query(models.HistorialLlaveFEA).filter(
                    models.HistorialLlaveFEA.medico_id == medico.id,
                    models.HistorialLlaveFEA.activo == True
                ).update({
                    "activo": False,
                    "fecha_inactivacion": datetime.datetime.utcnow()
                })
            except Exception:
                pass
        except Exception:
            pass

        # Generamos el nuevo par de llaves
        priv_pem, pub_pem = generate_ecdsa_keypair()
        old_pub_pem = medico.public_key_pem
        medico.public_key_pem = pub_pem.decode('utf-8')
        medico.private_key_enc = f.encrypt(priv_pem).decode('utf-8')

        # Archivar la llave previa en la lista histórica en memoria
        if not hasattr(medico, '_historical_keys'):
            medico._historical_keys = []
        if old_pub_pem and old_pub_pem not in medico._historical_keys:
            medico._historical_keys.append(old_pub_pem)

        # Registramos la nueva llave en el historial de la base de datos
        try:
            import models
            new_historial = models.HistorialLlaveFEA(
                medico_id=medico.id,
                public_key_pem=medico.public_key_pem,
                fecha_creacion=datetime.datetime.utcnow(),
                activo=True
            )
            db_session.add(new_historial)
        except Exception:
            pass

        db_session.add(medico)
        db_session.commit()
        logger.info(
            'ROTACION_DE_LLAVES_FEA: medico_id=%s (%s). La KEK cambió y se generó una nueva llave asimétrica. '
            'La llave pública anterior fue archivada en el historial para preservar la validez de firmas pasadas.',
            getattr(medico, 'id', '?'), getattr(medico, 'nombre_completo', '?')
        )
    
    private_key = serialization.load_pem_private_key(priv_pem, password=None)
    
    signature = private_key.sign(
        cadena_original.encode('utf-8'),
        ec.ECDSA(hashes.SHA256())
    )
    
    return 'ECDSA:' + base64.b64encode(signature).decode('utf-8')

def _verify_single_ecdsa(public_key_pem_str: str, signature_bytes: bytes, cadena_original: str) -> bool:
    try:
        public_key = serialization.load_pem_public_key(public_key_pem_str.encode('utf-8'))
        public_key.verify(
            signature_bytes,
            cadena_original.encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except Exception:
        return False

def verificar_firma(medico, cadena_original: str, sello_digital: str, fecha_firma: datetime.datetime = None, db_session = None) -> bool:
    if not sello_digital:
        return False
    if sello_digital.startswith('ECDSA:'):
        if medico is None or not getattr(medico, 'public_key_pem', None):
            return False
            
        try:
            b64_sig = sello_digital.split('ECDSA:', 1)[1]
            signature = base64.b64decode(b64_sig)
            
            # 1. Intentar con la llave pública activa actual
            if _verify_single_ecdsa(medico.public_key_pem, signature, cadena_original):
                return True

            # 2. Si falló (ej. el médico re-enroló su huella), buscar en el historial de llaves
            # A) Desde la relación del modelo ORM
            historial = getattr(medico, 'historial_llaves', None)
            if historial:
                for h_entry in historial:
                    if h_entry.public_key_pem != medico.public_key_pem:
                        if _verify_single_ecdsa(h_entry.public_key_pem, signature, cadena_original):
                            return True

            # B) Desde base de datos directa si db_session está disponible
            if db_session and hasattr(medico, 'id'):
                try:
                    import models
                    keys = db_session.query(models.HistorialLlaveFEA).filter(
                        models.HistorialLlaveFEA.medico_id == medico.id
                    ).all()
                    for k in keys:
                        if k.public_key_pem != medico.public_key_pem:
                            if _verify_single_ecdsa(k.public_key_pem, signature, cadena_original):
                                return True
                except Exception:
                    pass

            # C) Desde mocks de test (_historical_keys)
            mock_historical = getattr(medico, '_historical_keys', [])
            for old_pem in mock_historical:
                if _verify_single_ecdsa(old_pem, signature, cadena_original):
                    return True

            return False
        except Exception:
            return False
    else:
        if medico is None:
            return False
            
        # Caducidad del legacy HMAC: si no se puede acreditar la fecha de firma
        # (None) o la firma es posterior al corte, el sello legacy se rechaza (fail-closed).
        if not fecha_firma or fecha_firma >= datetime.datetime(2027, 1, 1):
            return False
            
        try:
            secret = get_hes_secret()
            token = medico.huella_token or medico.cedula
            secret_key_bytes = f'{token}-{secret}'.encode('utf-8')
            expected = hmac.new(secret_key_bytes, cadena_original.encode('utf-8'), hashlib.sha512).hexdigest()
            return hmac.compare_digest(expected, sello_digital)
        except Exception:
            return False

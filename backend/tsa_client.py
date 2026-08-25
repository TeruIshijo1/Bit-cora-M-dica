"""
Cliente de Sellado de Tiempo (TSA) conforme a RFC 3161.

Solicita a una Autoridad de Sellado de Tiempo un token que acredita que un
hash existía antes del genTime emitido por la autoridad. La firma clínica
NUNCA se bloquea por un fallo del TSA: ante cualquier error se devuelve None
y la firma queda marcada como pendiente de countersign.

Configuración (.env):
  TSA_URL      -> Endpoint del TSA (default: https://freetsa.org/tsr)
  TSA_TIMEOUT  -> Timeout en segundos (default: 3)
"""
import os
import base64
import logging
import urllib.request

from asn1crypto import core, algos, cms, x509
from asn1crypto.core import Sequence, SequenceOf

logger = logging.getLogger('hes.tsa')

TSA_STATUS_GRANTED = 0
TSA_STATUS_GRANTED_WITH_MODS = 1


class MessageImprint(Sequence):
    _fields = [
        ('hash_algorithm', algos.DigestAlgorithm),
        ('hashed_message', core.OctetString),
    ]


class StatusStrings(SequenceOf):
    _child_spec = core.UTF8String


class PKIStatusInfo(Sequence):
    _fields = [
        ('status', core.Integer),
        ('status_string', StatusStrings, {'optional': True}),
        ('fail_info', core.BitString, {'optional': True}),
    ]


class TimeStampReq(Sequence):
    _fields = [
        ('version', core.Integer),
        ('message_imprint', MessageImprint),
        ('req_policy', core.ObjectIdentifier, {'implicit': 0, 'optional': True}),
        ('nonce', core.Integer, {'implicit': 1, 'optional': True}),
        ('cert_req', core.Boolean, {'default': False}),
        ('extensions', core.Any, {'implicit': 2, 'optional': True}),
    ]


class TimeStampResp(Sequence):
    _fields = [
        ('status', PKIStatusInfo),
        ('time_stamp_token', cms.ContentInfo, {'optional': True}),
    ]


class TSTInfo(Sequence):
    _fields = [
        ('version', core.Integer),
        ('policy', core.ObjectIdentifier),
        ('message_imprint', MessageImprint),
        ('serial_number', core.Integer),
        ('gen_time', core.GeneralizedTime),
        ('tsa', x509.GeneralName, {'implicit': 0, 'optional': True}),
        ('extensions', core.Any, {'implicit': 1, 'optional': True}),
    ]


def get_tsa_url():
    return os.getenv('TSA_URL', 'https://freetsa.org/tsr')


def _parse_token(token_der: bytes, expected_hash: bytes):
    """Extrae (gen_time, serial, imprint_ok) de un TimeStampToken (ContentInfo CMS)."""
    ci = cms.ContentInfo.load(token_der)
    signed_data = ci['content']
    inner_der = bytes(signed_data['encap_content_info']['content'])
    tst = TSTInfo.load(inner_der)

    imprint = tst['message_imprint']['hashed_message'].native
    return {
        'gen_time': tst['gen_time'].native,
        'serial': format(tst['serial_number'].native, 'x'),
        'policy': tst['policy'].native,
        'imprint_ok': imprint == expected_hash,
    }


def get_timestamp(hash_sha256_hex: str):
    """
    Solicita un token RFC 3161 para el hash dado.
    Devuelve {'token_b64', 'gen_time', 'serial'} o None si el TSA no está
    disponible / rechaza la petición. Jamás lanza excepciones hacia el flujo de firma.
    """
    try:
        digest = bytes.fromhex(hash_sha256_hex)
        # Nota: sin nonce. OpenTSA/freetsa rechaza el INTEGER implicit-tagged
        # (badDataFormat) y el imprint del token ya liga el token a este hash.
        req = TimeStampReq({
            'version': 1,
            'message_imprint': {
                'hash_algorithm': {'algorithm': 'sha256'},
                'hashed_message': digest,
            },
            'cert_req': True,
        })

        request = urllib.request.Request(
            get_tsa_url(),
            data=req.dump(),
            headers={'Content-Type': 'application/timestamp-query'},
            method='POST',
        )
        timeout = float(os.getenv('TSA_TIMEOUT', '3'))
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body = resp.read()

        tsr = TimeStampResp.load(body)
        status = int(tsr['status']['status'].native)
        if status not in (TSA_STATUS_GRANTED, TSA_STATUS_GRANTED_WITH_MODS):
            logger.warning('TSA rechazó la petición con estatus %s', status)
            return None

        token = tsr['time_stamp_token']
        if token is None or token.contents in (None, b''):
            logger.warning('TSA respondió granted sin token')
            return None

        token_der = token.dump()
        info = _parse_token(token_der, digest)
        if not info['imprint_ok']:
            logger.warning('El imprint del token TSA no coincide con el hash firmado')
            return None

        return {
            'token_b64': base64.b64encode(token_der).decode('ascii'),
            'gen_time': info['gen_time'].isoformat(),
            'serial': info['serial'],
            'autoridad': get_tsa_url(),
        }
    except Exception as e:
        logger.warning('TSA no disponible (%s): la firma continúa sin sellado de tiempo.', e)
        return None


def verify_timestamp(token_b64: str, expected_hash_sha256_hex: str):
    """
    Verifica un token TSA almacenado contra el hash esperado.
    Devuelve {'disponible', 'verificado', 'gen_time', 'serial', 'autoridad'}.
    Nota: valida imprint y estructura; la validación de la cadena de
    certificados del TSA se realiza al resguardo del token original.
    """
    result = {'disponible': False, 'verificado': False, 'gen_time': None, 'serial': None, 'autoridad': get_tsa_url()}
    if not token_b64:
        return result
    try:
        token_der = base64.b64decode(token_b64)
        info = _parse_token(token_der, bytes.fromhex(expected_hash_sha256_hex))
        result.update({
            'disponible': True,
            'verificado': info['imprint_ok'],
            'gen_time': info['gen_time'].isoformat(),
            'serial': info['serial'],
        })
    except Exception as e:
        logger.warning('Token TSA ilegible o corrupto: %s', e)
        result['verificado'] = False
    return result

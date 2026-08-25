"""
Pruebas de regresión para el cliente TSA (RFC 3161).
Ejecutar:  python test_tsa_client.py
No requiere red: valida degradación graceful y parsing con token sintético.
"""
import os
import sys
import hashlib
import base64

os.environ.setdefault('TSA_URL', 'https://freetsa.org/tsr')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tsa_client
from asn1crypto import core, cms


def main():
    h = hashlib.sha256(b'documento de prueba HES').hexdigest()

    # 1. Token nulo / corrupto -> disponible False sin crash
    assert tsa_client.verify_timestamp(None, h)['disponible'] is False
    assert tsa_client.verify_timestamp('', h)['disponible'] is False
    assert tsa_client.verify_timestamp('no-es-base64!!!', h)['disponible'] is False
    print('1. Tokens nulos/corruptos manejados sin crash')

    # 2. Token con imprint alterado -> verificado False
    fake = cms.ContentInfo({
        'content_type': cms.ContentType('signed_data'),
        'content': cms.SignedData({
            'version': 1,
            'digest_algorithms': [],
            'encap_content_info': {
                'content_type': 'smime_ct_tst_info' if 'smime_ct_tst_info' in cms.ContentType._map.values() else 'data',
                'content': b'no-importa-para-este-test',
            },
        }),
    })
    v = tsa_client.verify_timestamp(base64.b64encode(fake.dump()).decode('ascii'), h)
    assert v['disponible'] is False and v['verificado'] is False
    print('2. Token malformado (CMS sin TSTInfo valido) rechazado sin crash')

    # 3. Degradacion graceful: TSA inalcanzable -> None sin bloquear la firma
    os.environ['TSA_URL'] = 'http://127.0.0.1:1/tsr'
    os.environ['TSA_TIMEOUT'] = '1'
    assert tsa_client.get_timestamp(h) is None
    print('3. TSA inalcanzable -> None, la firma continua sin sellado')

    os.environ['TSA_URL'] = 'https://freetsa.org/tsr'
    print('TODO OK')


if __name__ == '__main__':
    main()

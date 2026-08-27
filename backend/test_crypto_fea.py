"""
Pruebas de regresión para el módulo de Firma Electrónica Avanzada (crypto_fea).
Ejecutar:  python test_crypto_fea.py
No requiere base de datos ni red.
"""
import os
import sys
import hmac
import hashlib

os.environ['HES_HMAC_SECRET'] = os.getenv('HES_HMAC_SECRET', 'test-secret-para-pruebas')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crypto_fea


class FakeMedico:
    def __init__(self):
        self.id = 1
        self.nombre_completo = 'MEDICO PRUEBA'
        self.huella_token = 'token-huella-abc'
        self.cedula = 'CED-123'
        self.public_key_pem = None
        self.private_key_enc = None


class FakeDB:
    def add(self, o): pass
    def commit(self): pass


def main():
    m = FakeMedico()
    db = FakeDB()
    cadena = '||5704|PT-5704|HE-DIRMED|1|2026-08-24T12:00:00|1|CED-123|prueba||'

    # 1. Firma nueva -> ECDSA
    sello = crypto_fea.firmar_documento(db, m, cadena)
    assert sello.startswith('ECDSA:'), sello
    assert m.public_key_pem and m.private_key_enc
    print('1. Firma ECDSA generada OK')

    # 2. Verificacion ECDSA correcta
    assert crypto_fea.verificar_firma(m, cadena, sello) is True
    print('2. Verificacion ECDSA correcta')

    # 3. Tamper detectado
    assert crypto_fea.verificar_firma(m, cadena.replace('prueba', 'hack'), sello) is False
    print('3. Tamper detectado correctamente')

    # 4. Sellos malformados no crashean
    assert crypto_fea.verificar_firma(m, cadena, 'ECDSA:!!!no-es-base64!!!') is False
    assert crypto_fea.verificar_firma(m, cadena, 'ECDSA:') is False
    assert crypto_fea.verificar_firma(m, cadena, '') is False
    print('4. Sellos malformados manejados sin crash')

    # 5. Legacy HMAC sigue verificando (con fecha acreditada pre-corte)
    import datetime as dt
    secret = os.environ['HES_HMAC_SECRET']
    legacy = hmac.new(f'{m.huella_token}-{secret}'.encode(), cadena.encode(), hashlib.sha512).hexdigest()
    assert crypto_fea.verificar_firma(m, cadena, legacy, dt.datetime(2026, 8, 24)) is True
    print('5. Sello legacy HMAC verificado (fecha pre-corte)')

    # 6. Medico inexistente (None) no crashea
    assert crypto_fea.verificar_firma(None, cadena, sello) is False
    assert crypto_fea.verificar_firma(None, cadena, legacy) is False
    print('6. Medico None manejado sin crash')

    # 7. Rotacion de KEK: re-firma OK, y sello pre-rotacion preservado mediante historial de llaves
    m.huella_token = 'token-nuevo-tras-re-registro'
    sello2 = crypto_fea.firmar_documento(db, m, cadena)
    assert sello2.startswith('ECDSA:')
    assert crypto_fea.verificar_firma(m, cadena, sello2) is True
    # Con el historial de llaves, la firma pasada sigue siendo verificable (no-repudio)
    assert crypto_fea.verificar_firma(m, cadena, sello) is True
    print('7. Rotacion de KEK: re-firma OK y firma historica verificada via historial')

    # 8. Fail duro sin secreto
    respaldado = os.environ.pop('HES_HMAC_SECRET')
    try:
        crypto_fea.get_hes_secret()
        print('8. FALLO: no lanzo excepcion sin secreto')
        sys.exit(1)
    except RuntimeError:
        print('8. Fail-duro sin secreto OK')
    finally:
        os.environ['HES_HMAC_SECRET'] = respaldado

    # 9. Caducidad legacy: antes del corte valido, despues rechazado
    m.huella_token = 'token-huella-abc'
    assert crypto_fea.verificar_firma(m, cadena, legacy, dt.datetime(2026, 8, 24)) is True
    assert crypto_fea.verificar_firma(m, cadena, legacy, dt.datetime(2026, 12, 31, 23, 59, 59)) is True
    assert crypto_fea.verificar_firma(m, cadena, legacy, dt.datetime(2027, 1, 1)) is False
    assert crypto_fea.verificar_firma(m, cadena, legacy, dt.datetime(2028, 5, 1)) is False
    print('9. Caducidad legacy: pre-corte OK, post-corte rechazado')

    # 10. Legacy sin fecha acreditada -> fail-closed
    assert crypto_fea.verificar_firma(m, cadena, legacy, None) is False
    print('10. Legacy sin fecha acreditada rechazado (fail-closed)')

    # 11. ECDSA ignora la caducidad (no aplica a firmas asimetricas)
    assert crypto_fea.verificar_firma(m, cadena, sello2, dt.datetime(2030, 1, 1)) is True
    print('11. ECDSA no caduca por fecha')

    print('TODO OK')


if __name__ == '__main__':
    main()

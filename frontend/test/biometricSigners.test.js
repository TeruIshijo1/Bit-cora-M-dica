import test from 'node:test';
import assert from 'node:assert/strict';
import { nextDocumentSigner, signerRole, captureBelongsToSigner, witnessSigned } from '../src/utils/biometricSigners.js';

test('tutor retains own persisted role, never becomes a witness', () => {
  const tutor = { id: 1, tipo_firmante: 'TUTOR' };
  const witness = { id: 2, tipo_firmante: 'TESTIGO_2' };
  assert.equal(signerRole(nextDocumentSigner([tutor, witness], false, {})), 'TUTOR');
  assert.equal(nextDocumentSigner([tutor, witness], false, { paciente_firmado: true }), witness);
});
test('incapable patient without authorized representative has no default signer', () => {
  assert.equal(nextDocumentSigner([{ id: 1, tipo_firmante: 'PACIENTE' }, { id: 2, tipo_firmante: 'CONTACTO' }], false, {}), null);
});
test('witness status uses role rather than list position', () => {
  assert.equal(witnessSigned('TESTIGO_2', { testigo1_firmado: true }), false);
  assert.equal(witnessSigned('TESTIGO_2', { testigo2_firmado: true }), true);
});
test('another modal, signer or document cannot submit this shared capture', () => {
  const context = { action: 'FIRMA_FIRMANTE', patientRef: '1', documentCode: '02', documentRef: 7, expectedIdentityRef: 'firmante:3' };
  assert.equal(captureBelongsToSigner(context, '1', '02', 7, 3), true);
  for (const changed of [{ action: 'FIRMA_MEDICA' }, { patientRef: '2' }, { documentCode: '07' }, { documentRef: 8 }, { expectedIdentityRef: 'firmante:4' }]) {
    assert.equal(captureBelongsToSigner({ ...context, ...changed }, '1', '02', 7, 3), false);
  }
});

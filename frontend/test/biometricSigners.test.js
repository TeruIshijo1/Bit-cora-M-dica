import test from 'node:test';
import assert from 'node:assert/strict';
import { nextDocumentSigner, signerRole, patientCanAuthorize, captureBelongsToSigner, witnessSigned, witnessProgress, requiredWitnesses, expectedWitnesses, availableWitnessRoleFor, signedWitnessRoleFor, signerIdentityForRole } from '../src/utils/biometricSigners.js';

test('tutor keeps its profile but can fill an available witness slot', () => {
  const tutor = { id: 1, tipo_firmante: 'TUTOR' };
  const witness = { id: 2, tipo_firmante: 'TESTIGO_2' };
  assert.equal(signerRole(nextDocumentSigner([tutor, witness], false, {})), 'TUTOR');
  assert.equal(nextDocumentSigner([tutor, witness], true, { paciente_firmado: true }), tutor);
  assert.equal(availableWitnessRoleFor(tutor, { paciente_firmado: true }), 'TESTIGO_1');
  assert.equal(signerRole(tutor), 'TUTOR');
});
test('incapable patient without authorized representative has no default signer', () => {
  assert.equal(nextDocumentSigner([{ id: 1, tipo_firmante: 'PACIENTE' }, { id: 2, tipo_firmante: 'CONTACTO' }], false, {}), null);
});
test('witness status uses role rather than list position', () => {
  assert.equal(witnessSigned('TESTIGO_2', { testigo1_firmado: true }), false);
  assert.equal(witnessSigned('TESTIGO_2', { testigo2_firmado: true }), true);
});
test('witness progress counts actual signatures instead of the last witness position', () => {
  assert.equal(witnessProgress({ testigo1_firmado: false, testigo2_firmado: true }), 1);
  assert.equal(witnessProgress({ testigo1_firmado: true, testigo2_firmado: false }), 1);
  assert.equal(witnessProgress({ testigo1_firmado: true, testigo2_firmado: true }), 2);
});
test('another modal, signer or document cannot submit this shared capture', () => {
  const context = { action: 'FIRMA_FIRMANTE', patientRef: '1', documentCode: '02', documentRef: 7, expectedIdentityRef: signerIdentityForRole(3, 'TESTIGO_1') };
  assert.equal(captureBelongsToSigner(context, '1', '02', 7, 3, 'TESTIGO_1'), true);
  for (const changed of [{ action: 'FIRMA_MEDICA' }, { patientRef: '2' }, { documentCode: '07' }, { documentRef: 8 }, { expectedIdentityRef: signerIdentityForRole(4, 'TESTIGO_1') }, { expectedIdentityRef: signerIdentityForRole(3, 'TESTIGO_2') }]) {
    assert.equal(captureBelongsToSigner({ ...context, ...changed }, '1', '02', 7, 3, 'TESTIGO_1'), false);
  }
});
test('a document authorizer cannot also occupy a witness slot', () => {
  const tutor = { id: 8, tipo_firmante: 'TUTOR' };
  const status = { paciente_firmado: true, detalles: { firmante_paciente_id: 8 } };
  assert.equal(availableWitnessRoleFor(tutor, status), null);
});
test('a flexible signer keeps the witness slot already recorded for that document', () => {
  const tutor = { id: 8, tipo_firmante: 'TUTOR' };
  const status = { testigo2_firmado: true, detalles: { firmante_testigo2_id: 8 } };
  assert.equal(signedWitnessRoleFor(tutor.id, status), 'TESTIGO_2');
});
test('effective witness requirement from server is not reduced twice for a responsible authorizer', () => {
  const status = {
    testigos_requeridos: 1,
    detalles: { rol_firmante_paciente: 'REPRESENTANTE_LEGAL' },
  };
  assert.equal(requiredWitnesses(status, false), 1);
  assert.equal(requiredWitnesses({ testigos_requeridos: 2 }, true), 2);
  assert.equal(requiredWitnesses({ testigos_requeridos: 0, requiere_testigos: true }, true), 0);
});

test('a filled witness requirement does not offer another witness slot', () => {
  const family = { id: 12, tipo_firmante: 'FAMILIAR' };
  const status = { testigos_requeridos: 1, testigo2_firmado: true };
  assert.equal(availableWitnessRoleFor(family, status), null);
});

test('optional witness spaces remain available after representative authorization', () => {
  const family = { id: 12, tipo_firmante: 'FAMILIAR' };
  const status = {
    paciente_firmado: true,
    testigos_esperados: 2,
    testigos_requeridos: 0,
    detalles: { firmante_paciente_id: 8, rol_firmante_paciente: 'REPRESENTANTE_LEGAL' },
  };
  assert.equal(requiredWitnesses(status, false), 0);
  assert.equal(expectedWitnesses(status, false), 2);
  assert.equal(availableWitnessRoleFor(family, status, false), 'TESTIGO_1');
});

test('capacity from a saved format does not treat string false as true', () => {
  assert.equal(patientCanAuthorize('false'), false);
  assert.equal(patientCanAuthorize('0'), false);
  assert.equal(patientCanAuthorize('No'), false);
  assert.equal(patientCanAuthorize('true'), true);
  assert.equal(patientCanAuthorize(undefined), true);
});

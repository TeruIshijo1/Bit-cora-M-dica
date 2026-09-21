import test from 'node:test';
import assert from 'node:assert/strict';
import { captureBelongsToMedicalFlow, medicalBiometricFlow } from '../src/utils/medicalBiometricEnrollment.js';

test('new doctor uses explicit enrollment bound to its identity', () => {
  const doctor = { id: 42, biometric_status: 'SIN_BIOMETRIA', requiere_actualizacion_fea: false };
  const flow = medicalBiometricFlow(doctor);
  assert.equal(flow.action, 'ENROLAMIENTO_MEDICO');
  assert.equal(flow.endpoint, '/medicos/42/biometria/enrolar');
  assert.equal(flow.requiresReason, false);
  assert.equal(captureBelongsToMedicalFlow({
    action: flow.action,
    expectedIdentityRef: 'medico:42',
    documentRef: 42
  }, doctor, flow), true);
});

test('legacy fingerprint uses audited reenrollment with mandatory reason', () => {
  const doctor = { id: 7, biometric_status: 'LEGACY_RAW', requiere_actualizacion_fea: false };
  const flow = medicalBiometricFlow(doctor);
  assert.equal(flow.action, 'REENROLAMIENTO_MEDICO');
  assert.equal(flow.endpoint, '/medicos/7/biometria/reenrolar');
  assert.equal(flow.requiresReason, true);
});

test('pending reenrollment enters second-actor FEA ceremony', () => {
  const doctor = { id: 7, biometric_status: 'FMD_VALIDO', requiere_actualizacion_fea: true };
  const flow = medicalBiometricFlow(doctor);
  assert.equal(flow.action, 'ACTUALIZACION_FEA');
  assert.equal(flow.endpoint, '/medicos/7/fea/completar-actualizacion');
  assert.equal(flow.requiresReason, true);
});

test('capture from another doctor or stage is rejected', () => {
  const doctor = { id: 7, biometric_status: 'LEGACY_RAW', requiere_actualizacion_fea: false };
  const flow = medicalBiometricFlow(doctor);
  const context = { action: flow.action, expectedIdentityRef: 'medico:7', documentRef: '7' };
  assert.equal(captureBelongsToMedicalFlow(context, doctor, flow), true);
  assert.equal(captureBelongsToMedicalFlow({ ...context, expectedIdentityRef: 'medico:8' }, doctor, flow), false);
  assert.equal(captureBelongsToMedicalFlow({ ...context, action: 'ACTUALIZACION_FEA' }, doctor, flow), false);
});

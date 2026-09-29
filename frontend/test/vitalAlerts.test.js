import test from 'node:test';
import assert from 'node:assert/strict';
import { getVitalAlert, getVitalSummaryLabel } from '../src/utils/vitalAlerts.js';

test('folded vitals preserve the previous alert boundaries, including diastolic pressure', () => {
  const cases = [
    ['Presión Arterial', '122/84', null], ['Presión Arterial', '140/80', 'Alta'],
    ['Presión Arterial', '120/90', 'Alta'], ['Presión Arterial', '89/70', 'Baja'],
    ['Presión Arterial', '120/59', 'Baja'], ['Frec. Cardíaca', '100', 'Alta'],
    ['Frec. Cardíaca', '60', null], ['Frec. Cardíaca', '59', 'Baja'],
    ['Frec. Respiratoria', '22', 'Alta'], ['Frec. Respiratoria', '11', 'Baja'],
    ['Saturación O2', '91', 'Baja'], ['Saturación O2', '92', null],
    ['Temperatura', '37,5', 'Fiebre'], ['Temperatura', '36', null],
    ['Temperatura', '35,9', 'Baja'], ['Peso', '79', null],
  ];
  for (const [label, value, expected] of cases) assert.equal(getVitalAlert({ label, value }), expected, `${label}: ${value}`);
});

test('unavailable readings never become a clinical alert', () => {
  for (const value of [null, undefined, '', '—', 'No registrado']) {
    for (const label of ['Presión Arterial', 'Frec. Cardíaca', 'Frec. Respiratoria', 'Saturación O2', 'Temperatura']) {
      assert.equal(getVitalAlert({ label, value }), null, `${label}: ${value}`);
    }
  }
});

test('summary identifies an abnormal value with a readable label', () => {
  assert.equal(getVitalSummaryLabel('Saturación O2'), 'SpO₂');
  assert.equal(getVitalSummaryLabel('Presión Arterial'), 'PA');
  assert.equal(getVitalSummaryLabel('Medición adicional'), 'Medición adicional');
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { resolvePdfRequest } from '../src/utils/pdfRequest.js';

test('saved consent 09 uses the exact authorized preparation source', () => {
  assert.deepEqual(
    resolvePdfRequest('/ehr/paciente/5704/pdf-consentimiento-09?mrnum=1'),
    {
      method: 'post',
      url: '/ehr/paciente/5704/pdf-preparar?source=%2Fehr%2Fpaciente%2F5704%2Fpdf-consentimiento-09%3Fmrnum%3D1',
    },
  );
});

test('previews and formats without an implemented preparer remain authenticated GETs', () => {
  assert.deepEqual(
    resolvePdfRequest('/ehr/paciente/5704/pdf-consentimiento-09'),
    { method: 'get', url: '/ehr/paciente/5704/pdf-consentimiento-09' },
  );
  assert.deepEqual(
    resolvePdfRequest('/ehr/paciente/5704/pdf-consentimiento-02?mrnum=2'),
    { method: 'get', url: '/ehr/paciente/5704/pdf-consentimiento-02?mrnum=2' },
  );
});

test('external and protocol-relative PDF URLs are rejected', () => {
  assert.throws(() => resolvePdfRequest('https://example.com/file.pdf'));
  assert.throws(() => resolvePdfRequest('//example.com/file.pdf'));
});

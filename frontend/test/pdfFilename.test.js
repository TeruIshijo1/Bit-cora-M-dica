import test from 'node:test';
import assert from 'node:assert/strict';
import {
  isGenericPdfFilename,
  getStudyPdfDownloadName,
  parseContentDispositionFilename,
  inferPdfFilenameFromEndpoint,
} from '../src/utils/pdfFilename.js';

test('isGenericPdfFilename detects UUIDs and empty names', () => {
  assert.equal(isGenericPdfFilename('c32edfa1-0011-401d-90f9-837ebba89773.pdf'), true);
  assert.equal(isGenericPdfFilename('c32edfa1-0011-401d-90f9-837ebba89773'), true);
  assert.equal(isGenericPdfFilename('05bc8025-ae57-4f7c-b8ec-593a15568127.pdf'), true);
  assert.equal(isGenericPdfFilename(''), true);
  assert.equal(isGenericPdfFilename(null), true);
  assert.equal(isGenericPdfFilename('Expediente_Completo_PT_12345.pdf'), false);
  assert.equal(isGenericPdfFilename('Biometria_Hematica.pdf'), false);
});

test('getStudyPdfDownloadName produces clean descriptive filenames for studies with UUID names', () => {
  const study = {
    id: 99,
    ptmt_num: 1234,
    tipo: 'Laboratorio',
    estudio: 'Biometría Hemática Completa',
    nombre_archivo: 'c32edfa1-0011-401d-90f9-837ebba89773.pdf',
  };
  assert.equal(
    getStudyPdfDownloadName(study),
    'Laboratorio_Biometria_Hematica_Completa_PTMT-1234.pdf'
  );
});

test('parseContentDispositionFilename extracts filename and rejects UUID fallbacks', () => {
  assert.equal(
    parseContentDispositionFilename('inline; filename="Expediente_Completo_PT_12345.pdf"'),
    'Expediente_Completo_PT_12345.pdf'
  );
  assert.equal(
    parseContentDispositionFilename("attachment; filename*=UTF-8''Nota_Urgencias_123.pdf"),
    'Nota_Urgencias_123.pdf'
  );
  assert.equal(
    parseContentDispositionFilename('inline; filename="c32edfa1-0011-401d-90f9-837ebba89773.pdf"'),
    null
  );
});

test('inferPdfFilenameFromEndpoint infers friendly filename from API endpoint', () => {
  assert.equal(
    inferPdfFilenameFromEndpoint('/ehr/paciente/8842/pdf-expediente-completo'),
    'Expediente_Completo_PT_8842.pdf'
  );
  assert.equal(
    inferPdfFilenameFromEndpoint('/ehr/paciente/8842/pdf-nota-urgencias'),
    'Nota_Urgencias_PT_8842.pdf'
  );
  assert.equal(
    inferPdfFilenameFromEndpoint('/ehr/paciente/8842/pdf-consentimiento-04'),
    'Consentimiento_04_PT_8842.pdf'
  );
});

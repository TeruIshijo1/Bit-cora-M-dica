import test from 'node:test';
import assert from 'node:assert/strict';
import { friendlyBiometricError, friendlyReaderStatus } from '../src/utils/userMessages.js';

test('fingerprint mismatch is explained without technical language', () => {
  assert.equal(
    friendlyBiometricError('La huella no corresponde a la identidad vigente autorizada.'),
    'La huella no coincide con la registrada para esta persona. No se guardó la firma. Use el mismo dedo que se registró e inténtelo de nuevo.'
  );
});

test('expired challenge becomes a clear retry instruction', () => {
  assert.equal(
    friendlyBiometricError('Challenge inexistente, expirado, consumido o ajeno.'),
    'La lectura tardó demasiado y venció. Pulse “Intentar de nuevo”.'
  );
});

test('reader statuses use everyday wording', () => {
  assert.equal(friendlyReaderStatus('Solicitando challenge biométrico...'), 'Preparando el lector…');
  assert.equal(friendlyReaderStatus('Lector conectado'), 'Lector listo');
});

test('Vertical doctor profile errors confirm that the fingerprint was accepted', () => {
  assert.equal(
    friendlyBiometricError({
      code: 'VERTICAL_DOCTOR_PROFILE_NOT_READY',
      message: 'Su huella fue reconocida, pero su perfil médico en Vertical no está listo para firmar.'
    }),
    'Su huella fue reconocida, pero su perfil de firma en Vertical necesita revisión. Pida a Sistemas comprobar su cédula y autorización. No necesita registrar otra huella.'
  );
});

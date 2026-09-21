import test from 'node:test';
import assert from 'node:assert/strict';
import { friendlyBiometricError, friendlyReaderStatus } from '../src/utils/userMessages.js';

test('fingerprint mismatch is explained without technical language', () => {
  assert.equal(
    friendlyBiometricError('La huella no corresponde a la identidad vigente autorizada.'),
    'La huella no coincide con la persona seleccionada. Verifique el nombre e intente nuevamente.'
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

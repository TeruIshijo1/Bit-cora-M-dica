import test from 'node:test';
import assert from 'node:assert/strict';

import {
  isConfirmedClinicalSync,
  pendingClinicalSyncMessage
} from '../src/utils/clinicalSyncResult.js';

test('AF-07 Formato 15 EV never treats HTTP 202 as synchronized', () => {
  const response = {
    status: 202,
    data: { success: false, state: 'RETRYABLE_ERROR', operation_id: 'af07' }
  };
  assert.equal(isConfirmedClinicalSync(response), false);
  assert.match(pendingClinicalSyncMessage(response), /SINCRONIZACIÓN PENDIENTE/);
  assert.doesNotMatch(pendingClinicalSyncMessage(response), /guardado exitosamente en SQL Server/i);
});

test('AF-07 requires 200 or 201 plus success true plus SYNCED', () => {
  assert.equal(isConfirmedClinicalSync({ status: 200, data: { success: true, state: 'SYNCED' } }), true);
  assert.equal(isConfirmedClinicalSync({ status: 200, data: { success: true } }), false);
  assert.equal(isConfirmedClinicalSync({ status: 201, data: { success: false, state: 'SYNCED' } }), false);
});

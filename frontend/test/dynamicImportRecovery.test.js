import test from 'node:test';
import assert from 'node:assert/strict';

import {
  dynamicImportFailureId,
  shouldReloadForDynamicImportFailure,
  shouldReloadForMissingAsset,
} from '../src/utils/dynamicImportRecovery.js';

function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
}

test('identifies the missing Vite asset in a dynamic import failure', () => {
  const error = new TypeError(
    'Failed to fetch dynamically imported module: http://localhost:8000/assets/ClinicalPdfViewer-DVTyEp6E.js',
  );

  assert.equal(
    dynamicImportFailureId(error),
    'http://localhost:8000/assets/ClinicalPdfViewer-DVTyEp6E.js',
  );
});

test('allows one reload per failed asset and prevents reload loops', () => {
  const storage = memoryStorage();
  const firstBuild = new TypeError(
    'Failed to fetch dynamically imported module: http://localhost:8000/assets/ClinicalPdfViewer-old.js',
  );
  const nextBuild = new TypeError(
    'Failed to fetch dynamically imported module: http://localhost:8000/assets/ClinicalPdfViewer-new.js',
  );

  assert.equal(shouldReloadForDynamicImportFailure(firstBuild, storage), true);
  assert.equal(shouldReloadForDynamicImportFailure(firstBuild, storage), false);
  assert.equal(shouldReloadForDynamicImportFailure(nextBuild, storage), true);
});

test('does not reload for an unrelated render error', () => {
  assert.equal(
    shouldReloadForDynamicImportFailure(new Error('Cannot read properties of undefined'), memoryStorage()),
    false,
  );
});

test('allows one reload for a missing PDF worker asset', () => {
  const storage = memoryStorage();
  const workerUrl = '/assets/pdf.worker.min-old.mjs';

  assert.equal(shouldReloadForMissingAsset(workerUrl, storage), true);
  assert.equal(shouldReloadForMissingAsset(workerUrl, storage), false);
  assert.equal(shouldReloadForMissingAsset('/assets/pdf.worker.min-new.mjs', storage), true);
});

const RECOVERY_STORAGE_KEY = 'hes:dynamic-import-recovery';

const DYNAMIC_IMPORT_ERROR_PATTERNS = [
  /failed to fetch dynamically imported module/i,
  /error loading dynamically imported module/i,
  /importing a module script failed/i,
  /chunkloaderror/i,
  /loading chunk [\w-]+ failed/i,
];

function errorMessage(error) {
  if (typeof error === 'string') return error;
  return error?.message || String(error || '');
}

export function dynamicImportFailureId(error) {
  const message = errorMessage(error);
  if (!DYNAMIC_IMPORT_ERROR_PATTERNS.some((pattern) => pattern.test(message))) {
    return null;
  }

  const assetUrl = message.match(/https?:\/\/[^\s)]+\.js(?:\?[^\s)]*)?/i)?.[0];
  return assetUrl || message.slice(0, 500);
}

export function shouldReloadForDynamicImportFailure(error, storage) {
  const failureId = dynamicImportFailureId(error);
  if (!failureId) return false;

  try {
    if (storage?.getItem(RECOVERY_STORAGE_KEY) === failureId) return false;
    storage?.setItem(RECOVERY_STORAGE_KEY, failureId);
  } catch {
    // La recarga sigue siendo segura si el navegador bloquea sessionStorage.
  }

  return true;
}


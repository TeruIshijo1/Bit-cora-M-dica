const PENDING_STATES = new Set([
  'PENDING',
  'PROCESSING',
  'RETRYABLE_ERROR',
  'REQUIRES_RECONCILIATION'
]);

export function isConfirmedClinicalSync(response) {
  return [200, 201].includes(response?.status)
    && response?.data?.success === true
    && response?.data?.state === 'SYNCED';
}

export function pendingClinicalSyncMessage(response) {
  const data = response?.data || {};
  if (response?.status === 202 || data.success === false || PENDING_STATES.has(data.state)) {
    const operation = data.operation_id ? ` (${data.operation_id})` : '';
    return `SINCRONIZACIÓN PENDIENTE${operation}. El cambio no está confirmado en SQL Server.`;
  }
  return null;
}

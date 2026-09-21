export function createTrustedCapture({ api, fetchImpl = (...args) => fetch(...args), onChange = () => {}, wait = ms => new Promise(resolve => setTimeout(resolve, ms)), requestTimeoutMs = 15000, isSecureContext = () => globalThis.isSecureContext !== false }) {
  const base = 'http://127.0.0.1:8082';
  let generation = 0;
  let acquisition = null;
  let refreshing = null;
  let state = { status: 'Desconectado', devices: [], isAcquiring: false, fmdTemplate: null, captureContext: null, captureTimestamp: 0, challengeId: null, sessionId: null, error: null, errorKind: null };
  const update = patch => { state = { ...state, ...patch }; onChange({ ...state }); };
  async function local(path, body) {
    if (!isSecureContext()) throw new Error('Abra Bitácora mediante HTTPS con un certificado válido. La biometría no está disponible desde una dirección HTTP de intranet.');
    let response;
    const abort = new AbortController();
    const timeout = setTimeout(() => abort.abort(), requestTimeoutMs);
    try {
      response = await fetchImpl(base + path, {
        method: body ? 'POST' : 'GET',
        headers: { 'Content-Type': 'application/json' },
        targetAddressSpace: 'loopback',
        signal: abort.signal,
        ...(body ? { body: JSON.stringify(body) } : {})
      });
      const data = await response.json();
      if (!response.ok) throw Object.assign(new Error(data?.error || 'No se pudo conectar con el lector local.'), { agentResponse: true });
      return { status: response.status, data };
    } catch (error) {
      if (error.agentResponse) throw error;
      if (abort.signal.aborted) throw new Error('El agente local no respondió a tiempo. Revise su estado y vuelva a intentar.');
      throw new Error('No se pudo acceder al agente local. Compruebe que HES Biometric Agent esté iniciado y permita a Bitácora el acceso a dispositivos locales desde el navegador.');
    } finally { clearTimeout(timeout); }
  }
  const cancel = item => item ? local('/cancel-capture', item).catch(() => {}) : Promise.resolve();
  async function stop() {
    generation += 1;
    const previous = acquisition; acquisition = null;
    update({ isAcquiring: false, fmdTemplate: null, captureContext: null, captureTimestamp: 0, challengeId: null, sessionId: null, error: null, errorKind: null, status: 'Captura cancelada' });
    await cancel(previous);
  }
  function refreshDevices() {
    if (state.isAcquiring) return Promise.resolve(true);
    if (refreshing) return refreshing;
    const current = generation;
    refreshing = (async () => {
      try {
        const { data } = await local('/devices');
        const devices = data.devices || [];
        const availability = data.busy
          ? { status: 'Lector en uso en este equipo', error: 'Hay una lectura de huella en curso en este equipo. Termine la ventana de captura abierta o espere un momento.', errorKind: 'agent' }
          : { status: 'Lector conectado', ...(state.errorKind === 'agent' ? { error: null, errorKind: null } : {}) };
        update({ devices, ...(current !== generation || state.isAcquiring ? {} : availability) });
        return true;
      } catch (error) {
        if (current === generation && !state.isAcquiring) update({ devices: [], status: 'Lector no disponible', error: error.message, errorKind: 'agent' });
        return false;
      } finally { refreshing = null; }
    })();
    return refreshing;
  }
  async function start(context) {
    const stopping = stop();
    const current = generation;
    await stopping;
    const pendingProbe = refreshing;
    if (pendingProbe) await pendingProbe;
    if (current !== generation) return false;
    if (!context?.action) { update({ error: 'No se pudo preparar la lectura. Cierre esta ventana e intente nuevamente.', errorKind: 'capture', status: 'Lectura no disponible' }); return false; }
    update({ isAcquiring: true, status: 'Preparando el lector...', error: null, errorKind: null });
    try {
      if (!isSecureContext()) throw new Error('Abra Bitácora mediante HTTPS con un certificado válido para usar el lector.');
      const sessionId = globalThis.crypto.randomUUID();
      const response = await api.post('/biometrics/challenge', {
        action: context.action, session_id: sessionId, expected_medico_id: context.expectedMedicoId ?? null,
        expected_identity_ref: context.expectedIdentityRef ?? null,
        patient_ref: context.patientRef != null ? String(context.patientRef) : null,
        document_code: context.documentCode ?? null,
        document_ref: context.documentRef != null ? String(context.documentRef) : null
      }, { timeout: requestTimeoutMs });
      if (current !== generation) return false;
      const challenge = response.data;
      if (!challenge?.challenge_id || !challenge.capture_authorization) throw new Error('No se pudo iniciar la lectura. Intente nuevamente.');
      update({ challengeId: challenge.challenge_id, sessionId, captureContext: { ...context }, status: 'Iniciando lector...' });
      const started = await local('/begin-capture', { authorization: challenge.capture_authorization });
      const item = { acquisition_id: started.data?.acquisition_id, authorization: challenge.capture_authorization };
      if (!item.acquisition_id) throw new Error('El lector no respondió correctamente. Intente nuevamente.');
      if (current !== generation) { await cancel(item); return false; }
      acquisition = item;
      update({ status: 'Coloque su dedo sobre el lector...' });
      while (current === generation) {
        const result = await local('/capture-result', item);
        if (current !== generation) return false;
        if (result.status === 202) { await wait(250); continue; }
        if (!result.data?.fmd_template) throw new Error('No se pudo obtener una lectura clara. Limpie el lector e intente nuevamente.');
        const envelope = JSON.parse(result.data.fmd_template);
        if (envelope.protocol_version !== 2 || envelope.challenge_id !== challenge.challenge_id || envelope.session_id !== sessionId) throw new Error('La lectura ya no es válida. Intente nuevamente.');
        acquisition = null;
        update({ fmdTemplate: result.data.fmd_template, captureTimestamp: Date.now(), isAcquiring: false, status: 'Huella leída correctamente', error: null, errorKind: null });
        return true;
      }
      return false;
    } catch (error) {
      if (current !== generation) return false;
      const previous = acquisition; acquisition = null;
      await cancel(previous);
      if (current !== generation) return false;
      update({ isAcquiring: false, fmdTemplate: null, captureContext: null, captureTimestamp: 0, challengeId: null, sessionId: null, status: 'Captura no completada', error: error.response?.data?.detail || error.message, errorKind: 'capture' });
      return false;
    }
  }
  return { start, stop, refreshDevices, snapshot: () => ({ ...state }) };
}

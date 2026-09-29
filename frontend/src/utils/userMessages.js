const textOf = value => {
  if (typeof value === 'string') return value.trim();
  if (Array.isArray(value)) return value.map(item => item?.msg || item).filter(Boolean).join('. ');
  if (value && typeof value === 'object') {
    return textOf(value.message || value.detail || value.error || '');
  }
  return '';
};

export const friendlyBiometricError = (value, fallback = 'No se pudo leer la huella. Intente nuevamente.') => {
  const original = textOf(value);
  if (!original) return fallback;
  const message = original.toLowerCase();

  // Only label an error as a fingerprint mismatch when the server explicitly
  // identifies the huella. Role/context validation errors are not bad reads.
  if (message.includes('huella') && (message.includes('no corresponde') || message.includes('no coincide'))) {
    return 'La huella no coincide con la registrada para esta persona. No se guardó la firma. Use el mismo dedo que se registró e inténtelo de nuevo.';
  }
  if (message.includes('challenge') || message.includes('sesión actual') || message.includes('consumid') || message.includes('expirad') || message.includes('vencid')) {
    return 'La lectura tardó demasiado y venció. Pulse “Intentar de nuevo”.';
  }
  if (message.includes('contexto biométrico') || message.includes('contexto autorizado') || message.includes('captura ajena')) {
    return 'La lectura ya no corresponde a esta pantalla. Inicie una nueva captura.';
  }
  if (message.includes('attestation') || message.includes('protocolo v2') || message.includes('autorización de captura')) {
    return 'No se pudo comprobar la lectura. Intente nuevamente.';
  }
  if (message.includes('agente local') || message.includes('lector no disponible') || message.includes('no respondió') || message.includes('dispositivo')) {
    return 'No se pudo usar el lector de huellas. Revise que esté conectado e intente nuevamente.';
  }
  if (message.includes('requiere enrolamiento') || message.includes('requiere reenrolamiento') || message.includes('legacy')) {
    return 'Esta persona necesita registrar nuevamente su huella antes de firmar.';
  }
  if (message.includes('actualización fea') || message.includes('firma criptográfica bloqueada')) {
    return 'La firma electrónica del médico aún está pendiente de activación por otro administrador.';
  }
  if (message.includes('perfil médico en vertical') || message.includes('médico vertical')) {
    return 'Su huella fue reconocida, pero su perfil de firma en Vertical necesita revisión. Pida a Sistemas comprobar su cédula y autorización. No necesita registrar otra huella.';
  }

  return original
    .replaceAll('DigitalPersona', 'lector de huellas')
    .replaceAll('challenge', 'intento de lectura')
    .replaceAll('FMD', 'huella');
};

export const friendlyReaderStatus = value => {
  const status = textOf(value).toLowerCase();
  if (!status) return 'Preparando el lector…';
  if (status.includes('solicitando') || status.includes('iniciando')) return 'Preparando el lector…';
  if (status.includes('coloque')) return 'Coloque el dedo en el lector';
  if (status.includes('conectado')) return 'Lector listo';
  if (status.includes('ocupado')) return 'Lector ocupado. Espere un momento.';
  if (status.includes('correcta')) return 'Huella leída correctamente';
  if (status.includes('cancelada')) return 'Lector listo';
  if (status.includes('no completada')) return 'No se pudo leer la huella';
  if (status.includes('no disponible') || status.includes('desconectado')) return 'Lector no disponible';
  return textOf(value).replaceAll('DigitalPersona', 'lector de huellas');
};

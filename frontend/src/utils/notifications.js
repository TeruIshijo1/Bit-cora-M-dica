const NOTIFICATION_EVENT = 'hes:notification';

let notificationSequence = 0;

const inferType = (message) => {
  const value = String(message || '').toLowerCase();
  if (/(error|no se pudo|no pudo|falló|falla|incorrecto|invalido|inválido|excede|faltan|complete)/i.test(value)) {
    return 'error';
  }
  if (/(pendiente|solo lectura|aviso|cuidado|expirad)/i.test(value)) {
    return 'warning';
  }
  if (/(guardad|exitos|correctamente|registrad|actualizad|eliminad|cread)/i.test(value)) {
    return 'success';
  }
  return 'info';
};

export const notify = (message, options = {}) => {
  if (typeof window === 'undefined' || !message) return;

  window.dispatchEvent(new CustomEvent(NOTIFICATION_EVENT, {
    detail: {
      id: `${Date.now()}-${notificationSequence++}`,
      message: String(message),
      type: options.type || inferType(message),
      title: options.title || '',
      duration: options.duration || 5200,
    },
  }));
};

export const subscribeToNotifications = (listener) => {
  if (typeof window === 'undefined') return () => {};
  const handleNotification = (event) => listener(event.detail);
  window.addEventListener(NOTIFICATION_EVENT, handleNotification);
  return () => window.removeEventListener(NOTIFICATION_EVENT, handleNotification);
};

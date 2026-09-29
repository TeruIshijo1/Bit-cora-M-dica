import axios from 'axios';
import { purgeRegisteredBiometrics } from './utils/biometricLifecycle';
import { shouldOmitAuthorization } from './utils/authRequest';

// Base URL estándar para intranet / producción
const baseURL = import.meta.env.VITE_API_URL || '/api';
const AUTH_STORAGE_KEYS = [
  'token', 'rol', 'medico', 'usuario', 'medico_id', 'nombre_completo',
  'permisos_modulos', 'formatos_permitidos'
];
const LAST_ACTIVITY_KEY = 'hes_last_activity_at';

const clearStoredAuthentication = () => {
  AUTH_STORAGE_KEYS.forEach(key => localStorage.removeItem(key));
  localStorage.removeItem(LAST_ACTIVITY_KEY);
  sessionStorage.clear();
};

const saveRefreshedSession = response => {
  const refreshedToken = response?.headers?.['x-session-token'];
  if (!refreshedToken || !localStorage.getItem('token')) return false;
  localStorage.setItem('token', refreshedToken);
  return true;
};

const isBiometricMismatch = error => {
  const detail = error?.response?.data?.detail;
  const message = typeof detail === 'string'
    ? detail
    : (detail?.message || detail?.detail || '');
  const normalized = String(message).toLocaleLowerCase('es-MX');
  return normalized.includes('huella')
    && (normalized.includes('no corresponde') || normalized.includes('no coincide'));
};

const isAuthenticationFailure = error => {
  const detail = error?.response?.data?.detail;
  const message = typeof detail === 'string'
    ? detail
    : (detail?.message || detail?.detail || '');
  const normalized = String(message).toLocaleLowerCase('es-MX');
  return [
    'no autenticado',
    'not authenticated',
    'credenciales invalidas',
    'credenciales inválidas',
    'could not validate credentials',
    'sesión revocada',
    'usuario no existe',
    'sesión expirada por inactividad',
  ].some(phrase => normalized.includes(phrase));
};

const isBiometricSignatureRequest = config => {
  const method = String(config?.method || 'get').toUpperCase();
  if (!['POST', 'PUT', 'PATCH'].includes(method)) return false;

  const url = String(config?.url || '').toLocaleLowerCase('es-MX');
  // Una huella incorrecta es un fallo del intento de firma, no de la sesión
  // del médico. Nunca debemos purgar el JWT ni sacar al usuario de la pantalla
  // por un rechazo biométrico durante una operación clínica.
  if (url.includes('/firmar-biometrico')
    || url.includes('/biometrics/')
    || url.includes('/biometria/')
    || url.includes('/firmantes-biometricos')
    || url.includes('/huella')) return true;

  return false;
};

// Exportar la instancia de axios central
export const api = axios.create({
  baseURL
});

// Interceptor de solicitud para inyectar token JWT automáticamente en cada petición
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (shouldOmitAuthorization(config)) {
      if (typeof config.headers?.delete === 'function') config.headers.delete('Authorization');
      else if (config.headers) delete config.headers.Authorization;
    } else if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (token && !shouldOmitAuthorization(config) && config.sessionActivity === true) {
      const lastActivity = Number(localStorage.getItem(LAST_ACTIVITY_KEY));
      if (lastActivity) {
        const idleSeconds = Math.max(0, Math.floor((Date.now() - lastActivity) / 1000));
        config.headers['X-Session-Activity'] = String(idleSeconds);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor de respuesta para redirección limpia ante expiración de sesión (401)
api.interceptors.response.use(
  (response) => {
    saveRefreshedSession(response);
    return response;
  },
  (error) => {
    const sessionWasValidated = saveRefreshedSession(error.response);
    const authenticationWasValidated = error.response?.headers?.['x-session-authenticated'] === '1';
    // Un rechazo de la huella sólo cancela esa firma. Algunos errores de
    // matching heredados pueden llegar como 401; nunca deben purgar la sesión,
    // el formulario clínico ni las selecciones hechas en pantalla.
    const biometricMismatch = isBiometricMismatch(error);
    if (error.response && error.response.status === 401
      && isAuthenticationFailure(error)
      && !biometricMismatch
      && !sessionWasValidated
      && !authenticationWasValidated
      && !isBiometricSignatureRequest(error.config)
      && !shouldOmitAuthorization(error.config)) {
      purgeRegisteredBiometrics();
      clearStoredAuthentication();
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && !currentPath.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Función para obtener la URL base como string (útil para fetch)
export const getApiUrl = () => baseURL;

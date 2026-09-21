import axios from 'axios';
import { purgeRegisteredBiometrics } from './utils/biometricLifecycle';
import { shouldOmitAuthorization } from './utils/authRequest';

// Base URL estándar para intranet / producción
const baseURL = import.meta.env.VITE_API_URL || '/api';
const AUTH_STORAGE_KEYS = [
  'token', 'rol', 'medico', 'usuario', 'medico_id', 'nombre_completo',
  'permisos_modulos', 'formatos_permitidos'
];

const clearStoredAuthentication = () => {
  AUTH_STORAGE_KEYS.forEach(key => localStorage.removeItem(key));
  sessionStorage.clear();
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
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor de respuesta para redirección limpia ante expiración de sesión (401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401 && !shouldOmitAuthorization(error.config)) {
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

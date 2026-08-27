import axios from 'axios';

// Leer la URL guardada. Si es 'default', se usará la ruta relativa '/api'.
const savedUrl = localStorage.getItem('server_url') || '';

// Si hay una URL guardada (ej. https://xxx.ngrok-free.app) y no es 'default',
// construimos la baseURL absoluta. Si no, usamos la relativa para web.
const isDefault = savedUrl === 'default' || savedUrl === '';
const baseURL = isDefault ? '/api' : `${savedUrl.replace(/\/$/, '')}/api`;

// Exportar la instancia de axios central
export const api = axios.create({
  baseURL
});

// Interceptor de solicitud para inyectar token JWT automáticamente en cada petición
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && !config.headers.Authorization) {
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
    if (error.response && error.response.status === 401) {
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && !currentPath.startsWith('/login')) {
        localStorage.removeItem('token');
        localStorage.removeItem('rol');
        localStorage.removeItem('medico');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Función para obtener la URL base como string (útil para fetch)
export const getApiUrl = () => baseURL;


import axios from 'axios';

// Base URL estándar para intranet / producción
const baseURL = import.meta.env.VITE_API_URL || '/api';

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


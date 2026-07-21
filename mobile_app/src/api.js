import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const api = axios.create();

let cachedServerUrl = null;

export const setCachedServerUrl = (url) => {
  cachedServerUrl = url;
};

// Request interceptor para usar dinámicamente la URL del servidor y el token
api.interceptors.request.use(
  async (config) => {
    try {
      // Intentar obtener la URL del caché o del storage
      let baseUrl = cachedServerUrl;
      if (!baseUrl) {
        baseUrl = await SecureStore.getItemAsync('server_url');
        cachedServerUrl = baseUrl;
      }
      
      if (baseUrl) {
        // Asegurar que la baseURL se aplique a URLs relativas
        config.baseURL = baseUrl;
      }

      // Adjuntar el token si existe
      const token = await SecureStore.getItemAsync('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      return config;
    } catch (error) {
      return Promise.reject(error);
    }
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;

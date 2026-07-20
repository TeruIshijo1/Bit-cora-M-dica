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

// Función para obtener la URL base como string (útil para fetch)
export const getApiUrl = () => baseURL;

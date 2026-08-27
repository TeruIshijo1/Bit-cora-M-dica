import { useState, useCallback } from 'react';

/**
 * Custom Hook para estandarizar el manejo de errores de API y estado de carga.
 */
export function useApiError(initialError = null) {
  const [error, setError] = useState(initialError);
  const [loading, setLoading] = useState(false);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const handleApiError = useCallback((err, defaultMsg = 'Ocurrió un error inesperado al conectar con el servidor') => {
    let msg = defaultMsg;
    if (err?.response?.data?.detail) {
      if (typeof err.response.data.detail === 'string') {
        msg = err.response.data.detail;
      } else if (Array.isArray(err.response.data.detail)) {
        msg = err.response.data.detail.map(d => d.msg || JSON.stringify(d)).join(', ');
      }
    } else if (err?.message) {
      msg = err.message;
    }
    setError(msg);
    return msg;
  }, []);

  return {
    error,
    setError,
    clearError,
    handleApiError,
    loading,
    setLoading
  };
}

export default useApiError;

import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

// API para la base de datos principal (Servidor)
// const api = axios.create({ baseURL: 'http://localhost:8000/api' });

// API para el Agente Local de Huella (El programita que corre en la PC del médico)
const localAgentApi = axios.create({ baseURL: 'http://localhost:8081/api' });

/**
 * Hook que se comunica con nuestro propio backend FastAPI para
 * controlar el lector de huella U.are.U 4500 via WBF.
 *
 * Flujo:
 * 1. Al montar, consulta GET /fingerprint/status para ver si hay sensor
 * 2. Si hay sensor, llama POST /fingerprint/start para iniciar captura
 * 3. Hace polling cada 500ms con GET /fingerprint/poll hasta que el
 *    usuario ponga el dedo y se complete la captura
 */
export default function useFingerprint() {
  const [isReady, setIsReady] = useState(false);
  const [sample, setSample] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);
  const mountedRef = useRef(true);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await localAgentApi.get('/fingerprint/poll');
        if (!mountedRef.current) return;

        if (res.data.status === 'completed') {
          stopPolling();
          if (res.data.result?.success) {
            setSample(res.data.result.token);
          } else {
            setError(res.data.result?.error || 'Error en la captura');
          }
        }
        // Si status === 'idle', alguien más paró la captura o ya terminó
        if (res.data.status === 'idle') {
          stopPolling();
        }
      } catch {
        // Backend caido, no hacemos nada, reintentamos en el proximo tick
      }
    }, 500);
  }, [stopPolling]);

  const startCapture = useCallback(async () => {
    try {
      await localAgentApi.post('/fingerprint/start');
      startPolling();
    } catch {
      // Si falla el start, reintentamos en 3s
      setTimeout(() => startCapture(), 3000);
    }
  }, [startPolling]);

  useEffect(() => {
    mountedRef.current = true;

    const init = async (retries = 3) => {
      try {
        const res = await localAgentApi.get('/fingerprint/status');
        if (!mountedRef.current) return;

        if (res.data.available) {
          setIsReady(true);
          setError(null);
        } else {
          setIsReady(false);
          setError(res.data.message || 'Lector no disponible');
        }
      } catch (err) {
        if (!mountedRef.current) return;
        if (retries > 0) {
          setTimeout(() => init(retries - 1), 1000);
        } else {
          setIsReady(false);
          setError('No se puede conectar al Lector Local. Asegúrate de tener abierta la ventana negra.');
        }
      }
    };

    init();

    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, [stopPolling]);

  const clearSample = useCallback(() => {
    setSample(null);
    setError(null);
  }, []);

  return { isReady, sample, error, clearSample, startCapture };
}

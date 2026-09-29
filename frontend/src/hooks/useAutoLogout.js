import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { purgeBiometrics } from './useDigitalPersona';

const TIMEOUT_MS = 20 * 60 * 1000;
const HEARTBEAT_MS = 5 * 60 * 1000;
const LAST_ACTIVITY_KEY = 'hes_last_activity_at';
const AUTH_STORAGE_KEYS = [
  'token', 'rol', 'medico', 'usuario', 'medico_id', 'nombre_completo',
  'permisos_modulos', 'formatos_permitidos'
];

export default function useAutoLogout(isAuthenticated) {
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated || !localStorage.getItem('token')) return undefined;

    let timer = null;
    let expired = false;

    const lastActivity = () => Number(localStorage.getItem(LAST_ACTIVITY_KEY)) || 0;

    const expireSession = () => {
      if (expired) return;
      expired = true;
      if (timer) clearTimeout(timer);
      purgeBiometrics();
      AUTH_STORAGE_KEYS.forEach(key => localStorage.removeItem(key));
      localStorage.removeItem(LAST_ACTIVITY_KEY);
      sessionStorage.clear();
      alert('Tu sesión terminó después de 20 minutos sin actividad. Inicia sesión de nuevo.');
      navigate('/login', { replace: true });
    };

    const scheduleExpiry = () => {
      if (timer) clearTimeout(timer);
      const elapsed = Date.now() - lastActivity();
      if (elapsed >= TIMEOUT_MS) {
        expireSession();
        return;
      }
      timer = setTimeout(scheduleExpiry, TIMEOUT_MS - elapsed);
    };

    const handleActivity = () => {
      if (Date.now() - lastActivity() >= TIMEOUT_MS) {
        expireSession();
        return;
      }
      // Limita escrituras repetidas por mousemove sin alargar el cierre más de 10 s.
      if (Date.now() - lastActivity() >= 10_000) {
        localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
      }
      scheduleExpiry();
    };

    const handleStorage = event => {
      if (event.key === LAST_ACTIVITY_KEY) scheduleExpiry();
      if (event.key === 'token' && !event.newValue) {
        purgeBiometrics();
        navigate('/login', { replace: true });
      }
    };

    const checkWhenVisible = () => {
      if (document.visibilityState === 'visible') scheduleExpiry();
    };

    if (!lastActivity()) localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
    scheduleExpiry();

    const events = ['pointerdown', 'keydown', 'scroll', 'touchstart', 'mousemove'];
    events.forEach(event => window.addEventListener(event, handleActivity, { passive: true }));
    window.addEventListener('storage', handleStorage);
    document.addEventListener('visibilitychange', checkWhenVisible);

    const heartbeat = window.setInterval(() => {
      if (Date.now() - lastActivity() < TIMEOUT_MS && localStorage.getItem('token')) {
        api.get('/auth/session', { sessionActivity: true }).catch(() => {});
      }
    }, HEARTBEAT_MS);

    return () => {
      events.forEach(event => window.removeEventListener(event, handleActivity));
      window.removeEventListener('storage', handleStorage);
      document.removeEventListener('visibilitychange', checkWhenVisible);
      if (timer) clearTimeout(timer);
      clearInterval(heartbeat);
    };
  }, [isAuthenticated, navigate]);
}

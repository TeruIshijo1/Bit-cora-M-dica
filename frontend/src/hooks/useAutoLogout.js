import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

const TIMEOUT_MS = 12 * 60 * 60 * 1000; // 12 horas

export default function useAutoLogout() {
  const navigate = useNavigate();
  const timerRef = useRef(null);

  const resetTimer = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    
    // Solo iniciar timer si hay un token
    if (localStorage.getItem('token')) {
      timerRef.current = setTimeout(() => {
        // Expiro el tiempo
        localStorage.removeItem('token');
        localStorage.removeItem('rol');
        localStorage.removeItem('medico_id');
        localStorage.removeItem('nombre_completo');
        alert("Tu sesión ha expirado por inactividad. Por favor, ingresa de nuevo.");
        navigate('/login');
      }, TIMEOUT_MS);
    }
  };

  useEffect(() => {
    const events = ['mousemove', 'keydown', 'scroll', 'click'];
    
    const handleActivity = () => resetTimer();

    events.forEach(e => window.addEventListener(e, handleActivity));
    
    // Iniciar timer
    resetTimer();

    return () => {
      events.forEach(e => window.removeEventListener(e, handleActivity));
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [navigate]);
}

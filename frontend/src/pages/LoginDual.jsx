import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { FiLock, FiUser, FiEye, FiEyeOff, FiAlertCircle } from 'react-icons/fi';
import { MdLocalHospital, MdFingerprint } from 'react-icons/md';
import { useDigitalPersona } from '../hooks/useDigitalPersona';
import Button from '../components/ui/Button';
import PasswordChangeForm from '../components/PasswordChangeForm';
import { useAuth } from '../context/AuthContext';
import { friendlyBiometricError, friendlyReaderStatus } from '../utils/userMessages';

export default function LoginDual() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('medico'); // 'medico' or 'personal'
  const navigate = useNavigate();
  const { login } = useAuth();
  const [passwordChangeRequired, setPasswordChangeRequired] = useState(false);

  const handleAdminLogin = async (e) => {
    e.preventDefault();
    if (isProcessing) return;
    const attempt = ++loginAttemptRef.current;
    setIsProcessing(true);
    try {
      const res = await api.post('/auth/login/admin', { username, password }, { timeout: 15000 });
      if (attempt !== loginAttemptRef.current) return;
      login(res.data.access_token, { ...res.data, username });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('rol', res.data.rol);
      if (res.data.permisos_modulos) localStorage.setItem('permisos_modulos', res.data.permisos_modulos);
      else localStorage.removeItem('permisos_modulos');
      if (res.data.formatos_permitidos) localStorage.setItem('formatos_permitidos', res.data.formatos_permitidos);
      else localStorage.removeItem('formatos_permitidos');
      const role = res.data.rol;
      if (res.data.must_change_password) {
        setPassword('');
        setPasswordChangeRequired(true);
        return;
      }
      if (role === 'admin' || role === 'sistemas') {
        navigate('/admin');
      } else if (role === 'rh') {
        navigate('/rh');
      } else if (role === 'limpieza' || role === 'Mantenimiento/Limpieza') {
        navigate('/camas');
      } else {
        navigate('/captura');
      }
    } catch (error) {
      if (attempt !== loginAttemptRef.current) return;
      setLoginError(error.response?.data?.detail || 'No fue posible iniciar sesión. Revise sus datos e intente nuevamente.');
    } finally {
      if (attempt === loginAttemptRef.current) setIsProcessing(false);
    }
  };

  const mountTimeRef = useRef(Date.now());
  const processedTemplateRef = useRef(null);
  const loginAttemptRef = useRef(0);

  const { status, fmdTemplate, captureTimestamp, challengeId, sessionId, error, devices, resetFmd, startCapture, stopCapture, refreshDevices, isAcquiring } = useDigitalPersona();
  const startLoginCapture = () => {
    setLoginError(null);
    return startCapture({ action: 'LOGIN' });
  };
  const isReady = devices?.length > 0 && !error;

  // Purgar inmediatamente cualquier huella residual al montar y detener lector al desmontar
  useEffect(() => {
    resetFmd();
    mountTimeRef.current = Date.now();
    return () => {
      loginAttemptRef.current += 1;
      resetFmd();
      stopCapture();
    };
  }, []);

  const handleTabChange = (newTab) => {
    loginAttemptRef.current += 1;
    setIsProcessing(false);
    setActiveTab(newTab);
    setLoginError(null);
    resetFmd();
    processedTemplateRef.current = null;
    if (newTab === 'personal') {
      stopCapture();
    } else {
      mountTimeRef.current = Date.now();
      startLoginCapture();
    }
  };

  const handleBiometricLogin = async (customTemplate = null) => {
    const templateToUse = customTemplate || fmdTemplate;
    if (!templateToUse) {
      setLoginError('Por favor capture su huella primero.');
      return;
    }

    // Evitar procesar dos veces consecutivas el mismo template
    if (processedTemplateRef.current === templateToUse) {
      return;
    }
    processedTemplateRef.current = templateToUse;
    const activeChallengeId = challengeId;
    const activeSessionId = sessionId;
    const attempt = ++loginAttemptRef.current;

    // Purgar el template del estado de inmediato para que nunca persista
    resetFmd();
    setIsProcessing(true);
    setLoginError(null);
    try {
      const res = await api.post('/auth/login/biometric', {
        fmd_template: templateToUse,
        challenge_id: activeChallengeId,
        session_id: activeSessionId
      }, { timeout: 30000 });
      if (attempt !== loginAttemptRef.current) return;
      
      // En éxito: purgar memoria biométrica de forma definitiva y detener sensor
      resetFmd();
      stopCapture();

      login(res.data.access_token, { ...res.data, medico: res.data });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('rol', res.data.rol);
      localStorage.setItem('medico', JSON.stringify(res.data));
      if (res.data.formatos_permitidos) localStorage.setItem('formatos_permitidos', res.data.formatos_permitidos);
      else localStorage.removeItem('formatos_permitidos');

      const role = res.data.rol;
      if (role === 'medico' || role === 'ayudante') {
        navigate('/firma-express');
      } else if (role === 'admin' || role === 'sistemas') {
        navigate('/admin');
      } else if (role === 'rh') {
        navigate('/rh');
      } else if (role === 'limpieza' || role === 'Mantenimiento/Limpieza') {
        navigate('/camas');
      } else {
        navigate('/captura');
      }
    } catch (err) {
      if (attempt !== loginAttemptRef.current) return;
      setLoginError(friendlyBiometricError(err.response?.data?.detail, 'No se pudo validar la huella. Pulse “Intentar de nuevo”.'));
      resetFmd();
      processedTemplateRef.current = null;
    } finally {
      if (attempt === loginAttemptRef.current) setIsProcessing(false);
    }
  };

  // Auto-activar sensor en cuanto el lector esté detectado en la pestaña de Médicos
  useEffect(() => {
    if (activeTab === 'medico' && isReady && !isAcquiring && !isProcessing && !fmdTemplate && !loginError) {
      startLoginCapture();
    }
  }, [activeTab, isReady, isAcquiring, isProcessing, fmdTemplate, loginError]);

  useEffect(() => {
    if (activeTab === 'medico' && fmdTemplate && !isProcessing) {
      // Descartar si la huella fue capturada antes de que esta pantalla terminara de montar
      if (captureTimestamp && captureTimestamp < mountTimeRef.current) {
        console.warn("Descartando huella previa al montaje del login");
        resetFmd();
        return;
      }
      handleBiometricLogin(fmdTemplate);
    }
  }, [fmdTemplate, captureTimestamp, isProcessing, activeTab]);

  if (passwordChangeRequired) return <PasswordChangeForm onComplete={() => { setPasswordChangeRequired(false); setPassword(''); }} />;

  return (
    <div className="he-login min-h-screen flex bg-white font-sans text-slate-800">
      
      {/* Left Side: Branding / Institutional Background */}
      <div className="he-login-brand hidden lg:flex w-1/2 relative overflow-hidden flex-col justify-center items-center text-white">
        {/* Decorative Circles */}
        <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-white opacity-5 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-cyan-400 opacity-10 rounded-full blur-3xl pointer-events-none"></div>
        
        <div className="z-10 flex flex-col items-center px-12 text-center">
          <div className="mb-8 bg-white p-3 rounded-2xl shadow-xl inline-block border-2 border-white/20">
            <img src="/logo.png?v=6" alt="Hospital Escandón" className="h-32 object-contain" />
          </div>
          <h1 className="text-4xl font-bold tracking-wide mb-4 text-white drop-shadow-lg">
            Bitácora Clínica HE
          </h1>
          <p className="text-blue-100/90 text-lg max-w-md font-light leading-relaxed">
            Información clara y segura para la atención de cada paciente.
          </p>
        </div>
      </div>

      {/* Right Side: Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 sm:p-12">
        <div className="max-w-md w-full">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-black text-slate-800 tracking-tight mb-2">Iniciar sesión</h2>
            <p className="text-slate-500 text-sm">Elija cómo desea entrar</p>
          </div>

          {/* Navigation Tabs */}
          <div className="flex bg-slate-100 p-1.5 rounded-2xl mb-8 border border-slate-200/80">
            <button 
              onClick={() => handleTabChange('medico')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-all ${
                activeTab === 'medico' 
                  ? 'bg-white text-hes-blue-main shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-300/50'
              }`}
            >
              <MdLocalHospital className="text-lg" /> Médico con huella
            </button>
            <button 
              onClick={() => handleTabChange('personal')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-all ${
                activeTab === 'personal' 
                  ? 'bg-white text-hes-blue-main shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-300/50'
              }`}
            >
              <FiUser className="text-lg" /> Usuario y contraseña
            </button>
          </div>

          <div className="he-login-panel bg-white p-8 rounded-2xl border border-slate-200">
            {/* Tab: Médicos (Biométrico) */}
            {activeTab === 'medico' && (
              <div className="flex flex-col items-center animate-fadeIn">
                <p className="text-slate-600 text-center mb-6 text-sm font-medium">
                  {isProcessing 
                    ? 'Comprobando la huella…' 
                    : isAcquiring 
                    ? 'Coloque su dedo en el lector.' 
                    : 'Conecte el lector y pulse “Leer huella”.'}
                </p>
                
                <div className={`w-40 h-40 rounded-full border-4 flex items-center justify-center relative group transition-all duration-300 mb-6 ${
                  isProcessing 
                    ? 'border-emerald-500 bg-emerald-50' 
                    : isAcquiring 
                    ? 'border-hes-blue-main bg-blue-50/70 shadow-lg shadow-blue-500/20' 
                    : 'border-slate-200 bg-slate-50'
                }`}>
                  {isAcquiring && !isProcessing && (
                    <div className="absolute inset-0 rounded-full border-2 border-hes-blue-main animate-ping opacity-30"></div>
                  )}
                  <MdFingerprint className={`text-7xl transition-all duration-300 z-10 ${
                    isProcessing 
                      ? 'text-emerald-600 scale-110 drop-shadow-md' 
                      : isAcquiring 
                      ? 'text-hes-blue-main animate-pulse drop-shadow-md' 
                      : fmdTemplate 
                      ? 'text-emerald-600' 
                      : 'text-slate-400'
                  }`} />
                </div>

                {loginError && (
                  <div className="mb-5 bg-rose-50 text-rose-700 px-4 py-3 rounded-xl flex items-start gap-3 w-full border border-rose-200 text-xs font-semibold">
                    <FiAlertCircle className="mt-0.5 text-rose-600 flex-shrink-0 text-base" />
                    <span>{friendlyBiometricError(loginError, loginError)}</span>
                  </div>
                )}

                {error && !loginError && (
                  <div className="mb-5 bg-rose-50 text-rose-700 px-4 py-3 rounded-xl flex items-start gap-3 w-full border border-rose-200 text-xs font-semibold">
                    <FiAlertCircle className="mt-0.5 text-rose-600 flex-shrink-0 text-base" />
                    <span>{friendlyBiometricError(error)}</span>
                  </div>
                )}

                {(error || loginError) && !isProcessing && !isAcquiring && (
                  <Button className="w-full mb-4" onClick={devices?.length ? startLoginCapture : refreshDevices} icon={<MdFingerprint />}>
                    {devices?.length ? 'Intentar de nuevo' : 'Buscar lector'}
                  </Button>
                )}

                {isProcessing && (
                  <div className="mb-5 bg-blue-50 text-blue-700 px-4 py-3 rounded-xl flex items-center justify-center gap-3 w-full border border-blue-200 text-xs font-bold animate-pulse">
                    <FiLock className="text-blue-600 animate-spin text-base" />
                    <span>Comprobando la huella…</span>
                  </div>
                )}

                {isReady && !isProcessing && (
                  <div className="w-full space-y-3">
                    <div className="bg-slate-50 text-slate-700 px-4 py-2.5 rounded-xl border border-slate-200 text-center w-full text-xs font-bold">
                      {isAcquiring ? 'Lector listo · Coloque el dedo' : friendlyReaderStatus(status)}
                    </div>

                    {!isAcquiring && (
                      <button 
                        type="button"
                        onClick={() => { resetFmd(); startLoginCapture(); }}
                        className="w-full bg-hes-blue-main hover:bg-hes-blue-dark text-white font-bold py-3.5 rounded-xl shadow-md transition-all flex justify-center items-center gap-2 text-sm"
                      >
                        <MdFingerprint className="text-xl" /> Leer huella
                      </button>
                    )}
                  </div>
                )}

                {!isReady && !error && (
                  <div className="mt-4 bg-slate-50 text-slate-600 px-4 py-3 rounded-xl flex items-center justify-center gap-2 w-full border border-slate-200 text-xs font-medium">
                    <FiLock className="animate-spin text-slate-400" />
                    <span>Buscando el lector de huellas…</span>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Personal (Password) */}
            {activeTab === 'personal' && (
              <div className="animate-fadeIn">
                {loginError && (
                  <div role="alert" className="mb-5 bg-rose-50 text-rose-700 px-4 py-3 rounded-xl flex items-start gap-3 border border-rose-200 text-sm font-semibold">
                    <FiAlertCircle className="mt-0.5 shrink-0" />
                    <span>{loginError}</span>
                  </div>
                )}
                <form onSubmit={handleAdminLogin} className="space-y-6">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">Usuario</label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <FiUser className="text-slate-400" />
                      </div>
                      <input 
                        type="text" 
                        required
                        className="w-full border border-slate-300 rounded-xl pl-10 p-3.5 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-hes-blue-main focus:border-transparent transition-colors" 
                        placeholder="Ej. enfermera_piso1"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">Contraseña</label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <FiLock className="text-slate-400" />
                      </div>
                      <input 
                        type={showPassword ? "text" : "password"} 
                        required
                        className="w-full border border-slate-300 rounded-xl pl-10 p-3.5 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-hes-blue-main focus:border-transparent transition-colors" 
                        placeholder="••••••••"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                      />
                      <button 
                        type="button" 
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                      >
                        {showPassword ? <FiEyeOff /> : <FiEye />}
                      </button>
                    </div>
                  </div>

                  <Button type="submit" isLoading={isProcessing} className="w-full mt-4">
                    Entrar
                  </Button>
                </form>
              </div>
            )}
          </div>
          
          <div className="text-center mt-6 text-slate-400 text-xs font-medium">
            Uso interno · Hospital Escandón
          </div>
        </div>
      </div>
      
    </div>
  );
}

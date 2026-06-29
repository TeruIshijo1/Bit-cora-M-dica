import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FiLock, FiUser, FiEye, FiEyeOff, FiAlertCircle } from 'react-icons/fi';
import { MdLocalHospital, MdFingerprint } from 'react-icons/md';
import { useDigitalPersona } from '../hooks/useDigitalPersona';

const serverIP = window.location.hostname;
const api = axios.create({ baseURL: `http://${serverIP}:8000/api` });

export default function LoginDual() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('medico'); // 'medico' or 'personal'
  const navigate = useNavigate();

  const handleAdminLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post('/auth/login/admin', { username, password });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('rol', res.data.rol);
      if (res.data.rol === 'admin') {
        navigate('/admin');
      } else if (res.data.rol === 'rh') {
        navigate('/rh');
      } else {
        navigate('/captura');
      }
    } catch (error) {
      console.error(error);
      const msg = error.response?.data?.detail || error.message;
      alert(`Error de acceso: ${msg}`);
    }
  };

  const { status, fmdTemplate, error, devices, resetFmd, startCapture, isAcquiring } = useDigitalPersona();
  const isReady = devices?.length > 0 && !error;

  const handleBiometricLogin = async () => {
    if (!fmdTemplate) {
      setLoginError('Por favor capture su huella primero.');
      return;
    }
    setIsProcessing(true);
    setLoginError(null);
    try {
      const res = await api.post('/auth/login/biometric', { huella_token: "digitalpersona", fmd_template: fmdTemplate });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('rol', res.data.rol);
      localStorage.setItem('medico', JSON.stringify(res.data));
      navigate('/firma-express');
    } catch (err) {
      setLoginError('Huella no reconocida o médico no registrado.');
      resetFmd();
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-white font-sans text-slate-800">
      
      {/* Left Side: Branding / Institutional Background */}
      <div className="hidden lg:flex w-1/2 bg-gradient-to-br from-[#0a2342] to-[#175b8f] relative overflow-hidden flex-col justify-center items-center text-white">
        {/* Decorative Circles */}
        <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-white opacity-5 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-cyan-400 opacity-10 rounded-full blur-3xl pointer-events-none"></div>
        
        <div className="z-10 flex flex-col items-center px-12 text-center">
          <div className="bg-white p-6 rounded-3xl shadow-xl mb-8 border-4 border-white/10 backdrop-blur-sm">
            <img src="/logo.png" alt="Hospital Escandón" className="h-32 object-contain drop-shadow-sm" />
          </div>
          <h1 className="text-4xl font-bold tracking-wide mb-4 text-white drop-shadow-lg">
            Bitácora Médica HES
          </h1>
          <p className="text-blue-100/90 text-lg max-w-md font-light leading-relaxed">
            Plataforma centralizada para el registro de atenciones, firmas biométricas y administración hospitalaria.
          </p>
        </div>
        
        <div className="absolute bottom-8 left-0 right-0 text-center text-white/40 text-sm font-medium">
          &copy; {new Date().getFullYear()} Hospital Escandón. Todos los derechos reservados.
        </div>
      </div>

      {/* Right Side: Login Panel */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center items-center p-8 sm:p-12 xl:p-24 bg-slate-50 relative">
        <div className="w-full max-w-md">
          
          <div className="text-center mb-10 lg:hidden">
            <img src="/logo.png" alt="Hospital Escandón" className="h-32 mx-auto mb-4 drop-shadow-sm" />
            <h1 className="text-2xl font-bold text-hes-blue-main">Bitácora Médica HES</h1>
          </div>

          <div className="mb-8">
            <h2 className="text-3xl font-extrabold text-slate-800 mb-2">Bienvenido</h2>
            <p className="text-slate-500">Seleccione su método de acceso para continuar.</p>
          </div>

          {/* Custom Tabs */}
          <div className="flex bg-slate-200 p-1 rounded-xl mb-8">
            <button
              onClick={() => setActiveTab('medico')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-bold text-sm transition-all ${
                activeTab === 'medico' 
                  ? 'bg-white text-hes-blue-main shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-300/50'
              }`}
            >
              <MdFingerprint className="text-xl" /> Médicos
            </button>
            <button
              onClick={() => setActiveTab('personal')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-bold text-sm transition-all ${
                activeTab === 'personal' 
                  ? 'bg-white text-hes-blue-main shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-300/50'
              }`}
            >
              <FiUser className="text-lg" /> Personal / Admin
            </button>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
            {/* Tab: Médicos (Biométrico) */}
            {activeTab === 'medico' && (
              <div className="flex flex-col items-center animate-fadeIn">
                <p className="text-slate-500 text-center mb-8 text-sm">
                  Pulse "Capturar Huella" y coloque su dedo en el lector biométrico.
                </p>
                
                <div className={`w-40 h-40 rounded-full border-4 flex items-center justify-center relative group transition-colors duration-300 mb-8 ${isProcessing ? 'border-hes-green bg-[#e6f4ed]' : 'border-slate-50 bg-slate-50'}`}>
                  {isAcquiring && !isProcessing && <div className="absolute inset-0 rounded-full border border-hes-blue-light animate-ping opacity-20"></div>}
                  <MdFingerprint className={`text-7xl transition-all duration-300 z-10 ${isProcessing ? 'text-hes-green scale-110 drop-shadow-lg' : isAcquiring ? 'text-hes-blue-main animate-pulse drop-shadow-md' : fmdTemplate ? 'text-hes-green' : 'text-slate-300'}`} />
                </div>

                {loginError && (
                  <div className="mb-6 bg-red-50 text-red-700 px-4 py-3 rounded-lg flex items-start gap-3 w-full border border-red-100 text-sm">
                    <FiAlertCircle className="mt-0.5 text-red-600 flex-shrink-0" />
                    <span>{loginError}</span>
                  </div>
                )}

                {error && !loginError && (
                  <div className="mb-6 bg-red-50 text-red-700 px-4 py-3 rounded-lg flex items-start gap-3 w-full border border-red-100 text-sm">
                    <FiAlertCircle className="mt-0.5 text-red-600 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                {isProcessing && (
                  <div className="mb-6 bg-blue-50 text-blue-700 px-4 py-3 rounded-lg flex items-start gap-3 w-full border border-blue-100 text-sm">
                    <FiLock className="mt-0.5 text-blue-600 flex-shrink-0 animate-spin" />
                    <span>Verificando identidad, por favor espere...</span>
                  </div>
                )}

                {isReady && !isProcessing && (
                  <div className="w-full">
                    {fmdTemplate ? (
                      <>
                        <button 
                          onClick={handleBiometricLogin}
                          className="w-full bg-hes-green hover:bg-green-600 text-white font-bold py-4 rounded-xl shadow-md transition-all transform hover:-translate-y-1 flex justify-center items-center gap-2 mb-3 text-lg"
                        >
                          <MdFingerprint className="text-2xl" /> Ingresar al Sistema
                        </button>
                        <button 
                          onClick={resetFmd}
                          className="w-full text-slate-400 hover:text-slate-600 text-sm font-semibold py-2 transition-colors"
                        >
                          Volver a escanear
                        </button>
                      </>
                    ) : (
                      <div className="flex flex-col items-center gap-4 w-full">
                        <div className="bg-slate-50 text-slate-600 px-4 py-3 rounded-lg border border-slate-200 text-center w-full text-sm font-medium">
                          {status}
                        </div>
                        {!isAcquiring && (
                           <button 
                             onClick={startCapture}
                             className="w-full bg-hes-blue-main hover:bg-[#003870] text-white font-bold py-4 rounded-xl shadow-md transition-all flex justify-center items-center gap-2"
                           >
                             Capturar Huella
                           </button>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {!isReady && !error && (
                  <div className="mt-4 bg-slate-50 text-slate-600 px-4 py-3 rounded-lg flex items-start gap-3 w-full border border-slate-200 text-sm">
                    <FiLock className="mt-0.5 flex-shrink-0" />
                    <span>Buscando dispositivo lector de huellas...</span>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Personal (Password) */}
            {activeTab === 'personal' && (
              <div className="animate-fadeIn">
                <form onSubmit={handleAdminLogin} className="space-y-6">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">Nombre de Usuario</label>
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

                  <button type="submit" className="w-full bg-hes-blue-main hover:bg-[#003870] text-white font-bold py-4 rounded-xl shadow-md transition-all flex justify-center items-center gap-2 mt-4 text-lg">
                    Iniciar Sesión
                  </button>
                </form>
              </div>
            )}
          </div>
          
        </div>
      </div>
      
    </div>
  );
}

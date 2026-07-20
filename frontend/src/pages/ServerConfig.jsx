import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const ServerConfig = () => {
  const [serverUrl, setServerUrl] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    // Cargar URL guardada si existe, excepto si es 'default'
    const savedUrl = localStorage.getItem('server_url');
    if (savedUrl && savedUrl !== 'default') {
      setServerUrl(savedUrl);
    }
  }, []);

  const handleSave = (e) => {
    e.preventDefault();
    if (serverUrl.trim() === '') {
      alert('Por favor ingresa una URL válida o usa el botón de Web.');
      return;
    }
    localStorage.setItem('server_url', serverUrl.trim());
    // Recargar para aplicar los cambios en la instancia global de axios
    window.location.href = '/login';
  };

  const handleUseDefault = () => {
    localStorage.setItem('server_url', 'default');
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-xl shadow-lg max-w-md w-full">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-blue-900 mb-2">Configuración de Conexión</h1>
          <p className="text-slate-600 text-sm">
            Para que la aplicación se conecte correctamente, ingresa la dirección del servidor (Ej: enlace de ngrok).
          </p>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              URL del Servidor:
            </label>
            <input
              type="url"
              placeholder="https://0000-00-00.ngrok-free.app"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors shadow-md"
          >
            Guardar y Continuar
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-200 text-center">
          <p className="text-xs text-slate-500 mb-3">
            ¿Estás accediendo desde la computadora (Web)?
          </p>
          <button
            onClick={handleUseDefault}
            className="text-sm font-medium text-slate-600 hover:text-blue-600 underline transition-colors"
          >
            Usar servidor por defecto (Recomendado para Web)
          </button>
        </div>
      </div>
    </div>
  );
};

export default ServerConfig;

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiClock, FiMapPin, FiActivity, FiCheckCircle, FiUser, FiX } from 'react-icons/fi';
import { MdBed } from 'react-icons/md';
import { FaStethoscope } from 'react-icons/fa';

const serverIP = window.location.hostname;
const api = axios.create({ baseURL: `http://${serverIP}:8000/api` });

// Helper to get token
const getToken = () => localStorage.getItem('token');

export const TrasladoModal = ({ paciente, areas = [], onClose, onSuccess }) => {
  const [area, setArea] = useState(paciente?.area_hospitalaria || '');
  const [habitacion, setHabitacion] = useState(paciente?.num_habitacion || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!paciente) return null;

  const handleSave = async () => {
    if (!area || !habitacion) {
      setError("El área y la habitación son obligatorias");
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.put(`/pacientes/${paciente.id}`, {
        nombre_completo: paciente.nombre_completo,
        num_habitacion: habitacion,
        area_hospitalaria: area
      }, { headers: { Authorization: `Bearer ${getToken()}` } });
      
      setLoading(false);
      onSuccess();
    } catch (e) {
      console.error(e);
      setError("Error al trasladar al paciente.");
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-blue-50">
          <h2 className="text-lg font-bold text-blue-900 flex items-center gap-2">
            <FiMapPin /> Mover Paciente
          </h2>
          <button onClick={onClose} className="text-blue-400 hover:text-blue-600">
            <FiX className="text-xl" />
          </button>
        </div>
        
        <div className="p-6 space-y-4">
          <div>
            <p className="text-sm text-slate-500">Paciente:</p>
            <p className="font-semibold text-slate-800">{paciente.nombre_completo}</p>
          </div>

          {error && <div className="text-sm text-red-600 bg-red-50 p-2 rounded">{error}</div>}

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">Nueva Área Hospitalaria</label>
            <select 
              className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-slate-700 focus:ring-2 focus:ring-blue-500 outline-none"
              value={area} 
              onChange={e => setArea(e.target.value)}
            >
              <option value="">Seleccione el Área...</option>
              {areas.map(a => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">Nueva Habitación / Cama</label>
            <input 
              type="text" 
              className="w-full border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="Ej. 101, Cama 3" 
              value={habitacion} 
              onChange={e => setHabitacion(e.target.value)} 
            />
          </div>
        </div>
        
        <div className="p-5 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-slate-600 hover:bg-slate-200 transition-colors">
            Cancelar
          </button>
          <button onClick={handleSave} disabled={loading} className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-sm transition-colors disabled:opacity-50">
            {loading ? 'Guardando...' : 'Confirmar Traslado'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const PatientJourneyModal = ({ paciente, onClose }) => {
  const [eventos, setEventos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (paciente) {
      fetchJourney();
    }
  }, [paciente]);

  const fetchJourney = async () => {
    try {
      const res = await api.get(`/pacientes/${paciente.id}/journey`, { headers: { Authorization: `Bearer ${getToken()}` } });
      setEventos(res.data);
    } catch (e) {
      console.error("Error fetching journey", e);
    } finally {
      setLoading(false);
    }
  };

  if (!paciente) return null;

  const getIconForType = (tipo) => {
    switch(tipo) {
      case 'INGRESO': return <FiUser className="text-white text-lg" />;
      case 'TRASLADO': return <MdBed className="text-white text-lg" />;
      case 'ATENCION': return <FiActivity className="text-white text-lg" />;
      case 'FIRMA_MEDICA': return <FaStethoscope className="text-white text-lg" />;
      case 'ALTA': return <FiCheckCircle className="text-white text-lg" />;
      default: return <FiClock className="text-white text-lg" />;
    }
  };

  const getColorForType = (tipo) => {
    switch(tipo) {
      case 'INGRESO': return 'bg-emerald-500';
      case 'TRASLADO': return 'bg-blue-500';
      case 'ATENCION': return 'bg-orange-500';
      case 'FIRMA_MEDICA': return 'bg-indigo-500';
      case 'ALTA': return 'bg-slate-800';
      default: return 'bg-slate-400';
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        <div className="p-6 border-b border-slate-100 flex justify-between items-center sticky top-0 bg-white z-10 shadow-sm">
          <div>
            <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <FiActivity className="text-blue-600" /> Mapa de Trayectoria
            </h2>
            <p className="text-sm text-slate-500 mt-1">{paciente.nombre_completo}</p>
          </div>
          <button onClick={onClose} className="p-2 bg-slate-100 rounded-full hover:bg-slate-200 text-slate-500 transition-colors">
            <FiX className="text-xl" />
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto bg-slate-50/50 flex-1 relative">
          {loading ? (
            <div className="flex justify-center p-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <div className="relative pl-4 md:pl-8 py-4">
              {/* Vertical line */}
              <div className="absolute left-10 md:left-14 top-8 bottom-8 w-0.5 bg-slate-200 rounded-full"></div>
              
              <div className="space-y-8 relative">
                {eventos.map((evento, idx) => (
                  <div key={idx} className="flex gap-4 md:gap-6 items-start group">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center shadow-md z-10 shrink-0 ${getColorForType(evento.tipo)} ring-4 ring-white group-hover:scale-110 transition-transform`}>
                      {getIconForType(evento.tipo)}
                    </div>
                    
                    <div className="bg-white p-4 md:p-5 rounded-xl border border-slate-100 shadow-sm flex-1 hover:shadow-md transition-shadow">
                      <div className="flex flex-col md:flex-row md:justify-between md:items-center mb-2 gap-1">
                        <span className={`text-xs font-bold tracking-wider uppercase px-2 py-1 rounded-full w-max ${getColorForType(evento.tipo).replace('bg-', 'text-').replace('500', '600')} bg-opacity-10 ${getColorForType(evento.tipo).replace('500', '100')}`}>
                          {evento.tipo.replace('_', ' ')}
                        </span>
                        <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
                          <FiClock /> {new Date(evento.fecha).toLocaleString()}
                        </span>
                      </div>
                      
                      <p className="text-slate-700 font-medium mb-2">{evento.descripcion}</p>
                      
                      <div className="flex items-center gap-1.5 text-xs text-slate-500">
                        <FiUser /> <span>Registrado por: <strong>{evento.usuario}</strong></span>
                      </div>
                    </div>
                  </div>
                ))}
                
                {eventos.length === 0 && (
                  <div className="text-center p-8 text-slate-500 bg-white rounded-xl border border-slate-100">
                    No hay eventos registrados para este paciente.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

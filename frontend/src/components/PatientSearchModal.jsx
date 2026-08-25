import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiSearch, FiX, FiUser, FiCalendar, FiActivity, FiArrowRight, FiClock, FiFileText } from 'react-icons/fi';
import { MdLocalHospital } from 'react-icons/md';
import { api } from '../api';

export default function PatientSearchModal({ isOpen, onClose }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('todos'); // 'todos', 'activos', 'alta'
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        if (inputRef.current) inputRef.current.focus();
      }, 100);
      performSearch('');
    } else {
      setSearchTerm('');
    }
  }, [isOpen]);

  // Manejo de atajo Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Debounce de búsqueda
  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(() => {
      performSearch(searchTerm);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const performSearch = async (term) => {
    try {
      setLoading(true);
      const res = await api.get(`/ehr/pacientes/buscar?q=${encodeURIComponent(term)}&limit=40`);
      if (res.data && Array.isArray(res.data)) {
        setResults(res.data);
      } else {
        setResults([]);
      }
    } catch (err) {
      console.error("Error searching patients:", err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPatient = (ptNum) => {
    onClose();
    navigate(`/ehr/${ptNum}`);
  };

  if (!isOpen) return null;

  const filteredResults = results.filter(p => {
    if (filter === 'activos') return p.is_active;
    if (filter === 'alta') return !p.is_active;
    return true;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 md:pt-20 px-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div 
        className="bg-white rounded-3xl max-w-3xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[80vh] animate-scaleUp"
        onClick={(e) => e.stopPropagation()}
      >
        {/* BARRA DE BÚSQUEDA */}
        <div className="p-4 md:p-5 border-b border-slate-100 bg-slate-50/50 flex items-center gap-3">
          <div className="p-2.5 bg-hes-blue-main text-white rounded-2xl shadow-sm">
            <FiSearch className="text-xl" />
          </div>
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar paciente por Nombre, Folio (#5704) o CURP..."
              className="w-full bg-transparent border-none outline-none text-slate-800 text-sm md:text-base font-bold placeholder:text-slate-400 placeholder:font-medium"
            />
          </div>
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-200/50 transition-colors"
            >
              <FiX className="text-base" />
            </button>
          )}
          <button
            onClick={onClose}
            className="text-xs font-extrabold text-slate-500 hover:text-slate-800 bg-slate-200/60 hover:bg-slate-200 px-2.5 py-1.5 rounded-xl transition-colors hidden sm:block"
          >
            ESC
          </button>
        </div>

        {/* FILTROS RÁPIDOS */}
        <div className="flex items-center justify-between px-5 py-2.5 border-b border-slate-100 bg-white text-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-500">Filtrar:</span>
            <button
              onClick={() => setFilter('todos')}
              className={`px-3 py-1 rounded-full font-bold transition-all ${
                filter === 'todos' 
                  ? 'bg-hes-blue-main text-white shadow-sm' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Todos ({results.length})
            </button>
            <button
              onClick={() => setFilter('activos')}
              className={`px-3 py-1 rounded-full font-bold transition-all flex items-center gap-1 ${
                filter === 'activos' 
                  ? 'bg-emerald-600 text-white shadow-sm' 
                  : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Hospitalizados ({results.filter(p => p.is_active).length})
            </button>
            <button
              onClick={() => setFilter('alta')}
              className={`px-3 py-1 rounded-full font-bold transition-all ${
                filter === 'alta' 
                  ? 'bg-slate-700 text-white shadow-sm' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              De Alta / Históricos ({results.filter(p => !p.is_active).length})
            </button>
          </div>
          {loading && (
            <span className="text-[11px] text-hes-blue-main font-bold animate-pulse flex items-center gap-1">
              <FiActivity className="animate-spin" /> Buscando...
            </span>
          )}
        </div>

        {/* LISTADO DE RESULTADOS */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5 divide-y divide-slate-50">
          {filteredResults.length > 0 ? (
            filteredResults.map((pt) => (
              <div
                key={pt.pt_num}
                onClick={() => handleSelectPatient(pt.pt_num)}
                className="pt-2.5 first:pt-0 group cursor-pointer"
              >
                <div className="p-3.5 rounded-2xl border border-slate-200/80 bg-white hover:bg-blue-50/40 hover:border-hes-blue-main/40 transition-all flex items-start justify-between gap-3 shadow-sm hover:shadow">
                  <div className="space-y-1 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-extrabold text-slate-800 text-sm group-hover:text-hes-blue-main transition-colors">
                        {pt.name}
                      </span>
                      <span className="text-[11px] font-extrabold bg-blue-50 text-hes-blue-main px-2 py-0.5 rounded-md border border-blue-100">
                        Exp: #{pt.pt_num}
                      </span>
                      {pt.is_active ? (
                        <span className="text-[10px] font-black bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                          <MdLocalHospital /> {pt.cama || 'Hospitalizado'}
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                          Alta / Histórico
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                      <span>Edad: <strong>{pt.age} años</strong></span>
                      <span>•</span>
                      <span>Sexo: <strong>{pt.gender === 'M' ? 'Masculino' : 'Femenino'}</strong></span>
                      {pt.curp && (
                        <>
                          <span>•</span>
                          <span className="font-mono text-[11px]">CURP: {pt.curp}</span>
                        </>
                      )}
                      {pt.entry_date && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <FiCalendar className="text-[10px]" /> Ingreso: {pt.entry_date}
                          </span>
                        </>
                      )}
                      {pt.exit_date && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1 text-amber-700 font-semibold">
                            <FiClock className="text-[10px]" /> Egreso: {pt.exit_date}
                          </span>
                        </>
                      )}
                    </div>

                    <div className="text-xs text-slate-600 line-clamp-1 pt-0.5">
                      <strong className="text-slate-700">Diagnóstico:</strong> {pt.diagnostico}
                    </div>
                  </div>

                  <div className="self-center">
                    <button
                      type="button"
                      className="flex items-center gap-1 bg-slate-100 group-hover:bg-hes-blue-main group-hover:text-white text-slate-600 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0"
                    >
                      <span>Abrir</span>
                      <FiArrowRight className="text-xs group-hover:translate-x-0.5 transition-transform" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="py-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl">
                <FiUser />
              </div>
              <div className="space-y-1">
                <h4 className="font-bold text-slate-700 text-sm">
                  {loading ? 'Buscando en catálogo general...' : 'No se encontraron pacientes'}
                </h4>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  {loading 
                    ? 'Consultando expedientes...' 
                    : 'Intenta buscar por apellidos, nombre de pila, folio de expediente o CURP.'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* PIE DE PÁGINA */}
        <div className="px-5 py-3 border-t border-slate-100 bg-slate-50 text-[11px] text-slate-500 flex justify-between items-center">
          <span>Presiona <kbd className="font-bold bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700">ESC</kbd> para cerrar</span>
          <span className="font-semibold text-hes-blue-main flex items-center gap-1">
            <FiFileText /> Acceso instantáneo a expedientes activos e históricos
          </span>
        </div>
      </div>
    </div>
  );
}

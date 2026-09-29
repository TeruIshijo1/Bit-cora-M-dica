import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiActivity, FiArrowRight, FiCalendar, FiClock, FiFileText, FiSearch, FiUser, FiX } from 'react-icons/fi';
import { MdLocalHospital } from 'react-icons/md';
import { useCamasQuery, usePatientSearchQuery } from '../hooks/useQueries';
import { getOccupiedBedPatients } from '../utils/patientDirectory';

export default function PatientSearchModal({ isOpen, onClose }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('todos');
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const normalizedSearch = searchTerm.trim();
  const hasExplicitSearch = normalizedSearch.length >= 2;
  const bedsQuery = useCamasQuery(isOpen);
  const searchQuery = usePatientSearchQuery(normalizedSearch, isOpen && hasExplicitSearch);

  const closeModal = useCallback(() => {
    setSearchTerm('');
    setFilter('todos');
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      const focusTimer = setTimeout(() => inputRef.current?.focus(), 100);
      return () => clearTimeout(focusTimer);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && isOpen) closeModal();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, closeModal]);

  const bedPatients = useMemo(
    () => getOccupiedBedPatients(bedsQuery.data),
    [bedsQuery.data]
  );
  const results = hasExplicitSearch ? (searchQuery.data || []) : bedPatients;
  const filteredResults = hasExplicitSearch
    ? results.filter((patient) => {
        if (filter === 'activos') return patient.is_active;
        if (filter === 'alta') return !patient.is_active;
        return true;
      })
    : results;
  const loading = hasExplicitSearch ? searchQuery.isFetching : bedsQuery.isFetching;

  const handleSelectPatient = (ptNum) => {
    closeModal();
    navigate(`/ehr/${encodeURIComponent(ptNum)}`);
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 md:pt-20 px-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) closeModal();
      }}
    >
      <div
        className="bg-white rounded-3xl max-w-3xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[80vh] animate-scaleUp"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="p-4 md:p-5 border-b border-slate-100 bg-slate-50/50 flex items-center gap-3">
          <div className="p-2.5 bg-hes-blue-main text-white rounded-2xl shadow-sm">
            <FiSearch className="text-xl" />
          </div>
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Buscar paciente por nombre, folio o CURP..."
              className="w-full bg-transparent border-none outline-none text-slate-800 text-sm md:text-base font-bold placeholder:text-slate-400 placeholder:font-medium"
              aria-label="Buscar paciente por nombre, folio o CURP"
            />
          </div>
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-200/50 transition-colors"
              aria-label="Limpiar búsqueda"
            >
              <FiX />
            </button>
          )}
          <button
            type="button"
            onClick={closeModal}
            className="text-xs font-extrabold text-slate-500 hover:text-slate-800 bg-slate-200/60 hover:bg-slate-200 px-2.5 py-1.5 rounded-xl hidden sm:block"
          >
            ESC
          </button>
        </div>

        <div className="px-5 py-3 border-b border-slate-100 bg-white flex flex-wrap items-center justify-between gap-2 text-xs">
          <div>
            <div className="font-black text-slate-800">
              {hasExplicitSearch ? 'Resultados de búsqueda' : 'Pacientes en cama'}
            </div>
            <div className="text-slate-400 mt-0.5">
              {hasExplicitSearch
                ? 'La búsqueda explícita incluye camas virtuales y expedientes históricos.'
                : 'Acceso rápido al censo físico actual.'}
            </div>
          </div>
          {hasExplicitSearch && (
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setFilter('todos')}
                className={`px-2.5 py-1 rounded-full font-bold ${filter === 'todos' ? 'bg-hes-blue-main text-white' : 'bg-slate-100 text-slate-600'}`}
              >
                Todos ({results.length})
              </button>
              <button
                type="button"
                onClick={() => setFilter('activos')}
                className={`px-2.5 py-1 rounded-full font-bold ${filter === 'activos' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700'}`}
              >
                Activos ({results.filter((patient) => patient.is_active).length})
              </button>
              <button
                type="button"
                onClick={() => setFilter('alta')}
                className={`px-2.5 py-1 rounded-full font-bold ${filter === 'alta' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-600'}`}
              >
                Históricos ({results.filter((patient) => !patient.is_active).length})
              </button>
            </div>
          )}
          {loading && <FiActivity className="text-hes-blue-main animate-spin" />}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {filteredResults.length > 0 ? (
            filteredResults.map((patient) => (
              <button
                type="button"
                key={`${patient.pt_num}-${patient.cama || 'catalogo'}`}
                onClick={() => handleSelectPatient(patient.pt_num)}
                className="w-full text-left p-3.5 rounded-2xl border border-slate-200/80 bg-white hover:bg-blue-50/40 hover:border-hes-blue-main/40 transition-all flex items-start justify-between gap-3 shadow-sm hover:shadow group"
              >
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-extrabold text-slate-800 text-sm group-hover:text-hes-blue-main transition-colors truncate">
                      {patient.name}
                    </span>
                    <span className="text-[11px] font-extrabold bg-blue-50 text-hes-blue-main px-2 py-0.5 rounded-md border border-blue-100">
                      Exp. #{patient.pt_num}
                    </span>
                    {patient.is_active ? (
                      <span className="text-[10px] font-black bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <MdLocalHospital /> {patient.cama || 'Hospitalizado'}
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                        Alta / Histórico
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                    {patient.age && patient.age !== '--' && <span>Edad: <strong>{patient.age} años</strong></span>}
                    {patient.curp && <span className="font-mono text-[11px]">CURP: {patient.curp}</span>}
                    {patient.entry_date && <span className="flex items-center gap-1"><FiCalendar className="text-[10px]" /> Ingreso: {patient.entry_date}</span>}
                    {patient.exit_date && <span className="flex items-center gap-1 text-amber-700 font-semibold"><FiClock className="text-[10px]" /> Egreso: {patient.exit_date}</span>}
                  </div>

                  {patient.diagnostico && (
                    <div className="text-xs text-slate-600 line-clamp-1 pt-0.5">
                      <strong className="text-slate-700">Diagnóstico:</strong> {patient.diagnostico}
                    </div>
                  )}
                </div>
                <span className="self-center flex items-center gap-1 bg-slate-100 group-hover:bg-hes-blue-main group-hover:text-white text-slate-600 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0">
                  Abrir <FiArrowRight className="group-hover:translate-x-0.5 transition-transform" />
                </span>
              </button>
            ))
          ) : (
            <div className="py-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl">
                <FiUser />
              </div>
              <div className="space-y-1">
                <h4 className="font-bold text-slate-700 text-sm">
                  {loading ? 'Consultando...' : hasExplicitSearch ? 'No se encontraron pacientes' : 'No hay pacientes en camas físicas'}
                </h4>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  {hasExplicitSearch
                    ? 'Prueba con otro apellido, folio o CURP.'
                    : 'Escribe el nombre, folio o CURP para abrir cualquier otro expediente.'}
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="px-5 py-3 border-t border-slate-100 bg-slate-50 text-[11px] text-slate-500 flex justify-between items-center gap-3">
          <span>Presiona <kbd className="font-bold bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700">ESC</kbd> para cerrar</span>
          <span className="font-semibold text-hes-blue-main flex items-center gap-1">
            <FiFileText /> Expedientes activos e históricos
          </span>
        </div>
      </div>
    </div>
  );
}

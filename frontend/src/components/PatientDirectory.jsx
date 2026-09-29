import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiActivity, FiArrowRight, FiFileText, FiSearch, FiUser, FiX } from 'react-icons/fi';
import { MdLocalHospital } from 'react-icons/md';
import { useCamasQuery, usePatientSearchQuery } from '../hooks/useQueries';
import { getOccupiedBedPatients } from '../utils/patientDirectory';

function PatientResultCard({ patient, onOpen }) {
  const isBedPatient = patient.source === 'bed';
  const isActive = patient.is_active || isBedPatient;

  return (
    <button
      type="button"
      onClick={() => onOpen(patient.pt_num)}
      className="w-full text-left p-4 rounded-2xl border border-slate-200 bg-white hover:border-hes-blue-main/50 hover:bg-blue-50/40 hover:shadow-md transition-all group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-extrabold text-slate-800 group-hover:text-hes-blue-main transition-colors truncate">
              {patient.name}
            </span>
            <span className="text-[11px] font-extrabold bg-blue-50 text-hes-blue-main px-2 py-0.5 rounded-md border border-blue-100">
              Exp. #{patient.pt_num}
            </span>
            <span className={`text-[10px] font-black px-2 py-0.5 rounded-full border flex items-center gap-1 ${
              isActive
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-slate-100 text-slate-600 border-slate-200'
            }`}>
              {isActive && <MdLocalHospital />}
              {patient.cama || (isActive ? 'Hospitalizado' : 'Alta / Histórico')}
            </span>
          </div>

          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
            {patient.doctor && <span>Médico: <strong>{patient.doctor}</strong></span>}
            {patient.age && patient.age !== '--' && <span>Edad: <strong>{patient.age} años</strong></span>}
            {patient.curp && <span className="font-mono text-[11px]">CURP: {patient.curp}</span>}
            {patient.entry_date && <span>Ingreso: {patient.entry_date}</span>}
          </div>
        </div>

        <span className="shrink-0 self-center flex items-center gap-1 bg-slate-100 group-hover:bg-hes-blue-main group-hover:text-white text-slate-600 px-3 py-1.5 rounded-xl text-xs font-bold transition-all">
          Abrir <FiArrowRight className="group-hover:translate-x-0.5 transition-transform" />
        </span>
      </div>
    </button>
  );
}

export default function PatientDirectory() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const normalizedSearch = searchTerm.trim();
  const hasExplicitSearch = normalizedSearch.length >= 2;
  const bedsQuery = useCamasQuery(true);
  const searchQuery = usePatientSearchQuery(normalizedSearch, hasExplicitSearch);

  const bedPatients = useMemo(
    () => getOccupiedBedPatients(bedsQuery.data),
    [bedsQuery.data]
  );
  const patients = hasExplicitSearch ? (searchQuery.data || []) : bedPatients;
  const loading = hasExplicitSearch ? searchQuery.isFetching : bedsQuery.isLoading;
  const error = hasExplicitSearch ? searchQuery.error : bedsQuery.error;

  const openPatient = (ptNum) => navigate(`/ehr/${encodeURIComponent(ptNum)}`);

  return (
    <div className="flex-1 min-h-screen bg-slate-50 p-4 md:p-8">
      <div className="max-w-5xl mx-auto space-y-5">
        <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-5 md:p-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.14em] text-teal-700">
                <FiFileText /> Expedientes clínicos
              </div>
              <h1 className="text-2xl md:text-3xl font-black text-slate-900 tracking-tight mt-1">
                {hasExplicitSearch ? 'Buscar expediente' : 'Pacientes en cama'}
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                {hasExplicitSearch
                  ? 'Resultados del catálogo clínico. Puedes localizar también pacientes en cama virtual o históricos.'
                  : 'Acceso directo a los pacientes que actualmente ocupan una cama física.'}
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-bold text-slate-500 bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl">
              <MdLocalHospital className="text-emerald-600 text-base" />
              {hasExplicitSearch ? 'Búsqueda ampliada' : `${bedPatients.length} en cama`}
            </div>
          </div>

          <div className="relative mt-6">
            <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Buscar por nombre, folio o CURP..."
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-3.5 pl-11 pr-11 text-sm font-semibold text-slate-800 outline-none focus:border-hes-blue-main focus:bg-white focus:ring-4 focus:ring-blue-100 transition-all"
              aria-label="Buscar expediente por nombre, folio o CURP"
              autoFocus
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200"
                aria-label="Limpiar búsqueda"
              >
                <FiX />
              </button>
            )}
          </div>
          {!hasExplicitSearch && (
            <div className="mt-3 text-xs text-slate-400 flex items-center gap-2">
              <FiActivity className="text-emerald-500" />
              Escribe al menos 2 caracteres para buscar otro expediente.
            </div>
          )}
        </section>

        <section className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 md:px-6 py-4 border-b border-slate-100 flex items-center justify-between gap-3">
            <div>
              <h2 className="font-black text-slate-900 text-base">
                {hasExplicitSearch ? 'Resultados' : 'Censo clínico actual'}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {hasExplicitSearch ? `${patients.length} coincidencia(s)` : 'Solo pacientes asignados a camas físicas'}
              </p>
            </div>
            {loading && <FiActivity className="text-hes-blue-main animate-spin" />}
          </div>

          {error ? (
            <div className="p-8 text-center text-sm text-rose-600">
              No se pudo consultar el censo. Intenta actualizar la pantalla.
            </div>
          ) : patients.length > 0 ? (
            <div className="p-4 md:p-5 grid grid-cols-1 md:grid-cols-2 gap-3">
              {patients.map((patient) => (
                <PatientResultCard key={`${patient.pt_num}-${patient.cama || 'catalogo'}`} patient={patient} onOpen={openPatient} />
              ))}
            </div>
          ) : (
            <div className="p-10 text-center space-y-3">
              <div className="w-12 h-12 mx-auto rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center text-xl">
                <FiUser />
              </div>
              <div className="font-bold text-slate-700 text-sm">
                {loading ? 'Consultando...' : hasExplicitSearch ? 'No se encontraron expedientes' : 'No hay pacientes en camas físicas'}
              </div>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                {hasExplicitSearch
                  ? 'Prueba con el nombre completo, el folio o la CURP.'
                  : 'Los pacientes en cama virtual se localizan escribiendo su nombre, folio o CURP.'}
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import { 
  FiSearch, FiBell, FiCalendar, FiFileText, FiActivity, FiImage, 
  FiSettings, FiUser, FiMessageSquare, FiPlus, FiClock, FiChevronRight 
} from 'react-icons/fi';
import { MdOutlineBloodtype, MdOutlineMonitorHeart, MdOutlineWaterDrop } from 'react-icons/md';
import { FaTemperatureHalf } from 'react-icons/fa6';

export default function PatientDashboard() {
  const { pt_num } = useParams();
  const patientId = pt_num || '5704'; // Default a 5704 para la demo si entran desde menú

  const [activeTab, setActiveTab] = useState('Timeline');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('token');
        const res = await api.get(`/ehr/paciente/${patientId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        if (res.data && res.data.patient && !res.data.error) {
          setData(res.data);
        } else {
          setError(res.data?.error || res.data?.detail || "Error al obtener datos");
        }
      } catch (err) {
        console.error("Error fetching EHR:", err);
        setError("Error de conexión con el servidor. ¿Está el backend actualizado y ejecutándose?");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [patientId]);

  if (loading) {
    return <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-slate-50 text-slate-500 font-semibold">Cargando expediente clínico...</div>;
  }

  if (error || !data) {
    return <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-slate-50 text-red-500 font-semibold">{error || "No se pudo cargar el expediente."}</div>;
  }

  const { patient, vitals, timelineEvents, clinicalNotes, medications } = data;

  const getVitalIcon = (label) => {
    if (label.includes('Cardíaca')) return <MdOutlineMonitorHeart className="text-hes-blue-main text-2xl" />;
    if (label.includes('Arterial')) return <MdOutlineWaterDrop className="text-blue-500 text-2xl" />;
    if (label.includes('O2')) return <FiActivity className="text-teal-500 text-2xl" />;
    if (label.includes('Temp')) return <FaTemperatureHalf className="text-orange-500 text-2xl" />;
    return <FiActivity className="text-slate-400 text-2xl" />;
  };

  const getVitalColor = (label) => {
    if (label.includes('Cardíaca')) return "text-hes-blue-main";
    if (label.includes('Arterial')) return "text-blue-500";
    if (label.includes('O2')) return "text-teal-500";
    if (label.includes('Temp')) return "text-orange-500";
    return "text-slate-500";
  };

  return (
    <div className="flex h-[calc(100vh-64px)] bg-slate-50 text-slate-800 overflow-hidden font-sans">
      
      {/* LEFT SIDEBAR (Navegación Interna del EHR) */}
      <aside className="w-56 bg-white border-r border-slate-200 flex flex-col justify-between hidden md:flex">
        <div className="p-4">
          <ul className="space-y-1 mt-4">
            <li><button className="w-full flex items-center gap-3 px-4 py-2.5 bg-hes-blue-light/10 text-hes-blue-main font-semibold rounded-lg"><FiUser className="text-lg" /> Pacientes</button></li>
            <li><button className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-700 rounded-lg transition-colors"><FiCalendar className="text-lg" /> Calendario</button></li>
            <li><button className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-700 rounded-lg transition-colors"><FiFileText className="text-lg" /> Notas</button></li>
            <li><button className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-700 rounded-lg transition-colors"><MdOutlineBloodtype className="text-lg" /> Laboratorios</button></li>
            <li><button className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-700 rounded-lg transition-colors"><FiImage className="text-lg" /> Imagenología</button></li>
          </ul>
        </div>
        <div className="p-4 border-t border-slate-100">
          <button className="w-full flex items-center gap-3 px-4 py-2 text-slate-500 hover:bg-slate-50 rounded-lg"><FiSettings className="text-lg" /> Ajustes</button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-slate-50/50">
        
        {/* HEADER BÚSQUEDA (Simulado) */}
        <div className="flex justify-between items-center mb-6">
          <div className="relative w-full max-w-md">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input type="text" placeholder="Buscar pacientes, registros, órdenes..." className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-hes-blue-main/30" />
          </div>
        </div>

        {/* TOP CARD: INFO DEL PACIENTE */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-6">
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 border-b border-slate-100 pb-5">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 border border-slate-200">
                <FiUser className="text-3xl" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
                  {patient.name} <span className="text-sm font-medium text-hes-blue-main bg-hes-blue-light/10 px-2 py-0.5 rounded-full">{patient.age} • {patient.gender}</span>
                </h1>
                <div className="text-sm text-slate-500 mt-1 flex gap-3">
                  <span>MRN: <span className="font-medium text-slate-700">{patient.mrn}</span></span>
                  <span>•</span>
                  <span>FN: <span className="font-medium text-slate-700">{patient.dob}</span></span>
                </div>
                <div className="text-sm text-slate-500 mt-0.5">
                  {patient.phone} • {patient.email}
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2 bg-red-50 text-red-700 border border-red-100 px-3 py-1.5 rounded-lg text-sm font-medium">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              Alergias: {patient.allergies}
            </div>
          </div>

          {/* VITALS */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mt-5">
            {vitals.map((v, i) => (
              <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                <div className={`p-2 bg-white rounded-lg shadow-sm border border-slate-100 ${getVitalColor(v.label)}`}>
                  {getVitalIcon(v.label)}
                </div>
                <div>
                  <div className="text-xs font-medium text-slate-500 uppercase tracking-wide truncate max-w-[100px]" title={v.label}>{v.label}</div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-lg font-bold text-slate-800">{v.value}</span>
                    <span className="text-xs text-slate-500">{v.unit}</span>
                  </div>
                  <div className="text-[10px] font-medium text-hes-blue-main">{v.status}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* BOTTOM SECTION: TABS & SIDEBAR */}
        <div className="flex flex-col xl:flex-row gap-6">
          
          {/* TABS CONTENT */}
          <div className="flex-1">
            <div className="flex gap-6 border-b border-slate-200 mb-5 px-2">
              {['Notas Clínicas', 'Medicamentos', 'Resultados de Laboratorio', 'Timeline'].map(tab => (
                <button 
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`pb-3 text-sm font-semibold transition-colors relative ${activeTab === tab ? 'text-hes-blue-main' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  {tab}
                  {activeTab === tab && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-hes-blue-main rounded-t-full"></div>}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* TIMELINE PANEL */}
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-bold text-slate-800">Línea de Tiempo</h3>
                  <select className="text-sm border-none bg-slate-50 rounded text-slate-600 font-medium cursor-pointer outline-none">
                    <option>Visitas Recientes</option>
                  </select>
                </div>
                <div className="space-y-5 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
                  {timelineEvents.map((evt, i) => (
                    <div key={i} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                      <div className="flex items-center justify-center w-4 h-4 rounded-full border-2 border-white bg-hes-blue-main text-slate-500 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 absolute left-0 md:left-1/2 -ml-2 md:ml-0 z-10"></div>
                      <div className="w-[calc(100%-2rem)] md:w-[calc(50%-2rem)] ml-8 md:ml-0 p-4 bg-white rounded-xl border border-slate-100 shadow-sm hover:border-hes-blue-main/30 transition-colors cursor-pointer">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-slate-800 text-sm">{evt.date} • {evt.type}</span>
                        </div>
                        <div className="text-xs text-slate-500 mb-2">{evt.time}</div>
                        <p className="text-sm text-slate-600 leading-relaxed mb-3">{evt.desc}</p>
                        {evt.type === 'Nota de Evolución' && (
                          <div className="flex items-center gap-4 mt-2">
                            <button className="text-xs font-semibold text-hes-blue-main flex items-center gap-1 hover:underline">Ver nota <FiChevronRight /></button>
                            <a 
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
                              target="_blank" 
                              rel="noreferrer"
                              className="text-xs font-semibold text-emerald-600 flex items-center gap-1 hover:underline"
                            >
                              <FiFileText /> Imprimir PDF
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4 text-center">
                  <button className="text-sm font-semibold text-hes-blue-main hover:underline">Ver línea de tiempo completa →</button>
                </div>
              </div>

              {/* MEDICATIONS PANEL */}
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-bold text-slate-800">Medicamentos</h3>
                  <button className="text-sm text-hes-blue-main font-semibold flex items-center gap-1 hover:bg-hes-blue-light/10 px-2 py-1 rounded"><FiPlus /> Añadir</button>
                </div>
                <div className="space-y-3">
                  {medications && medications.length > 0 ? medications.map((med, i) => (
                    <div key={i} className="flex justify-between items-center p-3 border border-slate-100 rounded-xl hover:bg-slate-50 transition-colors">
                      <div>
                        <div className="font-bold text-slate-800 text-sm">{med.name}</div>
                        <div className="text-xs text-slate-500">{med.instruction}</div>
                      </div>
                      <div className="flex items-center gap-4 text-right">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${med.status === 'Activo' ? 'bg-teal-50 text-teal-700' : 'bg-slate-100 text-slate-600'}`}>
                          {med.status}
                        </span>
                        <div className="hidden sm:block">
                          <div className="text-sm font-semibold text-slate-700">{med.dose}</div>
                          <div className="text-xs text-slate-500">{med.freq}</div>
                        </div>
                      </div>
                    </div>
                  )) : (
                    <div className="text-sm text-slate-500 py-4 text-center">No hay medicamentos activos.</div>
                  )}
                </div>
                <div className="mt-4 text-center">
                  <button className="text-sm font-semibold text-hes-blue-main hover:underline">Ver todos los medicamentos →</button>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT SIDEBAR: QUICK ACTIONS */}
          <div className="w-full xl:w-72 flex flex-col gap-6">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
              <h3 className="font-bold text-slate-800 mb-4">Acciones Rápidas</h3>
              <div className="space-y-2">
                <button className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-hes-blue-main hover:bg-hes-blue-light/5 transition-all text-left group">
                  <div className="p-2 bg-slate-50 text-slate-600 rounded-lg group-hover:bg-hes-blue-main group-hover:text-white transition-colors"><MdOutlineBloodtype className="text-lg" /></div>
                  <div>
                    <div className="font-bold text-slate-800 text-sm group-hover:text-hes-blue-main">Ordenar Labs</div>
                    <div className="text-xs text-slate-500">BH, QS, Perfil Lipídico</div>
                  </div>
                </button>
                <button className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-hes-blue-main hover:bg-hes-blue-light/5 transition-all text-left group">
                  <div className="p-2 bg-slate-50 text-slate-600 rounded-lg group-hover:bg-hes-blue-main group-hover:text-white transition-colors"><FiMessageSquare className="text-lg" /></div>
                  <div>
                    <div className="font-bold text-slate-800 text-sm group-hover:text-hes-blue-main">Enviar Mensaje</div>
                    <div className="text-xs text-slate-500">Al equipo médico</div>
                  </div>
                </button>
                <button className="w-full flex items-center gap-3 p-3 rounded-xl border border-hes-blue-main/30 bg-hes-blue-light/5 hover:bg-hes-blue-main hover:text-white transition-all text-left group">
                  <div className="p-2 bg-hes-blue-main text-white rounded-lg group-hover:bg-white group-hover:text-hes-blue-main transition-colors"><FiFileText className="text-lg" /></div>
                  <div>
                    <div className="font-bold text-hes-blue-main text-sm group-hover:text-white">Crear Nota</div>
                    <div className="text-xs text-hes-blue-main/70 group-hover:text-blue-100">Nueva nota clínica</div>
                  </div>
                </button>
                <button className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-hes-blue-main hover:bg-hes-blue-light/5 transition-all text-left group">
                  <div className="p-2 bg-slate-50 text-slate-600 rounded-lg group-hover:bg-hes-blue-main group-hover:text-white transition-colors"><FiImage className="text-lg" /></div>
                  <div>
                    <div className="font-bold text-slate-800 text-sm group-hover:text-hes-blue-main">Solicitar Imagen</div>
                    <div className="text-xs text-slate-500">Rayos X, TAC, RM</div>
                  </div>
                </button>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-slate-800">Próximas Citas</h3>
                <button className="text-xs font-semibold text-hes-blue-main hover:underline flex items-center">Calendario <FiChevronRight/></button>
              </div>
              <div className="space-y-4">
                <div className="flex gap-4">
                  <div className="text-center w-12 shrink-0">
                    <div className="text-xs font-bold text-slate-500 uppercase">May</div>
                    <div className="text-xl font-bold text-slate-800">28</div>
                  </div>
                  <div>
                    <div className="font-bold text-slate-800 text-sm">Dr. Luis Pérez</div>
                    <div className="text-xs font-semibold text-teal-600">Visita de Seguimiento</div>
                    <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5"><FiClock/> 10:00 AM</div>
                  </div>
                </div>
                <div className="flex gap-4 pt-4 border-t border-slate-100">
                  <div className="text-center w-12 shrink-0">
                    <div className="text-xs font-bold text-slate-500 uppercase">Jun</div>
                    <div className="text-xl font-bold text-slate-800">10</div>
                  </div>
                  <div>
                    <div className="font-bold text-slate-800 text-sm">Toma de Muestra</div>
                    <div className="text-xs text-slate-500">Laboratorio Central</div>
                    <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5"><FiClock/> 11:30 AM</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

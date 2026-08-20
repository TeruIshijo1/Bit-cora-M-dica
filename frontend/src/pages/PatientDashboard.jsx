import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import { useDigitalPersona } from '../hooks/useDigitalPersona';
import { 
  FiSearch, FiBell, FiCalendar, FiFileText, FiActivity, FiImage, 
  FiSettings, FiUser, FiMessageSquare, FiPlus, FiClock, FiChevronRight, 
  FiEdit3, FiCheckCircle, FiAlertCircle, FiScissors, FiHome, FiUsers, 
  FiFolder, FiDownload, FiCheck, FiLayers, FiSave, FiX, FiCheckSquare,
  FiArrowLeft, FiExternalLink, FiShield, FiLock 
} from 'react-icons/fi';
import { 
  MdOutlineBloodtype, MdOutlineMonitorHeart, MdOutlineWaterDrop, 
  MdOutlineRestaurant, MdOutlineMedicalServices, MdOutlineBiotech,
  MdFingerprint, MdVerifiedUser 
} from 'react-icons/md';
import { FaTemperatureHalf } from 'react-icons/fa6';

export default function PatientDashboard() {
  const { pt_num } = useParams();
  const patientId = pt_num || '5704';

  const [activeTab, setActiveTab] = useState('Timeline'); // DEFAULT TAB IS TIMELINE
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFormatArea, setSelectedFormatArea] = useState('Todos');
  const [selectedFormat, setSelectedFormat] = useState(null); // FORMATO SELECCIONADO EN PESTAÑA FORMATOS
  const [firmas, setFirmas] = useState([]); // Firmas biométricas de PostgreSQL

  // Lector Biométrico DigitalPersona
  const { 
    status: dpStatus, 
    isReady: dpReady, 
    isAcquiring: dpAcquiring, 
    fmdTemplate: dpFmd, 
    error: dpError, 
    startCapture: dpStartCapture, 
    resetFmd: dpResetFmd, 
    stopCapture: dpStopCapture 
  } = useDigitalPersona();

  // Modal de Firma Biométrica
  const [signingModal, setSigningModal] = useState({
    open: false,
    slot: 1,
    title: 'Nota de Evolución 1',
    content: '',
    submitting: false,
    successMsg: null,
    errorMsg: null
  });

  // Modal de Auditoría y Verificación de Sello Completo NOM
  const [auditModal, setAuditModal] = useState({
    open: false,
    firma: null,
    loading: false,
    verification: null,
    copied: null
  });

  const handleOpenAuditModal = async (firma) => {
    setAuditModal({
      open: true,
      firma: firma,
      loading: true,
      verification: null,
      copied: null
    });

    try {
      const res = await api.post(`/ehr/paciente/${patientId}/verificar-integridad`, {
        firma_id: firma.id
      });
      if (res.data) {
        setAuditModal(prev => ({
          ...prev,
          loading: false,
          verification: res.data
        }));
      }
    } catch (err) {
      console.error("Error verifying integrity in real time:", err);
      setAuditModal(prev => ({
        ...prev,
        loading: false,
        verification: {
          integro: false,
          estado: "No se pudo completar la verificación en tiempo real con el servidor."
        }
      }));
    }
  };

  // Modal de Captura / Edición de Nota de Evolución
  const [notaModal, setNotaModal] = useState({
    open: false,
    isEdit: false,
    evolution_num: 1,
    fecha: new Date().toISOString().split('T')[0],
    hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
    turno: 'Matutino',
    vitals_ta: '120/80',
    vitals_fc: '80',
    vitals_fr: '18',
    vitals_sato2: '98',
    vitals_peso: '78.5',
    vitals_talla: '1.72',
    vitals_temp: '36.5',
    subjetivo: '',
    objetivo: '',
    analisis: '',
    plan: '',
    medico: 'JOSE JOSE PRUEBA ENRIQUEZ',
    cedula: 'PRUEBA-99281',
    mip: ''
  });
  const [savingNota, setSavingNota] = useState(false);

  const fetchFirmas = async () => {
    try {
      const res = await api.get(`/ehr/paciente/${patientId}/firmas`);
      if (res.data && Array.isArray(res.data)) {
        setFirmas(res.data);
      }
    } catch(e){
      console.warn("Could not load firmas:", e);
    }
  };

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

  useEffect(() => {
    fetchData();
    fetchFirmas();
  }, [patientId]);

  // Manejar captura de huella para firmar documento
  const handleOpenBiometricSign = (slot, title, content) => {
    setSigningModal({
      open: true,
      slot,
      title,
      content,
      submitting: false,
      successMsg: null,
      errorMsg: null
    });
    dpResetFmd();
    dpStartCapture();
  };

  useEffect(() => {
    if (signingModal.open && dpFmd && !signingModal.submitting && !signingModal.successMsg) {
      const executeBiometricSign = async () => {
        try {
          setSigningModal(prev => ({ ...prev, submitting: true, errorMsg: null }));
          const res = await api.post(`/ehr/paciente/${patientId}/firmar-biometrico`, {
            codigo_formato: 'HE-DIRMED-SINPRO-PLT-87/01',
            tipo_documento: `Nota de Evolución de Urgencias (Evolución ${signingModal.slot})`,
            evolution_slot: signingModal.slot,
            fmd_template: dpFmd,
            contenido_resumen: signingModal.content
          });
          
          if (res.data && res.data.success) {
            setSigningModal(prev => ({
              ...prev,
              submitting: false,
              successMsg: `¡Documento firmado biométricamente con éxito! Sello: ${res.data.firma.sello_digital}`
            }));
            await fetchFirmas();
            await fetchData();
            setTimeout(() => {
              setSigningModal(prev => ({ ...prev, open: false }));
              dpResetFmd();
            }, 2500);
          } else {
            setSigningModal(prev => ({ ...prev, submitting: false, errorMsg: res.data?.error || "Error al firmar documento." }));
          }
        } catch (err) {
          console.error("Error signing biometricamente:", err);
          setSigningModal(prev => ({ 
            ...prev, 
            submitting: false, 
            errorMsg: err.response?.data?.detail || "Huella no reconocida o error de conexión biométrica." 
          }));
          dpResetFmd();
        }
      };
      executeBiometricSign();
    }
  }, [dpFmd, signingModal.open]);

  if (loading) {
    return <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-slate-50 text-slate-500 font-semibold">Cargando expediente clínico...</div>;
  }

  if (error || !data) {
    return <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-slate-50 text-red-500 font-semibold">{error || "No se pudo cargar el expediente."}</div>;
  }

  const { 
    patient, vitals = [], timelineEvents = [], clinicalNotes = [], 
    evoluciones = {}, medications = [], dietas = {}, cuidados_enfermeria = [], 
    laboratorios = [], imagenologia = [], proximas_citas = [], 
    formatos_disponibles = [], cargos_solicitudes = {} 
  } = data;

  const getVitalIcon = (label) => {
    if (label.includes('Cardíaca')) return <MdOutlineMonitorHeart className="text-hes-blue-main text-2xl" />;
    if (label.includes('Arterial')) return <MdOutlineWaterDrop className="text-blue-500 text-2xl" />;
    if (label.includes('O2')) return <FiActivity className="text-teal-500 text-2xl" />;
    if (label.includes('Temp')) return <FaTemperatureHalf className="text-orange-500 text-2xl" />;
    return <FiActivity className="text-slate-400 text-2xl" />;
  };

  const getVitalColor = (label) => {
    if (label.includes('Cardíaca')) return 'bg-blue-50 text-hes-blue-main';
    if (label.includes('Arterial')) return 'bg-blue-50 text-blue-600';
    if (label.includes('O2')) return 'bg-teal-50 text-teal-600';
    if (label.includes('Temp')) return 'bg-orange-50 text-orange-600';
    return 'bg-slate-50 text-slate-600';
  };

  // Abrir modal para nueva evolución
  const handleOpenNewEvol = (slotNum = 1) => {
    let doctorName = 'JOSE JOSE PRUEBA ENRIQUEZ';
    let doctorCed = 'PRUEBA-99281';
    try {
      const storedMed = JSON.parse(localStorage.getItem('medico'));
      if (storedMed && storedMed.nombre_completo) {
        doctorName = storedMed.nombre_completo;
        doctorCed = storedMed.cedula || doctorCed;
      }
    } catch(e){}

    const now = new Date();
    setNotaModal({
      open: true,
      isEdit: false,
      evolution_num: slotNum,
      fecha: now.toISOString().split('T')[0],
      hora: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
      turno: 'Matutino',
      vitals_ta: '120/80',
      vitals_fc: '78',
      vitals_fr: '18',
      vitals_sato2: '98',
      vitals_peso: '78.5',
      vitals_talla: '1.72',
      vitals_temp: '36.5',
      subjetivo: '',
      objetivo: '',
      analisis: '',
      plan: '',
      medico: doctorName,
      cedula: doctorCed,
      mip: ''
    });
  };

  // Abrir modal para editar evolución existente
  const handleOpenEditEvol = (evol) => {
    if (!evol) return;
    setNotaModal({
      open: true,
      isEdit: true,
      evolution_num: evol.num || evol.evolution_num || 1,
      fecha: evol.fecha || evol.date || new Date().toISOString().split('T')[0],
      hora: evol.hora || evol.time || '12:00',
      turno: evol.turno || 'Matutino',
      vitals_ta: evol.vitals_ta || '120/80',
      vitals_fc: evol.vitals_fc || '80',
      vitals_fr: evol.vitals_fr || '18',
      vitals_sato2: evol.vitals_sato2 || '98',
      vitals_peso: evol.vitals_peso || '78.5',
      vitals_talla: evol.vitals_talla || '1.72',
      vitals_temp: evol.vitals_temp || '36.5',
      subjetivo: evol.subjetivo || evol.soap?.s || '',
      objetivo: evol.objetivo || evol.soap?.o || '',
      analisis: evol.analisis || evol.soap?.a || '',
      plan: evol.plan || evol.soap?.p || '',
      medico: evol.medico || evol.doctor || 'JOSE JOSE PRUEBA ENRIQUEZ',
      cedula: evol.cedula || 'PRUEBA-99281',
      mip: evol.mip || ''
    });
  };

  // Guardar evolución en backend / SQL Server
  const handleSaveNota = async (e) => {
    e.preventDefault();
    try {
      setSavingNota(true);
      const res = await api.post(`/ehr/paciente/${patientId}/nota-urgencias`, notaModal);
      if (res.data && (res.data.success || !res.data.error)) {
        setNotaModal(prev => ({ ...prev, open: false }));
        await fetchData();
        await fetchFirmas();
        alert(`¡Evolución ${notaModal.evolution_num} guardada con éxito en el expediente!\n(Al modificar el documento, cualquier firma digital previa se revocó conforme a la NOM)`);
      } else {
        alert(res.data?.error || "Error al guardar la nota.");
      }
    } catch (err) {
      console.error("Error saving note:", err);
      alert("Error al conectar con el servidor para guardar la nota.");
    } finally {
      setSavingNota(false);
    }
  };

  // Filtrado de formatos
  const allFormatos = formatos_disponibles.flatMap(cat => cat.formatos.map(f => ({ ...f, area: cat.area })));
  const filteredFormatos = selectedFormatArea === 'Todos' 
    ? allFormatos 
    : allFormatos.filter(f => f.area === selectedFormatArea);

  const tabsList = [
    { id: 'Timeline', label: 'Timeline (Historial)', icon: <FiClock /> },
    { id: 'Formatos Clínicos', label: 'Formatos Clínicos (+100)', icon: <FiFileText /> },
    { id: 'Medicamentos', label: 'Medicamentos', icon: <MdOutlineMedicalServices /> },
    { id: 'Dietas y Cuidados', label: 'Dietas y Cuidados', icon: <MdOutlineRestaurant /> },
    { id: 'Laboratorios', label: 'Laboratorios', icon: <MdOutlineBiotech /> },
    { id: 'Imagenología', label: 'Imagenología', icon: <FiImage /> },
    { id: 'Agenda y Citas', label: 'Agenda y Citas', icon: <FiCalendar /> }
  ];

  return (
    <div className="flex-1 bg-slate-50/50 min-h-screen p-4 md:p-8 flex flex-col gap-6">
      
      {/* TOP BAR / BREADCRUMB */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center font-bold text-lg shadow-sm">
            {patient.name.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-800">{patient.name}</h1>
              <span className="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded border border-emerald-200">
                {patient.cama || 'Cama Virtual'}
              </span>
            </div>
            <p className="text-xs text-slate-500">Expediente: <strong className="text-slate-700">{patient.mrn}</strong> • Ingreso: {patient.fecha_ingreso} {patient.hora_ingreso}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={() => handleOpenNewEvol(evoluciones.evolucion2 ? 3 : (evoluciones.evolucion1 ? 2 : 1))}
            className="flex items-center justify-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all"
          >
            <FiEdit3 /> Nueva Evolución
          </button>
          <a 
            href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
            target="_blank" 
            rel="noreferrer"
            className="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all"
            title="Genera e imprime el documento institucional de 2 páginas con las 3 evoluciones y sello biométrico"
          >
            <FiFileText /> Imprimir Formato General (87/01)
          </a>
        </div>
      </div>

      {/* PATIENT DEMOGRAPHICS & VITALS CARD */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 pb-4 border-b border-slate-100 text-xs">
          <div>
            <span className="text-slate-400 font-medium uppercase block">Edad / Sexo</span>
            <span className="font-bold text-slate-800 text-sm">{patient.age} • {patient.gender}</span>
          </div>
          <div>
            <span className="text-slate-400 font-medium uppercase block">Fecha Nacimiento</span>
            <span className="font-bold text-slate-800 text-sm">{patient.dob}</span>
          </div>
          <div>
            <span className="text-slate-400 font-medium uppercase block">Ubicación / Cama</span>
            <span className="font-bold text-hes-blue-main text-sm">{patient.cama}</span>
          </div>
          <div className="col-span-2 md:col-span-1">
            <span className="text-slate-400 font-medium uppercase block">Alergias</span>
            <span className="font-bold text-red-600 text-sm bg-red-50 px-2 py-0.5 rounded border border-red-100 inline-block">
              {patient.allergies}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-400 font-medium uppercase block">Diagnóstico de Ingreso</span>
            <span className="font-bold text-slate-800 text-sm truncate block" title={patient.diagnostico}>{patient.diagnostico}</span>
          </div>
        </div>

        {/* VITALS ROW */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-4">
          {vitals.map((v, i) => (
            <div key={i} className="flex items-center gap-3 p-2.5 bg-slate-50 rounded-xl border border-slate-100">
              <div className={`p-2 rounded-lg ${getVitalColor(v.label)}`}>
                {getVitalIcon(v.label)}
              </div>
              <div>
                <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide truncate max-w-[90px]" title={v.label}>{v.label}</div>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-extrabold text-slate-800">{v.value}</span>
                  <span className="text-[10px] text-slate-500">{v.unit}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* MAIN CONTENT AREA: TABS & SIDEBAR */}
      <div className="flex flex-col xl:flex-row gap-6">
        
        {/* TABS CONTAINER */}
        <div className="flex-1">
          
          {/* TABS NAVIGATION */}
          <div className="flex gap-2 overflow-x-auto border-b border-slate-200 mb-5 pb-1">
            {tabsList.map(tab => (
              <button 
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  if (tab.id !== 'Formatos Clínicos') {
                    setSelectedFormat(null);
                  }
                }}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold whitespace-nowrap transition-all ${
                  activeTab === tab.id 
                    ? 'bg-hes-blue-main text-white shadow-sm' 
                    : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* TAB 1: TIMELINE (HISTORIAL CRONOLÓGICO) */}
          {activeTab === 'Timeline' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Línea de Tiempo del Paciente</h2>
                  <p className="text-xs text-slate-500">Historial completo y cronológico de eventos clínicos, notas y atenciones.</p>
                </div>
                <span className="text-xs bg-blue-50 text-hes-blue-main font-semibold px-3 py-1 rounded-full border border-blue-100">
                  {timelineEvents.length} Eventos Registrados
                </span>
              </div>

              <div className="space-y-6 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-200">
                {timelineEvents.length === 0 ? (
                  <div className="text-center py-8 text-slate-400 text-xs">No hay eventos clínicos registrados aún.</div>
                ) : (
                  timelineEvents.map((evt, idx) => (
                    <div key={idx} className="relative flex items-start gap-4 group">
                      <div className="w-8 h-8 rounded-full bg-hes-blue-main text-white flex items-center justify-center shadow shrink-0 z-10 text-xs font-bold ring-4 ring-white">
                        {idx + 1}
                      </div>
                      <div className="flex-1 bg-slate-50 hover:bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-hes-blue-main/40 transition-all">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                          <span className="font-bold text-slate-800 text-sm">{evt.type}</span>
                          <span className="text-xs font-semibold text-hes-blue-main bg-blue-50 px-2 py-0.5 rounded self-start sm:self-auto">
                            {evt.date} • {evt.time}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed mt-1">{evt.desc}</p>
                        
                        {evt.type && evt.type.startsWith('Nota de Evolución') && (
                          <div className="flex items-center gap-3 mt-3 pt-2 border-t border-slate-200/60">
                            <button 
                              onClick={() => {
                                const fmt = allFormatos.find(f => f.codigo === 'HE-DIRMED-SINPRO-PLT-87/01') || allFormatos[0];
                                setSelectedFormat(fmt);
                                setActiveTab('Formatos Clínicos');
                              }}
                              className="text-xs font-semibold text-hes-blue-main hover:underline flex items-center gap-1"
                            >
                              Ver Formato Oficial <FiChevronRight />
                            </button>
                            <a 
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
                              target="_blank" 
                              rel="noreferrer"
                              className="text-xs font-semibold text-emerald-600 hover:underline flex items-center gap-1"
                            >
                              <FiDownload /> Imprimir PDF Oficial
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 2: FORMATOS CLÍNICOS (+100 FORMATOS CATEGORIZADOS & GESTOR DE NOTAS) */}
          {activeTab === 'Formatos Clínicos' && (
            <div>
              {/* CASO A: CUANDO SE ABRIÓ UN FORMATO ESPECÍFICO (EJ. NOTA DE EVOLUCIÓN DE URGENCIAS) */}
              {selectedFormat ? (
                <div className="space-y-6">
                  
                  {/* BOTÓN VOLVER Y CABECERA DEL FORMATO SELECCIONADO */}
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setSelectedFormat(null)}
                        className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3.5 py-2 rounded-xl text-xs font-bold transition-colors"
                      >
                        <FiArrowLeft /> Volver al Catálogo
                      </button>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs bg-emerald-100 text-emerald-800 font-extrabold px-2.5 py-0.5 rounded-full uppercase">Activo</span>
                          <span className="text-xs bg-blue-50 text-hes-blue-main font-semibold px-2 py-0.5 rounded border border-blue-100">{selectedFormat.codigo}</span>
                        </div>
                        <h2 className="text-lg font-bold text-slate-800 mt-0.5">{selectedFormat.nombre}</h2>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap self-end sm:self-auto">
                      <button
                        onClick={() => handleOpenNewEvol(evoluciones.evolucion2 ? 3 : (evoluciones.evolucion1 ? 2 : 1))}
                        className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                      >
                        <FiPlus /> Nueva Evolución
                      </button>
                      <a 
                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
                        target="_blank" 
                        rel="noreferrer"
                        className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                      >
                        <FiDownload /> Imprimir Formato General (3 en 1)
                      </a>
                    </div>
                  </div>

                  {/* VISTA DE LAS 3 EVOLUCIONES DE URGENCIAS */}
                  {selectedFormat.codigo === 'HE-DIRMED-SINPRO-PLT-87/01' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
                      <div className="pb-3 border-b border-slate-100">
                        <h3 className="font-bold text-slate-800 text-base">Evoluciones Consecutivas del Paciente (Hasta 3 notas en 1)</h3>
                        <p className="text-xs text-slate-500">Puedes capturar nuevas notas en los slots vacíos, editarlas y firmarlas con tu huella digital.</p>
                      </div>

                      <div className="grid grid-cols-1 gap-4">
                        {[1, 2, 3].map((slot) => {
                          const evolKey = `evolucion${slot}`;
                          const evolData = evoluciones[evolKey];
                          const exists = Boolean(evolData && (evolData.subjetivo || evolData.fecha));
                          
                          // Buscar si esta evolución ya tiene firma biométrica registrada en PostgreSQL
                          const firmaSlot = firmas.find(f => f.evolution_slot === slot);

                          return (
                            <div key={slot} className={`p-5 rounded-2xl border transition-all ${
                              exists ? 'border-slate-200 bg-slate-50/60' : 'border-dashed border-slate-300 bg-white/70'
                            }`}>
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 mb-3 border-b border-slate-200">
                                <div className="flex items-center gap-3">
                                  <span className={`w-8 h-8 rounded-lg font-bold flex items-center justify-center text-sm shadow-xs ${
                                    exists ? 'bg-hes-blue-main text-white' : 'bg-slate-200 text-slate-500'
                                  }`}>
                                    {slot}
                                  </span>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <div className="font-bold text-slate-800 text-base">
                                        Evolución y Observaciones {slot} {slot > 1 && <span className="text-xs text-hes-blue-main font-semibold">(Continuación)</span>}
                                      </div>
                                      {firmaSlot && (
                                        <span className="text-[11px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-200" title="Firmado conforme a la NOM-004-SSA3-2012 / NOM-024-SSA3-2012">
                                          <MdVerifiedUser className="text-sm text-emerald-600" /> Firmado Biométricamente (NOM)
                                        </span>
                                      )}
                                    </div>

                                    {exists ? (
                                      <div className="text-xs text-slate-500">
                                        Fecha: <span className="font-medium text-slate-700">{evolData.fecha} {evolData.hora}</span> • Turno: <span className="font-medium text-slate-700">{evolData.turno}</span>
                                      </div>
                                    ) : (
                                      <div className="text-xs text-slate-400 font-medium">Espacio disponible para captura médica subsecuente</div>
                                    )}
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {exists ? (
                                    <>
                                      {/* BOTÓN FIRMAR CON HUELLA BIOMÉTRICA */}
                                      <button
                                        onClick={() => handleOpenBiometricSign(slot, `Evolución ${slot}`, evolData.subjetivo || '')}
                                        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                          firmaSlot 
                                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100' 
                                            : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                        }`}
                                        title="Firmar electrónicamente con lector DigitalPersona"
                                      >
                                        <MdFingerprint className="text-base" /> {firmaSlot ? 'Refirmar con Huella' : 'Firmar con Huella (NOM)'}
                                      </button>

                                      <button
                                        onClick={() => handleOpenEditEvol(evolData)}
                                        className="flex items-center gap-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                      >
                                        <FiEdit3 /> Editar
                                      </button>
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias?evolucion=${slot}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white hover:bg-blue-50 text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                      >
                                        <FiFileText /> Imprimir Nota {slot}
                                      </a>
                                    </>
                                  ) : (
                                    <button
                                      onClick={() => handleOpenNewEvol(slot)}
                                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Evolución {slot}
                                    </button>
                                  )}
                                </div>
                              </div>

                              {/* CONTENIDO SOAP SI EXISTE */}
                              {exists ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                  {evolData.subjetivo && (
                                    <div className="p-3 bg-white rounded-xl border border-slate-100">
                                      <span className="font-bold text-hes-blue-main block uppercase mb-0.5">(S) Subjetivo</span>
                                      <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.subjetivo}</p>
                                    </div>
                                  )}
                                  {evolData.objetivo && (
                                    <div className="p-3 bg-white rounded-xl border border-slate-100">
                                      <span className="font-bold text-hes-blue-main block uppercase mb-0.5">(O) Objetivo</span>
                                      <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.objetivo}</p>
                                    </div>
                                  )}
                                  {evolData.analisis && (
                                    <div className="p-3 bg-white rounded-xl border border-slate-100">
                                      <span className="font-bold text-hes-blue-main block uppercase mb-0.5">(A) Análisis</span>
                                      <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.analisis}</p>
                                    </div>
                                  )}
                                  {evolData.plan && (
                                    <div className="p-3 bg-white rounded-xl border border-slate-100">
                                      <span className="font-bold text-hes-blue-main block uppercase mb-0.5">(P) Plan Terapéutico</span>
                                      <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.plan}</p>
                                    </div>
                                  )}
                                  
                                  {/* FOOTER DE FIRMA Y MÉDICO */}
                                  <div className="col-span-1 md:col-span-2 pt-2.5 border-t border-slate-200/60 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-[11px]">
                                    <div>
                                      Médico Responsable: <strong className="text-slate-800">{evolData.medico}</strong> (Céd. {evolData.cedula})
                                    </div>
                                    {firmaSlot && (
                                      <button
                                        type="button"
                                        onClick={() => handleOpenAuditModal(firmaSlot)}
                                        className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md border border-emerald-200 flex items-center gap-1.5 transition-colors cursor-pointer text-left"
                                        title="Haga clic para consultar el Sello HMAC, Tríada de Seguridad y Auditoría NOM"
                                      >
                                        <MdVerifiedUser className="text-emerald-600 shrink-0 text-xs" />
                                        <span>Sello: {firmaSlot.sello_digital ? `${firmaSlot.sello_digital.slice(0, 24)}...` : 'Verificado'} • {firmaSlot.fecha_hora_firma}</span>
                                        <span className="text-[9px] font-sans font-bold text-hes-blue-main bg-blue-50 px-1.5 py-0.5 rounded ml-1">Ver Auditoría 🔍</span>
                                      </button>
                                    )}
                                  </div>
                                </div>
                              ) : (
                                <div className="py-2 text-center text-xs text-slate-400">
                                  Haz clic en <strong>"+ Capturar Evolución {slot}"</strong> para redactar la nota SOAP de este turno.
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center space-y-3">
                      <div className="w-12 h-12 rounded-full bg-blue-50 text-hes-blue-main flex items-center justify-center mx-auto text-xl font-bold">
                        <FiFolder />
                      </div>
                      <h3 className="font-bold text-slate-800 text-lg">{selectedFormat.nombre}</h3>
                      <p className="text-xs text-slate-500 max-w-md mx-auto">{selectedFormat.subtitulo}</p>
                      <span className="inline-block text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full">
                        Formato en proceso de parametrización institucional
                      </span>
                    </div>
                  )}

                </div>
              ) : (
                /* CASO B: VISTA GENERAL DE CATÁLOGO MAESTRO DE FORMATOS */
                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-slate-100">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold text-slate-800">Catálogo Maestro de Formatos Clínicos</h2>
                        <span className="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded border border-emerald-200">+100 Formatos HES</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">Expediente clínico conforme a la norma NOM-004-SSA3-2012 y Calidad Institucional.</p>
                    </div>

                    {/* FILTRO POR AREA */}
                    <div className="flex gap-1.5 overflow-x-auto w-full md:w-auto pb-1">
                      {['Todos', 'Urgencias', 'Hospitalización', 'Cirugía y Quirófano', 'Consulta Externa e Interconsultas', 'Servicios Auxiliares y Diagnóstico'].map(area => (
                        <button
                          key={area}
                          onClick={() => setSelectedFormatArea(area)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-colors ${
                            selectedFormatArea === area 
                              ? 'bg-slate-800 text-white' 
                              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          {area.split(' ')[0]}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* GRID DE TODOS LOS FORMATOS */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredFormatos.map((fmt, i) => (
                      <div 
                        key={i} 
                        className={`p-5 rounded-2xl border transition-all flex flex-col justify-between cursor-pointer ${
                          fmt.activo 
                            ? 'border-emerald-200 bg-emerald-50/15 hover:border-emerald-400 hover:shadow-sm' 
                            : 'border-slate-200 bg-white hover:border-slate-300 opacity-90'
                        }`}
                        onClick={() => setSelectedFormat(fmt)}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-blue-50 text-hes-blue-main border border-blue-100">
                              {fmt.codigo}
                            </span>
                            {fmt.activo ? (
                              <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-full flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse"></span> Activo / Imprimible
                              </span>
                            ) : (
                              <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                                En Integración
                              </span>
                            )}
                          </div>
                          
                          <h3 className="font-bold text-slate-800 text-base mb-1">{fmt.nombre}</h3>
                          <p className="text-xs text-slate-500 leading-relaxed mb-3">{fmt.subtitulo}</p>
                          
                          <div className="flex items-center gap-3 text-[11px] text-slate-400 font-medium">
                            <span>Área: <strong className="text-slate-600">{fmt.area}</strong></span>
                            <span>•</span>
                            <span>{fmt.paginas} Pág(s)</span>
                            <span>•</span>
                            <span>{fmt.norma}</span>
                          </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2" onClick={e => e.stopPropagation()}>
                          {fmt.activo ? (
                            <div className="flex items-center gap-2 w-full">
                              <button
                                onClick={() => setSelectedFormat(fmt)}
                                className="flex-1 flex items-center justify-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-3 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                              >
                                <FiEdit3 /> Abrir Formato / Capturar
                              </button>
                              <a
                                href={`${api.defaults.baseURL}${fmt.url_pdf}`}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center justify-center gap-1 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                title="Imprimir PDF oficial"
                              >
                                <FiDownload /> PDF
                              </a>
                            </div>
                          ) : (
                            <button 
                              onClick={() => setSelectedFormat(fmt)}
                              className="w-full text-center py-1.5 text-xs font-semibold text-slate-500 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors"
                            >
                              Ver Información del Formato
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: MEDICAMENTOS */}
          {activeTab === 'Medicamentos' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Medicamentos y Prescripciones Activas</h2>
                  <p className="text-xs text-slate-500">Plan farmacológico indicado por el médico tratante.</p>
                </div>
                <button className="flex items-center gap-1 bg-hes-blue-main text-white px-3 py-1.5 rounded-xl text-xs font-bold">
                  <FiPlus /> Añadir Fármaco
                </button>
              </div>

              <div className="space-y-3">
                {medications.map((med, i) => (
                  <div key={i} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white transition-all flex justify-between items-center">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800 text-base">{med.name}</span>
                        <span className="text-xs font-semibold bg-blue-50 text-hes-blue-main px-2 py-0.5 rounded">{med.dose}</span>
                        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{med.route}</span>
                      </div>
                      <div className="text-xs text-slate-600 mt-1">Frecuencia: <strong className="text-slate-800">{med.freq}</strong></div>
                      <p className="text-xs text-slate-500 mt-0.5">{med.instruction}</p>
                    </div>
                    <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                      {med.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: DIETAS Y CUIDADOS */}
          {activeTab === 'Dietas y Cuidados' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="pb-3 border-b border-slate-100">
                <h2 className="text-lg font-bold text-slate-800">Régimen Dietético y Cuidados de Enfermería</h2>
                <p className="text-xs text-slate-500">Indicaciones nutricionales y cuidados específicos de piso y urgencias.</p>
              </div>

              {/* DIETA CARD */}
              <div className="p-5 rounded-2xl border border-blue-200 bg-blue-50/30">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-hes-blue-main flex items-center gap-1.5">
                    <MdOutlineRestaurant className="text-lg" /> Dieta Prescrita
                  </span>
                  <span className="text-xs bg-red-50 text-red-700 font-bold px-2.5 py-1 rounded-full border border-red-200">
                    {dietas.tipo}
                  </span>
                </div>
                <div className="space-y-2 text-xs">
                  <div><strong>Fase Clínica:</strong> {dietas.fase}</div>
                  <div><strong>Indicación Nutricional:</strong> {dietas.indicaciones}</div>
                  <div><strong>Inicio de Ayuno:</strong> {dietas.inicio}</div>
                  <div><strong>Nutriólogo Responsable:</strong> {dietas.nutriologo}</div>
                  <div><strong>Tolerancia Vía Oral:</strong> {dietas.tolerancia_via_oral}</div>
                </div>
              </div>

              {/* CUIDADOS DE ENFERMERIA */}
              <div className="space-y-3">
                <h3 className="font-bold text-slate-800 text-sm">Plan de Cuidados de Enfermería</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {cuidados_enfermeria.map((c, i) => (
                    <div key={i} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 flex items-start gap-3">
                      <FiCheckCircle className="text-emerald-600 text-base shrink-0 mt-0.5" />
                      <div>
                        <div className="font-bold text-slate-800 text-xs">{c.cuidado}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">Frecuencia: {c.frecuencia}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: LABORATORIOS */}
          {activeTab === 'Laboratorios' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Estudios de Laboratorio Clínico</h2>
                  <p className="text-xs text-slate-500">Resultados, parámetros y pruebas de diagnóstico central.</p>
                </div>
                <button className="flex items-center gap-1 bg-hes-blue-main text-white px-3 py-1.5 rounded-xl text-xs font-bold">
                  <FiPlus /> Solicitar Estudio
                </button>
              </div>

              <div className="space-y-4">
                {laboratorios.map((lab) => (
                  <div key={lab.id} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/40 hover:bg-white transition-all space-y-2">
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <span className="text-xs font-bold text-hes-blue-main block">{lab.id}</span>
                        <h3 className="font-bold text-slate-800 text-base">{lab.estudio}</h3>
                        <span className="text-xs text-slate-400">Solicitado: {lab.fecha_solicitud} • Por: {lab.solicitado_por}</span>
                      </div>
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                        lab.estatus === 'Completado' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {lab.estatus}
                      </span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-100 text-xs space-y-1">
                      <div className="font-semibold text-slate-700">Resultado: {lab.resultado_resumen}</div>
                      {lab.valores_criticos && (
                        <div className="text-slate-500 font-medium">Interpretación: {lab.valores_criticos}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 6: IMAGENOLOGÍA */}
          {activeTab === 'Imagenología' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Estudios de Imagenología y Gabinete</h2>
                  <p className="text-xs text-slate-500">Ultrasonidos, tomografías y radiografías con reporte radiológico.</p>
                </div>
                <button className="flex items-center gap-1 bg-hes-blue-main text-white px-3 py-1.5 rounded-xl text-xs font-bold">
                  <FiPlus /> Solicitar Imagen
                </button>
              </div>

              <div className="space-y-4">
                {imagenologia.map((img) => (
                  <div key={img.id} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/40 hover:bg-white transition-all space-y-3">
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <span className="text-xs font-bold text-hes-blue-main block">{img.id}</span>
                        <h3 className="font-bold text-slate-800 text-base">{img.estudio}</h3>
                        <span className="text-xs text-slate-400">Solicitado: {img.fecha_solicitud} • Por: {img.solicitado_por}</span>
                      </div>
                      <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {img.estatus}
                      </span>
                    </div>
                    <div className="p-3.5 bg-white rounded-xl border border-slate-100 text-xs space-y-2">
                      <div>
                        <strong className="text-slate-700 block mb-0.5">Hallazgos Radiológicos:</strong>
                        <p className="text-slate-600 leading-relaxed">{img.hallazgos}</p>
                      </div>
                      <div className="pt-2 border-t border-slate-100 text-hes-blue-main font-semibold">
                        Conclusión: {img.conclusion}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 7: AGENDA Y CITAS */}
          {activeTab === 'Agenda y Citas' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Citas Programadas y Seguimiento</h2>
                  <p className="text-xs text-slate-500">Próximas valoraciones médicas y control ambulatorio.</p>
                </div>
                <a 
                  href="/agenda"
                  className="flex items-center gap-1 bg-hes-blue-main text-white px-3.5 py-2 rounded-xl text-xs font-bold hover:bg-hes-blue-dark transition-all"
                >
                  <FiPlus /> Abrir Agenda Médica
                </a>
              </div>

              <div className="space-y-3">
                {proximas_citas.map((c) => (
                  <div key={c.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-blue-50 text-hes-blue-main rounded-xl font-bold text-center min-w-[70px]">
                        <div className="text-xs">{c.fecha}</div>
                        <div className="text-sm font-extrabold">{c.hora}</div>
                      </div>
                      <div>
                        <h4 className="font-bold text-slate-800 text-sm">{c.motivo}</h4>
                        <div className="text-xs text-slate-500">Médico: <strong className="text-slate-700">{c.medico}</strong> ({c.especialidad})</div>
                        <div className="text-xs text-slate-400 mt-0.5">Lugar: {c.lugar}</div>
                      </div>
                    </div>
                    <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                      {c.estatus}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* RIGHT SIDEBAR: REAL-TIME PATIENT CHARGES & ORDERS SUMMARY */}
        <div className="w-full xl:w-80 flex flex-col gap-6">
          
          {/* CHARGES & ACTIVE REQUESTS CARD */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 space-y-4">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2 pb-2 border-b border-slate-100">
              <FiLayers className="text-hes-blue-main text-base" /> Resumen de Solicitudes y Cargos
            </h3>

            {/* DIETA ACTIVA */}
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Dieta Actual</div>
              <div className="font-bold text-slate-800 text-sm mt-0.5">{cargos_solicitudes.dieta_activa || 'Ayuno'}</div>
              <div className="text-[10px] text-red-600 font-medium">NVO / Solución IV</div>
            </div>

            {/* COUNTERS */}
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-xl bg-blue-50/50 border border-blue-100 text-center">
                <div className="text-lg font-black text-hes-blue-main">{cargos_solicitudes.laboratorios_count || 4}</div>
                <div className="text-[10px] font-bold text-slate-600 uppercase">Labs Solicitados</div>
              </div>
              <div className="p-3 rounded-xl bg-teal-50/50 border border-teal-100 text-center">
                <div className="text-lg font-black text-teal-700">{cargos_solicitudes.imagenologia_count || 2}</div>
                <div className="text-[10px] font-bold text-slate-600 uppercase">Estudios Imagen</div>
              </div>
            </div>

            {/* PENDING ITEMS */}
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase mb-2">Seguimiento en Curso</div>
              <div className="space-y-1.5 text-xs">
                {cargos_solicitudes.solicitudes_pendientes?.map((s, i) => (
                  <div key={i} className="flex justify-between items-center p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="font-medium text-slate-700">{s.titulo}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      s.estado === 'Completado' || s.estado === 'Reportado' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {s.estado}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* PROXIMA CITA */}
            {cargos_solicitudes.proxima_cita && (
              <div className="p-3 rounded-xl bg-purple-50/50 border border-purple-100 text-xs">
                <div className="text-[10px] font-bold text-purple-700 uppercase">Próxima Valoración</div>
                <div className="font-bold text-slate-800 mt-0.5">{cargos_solicitudes.proxima_cita.fecha} {cargos_solicitudes.proxima_cita.hora}</div>
                <div className="text-slate-500 text-[11px] mt-0.5">{cargos_solicitudes.proxima_cita.medico}</div>
              </div>
            )}
          </div>

          {/* QUICK ACTIONS CARD */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 space-y-2">
            <h3 className="font-bold text-slate-800 text-sm mb-3">Acciones Rápidas</h3>
            
            <button
              onClick={() => handleOpenNewEvol(evoluciones.evolucion2 ? 3 : (evoluciones.evolucion1 ? 2 : 1))}
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-hes-blue-main/30 bg-blue-50/40 hover:bg-hes-blue-main hover:text-white transition-all text-left group"
            >
              <div className="p-2 bg-hes-blue-main text-white rounded-lg group-hover:bg-white group-hover:text-hes-blue-main transition-colors"><FiEdit3 className="text-lg" /></div>
              <div>
                <div className="font-bold text-hes-blue-main text-xs group-hover:text-white">Nueva Evolución</div>
                <div className="text-[10px] text-slate-500 group-hover:text-blue-100">Capturar SOAP turno actual</div>
              </div>
            </button>

            <a 
              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
              target="_blank" 
              rel="noreferrer"
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-emerald-500/30 bg-emerald-50/50 hover:bg-emerald-600 hover:text-white transition-all text-left group"
            >
              <div className="p-2 bg-emerald-600 text-white rounded-lg group-hover:bg-white group-hover:text-emerald-600 transition-colors"><FiFileText className="text-lg" /></div>
              <div>
                <div className="font-bold text-emerald-800 text-xs group-hover:text-white">Imprimir Formato General</div>
                <div className="text-[10px] text-emerald-600 group-hover:text-emerald-100">87/01 Oficial (2 páginas)</div>
              </div>
            </a>

            <button 
              onClick={() => {
                setSelectedFormat(null);
                setActiveTab('Formatos Clínicos');
              }}
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-hes-blue-main hover:bg-blue-50/30 transition-all text-left group"
            >
              <div className="p-2 bg-slate-50 text-slate-600 rounded-lg group-hover:bg-hes-blue-main group-hover:text-white transition-colors"><FiFolder className="text-lg" /></div>
              <div>
                <div className="font-bold text-slate-800 text-xs group-hover:text-hes-blue-main">Catálogo de Formatos</div>
                <div className="text-[10px] text-slate-500">+100 Formatos Oficiales</div>
              </div>
            </button>

            <a 
              href="/agenda"
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-purple-500 hover:bg-purple-50/30 transition-all text-left group"
            >
              <div className="p-2 bg-slate-50 text-slate-600 rounded-lg group-hover:bg-purple-600 group-hover:text-white transition-colors"><FiCalendar className="text-lg" /></div>
              <div>
                <div className="font-bold text-slate-800 text-xs group-hover:text-purple-600">Agenda Médica</div>
                <div className="text-[10px] text-slate-500">Programar visitas / citas</div>
              </div>
            </a>
          </div>

        </div>

      </div>

      {/* MODAL DE FIRMA BIOMÉTRICA (NOM-004-SSA3-2012 / NOM-024-SSA3-2012) */}
      {signingModal.open && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full p-6 text-center space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-hes-blue-main uppercase tracking-wide flex items-center gap-1.5">
                <FiShield /> Firma Electrónica Avanzada NOM
              </span>
              <button 
                onClick={() => {
                  setSigningModal(prev => ({ ...prev, open: false }));
                  dpStopCapture();
                }}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                <FiX />
              </button>
            </div>

            <div>
              <h3 className="font-bold text-slate-800 text-base">{signingModal.title}</h3>
              <p className="text-xs text-slate-500 mt-0.5">Coloque su dedo en el lector DigitalPersona para estampar la firma biométrica de la nota.</p>
            </div>

            {/* SENSOR ANIMADO */}
            <div className="py-4 flex flex-col items-center justify-center">
              <div className={`w-32 h-32 rounded-full border-4 flex items-center justify-center relative transition-all ${
                signingModal.successMsg 
                  ? 'border-emerald-500 bg-emerald-50 text-emerald-600' 
                  : dpAcquiring 
                  ? 'border-hes-blue-main bg-blue-50/60 text-hes-blue-main animate-pulse' 
                  : 'border-slate-200 bg-slate-50 text-slate-400'
              }`}>
                {dpAcquiring && (
                  <div className="absolute inset-0 rounded-full border-2 border-hes-blue-main animate-ping opacity-25"></div>
                )}
                {signingModal.successMsg ? (
                  <MdVerifiedUser className="text-6xl text-emerald-600" />
                ) : (
                  <MdFingerprint className="text-6xl" />
                )}
              </div>

              <div className="text-xs font-semibold mt-3">
                {signingModal.successMsg ? (
                  <span className="text-emerald-700 font-bold">{signingModal.successMsg}</span>
                ) : signingModal.submitting ? (
                  <span className="text-hes-blue-main font-bold">Verificando huella dactilar y generando sello digital...</span>
                ) : dpAcquiring ? (
                  <span className="text-hes-blue-main font-bold">Esperando lectura en el sensor...</span>
                ) : (
                  <span className="text-slate-500">{dpStatus}</span>
                )}
              </div>

              {signingModal.errorMsg && (
                <div className="mt-3 p-2.5 bg-red-50 text-red-700 rounded-xl text-xs font-semibold border border-red-200 max-w-sm">
                  {signingModal.errorMsg}
                </div>
              )}
            </div>

            <div className="text-[11px] text-slate-400 bg-slate-50 p-2.5 rounded-xl border border-slate-100 text-left space-y-1">
              <div><strong>Normativa Aplicable:</strong> NOM-004-SSA3-2012 y NOM-024-SSA3-2012</div>
              <div><strong>Algoritmo Criptográfico:</strong> SHA-256 + Sello HMAC SHA-512</div>
              <div><strong>Almacenamiento:</strong> Base de datos central PostgreSQL Hospital Escandón</div>
            </div>

            <div className="pt-2 flex justify-center gap-3">
              <button 
                onClick={() => {
                  setSigningModal(prev => ({ ...prev, open: false }));
                  dpStopCapture();
                }}
                className="px-5 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                Cerrar
              </button>
              {!signingModal.successMsg && (
                <button 
                  onClick={() => {
                    dpResetFmd();
                    dpStartCapture();
                  }}
                  className="px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-xs"
                >
                  Reintentar Captura
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL DE CAPTURA / EDICIÓN DE NOTA DE EVOLUCIÓN (SOAP) */}
      {notaModal.open && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            
            {/* MODAL HEADER */}
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-blue-50 text-hes-blue-main font-bold px-2.5 py-0.5 rounded border border-blue-100">HE-DIRMED-SINPRO-PLT-87/01</span>
                  <h3 className="text-lg font-bold text-slate-800">
                    {notaModal.isEdit ? `Editar Evolución ${notaModal.evolution_num}` : `Capturar Nueva Evolución ${notaModal.evolution_num}`}
                  </h3>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">Paciente: <strong>{patient.name}</strong> • Expediente: <strong>{patient.mrn}</strong></p>
              </div>
              <button 
                onClick={() => setNotaModal(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold p-1"
              >
                <FiX />
              </button>
            </div>

            <form onSubmit={handleSaveNota} className="space-y-4">
              
              {/* SLOT, FECHA, HORA, TURNO */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Evolución Slot *</label>
                  <select 
                    value={notaModal.evolution_num}
                    onChange={(e) => setNotaModal({ ...notaModal, evolution_num: parseInt(e.target.value) })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-hes-blue-main"
                  >
                    <option value={1}>Evolución 1 (Inicial)</option>
                    <option value={2}>Evolución 2 (Continuación)</option>
                    <option value={3}>Evolución 3 (Continuación)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Fecha *</label>
                  <input 
                    type="date" 
                    value={notaModal.fecha}
                    onChange={(e) => setNotaModal({ ...notaModal, fecha: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Hora *</label>
                  <input 
                    type="time" 
                    value={notaModal.hora}
                    onChange={(e) => setNotaModal({ ...notaModal, hora: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Turno *</label>
                  <select 
                    value={notaModal.turno}
                    onChange={(e) => setNotaModal({ ...notaModal, turno: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-semibold"
                  >
                    <option value="Matutino">Matutino</option>
                    <option value="Vespertino">Vespertino</option>
                    <option value="Nocturno">Nocturno</option>
                  </select>
                </div>
              </div>

              {/* SIGNOS VITALES */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500 block">Signos Vitales del Turno</span>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-xs">
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">TA (mmHg)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_ta} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_ta: e.target.value })}
                      placeholder="120/80" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">FC (lpm)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_fc} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_fc: e.target.value })}
                      placeholder="80" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">FR (rpm)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_fr} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_fr: e.target.value })}
                      placeholder="18" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">SatO2 (%)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_sato2} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_sato2: e.target.value })}
                      placeholder="98" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">Temp (°C)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_temp} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_temp: e.target.value })}
                      placeholder="36.5" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">Peso (kg)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_peso} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_peso: e.target.value })}
                      placeholder="78.5" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIONES SOAP */}
              <div className="space-y-3 text-xs">
                
                {/* SUBJETIVO */}
                <div>
                  <label className="block font-bold text-hes-blue-main uppercase mb-1">
                    (S) Subjetivo * (Interrogatorio, síntomas y estado referido por el paciente)
                  </label>
                  <textarea 
                    value={notaModal.subjetivo}
                    onChange={(e) => setNotaModal({ ...notaModal, subjetivo: e.target.value })}
                    placeholder="Ej. Paciente refiere dolor abdominal de 12 horas de evolución..."
                    className="w-full border border-slate-200 rounded-xl p-3 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                    rows={3}
                    required
                  />
                </div>

                {/* OBJETIVO */}
                <div>
                  <label className="block font-bold text-hes-blue-main uppercase mb-1">
                    (O) Objetivo (Exploración física, signos, hallazgos clínicos)
                  </label>
                  <textarea 
                    value={notaModal.objetivo}
                    onChange={(e) => setNotaModal({ ...notaModal, objetivo: e.target.value })}
                    placeholder="Ej. Abdomen blando, doloroso a la palpación en FID, McBurney positivo..."
                    className="w-full border border-slate-200 rounded-xl p-3 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                    rows={3}
                  />
                </div>

                {/* ANÁLISIS */}
                <div>
                  <label className="block font-bold text-hes-blue-main uppercase mb-1">
                    (A) Análisis / Valoración (Juicio diagnóstico y estado clínico)
                  </label>
                  <textarea 
                    value={notaModal.analisis}
                    onChange={(e) => setNotaModal({ ...notaModal, analisis: e.target.value })}
                    placeholder="Ej. Cuadro clínico compatible con abdomen agudo secundario a probable apendicitis..."
                    className="w-full border border-slate-200 rounded-xl p-3 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                    rows={2}
                  />
                </div>

                {/* PLAN */}
                <div>
                  <label className="block font-bold text-hes-blue-main uppercase mb-1">
                    (P) Plan Terapéutico (Laboratorios solicitados y tratamientos a establecer)
                  </label>
                  <textarea 
                    value={notaModal.plan}
                    onChange={(e) => setNotaModal({ ...notaModal, plan: e.target.value })}
                    placeholder="Ej. 1. Ayuno.\n2. Solución Hartmann 1000cc para 8 hrs.\n3. Solicitar BH, QS, EGO y USG abdominal..."
                    className="w-full border border-slate-200 rounded-xl p-3 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                    rows={3}
                  />
                </div>

              </div>

              {/* FIRMA / MÉDICO ASIGNADO */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                <div className="sm:col-span-2">
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Médico Responsable *</label>
                  <input 
                    type="text" 
                    value={notaModal.medico}
                    onChange={(e) => setNotaModal({ ...notaModal, medico: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Cédula Profesional *</label>
                  <input 
                    type="text" 
                    value={notaModal.cedula}
                    onChange={(e) => setNotaModal({ ...notaModal, cedula: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800"
                    required
                  />
                </div>
              </div>

              {/* MODAL FOOTER */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button 
                  type="button"
                  onClick={() => setNotaModal(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  disabled={savingNota}
                  className="px-6 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition-all flex items-center gap-1.5"
                >
                  <FiSave /> {savingNota ? 'Guardando en SQL Server...' : (notaModal.isEdit ? 'Actualizar Evolución' : 'Guardar Evolución')}
                </button>
              </div>

            </form>

          </div>
        </div>
      )}

      {/* MODAL DE AUDITORÍA Y VERIFICACIÓN DE INTEGRIDAD FORENSE NOM */}
      {auditModal.open && auditModal.firma && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full p-6 space-y-5 text-left my-8 max-h-[92vh] overflow-y-auto">
            
            {/* HEADER */}
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <span className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 font-bold text-xl border border-emerald-200">
                  <MdVerifiedUser />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-800">Verificación de Integridad y Sello Digital</h3>
                  <p className="text-xs text-slate-500">Expediente Clínico Electrónico — Hospital Escandón</p>
                </div>
              </div>
              <button 
                onClick={() => setAuditModal({ open: false, firma: null, loading: false, verification: null, copied: null })}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold p-1"
              >
                <FiX />
              </button>
            </div>

            {/* ESTADO EN VIVO DE VERIFICACIÓN CRIPTOGRÁFICA */}
            {auditModal.loading ? (
              <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 flex items-center gap-3 animate-pulse">
                <div className="w-5 h-5 border-2 border-hes-blue-main border-t-transparent rounded-full animate-spin"></div>
                <div className="text-xs font-semibold text-hes-blue-main">
                  Recalculando hashes matemáticos y verificando integridad criptográfica en tiempo real...
                </div>
              </div>
            ) : auditModal.verification?.integro ? (
              <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <FiCheckCircle className="text-emerald-600 text-2xl shrink-0" />
                  <div>
                    <span className="font-extrabold text-emerald-900 text-sm block">Firma íntegra y verificable</span>
                    <span className="text-xs text-emerald-700">El recálculo criptográfico en vivo confirma que el documento no ha sido alterado ni modificado.</span>
                  </div>
                </div>
                <span className="text-[11px] font-extrabold bg-emerald-200/90 text-emerald-950 px-3 py-1 rounded-full border border-emerald-300 self-end sm:self-auto">
                  ✓ Verificación Exitosa
                </span>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-red-50 border border-red-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <FiAlertCircle className="text-red-600 text-2xl shrink-0" />
                  <div>
                    <span className="font-extrabold text-red-900 text-sm block">Integridad invalidada</span>
                    <span className="text-xs text-red-700">Discrepancia detectada: el contenido actual del documento difiere del estado al momento de firmar.</span>
                  </div>
                </div>
                <span className="text-[11px] font-extrabold bg-red-200 text-red-900 px-3 py-1 rounded-full border border-red-300 self-end sm:self-auto">
                  ⚠ Alerta de Seguridad
                </span>
              </div>
            )}

            {/* TRÍADA EXPLÍCITA DE SEGURIDAD (3 TARJETAS) */}
            <div className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                Tríada de Seguridad Criptográfica
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                
                {/* 1. IDENTIDAD */}
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex items-center gap-1.5 text-hes-blue-main font-bold text-xs uppercase">
                    <FiUser /> 1. Identidad del Firmante
                  </div>
                  <div className="font-semibold text-slate-800">{auditModal.firma.nombre_medico}</div>
                  <div className="text-[11px] text-slate-500">Céd. Prof. <strong className="text-slate-700">{auditModal.firma.cedula_profesional}</strong></div>
                  <div className="text-[10px] text-emerald-700 font-medium pt-1 border-t border-slate-200/60">
                    Comprobada mediante Biometría Dactilar DigitalPersona (FMD ANSI 378-2004)
                  </div>
                </div>

                {/* 2. INTEGRIDAD */}
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex items-center gap-1.5 text-hes-blue-main font-bold text-xs uppercase">
                    <FiShield /> 2. Integridad del Documento
                  </div>
                  <div className="font-semibold text-slate-800">Función Hash SHA-256</div>
                  <div className="text-[11px] text-slate-500">Recalculado sobre Cadena Original</div>
                  <div className="text-[10px] text-emerald-700 font-medium pt-1 border-t border-slate-200/60">
                    Garantiza inalterabilidad total del texto y signos vitales
                  </div>
                </div>

                {/* 3. AUTENTICIDAD Y NO REPUDIO */}
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex items-center gap-1.5 text-hes-blue-main font-bold text-xs uppercase">
                    <FiLock /> 3. Autenticidad y No Repudio
                  </div>
                  <div className="font-semibold text-slate-800">Sello HMAC-SHA512</div>
                  <div className="text-[11px] text-slate-500">Generado con Clave Criptográfica</div>
                  <div className="text-[10px] text-emerald-700 font-medium pt-1 border-t border-slate-200/60">
                    Imposibilidad de falsificación o suplantación pericial
                  </div>
                </div>

              </div>
            </div>

            {/* SELLO CRIPTOGRÁFICO HMAC-SHA512 */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-bold text-slate-700 uppercase tracking-wide flex items-center gap-1.5">
                  <FiLock className="text-hes-blue-main" /> Sello Criptográfico HMAC-SHA512
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(auditModal.firma.sello_digital || '');
                    setAuditModal(prev => ({ ...prev, copied: 'sello' }));
                    setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                  }}
                  className="text-xs font-bold text-hes-blue-main hover:underline flex items-center gap-1"
                >
                  <FiCheckSquare /> {auditModal.copied === 'sello' ? '¡Copiado al portapapeles!' : 'Copiar Sello Completo'}
                </button>
              </div>
              <div className="p-3 bg-slate-900 text-emerald-400 font-mono text-[11px] rounded-xl break-all leading-relaxed select-all shadow-inner">
                {auditModal.firma.sello_digital || 'No disponible'}
              </div>
            </div>

            {/* HASH SHA-256 DE INTEGRIDAD DOCUMENTAL */}
            {auditModal.firma.hash_sha256 && (
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wide flex items-center gap-1.5">
                    <FiShield className="text-hes-blue-main" /> Hash SHA-256 de Integridad Documental
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(auditModal.firma.hash_sha256 || '');
                      setAuditModal(prev => ({ ...prev, copied: 'hash' }));
                      setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                    }}
                    className="text-xs font-bold text-hes-blue-main hover:underline flex items-center gap-1"
                  >
                    <FiCheckSquare /> {auditModal.copied === 'hash' ? '¡Copiado!' : 'Copiar Hash'}
                  </button>
                </div>
                <div className="p-2.5 bg-slate-100 text-slate-800 font-mono text-[11px] rounded-xl break-all select-all border border-slate-200">
                  {auditModal.firma.hash_sha256}
                </div>
              </div>
            )}

            {/* CADENA ORIGINAL NORMALIZADA */}
            {(auditModal.verification?.cadena_original || auditModal.firma.cadena_original) && (
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wide">
                    Cadena Original Normalizada
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(auditModal.verification?.cadena_original || auditModal.firma.cadena_original || '');
                      setAuditModal(prev => ({ ...prev, copied: 'cadena' }));
                      setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                    }}
                    className="text-xs font-bold text-hes-blue-main hover:underline flex items-center gap-1"
                  >
                    <FiCheckSquare /> {auditModal.copied === 'cadena' ? '¡Copiado!' : 'Copiar Cadena'}
                  </button>
                </div>
                <div className="p-2.5 bg-slate-50 text-slate-600 font-mono text-[10px] rounded-xl break-all select-all border border-slate-200 max-h-20 overflow-y-auto">
                  {auditModal.verification?.cadena_original || auditModal.firma.cadena_original}
                </div>
              </div>
            )}

            {/* FOOTER Y MARCO NORMATIVO */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pt-3 border-t border-slate-100 text-xs">
              <div className="text-slate-500 font-medium">
                <strong>Marco Normativo de Referencia:</strong> NOM-004-SSA3-2012 / NOM-024-SSA3-2012
              </div>
              <button
                type="button"
                onClick={() => setAuditModal({ open: false, firma: null, loading: false, verification: null, copied: null })}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold transition-colors self-end sm:self-auto"
              >
                Cerrar Verificación
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

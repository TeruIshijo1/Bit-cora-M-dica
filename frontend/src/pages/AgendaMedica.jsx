import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { 
  FiCalendar, FiClock, FiUser, FiPlus, FiFilter, FiCheckCircle, 
  FiAlertCircle, FiSearch, FiMapPin, FiFileText, FiRefreshCw, FiEdit3
} from 'react-icons/fi';
import { MdOutlineMedicalServices } from 'react-icons/md';
import { useEscapeKey } from '../hooks/useEscapeKey';
import { usePatientSearchQuery } from '../hooks/useQueries';

export default function AgendaMedica() {
  const rolActual = localStorage.getItem('rol');
  const isDoctorSession = rolActual === 'medico' || rolActual === 'ayudante';
  const sessionMedico = (() => {
    try {
      return JSON.parse(localStorage.getItem('medico') || 'null');
    } catch {
      return null;
    }
  })();
  const sessionMedicoId = sessionMedico?.medico_id || sessionMedico?.id || null;
  const [medicos, setMedicos] = useState([]);
  const [selectedMedicoId, setSelectedMedicoId] = useState('');
  const [citas, setCitas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEscapeKey(showModal, () => setShowModal(false));

  const [formData, setFormData] = useState({
    medico_id: '',
    nombre_paciente_manual: '',
    pt_num: '',
    expediente: '',
    paciente_id: null,
    fecha_hora: '',
    motivo: '',
    lugar: 'Consultorio 12 - Consulta Externa',
    notas: ''
  });

  const [showPatientDropdown, setShowPatientDropdown] = useState(false);
  const patientSearchTerm = formData.pt_num ? '' : formData.nombre_paciente_manual.trim();
  const patientSearchQuery = usePatientSearchQuery(
    patientSearchTerm,
    showPatientDropdown && patientSearchTerm.length >= 2,
    8,
  );
  const patientResults = patientSearchQuery.data || [];
  const searchingPatients = patientSearchQuery.isFetching;

  // Cargar lista de médicos
  useEffect(() => {
    const fetchMedicos = async () => {
      try {
        const res = await api.get('/medicos/list');
        if (res.data && Array.isArray(res.data)) {
          setMedicos(res.data);
          let defaultMedico = null;

          // Para una sesión médica, el backend ya entrega únicamente el
          // perfil vigente; no dependemos de un ID guardado en el navegador.
          if (isDoctorSession && res.data.length > 0) {
            defaultMedico = res.data[0];
          }

          // Para administración, seleccionar inicialmente el médico logueado
          // si existe; en otro caso usar el primer médico activo.
          if (!defaultMedico && !isDoctorSession) {
            const loggedMedicoStr = localStorage.getItem('medico');
            if (loggedMedicoStr) {
              try {
                const loggedMedico = JSON.parse(loggedMedicoStr);
                defaultMedico = res.data.find(m => String(m.id) === String(loggedMedico.medico_id));
              } catch {
                defaultMedico = null;
              }
            }
          }
          if (!defaultMedico && !isDoctorSession && res.data.length > 0) {
            defaultMedico = res.data[0];
          }

          if (defaultMedico) {
            setSelectedMedicoId(defaultMedico.id.toString());
            setFormData(prev => ({ ...prev, medico_id: defaultMedico.id }));
          } else if (isDoctorSession && sessionMedicoId) {
            setSelectedMedicoId(String(sessionMedicoId));
            setFormData(prev => ({ ...prev, medico_id: sessionMedicoId }));
          }
        }
      } catch (err) {
        console.error("Error fetching medicos:", err);
      }
    };
    fetchMedicos();
  }, [isDoctorSession, sessionMedicoId]);

  const [pendientesCount, setPendientesCount] = useState(0);

  // Cargar citas cuando cambia el médico seleccionado
  const fetchCitas = async () => {
    try {
      setLoading(true);
      const url = selectedMedicoId ? `/agenda/citas?medico_id=${selectedMedicoId}` : '/agenda/citas';
      const res = await api.get(url);
      if (res.data && Array.isArray(res.data)) {
        setCitas(res.data);
      }
      
      // Fetch pending signatures for the selected doctor
      if (selectedMedicoId) {
        const penRes = await api.get(`/atenciones/pendientes/${selectedMedicoId}`);
        if (penRes.data && Array.isArray(penRes.data)) {
          setPendientesCount(penRes.data.length);
        } else {
          setPendientesCount(0);
        }
      }
    } catch (err) {
      console.error("Error fetching citas:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCitas();
  }, [selectedMedicoId]);

  const handlePatientInputChange = (e) => {
    const val = e.target.value;
    setFormData(prev => ({ ...prev, nombre_paciente_manual: val, pt_num: '', expediente: '', paciente_id: null }));
    setShowPatientDropdown(val.trim().length >= 2);
  };

  const handleSelectPatientFromSearch = (pt) => {
    setFormData(prev => ({
      ...prev,
      nombre_paciente_manual: `${pt.name} (PT-${pt.pt_num})`,
      pt_num: pt.pt_num,
      expediente: pt.pt_num,
      paciente_id: pt.pt_num
    }));
    setShowPatientDropdown(false);
  };

  const handleCreateCita = async (e) => {
    e.preventDefault();
    if (!formData.nombre_paciente_manual || !formData.fecha_hora || !formData.motivo) {
      alert("Por favor complete los campos obligatorios.");
      return;
    }

    try {
      setSubmitting(true);
      const targetMedicoId = isDoctorSession
        ? (selectedMedicoId || sessionMedicoId)
        : (formData.medico_id || selectedMedicoId || null);
      if (!targetMedicoId) {
        alert('No se pudo identificar al médico de la sesión. Vuelve a iniciar sesión.');
        return;
      }

      await api.post('/agenda/citas', {
        ...formData,
        medico_id: parseInt(targetMedicoId, 10)
      });
      setShowModal(false);
      setShowPatientDropdown(false);
      setFormData({
        medico_id: isDoctorSession ? (selectedMedicoId || sessionMedicoId) : selectedMedicoId,
        nombre_paciente_manual: '',
        pt_num: '',
        expediente: '',
        paciente_id: null,
        fecha_hora: '',
        motivo: '',
        lugar: 'Consultorio 12 - Consulta Externa',
        notas: ''
      });
      fetchCitas();
    } catch (err) {
      console.error("Error creating cita:", err);
      alert("Error al programar la cita.");
    } finally {
      setSubmitting(false);
    }
  };

  const currentDoctor = medicos.find(m => m.id.toString() === String(selectedMedicoId || sessionMedicoId));

  return (
    <div className="he-agenda-page p-4 md:p-6 max-w-7xl mx-auto space-y-5 min-h-screen">
      
      {/* HEADER */}
      <div className="he-agenda-header flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-5 md:p-6">
        <div className="flex items-start gap-3.5">
          <div className="he-agenda-icon">📅</div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-black uppercase tracking-[0.14em] text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full">🩺 Control por especialista</span>
              <h1 className="text-[22px] font-black text-slate-900 tracking-tight">Agenda Médica y Programación de Visitas</h1>
            </div>
            <p className="text-xs text-slate-500 mt-1">Control de citas, pases de visita y seguimiento ambulatorio/hospitalario por especialista.</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto flex-wrap">
          <a
            href="/camas"
            className="he-btn-camas flex items-center gap-2 px-4 py-2.5 text-sm transition-all"
            title="Ver mapa de camas"
          >
            <MdOutlineMedicalServices className="text-lg" /> Ver Camas
          </a>
          <button 
            onClick={() => setShowModal(true)}
            className="he-btn-programar flex items-center gap-2 text-white px-4 py-2.5 text-sm transition-all"
          >
            <FiPlus /> Programar Nueva Cita / Visita
          </button>
          <button 
            onClick={fetchCitas}
            className="he-btn-ghost p-2.5 transition-colors"
            title="Refrescar agenda"
          >
            <FiRefreshCw />
          </button>
        </div>
      </div>

      {/* FILTER & DOCTOR PROFILE CARD */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* DOCTOR SELECTOR */}
        <div className="he-agenda-card p-5 space-y-3" style={{ '--he-accent': 'linear-gradient(90deg,#0e7490,#06b6d4)' }}>
          <label className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-500 flex items-center gap-1.5">
            <span className="w-6 h-6 rounded-lg flex items-center justify-center text-white text-xs" style={{ background: 'linear-gradient(135deg,#0e7490,#06b6d4)' }}><MdOutlineMedicalServices /></span> Médico Especialista
          </label>
          
          {rolActual === 'medico' ? (
            <div className="w-full border border-slate-200 bg-gradient-to-b from-slate-50 to-slate-100 rounded-xl px-3.5 py-3 text-sm font-bold text-slate-800">
              👨‍⚕️ {currentDoctor ? `${currentDoctor.nombre} (${currentDoctor.especialidad})` : 'Cargando su perfil...'}
            </div>
          ) : (
            <select 
              value={selectedMedicoId}
              onChange={(e) => {
                setSelectedMedicoId(e.target.value);
                setFormData(prev => ({ ...prev, medico_id: e.target.value }));
              }}
              className="he-search w-full px-3.5 py-2.5 text-sm font-bold text-slate-800 outline-none transition-colors"
            >
              <option value="">-- Todos los Médicos --</option>
              {medicos.map(m => (
                <option key={m.id} value={m.id}>
                  {m.nombre} ({m.especialidad})
                </option>
              ))}
            </select>
          )}

          {currentDoctor && (
            <div className="pt-3 border-t border-slate-100 text-xs space-y-1.5 bg-slate-50/70 rounded-xl p-3">
              <div className="text-slate-500">🪪 Cédula: <span className="font-black text-slate-800">{currentDoctor.cedula}</span></div>
              <div className="text-slate-500">🕗 Horario: <span className="font-bold text-slate-700">{currentDoctor.horario}</span></div>
            </div>
          )}
        </div>

        {/* STATS 1 */}
        <div className="he-agenda-card p-5 flex items-center justify-between" style={{ '--he-accent': 'linear-gradient(90deg,#059669,#00d1a1)' }}>
          <div>
            <div className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-400">Citas Programadas</div>
            <div className="he-agenda-num text-4xl font-black mt-1">{citas.length}</div>
            <div className="text-xs text-emerald-600 font-bold mt-1 flex items-center gap-1">● Activas para seguimiento</div>
          </div>
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl text-white shrink-0" style={{ background: 'linear-gradient(135deg,#059669,#00b48a)', boxShadow: '0 8px 18px -8px rgba(5,150,105,.7)' }}>
            <FiCheckCircle />
          </div>
        </div>

        {/* STATS 2 (Pendientes de Firma) */}
        <a href="/firma-express" className="he-agenda-card p-5 flex items-center justify-between cursor-pointer group" style={{ '--he-accent': 'linear-gradient(90deg,#ea580c,#f59e0b)' }}>
          <div>
            <div className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-400 group-hover:text-orange-500 transition-colors">Capturas por Firmar</div>
            <div className="he-agenda-num text-4xl font-black mt-1">{pendientesCount}</div>
            <div className="text-xs text-orange-600 font-bold mt-1 flex items-center gap-1">✍️ Requieren firma biométrica</div>
          </div>
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl text-white shrink-0 group-hover:scale-110 transition-all" style={{ background: 'linear-gradient(135deg,#ea580c,#f59e0b)', boxShadow: '0 8px 18px -8px rgba(234,88,12,.7)' }}>
            <FiEdit3 />
          </div>
        </a>

      </div>

      {/* APPOINTMENTS LIST */}
      <div className="he-agenda-card overflow-hidden" style={{ '--he-accent': 'linear-gradient(90deg,#4f46e5,#06b6d4)' }}>
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-gradient-to-b from-white to-slate-50/60">
          <h2 className="font-black text-slate-900 text-[16px] flex items-center gap-2">🗂️ Listado Cronológico de Citas y Visitas</h2>
          <span className="text-[11px] font-black bg-slate-800 text-white px-3 py-1 rounded-full">
            {citas.length} registros
          </span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-slate-500 text-sm flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></div>
            Cargando agenda médica...
          </div>
        ) : citas.length === 0 ? (
          <div className="py-14 text-center space-y-2">
            <div className="text-4xl">📭</div>
            <div className="font-black text-slate-700 text-sm">Sin citas programadas</div>
            <div className="text-xs text-slate-400">No hay citas registradas para este médico.</div>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {citas.map((c) => (
              <div key={c.id} className="he-cita-row p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-start gap-4">
                  <div className="he-cita-fecha p-3 font-bold flex flex-col items-center justify-center min-w-[74px]">
                    <span className="text-[11px] font-bold opacity-80">{c.fecha}</span>
                    <span className="text-[16px] font-black">{c.hora}</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-black text-slate-900 text-[15px]">{c.paciente_nombre}</span>
                      <span className="text-[10px] font-black bg-teal-50 text-teal-700 px-2.5 py-0.5 rounded-full border border-teal-200">
                        ● {c.estatus}
                      </span>
                    </div>
                    <div className="text-xs font-bold text-indigo-700 mt-1">🩺 {c.motivo}</div>
                    <div className="flex items-center gap-4 text-xs text-slate-500 mt-1.5 flex-wrap">
                      <span className="flex items-center gap-1 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-md"><FiMapPin /> {c.lugar}</span>
                      <span>👨‍⚕️ Médico: <strong className="text-slate-700">{c.medico_nombre}</strong></span>
                    </div>
                    {c.notas && (
                      <p className="text-xs text-slate-600 mt-2 bg-amber-50/70 p-2.5 rounded-xl border border-amber-100 max-w-2xl">
                        📝 Nota: {c.notas}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end md:self-center">
                  {(c.pt_num || c.expediente || c.paciente_id) && (
                    <Link
                      to={`/ehr/${encodeURIComponent(c.pt_num || c.expediente || c.paciente_id)}`}
                      className="he-btn-ghost text-xs font-bold px-3.5 py-2 transition-colors flex items-center gap-1.5"
                    >
                      <FiFileText /> Ver Expediente
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* MODAL PROGRAMAR CITA */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="he-agenda-card max-w-lg w-full p-6 space-y-4" style={{ '--he-accent': 'linear-gradient(90deg,#4f46e5,#00b48a)' }}>
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">📅 Programar Cita / Visita Médica</h3>
              <button 
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateCita} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Médico Asignado *</label>
                {isDoctorSession ? (
                  <div className="w-full border border-slate-200 bg-slate-50 rounded-xl px-3 py-2 text-sm font-semibold text-slate-800 flex items-center justify-between gap-2">
                    <span className="truncate">
                      {currentDoctor
                        ? `${currentDoctor.nombre} (${currentDoctor.especialidad})`
                        : (sessionMedico?.nombre_completo || 'Médico de la sesión')}
                    </span>
                    <span className="shrink-0 text-[10px] font-black uppercase tracking-wide text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-full">
                      Usted
                    </span>
                  </div>
                ) : (
                  <select 
                    value={formData.medico_id}
                    onChange={(e) => setFormData({ ...formData, medico_id: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 rounded-xl px-3 py-2 text-sm font-semibold text-slate-800"
                    required
                  >
                    <option value="">-- Seleccionar Médico --</option>
                    {medicos.map(m => (
                      <option key={m.id} value={m.id}>{m.nombre} ({m.especialidad})</option>
                    ))}
                  </select>
                )}
              </div>

              <div className="relative">
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Nombre del Paciente / Expediente *</label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input 
                      type="text" 
                      value={formData.nombre_paciente_manual}
                      onChange={handlePatientInputChange}
                      onFocus={() => { if (patientSearchTerm.length >= 2) setShowPatientDropdown(true); }}
                      placeholder="Buscar por Nombre, Folio o CURP..."
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:border-hes-blue-main outline-none"
                      required
                    />
                    {searchingPatients && (
                      <span className="absolute right-3 top-2.5 text-xs text-hes-blue-main animate-pulse font-bold">
                        Buscando...
                      </span>
                    )}
                  </div>
                </div>

                {/* DROPDOWN DE RESULTADOS */}
                {showPatientDropdown && patientResults.length > 0 && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-xl shadow-xl z-50 max-h-48 overflow-y-auto divide-y divide-slate-100">
                    {patientResults.map(pt => (
                      <div
                        key={pt.pt_num}
                        onClick={() => handleSelectPatientFromSearch(pt)}
                        className="p-2.5 hover:bg-blue-50 cursor-pointer transition-colors flex justify-between items-center text-xs"
                      >
                        <div>
                          <div className="font-bold text-slate-800">{pt.name}</div>
                          <div className="text-slate-400 text-[11px] flex gap-2">
                            <span>Exp: <strong className="text-hes-blue-main">#{pt.pt_num}</strong></span>
                            {pt.cama && <span>• Cama: {pt.cama}</span>}
                          </div>
                        </div>
                        <span className="text-[10px] font-bold bg-blue-100 text-hes-blue-main px-2 py-0.5 rounded-full">
                          Seleccionar
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Fecha y Hora *</label>
                  <input 
                    type="datetime-local" 
                    value={formData.fecha_hora}
                    onChange={(e) => setFormData({ ...formData, fecha_hora: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Lugar / Consultorio</label>
                  <input 
                    type="text" 
                    value={formData.lugar}
                    onChange={(e) => setFormData({ ...formData, lugar: e.target.value })}
                    placeholder="Consultorio 12"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Motivo de la Cita / Valoración *</label>
                <input 
                  type="text" 
                  value={formData.motivo}
                  onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
                  placeholder="Ej. Control Postoperatorio, Revaloración Urgencias"
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Instrucciones / Notas</label>
                <textarea 
                  value={formData.notas}
                  onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                  placeholder="Indicaciones previas, estudios requeridos..."
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm"
                  rows={2}
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button 
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-200 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  disabled={submitting}
                  className="he-btn-programar px-5 py-2.5 text-white text-sm transition-all"
                >
                  {submitting ? 'Guardando...' : 'Programar Cita'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

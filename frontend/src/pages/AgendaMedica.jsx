import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { 
  FiCalendar, FiClock, FiUser, FiPlus, FiFilter, FiCheckCircle, 
  FiAlertCircle, FiSearch, FiMapPin, FiFileText, FiRefreshCw 
} from 'react-icons/fi';
import { MdOutlineMedicalServices } from 'react-icons/md';

export default function AgendaMedica() {
  const [medicos, setMedicos] = useState([]);
  const [selectedMedicoId, setSelectedMedicoId] = useState('');
  const [citas, setCitas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    medico_id: '',
    nombre_paciente_manual: '',
    fecha_hora: '',
    motivo: '',
    lugar: 'Consultorio 12 - Consulta Externa',
    notas: ''
  });

  // Cargar lista de médicos
  useEffect(() => {
    const fetchMedicos = async () => {
      try {
        const res = await api.get('/medicos/list');
        if (res.data && Array.isArray(res.data)) {
          setMedicos(res.data);
          // Preseleccionar a JOSE JOSE PRUEBA ENRIQUEZ por defecto si existe
          const jose = res.data.find(m => m.nombre.includes('JOSE JOSE PRUEBA'));
          if (jose) {
            setSelectedMedicoId(jose.id.toString());
            setFormData(prev => ({ ...prev, medico_id: jose.id }));
          } else if (res.data.length > 0) {
            setSelectedMedicoId(res.data[0].id.toString());
            setFormData(prev => ({ ...prev, medico_id: res.data[0].id }));
          }
        }
      } catch (err) {
        console.error("Error fetching medicos:", err);
      }
    };
    fetchMedicos();
  }, []);

  // Cargar citas cuando cambia el médico seleccionado
  const fetchCitas = async () => {
    try {
      setLoading(true);
      const url = selectedMedicoId ? `/agenda/citas?medico_id=${selectedMedicoId}` : '/agenda/citas';
      const res = await api.get(url);
      if (res.data && Array.isArray(res.data)) {
        setCitas(res.data);
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

  const handleCreateCita = async (e) => {
    e.preventDefault();
    if (!formData.nombre_paciente_manual || !formData.fecha_hora || !formData.motivo) {
      alert("Por favor complete los campos obligatorios.");
      return;
    }

    try {
      setSubmitting(true);
      await api.post('/agenda/citas', {
        ...formData,
        medico_id: formData.medico_id ? parseInt(formData.medico_id) : (selectedMedicoId ? parseInt(selectedMedicoId) : null)
      });
      setShowModal(false);
      setFormData({
        medico_id: selectedMedicoId,
        nombre_paciente_manual: '',
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

  const currentDoctor = medicos.find(m => m.id.toString() === selectedMedicoId);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      
      {/* HEADER */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-blue-50 text-hes-blue-main rounded-xl"><FiCalendar className="text-xl" /></span>
            <h1 className="text-2xl font-bold text-slate-800">Agenda Médica y Programación de Visitas</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">Control de citas, pases de visita y seguimiento ambulatorio/hospitalario por especialista.</p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <button 
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2.5 rounded-xl font-semibold text-sm shadow-sm transition-all"
          >
            <FiPlus /> Programar Nueva Cita / Visita
          </button>
          <button 
            onClick={fetchCitas}
            className="p-2.5 border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-600 transition-colors"
            title="Refrescar agenda"
          >
            <FiRefreshCw />
          </button>
        </div>
      </div>

      {/* FILTER & DOCTOR PROFILE CARD */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* DOCTOR SELECTOR */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 space-y-3">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <MdOutlineMedicalServices /> Médico Especialista
          </label>
          <select 
            value={selectedMedicoId}
            onChange={(e) => {
              setSelectedMedicoId(e.target.value);
              setFormData(prev => ({ ...prev, medico_id: e.target.value }));
            }}
            className="w-full border border-slate-200 bg-slate-50 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none focus:border-hes-blue-main transition-colors"
          >
            <option value="">-- Todos los Médicos --</option>
            {medicos.map(m => (
              <option key={m.id} value={m.id}>
                {m.nombre} ({m.especialidad})
              </option>
            ))}
          </select>

          {currentDoctor && (
            <div className="pt-3 border-t border-slate-100 text-xs space-y-1">
              <div className="text-slate-500">Cédula: <span className="font-bold text-slate-700">{currentDoctor.cedula}</span></div>
              <div className="text-slate-500">Horario: <span className="font-medium text-slate-700">{currentDoctor.horario}</span></div>
            </div>
          )}
        </div>

        {/* STATS 1 */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Citas Programadas</div>
            <div className="text-3xl font-extrabold text-slate-800 mt-1">{citas.length}</div>
            <div className="text-xs text-emerald-600 font-medium mt-0.5">Activas para seguimiento</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center text-2xl font-bold">
            <FiCheckCircle />
          </div>
        </div>

        {/* STATS 2 */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Paciente Demo</div>
            <div className="text-base font-bold text-hes-blue-main mt-1">COMODIN COMODIN (PT-5704)</div>
            <div className="text-xs text-slate-500 mt-0.5">Cama Urgencias 1 (Virtual)</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-hes-blue-main flex items-center justify-center text-2xl font-bold">
            <FiUser />
          </div>
        </div>

      </div>

      {/* APPOINTMENTS LIST */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex justify-between items-center">
          <h2 className="font-bold text-slate-800 text-base">Listado Cronológico de Citas y Visitas</h2>
          <span className="text-xs bg-slate-100 text-slate-600 px-3 py-1 rounded-full font-medium">
            {citas.length} registros
          </span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-slate-500 text-sm">Cargando agenda médica...</div>
        ) : citas.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm">No hay citas registradas para este médico.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {citas.map((c) => (
              <div key={c.id} className="p-5 hover:bg-slate-50/70 transition-colors flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-blue-50 text-hes-blue-main rounded-xl font-bold flex flex-col items-center justify-center min-w-[70px]">
                    <span className="text-xs font-medium">{c.fecha}</span>
                    <span className="text-base font-extrabold">{c.hora}</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-800 text-base">{c.paciente_nombre}</span>
                      <span className="text-xs bg-teal-50 text-teal-700 px-2 py-0.5 rounded font-semibold border border-teal-100">
                        {c.estatus}
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-hes-blue-main mt-0.5">{c.motivo}</div>
                    <div className="flex items-center gap-4 text-xs text-slate-500 mt-1">
                      <span className="flex items-center gap-1"><FiMapPin /> {c.lugar}</span>
                      <span>Médico: <strong className="text-slate-700">{c.medico_nombre}</strong></span>
                    </div>
                    {c.notas && (
                      <p className="text-xs text-slate-600 mt-1.5 bg-slate-50 p-2 rounded-lg border border-slate-100 max-w-2xl">
                        Nota: {c.notas}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end md:self-center">
                  <a
                    href={`/ehr/5704`}
                    className="text-xs font-semibold text-hes-blue-main hover:bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-200 transition-colors flex items-center gap-1"
                  >
                    <FiFileText /> Ver Expediente
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* MODAL PROGRAMAR CITA */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-800">Programar Cita / Visita Médica</h3>
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
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Nombre del Paciente / Expediente *</label>
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={formData.nombre_paciente_manual}
                    onChange={(e) => setFormData({ ...formData, nombre_paciente_manual: e.target.value })}
                    placeholder="Ej. COMODIN COMODIN COMODIN (PT-5704)"
                    className="flex-1 border border-slate-200 rounded-xl px-3 py-2 text-sm"
                    required
                  />
                  <button 
                    type="button"
                    onClick={() => setFormData({ ...formData, nombre_paciente_manual: "COMODIN COMODIN COMODIN (PT-5704)", paciente_id: 5704 })}
                    className="text-xs bg-blue-50 text-hes-blue-main font-semibold px-2 py-1 rounded-lg border border-blue-200 hover:bg-blue-100"
                  >
                    Usar Demo
                  </button>
                </div>
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
                  className="px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-sm font-semibold shadow-sm transition-all"
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

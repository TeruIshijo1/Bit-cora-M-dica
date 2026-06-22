import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { MdSearch, MdBed } from 'react-icons/md';
import { FiCalendar, FiEdit3, FiFileText, FiUser, FiList, FiClock, FiActivity, FiMapPin, FiPlusCircle, FiCheckCircle } from 'react-icons/fi';
import { FaStethoscope } from 'react-icons/fa';

const serverIP = window.location.hostname;
const api = axios.create({ baseURL: `http://${serverIP}:8000/api` });

export default function CapturaEnfermeria() {
  const [pacientes, setPacientes] = useState([]);
  const [medicos, setMedicos] = useState([]);
  const [areas, setAreas] = useState([]);
  const [tiposAtencion, setTiposAtencion] = useState([]);
  
  const [habitacion, setHabitacion] = useState('');
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState(null);
  
  const [tipoAtencion, setTipoAtencion] = useState('');
  const [areaHospitalaria, setAreaHospitalaria] = useState('');
  const [nombreProcedimiento, setNombreProcedimiento] = useState('');
  const [medicoId, setMedicoId] = useState('');
  
  const now = new Date();
  const currentHora = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  
  const [fecha, setFecha] = useState(now.toISOString().slice(0, 10));
  const [hora, setHora] = useState(currentHora);
  const [procedimientoDetalle, setProcedimientoDetalle] = useState('');
  
  const [activeTab, setActiveTab] = useState('captura'); // captura, historial, pacientes
  const [historial, setHistorial] = useState([]);

  // Estados para nuevo paciente rápido
  const [isCreatingPaciente, setIsCreatingPaciente] = useState(false);
  const [newPacienteNombre, setNewPacienteNombre] = useState('');
  const [newPacienteAreaInline, setNewPacienteAreaInline] = useState('');
  
  // Estados para nuevo paciente en la pestaña Pacientes
  const [newPacienteNombreTab, setNewPacienteNombreTab] = useState('');
  const [newPacienteHabitacionTab, setNewPacienteHabitacionTab] = useState('');
  const [newPacienteAreaTab, setNewPacienteAreaTab] = useState('');

  // Estados para filtros de historial
  const [filterText, setFilterText] = useState('');
  const [filterArea, setFilterArea] = useState('');
  const [filterDate, setFilterDate] = useState('');

  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, [navigate]);

  useEffect(() => {
    if (activeTab === 'historial') fetchHistorial();
  }, [activeTab]);

  const getToken = () => localStorage.getItem('token');

  const fetchData = async () => {
    try {
      const resP = await api.get('/pacientes');
      setPacientes(resP.data);
      const resM = await api.get('/medicos');
      setMedicos(resM.data);
      const resA = await api.get('/catalogos/areas');
      setAreas(resA.data);
      const resT = await api.get('/catalogos/tipos');
      setTiposAtencion(resT.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchHistorial = async () => {
    try {
      const res = await api.get('/atenciones/mis-registros', {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      setHistorial(res.data);
    } catch (e) { console.error(e); }
  };

  const handleHabitacionChange = (e) => {
    const val = e.target.value;
    setHabitacion(val);
    const found = pacientes.find(p => p.num_habitacion.toLowerCase() === val.toLowerCase() || p.nombre_completo.toLowerCase().includes(val.toLowerCase()));
    setPacienteSeleccionado(found || null);
    setIsCreatingPaciente(false); // Reset al cambiar
  };

  const handleCreatePaciente = async () => {
    if (!newPacienteNombre || !habitacion || !newPacienteAreaInline) {
      alert("Ingrese nombre, habitación y área hospitalaria"); return;
    }
    try {
      const res = await api.post('/pacientes', {
        nombre_completo: newPacienteNombre,
        num_habitacion: habitacion,
        area_hospitalaria: newPacienteAreaInline
      }, { headers: { Authorization: `Bearer ${getToken()}` } });
      
      alert("Paciente ingresado exitosamente");
      setNewPacienteNombre('');
      setNewPacienteAreaInline('');
      setIsCreatingPaciente(false);
      fetchData(); // Recargar lista de pacientes
      setPacienteSeleccionado(res.data);
    } catch(e) {
      alert("Error al ingresar paciente");
    }
  };

  const handleCreatePacienteTab = async () => {
    if (!newPacienteNombreTab || !newPacienteHabitacionTab || !newPacienteAreaTab) {
      alert("Ingrese nombre, habitación y área hospitalaria"); return;
    }
    try {
      const res = await api.post('/pacientes', {
        nombre_completo: newPacienteNombreTab,
        num_habitacion: newPacienteHabitacionTab,
        area_hospitalaria: newPacienteAreaTab
      }, { headers: { Authorization: `Bearer ${getToken()}` } });
      
      alert("Paciente registrado exitosamente");
      setNewPacienteNombreTab('');
      setNewPacienteHabitacionTab('');
      setNewPacienteAreaTab('');
      fetchData(); // Recargar lista de pacientes
    } catch(e) {
      alert("Error al registrar paciente");
    }
  };

  const handleAltaPaciente = async (id) => {
    try {
      await api.put(`/pacientes/${id}/alta`, {}, { headers: { Authorization: `Bearer ${getToken()}` } });
      fetchData();
      if(pacienteSeleccionado?.id === id) {
        setPacienteSeleccionado(null);
        setHabitacion('');
      }
    } catch(e) { alert("Error al dar de alta al paciente"); }
  };

  const handleGuardarCaptura = async () => {
    if (!pacienteSeleccionado || !medicoId || !tipoAtencion || !nombreProcedimiento || !fecha || !hora) {
      alert("Faltan datos obligatorios");
      return;
    }

    try {
      const fechaRealizacionStr = `${fecha}T${hora}:00`;
      
      const res = await api.post('/atenciones/pre-captura', {
        medico_id: medicoId,
        paciente_id: pacienteSeleccionado.id,
        habitacion_capturada: habitacion,
        tipo_atencion: tipoAtencion,
        nombre_procedimiento: nombreProcedimiento,
        fecha_realizacion: fechaRealizacionStr,
        procedimiento_detalle: procedimientoDetalle
      }, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      alert(`Registro creado con éxito. Folio: ${res.data.folio}`);
      setHabitacion(''); setPacienteSeleccionado(null); setTipoAtencion(''); setNombreProcedimiento('');
      setProcedimientoDetalle(''); setMedicoId('');
    } catch (error) {
      if (error.response && error.response.status === 400) {
        alert(`ERROR DUPLICADO: ${error.response.data.detail}`);
      } else { alert("Error al guardar el registro"); }
    }
  };

  const historialFiltrado = historial.filter(h => {
    if (filterText && 
        !h.folio.toLowerCase().includes(filterText.toLowerCase()) && 
        !h.paciente.nombre_completo.toLowerCase().includes(filterText.toLowerCase()) &&
        !(h.medico && h.medico.nombre_completo.toLowerCase().includes(filterText.toLowerCase()))
    ) return false;
    if (filterArea && h.area_hospitalaria !== filterArea) return false;
    if (filterDate && !h.fecha_realizacion.startsWith(filterDate)) return false;
    return true;
  });

  return (
    <div className="w-full h-full overflow-y-auto p-6 bg-slate-50">
      <div className="max-w-5xl mx-auto w-full pb-12">
        
        {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-slate-200">
        <button 
          onClick={() => setActiveTab('captura')}
          className={`pb-3 px-4 font-semibold ${activeTab === 'captura' ? 'text-hes-blue-main border-b-2 border-hes-blue-main' : 'text-slate-500 hover:text-slate-700'}`}
        >
          <div className="flex items-center gap-2"><FiFileText /> Nueva Captura</div>
        </button>
        <button 
          onClick={() => setActiveTab('historial')}
          className={`pb-3 px-4 font-semibold ${activeTab === 'historial' ? 'text-hes-blue-main border-b-2 border-hes-blue-main' : 'text-slate-500 hover:text-slate-700'}`}
        >
          <div className="flex items-center gap-2"><FiList /> Mis Registros</div>
        </button>
        <button 
          onClick={() => setActiveTab('pacientes')}
          className={`pb-3 px-4 font-semibold ${activeTab === 'pacientes' ? 'text-hes-blue-main border-b-2 border-hes-blue-main' : 'text-slate-500 hover:text-slate-700'}`}
        >
          <div className="flex items-center gap-2"><FiUser /> Gestión de Pacientes</div>
        </button>
      </div>

      {activeTab === 'captura' && (
        <div className="flex flex-col gap-6 pb-24">
          <section className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex gap-6">
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-blue-800 flex items-center gap-2 mb-4"><FiUser /> 1. Paciente y Área</h2>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="relative">
                  <MdSearch className="absolute left-3 top-3.5 text-slate-400 text-xl" />
                  <input 
                    type="text" 
                    placeholder="Buscar habitación (ej. 101) o nombre..." 
                    className="w-full border border-slate-300 rounded-lg pl-10 p-3 focus:outline-none focus:ring-2 focus:ring-blue-600"
                    value={habitacion}
                    onChange={handleHabitacionChange}
                  />
                </div>
              </div>
              
              {pacienteSeleccionado ? (
                <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 font-medium text-blue-900 flex justify-between items-center">
                  <span>Paciente Actual: {pacienteSeleccionado.nombre_completo} (Hab: {pacienteSeleccionado.num_habitacion})</span>
                  <span className="text-xs text-blue-500 font-bold bg-blue-100 px-2 py-1 rounded">Ingresado</span>
                </div>
              ) : habitacion.length > 0 ? (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  {!isCreatingPaciente ? (
                     <div className="flex flex-col gap-2">
                        <span className="text-orange-800 font-medium">No se encontró paciente con ese dato.</span>
                        <button onClick={() => setIsCreatingPaciente(true)} className="flex items-center gap-1 text-sm font-bold text-orange-700 hover:text-orange-900 w-max">
                           <FiPlusCircle /> Ingresar paciente nuevo a esta habitación
                        </button>
                     </div>
                  ) : (
                     <div className="flex gap-2">
                        <input 
                           type="text" 
                           placeholder="Nombre completo" 
                           className="flex-1 border border-orange-300 rounded p-2 focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
                           value={newPacienteNombre}
                           onChange={e => setNewPacienteNombre(e.target.value)}
                        />
                        <select className="border border-orange-300 rounded p-2 bg-white text-sm" value={newPacienteAreaInline} onChange={e => setNewPacienteAreaInline(e.target.value)}>
                           <option value="">Área...</option>
                           {areas.map(a => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                        </select>
                        <button onClick={handleCreatePaciente} className="bg-orange-600 text-white px-4 py-2 rounded font-bold hover:bg-orange-700 text-sm">Guardar</button>
                        <button onClick={() => setIsCreatingPaciente(false)} className="bg-slate-200 text-slate-700 px-4 py-2 rounded font-bold text-sm">Cancelar</button>
                     </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-slate-500 bg-slate-50 p-4 border rounded-lg">
                  Ingrese el número de habitación (ej. 101) o nombre para encontrar al paciente o agregarlo.
                </div>
              )}
            </div>
            <div className="w-48 bg-slate-50 rounded-xl border flex flex-col items-center justify-center p-6">
              <MdBed className="text-blue-600 text-3xl mb-2" />
              <p className="text-slate-500 text-sm">Habitación</p>
              <p className="text-4xl font-bold text-[#1a2f4c]">{habitacion || '---'}</p>
            </div>
          </section>

          {/* 2. Tipo y Procedimiento */}
          <section className="bg-white rounded-xl shadow-sm p-6 border border-slate-100">
            <h2 className="text-lg font-semibold text-blue-800 flex items-center gap-2 mb-4"><FaStethoscope /> 2. Clasificación de la Atención</h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Tipo de Atención</label>
                <select 
                  className="w-full border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-600 bg-white"
                  value={tipoAtencion}
                  onChange={e => setTipoAtencion(e.target.value)}
                >
                  <option value="">Selecciona el Tipo de Atención...</option>
                  {tiposAtencion.map(t => <option key={t.id} value={t.nombre}>{t.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Nombre del Procedimiento</label>
                <input 
                  type="text"
                  placeholder="Ej. Colecistectomía Laparoscópica"
                  className="w-full border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  value={nombreProcedimiento}
                  onChange={e => setNombreProcedimiento(e.target.value)}
                />
              </div>
            </div>
          </section>

          {/* 3. Detalles y Fecha */}
          <section className="flex gap-6">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex-1">
               <h2 className="text-lg font-semibold text-blue-800 flex items-center gap-2 mb-4"><FiCalendar /> 3. Fecha, Hora y Responsable</h2>
               <div className="grid grid-cols-2 gap-4 mb-6">
                 <div>
                   <label className="block text-sm font-semibold text-slate-700 mb-1"><FiCalendar className="inline mr-1"/> Fecha</label>
                   <input type="date" className="w-full border border-slate-300 rounded-lg p-3" value={fecha} onChange={e => setFecha(e.target.value)} />
                 </div>
                 <div>
                   <label className="block text-sm font-semibold text-slate-700 mb-1"><FiClock className="inline mr-1"/> Hora</label>
                   <input type="time" className="w-full border border-slate-300 rounded-lg p-3" value={hora} onChange={e => setHora(e.target.value)} />
                 </div>
               </div>
               <label className="block text-sm font-semibold text-slate-700 mb-1"><FiUser className="inline mr-1"/> Médico Responsable</label>
               <select className="w-full border border-slate-300 rounded-lg p-3" value={medicoId} onChange={e => setMedicoId(e.target.value)}>
                 <option value="">Seleccione al médico...</option>
                 {medicos.map(m => <option key={m.id} value={m.id}>{m.nombre_completo} - {m.especialidad}</option>)}
               </select>
            </div>
            
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex-1">
               <h2 className="text-lg font-semibold text-blue-800 flex items-center gap-2 mb-4"><FiEdit3 /> 4. Detalle (Opcional)</h2>
               <textarea 
                  className="w-full h-32 border border-slate-300 rounded-lg p-3 resize-none"
                  placeholder="Describe brevemente observaciones clínicas..."
                  maxLength="1000"
                  value={procedimientoDetalle}
                  onChange={e => setProcedimientoDetalle(e.target.value)}
                ></textarea>
                <div className="text-right text-xs text-slate-400 mt-1">{procedimientoDetalle.length}/1000</div>
            </div>
          </section>

          <button onClick={handleGuardarCaptura} className="w-full bg-hes-blue-main hover:bg-[#003870] text-white text-lg font-semibold py-4 rounded-xl shadow-md transition-colors flex justify-center items-center gap-2">
            <FiCheckCircle className="text-2xl" /> Guardar Pre-Captura
          </button>
        </div>
      )}

      {activeTab === 'historial' && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
            <h3 className="font-bold text-slate-700 flex items-center gap-2">
              <FiActivity className="text-hes-blue-main" /> Mis Registros Capturados
            </h3>
            <button onClick={fetchHistorial} className="text-sm font-medium text-hes-blue-main hover:underline">Refrescar</button>
          </div>
          
          {/* Filtros */}
          <div className="p-4 bg-white border-b border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-4">
             <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Buscar Paciente / Folio</label>
                <input type="text" placeholder="Escribe para buscar..." className="w-full border rounded p-2 text-sm" value={filterText} onChange={e => setFilterText(e.target.value)} />
             </div>
             <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Filtrar por Área</label>
                <select className="w-full border rounded p-2 text-sm" value={filterArea} onChange={e => setFilterArea(e.target.value)}>
                   <option value="">Todas las áreas</option>
                   {areas.map(a => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                </select>
             </div>
             <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Filtrar por Fecha</label>
                <input type="date" className="w-full border rounded p-2 text-sm" value={filterDate} onChange={e => setFilterDate(e.target.value)} />
             </div>
          </div>
          <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="p-4 text-sm font-semibold text-slate-600">Folio</th>
                      <th className="p-4 text-sm font-semibold text-slate-600">Paciente / Hab</th>
                      <th className="p-4 text-sm font-semibold text-slate-600">Médico</th>
                      <th className="p-4 text-sm font-semibold text-slate-600">Procedimiento / Área</th>
                      <th className="p-4 text-sm font-semibold text-slate-600">Fecha Realización</th>
                      <th className="p-4 text-sm font-semibold text-slate-600">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historialFiltrado.map(h => (
                      <tr key={h.folio} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                        <td className="p-4 text-sm font-bold text-hes-blue-main">{h.folio}</td>
                        <td className="p-4 text-sm text-slate-800">
                          <div>{h.paciente.nombre_completo}</div>
                          <div className="text-xs text-slate-500">Hab: {h.habitacion_capturada}</div>
                        </td>
                        <td className="p-4 text-sm text-slate-600">{h.medico ? h.medico.nombre_completo : 'N/A'}</td>
                        <td className="p-4 text-sm text-slate-600">
                          <div>{h.nombre_procedimiento} ({h.tipo_atencion})</div>
                          <div className="text-xs text-slate-500">{h.area_hospitalaria}</div>
                        </td>
                        <td className="p-4 text-sm text-slate-600">{new Date(h.fecha_realizacion).toLocaleDateString()}</td>
                        <td className="p-4 text-sm">
                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                            h.estatus_pago === 'Pendiente de Firma' ? 'bg-orange-100 text-orange-700' : 
                            h.estatus_pago === 'Validado para Pago' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-700'
                          }`}>
                            {h.estatus_pago}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {historialFiltrado.length === 0 && (
                      <tr>
                        <td colSpan="6" className="p-8 text-center text-slate-500">No se encontraron registros de captura que coincidan.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'pacientes' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden p-6 space-y-6">

              <div className="bg-slate-50 p-6 rounded-xl border border-slate-200">
                <h3 className="text-lg font-bold text-slate-700 mb-4">Ingresar Nuevo Paciente</h3>
                <div className="flex gap-4 items-end">
                  <div className="flex-1">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Nombre Completo</label>
                    <input type="text" className="w-full border rounded-lg p-2" placeholder="Ej. Juan Pérez" value={newPacienteNombreTab} onChange={e => setNewPacienteNombreTab(e.target.value)} />
                  </div>
                  <div className="w-48">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Habitación</label>
                    <input type="text" className="w-full border rounded-lg p-2" placeholder="Ej. 101" value={newPacienteHabitacionTab} onChange={e => setNewPacienteHabitacionTab(e.target.value)} />
                  </div>
                  <div className="w-64">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Área Hospitalaria</label>
                    <select className="w-full border rounded-lg p-2 bg-white" value={newPacienteAreaTab} onChange={e => setNewPacienteAreaTab(e.target.value)}>
                      <option value="">Selecciona el Área...</option>
                      {areas.map(a => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                    </select>
                  </div>
                  <button onClick={handleCreatePacienteTab} className="bg-hes-blue-main text-white px-6 py-2 rounded-lg font-bold hover:bg-blue-800 transition-colors h-[42px]">
                    Ingresar
                  </button>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-700 mb-4">Gestión de Pacientes Activos (Camas Ocupadas)</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="p-3 text-sm font-semibold text-slate-600">ID</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Nombre del Paciente</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Habitación</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pacientes.map(p => (
                      <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3 text-sm font-semibold text-blue-700">{p.id}</td>
                        <td className="p-3 text-sm font-medium text-slate-800">{p.nombre_completo}</td>
                        <td className="p-3 text-sm text-slate-600">{p.num_habitacion}</td>
                        <td className="p-3 text-sm flex gap-3">
                          <button 
                            onClick={() => handleAltaPaciente(p.id)}
                            className="bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1 rounded font-semibold text-xs border border-red-200"
                          >
                            Dar de Alta
                          </button>
                        </td>
                      </tr>
                    ))}
                    {pacientes.length === 0 && (
                      <tr>
                        <td colSpan="4" className="p-6 text-center text-slate-500">No hay pacientes activos actualmente.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            </div>
          )}

      </div>
    </div>
  );
}

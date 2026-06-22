import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { MdLogout, MdLocalHospital, MdFingerprint, MdSearch, MdBed } from 'react-icons/md';
import { FiCheckCircle, FiClock, FiFileText, FiUser, FiActivity, FiMapPin, FiCalendar, FiEdit3 } from 'react-icons/fi';
import { FaStethoscope } from 'react-icons/fa';
import { useDigitalPersona } from '../hooks/useDigitalPersona';

const serverIP = window.location.hostname;
const api = axios.create({ baseURL: `http://${serverIP}:8000/api` });

export default function FirmaExpress() {
  const [activeTab, setActiveTab] = useState('pendientes'); // pendientes, captura, historial

  const [pendientes, setPendientes] = useState([]);
  const [historial, setHistorial] = useState([]);
  const [tiposAtencion, setTiposAtencion] = useState([]);
  const [areas, setAreas] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [medico, setMedico] = useState(null);
  
  const [selectedFolio, setSelectedFolio] = useState(null);
  
  // Captura Form State
  const [habitacion, setHabitacion] = useState('');
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState(null);
  const [tipoAtencion, setTipoAtencion] = useState('');
  const [newPacienteAreaInline, setNewPacienteAreaInline] = useState('');
  const [nombreProcedimiento, setNombreProcedimiento] = useState('');
  const [isCreatingPaciente, setIsCreatingPaciente] = useState(false);
  const [newPacienteNombre, setNewPacienteNombre] = useState('');
  
  const now = new Date();
  const currentHora = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  
  const [fecha, setFecha] = useState(now.toISOString().slice(0, 10));
  const [hora, setHora] = useState(currentHora);
  const [procedimientoDetalle, setProcedimientoDetalle] = useState('');

  const navigate = useNavigate();
  const { status, fmdTemplate, error, devices, resetFmd, isAcquiring, startCapture } = useDigitalPersona();
  const isReady = devices?.length > 0 && !error;

  useEffect(() => {
    const medStr = localStorage.getItem('medico');
    if (!medStr) {
      navigate('/login');
      return;
    }
    const medObj = JSON.parse(medStr);
    setMedico(medObj);

    fetchPendientes(medObj.medico_id);
    fetchHistorial(medObj.medico_id);
    fetchCatalogos();
  }, [navigate]);

  const fetchPendientes = async (id) => {
    try {
      const res = await api.get(`/atenciones/pendientes/${id}`);
      setPendientes(res.data);
    } catch(e) {
      console.error(e);
    }
  };

  const fetchHistorial = async (id) => {
    if(!medico) return;
    try {
      const token = localStorage.getItem('token');
      const res = await api.get(`/atenciones/historial/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      setHistorial(res.data);
    } catch (error) { console.error("Error cargando historial", error); }
  };

  const fetchCatalogos = async () => {
    try {
      const resT = await api.get('/catalogos/tipos');
      setTiposAtencion(resT.data);
      const resA = await api.get('/catalogos/areas');
      setAreas(resA.data);
      const resP = await api.get('/pacientes');
      setPacientes(resP.data);
    } catch(e) {
      console.error(e);
    }
  };

  const handleCreatePaciente = async () => {
    if(!newPacienteNombre || !habitacion || !newPacienteAreaInline) return;
    try {
      const res = await api.post('/pacientes', {
        nombre_completo: newPacienteNombre,
        num_habitacion: habitacion,
        area_hospitalaria: newPacienteAreaInline,
        activo: true
      }, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
      const newP = res.data;
      setPacientes([...pacientes, newP]);
      setPacienteSeleccionado(newP);
      setIsCreatingPaciente(false);
      setNewPacienteNombre('');
      setNewPacienteAreaInline('');
      setNewPacienteNombre('');
    } catch(e) {
      alert("Error al crear el paciente. Intente de nuevo.");
    }
  };

  const [isProcessing, setIsProcessing] = useState(false);

  // Removido useEffect automático para firma. Ahora es manual.

  const handleFirmarUnica = async (fmd_template) => {
    if(!selectedFolio || isProcessing) return;
    setIsProcessing(true);
    try {
        const res = await api.post('/atenciones/firmar-lote', {
            huella_token: "digitalpersona", 
            fmd_template,
            folios: [selectedFolio]
        });
        alert(res.data.message);
        setSelectedFolio(null);
        fetchPendientes(medico.medico_id);
        fetchHistorial(medico.medico_id);
        resetFmd();
    } catch (err) {
        alert("Huella no válida para firmar esta atención");
        resetFmd();
    } finally {
        setIsProcessing(false);
    }
  }

  const handleCambiarTipo = async (folio, nuevoTipo) => {
    try {
      await api.put(`/atenciones/${folio}?tipo_atencion=${nuevoTipo}`);
      setPendientes(pendientes.map(p => p.folio === folio ? {...p, tipo_atencion: nuevoTipo} : p));
    } catch (err) {
      alert("Error al cambiar el tipo de atención");
    }
  };

  // CAPTURA LOGIC
  const handleHabitacionChange = (e) => {
    const val = e.target.value;
    setHabitacion(val);
    const found = pacientes.find(p => p.num_habitacion.toLowerCase() === val.toLowerCase() || p.nombre_completo.toLowerCase().includes(val.toLowerCase()));
    setPacienteSeleccionado(found || null);
    setIsCreatingPaciente(false);
  };

  const handleGuardarCaptura = async () => {
    if (!pacienteSeleccionado || !tipoAtencion || !nombreProcedimiento || !fecha || !hora) {
      alert("Faltan datos obligatorios");
      return;
    }

    try {
      const fechaRealizacionStr = `${fecha}T${hora}:00`;
      const token = localStorage.getItem('token');
      
      const res = await api.post('/atenciones/pre-captura', {
        medico_id: medico.medico_id, // Hardcoded to current doctor
        paciente_id: pacienteSeleccionado.id,
        habitacion_capturada: habitacion,
        tipo_atencion: tipoAtencion,
        nombre_procedimiento: nombreProcedimiento,
        fecha_realizacion: fechaRealizacionStr,
        procedimiento_detalle: procedimientoDetalle
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert(`Registro creado con éxito. Ya puedes firmarlo en la pestaña de Pendientes.`);
      
      // Reset form
      setHabitacion('');
      setPacienteSeleccionado(null);
      setTipoAtencion('');
      setNombreProcedimiento('');
      setProcedimientoDetalle('');
      
      // Fetch new list and switch tabs
      fetchPendientes(medico.medico_id);
      fetchHistorial(medico.medico_id);
      setActiveTab('pendientes');

    } catch (error) {
      if (error.response && error.response.status === 400) {
        alert(`ERROR DUPLICADO: ${error.response.data.detail}`);
      } else {
        alert("Error al guardar el registro");
      }
    }
  };

  if(!medico) return null;

  const sidebarItems = [
    { id: 'pendientes', label: 'Atenciones Pendientes', icon: <FiActivity /> },
    { id: 'captura', label: 'Nueva Captura Manual', icon: <FiFileText /> },
    { id: 'historial', label: 'Historial de Firmadas', icon: <FiClock /> }
  ];

  return (
    <div className="flex w-full h-full">
      {/* Left Sidebar (Sub-menu) */}
      <div className="w-64 bg-white border-r border-slate-200 flex flex-col shadow-sm z-10 overflow-y-auto">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Menú Médico</h2>
        </div>
        
        {/* Doctor Profile Widget */}
        <div className="p-6 border-b border-slate-100 flex flex-col items-center text-center bg-white">
          <div className="w-28 h-28 rounded-full overflow-hidden mb-4 border-4 border-white shadow-lg bg-slate-100 flex items-center justify-center">
             {medico.foto_url ? (
               <img src={`http://${serverIP}:8000${medico.foto_url}`} alt="Perfil Médico" className="w-full h-full object-cover" />
             ) : (
               <FaStethoscope className="text-4xl text-slate-300" />
             )}
          </div>
          <h3 className="font-bold text-slate-800 text-[13px] tracking-wide leading-tight px-2 uppercase">
             {medico.medico_id} - {medico.nombre_completo}
          </h3>
          <div className="mt-3 bg-red-500/90 text-white text-[11px] font-bold px-3 py-1 rounded shadow-sm tracking-widest uppercase">
             {medico.especialidad || 'MÉDICO'}
          </div>
        </div>

        <ul className="flex-1 py-4">
          {sidebarItems.map(item => (
            <li key={item.id}>
              <button
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-6 py-3 text-left transition-colors font-medium border-l-4 ${
                  activeTab === item.id 
                    ? 'border-hes-blue-main bg-blue-50/50 text-hes-blue-main' 
                    : 'border-transparent text-slate-600 hover:bg-slate-50 hover:text-hes-blue-main'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
                {item.id === 'pendientes' && pendientes.length > 0 && (
                  <span className="ml-auto bg-orange-500 text-white text-xs px-2 py-0.5 rounded-full">{pendientes.length}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 bg-slate-50 overflow-y-auto p-8">
        <div className="max-w-5xl mx-auto w-full">
          <div className="flex justify-between items-center mb-6 border-b pb-4 border-slate-200">
            <h1 className="text-2xl font-bold text-slate-800">
              {sidebarItems.find(i => i.id === activeTab)?.label}
            </h1>
            <button 
              onClick={() => {
                fetchPendientes(medico.medico_id);
                fetchHistorial(medico.medico_id);
              }}
              className="text-sm font-bold text-hes-blue-main hover:underline flex items-center gap-1 bg-blue-50 px-3 py-1 rounded-full"
            >
              <FiActivity /> Refrescar
            </button>
          </div>

          {activeTab === 'pendientes' && (
            <>
              {pendientes.length === 0 ? (
                  <div className="bg-white rounded-xl shadow-sm p-12 text-center border border-slate-100 flex flex-col items-center">
                      <FiCheckCircle className="text-green-500 text-6xl mb-4" />
                      <h3 className="text-xl font-semibold text-slate-700">Todo al día</h3>
                      <p className="text-slate-500">No tienes atenciones pendientes por firmar en este momento.</p>
                  </div>
              ) : (
                  <div className="space-y-4">
                      {pendientes.map(p => (
                          <div key={p.folio} className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex justify-between items-center hover:border-blue-200 transition">
                              <div className="flex-1">
                                  <div className="flex items-center gap-3 mb-2">
                                      <select 
                                        value={p.tipo_atencion} 
                                        onChange={(e) => handleCambiarTipo(p.folio, e.target.value)}
                                        className="bg-blue-50 text-blue-800 text-sm font-bold px-2 py-1 rounded border border-blue-200 focus:outline-none"
                                      >
                                        {tiposAtencion.map(t => (
                                          <option key={t.id} value={t.nombre}>{t.nombre}</option>
                                        ))}
                                      </select>
                                      <span className="text-slate-500 text-sm">Folio: {p.folio}</span>
                                  </div>
                                  <h3 className="font-bold text-lg text-slate-800">{p.paciente.nombre_completo} <span className="text-slate-400 font-normal text-sm ml-2">Hab: {p.paciente.num_habitacion}</span></h3>
                                  
                                  <div className="text-sm text-slate-600 mt-2">
                                    <span className="font-semibold text-slate-700">{p.nombre_procedimiento}</span> - {p.area_hospitalaria}
                                  </div>
                                  
                                  <div className="flex items-center gap-2 mt-3 text-xs text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-100 w-fit">
                                    <FiUser /> Capturado por: {p.creador ? p.creador.username : 'Ti mismo (Autocaptura)'}
                                  </div>
                              </div>
                              <div className="text-right text-sm text-slate-500 bg-slate-50 p-4 rounded-xl border border-slate-100 flex flex-col items-end gap-2">
                                  <div className="text-right">
                                    <p className="font-semibold text-slate-700 flex items-center gap-1 justify-end"><FiClock /> {new Date(p.fecha_realizacion).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
                                    <p>{new Date(p.fecha_realizacion).toLocaleDateString()}</p>
                                  </div>
                                  {selectedFolio === p.folio ? (
                                    <div className="mt-2 flex flex-col gap-2">
                                      {fmdTemplate ? (
                                        <>
                                          <button 
                                            onClick={() => handleFirmarUnica(fmdTemplate)}
                                            disabled={isProcessing}
                                            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded shadow-sm text-xs font-bold flex items-center justify-center gap-1 transition-colors"
                                          >
                                            <FiCheckCircle className="text-lg"/> Confirmar Firma
                                          </button>
                                          <button 
                                            onClick={resetFmd}
                                            className="text-slate-500 hover:text-slate-700 text-[10px] font-semibold underline"
                                          >
                                            Re-escanear huella
                                          </button>
                                        </>
                                      ) : (
                                        <div className="flex flex-col items-center gap-1">
                                          <span className="text-xs text-slate-600">{status}</span>
                                          {!isAcquiring && (
                                            <button 
                                              onClick={startCapture}
                                              className="bg-hes-blue-main hover:bg-[#003870] text-white px-3 py-1.5 rounded shadow-sm text-xs font-bold transition-colors"
                                            >
                                              Capturar Huella
                                            </button>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  ) : (
                                    <button 
                                      onClick={() => setSelectedFolio(p.folio)}
                                      className="mt-2 bg-hes-blue-main hover:bg-blue-800 text-white px-4 py-2 rounded shadow-sm text-xs font-bold flex items-center justify-center gap-1 transition-colors"
                                    >
                                      <MdFingerprint className="text-lg"/> Preparar Firma
                                    </button>
                                  )}
                              </div>
                          </div>
                      ))}

                      <div 
                        className={`w-full ${selectedFolio && isReady ? (fmdTemplate ? 'bg-hes-green' : 'bg-hes-blue-main') : 'bg-slate-400 cursor-not-allowed'} text-white text-lg font-semibold py-4 rounded-xl shadow-md transition-colors flex justify-center items-center gap-2 mt-8 relative cursor-default`}
                      >
                          <MdFingerprint className={`text-3xl transition-all duration-300 ${selectedFolio && isReady && !fmdTemplate ? 'animate-pulse drop-shadow-md' : ''}`} /> 
                          <span>{!selectedFolio ? 'Selecciona "Preparar Firma" en una atención para activar el lector' : (!isReady ? (error || 'Buscando lector...') : (fmdTemplate ? 'Huella lista. Presione "Confirmar Firma"' : `Coloque su huella para el folio ${selectedFolio}`)) }</span>
                      </div>
                  </div>
              )}
            </>
          )}

          {activeTab === 'historial' && (
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100">
               {historial.length === 0 ? (
                   <p className="text-center text-slate-500 py-8">No hay atenciones firmadas aún.</p>
               ) : (
                   <div className="space-y-4">
                      {historial.map(h => (
                        <div key={h.folio} className="border p-4 rounded-lg flex justify-between items-center bg-slate-50">
                            <div>
                                <p className="font-bold text-slate-800">{h.paciente.nombre_completo}</p>
                                <p className="text-sm text-slate-600">{h.nombre_procedimiento} - {h.tipo_atencion}</p>
                                <p className="text-xs text-slate-500 mt-1">Folio: {h.folio} | Firmado: {new Date(h.fecha_firma).toLocaleString()}</p>
                            </div>
                            <div>
                                    <button 
                                      onClick={() => window.open(`http://${serverIP}:8000/api/atenciones/${h.folio}/pdf`, '_blank')}
                                      className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-semibold shadow-sm flex items-center gap-2 transition"
                                    >
                                      <FiFileText /> Imprimir Comprobante
                                    </button>
                                
                            </div>
                        </div>
                      ))}
                   </div>
               )}
            </div>
          )}

          {activeTab === 'captura' && (
            <div className="flex flex-col gap-6">
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
                    <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 font-medium text-blue-900">
                      Paciente Actual: {pacienteSeleccionado.nombre_completo} (Hab: {pacienteSeleccionado.num_habitacion})
                    </div>
                  ) : habitacion.length > 0 ? (
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                      {!isCreatingPaciente ? (
                         <div className="flex flex-col gap-2">
                            <span className="text-orange-800 font-medium">No se encontró paciente con ese dato.</span>
                            <button onClick={() => setIsCreatingPaciente(true)} className="flex items-center gap-1 text-sm font-bold text-orange-700 hover:text-orange-900 w-max">
                               + Ingresar paciente nuevo a esta habitación
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
                      Ingrese el número de habitación (ej. 101) o nombre para encontrar al paciente.
                    </div>
                  )}
                </div>
                <div className="w-48 bg-slate-50 rounded-xl border flex flex-col items-center justify-center p-6">
                  <MdBed className="text-blue-600 text-3xl mb-2" />
                  <p className="text-slate-500 text-sm">Habitación</p>
                  <p className="text-4xl font-bold text-[#1a2f4c]">{habitacion || '---'}</p>
                </div>
              </section>

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
                      <option value="">Selecciona el Tipo...</option>
                      {tiposAtencion.map(t => (
                        <option key={t.id} value={t.nombre}>{t.nombre}</option>
                      ))}
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

              <section className="flex gap-6">
                <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex-1">
                   <h2 className="text-lg font-semibold text-blue-800 flex items-center gap-2 mb-4"><FiCalendar /> 3. Fecha y Hora</h2>
                   <div className="grid grid-cols-2 gap-4 mb-6">
                     <div>
                       <label className="block text-sm font-semibold text-slate-700 mb-1"><FiCalendar className="inline mr-1"/> Fecha</label>
                       <input 
                          type="date" 
                          className="w-full border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-600"
                          value={fecha}
                          onChange={e => setFecha(e.target.value)}
                        />
                     </div>
                     <div>
                       <label className="block text-sm font-semibold text-slate-700 mb-1"><FiClock className="inline mr-1"/> Hora</label>
                       <input 
                          type="time" 
                          className="w-full border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-600"
                          value={hora}
                          onChange={e => setHora(e.target.value)}
                        />
                     </div>
                   </div>
                   <div className="bg-blue-50 border-l-4 border-blue-500 p-4 text-sm text-blue-800 rounded-r-lg mt-8">
                     <span className="font-bold">Médico Responsable:</span> {medico.nombre_completo} (Autocaptura)
                   </div>
                </div>
                
                <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex-1">
                   <h2 className="text-lg font-semibold text-blue-800 flex items-center gap-2 mb-4"><FiEdit3 /> 4. Detalle (Opcional)</h2>
                   <textarea 
                      className="w-full h-32 border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-600 resize-none"
                      placeholder="Describe brevemente el procedimiento realizado, hallazgos o notas clínicas relevantes..."
                      maxLength="1000"
                      value={procedimientoDetalle}
                      onChange={e => setProcedimientoDetalle(e.target.value)}
                    ></textarea>
                    <div className="text-right text-xs text-slate-400 mt-1">{procedimientoDetalle.length}/1000</div>
                </div>
              </section>

              <button 
                onClick={handleGuardarCaptura}
                className="w-full bg-hes-blue-main hover:bg-[#003870] text-white text-lg font-semibold py-4 rounded-xl shadow-md transition-colors flex justify-center items-center gap-2"
              >
                <FiFileText /> Guardar Pre-Captura Manual
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

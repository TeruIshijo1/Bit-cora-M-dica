// Imports and basic setup...
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { FiUserPlus, FiAlertCircle, FiCheckCircle, FiUsers, FiTrash2, FiLock, FiCamera, FiBarChart2, FiDatabase, FiList, FiUser, FiActivity, FiFileText, FiFolder, FiUpload, FiSearch, FiEdit } from 'react-icons/fi';
import { MdFingerprint } from 'react-icons/md';
import { useDigitalPersona } from '../hooks/useDigitalPersona';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const serverIP = window.location.hostname;
const api = axios.create({ baseURL: `http://${serverIP}:8000/api` });

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard'); 
  const [rolActual, setRolActual] = useState(localStorage.getItem('rol'));
  
  const { status: readerStatus, fmdTemplate, error, devices, resetFmd, startCapture, isAcquiring } = useDigitalPersona();
  const isReady = devices?.length > 0 && !error;
  
  const [formData, setFormData] = useState({ numero_empleado: '', nombre_completo: '', especialidad: '', cedula: '' });
  const [foto, setFoto] = useState(null);
  const [fotoPreview, setFotoPreview] = useState(null);
  const fileInputRef = useRef(null);
  const [status, setStatus] = useState(null);
  
  const [medicos, setMedicos] = useState([]);
  const [areas, setAreas] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [newArea, setNewArea] = useState('');
  const [newTipo, setNewTipo] = useState('');
  const [usuarios, setUsuarios] = useState([]);
  const [newUser, setNewUser] = useState({ username: '', password: '', rol: '' });
  
  // Edit Medico State
  const [editingMedico, setEditingMedico] = useState(null);
  const [editFormData, setEditFormData] = useState({ numero_empleado: '', nombre_completo: '', especialidad: '', cedula: '' });
  const [editFoto, setEditFoto] = useState(null);
  const [editFotoPreview, setEditFotoPreview] = useState(null);
  const editFileInputRef = useRef(null);
  
  const [stats, setStats] = useState(null);
  const [pacientes, setPacientes] = useState([]);
  const [newPacienteNombre, setNewPacienteNombre] = useState('');
  const [newPacienteHabitacion, setNewPacienteHabitacion] = useState('');
  const [newPacienteArea, setNewPacienteArea] = useState('');
  
  // Edit Paciente State
  const [editingPaciente, setEditingPaciente] = useState(null);
  const [editPacienteForm, setEditPacienteForm] = useState({ nombre_completo: '', num_habitacion: '', area_hospitalaria: '' });
  
  // Historial global
  const [historialGlobal, setHistorialGlobal] = useState([]);
  const [filterText, setFilterText] = useState('');
  const [filterArea, setFilterArea] = useState('');
  const [filterDate, setFilterDate] = useState('');

  // Escaneos RH
  const [escaneos, setEscaneos] = useState([]);
  const [uploadTitulo, setUploadTitulo] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [filterEscaneos, setFilterEscaneos] = useState('');
  const escaneoFileRef = useRef(null);

  useEffect(() => {
    fetchMedicos();
    fetchCatalogos();
    if(rolActual === 'admin' || rolActual === 'rh' || rolActual === 'sistemas') {
      fetchUsuarios();
      fetchStats();
      fetchPacientes();
      fetchHistorialGlobal();
      fetchEscaneos();
    }
  }, [rolActual]);

  const getToken = () => localStorage.getItem('token');

  const fetchStats = async () => {
    try {
      const res = await api.get('/stats', { headers: { Authorization: `Bearer ${getToken()}` } });
      setStats(res.data);
    } catch(e) { console.error("Error fetching stats", e); }
  };

  const fetchPacientes = async () => {
    try {
      const res = await api.get('/pacientes');
      setPacientes(res.data);
    } catch(e) { console.error("Error fetching pacientes", e); }
  };

  const fetchHistorialGlobal = async () => {
    try {
      const res = await api.get('/atenciones/todas', { headers: { Authorization: `Bearer ${getToken()}` } });
      setHistorialGlobal(res.data);
    } catch(e) { console.error("Error fetching historial", e); }
  };

  const fetchEscaneos = async () => {
    try {
      const res = await api.get('/escaneos', { headers: { Authorization: `Bearer ${getToken()}` } });
      setEscaneos(res.data);
    } catch(e) { console.error("Error fetching escaneos", e); }
  };

  const handleUploadEscaneo = async (e) => {
    e.preventDefault();
    if(!uploadTitulo || !uploadFile) return;

    if (uploadFile.size > 5 * 1024 * 1024) {
      alert("El archivo excede el tamaño máximo permitido de 5MB.");
      return;
    }

    try {
      const fd = new FormData();
      fd.append('titulo', uploadTitulo);
      fd.append('archivo', uploadFile);
      await api.post('/escaneos', fd, { headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${getToken()}` } });
      setUploadTitulo('');
      setUploadFile(null);
      if(escaneoFileRef.current) escaneoFileRef.current.value = '';
      fetchEscaneos();
      alert("Archivo subido correctamente");
    } catch(err) {
      if (err.response && err.response.data && err.response.data.detail) {
        alert(`Error al subir: ${err.response.data.detail}`);
      } else {
        alert("Error al subir archivo");
      }
    }
  };

  const handleDeleteEscaneo = async (id) => {
    if(!window.confirm("¿Seguro que deseas eliminar este archivo?")) return;
    try {
      await api.delete(`/escaneos/${id}`, { headers: { Authorization: `Bearer ${getToken()}` } });
      fetchEscaneos();
    } catch(err) { alert("Error al eliminar archivo"); }
  };

  const handleRenameEscaneo = async (id, currentTitle) => {
    const newTitle = window.prompt("Nuevo título:", currentTitle);
    if(newTitle && newTitle !== currentTitle) {
      try {
        await api.put(`/escaneos/${id}`, {titulo: newTitle}, { headers: { Authorization: `Bearer ${getToken()}` } });
        fetchEscaneos();
      } catch(err) { alert("Error al renombrar"); }
    }
  };

  const handleAltaPaciente = async (id) => {
    try {
      await api.put(`/pacientes/${id}/alta`, {}, { headers: { Authorization: `Bearer ${getToken()}` } });
      fetchPacientes();
    } catch(e) { alert("Error al dar de alta al paciente"); }
  };

  const fetchMedicos = async () => {
    try {
      const res = await api.get('/medicos'); 
      setMedicos(res.data);
    } catch(e) { console.error("Error fetching medicos", e); }
  };

  const fetchCatalogos = async () => {
    try {
      const resA = await api.get('/catalogos/areas');
      setAreas(resA.data);
      const resT = await api.get('/catalogos/tipos');
      setTipos(resT.data);
    } catch(e) { console.error("Error fetching catalogos", e); }
  };

  const fetchUsuarios = async () => {
    try {
      const res = await api.get('/usuarios', { headers: { Authorization: `Bearer ${getToken()}` } });
      setUsuarios(res.data);
    } catch(e) { console.error(e); }
  };

  const handleAddArea = async () => {
    if(!newArea.trim()) return;
    try {
      await api.post('/catalogos/areas', { nombre: newArea, activo: true }, { headers: { Authorization: `Bearer ${getToken()}` } });
      setNewArea('');
      fetchCatalogos();
    } catch(e) { alert("Error al agregar area"); }
  };

  const handleAddTipo = async () => {
    if(!newTipo.trim()) return;
    try {
      await api.post('/catalogos/tipos', { nombre: newTipo, activo: true }, { headers: { Authorization: `Bearer ${getToken()}` } });
      setNewTipo('');
      fetchCatalogos();
    } catch(e) { alert("Error al agregar tipo"); }
  };

  const handleAddUser = async () => {
    if(!newUser.username || !newUser.password || !newUser.rol) return;
    try {
      await api.post('/usuarios', newUser, { headers: { Authorization: `Bearer ${getToken()}` } });
      setNewUser({ username: '', password: '', rol: '' });
      fetchUsuarios();
      alert("Usuario creado exitosamente");
    } catch(e) { alert("Error al crear usuario."); }
  };

  const handleExportExcel = async () => {
    try {
      const response = await api.get('/atenciones/exportar', { 
        headers: { Authorization: `Bearer ${getToken()}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'atenciones_export.xlsx');
      document.body.appendChild(link);
      link.click();
    } catch (e) { alert("Error al exportar a Excel"); }
  };

  const handleDeleteUser = async (id) => {
    if(!window.confirm("¿Estás seguro de eliminar este usuario? Esta acción no se puede deshacer.")) return;
    try {
      await api.delete(`/usuarios/${id}`, { headers: { Authorization: `Bearer ${getToken()}` } });
      fetchUsuarios();
    } catch(e) {
      alert("Error al eliminar usuario o no tienes permisos.");
    }
  };

  const handleDownloadBackup = async () => {
    try {
      const response = await api.get('/backup', { 
        headers: { Authorization: `Bearer ${getToken()}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `backup_hes.db`);
      document.body.appendChild(link);
      link.click();
    } catch(e) { alert("Error al descargar respaldo"); }
  };

  const handleFotoChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFoto(e.target.files[0]);
      setFotoPreview(URL.createObjectURL(e.target.files[0]));
    }
  };

  const handleRegister = async () => {
    if (!formData.numero_empleado || !formData.nombre_completo || !formData.especialidad || !formData.cedula) {
      setStatus({ type: 'error', text: 'Por favor llene los campos.' }); return;
    }
    if (!fmdTemplate) {
      setStatus({ type: 'error', text: 'Debe escanear la huella.' }); return;
    }
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('numero_empleado', formData.numero_empleado);
      formDataToSend.append('nombre_completo', formData.nombre_completo);
      formDataToSend.append('especialidad', formData.especialidad);
      formDataToSend.append('cedula', formData.cedula);
      formDataToSend.append('fmd_template', fmdTemplate);
      if (foto) formDataToSend.append('foto', foto);

      await api.post('/medicos', formDataToSend, { headers: { 'Content-Type': 'multipart/form-data' } });
      setStatus({ type: 'success', text: 'Médico registrado exitosamente.' });
      setFormData({ numero_empleado: '', nombre_completo: '', especialidad: '', cedula: '' });
      setFoto(null); setFotoPreview(null); resetFmd(); fetchMedicos();
      setTimeout(() => setStatus(null), 3000);
    } catch (err) {
      setStatus({ type: 'error', text: 'Error al registrar médico.' });
      resetFmd();
    }
  };

  const toggleMedicoStatus = async (id, currentStatus) => {
    try {
      await api.put(`/medicos/${id}?activo=${!currentStatus}`, {}, { headers: { Authorization: `Bearer ${getToken()}` } });
      fetchMedicos();
    } catch (err) { alert("Error al cambiar estatus"); }
  };

  const handleCreatePaciente = async () => {
    if(!newPacienteNombre || !newPacienteHabitacion || !newPacienteArea) {
      alert("Ingrese nombre, habitación y área hospitalaria"); return;
    }
    try {
      await api.post('/pacientes', {
        nombre_completo: newPacienteNombre,
        num_habitacion: newPacienteHabitacion,
        area_hospitalaria: newPacienteArea
      }, { headers: { Authorization: `Bearer ${getToken()}` } });
      setNewPacienteNombre('');
      setNewPacienteHabitacion('');
      setNewPacienteArea('');
      fetchPacientes();
    } catch(err) {
      alert("Error al registrar paciente");
    }
  };

  const openEditPacienteModal = (p) => {
    setEditingPaciente(p.id);
    setEditPacienteForm({
      nombre_completo: p.nombre_completo,
      num_habitacion: p.num_habitacion,
      area_hospitalaria: p.area_hospitalaria || ''
    });
  };

  const handleEditPacienteSubmit = async () => {
    if(!editPacienteForm.nombre_completo || !editPacienteForm.num_habitacion) return;
    try {
      await api.put(`/pacientes/${editingPaciente}`, editPacienteForm, { headers: { Authorization: `Bearer ${getToken()}` } });
      setEditingPaciente(null);
      fetchPacientes();
    } catch(err) {
      alert("Error al actualizar paciente");
    }
  };

  const openEditModal = (m) => {
    setEditingMedico(m.id);
    setEditFormData({
      numero_empleado: m.numero_empleado || '',
      nombre_completo: m.nombre_completo || '',
      especialidad: m.especialidad || '',
      cedula: m.cedula || ''
    });
    setEditFoto(null);
    setEditFotoPreview(m.foto_url ? `http://${serverIP}:8000${m.foto_url}` : null);
  };

  const handleEditFotoChange = (e) => {
    if(e.target.files && e.target.files[0]) {
      setEditFoto(e.target.files[0]);
      setEditFotoPreview(URL.createObjectURL(e.target.files[0]));
    }
  };

  const handleEditSubmit = async () => {
    if(!editFormData.numero_empleado || !editFormData.nombre_completo || !editFormData.especialidad || !editFormData.cedula) {
      alert("Por favor complete los campos obligatorios");
      return;
    }
    const formDataToSend = new FormData();
    formDataToSend.append('numero_empleado', editFormData.numero_empleado);
    formDataToSend.append('nombre_completo', editFormData.nombre_completo);
    formDataToSend.append('especialidad', editFormData.especialidad);
    formDataToSend.append('cedula', editFormData.cedula);
    if(editFoto) formDataToSend.append('foto', editFoto);

    try {
      await api.put(`/medicos/${editingMedico}/datos`, formDataToSend, { headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${getToken()}` } });
      setEditingMedico(null);
      fetchMedicos();
    } catch(err) {
      alert("Error al actualizar datos del médico");
    }
  };

  const handleImpersonate = async (targetId, type) => {
    try {
      const res = await api.post('/auth/impersonate', { rol: type, target_id: targetId }, { headers: { Authorization: `Bearer ${getToken()}` } });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('rol', res.data.rol);
      if(type === 'medico') {
         localStorage.setItem('medico', JSON.stringify({
            medico_id: res.data.medico_id,
            nombre_completo: res.data.nombre_completo,
            especialidad: res.data.especialidad,
            cedula: res.data.cedula,
            foto_url: res.data.foto_url
         }));
         window.location.href = '/firma-express';
      } else {
         window.location.href = '/captura';
      }
    } catch(e) { alert("Error al entrar como este usuario"); }
  };

  const historialFiltrado = historialGlobal.filter(h => {
    if (filterText && !h.folio.toLowerCase().includes(filterText.toLowerCase()) && !h.paciente.nombre_completo.toLowerCase().includes(filterText.toLowerCase()) && !(h.medico && h.medico.nombre_completo.toLowerCase().includes(filterText.toLowerCase()))) return false;
    if (filterArea && h.area_hospitalaria !== filterArea) return false;
    if (filterDate && !h.fecha_realizacion.startsWith(filterDate)) return false;
    return true;
  });

  const escaneosFiltrados = escaneos.filter(e => {
    if(filterEscaneos && !e.titulo.toLowerCase().includes(filterEscaneos.toLowerCase()) && !e.nombre_archivo.toLowerCase().includes(filterEscaneos.toLowerCase())) return false;
    return true;
  });

  // Render Tabs Configuration
  const sidebarItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <FiBarChart2 /> },
    { id: 'historial', label: 'Historial Global', icon: <FiActivity /> },
    { id: 'pacientes', label: 'Pacientes', icon: <FiUser /> },
    { id: 'alta', label: 'Alta de Médicos', icon: <FiUserPlus /> },
    { id: 'directorio', label: 'Directorio', icon: <FiUsers /> },
    { id: 'escaneos', label: 'Escaneos Diarios', icon: <FiFolder /> },
    ...(rolActual === 'admin' || rolActual === 'sistemas' ? [{ id: 'catalogos', label: 'Catálogos', icon: <FiList /> }] : []),
    { id: 'usuarios', label: 'Configuración', icon: <FiLock /> }
  ];

  return (
    <div className="flex w-full h-full">
      {/* Left Sidebar (Sub-menu) */}
      <div className="w-64 bg-white border-r border-slate-200 flex flex-col shadow-sm z-10 overflow-y-auto">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Menú Principal</h2>
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
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 bg-slate-50 overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto w-full">
          
          <h1 className="text-2xl font-bold text-slate-800 mb-6 border-b pb-4 border-slate-200">
            {sidebarItems.find(i => i.id === activeTab)?.label}
          </h1>

          {activeTab === 'dashboard' && stats && (
            <div className="space-y-6">
              <div className="mb-4 flex justify-end">
                 <button onClick={handleExportExcel} className="bg-hes-green hover:bg-green-700 text-white font-bold py-2 px-4 rounded shadow-sm">
                   Exportar a Excel (XLSX)
                 </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center justify-center">
                  <h3 className="text-slate-500 font-semibold mb-2">Atenciones este Mes</h3>
                  <p className="text-5xl font-bold text-hes-blue-main">{stats.total_mes}</p>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center justify-center">
                  <h3 className="text-slate-500 font-semibold mb-2">Pendientes de Firma</h3>
                  <p className="text-5xl font-bold text-orange-500">{stats.pendientes_firma}</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                  <h3 className="text-slate-700 font-bold mb-4">Top 5 Procedimientos</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={stats.top_procedimientos} dataKey="total" nameKey="nombre" cx="50%" cy="50%" outerRadius={80} fill="#8884d8" label>
                          {stats.top_procedimientos.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                  <h3 className="text-slate-700 font-bold mb-4">Médicos Más Activos</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats.top_medicos}>
                        <XAxis dataKey="nombre" hide />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="total" fill="#003870" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'escaneos' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Formulario de Subida */}
              <div className="lg:col-span-1">
                <form onSubmit={handleUploadEscaneo} className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 sticky top-0">
                  <h3 className="text-lg font-bold text-slate-700 mb-4 border-b pb-2 flex items-center gap-2"><FiUpload /> Subir Nuevo Archivo</h3>
                  
                  <div className="mb-4">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Título / Nombre</label>
                    <input 
                      type="text" 
                      required 
                      className="w-full border border-slate-300 rounded-lg p-2" 
                      placeholder="Ej. Recetas Lunes 24" 
                      value={uploadTitulo} 
                      onChange={e => setUploadTitulo(e.target.value)} 
                    />
                  </div>
                  
                  <div className="mb-6">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Archivo (PDF, Imágenes, Excel)</label>
                    <input 
                      type="file" 
                      required 
                      ref={escaneoFileRef}
                      className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" 
                      onChange={e => setUploadFile(e.target.files[0])} 
                    />
                    <p className="text-xs text-slate-400 mt-1">Máximo 5MB</p>
                  </div>
                  
                  <button type="submit" className="w-full bg-hes-blue-main hover:bg-[#003870] text-white font-bold py-2 rounded-lg flex justify-center items-center gap-2">
                    <FiUpload /> Guardar Escaneo
                  </button>
                </form>
              </div>

              {/* Lista de Escaneos */}
              <div className="lg:col-span-2">
                <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
                  <div className="p-4 bg-slate-50 border-b border-slate-100 flex items-center gap-2">
                    <FiSearch className="text-slate-400" />
                    <input 
                      type="text" 
                      placeholder="Buscar por título o archivo..." 
                      className="w-full bg-transparent border-none focus:outline-none text-sm"
                      value={filterEscaneos}
                      onChange={e => setFilterEscaneos(e.target.value)}
                    />
                  </div>
                  <ul className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
                    {escaneosFiltrados.map(e => (
                      <li key={e.id} className="p-4 hover:bg-slate-50 flex justify-between items-center group">
                        <div className="flex items-start gap-3">
                          <div className="mt-1 text-slate-400"><FiFileText className="text-xl" /></div>
                          <div>
                            <h4 className="font-bold text-slate-800">{e.titulo}</h4>
                            <p className="text-xs text-slate-500">{e.nombre_archivo} • {new Date(e.fecha_subida).toLocaleString()}</p>
                            <p className="text-xs text-blue-600">Subido por: {e.subido_por?.username || 'Desconocido'}</p>
                          </div>
                        </div>
                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => handleRenameEscaneo(e.id, e.titulo)} className="text-slate-500 hover:text-blue-600 bg-white border border-slate-200 px-3 py-1 rounded text-xs font-semibold shadow-sm">Renombrar</button>
                          <a href={`http://${serverIP}:8000${e.ruta_archivo}`} target="_blank" rel="noreferrer" className="text-white bg-hes-blue-main hover:bg-[#003870] px-3 py-1 rounded text-xs font-semibold shadow-sm">Abrir</a>
                          <button onClick={() => handleDeleteEscaneo(e.id)} className="text-white bg-red-500 hover:bg-red-600 px-3 py-1 rounded text-xs font-semibold shadow-sm">X</button>
                        </div>
                      </li>
                    ))}
                    {escaneosFiltrados.length === 0 && (
                      <li className="p-8 text-center text-slate-500">No hay escaneos que coincidan con tu búsqueda.</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'historial' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
              <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                <h3 className="font-bold text-slate-700 flex items-center gap-2">
                  <FiActivity className="text-hes-blue-main" /> Historial de Atenciones (Global)
                </h3>
                <div className="flex gap-4">
                   <button onClick={fetchHistorialGlobal} className="text-sm font-medium text-hes-blue-main hover:underline">Refrescar</button>
                   <button onClick={handleExportExcel} className="text-sm font-bold text-green-700 hover:underline">Exportar Excel</button>
                </div>
              </div>
              
              {/* Filtros */}
              <div className="p-4 bg-white border-b border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-4">
                 <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">Buscar Paciente / Folio / Médico</label>
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
                    <label className="block text-xs font-semibold text-slate-500 mb-1">Fecha de Realización</label>
                    <input type="date" className="w-full border rounded p-2 text-sm" value={filterDate} onChange={e => setFilterDate(e.target.value)} />
                 </div>
              </div>

              <div className="overflow-x-auto p-4">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="p-3 text-sm font-semibold text-slate-600">Folio / Fecha</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Paciente / Hab</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Procedimiento / Área</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Médico</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historialFiltrado.map(h => (
                      <tr key={h.folio} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3 text-sm font-medium text-blue-700">
                          <div>{h.folio}</div>
                          <div className="text-xs text-slate-400">{new Date(h.fecha_realizacion).toLocaleDateString()}</div>
                        </td>
                        <td className="p-3 text-sm text-slate-800">
                          <div>{h.paciente.nombre_completo}</div>
                          <div className="text-xs text-slate-500">Hab: {h.habitacion_capturada}</div>
                        </td>
                        <td className="p-3 text-sm text-slate-600">
                          <div>{h.nombre_procedimiento} ({h.tipo_atencion})</div>
                          <div className="text-xs text-slate-500">{h.area_hospitalaria}</div>
                        </td>
                        <td className="p-3 text-sm text-slate-600">{h.medico ? h.medico.nombre_completo : 'N/A'}</td>
                        <td className="p-3 text-sm">
                          <div>
                            {h.ruta_archivo_firmado ? (
                                <a href={`http://${serverIP}:8000${h.ruta_archivo_firmado}`} target="_blank" rel="noreferrer" className="bg-hes-green hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-semibold shadow-sm flex items-center gap-2 w-max">
                                  <FiFileText className="inline" /> PDF
                                </a>
                            ) : (
                                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                                  h.estatus_pago === 'Pendiente de Firma' ? 'bg-orange-100 text-orange-700' : 
                                  h.estatus_pago === 'Validado para Pago' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-700'
                                }`}>
                                  {h.estatus_pago}
                                </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {historialFiltrado.length === 0 && (
                      <tr>
                        <td colSpan="5" className="p-6 text-center text-slate-500">No se encontraron registros.</td>
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
                    <input type="text" className="w-full border rounded-lg p-2" placeholder="Ej. Juan Pérez" value={newPacienteNombre} onChange={e => setNewPacienteNombre(e.target.value)} />
                  </div>
                  <div className="w-48">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Habitación</label>
                    <input type="text" className="w-full border rounded-lg p-2" placeholder="Ej. 101" value={newPacienteHabitacion} onChange={e => setNewPacienteHabitacion(e.target.value)} />
                  </div>
                  <div className="w-64">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Área Hospitalaria</label>
                    <select className="w-full border rounded-lg p-2 bg-white" value={newPacienteArea} onChange={e => setNewPacienteArea(e.target.value)}>
                      <option value="">Selecciona el Área...</option>
                      {areas.map(a => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                    </select>
                  </div>
                  <button onClick={handleCreatePaciente} className="bg-hes-blue-main text-white px-6 py-2 rounded-lg font-bold hover:bg-blue-800 transition-colors h-[42px]">
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
                      <th className="p-3 text-sm font-semibold text-slate-600">Área</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pacientes.map(p => (
                      <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3 text-sm font-semibold text-blue-700">{p.id}</td>
                        <td className="p-3 text-sm font-medium text-slate-800">{p.nombre_completo}</td>
                        <td className="p-3 text-sm text-slate-600">{p.num_habitacion}</td>
                        <td className="p-3 text-sm text-slate-600">{p.area_hospitalaria || 'No asignada'}</td>
                        <td className="p-3 text-sm flex gap-3">
                          <button onClick={() => openEditPacienteModal(p)} className="text-hes-blue-main hover:text-blue-800" title="Editar"><FiEdit /></button>
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

          {activeTab === 'alta' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
              <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-12">
                <div className="space-y-6">
                  <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">Datos del Médico</h3>
                  <div className="flex gap-6">
                    <div 
                      className="w-24 h-24 rounded-full bg-slate-100 border-2 border-dashed border-slate-300 flex items-center justify-center cursor-pointer overflow-hidden group relative"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {fotoPreview ? (
                        <img src={fotoPreview} alt="Preview" className="w-full h-full object-cover" />
                      ) : (
                        <div className="text-slate-400 flex flex-col items-center">
                          <FiCamera className="text-2xl mb-1" />
                        </div>
                      )}
                      <input type="file" hidden ref={fileInputRef} onChange={handleFotoChange} accept="image/*" />
                    </div>
                    <div className="flex-1 space-y-4">
                      <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-1">Número de Empleado / ID</label>
                        <input type="text" placeholder="Ej. EMP-0001" className="w-full border border-slate-300 rounded-lg p-3" value={formData.numero_empleado} onChange={e => setFormData({...formData, numero_empleado: e.target.value})} />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-1">Nombre Completo</label>
                        <input type="text" placeholder="Ej. Dr. Juan Pérez" className="w-full border border-slate-300 rounded-lg p-3" value={formData.nombre_completo} onChange={e => setFormData({...formData, nombre_completo: e.target.value})} />
                      </div>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Especialidad</label>
                    <input type="text" className="w-full border border-slate-300 rounded-lg p-3" value={formData.especialidad} onChange={e => setFormData({...formData, especialidad: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Cédula Profesional</label>
                    <input type="text" className="w-full border border-slate-300 rounded-lg p-3" value={formData.cedula} onChange={e => setFormData({...formData, cedula: e.target.value})} />
                  </div>
                </div>
                <div className="flex flex-col items-center justify-center bg-slate-50 p-6 rounded-xl border border-slate-200">
                  <h3 className="font-semibold text-slate-700 mb-4">Registro Biométrico</h3>
                  <div className={`w-40 h-40 rounded-full border-4 flex items-center justify-center relative mb-6 ${fmdTemplate ? 'border-hes-green bg-[#e6f4ed]' : 'border-slate-100 bg-white'}`}>
                    {isAcquiring && <div className="absolute inset-0 rounded-full border border-hes-blue-light animate-ping opacity-20"></div>}
                    <MdFingerprint className={`text-7xl ${fmdTemplate ? 'text-hes-green' : isAcquiring ? 'text-hes-blue-main animate-pulse' : 'text-slate-300'}`} />
                  </div>
                  {!isReady && !error && <div className="text-center text-slate-500 text-sm">{(readerStatus === 'Desconectado' || readerStatus === 'Iniciando...') ? 'Iniciando lector...' : readerStatus}</div>}
                  {error && <div className="text-center text-red-600 text-sm font-medium">{error}</div>}
                  {isReady && !fmdTemplate && !error && (
                    <>
                      <div className="text-center text-hes-blue-main text-sm font-medium mb-3">{readerStatus}</div>
                      {!isAcquiring && (
                        <button onClick={startCapture} className="bg-hes-blue-main hover:bg-[#003870] text-white px-6 py-2 rounded-lg text-sm font-semibold shadow-sm transition-all">Capturar Huella</button>
                      )}
                    </>
                  )}
                  {fmdTemplate && <button onClick={resetFmd} className="mt-4 text-sm text-slate-500 hover:text-slate-700 underline">Volver a capturar</button>}
                </div>
              </div>
              <div className="bg-slate-50 p-6 flex flex-col items-center gap-4 border-t border-slate-100">
                {status && <div className={`p-3 rounded text-sm w-full max-w-md text-center ${status.type === 'error' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{status.text}</div>}
                <button onClick={handleRegister} disabled={!fmdTemplate} className={`w-full max-w-md py-3 rounded-lg font-bold text-white shadow-md transition-colors ${!fmdTemplate ? 'bg-slate-400' : 'bg-hes-blue-main hover:bg-[#003870]'}`}>
                  Registrar Médico
                </button>
              </div>
            </div>
          )}

          {activeTab === 'directorio' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
               <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="p-3 text-sm font-semibold text-slate-600">Nombre</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Especialidad</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {medicos.map(m => (
                      <tr key={m.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3 text-sm font-medium text-slate-800">{m.nombre_completo}</td>
                        <td className="p-3 text-sm text-slate-600">{m.especialidad}</td>
                        <td className="p-3 text-sm flex gap-3">
                          <button onClick={() => openEditModal(m)} className="text-hes-blue-main hover:text-blue-800" title="Editar"><FiEdit /></button>
                          <button onClick={() => toggleMedicoStatus(m.id, true)} className="text-red-500 hover:text-red-700" title="Eliminar"><FiTrash2 /></button>
                          {(rolActual === 'admin' || rolActual === 'sistemas') && (
                            <button onClick={() => handleImpersonate(m.id, 'medico')} className="text-blue-500 underline text-xs">Entrar como...</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
            </div>
          )}

          {activeTab === 'catalogos' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <h3 className="text-lg font-bold text-slate-700 mb-4">Áreas Hospitalarias</h3>
                <div className="flex gap-2 mb-4">
                  <input type="text" value={newArea} onChange={e => setNewArea(e.target.value)} className="flex-1 border rounded-lg p-2" />
                  <button onClick={handleAddArea} className="bg-hes-blue-main text-white px-4 py-2 rounded-lg">Agregar</button>
                </div>
                <ul className="space-y-2 max-h-64 overflow-y-auto">
                  {areas.map(a => <li key={a.id} className="bg-slate-50 p-3 rounded-lg border">{a.nombre}</li>)}
                </ul>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <h3 className="text-lg font-bold text-slate-700 mb-4">Tipos de Atención</h3>
                <div className="flex gap-2 mb-4">
                  <input type="text" value={newTipo} onChange={e => setNewTipo(e.target.value)} className="flex-1 border rounded-lg p-2" />
                  <button onClick={handleAddTipo} className="bg-hes-blue-main text-white px-4 py-2 rounded-lg">Agregar</button>
                </div>
                <ul className="space-y-2 max-h-64 overflow-y-auto">
                  {tipos.map(t => <li key={t.id} className="bg-slate-50 p-3 rounded-lg border">{t.nombre}</li>)}
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'usuarios' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <h3 className="text-lg font-bold text-slate-700 mb-4">Añadir Usuario</h3>
                <div className="space-y-4">
                  <input type="text" placeholder="Nombre de usuario" className="w-full border p-2 rounded" value={newUser.username} onChange={e => setNewUser({...newUser, username: e.target.value})} />
                  <input type="password" placeholder="Contraseña" className="w-full border p-2 rounded" value={newUser.password} onChange={e => setNewUser({...newUser, password: e.target.value})} />
                  <select className="w-full border p-2 rounded" value={newUser.rol} onChange={e => setNewUser({...newUser, rol: e.target.value})}>
                    <option value="">Selecciona un Rol</option>
                    <option value="enfermeria">Enfermería</option>
                    {(rolActual === 'admin' || rolActual === 'sistemas') && <option value="rh">Recursos Humanos</option>}
                    {(rolActual === 'admin' || rolActual === 'sistemas') && <option value="admin">Administrador / Sistemas</option>}
                  </select>
                  <button onClick={handleAddUser} className="w-full bg-hes-blue-main hover:bg-blue-800 text-white font-bold py-2 rounded">Crear Usuario</button>
                </div>
              </div>
              <div className="flex flex-col gap-6">
                {(rolActual === 'admin' || rolActual === 'sistemas') && (
                  <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                    <h3 className="text-lg font-bold text-slate-700 mb-4">Respaldo de Base de Datos</h3>
                    <p className="text-sm text-slate-500 mb-4">Descarga una copia completa de la base de datos (SQLite) a tu computadora para seguridad y auditoría.</p>
                    <button onClick={handleDownloadBackup} className="w-full bg-slate-800 hover:bg-slate-900 text-white font-bold py-3 rounded flex justify-center items-center gap-2">
                      <FiDatabase /> Descargar Respaldo Ahora
                    </button>
                  </div>
                )}
                
                <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 flex-1">
                  <h3 className="text-lg font-bold text-slate-700 mb-4">Lista de Usuarios</h3>
                  <ul className="space-y-2">
                    {usuarios.map(u => (
                      <li key={u.id} className="bg-slate-50 p-3 rounded-lg border flex justify-between items-center text-sm">
                        <div>
                          <p className="font-bold text-slate-800">{u.username}</p>
                          <p className="text-slate-500 uppercase text-xs">{u.rol}</p>
                        </div>
                        {(rolActual === 'admin' || rolActual === 'sistemas') && (
                          <div className="flex gap-4 items-center">
                            <button onClick={() => handleImpersonate(u.id, u.rol)} className="text-blue-500 hover:underline text-xs font-semibold">Entrar como...</button>
                            {rolActual === 'sistemas' && (
                              <button onClick={() => handleDeleteUser(u.id)} className="text-red-500 hover:underline text-xs font-semibold">Eliminar</button>
                            )}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Edit Medico Modal */}
      {editingMedico && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden">
            <div className="bg-slate-50 border-b border-slate-100 p-6">
              <h3 className="text-xl font-bold text-slate-800">Editar Médico</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Número de Empleado / ID</label>
                <input type="text" className="w-full border border-slate-300 rounded-lg p-2" value={editFormData.numero_empleado} onChange={e => setEditFormData({...editFormData, numero_empleado: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Nombre Completo</label>
                <input type="text" className="w-full border border-slate-300 rounded-lg p-2" value={editFormData.nombre_completo} onChange={e => setEditFormData({...editFormData, nombre_completo: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Especialidad</label>
                <input type="text" className="w-full border border-slate-300 rounded-lg p-2" value={editFormData.especialidad} onChange={e => setEditFormData({...editFormData, especialidad: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Cédula Profesional</label>
                <input type="text" className="w-full border border-slate-300 rounded-lg p-2" value={editFormData.cedula} onChange={e => setEditFormData({...editFormData, cedula: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Actualizar Fotografía (Opcional)</label>
                <div className="flex items-center gap-4">
                  {editFotoPreview && (
                    <img src={editFotoPreview} alt="Preview" className="w-16 h-16 object-cover rounded-lg border" />
                  )}
                  <input type="file" ref={editFileInputRef} onChange={handleEditFotoChange} accept="image/*" className="text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-hes-blue-light file:text-hes-blue-main hover:file:bg-blue-100" />
                </div>
              </div>
            </div>
            <div className="bg-slate-50 border-t border-slate-100 p-6 flex justify-end gap-3">
              <button onClick={() => setEditingMedico(null)} className="px-6 py-2 rounded-lg font-semibold text-slate-600 hover:bg-slate-200 transition-colors">Cancelar</button>
              <button onClick={handleEditSubmit} className="px-6 py-2 rounded-lg font-semibold text-white bg-hes-blue-main hover:bg-[#003870] transition-colors shadow-sm">Guardar Cambios</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Paciente Modal */}
      {editingPaciente && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden">
            <div className="bg-slate-50 border-b border-slate-100 p-6">
              <h3 className="text-xl font-bold text-slate-800">Editar Paciente</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Nombre Completo</label>
                <input type="text" className="w-full border border-slate-300 rounded-lg p-2" value={editPacienteForm.nombre_completo} onChange={e => setEditPacienteForm({...editPacienteForm, nombre_completo: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Habitación</label>
                <input type="text" className="w-full border border-slate-300 rounded-lg p-2" value={editPacienteForm.num_habitacion} onChange={e => setEditPacienteForm({...editPacienteForm, num_habitacion: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Área Hospitalaria</label>
                <select className="w-full border border-slate-300 rounded-lg p-2 bg-white" value={editPacienteForm.area_hospitalaria} onChange={e => setEditPacienteForm({...editPacienteForm, area_hospitalaria: e.target.value})}>
                  <option value="">Selecciona el Área...</option>
                  {areas.map(a => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                </select>
              </div>
            </div>
            <div className="bg-slate-50 border-t border-slate-100 p-6 flex justify-end gap-3">
              <button onClick={() => setEditingPaciente(null)} className="px-6 py-2 rounded-lg font-semibold text-slate-600 hover:bg-slate-200 transition-colors">Cancelar</button>
              <button onClick={handleEditPacienteSubmit} className="px-6 py-2 rounded-lg font-semibold text-white bg-hes-blue-main hover:bg-[#003870] transition-colors shadow-sm">Guardar Cambios</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

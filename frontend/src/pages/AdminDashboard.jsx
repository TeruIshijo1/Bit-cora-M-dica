// Imports and basic setup...
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { FiUserPlus, FiAlertCircle, FiCheckCircle, FiUsers, FiTrash2, FiLock, FiCamera, FiBarChart2, FiDatabase, FiList, FiUser, FiActivity, FiFileText, FiFolder, FiUpload, FiSearch, FiEdit, FiPlusCircle } from 'react-icons/fi';
import { MdFingerprint } from 'react-icons/md';
import { useDigitalPersona } from '../hooks/useDigitalPersona';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { PatientJourneyModal } from '../components/PatientModals';

const serverIP = window.location.hostname;
const api = axios.create({ baseURL: `http://${serverIP}:8000/api` });

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const initialSchedule = {
  lunes: { activo: false, inicio: '', fin: '' },
  martes: { activo: false, inicio: '', fin: '' },
  miercoles: { activo: false, inicio: '', fin: '' },
  jueves: { activo: false, inicio: '', fin: '' },
  viernes: { activo: false, inicio: '', fin: '' },
  sabado: { activo: false, inicio: '', fin: '' },
  domingo: { activo: false, inicio: '', fin: '' }
};

const diasSemana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'];

const HorarioBuilder = ({ horario, setHorario }) => {
  const toggleDia = (dia) => {
    setHorario({ ...horario, [dia]: { ...horario[dia], activo: !horario[dia].activo } });
  };
  const handleChange = (dia, campo, valor) => {
    setHorario({ ...horario, [dia]: { ...horario[dia], [campo]: valor } });
  };

  return (
    <div className="mt-4 border border-slate-200 rounded-lg p-4 bg-slate-50 shadow-inner">
      <h3 className="font-semibold text-slate-700 mb-3 text-sm">Configurar Horario Laboral</h3>
      {diasSemana.map(dia => (
        <div key={dia} className="flex items-center gap-4 mb-2">
          <label className="flex items-center gap-2 w-28 capitalize text-sm font-medium text-slate-600">
            <input type="checkbox" checked={horario[dia]?.activo || false} onChange={() => toggleDia(dia)} className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"/>
            {dia}
          </label>
          <input type="time" disabled={!horario[dia]?.activo} value={horario[dia]?.inicio || ''} onChange={(e) => handleChange(dia, 'inicio', e.target.value)} className="border border-slate-300 rounded-md p-1.5 text-sm focus:ring-2 focus:ring-blue-500 outline-none disabled:bg-slate-200 disabled:text-slate-400 w-32" />
          <span className="text-sm font-medium text-slate-500">a</span>
          <input type="time" disabled={!horario[dia]?.activo} value={horario[dia]?.fin || ''} onChange={(e) => handleChange(dia, 'fin', e.target.value)} className="border border-slate-300 rounded-md p-1.5 text-sm focus:ring-2 focus:ring-blue-500 outline-none disabled:bg-slate-200 disabled:text-slate-400 w-32" />
        </div>
      ))}
    </div>
  );
};

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
  
  const [bajoContrato, setBajoContrato] = useState(false);
  const [horarioLaboral, setHorarioLaboral] = useState(initialSchedule);
  const [esAyudante, setEsAyudante] = useState(false);
  const [medicoAsignadoId, setMedicoAsignadoId] = useState('');
  
  const [medicoHuellaFilter, setMedicoHuellaFilter] = useState('todos');
  
  const [medicos, setMedicos] = useState([]);
  const [areas, setAreas] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [tiposAtencion, setTiposAtencion] = useState([]);
  const [notaModal, setNotaModal] = useState({ open: false, folio: '', text: '' });
  const [newArea, setNewArea] = useState('');
  const [newTipo, setNewTipo] = useState('');
  
  // Search state
  const [medicoSearchTerm, setMedicoSearchTerm] = useState('');
  const [usuarios, setUsuarios] = useState([]);
  const [newUser, setNewUser] = useState({ username: '', password: '', rol: '' });
  
  // Edit Medico State
  const [editingMedico, setEditingMedico] = useState(null);
  const [editFormData, setEditFormData] = useState({ numero_empleado: '', nombre_completo: '', especialidad: '', cedula: '' });
  const [editFoto, setEditFoto] = useState(null);
  const [editFotoPreview, setEditFotoPreview] = useState(null);
  const [editBajoContrato, setEditBajoContrato] = useState(false);
  const [editHorarioLaboral, setEditHorarioLaboral] = useState(initialSchedule);
  
  const [isHuellaModalOpen, setIsHuellaModalOpen] = useState(false);
  const [medicoParaHuella, setMedicoParaHuella] = useState(null);
  const editFileInputRef = useRef(null);
  
  const [stats, setStats] = useState(null);
  const [pacientes, setPacientes] = useState([]);
  const [auditoriaLogs, setAuditoriaLogs] = useState([]);
  const [cleanModal, setCleanModal] = useState({ open: false, atenciones: true, notas: true, traslados: true, pacientes: true });
  const [newPacienteNombre, setNewPacienteNombre] = useState('');
  const [newPacienteHabitacion, setNewPacienteHabitacion] = useState('');
  const [newPacienteArea, setNewPacienteArea] = useState('');
  
  const [trasladosModal, setTrasladosModal] = useState({ open: false, paciente: null, traslados: [] });
  const [journeyModal, setJourneyModal] = useState({ open: false, paciente: null });
  
  // Edit Paciente State
  const [editingPaciente, setEditingPaciente] = useState(null);
  const [editPacienteForm, setEditPacienteForm] = useState({ nombre_completo: '', num_habitacion: '', area_hospitalaria: '', codigo_barras: '' });
  
  // Historial global
  const [historialGlobal, setHistorialGlobal] = useState([]);
  const [filterText, setFilterText] = useState('');
  const [filterArea, setFilterArea] = useState('');
  const [filterDateStart, setFilterDateStart] = useState('');
  const [filterDateEnd, setFilterDateEnd] = useState('');

  // Escaneos RH
  const [escaneos, setEscaneos] = useState([]);
  const [uploadTitulo, setUploadTitulo] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [filterEscaneos, setFilterEscaneos] = useState('');
  const escaneoFileRef = useRef(null);

  const formatSchedule = (jsonStr) => {
    if (!jsonStr) return '';
    if (!jsonStr.startsWith('{')) return jsonStr;
    try {
      const h = JSON.parse(jsonStr);
      const activeDays = Object.keys(h).filter(d => h[d]?.activo);
      if (activeDays.length === 0) return 'Sin horario';
      return activeDays.map(d => `${d.substring(0,3).toUpperCase()} ${h[d].inicio}-${h[d].fin}`).join(', ');
    } catch(e) {
      return jsonStr;
    }
  };

  useEffect(() => {
    fetchMedicos();
    fetchCatalogos();
    if (rolActual === 'admin' || rolActual === 'sistemas' || rolActual === 'rh' || rolActual === 'director') {
      fetchUsuarios();
      fetchStats();
      fetchPacientes();
      fetchHistorialGlobal();
      fetchEscaneos();
      fetchAuditoria();
    }
  }, [rolActual]);

  const getToken = () => localStorage.getItem('token');

  const fetchStats = async () => {
    try {
      const res = await api.get('/analytics', { headers: { Authorization: `Bearer ${getToken()}` } });
      setStats(res.data);
    } catch(e) { console.error("Error fetching stats", e); }
  };

  const fetchAuditoria = async () => {
    try {
      const res = await api.get('/auditoria', { headers: { Authorization: `Bearer ${getToken()}` } });
      setAuditoriaLogs(res.data);
    } catch(e) { console.error("Error fetching auditoria", e); }
  };

  const fetchPacientes = async () => {
    try {
      const res = await api.get('/pacientes');
      setPacientes(res.data);
    } catch(e) { console.error("Error fetching pacientes", e); }
  };

  const openTrasladosModal = async (paciente) => {
    try {
      const res = await api.get(`/pacientes/${paciente.id}/traslados`, { headers: { Authorization: `Bearer ${getToken()}` } });
      setTrasladosModal({ open: true, paciente, traslados: res.data });
    } catch(e) { console.error("Error fetching traslados", e); }
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

  const handleReaperturar = async (folio) => {
    try {
      await api.put(`/atenciones/${folio}/reaperturar`, {}, { headers: { Authorization: `Bearer ${getToken()}` } });
      fetchHistorialGlobal();
      alert("Registro reaperturado exitosamente. Ahora puede ser editado/firmado.");
    } catch(e) {
      alert("Error al reaperturar");
    }
  };

  const handleAddNota = async () => {
    if(!notaModal.text.trim()) return;
    try {
      await api.post(`/atenciones/${notaModal.folio}/notas`, { nota: notaModal.text }, { headers: { Authorization: `Bearer ${getToken()}` } });
      setNotaModal({ open: false, folio: '', text: '' });
      fetchHistorialGlobal();
    } catch(e) {
      if (e.response && e.response.status === 400) alert(e.response.data.detail);
      else alert("Error al añadir nota");
    }
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

  const handleDeleteArea = async (id) => {
    if(!window.confirm("¿Estás seguro de eliminar esta Área? Ya no aparecerá en las nuevas listas.")) return;
    try {
      await api.delete(`/catalogos/areas/${id}`, { headers: { Authorization: `Bearer ${getToken()}` } });
      fetchCatalogos();
    } catch(e) { alert("Error al eliminar área"); }
  };

  const handleDeleteTipo = async (id) => {
    if(!window.confirm("¿Estás seguro de eliminar este Tipo de Atención? Ya no aparecerá en las nuevas listas.")) return;
    try {
      await api.delete(`/catalogos/tipos/${id}`, { headers: { Authorization: `Bearer ${getToken()}` } });
      fetchCatalogos();
    } catch(e) { alert("Error al eliminar tipo"); }
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
      const query = new URLSearchParams();
      if (filterDateStart) query.append('start_date', filterDateStart);
      if (filterDateEnd) query.append('end_date', filterDateEnd);
      const response = await api.get(`/atenciones/exportar?${query.toString()}`, { 
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

  const handleChangePassword = async (id, rolTarget) => {
    const newPass = window.prompt("Introduce la nueva contraseña para este usuario:");
    if (!newPass) return;
    try {
      await api.put(`/usuarios/${id}/password`, { new_password: newPass }, { headers: { Authorization: `Bearer ${getToken()}` } });
      alert("Contraseña actualizada exitosamente.");
    } catch (e) {
      if(e.response && e.response.data && e.response.data.detail) alert("Error: " + e.response.data.detail);
      else alert("Error al cambiar la contraseña.");
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

  const handleCleanDatabase = async () => {
    try {
      const response = await api.post('/admin/clean_records', {
        clean_atenciones: cleanModal.atenciones,
        clean_notas: cleanModal.notas,
        clean_traslados: cleanModal.traslados,
        clean_pacientes: cleanModal.pacientes
      }, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      alert(response.data.message);
      setCleanModal({ ...cleanModal, open: false });
      window.location.reload();
    } catch(e) {
      alert("Error limpiando la base de datos: " + (e.response?.data?.detail || e.message));
    }
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
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('numero_empleado', formData.numero_empleado);
      formDataToSend.append('nombre_completo', formData.nombre_completo);
      formDataToSend.append('especialidad', formData.especialidad);
      formDataToSend.append('cedula', formData.cedula);
      if (fmdTemplate) formDataToSend.append('fmd_template', fmdTemplate);
      if (foto) formDataToSend.append('foto', foto);
      formDataToSend.append('bajo_contrato', bajoContrato);
      if (bajoContrato) {
        formDataToSend.append('horario_laboral', JSON.stringify(horarioLaboral));
      }
      formDataToSend.append('es_ayudante', esAyudante);
      if (esAyudante && medicoAsignadoId) {
        formDataToSend.append('medico_asignado_id', medicoAsignadoId);
      }

      await api.post('/medicos', formDataToSend, { headers: { 'Content-Type': 'multipart/form-data' } });
      setStatus({ type: 'success', text: 'Médico registrado exitosamente.' });
      setFormData({ numero_empleado: '', nombre_completo: '', especialidad: '', cedula: '' });
      setBajoContrato(false);
      setHorarioLaboral(initialSchedule);
      setEsAyudante(false);
      setMedicoAsignadoId('');
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
        area_hospitalaria: newPacienteArea,
        codigo_barras: newPacienteCodigo || null
      }, { headers: { Authorization: `Bearer ${getToken()}` } });
      setNewPacienteNombre('');
      setNewPacienteHabitacion('');
      setNewPacienteArea('');
      setNewPacienteCodigo('');
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
      area_hospitalaria: p.area_hospitalaria || '',
      codigo_barras: p.codigo_barras || ''
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

  const closeEditModal = () => {
    setEditingMedico(null);
    setEditFoto(null);
    setEditFotoPreview(null);
  };

  const openHuellaModal = (medico) => {
    setMedicoParaHuella(medico);
    resetFmd();
    setIsHuellaModalOpen(true);
  };

  const closeHuellaModal = () => {
    setMedicoParaHuella(null);
    setIsHuellaModalOpen(false);
    resetFmd();
  };

  const handleSaveHuella = async () => {
    if (!fmdTemplate) {
      alert("Debes capturar la huella primero.");
      return;
    }
    try {
      const form = new FormData();
      form.append('fmd_template', fmdTemplate);
      await api.put(`/medicos/${medicoParaHuella.id}/huella`, form, {
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'multipart/form-data' }
      });
      alert("Huella registrada exitosamente");
      closeHuellaModal();
      fetchMedicos();
    } catch (e) {
      alert("Error al registrar huella");
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
    setEditBajoContrato(m.bajo_contrato || false);
    if (m.bajo_contrato && m.horario_laboral) {
      try {
        setEditHorarioLaboral(JSON.parse(m.horario_laboral));
      } catch (e) { setEditHorarioLaboral(initialSchedule); }
    } else {
      setEditHorarioLaboral(initialSchedule);
    }
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
    formDataToSend.append('bajo_contrato', editBajoContrato);
    if (editBajoContrato) {
      formDataToSend.append('horario_laboral', JSON.stringify(editHorarioLaboral));
    }

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
    if (filterText && !h.folio.toLowerCase().includes(filterText.toLowerCase()) && !h.paciente.nombre_completo.toLowerCase().includes(filterText.toLowerCase()) && !(h.medico && h.medico.nombre_completo.toLowerCase().includes(filterText.toLowerCase())) && !(h.hash_seguridad && h.hash_seguridad.toLowerCase().includes(filterText.toLowerCase()))) return false;
    if (filterArea && h.area_hospitalaria !== filterArea) return false;
    if (filterDateStart && h.fecha_realizacion.split('T')[0] < filterDateStart) return false;
    if (filterDateEnd && h.fecha_realizacion.split('T')[0] > filterDateEnd) return false;
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
    ...(rolActual === 'admin' || rolActual === 'sistemas' ? [{ id: 'catalogos', label: 'Catálogos', icon: <FiList /> }, { id: 'auditoria', label: 'Auditoría', icon: <FiDatabase /> }] : []),
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
                  <h3 className="text-slate-500 font-semibold mb-2">Pacientes Ingresados Activos</h3>
                  <p className="text-5xl font-bold text-hes-blue-main">{stats.total_pacientes_activos}</p>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center justify-center">
                  <h3 className="text-slate-500 font-semibold mb-2">Atenciones del Mes</h3>
                  <p className="text-5xl font-bold text-orange-500">{stats.total_atenciones_mes}</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 lg:col-span-1">
                  <h3 className="text-slate-700 font-bold mb-4">Visitas por Área</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={stats.visitas_por_area} dataKey="cantidad" nameKey="area" cx="50%" cy="50%" outerRadius={80} fill="#8884d8" label>
                          {stats.visitas_por_area.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 lg:col-span-2">
                  <h3 className="text-slate-700 font-bold mb-4">SLA Médico (Tiempo Promedio de Respuesta)</h3>
                  <p className="text-sm text-slate-500 mb-4">Minutos desde la solicitud de enfermería hasta la firma médica.</p>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats.sla_por_medico} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                        <XAxis type="number" unit=" min" />
                        <YAxis dataKey="medico" type="category" width={150} tick={{fontSize: 12}} />
                        <Tooltip formatter={(value) => [`${value} min`, 'Promedio']} />
                        <Bar dataKey="tiempo_promedio_minutos" fill="#003870">
                          {stats.sla_por_medico.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.tiempo_promedio_minutos > 120 ? '#EF4444' : '#00C49F'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
              
              <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                  <h3 className="text-slate-700 font-bold mb-4">Actividad de Atenciones (Últimos 7 Días)</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats.actividad_reciente}>
                        <XAxis dataKey="fecha" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="cantidad" fill="#8884d8" />
                      </BarChart>
                    </ResponsiveContainer>
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
                    <label className="block text-xs font-semibold text-slate-500 mb-1">Buscar Paciente / Folio / Médico / Código</label>
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
                    <label className="block text-xs font-semibold text-slate-500 mb-1">Filtrar por Periodo (Desde - Hasta)</label>
                  <div className="flex gap-2">
                    <input type="date" className="w-1/2 border rounded p-2 text-sm" value={filterDateStart} onChange={e => setFilterDateStart(e.target.value)} />
                    <input type="date" className="w-1/2 border rounded p-2 text-sm" value={filterDateEnd} onChange={e => setFilterDateEnd(e.target.value)} />
                  </div>
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
                      <th className="p-3 text-sm font-semibold text-slate-600">Auditoría (Cód. Firma)</th>
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
                          <div className="font-semibold cursor-pointer hover:text-blue-600 hover:underline w-fit" onClick={() => setJourneyModal({ open: true, paciente: h.paciente })}>
                            {h.paciente.nombre_completo}
                          </div>
                          <div className="text-xs text-slate-500">Hab: {h.habitacion_capturada}</div>
                          <div className="text-xs font-normal text-slate-500 mt-1">Capturado por: {h.registrado_por_nombre || (h.creador ? h.creador.username : 'Sistemas')}</div>
                        </td>
                        <td className="p-3 text-sm text-slate-600">
                          <div className="font-semibold">{h.nombre_procedimiento} <span className="font-normal">({h.tipo_atencion})</span></div>
                          <div className="text-xs text-slate-500 mb-2">{h.area_hospitalaria}</div>
                          {h.notas && h.notas.length > 0 && (
                            <div className="mt-2 pl-3 border-l-2 border-blue-200 bg-white p-2 rounded shadow-sm">
                              <h4 className="text-xs font-bold text-blue-800 mb-1">Notas de Enfermería:</h4>
                              {h.notas.map(n => (
                                <div key={n.id} className="text-xs mb-1">
                                  <span className="font-semibold text-slate-700">{n.creador?.nombre_completo || n.creador?.username}:</span> {n.nota} <span className="text-slate-400">({new Date(n.fecha_creacion).toLocaleDateString()})</span>
                                </div>
                              ))}
                            </div>
                          )}
                          {(rolActual === 'admin' || rolActual === 'sistemas') && (
                            <button onClick={() => setNotaModal({ open: true, folio: h.folio, text: '' })} className="mt-2 text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1">
                              <FiPlusCircle /> Añadir Nota
                            </button>
                          )}
                        </td>
                        <td className="p-3 text-sm text-slate-600">{h.medico ? h.medico.nombre_completo : 'N/A'}</td>
                        <td className="p-3 text-sm">
                          <div>
                            {h.ruta_archivo_firmado ? (
                                <a href={`http://${serverIP}:8000${h.ruta_archivo_firmado}`} target="_blank" rel="noreferrer" className="bg-hes-green hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-semibold shadow-sm flex items-center gap-2 w-max">
                                  <FiFileText className="inline" /> PDF
                                </a>
                            ) : (
                                <div className="flex flex-col gap-2">
                                  <span className={`px-3 py-1 rounded-full text-xs font-bold w-max ${
                                    h.estatus_pago === 'Pendiente de Firma' ? 'bg-orange-100 text-orange-700' : 
                                    h.estatus_pago === 'Validado para Pago' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-700'
                                  }`}>
                                    {h.estatus_pago}
                                  </span>
                                  {h.is_caducado && !h.ruta_archivo_firmado && h.estatus_pago === 'Pendiente de Firma' && (
                                    <div className="text-xs text-red-600 font-bold">Caducado</div>
                                  )}
                                  {h.is_caducado && (rolActual === 'admin' || rolActual === 'sistemas') && !h.ruta_archivo_firmado && h.estatus_pago === 'Pendiente de Firma' && (
                                    <button onClick={() => handleReaperturar(h.folio)} className="bg-slate-800 text-white text-xs px-2 py-1 rounded mt-1 hover:bg-slate-900 w-max shadow-sm">
                                      Reaperturar
                                    </button>
                                  )}
                                </div>
                            )}
                          </div>
                        </td>
                        <td className="p-3 text-sm">
                          <div className="text-[10px] text-slate-400 font-mono break-all max-w-[150px] bg-slate-50 p-1 rounded border">
                            {h.hash_seguridad ? h.hash_seguridad : (h.estatus_pago === 'Validado para Pago' ? 'Validado sin firma' : 'No firmado')}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {historialFiltrado.length === 0 && (
                      <tr>
                        <td colSpan="6" className="p-6 text-center text-slate-500">No se encontraron registros.</td>
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
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Nombre Completo</label>
                      <input type="text" className="w-full border rounded-lg p-2" placeholder="Ej. Juan Pérez" value={newPacienteNombre} onChange={e => setNewPacienteNombre(e.target.value)} />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Cama / Habitación</label>
                      <input type="text" className="w-full border rounded-lg p-2" placeholder="Ej. 101" value={newPacienteHabitacion} onChange={e => setNewPacienteHabitacion(e.target.value)} />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Área Hospitalaria</label>
                      <select className="w-full border rounded-lg p-2 bg-white" value={newPacienteArea} onChange={e => setNewPacienteArea(e.target.value)}>
                        <option value="">Seleccione el Área...</option>
                        {areas.map(a => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                      </select>
                    </div>
                  </div>
                  <button onClick={handleCreatePaciente} className="bg-hes-blue-main text-white px-6 py-2 rounded-lg font-bold hover:bg-blue-800 transition-colors h-[42px] mt-4">
                    Ingresar
                  </button>
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-700 mb-4">Gestión de Pacientes Activos (Camas Ocupadas)</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-100 text-left border-b">
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
                        <td className="p-3 font-semibold text-slate-700">#{p.id}</td>
                        <td className="p-3 text-slate-800">
                          <div className="font-semibold cursor-pointer hover:text-blue-600 hover:underline w-fit" onClick={() => setJourneyModal({ open: true, paciente: p })}>
                            {p.nombre_completo}
                          </div>
                          {p.registrado_por_nombre && <div className="text-xs font-normal text-slate-500 mt-1">Reg. por: {p.registrado_por_nombre}</div>}
                        </td>
                        <td className="p-3 text-sm text-slate-600">{p.num_habitacion}</td>
                        <td className="p-3 text-sm text-slate-600">{p.area_hospitalaria || 'No asignada'}</td>
                        <td className="p-3 text-sm flex gap-2 flex-wrap">
                          <button onClick={() => openEditPacienteModal(p)} className="bg-blue-50 text-blue-600 px-3 py-1 rounded font-semibold text-xs border border-blue-200 hover:bg-blue-100" title="Editar">Editar</button>
                          <button onClick={() => openTrasladosModal(p)} className="bg-indigo-50 text-indigo-600 px-3 py-1 rounded font-semibold text-xs border border-indigo-200 hover:bg-indigo-100" title="Historial Traslados">Traslados</button>
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
                        <td colSpan="6" className="p-6 text-center text-slate-500">No hay pacientes activos actualmente.</td>
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
                  <div className="p-4 border border-slate-200 rounded-lg bg-white shadow-sm mt-4">
                    <label className="flex items-center gap-3 cursor-pointer mb-2">
                      <input type="checkbox" checked={bajoContrato} onChange={(e) => setBajoContrato(e.target.checked)} className="w-5 h-5 rounded text-hes-blue-main focus:ring-hes-blue-light" />
                      <span className="font-semibold text-slate-700">¿Médico bajo contrato?</span>
                    </label>
                    <p className="text-xs text-slate-500 mb-2">Si está bajo contrato, defina su horario laboral para bloquear registros durante su turno.</p>
                    {bajoContrato && (
                      <HorarioBuilder horario={horarioLaboral} setHorario={setHorarioLaboral} />
                    )}
                  </div>
                  <div className="p-4 border border-slate-200 rounded-lg bg-white shadow-sm mt-4">
                    <label className="flex items-center gap-3 cursor-pointer mb-2">
                      <input type="checkbox" checked={esAyudante} onChange={(e) => setEsAyudante(e.target.checked)} className="w-5 h-5 rounded text-hes-blue-main focus:ring-hes-blue-light" />
                      <span className="font-semibold text-slate-700">¿Es perfil de Ayudante?</span>
                    </label>
                    <p className="text-xs text-slate-500 mb-2">Los ayudantes podrán registrar pacientes pero no podrán firmar notas.</p>
                    {esAyudante && (
                      <div className="mt-3">
                        <label className="block text-sm font-semibold text-slate-700 mb-1">Seleccione al Médico Titular</label>
                        <select className="w-full border border-slate-300 rounded-lg p-2 bg-white" value={medicoAsignadoId} onChange={e => setMedicoAsignadoId(e.target.value)}>
                          <option value="">-- Seleccionar --</option>
                          {medicos.filter(m => !m.es_ayudante).map(m => (
                            <option key={m.id} value={m.id}>{m.nombre_completo}</option>
                          ))}
                        </select>
                      </div>
                    )}
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
                <button onClick={handleRegister} className="w-full max-w-md py-3 rounded-lg font-bold text-white shadow-md transition-colors bg-hes-blue-main hover:bg-[#003870]">
                  Registrar Médico
                </button>
              </div>
            </div>
          )}

          {activeTab === 'directorio' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
               <div className="mb-4 flex flex-col md:flex-row gap-4">
                 <input 
                   type="text" 
                   placeholder="Buscar médico por nombre, especialidad u horario..." 
                   value={medicoSearchTerm}
                   onChange={e => setMedicoSearchTerm(e.target.value)}
                   className="w-full md:w-1/2 border border-slate-300 rounded-lg p-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-hes-blue-main"
                 />
                 <select
                   value={medicoHuellaFilter}
                   onChange={e => setMedicoHuellaFilter(e.target.value)}
                   className="w-full md:w-1/4 border border-slate-300 rounded-lg p-3 text-slate-700 bg-white"
                 >
                   <option value="todos">Todos (Huella)</option>
                   <option value="con_huella">Con huella registrada</option>
                   <option value="sin_huella">Sin huella registrada</option>
                 </select>
               </div>
               <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="p-3 text-sm font-semibold text-slate-600">Nombre</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Especialidad</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Horario</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Huella</th>
                      <th className="p-3 text-sm font-semibold text-slate-600">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {medicos.filter(m => {
                      const matchesSearch = (m.nombre_completo || '').toLowerCase().includes(medicoSearchTerm.toLowerCase()) ||
                        (m.especialidad || '').toLowerCase().includes(medicoSearchTerm.toLowerCase()) ||
                        formatSchedule(m.horario_laboral).toLowerCase().includes(medicoSearchTerm.toLowerCase());
                      const matchesHuella = medicoHuellaFilter === 'todos' ? true : (medicoHuellaFilter === 'con_huella' ? m.tiene_huella : !m.tiene_huella);
                      return matchesSearch && matchesHuella;
                    }).map(m => (
                      <tr key={m.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3 text-sm font-medium text-slate-800">
                          {m.nombre_completo}
                          {m.es_ayudante && <span className="ml-2 bg-purple-100 text-purple-700 text-[10px] px-2 py-0.5 rounded font-bold uppercase">Ayudante</span>}
                        </td>
                        <td className="p-3 text-sm text-slate-600">{m.especialidad}</td>
                        <td className="p-3 text-sm text-slate-600 text-xs">{m.bajo_contrato ? formatSchedule(m.horario_laboral) : <span className="text-slate-400">Sin Contrato</span>}</td>
                        <td className="p-3 text-sm">
                          {m.tiene_huella ? (
                            <span className="text-green-600 font-semibold bg-green-100 px-2 py-1 rounded text-xs flex items-center w-max gap-1"><FiCheckCircle/> Registrada</span>
                          ) : (
                            <span className="text-slate-500 font-semibold bg-slate-200 px-2 py-1 rounded text-xs flex items-center w-max gap-1">Sin huella</span>
                          )}
                        </td>
                        <td className="p-3 text-sm flex gap-3">
                          {!m.tiene_huella && <button onClick={() => openHuellaModal(m)} className="text-green-600 hover:text-green-800" title="Registrar Huella"><MdFingerprint size={20}/></button>}
                          <button onClick={() => openEditModal(m)} className="text-hes-blue-main hover:text-blue-800" title="Editar"><FiEdit size={18}/></button>
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
                  {areas.map(a => (
                    <li key={a.id} className="bg-slate-50 p-3 rounded-lg border flex justify-between items-center group">
                      <span>{a.nombre}</span>
                      <button onClick={() => handleDeleteArea(a.id)} className="text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                        <FiTrash2 />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <h3 className="text-lg font-bold text-slate-700 mb-4">Tipos de Atención</h3>
                <div className="flex gap-2 mb-4">
                  <input type="text" value={newTipo} onChange={e => setNewTipo(e.target.value)} className="flex-1 border rounded-lg p-2" />
                  <button onClick={handleAddTipo} className="bg-hes-blue-main text-white px-4 py-2 rounded-lg">Agregar</button>
                </div>
                <ul className="space-y-2 max-h-64 overflow-y-auto">
                  {tipos.map(t => (
                    <li key={t.id} className="bg-slate-50 p-3 rounded-lg border flex justify-between items-center group">
                      <span>{t.nombre}</span>
                      <button onClick={() => handleDeleteTipo(t.id)} className="text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                        <FiTrash2 />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'auditoria' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 text-slate-600 text-sm border-b border-slate-200">
                      <th className="p-4 font-semibold">Fecha y Hora</th>
                      <th className="p-4 font-semibold">Usuario</th>
                      <th className="p-4 font-semibold">Acción</th>
                      <th className="p-4 font-semibold">Detalles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditoriaLogs.map((log) => (
                      <tr key={log.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                        <td className="p-4 text-sm text-slate-700 whitespace-nowrap">
                          {new Date(log.fecha_hora + "Z").toLocaleString()}
                        </td>
                        <td className="p-4 text-sm font-medium text-slate-700">
                          {log.usuario ? log.usuario.username : 'Sistema'}
                        </td>
                        <td className="p-4 text-sm font-medium text-slate-800">
                          {log.accion}
                        </td>
                        <td className="p-4 text-sm text-slate-600 max-w-md">
                          {log.detalles_json}
                        </td>
                      </tr>
                    ))}
                    {auditoriaLogs.length === 0 && (
                      <tr>
                        <td colSpan="4" className="p-8 text-center text-slate-500">
                          No hay registros de auditoría aún.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
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

                {rolActual === 'sistemas' && (
                  <div className="bg-red-50 rounded-xl shadow-sm border border-red-200 p-6 mt-4">
                    <h3 className="text-lg font-bold text-red-700 mb-2 flex items-center gap-2"><FiAlertCircle /> Limpieza de Base de Datos</h3>
                    <p className="text-sm text-red-600 mb-4">Elimina permanentemente registros operativos sin afectar usuarios ni catálogos.</p>
                    <button onClick={() => setCleanModal({...cleanModal, open: true})} className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded flex justify-center items-center gap-2">
                      <FiTrash2 /> Iniciar Limpieza de Registros
                    </button>
                  </div>
                )}
                
                <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 flex-1 mt-4">
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
                            <button onClick={() => handleChangePassword(u.id, u.rol)} className="text-orange-500 hover:underline text-xs font-semibold">Cambiar Contraseña</button>
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
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="bg-slate-50 border-b border-slate-100 p-6 shrink-0">
              <h3 className="text-xl font-bold text-slate-800">Editar Médico</h3>
            </div>
            <div className="p-6 space-y-4 overflow-y-auto">
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
              <div className="p-4 border border-slate-200 rounded-lg bg-white shadow-sm mt-4">
                <label className="flex items-center gap-3 cursor-pointer mb-2">
                  <input type="checkbox" checked={editBajoContrato} onChange={(e) => setEditBajoContrato(e.target.checked)} className="w-5 h-5 rounded text-hes-blue-main focus:ring-hes-blue-light" />
                  <span className="font-semibold text-slate-700">¿Médico bajo contrato?</span>
                </label>
                <p className="text-xs text-slate-500 mb-2">Si está bajo contrato, defina su horario laboral para bloquear registros durante su turno.</p>
                {editBajoContrato && (
                  <HorarioBuilder horario={editHorarioLaboral} setHorario={setEditHorarioLaboral} />
                )}
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
                <label className="block text-sm font-semibold text-slate-700 mb-1">Cama / Habitación</label>
                <input type="text" className="w-full border border-slate-300 rounded-lg p-2" value={editPacienteForm.num_habitacion} onChange={e => setEditPacienteForm({...editPacienteForm, num_habitacion: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Área Hospitalaria</label>
                <select className="w-full border rounded-lg p-2 bg-white" value={editPacienteForm.area_hospitalaria} onChange={e => setEditPacienteForm({...editPacienteForm, area_hospitalaria: e.target.value})}>
                  <option value="">Seleccione el Área...</option>
                  {areas.map(a => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Código de Barras</label>
                <input type="text" className="w-full border border-slate-300 rounded-lg p-2" value={editPacienteForm.codigo_barras} onChange={e => setEditPacienteForm({...editPacienteForm, codigo_barras: e.target.value})} />
              </div>
            </div>
            <div className="bg-slate-50 border-t border-slate-100 p-6 flex justify-end gap-3">
              <button onClick={() => setEditingPaciente(null)} className="px-6 py-2 rounded-lg font-semibold text-slate-600 hover:bg-slate-200 transition-colors">Cancelar</button>
              <button onClick={handleEditPacienteSubmit} className="px-6 py-2 rounded-lg font-semibold text-white bg-hes-blue-main hover:bg-[#003870] transition-colors shadow-sm">Guardar Cambios</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Añadir Nota */}
      {notaModal.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-96 max-w-full">
            <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2"><FiEdit3 /> Añadir Nota de Enfermería</h3>
            <p className="text-sm text-slate-600 mb-2">Para el folio: <strong>{notaModal.folio}</strong></p>
            <textarea 
              className="w-full h-32 border border-slate-300 rounded-lg p-3 resize-none focus:ring-2 focus:ring-blue-500 mb-4"
              placeholder="Escribe la nota..."
              value={notaModal.text}
              onChange={e => setNotaModal({...notaModal, text: e.target.value})}
            ></textarea>
            <div className="flex justify-end gap-2">
              <button onClick={() => setNotaModal({ open: false, folio: '', text: '' })} className="px-4 py-2 text-sm font-bold text-slate-600 bg-slate-100 rounded hover:bg-slate-200">Cancelar</button>
              <button onClick={handleAddNota} className="px-4 py-2 text-sm font-bold text-white bg-hes-blue-main rounded hover:bg-blue-800">Guardar Nota</button>
            </div>
          </div>
        </div>
      )}

      {isHuellaModalOpen && medicoParaHuella && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-6 bg-hes-blue-main text-white flex justify-between items-center">
              <h2 className="text-xl font-bold">Registrar Huella</h2>
            </div>
            <div className="p-6 overflow-y-auto flex-1 text-center flex flex-col items-center">
              <p className="mb-4 text-slate-600 font-semibold">Doctor: {medicoParaHuella.nombre_completo}</p>
              <div className={`w-32 h-32 rounded-full border-4 flex items-center justify-center relative mb-4 ${fmdTemplate ? 'border-hes-green bg-[#e6f4ed]' : 'border-slate-100 bg-white'}`}>
                {isAcquiring && <div className="absolute inset-0 rounded-full border border-hes-blue-light animate-ping opacity-20"></div>}
                <MdFingerprint className={`text-6xl ${fmdTemplate ? 'text-hes-green' : isAcquiring ? 'text-hes-blue-main animate-pulse' : 'text-slate-300'}`} />
              </div>
              {!isReady && !error && <div className="text-center text-slate-500 text-sm mb-2">{(readerStatus === 'Desconectado' || readerStatus === 'Iniciando...') ? 'Iniciando lector...' : readerStatus}</div>}
              {error && <div className="text-center text-red-600 text-sm font-medium mb-2">{error}</div>}
              {isReady && !fmdTemplate && !error && (
                <>
                  <div className="text-center text-hes-blue-main text-sm font-medium mb-3">{readerStatus}</div>
                  {!isAcquiring && (
                    <button onClick={startCapture} className="bg-hes-blue-main hover:bg-[#003870] text-white px-6 py-2 rounded-lg text-sm font-semibold shadow-sm transition-all mb-2">Capturar Huella</button>
                  )}
                </>
              )}
              {fmdTemplate && <p className="text-green-600 font-bold mt-2">¡Huella capturada lista para guardar!</p>}
              {fmdTemplate && <button onClick={resetFmd} className="mt-2 text-sm text-slate-500 hover:text-slate-700 underline">Volver a capturar</button>}
            </div>
            <div className="p-6 bg-slate-50 border-t border-slate-100 flex justify-end gap-3 shrink-0">
              <button onClick={closeHuellaModal} className="px-6 py-2 rounded-lg font-semibold text-slate-600 hover:bg-slate-200 transition-colors">Cancelar</button>
              <button onClick={handleSaveHuella} disabled={!fmdTemplate} className={`px-6 py-2 rounded-lg font-bold text-white shadow-md transition-colors ${!fmdTemplate ? 'bg-slate-400' : 'bg-hes-blue-main hover:bg-[#003870]'}`}>Guardar Huella</button>
            </div>
          </div>
        </div>
      )}

      {/* Traslados Modal */}
      {trasladosModal.open && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h2 className="text-xl font-bold text-slate-800">
                Historial de Traslados: {trasladosModal.paciente?.nombre_completo}
              </h2>
              <button onClick={() => setTrasladosModal({ open: false, paciente: null, traslados: [] })} className="text-slate-400 hover:text-slate-600">
                <FiTrash2 className="hidden" /> {/* just a placeholder to keep imports clean */}
                <span className="text-2xl leading-none">&times;</span>
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-100 text-slate-600 text-sm border-b border-slate-200">
                      <th className="p-3 font-semibold">Fecha y Hora</th>
                      <th className="p-3 font-semibold">Origen</th>
                      <th className="p-3 font-semibold">Destino</th>
                      <th className="p-3 font-semibold">Usuario que Movió</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trasladosModal.traslados.map((t) => (
                      <tr key={t.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3 text-sm text-slate-700">
                          {new Date(t.fecha_traslado + "Z").toLocaleString()}
                        </td>
                        <td className="p-3 text-sm text-slate-600">
                          {t.origen_area || 'N/A'} - Hab: {t.origen_habitacion || 'N/A'}
                        </td>
                        <td className="p-3 text-sm text-slate-800 font-medium bg-blue-50/30">
                          {t.destino_area || 'N/A'} - Hab: {t.destino_habitacion || 'N/A'}
                        </td>
                        <td className="p-3 text-sm text-slate-600">
                          {t.usuario ? t.usuario.username : '-'}
                        </td>
                      </tr>
                    ))}
                    {trasladosModal.traslados.length === 0 && (
                      <tr>
                        <td colSpan="4" className="p-8 text-center text-slate-500">
                          Este paciente no tiene historial de traslados.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            
            <div className="p-6 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button onClick={() => setTrasladosModal({ open: false, paciente: null, traslados: [] })} className="px-6 py-2 border border-slate-300 rounded-lg text-slate-700 font-semibold hover:bg-slate-100">
                Cerrar
              </button>
            </div>
          </div>
        </div>

      )}

      {/* Clean DB Modal */}
      {cleanModal.open && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col">
            <div className="p-6 bg-red-600 text-white flex items-center gap-3">
              <FiAlertCircle className="text-3xl" />
              <div>
                <h2 className="text-xl font-bold">Limpiar Registros de Operación</h2>
                <p className="text-sm text-red-100">Esta acción no se puede deshacer.</p>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-slate-700 font-semibold mb-4">Selecciona qué información deseas eliminar permanentemente de la base de datos:</p>
              
              <label className="flex items-center gap-3 cursor-pointer p-3 border rounded-lg hover:bg-slate-50 transition-colors">
                <input type="checkbox" checked={cleanModal.atenciones} onChange={(e) => setCleanModal({...cleanModal, atenciones: e.target.checked})} className="w-5 h-5 rounded text-red-600 focus:ring-red-500" />
                <span className="text-slate-800 font-medium">Atenciones Médicas y Archivos PDF</span>
              </label>
              
              <label className="flex items-center gap-3 cursor-pointer p-3 border rounded-lg hover:bg-slate-50 transition-colors">
                <input type="checkbox" checked={cleanModal.notas} onChange={(e) => setCleanModal({...cleanModal, notas: e.target.checked})} className="w-5 h-5 rounded text-red-600 focus:ring-red-500" />
                <span className="text-slate-800 font-medium">Notas de Enfermería</span>
              </label>
              
              <label className="flex items-center gap-3 cursor-pointer p-3 border rounded-lg hover:bg-slate-50 transition-colors">
                <input type="checkbox" checked={cleanModal.traslados} onChange={(e) => setCleanModal({...cleanModal, traslados: e.target.checked})} className="w-5 h-5 rounded text-red-600 focus:ring-red-500" />
                <span className="text-slate-800 font-medium">Historial de Traslados (Trayectorias)</span>
              </label>

              <label className="flex items-center gap-3 cursor-pointer p-3 border rounded-lg hover:bg-slate-50 transition-colors">
                <input type="checkbox" checked={cleanModal.pacientes} onChange={(e) => setCleanModal({...cleanModal, pacientes: e.target.checked})} className="w-5 h-5 rounded text-red-600 focus:ring-red-500" />
                <span className="text-slate-800 font-medium">Pacientes Actuales (Liberar todas las camas)</span>
              </label>
              
              <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg">
                <p className="text-sm text-blue-800 flex items-start gap-2">
                  <FiLock className="mt-1 flex-shrink-0" />
                  <span><strong>Nota:</strong> Los usuarios, médicos, huellas y catálogos de áreas/procedimientos NUNCA serán borrados por esta herramienta.</span>
                </p>
              </div>
            </div>
            
            <div className="p-6 bg-slate-50 border-t border-slate-100 flex justify-end gap-3 shrink-0">
              <button onClick={() => setCleanModal({...cleanModal, open: false})} className="px-6 py-2 rounded-lg font-semibold text-slate-600 hover:bg-slate-200 transition-colors">Cancelar</button>
              <button onClick={handleCleanDatabase} disabled={!cleanModal.atenciones && !cleanModal.notas && !cleanModal.traslados && !cleanModal.pacientes} className="px-6 py-2 rounded-lg font-bold text-white bg-red-600 hover:bg-red-700 shadow-md transition-colors disabled:bg-slate-400">
                Confirmar Limpieza
              </button>
            </div>
          </div>
        </div>
      )}

      <PatientJourneyModal isOpen={journeyModal.open} onClose={() => setJourneyModal({ open: false, paciente: null })} paciente={journeyModal.paciente} />
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { 
  FiX, FiCheck, FiUser, FiUsers, FiShield, FiAlertTriangle, 
  FiPhone, FiMail, FiMapPin, FiCreditCard, FiTrash2, FiRefreshCw, 
  FiPlus, FiEdit3, FiCheckCircle 
} from 'react-icons/fi';
import { MdFingerprint, MdVerifiedUser } from 'react-icons/md';
import { api } from '../../api';
import { useDigitalPersona } from '../../hooks/useDigitalPersona';
import { friendlyBiometricError, friendlyReaderStatus } from '../../utils/userMessages';

export const FirmantesEpisodioModal = ({ 
  open, 
  onClose, 
  paciente, 
  initialSelectedFirmante = null,
  onSaveSuccess 
}) => {
  const { status: dpStatus, fmdTemplate: dpFmd, challengeId, sessionId, resetFmd, startCapture, isAcquiring, error: dpError } = useDigitalPersona();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);
  const [enrollmentReason, setEnrollmentReason] = useState('');

  // Lista de firmantes cargados desde backend / Vertical PTCN
  const [firmantes, setFirmantes] = useState([]);
  
  // Firmante actualmente seleccionado para edición o nuevo
  const [selectedFirmanteId, setSelectedFirmanteId] = useState(null); // id | 'NEW'

  // Evaluación de edad
  const parseEdad = (p) => {
    if (!p) return 30;
    const raw = String(p.edad || p.age || '').replace(/\D/g, '');
    return raw ? parseInt(raw, 10) : 30;
  };

  const edadNum = parseEdad(paciente);
  const isMinor = edadNum < 18;

  // Estado del formulario en edición
  const [formData, setFormData] = useState({
    id: null,
    tipo_firmante: isMinor ? 'REPRESENTANTE_LEGAL' : 'PACIENTE',
    nombre_completo: '',
    parentesco: isMinor ? 'Padre / Madre / Tutor Legal' : 'Titular (Propio Derecho)',
    identificacion_oficial: '',
    domicilio: 'Conocido en expediente clínico',
    telefono: '',
    email: '',
    fmd_template: '',
    tiene_huella: false
  });

  // Cargar firmantes al abrir modal
  useEffect(() => {
    if (open && paciente?.id) {
      cargarFirmantes(initialSelectedFirmante?.id || 'NEW');
      return () => resetFmd();
    }
  }, [open, paciente?.id, initialSelectedFirmante?.id]);

  const cargarFirmantes = async (targetFirmanteId = null, preserveFeedback = false, targetFirmanteName = null) => {
    setLoading(true);
    if (!preserveFeedback) {
      setFeedbackMsg(null);
    }
    try {
      const res = await api.get(`/pacientes/${paciente.id}/firmantes-biometricos`);
      const list = res.data || [];
      setFirmantes(list);

      // Si se especificó un ID objetivo o ya teníamos uno seleccionado
      const idToFind = targetFirmanteId || selectedFirmanteId || initialSelectedFirmante?.id;
      if (idToFind && idToFind !== 'NEW') {
        const found = list.find(f => f.id === idToFind);
        if (found) {
          selectFirmanteForEdit(found, preserveFeedback);
          // Enrollment starts only from the visible Capture button after selection.
          return;
        }
      }
      if (targetFirmanteName) {
        const foundByName = list.find(f => (f.nombre_completo || '').trim().toUpperCase() === targetFirmanteName.trim().toUpperCase());
        if (foundByName) {
          selectFirmanteForEdit(foundByName, preserveFeedback);
          return;
        }
      }

      if (idToFind === 'NEW') {
        handleInitNuevo(isMinor ? 'REPRESENTANTE_LEGAL' : 'TESTIGO_1');
        return;
      }

      if (list.length > 0) {
        selectFirmanteForEdit(list[0], preserveFeedback);
      } else {
        handleInitNuevo(isMinor ? 'REPRESENTANTE_LEGAL' : 'PACIENTE');
      }
    } catch (err) {
      console.error('Error cargando firmantes; consulte el mensaje de la interfaz.');
      setFeedbackMsg({ type: 'error', text: 'Error al consultar firmantes: ' + (err.response?.data?.detail || err.message) });
    } finally {
      setLoading(false);
    }
  };

  const selectFirmanteForEdit = (f, preserveFeedback = false) => {
    setSelectedFirmanteId(f.id);
    setFormData({
      id: f.id,
      tipo_firmante: f.tipo_firmante || 'PACIENTE',
      nombre_completo: f.nombre_completo || '',
      parentesco: f.parentesco || '',
      identificacion_oficial: f.identificacion_oficial || '',
      domicilio: f.domicilio || '',
      telefono: f.telefono || '',
      email: f.email || '',
      fmd_template: '',
      tiene_huella: Boolean(f.tiene_huella)
    });
    if (!preserveFeedback) {
      setFeedbackMsg(null);
    }
    setEnrollmentReason('');
    resetFmd();
  };

  const handleInitNuevo = (tipoSugerido = 'TESTIGO_1') => {
    setSelectedFirmanteId('NEW');
    
    let parentescoSugerido = 'Familiar / Testigo Presencial';
    let nombreSugerido = '';
    let domicilioSugerido = '';

    if (tipoSugerido === 'PACIENTE') {
      nombreSugerido = paciente?.nombre_completo || paciente?.name || '';
      parentescoSugerido = 'Titular (Propio Derecho)';
      domicilioSugerido = 'Conocido en expediente clínico';
    } else if (tipoSugerido === 'REPRESENTANTE_LEGAL') {
      parentescoSugerido = isMinor ? 'Padre / Madre / Tutor Legal' : 'Familiar Responsable';
    } else if (tipoSugerido === 'TESTIGO_2') {
      parentescoSugerido = 'Testigo Institucional / Familiar';
    }

    setFormData({
      id: null,
      tipo_firmante: tipoSugerido,
      nombre_completo: nombreSugerido,
      parentesco: parentescoSugerido,
      identificacion_oficial: '',
      domicilio: domicilioSugerido,
      telefono: '',
      email: '',
      fmd_template: '',
      tiene_huella: false
    });
    setFeedbackMsg(null);
    setEnrollmentReason('');
    resetFmd();
  };

  // Auto-guardar huella para firmantes que ya existen en BD (sin requerir click adicional)
  const autoSaveHuella = async (fmdCapturado, firmanteId, dataToSave = formData, activeChallengeId, activeSessionId) => {
    if (!firmanteId || firmanteId === 'NEW' || !fmdCapturado) return false;
    setSaving(true);
    try {
      const reenroll = Boolean(dataToSave.tiene_huella);
      const endpoint = `/pacientes/${paciente.id}/firmantes-biometricos/${firmanteId}/${reenroll ? 'reenrolar' : 'enrolar'}`;
      await api.post(endpoint, {
        fmd_template: fmdCapturado,
        challenge_id: activeChallengeId,
        session_id: activeSessionId,
        motivo: reenroll ? enrollmentReason : null
      });
      setFeedbackMsg({
        type: 'success',
        text: `Huella guardada para ${dataToSave.nombre_completo || 'esta persona'}. Ya puede usarla para firmar.`
      });
      if (onSaveSuccess) onSaveSuccess();
      await cargarFirmantes(firmanteId, true);
      return true;
    } catch (err) {
      console.error('Falló el enrolamiento biométrico; detalle disponible en la interfaz.');
      setFormData(previous => previous.id === firmanteId ? { ...previous, tiene_huella: Boolean(dataToSave.tiene_huella) } : previous);
      setFeedbackMsg({
        type: 'error',
        text: friendlyBiometricError(err.response?.data?.detail || err.message, 'No se pudo guardar la huella. Intente nuevamente.')
      });
      return false;
    } finally {
      setFormData(previous => previous.id === firmanteId ? { ...previous, fmd_template: '' } : previous);
      setSaving(false);
    }
  };

  // Escuchar captura de huella en vivo con el sensor DigitalPersona
  useEffect(() => {
    if (dpFmd && open) {
      const capturedFmd = dpFmd;
      const activeChallengeId = challengeId;
      const activeSessionId = sessionId;
      resetFmd();

      // Si el firmante ya existe en BD, auto-guardar inmediatamente
      if (formData.id && formData.nombre_completo.trim()) {
        const currentData = { ...formData };
        setFormData(prev => ({
          ...prev,
          fmd_template: capturedFmd,
          tiene_huella: true
        }));
        autoSaveHuella(capturedFmd, formData.id, currentData, activeChallengeId, activeSessionId);
      } else {
        // Firmante nuevo: solo guardar en state local, el usuario debe dar click en "Guardar"
        setFormData(prev => ({
          ...prev,
          fmd_template: capturedFmd,
          tiene_huella: true
        }));
        setFeedbackMsg({
          type: 'success',
          text: `Huella registrada correctamente para ${formData.nombre_completo || 'esta persona'}.`
        });
      }
    }
  }, [dpFmd, open]);

  const handleStartCapture = () => {
    if (!formData.nombre_completo.trim()) {
      setFeedbackMsg({ type: 'error', text: 'Por favor ingresa primero el nombre completo de la persona antes de capturar su huella.' });
      return;
    }
    if (!formData.id || selectedFirmanteId === 'NEW') {
      setFeedbackMsg({ type: 'error', text: 'Guarde primero los datos de la persona. Después podrá registrar su huella.' });
      return;
    }
    const reason = enrollmentReason.trim();
    if (formData.tiene_huella && !reason) {
      setFeedbackMsg({ type: 'error', text: 'Escriba por qué necesita actualizar la huella.' });
      return;
    }
    setEnrollmentReason(reason);
    setFeedbackMsg({
      type: 'info',
      text: `Coloque el dedo de ${formData.nombre_completo} en el lector.`
    });
    startCapture({
      action: formData.tiene_huella ? 'REENROLAMIENTO_FIRMANTE' : 'ENROLAMIENTO_FIRMANTE',
      expectedIdentityRef: `firmante:${formData.id}`,
      patientRef: paciente.id,
      documentRef: formData.id
    });
  };

  const handleSaveCurrent = async () => {
    if (!formData.nombre_completo.trim()) {
      setFeedbackMsg({ type: 'error', text: 'El nombre completo es obligatorio.' });
      return;
    }

    setSaving(true);
    setFeedbackMsg(null);

    const payload = {
      tipo_firmante: formData.tipo_firmante,
      nombre_completo: formData.nombre_completo.trim().toUpperCase(),
      parentesco: formData.parentesco.trim() || 'Titular',
      identificacion_oficial: formData.identificacion_oficial?.trim() || null,
      domicilio: formData.domicilio?.trim() || 'Conocido en expediente clínico',
      telefono: formData.telefono?.trim() || null,
      email: formData.email?.trim() || null
    };

    try {
      const response = formData.id
        ? await api.put(`/pacientes/${paciente.id}/firmantes-biometricos/${formData.id}`, payload)
        : await api.post(`/pacientes/${paciente.id}/firmantes-biometricos`, payload);
      const savedId = formData.id || response.data?.id;

      setFeedbackMsg({ 
        type: 'success', 
        text: formData.id
          ? `Datos de ${payload.nombre_completo} guardados.`
          : `Datos guardados. Ahora registre la huella de ${payload.nombre_completo}.`
      });

      if (onSaveSuccess) onSaveSuccess();
      await cargarFirmantes(savedId, true, payload.nombre_completo);
    } catch (err) {
      console.error('Error guardando firmante; consulte el mensaje de la interfaz.');
      setFeedbackMsg({ 
        type: 'error', 
        text: 'No se pudieron guardar los datos: ' + (err.response?.data?.detail || err.message) 
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFirmante = async (firmanteId, firmanteNombre) => {
    if (!window.confirm(`¿Desea quitar a “${firmanteNombre}” de las personas que pueden firmar en este episodio?`)) {
      return;
    }

    setDeletingId(firmanteId);
    setFeedbackMsg(null);
    try {
      await api.delete(`/pacientes/${paciente.id}/firmantes-biometricos/${firmanteId}`);
      setFeedbackMsg({ type: 'success', text: `${firmanteNombre} fue retirado de este episodio.` });
      if (onSaveSuccess) onSaveSuccess();
      await cargarFirmantes();
    } catch (err) {
      console.error('Error eliminando firmante; consulte el mensaje de la interfaz.');
      setFeedbackMsg({ type: 'error', text: 'No se pudo quitar a la persona: ' + (err.response?.data?.detail || err.message) });
    } finally {
      setDeletingId(null);
    }
  };

  const getBadgeStyle = (tipo) => {
    switch (tipo) {
      case 'PACIENTE':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'REPRESENTANTE_LEGAL':
      case 'TUTOR':
        return 'bg-amber-100 text-amber-900 border-amber-200';
      case 'TESTIGO_1':
        return 'bg-purple-100 text-purple-900 border-purple-200';
      case 'TESTIGO_2':
        return 'bg-indigo-100 text-indigo-900 border-indigo-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getTipoLabel = (tipo) => {
    switch (tipo) {
      case 'PACIENTE': return 'Paciente';
      case 'REPRESENTANTE_LEGAL': return 'Tutor o responsable';
      case 'TESTIGO_1': return 'Primer testigo';
      case 'TESTIGO_2': return 'Segundo testigo';
      case 'CONTACTO': return 'Familiar';
      default: return tipo;
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden animate-fadeIn">
        
        {/* HEADER MODAL */}
        <div className="he-sign-header px-6 py-4 text-white flex justify-between items-center shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-white/10 rounded-xl border border-white/20">
              <MdFingerprint className="text-2xl text-emerald-300" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold">Personas que pueden firmar</h2>
              <p className="text-xs text-blue-100">
                Paciente: <strong className="text-white">{paciente?.nombre_completo || paciente?.name}</strong> · Folio: {paciente?.codigo_barras || paciente?.id}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors">
            <FiX className="text-2xl" />
          </button>
        </div>

        {/* CONTENIDO PRINCIPAL: 2 COLUMNAS (LISTA DE FIRMANTES + FORMULARIO/LECTOR) */}
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row bg-slate-50">
          
          {/* COLUMNA IZQUIERDA: DIRECTORIO DE CONTACTOS/FIRMANTES */}
          <div className="w-full md:w-80 lg:w-96 bg-white border-r border-slate-200 p-4 flex flex-col overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <FiUsers className="text-hes-blue-main" /> Personas registradas ({firmantes.length})
              </span>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => handleInitNuevo('TESTIGO_1')}
                  className="px-2.5 py-1 bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 rounded-lg text-[11px] font-bold flex items-center gap-1 transition-colors"
                  title="Agregar una persona como testigo"
                >
                  <FiPlus /> Testigo
                </button>
                <button
                  type="button"
                  onClick={() => handleInitNuevo('REPRESENTANTE_LEGAL')}
                  className="px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 rounded-lg text-[11px] font-bold flex items-center gap-1 transition-colors"
                  title="Agregar tutor o responsable"
                >
                  <FiPlus /> Tutor o responsable
                </button>
              </div>
            </div>

            {loading ? (
              <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                <FiRefreshCw className="animate-spin text-hes-blue-main" /> Cargando directorio...
              </div>
            ) : firmantes.length > 0 ? (
              <div className="space-y-2.5 flex-1">
                {firmantes.map((f) => {
                  const isSelected = selectedFirmanteId === f.id;
                  return (
                    <div
                      key={f.id}
                      onClick={() => selectFirmanteForEdit(f)}
                      className={`p-3 rounded-xl border text-left cursor-pointer transition-all relative group ${
                        isSelected
                          ? 'bg-blue-50/90 border-blue-400 ring-2 ring-blue-500/20 shadow-xs'
                          : 'bg-slate-50/70 hover:bg-slate-100 border-slate-200'
                      }`}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md uppercase border inline-block ${getBadgeStyle(f.tipo_firmante)}`}>
                            {getTipoLabel(f.tipo_firmante)}
                          </span>
                          <h4 className="font-bold text-slate-800 text-xs mt-1 uppercase truncate max-w-[170px]" title={f.nombre_completo}>
                            {f.nombre_completo}
                          </h4>
                          <span className="text-[11px] text-slate-500 block truncate" title={f.parentesco}>
                            {f.parentesco || 'Familiar'}
                          </span>
                        </div>

                        <div className="flex flex-col items-end gap-1.5">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 border ${
                            f.tiene_huella ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-slate-100 text-slate-500 border-slate-200'
                          }`}>
                            <MdFingerprint className="text-xs" />
                            {f.tiene_huella ? 'Huella lista' : 'Falta huella'}
                          </span>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteFirmante(f.id, f.nombre_completo);
                            }}
                            disabled={deletingId === f.id}
                            className="text-slate-400 hover:text-rose-600 p-1 rounded hover:bg-rose-50 transition-colors opacity-0 group-hover:opacity-100"
                            title="Quitar esta persona"
                          >
                            <FiTrash2 className="text-xs" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-6 text-center text-slate-400 text-xs space-y-2 border border-dashed border-slate-200 rounded-xl my-auto">
                <FiUsers className="text-2xl text-slate-300 mx-auto" />
                <p>Aún no hay personas registradas.</p>
                <button
                  type="button"
                  onClick={() => handleInitNuevo(isMinor ? 'REPRESENTANTE_LEGAL' : 'PACIENTE')}
                  className="px-3 py-1.5 bg-hes-blue-main text-white text-xs font-bold rounded-lg shadow-xs inline-flex items-center gap-1"
                >
                  <FiPlus /> Agregar primera persona
                </button>
              </div>
            )}

            <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 leading-relaxed">
              Para un consentimiento, registre primero al paciente o responsable. La pantalla de firma le indicará si también necesita testigos.
            </div>
          </div>

          {/* COLUMNA DERECHA: EDICIÓN Y CAPTURA BIOMÉTRICA */}
          <div className="flex-1 p-6 overflow-y-auto space-y-5">
            
            {feedbackMsg && (
              <div className={`p-3.5 rounded-xl flex items-start gap-2.5 text-xs font-semibold ${
                feedbackMsg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                feedbackMsg.type === 'error' ? 'bg-rose-50 text-rose-800 border border-rose-200' :
                'bg-blue-50 text-blue-800 border border-blue-200'
              }`}>
                {feedbackMsg.type === 'success' && <FiCheck className="text-base text-emerald-600 shrink-0 mt-0.5" />}
                {feedbackMsg.type === 'error' && <FiAlertTriangle className="text-base text-rose-600 shrink-0 mt-0.5" />}
                {feedbackMsg.type === 'info' && <FiRefreshCw className="text-base text-blue-600 shrink-0 mt-0.5 animate-spin" />}
                <span>{feedbackMsg.text}</span>
              </div>
            )}

            <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-blue-50 text-hes-blue-main rounded-lg">
                    <FiEdit3 className="text-base" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-800 text-sm">
                      {selectedFirmanteId === 'NEW' ? 'Agregar una persona' : 'Datos de la persona'}
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      1. Guarde los datos · 2. Registre la huella
                    </p>
                  </div>
                </div>

                <span className={`text-xs px-2.5 py-1 rounded-full font-bold flex items-center gap-1 border ${
                  formData.tiene_huella ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-amber-50 text-amber-800 border-amber-300'
                }`}>
                  <MdFingerprint className="text-sm" />
                  {formData.tiene_huella ? 'Huella registrada' : 'Falta registrar huella'}
                </span>
              </div>

              {/* SELECCIÓN DE ROL */}
              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  ¿Quién es esta persona? *
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'PACIENTE', label: 'Paciente', desc: 'Firma por sí mismo' },
                    { id: 'REPRESENTANTE_LEGAL', label: 'Tutor o responsable', desc: 'Firma en nombre del paciente' },
                    { id: 'TESTIGO_1', label: 'Primer testigo', desc: 'Presencia la firma' },
                    { id: 'TESTIGO_2', label: 'Segundo testigo', desc: 'Presencia la firma' },
                  ].map(r => (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => setFormData({ ...formData, tipo_firmante: r.id })}
                      className={`p-2.5 rounded-xl border text-left transition-all ${
                        formData.tipo_firmante === r.id
                          ? 'bg-blue-50 border-blue-400 ring-2 ring-blue-500/20 text-blue-900 font-bold'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <div className="text-xs">{r.label}</div>
                      <div className="text-[10px] text-slate-400 font-normal leading-tight mt-0.5">{r.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* CAMPOS DEL FORMULARIO */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Nombre completo *</label>
                  <input
                    type="text"
                    value={formData.nombre_completo}
                    onChange={e => setFormData({ ...formData, nombre_completo: e.target.value })}
                    placeholder="Nombre y apellidos"
                    className="w-full border border-slate-300 rounded-lg p-2.5 text-xs focus:ring-2 focus:ring-blue-500 outline-none uppercase font-semibold text-slate-800"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Relación con el paciente *</label>
                  <input
                    type="text"
                    value={formData.parentesco}
                    onChange={e => setFormData({ ...formData, parentesco: e.target.value })}
                    placeholder="Ej. Titular, Padre, Madre, Hermano/a, Testigo Presencial"
                    className="w-full border border-slate-300 rounded-lg p-2.5 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-800 font-medium"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Identificación (INE o pasaporte)</label>
                  <div className="relative">
                    <FiCreditCard className="absolute left-3 top-3 text-slate-400" />
                    <input
                      type="text"
                      value={formData.identificacion_oficial || ''}
                      onChange={e => setFormData({ ...formData, identificacion_oficial: e.target.value })}
                      placeholder="Ej. INE 09283472938 / Pasaporte"
                      className="w-full border border-slate-300 rounded-lg pl-9 pr-2.5 py-2 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-800 uppercase"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Teléfono</label>
                  <div className="relative">
                    <FiPhone className="absolute left-3 top-3 text-slate-400" />
                    <input
                      type="text"
                      value={formData.telefono || ''}
                      onChange={e => setFormData({ ...formData, telefono: e.target.value })}
                      placeholder="Ej. 55 1234 5678"
                      className="w-full border border-slate-300 rounded-lg pl-9 pr-2.5 py-2 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-800"
                    />
                  </div>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 mb-1">Domicilio</label>
                  <div className="relative">
                    <FiMapPin className="absolute left-3 top-3 text-slate-400" />
                    <input
                      type="text"
                      value={formData.domicilio || ''}
                      onChange={e => setFormData({ ...formData, domicilio: e.target.value })}
                      placeholder="Calle, número, colonia, alcaldía / municipio, estado"
                      className="w-full border border-slate-300 rounded-lg pl-9 pr-2.5 py-2 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-800"
                    />
                  </div>
                </div>
              </div>

              {/* PASO 2: REGISTRO DE HUELLA */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 mt-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <MdVerifiedUser className="text-base text-emerald-600" /> 2. Registrar huella
                  </span>
                  <span className="text-[11px] text-slate-500 font-medium">
                    {isAcquiring ? 'Coloque el dedo en el lector' : friendlyReaderStatus(dpStatus)}
                  </span>
                </div>

                {dpError && (
                  <div className="text-[11px] text-amber-800 bg-amber-50 p-2 rounded-lg border border-amber-200">
                    {friendlyBiometricError(dpError)}
                  </div>
                )}

                {formData.tiene_huella && (
                  <div className="pt-2">
                    <label className="block text-xs font-bold text-slate-700 mb-1">¿Por qué necesita actualizar la huella? *</label>
                    <input
                      type="text"
                      value={enrollmentReason}
                      onChange={event => setEnrollmentReason(event.target.value)}
                      disabled={isAcquiring}
                      placeholder="Ej. La lectura anterior ya no es clara"
                      className="w-full border border-slate-300 rounded-lg p-2.5 text-xs focus:ring-2 focus:ring-hes-blue-main outline-none disabled:bg-slate-100"
                    />
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-200">
                  <div className="text-xs text-slate-600">
                    {formData.tiene_huella ? (
                      <span className="text-emerald-700 font-semibold flex items-center gap-1">
                        <FiCheckCircle /> La huella ya está registrada.
                      </span>
                    ) : (
                      <span className="text-slate-500">
                        {formData.id ? 'Pulse “Leer huella” y pida a la persona que coloque su dedo.' : 'Guarde primero los datos para habilitar el lector.'}
                      </span>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={handleStartCapture}
                    disabled={isAcquiring || !formData.id}
                    className="bg-hes-blue-main hover:bg-hes-blue-dark text-white font-bold px-4 py-2.5 rounded-xl text-xs flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                  >
                    <MdFingerprint className="text-base" />
                    {!formData.id ? 'Primero guarde los datos' : isAcquiring ? 'Leyendo huella…' : (formData.tiene_huella ? 'Actualizar huella' : 'Leer huella')}
                  </button>
                </div>
              </div>

            </div>

          </div>
        </div>

        {/* FOOTER MODAL CON ACCIONES */}
        <div className="px-6 py-3.5 bg-white border-t border-slate-200 flex justify-between items-center shrink-0">
          <div className="text-xs text-slate-500 flex items-center gap-1.5">
            Los cambios se guardan en el expediente del paciente.
          </div>

          <div className="flex gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-semibold transition-colors"
            >
              Cerrar
            </button>
            <button
              type="button"
              onClick={handleSaveCurrent}
              disabled={saving}
              className="bg-hes-blue-main hover:bg-hes-blue-dark text-white px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-md transition-all disabled:opacity-50 cursor-pointer"
            >
              {saving ? <FiRefreshCw className="animate-spin" /> : <FiCheck />}
              {saving ? 'Guardando…' : formData.id ? 'Guardar cambios' : 'Guardar datos y continuar'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

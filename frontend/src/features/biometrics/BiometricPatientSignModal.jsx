import React, { useState, useEffect, useRef } from 'react';
import { FiX, FiCheck, FiShield, FiAlertTriangle, FiUser, FiUsers, FiRefreshCw, FiArrowRight, FiInfo } from 'react-icons/fi';
import { MdFingerprint, MdVerifiedUser } from 'react-icons/md';
import { api } from '../../api';
import { useDigitalPersona } from '../../hooks/useDigitalPersona';
import { useBiometricSignersQuery, useDocumentSignaturesQuery } from '../../hooks/useQueries';
import { nextDocumentSigner, representativeRoles, signerRole, witnessSigned, captureBelongsToSigner } from '../../utils/biometricSigners';
import { friendlyBiometricError, friendlyReaderStatus } from '../../utils/userMessages';

export const BiometricPatientSignModal = ({ 
  open, 
  onClose, 
  patientId, 
  documentInfo = {}, 
  onSignSuccess,
  onOpenEnrollModal,
  onProceedToDoctorSign
}) => {
  const { status: dpStatus, fmdTemplate: dpFmd, captureContext, challengeId, sessionId, resetFmd, startCapture, isAcquiring, error: dpError } = useDigitalPersona();

  const code = documentInfo.codigo_formato || 'HE-DIRMED-CONSUL-PLT-02';
  const slot = documentInfo.slot ?? 0;
  const signerQuery = useBiometricSignersQuery(patientId, open);
  const statusQuery = useDocumentSignaturesQuery(patientId, code, slot, open);
  const firmantes = signerQuery.data || [];
  const docFirmasStatus = statusQuery.data;
  const loadingFirmantes = signerQuery.isPending || statusQuery.isPending;
  const operationVersion = useRef(0);
  const sending = useRef(false);
  const [selectedFirmanteId, setSelectedFirmanteId] = useState(null);
  const [selectedRole, setSelectedRole] = useState('PACIENTE'); // 'PACIENTE' | 'REPRESENTANTE_LEGAL' | 'TESTIGO_1' | 'TESTIGO_2'
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error' | 'info', text: '' }
  const [signedSeal, setSignedSeal] = useState(null);

  const [isPacienteCapaz, setIsPacienteCapaz] = useState(
    documentInfo.paciente_capaz !== undefined ? Boolean(documentInfo.paciente_capaz) : true
  );

  const isPacFirmado = !!docFirmasStatus?.paciente_firmado;
  const isT1Firmado = !!docFirmasStatus?.testigo1_firmado;
  const isT2Firmado = !!docFirmasStatus?.testigo2_firmado;

  useEffect(() => {
    if (documentInfo.paciente_capaz !== undefined) {
      setIsPacienteCapaz(Boolean(documentInfo.paciente_capaz));
    } else {
      setIsPacienteCapaz(true);
    }
  }, [documentInfo.paciente_capaz, open]);

  useEffect(() => {
    operationVersion.current += 1;
    sending.current = false;
    setSubmitting(false);
    setSelectedFirmanteId(null);
    if (open && patientId) {
      setFeedback(null);
      setSignedSeal(null);
      resetFmd();
      return () => { operationVersion.current += 1; resetFmd(); };
    }
  }, [open, patientId, documentInfo.codigo_formato, documentInfo.slot]);

  useEffect(() => {
    if (open && signerQuery.isSuccess && statusQuery.isSuccess && !selectedFirmanteId) {
      seleccionarFirmantePorDefecto(firmantes, isPacienteCapaz, docFirmasStatus);
    }
  }, [open, signerQuery.data, statusQuery.data, selectedFirmanteId, isPacienteCapaz]);

  const seleccionarFirmantePorDefecto = (list, capaz, estadoFirmas) => {
    const person = nextDocumentSigner(list || [], capaz, estadoFirmas);
    setSelectedFirmanteId(person?.id ?? null);
    setSelectedRole(signerRole(person));
    setSignedSeal(null);
  };

  // Separación deduplicada de firmantes
  const pacienteFirmante = firmantes.find(f => f.tipo_firmante === 'PACIENTE');
  
  // Different people can share a name. Identity is the persisted signer ID.
  const contactosMap = new Map();
  firmantes.forEach(f => {
    if (f.tipo_firmante !== 'PACIENTE') {
      if (!contactosMap.has(f.id)) {
        contactosMap.set(f.id, f);
      }
    }
  });
  const contactosUnicos = Array.from(contactosMap.values());
  const representantesElegibles = contactosUnicos.filter((c) =>
    representativeRoles.includes(signerRole(c))
  );

  const selectedFirmante = firmantes.find(f => f.id === selectedFirmanteId);
  const startSigningCapture = () => startCapture({
    action: 'FIRMA_FIRMANTE',
    expectedIdentityRef: `firmante:${selectedFirmanteId}`,
    patientRef: patientId,
    documentCode: documentInfo.codigo_formato || 'HE-DIRMED-CONSUL-PLT-02',
    documentRef: documentInfo.slot !== undefined ? documentInfo.slot : 0
  });

  // Testigos elegibles (misma regla para la lista y los pasos: si el paciente
  // no puede firmar, su tutor autorizador no cuenta como testigo)
  const testigosElegibles = contactosUnicos.filter((c) =>
    ['TESTIGO_1', 'TESTIGO_2'].includes((c.tipo_firmante || '').toUpperCase())
  );

  const sensorBtnRef = useRef(null);

  const isSelectedFirmanteYaFirmado = !!(
    selectedFirmante && (
      (['PACIENTE', ...representativeRoles].includes(selectedRole) && isPacFirmado) ||
      (selectedRole === 'TESTIGO_1' && isT1Firmado) ||
      (selectedRole === 'TESTIGO_2' && isT2Firmado)
    )
  );

  // Estado funcional de los 3 pasos (se palomea solo con lo ya registrado)
  const stepAutoriza = isPacFirmado ? 'done' : 'active';
  const stepTestigos = !isPacFirmado ? '' : (!docFirmasStatus?.requiere_testigos || (isT1Firmado && isT2Firmado) ? 'done' : 'active');
  const stepHuella = (isSelectedFirmanteYaFirmado || signedSeal) ? 'done' : (selectedFirmante ? 'active' : '');

  // Navegación por pasos: cada paso lleva a su parte del flujo
  const goPasoAutoriza = () => {
    setFeedback(null);
    seleccionarFirmantePorDefecto(firmantes, isPacienteCapaz, docFirmasStatus);
  };
  const goPasoTestigos = () => {
    setFeedback(null);
    const idxPend = testigosElegibles.findIndex(tt => !witnessSigned(signerRole(tt), docFirmasStatus));
    if (testigosElegibles.length === 0) {
      setFeedback({ type: 'info', text: 'Agregue los testigos que solicita este documento.' });
    } else if (idxPend === -1) {
      setFeedback({ type: 'success', text: 'Los testigos ya firmaron. Puede continuar.' });
    } else {
      setSelectedFirmanteId(testigosElegibles[idxPend].id);
      setSelectedRole(signerRole(testigosElegibles[idxPend]));
    }
  };
  const goPasoHuella = () => {
    if (!selectedFirmante) {
      setFeedback({ type: 'error', text: 'Primero selecciona quién va a firmar en el paso 2.' });
      return;
    }
    sensorBtnRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    sensorBtnRef.current?.focus({ preventScroll: true });
  };

  // Al cambiar de persona se limpia cualquier lectura previa. La lectura comienza
  // sólo cuando el usuario pulsa el botón visible, para evitar sorpresas.
  useEffect(() => {
    operationVersion.current += 1;
    setSignedSeal(null);
    sending.current = false;
    setSubmitting(false);
    if (open && selectedFirmanteId && !isSelectedFirmanteYaFirmado && statusQuery.isSuccess && signerQuery.isSuccess) {
      resetFmd();
      return () => { operationVersion.current += 1; resetFmd(); };
    }
  }, [open, selectedFirmanteId, isPacienteCapaz, patientId, code, slot]);

  // Manejador de cambio de capacidad del paciente
  const handleToggleCapacidad = (capaz) => {
    setIsPacienteCapaz(capaz);
    setFeedback(null);
    seleccionarFirmantePorDefecto(firmantes, capaz, docFirmasStatus);
  };

  const handleStartCapture = () => {
    if (!selectedFirmante) {
      setFeedback({ type: 'error', text: 'Por favor selecciona quién va a firmar.' });
      return;
    }
    if (!isPacienteCapaz && selectedFirmante.tipo_firmante === 'PACIENTE') {
      setFeedback({ 
        type: 'error', 
        text: 'El paciente fue indicado como no en condiciones de firmar. La autorización debe realizarse obligatoriamente por el Tutor o Representante Legal.' 
      });
      return;
    }
    setFeedback({ type: 'info', text: `Coloque el dedo de ${selectedFirmante.nombre_completo} en el lector.` });
    startSigningCapture();
  };

  // Cuando el sensor captura la huella en vivo
  useEffect(() => {
    if (dpFmd && open && selectedFirmanteId && !submitting && captureBelongsToSigner(captureContext, patientId, code, slot, selectedFirmanteId)) {
      ejecutarFirma(dpFmd);
    }
  }, [dpFmd]);

  const ejecutarFirma = async (fmd) => {
    if (!selectedFirmante || sending.current) return;
    if (!isPacienteCapaz && selectedRole === 'PACIENTE') {
      setFeedback({ 
        type: 'error', 
        text: 'El paciente no está habilitado para firmar. Debe firmar el Tutor o Representante Legal.' 
      });
      return;
    }
    setSubmitting(true);
    sending.current = true;
    const version = operationVersion.current;
    setFeedback(null);

    try {
      const payload = {
        fmd_template: fmd,
        firmante_id: selectedFirmante.id,
        rol_firmante: selectedRole,
        codigo_formato: documentInfo.codigo_formato || 'HE-DIRMED-CONSUL-PLT-02',
        tipo_documento: documentInfo.tipo_documento || documentInfo.title || 'Consentimiento Informado',
        evolution_slot: documentInfo.slot !== undefined ? documentInfo.slot : 0,
        challenge_id: challengeId,
        session_id: sessionId
      };

      const res = await api.post(`/ehr/paciente/${patientId}/firmar-biometrico-firmante`, payload);
      if (version !== operationVersion.current) return;
      if (res.status !== 200 || res.data?.success !== true || !res.data?.firma?.id) {
        throw new Error('No se confirmó el registro biométrico. Consulte el estado antes de reintentar.');
      }
      const firmaData = res.data?.firma || {};
      
      setSignedSeal(firmaData);
      
      const roleLabel = selectedRole === 'PACIENTE' 
        ? 'Paciente' 
        : (representativeRoles.includes(selectedRole) ? 'Tutor o responsable' : 'Testigo');

      setFeedback({ 
        type: 'success', 
        text: `Firma guardada. ${selectedFirmante.nombre_completo} (${roleLabel}) autorizó el documento.` 
      });

      resetFmd();
      if (onSignSuccess) await onSignSuccess(res.data);
      if (version !== operationVersion.current) return;

      // Actualizar estado de firmas del documento
      try {
        const resEstado = await statusQuery.refetch();
        if (version !== operationVersion.current || resEstado.isError) return;
        seleccionarFirmantePorDefecto(firmantes, isPacienteCapaz, resEstado.data);
      } catch (_) {}

    } catch (err) {
      if (version !== operationVersion.current) return;
      console.error('Falló la firma biométrica; detalle disponible en la interfaz.');
      const detail = err.response?.data?.detail || err.message;
      setFeedback({ 
        type: 'error', 
        text: friendlyBiometricError(detail, 'No se pudo guardar la firma. Intente nuevamente.')
      });
      resetFmd();
    } finally {
      if (version === operationVersion.current) {
        sending.current = false;
        setSubmitting(false);
      }
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="he-sign-modal bg-white shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden animate-fadeIn">
        
        {/* HEADER */}
        <div className="he-sign-header px-5 py-4 text-white flex justify-between items-center gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2.5 bg-white/10 rounded-xl border border-white/15 shrink-0">
              <MdFingerprint className="text-2xl text-slate-200" />
            </div>
            <div className="min-w-0">
              <h2 className="text-[15px] font-bold tracking-tight leading-tight">
                Firma con huella
              </h2>
              <p className="text-[12px] text-slate-300 truncate">
                {documentInfo.title || documentInfo.tipo_documento || 'Consentimiento informado'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-white/70 hover:text-white p-2 rounded-xl hover:bg-white/10 shrink-0" title="Cerrar">
            <FiX className="text-xl" />
          </button>
        </div>

        {/* CUERPO */}
        <div className="p-5 space-y-4 text-sm text-slate-700 max-h-[78vh] overflow-y-auto">
          
          {/* PASOS 1-2-3 (clicables: llevan a su parte del flujo) */}
          <div className="he-steps">
            <button type="button" onClick={goPasoAutoriza} title="Ir a la autorización" className={`he-step ${stepAutoriza}`}>
              <span className="he-step-num">{stepAutoriza === 'done' ? '✓' : '1'}</span>
              <span>Quién firma</span>
            </button>
            <span className="he-step-arrow">›</span>
            <button type="button" onClick={goPasoTestigos} title="Ir a los testigos" className={`he-step ${stepTestigos}`}>
              <span className="he-step-num">{stepTestigos === 'done' ? '✓' : '2'}</span>
              <span>Elegir persona</span>
            </button>
            <span className="he-step-arrow">›</span>
            <button type="button" onClick={goPasoHuella} title="Ir al sensor de huella" className={`he-step ${stepHuella}`}>
              <span className="he-step-num">{stepHuella === 'done' ? '✓' : '3'}</span>
              <span>Leer huella</span>
            </button>
          </div>
          
          {/* BANNER ÉXITO COMPACTO */}
          {isPacFirmado && (
            <div className="p-3 bg-emerald-50/60 border border-emerald-200 rounded-xl flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-full bg-emerald-700 text-white flex items-center justify-center shrink-0 text-sm font-bold">✓</div>
                <div className="min-w-0">
                  <div className="font-bold text-[13px] text-slate-900">Autorización registrada en el expediente</div>
                  <div className="text-[11px] text-slate-500">{docFirmasStatus?.listo_para_cierre_medico ? 'Puede continuar con la firma del médico tratante.' : 'Complete las firmas de los dos testigos antes del cierre médico.'}</div>
                </div>
              </div>
              {docFirmasStatus?.listo_para_cierre_medico && onProceedToDoctorSign && (
                <button
                  type="button"
                  onClick={() => { onClose(); onProceedToDoctorSign(); }}
                  className="he-btn-huella px-4 py-2 text-white text-xs flex items-center gap-1.5 shrink-0 cursor-pointer"
                  style={{ fontSize: 12 }}
                >
                  Continuar con firma médica <FiArrowRight />
                </button>
              )}
            </div>
          )}

          {/* PASO 1: ¿QUIÉN AUTORIZA? */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-bold text-slate-900">1. ¿Quién debe firmar?</span>
            </div>
            <div className="flex flex-col sm:flex-row gap-2.5">
              <button
                type="button"
                onClick={() => handleToggleCapacidad(true)}
                className={`he-who-card ${isPacienteCapaz ? 'selected-pac' : ''}`}
              >
                <span className="he-who-icon"><FiUser /></span>
                <span>
                  <span className="block font-bold text-slate-900 text-[13.5px]">Firma el paciente</span>
                  <span className="block text-[11.5px] text-slate-500 mt-0.5">Está consciente y puede decidir por sí mismo.</span>
                </span>
              </button>

              <button
                type="button"
                onClick={() => handleToggleCapacidad(false)}
                className={`he-who-card ${!isPacienteCapaz ? 'selected-tut' : ''}`}
              >
                <span className="he-who-icon"><FiUsers /></span>
                <span>
                  <span className="block font-bold text-slate-900 text-[13.5px]">Firma tutor o representante</span>
                  <span className="block text-[11.5px] text-slate-500 mt-0.5">El paciente no puede firmar en este momento.</span>
                </span>
              </button>
            </div>
          </div>

          {(signerQuery.isError || statusQuery.isError) && (
            <div role="alert" className="p-3 bg-amber-50 text-amber-800 rounded-xl">No se pudo confirmar el estado de firmantes. Cierre y vuelva a abrir para reintentar.</div>
          )}
          {feedback && (
            <div className={`he-feedback flex items-start gap-2.5 font-bold ${
              feedback.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
              feedback.type === 'error' ? 'bg-rose-50 text-rose-800 border border-rose-200' :
              'bg-blue-50 text-blue-800 border border-blue-200'
            }`}>
              {feedback.type === 'success' && <FiCheck className="text-lg text-emerald-600 shrink-0 mt-0.5" />}
              {feedback.type === 'error' && <FiAlertTriangle className="text-lg text-rose-600 shrink-0 mt-0.5" />}
              {feedback.type === 'info' && <FiRefreshCw className="text-lg text-blue-600 shrink-0 mt-0.5 animate-spin" />}
              <span>{feedback.text}</span>
            </div>
          )}

          {/* PASO 2: ¿QUIÉN PONE LA HUELLA AHORA? — lista única */}
          {loadingFirmantes ? (
            <div className="p-6 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
              <FiRefreshCw className="animate-spin text-base" /> Cargando personas registradas…
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[13px] font-bold text-slate-900">2. Elija a la persona</span>
                <span className="text-[11px] text-slate-400 font-semibold">Pulse sobre su nombre</span>
              </div>

              {/* Autorizador */}
              <div className="text-[11px] font-bold text-slate-500 mt-1">Persona que autoriza el documento</div>
              {isPacienteCapaz ? (
                pacienteFirmante ? (
                  <button
                    key={pacienteFirmante.id}
                    type="button"
                    onClick={() => { setSelectedFirmanteId(pacienteFirmante.id); setSelectedRole('PACIENTE'); setFeedback(null); }}
                    className={`he-person-row ${selectedFirmanteId === pacienteFirmante.id && selectedRole === 'PACIENTE' ? 'selected' : ''} ${isPacFirmado ? 'signed' : ''}`}
                  >
                    <span className="he-radio">{(selectedFirmanteId === pacienteFirmante.id && selectedRole === 'PACIENTE') || isPacFirmado ? <span className="he-radio-dot" /> : null}</span>
                    <span className="flex-1 min-w-0">
                      <span className="block font-bold text-slate-900 text-[14px] truncate">{pacienteFirmante.nombre_completo}</span>
                      <span className="block text-[11px] text-slate-500">Paciente titular · Firma por sí mismo</span>
                    </span>
                    {isPacFirmado
                      ? <span className="he-pill-status he-pill-done signed">Firmado</span>
                      : <span className={`he-pill-status ${(selectedFirmanteId === pacienteFirmante.id && selectedRole === 'PACIENTE') ? 'he-pill-todo' : 'he-pill-done'}`}>{(selectedFirmanteId === pacienteFirmante.id && selectedRole === 'PACIENTE') ? 'Firmar ahora' : 'Pendiente'}</span>}
                  </button>
                ) : (
                  <div className="p-3 bg-slate-50 text-slate-500 rounded-xl border text-xs">No se encontró al paciente titular.</div>
                )
              ) : (
                representantesElegibles.length > 0 ? (
                  representantesElegibles.map((c) => {
                    const persistedRole = (c.tipo_firmante || 'REPRESENTANTE_LEGAL').toUpperCase();
                    const isSel = selectedFirmanteId === c.id && selectedRole === persistedRole;
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => { setSelectedFirmanteId(c.id); setSelectedRole(persistedRole); setFeedback(null); }}
                        className={`he-person-row ${isSel ? 'selected' : ''} ${isPacFirmado ? 'signed' : ''}`}
                      >
                        <span className="he-radio">{isSel || isPacFirmado ? <span className="he-radio-dot" /> : null}</span>
                        <span className="flex-1 min-w-0">
                          <span className="block font-bold text-slate-900 text-[14px] truncate">{c.nombre_completo}</span>
                          <span className="block text-[11px] text-slate-500">{persistedRole.replaceAll('_', ' ')} · {c.parentesco || 'Familiar'} · ID: {c.identificacion_oficial || 'Expediente'}</span>
                        </span>
                        {isPacFirmado
                          ? <span className="he-pill-status he-pill-done signed">Firmado</span>
                          : <span className={`he-pill-status ${isSel ? 'he-pill-todo' : 'he-pill-done'}`}>{isSel ? 'Firmar ahora' : 'Pendiente'}</span>}
                      </button>
                    );
                  })
                ) : (
                  <div className="p-3 bg-amber-50 text-amber-800 rounded-xl border border-amber-200 text-xs">No hay tutores registrados. Agrega un familiar en Contactos.</div>
                )
              )}

              {/* Testigos */}
              <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100">
                <div className="text-[11px] font-bold text-slate-500">Testigos · {docFirmasStatus?.requiere_testigos ? 'Este documento requiere dos' : 'Sólo si el documento los requiere'}</div>
                <span className="text-[10px] font-semibold text-slate-400">{isT1Firmado ? '1/2' : ''}{isT2Firmado ? ' · 2/2' : ''}</span>
              </div>
              {(() => {
                // testigosElegibles se calcula arriba (pasos y lista comparten la regla)
                if (testigosElegibles.length === 0) {
                  return (
                    <p className="text-[11.5px] text-slate-400 italic p-3 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                      No hay testigos registrados. Complete los requeridos por este documento.
                    </p>
                  );
                }
                return testigosElegibles.slice(0, 4).map((tt, idx) => {
                  const rolTestigo = (tt.tipo_firmante || '').toUpperCase();
                  const isSel = selectedFirmanteId === tt.id && selectedRole === rolTestigo;
                  const isDone = witnessSigned(rolTestigo, docFirmasStatus);
                  return (
                    <button
                      key={`tg-${tt.id}-${idx}`}
                      type="button"
                      onClick={() => { setSelectedFirmanteId(tt.id); setSelectedRole(rolTestigo); setFeedback(null); }}
                      className={`he-person-row ${isSel ? 'selected' : ''} ${isDone ? 'signed' : ''}`}
                    >
                      <span className="he-radio">{isSel || isDone ? <span className="he-radio-dot" /> : null}</span>
                      <span className="flex-1 min-w-0">
                        <span className="block font-bold text-slate-800 text-[13px] truncate">{tt.nombre_completo} <span className="text-[10px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded-md ml-1">{rolTestigo === 'TESTIGO_1' ? 'T1' : 'T2'}</span></span>
                        <span className="block text-[11px] text-slate-500">{tt.parentesco || 'Familiar / Testigo'} · ID: {tt.identificacion_oficial || 'INE'}</span>
                      </span>
                      {isDone
                        ? <span className="he-pill-status he-pill-done signed">Firmado</span>
                        : <span className={`he-pill-status ${isSel ? 'he-pill-todo' : 'he-pill-done'}`}>{isSel ? 'Firmar ahora' : 'Disponible'}</span>}
                    </button>
                  );
                });
              })()}
            </div>
          )}

          {/* PASO 3: CAPTURA DE HUELLA */}
          <div className="space-y-2">
            <span className="text-[13px] font-bold text-slate-900">3. Lea la huella</span>
            <div className="he-sensor-card p-4 flex flex-col sm:flex-row items-center gap-4">
              <div className={`he-sensor-orb ${isSelectedFirmanteYaFirmado || signedSeal ? 'ok' : isAcquiring ? 'live' : ''}`}>{isSelectedFirmanteYaFirmado || signedSeal ? <FiCheck /> : <MdFingerprint />}</div>
              <div className="flex-1 min-w-0 text-center sm:text-left">
                <div className="text-[11px] font-semibold text-slate-500">Lector de huellas · {isAcquiring ? 'Listo para leer' : dpFmd ? 'Huella leída' : friendlyReaderStatus(dpStatus)}</div>
                <div className="mt-1 text-[14px] font-bold text-slate-900 truncate">
                  {selectedFirmante ? <>{selectedFirmante.nombre_completo}</> : 'Seleccione una persona en el paso 2'}
                </div>
                <div className="text-[11.5px] text-slate-500">
                  {selectedFirmante ? (selectedRole === 'PACIENTE' ? 'Paciente' : representativeRoles.includes(selectedRole) ? 'Tutor o responsable' : selectedRole === 'TESTIGO_1' ? 'Primer testigo' : 'Segundo testigo') : 'Seleccione primero a una persona.'}
                  {isSelectedFirmanteYaFirmado ? ' · Ya registrado' : ''}
                </div>
                {dpError ? <div className="mt-1.5 text-[11px] font-semibold text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1 inline-block">{friendlyBiometricError(dpError)}</div> : null}
              </div>
              <button
                type="button"
                ref={sensorBtnRef}
                onClick={handleStartCapture}
                disabled={!selectedFirmante || isAcquiring || submitting || signerQuery.isError || statusQuery.isError}
                className={`he-btn-huella text-white flex items-center gap-2 shrink-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${isAcquiring ? 'live' : ''}`}
              >
                <MdFingerprint className="text-lg" />
                {isAcquiring
                  ? 'Apoye el dedo…'
                  : submitting
                    ? 'Registrando…'
                    : isSelectedFirmanteYaFirmado ? 'Leer nuevamente' : 'Leer huella'}
              </button>
            </div>
          </div>

          {/* SELLO DIGITAL OBTENIDO */}
          {signedSeal && (
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1.5">
              <div className="font-bold text-emerald-800 flex items-center gap-1.5 text-[13px]">
                <FiCheck className="text-emerald-700" /> Firma guardada correctamente
              </div>
              <div className="text-[11px] text-slate-500">
                Fecha y hora: <strong>{signedSeal.fecha_hora}</strong>
              </div>
            </div>
          )}

        </div>

        {/* FOOTER */}
        <div className="px-5 py-3.5 bg-white border-t border-slate-200 flex justify-between items-center gap-3 flex-wrap">
          <span className="text-[11px] text-slate-400">
            La firma queda guardada y vinculada a este documento.
          </span>
          <div className="flex items-center gap-2 ml-auto">
            {docFirmasStatus?.listo_para_cierre_medico && onProceedToDoctorSign && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onProceedToDoctorSign();
                }}
                className="he-btn-huella px-5 py-2.5 text-white text-xs flex items-center gap-1.5 cursor-pointer"
                style={{ fontSize: 13 }}
              >
                Continuar a firma médica <FiArrowRight />
              </button>
            )}
            <button 
              type="button" 
              onClick={onClose} 
              className="he-btn-ghost px-4 py-2.5 text-xs font-bold cursor-pointer"
            >
              Cerrar
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

import React, { useState, useEffect, useRef } from 'react';
import { FiX, FiCheck, FiShield, FiAlertTriangle, FiUser, FiUsers, FiRefreshCw, FiArrowRight, FiInfo } from 'react-icons/fi';
import { MdFingerprint, MdVerifiedUser } from 'react-icons/md';
import { api } from '../../api';
import { useDigitalPersona } from '../../hooks/useDigitalPersona';
import { useBiometricSignersQuery, useDocumentSignaturesQuery } from '../../hooks/useQueries';
import { nextDocumentSigner, representativeRoles, signerRole, patientCanAuthorize, witnessSigned, witnessProgress, requiredWitnesses, expectedWitnesses, witnessCandidateRoles, availableWitnessRoleFor, signedWitnessRoleFor, signerIdentityForRole, captureBelongsToSigner } from '../../utils/biometricSigners';
import { friendlyBiometricError, friendlyReaderStatus } from '../../utils/userMessages';

export const BiometricPatientSignModal = ({ 
  open, 
  onClose, 
  patientId, 
  documentInfo = {}, 
  onSignSuccess,
  onSignatureSaved,
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
  const signaturesUnverified = Boolean(docFirmasStatus?.detalles?.source_unverified);
  const loadingFirmantes = signerQuery.isPending || statusQuery.isPending;
  const operationVersion = useRef(0);
  const sending = useRef(false);
  const [selectedFirmanteId, setSelectedFirmanteId] = useState(null);
  const [selectedRole, setSelectedRole] = useState('PACIENTE'); // 'PACIENTE' | 'REPRESENTANTE_LEGAL' | 'TESTIGO_1' | 'TESTIGO_2'
  const [submitting, setSubmitting] = useState(false);
  const [checkingSignatures, setCheckingSignatures] = useState(false);
  const [applying, setApplying] = useState(false);
  const [savedThisSession, setSavedThisSession] = useState(0);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error' | 'info', text: '' }
  const [signedSeal, setSignedSeal] = useState(null);

  const [isPacienteCapaz, setIsPacienteCapaz] = useState(patientCanAuthorize(documentInfo.paciente_capaz));

  const isPacFirmado = !!docFirmasStatus?.paciente_firmado;
  const isT1Firmado = !!docFirmasStatus?.testigo1_firmado;
  const isT2Firmado = !!docFirmasStatus?.testigo2_firmado;
  const signedWitnessCount = witnessProgress(docFirmasStatus);
  const requiredWitnessCount = requiredWitnesses(docFirmasStatus, isPacienteCapaz);
  const expectedWitnessCount = expectedWitnesses(docFirmasStatus, isPacienteCapaz);
  const missingWitnessCount = Math.max(0, requiredWitnessCount - signedWitnessCount);
  const missingExpectedWitnessCount = Math.max(0, expectedWitnessCount - signedWitnessCount);
  const capacityLocked = (documentInfo.paciente_capaz !== undefined && documentInfo.paciente_capaz !== null && documentInfo.paciente_capaz !== '') || isPacFirmado;

  useEffect(() => {
    setIsPacienteCapaz(patientCanAuthorize(documentInfo.paciente_capaz));
  }, [documentInfo.paciente_capaz, open]);

  useEffect(() => {
    operationVersion.current += 1;
    sending.current = false;
    setSubmitting(false);
    setCheckingSignatures(false);
    setApplying(false);
    setSavedThisSession(0);
    setSelectedFirmanteId(null);
    if (open && patientId) {
      setFeedback(null);
      setSignedSeal(null);
      resetFmd();
      return () => { operationVersion.current += 1; resetFmd(); };
    }
  }, [open, patientId, documentInfo.codigo_formato, documentInfo.slot]);

  useEffect(() => {
    if (open && signerQuery.isSuccess && statusQuery.isSuccess && !signaturesUnverified && !selectedFirmanteId) {
      seleccionarFirmantePorDefecto(firmantes, isPacienteCapaz, docFirmasStatus);
    }
  }, [open, signerQuery.data, statusQuery.data, selectedFirmanteId, isPacienteCapaz, signaturesUnverified]);

  useEffect(() => {
    if (open && signaturesUnverified) {
      operationVersion.current += 1;
      setSelectedFirmanteId(null);
      resetFmd();
    }
  }, [open, signaturesUnverified]);

  const seleccionarFirmantePorDefecto = (list, capaz, estadoFirmas) => {
    const person = nextDocumentSigner(list || [], capaz, estadoFirmas);
    const documentRole = estadoFirmas?.paciente_firmado
      ? (signedWitnessRoleFor(person?.id, estadoFirmas) || availableWitnessRoleFor(person, estadoFirmas, capaz) || signerRole(person))
      : signerRole(person);
    setSelectedFirmanteId(person?.id ?? null);
    setSelectedRole(documentRole);
    setSignedSeal(null);
  };

  // Separación deduplicada de firmantes
  const pacienteFirmante = firmantes.find(f => f.tipo_firmante === 'PACIENTE');
  const patientSignedByThisPerson = isPacFirmado && pacienteFirmante
    && String(docFirmasStatus?.detalles?.firmante_paciente_id ?? '') === String(pacienteFirmante.id);
  
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
  const startSigningCapture = ({ firmanteId = selectedFirmanteId, role = selectedRole } = {}) => startCapture({
    action: 'FIRMA_FIRMANTE',
    expectedIdentityRef: signerIdentityForRole(firmanteId, role),
    patientRef: patientId,
    documentCode: documentInfo.codigo_formato || 'HE-DIRMED-CONSUL-PLT-02',
    documentRef: documentInfo.slot !== undefined ? documentInfo.slot : 0
  });

  // Testigos elegibles (misma regla para la lista y los pasos: si el paciente
  // no puede firmar, su tutor autorizador no cuenta como testigo)
  const selectedAuthorizerId = !isPacienteCapaz && representativeRoles.includes(selectedRole)
    ? selectedFirmanteId
    : docFirmasStatus?.detalles?.firmante_paciente_id;
  const testigosElegibles = contactosUnicos.filter((c) =>
    witnessCandidateRoles.includes(signerRole(c))
    && (selectedAuthorizerId == null || String(c.id) !== String(selectedAuthorizerId))
  );

  const sensorBtnRef = useRef(null);

  const isSelectedRoleOccupied = !!(
    selectedFirmante && (
      (['PACIENTE', ...representativeRoles].includes(selectedRole) && isPacFirmado) ||
      (selectedRole === 'TESTIGO_1' && isT1Firmado) ||
      (selectedRole === 'TESTIGO_2' && isT2Firmado)
    )
  );
  const signedPersonId = selectedRole === 'TESTIGO_1'
    ? docFirmasStatus?.detalles?.firmante_testigo1_id
    : selectedRole === 'TESTIGO_2'
      ? docFirmasStatus?.detalles?.firmante_testigo2_id
      : docFirmasStatus?.detalles?.firmante_paciente_id;
  const isSelectedFirmanteYaFirmado = isSelectedRoleOccupied
    && signedPersonId != null
    && String(signedPersonId) === String(selectedFirmanteId);

  // Dos pasos visibles: elegir a la persona y confirmar su identidad con la huella.
  const stepPersona = selectedFirmante ? 'done' : 'active';
  const stepHuella = (isSelectedRoleOccupied || signedSeal) ? 'done' : (selectedFirmante ? 'active' : '');

  // Navegación por pasos: cada paso lleva a su parte del flujo.
  // La acción principal de cada persona inicia la lectura directamente.
  const goPasoAutoriza = () => {
    setFeedback(null);
    seleccionarFirmantePorDefecto(firmantes, isPacienteCapaz, docFirmasStatus);
  };
  const goPasoHuella = () => {
    if (!selectedFirmante) {
      setFeedback({ type: 'error', text: 'Primero selecciona quién va a firmar en el paso 2.' });
      return;
    }
    sensorBtnRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    sensorBtnRef.current?.focus({ preventScroll: true });
  };

  // Al cambiar de persona se limpia cualquier lectura previa. La captura sólo
  // comienza después de una acción explícita sobre la persona elegida.
  useEffect(() => {
    operationVersion.current += 1;
    setSignedSeal(null);
    sending.current = false;
    setSubmitting(false);
    if (open && selectedFirmanteId && !isSelectedRoleOccupied && statusQuery.isSuccess && signerQuery.isSuccess) {
      resetFmd();
      return () => { operationVersion.current += 1; resetFmd(); };
    }
  }, [open, selectedFirmanteId, selectedRole, isPacienteCapaz, patientId, code, slot]);

  // Manejador de cambio de capacidad del paciente
  const handleToggleCapacidad = (capaz) => {
    if (capacityLocked) return;
    setIsPacienteCapaz(capaz);
    setFeedback(null);
    seleccionarFirmantePorDefecto(firmantes, capaz, docFirmasStatus);
  };

  const isRoleAlreadySigned = (role, status) => {
    if (['PACIENTE', ...representativeRoles].includes(role)) return Boolean(status?.paciente_firmado);
    if (role === 'TESTIGO_1') return Boolean(status?.testigo1_firmado);
    if (role === 'TESTIGO_2') return Boolean(status?.testigo2_firmado);
    return false;
  };

  const handleStartCapture = async ({ firmanteId = selectedFirmanteId, role = selectedRole } = {}) => {
    const captureFirmante = firmantes.find(f => String(f.id) === String(firmanteId)) || selectedFirmante;
    const captureRole = role || selectedRole;
    if (signaturesUnverified) {
      setFeedback({ type: 'info', text: 'No se pudo verificar el estado de las firmas. Actualice el estado antes de leer la huella.' });
      return;
    }
    if (!captureFirmante) {
      setFeedback({ type: 'error', text: 'Por favor selecciona quién va a firmar.' });
      return;
    }
    const captureAlreadySigned = isRoleAlreadySigned(captureRole, docFirmasStatus);
    const captureHasSeal = signedSeal
      && String(firmanteId) === String(selectedFirmanteId)
      && captureRole === selectedRole;
    if (captureAlreadySigned || captureHasSeal) {
      setFeedback({ type: 'info', text: 'Este lugar ya tiene una firma registrada. Seleccione a la siguiente persona.' });
      return;
    }
    if (!isPacienteCapaz && captureFirmante.tipo_firmante === 'PACIENTE') {
      setFeedback({ 
        type: 'error', 
        text: 'El paciente fue indicado como no en condiciones de firmar. La autorización debe realizarse obligatoriamente por el Tutor o Representante Legal.' 
      });
      return;
    }
    if (checkingSignatures || submitting || isAcquiring) return;
    const version = operationVersion.current;
    setCheckingSignatures(true);
    try {
      const latest = await statusQuery.refetch();
      if (version !== operationVersion.current || !open) return;
      if (latest.isError || !latest.data) {
        setFeedback({ type: 'error', text: 'No se pudo consultar el estado de las firmas. Intente de nuevo.' });
        return;
      }
      if (latest.data.detalles?.source_unverified) {
        setFeedback({ type: 'info', text: 'No se pudo verificar el estado de las firmas. No repita la huella todavía.' });
        return;
      }
      const roleOccupied = isRoleAlreadySigned(captureRole, latest.data);
      if (roleOccupied || captureHasSeal) {
        setFeedback({ type: 'info', text: 'Este lugar ya tiene una firma registrada. Seleccione a la siguiente persona.' });
        return;
      }
      if (captureRole.startsWith('TESTIGO_') && !latest.data.paciente_firmado) {
        setFeedback({ type: 'info', text: 'Primero debe firmar la persona que autoriza el documento.' });
        return;
      }
      setFeedback({ type: 'info', text: `Coloque el dedo de ${captureFirmante.nombre_completo} en el lector.` });
      void startSigningCapture({ firmanteId, role: captureRole });
    } catch (_) {
      if (version === operationVersion.current) {
        setFeedback({ type: 'error', text: 'No se pudo consultar el estado de las firmas. Intente de nuevo.' });
      }
    } finally {
      if (version === operationVersion.current) setCheckingSignatures(false);
    }
  };

  const selectAndStartCapture = (firmanteId, role) => {
    setSelectedFirmanteId(firmanteId);
    setSelectedRole(role);
    setFeedback(null);
    void handleStartCapture({ firmanteId, role });
  };

  // Cuando el sensor captura la huella en vivo
  useEffect(() => {
    if (dpFmd && open && !signaturesUnverified && selectedFirmanteId && !submitting && captureBelongsToSigner(captureContext, patientId, code, slot, selectedFirmanteId, selectedRole)) {
      ejecutarFirma(dpFmd);
    }
  }, [dpFmd, signaturesUnverified]);

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
      setSavedThisSession(count => count + 1);
      
      const roleLabel = selectedRole === 'PACIENTE' 
        ? 'Paciente' 
        : (representativeRoles.includes(selectedRole) ? 'Tutor o responsable' : 'Testigo');

      setFeedback({ 
        type: 'success', 
        text: `Firma guardada. ${selectedFirmante.nombre_completo} (${roleLabel}) autorizó el documento.` 
      });

      resetFmd();
      if (version !== operationVersion.current) return;

      // Actualizar estado de firmas del documento
      try {
        const resEstado = await statusQuery.refetch();
        if (version !== operationVersion.current || resEstado.isError) return;
        seleccionarFirmantePorDefecto(firmantes, isPacienteCapaz, resEstado.data);
        if (onSignatureSaved) {
          await onSignatureSaved({
            documentInfo,
            signatureStatus: resEstado.data,
          });
        }
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

  const applyAndClose = async () => {
    if (applying) return;
    setApplying(true);
    try {
      const refreshed = await statusQuery.refetch();
      if (refreshed.isError || !refreshed.data || refreshed.data.detalles?.source_unverified) throw new Error('No se pudo actualizar el estado de las firmas.');
      if (onSignSuccess) await onSignSuccess({
        applied: true,
        saved_count: savedThisSession,
        documentInfo,
        signatureStatus: refreshed.data,
      });
      resetFmd();
      onClose();
    } catch (_) {
      setFeedback({ type: 'error', text: 'Las firmas se guardaron, pero no se pudo actualizar la pantalla. Pulse “Aceptar y aplicar firmas” nuevamente.' });
    } finally {
      setApplying(false);
    }
  };

  const continueToDoctorSign = async () => {
    if (applying) return;
    setApplying(true);
    try {
      const refreshed = await statusQuery.refetch();
      if (refreshed.isError || refreshed.data?.detalles?.source_unverified || !refreshed.data?.listo_para_cierre_medico) {
        throw new Error('Aún no se confirmó que las firmas requeridas estén completas.');
      }
      if (onSignSuccess) await onSignSuccess({
        applied: true,
        saved_count: savedThisSession,
        documentInfo,
        signatureStatus: refreshed.data,
      });
      resetFmd();
      onClose();
      onProceedToDoctorSign?.();
    } catch (_) {
      setFeedback({ type: 'error', text: 'Las firmas se guardaron, pero no se pudo actualizar la pantalla. Intente nuevamente.' });
    } finally {
      setApplying(false);
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
          <button
            onClick={savedThisSession > 0 && !signaturesUnverified ? applyAndClose : onClose}
            className="text-white/70 hover:text-white p-2 rounded-xl hover:bg-white/10 shrink-0"
            title={savedThisSession > 0 && !signaturesUnverified ? 'Aceptar y aplicar firmas' : 'Cerrar'}
          >
            <FiX className="text-xl" />
          </button>
        </div>

        {/* CUERPO */}
        <div className="p-5 space-y-4 text-sm text-slate-700 max-h-[78vh] overflow-y-auto">
          {signaturesUnverified ? (
            <div role="alert" className="p-4 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 space-y-3">
              <div className="font-bold text-[13px]">No se pudo verificar el estado de las firmas.</div>
              <p className="text-xs">Intente actualizar; no repita la huella todavía. Las firmas guardadas pueden estar pendientes de verificación.</p>
              <button
                type="button"
                onClick={() => statusQuery.refetch()}
                disabled={statusQuery.isFetching}
                className="he-btn-ghost px-4 py-2 text-xs font-bold cursor-pointer disabled:opacity-60"
              >
                {statusQuery.isFetching ? 'Actualizando…' : 'Actualizar estado'}
              </button>
            </div>
          ) : (
          <>
          {/* Dos pasos sencillos: persona y huella */}
          <div className="he-steps">
            <button type="button" onClick={goPasoAutoriza} title="Elegir a la persona" className={`he-step ${stepPersona}`}>
              <span className="he-step-num">{stepPersona === 'done' ? '✓' : '1'}</span>
              <span>Elegir persona</span>
            </button>
            <span className="he-step-arrow">›</span>
            <button type="button" onClick={goPasoHuella} title="Ir al sensor de huella" className={`he-step ${stepHuella}`}>
              <span className="he-step-num">{stepHuella === 'done' ? '✓' : '2'}</span>
              <span>Confirmar con huella</span>
            </button>
          </div>
          
          {/* BANNER ÉXITO COMPACTO */}
          {isPacFirmado && (
            <div className={`p-3 border rounded-xl flex items-center justify-between gap-3 text-xs ${missingExpectedWitnessCount > 0 ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50/60 border-emerald-200'}`}>
              <div className="flex items-center gap-2.5 min-w-0">
                <div className={`w-8 h-8 rounded-full text-white flex items-center justify-center shrink-0 text-sm font-bold ${missingExpectedWitnessCount > 0 ? 'bg-amber-700' : 'bg-emerald-700'}`}>✓</div>
                <div className="min-w-0">
                  <div className="font-bold text-[13px] text-slate-900">Autorización registrada en el expediente</div>
                  <div className="text-[11px] text-slate-500">
                    {docFirmasStatus?.listo_para_cierre_medico
                      ? (missingExpectedWitnessCount > 0
                        ? `Falta${missingExpectedWitnessCount === 1 ? '' : 'n'} ${missingExpectedWitnessCount} testigo${missingExpectedWitnessCount === 1 ? '' : 's'} previsto${missingExpectedWitnessCount === 1 ? '' : 's'} en este formato. Puede continuar con el médico; el documento quedará señalado para revisión.`
                        : 'Ya puede firmar el médico.')
                      : missingWitnessCount > 0
                        ? `Falta${missingWitnessCount === 1 ? '' : 'n'} ${missingWitnessCount === 1 ? 'la firma de 1 testigo' : `la firma de ${missingWitnessCount} testigos`}.`
                        : 'Seleccione a la siguiente persona que debe firmar.'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* PASO 1: ¿QUIÉN AUTORIZA? */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-bold text-slate-900">¿Quién firmará este documento?</span>
            </div>
            <div className="flex flex-col sm:flex-row gap-2.5">
              <button
                type="button"
                onClick={() => handleToggleCapacidad(true)}
                disabled={capacityLocked}
                className={`he-who-card ${isPacienteCapaz ? 'selected-pac' : ''} disabled:cursor-default`}
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
                disabled={capacityLocked}
                className={`he-who-card ${!isPacienteCapaz ? 'selected-tut' : ''} disabled:cursor-default`}
              >
                <span className="he-who-icon"><FiUsers /></span>
                <span>
                  <span className="block font-bold text-slate-900 text-[13.5px]">Firma tutor o representante</span>
                  <span className="block text-[11.5px] text-slate-500 mt-0.5">El paciente no puede firmar en este momento.</span>
                </span>
              </button>
            </div>
            {capacityLocked && (
              <p className="text-[11px] text-slate-500">La persona que autoriza se define al guardar el documento y no se cambia aquí.</p>
            )}
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
                <span className="text-[13px] font-bold text-slate-900">Seleccione a la persona que pondrá su huella</span>
                <span className="text-[11px] text-slate-400 font-semibold">Seleccione para firmar ahora</span>
              </div>

              {/* Autorizador */}
              <div className="text-[11px] font-bold text-slate-500 mt-1">Persona que autoriza el documento</div>
              {isPacienteCapaz ? (
                pacienteFirmante ? (
                  <button
                    key={pacienteFirmante.id}
                    type="button"
                    onClick={() => selectAndStartCapture(pacienteFirmante.id, 'PACIENTE')}
                    className={`he-person-row ${selectedFirmanteId === pacienteFirmante.id && selectedRole === 'PACIENTE' ? 'selected' : ''} ${patientSignedByThisPerson ? 'signed' : ''}`}
                  >
                    <span className="he-radio">{(selectedFirmanteId === pacienteFirmante.id && selectedRole === 'PACIENTE') || patientSignedByThisPerson ? <span className="he-radio-dot" /> : null}</span>
                    <span className="flex-1 min-w-0">
                      <span className="block font-bold text-slate-900 text-[14px] truncate">{pacienteFirmante.nombre_completo}</span>
                      <span className="block text-[11px] text-slate-500">Paciente titular · Firma por sí mismo</span>
                    </span>
                    {isPacFirmado
                      ? <span className={`he-pill-status he-pill-done ${patientSignedByThisPerson ? 'signed' : ''}`}>{patientSignedByThisPerson ? 'Firmado' : 'Ya autorizado'}</span>
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
                    const signedByThisPerson = isPacFirmado
                      && String(docFirmasStatus?.detalles?.firmante_paciente_id ?? '') === String(c.id);
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => selectAndStartCapture(c.id, persistedRole)}
                        className={`he-person-row ${isSel ? 'selected' : ''} ${signedByThisPerson ? 'signed' : ''}`}
                      >
                        <span className="he-radio">{isSel || signedByThisPerson ? <span className="he-radio-dot" /> : null}</span>
                        <span className="flex-1 min-w-0">
                          <span className="block font-bold text-slate-900 text-[14px] truncate">{c.nombre_completo}</span>
                          <span className="block text-[11px] text-slate-500">{persistedRole.replaceAll('_', ' ')} · {c.parentesco || 'Familiar'} · ID: {c.identificacion_oficial || 'Expediente'}</span>
                        </span>
                        {isPacFirmado
                          ? <span className={`he-pill-status he-pill-done ${signedByThisPerson ? 'signed' : ''}`}>{signedByThisPerson ? 'Firmado' : 'Ya autorizado'}</span>
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
                <div className="text-[11px] font-bold text-slate-500">
                  Testigos · {expectedWitnessCount === 0
                    ? 'Este documento no tiene espacios para testigos'
                    : requiredWitnessCount === 0
                      ? `Puede agregar hasta ${expectedWitnessCount} testigo${expectedWitnessCount === 1 ? '' : 's'} (opcional)`
                      : `Necesita al menos ${requiredWitnessCount}; puede agregar hasta ${expectedWitnessCount}`}
                </div>
                {expectedWitnessCount > 0 && <span className="text-[10px] font-semibold text-slate-500">{signedWitnessCount} de {expectedWitnessCount} registrado{expectedWitnessCount === 1 ? '' : 's'}</span>}
              </div>
              {(() => {
                // testigosElegibles se calcula arriba (pasos y lista comparten la regla)
                if (expectedWitnessCount === 0) {
                  return (
                    <p className="text-[11.5px] text-slate-500 p-3 bg-slate-50 rounded-xl border border-slate-200">
                      Sólo debe firmar la persona que autoriza.
                    </p>
                  );
                }
                if (testigosElegibles.length === 0) {
                  return (
                    <p className="text-[11.5px] text-slate-400 italic p-3 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                      {missingWitnessCount > 0
                        ? 'No hay testigos disponibles. Registre a la persona que falta para continuar.'
                        : 'No hay más testigos disponibles. Puede continuar con la firma médica.'}
                    </p>
                  );
                }
                return testigosElegibles.map((tt) => {
                  const signedRole = signedWitnessRoleFor(tt.id, docFirmasStatus);
                  const rolTestigo = signedRole || availableWitnessRoleFor(tt, docFirmasStatus, isPacienteCapaz);
                  if (!rolTestigo) return null;
                  const isSel = selectedFirmanteId === tt.id && selectedRole === rolTestigo;
                  const isDone = Boolean(signedRole) && witnessSigned(signedRole, docFirmasStatus);
                  return (
                    <button
                      key={`tg-${tt.id}`}
                      type="button"
                      disabled={!isPacFirmado && !isDone}
                      onClick={() => selectAndStartCapture(tt.id, rolTestigo)}
                      className={`he-person-row ${isSel ? 'selected' : ''} ${isDone ? 'signed' : ''} disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      <span className="he-radio">{isSel || isDone ? <span className="he-radio-dot" /> : null}</span>
                      <span className="flex-1 min-w-0">
                        <span className="block font-bold text-slate-800 text-[13px] truncate">{tt.nombre_completo} <span className="text-[10px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded-md ml-1">{rolTestigo === 'TESTIGO_1' ? 'T1' : 'T2'}</span></span>
                        <span className="block text-[11px] text-slate-500">
                          {tt.parentesco || 'Familiar'} · {representativeRoles.includes(signerRole(tt)) ? 'Firmará como testigo en este documento' : 'Testigo presencial'} · ID: {tt.identificacion_oficial || 'INE'}
                        </span>
                      </span>
                      {isDone
                        ? <span className="he-pill-status he-pill-done signed">Firmado</span>
                        : <span className={`he-pill-status ${isSel ? 'he-pill-todo' : 'he-pill-done'}`}>{!isPacFirmado ? 'Primero autoriza' : isSel ? 'Firmar ahora' : 'Disponible'}</span>}
                    </button>
                  );
                });
              })()}
            </div>
          )}

          {/* PASO 3: CAPTURA DE HUELLA */}
          <div className="space-y-2">
            <span className="text-[13px] font-bold text-slate-900">Confirme la identidad con la huella</span>
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
                disabled={!selectedFirmante || isSelectedRoleOccupied || Boolean(signedSeal) || isAcquiring || submitting || checkingSignatures || signerQuery.isError || statusQuery.isError}
                className={`he-btn-huella text-white flex items-center gap-2 shrink-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${isAcquiring ? 'live' : ''}`}
              >
                <MdFingerprint className="text-lg" />
                {isAcquiring
                  ? 'Apoye el dedo…'
                    : checkingSignatures
                      ? 'Revisando firmas…'
                    : submitting
                    ? 'Registrando…'
                    : isSelectedRoleOccupied || signedSeal ? 'Firma registrada' : 'Reintentar huella'}
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
          </>
          )}

        </div>

        {/* FOOTER */}
        <div className="px-5 py-3.5 bg-white border-t border-slate-200 flex justify-between items-center gap-3 flex-wrap">
          <span className="text-[11px] text-slate-500">
            {signaturesUnverified
              ? 'Actualice el estado de las firmas antes de continuar.'
              : savedThisSession > 0
              ? `${savedThisSession === 1 ? 'La firma ya está guardada' : 'Las firmas ya están guardadas'}. Pulse Aceptar para actualizar el documento.`
              : 'Seleccione a una persona; la lectura comenzará automáticamente.'}
          </span>
          <div className="flex items-center gap-2 ml-auto">
            {signaturesUnverified ? (
              <button type="button" onClick={onClose} className="he-btn-ghost px-4 py-2.5 text-xs font-bold cursor-pointer">
                Cerrar
              </button>
            ) : docFirmasStatus?.listo_para_cierre_medico && onProceedToDoctorSign ? (
              <button
                type="button"
                onClick={continueToDoctorSign}
                disabled={applying}
                className="he-btn-huella px-5 py-2.5 text-white text-xs flex items-center gap-1.5 cursor-pointer"
                style={{ fontSize: 13 }}
              >
                {applying ? 'Aplicando firmas…' : 'Aplicar firmas y continuar con el médico'} <FiArrowRight />
              </button>
            ) : savedThisSession > 0 ? (
              <button
                type="button"
                onClick={applyAndClose}
                disabled={applying}
                className="he-btn-huella px-5 py-2.5 text-white text-xs font-bold cursor-pointer disabled:opacity-60"
              >
                {applying ? 'Aplicando firmas…' : 'Aceptar y aplicar firmas'}
              </button>
            ) : (
              <button
                type="button"
                onClick={onClose}
                className="he-btn-ghost px-4 py-2.5 text-xs font-bold cursor-pointer"
              >
                Cancelar
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

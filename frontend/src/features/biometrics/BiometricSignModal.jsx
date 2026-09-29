import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../api';
import { useDigitalPersona } from '../../hooks/useDigitalPersona';
import { useDocumentSignaturesQuery } from '../../hooks/useQueries';
import { useEscapeKey } from '../../hooks/useEscapeKey';
import Button from '../../components/ui/Button';
import AlertBanner from '../../components/ui/AlertBanner';
import { friendlyBiometricError, friendlyReaderStatus } from '../../utils/userMessages';
import { MdFingerprint } from 'react-icons/md';
import { FiCheckCircle, FiAlertCircle, FiX } from 'react-icons/fi';

/**
 * Modal Unificado de Firma Biométrica NOM-024.
 * Centraliza la escucha de hardware de huella (dpFmd) en un único efecto para evitar carreras de estado.
 */
export default function BiometricSignModal({
  isOpen,
  onClose,
  patientId,
  title = "Firma médica con huella",
  documentType = "Nota de Evolución de Urgencias",
  formatCode = "HE-DIRMED-SINPRO-PLT-87/01",
  evolutionSlot = 1,
  summaryContent = "",
  customPayload = null,
  customEndpoint = null,
  onSigned
}) {
  useEscapeKey(isOpen, onClose);

  const { status: dpStatus, fmdTemplate: dpFmd, captureContext, challengeId, sessionId, error: dpError, devices, resetFmd, startCapture, isAcquiring } = useDigitalPersona();

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [checking, setChecking] = useState(false);
  const operationVersion = useRef(0);
  const [pendingSync, setPendingSync] = useState(null);
  const signatureQuery = useDocumentSignaturesQuery(patientId, formatCode, evolutionSlot, isOpen && !customEndpoint);
  const existingSignature = !customEndpoint && Boolean(signatureQuery.data?.medico_firmado);
  const unverifiedSignature = !customEndpoint && Boolean(signatureQuery.data?.medico_sync_unverified);
  const syncState = signatureQuery.data?.medico_sync_state || pendingSync?.state;
  const syncOperationId = signatureQuery.data?.medico_sync_operation_id || pendingSync?.operationId;
  const signatureLocked = existingSignature || unverifiedSignature || Boolean(successMsg || pendingSync);

  const startSignatureCapture = async () => {
    if (submitting || checking || isAcquiring || signatureLocked) return;
    const version = operationVersion.current;
    setChecking(true);
    setErrorMsg(null);
    try {
      if (!customEndpoint) {
        const latest = await signatureQuery.refetch();
        if (version !== operationVersion.current) return;
        if (latest.isError || !latest.data) {
          setErrorMsg('No se pudo consultar si este documento ya está firmado. Intente de nuevo.');
          return;
        }
        if (latest.data.medico_firmado || latest.data.medico_sync_unverified) return;
      }
      resetFmd();
      void startCapture({
        action: 'FIRMA_MEDICA',
        patientRef: patientId,
        documentCode: formatCode,
        documentRef: evolutionSlot || 0
      });
    } catch (_) {
      if (version === operationVersion.current) setErrorMsg('No se pudo consultar el estado del documento. Intente de nuevo.');
    } finally {
      if (version === operationVersion.current) setChecking(false);
    }
  };

  // Abrir la ventana nunca enciende el lector.
  useEffect(() => {
    operationVersion.current += 1;
    if (isOpen) {
      setSubmitting(false);
      setChecking(false);
      setPendingSync(null);
      setErrorMsg(null);
      setSuccessMsg(null);
      resetFmd();
      return () => {
        operationVersion.current += 1;
        resetFmd();
      };
    }
  }, [isOpen, patientId, formatCode, evolutionSlot, customEndpoint]);

  // ÚNICO EFECTO que reacciona a la adquisición de huella biométrica
  useEffect(() => {
    if (!isOpen || !dpFmd || submitting || signatureLocked) return;
    if (captureContext?.action !== 'FIRMA_MEDICA' || String(captureContext.patientRef) !== String(patientId)
      || captureContext.documentCode !== formatCode || String(captureContext.documentRef ?? 0) !== String(evolutionSlot ?? 0)) return;

    const executeSignature = async () => {
      const version = operationVersion.current;
      try {
        setSubmitting(true);
        setErrorMsg(null);

        const endpoint = customEndpoint || `/ehr/paciente/${patientId}/firmar-biometrico`;
        const payload = customPayload 
          ? { ...customPayload, fmd_template: dpFmd, challenge_id: challengeId, session_id: sessionId }
          : {
              codigo_formato: formatCode,
              tipo_documento: documentType,
              evolution_slot: evolutionSlot,
              fmd_template: dpFmd,
              challenge_id: challengeId,
              session_id: sessionId,
            };

        const res = await api.post(endpoint, payload, customEndpoint
          ? undefined
          : { headers: { 'Idempotency-Key': challengeId } });
        if (version !== operationVersion.current) return;
        if (res.status === 202 && res.data?.operation_id) {
          setPendingSync({ state: res.data.state || 'PENDING', operationId: res.data.operation_id });
          resetFmd();
          if (onSigned) await Promise.resolve().then(() => onSigned(res.data)).catch(() => {});
          if (!customEndpoint) await signatureQuery.refetch();
          return;
        }

        if (res.data && res.data.success) {
          setSuccessMsg('Firma guardada correctamente.');
          
          resetFmd();
          if (onSigned) await Promise.resolve().then(() => onSigned(res.data)).catch(() => {});
          if (!customEndpoint) await signatureQuery.refetch();
        } else {
          const msg = res.data?.error || "No se confirmó la firma. Revise el estado del documento antes de reintentar.";
          setErrorMsg(msg);
          resetFmd();
        }
      } catch (err) {
        if (version !== operationVersion.current) return;
        if (err.response?.data?.operation_id) {
          setPendingSync({ state: err.response.data.state || 'FAILED', operationId: err.response.data.operation_id });
          resetFmd();
          if (onSigned) await Promise.resolve().then(() => onSigned(err.response.data)).catch(() => {});
          if (!customEndpoint) await signatureQuery.refetch();
          return;
        }
        const msg = err.response?.data?.detail || "No se confirmó la firma. Revise el estado del documento antes de reintentar.";
        setErrorMsg(friendlyBiometricError(msg, 'No se pudo guardar la firma. Intente nuevamente.'));
        resetFmd();
      } finally {
        if (version === operationVersion.current) setSubmitting(false);
      }
    };

    executeSignature();
  }, [dpFmd, isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 space-y-5 animate-scaleUp">
        
        {/* Cabecera */}
        <div className="flex justify-between items-start border-b border-slate-100 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-hes-blue-main/10 text-hes-blue-main rounded-2xl">
              <MdFingerprint className="text-3xl animate-pulse" />
            </div>
            <div>
              <h3 className="text-lg font-black text-slate-800">{title}</h3>
              <p className="text-xs text-slate-500">Revise el documento y pulse “Firmar ahora”</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <FiX className="text-xl" />
          </button>
        </div>

        {/* Resumen del Documento */}
        <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-200 text-xs space-y-1">
          <div className="flex justify-between text-slate-500 font-bold">
            <span>Documento:</span>
            <span className="text-slate-800">{documentType}</span>
          </div>
          {summaryContent && (
            <p className="text-slate-600 italic bg-white p-2 rounded-xl border border-slate-100 mt-2 text-[11px] line-clamp-3">
              "{summaryContent}"
            </p>
          )}
        </div>

        {/* Estado del Lector */}
        <div className="text-center py-4 space-y-3">
          <div className="inline-flex p-4 rounded-full bg-slate-100 border border-slate-200 shadow-inner">
            <MdFingerprint className={`text-5xl ${isAcquiring ? 'text-hes-blue-light animate-bounce' : 'text-slate-400'}`} />
          </div>
          
          <div>
            <p className="text-xs font-bold text-slate-700">
              {friendlyReaderStatus(dpStatus) || 'Coloque su dedo en el lector'}
            </p>
            <p className="text-[11px] text-slate-400">
              La huella se usará únicamente para confirmar esta firma.
            </p>
          </div>
        </div>

        {/* Mensajes de Estado */}
        <AlertBanner title="Lector de huellas" message={dpError && !signatureLocked ? friendlyBiometricError(dpError) : null} />
        <AlertBanner type="warning" title="No se pudo consultar el documento" message={!customEndpoint && signatureQuery.isError ? 'Pulse “Consultar estado” antes de volver a leer la huella.' : null} />
        <AlertBanner
          type={syncState === 'FAILED' ? 'error' : 'warning'}
          title={unverifiedSignature ? 'Firma local pendiente de revisión' : syncState === 'FAILED' ? 'Envío pendiente de revisión' : 'Firma guardada en el expediente'}
          message={signatureLocked && (unverifiedSignature || (syncState && syncState !== 'SYNCED'))
            ? `${unverifiedSignature ? 'Existe una firma local, pero Vertical no respondió para comprobar la versión actual. Pida a Sistemas revisar el estado.' : syncState === 'FAILED' ? 'El envío a Vertical falló. Pida a Sistemas revisar la sincronización.' : 'El envío a Vertical sigue pendiente.'} No vuelva a leer la huella.${syncOperationId ? ` Folio de seguimiento: ${syncOperationId}` : ''}`
            : null}
        />
        {errorMsg && (
          <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100 flex items-center gap-2">
            <FiAlertCircle className="text-base flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {(successMsg || existingSignature || pendingSync) && !unverifiedSignature && (!pendingSync || syncState === 'SYNCED') && (
          <div className="p-3 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100 space-y-2">
            <div className="flex items-center gap-2 font-bold">
              <FiCheckCircle className="text-base flex-shrink-0" />
              <span>Firma médica guardada en el expediente</span>
            </div>
          </div>
        )}

        {/* Botones de Acción */}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button variant="secondary" size="sm" onClick={onClose}>
            {signatureLocked ? 'Aceptar' : 'Cerrar'}
          </Button>
          {!customEndpoint && signatureQuery.isError && !signatureLocked && (
            <Button variant="primary" size="sm" onClick={() => { setErrorMsg(null); signatureQuery.refetch(); }}>Consultar estado</Button>
          )}
          {!customEndpoint && signatureLocked && (unverifiedSignature || (syncState && syncState !== 'SYNCED')) && (
            <Button variant="primary" size="sm" onClick={() => signatureQuery.refetch()} isLoading={signatureQuery.isFetching}>Actualizar estado</Button>
          )}
          {!signatureLocked && (customEndpoint || !signatureQuery.isError) && <Button
            variant="primary"
            size="sm"
            isLoading={submitting || checking}
            disabled={isAcquiring || (!customEndpoint && !signatureQuery.isSuccess)}
            icon={<MdFingerprint />}
            onClick={startSignatureCapture}
          >
            Firmar ahora
          </Button>}
        </div>

      </div>
    </div>
  );
}

import React, { useEffect, useMemo, useState } from 'react';
import { FiCheck, FiInfo, FiX } from 'react-icons/fi';
import { MdFingerprint } from 'react-icons/md';
import { api } from '../../api';
import { useDigitalPersona } from '../../hooks/useDigitalPersona';
import { useSpecialSignatureSignersQuery, useDocumentSignaturesQuery } from '../../hooks/useQueries';

export default function SpecialSignerBiometricSignModal({ open, onClose, patientId, documentInfo = {}, onSaved, selfSignerId = null }) {
  const code = documentInfo.codigo_formato || '';
  const slot = documentInfo.slot ?? 0;
  const role = String(documentInfo.rol_firmante || '').toUpperCase();
  const roleLabel = documentInfo.areaLabel || role.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());
  const title = documentInfo.title || documentInfo.tipo_documento || 'Formato clínico';
  const signersQuery = useSpecialSignatureSignersQuery(code, role, open);
  const signatureQuery = useDocumentSignaturesQuery(patientId, code, slot, open);
  const signers = signersQuery.data || [];
  const status = signatureQuery.data;
  const specialStatus = status?.firmas_especiales_estado?.[role] || status?.detalles?.firmas_especiales?.[role] || {};
  const [selectedId, setSelectedId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const { status: readerStatus, devices, fmdTemplate, captureContext, challengeId, sessionId,
    startCapture, resetFmd, isAcquiring, error: readerError } = useDigitalPersona();

  const selectedSigner = useMemo(
    () => signers.find(person => String(person.id) === String(selectedId)),
    [signers, selectedId],
  );
  const alreadySigned = Boolean(specialStatus.firmado);
  const statusUnavailable = signatureQuery.isPending || signatureQuery.isError || status?.detalles?.source_unverified;

  useEffect(() => {
    if (!open) return undefined;
    setSelectedId(selfSignerId == null ? '' : String(selfSignerId)); setFeedback(null); setSubmitting(false); resetFmd();
    return () => resetFmd();
  }, [open, patientId, code, slot, role, selfSignerId]);

  useEffect(() => { resetFmd(); setFeedback(null); }, [selectedId]);
  if (!open) return null;

  const beginCapture = async () => {
    if (!selectedSigner || isAcquiring || alreadySigned || statusUnavailable) return;
    setFeedback(null);
    const started = await startCapture({
      action: 'FIRMA_USUARIO_ESPECIAL',
      expectedIdentityRef: `usuario_especial:${selectedSigner.id}|role:${role}`,
      patientRef: patientId,
      documentCode: code,
      documentRef: String(slot),
    });
    if (!started) setFeedback({ type: 'error', text: 'No se pudo iniciar la lectura de huella.' });
  };

  const saveSignature = async () => {
    if (!selectedSigner || !fmdTemplate || submitting) return;
    const expectedIdentity = `usuario_especial:${selectedSigner.id}|role:${role}`;
    const captureMatches = captureContext?.action === 'FIRMA_USUARIO_ESPECIAL'
      && captureContext?.expectedIdentityRef === expectedIdentity
      && String(captureContext?.patientRef) === String(patientId)
      && captureContext?.documentCode === code
      && String(captureContext?.documentRef ?? 0) === String(slot);
    if (!captureMatches || statusUnavailable || alreadySigned) {
      setFeedback({ type: 'error', text: 'La captura ya no corresponde a este documento. Inicie una lectura nueva.' });
      resetFmd(); return;
    }
    setSubmitting(true); setFeedback(null);
    try {
      await api.post(`/ehr/paciente/${encodeURIComponent(patientId)}/firmar-biometrico-especial`, {
        usuario_firmante_id: selectedSigner.id,
        rol_firmante: role,
        codigo_formato: code,
        tipo_documento: documentInfo.tipo_documento || title,
        evolution_slot: slot,
        fmd_template: fmdTemplate,
        challenge_id: challengeId,
        session_id: sessionId,
      }, { headers: { 'Idempotency-Key': challengeId } });
      resetFmd();
      const updated = await signatureQuery.refetch();
      await onSaved?.(updated.data);
      setFeedback({ type: 'success', text: `Firma biométrica registrada para ${selectedSigner.nombre_completo}. No equivale a FEA.` });
    } catch (failure) {
      if (failure.response?.status === 409) {
        const updated = await signatureQuery.refetch();
        await onSaved?.(updated.data);
      }
      setFeedback({ type: 'error', text: failure.response?.data?.detail || 'No se pudo registrar la firma biométrica. Revise el estado antes de volver a intentar.' });
      resetFmd();
    } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 p-3 sm:p-6" role="dialog" aria-modal="true" aria-labelledby="special-sign-title">
      <section className="w-full max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 bg-slate-50 px-5 py-4">
          <div>
            <h2 id="special-sign-title" className="font-bold text-slate-900">Firma biométrica · {roleLabel}</h2>
            <p className="mt-1 text-xs text-slate-600">{title} · {code}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-200" aria-label="Cerrar"><FiX /></button>
        </header>
        <div className="space-y-4 p-5">
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
            <FiInfo className="mr-1 inline" /> La persona de {roleLabel} debe colocar su dedo. Es evidencia biométrica del acto y no una FEA.
          </div>
          {alreadySigned ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              <FiCheck className="mr-1 inline" /> Firmado por <strong>{specialStatus.firmante || 'Usuario autorizado'}</strong> el {specialStatus.fecha || 'fecha registrada'}.
            </div>
          ) : (
            <>
              <label className="block text-sm font-semibold text-slate-700">
                Personal de {roleLabel}
                <select value={selectedId} onChange={event => setSelectedId(event.target.value)} disabled={selfSignerId != null || signersQuery.isPending || submitting || isAcquiring} className="mt-1 w-full rounded-xl border border-slate-300 bg-white p-3">
                  <option value="">Seleccione una cuenta con huella y permiso de firma</option>
                  {signers.map(person => <option key={person.id} value={person.id}>{person.nombre_completo} · {person.username}</option>)}
                </select>
              </label>
              {signersQuery.isError && <p className="text-sm text-red-700">{signersQuery.error?.response?.data?.detail || 'No se pudo cargar el personal autorizado.'}</p>}
              {!signersQuery.isPending && !signersQuery.isError && signers.length === 0 && <p className="text-sm text-amber-800">No hay cuentas activas de {roleLabel} con huella y permiso para este formato.</p>}
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-700"><MdFingerprint className="text-xl text-blue-700" />{readerStatus}</div>
                  <span className="text-xs text-slate-500">{devices.length ? 'Lector disponible' : 'Conecte el lector'}</span>
                </div>
                {readerError && <p className="mt-2 text-xs text-red-700">{readerError}</p>}
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={beginCapture} disabled={!selectedSigner || !devices.length || isAcquiring || submitting || alreadySigned || statusUnavailable} className="rounded-xl bg-blue-700 px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">{isAcquiring ? 'Leyendo huella…' : fmdTemplate ? 'Volver a leer huella' : 'Leer huella'}</button>
                  {fmdTemplate && <button type="button" onClick={saveSignature} disabled={submitting || !selectedSigner || statusUnavailable} className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{submitting ? 'Guardando…' : 'Registrar firma'}</button>}
                </div>
              </div>
            </>
          )}
          {statusUnavailable && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">No se pudo confirmar la versión actual de las firmas. Actualice el estado antes de continuar.</p>}
          {feedback && <p role="status" className={`rounded-lg p-3 text-sm ${feedback.type === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>{feedback.text}</p>}
          <div className="flex justify-end"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Cerrar</button></div>
        </div>
      </section>
    </div>
  );
}

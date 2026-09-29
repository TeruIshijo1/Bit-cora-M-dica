import React, { useEffect, useState } from 'react';
import { FiX } from 'react-icons/fi';
import { MdFingerprint } from 'react-icons/md';
import { api } from '../../api';
import { useDigitalPersona } from '../../hooks/useDigitalPersona';

export default function UserBiometricEnrollmentModal({ open, user, reenrollment = false, onClose, onSaved }) {
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const { status, devices, fmdTemplate, captureContext, challengeId, sessionId,
    startCapture, resetFmd, isAcquiring, error: readerError } = useDigitalPersona();

  useEffect(() => {
    if (!open) return undefined;
    setReason(''); setSaving(false); setError(''); setSuccess(''); resetFmd();
    return () => resetFmd();
  }, [open, user?.id]);

  if (!open || !user) return null;

  const capture = async () => {
    setError('');
    const started = await startCapture({
      action: reenrollment ? 'REENROLAMIENTO_USUARIO' : 'ENROLAMIENTO_USUARIO',
      expectedIdentityRef: `usuario:${user.id}`,
      documentRef: String(user.id),
    });
    if (!started) setError('No se pudo iniciar la lectura de huella.');
  };

  const save = async () => {
    if (!fmdTemplate || saving) return;
    if (reenrollment && !reason.trim()) { setError('Indique el motivo de la actualización.'); return; }
    const expectedAction = reenrollment ? 'REENROLAMIENTO_USUARIO' : 'ENROLAMIENTO_USUARIO';
    if (captureContext?.action !== expectedAction
      || captureContext?.expectedIdentityRef !== `usuario:${user.id}`
      || String(captureContext?.documentRef) !== String(user.id)) {
      setError('La captura ya no corresponde a esta cuenta. Inicie una lectura nueva.');
      resetFmd(); return;
    }
    setSaving(true); setError('');
    try {
      await api.post(`/usuarios/${user.id}/biometria/${reenrollment ? 'reenrolar' : 'enrolar'}`, {
        fmd_template: fmdTemplate, challenge_id: challengeId, session_id: sessionId,
        motivo: reason.trim() || undefined,
      }, { headers: { 'Idempotency-Key': challengeId } });
      resetFmd();
      setSuccess(`Huella ${reenrollment ? 'actualizada' : 'registrada'} para ${user.nombre_completo || user.username}.`);
      await onSaved?.();
    } catch (failure) {
      setError(failure.response?.data?.detail || 'No se pudo registrar la huella. Revise el estado e intente de nuevo.');
      resetFmd();
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/60 p-3 sm:p-6" role="dialog" aria-modal="true" aria-labelledby="user-biometric-enrollment-title">
      <section className="w-full max-w-lg overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 bg-slate-50 px-5 py-4">
          <div>
            <h2 id="user-biometric-enrollment-title" className="font-bold text-slate-900">{reenrollment ? 'Actualizar huella digital' : 'Registrar huella digital'}</h2>
            <p className="mt-1 text-xs text-slate-600">{user.nombre_completo || user.username} · {user.username}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-200" aria-label="Cerrar"><FiX /></button>
        </header>
        <div className="space-y-4 p-5">
          {reenrollment && <label className="block text-sm font-semibold text-slate-700">Motivo de la actualización *<input value={reason} onChange={event => setReason(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 p-3 font-normal" maxLength={500} /></label>}
          <div className="rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between gap-3 text-sm text-slate-700">
              <span className="flex items-center gap-2 font-semibold"><MdFingerprint className="text-xl text-blue-700" />{status}</span>
              <span className="text-xs text-slate-500">{devices.length ? 'Lector disponible' : 'Conecte el lector'}</span>
            </div>
            {readerError && <p className="mt-2 text-xs text-red-700">{readerError}</p>}
            {fmdTemplate && <p className="mt-2 text-xs font-semibold text-emerald-700">Huella leída. Confirme para guardarla en la cuenta.</p>}
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={capture} disabled={!devices.length || isAcquiring || saving || (reenrollment && !reason.trim())} className="rounded-xl bg-blue-700 px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">
                {isAcquiring ? 'Leyendo huella…' : fmdTemplate ? 'Volver a leer' : 'Leer huella'}
              </button>
              {fmdTemplate && <button type="button" onClick={save} disabled={saving || (reenrollment && !reason.trim())} className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{saving ? 'Guardando…' : 'Guardar huella'}</button>}
            </div>
          </div>
          {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
          {success && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{success}</p>}
          <div className="flex justify-end"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Cerrar</button></div>
        </div>
      </section>
    </div>
  );
}

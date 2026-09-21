import { useState } from 'react';
import { useChangePassword } from '../hooks/useQueries';
import { useAuth } from '../context/AuthContext';
import Button from './ui/Button';
import AlertBanner from './ui/AlertBanner';

export default function PasswordChangeForm({ onComplete }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState(false);
  const change = useChangePassword();
  const { logout } = useAuth();
  const leave = async () => { await logout(); onComplete(); };
  const submit = async event => {
    event.preventDefault();
    if (change.isPending) return;
    setError('');
    if (next !== confirmation) { setError('Las contraseñas nuevas no coinciden.'); return; }
    try {
      const result = await change.mutateAsync({ current_password: current, new_password: next });
      if (result?.success !== true) throw new Error('No se confirmó el cambio de contraseña.');
      setCurrent(''); setNext(''); setConfirmation('');
      await logout();
      setCompleted(true);
    } catch (failure) {
      const detail = failure.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'No se pudo cambiar la contraseña. Compruebe la conexión e intente nuevamente.');
    } finally { change.reset(); }
  };
  return <main className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
    <form onSubmit={submit} className="w-full max-w-md bg-white rounded-2xl shadow p-8 space-y-5">
      <h1 className="text-2xl font-bold">Cambiar contraseña temporal</h1>
      {completed ? <>
        <AlertBanner type="success" message="Contraseña actualizada. Inicie sesión con la nueva contraseña." />
        <Button className="w-full" onClick={onComplete}>Volver al acceso</Button>
      </> : <>
        <p className="text-sm text-slate-600">Debe establecer una contraseña propia antes de utilizar Bitácora.</p>
        <AlertBanner title="Cambio de contraseña" message={error} />
        {[
          ['Contraseña actual', current, setCurrent, 'current-password'],
          ['Nueva contraseña', next, setNext, 'new-password'],
          ['Confirmar nueva contraseña', confirmation, setConfirmation, 'new-password'],
        ].map(([label, value, setter, autocomplete]) => <label key={label} className="block text-sm font-semibold">
          {label}<input className="mt-2 w-full border rounded-lg p-3" type="password" autoComplete={autocomplete} required value={value} onChange={event=>setter(event.target.value)} disabled={change.isPending} />
        </label>)}
        <p className="text-xs text-slate-500">Use al menos 14 caracteres, mayúsculas, minúsculas, números y un símbolo.</p>
        <Button type="submit" isLoading={change.isPending} className="w-full">Guardar contraseña</Button>
        <Button variant="secondary" onClick={leave} disabled={change.isPending} className="w-full">Volver al acceso</Button>
      </>}
    </form>
  </main>;
}

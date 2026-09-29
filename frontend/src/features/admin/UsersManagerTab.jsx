import { useState } from 'react';
import { api } from '../../api';
import Button from '../../components/ui/Button';
import AlertBanner from '../../components/ui/AlertBanner';
import { FiUserPlus, FiUsers, FiKey, FiEdit, FiTrash2 } from 'react-icons/fi';
import { MdFingerprint } from 'react-icons/md';
import { usePermissionCatalogQuery, useSaveUser } from '../../hooks/useQueries';
import { effectiveModules, parsePermissionValue, passwordHelp, validPassword } from '../../utils/permissions';
import UserBiometricEnrollmentModal from './UserBiometricEnrollmentModal';

const emptyUser = { username: '', password: '', rol: '', nombre_completo: '' };

export default function UsersManagerTab({ usuarios = [], rolActual = '', onRefresh }) {
  const catalog = usePermissionCatalogQuery();
  const save = useSaveUser();
  const [editingId, setEditingId] = useState(null);
  const [newUser, setNewUser] = useState(emptyUser);
  const [grants, setGrants] = useState({});
  const [formats, setFormats] = useState([]);
  const [signatureFormats, setSignatureFormats] = useState([]);
  const [biometricSigningEnabled, setBiometricSigningEnabled] = useState(false);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [biometricTarget, setBiometricTarget] = useState(null);
  const modules = catalog.data?.modules || [];
  const availableFormats = catalog.data?.formats || [];
  const groups = [...new Set(modules.map(item => item.group))];
  const normalizeSignatureRole = value => String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  const rolesById = Object.fromEntries((catalog.data?.roles || []).map(role => [normalizeSignatureRole(role.id), role.label]));
  const requiredRoles = item => item.firmas_especiales_requeridas || [];
  const requiredAreaLabel = item => requiredRoles(item).map(role => rolesById[normalizeSignatureRole(role)] || normalizeSignatureRole(role).replaceAll('_', ' ')).join(' / ');
  const eligibleSignatureFormats = availableFormats.filter(item => requiredRoles(item).some(role => normalizeSignatureRole(role) === normalizeSignatureRole(newUser.rol)));
  const displayedFormatName = item => requiredRoles(item).length ? `${item.nombre} (requiere firma de: ${requiredAreaLabel(item)})` : item.nombre;
  const canAssign = item => (!item.roles || item.roles.includes(newUser.rol)) && (!catalog.data?.role_limits[newUser.rol] || catalog.data.role_limits[newUser.rol].includes(item.id));
  const reset = () => { setEditingId(null); setNewUser(emptyUser); setGrants({}); setFormats([]); setSignatureFormats([]); setBiometricSigningEnabled(false); setSearch(''); };
  const selectRole = rol => {
    setNewUser(previous => ({ ...previous, rol }));
    setGrants(effectiveModules({ rol }));
    if (['rh', 'banco_sangre'].includes(rol)) setFormats([]);
    setSignatureFormats(previous => previous.filter(code => availableFormats.some(item => item.codigo === code && requiredRoles(item).some(required => normalizeSignatureRole(required) === normalizeSignatureRole(rol)))));
  };
  const edit = user => {
    setEditingId(user.id);
    setNewUser({ username: user.username, password: '', rol: user.rol, nombre_completo: user.nombre_completo || '' });
    setGrants(effectiveModules(user));
    const savedFormats = parsePermissionValue(user.formatos_permitidos, []);
    setFormats(user.formatos_permitidos == null ? availableFormats.map(item => item.codigo) : Array.isArray(savedFormats) ? savedFormats : []);
    const savedSignatureFormats = parsePermissionValue(user.formatos_firma_permitidos, []);
    const signable = Array.isArray(savedSignatureFormats) ? savedSignatureFormats : [];
    setSignatureFormats(signable);
    setBiometricSigningEnabled(signable.length > 0);
    setSuccess(''); setError('');
  };
  const submit = async event => {
    event.preventDefault();
    setError(''); setSuccess('');
    if (!editingId && !validPassword(newUser.password)) { setError(passwordHelp); return; }
    try {
      const payload = {
        rol: newUser.rol, nombre_completo: newUser.nombre_completo,
        permisos_modulos: JSON.stringify(Object.fromEntries(modules.map(item => [item.id, Boolean(grants[item.id] && canAssign(item))]))),
        formatos_permitidos: JSON.stringify(['rh', 'banco_sangre'].includes(newUser.rol) ? [] : formats),
        formatos_firma_permitidos: JSON.stringify(biometricSigningEnabled ? signatureFormats : []),
      };
      if (editingId) payload.id = editingId;
      else Object.assign(payload, { username: newUser.username.trim(), password: newUser.password });
      await save.mutateAsync(payload);
      setSuccess(editingId ? `Accesos de ${newUser.username} actualizados.` : `Usuario ${newUser.username} creado.`);
      reset();
      await onRefresh?.();
    } catch (failure) {
      const detail = failure.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'No se pudo guardar el usuario. Revise los datos e intente nuevamente.');
    }
  };
  const changePassword = async user => {
    const password = window.prompt(`Nueva contraseña para ${user.username}. ${passwordHelp}`);
    if (!password) return;
    if (!validPassword(password)) { setError(passwordHelp); return; }
    try {
      await api.put(`/usuarios/${user.id}/password`, { new_password: password });
      setSuccess('Contraseña restablecida. El usuario deberá cambiarla al ingresar.');
    } catch (failure) { setError(failure.response?.data?.detail || 'No se pudo restablecer la contraseña.'); }
  };
  const deleteUser = async user => {
    if (!window.confirm(`¿Eliminar a ${user.username}?`)) return;
    try { await api.delete(`/usuarios/${user.id}`); await onRefresh?.(); }
    catch (failure) { setError(failure.response?.data?.detail || 'No se pudo eliminar el usuario.'); }
  };
  const visibleFormats = availableFormats.filter(item => `${item.nombre} ${item.codigo} ${item.area || ''}`.toLowerCase().includes(search.toLowerCase()));

  return <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
    <section className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
      <h3 className="font-bold text-slate-800 flex items-center gap-2"><FiUserPlus /> {editingId ? 'Editar usuario y permisos' : 'Añadir Nuevo Usuario'}</h3>
      <p className="text-sm text-slate-500">Elija el rol y marque las áreas y formatos disponibles para esta persona.</p>
      <AlertBanner message={error} title="Revise los datos" />
      <AlertBanner type="success" message={success} />
      {catalog.isError && <AlertBanner message="No se pudo cargar el catálogo de permisos." onRetry={catalog.refetch} />}
      {catalog.isPending ? <p>Cargando áreas y formatos…</p> : <form onSubmit={submit} className="space-y-4 text-sm">
        <label className="block font-semibold">Nombre de usuario *
          <input required disabled={Boolean(editingId)} autoComplete="off" className="mt-1 w-full border rounded-xl p-2.5" value={newUser.username} onChange={event => setNewUser({ ...newUser, username: event.target.value })} />
        </label>
        <label className="block font-semibold">Nombre completo
          <input className="mt-1 w-full border rounded-xl p-2.5" value={newUser.nombre_completo} onChange={event => setNewUser({ ...newUser, nombre_completo: event.target.value })} />
        </label>
        {!editingId && <label className="block font-semibold">Contraseña *
          <input type="password" required minLength={8} autoComplete="new-password" className="mt-1 w-full border rounded-xl p-2.5" value={newUser.password} onChange={event => setNewUser({ ...newUser, password: event.target.value })} />
          <span className="block mt-1 text-xs font-normal text-slate-500">{passwordHelp}</span>
        </label>}
        <label className="block font-semibold">Rol en el hospital *
          <select required value={newUser.rol} onChange={event => selectRole(event.target.value)} className="mt-1 w-full border rounded-xl p-2.5 bg-white">
            <option value="">Seleccione un rol…</option>
            {(catalog.data?.roles || []).map(role => <option key={role.id} value={role.id}>{role.label}</option>)}
          </select>
        </label>
        {newUser.rol === 'rh' && <AlertBanner type="info" title="Acceso de Recursos Humanos" message="RH sólo puede acceder a Dashboard, Historial Global, Alta de Médicos, Directorio y Escaneos Diarios. Puede desmarcar cualquiera de estas áreas." />}
        <fieldset disabled={!newUser.rol || save.isPending} className="border rounded-xl p-4 bg-slate-50 space-y-4">
          <legend className="font-bold px-1">Permisos de áreas</legend>
          <div className="flex flex-wrap gap-3 text-xs">
            <button type="button" onClick={() => setGrants(Object.fromEntries(modules.map(item => [item.id, canAssign(item)])))}>Seleccionar disponibles</button>
            <button type="button" onClick={() => setGrants({})}>Quitar todos</button>
            <button type="button" onClick={() => setGrants(effectiveModules({ rol: newUser.rol }))}>Usar sugeridos del rol</button>
          </div>
          {groups.map(group => <div key={group}>
            <h4 className="font-semibold text-slate-500 text-xs mb-2">{group}</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {modules.filter(item => item.group === group).map(item => <label key={item.id} className={`flex items-center gap-2 ${canAssign(item) ? 'text-slate-700' : 'text-slate-400'}`}>
                <input type="checkbox" disabled={!canAssign(item)} checked={Boolean(grants[item.id] && canAssign(item))} onChange={event => setGrants({ ...grants, [item.id]: event.target.checked })} />{item.label}
              </label>)}
            </div>
          </div>)}
          <p className="text-xs text-slate-500">Las áreas nuevas se incorporan al catálogo y requieren que les conceda acceso.</p>
        </fieldset>
        <fieldset disabled={['rh', 'banco_sangre'].includes(newUser.rol) || save.isPending} className="border rounded-xl p-4 bg-slate-50 space-y-3">
          <legend className="font-bold px-1">Formatos clínicos permitidos ({formats.length})</legend>
          <input aria-label="Buscar formatos" placeholder="Buscar por nombre, código o área…" className="w-full border rounded-lg p-2" value={search} onChange={event => setSearch(event.target.value)} />
          <div className="flex gap-4 text-xs"><button type="button" onClick={() => setFormats(availableFormats.map(item => item.codigo))}>Seleccionar todos</button><button type="button" onClick={() => setFormats([])}>Quitar todos</button></div>
          <div className="max-h-72 overflow-y-auto space-y-2">
            {visibleFormats.map(item => <label key={item.codigo} className="flex items-start gap-2 text-xs text-slate-700">
              <input className="mt-1" type="checkbox" checked={formats.includes(item.codigo)} onChange={event => setFormats(event.target.checked ? [...formats, item.codigo] : formats.filter(code => code !== item.codigo))} />
              <span>{displayedFormatName(item)}<small className="block text-slate-400">{item.codigo}</small></span>
            </label>)}
            {!visibleFormats.length && <p className="text-slate-500">No hay formatos que coincidan.</p>}
          </div>
          <p className="text-xs text-slate-500">{newUser.rol === 'banco_sangre' ? 'Banco de Sangre consulta los documentos asignados para firma desde Firmas del área.' : 'Sin selección no se permite ningún formato. Para abrirlos también debe tener acceso al Expediente Clínico.'}</p>
        </fieldset>
        <fieldset disabled={!newUser.rol || save.isPending} className="border rounded-xl p-4 bg-white space-y-3">
          <legend className="font-bold px-1">Firma biométrica</legend>
          <label className="flex items-start gap-2 text-sm font-semibold text-slate-700">
            <input type="checkbox" checked={biometricSigningEnabled} onChange={event => { setBiometricSigningEnabled(event.target.checked); if (!event.target.checked) setSignatureFormats([]); }} />
            Habilitar esta cuenta para firmar con huella
          </label>
          {biometricSigningEnabled && <>
            <p className="text-xs text-slate-500">Seleccione los formatos que podrá revisar y firmar en la bandeja compartida. Active también el permiso Firmas del área. Desde la sesión de un médico, la persona puede firmar con su propia huella sin cerrar esa sesión.</p>
            <div className="max-h-64 overflow-y-auto space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
              {eligibleSignatureFormats.map(item => <label key={item.codigo} className="flex items-start gap-2 text-xs text-slate-700">
                <input className="mt-1" type="checkbox" checked={signatureFormats.includes(item.codigo)} onChange={event => setSignatureFormats(event.target.checked ? [...signatureFormats, item.codigo] : signatureFormats.filter(code => code !== item.codigo))} />
                <span>{displayedFormatName(item)}<small className="block text-slate-400">{item.codigo}</small></span>
              </label>)}
              {!eligibleSignatureFormats.length && <p className="text-xs text-slate-500">El catálogo no tiene formatos configurados para firma del área de {rolesById[normalizeSignatureRole(newUser.rol)] || newUser.rol}.</p>}
            </div>
          </>}
          {!biometricSigningEnabled && <p className="text-xs text-slate-500">La huella puede registrarse desde el botón del usuario. Para firmar, active esta opción y asigne al menos un formato.</p>}
        </fieldset>
        <Button type="submit" isLoading={save.isPending} disabled={catalog.isError} className="w-full">{editingId ? 'Guardar permisos' : 'Crear Usuario'}</Button>
        {editingId && <Button variant="secondary" onClick={reset}>Cancelar edición</Button>}
      </form>}
    </section>
    <section className="bg-white rounded-2xl border border-slate-200 p-6 h-fit">
      <h3 className="font-bold flex items-center gap-2 mb-4"><FiUsers /> Usuarios registrados ({usuarios.length})</h3>
      <div className="divide-y max-h-[720px] overflow-y-auto">
        {usuarios.map(user => <div key={user.id} className="py-4 flex flex-wrap justify-between items-center gap-3">
          <div><p className="font-bold">{user.username}</p><p className="text-xs text-slate-500">{user.nombre_completo} · {catalog.data?.roles.find(role => role.id === user.rol)?.label || user.rol}</p>
            <p className="mt-1 text-[11px] text-slate-500">Huella: {user.tiene_huella ? 'registrada' : user.biometric_status === 'SIN_BIOMETRIA' ? 'pendiente' : 'requiere actualización'} · Formatos asignados para firma: {Array.isArray(parsePermissionValue(user.formatos_firma_permitidos, [])) ? parsePermissionValue(user.formatos_firma_permitidos, []).length : 0}</p>
          </div>
          <div className="flex gap-1">
            {user.activo && ['admin', 'sistemas'].includes(rolActual) && <Button size="sm" variant="ghost" icon={<MdFingerprint />} onClick={() => setBiometricTarget({ user, reenrollment: user.biometric_status !== 'SIN_BIOMETRIA' })}>{user.biometric_status === 'SIN_BIOMETRIA' ? 'Huella digital' : 'Actualizar huella'}</Button>}
            <Button size="sm" variant="ghost" icon={<FiEdit />} disabled={!catalog.data} onClick={() => edit(user)}>Permisos</Button>
            <Button size="sm" variant="ghost" icon={<FiKey />} onClick={() => changePassword(user)}>Clave</Button>
            {rolActual === 'sistemas' && <Button size="sm" variant="danger" icon={<FiTrash2 />} onClick={() => deleteUser(user)}>Borrar</Button>}
          </div>
        </div>)}
      </div>
    </section>
    {biometricTarget && <UserBiometricEnrollmentModal
      open
      user={biometricTarget.user}
      reenrollment={biometricTarget.reenrollment}
      onClose={() => setBiometricTarget(null)}
      onSaved={async () => { await onRefresh?.(); setBiometricTarget(null); }}
    />}
  </div>;
}

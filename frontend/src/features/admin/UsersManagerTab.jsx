import React, { useState } from 'react';
import { api } from '../../api';
import Button from '../../components/ui/Button';
import { FiUserPlus, FiUsers, FiLock, FiTrash2, FiKey, FiDatabase, FiShield } from 'react-icons/fi';

/**
 * Pestaña de Gestión de Usuarios y Roles Institucionales.
 */
export default function UsersManagerTab({
  usuarios = [],
  formatosDisponibles = [],
  rolActual = '',
  onRefresh,
  onDownloadBackup
}) {
  const [newUser, setNewUser] = useState({
    username: '',
    password: '',
    rol: '',
    nombre_completo: ''
  });

  const [userPermsObj, setUserPermsObj] = useState({
    admin: false,
    rh: false,
    camas: false,
    agenda: false,
    ehr: false,
    captura_enfermeria: false,
    captura_medica: false
  });

  const [userFormatosArr, setUserFormatosArr] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const handleAddUser = async (e) => {
    e.preventDefault();
    if (!newUser.username || !newUser.password || !newUser.rol) {
      setErrorMsg("Ingrese usuario, contraseña y rol.");
      return;
    }
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await api.post('/usuarios', {
        ...newUser,
        permisos_modulos: JSON.stringify(userPermsObj),
        formatos_permitidos: JSON.stringify(userFormatosArr)
      });
      setSuccessMsg(`Usuario ${newUser.username} creado exitosamente.`);
      setNewUser({ username: '', password: '', rol: '', nombre_completo: '' });
      setUserPermsObj({ admin: false, rh: false, camas: false, agenda: false, ehr: false, captura_enfermeria: false, captura_medica: false });
      setUserFormatosArr([]);
      if (onRefresh) await onRefresh();
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Error al crear usuario.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteUser = async (id, username) => {
    if (!window.confirm(`¿Seguro que desea eliminar al usuario ${username}?`)) return;
    try {
      await api.delete(`/usuarios/${id}`);
      if (onRefresh) await onRefresh();
    } catch (err) {
      alert(err.response?.data?.detail || "Error al eliminar usuario.");
    }
  };

  const handleChangePassword = async (id, username) => {
    const newPass = prompt(`Ingrese la nueva contraseña para ${username}:`);
    if (!newPass) return;
    try {
      await api.put(`/usuarios/${id}/password`, { new_password: newPass });
      alert("Contraseña actualizada exitosamente.");
    } catch (err) {
      alert(err.response?.data?.detail || "Error al actualizar contraseña.");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      {/* Columna Izquierda: Formulario de Creación */}
      <div className="lg:col-span-6 bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
        <div>
          <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
            <FiUserPlus className="text-hes-blue-main" /> Añadir Nuevo Usuario
          </h3>
          <p className="text-xs text-slate-500">
            Configure credenciales, roles y permisos de acceso
          </p>
        </div>

        {errorMsg && (
          <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100 font-medium">
            {errorMsg}
          </div>
        )}
        {successMsg && (
          <div className="p-3 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100 font-medium">
            {successMsg}
          </div>
        )}

        <form onSubmit={handleAddUser} className="space-y-3 text-xs">
          <div>
            <label className="block font-bold text-slate-600 mb-1">Nombre de Usuario *</label>
            <input
              type="text"
              placeholder="ej. enfermeria_piso2"
              value={newUser.username}
              onChange={e => setNewUser({ ...newUser, username: e.target.value })}
              className="w-full border border-slate-200 rounded-xl p-2.5 outline-none focus:border-hes-blue-main font-semibold"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-600 mb-1">Contraseña *</label>
            <input
              type="password"
              placeholder="••••••••"
              value={newUser.password}
              onChange={e => setNewUser({ ...newUser, password: e.target.value })}
              className="w-full border border-slate-200 rounded-xl p-2.5 outline-none focus:border-hes-blue-main"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-600 mb-1">Rol en el Hospital *</label>
            <select
              value={newUser.rol}
              onChange={e => setNewUser({ ...newUser, rol: e.target.value })}
              className="w-full border border-slate-200 rounded-xl p-2.5 outline-none focus:border-hes-blue-main font-semibold bg-white"
            >
              <option value="">Selecciona un Rol...</option>
              <option value="enfermeria">Enfermería</option>
              <option value="nutricion">Nutrición</option>
              <option value="limpieza">Limpieza / Mantenimiento</option>
              <option value="laboratorio">Laboratorio</option>
              <option value="banco_sangre">Banco de Sangre</option>
              {(rolActual === 'admin' || rolActual === 'sistemas') && <option value="rh">Recursos Humanos (RH)</option>}
              {(rolActual === 'admin' || rolActual === 'sistemas') && <option value="admin">Administrador / Sistemas</option>}
            </select>
          </div>

          {/* Permisos de Módulos */}
          <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-2 mt-3">
            <h4 className="font-bold text-slate-700 text-xs">Permisos de Módulos</h4>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 text-slate-600 cursor-pointer">
                <input type="checkbox" checked={userPermsObj.admin} onChange={e => setUserPermsObj({ ...userPermsObj, admin: e.target.checked })} className="rounded text-hes-blue-main" />
                Admin Dashboard
              </label>
              <label className="flex items-center gap-2 text-slate-600 cursor-pointer">
                <input type="checkbox" checked={userPermsObj.rh} onChange={e => setUserPermsObj({ ...userPermsObj, rh: e.target.checked })} className="rounded text-hes-blue-main" />
                Recursos Humanos
              </label>
              <label className="flex items-center gap-2 text-slate-600 cursor-pointer">
                <input type="checkbox" checked={userPermsObj.agenda} onChange={e => setUserPermsObj({ ...userPermsObj, agenda: e.target.checked })} className="rounded text-hes-blue-main" />
                Agenda Médica
              </label>
              <label className="flex items-center gap-2 text-slate-600 cursor-pointer">
                <input type="checkbox" checked={userPermsObj.camas} onChange={e => setUserPermsObj({ ...userPermsObj, camas: e.target.checked })} className="rounded text-hes-blue-main" />
                Censo de Camas
              </label>
              <label className="flex items-center gap-2 text-slate-600 cursor-pointer">
                <input type="checkbox" checked={userPermsObj.ehr} onChange={e => setUserPermsObj({ ...userPermsObj, ehr: e.target.checked })} className="rounded text-hes-blue-main" />
                Expediente Clínico
              </label>
              <label className="flex items-center gap-2 text-slate-600 cursor-pointer">
                <input type="checkbox" checked={userPermsObj.captura_enfermeria} onChange={e => setUserPermsObj({ ...userPermsObj, captura_enfermeria: e.target.checked })} className="rounded text-hes-blue-main" />
                Captura Enfermería
              </label>
            </div>
          </div>

          {/* Formatos Permitidos */}
          <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-2 max-h-44 overflow-y-auto">
            <h4 className="font-bold text-slate-700 text-xs">Formatos Clínicos Permitidos</h4>
            <div className="space-y-1.5">
              {formatosDisponibles.map(f => (
                <label key={f.id} className="flex items-center gap-2 text-slate-600 text-[11px] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={userFormatosArr.includes(f.codigo)}
                    onChange={e => {
                      if (e.target.checked) setUserFormatosArr([...userFormatosArr, f.codigo]);
                      else setUserFormatosArr(userFormatosArr.filter(c => c !== f.codigo));
                    }}
                    className="rounded text-hes-blue-main"
                  />
                  <span>{f.nombre}</span> <span className="text-slate-400 font-mono">({f.codigo})</span>
                </label>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              isLoading={submitting}
              icon={<FiUserPlus />}
              className="w-full"
            >
              Crear Usuario
            </Button>
          </div>
        </form>
      </div>

      {/* Columna Derecha: Lista de Usuarios y Respaldo */}
      <div className="lg:col-span-6 space-y-6">
        
        {/* Respaldo Rápido */}
        {(rolActual === 'admin' || rolActual === 'sistemas') && onDownloadBackup && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-3">
            <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <FiDatabase className="text-hes-blue-main" /> Respaldo de Base de Datos
            </h3>
            <p className="text-xs text-slate-500">
              Descarga un volcado completo de la base de datos para custodia y auditoría externa.
            </p>
            <Button
              variant="secondary"
              icon={<FiDatabase />}
              onClick={onDownloadBackup}
              className="w-full"
            >
              Descargar Respaldo Ahora
            </Button>
          </div>
        )}

        {/* Lista de Usuarios */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <FiUsers className="text-hes-blue-main" /> Usuarios Registrados
            </h3>
            <span className="text-xs font-bold bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
              {usuarios.length} cuentas
            </span>
          </div>

          <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto pr-1">
            {usuarios.map(u => (
              <div key={u.id} className="py-3 flex justify-between items-center text-xs">
                <div>
                  <p className="font-bold text-slate-800 text-sm">{u.username}</p>
                  <span className="inline-block mt-0.5 px-2 py-0.5 rounded-md bg-blue-50 text-hes-blue-main font-bold uppercase text-[10px]">
                    {u.rol}
                  </span>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={<FiKey />}
                    onClick={() => handleChangePassword(u.id, u.username)}
                  >
                    Clave
                  </Button>
                  {rolActual === 'sistemas' && (
                    <Button
                      variant="danger"
                      size="sm"
                      icon={<FiTrash2 />}
                      onClick={() => handleDeleteUser(u.id, u.username)}
                    >
                      Borrar
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

    </div>
  );
}

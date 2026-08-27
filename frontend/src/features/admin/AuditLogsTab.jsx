import React, { useState } from 'react';
import { FiSearch, FiActivity, FiUser, FiClock } from 'react-icons/fi';

/**
 * Pestaña de Trazabilidad y Logs de Auditoría del Sistema.
 */
export default function AuditLogsTab({ logs = [] }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredLogs = logs.filter(log => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    const username = log.usuario?.username?.toLowerCase() || 'sistema';
    const accion = log.accion?.toLowerCase() || '';
    const detalles = log.detalles_json?.toLowerCase() || '';
    return username.includes(term) || accion.includes(term) || detalles.includes(term);
  });

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header y Buscador */}
      <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50/50">
        <div>
          <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
            <FiActivity className="text-hes-blue-main" /> Registro de Auditoría y Trazabilidad
          </h3>
          <p className="text-xs text-slate-500">
            Eventos de autenticación, firmas biométricas y modificaciones operativas
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <FiSearch className="absolute left-3 top-3 text-slate-400 text-sm" />
          <input
            type="text"
            placeholder="Buscar por usuario o acción..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-xl bg-white focus:border-hes-blue-main outline-none"
          />
        </div>
      </div>

      {/* Tabla de Logs */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wider border-b border-slate-200 font-bold">
              <th className="p-4">Fecha y Hora</th>
              <th className="p-4">Usuario</th>
              <th className="p-4">Acción</th>
              <th className="p-4">Detalles</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredLogs.map((log) => (
              <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                <td className="p-4 text-xs text-slate-600 whitespace-nowrap font-mono">
                  {new Date(log.fecha_hora + "Z").toLocaleString()}
                </td>
                <td className="p-4 text-xs font-semibold text-slate-800">
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                    <FiUser className="text-[10px]" />
                    {log.usuario ? log.usuario.username : 'Sistema'}
                  </span>
                </td>
                <td className="p-4 text-xs font-bold text-hes-blue-main">
                  {log.accion}
                </td>
                <td className="p-4 text-xs text-slate-600 max-w-lg truncate">
                  {log.detalles_json || '-'}
                </td>
              </tr>
            ))}

            {filteredLogs.length === 0 && (
              <tr>
                <td colSpan="4" className="p-12 text-center text-slate-400 text-xs">
                  No se encontraron registros de auditoría que coincidan con la búsqueda.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaUserMd, FaUserAlt, FaSearch, FaSync, FaExclamationTriangle, FaInfoCircle, FaBed, FaDoorOpen, FaLock, FaTrashAlt, FaTools, FaBroom, FaBell } from 'react-icons/fa';
import { FiFileText, FiArrowRight, FiX, FiFilter, FiGrid, FiList, FiBell } from 'react-icons/fi';
import { getApiUrl } from '../api';
import { useEscapeKey } from '../hooks/useEscapeKey';

const STATUS_CONFIG = {
  Ocupada: { color: 'red', bg: 'bg-red-50', border: 'border-red-100', text: 'text-red-700', icon: FaUserAlt, dot: 'bg-red-500', label: 'Ocupada' },
  Libre: { color: 'emerald', bg: 'bg-emerald-50', border: 'border-emerald-100', text: 'text-emerald-700', icon: FaDoorOpen, dot: 'bg-emerald-500', label: 'Disponible' },
  Inhabilitada: { color: 'slate', bg: 'bg-slate-50', border: 'border-slate-100', text: 'text-slate-600', icon: FaLock, dot: 'bg-slate-400', label: 'Inhabilitada' },
};

const CLEANING_STATUS_CONFIG = {
  'Disponible': { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-100', icon: FaBroom, label: 'Disponible' },
  'Limpia': { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-100', icon: FaBroom, label: 'Limpia' },
  'Sucia': { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-100', icon: FaTrashAlt, label: 'Sucia' },
  'En proceso de limpieza': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-100', icon: FaBroom, label: 'En limpieza' },
  'En mantenimiento': { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-100', icon: FaTools, label: 'Mantenimiento' },
  'Fuera de servicio': { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200', icon: FaLock, label: 'Fuera de servicio' },
};

const GROUP_CONFIG = {
  'PPB (Planta Baja)': { icon: '🏢', color: 'blue' },
  'PPA (Planta Alta)': { icon: '🏢', color: 'indigo' },
  'Urgencias': { icon: '🚑', color: 'red' },
  'Quirófanos': { icon: '🏥', color: 'purple' },
  'Terapia Intensiva': { icon: '🩺', color: 'pink' },
  'Corta Estancia': { icon: '⏱️', color: 'orange' },
  'Otras Áreas': { icon: '📍', color: 'slate' },
  'Camas Virtuales': { icon: '☁️', color: 'cyan' },
};

const SkeletonCard = () => (
  <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 animate-pulse h-full">
    <div className="flex justify-between items-start mb-3">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-slate-200"></div>
        <div className="h-4 w-24 bg-slate-200 rounded"></div>
      </div>
      <div className="h-5 w-20 bg-slate-200 rounded"></div>
    </div>
    <div className="space-y-2">
      <div className="h-4 w-3/4 bg-slate-200 rounded"></div>
      <div className="h-4 w-1/2 bg-slate-200 rounded"></div>
      <div className="h-4 w-5/6 bg-slate-200 rounded"></div>
    </div>
  </div>
);

const StatusBadge = ({ status, size = 'sm' }) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.Libre;
  const Icon = config.icon;
  const sizes = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-3 py-1 text-xs',
    lg: 'px-4 py-1.5 text-sm',
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-semibold border ${sizes[size]} ${config.bg} ${config.border} ${config.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`}></span>
      {config.label}
    </span>
  );
};

const CleaningBadge = ({ status, size = 'sm' }) => {
  if (!status) return null;
  const config = CLEANING_STATUS_CONFIG[status] || CLEANING_STATUS_CONFIG['Disponible'];
  const Icon = config.icon;
  const sizes = {
    sm: 'px-1.5 py-0.5 text-[9px]',
    md: 'px-2 py-0.5 text-[10px]',
    lg: 'px-3 py-1 text-xs',
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded font-semibold border ${sizes[size]} ${config.bg} ${config.border} ${config.text}`}>
      <Icon className="w-2.5 h-2.5" />
      {config.label}
    </span>
  );
};

const BedCard = ({ cama, onClick, isLimpiezaRole, isEnfermeriaRole, navigate }) => {
  const statusConfig = STATUS_CONFIG[cama.Estatus] || STATUS_CONFIG.Libre;
  const isOcupada = cama.Estatus === 'Ocupada';
  const isInhabilitada = cama.Estatus === 'Inhabilitada';
  const isLibre = cama.Estatus === 'Libre';
  
  const cleaningStatus = cama.estado_limpieza;
  const cleaningConfig = cleaningStatus ? CLEANING_STATUS_CONFIG[cleaningStatus] : null;
  const isClean = cleaningStatus && (cleaningStatus.toLowerCase() === 'disponible' || cleaningStatus.toLowerCase() === 'limpia');
  
  let showCleaningBadge = false;
  if (cleaningStatus) {
    if (isClean) {
      showCleaningBadge = !isOcupada && (isLimpiezaRole || isEnfermeriaRole);
    } else {
      showCleaningBadge = true;
    }
  }

  const handleClick = (e) => {
    if (e.target.closest('button, select, a')) return;
    onClick(cama);
  };

  const handleEHRClick = (e, ptNum) => {
    e.stopPropagation();
    navigate(`/ehr/${ptNum}`);
  };

  const handleCapturaClick = (e) => {
    e.stopPropagation();
    navigate('/captura', {
      state: {
        habitacion: cama.RoomName || cama.RoomCode,
        pacienteNombre: cama.PatientName || '',
        ptNum: cama.PTNum || '',
        medicoTratante: cama.DoctorName || '',
      }
    });
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`relative group bg-white rounded-xl shadow-sm border transition-all duration-200 hover:shadow-lg hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-hes-blue-main/20 focus:ring-offset-2 ${isOcupada ? 'border-red-100' : isInhabilitada ? 'border-slate-200' : 'border-emerald-100'} ${cleaningConfig && !isClean ? cleaningConfig.bg + '/50' : ''}`}
      style={{ minHeight: '160px' }}
      aria-label={`Cama ${cama.RoomName}, estado ${cama.Estatus}${cleaningStatus ? `, limpieza ${cleaningStatus}` : ''}`}
    >
      <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {isOcupada && cama.PTNum && !isLimpiezaRole && (
          <button
            onClick={(e) => handleEHRClick(e, cama.PTNum)}
            className="p-1.5 bg-white/90 hover:bg-slate-100 rounded-lg shadow-sm transition-colors"
            aria-label="Ver expediente clínico"
            title="Ver expediente clínico"
          >
            <FiFileText className="w-4 h-4 text-slate-500" />
          </button>
        )}
        {isLibre && (
          <button
            onClick={handleCapturaClick}
            className="p-1.5 bg-white/90 hover:bg-slate-100 rounded-lg shadow-sm transition-colors"
            aria-label="Ingresar paciente"
            title="Ingresar paciente"
          >
            <FiArrowRight className="w-4 h-4 text-emerald-500" />
          </button>
        )}
      </div>

      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${statusConfig.dot}`} aria-hidden="true"></span>
          <h3 className="text-sm font-semibold text-slate-800 truncate max-w-[120px]" title={cama.RoomName}>
            {cama.RoomName}
          </h3>
        </div>
        <StatusBadge status={cama.Estatus} size="sm" />
      </div>

      <div className="flex items-center justify-between mb-2">
        {showCleaningBadge && cleaningConfig && (
          <CleaningBadge status={cleaningStatus} size="sm" />
        )}
        {!showCleaningBadge && cleaningConfig && isClean && !isOcupada && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-semibold rounded border bg-emerald-50 text-emerald-700 border-emerald-100">
            <FaBroom className="w-2.5 h-2.5" />
            Lista
          </span>
        )}
      </div>

      <div className="flex-1 flex flex-col justify-center min-h-[60px]">
        {isOcupada ? (
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <statusConfig.icon className="mt-0.5 flex-shrink-0 text-slate-400 text-[11px]" aria-hidden="true" />
              <span className="text-xs text-slate-800 font-medium leading-tight truncate block">
                {isLimpiezaRole ? "*** Paciente Oculto ***" : cama.PatientName || 'Sin nombre'}
              </span>
            </div>
            {cama.DoctorName && !isLimpiezaRole && (
              <div className="flex items-start gap-2">
                <FaUserMd className="mt-0.5 flex-shrink-0 text-slate-400 text-[11px]" aria-hidden="true" />
                <span className="text-[11px] text-slate-500 leading-tight truncate block">{cama.DoctorName}</span>
              </div>
            )}
            {cama.PTNum && !isLimpiezaRole && (
              <button
                onClick={(e) => handleEHRClick(e, cama.PTNum)}
                className="mt-2 flex items-center justify-center gap-1.5 w-full py-1.5 px-2 bg-white hover:bg-slate-50 text-slate-600 rounded-lg text-[11px] font-medium border border-slate-200 hover:border-slate-300 transition-all shadow-sm"
              >
                <FiFileText className="text-xs text-slate-400" />
                <span>Expediente</span>
              </button>
            )}
          </div>
        ) : isInhabilitada ? (
          <div className="flex items-center gap-1.5 text-xs text-slate-500 py-2">
            <FaLock className="text-slate-400 text-[11px]" aria-hidden="true" />
            <span>No disponible</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-xs text-slate-500 py-2">
            <FaDoorOpen className="text-emerald-400 text-[11px]" aria-hidden="true" />
            <span className="font-medium text-emerald-600">Disponible para ingreso</span>
          </div>
        )}
      </div>

      {cama.RoomCode && (
        <div className="mt-3 pt-2 border-t border-slate-100">
          <span className="text-[10px] text-slate-400 font-mono">{cama.RoomCode}</span>
        </div>
      )}
    </button>
  );
};

const PatientTimelineModal = ({ cama, timelineData, loadingTimeline, onClose, onEHR, onCaptura }) => {
  if (!cama) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fade-in" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh] animate-slide-up">
        <div className="p-4 bg-gradient-to-r from-hes-blue-main to-hes-blue-cross text-white flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <FaUserAlt className="w-5 h-5" />
            </div>
            <div>
              <h2 id="modal-title" className="text-xl font-bold">{cama.PatientName}</h2>
              <p className="text-xs text-blue-100">{cama.RoomName} • {cama.Estatus}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-white/10 rounded-lg transition-colors" aria-label="Cerrar">
            <FiX className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {loadingTimeline ? (
            <div className="flex justify-center p-8">
              <div className="animate-spin h-8 w-8 border-4 border-hes-blue-main border-t-transparent rounded-full"></div>
            </div>
          ) : (
            <div className="space-y-6">
              {timelineData?.demographics && (
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-5 rounded-xl border border-blue-100">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center shadow-sm">
                      <FiInfoCircle className="w-4 h-4 text-hes-blue-main" />
                    </div>
                    <h3 className="font-semibold text-hes-blue-main">Ficha Rápida</h3>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                    <div>
                      <p className="text-slate-500 text-xs uppercase tracking-wide">Edad / Nac.</p>
                      <p className="font-medium text-slate-800">{timelineData.demographics.BirthDate ? new Date(timelineData.demographics.BirthDate).toLocaleDateString('es-MX') : 'N/D'}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 text-xs uppercase tracking-wide">Sexo</p>
                      <p className="font-medium text-slate-800">{timelineData.demographics.Gender || 'N/D'}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 text-xs uppercase tracking-wide">Tipo Sangre</p>
                      <p className="font-bold text-red-600">{timelineData.demographics.BloodType || 'N/D'}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 text-xs uppercase tracking-wide">Religión</p>
                      <p className="font-medium text-slate-800">{timelineData.demographics.Religion || 'N/D'}</p>
                    </div>
                  </div>
                </div>
              )}

              {timelineData?.timeline && timelineData.timeline.length > 0 && (
                <div>
                  <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
                    <FaBed className="w-5 h-5 text-hes-blue-main" />
                    Línea de Tiempo (Journey)
                  </h3>
                  <div className="relative pl-4 border-l border-slate-200">
                    {timelineData.timeline.map((item, idx) => (
                      <div key={idx} className="relative pb-6 last:pb-0">
                        <div className="absolute left-[-8px] top-0 w-3 h-3 rounded-full bg-hes-blue-main border-3 border-white shadow-sm z-10" />
                        <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow ml-1">
                          <div className="flex justify-between items-start mb-2">
                            <div className="font-bold text-slate-800 text-sm">{item.RoomName}</div>
                            <span className="text-xs text-slate-400 whitespace-nowrap">
                              {idx === 0 ? 'Actual' : `#${timelineData.timeline.length - idx}`}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-1 text-xs text-slate-500">
                            <div>
                              <span className="text-slate-400">Entrada:</span>
                              <span className="ml-1 font-mono">{new Date(item.EntryDate).toLocaleString('es-MX')}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">Salida:</span>
                              <span className="ml-1 font-mono">{item.ExitDate ? new Date(item.ExitDate).toLocaleString('es-MX') : 'Actual'}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!timelineData?.timeline || timelineData.timeline.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <FaInfoCircle className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                  <p className="text-sm">No hay historial de movimientos para este paciente</p>
                </div>
              ) : null}
            </div>
          )}
        </div>

        <div className="p-4 border-t bg-slate-50 flex flex-wrap justify-end gap-2.5">
          <button onClick={onClose} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg transition-colors">Cerrar</button>
          <button onClick={() => { onClose(); onEHR(cama.PTNum); }} className="px-4 py-2 bg-hes-blue-main text-white font-bold hover:bg-hes-blue-cross rounded-lg shadow-sm transition-colors flex items-center gap-1.5">
            <FiFileText className="w-4 h-4" />
            <span>Ver Expediente (EHR)</span>
          </button>
          <button onClick={() => { onClose(); onCaptura(cama); }} className="px-4 py-2 bg-hes-green text-white font-medium hover:bg-green-700 rounded-lg shadow-sm transition-colors">
            Continuar a Captura
          </button>
        </div>
      </div>
    </div>
  );
};

const CleaningModal = ({ cama, estadoLimpieza, setEstadoLimpieza, notasLimpieza, setNotasLimpieza, savingLimpieza, onSave, onClose }) => {
  if (!cama) return null;

  const config = CLEANING_STATUS_CONFIG[estadoLimpieza] || CLEANING_STATUS_CONFIG['Disponible'];
  const requiresNotes = ['En mantenimiento', 'Fuera de servicio'].includes(estadoLimpieza);
  const Icon = config.icon;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fade-in" role="dialog" aria-modal="true" aria-labelledby="cleaning-modal-title">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col animate-slide-up">
        <div className="p-4 bg-gradient-to-r from-yellow-500 to-amber-500 text-white flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h2 id="cleaning-modal-title" className="text-xl font-bold">Estado de Limpieza</h2>
              <p className="text-xs text-yellow-100">{cama.RoomName}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-white/10 rounded-lg transition-colors" aria-label="Cerrar">
            <FiX className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          <label className="block text-sm font-semibold text-slate-700 mb-2">Estado de la cama</label>
          <div className="relative">
            <select
              value={estadoLimpieza}
              onChange={(e) => setEstadoLimpieza(e.target.value)}
              className="w-full appearance-none border border-slate-300 rounded-xl py-3 pl-4 pr-10 bg-white focus:outline-none focus:ring-2 focus:ring-hes-blue-main focus:border-transparent transition-all text-sm"
            >
              {Object.entries(CLEANING_STATUS_CONFIG).map(([key, cfg]) => (
                <option key={key} value={key}>
                  {cfg.icon ? <span key={key} className="inline-block mr-2" role="img" aria-label={cfg.label}>{cfg.icon === FaBroom ? '🧹' : cfg.icon === FaTrashAlt ? '🗑️' : cfg.icon === FaTools ? '🔧' : cfg.icon === FaLock ? '🔒' : ''}</span> : ''} {key}
                </option>
              ))}
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              <FiFilter className="w-4 h-4" />
            </div>
          </div>

          {requiresNotes && (
            <div className="mt-4 animate-slide-down">
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Motivo ({estadoLimpieza}): <span className="text-red-500">*</span>
              </label>
              <textarea
                value={notasLimpieza}
                onChange={(e) => setNotasLimpieza(e.target.value)}
                className="w-full border border-slate-300 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-hes-blue-main focus:border-transparent transition-all text-sm resize-none"
                rows="3"
                placeholder="Describa el motivo del mantenimiento o por qué está fuera de servicio..."
                required
                aria-required="true"
              />
              <p className="text-xs text-slate-400 mt-1">Mínimo 10 caracteres</p>
            </div>
          )}

          {!requiresNotes && cleaningStatus && (
            <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="text-sm text-slate-600">
                <span className="font-medium">Estado actual:</span> {cleaningStatus}
              </p>
            </div>
          )}
        </div>

        <div className="p-4 border-t bg-slate-50 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg transition-colors">Cancelar</button>
          <button
            onClick={onSave}
            disabled={savingLimpieza || (requiresNotes && notasLimpieza.trim().length < 10)}
            className="px-4 py-2 bg-yellow-500 text-white font-medium hover:bg-yellow-600 rounded-lg shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {savingLimpieza ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                Guardando...
              </>
            ) : (
              'Guardar cambios'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

const GroupHeader = ({ groupName, count }) => {
  const config = GROUP_CONFIG[groupName] || { icon: '📍', color: 'slate' };
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700 border-blue-100',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-100',
    red: 'bg-red-50 text-red-700 border-red-100',
    purple: 'bg-purple-50 text-purple-700 border-purple-100',
    pink: 'bg-pink-50 text-pink-700 border-pink-100',
    orange: 'bg-orange-50 text-orange-700 border-orange-100',
    slate: 'bg-slate-50 text-slate-700 border-slate-100',
    cyan: 'bg-cyan-50 text-cyan-700 border-cyan-100',
  };
  const classes = colorClasses[config.color] || colorClasses.slate;

  return (
    <div className="mb-6">
      <h2 className="flex items-center gap-3 mb-4">
        <span className="text-xl">{config.icon}</span>
        <span className="text-lg font-semibold text-slate-800">{groupName}</span>
        <span className={`ml-auto px-3 py-1 text-xs font-bold rounded-full border ${classes}`}>
          {count} cama{count !== 1 ? 's' : ''}
        </span>
      </h2>
    </div>
  );
};

const EmptyState = ({ title, description, icon: Icon, action }) => (
  <div className="col-span-full flex flex-col items-center justify-center py-16 px-4 text-center">
    <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
      <Icon className="w-8 h-8 text-slate-400" />
    </div>
    <h3 className="text-lg font-semibold text-slate-700 mb-1">{title}</h3>
    <p className="text-sm text-slate-500 mb-6 max-w-sm">{description}</p>
    {action && (
      <button onClick={action} className="px-4 py-2 bg-hes-blue-main text-white font-medium rounded-lg hover:bg-hes-blue-cross transition-colors flex items-center gap-2">
        <FiSync className="w-4 h-4" />
        {action.label || 'Reintentar'}
      </button>
    )}
  </div>
);

const CamasDashboard = () => {
  const [camas, setCamas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [viewMode, setViewMode] = useState('grid');
  const [selectedGroup, setSelectedGroup] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCama, setSelectedCama] = useState(null);
  const [timelineData, setTimelineData] = useState(null);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  const [modalLimpiezaOpen, setModalLimpiezaOpen] = useState(false);
  const [estadoLimpieza, setEstadoLimpieza] = useState("Disponible");
  const [notasLimpieza, setNotasLimpieza] = useState("");
  const [savingLimpieza, setSavingLimpieza] = useState(false);

  const currentUserRole = localStorage.getItem('rol');
  const isLimpiezaRole = currentUserRole === 'Mantenimiento/Limpieza' || currentUserRole === 'limpieza';
  const isEnfermeriaRole = currentUserRole === 'enfermeria';

  const navigate = useNavigate();

  useEscapeKey(modalOpen && selectedCama, () => setModalOpen(false));
  useEscapeKey(modalLimpiezaOpen && selectedCama, () => setModalLimpiezaOpen(false));

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const fetchCamas = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${getApiUrl()}/camas`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Error al cargar camas');
      const data = await response.json();
      setCamas(Array.isArray(data) ? data : []);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCamas();
    const interval = setInterval(fetchCamas, 30000);
    return () => clearInterval(interval);
  }, [fetchCamas]);

  const handleCamaClick = useCallback(async (cama) => {
    if (isLimpiezaRole) {
      setSelectedCama(cama);
      setEstadoLimpieza(cama.estado_limpieza || "Disponible");
      setNotasLimpieza(cama.notas_limpieza || "");
      setModalLimpiezaOpen(true);
      return;
    }

    if (cama.PTNum) {
      setSelectedCama(cama);
      setModalOpen(true);
      setLoadingTimeline(true);
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${getApiUrl()}/camas/paciente/${cama.PTNum}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        setTimelineData(data);
      } catch (e) {
        console.error("Error fetching timeline:", e);
      }
      setLoadingTimeline(false);
    } else {
      navigate('/captura', {
        state: {
          habitacion: cama.RoomName || cama.RoomCode,
          pacienteNombre: cama.PatientName || '',
          ptNum: cama.PTNum || '',
          medicoTratante: cama.DoctorName || '',
        }
      });
    }
  }, [isLimpiezaRole, navigate]);

  const handleGuardarLimpieza = useCallback(async () => {
    if ((estadoLimpieza === "En mantenimiento" || estadoLimpieza === "Fuera de servicio") && notasLimpieza.trim().length < 10) {
      alert(`Debe escribir un motivo (mín. 10 caracteres) si el estado es '${estadoLimpieza}'`);
      return;
    }

    setSavingLimpieza(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${getApiUrl()}/camas/${selectedCama.RoomName}/limpieza`, {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          estado_limpieza: estadoLimpieza,
          notas_limpieza: notasLimpieza
        })
      });
      if (res.ok) {
        setModalLimpiezaOpen(false);
        fetchCamas();
      } else {
        alert("Error al actualizar estado");
      }
    } catch (e) {
      console.error(e);
      alert("Error de red");
    }
    setSavingLimpieza(false);
  }, [estadoLimpieza, notasLimpieza, selectedCama, fetchCamas]);

  const groupCamas = useCallback((camasList) => {
    const groups = {
      'PPB (Planta Baja)': [],
      'PPA (Planta Alta)': [],
      'Urgencias': [],
      'Quirófanos': [],
      'Terapia Intensiva': [],
      'Corta Estancia': [],
      'Otras Áreas': [],
      'Camas Virtuales': []
    };

    camasList.forEach(cama => {
      const name = (cama.RoomName || '').toUpperCase();
      const code = (cama.RoomCode || '').toUpperCase();
      
      if (name.includes('VIRTUAL')) {
        groups['Camas Virtuales'].push(cama);
      } else if (name.includes('URGENCIA') || code.includes('URG') || code.includes('CONSCUR')) {
        groups['Urgencias'].push(cama);
      } else if (name.includes('QUIR')) {
        groups['Quirófanos'].push(cama);
      } else if (name.includes('TERAPIA') || code.includes('UTI') || name.includes('CUBICULO')) {
        groups['Terapia Intensiva'].push(cama);
      } else if (name.includes('CORTA ESTANCIA') || name.includes('CE')) {
        groups['Corta Estancia'].push(cama);
      } else if (name.includes(' 10') || code.includes('PB') || code.includes('10')) {
        groups['PPB (Planta Baja)'].push(cama);
      } else if (name.includes(' 20') || code.includes('PA') || code.includes('20')) {
        groups['PPA (Planta Alta)'].push(cama);
      } else {
        groups['Otras Áreas'].push(cama);
      }
    });

    for (const key in groups) {
      groups[key].sort((a, b) => (a.RoomName || '').localeCompare(b.RoomName || ''));
    }

    return groups;
  }, []);

  const filteredCamas = useMemo(() => {
    if (!debouncedSearch) return camas;
    const term = debouncedSearch.toLowerCase();
    return camas.filter(c => 
      (c.RoomName && c.RoomName.toLowerCase().includes(term)) ||
      (c.RoomCode && c.RoomCode.toLowerCase().includes(term)) ||
      (c.PatientName && c.PatientName.toLowerCase().includes(term)) ||
      (c.PTNum && c.PTNum.toLowerCase().includes(term))
    );
  }, [camas, debouncedSearch]);

  const groupedCamas = useMemo(() => groupCamas(filteredCamas), [groupCamas, filteredCamas]);
  
  const stats = useMemo(() => ({
    total: camas.length,
    libres: camas.filter(c => c.Estatus === 'Libre').length,
    ocupadas: camas.filter(c => c.Estatus === 'Ocupada').length,
    inhabilitadas: camas.filter(c => c.Estatus === 'Inhabilitada').length,
    sucias: camas.filter(c => c.estado_limpieza?.toLowerCase() === 'sucia').length,
    mantenimiento: camas.filter(c => c.estado_limpieza?.toLowerCase() === 'en mantenimiento').length,
  }), [camas]);

  const camasProblematicas = useMemo(() => 
    camas.filter(c => {
      if (!c.estado_limpieza) return false;
      const estado = c.estado_limpieza.toLowerCase();
      return c.Estatus === 'Ocupada' && estado !== 'disponible' && estado !== 'limpia';
    })
  , [camas]);

  const visibleGroups = useMemo(() => 
    Object.entries(groupedCamas).filter(([, list]) => list.length > 0)
  , [groupedCamas]);

  if (loading && camas.length === 0) {
    return (
      <div className="w-full p-6 pb-10 bg-slate-50/50 min-h-screen">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {[...Array(10)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full p-6 pb-10 bg-slate-50/50 min-h-screen">
      <style jsx>{`
        @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slide-up { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slide-down { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade-in { animation: fade-in 0.2s ease-out; }
        .animate-slide-up { animation: slide-up 0.25s ease-out; }
        .animate-slide-down { animation: slide-down 0.2s ease-out; }
      `}</style>

      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800 tracking-tight flex items-center gap-2">
            <FaBed className="w-6 h-6 text-hes-blue-main" />
            Ocupación de Camas
          </h1>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5 flex-wrap">
            <span className="flex items-center gap-1">
              <FaInfoCircle className="w-3 h-3" />
              Fuente: V_MRPT & PC
            </span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1 text-emerald-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Auto-refresh (30s)
            </span>
            {lastUpdate && (
              <>
                <span className="text-slate-300">•</span>
                <span>Actualizado: {lastUpdate.toLocaleTimeString('es-MX', { hour: '2-digit', minute:'2-digit' })}</span>
              </>
            )}
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full lg:w-auto">
          <div className="relative w-full sm:w-72">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <FaSearch className="w-4 h-4" />
            </div>
            <input
              type="text"
              placeholder="Buscar cama, paciente, código..."
              className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-xl text-sm bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-hes-blue-main/20 focus:border-hes-blue-main transition-all shadow-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="Buscar camas"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-1 bg-white border border-slate-200 rounded-xl p-1" role="group" aria-label="Vista">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-lg transition-colors ${viewMode === 'grid' ? 'bg-hes-blue-main text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                aria-label="Vista cuadrícula"
                aria-pressed={viewMode === 'grid'}
              >
                <FiGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-lg transition-colors ${viewMode === 'list' ? 'bg-hes-blue-main text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                aria-label="Vista lista"
                aria-pressed={viewMode === 'list'}
              >
                <FiList className="w-4 h-4" />
              </button>
            </div>

            <div className="flex gap-1.5 text-xs font-medium overflow-x-auto pb-1">
              <StatPill label="Total" value={stats.total} variant="default" />
              <StatPill label="Libres" value={stats.libres} variant="success" />
              <StatPill label="Ocupadas" value={stats.ocupadas} variant="danger" />
              {stats.inhabilitadas > 0 && <StatPill label="Inhab." value={stats.inhabilitadas} variant="secondary" />}
              {stats.sucias > 0 && <StatPill label="Sucias" value={stats.sucias} variant="warning" />}
              {stats.mantenimiento > 0 && <StatPill label="Mant." value={stats.mantenimiento} variant="warning" />}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl mb-6 shadow-sm text-sm flex items-center gap-2" role="alert">
          <FaExclamationTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={fetchCamas} className="ml-auto px-3 py-1 text-xs bg-red-100 hover:bg-red-200 rounded-lg font-medium">Reintentar</button>
        </div>
      )}

      {camasProblematicas.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 p-4 mb-6 shadow-sm rounded-xl flex items-start gap-3" role="alert">
          <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
            <FaBell className="w-4 h-4" />
          </div>
          <div>
            <p className="font-semibold text-sm">Notificación de Mantenimiento / Limpieza</p>
            <p className="text-xs text-amber-700 mt-0.5">
              Hay <strong>{camasProblematicas.length}</strong> cama{camasProblematicas.length !== 1 ? 's' : ''} con paciente registrado 
              cuyo estado de limpieza <strong>NO es "Disponible"</strong>.
            </p>
          </div>
        </div>
      )}

      {/* Bed Groups */}
      <div className="space-y-8">
        {visibleGroups.length === 0 ? (
          <EmptyState
            title="No se encontraron camas"
            description={debouncedSearch ? `No hay camas que coincidan con "${debouncedSearch}"` : 'No hay camas registradas en el sistema'}
            icon={FaBed}
            action={{ label: 'Limpiar búsqueda', onClick: () => setSearchTerm('') }}
          />
        ) : (
          visibleGroups.map(([groupName, groupCamasList]) => (
            <div key={groupName}>
              <GroupHeader groupName={groupName} count={groupCamasList.length} />
              
              <div className={`grid gap-3 ${
                viewMode === 'grid' 
                  ? 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5' 
                  : 'grid-cols-1'
              }`}>
                {groupCamasList.map((cama, index) => (
                  <BedCard
                    key={`${cama.RoomName}-${index}`}
                    cama={cama}
                    onClick={handleCamaClick}
                    isLimpiezaRole={isLimpiezaRole}
                    isEnfermeriaRole={isEnfermeriaRole}
                    navigate={navigate}
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {modalOpen && (
        <PatientTimelineModal
          cama={selectedCama}
          timelineData={timelineData}
          loadingTimeline={loadingTimeline}
          onClose={() => { setModalOpen(false); setSelectedCama(null); setTimelineData(null); }}
          onEHR={(ptNum) => navigate(`/ehr/${ptNum}`)}
          onCaptura={(cama) => navigate('/captura', {
            state: {
              habitacion: cama.RoomName || cama.RoomCode,
              pacienteNombre: cama.PatientName || '',
              ptNum: cama.PTNum || '',
              medicoTratante: cama.DoctorName || '',
            }
          })}
        />
      )}

      {modalLimpiezaOpen && (
        <CleaningModal
          cama={selectedCama}
          estadoLimpieza={estadoLimpieza}
          setEstadoLimpieza={setEstadoLimpieza}
          notasLimpieza={notasLimpieza}
          setNotasLimpieza={setNotasLimpieza}
          savingLimpieza={savingLimpieza}
          onSave={handleGuardarLimpieza}
          onClose={() => { setModalLimpiezaOpen(false); setSelectedCama(null); }}
        />
      )}
    </div>
  );
};

const StatPill = ({ label, value, variant }) => {
  const variants = {
    default: 'bg-slate-50 border-slate-200 text-slate-600',
    success: 'bg-emerald-50 border-emerald-100 text-emerald-700',
    danger: 'bg-red-50 border-red-100 text-red-700',
    warning: 'bg-amber-50 border-amber-100 text-amber-700',
    secondary: 'bg-slate-100 border-slate-200 text-slate-700',
  };
  return (
    <div className={`px-2.5 py-1.5 rounded-lg border whitespace-nowrap ${variants[variant]}`} role="status" aria-live="polite">
      <span className="font-semibold">{value}</span>
      <span className="ml-1 text-[10px] opacity-75">{label}</span>
    </div>
  );
};

export default CamasDashboard;
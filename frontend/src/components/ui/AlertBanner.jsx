import React from 'react';
import { FiAlertCircle, FiAlertTriangle, FiCheckCircle, FiInfo, FiRefreshCw, FiX } from 'react-icons/fi';

/**
 * Componente AlertBanner para retroalimentación visual de errores, advertencias y caídas de API (ej: 503).
 */
export default function AlertBanner({ 
  message, 
  type = 'error', 
  title,
  onRetry, 
  onClose,
  className = ''
}) {
  if (!message) return null;

  const styles = {
    error: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      text: 'text-red-800',
      desc: 'text-red-700',
      icon: <FiAlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />,
      defaultTitle: 'Error de Conexión / Sistema'
    },
    warning: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      text: 'text-amber-800',
      desc: 'text-amber-700',
      icon: <FiAlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />,
      defaultTitle: 'Aviso de Disponibilidad'
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      text: 'text-blue-800',
      desc: 'text-blue-700',
      icon: <FiInfo className="w-5 h-5 text-blue-500 flex-shrink-0" />,
      defaultTitle: 'Información del Sistema'
    },
    success: {
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      text: 'text-emerald-800',
      desc: 'text-emerald-700',
      icon: <FiCheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0" />,
      defaultTitle: 'Operación Exitosa'
    }
  };

  const current = styles[type] || styles.error;

  return (
    <div 
      role="alert"
      className={`rounded-xl border p-4 mb-4 ${current.bg} ${current.border} shadow-sm transition-all duration-200 ${className}`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{current.icon}</div>
        
        <div className="flex-1 min-w-0">
          <h4 className={`text-sm font-bold ${current.text}`}>
            {title || current.defaultTitle}
          </h4>
          <p className={`text-sm mt-0.5 ${current.desc}`}>
            {message}
          </p>
          
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-xs transition-colors"
            >
              <FiRefreshCw className="w-3.5 h-3.5" /> Reintentar
            </button>
          )}
        </div>

        {onClose && (
          <button
            onClick={onClose}
            aria-label="Cerrar alerta"
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
          >
            <FiX className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

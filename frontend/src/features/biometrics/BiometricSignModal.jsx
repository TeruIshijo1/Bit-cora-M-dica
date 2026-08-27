import React, { useState, useEffect } from 'react';
import { api } from '../../api';
import { useDigitalPersona } from '../../hooks/useDigitalPersona';
import { useEscapeKey } from '../../hooks/useEscapeKey';
import Button from '../../components/ui/Button';
import { MdFingerprint } from 'react-icons/md';
import { FiCheckCircle, FiAlertCircle, FiCopy, FiCheck, FiX } from 'react-icons/fi';

/**
 * Modal Unificado de Firma Biométrica NOM-024.
 * Centraliza la escucha de hardware de huella (dpFmd) en un único efecto para evitar carreras de estado.
 */
export default function BiometricSignModal({
  isOpen,
  onClose,
  patientId,
  title = "Firma Electrónica Avanzada Biométrica",
  documentType = "Nota de Evolución de Urgencias",
  formatCode = "HE-DIRMED-SINPRO-PLT-87/01",
  evolutionSlot = 1,
  summaryContent = "",
  customPayload = null,
  customEndpoint = null,
  onSigned
}) {
  useEscapeKey(isOpen, onClose);

  const { status: dpStatus, fmdTemplate: dpFmd, error: dpError, devices, resetFmd, startCapture, isAcquiring } = useDigitalPersona();

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [selloDigital, setSelloDigital] = useState(null);
  const [selloCopiado, setSelloCopiado] = useState(false);

  // Inicializar captura cuando se abre el modal
  useEffect(() => {
    if (isOpen) {
      setErrorMsg(null);
      setSuccessMsg(null);
      setSelloDigital(null);
      setSelloCopiado(false);
      resetFmd();
      startCapture();
    }
  }, [isOpen]);

  // ÚNICO EFECTO que reacciona a la adquisición de huella biométrica
  useEffect(() => {
    if (!isOpen || !dpFmd || submitting || successMsg) return;

    const executeSignature = async () => {
      try {
        setSubmitting(true);
        setErrorMsg(null);

        const endpoint = customEndpoint || `/ehr/paciente/${patientId}/firmar-biometrico`;
        const payload = customPayload 
          ? { ...customPayload, fmd_template: dpFmd }
          : {
              codigo_formato: formatCode,
              tipo_documento: documentType,
              evolution_slot: evolutionSlot,
              fmd_template: dpFmd,
              contenido_resumen: summaryContent
            };

        const res = await api.post(endpoint, payload);

        if (res.data && res.data.success) {
          const sello = res.data.firma?.sello_digital || res.data.message || 'Sello generado exitosamente';
          setSelloDigital(sello);
          setSuccessMsg(`¡Documento firmado biométricamente con éxito! Sello: ${sello}`);
          
          if (onSigned) {
            await onSigned(res.data);
          }

          setTimeout(() => {
            resetFmd();
            onClose();
          }, 2500);
        } else {
          setErrorMsg(res.data?.error || "Error al autenticar firma biométrica.");
          resetFmd();
        }
      } catch (err) {
        setErrorMsg(err.response?.data?.detail || "Huella dactilar no reconocida como médico adscrito autorizado.");
        resetFmd();
      } finally {
        setSubmitting(false);
      }
    };

    executeSignature();
  }, [dpFmd, isOpen]);

  if (!isOpen) return null;

  const handleCopySello = () => {
    if (!selloDigital) return;
    navigator.clipboard.writeText(selloDigital);
    setSelloCopiado(true);
    setTimeout(() => setSelloCopiado(false), 2000);
  };

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
              <p className="text-xs text-slate-500 font-mono">
                {formatCode} • Ranura {evolutionSlot}
              </p>
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
            <span>Tipo de Documento:</span>
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
              {dpStatus || 'Coloque su dedo en el lector biométrico'}
            </p>
            <p className="text-[11px] text-slate-400">
              Verificando firma con plantilla digital encriptada SHA-256
            </p>
          </div>
        </div>

        {/* Mensajes de Estado */}
        {errorMsg && (
          <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100 flex items-center gap-2">
            <FiAlertCircle className="text-base flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100 space-y-2">
            <div className="flex items-center gap-2 font-bold">
              <FiCheckCircle className="text-base flex-shrink-0" />
              <span>Firma Biométrica Acreditada</span>
            </div>
            {selloDigital && (
              <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-emerald-200 font-mono text-[10px] break-all">
                <span className="truncate pr-2">{selloDigital}</span>
                <button
                  onClick={handleCopySello}
                  className="shrink-0 p-1 text-emerald-600 hover:text-emerald-800"
                  title="Copiar Sello Digital"
                >
                  {selloCopiado ? <FiCheck className="text-sm text-green-600" /> : <FiCopy className="text-sm" />}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Botones de Acción */}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            size="sm"
            isLoading={submitting}
            icon={<MdFingerprint />}
            onClick={() => { resetFmd(); startCapture(); }}
          >
            Reintentar Huella
          </Button>
        </div>

      </div>
    </div>
  );
}

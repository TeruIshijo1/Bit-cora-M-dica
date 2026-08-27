import React, { useState, useEffect } from 'react';
import { api } from '../../../api';
import { useEscapeKey } from '../../../hooks/useEscapeKey';
import Button from '../../../components/ui/Button';
import { FiAlertCircle, FiCheckCircle, FiActivity, FiPlus, FiX } from 'react-icons/fi';

/**
 * Modal para la gestión completa de Alergias del Paciente (PTAL y catálogo DIS_AL).
 */
export default function AllergiesModal({
  isOpen,
  onClose,
  patientId,
  allergiesList = [],
  initialCustomText = '',
  onUpdate
}) {
  useEscapeKey(isOpen, onClose);

  const [searchCatalog, setSearchCatalog] = useState('');
  const [catalogResults, setCatalogResults] = useState([]);
  const [selectedAllergy, setSelectedAllergy] = useState(null);
  const [allergicSince, setAllergicSince] = useState('');
  const [notes, setNotes] = useState('');
  const [customText, setCustomText] = useState(initialCustomText || '');

  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submittingText, setSubmittingText] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    setCustomText(initialCustomText || '');
  }, [initialCustomText]);

  // Búsqueda en vivo de catálogo oficial DIS_AL
  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(async () => {
      try {
        setLoadingCatalog(true);
        const res = await api.get(`/ehr/alergias/catalogo?q=${encodeURIComponent(searchCatalog || '')}&limit=40`);
        if (res.data && Array.isArray(res.data)) {
          setCatalogResults(res.data);
        }
      } catch (err) {
        // Fallback silencioso de catálogo
      } finally {
        setLoadingCatalog(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [searchCatalog, isOpen]);

  if (!isOpen) return null;

  const handleSaveAllergy = async (e) => {
    e.preventDefault();
    if (!selectedAllergy) {
      setErrorMsg("Debe seleccionar una alergia del catálogo oficial.");
      return;
    }
    try {
      setSubmitting(true);
      setErrorMsg(null);
      const user = localStorage.getItem('usuario') || 'medico_adscrito';
      const res = await api.post(`/ehr/paciente/${patientId}/alergias/registrar`, {
        allergy_num: selectedAllergy.allergy_id,
        allergic_since: allergicSince || null,
        notes: notes || '',
        user: user
      });
      if (res.data && res.data.success) {
        setSuccessMsg(res.data.message);
        setSelectedAllergy(null);
        setSearchCatalog('');
        setNotes('');
        setAllergicSince('');
        if (onUpdate) await onUpdate();
        setTimeout(() => setSuccessMsg(null), 2500);
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Error al registrar alergia.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleInactivateAllergy = async (ptalNum) => {
    if (!window.confirm("¿Confirma que desea inactivar esta alergia en el expediente?")) return;
    try {
      const user = localStorage.getItem('usuario') || 'medico_adscrito';
      const res = await api.post(`/ehr/paciente/${patientId}/alergias/inactivar`, {
        ptal_num: ptalNum,
        user: user
      });
      if (res.data && res.data.success) {
        if (onUpdate) await onUpdate();
      }
    } catch (err) {
      alert(err.response?.data?.detail || "Error al inactivar alergia.");
    }
  };

  const handleUpdateCustomText = async (e) => {
    e.preventDefault();
    try {
      setSubmittingText(true);
      setErrorMsg(null);
      const res = await api.post(`/ehr/paciente/${patientId}/alergias/texto`, {
        allergies_text: customText || 'NEGADAS'
      });
      if (res.data && res.data.success) {
        setSuccessMsg(res.data.message);
        if (onUpdate) await onUpdate();
        setTimeout(() => setSuccessMsg(null), 2500);
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Error al actualizar texto de alergias.");
    } finally {
      setSubmittingText(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-3xl w-full p-6 shadow-2xl border border-slate-100 space-y-5 animate-scaleUp max-h-[90vh] overflow-y-auto">
        
        {/* Cabecera */}
        <div className="flex justify-between items-start border-b border-slate-100 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-red-50 text-red-600 rounded-2xl">
              <FiAlertCircle className="text-2xl" />
            </div>
            <div>
              <h3 className="text-lg font-black text-slate-800">Catálogo de Alergias del Paciente</h3>
              <p className="text-xs text-slate-500">
                Sincronización de alergias con el catálogo oficial del hospital
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

        {/* Mensajes de Feedback */}
        {errorMsg && (
          <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100 flex items-center gap-2">
            <FiAlertCircle className="text-base flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div className="p-3 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100 flex items-center gap-2">
            <FiCheckCircle className="text-base flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Sección 1: Alergias Activas */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <FiActivity className="text-red-500" /> Alergias Registradas del Paciente
            </h4>
            <span className="text-[11px] font-bold bg-red-50 text-red-700 px-2.5 py-0.5 rounded-full border border-red-100">
              {allergiesList.length} Activas
            </span>
          </div>

          {allergiesList.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {allergiesList.map((al) => (
                <div key={al.ptal_num} className="p-3.5 rounded-2xl border border-red-100 bg-red-50/30 hover:bg-red-50/60 transition-all flex flex-col justify-between gap-2 shadow-2xs">
                  <div className="space-y-1">
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-extrabold text-slate-800 text-xs leading-snug">
                        {al.allergy_name}
                      </span>
                      <span className="text-[10px] font-mono bg-white text-slate-600 px-1.5 py-0.5 rounded border border-slate-200 shrink-0">
                        Cód: {al.allergy_num}
                      </span>
                    </div>
                    {al.notes && (
                      <p className="text-[11px] text-slate-600 bg-white/80 p-1.5 rounded-lg border border-red-50">
                        <strong className="text-slate-700">Notas:</strong> {al.notes}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-x-2 text-[10px] text-slate-400 pt-1">
                      {al.allergic_since && <span>Desde: <strong>{al.allergic_since}</strong></span>}
                      {al.allergic_since && <span>•</span>}
                      <span>Por: <strong>{al.created_by}</strong> ({al.created_on})</span>
                    </div>
                  </div>
                  <div className="flex justify-end pt-1 border-t border-red-100/60">
                    <Button
                      variant="danger"
                      size="sm"
                      icon={<FiX className="text-xs" />}
                      onClick={() => handleInactivateAllergy(al.ptal_num)}
                    >
                      Inactivar
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-xs text-slate-400">
              El paciente no tiene alergias registradas actualmente.
            </div>
          )}
        </div>

        {/* Sección 2: Formulario de Nueva Alergia */}
        <form onSubmit={handleSaveAllergy} className="space-y-4 pt-4 border-t border-slate-100 bg-slate-50/70 p-4 rounded-2xl border border-slate-200">
          <h4 className="text-xs font-black uppercase tracking-wider text-hes-blue-main flex items-center gap-1.5">
            <FiPlus /> Registrar Nueva Alergia (Catálogo Oficial DIS_AL)
          </h4>

          <div className="space-y-1 text-xs">
            <label className="block text-[10px] font-bold text-slate-600 uppercase">
              Buscar Alergia o Sustancia en Catálogo *
            </label>
            <div className="relative">
              <input
                type="text"
                value={searchCatalog}
                onChange={(e) => setSearchCatalog(e.target.value)}
                placeholder="Escriba el nombre del fármaco o sustancia (ej. Penicilinas, Sulfas, Betanecol, Huevo)..."
                className="w-full border border-slate-200 bg-white rounded-xl p-2.5 text-xs font-semibold focus:border-hes-blue-main outline-none"
              />
              {loadingCatalog && (
                <span className="absolute right-3 top-2.5 text-[10px] text-hes-blue-main font-bold animate-pulse">
                  Buscando...
                </span>
              )}
            </div>

            {catalogResults.length > 0 && !selectedAllergy && (
              <div className="max-h-44 overflow-y-auto bg-white border border-slate-200 rounded-xl shadow-lg mt-1 divide-y divide-slate-100">
                {catalogResults.map((cat) => (
                  <div
                    key={cat.allergy_id}
                    onClick={() => {
                      setSelectedAllergy(cat);
                      setSearchCatalog(cat.name);
                    }}
                    className="p-2.5 hover:bg-blue-50 cursor-pointer flex items-center justify-between text-xs transition-colors"
                  >
                    <span className="font-bold text-slate-800">{cat.name}</span>
                    <span className="text-[10px] font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                      ID: {cat.allergy_id}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {selectedAllergy && (
              <div className="p-2.5 bg-blue-50 rounded-xl border border-blue-200 flex items-center justify-between mt-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] bg-hes-blue-main text-white font-extrabold px-1.5 py-0.5 rounded">
                    ID #{selectedAllergy.allergy_id}
                  </span>
                  <span className="text-xs font-black text-hes-blue-main">
                    {selectedAllergy.name}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => { setSelectedAllergy(null); setSearchCatalog(''); }}
                  className="text-xs text-slate-400 hover:text-red-500 font-bold"
                >
                  Cambiar
                </button>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">
                Alérgico Desde (Opcional)
              </label>
              <input
                type="date"
                value={allergicSince}
                onChange={(e) => setAllergicSince(e.target.value)}
                className="w-full border border-slate-200 bg-white rounded-xl p-2 text-xs font-semibold outline-none"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">
                Notas / Reacción Clínica
              </label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Ej. Anafilaxia previa, Urticaria, Shock..."
                className="w-full border border-slate-200 bg-white rounded-xl p-2 text-xs font-semibold outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              variant="primary"
              isLoading={submitting}
              disabled={!selectedAllergy}
              icon={<FiPlus />}
            >
              Guardar Alergia
            </Button>
          </div>
        </form>

        {/* Sección 3: Texto de Formatos Clínicos */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-700">
              Texto en Formatos y Notas Clínicas
            </h4>
            <p className="text-[11px] text-slate-500">
              Este texto se imprime en el Formato 87/01 y en Dietas.
            </p>
          </div>

          <form onSubmit={handleUpdateCustomText} className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              placeholder="Ej. Alérgico a Penicilina, Sulfas..."
              className="flex-1 border border-slate-200 bg-white rounded-xl p-2 text-xs font-semibold focus:border-hes-blue-main outline-none"
            />
            <Button
              type="submit"
              variant="secondary"
              isLoading={submittingText}
            >
              Actualizar Texto
            </Button>
          </form>
        </div>

        {/* Pie */}
        <div className="flex justify-end pt-3 border-t border-slate-100">
          <Button variant="ghost" onClick={onClose}>
            Cerrar
          </Button>
        </div>

      </div>
    </div>
  );
}

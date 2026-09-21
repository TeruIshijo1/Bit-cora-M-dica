import React from 'react';
import { FiFileText, FiPlus, FiLock, FiEdit3, FiCheckCircle, FiPrinter } from 'react-icons/fi';
import { MdFingerprint, MdVerifiedUser } from 'react-icons/md';

/**
 * FormatoClinicoDetalle — PLANTILLA PREDEFINIDA HES
 * Úsala para CUALQUIER formato clínico actual o futuro (100+).
 * Solo visual premium, no cambia lógica. Reversible: borrar archivo + quitar import.
 *
 * Props:
 *  formato: { codigo, nombre, subtitulo, area, url_pdf }
 *  historial: [] registros Vertical (con mrnum, firmado, medico_tratante, etc)
 *  selectedMrnum, onSelectMrnum(mrnum)
 *  loading
 *  isPatientDischarged, isOwner(doc), isAdminOrSistemas
 *  onNuevo(), onEditar(doc), onFirmarMedico(mrnum), onFirmaPaciente(doc), onVerificar(firmaInfo)
 *  getPdfUrl(doc) -> string
 *  emptyTitle, emptyDesc, emptyCtaLabel (opcionales para futuros formatos)
 */
export function getAreaMeta(area = '') {
  const a = (area || '').toLowerCase();
  if (a.includes('urgencia')) return { icon: '🚨', grad: 'linear-gradient(135deg,#dc2626,#f97316)' };
  if (a.includes('hospital')) return { icon: '🏥', grad: 'linear-gradient(135deg,#004687,#0088c9)' };
  if (a.includes('cirug') || a.includes('quir')) return { icon: '🔪', grad: 'linear-gradient(135deg,#7c3aed,#06b6d4)' };
  if (a.includes('expediente') || a.includes('integral')) return { icon: '📋', grad: 'linear-gradient(135deg,#047857,#00b48a)' };
  if (a.includes('auxiliar') || a.includes('diagn')) return { icon: '🧬', grad: 'linear-gradient(135deg,#0e7490,#22d3ee)' };
  return { icon: '🩺', grad: 'linear-gradient(135deg,#0a3d6e,#005fa9)' };
}

function DetailItem({ label, children, mono = false }) {
  return (
    <div className="he-det-item">
      <span className="he-det-label">{label}</span>
      <span className={`he-det-value ${mono ? 'he-det-mono' : ''}`}>{children}</span>
    </div>
  );
}

export default function FormatoClinicoDetalle({
  formato = {},
  historial = [],
  selectedMrnum = null,
  onSelectMrnum = () => {},
  loading = false,
  isPatientDischarged = false,
  isOwner = () => true,
  onNuevo = () => {},
  onEditar = () => {},
  onFirmarMedico = () => {},
  onFirmaPaciente = () => {},
  onVerificar = () => {},
  getPdfUrl = () => null,
  emptyTitle = null,
  emptyDesc = null,
  emptyCtaLabel = '+ Nuevo Registro',
}) {
  const areaMeta = getAreaMeta(formato.area);
  const activeDoc = historial.find(d => d.mrnum === selectedMrnum) || historial[0] || null;
  const isDocSigned = Boolean(activeDoc?.firmado);
  const owner = activeDoc ? isOwner(activeDoc) : false;

  return (
    <div className="he-det-card">
      {/* HEADER */}
      <div className="he-det-header">
        <div className="flex items-center gap-3.5 min-w-0">
          <div className="he-det-icon" style={{ background: areaMeta.grad }}>{areaMeta.icon}</div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="he-det-code">{formato.codigo || 'HE-FORMATO'}</span>
              <span className="he-det-area">{formato.area || 'Expediente Clínico'}</span>
            </div>
            <h3 className="he-det-title">{formato.nombre || 'Formato Clínico'}</h3>
            <p className="he-det-sub">{formato.subtitulo || 'Formato institucional registrado en Vertical EHR y sincronizado con Bitácora HES.'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {!isPatientDischarged && (
            <button type="button" onClick={onNuevo} className="he-btn-ghost flex items-center gap-1.5 px-4 py-2.5 text-xs cursor-pointer">
              <FiPlus className="text-sm" /> {emptyCtaLabel}
            </button>
          )}
        </div>
      </div>

      {/* CONTENIDO */}
      <div className="p-5 md:p-6 space-y-5">
        {loading ? (
          <div className="text-center py-12">
            <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-800 rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-xs font-bold text-slate-400 animate-pulse">Consultando historial en Vertical EHR...</p>
          </div>
        ) : historial.length > 0 && activeDoc ? (
          <div className="space-y-5">
            {/* TABS VERSIONES */}
            <div className="he-det-tabs">
              {historial.map((doc, idx) => {
                const isActive = (selectedMrnum || historial[0]?.mrnum) === doc.mrnum;
                return (
                  <button
                    key={doc.mrnum}
                    type="button"
                    onClick={() => onSelectMrnum(doc.mrnum)}
                    className={`he-det-tab ${isActive ? 'he-det-tab-active' : ''}`}
                  >
                    <span>Doc #{historial.length - idx}</span>
                    <span className="opacity-70 font-semibold">({doc.created_on ? doc.created_on.split(' ')[0] : 'S/F'})</span>
                    {doc.firmado && <span className="he-det-dot"></span>}
                  </button>
                );
              })}
            </div>

            {/* ESTADO FIRMA */}
            <div className={`he-det-sign ${isDocSigned ? 'he-det-sign-ok' : 'he-det-sign-pend'}`}>
              <div className="flex items-center gap-3 min-w-0">
                <div className={`he-det-sign-icon ${isDocSigned ? 'ok' : 'pend'}`}>{isDocSigned ? '✓' : '!'}</div>
                <div className="min-w-0">
                  <h4 className="he-det-sign-title">
                    {isDocSigned ? 'Documento Oficial Firmado (Vertical EHR & Bitácora)' : 'Registro Pendiente de Firma Biométrica'}
                  </h4>
                  <p className="he-det-sign-sub">
                    {isDocSigned
                      ? <>Firmado digitalmente por <strong>{activeDoc.signed_by || activeDoc.medico_tratante}</strong> el {activeDoc.signed_on || 'fecha registrada'} <span className="he-det-mono-inline">(MR_ST: {activeDoc.mr_st})</span></>
                      : <>Generado el {activeDoc.created_on} por {activeDoc.created_by}. Requiere firma para validez legal NOM-004.</>}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap justify-end">
                {!isPatientDischarged && (
                  isDocSigned ? (
                    <span className="he-det-chip-ok" title="Documento cerrado NOM-004 / NOM-024"><FiLock /> Firmado (Inmutable)</span>
                  ) : !owner ? (
                    <span className="he-det-chip-lock" title="Documento de otro médico"><FiLock /> Solo Lectura ({activeDoc.medico_tratante || 'Otro Médico'})</span>
                  ) : (
                    <button type="button" onClick={() => onEditar(activeDoc)} className="he-btn-ghost flex items-center gap-1.5 px-4 py-2 text-xs cursor-pointer">
                      <FiEdit3 /> Editar
                    </button>
                  )
                )}
                {!isPatientDischarged && (
                  <button
                    type="button"
                    disabled={!owner}
                    onClick={() => onFirmarMedico(activeDoc.mrnum)}
                    className={`he-det-btn-sign ${!owner ? 'disabled' : isDocSigned ? 'refirm' : 'firm'}`}
                    title="Firma Electrónica Avanzada del Médico (NOM-024)"
                  >
                    <FiCheckCircle /> {isDocSigned ? '✓ Firma médica' : 'Firmar como médico'}
                  </button>
                )}
                {!isPatientDischarged && (
                  <button type="button" onClick={() => onFirmaPaciente(activeDoc)} className="he-det-btn-patient" title="Firma dactilar paciente / testigos">
                    <MdFingerprint className="text-base" /> Paciente / familiar
                  </button>
                )}
                {isDocSigned && (
                  <button type="button" onClick={() => onVerificar(activeDoc)} className="he-det-btn-verify" title="Verificar sello y auditoría NOM-024">
                    <MdVerifiedUser className="text-base" /> Verificar Integridad y Sello
                  </button>
                )}
                {getPdfUrl(activeDoc) && (
                  <a href={getPdfUrl(activeDoc)} target="_blank" rel="noreferrer" className="he-btn-open flex items-center gap-1.5 px-4 py-2 text-white text-xs font-bold">
                    <FiPrinter /> Imprimir PDF Oficial
                  </a>
                )}
              </div>
            </div>

            {/* DETALLE */}
            <div className="he-det-grid">
              <DetailItem label="Médico Responsable"><strong>{activeDoc.medico_tratante || 'NO ASIGNADO'}</strong></DetailItem>
              <DetailItem label="Diagnóstico Asociado">{activeDoc.diagnostico || 'VALORACIÓN CLÍNICA INSTITUCIONAL'}</DetailItem>
              <DetailItem label="Identificador en Vertical" mono>{activeDoc.controller_name} (Folio #{activeDoc.mrnum})</DetailItem>
              <DetailItem label="Auditoría y Trazabilidad">Creado por {activeDoc.created_by} el {activeDoc.created_on}</DetailItem>
              {activeDoc.observaciones && (
                <div className="md:col-span-2">
                  <span className="he-det-label">Observaciones / Plan Clínico</span>
                  <p className="he-det-obs">{activeDoc.observaciones}</p>
                </div>
              )}
              {(activeDoc.tutor || activeDoc.pariente || activeDoc.representante_legal) && (
                <DetailItem label="Familiar / Tutor Registrado">
                  <strong>{activeDoc.tutor || activeDoc.pariente || activeDoc.representante_legal} {activeDoc.parentesco ? `(${activeDoc.parentesco})` : ''}</strong>
                </DetailItem>
              )}
              {(activeDoc.testigo1 || activeDoc.testigo2) && (
                <DetailItem label="Testigos Presenciales">T1: {activeDoc.testigo1 || 'N/A'} • T2: {activeDoc.testigo2 || 'N/A'}</DetailItem>
              )}
            </div>
          </div>
        ) : (
          <div className="he-det-empty">
            <div className="he-det-empty-icon"><FiFileText /></div>
            <h4 className="font-black text-slate-800 text-sm">{emptyTitle || `Sin registros de ${formato.nombre || 'este formato'}`}</h4>
            <p className="text-xs text-slate-500 max-w-md mx-auto">{emptyDesc || 'Capture el documento conforme a NOM-004-SSA3-2012. Al guardar se folia en Vertical y queda listo para firma biométrica.'}</p>
            {!isPatientDischarged && (
              <button type="button" onClick={onNuevo} className="he-btn-open inline-flex items-center gap-1.5 text-white px-5 py-2.5 text-xs font-bold">
                <FiPlus /> {emptyCtaLabel}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

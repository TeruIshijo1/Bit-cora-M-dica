import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import { useDigitalPersona } from '../hooks/useDigitalPersona';
import { useEscapeKey } from '../hooks/useEscapeKey';
import { 
  FiSearch, FiBell, FiCalendar, FiFileText, FiActivity, FiImage, 
  FiSettings, FiUser, FiMessageSquare, FiPlus, FiClock, FiChevronRight, 
  FiEdit3, FiCheckCircle, FiAlertCircle, FiScissors, FiHome, FiUsers, 
  FiFolder, FiDownload, FiCheck, FiLayers, FiSave, FiX, FiCheckSquare,
  FiArrowLeft, FiExternalLink, FiShield, FiLock, FiCopy, FiServer, FiPrinter,
  FiCreditCard, FiPhone, FiMapPin, FiMail, FiAlertTriangle, FiRotateCcw, FiTrash2
} from 'react-icons/fi';
import { 
  MdOutlineBloodtype, MdOutlineMonitorHeart, MdOutlineWaterDrop, 
  MdOutlineRestaurant, MdOutlineMedicalServices, MdOutlineBiotech,
  MdFingerprint, MdVerifiedUser 
} from 'react-icons/md';
import { FaTemperatureHalf } from 'react-icons/fa6';
import AllergiesModal from '../features/ehr/modals/AllergiesModal';
const ClinicalPdfViewer = React.lazy(() => import('../components/ClinicalPdfViewer'));
import { FirmantesEpisodioModal } from '../features/biometrics/FirmantesEpisodioModal';
import FormatoClinicoDetalle from '../components/FormatoClinicoDetalle';
import { BiometricPatientSignModal } from '../features/biometrics/BiometricPatientSignModal';
import { isConfirmedClinicalSync, pendingClinicalSyncMessage } from '../utils/clinicalSyncResult';
import { friendlyBiometricError, friendlyReaderStatus } from '../utils/userMessages';

const FamiliarSelectorSection = ({
  label = "Nombre del Familiar, Tutor o Representante Legal Responsable:",
  value = "",
  onChangeValue,
  parentescoValue = "",
  onChangeParentesco,
  firmantesList = [],
  required = true
}) => {
  const tutoresYContactos = (firmantesList || []).filter(f => f.tipo_firmante !== 'PACIENTE');
  const availableOptions = tutoresYContactos.length > 0 ? tutoresYContactos : (firmantesList || []);

  const selectedOption = availableOptions.find(
    f => f.nombre_completo.trim().toUpperCase() === (value || '').trim().toUpperCase()
  );

  return (
    <div className="p-3.5 bg-amber-50 rounded-2xl border border-amber-200 space-y-2.5">
      <div className="flex items-center justify-between flex-wrap gap-1">
        <label className="block text-[11px] font-bold text-amber-900 uppercase">
          {label}
        </label>
        {availableOptions.length > 0 && (
          <span className="text-[10px] text-amber-800 font-semibold flex items-center gap-1">
            <FiUsers className="text-xs text-amber-700" />
            {availableOptions.length} contacto(s) en expediente
          </span>
        )}
      </div>

      {availableOptions.length > 0 ? (
        <div className="space-y-2">
          <select
            value={selectedOption ? selectedOption.id : (value ? '__saved__' : '')}
            onChange={(e) => {
              const val = e.target.value;
              if (!val) {
                onChangeValue && onChangeValue('');
                if (onChangeParentesco) onChangeParentesco('');
              } else {
                const found = availableOptions.find(f => f.id === parseInt(val, 10));
                if (found) {
                  onChangeValue && onChangeValue(found.nombre_completo);
                  if (onChangeParentesco) {
                    onChangeParentesco(found.parentesco || 'Familiar / Representante Legal');
                  }
                }
              }
            }}
            className="w-full border border-amber-300 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none cursor-pointer"
          >
            <option value="">-- Seleccionar Familiar o Tutor Registrado --</option>
            {availableOptions.map(f => {
              const rolText = f.tipo_firmante === 'REPRESENTANTE_LEGAL' || f.tipo_firmante === 'TUTOR'
                ? 'TUTOR / REP. LEGAL'
                : (f.tipo_firmante === 'TESTIGO_1' ? 'TESTIGO 1' : (f.tipo_firmante === 'TESTIGO_2' ? 'TESTIGO 2' : f.tipo_firmante));
              return (
                <option key={f.id} value={f.id}>
                  {f.nombre_completo} • [{rolText}] {f.parentesco ? `(${f.parentesco})` : ''} {f.tiene_huella ? '✓ Con Huella' : ''}
                </option>
              );
            })}
            {value && !selectedOption && (
              <option value="__saved__">
                {value} ({parentescoValue || 'Acreditado en Consentimiento'})
              </option>
            )}
          </select>

          {value && (
            <div className="p-2.5 bg-amber-100/80 border border-amber-200 rounded-xl flex items-center justify-between text-[11px] text-amber-950">
              <div>
                <span className="font-bold">{value}</span>
                <span className="text-amber-800 ml-2">
                  Parentesco: <b>{parentescoValue || 'Familiar / Representante Legal'}</b>
                </span>
              </div>
              <span className="text-[10px] bg-amber-200 text-amber-900 font-bold px-2 py-0.5 rounded-md">
                Tutor Acreditado
              </span>
            </div>
          )}
        </div>
      ) : (
        <div className="p-2.5 bg-white rounded-xl border border-amber-200 text-[11px] text-amber-800">
          ⚠ No hay familiares o tutores registrados en el expediente por Admisión / Trabajo Social.
        </div>
      )}
    </div>
  );
};

const TestigosSelectorSection = ({
  testigo1 = "",
  parentesco1 = "",
  identificacion1 = "",
  domicilio1 = "",
  testigo2 = "",
  parentesco2 = "",
  identificacion2 = "",
  domicilio2 = "",
  onUpdateTestigo1,
  onUpdateTestigo2,
  firmantesList = [],
  showWitness2 = true
}) => {
  const availableTestigos = (firmantesList || []).filter(f => f.tipo_firmante !== 'PACIENTE');

  const selectedT1 = availableTestigos.find(
    f => f.nombre_completo.trim().toUpperCase() === (testigo1 || '').trim().toUpperCase()
  );
  const selectedT2 = availableTestigos.find(
    f => f.nombre_completo.trim().toUpperCase() === (testigo2 || '').trim().toUpperCase()
  );

  return (
    <div className="he-ed-sec p-4 space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-1">
        <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <FiUsers className="text-hes-blue-main text-sm" /> 4. Testigos Presenciales
        </h4>
        <span className="text-[10px] text-slate-500 font-medium">
          Selección de testigos registrados en expediente
        </span>
      </div>

      {availableTestigos.length === 0 ? (
        <div className="p-3 bg-white border border-slate-200 rounded-xl text-slate-600 text-xs">
          ℹ No hay testigos registrados en este expediente por Admisión / Trabajo Social.
        </div>
      ) : (
        <div className="space-y-3">
          {/* SELECTOR TESTIGO 1 */}
          <div className="bg-white p-3 rounded-xl border border-slate-200 space-y-2">
            <label className="block text-[11px] font-bold text-slate-700 uppercase">
              Seleccionar Testigo 1 (Presencial):
            </label>
            <select
              value={selectedT1 ? selectedT1.id : (testigo1 ? '__saved__' : '')}
              onChange={(e) => {
                const val = e.target.value;
                if (!val) {
                  onUpdateTestigo1 && onUpdateTestigo1({
                    testigo1: '',
                    parentesco1: '',
                    identificacion1: '',
                    domicilio1: ''
                  });
                } else {
                  const found = availableTestigos.find(f => f.id === parseInt(val, 10));
                  if (found && onUpdateTestigo1) {
                    onUpdateTestigo1({
                      testigo1: found.nombre_completo,
                      parentesco1: found.parentesco || 'Familiar / Testigo Presencial',
                      identificacion1: found.identificacion_oficial || 'INE / Credencial Oficial',
                      domicilio1: found.domicilio || 'Conocido en expediente clínico'
                    });
                  }
                }
              }}
              className="w-full border border-blue-300 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none cursor-pointer"
            >
              <option value="">-- Sin Testigo 1 / No Asignado --</option>
              {availableTestigos.map(f => (
                <option key={f.id} value={f.id}>
                  {f.nombre_completo} {f.parentesco ? `(${f.parentesco})` : ''} {f.tiene_huella ? '• [✓ Huella Registrada]' : ''}
                </option>
              ))}
              {testigo1 && !selectedT1 && (
                <option value="__saved__">
                  {testigo1} (Acreditado en Consentimiento)
                </option>
              )}
            </select>

            {testigo1 && (
              <div className="p-2.5 bg-blue-50/70 border border-blue-100 rounded-lg flex items-center justify-between text-[11px] text-blue-900">
                <div>
                  <span className="font-bold">{testigo1}</span>
                  <span className="text-slate-500 ml-2">
                    {parentesco1 || 'Testigo Presencial'} • {identificacion1 || 'INE'} • {domicilio1 || 'Expediente HES'}
                  </span>
                </div>
                <span className="text-[10px] bg-blue-200 text-blue-800 font-bold px-2 py-0.5 rounded">
                  Testigo 1 Acreditado
                </span>
              </div>
            )}
          </div>

          {/* SELECTOR TESTIGO 2 (OPCIONAL) */}
          {showWitness2 && (
            <div className="bg-white p-3 rounded-xl border border-slate-200 space-y-2">
              <label className="block text-[11px] font-bold text-slate-700 uppercase">
                Seleccionar Testigo 2 (Opcional):
              </label>
              <select
                value={selectedT2 ? selectedT2.id : (testigo2 ? '__saved__' : '')}
                onChange={(e) => {
                  const val = e.target.value;
                  if (!val) {
                    onUpdateTestigo2 && onUpdateTestigo2({
                      testigo2: '',
                      parentesco2: '',
                      identificacion2: '',
                      domicilio2: ''
                    });
                  } else {
                    const found = availableTestigos.find(f => f.id === parseInt(val, 10));
                    if (found && onUpdateTestigo2) {
                      onUpdateTestigo2({
                        testigo2: found.nombre_completo,
                        parentesco2: found.parentesco || 'Testigo Presencial / Institucional',
                        identificacion2: found.identificacion_oficial || 'INE / Credencial Oficial',
                        domicilio2: found.domicilio || 'Conocido en expediente clínico'
                      });
                    }
                  }
                }}
                className="w-full border border-blue-300 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none cursor-pointer"
              >
                <option value="">-- Sin Testigo 2 / No Aplica --</option>
                {availableTestigos
                  .filter(f => f.nombre_completo.trim().toUpperCase() !== (testigo1 || '').trim().toUpperCase())
                  .map(f => (
                    <option key={f.id} value={f.id}>
                      {f.nombre_completo} {f.parentesco ? `(${f.parentesco})` : ''} {f.tiene_huella ? '• [✓ Huella Registrada]' : ''}
                    </option>
                  ))}
                {testigo2 && !selectedT2 && (
                  <option value="__saved__">
                    {testigo2} (Acreditado en Consentimiento)
                  </option>
                )}
              </select>

              {testigo2 && (
                <div className="p-2.5 bg-blue-50/70 border border-blue-100 rounded-lg flex items-center justify-between text-[11px] text-blue-900">
                  <div>
                    <span className="font-bold">{testigo2}</span>
                    <span className="text-slate-500 ml-2">
                      {parentesco2 || 'Testigo Presencial'} • {identificacion2 || 'INE'} • {domicilio2 || 'Expediente HES'}
                    </span>
                  </div>
                  <span className="text-[10px] bg-blue-200 text-blue-800 font-bold px-2 py-0.5 rounded">
                    Testigo 2 Acreditado
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default function PatientDashboard() {
  const { pt_num } = useParams();
  const patientId = pt_num || '5704';

  const [activeTab, setActiveTab] = useState('Timeline'); // DEFAULT TAB IS TIMELINE
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [firmas, setFirmas] = useState([]);
  const [selectedLabPdf, setSelectedLabPdf] = useState(null);
  const [selectedImgPdf, setSelectedImgPdf] = useState(null);
  const [labPdfBlobs, setLabPdfBlobs] = useState({});
  const [loadingPdfId, setLoadingPdfId] = useState(null);
  const [imgPdfBlobs, setImgPdfBlobs] = useState({});
  const [loadingImgPdfId, setLoadingImgPdfId] = useState(null);

  const getCleanPdfPath = (item) => {
    if (!item) return null;
    let url = item.url_pdf || (item.ptmt_num ? `/kh/estudios/${item.ptmt_num}/pdf` : null);
    if (!url) return null;
    if (url.startsWith('/api/')) return url.substring(4);
    if (url.startsWith('api/')) return '/' + url.substring(4);
    if (!url.startsWith('/')) return '/' + url;
    return url;
  };

  const handleToggleLabPdf = async (lab) => {
    if (selectedLabPdf?.id === lab.id) {
      setSelectedLabPdf(null);
      return;
    }
    setSelectedLabPdf(lab);
    const cleanPath = getCleanPdfPath(lab);
    if (!labPdfBlobs[lab.id] && cleanPath) {
      try {
        setLoadingPdfId(lab.id);
        const res = await api.get(cleanPath, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        setLabPdfBlobs(prev => ({ ...prev, [lab.id]: blobUrl }));
      } catch (err) {
        console.error("Error cargando PDF del estudio:", err);
        alert("No se pudo cargar el PDF del estudio: " + (err.response?.data?.detail || err.message));
      } finally {
        setLoadingPdfId(null);
      }
    }
  };

  const handleOpenLabPdfNewTab = async (lab) => {
    let blobUrl = labPdfBlobs[lab.id];
    const cleanPath = getCleanPdfPath(lab);
    if (!blobUrl && cleanPath) {
      try {
        const res = await api.get(cleanPath, { responseType: 'blob' });
        blobUrl = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        setLabPdfBlobs(prev => ({ ...prev, [lab.id]: blobUrl }));
      } catch (err) {
        console.error("Error abriendo PDF:", err);
      }
    }
    if (blobUrl) {
      window.open(blobUrl, '_blank');
    }
  };

  const handleToggleImgPdf = async (img) => {
    if (selectedImgPdf?.id === img.id) {
      setSelectedImgPdf(null);
      return;
    }
    setSelectedImgPdf(img);
    const cleanPath = getCleanPdfPath(img);
    if (!imgPdfBlobs[img.id] && cleanPath) {
      try {
        setLoadingImgPdfId(img.id);
        const res = await api.get(cleanPath, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        setImgPdfBlobs(prev => ({ ...prev, [img.id]: blobUrl }));
      } catch (err) {
        console.error("Error cargando PDF de imagenología:", err);
        alert("No se pudo cargar el PDF: " + (err.response?.data?.detail || err.message));
      } finally {
        setLoadingImgPdfId(null);
      }
    }
  };

  const handleOpenImgPdfNewTab = async (img) => {
    let blobUrl = imgPdfBlobs[img.id];
    const cleanPath = getCleanPdfPath(img);
    if (!blobUrl && cleanPath) {
      try {
        const res = await api.get(cleanPath, { responseType: 'blob' });
        blobUrl = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        setImgPdfBlobs(prev => ({ ...prev, [img.id]: blobUrl }));
      } catch (err) {
        console.error("Error abriendo PDF:", err);
      }
    }
    if (blobUrl) {
      window.open(blobUrl, '_blank');
    }
  };
  
  const isPatientDischarged = Boolean(
    data?.patient?.status === 'Alta' || 
    data?.patient?.is_alta || 
    data?.patient?.is_active === false || 
    (data?.patient?.fecha_egreso && data?.patient?.fecha_egreso !== '___/___/___')
  );
  
  const [firmantesModalOpen, setFirmantesModalOpen] = useState(false);
  const [selectedFirmanteForModal, setSelectedFirmanteForModal] = useState(null);
  const [firmantesList, setFirmantesList] = useState([]);
  const [patientSignModal, setPatientSignModal] = useState({ open: false, documentInfo: {} });
  const [selectedFormatArea, setSelectedFormatArea] = useState('Todos');
  const [searchFormatoQuery, setSearchFormatoQuery] = useState('');
  const [selectedFormat, setSelectedFormat] = useState(null); // FORMATO SELECCIONADO EN PESTAÑA FORMATOS
  const [consentForm3201, setConsentForm3201] = useState({
    tipo_interrogatorio: 'Directo',
    testigo1: '',
    testigo2: '',
    paciente_o_representante: '',
    representante_legal: ''
  });
  const [consentModal3201, setConsentModal3201] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    tipo_interrogatorio: 'Directo',
    testigo1: '',
    testigo2: '',
    paciente_capaz: true,
    paciente_o_representante: '',
    representante_legal: '',
    saving: false
  });

  // Candado de Seguridad y Autoría Médica (NOM-004 / NOM-024)
  const storedUser = (() => {
    try { return JSON.parse(localStorage.getItem('user')); } catch(e) { return null; }
  })();
  const storedMedico = (() => {
    try { return JSON.parse(localStorage.getItem('medico')); } catch(e) { return null; }
  })();
  const userRole = localStorage.getItem('rol') || storedUser?.rol || '';
  const currentDoctorName = storedMedico?.nombre_completo || storedUser?.nombre_completo || '';
  const currentDoctorCedula = storedMedico?.cedula || storedUser?.cedula || '';
  const isAdminOrSistemas = ['admin', 'sistemas'].includes(userRole);
  const currentUser = storedUser || storedMedico || {};

  const isPatientAdult = (patientObj) => {
    if (!patientObj) return true;
    const ageVal = parseInt(patientObj.age, 10);
    if (!isNaN(ageVal)) return ageVal >= 18;
    if (patientObj.dob) {
      try {
        const parts = String(patientObj.dob).split(/[\/\-\s]/);
        if (parts.length >= 3) {
          const yearPart = parseInt(parts[2], 10);
          if (yearPart > 1900) {
            const currentYear = new Date().getFullYear();
            return (currentYear - yearPart) >= 18;
          }
        }
      } catch (e) {}
    }
    return true;
  };

  const getDefaultFirmantesForConsent = (firmantes = []) => {
    const list = Array.isArray(firmantes) ? firmantes : [];
    const tutorObj = list.find(f => ['REPRESENTANTE_LEGAL', 'TUTOR', 'CONTACTO'].includes(f.tipo_firmante)) || list.find(f => f.tipo_firmante !== 'PACIENTE');
    const testigo1Obj = list.find(f => ['TESTIGO_1', 'TESTIGO'].includes(f.tipo_firmante)) || list.find(f => f.tipo_firmante !== 'PACIENTE' && f.id !== tutorObj?.id);
    const testigo2Obj = list.find(f => f.tipo_firmante === 'TESTIGO_2') || list.find(f => f.tipo_firmante !== 'PACIENTE' && f.id !== tutorObj?.id && f.id !== testigo1Obj?.id);

    return {
      tutor: tutorObj?.nombre_completo || '',
      parentesco_tutor: tutorObj?.parentesco || 'Tutor / Representante Legal',
      domicilio_tutor: tutorObj?.domicilio || 'Conocido en expediente clínico',
      identificacion_tutor: tutorObj?.identificacion_oficial || 'INE / Identificación Oficial',
      telefono_tutor: tutorObj?.telefono || '',

      testigo1: testigo1Obj?.nombre_completo || '',
      parentesco1: testigo1Obj?.parentesco || 'Familiar / Testigo Presencial',
      domicilio1: testigo1Obj?.domicilio || 'Conocido en expediente clínico',
      identificacion1: testigo1Obj?.identificacion_oficial || 'INE / Identificación Oficial',

      testigo2: testigo2Obj?.nombre_completo || '',
      parentesco2: testigo2Obj?.parentesco || 'Familiar / Testigo Presencial',
      domicilio2: testigo2Obj?.domicilio || 'Conocido en expediente clínico',
      identificacion2: testigo2Obj?.identificacion_oficial || 'INE / Identificación Oficial',
    };
  };

  const canModifyOrSignDocument = (docDoctorName) => {
    if (isPatientDischarged) return false;
    if (isAdminOrSistemas) return true;
    if (!docDoctorName || docDoctorName.trim() === '') return true;
    if (!currentDoctorName) return false;

    const normalize = (name) => {
      return (name || '')
        .toUpperCase()
        .replace(/^DR(A)?\.?\s+/, '')
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^A-Z0-9]/g, "")
        .trim();
    };

    const normDoc = normalize(docDoctorName);
    const normUser = normalize(currentDoctorName);

    return normDoc === normUser || normDoc.includes(normUser) || normUser.includes(normDoc);
  };

  const [selectedMrnum25, setSelectedMrnum25] = useState(null);
  const [selectedMrnum32, setSelectedMrnum32] = useState(null);
  const [selectedMrnumEED, setSelectedMrnumEED] = useState(null);
  const [selectedMrnum3401, setSelectedMrnum3401] = useState(null);
  const [selectedMrnum12, setSelectedMrnum12] = useState(null);
  const [selectedMrnum04, setSelectedMrnum04] = useState(null);
  const [selectedMrnum08, setSelectedMrnum08] = useState(null);
  const [selectedMrnum15, setSelectedMrnum15] = useState(null);
  const [selectedMrnum02, setSelectedMrnum02] = useState(null);
  const [selectedMrnum43, setSelectedMrnum43] = useState(null);
  const [selectedMrnum06, setSelectedMrnum06] = useState(null);
  const [selectedMrnum11, setSelectedMrnum11] = useState(null);
  const [selectedMrnum19, setSelectedMrnum19] = useState(null);
  const [selectedMrnum07, setSelectedMrnum07] = useState(null);

  const [consentModal07, setConsentModal07] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    mrnum: null,
    medico_tratante: '',
    cedula: '',
    procedimiento_quirurgico: 'INTERVENCIÓN QUIRÚRGICA PROGRAMADA',
    descripcion_procedimiento: 'procedimiento quirúrgico bajo técnica aséptica protocolizada y monitoreo continuo',
    riesgos_inherentes: 'sangrado transoperatorio, infección de herida quirúrgica, dehiscencia, reacciones medicamentosas',
    beneficios: 'resolución del cuadro clínico de base, preservación funcional y mejora de salud',
    alternativas: 'tratamiento médico conservador o diferimiento según valoración',
    paciente_capaz: true,
    representante_legal: '',
    parentesco: 'El Paciente',
    testigo1: '',
    testigo2: '',
    saving: false
  });

  const [consentModal08, setConsentModal08] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    mrnum: null,
    medico_tratante: '',
    cedula: '',
    diagnostico: 'VALORACIÓN Y TRATAMIENTO EN ADMISIÓN CONTINUA',
    procedimientos: 'Instalación de accesos vasculares venosos/arteriales, toma de muestras de laboratorio, monitorización hemodinámica continua, administración de soluciones parenterales y farmacoterapia requerida según evolución clínica.',
    riesgos_inherentes_a_procedimien: 'Medios',
    prob_proced_y_alts: 'Estudios complementarios de laboratorio y gabinete (Rayos X, Ultrasonografía POCUS, TAC), observación clínica estrecha, interconsultas especializadas y tratamiento conservador.',
    beneficios: 'Estabilización de signos vitales, mitigación de síntomas agudos, confirmación diagnóstica oportuna, restitución hemodinámica y prevención de complicaciones graves.',
    paciente_capaz: true,
    pariente: '',
    yo_autorizo: '',
    parentesco: 'Paciente',
    testigo1: '',
    testigo2: '',
    saving: false
  });

  const [consentModal02, setConsentModal02] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    tipo: 'autorizo', // 'autorizo' | 'no_autorizo'
    mrnum: null,
    medico_tratante: '',
    cedula: '',
    diagnostico: '',
    proced_para_confirmar_diagnost: 'Estudios preoperatorios, valoración de riesgo quirúrgico y protocolo anestésico',
    beneficio_de_dicho_procedimiento: 'Resolución terapéutica de la patología de base, preservación funcional y mejora en la calidad de vida',
    tratamientos_medicos: 'Manejo farmacológico perioperatorio, analgesia y antibioticoterapia profiláctica',
    tratamientos_quirurgicos: 'Intervención quirúrgica protocolizada bajo técnica aséptica',
    tratamientos_endoscopicos: 'No requeridos en este tiempo quirúrgico / según hallazgos transoperatorios',
    tratamientos_de_rehabilitacion: 'Deambulación temprana asistida y cuidados postoperatorios de herida quirúrgica',
    alternativas: 'Tratamiento médico expectante o diferimiento según evolución clínica',
    anestesia: 'SI',
    tipo_de_anestesia: 'General balanceada / Bloqueo neuroaxial según valoración anestesiológica',
    principales_riesgos: 'Hemorragia, infección de sitio quirúrgico, lesión de órganos o estructuras vecinas, reacciones adversas a medicamentos o anestésicos, eventos tromboembólicos',
    paciente_capaz: true,
    pariente: '',
    testigo1: '',
    testigo2: '',
    motivo_de_no_autorizacion: '',
    domicilio_testigo1: 'Conocido en expediente clínico',
    identificacion_testigo1: 'INE / Identificación Oficial',
    parentesco_testigo1: 'Familiar / Testigo Presencial',
    saving: false
  });

  const [consentModal15, setConsentModal15] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    tipo: 'autorizo', // 'autorizo' | 'no_autorizo'
    medico_tratante: '',
    cedula: '',
    diagnostico: 'EMBARAZO A TÉRMINO / INDICACIÓN DE CESÁREA',
    procedimiento_consiste: 'Extracción quirúrgica del feto mediante laparotomía e histerotomía transversa',
    beneficios: 'Nacimiento seguro y oportuno del recién nacido y preservación de la salud materna',
    alternativas: 'Parto vaginal expectante o monitoreo continuo materno-fetal según evolución',
    paciente_capaz: true,
    pariente: '',
    testigo1: '',
    testigo2: '',
    motivo_no_acepto: '',
    domicilio_testigo: '',
    identificacion_testigo: '',
    parentesco_testigo: '',
    saving: false
  });

  const [consentModal04, setConsentModal04] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    medico_tratante: '',
    cedula: '',
    paciente_capaz: true,
    pariente: '',
    testigo1: '',
    saving: false
  });

  const [consentModal12, setConsentModal12] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    medico_tratante: '',
    cedula: '',
    diagnostico: '',
    servicio: 'URGENCIAS',
    beneficios: 'Evaluación integral de la condición materno-fetal, resolución adecuada del evento obstétrico.',
    alternativas: 'Manejo médico expectante, tratamiento farmacológico alternativo o diferimiento según evolución clínica.',
    paciente_capaz: true,
    pariente: '',
    testigo1: '',
    testigo2: '',
    saving: false
  });

  const [consentModal3401, setConsentModal3401] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    medico_tratante: '',
    cedula: '',
    tipo_interrogatorio: 'DIRECTO',
    paciente_capaz: true,
    pariente: '',
    testigo1: '',
    testigo2: '',
    gruporh: 'O POSITIVO',
    alergias: 'NEGADAS',
    ta: '', fc_meta: '', f_resp: '', temperatura: '', peso: '', talla: '',
    irm: '', fbpr: '', fpr: '',
    conclusiones: '', conclusiones_2: '', conclusiones_3: '',
    ta_basal: '', fc_basal: '', obs_basal: '',
    ta_p_inicio: '', fc_p_inicio: '', obs_p_inicio: '',
    ta_p_2: '', fc_p_2: '', obs_p_2: '',
    ta_p_4: '', fc_p_4: '', obs_p_4: '',
    ta_p_6: '', fc_p_6: '', obs_p_6: '',
    ta_p_8: '', fc_p_8: '', obs_p_8: '',
    ta_p_10: '', fc_p_10: '', obs_p_10: '',
    ta_p_12: '', fc_p_12: '', obs_p_12: '',
    ta_p_14: '', fc_p_14: '', obs_p_14: '',
    ta_p_16: '', fc_p_16: '', obs_p_16: '',
    ta_p_18: '', fc_p_18: '', obs_p_18: '',
    ta_p_20: '', fc_p_20: '', obs_p_20: '',
    ta_a_inicio: '', fc_a_inicio: '', obs_a_inicio: '',
    ta_a_2: '', fc_a_2: '', obs_a_2: '',
    ta_a_4: '', fc_a_4: '', obs_a_4: '',
    ta_a_6: '', fc_a_6: '', obs_a_6: '',
    ta_a_8: '', fc_a_8: '', obs_a_8: '',
    ta_a_10: '', fc_a_10: '', obs_a_10: '',
    ta_a_12: '', fc_a_12: '', obs_a_12: '',
    ta_a_14: '', fc_a_14: '', obs_a_14: '',
    ta_final: '', fc_final: '', obs_final: '',
    saving: false
  });

    const [consentModal25, setConsentModal25] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    medico_tratante: '',
    cedula: '',
    testigo1: '',
    testigo2: '',
    paciente_capaz: true,
    pariente: '',
    paciente_o_representante: '',
    saving: false
  });

    const [consentModalEED, setConsentModalEED] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    tipo_interrogatorio: 'Directo',
    paciente_capaz: true,
    responsable: '',
    comentarios: '',
    ta: '', fc_meta: '', fr: '', talla: '', peso: '',
    ta_basal: '', fc_basal: '', so2_basal: '', s_basal: '',
    ta_5mcg: '', fc_5mcg: '', so2_5mcg: '', s_5mcg: '',
    ta_10mcg: '', fc_10mcg: '', so2_10mcg: '', s_10mcg: '',
    ta_20mcg: '', fc_20mcg: '', so2_20mcg: '', s_20mcg: '',
    ta_30mcg: '', fc_30mcg: '', so2_30mcg: '', s_30mcg: '',
    ta_40mcg: '', fc_40mcg: '', so2_40mcg: '', s_40mcg: '',
    ta_antropina: '', fc_antropina: '', so2_antropina: '', s_antropina: '',
    ta_2min: '', fc_2min: '', so2_2min: '', sintomas_2min: '',
    ta_4min: '', fc_4min: '', so2_4min: '', sintomas_4min: '',
    saving: false
  });

  const [consentModal43, setConsentModal43] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    medico_tratante: '',
    cedula: '',
    diagnostico: 'INSUFICIENCIA RESPIRATORIA AGUDA / COMPROMISO DE VÍA AÉREA',
    servicio: 'URGENCIAS / TERAPIA INTENSIVA',
    beneficios: 'Aseguramiento de la vía aérea permeable, soporte ventilatorio mecánico invasivo, optimización de la oxigenación tisular y prevención del paro respiratorio o colapso hemodinámico.',
    riesgos: 'Traumatismo de la vía aérea (laringe, cuerdas vocales, tráquea), broncoaspiración, intubación esofágica o selectiva, broncoespasmo, arritmias, hipotensión, neumotórax o necesidad de ventilación mecánica prolongada.',
    alternativas: 'Oxigenoterapia de alto flujo, ventilación mecánica no invasiva (según indicación y estabilidad clínica) o manejo médico conservador.',
    paciente_capaz: true,
    pariente: '',
    testigo1: '',
    testigo2: '',
    domicilio_testigo1: 'Conocido en expediente clínico',
    identificacion_testigo1: 'INE / Identificación Oficial',
    parentesco_testigo1: 'Familiar / Testigo Presencial',
    domicilio_testigo2: 'Conocido en expediente clínico',
    identificacion_testigo2: 'INE / Identificación Oficial',
    parentesco_testigo2: 'Familiar / Testigo Presencial',
    saving: false
  });

  const [consentModal06, setConsentModal06] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    mrnum: null,
    medico_anestesiologo: '',
    cedula: '',
    cedula_especialidad: 'CÉD. ESP. 9827461',
    diagnostico: 'PROGRAMACIÓN QUIRÚRGICA / VALORACIÓN ANESTESIOLÓGICA',
    servicio: 'QUIRÓFANO',
    tipo_cirugia: 'PROGRAMADA',
    magnitud_cirugia: 'MAYOR',
    asa: 'CLASE II',
    tipo_anestesia: 'ANESTESIA GENERAL BALANCEADA CON INTUBACIÓN OROTRAQUEAL / BLOQUEO NEUROAXIAL',
    beneficios_anestesia: 'Abolición del dolor y sensibilidad táctil, estabilidad hemodinámica y relajación muscular transoperatoria.',
    alternativas_anestesia: 'Anestesia neuroaxial pura, sedación consciente monitoreada o anestesia local infiltrativa según técnica.',
    paciente_capaz: true,
    pariente: '',
    parentesco: 'Paciente',
    testigo1: '',
    testigo2: '',
    saving: false
  });

  const [consentModal11, setConsentModal11] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    mrnum: null,
    medico_tratante: '',
    cedula: '',
    diagnostico: 'ENFERMEDAD EN ETAPA AVANZADA / PRONÓSTICO GRAVE Y LIMITADO',
    servicio: 'URGENCIAS / MEDICINA INTERNA',
    beneficios_y_riesgos_de_nr: 'Evitar encarnizamiento terapéutico y maniobras invasivas desproporcionadas en fase terminal, garantizando confort y dignidad.',
    riesgos_de_no_aplicar: 'Cese irreversible de las funciones cardiorrespiratorias y sobreveniencia de la muerte natural sin soporte artificial.',
    alternativa_nr: 'Manejo médico conservador integral, analgesia multimodal, sedación paliativa y medidas de confort bioético.',
    paciente_capaz: true,
    pariente: '',
    parentesco: 'Paciente',
    testigo1: '',
    testigo2: '',
    saving: false
  });

  const [consentModal19, setConsentModal19] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    tipo: 'autorizo',
    mrnum: null,
    medico_tratante: '',
    cedula: '',
    diagnostico: 'MIOMATOSIS UTERINA / HEMORRAGIA UTERINA ANORMAL',
    explicacion_de_proceso: 'Histerectomía total abdominal / laparoscópica con hemostasia cuidadosa y técnica quirúrgica normada.',
    beneficios_de_procedimiento: 'Resolución definitiva del sangrado uterino anormal, dolor pélvico crónico o patología ginecológica.',
    intervencion_complementaria: 'Salpingectomía bilateral, ooforectomía o lisis de adherencias según hallazgos transoperatorios y edad.',
    alternativas_terapeuticas: 'Manejo hormonal farmacológico, miomectomía conservadora o dispositivo intrauterino medicado.',
    motivo_de_no_autorizacion: '',
    paciente_capaz: true,
    pariente: '',
    parentesco: 'Paciente',
    testigo1: '',
    testigo2: '',
    saving: false
  });

  // ESTADOS PARA FORMATO 15: EGRESO VOLUNTARIO (HE-DIRMED-SINPRO-PLT-15)
  const [selectedMrnum15EV, setSelectedMrnum15EV] = useState(null);
  const [modal15EV, setModal15EV] = useState({
    open: false,
    isEdit: false,
    isNew: true,
    mrnum: null,
    medico_tratante: '',
    cedula: '',
    diagnostico_ingreso: '',
    diagnostico_egreso: '',
    motivo_egreso: 'Decisión personal y familiar para continuar con la convalecencia y cuidados médicos en domicilio particular.',
    medidas_recomendadas: 'Continuar con hidratación oral estricta con electrolitos, dieta blanda fraccionada, apego puntual al tratamiento farmacológico prescrito en la receta médica adjunta, reposo relativo en domicilio y control térmico con medios físicos.',
    factores_riesgo: 'Deshidratación severa, desequilibrio hidroelectrolítico, deterioro clínico agudo por omisión de vigilancia intrahospitalaria y necesidad de reingreso urgente a unidad hospitalaria.',
    paciente_capaz: true,
    declarante: '',
    parentesco: 'El Paciente',
    identificacion: 'INE / Identificación Oficial',
    domicilio_declarante: 'Conocido en expediente clínico',
    testigo1: '',
    parentesco1: '',
    identificacion1: '',
    domicilio1: '',
    testigo2: '',
    parentesco2: '',
    identificacion2: '',
    domicilio2: '',
    saving: false
  });

  // ESTADOS UNIVERSALES PARA CUALQUIERA DE LOS 100+ FORMATOS CLÍNICOS EN VERTICAL
  const [genericFormatHistory, setGenericFormatHistory] = useState([]);
  const [loadingGenericHistory, setLoadingGenericHistory] = useState(false);
  const [selectedGenericMrnum, setSelectedGenericMrnum] = useState(null);
  const [creatingGenericRecord, setCreatingGenericRecord] = useState(false);
  const [universalEditModal, setUniversalEditModal] = useState({
    open: false,
    isEdit: false,
    isNew: false,
    mrnum: null,
    codigo: '',
    nombre: '',
    medico_tratante: '',
    diagnostico: '',
    observaciones: '',
    paciente_capaz: true,
    tutor: '',
    parentesco: '',
    identificacion_tutor: '',
    domicilio_tutor: '',
    testigo1: '',
    parentesco1: '',
    identificacion1: '',
    domicilio1: '',
    testigo2: '',
    parentesco2: '',
    identificacion2: '',
    domicilio2: '',
    saving: false
  });

  // Lector Biométrico DigitalPersona
  const { 
    status: dpStatus, 
    isReady: dpReady, 
    isAcquiring: dpAcquiring, 
    fmdTemplate: dpFmd, 
    captureContext: dpCaptureContext,
    challengeId: dpChallengeId,
    sessionId: dpSessionId,
    error: dpError, 
    startCapture: dpStartCapture, 
    resetFmd: dpResetFmd, 
    stopCapture: dpStopCapture 
  } = useDigitalPersona();

  // Modal de Firma Biométrica
  const [signingModal, setSigningModal] = useState({
    open: false,
    slot: 1,
    title: 'Nota de Evolución 1',
    content: '',
    submitting: false,
    successMsg: null,
    errorMsg: null
  });
  const signingVersion = useRef(0);
  const signingCloseTimer = useRef(null);

  // Modal de Auditoría y Verificación de Sello Completo NOM
  const [auditModal, setAuditModal] = useState({
    open: false,
    firma: null,
    loading: false,
    verification: null,
    copied: null
  });

  // Modal de Toma y Modificación de Signos Vitales (PTVS - SQL Server)
  const [vitalsHistoryModal, setVitalsHistoryModal] = useState({
    open: false,
    loading: false,
    history: []
  });

  const handleOpenVitalsHistory = async () => {
    setVitalsHistoryModal({ open: true, loading: true, history: [] });
    try {
      const res = await api.get(`/ehr/paciente/${patientId}/historial-signos-vitales`);
      setVitalsHistoryModal({
        open: true,
        loading: false,
        history: res.data || []
      });
    } catch (err) {
      console.error("Error fetching vitals history:", err);
      setVitalsHistoryModal({ open: true, loading: false, history: [] });
    }
  };

    const [vitalsModal, setVitalsModal] = useState({
    open: false,
    systolic: '120',
    diastolic: '80',
    pulse: '78',
    respiratory: '18',
    oxygen_saturation: '98',
    temperature: '36.5',
    weight: '75.0',
    height: '1.72',
    submitting: false,
    errorMsg: null,
    successMsg: null
  });

  const handleOpenVitalsModal = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden registrar ni modificar signos vitales en un paciente dado de alta.");
      return;
    }
    const ptvs = data?.ptvs || {};
    const sys = ptvs.systolic || (ptvs.ta ? ptvs.ta.split('/')[0] : '120');
    const dia = ptvs.diastolic || (ptvs.ta ? ptvs.ta.split('/')[1] : '80');
    
    setVitalsModal({
      open: true,
      systolic: sys || '120',
      diastolic: dia || '80',
      pulse: ptvs.fc || '78',
      respiratory: ptvs.fr || '18',
      oxygen_saturation: ptvs.sat_o2 || '98',
      temperature: ptvs.temp || '36.5',
      weight: ptvs.peso || '75.0',
      height: ptvs.talla || '1.72',
      submitting: false,
      errorMsg: null,
      successMsg: null
    });
  };

  const handleSaveVitals = async (e) => {
    e.preventDefault();
    setVitalsModal(prev => ({ ...prev, submitting: true, errorMsg: null, successMsg: null }));
    try {
      await api.post(`/ehr/paciente/${patientId}/signos-vitales`, {
        systolic: vitalsModal.systolic,
        diastolic: vitalsModal.diastolic,
        pulse: vitalsModal.pulse,
        respiratory: vitalsModal.respiratory,
        oxygen_saturation: vitalsModal.oxygen_saturation,
        temperature: vitalsModal.temperature,
        weight: vitalsModal.weight,
        height: vitalsModal.height
      });
      setVitalsModal(prev => ({ ...prev, submitting: false, successMsg: "¡Signos vitales guardados exitosamente!" }));
      setTimeout(() => {
        setVitalsModal(prev => ({ ...prev, open: false, successMsg: null }));
        fetchData();
      }, 900);
    } catch (err) {
      console.error("Error saving PTVS vitals:", err);
      setVitalsModal(prev => ({
        ...prev,
        submitting: false,
        errorMsg: err.response?.data?.detail || "Error al guardar signos vitales."
      }));
    }
  };

  const handleOpenAuditModal = async (firmaOrInfo) => {
    const firmaObj = (firmaOrInfo && typeof firmaOrInfo === 'object') ? firmaOrInfo : {};
    const safeFirma = {
      id: firmaObj.id || null,
      nombre_medico: firmaObj.nombre_medico || data?.patient?.attending || 'MÉDICO TRATANTE HES',
      cedula_profesional: firmaObj.cedula_profesional || data?.patient?.cedula || '',
      sello_digital: firmaObj.sello_digital || '',
      hash_sha256: firmaObj.hash_sha256 || '',
      codigo_formato: firmaObj.codigo_formato || selectedFormat?.codigo || '',
      evolution_slot: firmaObj.evolution_slot || firmaObj.slot || 0,
      ...firmaObj
    };

    setAuditModal({
      open: true,
      firma: safeFirma,
      loading: true,
      verification: null,
      copied: null,
      showVerticalQR: true
    });

    try {
      const res = await api.post(`/ehr/paciente/${patientId}/verificar-integridad`, {
        firma_id: safeFirma.id || null,
        codigo_formato: safeFirma.codigo_formato || selectedFormat?.codigo || null,
        slot: safeFirma.evolution_slot || 0
      });
      if (res.data) {
        setAuditModal(prev => ({
          ...prev,
          loading: false,
          verification: res.data,
          firma: {
            ...prev.firma,
            nombre_medico: res.data.triada_seguridad?.identidad?.firmante || prev.firma?.nombre_medico,
            cedula_profesional: res.data.triada_seguridad?.identidad?.cedula || prev.firma?.cedula_profesional,
            sello_digital: res.data.sello_digital || prev.firma?.sello_digital,
            hash_sha256: res.data.hash_sha256 || prev.firma?.hash_sha256
          }
        }));
      }
    } catch (err) {
      console.error("Error verifying integrity in real time:", err);
      setAuditModal(prev => ({
        ...prev,
        loading: false,
        verification: {
          integro: false,
          estado: err.response?.data?.detail || "No se pudo completar la verificación en tiempo real con el servidor."
        }
      }));
    }
  };

  // Modal de Prescripción Médica de Fármacos (PTDG - SQL Server)
  const [prescriptionModal, setPrescriptionModal] = useState({
    open: false,
    name: '',
    amount: '',
    uom: 'mg',
    route: 'Oral',
    frequency: 'Cada 8 horas',
    prn: false,
    why: '',
    dispense: '',
    refills: 0,
    instruction: '',
    waitingFingerprint: false,
    submitting: false,
    errorMsg: null,
    successMsg: null
  });

  const handleOpenPrescriptionModal = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden prescribir fármacos en un paciente dado de alta.");
      return;
    }
    setPrescriptionModal({
      open: true,
      name: '',
      amount: '',
      uom: 'mg',
      route: 'Oral',
      frequency: 'Cada 8 horas',
      prn: false,
      why: '',
      dispense: '',
      refills: 0,
      instruction: '',
      waitingFingerprint: false,
      submitting: false,
      errorMsg: null,
      successMsg: null
    });
    dpResetFmd();
  };

  const handleStartPrescriptionFingerprint = (e) => {
    e.preventDefault();
    if (!prescriptionModal.name.trim()) {
      setPrescriptionModal(prev => ({ ...prev, errorMsg: "Ingrese el nombre del fármaco o principio activo." }));
      return;
    }
    setPrescriptionModal(prev => ({ ...prev, waitingFingerprint: true, errorMsg: null, successMsg: null }));
    dpResetFmd();
    dpStartCapture({
      action: 'PRESCRIPCION',
      patientRef: patientId,
      documentCode: 'HE-DIRMED-SINPRO-REC-01'
    });
  };

  // Modal para Suspender / Discontinuar Fármaco
  const [discontinueModal, setDiscontinueModal] = useState({
    open: false,
    med: null,
    reason: 'Completó esquema terapéutico / Modificación de plan',
    waitingFingerprint: false,
    submitting: false,
    errorMsg: null,
    successMsg: null
  });

  const handleOpenDiscontinue = (med) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden suspender ni modificar fármacos en un paciente dado de alta.");
      return;
    }
    setDiscontinueModal({
      open: true,
      med,
      reason: 'Completó esquema terapéutico / Modificación de plan',
      waitingFingerprint: false,
      submitting: false,
      errorMsg: null,
      successMsg: null
    });
    dpResetFmd();
  };

  const handleStartDiscontinueFingerprint = (e) => {
    e.preventDefault();
    setDiscontinueModal(prev => ({ ...prev, waitingFingerprint: true, errorMsg: null }));
    dpResetFmd();
    dpStartCapture({
      action: 'SUSPENSION',
      patientRef: patientId,
      documentCode: 'HE-DIRMED-SINPRO-SUSP-01'
    });
  };

  // Modal de Prescripción de Régimen Dietético y Cuidados (MR_SOL_DIET + PostgreSQL)
  const [dietModal, setDietModal] = useState({
    open: false,
    tipo_dieta: 'Ayuno Estricto',
    horario: 'Continuo',
    fase_clinica: '',
    indicaciones_nutricionales: '',
    inicio_ayuno_dieta: '',
    nutriologo_responsable: '',
    alergias_alimentarias: '',
    tolerancia_via_oral: 'Adecuada',
    cuidados_enfermeria: [],
    waitingFingerprint: false,
    submitting: false,
    errorMsg: null,
    successMsg: null
  });

  const handleOpenDietModal = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden prescribir dietas ni cuidados en un paciente dado de alta.");
      return;
    }
    setDietModal(prev => ({
      ...prev,
      open: true,
      tipo_dieta: (dietas && dietas.tipo && dietas.tipo !== 'Sin dieta asignada') ? dietas.tipo : 'Ayuno Estricto',
      horario: (dietas && dietas.horario && dietas.horario !== '--') ? dietas.horario : 'Continuo',
      fase_clinica: (dietas && dietas.fase && dietas.fase !== '--') ? dietas.fase : '',
      indicaciones_nutricionales: (dietas && dietas.indicaciones && !dietas.indicaciones.startsWith('No se ha')) ? dietas.indicaciones : '',
      inicio_ayuno_dieta: (dietas && dietas.inicio && dietas.inicio !== '--') ? dietas.inicio : (new Date().toLocaleDateString('es-MX') + ' ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
      nutriologo_responsable: (dietas && dietas.nutriologo && dietas.nutriologo !== '--') ? dietas.nutriologo : '',
      alergias_alimentarias: (dietas && dietas.alergias_alimentarias && dietas.alergias_alimentarias !== '--') ? dietas.alergias_alimentarias : '',
      tolerancia_via_oral: (dietas && dietas.tolerancia_via_oral && dietas.tolerancia_via_oral !== '--') ? dietas.tolerancia_via_oral : 'Adecuada',
      cuidados_enfermeria: (cuidados_enfermeria && Array.isArray(cuidados_enfermeria)) ? [...cuidados_enfermeria] : [],
      waitingFingerprint: false,
      submitting: false,
      errorMsg: null,
      successMsg: null
    }));
    dpResetFmd();
  };

  const handleStartDietFingerprint = (e) => {
    e.preventDefault();
    setDietModal(prev => ({ ...prev, waitingFingerprint: true, errorMsg: null, successMsg: null }));
    dpResetFmd();
    dpStartCapture({
      action: 'DIETA',
      patientRef: patientId,
      documentCode: 'HE-DIRMED-SINPRO-DIETA-01'
    });
  };

  // Modal de Gestión de Alergias (PTAL + DIS_AL en SQL Server)
  const [allergyModal, setAllergyModal] = useState({
    open: false,
    allergiesList: [],
    customAllergiesText: '',
    searchCatalog: '',
    catalogResults: [],
    selectedAllergy: null,
    allergic_since: '',
    notes: '',
    loadingCatalog: false,
    submitting: false,
    submittingText: false,
    errorMsg: null,
    successMsg: null
  });

  // CIERRE DE MODALES CON TECLA ESC
  useEscapeKey(signingModal.open, () => {
    setSigningModal(prev => ({ ...prev, open: false }));
    dpStopCapture();
  });
  useEscapeKey(auditModal.open && auditModal.firma, () => setAuditModal({ open: false, firma: null, loading: false, verification: null, copied: null }));
  useEscapeKey(vitalsHistoryModal.open, () => setVitalsHistoryModal(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModal25.open, () => setConsentModal25(prev => ({ ...prev, open: false })));
  useEscapeKey(vitalsModal.open, () => setVitalsModal(prev => ({ ...prev, open: false })));
  useEscapeKey(prescriptionModal.open, () => setPrescriptionModal(prev => ({ ...prev, open: false, waitingFingerprint: false })));
  useEscapeKey(discontinueModal.open, () => setDiscontinueModal(prev => ({ ...prev, open: false })));
  useEscapeKey(dietModal.open, () => setDietModal(prev => ({ ...prev, open: false, waitingFingerprint: false })));
  useEscapeKey(allergyModal.open, () => setAllergyModal(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModal08.open, () => setConsentModal08(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModal02.open, () => setConsentModal02(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModal3201.open, () => setConsentModal3201(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModalEED.open, () => setConsentModalEED(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModal43.open, () => setConsentModal43(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModal06.open, () => setConsentModal06(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModal11.open, () => setConsentModal11(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModal19.open, () => setConsentModal19(prev => ({ ...prev, open: false })));
  useEscapeKey(modal15EV.open, () => setModal15EV(prev => ({ ...prev, open: false })));
  useEscapeKey(universalEditModal.open, () => setUniversalEditModal(prev => ({ ...prev, open: false })));

  const fetchPatientAllergies = async () => {
    try {
      const res = await api.get(`/ehr/paciente/${patientId}/alergias`);
      if (res.data && Array.isArray(res.data)) {
        setAllergyModal(prev => ({ ...prev, allergiesList: res.data }));
      }
    } catch (e) {
      console.warn("Error loading patient allergies:", e);
    }
  };

  const handleOpenAllergyModal = async () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden modificar alergias en un paciente dado de alta.");
      return;
    }
    setAllergyModal(prev => ({
      ...prev,
      open: true,
      customAllergiesText: (patient && patient.allergies && patient.allergies !== 'Sin alergias reportadas' && patient.allergies !== 'Sin alergias registradas') ? patient.allergies : '',
      searchCatalog: '',
      catalogResults: [],
      selectedAllergy: null,
      allergic_since: '',
      notes: '',
      errorMsg: null,
      successMsg: null
    }));
    await fetchPatientAllergies();
  };

  // Modal de Captura / Edición de Nota de Evolución
  const [notaModal, setNotaModal] = useState({
    open: false,
    isEdit: false,
    evolution_num: 1,
    fecha: new Date().toISOString().split('T')[0],
    hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
    turno: 'Matutino',
    vitals_ta: '',
    vitals_fc: '',
    vitals_fr: '',
    vitals_sato2: '',
    vitals_peso: '',
    vitals_talla: '',
    vitals_temp: '',
    subjetivo: '',
    objetivo: '',
    analisis: '',
    plan: '',
    medico: '',
    cedula: '',
    mip: ''
  });
  const [savingNota, setSavingNota] = useState(false);
  const [savingConsent, setSavingConsent] = useState(false);

  useEscapeKey(notaModal.open, () => setNotaModal(prev => ({ ...prev, open: false })));

  const fetchFirmas = async () => {
    try {
      const res = await api.get(`/ehr/paciente/${patientId}/firmas`);
      if (res.data && Array.isArray(res.data)) {
        setFirmas(res.data);
      }
    } catch(e){
      console.warn("Could not load firmas:", e);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const res = await api.get(`/ehr/paciente/${patientId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (res.data && res.data.patient && !res.data.error) {
        setData(res.data);
        if (res.data.consentimiento_32_01) {
          setConsentForm3201({
            tipo_interrogatorio: res.data.consentimiento_32_01.tipo_interrogatorio || 'Directo',
            testigo1: res.data.consentimiento_32_01.testigo1 || '',
            testigo2: res.data.consentimiento_32_01.testigo2 || '',
            paciente_o_representante: res.data.consentimiento_32_01.paciente_o_representante || res.data.patient.name || '',
            representante_legal: res.data.consentimiento_32_01.representante_legal || ''
          });
        } else {
          setConsentForm3201(prev => ({
            ...prev,
            paciente_o_representante: res.data.patient.name,
          }));
        }
      } else {
        setError(res.data?.error || res.data?.detail || "Error al obtener datos");
      }
    } catch (err) {
      console.error("Error fetching EHR:", err);
      setError("Error de conexión con el servidor. ¿Está el backend actualizado y ejecutándose?");
    } finally {
      setLoading(false);
    }
  };

  const fetchFirmantes = async () => {
    try {
      const res = await api.get(`/pacientes/${patientId}/firmantes-biometricos`);
      setFirmantesList(res.data || []);
    } catch (err) {
      console.debug("Error consultando firmantes:", err);
    }
  };

  const handleDeleteFirmanteFromDashboard = async (firmanteId, firmanteNombre) => {
    if (!window.confirm(`¿Estás seguro de eliminar a "${firmanteNombre}" del directorio de firmantes de este paciente?`)) {
      return;
    }
    try {
      await api.delete(`/pacientes/${patientId}/firmantes-biometricos/${firmanteId}`);
      await fetchFirmantes();
    } catch (err) {
      console.error("Error eliminando firmante:", err);
      alert("Error al eliminar firmante: " + (err.response?.data?.detail || err.message));
    }
  };

  const getFirmanteBadgeConfig = (tipo) => {
    switch (tipo) {
      case 'PACIENTE':
        return { label: 'Paciente', style: 'bg-blue-50 text-blue-700 border-blue-200' };
      case 'REPRESENTANTE_LEGAL':
      case 'TUTOR':
        return { label: 'Tutor o responsable', style: 'bg-amber-50 text-amber-800 border-amber-200' };
      case 'TESTIGO_1':
        return { label: 'Primer testigo', style: 'bg-slate-50 text-slate-700 border-slate-200' };
      case 'TESTIGO_2':
        return { label: 'Segundo testigo', style: 'bg-slate-50 text-slate-700 border-slate-200' };
      case 'TESTIGO':
        return { label: 'Testigo', style: 'bg-slate-50 text-slate-700 border-slate-200' };
      default:
        return { label: 'Contacto Familiar', style: 'bg-slate-100 text-slate-700 border-slate-200' };
    }
  };

  useEffect(() => {
    fetchData();
    fetchFirmas();
    fetchFirmantes();
  }, [patientId]);

  // Manejar captura de huella para firmar documento
  const handleOpenBiometricSign = (slot, title, content, codigoFormato, tipoDocumento) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden firmar ni refirmar documentos en un episodio cerrado / paciente de alta.");
      return;
    }
    setSigningModal({
      open: true,
      slot,
      title,
      content,
      codigoFormato,
      tipoDocumento,
      submitting: false,
      successMsg: null,
      errorMsg: null
    });
    dpResetFmd();
  };

  // Helper para consultar estado de firmas (Médico, Paciente/Tutor, Testigos) conforme a NOM-004
  const getDocumentSignaturesSummary = (codigoFormato, slot = 0) => {
    if (!codigoFormato || !firmas || !Array.isArray(firmas)) {
      return {
        firmaMedico: null,
        firmaPaciente: null,
        firmaTestigo1: null,
        firmaTestigo2: null,
        hasMedico: false,
        hasPaciente: false,
        hasTestigo1: false,
        hasTestigo2: false,
        isFullySigned: false,
        allFirmas: []
      };
    }
    const cleanCodigo = codigoFormato.replace('HE-DIRMED-', '').replace('SINPRO-', '').replace('CONSUL-', '');
    const docFirmas = firmas.filter(f => 
      f.codigo_formato === codigoFormato &&
      (
        (slot && f.evolution_slot === slot) ||
        (!slot && (f.evolution_slot === 0 || f.evolution_slot === null || f.evolution_slot === undefined))
      )
    );
    const firmaMedico = docFirmas.find(f => (f.rol_firmante || 'MEDICO').toUpperCase() === 'MEDICO');
    const firmaPaciente = docFirmas.find(f => ['PACIENTE', 'REPRESENTANTE_LEGAL', 'TUTOR'].includes((f.rol_firmante || '').toUpperCase()));
    const firmaTestigo1 = docFirmas.find(f => ['TESTIGO_1', 'TESTIGO'].includes((f.rol_firmante || '').toUpperCase()));
    const firmaTestigo2 = docFirmas.find(f => (f.rol_firmante || '').toUpperCase() === 'TESTIGO_2');

    return {
      firmaMedico,
      firmaPaciente,
      firmaTestigo1,
      firmaTestigo2,
      hasMedico: Boolean(firmaMedico),
      hasPaciente: Boolean(firmaPaciente),
      hasTestigo1: Boolean(firmaTestigo1),
      hasTestigo2: Boolean(firmaTestigo2),
      isFullySigned: Boolean(firmaMedico &&
        (!docFirmas.some(f => f.requiere_testigos) || (firmaPaciente && firmaTestigo1 && firmaTestigo2))),
      allFirmas: docFirmas
    };
  };

  // La firma médica es independiente del flujo de paciente, familiares y testigos.
  const handleDoctorSign = (slot, title, content, codigoFormato, tipoDocumento) => {
    if (isPatientDischarged) {
      alert('Este expediente está cerrado porque el paciente ya fue dado de alta. No se pueden agregar firmas.');
      return;
    }
    handleOpenBiometricSign(slot, title, content, codigoFormato, tipoDocumento);
  };

  const patientSignatureLabel = (summary) => summary?.hasPaciente
    ? '✓ Paciente / familiar'
    : 'Firmar paciente / familiar';

  const doctorSignatureLabel = (summary) => summary?.hasMedico
    ? '✓ Firma médica'
    : 'Firmar como médico';

  // La lectura comienza solo cuando el usuario pulsa "Leer huella".
  useEffect(() => {
    signingVersion.current += 1;
    if (signingModal.open) dpResetFmd();
    return () => {
      signingVersion.current += 1;
      clearTimeout(signingCloseTimer.current);
      if (signingModal.open) dpResetFmd();
    };
  }, [signingModal.open, patientId, signingModal.codigoFormato, signingModal.slot]);

  useEffect(() => {
    if (signingModal.open && dpFmd && !signingModal.submitting && !signingModal.successMsg) {
      if (dpCaptureContext?.action !== 'FIRMA_MEDICA' || String(dpCaptureContext.patientRef) !== String(patientId)
        || dpCaptureContext.documentCode !== (signingModal.codigoFormato || 'HE-DIRMED-SINPRO-PLT-87/01')
        || String(dpCaptureContext.documentRef ?? 0) !== String(signingModal.slot ?? 0)) return;
      const executeBiometricSign = async () => {
        const version = signingVersion.current;
        try {
          setSigningModal(prev => ({ ...prev, submitting: true, errorMsg: null }));
          const res = await api.post(`/ehr/paciente/${patientId}/firmar-biometrico`, {
            codigo_formato: signingModal.codigoFormato || 'HE-DIRMED-SINPRO-PLT-87/01',
            tipo_documento: signingModal.tipoDocumento || `Nota de Evolución de Urgencias (Evolución ${signingModal.slot})`,
            evolution_slot: signingModal.slot,
            fmd_template: dpFmd,
            challenge_id: dpChallengeId,
            session_id: dpSessionId,
          }, { headers: { 'Idempotency-Key': dpChallengeId } });
          if (version !== signingVersion.current) return;
          
          if (isConfirmedClinicalSync(res)) {
            setSigningModal(prev => ({
              ...prev,
              submitting: false,
              successMsg: 'Firma guardada correctamente.'
            }));
            await fetchFirmas();
            await fetchData();
            if (selectedFormat && selectedFormat.codigo) {
              await fetchGenericHistory(selectedFormat.codigo);
            }
            if (version !== signingVersion.current) return;
            signingCloseTimer.current = setTimeout(() => {
              setSigningModal(prev => ({ ...prev, open: false }));
              dpResetFmd();
            }, 2500);
          } else {
            setSigningModal(prev => ({ 
              ...prev, 
              submitting: false, 
              errorMsg: res.status === 202
                ? `Firma guardada localmente; sincronización pendiente (${res.data.operation_id}).`
                : (res.data?.message || res.data?.error || "Huella dactilar no reconocida. Sensor reiniciado: limpie su dedo y colóquelo de nuevo.")
            }));
            dpResetFmd();
          }
        } catch (err) {
          if (version !== signingVersion.current) return;
          console.error("No se confirmó la firma biométrica; consulte el mensaje de la interfaz.");
          setSigningModal(prev => ({ 
            ...prev, 
            submitting: false, 
            errorMsg: err.response?.data?.detail || "Huella dactilar no reconocida. Sensor reiniciado: limpie su dedo y colóquelo de nuevo." 
          }));
          dpResetFmd();
        }
      };
      executeBiometricSign();
    }
  }, [dpFmd, signingModal.open]);

  // Biometría para Prescripción Médica de Fármacos
  useEffect(() => {
    if (prescriptionModal.open && prescriptionModal.waitingFingerprint && dpFmd && !prescriptionModal.submitting && !prescriptionModal.successMsg) {
      const executePrescriptionBiometric = async () => {
        try {
          setPrescriptionModal(prev => ({ ...prev, submitting: true, errorMsg: null }));
          const res = await api.post(`/ehr/paciente/${patientId}/medicamentos/prescribir-biometrico`, {
            name: prescriptionModal.name,
            amount: prescriptionModal.amount,
            uom: prescriptionModal.uom,
            route: prescriptionModal.route,
            frequency: prescriptionModal.frequency,
            prn: prescriptionModal.prn,
            why: prescriptionModal.why,
            dispense: prescriptionModal.dispense,
            refills: prescriptionModal.refills,
            instruction: prescriptionModal.instruction,
            fmd_template: dpFmd,
            challenge_id: dpChallengeId,
            session_id: dpSessionId
          }, { headers: { 'Idempotency-Key': dpChallengeId } });

          if (isConfirmedClinicalSync(res)) {
            setPrescriptionModal(prev => ({
              ...prev,
              submitting: false,
              successMsg: res.data.message
            }));
            await fetchData();
            setTimeout(() => {
              setPrescriptionModal(prev => ({ ...prev, open: false, waitingFingerprint: false, successMsg: null }));
              dpResetFmd();
            }, 1800);
          } else {
            setPrescriptionModal(prev => ({
              ...prev,
              submitting: false,
              errorMsg: res.status === 202
                ? `Prescripción guardada; sincronización pendiente (${res.data.operation_id}).`
                : (res.data?.message || res.data?.error || "Error al prescribir fármaco.")
            }));
          }
        } catch (err) {
          console.error("Falló la autorización biométrica de prescripción.");
          setPrescriptionModal(prev => ({
            ...prev,
            submitting: false,
            waitingFingerprint: false,
            errorMsg: err.response?.data?.detail || "Huella dactilar no reconocida como médico adscrito autorizado."
          }));
          dpResetFmd();
        }
      };
      executePrescriptionBiometric();
    }
  }, [dpFmd, prescriptionModal.open, prescriptionModal.waitingFingerprint]);

  // Biometría para Suspender / Discontinuar Fármaco
  useEffect(() => {
    if (discontinueModal.open && discontinueModal.waitingFingerprint && dpFmd && !discontinueModal.submitting && !discontinueModal.successMsg) {
      const executeDiscontinueBiometric = async () => {
        try {
          setDiscontinueModal(prev => ({ ...prev, submitting: true, errorMsg: null }));
          const res = await api.post(`/ehr/paciente/${patientId}/medicamentos/discontinuar-biometrico`, {
            ptdg_num: discontinueModal.med.ptdg_num,
            reason: discontinueModal.reason,
            fmd_template: dpFmd,
            challenge_id: dpChallengeId,
            session_id: dpSessionId
          }, { headers: { 'Idempotency-Key': dpChallengeId } });
          if (isConfirmedClinicalSync(res)) {
            setDiscontinueModal(prev => ({ ...prev, submitting: false, successMsg: res.data.message }));
            await fetchData();
            setTimeout(() => {
              setDiscontinueModal(prev => ({ ...prev, open: false, waitingFingerprint: false, successMsg: null }));
              dpResetFmd();
            }, 1800);
          } else {
            setDiscontinueModal(prev => ({
              ...prev,
              submitting: false,
              errorMsg: res.status === 202
                ? `Suspensión guardada; sincronización pendiente (${res.data.operation_id}).`
                : (res.data?.message || res.data?.error || "Error al suspender medicamento.")
            }));
          }
        } catch (err) {
          console.error("Falló la autorización biométrica de suspensión.");
          setDiscontinueModal(prev => ({
            ...prev,
            submitting: false,
            waitingFingerprint: false,
            errorMsg: err.response?.data?.detail || "Huella dactilar no autorizada."
          }));
          dpResetFmd();
        }
      };
      executeDiscontinueBiometric();
    }
  }, [dpFmd, discontinueModal.open, discontinueModal.waitingFingerprint]);

  // Biometría para Prescripción de Régimen Dietético y Cuidados
  useEffect(() => {
    if (dietModal.open && dietModal.waitingFingerprint && dpFmd && !dietModal.submitting && !dietModal.successMsg) {
      const executeDietBiometric = async () => {
        try {
          setDietModal(prev => ({ ...prev, submitting: true, errorMsg: null }));
          const res = await api.post(`/ehr/paciente/${patientId}/dieta-cuidados/prescribir-biometrico`, {
            tipo_dieta: dietModal.tipo_dieta,
            horario: dietModal.horario,
            fase_clinica: dietModal.fase_clinica,
            indicaciones_nutricionales: dietModal.indicaciones_nutricionales,
            inicio_ayuno_dieta: dietModal.inicio_ayuno_dieta,
            nutriologo_responsable: dietModal.nutriologo_responsable,
            alergias_alimentarias: dietModal.alergias_alimentarias,
            tolerancia_via_oral: dietModal.tolerancia_via_oral,
            cuidados_enfermeria: dietModal.cuidados_enfermeria,
            fmd_template: dpFmd,
            challenge_id: dpChallengeId,
            session_id: dpSessionId
          }, { headers: { 'Idempotency-Key': dpChallengeId } });

          if (isConfirmedClinicalSync(res)) {
            setDietModal(prev => ({
              ...prev,
              submitting: false,
              successMsg: res.data.message
            }));
            await fetchData();
            setTimeout(() => {
              setDietModal(prev => ({ ...prev, open: false, waitingFingerprint: false, successMsg: null }));
              dpResetFmd();
            }, 1800);
          } else {
            setDietModal(prev => ({
              ...prev,
              submitting: false,
              errorMsg: res.status === 202
                ? `Dieta guardada; sincronización pendiente (${res.data.operation_id}).`
                : (res.data?.message || res.data?.error || "Error al prescribir dieta.")
            }));
          }
        } catch (err) {
          console.error("Falló la autorización biométrica de dieta.");
          setDietModal(prev => ({
            ...prev,
            submitting: false,
            waitingFingerprint: false,
            errorMsg: err.response?.data?.detail || "Huella dactilar no autorizada."
          }));
          dpResetFmd();
        }
      };
      executeDietBiometric();
    }
  }, [dpFmd, dietModal.open, dietModal.waitingFingerprint]);

  // FUNCIONES UNIVERSALES PARA CUALQUIERA DE LOS 100+ FORMATOS EN VERTICAL
  const fetchGenericHistory = async (codigo) => {
    if (!codigo) return;
    try {
      setLoadingGenericHistory(true);
      const res = await api.get(`/ehr/paciente/${patientId}/formato-historial?codigo=${encodeURIComponent(codigo)}`);
      if (res.data) {
        setGenericFormatHistory(res.data);
        if (res.data.length > 0) {
          setSelectedGenericMrnum(res.data[0].mrnum);
        } else {
          setSelectedGenericMrnum(null);
        }
      }
    } catch (err) {
      console.error('Error consultando historial universal del formato:', err);
    } finally {
      setLoadingGenericHistory(false);
    }
  };

  const handleCreateGenericRecord = async (codigo, nombre) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear registros en un paciente dado de alta.");
      return;
    }
    try {
      setCreatingGenericRecord(true);
      const defFirm = getDefaultFirmantesForConsent(firmantesList);
      const res = await api.post(`/ehr/paciente/${patientId}/formato-crear-registro`, {
        codigo: codigo,
        medico_tratante: currentDoctorName || data?.patient?.attending || '',
        diagnostico: `VALORACIÓN CLÍNICA - ${nombre || 'FORMATO INSTITUCIONAL'}`,
        testigo1: defFirm.testigo1 || '',
        testigo2: defFirm.testigo2 || '',
        pariente: defFirm.tutor || '',
        representante_legal: defFirm.tutor || '',
        parentesco: defFirm.parentesco_tutor || '',
        domicilio_tutor: defFirm.domicilio_tutor || '',
        identificacion_tutor: defFirm.identificacion_tutor || ''
      });
      if (res.data && res.data.status === 'success') {
        alert(`¡Registro inicial creado en Vertical (${res.data.controller} # ${res.data.mrnum})! Ahora puedes proceder a firmarlo biométricamente.`);
        await fetchGenericHistory(codigo);
        setSelectedGenericMrnum(res.data.mrnum);
      }
    } catch (err) {
      console.error('Error creando registro universal en Vertical:', err);
      alert(err.response?.data?.detail || 'Error al crear registro en Vertical.');
    } finally {
      setCreatingGenericRecord(false);
    }
  };

  useEffect(() => {
    if (selectedFormat && selectedFormat.codigo) {
      const customCodes = [
        'HE-DIRMED-SINPRO-PLT-87/01',
        'HE-DIRMED-CONSUL-PLT-32/01',
        'HE-DIRMED-CONSUL-PLT-34',
        'HE-DIRMED-CONSUL-PLT-34/01',
        'HE-DIRMED-CONSUL-PLT-25',
        'HE-DIRMED-CONSUL-PLT-12',
        'HE-DIRMED-CONSUL-PLT-04',
        'HE-DIRMED-CONSUL-PLT-15',
        'HE-DIRMED-SINPRO-PLT-15',
        'PLT-EV-15',
        'SINPRO-PLT-15',
        'HE-DIRMED-NOTAS-HOS-EV',
        'HE-DIRMED-CONSUL-PLT-08',
        'HE-DIRMED-CONSUL-PLT-08/01',
        '08',
        'HE-DIRMED-CONSUL-PLT-02',
        'HE-DIRMED-CONSUL-PLT-EED',
        'HE-DIRMED-SINPRO-PLT-43',
        'HE-DIRMED-CONSUL-PLT-43',
        '43',
        'PLT-43',
        'HE-DIRMED-CONSUL-PLT-06',
        '06',
        'PLT-06',
        'HE-DIRMED-CONSUL-PLT-11',
        '11',
        'PLT-11',
        'HE-DIRMED-CONSUL-PLT-19',
        '19',
        'PLT-19',
        'HE-DIRMED-CONSUL-PLT-07',
        '07',
        'PLT-07'
      ];
      if (!customCodes.includes(selectedFormat.codigo)) {
        fetchGenericHistory(selectedFormat.codigo);
      }
    }
  }, [selectedFormat]);

  if (loading) {
    return <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-slate-50 text-slate-500 font-semibold">Cargando expediente clínico...</div>;
  }

  if (error || !data) {
    return <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-slate-50 text-red-500 font-semibold">{error || "No se pudo cargar el expediente."}</div>;
  }

  const { 
    patient, vitals = [], timelineEvents = [], clinicalNotes = [], 
    evoluciones = {}, medications = [], dietas = {}, cuidados_enfermeria = [], 
    laboratorios = [], imagenologia = [], proximas_citas = [], 
    formatos_disponibles = [], cargos_solicitudes = {} 
  } = data;

  const getVitalIcon = (label) => {
    if (label.includes('Cardíaca')) return <MdOutlineMonitorHeart className="text-hes-blue-main text-2xl" />;
    if (label.includes('Arterial')) return <MdOutlineWaterDrop className="text-blue-500 text-2xl" />;
    if (label.includes('O2')) return <FiActivity className="text-teal-500 text-2xl" />;
    if (label.includes('Temp')) return <FaTemperatureHalf className="text-orange-500 text-2xl" />;
    return <FiActivity className="text-slate-400 text-2xl" />;
  };

  const getVitalColor = (label) => {
    if (label.includes('Cardíaca')) return 'bg-blue-50 text-hes-blue-main';
    if (label.includes('Arterial')) return 'bg-blue-50 text-blue-600';
    if (label.includes('O2')) return 'bg-teal-50 text-teal-600';
    if (label.includes('Temp')) return 'bg-orange-50 text-orange-600';
    return 'bg-slate-50 text-slate-600';
  };

  // Abrir modal para nueva evolución
  const handleOpenNewEvol = (slotNum = 1, formatoCodigo = 'HE-DIRMED-SINPRO-PLT-87/01') => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden registrar nuevas evoluciones en un paciente dado de alta.");
      return;
    }
    let doctorName = currentDoctorName || data?.patient?.attending || '';
    let doctorCed = currentDoctorCedula || data?.patient?.cedula || '';

    const ptvs = data?.ptvs || {};
    const defaultTa = ptvs.ta || '';
    const defaultFc = ptvs.fc || '';
    const defaultFr = ptvs.fr || '';
    const defaultSat = ptvs.sat_o2 || '';
    const defaultPeso = ptvs.peso || '';
    const defaultTalla = ptvs.talla || '';
    const defaultTemp = ptvs.temp || '';

    const now = new Date();
    setNotaModal({
      open: true,
      isEdit: false,
      formato_codigo: formatoCodigo,
      mrnum_24_hoja_evol: null,
      evolution_num: slotNum,
      fecha: now.toISOString().split('T')[0],
      hora: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
      turno: 'Matutino',
      vitals_ta: defaultTa,
      vitals_fc: defaultFc,
      vitals_fr: defaultFr,
      vitals_sato2: defaultSat,
      vitals_peso: defaultPeso,
      vitals_talla: defaultTalla,
      vitals_temp: defaultTemp,
      subjetivo: '',
      objetivo: '',
      analisis: '',
      plan: '',
      medico: doctorName,
      cedula: doctorCed,
      has_mip: false,
      mip: ''
    });
  };

  // Abrir modal para editar evolución existente
  const handleOpenEditEvol = (evol, formatoCodigo = 'HE-DIRMED-SINPRO-PLT-87/01') => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar notas clínicas en un paciente dado de alta.");
      return;
    }
    if (!evol) return;
    const cleanMip = (evol.mip && String(evol.mip).trim().toUpperCase() !== 'NONE' && String(evol.mip).trim().toUpperCase() !== 'NULL') ? String(evol.mip).trim() : '';
    setNotaModal({
      open: true,
      isEdit: true,
      formato_codigo: formatoCodigo,
      mrnum_24_hoja_evol: evol.mrnum_24_hoja_evol || evol.slot || null,
      mrnum: evol.mrnum_24_hoja_evol || evol.slot || null,
      evolution_num: evol.num || evol.evolution_num || 1,
      fecha: evol.fecha || evol.date || new Date().toISOString().split('T')[0],
      hora: evol.hora || evol.time || '12:00',
      turno: evol.turno || 'Matutino',
      vitals_ta: evol.vitals_ta || '',
      vitals_fc: evol.vitals_fc || '',
      vitals_fr: evol.vitals_fr || '',
      vitals_sato2: evol.vitals_sato2 || '',
      vitals_peso: evol.vitals_peso || '',
      vitals_talla: evol.vitals_talla || '',
      vitals_temp: evol.vitals_temp || '',
      subjetivo: evol.subjetivo || evol.soap?.s || '',
      objetivo: evol.objetivo || evol.soap?.o || '',
      analisis: evol.analisis || evol.soap?.a || '',
      plan: evol.plan || evol.soap?.p || '',
      medico: evol.medico || evol.doctor || currentDoctorName || data?.patient?.attending || '',
      cedula: evol.cedula || currentDoctorCedula || data?.patient?.cedula || '',
      has_mip: !!cleanMip,
      mip: cleanMip
    });
  };

  // Guardar evolución en backend / SQL Server
  const handleSaveNota = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    try {
      setSavingNota(true);
      const isHosp = notaModal.formato_codigo === 'HE-DIRMED-CONSUL-PLT-24' || (selectedFormat && selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-24');
      const endpoint = isHosp ? `/ehr/paciente/${patientId}/nota-hospitalizacion` : `/ehr/paciente/${patientId}/nota-urgencias`;
      const res = await api.post(endpoint, notaModal);
      if (isConfirmedClinicalSync(res)) {
        setNotaModal(prev => ({ ...prev, open: false }));
        await fetchData();
        await fetchFirmas();
        const tipoLabel = isHosp ? 'de Hospitalización ' : '';
        alert(`¡Evolución ${notaModal.evolution_num} ${tipoLabel}guardada con éxito en el expediente!\n(Al modificar el documento, cualquier firma digital previa se revocó conforme a la NOM)`);
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || "Error al guardar la nota.");
      }
    } catch (err) {
      console.error("Error saving note:", err);
      alert("Error al conectar con el servidor para guardar la nota.");
    } finally {
      setSavingNota(false);
    }
  };

  const handleOpenNewConsent25 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal25({
      open: true,
      isEdit: false,
      isNew: true,
      mrnum: null,
      medico_tratante: currentDoctorName || data?.patient?.attending || '',
      cedula: currentDoctorCedula || data?.patient?.cedula || '',
      testigo1: defFirm.testigo1 || data?.consentimiento_25?.testigo1 || '',
      testigo2: defFirm.testigo2 || data?.consentimiento_25?.testigo2 || '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      paciente_o_representante: isAdult ? (p.name || '') : (defFirm.tutor || ''),
      saving: false
    });
  };

  const handleOpenEditConsent25 = (record) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = record || data?.consentimiento_25 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedRep = c.paciente_o_representante || c.pariente || '';
    const hasOtherRep = savedRep && savedRep !== p.name;
    setConsentModal25({
      open: true,
      isEdit: true,
      isNew: false,
      mrnum: c.mrnum || null,
      medico_tratante: c.medico_tratante || currentDoctorName || data?.patient?.attending || '',
      cedula: c.cedula || currentDoctorCedula || data?.patient?.cedula || '',
      testigo1: c.testigo1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || defFirm.testigo2 || '',
      paciente_capaz: isAdult,
      pariente: hasOtherRep ? savedRep : (isAdult ? '' : (defFirm.tutor || '')),
      paciente_o_representante: savedRep || (isAdult ? p.name : (defFirm.tutor || '')),
      saving: false
    });
  };

  const handleSaveConsentModal25 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal25(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = {
        is_new: Boolean(consentModal25.isNew),
        mrnum: consentModal25.mrnum,
        medico_tratante: currentDoctorName || consentModal25.medico_tratante || data?.patient?.attending || '',
        cedula: currentDoctorCedula || consentModal25.cedula || data?.patient?.cedula || '',
        testigo1: consentModal25.testigo1 || '',
        testigo2: consentModal25.testigo2 || '',
        paciente_o_representante: consentModal25.paciente_capaz ? (p.name || '') : (consentModal25.pariente || consentModal25.paciente_o_representante || '')
      };
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-25`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal25(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        if (res.data?.mrnum) {
          setSelectedMrnum25(res.data.mrnum);
        }
        alert('¡Consentimiento Formato 25 guardado con éxito en el expediente SQL Server!\n(Conforme a la NOM-024, el documento ha quedado registrado bajo tu autoría)');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el consentimiento.');
        setConsentModal25(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error('Error saving consent 25:', err);
      alert('Error al conectar con el servidor para guardar el consentimiento.');
      setConsentModal25(prev => ({ ...prev, saving: false }));
    }
  };


    const handleOpenNewConsent3201 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal3201({
      open: true,
      isEdit: false,
      isNew: true,
      tipo_interrogatorio: isAdult ? 'Directo' : 'Indirecto',
      testigo1: defFirm.testigo1 || '',
      testigo2: defFirm.testigo2 || '',
      paciente_capaz: isAdult,
      representante_legal: isAdult ? '' : (defFirm.tutor || ''),
      paciente_o_representante: isAdult ? (p.name || '') : (defFirm.tutor || ''),
      saving: false
    });
  };

  const handleOpenEditConsent3201 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = data?.consentimiento_32_01 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedRep = c.representante_legal || '';
    const hasOtherRep = savedRep && savedRep !== p.name;
    setConsentModal3201({
      open: true,
      isEdit: true,
      isNew: false,
      tipo_interrogatorio: c.tipo_interrogatorio || consentForm3201.tipo_interrogatorio || (isAdult ? 'Directo' : 'Indirecto'),
      testigo1: c.testigo1 || consentForm3201.testigo1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || consentForm3201.testigo2 || defFirm.testigo2 || '',
      paciente_capaz: isAdult,
      representante_legal: savedRep || (isAdult ? '' : (defFirm.tutor || '')),
      paciente_o_representante: c.paciente_o_representante || consentForm3201.paciente_o_representante || p.name || '',
      saving: false
    });
  };

  const handleSaveConsentModal3201 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal3201(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = {
        is_new: Boolean(consentModal3201.isNew),
        mrnum: consentModal3201.mrnum,
        tipo_interrogatorio: consentModal3201.paciente_capaz ? 'Directo' : 'Indirecto',
        testigo1: consentModal3201.testigo1,
        testigo2: consentModal3201.testigo2,
        paciente_o_representante: p.name || '',
        representante_legal: consentModal3201.paciente_capaz ? '' : (consentModal3201.representante_legal || ''),
        medico_tratante: currentDoctorName || data?.patient?.attending || '',
        cedula: currentDoctorCedula || data?.patient?.cedula || '',
        alergias: data?.patient?.allergies || 'NEGADAS',
        diagnostico: data?.patient?.diagnostico || ''
      };
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-32-01`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentForm3201(payload);
        setConsentModal3201(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert("¡Consentimiento 32/01 guardado con éxito en el expediente SQL Server!\n(Conforme a la NOM-024, el documento ha quedado registrado bajo tu autoría)");
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || "Error al guardar el consentimiento.");
        setConsentModal3201(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error("Error saving consent:", err);
      alert("Error al conectar con el servidor para guardar el consentimiento.");
      setConsentModal3201(prev => ({ ...prev, saving: false }));
    }
  };


    const handleOpenNewConsentEED = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModalEED({
      open: true, isEdit: false, isNew: true,
      tipo_interrogatorio: isAdult ? 'Directo' : 'Indirecto',
      paciente_capaz: isAdult,
      responsable: isAdult ? (p.name || '') : (defFirm.tutor || ''),
      testigo1: defFirm.testigo1 || '',
      testigo2: defFirm.testigo2 || '',
      comentarios: '',
      ta: '', fc_meta: '', fr: '', talla: '', peso: '',
      ta_basal: '', fc_basal: '', so2_basal: '', s_basal: '',
      ta_5mcg: '', fc_5mcg: '', so2_5mcg: '', s_5mcg: '',
      ta_10mcg: '', fc_10mcg: '', so2_10mcg: '', s_10mcg: '',
      ta_20mcg: '', fc_20mcg: '', so2_20mcg: '', s_20mcg: '',
      ta_30mcg: '', fc_30mcg: '', so2_30mcg: '', s_30mcg: '',
      ta_40mcg: '', fc_40mcg: '', so2_40mcg: '', s_40mcg: '',
      ta_antropina: '', fc_antropina: '', so2_antropina: '', s_antropina: '',
      ta_2min: '', fc_2min: '', so2_2min: '', sintomas_2min: '',
      ta_4min: '', fc_4min: '', so2_4min: '', sintomas_4min: '',
      saving: false
    });
  };

  const handleOpenEditConsentEED = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = data?.consentimiento_eed || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedResp = c.responsable || '';
    const hasOtherResp = savedResp && savedResp !== p.name;
    setConsentModalEED({
      open: true, isEdit: true, isNew: false, saving: false,
      tipo_interrogatorio: c.tipo_interrogatorio || (isAdult ? 'Directo' : 'Indirecto'),
      paciente_capaz: isAdult,
      responsable: savedResp || (isAdult ? p.name : (defFirm.tutor || '')),
      testigo1: c.testigo1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || defFirm.testigo2 || '',
      comentarios: c.comentarios || '',
      ta: c.ta || '', fc_meta: c.fc_meta || '', fr: c.fr || '', talla: c.talla || '', peso: c.peso || '',
      ta_basal: c.ta_basal || '', fc_basal: c.fc_basal || '', so2_basal: c.so2_basal || '', s_basal: c.s_basal || '',
      ta_5mcg: c.ta_5mcg || '', fc_5mcg: c.fc_5mcg || '', so2_5mcg: c.so2_5mcg || '', s_5mcg: c.s_5mcg || '',
      ta_10mcg: c.ta_10mcg || '', fc_10mcg: c.fc_10mcg || '', so2_10mcg: c.so2_10mcg || '', s_10mcg: c.s_10mcg || '',
      ta_20mcg: c.ta_20mcg || '', fc_20mcg: c.fc_20mcg || '', so2_20mcg: c.so2_20mcg || '', s_20mcg: c.s_20mcg || '',
      ta_30mcg: c.ta_30mcg || '', fc_30mcg: c.fc_30mcg || '', so2_30mcg: c.so2_30mcg || '', s_30mcg: c.s_30mcg || '',
      ta_40mcg: c.ta_40mcg || '', fc_40mcg: c.fc_40mcg || '', so2_40mcg: c.so2_40mcg || '', s_40mcg: c.s_40mcg || '',
      ta_antropina: c.ta_atropina || '', fc_antropina: c.fc_atropina || '', so2_antropina: c.so2_atropina || '', s_antropina: c.s_atropina || '',
      ta_2min: c.ta_2min || '', fc_2min: c.fc_2min || '', so2_2min: c.so2_2min || '', sintomas_2min: c.sintomas_2min || '',
      ta_4min: c.ta_4min || '', fc_4min: c.fc_4min || '', so2_4min: c.so2_4min || '', sintomas_4min: c.sintomas_4min || ''
    });
  };

  const handleSaveConsentModalEED = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModalEED(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = { 
        ...consentModalEED,
        is_new: Boolean(consentModalEED.isNew),
        medico: currentDoctorName || consentModalEED.medico || data?.patient?.attending || '',
        cedula: currentDoctorCedula || consentModalEED.cedula || data?.patient?.cedula || '',
        responsable: consentModalEED.paciente_capaz ? (p.name || '') : (consentModalEED.responsable || ''),
        tipo_interrogatorio: consentModalEED.paciente_capaz ? 'Directo' : 'Indirecto'
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.isNew;
      delete payload.saving;
      const token = localStorage.getItem('token');
      const res = await api.post('/ehr/paciente/'+patientId+'/consentimiento-eed', payload, { headers: { Authorization: `Bearer ${token}` } });
      if (isConfirmedClinicalSync(res)) {
        setConsentModalEED(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('Guardado con exito.');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar.');
        setConsentModalEED(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al guardar.');
      setConsentModalEED(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent3401 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal3401({
      open: true,
      isEdit: false,
      isNew: true,
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      tipo_interrogatorio: isAdult ? 'DIRECTO' : 'INDIRECTO',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      testigo1: defFirm.testigo1 || data?.consentimiento_34_01?.testigo1 || data?.consentimiento_25?.testigo1 || '',
      testigo2: defFirm.testigo2 || data?.consentimiento_34_01?.testigo2 || data?.consentimiento_25?.testigo2 || '',
      gruporh: p.grupo_rh || '',
      alergias: p.allergies || 'NEGADAS',
      ta: data?.ptvs?.ta || '',
      fc_meta: '',
      f_resp: data?.ptvs?.fr || '',
      temperatura: data?.ptvs?.temp || '',
      peso: p.weight || data?.ptvs?.peso || '',
      talla: p.height || data?.ptvs?.talla || '',
      irm: '',
      fbpr: '',
      fpr: '',
      conclusiones: '',
      conclusiones_2: '',
      conclusiones_3: '',
      ta_basal: '', fc_basal: '', obs_basal: '',
      ta_p_inicio: '', fc_p_inicio: '', obs_p_inicio: '',
      ta_p_2: '', fc_p_2: '', obs_p_2: '',
      ta_p_4: '', fc_p_4: '', obs_p_4: '',
      ta_p_6: '', fc_p_6: '', obs_p_6: '',
      ta_p_8: '', fc_p_8: '', obs_p_8: '',
      ta_p_10: '', fc_p_10: '', obs_p_10: '',
      ta_p_12: '', fc_p_12: '', obs_p_12: '',
      ta_p_14: '', fc_p_14: '', obs_p_14: '',
      ta_p_16: '', fc_p_16: '', obs_p_16: '',
      ta_p_18: '', fc_p_18: '', obs_p_18: '',
      ta_p_20: '', fc_p_20: '', obs_p_20: '',
      ta_a_inicio: '', fc_a_inicio: '', obs_a_inicio: '',
      ta_a_2: '', fc_a_2: '', obs_a_2: '',
      ta_a_4: '', fc_a_4: '', obs_a_4: '',
      ta_a_6: '', fc_a_6: '', obs_a_6: '',
      ta_a_8: '', fc_a_8: '', obs_a_8: '',
      ta_a_10: '', fc_a_10: '', obs_a_10: '',
      ta_a_12: '', fc_a_12: '', obs_a_12: '',
      ta_a_14: '', fc_a_14: '', obs_a_14: '',
      ta_final: '', fc_final: '', obs_final: '',
      saving: false
    });
  };

  const handleOpenEditConsent3401 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = data?.consentimiento_34_01 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    setConsentModal3401({
      open: true,
      isEdit: true,
      saving: false,
      medico_tratante: c.medico_tratante || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      tipo_interrogatorio: c.tipo_interrogatorio || (isAdult ? 'DIRECTO' : 'INDIRECTO'),
      paciente_capaz: isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      testigo1: c.testigo1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || defFirm.testigo2 || '',
      gruporh: c.gruporh || 'O POSITIVO',
      alergias: c.alergias || 'NEGADAS',
      ta: c.ta || '', fc_meta: c.fc_meta || '', f_resp: c.f_resp || '', temperatura: c.temperatura || '', peso: c.peso || '', talla: c.talla || '',
      irm: c.irm || '', fbpr: c.fbpr || '', fpr: c.fpr || '',
      conclusiones: c.conclusiones || '', conclusiones_2: c.conclusiones_2 || '', conclusiones_3: c.conclusiones_3 || '',
      ta_basal: c.ta_basal || '', fc_basal: c.fc_basal || '', obs_basal: c.obs_basal || '',
      ta_p_inicio: c.ta_p_inicio || '', fc_p_inicio: c.fc_p_inicio || '', obs_p_inicio: c.obs_p_inicio || '',
      ta_p_2: c.ta_p_2 || '', fc_p_2: c.fc_p_2 || '', obs_p_2: c.obs_p_2 || '',
      ta_p_4: c.ta_p_4 || '', fc_p_4: c.fc_p_4 || '', obs_p_4: c.obs_p_4 || '',
      ta_p_6: c.ta_p_6 || '', fc_p_6: c.fc_p_6 || '', obs_p_6: c.obs_p_6 || '',
      ta_p_8: c.ta_p_8 || '', fc_p_8: c.fc_p_8 || '', obs_p_8: c.obs_p_8 || '',
      ta_p_10: c.ta_p_10 || '', fc_p_10: c.fc_p_10 || '', obs_p_10: c.obs_p_10 || '',
      ta_p_12: c.ta_p_12 || '', fc_p_12: c.fc_p_12 || '', obs_p_12: c.obs_p_12 || '',
      ta_p_14: c.ta_p_14 || '', fc_p_14: c.fc_p_14 || '', obs_p_14: c.obs_p_14 || '',
      ta_p_16: c.ta_p_16 || '', fc_p_16: c.fc_p_16 || '', obs_p_16: c.obs_p_16 || '',
      ta_p_18: c.ta_p_18 || '', fc_p_18: c.fc_p_18 || '', obs_p_18: c.obs_p_18 || '',
      ta_p_20: c.ta_p_20 || '', fc_p_20: c.fc_p_20 || '', obs_p_20: c.obs_p_20 || '',
      ta_a_inicio: c.ta_a_inicio || '', fc_a_inicio: c.fc_a_inicio || '', obs_a_inicio: c.obs_a_inicio || '',
      ta_a_2: c.ta_a_2 || '', fc_a_2: c.fc_a_2 || '', obs_a_2: c.obs_a_2 || '',
      ta_a_4: c.ta_a_4 || '', fc_a_4: c.fc_a_4 || '', obs_a_4: c.obs_a_4 || '',
      ta_a_6: c.ta_a_6 || '', fc_a_6: c.fc_a_6 || '', obs_a_6: c.obs_a_6 || '',
      ta_a_8: c.ta_a_8 || '', fc_a_8: c.fc_a_8 || '', obs_a_8: c.obs_a_8 || '',
      ta_a_10: c.ta_a_10 || '', fc_a_10: c.fc_a_10 || '', obs_a_10: c.obs_a_10 || '',
      ta_a_12: c.ta_a_12 || '', fc_a_12: c.fc_a_12 || '', obs_a_12: c.obs_a_12 || '',
      ta_a_14: c.ta_a_14 || '', fc_a_14: c.fc_a_14 || '', obs_a_14: c.obs_a_14 || '',
      ta_final: c.ta_final || '', fc_final: c.fc_final || '', obs_final: c.obs_final || ''
    });
  };

  const handleSaveConsentModal3401 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal3401(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal3401,
        medico_tratante: currentDoctorName || consentModal3401.medico_tratante || data?.patient?.attending || '',
        cedula: currentDoctorCedula || consentModal3401.cedula || data?.patient?.cedula || '',
        pariente: consentModal3401.paciente_capaz ? '' : (consentModal3401.pariente || ''),
        tipo_interrogatorio: consentModal3401.paciente_capaz ? 'DIRECTO' : 'INDIRECTO'
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-34-01`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal3401(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Consentimiento Formato 34/01 (Mesa Inclinada) guardado con éxito en el expediente SQL Server!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal3401(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal3401(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent12 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal12({
      open: true,
      isEdit: false,
      isNew: true,
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      diagnostico: p.diagnostico || '',
      servicio: 'URGENCIAS',
      beneficios: '',
      alternativas: '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      testigo1: defFirm.testigo1 || data?.consentimiento_12?.testigo1 || data?.consentimiento_25?.testigo1 || '',
      testigo2: defFirm.testigo2 || data?.consentimiento_12?.testigo2 || data?.consentimiento_25?.testigo2 || '',
      saving: false
    });
  };

  const handleOpenEditConsent12 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_12 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    setConsentModal12({
      open: true,
      isEdit: true,
      isNew: false,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      diagnostico: c.diagnostico || p.diagnostico || '',
      servicio: c.servicio || 'URGENCIAS',
      beneficios: c.beneficios || '',
      alternativas: c.alternativas || '',
      paciente_capaz: isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      testigo1: c.testigo1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleSaveConsentModal12 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal12(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal12,
        medico_tratante: currentDoctorName || consentModal12.medico_tratante || data?.patient?.attending || '',
        cedula: currentDoctorCedula || consentModal12.cedula || data?.patient?.cedula || '',
        pariente: consentModal12.paciente_capaz ? '' : (consentModal12.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-12`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal12(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Consentimiento Formato 12 (Gineco Hosp/Urg) guardado con éxito en el expediente SQL Server!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal12(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal12(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent04 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal04({
      open: true,
      isEdit: false,
      isNew: true,
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      testigo1: defFirm.testigo1 || data?.consentimiento_04?.testigo1 || data?.consentimiento_12?.testigo1 || '',
      saving: false
    });
  };

  const handleOpenEditConsent04 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_04 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    setConsentModal04({
      open: true,
      isEdit: true,
      isNew: false,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      paciente_capaz: isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      testigo1: c.testigo1 || defFirm.testigo1 || '',
      saving: false
    });
  };

  const handleSaveConsentModal04 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal04(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal04,
        medico_tratante: currentDoctorName || consentModal04.medico_tratante || data?.patient?.attending || '',
        cedula: currentDoctorCedula || consentModal04.cedula || data?.patient?.cedula || '',
        pariente: consentModal04.paciente_capaz ? '' : (consentModal04.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-04`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal04(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Consentimiento Formato 04 (Catéter Venoso Central) guardado con éxito en SQL Server!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal04(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal04(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent15 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal15({
      open: true,
      isEdit: false,
      isNew: true,
      tipo: 'autorizo',
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      diagnostico: p.diagnostico || '',
      procedimiento_consiste: '',
      beneficios: '',
      alternativas: '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      testigo1: defFirm.testigo1 || data?.consentimiento_15?.testigo1 || data?.consentimiento_12?.testigo1 || '',
      testigo2: defFirm.testigo2 || data?.consentimiento_15?.testigo2 || '',
      motivo_no_acepto: '',
      domicilio_testigo: defFirm.domicilio1 || 'Conocido en expediente clínico',
      identificacion_testigo: defFirm.identificacion1 || 'INE / Identificación Oficial',
      parentesco_testigo: defFirm.parentesco1 || 'Familiar / Testigo Presencial',
      saving: false
    });
  };

  const handleOpenEditConsent15 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_15 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    const isNoAutorizo = Boolean(c.no_autorizo || c.tipo === 'no_autorizo');
    setConsentModal15({
      open: true,
      isEdit: true,
      isNew: false,
      tipo: isNoAutorizo ? 'no_autorizo' : 'autorizo',
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      diagnostico: c.diagnostico || p.diagnostico || '',
      procedimiento_consiste: c.procedimiento_consiste || '',
      beneficios: c.beneficios || '',
      alternativas: c.alternativas || '',
      paciente_capaz: isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      testigo1: c.testigo1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || defFirm.testigo2 || '',
      motivo_no_acepto: c.motivo_no_acepto || c.motivo_rechazo || '',
      domicilio_testigo: c.domicilio_testigo || defFirm.domicilio1 || 'Conocido en expediente clínico',
      identificacion_testigo: c.identificacion_testigo || defFirm.identificacion1 || 'INE / Identificación Oficial',
      parentesco_testigo: c.parentesco_testigo || defFirm.parentesco1 || 'Familiar / Testigo Presencial',
      saving: false
    });
  };

  const handleSaveConsentModal15 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal15(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal15,
        no_autorizo: consentModal15.tipo === 'no_autorizo',
        medico_tratante: currentDoctorName || consentModal15.medico_tratante || data?.patient?.attending || '',
        cedula: currentDoctorCedula || consentModal15.cedula || data?.patient?.cedula || '',
        pariente: consentModal15.paciente_capaz ? '' : (consentModal15.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-15`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal15(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Consentimiento Formato 15 (Cesárea / Disentimiento) guardado con éxito en SQL Server!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal15(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal15(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent02 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal02({
      open: true,
      isEdit: false,
      isNew: true,
      tipo: 'autorizo',
      mrnum: null,
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      diagnostico: p.diagnostico || '',
      proced_para_confirmar_diagnost: '',
      beneficio_de_dicho_procedimiento: '',
      tratamientos_medicos: '',
      tratamientos_quirurgicos: '',
      tratamientos_endoscopicos: '',
      tratamientos_de_rehabilitacion: '',
      alternativas: '',
      anestesia: 'SI',
      tipo_de_anestesia: '',
      principales_riesgos: '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      testigo1: defFirm.testigo1 || data?.consentimiento_02?.testigo1 || data?.consentimiento_15?.testigo1 || '',
      testigo2: defFirm.testigo2 || data?.consentimiento_02?.testigo2 || '',
      motivo_de_no_autorizacion: '',
      domicilio_testigo1: defFirm.domicilio1 || 'Conocido en expediente clínico',
      identificacion_testigo1: defFirm.identificacion1 || 'INE / Identificación Oficial',
      parentesco_testigo1: defFirm.parentesco1 || 'Familiar / Testigo Presencial',
      saving: false
    });
  };

  const handleOpenEditConsent02 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_02 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    const isNoAutorizo = Boolean(c.no_autorizo || c.tipo === 'no_autorizo' || c.motivo_de_no_autorizacion);
    setConsentModal02({
      open: true,
      isEdit: true,
      isNew: false,
      tipo: isNoAutorizo ? 'no_autorizo' : 'autorizo',
      mrnum: c.mrnum || null,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      diagnostico: c.diagnostico || p.diagnostico || '',
      proced_para_confirmar_diagnost: c.proced_para_confirmar_diagnost || c.proced_confirmar || '',
      beneficio_de_dicho_procedimiento: c.beneficio_de_dicho_procedimiento || c.beneficios || '',
      tratamientos_medicos: c.tratamientos_medicos || '',
      tratamientos_quirurgicos: c.tratamientos_quirurgicos || '',
      tratamientos_endoscopicos: c.tratamientos_endoscopicos || '',
      tratamientos_de_rehabilitacion: c.tratamientos_de_rehabilitacion || '',
      alternativas: c.alternativas || '',
      anestesia: c.anestesia || 'SI',
      tipo_de_anestesia: c.tipo_de_anestesia || c.tipo_anestesia || '',
      principales_riesgos: c.principales_riesgos || '',
      paciente_capaz: isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      testigo1: c.testigo1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || defFirm.testigo2 || '',
      motivo_de_no_autorizacion: c.motivo_de_no_autorizacion || c.motivo_no_acepto || '',
      domicilio_testigo1: c.domicilio_testigo1 || c.domicilio_testigo || defFirm.domicilio1 || 'Conocido en expediente clínico',
      identificacion_testigo1: c.identificacion_testigo1 || c.identificacion_testigo || defFirm.identificacion1 || 'INE / Identificación Oficial',
      parentesco_testigo1: c.parentesco_testigo1 || c.parentesco_testigo || defFirm.parentesco1 || 'Familiar / Testigo Presencial',
      saving: false
    });
  };

  const handleSaveConsentModal02 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal02(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal02,
        no_autorizo: consentModal02.tipo === 'no_autorizo',
        medico_tratante: currentDoctorName || consentModal02.medico_tratante || data?.patient?.attending || '',
        cedula: currentDoctorCedula || consentModal02.cedula || data?.patient?.cedula || '',
        pariente: consentModal02.paciente_capaz ? '' : (consentModal02.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-02`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal02(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Consentimiento Formato 02 (Tratamiento Quirúrgico / Disentimiento) guardado con éxito en SQL Server!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal02(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal02(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent43 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal43({
      open: true,
      isEdit: false,
      isNew: true,
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      diagnostico: p.diagnostico || '',
      servicio: p.area || 'URGENCIAS / TERAPIA INTENSIVA',
      beneficios: '',
      riesgos: '',
      alternativas: '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      testigo1: defFirm.testigo1 || data?.consentimiento_43?.testigo1 || '',
      testigo2: defFirm.testigo2 || data?.consentimiento_43?.testigo2 || '',
      domicilio_testigo1: defFirm.domicilio1 || 'Conocido en expediente clínico',
      identificacion_testigo1: defFirm.identificacion1 || 'INE / Identificación Oficial',
      parentesco_testigo1: defFirm.parentesco1 || 'Familiar / Testigo Presencial',
      domicilio_testigo2: defFirm.domicilio2 || 'Conocido en expediente clínico',
      identificacion_testigo2: defFirm.identificacion2 || 'INE / Identificación Oficial',
      parentesco_testigo2: defFirm.parentesco2 || 'Familiar / Testigo Presencial',
      saving: false
    });
  };

  const handleOpenEditConsent43 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_43 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || (c.declarante && c.declarante !== p.name ? c.declarante : '');
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    setConsentModal43({
      open: true,
      isEdit: true,
      isNew: false,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      diagnostico: c.diagnostico || p.diagnostico || '',
      servicio: c.servicio || p.area || 'URGENCIAS / TERAPIA INTENSIVA',
      beneficios: c.beneficios || '',
      riesgos: c.riesgos || c.principales_riesgos || '',
      alternativas: c.alternativas || '',
      paciente_capaz: isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      testigo1: c.testigo1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || defFirm.testigo2 || '',
      domicilio_testigo1: c.domicilio_testigo1 || defFirm.domicilio1 || 'Conocido en expediente clínico',
      identificacion_testigo1: c.identificacion_testigo1 || defFirm.identificacion1 || 'INE / Identificación Oficial',
      parentesco_testigo1: c.parentesco_testigo1 || defFirm.parentesco1 || 'Familiar / Testigo Presencial',
      domicilio_testigo2: c.domicilio_testigo2 || defFirm.domicilio2 || 'Conocido en expediente clínico',
      identificacion_testigo2: c.identificacion_testigo2 || defFirm.identificacion2 || 'INE / Identificación Oficial',
      parentesco_testigo2: c.parentesco_testigo2 || defFirm.parentesco2 || 'Familiar / Testigo Presencial',
      saving: false
    });
  };

  const handleSaveConsentModal43 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal43(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = { 
        ...consentModal43,
        medico_tratante: currentDoctorName || consentModal43.medico_tratante || p.attending || '',
        cedula: currentDoctorCedula || consentModal43.cedula || p.cedula || '',
        pariente: consentModal43.paciente_capaz ? '' : (consentModal43.pariente || ''),
        declarante: consentModal43.paciente_capaz ? (p.name || '') : (consentModal43.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-43`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal43(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Formato 43 (Orden de Intubación Endotraqueal) guardado con éxito en SQL Server!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal43(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal43(prev => ({ ...prev, saving: false }));
    }
  };

  // ==========================================
  // FORMATO 06: PROCEDIMIENTO ANESTÉSICO
  // ==========================================
  const handleOpenNewConsent06 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal06({
      open: true,
      isEdit: false,
      isNew: true,
      mrnum: null,
      medico_anestesiologo: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      cedula_especialidad: '',
      diagnostico: p.diagnostico || '',
      servicio: p.area || 'QUIRÓFANO',
      tipo_cirugia: 'PROGRAMADA',
      magnitud_cirugia: 'MAYOR',
      asa: 'CLASE II',
      tipo_anestesia: '',
      beneficios_anestesia: '',
      alternativas_anestesia: '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      parentesco: isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal'),
      testigo1: defFirm.testigo1 || '',
      testigo2: defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleOpenEditConsent06 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_06 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || (c.declarante && c.declarante !== p.name ? c.declarante : '');
    setConsentModal06({
      open: true,
      isEdit: true,
      isNew: false,
      mrnum: c.mrnum || null,
      medico_anestesiologo: c.medico_anestesiologo || c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      cedula_especialidad: c.cedula_especialidad || '',
      diagnostico: c.diagnostico || p.diagnostico || '',
      servicio: c.servicio || p.area || 'QUIRÓFANO',
      tipo_cirugia: c.tipo_cirugia || 'PROGRAMADA',
      magnitud_cirugia: c.magnitud_cirugia || 'MAYOR',
      asa: c.asa || 'CLASE II',
      tipo_anestesia: c.tipo_anestesia || '',
      beneficios_anestesia: c.beneficios_anestesia || '',
      alternativas_anestesia: c.alternativas_anestesia || '',
      paciente_capaz: c.paciente_capaz !== undefined ? Boolean(c.paciente_capaz) : isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      parentesco: c.parentesco || (isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal')),
      testigo1: c.testigo1 || c.testigo_1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || c.testigo_2 || defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleSaveConsentModal06 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal06(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = { 
        ...consentModal06,
        medico_anestesiologo: currentDoctorName || consentModal06.medico_anestesiologo || p.attending || '',
        medico_tratante: currentDoctorName || consentModal06.medico_anestesiologo || p.attending || '',
        cedula: currentDoctorCedula || consentModal06.cedula || p.cedula || '',
        pariente: consentModal06.paciente_capaz ? '' : (consentModal06.pariente || ''),
        declarante: consentModal06.paciente_capaz ? (p.name || '') : (consentModal06.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-06`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal06(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Formato 06 (Procedimiento Anestésico) guardado con éxito!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal06(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal06(prev => ({ ...prev, saving: false }));
    }
  };

  // ==========================================
  // FORMATO 11: CONSENTIMIENTO DE NO REANIMACIÓN
  // ==========================================
  const handleOpenNewConsent11 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal11({
      open: true,
      isEdit: false,
      isNew: true,
      mrnum: null,
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      diagnostico: p.diagnostico || '',
      servicio: p.area || 'URGENCIAS / MEDICINA INTERNA',
      beneficios_y_riesgos_de_nr: '',
      riesgos_de_no_aplicar: '',
      alternativa_nr: '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      parentesco: isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal'),
      testigo1: defFirm.testigo1 || '',
      testigo2: defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleOpenEditConsent11 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_11 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || (c.declarante && c.declarante !== p.name ? c.declarante : '');
    setConsentModal11({
      open: true,
      isEdit: true,
      isNew: false,
      mrnum: c.mrnum || null,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      diagnostico: c.diagnostico || p.diagnostico || '',
      servicio: c.servicio || p.area || 'URGENCIAS / MEDICINA INTERNA',
      beneficios_y_riesgos_de_nr: c.beneficios_y_riesgos_de_nr || '',
      riesgos_de_no_aplicar: c.riesgos_de_no_aplicar || '',
      alternativa_nr: c.alternativa_nr || '',
      paciente_capaz: c.paciente_capaz !== undefined ? Boolean(c.paciente_capaz) : isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      parentesco: c.parentesco || (isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal')),
      testigo1: c.testigo1 || c.testigo_1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || c.testigo_2 || defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleSaveConsentModal11 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal11(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = { 
        ...consentModal11,
        medico_tratante: currentDoctorName || consentModal11.medico_tratante || p.attending || '',
        cedula: currentDoctorCedula || consentModal11.cedula || p.cedula || '',
        pariente: consentModal11.paciente_capaz ? '' : (consentModal11.pariente || ''),
        declarante: consentModal11.paciente_capaz ? (p.name || '') : (consentModal11.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-11`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal11(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Formato 11 (No Reanimación) guardado con éxito!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal11(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal11(prev => ({ ...prev, saving: false }));
    }
  };

  // ==========================================
  // FORMATO 19: CONSENTIMIENTO PARA HISTERECTOMÍA
  // ==========================================
  const handleOpenNewConsent19 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal19({
      open: true,
      isEdit: false,
      isNew: true,
      tipo: 'autorizo',
      mrnum: null,
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      diagnostico: p.diagnostico || '',
      explicacion_de_proceso: '',
      beneficios_de_procedimiento: '',
      intervencion_complementaria: '',
      alternativas_terapeuticas: '',
      motivo_de_no_autorizacion: '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      parentesco: isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal'),
      testigo1: defFirm.testigo1 || '',
      testigo2: defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleOpenEditConsent19 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_19 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || (c.declarante && c.declarante !== p.name ? c.declarante : '');
    const isNoAutorizo = Boolean(c.no_autorizo || c.tipo === 'no_autorizo' || c.motivo_de_no_autorizacion);
    setConsentModal19({
      open: true,
      isEdit: true,
      isNew: false,
      tipo: isNoAutorizo ? 'no_autorizo' : 'autorizo',
      mrnum: c.mrnum || null,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      diagnostico: c.diagnostico || p.diagnostico || '',
      explicacion_de_proceso: c.explicacion_de_proceso || c.explicacion || '',
      beneficios_de_procedimiento: c.beneficios_de_procedimiento || c.beneficios || '',
      intervencion_complementaria: c.intervencion_complementaria || '',
      alternativas_terapeuticas: c.alternativas_terapeuticas || c.alternativas || '',
      motivo_de_no_autorizacion: c.motivo_de_no_autorizacion || c.motivo_no_acepto || '',
      paciente_capaz: c.paciente_capaz !== undefined ? Boolean(c.paciente_capaz) : isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      parentesco: c.parentesco || (isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal')),
      testigo1: c.testigo1 || c.testigo_1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || c.testigo_2 || defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleSaveConsentModal19 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal19(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = { 
        ...consentModal19,
        no_autorizo: consentModal19.tipo === 'no_autorizo',
        medico_tratante: currentDoctorName || consentModal19.medico_tratante || p.attending || '',
        cedula: currentDoctorCedula || consentModal19.cedula || p.cedula || '',
        pariente: consentModal19.paciente_capaz ? '' : (consentModal19.pariente || ''),
        declarante: consentModal19.paciente_capaz ? (p.name || '') : (consentModal19.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-19`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal19(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Formato 19 (Histerectomía) guardado con éxito!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal19(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal19(prev => ({ ...prev, saving: false }));
    }
  };

  // ==========================================
  // FORMATO 07: PROCEDIMIENTOS QUIRÚRGICOS
  // ==========================================
  const handleOpenNewConsent07 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal07({
      open: true,
      isEdit: false,
      isNew: true,
      mrnum: null,
      medico_tratante: currentDoctorName || p.attending || '',
      cedula: currentDoctorCedula || p.cedula || '',
      procedimiento_quirurgico: p.diagnostico || '',
      descripcion_procedimiento: '',
      riesgos_inherentes: '',
      beneficios: '',
      alternativas: '',
      paciente_capaz: isAdult,
      representante_legal: isAdult ? '' : (defFirm.tutor || ''),
      parentesco: isAdult ? 'El Paciente' : (defFirm.parentesco_tutor || 'Representante Legal'),
      testigo1: defFirm.testigo1 || '',
      testigo2: defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleOpenEditConsent07 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_07 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.representante_legal || c.pariente || (c.declarante && c.declarante !== p.name ? c.declarante : '');
    setConsentModal07({
      open: true,
      isEdit: true,
      isNew: false,
      mrnum: c.mrnum || null,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || p.attending || '',
      cedula: c.cedula || currentDoctorCedula || p.cedula || '',
      procedimiento_quirurgico: c.procedimiento_quirurgico || p.diagnostico || '',
      descripcion_procedimiento: c.descripcion_procedimiento || '',
      riesgos_inherentes: c.riesgos_inherentes || c.riesgos || '',
      beneficios: c.beneficios || '',
      alternativas: c.alternativas || '',
      paciente_capaz: c.paciente_capaz !== undefined ? Boolean(c.paciente_capaz) : isAdult,
      representante_legal: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      parentesco: c.parentesco || (isAdult ? 'El Paciente' : (defFirm.parentesco_tutor || 'Representante Legal')),
      testigo1: c.testigo1 || c.testigo_1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || c.testigo_2 || defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleSaveConsentModal07 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal07(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = { 
        ...consentModal07,
        medico_tratante: currentDoctorName || consentModal07.medico_tratante || p.attending || '',
        cedula: currentDoctorCedula || consentModal07.cedula || p.cedula || '',
        representante_legal: consentModal07.paciente_capaz ? '' : (consentModal07.representante_legal || ''),
        declarante: consentModal07.paciente_capaz ? (p.name || '') : (consentModal07.representante_legal || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-07`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal07(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        if (res.data?.mrnum) {
          setSelectedMrnum07(res.data.mrnum);
        }
        alert('¡Formato 07 (Procedimientos Quirúrgicos) guardado con éxito!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal07(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal07(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent08 = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear consentimientos en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setConsentModal08({
      open: true,
      isEdit: false,
      isNew: true,
      mrnum: null,
      medico_tratante: currentDoctorName || data?.patient?.attending || '',
      cedula: currentDoctorCedula || data?.patient?.cedula || '',
      diagnostico: p.diagnostico || '',
      procedimientos: '',
      riesgos_inherentes_a_procedimien: '',
      prob_proced_y_alts: '',
      beneficios: '',
      paciente_capaz: isAdult,
      pariente: isAdult ? '' : (defFirm.tutor || ''),
      yo_autorizo: isAdult ? (p.name || '') : (defFirm.tutor || ''),
      parentesco: isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal'),
      testigo1: defFirm.testigo1 || data?.consentimiento_08?.testigo1 || data?.consentimiento_02?.testigo1 || '',
      testigo2: defFirm.testigo2 || data?.consentimiento_08?.testigo2 || data?.consentimiento_02?.testigo2 || '',
      saving: false
    });
  };

  const handleOpenEditConsent08 = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar consentimientos en un paciente dado de alta.");
      return;
    }
    const c = item || data?.consentimiento_08 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedPariente = c.pariente || c.yo_autorizo || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    setConsentModal08({
      open: true,
      isEdit: true,
      isNew: false,
      mrnum: c.mrnum || null,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || data?.patient?.attending || '',
      cedula: c.cedula || currentDoctorCedula || data?.patient?.cedula || '',
      diagnostico: c.diagnostico || p.diagnostico || '',
      procedimientos: c.procedimientos || '',
      riesgos_inherentes_a_procedimien: c.riesgos_inherentes_a_procedimien || c.riesgos || '',
      prob_proced_y_alts: c.prob_proced_y_alts || c.alternativas || '',
      beneficios: c.beneficios || '',
      paciente_capaz: isAdult,
      pariente: savedPariente || (isAdult ? '' : (defFirm.tutor || '')),
      yo_autorizo: savedPariente || (isAdult ? p.name : (defFirm.tutor || '')),
      parentesco: c.parentesco || c.parentesco_paciente || (isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal')),
      testigo1: c.testigo1 || c.testigo_1 || defFirm.testigo1 || '',
      testigo2: c.testigo2 || c.testigo_2 || defFirm.testigo2 || '',
      saving: false
    });
  };

  const handleSaveConsentModal08 = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setConsentModal08(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal08,
        medico_tratante: currentDoctorName || consentModal08.medico_tratante || data?.patient?.attending || '',
        cedula: currentDoctorCedula || consentModal08.cedula || data?.patient?.cedula || '',
        pariente: consentModal08.paciente_capaz ? '' : (consentModal08.pariente || ''),
        yo_autorizo: consentModal08.paciente_capaz ? (data?.patient?.name || patient?.name || '') : (consentModal08.pariente || ''),
        parentesco: consentModal08.paciente_capaz ? 'Paciente' : (consentModal08.parentesco || 'Representante Legal')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-08`, payload);
      if (isConfirmedClinicalSync(res)) {
        setConsentModal08(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        if (res.data?.mrnum) {
          setSelectedMrnum08(res.data.mrnum);
        }
        alert('¡Consentimiento Formato 08 (Admisión Continua y Diagnóstico) guardado con éxito en SQL Server!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setConsentModal08(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal08(prev => ({ ...prev, saving: false }));
    }
  };

  // =========================================================================
  // HANDLERS PARA FORMATO 15: EGRESO VOLUNTARIO (HE-DIRMED-SINPRO-PLT-15)
  // =========================================================================
  const handleOpenNew15EV = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear registros en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setModal15EV({
      open: true,
      isEdit: false,
      isNew: true,
      mrnum: null,
      medico_tratante: currentDoctorName || data?.patient?.attending || '',
      cedula: currentDoctorCedula || data?.patient?.cedula || '',
      diagnostico_ingreso: p.diagnostico || '',
      diagnostico_egreso: p.diagnostico || '',
      motivo_egreso: '',
      medidas_recomendadas: '',
      factores_riesgo: '',
      paciente_capaz: isAdult,
      declarante: isAdult ? (p.name || '') : (defFirm.tutor || ''),
      parentesco: isAdult ? 'El Paciente' : (defFirm.parentesco_tutor || 'Familiar / Representante Legal'),
      identificacion: defFirm.identificacion_tutor || '',
      domicilio_declarante: defFirm.domicilio_tutor || '',
      testigo1: defFirm.testigo1 || '',
      parentesco1: defFirm.parentesco1 || '',
      identificacion1: defFirm.identificacion1 || '',
      domicilio1: defFirm.domicilio1 || '',
      testigo2: defFirm.testigo2 || '',
      parentesco2: defFirm.parentesco2 || '',
      identificacion2: defFirm.identificacion2 || '',
      domicilio2: defFirm.domicilio2 || '',
      saving: false
    });
  };

  const handleOpenEdit15EV = (item) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar registros en un paciente dado de alta.");
      return;
    }
    const c = item || data?.egreso_voluntario_15 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedDeclarante = c.declarante || c.n_replegal || c.representante_legal || '';
    const isCapaz = c.paciente_capaz !== undefined ? Boolean(c.paciente_capaz) : isAdult;

    setModal15EV({
      open: true,
      isEdit: true,
      isNew: false,
      mrnum: c.mrnum || null,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || data?.patient?.attending || '',
      cedula: c.cedula || currentDoctorCedula || data?.patient?.cedula || '',
      diagnostico_ingreso: c.diagnostico_ingreso || c.diagnostico || p.diagnostico || '',
      diagnostico_egreso: c.diagnostico_egreso || c.diagnostico || p.diagnostico || '',
      motivo_egreso: c.motivo_egreso || '',
      medidas_recomendadas: c.medidas_recomendadas || '',
      factores_riesgo: c.factores_riesgo || '',
      paciente_capaz: isCapaz,
      declarante: savedDeclarante || (isCapaz ? (p.name || '') : (defFirm.tutor || '')),
      parentesco: c.parentesco || (isCapaz ? 'El Paciente' : (defFirm.parentesco_tutor || 'Familiar / Representante Legal')),
      identificacion: c.identificacion || defFirm.identificacion_tutor || '',
      domicilio_declarante: c.domicilio_declarante || defFirm.domicilio_tutor || '',
      testigo1: c.testigo1 || c.testigo_1 || defFirm.testigo1 || '',
      parentesco1: c.parentesco1 || c.parentesco_testigo1 || defFirm.parentesco1 || '',
      identificacion1: c.identificacion1 || c.identificacion_testigo1 || defFirm.identificacion1 || '',
      domicilio1: c.domicilio1 || c.domicilio_testigo1 || defFirm.domicilio1 || '',
      testigo2: c.testigo2 || c.testigo_2 || defFirm.testigo2 || '',
      parentesco2: c.parentesco2 || c.parentesco_testigo2 || defFirm.parentesco2 || '',
      identificacion2: c.identificacion2 || c.identificacion_testigo2 || defFirm.identificacion2 || '',
      domicilio2: c.domicilio2 || c.domicilio_testigo2 || defFirm.domicilio2 || '',
      saving: false
    });
  };

  const handleSaveModal15EV = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setModal15EV(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = {
        ...modal15EV,
        medico_tratante: currentDoctorName || modal15EV.medico_tratante || data?.patient?.attending || '',
        cedula: currentDoctorCedula || modal15EV.cedula || data?.patient?.cedula || '',
        declarante: modal15EV.paciente_capaz ? (p.name || 'El Paciente') : (modal15EV.declarante || ''),
        n_replegal: modal15EV.paciente_capaz ? (p.name || 'El Paciente') : (modal15EV.declarante || ''),
        parentesco: modal15EV.paciente_capaz ? 'El Paciente' : (modal15EV.parentesco || 'Representante Legal'),
        testigo_1: modal15EV.testigo1 || '',
        testigo_2: modal15EV.testigo2 || ''
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/egreso-voluntario-15`, payload);
      if (isConfirmedClinicalSync(res)) {
        setModal15EV(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        if (res.data?.mrnum) {
          setSelectedMrnum15EV(res.data.mrnum);
        }
        alert('¡Formato 15 (Egreso Voluntario) guardado exitosamente en SQL Server y expediente clínico!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato de egreso voluntario.');
        setModal15EV(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error('Error guardando egreso voluntario 15:', err);
      alert(err.response?.data?.detail || 'Error al conectar con el servidor.');
      setModal15EV(prev => ({ ...prev, saving: false }));
    }
  };

  // =========================================================================
  // HANDLERS UNIVERSALES (PARA CUALQUIERA DE LOS 100+ FORMATOS EN VERTICAL)
  // =========================================================================
  const handleOpenNewUniversal = () => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden crear registros en un paciente dado de alta.");
      return;
    }
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    setUniversalEditModal({
      open: true,
      isEdit: false,
      isNew: true,
      mrnum: null,
      codigo: selectedFormat?.codigo || '',
      nombre: selectedFormat?.nombre || 'Formato Institucional',
      medico_tratante: currentDoctorName || 'Médico Adscrito',
      diagnostico: p.diagnostico || `VALORACIÓN CLÍNICA - ${selectedFormat?.nombre || 'FORMATO'}`,
      observaciones: '',
      paciente_capaz: isAdult,
      tutor: isAdult ? '' : (defFirm.tutor || ''),
      parentesco: isAdult ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal'),
      identificacion_tutor: defFirm.identificacion_tutor || 'INE / Credencial Oficial',
      domicilio_tutor: defFirm.domicilio_tutor || 'Conocido en expediente clínico',
      testigo1: defFirm.testigo1 || '',
      parentesco1: defFirm.parentesco1 || 'Familiar / Testigo Presencial',
      identificacion1: defFirm.identificacion1 || 'INE / Credencial Oficial',
      domicilio1: defFirm.domicilio1 || 'Conocido en expediente clínico',
      testigo2: defFirm.testigo2 || '',
      parentesco2: defFirm.parentesco2 || 'Testigo Presencial / Institucional',
      identificacion2: defFirm.identificacion2 || 'INE / Credencial Oficial',
      domicilio2: defFirm.domicilio2 || 'Conocido en expediente clínico',
      saving: false
    });
  };

  const handleOpenEditUniversal = (activeDoc) => {
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden editar registros en un paciente dado de alta.");
      return;
    }
    const doc = activeDoc || {};
    const summary = getDocumentSignaturesSummary(selectedFormat?.codigo, doc.mrnum);
    if (summary.hasMedico || doc.firmado || doc.mr_st === 'FM') {
      alert("Documento Inmutable: Este registro ya fue firmado biométricamente conforme a la NOM-004-SSA3-2012 y NOM-024-SSA3-2012. Los documentos clínicos firmados no pueden ser editados.");
      return;
    }
    const docDoc = doc.medico_tratante || doc.n_medico || doc.created_by;
    if (!canModifyOrSignDocument(docDoc)) {
      alert(`Candado de Seguridad NOM-024: Este documento fue elaborado por "${docDoc || 'otro médico'}". Solo el médico autor puede editarlo.`);
      return;
    }

    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defFirm = getDefaultFirmantesForConsent(firmantesList);
    const savedTutor = doc.tutor || doc.pariente || doc.representante_legal || '';
    const isCapaz = doc.paciente_capaz !== undefined ? Boolean(doc.paciente_capaz) : isAdult;

    setUniversalEditModal({
      open: true,
      isEdit: true,
      isNew: false,
      mrnum: doc.mrnum || null,
      codigo: selectedFormat?.codigo || '',
      nombre: selectedFormat?.nombre || 'Formato Institucional',
      medico_tratante: doc.medico_tratante || doc.n_medico || currentDoctorName || 'Médico Adscrito',
      diagnostico: doc.diagnostico || p.diagnostico || `VALORACIÓN CLÍNICA - ${selectedFormat?.nombre || 'FORMATO'}`,
      observaciones: doc.observaciones || doc.contenido || doc.resumen || '',
      paciente_capaz: isCapaz,
      tutor: savedTutor || (isCapaz ? '' : (defFirm.tutor || '')),
      parentesco: doc.parentesco || (isCapaz ? 'Paciente' : (defFirm.parentesco_tutor || 'Representante Legal')),
      identificacion_tutor: doc.identificacion_tutor || defFirm.identificacion_tutor || 'INE / Credencial Oficial',
      domicilio_tutor: doc.domicilio_tutor || defFirm.domicilio_tutor || 'Conocido en expediente clínico',
      testigo1: doc.testigo1 || doc.testigo_1 || defFirm.testigo1 || '',
      parentesco1: doc.parentesco1 || doc.parentesco_testigo1 || defFirm.parentesco1 || 'Familiar / Testigo Presencial',
      identificacion1: doc.identificacion1 || doc.identificacion_testigo1 || defFirm.identificacion1 || 'INE / Credencial Oficial',
      domicilio1: doc.domicilio1 || doc.domicilio_testigo1 || defFirm.domicilio1 || 'Conocido en expediente clínico',
      testigo2: doc.testigo2 || doc.testigo_2 || defFirm.testigo2 || '',
      parentesco2: doc.parentesco2 || doc.parentesco_testigo2 || defFirm.parentesco2 || 'Testigo Presencial / Institucional',
      identificacion2: doc.identificacion2 || doc.identificacion_testigo2 || defFirm.identificacion2 || 'INE / Credencial Oficial',
      domicilio2: doc.domicilio2 || doc.domicilio_testigo2 || defFirm.domicilio2 || 'Conocido en expediente clínico',
      saving: false
    });
  };

  const handleSaveUniversalModal = async (e) => {
    e.preventDefault();
    if (isPatientDischarged) {
      alert("Expediente en Modo Solo Lectura: De conformidad con la NOM-004-SSA3-2012 y NOM-024-SSA3-2012, no se pueden guardar cambios en un paciente de alta.");
      return;
    }
    setUniversalEditModal(prev => ({ ...prev, saving: true }));
    try {
      const payload = {
        ...universalEditModal,
        medico_tratante: currentDoctorName || universalEditModal.medico_tratante || data?.patient?.attending || '',
        pariente: universalEditModal.paciente_capaz ? '' : (universalEditModal.tutor || ''),
        representante_legal: universalEditModal.paciente_capaz ? '' : (universalEditModal.tutor || ''),
        testigo_1: universalEditModal.testigo1 || '',
        testigo_2: universalEditModal.testigo2 || ''
      };
      delete payload.open;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/formato-guardar-registro`, payload);
      if (isConfirmedClinicalSync(res)) {
        setUniversalEditModal(prev => ({ ...prev, open: false, saving: false }));
        if (selectedFormat && selectedFormat.codigo) {
          await fetchGenericHistory(selectedFormat.codigo);
        }
        await fetchData();
        await fetchFirmas();
        if (res.data?.mrnum) {
          setSelectedGenericMrnum(res.data.mrnum);
        }
        alert('¡Registro de formato guardado correctamente en SQL Server y expediente clínico!');
      } else {
        alert(pendingClinicalSyncMessage(res) || res.data?.error || 'Error al guardar el formato.');
        setUniversalEditModal(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error('Error guardando formato universal:', err);
      alert(err.response?.data?.detail || 'Error al conectar con el servidor.');
      setUniversalEditModal(prev => ({ ...prev, saving: false }));
    }
  };

  // Filtrado de formatos (únicamente los formatos activos / desarrollados)
  const allFormatos = (formatos_disponibles || [])
    .flatMap(cat => (cat?.formatos || []).map(f => ({ ...f, area: cat?.area || 'General' })))
    .filter(f => f && f.activo !== false);

  const availableAreas = ['Todos', ...Array.from(new Set(allFormatos.map(f => f.area).filter(Boolean)))];

  const filteredFormatos = (selectedFormatArea === 'Todos' 
    ? allFormatos 
    : allFormatos.filter(f => f.area === selectedFormatArea)
  ).filter(f => f && ((f.nombre || '').toLowerCase().includes((searchFormatoQuery || '').toLowerCase()) || (f.codigo || '').toLowerCase().includes((searchFormatoQuery || '').toLowerCase())));

  const tabsList = [
    { id: 'Timeline', label: 'Historial', icon: <FiClock /> },
    { id: 'Formatos Clínicos', label: `Formatos Clínicos (${allFormatos.length})`, icon: <FiFileText /> },
    { id: 'Medicamentos', label: 'Medicamentos', icon: <MdOutlineMedicalServices /> },
    { id: 'Dietas y Cuidados', label: 'Dietas y Cuidados', icon: <MdOutlineRestaurant /> },
    { id: 'Contactos y Responsables', label: `Contactos / Responsables (${firmantesList.length})`, icon: <FiUsers /> },
    { id: 'Laboratorios', label: 'Laboratorios', icon: <MdOutlineBiotech /> },
    { id: 'Imagenología', label: 'Imagenología', icon: <FiImage /> },
    { id: 'Agenda y Citas', label: 'Agenda y Citas', icon: <FiCalendar /> }
  ];

  const pName = patient?.name || 'Paciente Sin Nombre';
  const pInitial = (pName.trim().charAt(0) || 'P').toUpperCase();

  // HES Premium: color e icono por área clínica (solo visual, reversible)
  const getAreaStyle = (area = '') => {
    const a = (area || '').toLowerCase();
    if (a.includes('urgencia')) return { accent: 'linear-gradient(90deg,#dc2626,#f97316)', solid: '#dc2626', icon: '🚨' };
    if (a.includes('hospital')) return { accent: 'linear-gradient(90deg,#004687,#0088c9)', solid: '#005fa9', icon: '🏥' };
    if (a.includes('cirug') || a.includes('quir')) return { accent: 'linear-gradient(90deg,#7c3aed,#06b6d4)', solid: '#7c3aed', icon: '🔪' };
    if (a.includes('expediente') || a.includes('integral')) return { accent: 'linear-gradient(90deg,#065f46,#00b48a)', solid: '#047857', icon: '📋' };
    if (a.includes('auxiliar') || a.includes('diagn')) return { accent: 'linear-gradient(90deg,#0e7490,#22d3ee)', solid: '#0e7490', icon: '🧬' };
    return { accent: 'linear-gradient(90deg,#334155,#64748b)', solid: '#475569', icon: '🩺' };
  };

  return (
    <div className="he-premium-scope flex-1 min-w-0 max-w-full min-h-screen p-4 md:p-8 flex flex-col gap-6 overflow-x-hidden">
      
      {/* TOP BAR / BREADCRUMB */}
      <div className="he-top-patient flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-4 md:p-5 pl-5 md:pl-6">
        <div className="flex items-center gap-3">
          <div className="he-avatar w-12 h-12 rounded-2xl text-white flex items-center justify-center font-black text-xl shadow-sm">
            {pInitial}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-black uppercase tracking-[0.14em] text-teal-700 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-full">🩺 Expediente clínico</span>
              <h1 className="text-xl font-black text-slate-900 tracking-tight">{pName}</h1>
              {isPatientDischarged ? (
                <span className="text-xs bg-slate-100 text-slate-700 font-bold px-2.5 py-0.5 rounded-lg border border-slate-300 flex items-center gap-1 shadow-2xs">
                  <FiCheckCircle className="text-emerald-600 text-xs" /> ALTA / HISTÓRICO
                </span>
              ) : (
                <span className="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded border border-emerald-200">
                  {patient?.cama || 'Cama Virtual'}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Expediente: <strong className="text-slate-700">{patient?.mrn || 'PT-' + patientId}</strong> • Ingreso: {patient?.fecha_ingreso || '—'} {patient?.hora_ingreso || ''}
              {isPatientDischarged && patient?.fecha_egreso && patient?.fecha_egreso !== '___/___/___' && (
                <> • <strong className="text-slate-700">Egreso:</strong> {patient.fecha_egreso} {patient.hora_egreso && patient.hora_egreso !== '__:__' ? patient.hora_egreso : ''}</>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto flex-wrap">
          {!isPatientDischarged ? (
            <button
              onClick={() => handleOpenNewEvol(evoluciones.evolucion2 ? 3 : (evoluciones.evolucion1 ? 2 : 1))}
              className="he-btn-primary flex items-center justify-center gap-2 text-white px-4 py-2.5 rounded-xl text-sm font-bold shadow-sm transition-all cursor-pointer"
            >
              <FiEdit3 /> Nueva Evolución
            </button>
          ) : (
            <div className="flex items-center gap-1.5 bg-slate-100 text-slate-700 border border-slate-300 px-3.5 py-2 rounded-xl text-xs font-bold shadow-2xs">
              <FiCheckCircle className="text-emerald-600 text-sm" /> Paciente Egresado (Vertical)
            </div>
          )}
          <a 
            href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-expediente-completo`} 
            target="_blank" 
            rel="noreferrer"
            className="he-btn-expediente flex items-center justify-center gap-2 text-white px-4 py-2.5 rounded-xl text-sm font-bold shadow-sm hover:shadow-md transition-all cursor-pointer"
            title="Genera e imprime el Expediente Clínico Completo institucional (Carátula foliada, notas de evolución urgencias/hosp, consentimientos, recetas y paraclínicos)"
          >
            <FiLayers className="text-base" /> Expediente Completo (PDF)
          </a>
          <a 
            href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
            target="_blank" 
            rel="noreferrer"
            className="hidden lg:flex items-center justify-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 px-3 py-2 rounded-xl text-xs font-semibold shadow-2xs transition-all"
            title="Imprimir formato individual de Nota de Urgencias (87/01)"
          >
            <FiFileText className="text-slate-500" /> Nota 87/01
          </a>
        </div>
      </div>

      {/* BANNER AVISO MODO SOLO LECTURA (NOM-004-SSA3-2012 / NOM-024-SSA3-2012) */}
      {isPatientDischarged && (
        <div className="bg-amber-50/90 border border-amber-300 rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-amber-900 animate-in fade-in duration-200">
          <div className="flex items-start sm:items-center gap-3">
            <div className="p-2.5 bg-amber-100 rounded-xl text-amber-700 shrink-0 mt-0.5 sm:mt-0 shadow-2xs">
              <FiAlertTriangle className="text-xl" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold text-sm text-slate-800">Expediente en Modo Solo Lectura</span>
                <span className="bg-amber-200/80 text-amber-900 text-[10px] font-extrabold uppercase px-2 py-0.5 rounded">
                  Episodio Clínico Cerrado / Paciente de Alta
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                De conformidad con la <strong>NOM-004-SSA3-2012</strong> y <strong>NOM-024-SSA3-2012</strong>, no se pueden agregar ni modificar notas, consentimientos, medicamentos o signos vitales en un episodio concluido. Las altas y reingresos se sincronizan en tiempo real directamente desde el sistema hospitalario <strong>Vertical (HIS)</strong>.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* PATIENT DEMOGRAPHICS & VITALS CARD */}
      <div className="he-vitals-card bg-white p-5 md:p-6 shadow-sm">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-12 gap-3 pb-4 border-b border-slate-100 text-xs">
          <div className="he-demo-box lg:col-span-2">
            <span className="he-demo-label">Edad / Sexo</span>
            <span className="he-demo-value">{patient.age} · {patient.gender}</span>
          </div>
          <div className="he-demo-box lg:col-span-2">
            <span className="he-demo-label">Fecha nacimiento</span>
            <span className="he-demo-value">{patient.dob}</span>
          </div>
          <div className="he-demo-box lg:col-span-2">
            <span className="he-demo-label">Ubicación / Estado</span>
            {isPatientDischarged ? (
              <span className="he-demo-value flex items-center gap-1.5 text-slate-600">
                <FiCheckCircle className="text-emerald-600" /> Dado de alta
              </span>
            ) : (
              <span className="he-demo-value text-[#0f2a4e] truncate block" title={patient.cama}>{patient.cama}</span>
            )}
          </div>
          <div className="col-span-2 md:col-span-2 lg:col-span-3">
            <div className="flex items-center justify-between mb-1">
              <span className="he-demo-label" style={{ marginBottom: 0 }}>Alergias</span>
              {!isPatientDischarged && (
                <button
                  type="button"
                  onClick={handleOpenAllergyModal}
                  className="text-[11px] font-bold text-[#0f2a4e] hover:underline flex items-center gap-1 cursor-pointer"
                  title="Gestionar alergias"
                >
                  <FiEdit3 className="text-[11px]" /> Gestionar
                </button>
              )}
            </div>
            <div
              onClick={!isPatientDischarged ? handleOpenAllergyModal : undefined}
              className={`px-2.5 py-2 rounded-[10px] text-xs font-bold block truncate ${patient.allergies && !/sin alergia/i.test(patient.allergies) ? 'he-allergy-alert' : 'he-allergy-ok'} ${!isPatientDischarged ? 'cursor-pointer' : ''}`}
              title={`${patient.allergies || 'Sin alergias registradas'}${!isPatientDischarged ? ' — clic para gestionar' : ''}`}
            >
              {(patient.allergies && !/sin alergia/i.test(patient.allergies) ? '⚠ ' : '') + (patient.allergies || 'Sin alergias registradas')}
            </div>
          </div>
          <div className="he-demo-box col-span-2 md:col-span-2 lg:col-span-3">
            <span className="he-demo-label">Diagnóstico de ingreso</span>
            <span className="he-demo-value block leading-snug" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }} title={patient.diagnostico}>{patient.diagnostico}</span>
          </div>
        </div>

        {/* VITALS SECTION HEADER */}
        <div className="flex flex-wrap items-center justify-between gap-2 mt-4">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-[13px] font-bold text-slate-900">Signos vitales</span>
            {data?.ptvs?.procedure_date && (
              <span className="text-[11.5px] text-slate-400">
                Última toma: <strong className="text-slate-600 font-semibold">{data.ptvs.procedure_date}</strong>
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleOpenVitalsHistory}
              className="he-btn-ghost flex items-center gap-1.5 px-3 py-2 text-xs font-bold transition-all cursor-pointer"
              title="Ver historial cronológico de todas las tomas"
            >
              <FiClock /> Historial
            </button>
            {!isPatientDischarged && (
              <button
                type="button"
                onClick={handleOpenVitalsModal}
                className="he-btn-navy flex items-center gap-1.5 px-3.5 py-2 text-xs transition-all cursor-pointer"
                title="Capturar o modificar signos vitales"
              >
                <FiEdit3 /> Nueva toma
              </button>
            )}
          </div>
        </div>

        {/* VITALS ROW */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mt-3">
          {vitals.map((v, i) => {
            const raw = String(v.value ?? '').replace(',', '.');
            const num = parseFloat(raw);
            let alert = null;
            const lab = v.label || '';
            if (/arteri|tensi|TA\b/i.test(lab)) {
              const m = raw.match(/(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)/);
              if (m) {
                const s = parseFloat(m[1]); const d = parseFloat(m[2]);
                if (s >= 140 || d >= 90) alert = 'Alta';
                else if (s < 90 || d < 60) alert = 'Baja';
              }
            } else if (/card[ií]aca|FC\b|pulso/i.test(lab)) {
              if (!isNaN(num) && (num >= 100 || num < 60)) alert = num >= 100 ? 'Alta' : 'Baja';
            } else if (/respirat|FR\b/i.test(lab)) {
              if (!isNaN(num) && (num >= 22 || num < 12)) alert = num >= 22 ? 'Alta' : 'Baja';
            } else if (/saturaci|O2|spo2/i.test(lab)) {
              if (!isNaN(num) && num < 92) alert = 'Baja';
            } else if (/temperatura/i.test(lab)) {
              if (!isNaN(num) && (num >= 37.5 || num < 36)) alert = num >= 37.5 ? 'Fiebre' : 'Baja';
            }
            return (
            <div
              key={i}
              onClick={!isPatientDischarged ? handleOpenVitalsModal : handleOpenVitalsHistory}
              className={`he-vital-tile flex items-center gap-2.5 p-3 cursor-pointer group ${alert ? 'alert' : ''}`}
              title={`${v.label}: ${v.value} ${v.unit || ''}${alert ? ` — ${alert}, revisar` : ''}${!isPatientDischarged ? ' (clic para nueva toma)' : ''}`}
            >
              <div className={`p-2 rounded-lg shrink-0 ${getVitalColor(v.label)}`}>
                {getVitalIcon(v.label)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <div className="he-reg-label tracking-wide truncate flex-1" title={v.label}>{v.label}</div>
                  {alert && <span className="he-vital-flag">{alert}</span>}
                </div>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className={`text-[19px] font-extrabold tabular-nums ${alert ? 'he-vital-val-alert' : 'text-slate-900'}`}>{v.value}</span>
                  <span className="text-[10.5px] text-slate-400 font-medium">{v.unit}</span>
                </div>
              </div>
            </div>
            );
          })}
        </div>
      </div>

      {/* MAIN CONTENT AREA: TABS & SIDEBAR */}
      <div className="flex flex-col xl:flex-row gap-6">
        
        {/* TABS CONTAINER */}
        <div className="flex-1 min-w-0">
          
          {/* TABS NAVIGATION */}
          <div className="he-tabs-bar flex w-full min-w-0 max-w-full gap-1.5 overflow-x-auto mb-5">
            {tabsList.map(tab => (
              <button 
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  if (tab.id !== 'Formatos Clínicos') {
                    setSelectedFormat(null);
                  }
                }}
                className={`he-tab ${activeTab === tab.id ? 'he-tab-active' : ''} flex items-center gap-2 px-4 py-2.5 text-sm whitespace-nowrap transition-all`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* TAB 1: TIMELINE (HISTORIAL CRONOLÓGICO) */}
          {activeTab === 'Timeline' && (
            <div className="he-tl-section">
              <div className="he-tl-head">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="he-tl-icon"><FiClock /></div>
                  <div className="min-w-0">
                    <h2 className="text-[16px] font-bold text-slate-900 tracking-tight">Línea de tiempo del paciente</h2>
                    <p className="text-xs text-slate-500">Historial cronológico de eventos clínicos, notas y atenciones.</p>
                  </div>
                </div>
                <span className="text-xs font-bold text-slate-600 bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-full whitespace-nowrap">
                  {timelineEvents.length} eventos
                </span>
              </div>

              <div className="p-4 md:p-5">
              {timelineEvents.length === 0 ? (
                <div className="text-center py-10">
                  <div className="text-3xl mb-2">📋</div>
                  <div className="font-bold text-slate-700 text-sm">Sin eventos registrados</div>
                  <div className="text-xs text-slate-400 mt-0.5">Aún no hay actividad clínica en este expediente.</div>
                </div>
              ) : (
                <div className="he-tl-rail space-y-4">
                  {timelineEvents.map((evt, idx) => {
                    const matchingFirma = firmas.find(f =>
                      (evt.format_code && f.codigo_formato === evt.format_code) ||
                      (evt.type?.includes('Evolución') && f.evolution_slot === (evt.type.includes('1') ? 1 : evt.type.includes('2') ? 2 : 3))
                    );
                    const isSigned = Boolean(evt.signed || matchingFirma);
                    const txt = `${evt.badge || ''} ${evt.category || ''} ${evt.type || ''}`;
                    let st = { icon: <FiFileText />, border: '#94a3b8', accent: '#94a3b8', bg: '#f8fafc' };
                    if (/evoluci|87\/01|PLT-24/i.test(txt)) st = { icon: <FiActivity />, border: '#0f2a4e', accent: '#0f2a4e', bg: '#eef3f9' };
                    else if (/consentimiento|autorizaci/i.test(txt)) st = { icon: <FiShield />, border: '#5b5bd6', accent: '#5b5bd6', bg: '#f1f1fb' };
                    else if (/laboratorio/i.test(txt)) st = { icon: <MdOutlineBiotech />, border: '#0e7490', accent: '#0e7490', bg: '#ecf7f9' };
                    else if (/imagen|radiolog|ultrasonido|tomograf/i.test(txt)) st = { icon: <FiImage />, border: '#334155', accent: '#334155', bg: '#f1f5f9' };
                    else if (/medicamento|f[aá]rmaco|receta/i.test(txt)) st = { icon: <MdOutlineMedicalServices />, border: '#166b4d', accent: '#166b4d', bg: '#ecf5f0' };
                    else if (/dieta|nutrici|ayuno/i.test(txt)) st = { icon: <MdOutlineRestaurant />, border: '#92400e', accent: '#92400e', bg: '#faf3ec' };
                    else if (/signos|monitoreo|vitales/i.test(txt)) st = { icon: <FiActivity />, border: '#0e7490', accent: '#0e7490', bg: '#ecf7f9' };
                    else if (/traslado/i.test(txt)) st = { icon: <FiMapPin />, border: '#9a3412', accent: '#9a3412', bg: '#faf1ec' };
                    else if (/ingreso|alta|egreso/i.test(txt)) st = { icon: <FiCheckCircle />, border: '#0f172a', accent: '#0f172a', bg: '#eef1f6' };

                    const openFormato = () => {
                      const fmt = allFormatos.find(f => f.codigo === evt.format_code) || {
                        codigo: evt.format_code,
                        nombre: evt.type,
                        subtitulo: 'Formato Institucional HES',
                        area: evt.category || 'Servicios Clínicos'
                      };
                      setSelectedFormat(fmt);
                      setActiveTab('Formatos Clínicos');
                    };

                    return (
                      <div key={evt.id || idx} className="he-tl-row">
                        <div className="he-tl-node" style={{ borderColor: st.border, color: st.border, background: st.bg }} title={evt.category || evt.type}>
                          {st.icon}
                        </div>
                        <div className="he-tl-card" style={{ borderLeftColor: st.accent }}>
                          <div className="flex justify-between gap-3 flex-wrap">
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="he-tl-title">{evt.type}</span>
                                {evt.badge && <span className="he-tl-badge">{evt.badge}</span>}
                                {isSigned && (
                                  <span className="he-tl-signed"><MdVerifiedUser /> Firmado · NOM-024</span>
                                )}
                              </div>
                              <p className="he-tl-desc">{evt.desc}</p>
                            </div>
                            <div className="he-tl-date">
                              <b>{evt.date}</b>
                              <span>{evt.time}</span>
                            </div>
                          </div>

                          <div className="he-tl-actions">
                            {evt.format_code && (
                              <button onClick={openFormato} className="he-tl-btn he-tl-btn-primary">
                                Abrir formato <FiChevronRight />
                              </button>
                            )}
                            {evt.pdf_url && (
                              <a href={`${api.defaults.baseURL}${evt.pdf_url}`} target="_blank" rel="noreferrer" className="he-tl-btn he-tl-btn-ghost">
                                <FiDownload /> PDF
                              </a>
                            )}
                            {evt.action_type === 'tab_medications' && (
                              <button onClick={() => setActiveTab('Medicamentos')} className="he-tl-btn he-tl-btn-ghost">
                                Ver medicamentos <FiChevronRight />
                              </button>
                            )}
                            {evt.action_type === 'tab_diets' && (
                              <button onClick={() => setActiveTab('Dietas y Cuidados')} className="he-tl-btn he-tl-btn-ghost">
                                Ver dieta y cuidados <FiChevronRight />
                              </button>
                            )}
                            {evt.action_type === 'tab_labs' && (
                              <button onClick={() => setActiveTab('Laboratorios')} className="he-tl-btn he-tl-btn-ghost">
                                Ver laboratorio <FiChevronRight />
                              </button>
                            )}
                            {evt.action_type === 'tab_imaging' && (
                              <button onClick={() => setActiveTab('Imagenología')} className="he-tl-btn he-tl-btn-ghost">
                                Ver imagen <FiChevronRight />
                              </button>
                            )}
                            {evt.action_type === 'vitals_modal' && (
                              <button onClick={!isPatientDischarged ? handleOpenVitalsModal : handleOpenVitalsHistory} className="he-tl-btn he-tl-btn-ghost">
                                {!isPatientDischarged ? <FiActivity /> : <FiClock />} Signos vitales
                              </button>
                            )}
                            {matchingFirma && (
                              <button
                                type="button"
                                onClick={() => handleOpenAuditModal(matchingFirma)}
                                className="he-tl-seal"
                                title="Verificar sello y auditoría NOM-024"
                              >
                                Sello: {matchingFirma.sello_digital ? `${matchingFirma.sello_digital.slice(0, 12)}…` : 'Verificado'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              </div>
            </div>
          )}

          {/* TAB 2: FORMATOS CLÍNICOS (+100 FORMATOS CATEGORIZADOS & GESTOR DE NOTAS) */}
          {activeTab === 'Formatos Clínicos' && (
            <div>
              {/* CASO A: CUANDO SE ABRIÓ UN FORMATO ESPECÍFICO (EJ. NOTA DE EVOLUCIÓN DE URGENCIAS) */}
              {selectedFormat ? (
                <div className="space-y-6">
                  
                  {/* BARRA DE NAVEGACIÓN COMPACTA (SIN DUPLICACIÓN DE TÍTULOS NI BOTONES) */}
                  <div className="he-det-nav flex items-center justify-between p-3 px-4">
                    <button
                      type="button"
                      onClick={() => setSelectedFormat(null)}
                      className="he-btn-ghost inline-flex items-center gap-2 text-xs font-bold px-4 py-2 transition-all cursor-pointer"
                    >
                      <FiArrowLeft className="text-sm" /> Volver al Catálogo de Formatos
                    </button>
                    <span className="text-xs text-slate-400 font-medium hidden sm:inline-flex items-center gap-1.5">
                      🩺 Expediente Clínico Electrónico • Folio <strong className="text-slate-700 font-mono">PT-{patientId}</strong>
                    </span>
                  </div>

                  {/* VISTA DE TODAS LAS EVOLUCIONES CONSECUTIVAS DE URGENCIAS (SIN LÍMITE) */}
                  {selectedFormat.codigo === 'HE-DIRMED-SINPRO-PLT-87/01' ? (() => {
                    const evolList = data?.evoluciones_list && data.evoluciones_list.length > 0
                      ? [...data.evoluciones_list]
                      : Object.values(evoluciones || {}).filter(e => e && (e.subjetivo || e.fecha));
                    
                    // Orden de antigüedad asegurado por num / fecha
                    evolList.sort((a, b) => (a.num || 0) - (b.num || 0));
                    const nextSlot = evolList.length + 1;

                    return (
                      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-slate-100">
                          <div>
                            <h3 className="font-bold text-slate-800 text-base">
                              Evoluciones Consecutivas del Paciente ({evolList.length} {evolList.length === 1 ? 'nota registrada' : 'notas registradas'})
                            </h3>
                            <p className="text-xs text-slate-500">
                              Historial cronológico continuo sin límite de evoluciones. Cada turno conserva su orden de antigüedad y firma biométrica.
                            </p>
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <a
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-colors"
                              title="Imprimir formato general con todas las evoluciones consecutivas"
                            >
                              <FiFileText className="text-sm" /> Imprimir Expediente Completo
                            </a>
                            {!isPatientDischarged && (
                              <button
                                onClick={() => handleOpenNewEvol(nextSlot)}
                                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-1.5 rounded-xl text-xs font-bold shadow-xs transition-colors"
                              >
                                <FiPlus className="text-sm" /> + Nueva Evolución ({nextSlot})
                              </button>
                            )}
                          </div>
                        </div>

                        {evolList.length === 0 ? (
                          <div className="p-8 text-center bg-slate-50/60 rounded-2xl border border-dashed border-slate-300 space-y-3">
                            <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto text-xl font-bold">
                              <FiPlus />
                            </div>
                            <h4 className="font-bold text-slate-700 text-sm">No hay evoluciones capturadas para este paciente</h4>
                            <p className="text-xs text-slate-500 max-w-md mx-auto">
                              Comienza el seguimiento médico redactando la primera evolución y observaciones del turno.
                            </p>
                            {!isPatientDischarged ? (
                              <button
                                onClick={() => handleOpenNewEvol(1)}
                                className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                              >
                                <FiPlus /> Capturar Primera Evolución (Evolución 1)
                              </button>
                            ) : (
                              <div className="text-xs text-slate-500 font-medium italic">
                                Expediente en solo lectura. No hay evoluciones registradas para este episodio.
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 gap-4">
                            {evolList.map((evolData) => {
                              const slot = evolData.num;
                              const firmaSlot = firmas.find(f => f.evolution_slot === slot);

                              return (
                                <div key={slot} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/60 transition-all">
                                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 mb-3 border-b border-slate-200">
                                    <div className="flex items-center gap-3">
                                      <span className="w-8 h-8 rounded-lg font-bold flex items-center justify-center text-sm shadow-xs bg-hes-blue-main text-white">
                                        {slot}
                                      </span>
                                      <div>
                                        <div className="flex items-center gap-2">
                                          <div className="font-bold text-slate-800 text-base">
                                            Evolución y Observaciones {slot} {slot > 1 && <span className="text-xs text-hes-blue-main font-semibold">(Continuación)</span>}
                                          </div>
                                          {firmaSlot && (
                                            <span className="text-[11px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-200" title="Firmado conforme a la NOM-004-SSA3-2012 / NOM-024-SSA3-2012">
                                              <MdVerifiedUser className="text-sm text-emerald-600" /> Firmado Biométricamente (NOM)
                                            </span>
                                          )}
                                        </div>
                                        <div className="text-xs text-slate-500">
                                          Fecha: <span className="font-medium text-slate-700">{evolData.fecha} {evolData.hora}</span> • Turno: <span className="font-medium text-slate-700">{evolData.turno}</span>
                                        </div>
                                      </div>
                                    </div>

                                    <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                      {!isPatientDischarged && (
                                        canModifyOrSignDocument(evolData.medico) ? (
                                          <>
                                            {/* BOTÓN FIRMAR CON HUELLA BIOMÉTRICA */}
                                            <button
                                              onClick={() => handleOpenBiometricSign(slot, `Evolución ${slot}`, evolData.subjetivo || '')}
                                              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                firmaSlot 
                                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100' 
                                                  : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                              }`}
                                              title="Firmar este registro con su huella"
                                            >
                                              <MdFingerprint className="text-base" /> {firmaSlot ? 'Firmar de nuevo' : 'Firmar con huella'}
                                            </button>

                                            {!firmaSlot && (
                                              <button
                                                onClick={() => handleOpenEditEvol(evolData)}
                                                className="flex items-center gap-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                              >
                                                <FiEdit3 /> Editar
                                              </button>
                                            )}
                                          </>
                                        ) : (
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-500 border border-slate-200 px-2.5 py-1.5 rounded-lg text-xs font-bold" title="Nota elaborada por otro médico">
                                            <FiLock /> Solo Lectura ({evolData.medico || 'Otro Médico'})
                                          </span>
                                        )
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias?evolucion=${slot}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white hover:bg-blue-50 text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                      >
                                        <FiFileText /> Imprimir Nota {slot}
                                      </a>
                                    </div>
                                  </div>

                                  {/* CONTENIDO SOAP */}
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                    {evolData.subjetivo && (
                                      <div className="p-3 bg-white rounded-xl border border-slate-100">
                                        <span className="font-bold text-hes-blue-main block uppercase mb-0.5">(S) Subjetivo</span>
                                        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.subjetivo}</p>
                                      </div>
                                    )}
                                    {evolData.objetivo && (
                                      <div className="p-3 bg-white rounded-xl border border-slate-100">
                                        <span className="font-bold text-hes-blue-main block uppercase mb-0.5">(O) Objetivo</span>
                                        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.objetivo}</p>
                                      </div>
                                    )}
                                    {evolData.analisis && (
                                      <div className="p-3 bg-white rounded-xl border border-slate-100">
                                        <span className="font-bold text-hes-blue-main block uppercase mb-0.5">(A) Análisis</span>
                                        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.analisis}</p>
                                      </div>
                                    )}
                                    {evolData.plan && (
                                      <div className="p-3 bg-white rounded-xl border border-slate-100">
                                        <span className="font-bold text-hes-blue-main block uppercase mb-0.5">(P) Plan Terapéutico</span>
                                        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.plan}</p>
                                      </div>
                                    )}
                                    
                                    {/* FOOTER DE FIRMA Y MÉDICO */}
                                    <div className="col-span-1 md:col-span-2 pt-2.5 border-t border-slate-200/60 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-[11px]">
                                      <div>
                                        Médico Responsable: <strong className="text-slate-800">{evolData.medico}</strong> (Céd. {evolData.cedula})
                                      </div>
                                      {firmaSlot && (
                                        <button
                                          type="button"
                                          onClick={() => handleOpenAuditModal(firmaSlot)}
                                          className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md border border-emerald-200 flex items-center gap-1.5 transition-colors cursor-pointer text-left"
                                          title="Ver los detalles de la firma"
                                        >
                                          <MdVerifiedUser className="text-emerald-600 shrink-0 text-xs" />
                                          <span>Firma verificada • {firmaSlot.fecha_hora_firma}</span>
                                          <span className="text-[9px] font-sans font-bold text-hes-blue-main bg-blue-50 px-1.5 py-0.5 rounded ml-1">Ver detalles</span>
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}

                            {/* CARD BOTÓN PARA SIGUIENTE EVOLUCIÓN */}
                            {!isPatientDischarged && (
                              <div className="p-4 rounded-2xl border border-dashed border-slate-300 bg-white/70 flex items-center justify-between">
                                <div className="text-xs text-slate-500">
                                  ¿Deseas redactar una nueva nota para el siguiente turno o médico?
                                </div>
                                <button
                                  onClick={() => handleOpenNewEvol(nextSlot, 'HE-DIRMED-SINPRO-PLT-87/01')}
                                  className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                >
                                  <FiPlus /> + Capturar Evolución {nextSlot}
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })() : selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-24' ? (() => {
                    const evolList = data?.evoluciones_hospitalizacion_list && data.evoluciones_hospitalizacion_list.length > 0
                      ? [...data.evoluciones_hospitalizacion_list]
                      : [];
                    
                    evolList.sort((a, b) => (a.num || 0) - (b.num || 0));
                    const nextSlot = evolList.length + 1;

                    return (
                      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-slate-100">
                          <div>
                            <h3 className="font-bold text-slate-800 text-base">
                              Evoluciones Consecutivas de Hospitalización ({evolList.length} {evolList.length === 1 ? 'nota registrada' : 'notas registradas'})
                            </h3>
                            <p className="text-xs text-slate-500">
                              Seguimiento médico integral continuo en piso / hospitalización (HE-DIRMED-CONSUL-PLT-24). Cada turno conserva su orden de antigüedad y firma biométrica.
                            </p>
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <a
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-hospitalizacion`}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-colors"
                              title="Imprimir formato general con todas las evoluciones de hospitalización consecutivas"
                            >
                              <FiFileText className="text-sm" /> Imprimir Expediente Completo
                            </a>
                            {!isPatientDischarged && (
                              <button
                                onClick={() => handleOpenNewEvol(nextSlot, 'HE-DIRMED-CONSUL-PLT-24')}
                                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-1.5 rounded-xl text-xs font-bold shadow-xs transition-colors"
                              >
                                <FiPlus className="text-sm" /> + Nueva Evolución ({nextSlot})
                              </button>
                            )}
                          </div>
                        </div>

                        {evolList.length === 0 ? (
                          <div className="p-8 text-center bg-slate-50/60 rounded-2xl border border-dashed border-slate-300 space-y-3">
                            <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto text-xl font-bold">
                              <FiPlus />
                            </div>
                            <h4 className="font-bold text-slate-700 text-sm">No hay evoluciones de hospitalización capturadas para este paciente</h4>
                            <p className="text-xs text-slate-500 max-w-md mx-auto">
                              Comienza el seguimiento médico en piso redactando la primera evolución y observaciones del turno.
                            </p>
                            {!isPatientDischarged && (
                              <button
                                onClick={() => handleOpenNewEvol(1, 'HE-DIRMED-CONSUL-PLT-24')}
                                className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                              >
                                <FiPlus /> Capturar Primera Evolución de Hospitalización
                              </button>
                            )}
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 gap-4">
                            {evolList.map((evolData) => {
                              const slot = evolData.num;
                              const firmaSlot = firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-24' && f.evolution_slot === slot);

                              return (
                                <div key={slot} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/60 transition-all">
                                   <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 mb-3 border-b border-slate-200">
                                    <div className="flex items-center gap-3">
                                      <span className="w-8 h-8 rounded-lg font-bold flex items-center justify-center text-sm shadow-xs bg-indigo-600 text-white">
                                        {slot}
                                      </span>
                                      <div>
                                        <div className="flex items-center gap-2">
                                          <div className="font-bold text-slate-800 text-base">
                                            Evolución y Observaciones {slot} {slot > 1 && <span className="text-xs text-indigo-600 font-semibold">(Continuación)</span>}
                                          </div>
                                          {firmaSlot && (
                                            <span className="text-[11px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-200" title="Firmado conforme a la NOM-004-SSA3-2012 / NOM-024-SSA3-2012">
                                              <MdVerifiedUser className="text-sm text-emerald-600" /> Firmado Biométricamente (NOM)
                                            </span>
                                          )}
                                        </div>
                                        <div className="text-xs text-slate-500">
                                          Fecha: <span className="font-medium text-slate-700">{evolData.fecha} {evolData.hora}</span> • Turno: <span className="font-medium text-slate-700">{evolData.turno}</span>
                                        </div>
                                      </div>
                                    </div>

                                    <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                      {!isPatientDischarged && canModifyOrSignDocument(evolData.medico) && (
                                        <>
                                          <button
                                            onClick={() => handleOpenBiometricSign(slot, `Evolución ${slot} Hosp`, evolData.subjetivo || '', 'HE-DIRMED-CONSUL-PLT-24', 'Nota Médica de Evolución de Hospitalización')}
                                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                              firmaSlot 
                                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100' 
                                                : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                            }`}
                                            title="Firmar este registro con su huella"
                                          >
                                            <MdFingerprint className="text-base" /> {firmaSlot ? 'Firmar de nuevo' : 'Firmar con huella'}
                                          </button>

                                          <button
                                            onClick={() => handleOpenEditEvol(evolData, 'HE-DIRMED-CONSUL-PLT-24')}
                                            className="flex items-center gap-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                          >
                                            <FiEdit3 /> Editar
                                          </button>
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-hospitalizacion?evolucion=${slot}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                      >
                                        <FiFileText /> Imprimir Nota {slot}
                                      </a>
                                    </div>
                                  </div>

                                  {/* CONTENIDO SOAP */}
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                    {evolData.subjetivo && (
                                      <div className="p-3 bg-white rounded-xl border border-slate-100">
                                        <span className="font-bold text-indigo-700 block uppercase mb-0.5">(S) Subjetivo</span>
                                        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.subjetivo}</p>
                                      </div>
                                    )}
                                    {evolData.objetivo && (
                                      <div className="p-3 bg-white rounded-xl border border-slate-100">
                                        <span className="font-bold text-indigo-700 block uppercase mb-0.5">(O) Objetivo</span>
                                        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.objetivo}</p>
                                      </div>
                                    )}
                                    {evolData.analisis && (
                                      <div className="p-3 bg-white rounded-xl border border-slate-100">
                                        <span className="font-bold text-indigo-700 block uppercase mb-0.5">(A) Análisis</span>
                                        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.analisis}</p>
                                      </div>
                                    )}
                                    {evolData.plan && (
                                      <div className="p-3 bg-white rounded-xl border border-slate-100">
                                        <span className="font-bold text-indigo-700 block uppercase mb-0.5">(P) Plan Terapéutico</span>
                                        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{evolData.plan}</p>
                                      </div>
                                    )}
                                    
                                    <div className="col-span-1 md:col-span-2 pt-2.5 border-t border-slate-200/60 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-[11px]">
                                      <div>
                                        Médico Responsable: <strong className="text-slate-800">{evolData.medico}</strong> (Céd. {evolData.cedula})
                                      </div>
                                      {firmaSlot && (
                                        <button
                                          type="button"
                                          onClick={() => handleOpenAuditModal(firmaSlot)}
                                          className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md border border-emerald-200 flex items-center gap-1.5 transition-colors cursor-pointer text-left"
                                          title="Ver los detalles de la firma"
                                        >
                                          <MdVerifiedUser className="text-emerald-600 shrink-0 text-xs" />
                                          <span>Firma verificada • {firmaSlot.fecha_hora_firma}</span>
                                          <span className="text-[9px] font-sans font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded ml-1">Ver detalles</span>
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}

                            {!isPatientDischarged && (
                              <div className="p-4 rounded-2xl border border-dashed border-slate-300 bg-white/70 flex items-center justify-between">
                                <div className="text-xs text-slate-500">
                                  ¿Deseas redactar una nueva nota de pase de visita o cambio de turno en hospitalización?
                                </div>
                                <button
                                  onClick={() => handleOpenNewEvol(nextSlot, 'HE-DIRMED-CONSUL-PLT-24')}
                                  className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                >
                                  <FiPlus /> + Capturar Evolución {nextSlot}
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })() : selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-32/01' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
                      <div className="pb-3 border-b border-slate-100 flex flex-col md:flex-row gap-4 justify-between md:items-center">
                        <div>
                          <h3 className="font-bold text-slate-800 text-base">Consentimiento y Autorización del Procedimiento</h3>
                          <p className="text-xs text-slate-500">Documento de consentimiento informado institucional conforme a la NOM-004-SSA3-2012.</p>
                        </div>
                      </div>

                      {/* SUB-CARD IDENTICAL TO 87/01 EVOLUCION CARDS */}
                      <div className="border border-slate-200/80 rounded-xl p-5 hover:border-hes-blue-main/40 transition-all bg-slate-50/40 space-y-4">
                        {/* HEADER DE LA TARJETA */}
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-slate-200/60">
                          <div className="flex items-center gap-2.5">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs ${
                              data?.consentimiento_32_01 ? 'bg-hes-blue-main text-white' : 'bg-slate-200 text-slate-500'
                            }`}>
                              1
                            </div>
                            <div>
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-bold text-slate-800 text-sm">Consentimiento Informado para Ecocardiograma Transesofágico</span>
                                {(() => {
                                  const summary32 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-32/01', 0);
                                  const isCapaz32 = consentForm3201.paciente_capaz !== undefined ? Boolean(consentForm3201.paciente_capaz) : isPatientAdult(data?.patient);
                                  return (
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      {summary32.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-emerald-300">
                                          <FiCheck className="text-emerald-600" /> {isCapaz32 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : data?.consentimiento_32_01 ? (
                                        <span className="inline-flex items-center gap-1 bg-amber-50 text-amber-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-amber-200">
                                          1. {isCapaz32 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {summary32.hasMedico ? (
                                        <button
                                          type="button"
                                          onClick={() => {
                                            const f = summary32.firmaMedico || firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-32/01');
                                            handleOpenAuditModal(f || { codigo_formato: 'HE-DIRMED-CONSUL-PLT-32/01', slot: 0 });
                                          }}
                                          className="inline-flex items-center gap-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary32.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-blue-200 animate-pulse">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  );
                                })()}
                              </div>
                              <div className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-2">
                                <span>Fecha: {new Date().toLocaleDateString('es-MX')}</span>
                                <span>•</span>
                                <span>Interrogatorio: <strong>{consentForm3201.tipo_interrogatorio}</strong></span>
                              </div>
                            </div>
                          </div>

                          {/* ACCIONES TOP RIGHT */}
                          <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                            {data?.consentimiento_32_01 ? (
                              <>
                                {!isPatientDischarged && (() => {
                                  const summary32 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-32/01', 0);
                                  const isCapaz32 = (consentForm3201.tipo_interrogatorio === 'Directo' && isPatientAdult(data?.patient));
                                  return (
                                    <>
                                      {/* FIRMA PACIENTE / TESTIGO */}
                                      <button
                                        type="button"
                                        onClick={() => setPatientSignModal({
                                          open: true,
                                          documentInfo: {
                                            codigo_formato: 'HE-DIRMED-CONSUL-PLT-32/01',
                                            tipo_documento: 'Consentimiento 32/01 (Ecocardiograma Transesofágico)',
                                            title: 'Consentimiento Informado 32/01',
                                            slot: 0,
                                            paciente_capaz: isCapaz32,
                                            representante_legal: consentForm3201.representante_legal || consentForm3201.paciente_o_representante,
                                            parentesco: isCapaz32 ? 'Paciente' : 'Tutor / Representante Legal'
                                          }
                                        })}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                          summary32.hasPaciente
                                            ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                            : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                        }`}
                                        title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                      >
                                        <MdFingerprint className={`text-base ${summary32.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                        {patientSignatureLabel(summary32)}
                                      </button>

                                      {/* FIRMA MÉDICO */}
                                      {canModifyOrSignDocument(data?.patient?.attending) && (
                                        <button
                                          onClick={() => handleDoctorSign(0, 'Consentimiento 32/01', JSON.stringify(consentForm3201), 'HE-DIRMED-CONSUL-PLT-32/01', 'Consentimiento Informado para Ecocardiograma Transesofágico')}
                                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                            summary32.hasMedico 
                                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100' 
                                              : (summary32.hasPaciente ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-emerald-600 hover:bg-emerald-700 text-white')
                                          }`}
                                          title="Firmar este documento con su huella"
                                        >
                                          <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary32)}
                                        </button>
                                      )}
                                    </>
                                  );
                                })()}
                                {!isPatientDischarged && canModifyOrSignDocument(data?.patient?.attending) && (
                                  <button
                                    onClick={handleOpenEditConsent3201}
                                    className="flex items-center gap-1 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                  >
                                    <FiEdit3 className="text-slate-500" /> Editar
                                  </button>
                                )}
                                <a
                                  href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-32-01?tipo_interrogatorio=${encodeURIComponent(consentForm3201.tipo_interrogatorio)}&testigo1=${encodeURIComponent(consentForm3201.testigo1)}&testigo2=${encodeURIComponent(consentForm3201.testigo2)}&paciente_o_representante=${encodeURIComponent(consentForm3201.paciente_o_representante || data?.patient?.name || '')}&representante_legal=${encodeURIComponent(consentForm3201.representante_legal || '')}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="flex items-center gap-1 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-slate-700 hover:text-hes-blue-main px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                >
                                  <FiPrinter className="text-slate-500" /> Imprimir PDF
                                </a>
                              </>
                            ) : (
                              !isPatientDischarged && (
                                <button
                                  onClick={handleOpenNewConsent3201}
                                  className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                >
                                  <FiPlus /> Capturar Consentimiento 32/01
                                </button>
                              )
                            )}
                          </div>
                        </div>

                        {/* CUERPO READ-ONLY SI YA FUE GENERADO */}
                        {data?.consentimiento_32_01 ? (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                            {/* (A) DATOS DE INTERROGATORIO */}
                            <div className="p-3.5 bg-white rounded-xl border border-slate-100 space-y-2">
                              <span className="font-bold text-hes-blue-main block uppercase mb-1">(A) Datos de Interrogatorio y Autorización</span>
                              <div className="space-y-1.5 text-slate-700">
                                <div><span className="font-semibold text-slate-500">Tipo de Interrogatorio:</span> <span className="font-bold text-slate-800">{consentForm3201.tipo_interrogatorio}</span></div>
                                <div><span className="font-semibold text-slate-500">Paciente (Titular):</span> <span className="font-bold text-slate-800">{consentForm3201.paciente_o_representante || data?.patient?.name}</span></div>
                                <div><span className="font-semibold text-slate-500">Representante Legal:</span> <span className="font-medium text-slate-800">{consentForm3201.representante_legal || 'No especificado / Directo'}</span></div>
                              </div>
                            </div>

                            {/* (B) TESTIGOS Y MÉDICO */}
                            <div className="p-3.5 bg-white rounded-xl border border-slate-100 space-y-2">
                              <span className="font-bold text-hes-blue-main block uppercase mb-1">(B) Testigos Presenciales y Médico</span>
                              <div className="space-y-1.5 text-slate-700">
                                <div><span className="font-semibold text-slate-500">Testigo 1:</span> <span className="font-bold text-slate-800">{consentForm3201.testigo1 || 'Pendiente'}</span></div>
                                <div><span className="font-semibold text-slate-500">Testigo 2:</span> <span className="font-bold text-slate-800">{consentForm3201.testigo2 || 'Pendiente'}</span></div>
                                 <div><span className="font-semibold text-slate-500">Médico Autorizado:</span> <span className="font-bold text-slate-800">{currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</span>{(currentDoctorCedula || data?.patient?.cedula) ? <span className="text-slate-500"> (Céd. {currentDoctorCedula || data?.patient?.cedula})</span> : ''}</div>
                              </div>
                            </div>

                            {/* PREVIEW EN VIVO DE LA DECLARACIÓN */}
                            <div className="col-span-1 md:col-span-2 p-3.5 bg-blue-50/50 rounded-xl border border-blue-100 text-xs text-slate-700 leading-relaxed">
                              <span className="font-bold text-hes-blue-main block uppercase text-[10px] mb-1">Declaración del Procedimiento:</span>
                              <p className="italic">
                                "Yo <strong>{consentForm3201.paciente_o_representante || data?.patient?.name}</strong> en calidad de Paciente 
                                {consentForm3201.representante_legal ? <span> y <strong>{consentForm3201.representante_legal}</strong> en calidad de Representante Legal</span> : ''}, 
                                acepto voluntariamente y autorizo al Dr(a). <strong>{currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</strong> para que practique en la persona del denominado paciente el Ecocardiograma transesofágico..."
                              </p>
                            </div>

                            {/* FOOTER DE FIRMA Y MÉDICO */}
                            <div className="col-span-1 md:col-span-2 pt-2.5 border-t border-slate-200/60 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-[11px]">
                              <div>
                                Médico Responsable: <strong className="text-slate-800">{currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</strong>{(currentDoctorCedula || data?.patient?.cedula) ? ` (Céd. ${currentDoctorCedula || data?.patient?.cedula})` : ''}
                              </div>
                              {(() => {
                                const firmaConsent = firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-32/01');
                                return firmaConsent ? (
                                  <button
                                    type="button"
                                    onClick={() => handleOpenAuditModal(firmaConsent)}
                                    className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md border border-emerald-200 flex items-center gap-1.5 transition-colors cursor-pointer text-left"
                                    title="Ver los detalles de la firma"
                                  >
                                    <MdVerifiedUser className="text-emerald-600 shrink-0 text-xs" />
                                    <span>Firma verificada • {firmaConsent.fecha_hora_firma}</span>
                                    <span className="text-[9px] font-sans font-bold text-hes-blue-main bg-blue-50 px-1.5 py-0.5 rounded ml-1">Ver detalles</span>
                                  </button>
                                ) : null;
                              })()}
                            </div>
                          </div>
                        ) : (
                          <div className="py-8 text-center text-xs text-slate-400 space-y-3">
                            <p>No se ha registrado aún el consentimiento informado para este paciente en SQL Server.</p>
                            {!isPatientDischarged && (
                              <button
                                onClick={handleOpenNewConsent3201}
                                className="inline-flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                              >
                                <FiPlus /> Capturar Consentimiento 32/01
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-25' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial25 = (data?.historial_25 && data.historial_25.length > 0)
                          ? data.historial_25
                          : (data?.consentimiento_25 ? [data.consentimiento_25] : []);

                        const activeDoc25 = (selectedMrnum25 ? historial25.find(h => h.mrnum === selectedMrnum25) : null)
                          || (historial25.length > 0 ? historial25[0] : null)
                          || data?.consentimiento_25;

                        const docDoctor25 = activeDoc25?.medico_tratante || activeDoc25?.n_medico || '';
                        const isOwner25 = canModifyOrSignDocument(docDoctor25);
                        const summary25 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-25', activeDoc25?.mrnum || 0);
                        const firmaDoc25 = summary25.firmaMedico || summary25.allFirmas[0];
                        const isSigned25 = Boolean(activeDoc25?.firmado || activeDoc25?.signed_by || summary25.hasMedico);
                        const isCapaz25 = activeDoc25?.paciente_capaz !== undefined ? activeDoc25.paciente_capaz : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiFolder />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">{selectedFormat.nombre}</h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial25.length} {historial25.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      {/* BADGE PACIENTE */}
                                      {summary25.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz25 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : activeDoc25 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz25 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned25 ? (
                                        <button
                                          type="button"
                                          onClick={() => {
                                            if (firmaDoc25) handleOpenAuditModal(firmaDoc25);
                                            else handleOpenAuditModal({ codigo_formato: 'HE-DIRMED-CONSUL-PLT-25', slot: activeDoc25?.mrnum || 0 });
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary25.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                      {!isOwner25 && docDoctor25 && (
                                        <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-900 border border-amber-300 font-bold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full shadow-xs">
                                          <FiLock /> Bloqueado ({docDoctor25})
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent25}
                                      className="flex items-center gap-1.5 he-fmt-btn-new px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Nuevo Consentimiento
                                    </button>
                                  )}

                                  {activeDoc25 && (
                                    <>
                                      {isOwner25 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              {/* FIRMA PACIENTE / TESTIGO */}
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-CONSUL-PLT-25',
                                                    tipo_documento: 'Consentimiento Revisión Ginecológica (25)',
                                                    title: 'Consentimiento Informado 25',
                                                    slot: activeDoc25.mrnum || 0,
                                                    paciente_capaz: isCapaz25,
                                                    representante_legal: activeDoc25?.representante_legal || activeDoc25?.pariente || activeDoc25?.paciente_resp,
                                                    parentesco: activeDoc25?.parentesco || activeDoc25?.parentesco_paciente || (isCapaz25 ? 'Paciente' : 'Tutor / Representante Legal')
                                                  }
                                                })}
                                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                                  summary25.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary25.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary25)}
                                              </button>

                                              {/* FIRMA MÉDICO */}
                                              <button
                                                onClick={() => handleDoctorSign(activeDoc25.mrnum || 0, 'Consentimiento Revisión Ginecológica', JSON.stringify(activeDoc25), 'HE-DIRMED-CONSUL-PLT-25', 'Consentimiento Informado')}
                                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                                  isSigned25 
                                                    ? 'he-fmt-btn-plain' 
                                                    : (summary25.hasPaciente ? 'he-fmt-btn-sign' : 'he-fmt-btn-sign')
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary25)}
                                              </button>
                                              <button onClick={() => handleOpenEditConsent25(activeDoc25)} className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all">
                                                <FiEdit3 className="text-slate-500" /> Editar
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-500 border border-slate-200 px-2.5 py-1.5 rounded-xl text-xs font-bold" title="Documento elaborado por otro médico">
                                          <FiLock /> Solo Lectura
                                        </span>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-25${activeDoc25.mrnum ? `?mrnum=${activeDoc25.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-slate-700 hover:text-hes-blue-main px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                      >
                                        <FiPrinter className="text-slate-500" /> Imprimir PDF
                                      </a>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES / DOCUMENTOS PREVIOS */}
                              {historial25.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial25.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial25.map((item, idx) => {
                                      const isSelected = (!selectedMrnum25 && idx === 0) || selectedMrnum25 === item.mrnum;
                                      const itemOwner = canModifyOrSignDocument(item.medico_tratante);
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          type="button"
                                          onClick={() => setSelectedMrnum25(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>#{historial25.length - idx} • {item.created_on || 'Sin fecha'}</span>
                                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-normal ${isSelected ? 'bg-blue-700 text-blue-100' : 'bg-slate-100 text-slate-600'}`}>
                                            {item.medico_tratante || 'Dr. Médico'}
                                          </span>
                                          {!itemOwner && (
                                            <FiLock className={isSelected ? 'text-blue-200' : 'text-amber-600'} title="Solo Lectura (Otro Médico)" />
                                          )}
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {!isOwner25 && docDoctor25 && (
                                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-2 text-amber-800 text-xs font-semibold">
                                  <FiLock className="text-amber-600 text-base shrink-0" />
                                  <span>Candado de Seguridad NOM-004: Este registro #{activeDoc25?.mrnum || 1} pertenece al <strong>{docDoctor25}</strong>. Al ser de otro profesional, está protegido en modo Solo Lectura. Puedes crear tu propio registro dando clic en "+ Capturar Nuevo Consentimiento".</span>
                                </div>
                              )}

                              {activeDoc25 ? (
                                <div className="text-xs space-y-4">
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                                     <div><span className="text-slate-500 block">Médico Tratante:</span><span className="font-bold text-slate-800">{activeDoc25.medico_tratante || 'DR. MEDICO TRATANTE'}</span></div>
                                     <div><span className="text-slate-500 block">Fecha y Hora de Registro:</span><span className="font-bold text-slate-800">{activeDoc25.created_on || '--'}</span></div>
                                     <div><span className="text-slate-500 block">Identificador SQL (MRNum):</span><span className="font-mono font-bold text-hes-blue-main">{activeDoc25.mrnum || '1'}</span></div>
                                  </div>
                                  <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100">
                                     <span className="text-hes-blue-main font-bold block mb-1">Procedimiento Proyectado:</span>
                                     <p className="text-slate-700">Revisión ginecológica u obstétrica (tacto vaginal, tacto rectal, exploración mamaria), hospitalización, colocación de sondas y catéteres, aplicación de medicamentos, transfusiones sanguíneas, estudios de gabinete.</p>
                                  </div>
                                  <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
                                     {firmaDoc25 ? (
                                          <button onClick={() => handleOpenAuditModal(firmaDoc25)} className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1 transition-colors">
                                              <MdVerifiedUser /> Sello: {firmaDoc25.sello_digital ? `${firmaDoc25.sello_digital.slice(0, 20)}...` : 'Verificado'}
                                          </button>
                                     ) : (activeDoc25?.signed_by || activeDoc25?.signed_on) ? (
                                          <span className="text-emerald-700 font-mono text-[10px] bg-emerald-50 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1">
                                              <MdVerifiedUser /> Firmado en Vertical: {activeDoc25.signed_by} ({activeDoc25.signed_on})
                                          </span>
                                     ) : <div/>}
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center text-xs text-slate-400 space-y-3">
                                  <p>No se ha registrado ningún consentimiento para este paciente.</p>
                                  {!isPatientDischarged && (
                                    <button onClick={handleOpenNewConsent25} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                      <FiPlus /> Capturar Primer Consentimiento Formato 25
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
) : selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-EED' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full ring-1 ring-slate-100">
                      <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                              <FiActivity />
                            </div>
                            <div>
                              <h3 className="font-bold text-slate-800 text-sm">{selectedFormat.nombre}</h3>
                              <div className="flex items-center gap-2 mt-1">
                                {(() => {
                                  const summaryEED = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-EED', 0);
                                  const isCapazEED = data?.consentimiento_eed?.paciente_capaz !== undefined ? data.consentimiento_eed.paciente_capaz : isPatientAdult(data?.patient);
                                  return (
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      {summaryEED.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-emerald-300">
                                          <FiCheck className="text-emerald-600" /> {isCapazEED ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : data?.consentimiento_eed ? (
                                        <span className="inline-flex items-center gap-1 bg-amber-50 text-amber-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-amber-200">
                                          1. {isCapazEED ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {summaryEED.hasMedico ? (
                                        <button
                                          type="button"
                                          onClick={() => {
                                            const f = summaryEED.firmaMedico || firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-EED');
                                            handleOpenAuditModal(f || { codigo_formato: 'HE-DIRMED-CONSUL-PLT-EED', slot: 0 });
                                          }}
                                          className="inline-flex items-center gap-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summaryEED.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-blue-200 animate-pulse">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  );
                                })()}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                            {(() => {
                              const docDoctorEED = data?.consentimiento_eed?.medico || data?.patient?.attending || '';
                              const isOwnerEED = canModifyOrSignDocument(docDoctorEED);
                              const summaryEED = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-EED', 0);
                              const isCapazEED = data?.consentimiento_eed?.paciente_capaz !== undefined ? data.consentimiento_eed.paciente_capaz : isPatientAdult(data?.patient);
                              const isSignedEED = Boolean(summaryEED.hasMedico);

                              return data?.consentimiento_eed ? (
                                <>
                                  {isOwnerEED ? (
                                    <>
                                      {!isPatientDischarged && (
                                        <>
                                          {/* FIRMA PACIENTE / TESTIGO */}
                                          <button
                                            type="button"
                                            onClick={() => setPatientSignModal({
                                              open: true,
                                              documentInfo: {
                                                codigo_formato: 'HE-DIRMED-CONSUL-PLT-EED',
                                                tipo_documento: 'Consentimiento Ecocardiograma Estrés (EED)',
                                                title: 'Consentimiento Informado EED',
                                                slot: 0,
                                                paciente_capaz: isCapazEED,
                                                representante_legal: data?.consentimiento_eed?.representante_legal || data?.consentimiento_eed?.responsable,
                                                parentesco: data?.consentimiento_eed?.parentesco || (isCapazEED ? 'Paciente' : 'Tutor / Representante Legal')
                                              }
                                            })}
                                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                              summaryEED.hasPaciente
                                                ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                            }`}
                                            title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                          >
                                            <MdFingerprint className={`text-base ${summaryEED.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                            {patientSignatureLabel(summaryEED)}
                                          </button>

                                          {/* FIRMA MÉDICO */}
                                          <button
                                            onClick={() => handleDoctorSign(0, 'Ecocardiograma Estrés', JSON.stringify(data.consentimiento_eed), 'HE-DIRMED-CONSUL-PLT-EED', 'Consentimiento Informado')}
                                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                              isSignedEED 
                                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-300' 
                                                : (summaryEED.hasPaciente ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-emerald-600 hover:bg-emerald-700 text-white')
                                            }`}
                                          >
                                            <MdFingerprint className="text-base" /> {doctorSignatureLabel(summaryEED)}
                                          </button>
                                          <button onClick={handleOpenEditConsentEED} className="flex items-center gap-1 bg-white border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold">
                                            <FiEdit3 /> Editar
                                          </button>
                                        </>
                                      )}
                                    </>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                      <FiLock /> Solo Lectura
                                    </span>
                                  )}
                                  <a href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-eed`} target="_blank" rel="noreferrer" className="flex items-center gap-1 bg-white text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold">
                                    <FiFileText /> Imprimir PDF Oficial
                                  </a>
                                </>
                              ) : (
                                !isPatientDischarged && (
                                  <button onClick={handleOpenNewConsentEED} className="flex items-center gap-1.5 bg-emerald-600 text-white px-4 py-1.5 rounded-lg text-xs font-bold">
                                    <FiPlus /> Capturar EED
                                  </button>
                                )
                              );
                            })()}
                          </div>
                        </div>
                      </div>
                      
                      <div className="p-4 sm:p-5 bg-white grow flex flex-col">
                        {data?.consentimiento_eed ? (
                          <div className="text-xs space-y-4">
                            <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                               <div><span className="text-slate-500 block">Responsable:</span><span className="font-bold text-slate-800">{data.consentimiento_eed.responsable || data.patient.name}</span></div>
                               <div><span className="text-slate-500 block">TA / FR / Peso / Talla:</span><span className="font-bold text-slate-800">{data.consentimiento_eed.ta} / {data.consentimiento_eed.fr} / {data.consentimiento_eed.peso} / {data.consentimiento_eed.talla}</span></div>
                            </div>
                            <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100">
                               <span className="text-hes-blue-main font-bold block mb-1">Comentarios:</span>
                               <p className="text-slate-700 italic">{data.consentimiento_eed.comentarios || 'Ninguno'}</p>
                            </div>
                            <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
                               {(() => {
                                const firma = firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-EED');
                                return firma ? (
                                    <button onClick={() => handleOpenAuditModal(firma)} className="text-emerald-700 font-mono text-[10px] bg-emerald-50 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1">
                                        <MdVerifiedUser /> Sello: {firma.sello_digital.slice(0, 20)}...
                                    </button>
                                ) : <div/>;
                               })()}
                            </div>
                          </div>
                        ) : (
                          <div className="py-8 text-center text-xs text-slate-400 space-y-3">
                            <p>No se ha registrado el Ecocardiograma de Estrés con Dobutamina.</p>
                            {!isPatientDischarged && (
                              <button onClick={handleOpenNewConsentEED} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                <FiPlus /> Capturar Formato EED
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-34' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial34 = (data?.historial_34_01 && data.historial_34_01.length > 0)
                          ? data.historial_34_01
                          : (data?.consentimiento_34_01 ? [data.consentimiento_34_01] : []);

                        const activeDoc34 = (selectedMrnum3401 ? historial34.find(h => h.mrnum === selectedMrnum3401) : null)
                          || (historial34.length > 0 ? historial34[0] : null)
                          || data?.consentimiento_34_01;

                        const docDoctor34 = activeDoc34?.medico_tratante || activeDoc34?.nombre_medico_mi || '';
                        const isOwner34 = canModifyOrSignDocument(docDoctor34);
                        const summary34 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-34', activeDoc34?.mrnum || 0);
                        const firmaDoc34 = summary34.firmaMedico || summary34.allFirmas[0];
                        const isSigned34 = Boolean(activeDoc34?.firmado || activeDoc34?.signed_by || summary34.hasMedico);
                        const isCapaz34 = activeDoc34?.paciente_capaz !== undefined ? activeDoc34.paciente_capaz : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiActivity />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">{selectedFormat.nombre}</h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial34.length} {historial34.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      {/* BADGE PACIENTE */}
                                      {summary34.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz34 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : activeDoc34 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz34 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned34 ? (
                                        <button
                                          type="button"
                                          onClick={() => {
                                            if (firmaDoc34) handleOpenAuditModal(firmaDoc34);
                                            else handleOpenAuditModal({ codigo_formato: 'HE-DIRMED-CONSUL-PLT-34', slot: activeDoc34?.mrnum || 0 });
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary34.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc34 ? (
                                    <>
                                      {isOwner34 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              {/* FIRMA PACIENTE / TESTIGO */}
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-CONSUL-PLT-34',
                                                    tipo_documento: 'Consentimiento Mesa Inclinada (34/01)',
                                                    title: 'Consentimiento Informado 34/01',
                                                    slot: activeDoc34.mrnum || 0,
                                                    paciente_capaz: isCapaz34,
                                                    representante_legal: activeDoc34?.representante_legal || activeDoc34?.nombre_representante || activeDoc34?.rep_legal,
                                                    parentesco: activeDoc34?.parentesco || activeDoc34?.parentesco_representante || (isCapaz34 ? 'Paciente' : 'Tutor / Representante Legal')
                                                  }
                                                })}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  summary34.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary34.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary34)}
                                              </button>

                                              {/* FIRMA MÉDICO */}
                                              <button
                                                onClick={() => handleDoctorSign(activeDoc34.mrnum || 0, 'Mesa Inclinada (Tilt Test)', JSON.stringify(activeDoc34), 'HE-DIRMED-CONSUL-PLT-34', 'Consentimiento Informado')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned34 
                                                    ? 'he-fmt-btn-plain' 
                                                    : (summary34.hasPaciente ? 'he-fmt-btn-sign' : 'he-fmt-btn-sign')
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary34)}
                                              </button>
                                              <button
                                                onClick={() => handleOpenEditConsent3401(activeDoc34)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar
                                              </button>
                                              <button
                                                onClick={handleOpenNewConsent3401}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> Capturar Nuevo Consentimiento
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNewConsent3401}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> Capturar Nuevo Consentimiento
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-34-01${activeDoc34.mrnum ? `?mrnum=${activeDoc34.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent3401}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Mesa Inclinada
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES / DOCUMENTOS PREVIOS */}
                              {historial34.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial34.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial34.map((item, idx) => {
                                      const isSelected = (!selectedMrnum3401 && idx === 0) || selectedMrnum3401 === item.mrnum;
                                      const itemOwner = canModifyOrSignDocument(item.medico_tratante || item.nombre_medico_mi);
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          type="button"
                                          onClick={() => setSelectedMrnum3401(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>#{historial34.length - idx} • {item.created_on || 'Sin fecha'}</span>
                                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-normal ${isSelected ? 'bg-blue-700 text-blue-100' : 'bg-slate-100 text-slate-600'}`}>
                                            {item.medico_tratante || item.nombre_medico_mi || 'Dr. Médico'}
                                          </span>
                                          {!itemOwner && (
                                            <FiLock className={isSelected ? 'text-blue-200' : 'text-amber-600'} title="Solo Lectura (Otro Médico)" />
                                          )}
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {!isOwner34 && docDoctor34 && (
                                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between gap-3 text-amber-800 text-xs font-semibold flex-wrap">
                                  <div className="flex items-center gap-2">
                                    <FiLock className="text-amber-600 text-base shrink-0" />
                                    <span>Candado de Seguridad NOM-004: Este registro #{activeDoc34?.mrnum || 1} pertenece al <strong>{docDoctor34}</strong>. Al ser de otro profesional, está protegido en modo Solo Lectura.</span>
                                  </div>
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent3401}
                                      className="inline-flex items-center gap-1 bg-amber-600 hover:bg-amber-700 text-white px-3 py-1 rounded-lg text-xs font-bold shadow-xs transition-colors shrink-0"
                                    >
                                      <FiPlus /> Capturar Nuevo Consentimiento
                                    </button>
                                  )}
                                </div>
                              )}

                              {activeDoc34 ? (
                                <div className="text-xs space-y-4">
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                                      <div><span className="text-slate-500 block">Médico Tratante:</span><span className="font-bold text-slate-800">{activeDoc34.medico_tratante || activeDoc34.nombre_medico_mi || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</span></div>
                                     <div><span className="text-slate-500 block">Pariente / Representante:</span><span className="font-bold text-slate-800">{activeDoc34.pariente || data.patient.name}</span></div>
                                     <div><span className="text-slate-500 block">Signos Vitales:</span><span className="font-bold text-slate-800">TA: {activeDoc34.ta || '--'} | FC Meta: {activeDoc34.fc_meta || '--'} | FR: {activeDoc34.f_resp || '--'}</span></div>
                                  </div>
                                  <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100">
                                     <span className="text-hes-blue-main font-bold block mb-1">Conclusiones del Estudio:</span>
                                     <p className="text-slate-700">{activeDoc34.conclusiones || 'Sin conclusiones registradas.'}</p>
                                     {activeDoc34.conclusiones_2 && <p className="text-slate-700 mt-1">{activeDoc34.conclusiones_2}</p>}
                                     {activeDoc34.conclusiones_3 && <p className="text-slate-700 mt-1">{activeDoc34.conclusiones_3}</p>}
                                  </div>
                                  <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
                                     {firmaDoc34 ? (
                                          <button onClick={() => handleOpenAuditModal(firmaDoc34)} className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1 transition-colors">
                                              <MdVerifiedUser /> Sello: {firmaDoc34.sello_digital ? `${firmaDoc34.sello_digital.slice(0, 20)}...` : 'Verificado'}
                                          </button>
                                     ) : (activeDoc34?.signed_by || activeDoc34?.signed_on) ? (
                                          <span className="text-emerald-700 font-mono text-[10px] bg-emerald-50 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1">
                                              <MdVerifiedUser /> Firmado en Vertical: {activeDoc34.signed_by} ({activeDoc34.signed_on})
                                          </span>
                                     ) : <div/>}
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center text-xs text-slate-400 space-y-3">
                                  <p>No se ha registrado el Estudio de Mesa Inclinada para este paciente.</p>
                                  {!isPatientDischarged && (
                                    <button onClick={handleOpenNewConsent3401} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                      <FiPlus /> Capturar Formato 34/01
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-12' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial12 = (data?.historial_12 && data.historial_12.length > 0)
                          ? data.historial_12
                          : (data?.consentimiento_12 ? [data.consentimiento_12] : []);

                        const activeDoc12 = (selectedMrnum12 ? historial12.find(h => h.mrnum === selectedMrnum12) : null)
                          || (historial12.length > 0 ? historial12[0] : null)
                          || data?.consentimiento_12;

                        const docDoctor12 = activeDoc12?.medico_tratante || activeDoc12?.n_medico || '';
                        const isOwner12 = canModifyOrSignDocument(docDoctor12);
                        const summary12 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-12', activeDoc12?.mrnum || 0);
                        const firmaDoc12 = summary12.firmaMedico || summary12.allFirmas[0];
                        const isSigned12 = Boolean(activeDoc12?.firmado || activeDoc12?.signed_by || summary12.hasMedico);
                        const isCapaz12 = activeDoc12?.paciente_capaz !== undefined ? activeDoc12.paciente_capaz : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiFileText />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">{selectedFormat.nombre}</h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial12.length} {historial12.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      {/* BADGE PACIENTE */}
                                      {summary12.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz12 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : activeDoc12 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz12 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned12 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc12) {
                                              handleOpenAuditModal(firmaDoc12);
                                            }
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary12.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc12 ? (
                                    <>
                                      {isOwner12 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              {/* FIRMA PACIENTE / TESTIGO */}
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-CONSUL-PLT-12',
                                                    tipo_documento: 'Consentimiento Gineco y Obstetricia (12)',
                                                    title: 'Consentimiento Informado 12',
                                                    slot: activeDoc12.mrnum || 0,
                                                    paciente_capaz: isCapaz12,
                                                    representante_legal: activeDoc12?.representante_legal || activeDoc12?.nom_paciente_o_rep || activeDoc12?.paciente_o_representante,
                                                    parentesco: activeDoc12?.parentesco || activeDoc12?.parentesco_pac || (isCapaz12 ? 'Paciente' : 'Tutor / Representante Legal')
                                                  }
                                                })}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  summary12.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary12.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary12)}
                                              </button>

                                              {/* FIRMA MÉDICO */}
                                              <button
                                                onClick={() => handleDoctorSign(activeDoc12.mrnum || 0, 'Consentimiento Gineco y Obstetricia (Hosp/Urg)', JSON.stringify(activeDoc12), 'HE-DIRMED-CONSUL-PLT-12', 'Consentimiento Informado')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned12 
                                                    ? 'he-fmt-btn-plain' 
                                                    : (summary12.hasPaciente ? 'he-fmt-btn-sign' : 'he-fmt-btn-sign')
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary12)}
                                              </button>
                                              <button
                                                onClick={() => handleOpenEditConsent12(activeDoc12)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar
                                              </button>
                                              <button
                                                onClick={handleOpenNewConsent12}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> Capturar Nuevo Consentimiento
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNewConsent12}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> Capturar Nuevo Consentimiento
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-12${activeDoc12.mrnum ? `?mrnum=${activeDoc12.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent12}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Consentimiento 12
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES */}
                              {historial12.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial12.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial12.map((item, idx) => {
                                      const isSelected = (!selectedMrnum12 && idx === 0) || selectedMrnum12 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum12(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial12.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                          {item.firmado && (
                                            <span className={`text-[9px] px-1 rounded font-bold ${isSelected ? 'bg-emerald-400 text-emerald-950' : 'bg-emerald-100 text-emerald-800'}`}>
                                              ✓
                                            </span>
                                          )}
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc12 ? (
                                <div className="space-y-4">
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                                      <p className="text-[11px] font-bold text-slate-500 uppercase">Diagnóstico Clínico</p>
                                      <p className="text-sm font-extrabold text-slate-800">{activeDoc12.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                      <div className="pt-2 flex items-center gap-2 text-xs">
                                        <span className="font-semibold text-slate-500">Servicio:</span>
                                        <span className="font-bold px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-[11px]">{activeDoc12.servicio || 'URGENCIAS'}</span>
                                      </div>
                                    </div>
                                    <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                                      <p className="text-[11px] font-bold text-slate-500 uppercase">Médico Tratante Responsable</p>
                                      <p className="text-sm font-extrabold text-slate-800">{activeDoc12.medico_tratante || activeDoc12.n_medico || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                      <p className="text-xs text-slate-600">Cédula Profesional: <span className="font-mono font-bold">{activeDoc12.cedula || currentDoctorCedula || data?.patient?.cedula || 'SIN CÉDULA'}</span></p>
                                    </div>
                                  </div>

                                  <div className="p-3.5 bg-blue-50/50 rounded-xl border border-blue-200 space-y-2 text-xs">
                                    <p className="font-bold text-hes-blue-main uppercase text-[11px]">Procedimientos e Intervenciones Proyectados</p>
                                    <p className="text-slate-700 leading-relaxed">
                                      {activeDoc12.procedimientos || 'Revisión ginecológica u obstétrica conforme a valoración clínica.'}
                                    </p>
                                  </div>

                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                                      <p className="font-bold text-slate-600 text-[11px]">Beneficios Esperados</p>
                                      <p className="text-slate-700 italic">{activeDoc12.beneficios || 'Sin beneficios especificados.'}</p>
                                    </div>
                                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                                      <p className="font-bold text-slate-600 text-[11px]">Procedimientos Alternativos</p>
                                      <p className="text-slate-700 italic">{activeDoc12.alternativas || 'Sin alternativas especificadas.'}</p>
                                    </div>
                                  </div>

                                  {isSigned12 && (
                                    <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                                      <div className="flex items-center gap-2">
                                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                                          <MdVerifiedUser /> Firmado Digitalmente
                                        </span>
                                        {activeDoc12.signed_on && (
                                          <span className="text-[11px] text-slate-500 font-mono">
                                            {activeDoc12.signed_on}
                                          </span>
                                        )}
                                      </div>
                                      {firmaDoc12 && (
                                        <button 
                                          onClick={() => handleOpenAuditModal(firmaDoc12)} 
                                          className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1 transition-colors"
                                        >
                                          <FiLock /> Sello: {firmaDoc12.sello_digital?.substring(0, 10)}... (Auditar)
                                        </button>
                                      )}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div className="py-8 text-center text-xs text-slate-400 space-y-3">
                                  <p>No se ha registrado el Consentimiento 12 para este paciente.</p>
                                  {!isPatientDischarged && (
                                    <button onClick={handleOpenNewConsent12} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                      <FiPlus /> Capturar Consentimiento Formato 12
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-04' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial04 = (data?.historial_04 && data.historial_04.length > 0)
                          ? data.historial_04
                          : (data?.consentimiento_04 ? [data.consentimiento_04] : []);

                        const activeDoc04 = (selectedMrnum04 ? historial04.find(h => h.mrnum === selectedMrnum04) : null)
                          || (historial04.length > 0 ? historial04[0] : null)
                          || data?.consentimiento_04;

                        const docDoctor04 = activeDoc04?.medico_tratante || activeDoc04?.n_medico || '';
                        const isOwner04 = canModifyOrSignDocument(docDoctor04);
                        const summary04 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-04', activeDoc04?.mrnum || 0);
                        const firmaDoc04 = summary04.firmaMedico || summary04.allFirmas[0];
                        const isSigned04 = Boolean(activeDoc04?.firmado || activeDoc04?.signed_by || summary04.hasMedico);
                        const isCapaz04 = activeDoc04?.paciente_capaz !== undefined ? activeDoc04.paciente_capaz : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiFileText />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">{selectedFormat.nombre}</h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial04.length} {historial04.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      {/* BADGE PACIENTE */}
                                      {summary04.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz04 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : activeDoc04 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz04 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned04 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc04) {
                                              handleOpenAuditModal(firmaDoc04);
                                            }
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary04.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc04 ? (
                                    <>
                                      {isOwner04 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              {/* FIRMA PACIENTE / TESTIGO */}
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-CONSUL-PLT-04',
                                                    tipo_documento: 'Consentimiento Catéter Venoso Central (04)',
                                                    title: 'Consentimiento Informado 04',
                                                    slot: activeDoc04.mrnum || 0,
                                                    paciente_capaz: isCapaz04,
                                                    representante_legal: activeDoc04?.representante_legal || activeDoc04?.nombre_tutor || activeDoc04?.pariente,
                                                    parentesco: activeDoc04?.parentesco || activeDoc04?.parentesco_tutor || (isCapaz04 ? 'Paciente' : 'Tutor / Representante Legal')
                                                  }
                                                })}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  summary04.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary04.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary04)}
                                              </button>

                                              {/* FIRMA MÉDICO */}
                                              <button
                                                onClick={() => handleDoctorSign(activeDoc04.mrnum || 0, 'Consentimiento Colocación de Catéter Venoso Central', JSON.stringify(activeDoc04), 'HE-DIRMED-CONSUL-PLT-04', 'Consentimiento Informado')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned04 
                                                    ? 'he-fmt-btn-plain' 
                                                    : (summary04.hasPaciente ? 'he-fmt-btn-sign' : 'he-fmt-btn-sign')
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary04)}
                                              </button>
                                              <button
                                                onClick={() => handleOpenEditConsent04(activeDoc04)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar
                                              </button>
                                              <button
                                                onClick={handleOpenNewConsent04}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> Capturar Nuevo Consentimiento
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNewConsent04}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> Capturar Nuevo Consentimiento
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-04${activeDoc04.mrnum ? `?mrnum=${activeDoc04.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent04}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Consentimiento Formato 04
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES */}
                              {historial04.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial04.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial04.map((item, idx) => {
                                      const isSelected = (!selectedMrnum04 && idx === 0) || selectedMrnum04 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum04(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial04.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                          {item.firmado && (
                                            <span className={`text-[9px] px-1 rounded font-bold ${isSelected ? 'bg-emerald-400 text-emerald-950' : 'bg-emerald-100 text-emerald-800'}`}>
                                              ✓
                                            </span>
                                          )}
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc04 ? (
                                <div className="space-y-4">
                                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                                    <p className="text-[11px] font-bold text-slate-500 uppercase">Médico Tratante Responsable</p>
                                    <p className="text-sm font-extrabold text-slate-800">{activeDoc04.medico_tratante || activeDoc04.n_medico || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    <p className="text-xs text-slate-600">Cédula Profesional: <span className="font-mono font-bold">{activeDoc04.cedula || currentDoctorCedula || data?.patient?.cedula || 'SIN CÉDULA'}</span></p>
                                  </div>

                                  <div className="p-3.5 bg-blue-50/50 rounded-xl border border-blue-200 space-y-2 text-xs">
                                    <p className="font-bold text-hes-blue-main uppercase text-[11px]">Procedimiento y Objetivo Autorizado</p>
                                    <p className="text-slate-700 leading-relaxed">
                                      {activeDoc04.procedimiento || activeDoc04.procedimientos || 'Colocación de catéter vascular conforme a indicación médica.'}
                                    </p>
                                  </div>

                                  {isSigned04 && (
                                    <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                                      <div className="flex items-center gap-2">
                                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                                          <MdVerifiedUser /> Firmado Digitalmente
                                        </span>
                                        {activeDoc04.signed_on && (
                                          <span className="text-[11px] text-slate-500 font-mono">
                                            {activeDoc04.signed_on}
                                          </span>
                                        )}
                                      </div>
                                      {firmaDoc04 && (
                                        <button 
                                          onClick={() => handleOpenAuditModal(firmaDoc04)} 
                                          className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1 transition-colors"
                                        >
                                          <FiLock /> Sello: {firmaDoc04.sello_digital?.substring(0, 10)}... (Auditar)
                                        </button>
                                      )}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div className="py-8 text-center text-xs text-slate-400 space-y-3">
                                  <p>No se ha registrado el Consentimiento 04 para este paciente.</p>
                                  {!isPatientDischarged && (
                                    <button onClick={handleOpenNewConsent04} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                      <FiPlus /> Capturar Consentimiento Formato 04
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-15' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial15 = (data?.historial_15 && data.historial_15.length > 0)
                          ? data.historial_15
                          : (data?.consentimiento_15 ? [data.consentimiento_15] : []);

                        const activeDoc15 = (selectedMrnum15 ? historial15.find(h => h.mrnum === selectedMrnum15) : null)
                          || (historial15.length > 0 ? historial15[0] : null)
                          || data?.consentimiento_15;

                        const docDoctor15 = activeDoc15?.medico_tratante || activeDoc15?.n_medico || '';
                        const isOwner15 = canModifyOrSignDocument(docDoctor15);
                        const summary15 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-15', activeDoc15?.mrnum || 0);
                        const firmaDoc15 = summary15.firmaMedico || summary15.allFirmas[0];
                        const isSigned15 = Boolean(activeDoc15?.firmado || activeDoc15?.signed_by || summary15.hasMedico);
                        const isNoAutorizado = Boolean(activeDoc15?.no_autorizo || activeDoc15?.tipo === 'no_autorizo');
                        const isCapaz15 = activeDoc15?.paciente_capaz !== undefined ? activeDoc15.paciente_capaz : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiFileText />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">{selectedFormat.nombre}</h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial15.length} {historial15.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                      {activeDoc15 && (
                                        <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${isNoAutorizado ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'}`}>
                                          {isNoAutorizado ? 'NO AUTORIZADO (DISENTIMIENTO)' : 'AUTORIZADO'}
                                        </span>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      {/* BADGE PACIENTE */}
                                      {summary15.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz15 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : activeDoc15 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz15 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned15 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc15) {
                                              handleOpenAuditModal(firmaDoc15);
                                            }
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary15.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc15 ? (
                                    <>
                                      {isOwner15 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              {/* FIRMA PACIENTE / TESTIGO */}
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-CONSUL-PLT-15',
                                                    tipo_documento: 'Consentimiento para Cesárea (15)',
                                                    title: 'Consentimiento Informado Cesárea (15)',
                                                    slot: activeDoc15.mrnum || 0,
                                                    paciente_capaz: isCapaz15,
                                                    representante_legal: activeDoc15?.representante_legal || activeDoc15?.nombre_tutor || activeDoc15?.tutor,
                                                    parentesco: activeDoc15?.parentesco || activeDoc15?.parentesco_tutor || (isCapaz15 ? 'Paciente' : 'Tutor / Representante Legal')
                                                  }
                                                })}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  summary15.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary15.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary15)}
                                              </button>

                                              {/* FIRMA MÉDICO */}
                                              <button
                                                onClick={() => handleDoctorSign(activeDoc15.mrnum || 0, 'Consentimiento / Disentimiento para Cesárea', JSON.stringify(activeDoc15), 'HE-DIRMED-CONSUL-PLT-15', 'Consentimiento Informado')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned15 
                                                    ? 'he-fmt-btn-plain' 
                                                    : (summary15.hasPaciente ? 'he-fmt-btn-sign' : 'he-fmt-btn-sign')
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary15)}
                                              </button>
                                              <button
                                                onClick={() => handleOpenEditConsent15(activeDoc15)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar
                                              </button>
                                              <button
                                                onClick={handleOpenNewConsent15}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> Capturar Nuevo Formato (Cesárea)
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNewConsent15}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> Capturar Nuevo Formato (Cesárea)
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-15${activeDoc15.mrnum ? `?mrnum=${activeDoc15.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent15}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Formato 15 (Cesárea)
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES */}
                              {historial15.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial15.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial15.map((item, idx) => {
                                      const isSelected = (!selectedMrnum15 && idx === 0) || selectedMrnum15 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum15(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial15.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc15 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Tratante</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor15 || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Diagnóstico Clínico</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{activeDoc15.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Modalidad</span>
                                      <p className={`font-bold text-xs mt-0.5 ${isNoAutorizado ? 'text-red-700' : 'text-emerald-700'}`}>
                                        {isNoAutorizado ? 'NO AUTORIZO (DISENTIMIENTO)' : 'AUTORIZO PROCEDIMIENTO'}
                                      </p>
                                    </div>
                                  </div>

                                  {isNoAutorizado ? (
                                    <div className="p-3.5 bg-red-50/70 rounded-xl border border-red-200 space-y-2 text-xs">
                                      <p className="font-bold text-red-800 uppercase text-[11px]">Motivo por el cual No Acepta la Intervención</p>
                                      <p className="text-slate-800 italic leading-relaxed">
                                        «{activeDoc15.motivo_no_acepto || activeDoc15.motivo_rechazo || 'Decisión personal del paciente / familiar responsable tras recibir información clínica completa.'}»
                                      </p>
                                    </div>
                                  ) : (
                                    <div className="p-3.5 bg-blue-50/50 rounded-xl border border-blue-200 space-y-2 text-xs">
                                      <p className="font-bold text-hes-blue-main uppercase text-[11px]">Procedimiento y Objetivo Autorizado</p>
                                      <p className="text-slate-700 leading-relaxed">
                                        Extracción quirúrgica del feto mediante laparotomía e histerotomía transversa bajo anestesia para resolución segura del embarazo y preservación de la salud materno-fetal conforme a la NOM-004-SSA3-2012.
                                      </p>
                                    </div>
                                  )}

                                  {isSigned15 && (
                                    <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                                      <div className="flex items-center gap-2">
                                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                                          <MdVerifiedUser /> Firmado Digitalmente
                                        </span>
                                        {activeDoc15.signed_on && (
                                          <span className="text-[11px] text-slate-500 font-mono">
                                            {activeDoc15.signed_on}
                                          </span>
                                        )}
                                      </div>
                                      {firmaDoc15 && (
                                        <button 
                                          onClick={() => handleOpenAuditModal(firmaDoc15)} 
                                          className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1 transition-colors"
                                        >
                                          <FiLock /> Sello: {firmaDoc15.sello_digital?.substring(0, 10)}... (Auditar)
                                        </button>
                                      )}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div className="py-8 text-center text-xs text-slate-400 space-y-3">
                                  <p>No se ha registrado el Formato 15 (Cesárea / Disentimiento) para este paciente.</p>
                                  {!isPatientDischarged && (
                                    <button onClick={handleOpenNewConsent15} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                      <FiPlus /> Capturar Formato 15 (Cesárea)
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                                    ) : (selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-07' || selectedFormat?.codigo === '07' || selectedFormat?.codigo === 'PLT-07' || selectedFormat?.codigo === 'CI_PQ') ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial07 = (data?.historial_07 && data.historial_07.length > 0)
                          ? data.historial_07
                          : (data?.consentimiento_07 ? [data.consentimiento_07] : []);

                        const activeDoc07 = (selectedMrnum07 ? historial07.find(h => h.mrnum === selectedMrnum07) : null)
                          || (historial07.length > 0 ? historial07[0] : null)
                          || data?.consentimiento_07;

                        const docDoctor07 = activeDoc07?.medico_tratante || activeDoc07?.n_medico || '';
                        const isOwner07 = canModifyOrSignDocument(docDoctor07);
                        const summary07 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-07', activeDoc07?.mrnum || 0);
                        const firmaDoc07 = summary07.firmaMedico || summary07.allFirmas[0];
                        const isSigned07 = Boolean(activeDoc07?.firmado || activeDoc07?.signed_by || summary07.hasMedico);
                        const isCapaz07 = activeDoc07?.paciente_capaz !== undefined ? activeDoc07.paciente_capaz : isPatientAdult(data?.patient);

                        return (
                          <>
                            {/* HEADER REDISEÑADO ELEGANTE Y COMPACTO */}
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
                                
                                {/* LADO IZQUIERDO: ICONO + TÍTULO + BADGES EN LÍNEA */}
                                <div className="flex items-center gap-3.5">
                                  <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-hes-blue-dark to-hes-blue-main text-white flex items-center justify-center text-xl font-bold shadow-sm shrink-0">
                                    <FiFileText />
                                  </div>
                                  <div className="space-y-1">
                                    <h3 className="font-bold text-slate-900 text-sm sm:text-base leading-tight">
                                      {selectedFormat.nombre}
                                    </h3>
                                    
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md border border-slate-200">
                                        PLT-07
                                      </span>
                                      <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md border border-blue-200">
                                        {historial07.length} {historial07.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                      
                                      {/* BADGE PACIENTE / TUTOR */}
                                      {summary07.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz07 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : activeDoc07 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz07 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned07 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc07) handleOpenAuditModal(firmaDoc07);
                                          }}
                                          className="inline-flex items-center gap-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-emerald-300 transition-colors cursor-pointer"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser className="text-emerald-600" /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary07.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                {/* LADO DERECHO: TOOLBAR DE ACCIONES AGRUPADAS */}
                                <div className="flex items-center gap-2 flex-wrap self-stretch sm:self-auto justify-end">
                                  {activeDoc07 ? (
                                    <>
                                      {/* FIRMA PACIENTE / TESTIGO */}
                                      {!isPatientDischarged && (
                                        <button
                                          type="button"
                                          onClick={() => setPatientSignModal({
                                            open: true,
                                            documentInfo: {
                                              codigo_formato: 'HE-DIRMED-CONSUL-PLT-07',
                                              tipo_documento: 'Consentimiento para Procedimientos Quirúrgicos (07)',
                                              title: 'Consentimiento para Procedimientos Quirúrgicos (07)',
                                              slot: activeDoc07.mrnum || 0,
                                              paciente_capaz: isCapaz07,
                                              representante_legal: activeDoc07?.representante_legal || activeDoc07?.pariente || activeDoc07?.nom_firmante,
                                              parentesco: activeDoc07?.parentesco || (isCapaz07 ? 'El Paciente' : 'Representante Legal')
                                            }
                                          })}
                                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                            summary07.hasPaciente
                                              ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300'
                                              : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                          }`}
                                          title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                        >
                                          <MdFingerprint className={`text-base ${summary07.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                          {patientSignatureLabel(summary07)}
                                        </button>
                                      )}

                                      {/* FIRMA MÉDICO */}
                                      {!isPatientDischarged && (isOwner07 ? (
                                        <button
                                          onClick={() => handleDoctorSign(activeDoc07.mrnum || 0, 'Consentimiento Quirúrgico (Formato 07)', JSON.stringify(activeDoc07), 'HE-DIRMED-CONSUL-PLT-07', 'Consentimiento Informado')}
                                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                            isSigned07 
                                              ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300' 
                                              : (summary07.hasPaciente ? 'he-fmt-btn-sign' : 'he-fmt-btn-sign')
                                          }`}
                                        >
                                          <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary07)}
                                        </button>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-500 border border-slate-200 px-2.5 py-1.5 rounded-xl text-xs font-bold" title="Documento elaborado por otro médico">
                                          <FiLock /> {docDoctor07 ? `Médico: ${docDoctor07}` : 'Bloqueado'}
                                        </span>
                                      ))}

                                      {/* EDITAR */}
                                      {!isPatientDischarged && isOwner07 && (
                                        <button
                                          onClick={() => handleOpenEditConsent07(activeDoc07)}
                                          className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                        >
                                          <FiEdit3 className="text-slate-500" /> Editar
                                        </button>
                                      )}

                                      {/* IMPRIMIR PDF */}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-07${activeDoc07?.mrnum ? `?mrnum=${activeDoc07.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-slate-700 hover:text-hes-blue-main px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                      >
                                        <FiPrinter className="text-slate-500" /> Imprimir PDF
                                      </a>
                                    </>
                                  ) : (
                                    /* IMPRIMIR PDF PREVIA SI NO HAY DOC GUARDADO */
                                    <a
                                      href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-07`}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="flex items-center gap-1 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-slate-700 hover:text-hes-blue-main px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                    >
                                      <FiPrinter className="text-slate-500" /> Imprimir PDF
                                    </a>
                                  )}

                                  {/* NUEVO CONSENTIMIENTO */}
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent07}
                                      className="flex items-center gap-1 he-fmt-btn-new px-3.5 py-1.5 rounded-xl text-xs font-bold shadow-xs transition-all"
                                    >
                                      <FiPlus /> Nuevo Formato (07)
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* CONTENIDO DEL CONSENTIMIENTO 07 */}
                            <div className="p-4 sm:p-6 overflow-y-auto flex-1 space-y-4">
                              {/* SELECTOR DE VERSIONES */}
                              {historial07.length > 1 && (
                                <div className="flex items-center gap-2 pb-3 border-b border-slate-100 overflow-x-auto">
                                  <span className="text-[11px] font-bold text-slate-500 shrink-0">Historial:</span>
                                  <div className="flex gap-1.5">
                                    {historial07.map((item, idx) => {
                                      const isSelected = (activeDoc07?.mrnum === item.mrnum) || (!selectedMrnum07 && idx === 0);
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum07(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial07.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc07 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Tratante</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor07 || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Procedimiento Quirúrgico</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{activeDoc07.procedimiento_quirurgico || 'INTERVENCIÓN QUIRÚRGICA'}</p>
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Descripción y Técnica</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc07.descripcion_procedimiento || 'Sin descripción de técnica registrada.'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Riesgos Inherentes</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc07.riesgos_inherentes || activeDoc07.riesgos || 'Sin riesgos adicionales especificados.'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Beneficios Esperados</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc07.beneficios || 'Sin beneficios adicionales especificados.'}</p>
                                    </div>
                                  </div>

                                  <div className="he-reg-box p-3">
                                    <span className="he-reg-label">Alternativas Terapéuticas</span>
                                    <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc07.alternativas || 'Sin alternativas adicionales especificadas.'}</p>
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center space-y-3">
                                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                                    <FiFileText />
                                  </div>
                                  <h4 className="font-bold text-slate-700 text-sm">Sin registro de Consentimiento Quirúrgico (Formato 07)</h4>
                                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                    Capture la autorización quirúrgica informada para generar el documento oficial conforme a la NOM-004-SSA3-2012.
                                  </p>
                                  <div className="flex items-center justify-center gap-2">
                                    {!isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent07}
                                        className="inline-flex items-center gap-1.5 he-fmt-btn-sign px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                      >
                                        <FiPlus /> Capturar Formato 07 (Quirúrgico)
                                      </button>
                                    )}
                                    <a
                                      href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-07`}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="inline-flex items-center gap-1 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-slate-700 hover:text-hes-blue-main px-4 py-2 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                    >
                                      <FiPrinter className="text-slate-500" /> Vista Previa PDF
                                    </a>
                                  </div>
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>

                  ) : selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-02' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial02 = (data?.historial_02 && data.historial_02.length > 0)
                          ? data.historial_02
                          : (data?.consentimiento_02 ? [data.consentimiento_02] : []);

                        const activeDoc02 = (selectedMrnum02 ? historial02.find(h => h.mrnum === selectedMrnum02) : null)
                          || (historial02.length > 0 ? historial02[0] : null)
                          || data?.consentimiento_02;

                        const docDoctor02 = activeDoc02?.medico_tratante || activeDoc02?.n_medico || '';
                        const isOwner02 = canModifyOrSignDocument(docDoctor02);
                        const summary02 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-02', activeDoc02?.mrnum || 0);
                        const firmaDoc02 = summary02.firmaMedico || summary02.allFirmas[0];
                        const isSigned02 = Boolean(activeDoc02?.firmado || activeDoc02?.signed_by || summary02.hasMedico);
                        const isNoAutorizado = Boolean(activeDoc02?.no_autorizo || activeDoc02?.tipo === 'no_autorizo' || activeDoc02?.motivo_de_no_autorizacion);
                        const isCapaz02 = activeDoc02?.paciente_capaz !== undefined ? activeDoc02.paciente_capaz : isPatientAdult(data?.patient);

                        return (
                          <>
                            {/* HEADER REDISEÑADO ELEGANTE Y COMPACTO */}
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
                                
                                {/* LADO IZQUIERDO: ICONO + TÍTULO + BADGES EN LÍNEA */}
                                <div className="flex items-center gap-3.5">
                                  <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-hes-blue-dark to-hes-blue-main text-white flex items-center justify-center text-xl font-bold shadow-sm shrink-0">
                                    <FiFileText />
                                  </div>
                                  <div className="space-y-1">
                                    <h3 className="font-bold text-slate-900 text-sm sm:text-base leading-tight">
                                      {selectedFormat.nombre}
                                    </h3>
                                    
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md border border-slate-200">
                                        PLT-02
                                      </span>
                                      <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md border border-blue-200">
                                        {historial02.length} {historial02.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                      {activeDoc02 && (
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                                          isNoAutorizado 
                                            ? 'bg-rose-50 text-rose-700 border-rose-200' 
                                            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                        }`}>
                                          {isNoAutorizado ? 'Disentimiento' : 'Autorizado'}
                                        </span>
                                      )}
                                      
                                      {/* BADGE PACIENTE / TUTOR */}
                                      {summary02.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz02 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : activeDoc02 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz02 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned02 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc02) handleOpenAuditModal(firmaDoc02);
                                          }}
                                          className="inline-flex items-center gap-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-emerald-300 transition-colors cursor-pointer"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser className="text-emerald-600" /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary02.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                {/* LADO DERECHO: TOOLBAR DE ACCIONES AGRUPADAS */}
                                <div className="flex items-center gap-2 flex-wrap self-stretch sm:self-auto justify-end">
                                  {activeDoc02 ? (
                                    <>
                                      {/* FIRMA PACIENTE / TESTIGO */}
                                      {!isPatientDischarged && (
                                        <button
                                          type="button"
                                          onClick={() => setPatientSignModal({
                                            open: true,
                                            documentInfo: {
                                              codigo_formato: 'HE-DIRMED-CONSUL-PLT-02',
                                              tipo_documento: 'Consentimiento Quirúrgico (02)',
                                              title: 'Consentimiento Informado Quirúrgico (02)',
                                              slot: activeDoc02.mrnum || 0,
                                              paciente_capaz: isCapaz02,
                                              representante_legal: activeDoc02?.representante_legal || activeDoc02?.paciente_o_representante || activeDoc02?.nom_firmante,
                                              parentesco: activeDoc02?.parentesco || activeDoc02?.parentesco_pac || (isCapaz02 ? 'Paciente' : 'Tutor / Representante Legal')
                                            }
                                          })}
                                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                            summary02.hasPaciente
                                              ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300'
                                              : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                          }`}
                                          title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                        >
                                          <MdFingerprint className={`text-base ${summary02.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                          {patientSignatureLabel(summary02)}
                                        </button>
                                      )}

                                      {/* FIRMA MÉDICO */}
                                      {!isPatientDischarged && (isOwner02 ? (
                                        <button
                                          onClick={() => handleDoctorSign(activeDoc02.mrnum || 0, 'Consentimiento / Disentimiento Quirúrgico', JSON.stringify(activeDoc02), 'HE-DIRMED-CONSUL-PLT-02', 'Consentimiento Informado')}
                                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                            isSigned02 
                                              ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300' 
                                              : (summary02.hasPaciente ? 'he-fmt-btn-sign' : 'he-fmt-btn-sign')
                                          }`}
                                        >
                                          <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary02)}
                                        </button>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-500 border border-slate-200 px-2.5 py-1.5 rounded-xl text-xs font-bold" title="Documento elaborado por otro médico">
                                          <FiLock /> Solo Lectura
                                        </span>
                                      ))}

                                      {/* EDITAR */}
                                      {!isPatientDischarged && isOwner02 && (
                                        <button
                                          onClick={() => handleOpenEditConsent02(activeDoc02)}
                                          className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                        >
                                          <FiEdit3 className="text-slate-500" /> Editar
                                        </button>
                                      )}

                                      {/* IMPRIMIR PDF */}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-02${activeDoc02.mrnum ? `?mrnum=${activeDoc02.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-slate-700 hover:text-hes-blue-main px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                      >
                                        <FiPrinter className="text-slate-500" /> Imprimir PDF
                                      </a>

                                      {/* CAPTURAR NUEVO */}
                                      {!isPatientDischarged && (
                                        <button
                                          onClick={handleOpenNewConsent02}
                                          className="flex items-center gap-1 he-fmt-btn-new px-3.5 py-1.5 rounded-xl text-xs font-bold shadow-xs transition-all"
                                        >
                                          <FiPlus /> Nuevo Formato (02)
                                        </button>
                                      )}
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent02}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-all"
                                      >
                                        <FiPlus /> Capturar Formato 02 (Quirúrgico)
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES */}
                              {historial02.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial02.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial02.map((item, idx) => {
                                      const isSelected = (!selectedMrnum02 && idx === 0) || selectedMrnum02 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum02(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial02.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc02 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Tratante</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor02 || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Diagnóstico Clínico</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{activeDoc02.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Modalidad</span>
                                      <p className={`font-bold text-xs mt-0.5 ${isNoAutorizado ? 'text-red-700' : 'text-emerald-700'}`}>
                                        {isNoAutorizado ? 'NO AUTORIZO (DISENTIMIENTO)' : 'AUTORIZO PROCEDIMIENTO'}
                                      </p>
                                    </div>
                                  </div>

                                  {!isNoAutorizado ? (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                      <div className="he-reg-box p-3">
                                        <span className="he-reg-label">Tratamientos Quirúrgicos</span>
                                        <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc02.tratamientos_quirurgicos || 'Procedimiento quirúrgico indicado'}</p>
                                      </div>
                                      <div className="he-reg-box p-3">
                                        <span className="he-reg-label">Protocolo Anestésico</span>
                                        <p className="text-slate-700 text-xs mt-1 leading-relaxed">
                                          <b>Anestesia:</b> {activeDoc02.anestesia || 'SI'} • <b>Tipo:</b> {activeDoc02.tipo_de_anestesia || 'General balanceada / Bloqueo'}
                                        </p>
                                      </div>
                                    </div>
                                  ) : (
                                    <div className="p-3.5 bg-red-50/70 border border-red-200 rounded-xl">
                                      <span className="text-[10px] font-bold text-red-800 uppercase">Motivo de No Autorización (Disentimiento)</span>
                                      <p className="text-red-900 font-medium text-xs mt-1 italic">«{activeDoc02.motivo_de_no_autorizacion || 'Decisión informada del paciente / familiar responsable.'}»</p>
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div className="py-8 text-center space-y-3">
                                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                                    <FiFileText />
                                  </div>
                                  <h4 className="font-bold text-slate-700 text-sm">Sin registro de Consentimiento Quirúrgico (Formato 02)</h4>
                                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                    Capture la autorización quirúrgica o el disentimiento informado para generar el documento oficial.
                                  </p>
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent02}
                                      className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Formato 02 (Quirúrgico)
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-08' || selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-08/01' || selectedFormat?.codigo === '08') ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial08 = (data?.historial_08 && data.historial_08.length > 0)
                          ? data.historial_08
                          : (data?.consentimiento_08 ? [data.consentimiento_08] : []);

                        const activeDoc08 = (selectedMrnum08 ? historial08.find(h => h.mrnum === selectedMrnum08) : null)
                          || (historial08.length > 0 ? historial08[0] : null)
                          || data?.consentimiento_08;

                        const docDoctor08 = activeDoc08?.medico_tratante || activeDoc08?.n_medico || '';
                        const isOwner08 = canModifyOrSignDocument(docDoctor08);
                        const summary08 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-08', activeDoc08?.mrnum || 0);
                        const firmaDoc08 = summary08.firmaMedico || summary08.allFirmas[0];
                        const isSigned08 = Boolean(activeDoc08?.firmado || activeDoc08?.signed_by || summary08.hasMedico);
                        const isCapaz08 = activeDoc08?.paciente_capaz !== undefined ? activeDoc08.paciente_capaz : isPatientAdult(data?.patient);

                        return (
                          <>
                            {/* HEADER REDISEÑADO ELEGANTE Y COMPACTO */}
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
                                
                                {/* LADO IZQUIERDO: ICONO + TÍTULO + BADGES EN LÍNEA */}
                                <div className="flex items-center gap-3.5">
                                  <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-hes-blue-dark to-hes-blue-main text-white flex items-center justify-center text-xl font-bold shadow-sm shrink-0">
                                    <FiFileText />
                                  </div>
                                  <div className="space-y-1">
                                    <h3 className="font-bold text-slate-900 text-sm sm:text-base leading-tight">
                                      {selectedFormat.nombre}
                                    </h3>
                                    
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md border border-slate-200">
                                        PLT-08
                                      </span>
                                      <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md border border-blue-200">
                                        {historial08.length} {historial08.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                      
                                      {/* BADGE PACIENTE / TUTOR */}
                                      {summary08.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz08 ? 'Paciente' : 'Tutor / Rep.'}: Huella ✔
                                        </span>
                                      ) : activeDoc08 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz08 ? 'Paciente' : 'Tutor / Rep.'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned08 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc08) handleOpenAuditModal(firmaDoc08);
                                          }}
                                          className="inline-flex items-center gap-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold text-[10px] px-2 py-0.5 rounded-md border border-emerald-300 transition-colors cursor-pointer"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser className="text-emerald-600" /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary08.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                {/* LADO DERECHO: TOOLBAR DE ACCIONES AGRUPADAS */}
                                <div className="flex items-center gap-2 flex-wrap self-stretch sm:self-auto justify-end">
                                  {activeDoc08 ? (
                                    <>
                                      {/* FIRMA PACIENTE / TESTIGO */}
                                      {!isPatientDischarged && (
                                        <button
                                          type="button"
                                          onClick={() => setPatientSignModal({
                                            open: true,
                                            documentInfo: {
                                              codigo_formato: 'HE-DIRMED-CONSUL-PLT-08',
                                              tipo_documento: 'Consentimiento Diagnóstico en Admisión Continua (08)',
                                              title: 'Consentimiento Informado Admisión Continua (08)',
                                              slot: activeDoc08.mrnum || 0,
                                              paciente_capaz: isCapaz08,
                                              representante_legal: activeDoc08?.representante_legal || activeDoc08?.nom_autoriza || activeDoc08?.declarante,
                                              parentesco: activeDoc08?.parentesco || (isCapaz08 ? 'Paciente' : 'Tutor / Representante Legal')
                                            }
                                          })}
                                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                            summary08.hasPaciente
                                              ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300'
                                              : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                          }`}
                                          title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                        >
                                          <MdFingerprint className={`text-base ${summary08.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                          {patientSignatureLabel(summary08)}
                                        </button>
                                      )}

                                      {/* FIRMA MÉDICO */}
                                      {!isPatientDischarged && (isOwner08 ? (
                                        <button
                                          onClick={() => handleDoctorSign(activeDoc08.mrnum || 0, 'Consentimiento Informado para Admisión Continua', JSON.stringify(activeDoc08), 'HE-DIRMED-CONSUL-PLT-08', 'Consentimiento Informado')}
                                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                                            isSigned08 
                                              ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300' 
                                              : (summary08.hasPaciente ? 'he-fmt-btn-sign' : 'he-fmt-btn-sign')
                                          }`}
                                        >
                                          <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary08)}
                                        </button>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-500 border border-slate-200 px-2.5 py-1.5 rounded-xl text-xs font-bold" title="Documento elaborado por otro médico">
                                          <FiLock /> Solo Lectura
                                        </span>
                                      ))}

                                      {/* EDITAR */}
                                      {!isPatientDischarged && isOwner08 && (
                                        <button
                                          onClick={() => handleOpenEditConsent08(activeDoc08)}
                                          className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                        >
                                          <FiEdit3 className="text-slate-500" /> Editar
                                        </button>
                                      )}

                                      {/* IMPRIMIR PDF */}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-08${activeDoc08.mrnum ? `?mrnum=${activeDoc08.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-slate-700 hover:text-hes-blue-main px-3 py-1.5 rounded-xl text-xs font-semibold shadow-2xs transition-all"
                                      >
                                        <FiPrinter className="text-slate-500" /> Imprimir PDF
                                      </a>

                                      {/* CAPTURAR NUEVO */}
                                      {!isPatientDischarged && (
                                        <button
                                          onClick={handleOpenNewConsent08}
                                          className="flex items-center gap-1 he-fmt-btn-new px-3.5 py-1.5 rounded-xl text-xs font-bold shadow-xs transition-all"
                                        >
                                          <FiPlus /> Nuevo Formato (08)
                                        </button>
                                      )}
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent08}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-all"
                                      >
                                        <FiPlus /> Capturar Formato 08 (Admisión Continua)
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES */}
                              {historial08.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial08.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial08.map((item, idx) => {
                                      const isSelected = (!selectedMrnum08 && idx === 0) || selectedMrnum08 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum08(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial08.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc08 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Tratante</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor08 || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Diagnóstico Clínico</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{activeDoc08.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Riesgos Inherentes</span>
                                      <p className="font-bold text-amber-700 text-xs mt-0.5">
                                        {activeDoc08.riesgos_inherentes_a_procedimien || activeDoc08.riesgos || 'No especificados'}
                                      </p>
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Procedimientos de Diagnóstico</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc08.procedimientos || 'Sin procedimientos especificados.'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Beneficios Esperados</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc08.beneficios || 'Sin beneficios especificados.'}</p>
                                    </div>
                                  </div>

                                  <div className="he-reg-box p-3">
                                    <span className="he-reg-label">Probables Procedimientos y Alternativas</span>
                                    <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc08.prob_proced_y_alts || activeDoc08.alternativas || 'Sin alternativas especificadas.'}</p>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 1</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc08.testigo1 || activeDoc08.testigo_1 || getDefaultFirmantesForConsent(firmantesList).testigo1 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 2</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc08.testigo2 || activeDoc08.testigo_2 || getDefaultFirmantesForConsent(firmantesList).testigo2 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center space-y-3">
                                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                                    <FiFileText />
                                  </div>
                                  <h4 className="font-bold text-slate-700 text-sm">Sin registro de Consentimiento en Admisión Continua (Formato 08)</h4>
                                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                    Capture el consentimiento informado para procedimientos de diagnóstico y tratamiento en admisión continua.
                                  </p>
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent08}
                                      className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Formato 08 (Admisión Continua)
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (selectedFormat?.codigo === 'HE-DIRMED-SINPRO-PLT-43' || selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-43' || selectedFormat?.codigo === '43') ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial43 = (data?.historial_43 && data.historial_43.length > 0)
                          ? data.historial_43
                          : (data?.consentimiento_43 ? [data.consentimiento_43] : []);

                        const activeDoc43 = (selectedMrnum43 ? historial43.find(h => h.mrnum === selectedMrnum43) : null)
                          || (historial43.length > 0 ? historial43[0] : null)
                          || data?.consentimiento_43;

                        const docDoctor43 = activeDoc43?.medico_tratante || activeDoc43?.n_medico || '';
                        const isOwner43 = canModifyOrSignDocument(docDoctor43);
                        const summary43 = getDocumentSignaturesSummary('HE-DIRMED-SINPRO-PLT-43', activeDoc43?.mrnum || 0);
                        const firmaDoc43 = summary43.firmaMedico || summary43.allFirmas[0];
                        const isSigned43 = Boolean(activeDoc43?.firmado || activeDoc43?.signed_by || summary43.hasMedico);
                        const isCapaz43 = activeDoc43?.paciente_capaz !== undefined ? Boolean(activeDoc43.paciente_capaz) : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiActivity />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">
                                        {selectedFormat.nombre || 'Orden de Intubación Endotraqueal / Soporte Ventilatorio'}
                                      </h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial43.length} {historial43.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      {/* BADGE PACIENTE / DECLARANTE */}
                                      {summary43.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz43 ? 'Paciente' : 'Declarante'}: Huella ✔
                                        </span>
                                      ) : activeDoc43 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz43 ? 'Paciente' : 'Declarante'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned43 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc43) handleOpenAuditModal(firmaDoc43);
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary43.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc43 ? (
                                    <>
                                      {isOwner43 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              {/* FIRMA PACIENTE / TUTOR / TESTIGO */}
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-SINPRO-PLT-43',
                                                    tipo_documento: 'Orden de Intubación Endotraqueal (43)',
                                                    title: 'Orden de Intubación Formato 43',
                                                    slot: activeDoc43.mrnum || 0,
                                                    paciente_capaz: isCapaz43,
                                                    representante_legal: activeDoc43?.representante_legal || activeDoc43?.declarante || activeDoc43?.familiar_responsable,
                                                    parentesco: activeDoc43?.parentesco || activeDoc43?.parentesco_declarante || 'Tutor / Representante Legal'
                                                  }
                                                })}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  summary43.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary43.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary43)}
                                              </button>

                                              {/* FIRMA MÉDICO */}
                                              <button
                                                onClick={() => handleDoctorSign(activeDoc43.mrnum || 0, 'Orden de Intubación Endotraqueal', JSON.stringify(activeDoc43), 'HE-DIRMED-SINPRO-PLT-43', 'Orden de Intubación')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned43 
                                                    ? 'he-fmt-btn-plain' 
                                                    : 'he-fmt-btn-sign'
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary43)}
                                              </button>

                                              {/* EDITAR */}
                                              <button
                                                onClick={() => handleOpenEditConsent43(activeDoc43)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar
                                              </button>

                                              {/* NUEVO */}
                                              <button
                                                onClick={handleOpenNewConsent43}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> Capturar Nueva Orden
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNewConsent43}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> Capturar Nueva Orden
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-43${activeDoc43.mrnum ? `?mrnum=${activeDoc43.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent43}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Orden de Intubación
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* HISTORIAL DE VERSIONES */}
                              {historial43.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial43.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial43.map((item, idx) => {
                                      const isSelected = (!selectedMrnum43 && idx === 0) || selectedMrnum43 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum43(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial43.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc43 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Tratante</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor43 || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Diagnóstico Clínico</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{activeDoc43.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Servicio / Área</span>
                                      <p className="font-bold text-hes-blue-main text-xs mt-0.5">
                                        {activeDoc43.servicio || data?.patient?.area || 'HOSPITALIZACIÓN'}
                                      </p>
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Beneficios Esperados</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc43.beneficios || 'Sin beneficios adicionales especificados.'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Riesgos Inherentes</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc43.riesgos || activeDoc43.principales_riesgos || 'Sin riesgos adicionales especificados.'}</p>
                                    </div>
                                  </div>

                                  <div className="he-reg-box p-3">
                                    <span className="he-reg-label">Alternativas Clínicas</span>
                                    <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc43.alternativas || 'Sin alternativas adicionales especificadas.'}</p>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 1</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc43.testigo1 || activeDoc43.testigo_1 || getDefaultFirmantesForConsent(firmantesList).testigo1 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 2</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc43.testigo2 || activeDoc43.testigo_2 || getDefaultFirmantesForConsent(firmantesList).testigo2 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center space-y-3">
                                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                                    <FiActivity />
                                  </div>
                                  <h4 className="font-bold text-slate-700 text-sm">Sin registro de Orden de Intubación Endotraqueal (Formato 43)</h4>
                                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                    Capture la orden médica y consentimiento informado para intubación endotraqueal y soporte ventilatorio.
                                  </p>
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent43}
                                      className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Formato 43 (Orden de Intubación)
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-06' || selectedFormat?.codigo === '06' || selectedFormat?.codigo === 'PLT-06') ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial06 = (data?.historial_06 && data.historial_06.length > 0)
                          ? data.historial_06
                          : (data?.consentimiento_06 ? [data.consentimiento_06] : []);

                        const activeDoc06 = (selectedMrnum06 ? historial06.find(h => h.mrnum === selectedMrnum06) : null)
                          || (historial06.length > 0 ? historial06[0] : null)
                          || data?.consentimiento_06;

                        const docDoctor06 = activeDoc06?.medico_anestesiologo || activeDoc06?.medico_tratante || activeDoc06?.n_medico || '';
                        const isOwner06 = canModifyOrSignDocument(docDoctor06);
                        const summary06 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-06', activeDoc06?.mrnum || 0);
                        const firmaDoc06 = summary06.firmaMedico || summary06.allFirmas[0];
                        const isSigned06 = Boolean(activeDoc06?.firmado || activeDoc06?.signed_by || summary06.hasMedico);
                        const isCapaz06 = activeDoc06?.paciente_capaz !== undefined ? Boolean(activeDoc06.paciente_capaz) : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiActivity />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">
                                        {selectedFormat.nombre || 'Consentimiento para Procedimiento Anestésico'}
                                      </h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial06.length} {historial06.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      {summary06.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz06 ? 'Paciente' : 'Declarante'}: Huella ✔
                                        </span>
                                      ) : activeDoc06 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz06 ? 'Paciente' : 'Declarante'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {isSigned06 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc06) handleOpenAuditModal(firmaDoc06);
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary06.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc06 ? (
                                    <>
                                      {isOwner06 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-CONSUL-PLT-06',
                                                    tipo_documento: 'Procedimiento Anestésico (06)',
                                                    title: 'Consentimiento Anestésico Formato 06',
                                                    slot: activeDoc06.mrnum || 0,
                                                    paciente_capaz: isCapaz06,
                                                    representante_legal: activeDoc06?.representante_legal || activeDoc06?.declarante || activeDoc06?.pariente,
                                                    parentesco: activeDoc06?.parentesco || 'Tutor / Representante Legal'
                                                  }
                                                })}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  summary06.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary06.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary06)}
                                              </button>

                                              <button
                                                onClick={() => handleDoctorSign(activeDoc06.mrnum || 0, 'Procedimiento Anestésico', JSON.stringify(activeDoc06), 'HE-DIRMED-CONSUL-PLT-06', 'Procedimiento Anestésico')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned06 
                                                    ? 'he-fmt-btn-plain' 
                                                    : 'he-fmt-btn-sign'
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary06)}
                                              </button>

                                              <button
                                                onClick={() => handleOpenEditConsent06(activeDoc06)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar Consentimiento
                                              </button>

                                              <button
                                                onClick={handleOpenNewConsent06}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> Nuevo Consentimiento
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNewConsent06}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> Nuevo Consentimiento
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-06${activeDoc06.mrnum ? `?mrnum=${activeDoc06.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent06}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Consentimiento Anestésico
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {historial06.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial06.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial06.map((item, idx) => {
                                      const isSelected = (!selectedMrnum06 && idx === 0) || selectedMrnum06 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum06(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial06.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc06 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Anestesiólogo</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor06 || currentDoctorName || 'MÉDICO ANESTESIÓLOGO'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Tipo de Cirugía</span>
                                      <p className="font-bold text-hes-blue-main text-xs mt-0.5">
                                        {activeDoc06.tipo_cirugia || 'PROGRAMADA'}
                                      </p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Magnitud de Cirugía</span>
                                      <p className="font-bold text-indigo-700 text-xs mt-0.5">
                                        {activeDoc06.magnitud_cirugia || 'MAYOR'}
                                      </p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Estado Físico A.S.A.</span>
                                      <p className="font-bold text-emerald-700 text-xs mt-0.5">
                                        {activeDoc06.asa || 'CLASE II'}
                                      </p>
                                    </div>
                                  </div>

                                  <div className="he-reg-box p-3">
                                    <span className="he-reg-label">Tipo de Anestesia Indicada</span>
                                    <p className="font-semibold text-slate-800 text-xs mt-1 leading-relaxed">
                                      {activeDoc06.tipo_anestesia || 'ANESTESIA GENERAL BALANCEADA CON INTUBACIÓN OROTRAQUEAL / BLOQUEO NEUROAXIAL'}
                                    </p>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Beneficios de la Anestesia</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc06.beneficios_anestesia || 'Abolición del dolor y sensibilidad táctil, estabilidad hemodinámica y relajación muscular transoperatoria.'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Alternativas Clínicas</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc06.alternativas_anestesia || 'Anestesia neuroaxial pura, sedación consciente monitoreada o anestesia local infiltrativa según técnica.'}</p>
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 1</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc06.testigo1 || activeDoc06.testigo_1 || getDefaultFirmantesForConsent(firmantesList).testigo1 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 2</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc06.testigo2 || activeDoc06.testigo_2 || getDefaultFirmantesForConsent(firmantesList).testigo2 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center space-y-3">
                                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                                    <FiActivity />
                                  </div>
                                  <h4 className="font-bold text-slate-700 text-sm">Sin registro de Consentimiento Anestésico (Formato 06)</h4>
                                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                    Capture el consentimiento informado para autorizar procedimiento anestésico seleccionando el tipo de cirugía, magnitud y clasificación ASA.
                                  </p>
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent06}
                                      className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Formato 06 (Procedimiento Anestésico)
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-11' || selectedFormat?.codigo === '11' || selectedFormat?.codigo === 'PLT-11') ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial11 = (data?.historial_11 && data.historial_11.length > 0)
                          ? data.historial_11
                          : (data?.consentimiento_11 ? [data.consentimiento_11] : []);

                        const activeDoc11 = (selectedMrnum11 ? historial11.find(h => h.mrnum === selectedMrnum11) : null)
                          || (historial11.length > 0 ? historial11[0] : null)
                          || data?.consentimiento_11;

                        const docDoctor11 = activeDoc11?.medico_tratante || activeDoc11?.n_medico || '';
                        const isOwner11 = canModifyOrSignDocument(docDoctor11);
                        const summary11 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-11', activeDoc11?.mrnum || 0);
                        const firmaDoc11 = summary11.firmaMedico || summary11.allFirmas[0];
                        const isSigned11 = Boolean(activeDoc11?.firmado || activeDoc11?.signed_by || summary11.hasMedico);
                        const isCapaz11 = activeDoc11?.paciente_capaz !== undefined ? Boolean(activeDoc11.paciente_capaz) : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiActivity />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">
                                        {selectedFormat.nombre || 'Consentimiento de No Reanimación / Voluntad Anticipada'}
                                      </h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial11.length} {historial11.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      {summary11.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz11 ? 'Paciente' : 'Declarante'}: Huella ✔
                                        </span>
                                      ) : activeDoc11 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz11 ? 'Paciente' : 'Declarante'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {isSigned11 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc11) handleOpenAuditModal(firmaDoc11);
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary11.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc11 ? (
                                    <>
                                      {isOwner11 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-CONSUL-PLT-11',
                                                    tipo_documento: 'Consentimiento No Reanimación (11)',
                                                    title: 'Consentimiento No Reanimación Formato 11',
                                                    slot: activeDoc11.mrnum || 0,
                                                    paciente_capaz: isCapaz11,
                                                    representante_legal: activeDoc11?.representante_legal || activeDoc11?.declarante || activeDoc11?.pariente,
                                                    parentesco: activeDoc11?.parentesco || 'Tutor / Representante Legal'
                                                  }
                                                })}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  summary11.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary11.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary11)}
                                              </button>

                                              <button
                                                onClick={() => handleDoctorSign(activeDoc11.mrnum || 0, 'Consentimiento No Reanimación', JSON.stringify(activeDoc11), 'HE-DIRMED-CONSUL-PLT-11', 'No Reanimación')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned11 
                                                    ? 'he-fmt-btn-plain' 
                                                    : 'he-fmt-btn-sign'
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary11)}
                                              </button>

                                              <button
                                                onClick={() => handleOpenEditConsent11(activeDoc11)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar Consentimiento
                                              </button>

                                              <button
                                                onClick={handleOpenNewConsent11}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> Nuevo Consentimiento
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNewConsent11}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> Nuevo Consentimiento
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-11${activeDoc11.mrnum ? `?mrnum=${activeDoc11.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent11}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Formato 11 (No Reanimación)
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {historial11.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial11.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial11.map((item, idx) => {
                                      const isSelected = (!selectedMrnum11 && idx === 0) || selectedMrnum11 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum11(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial11.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc11 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Tratante</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor11 || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Diagnóstico Clínico</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{activeDoc11.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                    </div>
                                  </div>

                                  <div className="he-reg-box p-3">
                                    <span className="he-reg-label">Beneficios y Riesgos de No Reanimación</span>
                                    <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc11.beneficios_y_riesgos_de_nr || 'Sin especificación adicional.'}</p>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Riesgos de No Aplicar Reanimación</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc11.riesgos_de_no_aplicar || 'Sin especificación adicional.'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Alternativas Bioéticas y Paliativas</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc11.alternativa_nr || 'Sin alternativas adicionales especificadas.'}</p>
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 1</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc11.testigo1 || activeDoc11.testigo_1 || getDefaultFirmantesForConsent(firmantesList).testigo1 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 2</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc11.testigo2 || activeDoc11.testigo_2 || getDefaultFirmantesForConsent(firmantesList).testigo2 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center space-y-3">
                                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                                    <FiActivity />
                                  </div>
                                  <h4 className="font-bold text-slate-700 text-sm">Sin registro de No Reanimación (Formato 11)</h4>
                                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                    Capture el consentimiento informado de no reanimación cardiopulmonar / voluntad anticipada conforme a la normatividad bioética.
                                  </p>
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent11}
                                      className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Formato 11 (No Reanimación)
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-19' || selectedFormat?.codigo === '19' || selectedFormat?.codigo === 'PLT-19') ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial19 = (data?.historial_19 && data.historial_19.length > 0)
                          ? data.historial_19
                          : (data?.consentimiento_19 ? [data.consentimiento_19] : []);

                        const activeDoc19 = (selectedMrnum19 ? historial19.find(h => h.mrnum === selectedMrnum19) : null)
                          || (historial19.length > 0 ? historial19[0] : null)
                          || data?.consentimiento_19;

                        const docDoctor19 = activeDoc19?.medico_tratante || activeDoc19?.n_medico || '';
                        const isOwner19 = canModifyOrSignDocument(docDoctor19);
                        const summary19 = getDocumentSignaturesSummary('HE-DIRMED-CONSUL-PLT-19', activeDoc19?.mrnum || 0);
                        const firmaDoc19 = summary19.firmaMedico || summary19.allFirmas[0];
                        const isSigned19 = Boolean(activeDoc19?.firmado || activeDoc19?.signed_by || summary19.hasMedico);
                        const isCapaz19 = activeDoc19?.paciente_capaz !== undefined ? Boolean(activeDoc19.paciente_capaz) : isPatientAdult(data?.patient);
                        const isNoAutorizo = Boolean(activeDoc19?.no_autorizo || activeDoc19?.tipo === 'no_autorizo' || activeDoc19?.motivo_de_no_autorizacion);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiActivity />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-bold text-slate-800 text-sm">
                                        {selectedFormat.nombre || 'Consentimiento para Histerectomía'}
                                      </h3>
                                      <span className="text-[10px] font-extrabold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                        {historial19.length} {historial19.length === 1 ? 'registro' : 'registros'}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      <span className={`inline-flex items-center gap-1 font-extrabold text-[10px] px-2.5 py-0.5 rounded-full ${
                                        isNoAutorizo ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                      }`}>
                                        {isNoAutorizo ? 'DECISIÓN: NO AUTORIZO' : 'DECISIÓN: AUTORIZO'}
                                      </span>

                                      {summary19.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz19 ? 'Paciente' : 'Declarante'}: Huella ✔
                                        </span>
                                      ) : activeDoc19 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz19 ? 'Paciente' : 'Declarante'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {isSigned19 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc19) handleOpenAuditModal(firmaDoc19);
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary19.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc19 ? (
                                    <>
                                      {isOwner19 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-CONSUL-PLT-19',
                                                    tipo_documento: 'Consentimiento Histerectomía (19)',
                                                    title: 'Consentimiento Histerectomía Formato 19',
                                                    slot: activeDoc19.mrnum || 0,
                                                    paciente_capaz: isCapaz19,
                                                    representante_legal: activeDoc19?.representante_legal || activeDoc19?.declarante || activeDoc19?.pariente,
                                                    parentesco: activeDoc19?.parentesco || 'Tutor / Representante Legal'
                                                  }
                                                })}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  summary19.hasPaciente
                                                    ? 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800'
                                                    : 'bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 hover:text-hes-blue-main hover:border-hes-blue-main'
                                                }`}
                                                title="Firma Dactilar del Paciente, Tutor o Testigos (NOM-004)"
                                              >
                                                <MdFingerprint className={`text-base ${summary19.hasPaciente ? 'text-emerald-700' : 'text-hes-blue-main'}`} />
                                                {patientSignatureLabel(summary19)}
                                              </button>

                                              <button
                                                onClick={() => handleDoctorSign(activeDoc19.mrnum || 0, 'Consentimiento para Histerectomía', JSON.stringify(activeDoc19), 'HE-DIRMED-CONSUL-PLT-19', 'Histerectomía')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned19 
                                                    ? 'he-fmt-btn-plain' 
                                                    : 'he-fmt-btn-sign'
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary19)}
                                              </button>

                                              <button
                                                onClick={() => handleOpenEditConsent19(activeDoc19)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar Consentimiento
                                              </button>

                                              <button
                                                onClick={handleOpenNewConsent19}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> Nuevo Consentimiento
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNewConsent19}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> Nuevo Consentimiento
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-19${activeDoc19.mrnum ? `?mrnum=${activeDoc19.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNewConsent19}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Formato 19 (Histerectomía)
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {historial19.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial19.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial19.map((item, idx) => {
                                      const isSelected = (!selectedMrnum19 && idx === 0) || selectedMrnum19 === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum19(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial19.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc19 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Tratante</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor19 || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Diagnóstico Clínico</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{activeDoc19.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                    </div>
                                  </div>

                                  <div className="he-reg-box p-3">
                                    <span className="he-reg-label">Explicación del Proceso Quirúrgico</span>
                                    <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc19.explicacion_de_proceso || activeDoc19.explicacion || 'Sin explicación quirúrgica adicional registrada.'}</p>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Beneficios del Procedimiento</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc19.beneficios_de_procedimiento || activeDoc19.beneficios || 'Sin beneficios adicionales especificados.'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Intervención Complementaria</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc19.intervencion_complementaria || 'Sin intervenciones complementarias especificadas.'}</p>
                                    </div>
                                  </div>

                                  <div className="he-reg-box p-3">
                                    <span className="he-reg-label">Alternativas Terapéuticas</span>
                                    <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc19.alternativas_terapeuticas || activeDoc19.alternativas || 'Manejo hormonal farmacológico, miomectomía conservadora o dispositivo intrauterino medicado.'}</p>
                                  </div>

                                  {isNoAutorizo && (
                                    <div className="p-3 bg-red-50 rounded-xl border border-red-200">
                                      <span className="text-[10px] font-bold text-red-700 uppercase">Motivo de No Autorización</span>
                                      <p className="text-red-800 text-xs mt-1 leading-relaxed font-semibold">{activeDoc19.motivo_de_no_autorizacion || activeDoc19.motivo_no_acepto || 'No especificado por el paciente/familiar'}</p>
                                    </div>
                                  )}

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 1</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc19.testigo1 || activeDoc19.testigo_1 || getDefaultFirmantesForConsent(firmantesList).testigo1 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 2</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc19.testigo2 || activeDoc19.testigo_2 || getDefaultFirmantesForConsent(firmantesList).testigo2 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center space-y-3">
                                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                                    <FiActivity />
                                  </div>
                                  <h4 className="font-bold text-slate-700 text-sm">Sin registro de Consentimiento para Histerectomía (Formato 19)</h4>
                                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                    Capture el consentimiento informado o decisión de no autorización para procedimiento de histerectomía abdominal o laparoscópica.
                                  </p>
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNewConsent19}
                                      className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Formato 19 (Histerectomía)
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (selectedFormat?.codigo === 'HE-DIRMED-SINPRO-PLT-15' || selectedFormat?.codigo === 'PLT-EV-15' || selectedFormat?.codigo === 'SINPRO-PLT-15' || selectedFormat?.codigo === 'HE-DIRMED-NOTAS-HOS-EV' || selectedFormat?.nombre?.toLowerCase().includes('egreso voluntario')) ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full animate-fadeIn">
                      {(() => {
                        const historial15EV = (data?.historial_15_ev && data.historial_15_ev.length > 0)
                          ? data.historial_15_ev
                          : (data?.egreso_voluntario_15 ? [data.egreso_voluntario_15] : []);

                        const activeDoc15 = (selectedMrnum15EV ? historial15EV.find(h => h.mrnum === selectedMrnum15EV) : null)
                          || (historial15EV.length > 0 ? historial15EV[0] : null)
                          || data?.egreso_voluntario_15;

                        const docDoctor15 = activeDoc15?.medico_tratante || activeDoc15?.n_medico || '';
                        const isOwner15 = canModifyOrSignDocument(docDoctor15);
                        const summary15 = getDocumentSignaturesSummary('HE-DIRMED-SINPRO-PLT-15', activeDoc15?.mrnum || 0);
                        const firmaDoc15EV = summary15.firmaMedico || summary15.allFirmas[0];
                        const isSigned15 = Boolean(activeDoc15?.firmado || activeDoc15?.signed_by || summary15.hasMedico);
                        const isCapaz15 = activeDoc15?.paciente_capaz !== undefined ? Boolean(activeDoc15.paciente_capaz) : isPatientAdult(data?.patient);

                        return (
                          <>
                            <div className="he-fmt-head p-4 sm:p-5 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="he-fmt-head-icon w-10 h-10 text-lg font-bold">
                                    <FiFileText />
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs bg-amber-100 text-amber-800 font-bold px-2.5 py-0.5 rounded-full border border-amber-200">
                                        HE-DIRMED-SINPRO-PLT-15
                                      </span>
                                      <span className="he-det-area">
                                        Egreso Voluntario
                                      </span>
                                    </div>
                                    <h3 className="he-fmt-title">Egreso Voluntario Hospitalario</h3>
                                    <p className="text-xs text-slate-500">Documento formal de alta voluntaria contra recomendación médica (NOM-004-SSA3-2012 / Tabla MR_EV_HOSP).</p>
                                    <div className="flex items-center gap-2 mt-1">
                                      {/* BADGE PACIENTE / DECLARANTE */}
                                      {summary15.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-ok">
                                          <FiCheck className="text-emerald-600" /> {isCapaz15 ? 'Paciente' : 'Declarante'}: Huella ✔
                                        </span>
                                      ) : activeDoc15 ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-pend">
                                          1. {isCapaz15 ? 'Paciente' : 'Declarante'}: Pendiente Huella
                                        </span>
                                      ) : null}

                                      {/* BADGE MÉDICO */}
                                      {isSigned15 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc15EV) handleOpenAuditModal(firmaDoc15EV);
                                          }}
                                          className="inline-flex items-center gap-1 he-fmt-st-ok cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> 2. Médico: Sellado FEA
                                        </button>
                                      ) : summary15.hasPaciente ? (
                                        <span className="inline-flex items-center gap-1 he-fmt-st-next">
                                          2. Listo para Cierre Médico
                                        </span>
                                      ) : null}
                                    </div>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 flex-wrap">
                                  {activeDoc15 ? (
                                    <>
                                      {isOwner15 ? (
                                        <>
                                          {!isPatientDischarged && (
                                            <>
                                              <button
                                                onClick={() => handleDoctorSign(activeDoc15.mrnum || 0, 'Egreso Voluntario', JSON.stringify(activeDoc15), 'HE-DIRMED-SINPRO-PLT-15', 'Egreso Voluntario')}
                                                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                                  isSigned15 
                                                    ? 'he-fmt-btn-plain' 
                                                    : 'he-fmt-btn-sign'
                                                }`}
                                              >
                                                <MdFingerprint className="text-base" /> {doctorSignatureLabel(summary15)}
                                              </button>

                                              <button
                                                type="button"
                                                onClick={() => setPatientSignModal({
                                                  open: true,
                                                  documentInfo: {
                                                    codigo_formato: 'HE-DIRMED-SINPRO-PLT-15',
                                                    tipo_documento: 'Egreso Voluntario',
                                                    title: 'Egreso Voluntario',
                                                    slot: activeDoc15.mrnum || 0,
                                                    paciente_capaz: isCapaz15,
                                                    representante_legal: activeDoc15.declarante || activeDoc15.n_replegal,
                                                    parentesco: activeDoc15.parentesco
                                                  }
                                                })}
                                                className="flex items-center gap-1.5 px-3 py-1.5 he-fmt-btn-plain rounded-lg text-xs font-bold shadow-xs transition-all"
                                                title="Firma del paciente o familiar responsable"
                                              >
                                                <MdFingerprint className="text-base text-emerald-600" /> {patientSignatureLabel(summary15)}
                                              </button>

                                              <button
                                                onClick={() => handleOpenEdit15EV(activeDoc15)}
                                                className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                              >
                                                <FiEdit3 /> Editar
                                              </button>

                                              <button
                                                onClick={handleOpenNew15EV}
                                                className="flex items-center gap-1 he-fmt-btn-new px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                              >
                                                <FiPlus /> + Nuevo Egreso Voluntario
                                              </button>
                                            </>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          {!isPatientDischarged && (
                                            <button
                                              onClick={handleOpenNew15EV}
                                              className="flex items-center gap-1.5 he-fmt-btn-sign px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                            >
                                              <FiPlus /> + Nuevo Egreso Voluntario
                                            </button>
                                          )}
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-egreso-voluntario-15${activeDoc15.mrnum ? `?mrnum=${activeDoc15.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 he-fmt-btn-plain px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    !isPatientDischarged && (
                                      <button
                                        onClick={handleOpenNew15EV}
                                        className="flex items-center gap-1.5 he-fmt-btn-sign px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                      >
                                        <FiPlus /> Capturar Egreso Voluntario (Formato 15)
                                      </button>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>

                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {historial15EV.length > 0 && (
                                <div className="he-reg-hist p-3 space-y-2">
                                  <div className="he-reg-hist-head flex items-center justify-between">
                                    <span>Historial de Registros ({historial15EV.length})</span>
                                    <span className="text-[10px] font-medium text-slate-400">Selecciona un documento para visualizarlo o imprimirlo</span>
                                  </div>
                                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                                    {historial15EV.map((item, idx) => {
                                      const isSelected = (!selectedMrnum15EV && idx === 0) || selectedMrnum15EV === item.mrnum;
                                      return (
                                        <button
                                          key={item.mrnum || idx}
                                          onClick={() => setSelectedMrnum15EV(item.mrnum)}
                                          className={`he-reg-tab ${isSelected ? 'he-reg-tab-active' : ''}`}
                                        >
                                          <span>Doc #{historial15EV.length - idx}</span>
                                          <span className="he-reg-date">
                                            {item.created_on ? item.created_on.split(' ')[0] : 'S/F'}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {activeDoc15 ? (
                                <div className="space-y-3">
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Médico Tratante / Responsable</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{docDoctor15 || currentDoctorName || data?.patient?.attending || 'MÉDICO TRATANTE'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Declarante / Tutor Responsable</span>
                                      <p className="font-bold text-slate-800 text-xs mt-0.5">{activeDoc15.declarante || activeDoc15.n_replegal || 'El Paciente'}</p>
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Diagnóstico de Ingreso</span>
                                      <p className="text-slate-800 font-semibold text-xs mt-0.5">{activeDoc15.diagnostico_ingreso || activeDoc15.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Diagnóstico de Egreso</span>
                                      <p className="text-slate-800 font-semibold text-xs mt-0.5">{activeDoc15.diagnostico_egreso || activeDoc15.diagnostico || data?.patient?.diagnostico || 'SIN DIAGNÓSTICO ESPECIFICADO'}</p>
                                    </div>
                                  </div>

                                  <div className="he-reg-box p-3">
                                    <span className="he-reg-label">Motivo del Egreso Voluntario</span>
                                    <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc15.motivo_egreso || 'Decisión personal y familiar para continuar con la convalecencia y cuidados médicos en domicilio particular.'}</p>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Medidas Recomendadas al Egreso</span>
                                      <p className="text-slate-700 text-xs mt-1 leading-relaxed">{activeDoc15.medidas_recomendadas || 'Continuar con hidratación oral estricta con electrolitos, dieta blanda fraccionada, apego puntual al tratamiento farmacológico prescrito en la receta médica adjunta, reposo relativo en domicilio y control térmico con medios físicos.'}</p>
                                    </div>
                                    <div className="p-3 bg-amber-50 rounded-xl border border-amber-200">
                                      <span className="text-[10px] font-bold text-amber-800 uppercase">Factores de Riesgo Notificados</span>
                                      <p className="text-amber-900 text-xs mt-1 leading-relaxed">{activeDoc15.factores_riesgo || 'Deshidratación severa, desequilibrio hidroelectrolítico, deterioro clínico agudo por omisión de vigilancia intrahospitalaria y necesidad de reingreso urgente a unidad hospitalaria.'}</p>
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 1</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc15.testigo1 || activeDoc15.testigo_1 || getDefaultFirmantesForConsent(firmantesList).testigo1 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                    <div className="he-reg-box p-3">
                                      <span className="he-reg-label">Testigo 2</span>
                                      <p className="text-slate-700 text-xs mt-0.5">{activeDoc15.testigo2 || activeDoc15.testigo_2 || getDefaultFirmantesForConsent(firmantesList).testigo2 || 'Pendiente en Trabajo Social'}</p>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="py-8 text-center space-y-3">
                                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                                    <FiFileText />
                                  </div>
                                  <h4 className="font-bold text-slate-700 text-sm">Sin registro de Egreso Voluntario (Formato 15)</h4>
                                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                    Capture el documento legal de egreso voluntario hospitalario conforme a los lineamientos de la NOM-004-SSA3-2012.
                                  </p>
                                  {!isPatientDischarged && (
                                    <button
                                      onClick={handleOpenNew15EV}
                                      className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Egreso Voluntario (Formato 15)
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (
                    /* TARJETA UNIVERSAL — PLANTILLA PREDEFINIDA FormatoClinicoDetalle (usar para TODOS los futuros formatos) */
                    <FormatoClinicoDetalle
                      formato={selectedFormat}
                      historial={genericFormatHistory}
                      selectedMrnum={selectedGenericMrnum}
                      onSelectMrnum={setSelectedGenericMrnum}
                      loading={loadingGenericHistory}
                      isPatientDischarged={isPatientDischarged}
                      isOwner={(doc) => isAdminOrSistemas || (doc?.medico_tratante && currentDoctorName && (doc.medico_tratante.toLowerCase().includes(currentDoctorName.toLowerCase()) || currentDoctorName.toLowerCase().includes(doc.medico_tratante.toLowerCase())))}
                      onNuevo={handleOpenNewUniversal}
                      onEditar={handleOpenEditUniversal}
                      onFirmarMedico={(mrnum) => {
                        const d = (genericFormatHistory || []).find((x) => x.mrnum === mrnum) || {};
                        handleDoctorSign(mrnum, selectedFormat.nombre, JSON.stringify(d), selectedFormat.codigo, selectedFormat.nombre);
                      }}
                      onFirmaPaciente={(doc) => {
                        const isCapazGeneric = doc?.paciente_capaz !== undefined ? Boolean(doc.paciente_capaz) : isPatientAdult(data?.patient);
                        setPatientSignModal({
                          open: true,
                          documentInfo: {
                            codigo_formato: selectedFormat.codigo,
                            tipo_documento: selectedFormat.nombre,
                            title: selectedFormat.nombre,
                            slot: doc?.mrnum || 0,
                            paciente_capaz: isCapazGeneric,
                            representante_legal: doc?.representante_legal || doc?.pariente || doc?.declarante || doc?.paciente_o_representante,
                            parentesco: doc?.parentesco || doc?.parentesco_declarante || (isCapazGeneric ? 'Paciente' : 'Tutor / Representante Legal')
                          }
                        });
                      }}
                      onVerificar={(doc) => {
                        const summaryUni = getDocumentSignaturesSummary(selectedFormat.codigo, doc?.mrnum || 0);
                        const fUni = summaryUni.firmaMedico || summaryUni.allFirmas[0] || firmas.find((f) => f.codigo_formato === selectedFormat.codigo);
                        handleOpenAuditModal(fUni || { codigo_formato: selectedFormat.codigo, slot: doc?.mrnum || 0, nombre_medico: doc?.signed_by || doc?.medico_tratante });
                      }}
                      getPdfUrl={(doc) => {
                        if (!selectedFormat.url_pdf) return null;
                        if (selectedFormat.url_pdf.startsWith('http')) return selectedFormat.url_pdf;
                        const base = api.defaults.baseURL || '';
                        const sep = selectedFormat.url_pdf.includes('?') ? '&' : '?';
                        return doc?.mrnum ? `${base}${selectedFormat.url_pdf}${sep}mrnum=${doc.mrnum}` : `${base}${selectedFormat.url_pdf}`;
                      }}
                    />
                  )}

                </div>
              ) : (
                /* CASO B: VISTA GENERAL DE CATÁLOGO MAESTRO DE FORMATOS */
                <div className="he-catalog p-6 space-y-6">
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-slate-100">
                    <div className="flex items-start gap-3">
                      <div className="w-11 h-11 rounded-2xl flex items-center justify-center text-xl text-white shrink-0" style={{ background: 'linear-gradient(135deg,#004687,#0088c9)' , boxShadow: '0 8px 18px -8px rgba(0,70,135,0.7)' }}>📋</div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h2 className="he-catalog-title text-lg font-black text-slate-900">Catálogo de Formatos Clínicos</h2>
                          <span className="he-count-badge text-xs font-bold px-2.5 py-0.5 rounded-full">{allFormatos.length} Formatos Activos</span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">Expediente clínico conforme a la norma <strong>NOM-004-SSA3-2012</strong> y Calidad Institucional.</p>
                      </div>
                    </div>

                    {/* BUSCADOR Y FILTRO POR AREA */}
                    <div className="flex flex-col md:items-end gap-2.5 w-full md:w-auto">
                      <div className="relative w-full md:w-72">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <FiSearch className="text-slate-400" />
                        </div>
                        <input
                          type="text"
                          className="he-search block w-full pl-10 pr-3 py-2 text-sm"
                          placeholder="🔍 Buscar formato o código..."
                          value={searchFormatoQuery}
                          onChange={(e) => setSearchFormatoQuery(e.target.value)}
                        />
                      </div>
                      <div className="flex gap-1.5 overflow-x-auto w-full pb-1 md:justify-end md:flex-wrap">
                        {availableAreas.map(area => (
                          <button
                            key={area}
                            onClick={() => setSelectedFormatArea(area)}
                            className={`he-area-pill ${selectedFormatArea === area ? 'he-area-pill-active' : ''} px-3 py-1.5 text-xs whitespace-nowrap transition-colors`}
                          >
                            {area}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* GRID DE TODOS LOS FORMATOS */}
                  <div className="he-grid grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredFormatos.map((fmt, i) => {
                      const areaStyle = getAreaStyle(fmt.area);
                      return (
                      <div 
                        key={i} 
                        className="he-fmt p-5 flex flex-col justify-between cursor-pointer"
                        style={{ '--he-accent': areaStyle.accent, '--he-accent-solid': areaStyle.solid }}
                        onClick={() => setSelectedFormat(fmt)}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-3">
                            <span className="he-fmt-code text-[11px] font-bold px-2 py-1 rounded-lg">
                              {fmt.codigo}
                            </span>
                            {fmt.activo ? (
                              <span className="he-fmt-status text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1.5">
                                <span className="he-fmt-status-dot"></span> Activo / Imprimible
                              </span>
                            ) : (
                              <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
                                En Integración
                              </span>
                            )}
                          </div>
                          
                          <div className="flex items-start gap-3 mb-2">
                            <div className="he-fmt-icon" style={{ background: areaStyle.solid }}>{areaStyle.icon}</div>
                            <h3 className="he-fmt-title font-black text-slate-900 text-[15px] flex-1">{fmt.nombre}</h3>
                          </div>
                          <p className="text-xs text-slate-500 leading-relaxed mb-3 pl-[48px]">{fmt.subtitulo}</p>
                          
                          <div className="he-fmt-meta flex items-center gap-2 text-[11px] text-slate-500 font-medium flex-wrap ml-[48px]">
                            <span className="inline-flex items-center gap-1">🏷️ Área: <strong className="text-slate-700">{fmt.area}</strong></span>
                            <span className="text-slate-300">•</span>
                            <span className="inline-flex items-center gap-1">📄 {fmt.paginas} Pág(s)</span>
                            <span className="text-slate-300">•</span>
                            <span className="inline-flex items-center gap-1">🛡️ {fmt.norma}</span>
                          </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2 pl-[48px]" onClick={e => e.stopPropagation()}>
                          {fmt.activo ? (
                            <div className="flex items-center gap-2 w-full">
                              <button
                                onClick={() => setSelectedFormat(fmt)}
                                className="he-btn-open flex-1 flex items-center justify-center gap-1.5 text-white px-3 py-2.5 text-xs shadow-xs"
                              >
                                <FiEdit3 /> Abrir Formato / Capturar
                              </button>
                              <a
                                href={fmt.url_pdf?.startsWith('/api') ? fmt.url_pdf : `${api.defaults.baseURL}${fmt.url_pdf}`}
                                target="_blank"
                                rel="noreferrer"
                                className="he-btn-pdf flex items-center justify-center gap-1 text-white px-4 py-2.5 text-xs font-bold shadow-xs"
                                title="Imprimir PDF oficial"
                              >
                                <FiDownload /> PDF
                              </a>
                            </div>
                          ) : (
                            <button 
                              onClick={() => setSelectedFormat(fmt)}
                              className="w-full text-center py-2 text-xs font-semibold text-slate-500 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors"
                            >
                              Ver Información del Formato
                            </button>
                          )}
                        </div>
                      </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: MEDICAMENTOS (TABLA MAESTRA PTDG - SQL SERVER) */}
          {activeTab === 'Medicamentos' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex flex-wrap justify-between items-center gap-3 pb-4 border-b border-slate-100">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-black text-slate-800">Medicamentos y Prescripciones</h2>
                    <span className="bg-blue-50 text-hes-blue-main text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-100 flex items-center gap-1">
                      <FiActivity /> Tabla de Medicamentos
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Plan farmacológico y recetas normadas conforme a la <strong>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</strong>.
                  </p>
                </div>
                {!isPatientDischarged && (
                  <button 
                    type="button"
                    onClick={handleOpenPrescriptionModal}
                    className="flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all"
                  >
                    <FiPlus className="text-sm" /> Prescribir Fármaco (Receta)
                  </button>
                )}
              </div>

              {/* LISTADO DE MEDICAMENTOS */}
              <div className="space-y-3">
                {medications && medications.length > 0 ? (
                  medications.map((med, i) => (
                    <div 
                      key={i} 
                      className={`p-5 rounded-2xl border transition-all flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${
                        med.status === 'Activo'
                          ? 'border-slate-200 bg-white hover:border-hes-blue-main/30 hover:shadow-sm'
                          : 'border-slate-200 bg-slate-50/70 opacity-80'
                      }`}
                    >
                      <div className="space-y-1.5 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-black text-slate-800 text-base">{med.name}</span>
                          {med.dose && (
                            <span className="text-xs font-extrabold bg-blue-50 text-hes-blue-main px-2.5 py-0.5 rounded-lg border border-blue-100">
                              {med.dose}
                            </span>
                          )}
                          <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">
                            Vía: {med.route || 'Oral'}
                          </span>
                          {med.prn && (
                            <span className="text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-md">
                              PRN (Por Razón Necesaria)
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
                          <div>Frecuencia: <strong className="text-slate-800">{med.freq || 'Cada 8 horas'}</strong></div>
                          {med.dispense && <div>Surtido: <strong className="text-slate-700">{med.dispense}</strong></div>}
                          {med.date && <div className="text-slate-400">Prescrito: {med.date}</div>}
                        </div>

                        {med.why && (
                          <div className="text-xs text-slate-600">
                            <strong>Indicación / Motivo:</strong> <span className="italic text-slate-700">{med.why}</span>
                          </div>
                        )}

                        {med.instruction && (
                          <p className="text-xs text-slate-500 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                            <strong>Instrucciones:</strong> {med.instruction}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 self-end md:self-center">
                        <span className={`text-xs font-bold px-3 py-1 rounded-full border ${
                          med.status === 'Activo'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-slate-100 text-slate-600 border-slate-200'
                        }`}>
                          {med.status}
                        </span>

                        {!isPatientDischarged && med.status === 'Activo' && med.ptdg_num && (
                          <button
                            type="button"
                            onClick={() => handleOpenDiscontinue(med)}
                            className="text-xs font-bold text-red-600 hover:text-red-700 hover:bg-red-50 px-2.5 py-1 rounded-lg border border-transparent hover:border-red-200 transition-all"
                            title="Suspender o discontinuar este fármaco con huella biométrica"
                          >
                            Suspender
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-8 rounded-2xl border-2 border-dashed border-slate-200 text-center space-y-3 bg-slate-50/50">
                    <div className="w-12 h-12 rounded-2xl bg-blue-50 text-hes-blue-main flex items-center justify-center mx-auto text-2xl">
                      <MdOutlineMedicalServices />
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-bold text-slate-800 text-sm">Sin Medicamentos Prescritos</h4>
                      <p className="text-xs text-slate-500 max-w-md mx-auto">
                        No hay registros farmacológicos activos para este paciente. Prescribe nuevos medicamentos usando la huella biométrica del médico tratante.
                      </p>
                    </div>
                    {!isPatientDischarged && (
                      <button
                        type="button"
                        onClick={handleOpenPrescriptionModal}
                        className="inline-flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all"
                      >
                        <FiPlus /> Prescribir Primer Fármaco
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: DIETAS Y CUIDADOS (MR_SOL_DIET + POSTGRESQL) */}
          {activeTab === 'Dietas y Cuidados' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex flex-wrap justify-between items-center gap-3 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-black text-slate-800">Régimen Dietético y Cuidados de Enfermería</h2>
                    <span className="bg-blue-50 text-hes-blue-main text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-100 flex items-center gap-1">
                      <FiActivity /> Dietas y Cuidados
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Plan nutricional hospitalario y cuidados clínicos de enfermería conforme a la <strong>NOM-004-SSA3-2012</strong>.
                  </p>
                </div>
                {!isPatientDischarged && (
                  <button 
                    type="button"
                    onClick={handleOpenDietModal}
                    className="flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all"
                  >
                    <FiPlus className="text-sm" /> Prescribir Dieta y Cuidados
                  </button>
                )}
              </div>

              {/* DIETA CARD */}
              <div className="p-6 rounded-2xl border border-blue-200 bg-blue-50/20 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-blue-100 pb-3">
                  <span className="text-xs font-black uppercase tracking-wider text-hes-blue-main flex items-center gap-2">
                    <MdOutlineRestaurant className="text-xl text-hes-blue-main" /> Dieta Prescrita
                  </span>
                  <div className="flex items-center gap-2">
                    {dietas.horario && (
                      <span className="text-xs font-semibold bg-white text-slate-600 px-2.5 py-1 rounded-lg border border-slate-200">
                        Horario: <strong>{dietas.horario}</strong>
                      </span>
                    )}
                    <span className={`text-xs font-black px-3 py-1 rounded-full border shadow-sm ${
                      dietas.tipo?.toLowerCase().includes('ayuno')
                        ? 'bg-red-50 text-red-700 border-red-200'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    }`}>
                      {dietas.tipo || 'Ayuno Estricto'}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="space-y-2 bg-white p-3.5 rounded-xl border border-blue-100">
                    <div><strong className="text-slate-700">Fase Clínica:</strong> <span className="text-slate-800">{dietas.fase || 'Valoración hospitalaria'}</span></div>
                    <div><strong className="text-slate-700">Inicio de Régimen:</strong> <span className="text-slate-800">{dietas.inicio || '--'}</span></div>
                    <div><strong className="text-slate-700">Tolerancia Vía Oral:</strong> <span className="text-slate-800">{dietas.tolerancia_via_oral || 'Adecuada'}</span></div>
                  </div>

                  <div className="space-y-2 bg-white p-3.5 rounded-xl border border-blue-100">
                    <div><strong className="text-slate-700">Alergias / Intolerancias:</strong> <span className="text-red-700 font-semibold">{dietas.alergias_alimentarias || 'Ninguna conocida'}</span></div>
                    <div><strong className="text-slate-700">Responsable:</strong> <span className="text-slate-800">{dietas.nutriologo || 'Lic. Nutrición Clínica HES'}</span></div>
                  </div>
                </div>

                <div className="p-3.5 bg-white rounded-xl border border-blue-100 text-xs">
                  <strong className="text-slate-700 block mb-1">Indicación Nutricional Detallada:</strong>
                  <p className="text-slate-600 leading-relaxed">{dietas.indicaciones || 'Nada por vía oral (NVO). Solución Hartmann IV continua.'}</p>
                </div>
              </div>

              {/* CUIDADOS DE ENFERMERIA */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-black text-slate-800 text-sm">Plan de Cuidados de Enfermería</h3>
                  <span className="text-[11px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                    {(cuidados_enfermeria || []).length} Cuidados Asignados
                  </span>
                </div>

                {cuidados_enfermeria && cuidados_enfermeria.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {cuidados_enfermeria.map((c, i) => (
                      <div key={i} className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-white transition-all flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <FiCheckCircle className="text-emerald-600 text-lg shrink-0 mt-0.5" />
                          <div>
                            <div className="font-bold text-slate-800 text-xs">{c.cuidado}</div>
                            <div className="text-[11px] text-slate-500 mt-0.5">Frecuencia: <strong className="text-slate-700">{c.frecuencia}</strong></div>
                          </div>
                        </div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          c.estado === 'Activo' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {c.estado || 'Activo'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-6 text-center bg-slate-50/80 rounded-2xl border border-dashed border-slate-200 space-y-1.5">
                    <FiCheckCircle className="text-2xl text-slate-300 mx-auto" />
                    <div className="text-xs font-bold text-slate-600">Sin plan de cuidados de enfermería asignado</div>
                    <p className="text-[11px] text-slate-400">
                      Presione "+ Prescribir Dieta y Cuidados" para capturar indicaciones específicas de enfermería.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB: CONTACTOS Y RESPONSABLES / PERSONAS AUTORIZADAS PARA FIRMAR */}
          {activeTab === 'Contactos y Responsables' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex flex-wrap justify-between items-center gap-3 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-black text-slate-800">Personas autorizadas para firmar</h2>
                    <span className="bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
                      <FiUsers /> Guardado en el expediente
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Registre a los familiares, responsables o testigos que podrán firmar documentos del paciente.
                  </p>
                </div>
                {!isPatientDischarged && (
                  <div className="flex flex-wrap items-center gap-2">
                    <button 
                      type="button"
                      onClick={() => {
                        setSelectedFirmanteForModal(null);
                        setFirmantesModalOpen(true);
                      }}
                      className="flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all"
                    >
                      <FiPlus className="text-sm" /> Agregar persona
                    </button>
                  </div>
                )}
              </div>

              {firmantesList && firmantesList.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {firmantesList.map((f, idx) => {
                    const badge = getFirmanteBadgeConfig(f.tipo_firmante);
                    return (
                      <div key={f.id || idx} className={`p-5 rounded-2xl border-2 transition-all space-y-3 shadow-xs flex flex-col justify-between ${
                        f.tiene_huella 
                          ? 'border-emerald-200 bg-emerald-50/20 hover:bg-white' 
                          : 'border-amber-300 bg-amber-50/30 hover:bg-white'
                      }`}>
                        <div className="space-y-2">
                          <div className="flex justify-between items-start gap-2">
                            <div>
                              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-md uppercase border inline-block ${badge.style}`}>
                                {badge.label}
                              </span>
                              <h3 className="font-bold text-slate-800 text-sm mt-1.5 uppercase">{f.nombre_completo}</h3>
                              <span className="text-xs text-slate-500 font-medium">Parentesco: <strong>{f.parentesco || 'Familiar'}</strong></span>
                            </div>
                            <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1 border ${
                              f.tiene_huella ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-amber-100 text-amber-800 border-amber-400 animate-pulse'
                            }`}>
                              <MdFingerprint className="text-sm" />
                              {f.tiene_huella ? 'Huella registrada' : 'Falta la huella'}
                            </span>
                          </div>

                          <div className="text-xs space-y-1 text-slate-600 border-t border-slate-100 pt-2 font-normal">
                            {f.identificacion_oficial && (
                              <div className="flex items-center gap-1.5 text-slate-600">
                                <FiCreditCard className="text-slate-400 shrink-0" />
                                <span>ID: <strong>{f.identificacion_oficial}</strong></span>
                              </div>
                            )}
                            {f.telefono && (
                              <div className="flex items-center gap-1.5 text-slate-600">
                                <FiPhone className="text-slate-400 shrink-0" />
                                <span>Tel: {f.telefono}</span>
                              </div>
                            )}
                            {f.domicilio && (
                              <div className="flex items-start gap-1.5 text-slate-500 text-[11px]">
                                <FiMapPin className="text-slate-400 shrink-0 mt-0.5" />
                                <span className="truncate" title={f.domicilio}>{f.domicilio}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        {!isPatientDischarged && (
                          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                            <button
                              type="button"
                              onClick={() => handleDeleteFirmanteFromDashboard(f.id, f.nombre_completo)}
                              className="text-[11px] font-semibold text-rose-500 hover:text-rose-700 hover:underline flex items-center gap-1"
                              title="Eliminar registro"
                            >
                              <FiTrash2 className="text-xs" /> Eliminar
                            </button>

                            {f.tiene_huella ? (
                              <button 
                                type="button"
                                onClick={() => {
                                  setSelectedFirmanteForModal(f);
                                  setFirmantesModalOpen(true);
                                }}
                                className="text-[11px] font-semibold text-slate-500 hover:text-slate-700 hover:underline flex items-center gap-1"
                              >
                                <FiEdit3 className="text-xs" /> Editar datos
                              </button>
                            ) : (
                              <button 
                                type="button"
                                onClick={() => {
                                  setSelectedFirmanteForModal(f);
                                  setFirmantesModalOpen(true);
                                }}
                                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold px-3 py-1.5 rounded-lg shadow-sm transition-all"
                              >
                                <MdFingerprint className="text-sm" /> Registrar huella
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-12 text-center bg-slate-50/80 rounded-2xl border border-dashed border-slate-200 space-y-3">
                  <FiUsers className="text-3xl text-slate-300 mx-auto" />
                  <div className="text-sm font-bold text-slate-700">Aún no hay personas registradas</div>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Agregue a la persona, guarde sus datos y después registre su huella.
                  </p>
                  {!isPatientDischarged && (
                    <button 
                      type="button"
                      onClick={() => {
                        setSelectedFirmanteForModal(null);
                        setFirmantesModalOpen(true);
                      }}
                      className="inline-flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all mt-2"
                    >
                      <MdFingerprint className="text-base text-emerald-300" /> Agregar persona
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: LABORATORIOS */}
          {activeTab === 'Laboratorios' && (
            <div className="he-lab-section p-6 space-y-5">
              <div className="flex justify-between items-center pb-4 border-b border-slate-100 flex-wrap gap-3">
                <div className="flex items-start gap-3">
                  <div className="he-lab-header-icon" style={{ background: 'linear-gradient(135deg,#0e7490,#06b6d4)' }}>🧪</div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-lg font-black text-slate-900 tracking-tight flex items-center gap-2">
                        Estudios de Laboratorio Clínico
                      </h2>
                      <span className="text-[11px] font-black px-2.5 py-0.5 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200">{laboratorios.length} estudios</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">Resultados, parámetros y archivos PDF digitalizados directamente desde <strong>Vertical Medsys</strong>.</p>
                  </div>
                </div>
                {!isPatientDischarged && (
                  <button className="he-btn-view flex items-center gap-1.5 text-white px-4 py-2 text-xs transition-all shadow-sm">
                    <FiPlus /> Solicitar Estudio
                  </button>
                )}
              </div>

              {laboratorios.length === 0 ? (
                <div className="p-10 text-center bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200 space-y-2">
                  <div className="text-4xl">🧪</div>
                  <div className="font-black text-slate-700 text-sm">Sin estudios de laboratorio</div>
                  <div className="text-xs text-slate-400">No se encontraron estudios registrados para este paciente.</div>
                </div>
              ) : (
                <div className="he-grid space-y-4">
                  {laboratorios.map((lab) => {
                    const isPdfOpen = selectedLabPdf?.id === lab.id;
                    const hasPdf = Boolean(lab.url_pdf || lab.tiene_documento);
                    const isDone = lab.estatus === 'Completado' || lab.estatus === 'Reportado';

                    return (
                      <div key={lab.id} className={`he-lab-card ${isPdfOpen ? 'open' : ''} p-5 pl-6 space-y-3`} style={{ '--he-lab-accent': isDone ? 'linear-gradient(180deg,#059669,#00b48a)' : 'linear-gradient(180deg,#f59e0b,#f97316)' }}>
                        <div className="flex justify-between items-start gap-3 flex-wrap">
                          <div className="space-y-1.5 flex-1 min-w-[220px]">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="he-folio-chip text-[11px] font-black px-2.5 py-1 rounded-lg">{lab.id}</span>
                              {hasPdf && (
                                <span className="he-pdf-badge inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-black">
                                  <FiFileText className="text-rose-500" /> PDF Oficial Adjunto
                                </span>
                              )}
                            </div>
                            <h3 className="font-black text-slate-900 text-[16px] tracking-tight">{lab.estudio}</h3>
                            <span className="text-xs text-slate-400 block">
                              🗓️ Solicitado / Registrado: <strong className="text-slate-600">{lab.fecha_solicitud}</strong> • 👨‍⚕️ Por: <strong className="text-slate-600">{lab.solicitado_por}</strong>
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-2 shrink-0">
                            <span className={`he-estatus ${isDone ? 'he-estatus-ok' : 'he-estatus-warn'}`}>
                              <span className="he-estatus-dot"></span>{lab.estatus}
                            </span>
                          </div>
                        </div>

                        <div className="he-result-box p-3.5 text-xs space-y-1.5">
                          <div className="font-bold text-slate-800 flex items-center justify-between gap-2 flex-wrap">
                            <span>📊 Resultado: {lab.resultado_resumen}</span>
                            {lab.tamanio_bytes && (
                              <span className="text-[11px] text-slate-400 font-semibold bg-white px-2 py-0.5 rounded-md border border-slate-200">
                                {(lab.tamanio_bytes / 1024).toFixed(1)} KB
                              </span>
                            )}
                          </div>
                          {lab.valores_criticos && (
                            <div className="text-slate-500 font-medium border-t border-blue-100 pt-1.5">💡 Interpretación: {lab.valores_criticos}</div>
                          )}
                        </div>

                        {/* ACCIONES Y BOTONES DE VISOR PDF */}
                        {hasPdf && (
                          <div className="pt-3 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2.5">
                            <div className="flex items-center gap-2 flex-wrap">
                              <button
                                type="button"
                                onClick={() => handleToggleLabPdf(lab)}
                                disabled={loadingPdfId === lab.id}
                                className={`flex items-center gap-1.5 px-4 py-2.5 text-xs text-white transition-all shadow-sm ${
                                  isPdfOpen ? 'he-btn-hide' : 'he-btn-view'
                                }`}
                              >
                                <FiFileText className="text-sm" />
                                {loadingPdfId === lab.id ? 'Cargando resultado...' : (isPdfOpen ? 'Ocultar resultado' : 'Ver resultado')}
                              </button>

                              <button
                                type="button"
                                onClick={() => handleOpenLabPdfNewTab(lab)}
                                className="he-btn-ghost flex items-center gap-1.5 px-3.5 py-2.5 text-xs transition-all cursor-pointer"
                              >
                                <FiExternalLink className="text-xs" />
                                Abrir en Pestaña Nueva
                              </button>

                              {labPdfBlobs[lab.id] && (
                                <a
                                  href={labPdfBlobs[lab.id]}
                                  download={lab.nombre_archivo || `${lab.id}.pdf`}
                                  className="he-btn-download flex items-center gap-1.5 px-3.5 py-2.5 text-xs transition-all"
                                >
                                  <FiDownload className="text-xs" />
                                  Descargar
                                </a>
                              )}
                            </div>

                            {lab.nombre_archivo && (
                              <span className="he-file-chip text-[11px] text-slate-500 truncate max-w-xs">
                                📎 {lab.nombre_archivo}
                              </span>
                            )}
                          </div>
                        )}

                        {/* VISOR CLÍNICO NATIVO CON ANOTACIONES */}
                        {isPdfOpen && hasPdf && (
                          <div className="mt-3 animate-fadeIn">
                            {loadingPdfId === lab.id ? (
                              <div className="h-[300px] flex flex-col items-center justify-center text-slate-400 text-xs gap-3 bg-white border border-slate-200 rounded-2xl">
                                <div className="w-8 h-8 border-4 border-slate-200 border-t-cyan-600 rounded-full animate-spin"></div>
                                <span>Cargando documento PDF…</span>
                              </div>
                            ) : labPdfBlobs[lab.id] ? (
                              <React.Suspense fallback={<div className="h-[300px] flex items-center justify-center text-slate-400 text-xs bg-white border border-slate-200 rounded-2xl">Cargando visor clínico…</div>}>
                              <div className="he-viewer-frame">
                              <ClinicalPdfViewer
                                fileUrl={labPdfBlobs[lab.id]}
                                docId={`lab-${lab.id}`}
                                title={lab.nombre_archivo || lab.estudio}
                                meta={`PTMT #${lab.ptmt_num || lab.id} · ${lab.fecha_solicitud || ''}`}
                                downloadName={lab.nombre_archivo || `${lab.id}.pdf`}
                                onClose={() => setSelectedLabPdf(null)}
                                onOpenNewTab={() => handleOpenLabPdfNewTab(lab)}
                              />
                              </div>
                              </React.Suspense>
                            ) : (
                              <div className="h-[160px] flex items-center justify-center text-rose-500 text-xs bg-rose-50 border border-rose-200 rounded-2xl">
                                No se pudo renderizar el PDF. Intenta abrirlo en pestaña nueva.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 6: IMAGENOLOGÍA */}
          {activeTab === 'Imagenología' && (
            <div className="he-lab-section p-6 space-y-5">
              <div className="flex justify-between items-center pb-4 border-b border-slate-100 flex-wrap gap-3">
                <div className="flex items-start gap-3">
                  <div className="he-lab-header-icon" style={{ background: 'linear-gradient(135deg,#4f46e5,#06b6d4)' }}>🖼️</div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-lg font-black text-slate-900 tracking-tight">
                        Estudios de Imagenología y Gabinete
                      </h2>
                      <span className="text-[11px] font-black px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">{imagenologia.length} estudios</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">Ultrasonidos, tomografías y radiografías con reporte radiológico digital.</p>
                  </div>
                </div>
                {!isPatientDischarged && (
                  <button className="he-btn-view flex items-center gap-1.5 text-white px-4 py-2 text-xs transition-all shadow-sm">
                    <FiPlus /> Solicitar Imagen
                  </button>
                )}
              </div>

              {imagenologia.length === 0 ? (
                <div className="p-10 text-center bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200 space-y-2">
                  <div className="text-4xl">🖼️</div>
                  <div className="font-black text-slate-700 text-sm">Sin estudios de imagenología</div>
                  <div className="text-xs text-slate-400">No se encontraron estudios de imagen o gabinete registrados para este paciente.</div>
                </div>
              ) : (
                <div className="he-grid space-y-4">
                  {imagenologia.map((img) => {
                    const isPdfOpen = selectedImgPdf?.id === img.id;
                    const hasPdf = Boolean(img.url_pdf || img.tiene_documento);
                    const isDone = img.estatus === 'Completado' || img.estatus === 'Reportado';

                    return (
                      <div key={img.id} className={`he-lab-card ${isPdfOpen ? 'open' : ''} p-5 pl-6 space-y-3`} style={{ '--he-lab-accent': isDone ? 'linear-gradient(180deg,#4f46e5,#06b6d4)' : 'linear-gradient(180deg,#f59e0b,#f97316)' }}>
                        <div className="flex justify-between items-start gap-3 flex-wrap">
                          <div className="space-y-1.5 flex-1 min-w-[220px]">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="he-folio-chip text-[11px] font-black px-2.5 py-1 rounded-lg">{img.id}</span>
                              {hasPdf && (
                                <span className="he-pdf-badge inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-black">
                                  <FiFileText className="text-rose-500" /> Archivo Adjunto
                                </span>
                              )}
                            </div>
                            <h3 className="font-black text-slate-900 text-[16px] tracking-tight">{img.estudio}</h3>
                            <span className="text-xs text-slate-400 block">
                              🗓️ Solicitado / Registrado: <strong className="text-slate-600">{img.fecha_solicitud}</strong> • 👨‍⚕️ Por: <strong className="text-slate-600">{img.solicitado_por}</strong>
                            </span>
                          </div>
                          <span className={`he-estatus ${isDone ? 'he-estatus-ok' : 'he-estatus-warn'} shrink-0`}>
                            <span className="he-estatus-dot"></span>{img.estatus}
                          </span>
                        </div>

                        <div className="he-result-box p-3.5 text-xs space-y-2">
                          {img.hallazgos && (
                            <div>
                              <strong className="block mb-1 text-[11px] uppercase tracking-wide">🔍 Hallazgos Radiológicos:</strong>
                              <p className="text-slate-600 leading-relaxed">{img.hallazgos}</p>
                            </div>
                          )}
                          {img.conclusion && (
                            <div className="he-conclusion font-bold text-xs">
                              ✅ Conclusión: {img.conclusion}
                            </div>
                          )}
                          {img.resultado_resumen && !img.hallazgos && (
                            <div className="text-slate-700 font-bold">{img.resultado_resumen}</div>
                          )}
                        </div>

                        {hasPdf && (
                          <div className="pt-3 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2.5">
                            <div className="flex items-center gap-2 flex-wrap">
                              <button
                                type="button"
                                onClick={() => handleToggleImgPdf(img)}
                                disabled={loadingImgPdfId === img.id}
                                className={`flex items-center gap-1.5 px-4 py-2.5 text-xs text-white transition-all shadow-sm ${
                                  isPdfOpen ? 'he-btn-hide' : 'he-btn-view'
                                }`}
                              >
                                <FiFileText className="text-sm" />
                                {loadingImgPdfId === img.id ? 'Cargando resultado...' : (isPdfOpen ? 'Ocultar resultado' : 'Ver resultado')}
                              </button>

                              <button
                                type="button"
                                onClick={() => handleOpenImgPdfNewTab(img)}
                                className="he-btn-ghost flex items-center gap-1.5 px-3.5 py-2.5 text-xs transition-all cursor-pointer"
                              >
                                <FiExternalLink className="text-xs" />
                                Abrir en Pestaña Nueva
                              </button>

                              {imgPdfBlobs[img.id] && (
                                <a
                                  href={imgPdfBlobs[img.id]}
                                  download={img.nombre_archivo || `${img.id}.pdf`}
                                  className="he-btn-download flex items-center gap-1.5 px-3.5 py-2.5 text-xs transition-all"
                                >
                                  <FiDownload className="text-xs" />
                                  Descargar
                                </a>
                              )}
                            </div>

                            {img.nombre_archivo && (
                              <span className="he-file-chip text-[11px] text-slate-500 truncate max-w-xs">
                                📎 {img.nombre_archivo}
                              </span>
                            )}
                          </div>
                        )}

                        {/* VISOR CLÍNICO NATIVO CON ANOTACIONES */}
                        {isPdfOpen && hasPdf && (
                          <div className="mt-3 animate-fadeIn">
                            {loadingImgPdfId === img.id ? (
                              <div className="h-[300px] flex flex-col items-center justify-center text-slate-400 text-xs gap-3 bg-white border border-slate-200 rounded-2xl">
                                <div className="w-8 h-8 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></div>
                                <span>Cargando documento PDF…</span>
                              </div>
                            ) : imgPdfBlobs[img.id] ? (
                              <React.Suspense fallback={<div className="h-[300px] flex items-center justify-center text-slate-400 text-xs bg-white border border-slate-200 rounded-2xl">Cargando visor clínico…</div>}>
                              <div className="he-viewer-frame">
                              <ClinicalPdfViewer
                                fileUrl={imgPdfBlobs[img.id]}
                                docId={`img-${img.id}`}
                                title={img.nombre_archivo || img.estudio}
                                meta={`Imagenología · ${img.fecha_solicitud || ''}`}
                                downloadName={img.nombre_archivo || `${img.id}.pdf`}
                                onClose={() => setSelectedImgPdf(null)}
                                onOpenNewTab={() => handleOpenImgPdfNewTab(img)}
                              />
                              </div>
                              </React.Suspense>
                            ) : (
                              <div className="h-[160px] flex items-center justify-center text-rose-500 text-xs bg-rose-50 border border-rose-200 rounded-2xl">
                                No se pudo renderizar el PDF. Intenta abrirlo en pestaña nueva.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 7: AGENDA Y CITAS */}
          {activeTab === 'Agenda y Citas' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Citas Programadas y Seguimiento</h2>
                  <p className="text-xs text-slate-500">Próximas valoraciones médicas y control ambulatorio.</p>
                </div>
                <a 
                  href="/agenda"
                  className="flex items-center gap-1 bg-hes-blue-main text-white px-3.5 py-2 rounded-xl text-xs font-bold hover:bg-hes-blue-dark transition-all"
                >
                  <FiPlus /> Abrir Agenda Médica
                </a>
              </div>

              <div className="space-y-3">
                {proximas_citas.map((c) => (
                  <div key={c.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-blue-50 text-hes-blue-main rounded-xl font-bold text-center min-w-[70px]">
                        <div className="text-xs">{c.fecha}</div>
                        <div className="text-sm font-extrabold">{c.hora}</div>
                      </div>
                      <div>
                        <h4 className="font-bold text-slate-800 text-sm">{c.motivo}</h4>
                        <div className="text-xs text-slate-500">Médico: <strong className="text-slate-700">{c.medico}</strong> ({c.especialidad})</div>
                        <div className="text-xs text-slate-400 mt-0.5">Lugar: {c.lugar}</div>
                      </div>
                    </div>
                    <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                      {c.estatus}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* RIGHT SIDEBAR: REAL-TIME PATIENT CHARGES & ORDERS SUMMARY */}
        <div className="w-full xl:w-[340px] flex flex-col gap-5">
          
          {/* CHARGES & ACTIVE REQUESTS CARD */}
          <div className="he-side-card p-5 space-y-4">
            <h3 className="font-black text-slate-900 text-sm flex items-center gap-2 pb-3 border-b border-slate-100">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-sm" style={{ background: 'linear-gradient(135deg,#004687,#0088c9)' }}><FiLayers /></span> Resumen de Solicitudes y Cargos
            </h3>

            {/* DIETA ACTIVA */}
            <div className="he-diet-box p-3.5 rounded-xl border border-slate-100">
              <div className="text-[10px] font-black text-slate-500 uppercase tracking-[0.12em] flex items-center gap-1.5">🍽️ Dieta Actual</div>
              <div className="font-black text-slate-900 text-[15px] mt-1">{cargos_solicitudes.dieta_activa || 'Ayuno'}</div>
              <div className="text-[11px] text-red-600 font-bold mt-0.5 flex items-center gap-1">⛔ NVO / Solución IV</div>
            </div>

            {/* COUNTERS (INTERACTIVOS CON ACCESO DIRECTO) */}
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => setActiveTab('Laboratorios')}
                className="he-counter p-3.5 bg-gradient-to-b from-blue-50 to-white border border-blue-100 hover:border-blue-300 hover:shadow-sm rounded-2xl text-center cursor-pointer transition-all group"
                title="Hacer clic para ver Estudios de Laboratorio"
              >
                <div className="he-num text-2xl font-black group-hover:scale-105 transition-transform text-blue-900">
                  🧪 {laboratorios?.length ?? cargos_solicitudes.laboratorios_count ?? 0}
                </div>
                <div className="text-[10px] font-black text-slate-600 uppercase tracking-wide mt-0.5">Labs Solicitados</div>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('Imagenología')}
                className="he-counter p-3.5 bg-gradient-to-b from-teal-50 to-white border border-teal-100 hover:border-teal-300 hover:shadow-sm rounded-2xl text-center cursor-pointer transition-all group"
                title="Hacer clic para ver Estudios de Imagenología"
              >
                <div className="he-num text-2xl font-black group-hover:scale-105 transition-transform text-teal-900">
                  🖼️ {imagenologia?.length ?? cargos_solicitudes.imagenologia_count ?? 0}
                </div>
                <div className="text-[10px] font-black text-slate-600 uppercase tracking-wide mt-0.5">Estudios Imagen</div>
              </button>
            </div>

            {/* PENDING ITEMS */}
            <div>
              <div className="text-[10px] font-black text-slate-500 uppercase tracking-[0.12em] mb-2 flex items-center gap-1.5">📡 Seguimiento en Curso</div>
              {cargos_solicitudes.solicitudes_pendientes && cargos_solicitudes.solicitudes_pendientes.length > 0 ? (
                <div className="space-y-1.5 text-xs">
                  {cargos_solicitudes.solicitudes_pendientes.map((s, i) => (
                    <div 
                      key={i} 
                      onClick={() => setActiveTab(s.tipo === 'Imagenología' ? 'Imagenología' : 'Laboratorios')}
                      className="he-track-item flex justify-between items-center p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-100 cursor-pointer transition-colors"
                      title="Clic para ver detalle"
                    >
                      <span className="font-bold text-slate-700 flex items-center gap-1.5 truncate max-w-[190px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block shrink-0"></span>
                        <span className="truncate">{s.titulo}</span>
                      </span>
                      <span className={`text-[10px] font-black px-2 py-0.5 rounded-full border shrink-0 ${
                        s.estado === 'Completado' || s.estado === 'Reportado' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}>
                        {s.estado}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 text-center rounded-xl bg-slate-50/70 border border-dashed border-slate-200 text-slate-400 text-[11px] font-medium">
                  Sin estudios en proceso
                </div>
              )}
            </div>

            {/* PROXIMA CITA */}
            {cargos_solicitudes.proxima_cita && (
              <div className="p-3.5 rounded-xl text-xs border border-purple-200" style={{ background: 'linear-gradient(135deg,#faf5ff,#f5f3ff)' }}>
                <div className="text-[10px] font-black text-purple-700 uppercase tracking-[0.12em] flex items-center gap-1.5">📅 Próxima Valoración</div>
                <div className="font-black text-slate-900 mt-1 text-sm">{cargos_solicitudes.proxima_cita.fecha} {cargos_solicitudes.proxima_cita.hora}</div>
                <div className="text-slate-500 text-[11px] mt-0.5">👨‍⚕️ {cargos_solicitudes.proxima_cita.medico}</div>
              </div>
            )}
          </div>

          {/* QUICK ACTIONS CARD */}
          <div className="he-side-card p-5 space-y-2.5">
            <h3 className="font-black text-slate-900 text-sm mb-1 flex items-center gap-2">⚡ Acciones Rápidas</h3>
            
            {!isPatientDischarged && (
              <button
                onClick={() => handleOpenNewEvol(evoluciones.evolucion2 ? 3 : (evoluciones.evolucion1 ? 2 : 1))}
                className="he-quick w-full flex items-center gap-3 p-3 border border-hes-blue-main/30 bg-blue-50/40 hover:bg-hes-blue-main hover:text-white transition-all text-left group"
              >
                <div className="p-2.5 bg-hes-blue-main text-white rounded-xl group-hover:bg-white group-hover:text-hes-blue-main transition-colors shadow-sm"><FiEdit3 className="text-lg" /></div>
                <div>
                  <div className="font-black text-hes-blue-main text-[13px] group-hover:text-white">Nueva Evolución</div>
                  <div className="text-[11px] text-slate-500 group-hover:text-blue-100">Capturar SOAP turno actual</div>
                </div>
              </button>
            )}

            <a 
              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-expediente-completo`} 
              target="_blank" 
              rel="noreferrer"
              className="he-quick w-full flex items-center gap-3 p-3 border border-emerald-500/40 bg-gradient-to-r from-emerald-50/70 to-teal-50/70 hover:from-emerald-600 hover:to-teal-700 hover:text-white transition-all text-left group shadow-2xs"
            >
              <div className="p-2.5 bg-emerald-600 text-white rounded-xl group-hover:bg-white group-hover:text-emerald-700 transition-colors shadow-sm"><FiLayers className="text-lg" /></div>
              <div>
                <div className="font-black text-emerald-900 text-[13px] group-hover:text-white">Expediente Completo (PDF)</div>
                <div className="text-[11px] text-emerald-700 group-hover:text-emerald-100">Compilado Integral Oficial NOM-004</div>
              </div>
            </a>

            <a 
              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
              target="_blank" 
              rel="noreferrer"
              className="he-quick w-full flex items-center gap-3 p-3 border border-slate-200 bg-slate-50/50 hover:bg-slate-700 hover:text-white transition-all text-left group"
            >
              <div className="p-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl group-hover:bg-white group-hover:text-slate-800 transition-colors shadow-sm"><FiFileText className="text-lg" /></div>
              <div>
                <div className="font-black text-slate-800 text-[13px] group-hover:text-white">Nota de Urgencias</div>
                <div className="text-[11px] text-slate-500 group-hover:text-slate-200">Formato 87/01 Oficial</div>
              </div>
            </a>

            <button 
              onClick={() => {
                setSelectedFormat(null);
                setActiveTab('Formatos Clínicos');
              }}
              className="he-quick w-full flex items-center gap-3 p-3 border border-slate-100 hover:border-hes-blue-main hover:bg-blue-50/30 transition-all text-left group bg-white"
            >
              <div className="p-2.5 bg-slate-100 text-slate-600 rounded-xl group-hover:bg-hes-blue-main group-hover:text-white transition-colors"><FiFolder className="text-lg" /></div>
              <div>
                <div className="font-black text-slate-800 text-[13px] group-hover:text-hes-blue-main">Catálogo de Formatos</div>
                <div className="text-[11px] text-slate-500">+100 Formatos Oficiales</div>
              </div>
            </button>

            <a 
              href="/agenda"
              className="he-quick w-full flex items-center gap-3 p-3 border border-slate-100 hover:border-purple-500 hover:bg-purple-50/30 transition-all text-left group bg-white"
            >
              <div className="p-2.5 bg-slate-100 text-slate-600 rounded-xl group-hover:bg-purple-600 group-hover:text-white transition-colors"><FiCalendar className="text-lg" /></div>
              <div>
                <div className="font-black text-slate-800 text-[13px] group-hover:text-purple-600">Agenda Médica</div>
                <div className="text-[11px] text-slate-500">Programar visitas / citas</div>
              </div>
            </a>
          </div>

        </div>

      </div>

      {/* MODAL DE FIRMA BIOMÉTRICA (NOM-004-SSA3-2012 / NOM-024-SSA3-2012) */}
      {signingModal.open && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full p-6 text-center space-y-4 overflow-hidden">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-hes-blue-main uppercase tracking-wide flex items-center gap-1.5">
                <FiShield /> Firma médica con huella
              </span>
              <button 
                onClick={() => {
                  setSigningModal(prev => ({ ...prev, open: false }));
                  dpStopCapture();
                }}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                <FiX />
              </button>
            </div>

            <div>
              <h3 className="font-bold text-slate-800 text-base">{signingModal.title}</h3>
              <p className="text-xs text-slate-500 mt-0.5">Presione el botón y coloque su dedo en el lector.</p>
            </div>

            {/* SENSOR ANIMADO INTERACTIVO */}
            <div className="py-4 flex flex-col items-center justify-center">
              <button
                type="button"
                onClick={() => {
                  if (!signingModal.submitting && !signingModal.successMsg) {
                    dpResetFmd();
                    dpStartCapture({
                      action: 'FIRMA_MEDICA', patientRef: patientId,
                      documentCode: signingModal.codigoFormato || 'HE-DIRMED-SINPRO-PLT-87/01',
                      documentRef: signingModal.slot || 0
                    });
                  }
                }}
                disabled={signingModal.submitting || !!signingModal.successMsg}
                title={dpAcquiring ? "Sensor activo: coloque su dedo sobre el lector" : "Haga clic para activar el sensor de huella"}
                className={`w-32 h-32 rounded-full border-4 flex items-center justify-center relative transition-all ${
                  signingModal.successMsg 
                    ? 'border-emerald-500 bg-emerald-50 text-emerald-600 cursor-default' 
                    : dpAcquiring 
                    ? 'border-hes-blue-main bg-blue-50/60 text-hes-blue-main animate-pulse shadow-lg shadow-blue-200 cursor-pointer' 
                    : 'border-slate-200 bg-slate-50 text-slate-400 hover:border-hes-blue-main hover:text-hes-blue-main cursor-pointer'
                }`}
              >
                {dpAcquiring && (
                  <div className="absolute inset-0 rounded-full border-2 border-hes-blue-main animate-ping opacity-25"></div>
                )}
                {signingModal.successMsg ? (
                  <MdVerifiedUser className="text-6xl text-emerald-600" />
                ) : (
                  <MdFingerprint className="text-6xl" />
                )}
              </button>

              <div className="mt-4 w-full px-1 sm:px-2">
                {signingModal.successMsg ? (
                  <div className="w-full p-3 bg-emerald-50 rounded-xl border border-emerald-200 shadow-sm space-y-2">
                    <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-emerald-700 text-center">
                      <FiCheckCircle className="shrink-0" />
                      <span>Firma guardada correctamente</span>
                    </div>
                  </div>
                ) : signingModal.submitting ? (
                  <div className="text-xs font-bold text-hes-blue-main text-center animate-pulse">Guardando la firma...</div>
                ) : dpAcquiring ? (
                  <div className="text-xs font-bold text-emerald-700 text-center animate-pulse">Coloque su dedo en el lector...</div>
                ) : (
                  <div className="text-xs font-bold text-slate-600 text-center">{friendlyReaderStatus(dpStatus)}</div>
                )}
              </div>

              {signingModal.errorMsg && (
                <div className="mt-3 p-2.5 bg-red-50 text-red-700 rounded-xl text-xs font-semibold border border-red-200 w-full break-words text-left">
                  {friendlyBiometricError(signingModal.errorMsg)}
                </div>
              )}
              {dpError && !signingModal.errorMsg && (
                <div className="mt-3 p-2.5 bg-amber-50 text-amber-800 rounded-xl text-xs font-semibold border border-amber-200 w-full break-words text-left">
                  {friendlyBiometricError(dpError)}
                </div>
              )}
            </div>

            <div className="text-[11px] text-slate-500 bg-slate-50 p-2.5 rounded-xl border border-slate-100 text-left">
              La firma quedará guardada en el expediente con la fecha, hora e identidad del médico.
            </div>

            <div className="pt-2 flex justify-center gap-3">
              <button 
                onClick={() => {
                  setSigningModal(prev => ({ ...prev, open: false }));
                  dpStopCapture();
                }}
                className="px-5 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                Cerrar
              </button>
              {!signingModal.successMsg && (
                <button 
                  onClick={() => {
                    dpResetFmd();
                    dpStartCapture({
                      action: 'FIRMA_MEDICA', patientRef: patientId,
                      documentCode: signingModal.codigoFormato || 'HE-DIRMED-SINPRO-PLT-87/01',
                      documentRef: signingModal.slot || 0
                    });
                  }}
                  className="px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-xs flex items-center gap-1.5 cursor-pointer"
                >
                  <MdFingerprint className="text-base" />
                  {dpAcquiring ? 'Intentar de nuevo' : 'Leer huella'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL DE CAPTURA / EDICIÓN DE NOTA DE EVOLUCIÓN (SOAP) */}
      {notaModal.open && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            
            {/* MODAL HEADER */}
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-blue-50 text-hes-blue-main font-bold px-2.5 py-0.5 rounded border border-blue-100">
                    {notaModal.formato_codigo || 'HE-DIRMED-SINPRO-PLT-87/01'}
                  </span>
                  <h3 className="text-lg font-bold text-slate-800">
                    {notaModal.isEdit ? `Editar Evolución ${notaModal.evolution_num}` : `Capturar Nueva Evolución ${notaModal.evolution_num}`} {notaModal.formato_codigo === 'HE-DIRMED-CONSUL-PLT-24' ? '(Hospitalización)' : '(Urgencias)'}
                  </h3>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">Paciente: <strong>{patient.name}</strong> • Expediente: <strong>{patient.mrn}</strong></p>
              </div>
              <button 
                onClick={() => setNotaModal(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold p-1"
              >
                <FiX />
              </button>
            </div>

            <form onSubmit={handleSaveNota} className="space-y-4">
              
              {/* SLOT, FECHA, HORA, TURNO */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Evolución Slot *</label>
                  <div className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-hes-blue-main flex items-center justify-between">
                    <span>Evolución {notaModal.evolution_num} {notaModal.evolution_num > 1 ? '(Continuación)' : '(Inicial)'}</span>
                    <span className="text-[10px] text-slate-400 font-normal">Consecutivo</span>
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Fecha *</label>
                  <input 
                    type="date" 
                    value={notaModal.fecha}
                    onChange={(e) => setNotaModal({ ...notaModal, fecha: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Hora *</label>
                  <input 
                    type="time" 
                    value={notaModal.hora}
                    onChange={(e) => setNotaModal({ ...notaModal, hora: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Turno *</label>
                  <select 
                    value={notaModal.turno}
                    onChange={(e) => setNotaModal({ ...notaModal, turno: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-semibold"
                  >
                    <option value="Matutino">Matutino</option>
                    <option value="Vespertino">Vespertino</option>
                    <option value="Nocturno">Nocturno</option>
                  </select>
                </div>
              </div>

              {/* SIGNOS VITALES */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500 block">Signos Vitales del Turno</span>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-xs">
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">TA (mmHg)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_ta} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_ta: e.target.value })}
                      placeholder="120/80" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">FC (lpm)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_fc} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_fc: e.target.value })}
                      placeholder="80" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">FR (rpm)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_fr} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_fr: e.target.value })}
                      placeholder="18" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">SatO2 (%)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_sato2} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_sato2: e.target.value })}
                      placeholder="98" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">Temp (°C)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_temp} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_temp: e.target.value })}
                      placeholder="36.5" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500">Peso (kg)</label>
                    <input 
                      type="text" 
                      value={notaModal.vitals_peso} 
                      onChange={(e) => setNotaModal({ ...notaModal, vitals_peso: e.target.value })}
                      placeholder="78.5" 
                      className="w-full border border-slate-200 bg-white rounded-lg px-2 py-1 text-xs font-semibold"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIONES SOAP */}
              <div className="space-y-3 text-xs">
                
                {/* SUBJETIVO */}
                <div>
                  <label className="block font-bold text-hes-blue-main uppercase mb-1">
                    (S) Subjetivo * (Interrogatorio, síntomas y estado referido por el paciente)
                  </label>
                  <textarea 
                    value={notaModal.subjetivo}
                    onChange={(e) => setNotaModal({ ...notaModal, subjetivo: e.target.value })}
                    placeholder="Ej. Paciente refiere dolor abdominal de 12 horas de evolución..."
                    className="w-full border border-slate-200 rounded-xl p-3 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                    rows={3}
                    required
                  />
                </div>

                {/* OBJETIVO */}
                <div>
                  <label className="block font-bold text-hes-blue-main uppercase mb-1">
                    (O) Objetivo (Exploración física, signos, hallazgos clínicos)
                  </label>
                  <textarea 
                    value={notaModal.objetivo}
                    onChange={(e) => setNotaModal({ ...notaModal, objetivo: e.target.value })}
                    placeholder="Ej. Abdomen blando, doloroso a la palpación en FID, McBurney positivo..."
                    className="w-full border border-slate-200 rounded-xl p-3 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                    rows={3}
                  />
                </div>

                {/* ANÁLISIS */}
                <div>
                  <label className="block font-bold text-hes-blue-main uppercase mb-1">
                    (A) Análisis / Valoración (Juicio diagnóstico y estado clínico)
                  </label>
                  <textarea 
                    value={notaModal.analisis}
                    onChange={(e) => setNotaModal({ ...notaModal, analisis: e.target.value })}
                    placeholder="Ej. Cuadro clínico compatible con abdomen agudo secundario a probable apendicitis..."
                    className="w-full border border-slate-200 rounded-xl p-3 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                    rows={2}
                  />
                </div>

                {/* PLAN */}
                <div>
                  <label className="block font-bold text-hes-blue-main uppercase mb-1">
                    (P) Plan Terapéutico (Laboratorios solicitados y tratamientos a establecer)
                  </label>
                  <textarea 
                    value={notaModal.plan}
                    onChange={(e) => setNotaModal({ ...notaModal, plan: e.target.value })}
                    placeholder="Ej. 1. Ayuno.\n2. Solución Hartmann 1000cc para 8 hrs.\n3. Solicitar BH, QS, EGO y USG abdominal..."
                    className="w-full border border-slate-200 rounded-xl p-3 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                    rows={3}
                  />
                </div>

              </div>

              {/* FIRMA / MÉDICO ASIGNADO */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-2">
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Médico Responsable *</label>
                    <input 
                      type="text" 
                      value={notaModal.medico}
                      onChange={(e) => setNotaModal({ ...notaModal, medico: e.target.value })}
                      className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800 focus:border-hes-blue-main"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Cédula Profesional *</label>
                    <input 
                      type="text" 
                      value={notaModal.cedula}
                      onChange={(e) => setNotaModal({ ...notaModal, cedula: e.target.value })}
                      className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800 focus:border-hes-blue-main"
                      required
                    />
                  </div>
                </div>

                {/* TOGGLE / CHECKBOX PARA MIP / RESIDENTE */}
                <div className="pt-2 border-t border-slate-200/80">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={notaModal.has_mip || false}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setNotaModal(prev => ({
                          ...prev,
                          has_mip: checked,
                          mip: checked ? (prev.mip || '') : ''
                        }));
                      }}
                      className="rounded text-hes-blue-main focus:ring-hes-blue-light h-4 w-4"
                    />
                    <span className="text-xs font-bold text-slate-700">
                      ¿Participa Médico Interno de Pregrado (MIP) o Residente?
                    </span>
                    <span className="text-[10px] text-slate-400 font-normal">
                      (Si se activa, el documento solicitará e imprimirá las 2 firmas; si se desactiva, solo 1 firma del médico)
                    </span>
                  </label>

                  {notaModal.has_mip && (
                    <div className="mt-2.5 pl-6">
                      <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">
                        Nombre Completo del MIP / Residente *
                      </label>
                      <input
                        type="text"
                        value={notaModal.mip || ''}
                        onChange={(e) => setNotaModal({ ...notaModal, mip: e.target.value })}
                        placeholder="Ej: MIP CARLOS ALBERTO PEREZ GOMEZ"
                        className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800 focus:border-hes-blue-main"
                        required={notaModal.has_mip}
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* MODAL FOOTER */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button 
                  type="button"
                  onClick={() => setNotaModal(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  disabled={savingNota}
                  className="px-6 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition-all flex items-center gap-1.5"
                >
                  <FiSave /> {savingNota ? 'Guardando...' : (notaModal.isEdit ? 'Actualizar Evolución' : 'Guardar Evolución')}
                </button>
              </div>

            </form>

          </div>
        </div>
      )}

      {/* MODAL DE HISTORIAL DE SIGNOS VITALES */}
      {vitalsHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div
            className="he-hist-card bg-white w-full p-5 md:p-6 shadow-2xl space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-100 text-[#0f2a4e] rounded-xl">
                  <FiClock className="text-xl" />
                </div>
                <div>
                  <h3 className="text-[17px] font-bold text-slate-900 tracking-tight">Historial de signos vitales</h3>
                  <p className="text-xs text-slate-500">
                    Expediente: <strong className="text-slate-700">PT-{patientId}</strong> • Registro inmutable de tomas por enfermería y médicos
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  type="button"
                  onClick={() => {
                    setVitalsHistoryModal(prev => ({ ...prev, open: false }));
                    handleOpenVitalsModal();
                  }}
                  className="he-btn-navy flex items-center gap-1.5 px-3 py-1.5 text-xs shadow-sm transition"
                >
                  <FiPlus /> Nueva Toma
                </button>
                <button 
                  type="button" 
                  onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))} 
                  className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <FiX className="text-xl" />
                </button>
              </div>
            </div>

            {/* CUERPO CON TABLA */}
            <div className="flex-1 overflow-y-auto">
              {vitalsHistoryModal.loading ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hes-blue-main"></div>
                  <span className="text-xs font-medium">Cargando historial de signos vitales...</span>
                </div>
              ) : vitalsHistoryModal.history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <FiActivity className="text-4xl text-slate-300" />
                  <p className="text-sm font-bold text-slate-600">No hay registros de signos vitales previos</p>
                  <p className="text-xs text-slate-400">Las tomas de signos vitales que registres aparecerán en este historial cronológico.</p>
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-200 rounded-2xl shadow-sm">
                  <table className="he-hist-table w-full text-left text-[13px]">
                      <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-3.5">Fecha y Hora</th>
                        <th className="py-3 px-3">Capturado Por</th>
                        <th className="py-3 px-3 text-center">TA (mmHg)</th>
                        <th className="py-3 px-3 text-center">FC (lpm)</th>
                        <th className="py-3 px-3 text-center">FR (rpm)</th>
                        <th className="py-3 px-3 text-center">Sat O2</th>
                        <th className="py-3 px-3 text-center">Temp (°C)</th>
                        <th className="py-3 px-3 text-center">Peso / Talla</th>
                        <th className="py-3 px-3 text-center">IMC</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {vitalsHistoryModal.history.map((row, idx) => {
                        const sys = parseInt(row.sistolica);
                        const dia = parseInt(row.diastolica);
                        const fc = parseInt(row.fc);
                        const sat = parseInt(row.sat_o2);
                        const temp = parseFloat(row.temperatura);
                        const pesoN = parseFloat(row.peso);
                        const tallaN = parseFloat(row.talla);
                        const imcN = parseFloat(row.imc);

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 92;
                        const isSatWarn = sat && sat >= 92 && sat < 95;
                        const isFever = temp && temp >= 37.5;
                        const fmtTemp = (row.temperatura === '--' || isNaN(temp)) ? '--' : temp.toFixed(1);
                        const fmtPeso = (row.peso === '--' || isNaN(pesoN)) ? '--' : (Number.isInteger(pesoN) ? String(pesoN) : String(Math.round(pesoN * 10) / 10));
                        const fmtTalla = (row.talla === '--' || isNaN(tallaN)) ? '--' : tallaN.toFixed(2);
                        const fmtImc = (row.imc === '--' || row.imc == null || isNaN(imcN)) ? '--' : imcN.toFixed(1);

                        return (
                          <tr key={row.id || idx} className="hover:bg-blue-50/40 transition-colors">
                            <td className="py-2.5 px-3.5 whitespace-nowrap font-bold text-slate-800">
                              <span className="flex items-center gap-1.5">
                                <FiClock className="text-hes-blue-main shrink-0" />
                                {row.fecha_hora}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-lg text-sm font-semibold">
                                <FiUser className="text-slate-400" /> {row.capturado_por}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isTaAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFcAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isSatLow ? 'he-hist-bad' : isSatWarn ? 'he-hist-warn' : 'he-hist-ok'}`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFever ? 'he-hist-bad' : 'text-slate-800'}`}>
                                {fmtTemp}{fmtTemp !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-[12.5px]">
                              {fmtPeso !== '--' ? `${fmtPeso} kg` : '--'} / {fmtTalla !== '--' ? `${fmtTalla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="he-hist-pill he-hist-mute">
                                 {fmtImc}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="flex justify-between items-center pt-3 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                Total de tomas registradas: <strong className="text-slate-800">{vitalsHistoryModal.history.length}</strong>
              </span>
              <button
                type="button"
                onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold transition shadow-sm"
              >
                Cerrar Historial
              </button>
            </div>

          </div>
        </div>
      )}

      {/* MODAL DE CAPTURA / EDICIÓN DE CONSENTIMIENTO INFORMADO (32/01) */}
      {consentModalEED.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setConsentModalEED({ ...consentModalEED, open: false })}></div>
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
            <div className="bg-hes-blue-main text-white px-5 py-4 flex items-center justify-between shrink-0">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <FiActivity />
                {consentModalEED.isEdit ? 'Editar Ecocardiograma de Estrés' : 'Capturar Ecocardiograma de Estrés'}
              </h3>
              <button onClick={() => setConsentModalEED({ ...consentModalEED, open: false })} className="text-white/80 hover:text-white transition-colors">
                <FiX size={24} />
              </button>
            </div>
            
            <form onSubmit={handleSaveConsentModalEED} className="overflow-y-auto p-5 grow bg-slate-50 space-y-6">
                
                <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
                    <h4 className="text-sm font-bold text-hes-blue-main mb-3">Datos Generales</h4>
                    <div className="space-y-3 mb-3">
                      {isPatientAdult(data?.patient || patient) ? (
                        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                          <div className="flex items-center justify-between">
                            <label className="flex items-center gap-2 cursor-pointer select-none">
                              <input
                                type="checkbox"
                                checked={consentModalEED.paciente_capaz}
                                onChange={(e) => setConsentModalEED({ ...consentModalEED, paciente_capaz: e.target.checked, responsable: e.target.checked ? (data?.patient?.name || patient?.name || '') : '' })}
                                className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main cursor-pointer"
                              />
                              <span className="text-xs font-bold text-slate-800">
                                ¿El paciente puede otorgar consentimiento y firmar por sí mismo? (Mayor de edad)
                              </span>
                            </label>
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                              Mayor de edad ({data?.patient?.age || patient?.age || '—'} años)
                            </span>
                          </div>

                          {consentModalEED.paciente_capaz ? (
                            <div className="text-[11px] text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                              <span>✓</span>
                              <span>Se asignará automáticamente al paciente (<b>{data?.patient?.name || patient?.name}</b>) en la firma legal.</span>
                            </div>
                          ) : (
                            <FamiliarSelectorSection
                              label="Nombre del Familiar / Tutor / Representante Legal (Obligatorio):"
                              value={consentModalEED.responsable}
                              onChangeValue={(val) => setConsentModalEED(prev => ({ ...prev, responsable: val }))}
                              firmantesList={firmantesList}
                              required={!consentModalEED.paciente_capaz}
                              placeholder="Nombre completo del familiar o representante legal responsable"
                            />
                          )}
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label={`Padre, Madre, Tutor o Representante Legal (Paciente menor de edad: ${data?.patient?.age || patient?.age || '—'} años):`}
                          value={consentModalEED.responsable}
                          onChangeValue={(val) => setConsentModalEED(prev => ({ ...prev, responsable: val }))}
                          firmantesList={firmantesList}
                          required={true}
                          placeholder="Nombre completo del padre, madre o tutor responsable"
                        />
                      )}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                        <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">TA</label>
                            <input type="text" value={consentModalEED.ta} onChange={e => setConsentModalEED({...consentModalEED, ta: e.target.value})} className="w-full px-3 py-2 border rounded-lg text-sm" />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">FC META</label>
                            <input type="text" value={consentModalEED.fc_meta} onChange={e => setConsentModalEED({...consentModalEED, fc_meta: e.target.value})} className="w-full px-3 py-2 border rounded-lg text-sm" />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">FR</label>
                            <input type="text" value={consentModalEED.fr} onChange={e => setConsentModalEED({...consentModalEED, fr: e.target.value})} className="w-full px-3 py-2 border rounded-lg text-sm" />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <label className="block text-[10px] font-semibold text-slate-700 mb-1">Peso</label>
                                <input type="text" value={consentModalEED.peso} onChange={e => setConsentModalEED({...consentModalEED, peso: e.target.value})} className="w-full px-2 py-2 border rounded-lg text-sm" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold text-slate-700 mb-1">Talla</label>
                                <input type="text" value={consentModalEED.talla} onChange={e => setConsentModalEED({...consentModalEED, talla: e.target.value})} className="w-full px-2 py-2 border rounded-lg text-sm" />
                            </div>
                        </div>
                    </div>
                </div>

                <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 overflow-x-auto">
                    <h4 className="text-sm font-bold text-hes-blue-main mb-3">Monitoreo Hemodinámico</h4>
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-slate-100 text-xs text-slate-700">
                            <tr>
                                <th className="px-3 py-2 rounded-tl-lg">Etapa</th>
                                <th className="px-3 py-2">TA</th>
                                <th className="px-3 py-2">FC</th>
                                <th className="px-3 py-2">SO2 %</th>
                                <th className="px-3 py-2 rounded-tr-lg">Síntomas</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {['basal', '5mcg', '10mcg', '20mcg', '30mcg', '40mcg', 'antropina'].map(stage => (
                                <tr key={stage}>
                                    <td className="px-3 py-2 font-semibold text-slate-600 capitalize">{stage === 'antropina' ? 'Atropina' : stage}</td>
                                    <td className="px-2 py-1"><input value={consentModalEED[`ta_${stage}`]} onChange={e => setConsentModalEED({...consentModalEED, [`ta_${stage}`]: e.target.value})} className="w-16 border rounded px-2 py-1 text-xs"/></td>
                                    <td className="px-2 py-1"><input value={consentModalEED[`fc_${stage}`]} onChange={e => setConsentModalEED({...consentModalEED, [`fc_${stage}`]: e.target.value})} className="w-16 border rounded px-2 py-1 text-xs"/></td>
                                    <td className="px-2 py-1"><input value={consentModalEED[`so2_${stage}`]} onChange={e => setConsentModalEED({...consentModalEED, [`so2_${stage}`]: e.target.value})} className="w-16 border rounded px-2 py-1 text-xs"/></td>
                                    <td className="px-2 py-1"><input value={consentModalEED[`s_${stage}`]} onChange={e => setConsentModalEED({...consentModalEED, [`s_${stage}`]: e.target.value})} className="w-full border rounded px-2 py-1 text-xs"/></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <h5 className="text-xs font-bold text-hes-blue-main mt-4 mb-2">Recuperación</h5>
                    <table className="w-full text-left text-sm">
                        <tbody className="divide-y divide-slate-100">
                            {['2min', '4min'].map(stage => (
                                <tr key={stage}>
                                    <td className="px-3 py-2 font-semibold text-slate-600">{stage}</td>
                                    <td className="px-2 py-1"><input value={consentModalEED[`ta_${stage}`]} onChange={e => setConsentModalEED({...consentModalEED, [`ta_${stage}`]: e.target.value})} className="w-16 border rounded px-2 py-1 text-xs"/></td>
                                    <td className="px-2 py-1"><input value={consentModalEED[`fc_${stage}`]} onChange={e => setConsentModalEED({...consentModalEED, [`fc_${stage}`]: e.target.value})} className="w-16 border rounded px-2 py-1 text-xs"/></td>
                                    <td className="px-2 py-1"><input value={consentModalEED[`so2_${stage}`]} onChange={e => setConsentModalEED({...consentModalEED, [`so2_${stage}`]: e.target.value})} className="w-16 border rounded px-2 py-1 text-xs"/></td>
                                    <td className="px-2 py-1"><input value={consentModalEED[`sintomas_${stage}`]} onChange={e => setConsentModalEED({...consentModalEED, [`sintomas_${stage}`]: e.target.value})} className="w-full border rounded px-2 py-1 text-xs"/></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
                    <label className="block text-sm font-bold text-hes-blue-main mb-2">Comentarios / Incidencias</label>
                    <textarea value={consentModalEED.comentarios} onChange={e => setConsentModalEED({...consentModalEED, comentarios: e.target.value})} rows="3" className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Escriba aquí los comentarios..."></textarea>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                    <button type="button" onClick={() => setConsentModalEED({ ...consentModalEED, open: false })} className="px-4 py-2 rounded-xl text-slate-600 font-bold hover:bg-slate-200">
                        Cancelar
                    </button>
                    <button type="submit" disabled={consentModalEED.saving} className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-xl font-bold">
                        {consentModalEED.saving ? 'Guardando...' : 'Guardar Formato'}
                    </button>
                </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL DE HISTORIAL DE SIGNOS VITALES */}
      {vitalsHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div
            className="he-hist-card bg-white w-full p-5 md:p-6 shadow-2xl space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-100 text-[#0f2a4e] rounded-xl">
                  <FiClock className="text-xl" />
                </div>
                <div>
                  <h3 className="text-[17px] font-bold text-slate-900 tracking-tight">Historial de signos vitales</h3>
                  <p className="text-xs text-slate-500">
                    Expediente: <strong className="text-slate-700">PT-{patientId}</strong> • Registro inmutable de tomas por enfermería y médicos
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  type="button"
                  onClick={() => {
                    setVitalsHistoryModal(prev => ({ ...prev, open: false }));
                    handleOpenVitalsModal();
                  }}
                  className="he-btn-navy flex items-center gap-1.5 px-3 py-1.5 text-xs shadow-sm transition"
                >
                  <FiPlus /> Nueva Toma
                </button>
                <button 
                  type="button" 
                  onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))} 
                  className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <FiX className="text-xl" />
                </button>
              </div>
            </div>

            {/* CUERPO CON TABLA */}
            <div className="flex-1 overflow-y-auto">
              {vitalsHistoryModal.loading ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hes-blue-main"></div>
                  <span className="text-xs font-medium">Cargando historial de signos vitales...</span>
                </div>
              ) : vitalsHistoryModal.history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <FiActivity className="text-4xl text-slate-300" />
                  <p className="text-sm font-bold text-slate-600">No hay registros de signos vitales previos</p>
                  <p className="text-xs text-slate-400">Las tomas de signos vitales que registres aparecerán en este historial cronológico.</p>
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-200 rounded-2xl shadow-sm">
                  <table className="he-hist-table w-full text-left text-[13px]">
                      <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-3.5">Fecha y Hora</th>
                        <th className="py-3 px-3">Capturado Por</th>
                        <th className="py-3 px-3 text-center">TA (mmHg)</th>
                        <th className="py-3 px-3 text-center">FC (lpm)</th>
                        <th className="py-3 px-3 text-center">FR (rpm)</th>
                        <th className="py-3 px-3 text-center">Sat O2</th>
                        <th className="py-3 px-3 text-center">Temp (°C)</th>
                        <th className="py-3 px-3 text-center">Peso / Talla</th>
                        <th className="py-3 px-3 text-center">IMC</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {vitalsHistoryModal.history.map((row, idx) => {
                        const sys = parseInt(row.sistolica);
                        const dia = parseInt(row.diastolica);
                        const fc = parseInt(row.fc);
                        const sat = parseInt(row.sat_o2);
                        const temp = parseFloat(row.temperatura);
                        const pesoN = parseFloat(row.peso);
                        const tallaN = parseFloat(row.talla);
                        const imcN = parseFloat(row.imc);

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 92;
                        const isSatWarn = sat && sat >= 92 && sat < 95;
                        const isFever = temp && temp >= 37.5;
                        const fmtTemp = (row.temperatura === '--' || isNaN(temp)) ? '--' : temp.toFixed(1);
                        const fmtPeso = (row.peso === '--' || isNaN(pesoN)) ? '--' : (Number.isInteger(pesoN) ? String(pesoN) : String(Math.round(pesoN * 10) / 10));
                        const fmtTalla = (row.talla === '--' || isNaN(tallaN)) ? '--' : tallaN.toFixed(2);
                        const fmtImc = (row.imc === '--' || row.imc == null || isNaN(imcN)) ? '--' : imcN.toFixed(1);

                        return (
                          <tr key={row.id || idx} className="hover:bg-blue-50/40 transition-colors">
                            <td className="py-2.5 px-3.5 whitespace-nowrap font-bold text-slate-800">
                              <span className="flex items-center gap-1.5">
                                <FiClock className="text-hes-blue-main shrink-0" />
                                {row.fecha_hora}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-lg text-sm font-semibold">
                                <FiUser className="text-slate-400" /> {row.capturado_por}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isTaAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFcAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isSatLow ? 'he-hist-bad' : isSatWarn ? 'he-hist-warn' : 'he-hist-ok'}`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFever ? 'he-hist-bad' : 'text-slate-800'}`}>
                                {fmtTemp}{fmtTemp !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-[12.5px]">
                              {fmtPeso !== '--' ? `${fmtPeso} kg` : '--'} / {fmtTalla !== '--' ? `${fmtTalla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="he-hist-pill he-hist-mute">
                                 {fmtImc}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="flex justify-between items-center pt-3 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                Total de tomas registradas: <strong className="text-slate-800">{vitalsHistoryModal.history.length}</strong>
              </span>
              <button
                type="button"
                onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold transition shadow-sm"
              >
                Cerrar Historial
              </button>
            </div>

          </div>
        </div>
      )}

      {consentModal3201.open && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            
            {/* MODAL HEADER */}
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-blue-50 text-hes-blue-main font-bold px-2.5 py-0.5 rounded border border-blue-100">HE-DIRMED-CONSUL-PLT-32/01</span>
                  <h3 className="text-lg font-bold text-slate-800">
                    {consentModal3201.isEdit ? 'Editar Consentimiento Informado' : 'Capturar Consentimiento Informado'}
                  </h3>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">Paciente: <strong>{data?.patient?.name}</strong> • Expediente: <strong>{data?.patient?.mrn}</strong></p>
              </div>
              <button 
                onClick={() => setConsentModal3201(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold p-1"
              >
                <FiX />
              </button>
            </div>

            {/* ADVERTENCIA NOM-024 SI ES EDICIÓN */}
            {consentModal3201.isEdit && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2">
                <span className="text-base leading-none">⚠️</span>
                <div>
                  <strong>Aviso de Integridad (NOM-024-SSA3-2012):</strong>
                  <p className="text-[11px] mt-0.5">Al modificar y guardar cambios en este documento, cualquier firma electrónica o huella previa quedará revocada automáticamente para preservar la inmutabilidad legal.</p>
                </div>
              </div>
            )}

            <form onSubmit={handleSaveConsentModal3201} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                <div className="sm:col-span-2 space-y-3">
                  {isPatientAdult(data?.patient || patient) ? (
                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={consentModal3201.paciente_capaz}
                            onChange={(e) => setConsentModal3201({ ...consentModal3201, paciente_capaz: e.target.checked, tipo_interrogatorio: e.target.checked ? 'Directo' : 'Indirecto', representante_legal: e.target.checked ? '' : consentModal3201.representante_legal })}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main cursor-pointer"
                          />
                          <span className="text-xs font-bold text-slate-800">
                            ¿El paciente puede otorgar consentimiento y firmar por sí mismo? (Mayor de edad)
                          </span>
                        </label>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          Mayor de edad ({data?.patient?.age || patient?.age || '—'} años)
                        </span>
                      </div>

                      {consentModal3201.paciente_capaz ? (
                        <div className="text-[11px] text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                          <span>✓</span>
                          <span>Se asignará automáticamente al paciente (<b>{data?.patient?.name || patient?.name}</b>) en la firma legal.</span>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar / Tutor / Representante Legal (Obligatorio):"
                          value={consentModal3201.representante_legal}
                          onChangeValue={(val) => setConsentModal3201(prev => ({ ...prev, representante_legal: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal3201.paciente_capaz}
                          placeholder="Nombre completo del familiar o representante legal responsable"
                        />
                      )}
                    </div>
                  ) : (
                    <FamiliarSelectorSection
                      label={`Padre, Madre, Tutor o Representante Legal (Paciente menor de edad: ${data?.patient?.age || patient?.age || '—'} años):`}
                      value={consentModal3201.representante_legal}
                      onChangeValue={(val) => setConsentModal3201(prev => ({ ...prev, representante_legal: val }))}
                      firmantesList={firmantesList}
                      required={true}
                      placeholder="Nombre completo del padre, madre o tutor responsable"
                    />
                  )}
                </div>

                {/* TESTIGOS SELECTOR Y CAMPOS */}
                <div className="sm:col-span-2 space-y-2">
                  {firmantesList && firmantesList.length > 0 && (
                    <div className="p-2 bg-blue-50/70 border border-blue-200 rounded-xl flex items-center justify-between gap-2 flex-wrap text-xs">
                      <span className="font-bold text-blue-900 flex items-center gap-1">
                        <FiUsers className="text-hes-blue-main" /> Testigos del expediente:
                      </span>
                      <div className="flex items-center gap-2">
                        <select
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val) {
                              const found = firmantesList.find(f => f.id === parseInt(val, 10));
                              if (found) setConsentModal3201(prev => ({ ...prev, testigo1: found.nombre_completo }));
                            }
                          }}
                          defaultValue=""
                          className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                        >
                          <option value="">-- Cargar Testigo 1 --</option>
                          {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                        </select>
                        <select
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val) {
                              const found = firmantesList.find(f => f.id === parseInt(val, 10));
                              if (found) setConsentModal3201(prev => ({ ...prev, testigo2: found.nombre_completo }));
                            }
                          }}
                          defaultValue=""
                          className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                        >
                          <option value="">-- Cargar Testigo 2 --</option>
                          {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                        </select>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 1 (Nombre Completo) *</label>
                      <input 
                        type="text" 
                        value={consentModal3201.testigo1}
                        onChange={(e) => setConsentModal3201({ ...consentModal3201, testigo1: e.target.value })}
                        className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                        placeholder="Nombre completo de Testigo 1"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 2 (Nombre Completo) *</label>
                      <input 
                        type="text" 
                        value={consentModal3201.testigo2}
                        onChange={(e) => setConsentModal3201({ ...consentModal3201, testigo2: e.target.value })}
                        className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                        placeholder="Nombre completo de Testigo 2"
                        required
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* MODAL FOOTER */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button 
                  type="button"
                  onClick={() => setConsentModal3201(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  disabled={consentModal3201.saving}
                  className="px-6 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition-all flex items-center gap-1.5"
                >
                  <FiSave /> {consentModal3201.saving ? 'Guardando en Vertical...' : 'Guardar en Expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL DE HISTORIAL DE SIGNOS VITALES */}
      {vitalsHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div
            className="he-hist-card bg-white w-full p-5 md:p-6 shadow-2xl space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-100 text-[#0f2a4e] rounded-xl">
                  <FiClock className="text-xl" />
                </div>
                <div>
                  <h3 className="text-[17px] font-bold text-slate-900 tracking-tight">Historial de signos vitales</h3>
                  <p className="text-xs text-slate-500">
                    Expediente: <strong className="text-slate-700">PT-{patientId}</strong> • Registro inmutable de tomas por enfermería y médicos
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  type="button"
                  onClick={() => {
                    setVitalsHistoryModal(prev => ({ ...prev, open: false }));
                    handleOpenVitalsModal();
                  }}
                  className="he-btn-navy flex items-center gap-1.5 px-3 py-1.5 text-xs shadow-sm transition"
                >
                  <FiPlus /> Nueva Toma
                </button>
                <button 
                  type="button" 
                  onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))} 
                  className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <FiX className="text-xl" />
                </button>
              </div>
            </div>

            {/* CUERPO CON TABLA */}
            <div className="flex-1 overflow-y-auto">
              {vitalsHistoryModal.loading ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hes-blue-main"></div>
                  <span className="text-xs font-medium">Cargando historial de signos vitales...</span>
                </div>
              ) : vitalsHistoryModal.history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <FiActivity className="text-4xl text-slate-300" />
                  <p className="text-sm font-bold text-slate-600">No hay registros de signos vitales previos</p>
                  <p className="text-xs text-slate-400">Las tomas de signos vitales que registres aparecerán en este historial cronológico.</p>
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-200 rounded-2xl shadow-sm">
                  <table className="he-hist-table w-full text-left text-[13px]">
                      <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-3.5">Fecha y Hora</th>
                        <th className="py-3 px-3">Capturado Por</th>
                        <th className="py-3 px-3 text-center">TA (mmHg)</th>
                        <th className="py-3 px-3 text-center">FC (lpm)</th>
                        <th className="py-3 px-3 text-center">FR (rpm)</th>
                        <th className="py-3 px-3 text-center">Sat O2</th>
                        <th className="py-3 px-3 text-center">Temp (°C)</th>
                        <th className="py-3 px-3 text-center">Peso / Talla</th>
                        <th className="py-3 px-3 text-center">IMC</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {vitalsHistoryModal.history.map((row, idx) => {
                        const sys = parseInt(row.sistolica);
                        const dia = parseInt(row.diastolica);
                        const fc = parseInt(row.fc);
                        const sat = parseInt(row.sat_o2);
                        const temp = parseFloat(row.temperatura);
                        const pesoN = parseFloat(row.peso);
                        const tallaN = parseFloat(row.talla);
                        const imcN = parseFloat(row.imc);

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 92;
                        const isSatWarn = sat && sat >= 92 && sat < 95;
                        const isFever = temp && temp >= 37.5;
                        const fmtTemp = (row.temperatura === '--' || isNaN(temp)) ? '--' : temp.toFixed(1);
                        const fmtPeso = (row.peso === '--' || isNaN(pesoN)) ? '--' : (Number.isInteger(pesoN) ? String(pesoN) : String(Math.round(pesoN * 10) / 10));
                        const fmtTalla = (row.talla === '--' || isNaN(tallaN)) ? '--' : tallaN.toFixed(2);
                        const fmtImc = (row.imc === '--' || row.imc == null || isNaN(imcN)) ? '--' : imcN.toFixed(1);

                        return (
                          <tr key={row.id || idx} className="hover:bg-blue-50/40 transition-colors">
                            <td className="py-2.5 px-3.5 whitespace-nowrap font-bold text-slate-800">
                              <span className="flex items-center gap-1.5">
                                <FiClock className="text-hes-blue-main shrink-0" />
                                {row.fecha_hora}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-lg text-sm font-semibold">
                                <FiUser className="text-slate-400" /> {row.capturado_por}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isTaAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFcAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isSatLow ? 'he-hist-bad' : isSatWarn ? 'he-hist-warn' : 'he-hist-ok'}`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFever ? 'he-hist-bad' : 'text-slate-800'}`}>
                                {fmtTemp}{fmtTemp !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-[12.5px]">
                              {fmtPeso !== '--' ? `${fmtPeso} kg` : '--'} / {fmtTalla !== '--' ? `${fmtTalla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="he-hist-pill he-hist-mute">
                                 {fmtImc}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="flex justify-between items-center pt-3 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                Total de tomas registradas: <strong className="text-slate-800">{vitalsHistoryModal.history.length}</strong>
              </span>
              <button
                type="button"
                onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold transition shadow-sm"
              >
                Cerrar Historial
              </button>
            </div>

          </div>
        </div>
      )}

      {/* MODAL DE AUDITORÍA Y VERIFICACIÓN DE INTEGRIDAD FORENSE NOM */}
      {auditModal.open && auditModal.firma && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="he-vrf-modal bg-white shadow-2xl max-w-3xl w-full text-left my-8 max-h-[92vh] flex flex-col overflow-hidden">
            
            {/* HEADER */}
            <div className="he-vrf-header flex justify-between items-center gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <span className="he-vrf-shield">
                  <MdVerifiedUser />
                </span>
                <div className="min-w-0">
                  <h3 className="text-[16px] font-bold text-white tracking-tight">Verificación de integridad y sello digital</h3>
                  <p className="text-[11.5px] text-slate-300">Expediente Clínico Electrónico — Hospital Escandón · {(auditModal.firma.codigo_formato || selectedFormat?.codigo || 'Documento clínico')}</p>
                </div>
              </div>
              <button 
                onClick={() => setAuditModal({ open: false, firma: null, loading: false, verification: null, copied: null })}
                className="text-slate-300 hover:text-white text-lg p-2 rounded-lg hover:bg-white/10 transition-colors shrink-0"
                title="Cerrar verificación"
              >
                <FiX />
              </button>
            </div>

            {/* CUERPO CON SCROLL */}
            <div className="he-vrf-body space-y-5">

            {/* ESTADO EN VIVO DE VERIFICACIÓN CRIPTOGRÁFICA */}
            {auditModal.loading ? (
              <div className="he-vrf-banner he-vrf-banner-load">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 border-[3px] border-[#0f2a4e] border-t-transparent rounded-full animate-spin shrink-0"></div>
                  <div className="text-xs font-semibold text-slate-700">
                    Recalculando hashes y verificando integridad criptográfica en tiempo real...
                  </div>
                </div>
              </div>
            ) : auditModal.verification?.integro ? (
              <div className="he-vrf-banner he-vrf-banner-ok">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="he-vrf-check ok"><FiCheck /></span>
                  <div className="min-w-0">
                    <span className="font-bold text-slate-900 text-[14.5px] block">Firma íntegra y verificable</span>
                    <span className="text-xs text-slate-500">El recálculo criptográfico confirma que el documento no ha sido alterado.</span>
                  </div>
                </div>
                <span className="he-vrf-pill ok">
                  Verificación exitosa
                </span>
              </div>
            ) : (
              <div className="he-vrf-banner he-vrf-banner-bad">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="he-vrf-check bad"><FiX /></span>
                  <div className="min-w-0">
                    <span className="font-bold text-slate-900 text-[14.5px] block">Integridad invalidada</span>
                    <span className="text-xs text-slate-500">El contenido actual difiere del estado al momento de firmar.</span>
                  </div>
                </div>
                <span className="he-vrf-pill bad">
                  Alerta de seguridad
                </span>
              </div>
            )}

            {/* TRÍADA EXPLÍCITA DE SEGURIDAD (3 TARJETAS) */}
            <div className="space-y-2.5">
              <span className="text-[12px] font-bold uppercase tracking-wider text-slate-700 block">
                Tríada de seguridad criptográfica
              </span>
              <div className="he-vrf-triad grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                
                {/* 1. IDENTIDAD */}
                <div className="he-vrf-card p-4 space-y-1.5">
                  <div className="flex items-center gap-2 text-slate-900 font-bold text-xs">
                    <span className="he-vrf-step">1</span> Identidad del firmante
                  </div>
                  <div className="font-bold text-slate-900 text-[13.5px] leading-snug">{auditModal.firma.nombre_medico}</div>
                  <div className="text-[11px] text-slate-500">Céd. Prof. <strong className="text-slate-700">{auditModal.firma.cedula_profesional}</strong></div>
                  <div className="text-[10.5px] text-slate-500 pt-2 border-t border-slate-100 leading-relaxed">
                    Comprobada con biometría dactilar DigitalPersona (FMD ANSI 378-2004).
                  </div>
                </div>

                {/* 2. INTEGRIDAD */}
                <div className="he-vrf-card p-4 space-y-1.5">
                  <div className="flex items-center gap-2 text-slate-900 font-bold text-xs">
                    <span className="he-vrf-step">2</span> Integridad del documento
                  </div>
                  <div className="font-bold text-slate-900 text-[13.5px]">Función hash SHA-256</div>
                  <div className="text-[11px] text-slate-500">Recalculado sobre la cadena original.</div>
                  <div className="text-[10.5px] text-slate-500 pt-2 border-t border-slate-100 leading-relaxed">
                    Garantiza la inalterabilidad del texto y los signos vitales.
                  </div>
                </div>

                {/* 3. AUTENTICIDAD Y NO REPUDIO */}
                <div className="he-vrf-card p-4 space-y-1.5">
                  <div className="flex items-center gap-2 text-slate-900 font-bold text-xs">
                    <span className="he-vrf-step">3</span> Autenticidad y no repudio
                  </div>
                  <div className="font-bold text-slate-900 text-[13.5px]">
                    {(auditModal.firma.sello_digital || '').startsWith('ECDSA:') ? 'Firma ECDSA P-256' : 'Sello HMAC-SHA512 (Legacy)'}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {(auditModal.firma.sello_digital || '').startsWith('ECDSA:') ? 'Clave privada exclusiva del firmante.' : 'Clave criptográfica institucional.'}
                  </div>
                  <div className="text-[10.5px] text-slate-500 pt-2 border-t border-slate-100 leading-relaxed">
                    Impide la falsificación o suplantación pericial.
                  </div>
                </div>

              </div>
            </div>

            {/* SECCIÓN FIRMA Y CÓDIGO QR DE VERTICAL (EHR HOST) */}
            {auditModal.verification?.firma_vertical?.disponible && (
              <div className="he-vrf-term p-4 space-y-3">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-[10px] bg-[#0f2a4e] text-white flex items-center justify-center text-sm shrink-0">
                      <FiServer />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 text-[13px] flex items-center gap-2">
                        Firma Vertical (EHR Host)
                        <span className="text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200 px-2 py-0.5 rounded-full">
                          Sincronizado
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500">
                        Firmado por: <strong className="text-slate-700">{auditModal.verification.firma_vertical.firmado_por}</strong>
                        {auditModal.verification.firma_vertical.fecha_firma && ` · ${auditModal.verification.firma_vertical.fecha_firma}`}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setAuditModal(prev => ({ ...prev, showVerticalQR: !prev.showVerticalQR }))}
                    className="he-vrf-copy"
                  >
                    <FiExternalLink /> {auditModal.showVerticalQR ? 'Ocultar QR' : 'Ver QR'}
                  </button>
                </div>

                {auditModal.showVerticalQR && (
                  <div className="pt-3 border-t border-slate-200 flex flex-col sm:flex-row items-center gap-4 bg-white p-3 rounded-xl">
                    {auditModal.verification.firma_vertical.qr_data_url ? (
                      <div className="flex flex-col items-center gap-1.5 bg-white p-2.5 rounded-xl border border-slate-200 shrink-0">
                        <img
                          src={auditModal.verification.firma_vertical.qr_data_url}
                          alt="Código QR Vertical"
                          className="w-36 h-36 object-contain"
                        />
                        <span className="text-[9px] font-mono text-slate-400 uppercase tracking-wider font-semibold">QR oficial Vertical</span>
                      </div>
                    ) : (
                      <div className="w-36 h-36 flex items-center justify-center bg-slate-100 rounded-xl text-slate-400 text-xs">
                        QR no disponible
                      </div>
                    )}

                    <div className="flex-1 space-y-1.5 w-full text-xs">
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="font-bold text-slate-700">Token criptográfico Vertical</span>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(auditModal.verification.firma_vertical.cadena_firma || '');
                            setAuditModal(prev => ({ ...prev, copied: 'vertical' }));
                            setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                          }}
                          className="he-vrf-copy"
                        >
                          <FiCheckSquare /> {auditModal.copied === 'vertical' ? 'Copiado' : 'Copiar token'}
                        </button>
                      </div>
                      <div className="he-vrf-mono-dark p-2.5 text-slate-300 font-mono text-[10px] break-all select-all max-h-24 overflow-y-auto leading-relaxed">
                        {auditModal.verification.firma_vertical.cadena_firma}
                      </div>
                      <p className="text-[10px] text-slate-400">
                        Corresponde al registro nativo en el servidor EHR de Vertical para este documento.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* SELLO CRIPTOGRÁFICO DIGITAL */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-xs flex-wrap gap-2">
                <span className="font-bold text-slate-800 text-[12.5px] flex items-center gap-1.5">
                  <FiLock className="text-slate-500" /> {(auditModal.firma.sello_digital || '').startsWith('ECDSA:') ? 'Sello digital ECDSA P-256' : 'Sello criptográfico HMAC-SHA512 (Legacy)'}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(auditModal.firma.sello_digital || '');
                    setAuditModal(prev => ({ ...prev, copied: 'sello' }));
                    setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                  }}
                  className="he-vrf-copy"
                >
                  <FiCheckSquare /> {auditModal.copied === 'sello' ? 'Copiado' : 'Copiar sello'}
                </button>
              </div>
              <div className="he-vrf-mono-dark p-3 text-emerald-300 font-mono text-[11px] break-all leading-relaxed select-all">
                {auditModal.firma.sello_digital || 'No disponible'}
              </div>
            </div>

            {/* HASH SHA-256 DE INTEGRIDAD DOCUMENTAL */}
            {auditModal.firma.hash_sha256 && (
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs flex-wrap gap-2">
                  <span className="font-bold text-slate-800 text-[12.5px] flex items-center gap-1.5">
                    <FiShield className="text-slate-500" /> Hash SHA-256 documental
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(auditModal.firma.hash_sha256 || '');
                      setAuditModal(prev => ({ ...prev, copied: 'hash' }));
                      setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                    }}
                    className="he-vrf-copy"
                  >
                    <FiCheckSquare /> {auditModal.copied === 'hash' ? 'Copiado' : 'Copiar hash'}
                  </button>
                </div>
                <div className="he-vrf-mono-light p-2.5 text-slate-700 font-mono text-[11px] break-all select-all">
                  {auditModal.firma.hash_sha256}
                </div>
              </div>
            )}

            {/* SELLADO DE TIEMPO RFC 3161 (TSA) */}
            {auditModal.verification?.sellado_tiempo && (
              <div className={`p-3 rounded-xl border text-xs space-y-1 ${
                auditModal.verification.sellado_tiempo.disponible
                  ? (auditModal.verification.sellado_tiempo.verificado
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-red-50 border-red-200 text-red-700')
                  : 'bg-amber-50 border-amber-200 text-amber-800'
              }`}>
                <div className="font-bold flex items-center gap-1.5">
                  <FiClock /> Sellado de Tiempo (TSA RFC 3161)
                  {auditModal.verification.sellado_tiempo.disponible ? (
                    <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                      auditModal.verification.sellado_tiempo.verificado ? 'bg-emerald-200 text-emerald-900' : 'bg-red-200 text-red-900'
                    }`}>
                      {auditModal.verification.sellado_tiempo.verificado ? '✓ Token válido' : '✗ Token inválido'}
                    </span>
                  ) : (
                    <span className="text-[10px] font-black bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full">
                      Pendiente de countersign
                    </span>
                  )}
                </div>
                {auditModal.verification.sellado_tiempo.disponible ? (
                  <p className="text-[11px]">
                    Una Autoridad de Sellado de Tiempo certificó que este documento existía el{' '}
                    <strong>{new Date(auditModal.verification.sellado_tiempo.gen_time).toLocaleString()}</strong> (hora de autoridad, independiente del servidor del hospital).
                  </p>
                ) : (
                  <p className="text-[11px]">Esta firma no cuenta con token de autoridad de tiempo. La fecha mostrada proviene del servidor del hospital.</p>
                )}
              </div>
            )}

            {/* CADENA ORIGINAL NORMALIZADA */}
            {(auditModal.verification?.cadena_original || auditModal.firma.cadena_original) && (
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs flex-wrap gap-2">
                  <span className="font-bold text-slate-800 text-[12.5px]">
                    Cadena original normalizada
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(auditModal.verification?.cadena_original || auditModal.firma.cadena_original || '');
                      setAuditModal(prev => ({ ...prev, copied: 'cadena' }));
                      setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                    }}
                    className="he-vrf-copy"
                  >
                    <FiCheckSquare /> {auditModal.copied === 'cadena' ? 'Copiado' : 'Copiar cadena'}
                  </button>
                </div>
                <div className="he-vrf-mono-light p-2.5 text-slate-500 font-mono text-[10px] break-all select-all max-h-20 overflow-y-auto">
                  {auditModal.verification?.cadena_original || auditModal.firma.cadena_original}
                </div>
              </div>
            )}
            </div>

            {/* FOOTER Y MARCO NORMATIVO */}
            <div className="he-vrf-footer flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs">
              <div className="text-slate-400 font-medium flex items-center gap-1.5">
                <FiShield className="text-slate-300" /> NOM-004-SSA3-2012 · NOM-024-SSA3-2012
              </div>
              <button
                type="button"
                onClick={() => setAuditModal({ open: false, firma: null, loading: false, verification: null, copied: null })}
                className="he-btn-navy px-5 py-2.5 text-xs transition self-end sm:self-auto cursor-pointer"
              >
                Cerrar verificación
              </button>
            </div>

          </div>
        </div>
      )}

      {/* MODAL DE TOMA / MODIFICACIÓN DE SIGNOS VITALES (PTVS - SQL SERVER) */}
      {vitalsModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 shadow-2xl border border-slate-100 space-y-5 animate-scaleUp">
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <FiActivity className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-slate-800">Toma de Signos Vitales</h3>
                  <p className="text-xs text-slate-500">
                    Sincronización directa de signos vitales
                  </p>
                </div>
              </div>
              <button 
                type="button" 
                onClick={() => setVitalsModal(prev => ({ ...prev, open: false }))} 
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            {/* MENSAJES */}
            {vitalsModal.errorMsg && (
              <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100 flex items-center gap-2">
                <FiAlertCircle className="text-base flex-shrink-0" />
                <span>{vitalsModal.errorMsg}</span>
              </div>
            )}
            {vitalsModal.successMsg && (
              <div className="p-3 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100 flex items-center gap-2">
                <FiCheckCircle className="text-base flex-shrink-0" />
                <span>{vitalsModal.successMsg}</span>
              </div>
            )}

            {/* FORMULARIO */}
            <form onSubmit={handleSaveVitals} className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                
                {/* PRESIÓN SISTÓLICA */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    TA Sistólica (mmHg) *
                  </label>
                  <input
                    type="number"
                    value={vitalsModal.systolic}
                    onChange={(e) => setVitalsModal({ ...vitalsModal, systolic: e.target.value })}
                    placeholder="120"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>

                {/* PRESIÓN DIASTÓLICA */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    TA Diastólica (mmHg) *
                  </label>
                  <input
                    type="number"
                    value={vitalsModal.diastolic}
                    onChange={(e) => setVitalsModal({ ...vitalsModal, diastolic: e.target.value })}
                    placeholder="80"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>

                {/* FREC. CARDÍACA */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Frec. Cardíaca (lpm) *
                  </label>
                  <input
                    type="number"
                    value={vitalsModal.pulse}
                    onChange={(e) => setVitalsModal({ ...vitalsModal, pulse: e.target.value })}
                    placeholder="78"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>

                {/* FREC. RESPIRATORIA */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Frec. Respiratoria (rpm) *
                  </label>
                  <input
                    type="number"
                    value={vitalsModal.respiratory}
                    onChange={(e) => setVitalsModal({ ...vitalsModal, respiratory: e.target.value })}
                    placeholder="18"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>

                {/* SATURACIÓN O2 */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Saturación O2 (%) *
                  </label>
                  <input
                    type="number"
                    value={vitalsModal.oxygen_saturation}
                    onChange={(e) => setVitalsModal({ ...vitalsModal, oxygen_saturation: e.target.value })}
                    placeholder="98"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>

                {/* TEMPERATURA */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Temperatura (°C) *
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={vitalsModal.temperature}
                    onChange={(e) => setVitalsModal({ ...vitalsModal, temperature: e.target.value })}
                    placeholder="36.5"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>

                {/* PESO */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Peso (kg) *
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={vitalsModal.weight}
                    onChange={(e) => setVitalsModal({ ...vitalsModal, weight: e.target.value })}
                    placeholder="75.0"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>

                {/* TALLA / ESTATURA */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Talla / Altura (m) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={vitalsModal.height}
                    onChange={(e) => setVitalsModal({ ...vitalsModal, height: e.target.value })}
                    placeholder="1.72"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>

                {/* IMC CALCULADO */}
                <div className="bg-slate-100 p-2 rounded-xl flex flex-col justify-center items-center border border-slate-200">
                  <span className="text-[10px] font-bold uppercase text-slate-500">IMC Estimado</span>
                  <span className="text-base font-extrabold text-slate-800">
                    {(() => {
                      const w = parseFloat(vitalsModal.weight);
                      let h = parseFloat(vitalsModal.height);
                      if (h > 3) h = h / 100;
                      if (w > 0 && h > 0) return (w / (h * h)).toFixed(1);
                      return '--';
                    })()}
                  </span>
                  <span className="text-[9px] text-slate-400">kg/m²</span>
                </div>

              </div>

              {/* BOTONES DE ACCIÓN */}
              <div className="flex items-center justify-between gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setVitalsModal(prev => ({ ...prev, open: false }));
                    handleOpenVitalsHistory();
                  }}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-hes-blue-main hover:bg-blue-50 border border-blue-200 text-xs font-bold transition-all shadow-sm"
                >
                  <FiClock /> Ver Historial de Tomas
                </button>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setVitalsModal(prev => ({ ...prev, open: false }))}
                    className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                  >
                    Cancelar
                  </button>
                <button
                  type="submit"
                  disabled={vitalsModal.submitting}
                  className="flex items-center gap-2 px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <FiSave /> {vitalsModal.submitting ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
                </div>
              </div>
            </form>

          </div>
        </div>
      )}

      {/* MODAL DE HISTORIAL DE SIGNOS VITALES */}
      {vitalsHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div
            className="he-hist-card bg-white w-full p-5 md:p-6 shadow-2xl space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-100 text-[#0f2a4e] rounded-xl">
                  <FiClock className="text-xl" />
                </div>
                <div>
                  <h3 className="text-[17px] font-bold text-slate-900 tracking-tight">Historial de signos vitales</h3>
                  <p className="text-xs text-slate-500">
                    Expediente: <strong className="text-slate-700">PT-{patientId}</strong> • Registro inmutable de tomas por enfermería y médicos
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  type="button"
                  onClick={() => {
                    setVitalsHistoryModal(prev => ({ ...prev, open: false }));
                    handleOpenVitalsModal();
                  }}
                  className="he-btn-navy flex items-center gap-1.5 px-3 py-1.5 text-xs shadow-sm transition"
                >
                  <FiPlus /> Nueva Toma
                </button>
                <button 
                  type="button" 
                  onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))} 
                  className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <FiX className="text-xl" />
                </button>
              </div>
            </div>

            {/* CUERPO CON TABLA */}
            <div className="flex-1 overflow-y-auto">
              {vitalsHistoryModal.loading ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hes-blue-main"></div>
                  <span className="text-xs font-medium">Cargando historial de signos vitales...</span>
                </div>
              ) : vitalsHistoryModal.history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <FiActivity className="text-4xl text-slate-300" />
                  <p className="text-sm font-bold text-slate-600">No hay registros de signos vitales previos</p>
                  <p className="text-xs text-slate-400">Las tomas de signos vitales que registres aparecerán en este historial cronológico.</p>
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-200 rounded-2xl shadow-sm">
                  <table className="he-hist-table w-full text-left text-[13px]">
                      <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-3.5">Fecha y Hora</th>
                        <th className="py-3 px-3">Capturado Por</th>
                        <th className="py-3 px-3 text-center">TA (mmHg)</th>
                        <th className="py-3 px-3 text-center">FC (lpm)</th>
                        <th className="py-3 px-3 text-center">FR (rpm)</th>
                        <th className="py-3 px-3 text-center">Sat O2</th>
                        <th className="py-3 px-3 text-center">Temp (°C)</th>
                        <th className="py-3 px-3 text-center">Peso / Talla</th>
                        <th className="py-3 px-3 text-center">IMC</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {vitalsHistoryModal.history.map((row, idx) => {
                        const sys = parseInt(row.sistolica);
                        const dia = parseInt(row.diastolica);
                        const fc = parseInt(row.fc);
                        const sat = parseInt(row.sat_o2);
                        const temp = parseFloat(row.temperatura);
                        const pesoN = parseFloat(row.peso);
                        const tallaN = parseFloat(row.talla);
                        const imcN = parseFloat(row.imc);

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 92;
                        const isSatWarn = sat && sat >= 92 && sat < 95;
                        const isFever = temp && temp >= 37.5;
                        const fmtTemp = (row.temperatura === '--' || isNaN(temp)) ? '--' : temp.toFixed(1);
                        const fmtPeso = (row.peso === '--' || isNaN(pesoN)) ? '--' : (Number.isInteger(pesoN) ? String(pesoN) : String(Math.round(pesoN * 10) / 10));
                        const fmtTalla = (row.talla === '--' || isNaN(tallaN)) ? '--' : tallaN.toFixed(2);
                        const fmtImc = (row.imc === '--' || row.imc == null || isNaN(imcN)) ? '--' : imcN.toFixed(1);

                        return (
                          <tr key={row.id || idx} className="hover:bg-blue-50/40 transition-colors">
                            <td className="py-2.5 px-3.5 whitespace-nowrap font-bold text-slate-800">
                              <span className="flex items-center gap-1.5">
                                <FiClock className="text-hes-blue-main shrink-0" />
                                {row.fecha_hora}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-lg text-sm font-semibold">
                                <FiUser className="text-slate-400" /> {row.capturado_por}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isTaAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFcAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isSatLow ? 'he-hist-bad' : isSatWarn ? 'he-hist-warn' : 'he-hist-ok'}`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFever ? 'he-hist-bad' : 'text-slate-800'}`}>
                                {fmtTemp}{fmtTemp !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-[12.5px]">
                              {fmtPeso !== '--' ? `${fmtPeso} kg` : '--'} / {fmtTalla !== '--' ? `${fmtTalla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="he-hist-pill he-hist-mute">
                                 {fmtImc}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="flex justify-between items-center pt-3 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                Total de tomas registradas: <strong className="text-slate-800">{vitalsHistoryModal.history.length}</strong>
              </span>
              <button
                type="button"
                onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold transition shadow-sm"
              >
                Cerrar Historial
              </button>
            </div>

          </div>
        </div>
      )}

      {/* MODAL DE PRESCRIPCIÓN MÉDICA DE FÁRMACOS (PTDG - SQL SERVER CON HUELLA DIGITAL) */}
      {prescriptionModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 space-y-5 animate-scaleUp max-h-[90vh] overflow-y-auto">
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <MdOutlineMedicalServices className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-slate-800">Receta y Prescripción Médica</h3>
                  <p className="text-xs text-slate-500">
                    Registro formal de medicamentos • Firma obligatoria del médico tratante
                  </p>
                </div>
              </div>
              <button 
                type="button" 
                onClick={() => setPrescriptionModal(prev => ({ ...prev, open: false, waitingFingerprint: false }))} 
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            {/* MENSAJES */}
            {prescriptionModal.errorMsg && (
              <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100 flex items-center gap-2">
                <FiAlertCircle className="text-base flex-shrink-0" />
                <span>{prescriptionModal.errorMsg}</span>
              </div>
            )}
            {prescriptionModal.successMsg && (
              <div className="p-3 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100 flex items-center gap-2">
                <FiCheckCircle className="text-base flex-shrink-0" />
                <span>{prescriptionModal.successMsg}</span>
              </div>
            )}

            {/* FORMULARIO DE RECETA */}
            <form onSubmit={handleStartPrescriptionFingerprint} className="space-y-4">
              
              {/* NOMBRE DEL FÁRMACO */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  Nombre del Medicamento / Principio Activo *
                </label>
                <input
                  type="text"
                  value={prescriptionModal.name}
                  onChange={(e) => setPrescriptionModal({ ...prescriptionModal, name: e.target.value })}
                  placeholder="Ej. Ceftriaxona 1g, Paracetamol, Omeprazol..."
                  className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-3 py-2 text-sm font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                  required
                />
              </div>

              {/* DOSIS, UNIDAD, VÍA Y FRECUENCIA */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Dosis / Cantidad *</label>
                  <input
                    type="text"
                    value={prescriptionModal.amount}
                    onChange={(e) => setPrescriptionModal({ ...prescriptionModal, amount: e.target.value })}
                    placeholder="Ej. 500, 1, 30"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-2.5 py-1.5 text-xs font-semibold"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Unidad (UOM) *</label>
                  <select
                    value={prescriptionModal.uom}
                    onChange={(e) => setPrescriptionModal({ ...prescriptionModal, uom: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-2.5 py-1.5 text-xs font-semibold"
                  >
                    <option value="mg">mg</option>
                    <option value="g">g</option>
                    <option value="ml">ml</option>
                    <option value="tabletas">tabletas</option>
                    <option value="ampolletas">ampolletas</option>
                    <option value="cápsulas">cápsulas</option>
                    <option value="gotas">gotas</option>
                    <option value="UI">UI</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Vía *</label>
                  <select
                    value={prescriptionModal.route}
                    onChange={(e) => setPrescriptionModal({ ...prescriptionModal, route: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-2.5 py-1.5 text-xs font-semibold"
                  >
                    <option value="Oral">Oral</option>
                    <option value="Intravenosa">Intravenosa</option>
                    <option value="Intramuscular">Intramuscular</option>
                    <option value="Subcutánea">Subcutánea</option>
                    <option value="Tópica">Tópica</option>
                    <option value="Inhalatoria">Inhalatoria</option>
                    <option value="Oftálmica">Oftálmica</option>
                    <option value="Rectal">Rectal</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Frecuencia *</label>
                  <select
                    value={prescriptionModal.frequency}
                    onChange={(e) => setPrescriptionModal({ ...prescriptionModal, frequency: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-2.5 py-1.5 text-xs font-semibold"
                  >
                    <option value="Cada 8 horas">Cada 8 horas</option>
                    <option value="Cada 12 horas">Cada 12 horas</option>
                    <option value="Cada 24 horas">Cada 24 horas</option>
                    <option value="Cada 6 horas">Cada 6 horas</option>
                    <option value="Cada 4 horas">Cada 4 horas</option>
                    <option value="Dosis única">Dosis única</option>
                    <option value="Para 8 horas">Para 8 horas</option>
                    <option value="Infusión continua">Infusión continua</option>
                  </select>
                </div>
              </div>

              {/* PRN Y MOTIVO */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="prn_check"
                    checked={prescriptionModal.prn}
                    onChange={(e) => setPrescriptionModal({ ...prescriptionModal, prn: e.target.checked })}
                    className="w-4 h-4 text-hes-blue-main rounded border-slate-300"
                  />
                  <label htmlFor="prn_check" className="text-xs font-bold text-slate-700 cursor-pointer">
                    PRN (Por Razón Necesaria)
                  </label>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">
                    Indicación / Motivo Clínico ({prescriptionModal.prn ? 'Condición de aplicación' : 'Justificación'})
                  </label>
                  <input
                    type="text"
                    value={prescriptionModal.why}
                    onChange={(e) => setPrescriptionModal({ ...prescriptionModal, why: e.target.value })}
                    placeholder="Ej. Dolor moderado, fiebre >38°C, profilaxis antibiótica..."
                    className="w-full border border-slate-200 bg-white rounded-xl px-2.5 py-1.5 text-xs"
                  />
                </div>
              </div>

              {/* DISPENSACIÓN EN FARMACIA */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Cantidad a Surtir / Dispensar</label>
                  <input
                    type="text"
                    value={prescriptionModal.dispense}
                    onChange={(e) => setPrescriptionModal({ ...prescriptionModal, dispense: e.target.value })}
                    placeholder="Ej. 1 caja, 5 ampolletas, 14 tabletas"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-2.5 py-1.5 text-xs font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Resurtidos Permitidos</label>
                  <input
                    type="number"
                    min="0"
                    max="5"
                    value={prescriptionModal.refills}
                    onChange={(e) => setPrescriptionModal({ ...prescriptionModal, refills: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl px-2.5 py-1.5 text-xs font-semibold"
                  />
                </div>
              </div>

              {/* INSTRUCCIONES DETALLADAS */}
              <div>
                <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">
                  Instrucciones de Administración al Paciente / Enfermería
                </label>
                <textarea
                  value={prescriptionModal.instruction}
                  onChange={(e) => setPrescriptionModal({ ...prescriptionModal, instruction: e.target.value })}
                  placeholder="Ej. Diluir en 100ml de solución fisiológica y pasar en 30 minutos. Administrar con alimentos..."
                  className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl p-2.5 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                  rows={2}
                />
              </div>

              {/* ÁREA DE AUTENTICACIÓN BIOMÉTRICA DACTILAR */}
              <div className="p-4 rounded-2xl bg-blue-50/50 border border-blue-100 flex flex-col items-center justify-center text-center space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-hes-blue-main uppercase tracking-wider">
                  <MdFingerprint className="text-xl" /> Confirmación del médico
                </div>
                
                {prescriptionModal.waitingFingerprint ? (
                  <div className="space-y-2 py-2 animate-fadeIn">
                    <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mx-auto text-hes-blue-main animate-pulse shadow-inner">
                      <MdFingerprint className="text-3xl animate-bounce" />
                    </div>
                    <p className="text-xs font-bold text-slate-700">
                      Coloque su dedo en el lector...
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Al reconocer su huella, se guardará el medicamento.
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 max-w-md">
                    Para guardar la indicación, confirme con su huella.
                  </p>
                )}
              </div>

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setPrescriptionModal(prev => ({ ...prev, open: false, waitingFingerprint: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={prescriptionModal.submitting}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <MdFingerprint className="text-base" />
                  {prescriptionModal.waitingFingerprint 
                    ? (prescriptionModal.submitting ? 'Guardando indicación...' : 'Coloque su dedo en el lector...') 
                    : 'Firmar y Prescribir con Huella'}
                </button>
              </div>

            </form>

          </div>
        </div>
      )}

      {/* MODAL DE HISTORIAL DE SIGNOS VITALES */}
      {vitalsHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div
            className="he-hist-card bg-white w-full p-5 md:p-6 shadow-2xl space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-100 text-[#0f2a4e] rounded-xl">
                  <FiClock className="text-xl" />
                </div>
                <div>
                  <h3 className="text-[17px] font-bold text-slate-900 tracking-tight">Historial de signos vitales</h3>
                  <p className="text-xs text-slate-500">
                    Expediente: <strong className="text-slate-700">PT-{patientId}</strong> • Registro inmutable de tomas por enfermería y médicos
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  type="button"
                  onClick={() => {
                    setVitalsHistoryModal(prev => ({ ...prev, open: false }));
                    handleOpenVitalsModal();
                  }}
                  className="he-btn-navy flex items-center gap-1.5 px-3 py-1.5 text-xs shadow-sm transition"
                >
                  <FiPlus /> Nueva Toma
                </button>
                <button 
                  type="button" 
                  onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))} 
                  className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <FiX className="text-xl" />
                </button>
              </div>
            </div>

            {/* CUERPO CON TABLA */}
            <div className="flex-1 overflow-y-auto">
              {vitalsHistoryModal.loading ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hes-blue-main"></div>
                  <span className="text-xs font-medium">Cargando historial de signos vitales...</span>
                </div>
              ) : vitalsHistoryModal.history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <FiActivity className="text-4xl text-slate-300" />
                  <p className="text-sm font-bold text-slate-600">No hay registros de signos vitales previos</p>
                  <p className="text-xs text-slate-400">Las tomas de signos vitales que registres aparecerán en este historial cronológico.</p>
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-200 rounded-2xl shadow-sm">
                  <table className="he-hist-table w-full text-left text-[13px]">
                      <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-3.5">Fecha y Hora</th>
                        <th className="py-3 px-3">Capturado Por</th>
                        <th className="py-3 px-3 text-center">TA (mmHg)</th>
                        <th className="py-3 px-3 text-center">FC (lpm)</th>
                        <th className="py-3 px-3 text-center">FR (rpm)</th>
                        <th className="py-3 px-3 text-center">Sat O2</th>
                        <th className="py-3 px-3 text-center">Temp (°C)</th>
                        <th className="py-3 px-3 text-center">Peso / Talla</th>
                        <th className="py-3 px-3 text-center">IMC</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {vitalsHistoryModal.history.map((row, idx) => {
                        const sys = parseInt(row.sistolica);
                        const dia = parseInt(row.diastolica);
                        const fc = parseInt(row.fc);
                        const sat = parseInt(row.sat_o2);
                        const temp = parseFloat(row.temperatura);
                        const pesoN = parseFloat(row.peso);
                        const tallaN = parseFloat(row.talla);
                        const imcN = parseFloat(row.imc);

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 92;
                        const isSatWarn = sat && sat >= 92 && sat < 95;
                        const isFever = temp && temp >= 37.5;
                        const fmtTemp = (row.temperatura === '--' || isNaN(temp)) ? '--' : temp.toFixed(1);
                        const fmtPeso = (row.peso === '--' || isNaN(pesoN)) ? '--' : (Number.isInteger(pesoN) ? String(pesoN) : String(Math.round(pesoN * 10) / 10));
                        const fmtTalla = (row.talla === '--' || isNaN(tallaN)) ? '--' : tallaN.toFixed(2);
                        const fmtImc = (row.imc === '--' || row.imc == null || isNaN(imcN)) ? '--' : imcN.toFixed(1);

                        return (
                          <tr key={row.id || idx} className="hover:bg-blue-50/40 transition-colors">
                            <td className="py-2.5 px-3.5 whitespace-nowrap font-bold text-slate-800">
                              <span className="flex items-center gap-1.5">
                                <FiClock className="text-hes-blue-main shrink-0" />
                                {row.fecha_hora}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-lg text-sm font-semibold">
                                <FiUser className="text-slate-400" /> {row.capturado_por}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isTaAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFcAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isSatLow ? 'he-hist-bad' : isSatWarn ? 'he-hist-warn' : 'he-hist-ok'}`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFever ? 'he-hist-bad' : 'text-slate-800'}`}>
                                {fmtTemp}{fmtTemp !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-[12.5px]">
                              {fmtPeso !== '--' ? `${fmtPeso} kg` : '--'} / {fmtTalla !== '--' ? `${fmtTalla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="he-hist-pill he-hist-mute">
                                 {fmtImc}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="flex justify-between items-center pt-3 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                Total de tomas registradas: <strong className="text-slate-800">{vitalsHistoryModal.history.length}</strong>
              </span>
              <button
                type="button"
                onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold transition shadow-sm"
              >
                Cerrar Historial
              </button>
            </div>

          </div>
        </div>
      )}

      {/* MODAL PARA SUSPENDER / DISCONTINUAR FÁRMACO (PTDG) */}
      {discontinueModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp">
            
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="p-2.5 bg-red-50 text-red-600 rounded-xl">
                  <FiAlertCircle className="text-xl" />
                </div>
                <div>
                  <h3 className="text-base font-black text-slate-800">Suspender Medicamento</h3>
                  <p className="text-xs text-slate-500">Se marcará como discontinuado</p>
                </div>
              </div>
              <button 
                type="button" 
                onClick={() => setDiscontinueModal(prev => ({ ...prev, open: false }))} 
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <FiX className="text-lg" />
              </button>
            </div>

            {discontinueModal.errorMsg && (
              <div className="p-2.5 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100">
                {discontinueModal.errorMsg}
              </div>
            )}
            {discontinueModal.successMsg && (
              <div className="p-2.5 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100">
                {discontinueModal.successMsg}
              </div>
            )}

            <div className="p-3 bg-slate-50 rounded-xl text-xs space-y-1">
              <div className="font-bold text-slate-800 text-sm">{discontinueModal.med?.name}</div>
              <div className="text-slate-500">{discontinueModal.med?.dose} • {discontinueModal.med?.freq}</div>
            </div>

            <form onSubmit={handleStartDiscontinueFingerprint} className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Motivo de Suspensión *</label>
                <input
                  type="text"
                  value={discontinueModal.reason}
                  onChange={(e) => setDiscontinueModal({ ...discontinueModal, reason: e.target.value })}
                  className="w-full border border-slate-200 rounded-xl p-2 text-xs font-semibold"
                  required
                />
              </div>

              {discontinueModal.waitingFingerprint ? (
                <div className="p-3 bg-red-50 rounded-xl text-center space-y-1 animate-fadeIn">
                  <MdFingerprint className="text-3xl text-red-600 mx-auto animate-bounce" />
                  <p className="text-xs font-bold text-red-800">Coloque su huella en el lector para confirmar...</p>
                </div>
              ) : (
                <p className="text-[11px] text-slate-400">
                  Requiere confirmación biométrica del médico para asentar en auditoría.
                </p>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setDiscontinueModal(prev => ({ ...prev, open: false }))}
                  className="px-3 py-1.5 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={discontinueModal.submitting}
                  className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition-all disabled:opacity-50"
                >
                  {discontinueModal.waitingFingerprint ? 'Esperando huella...' : 'Confirmar con Huella'}
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

      {/* MODAL DE HISTORIAL DE SIGNOS VITALES */}
      {vitalsHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div
            className="he-hist-card bg-white w-full p-5 md:p-6 shadow-2xl space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-100 text-[#0f2a4e] rounded-xl">
                  <FiClock className="text-xl" />
                </div>
                <div>
                  <h3 className="text-[17px] font-bold text-slate-900 tracking-tight">Historial de signos vitales</h3>
                  <p className="text-xs text-slate-500">
                    Expediente: <strong className="text-slate-700">PT-{patientId}</strong> • Registro inmutable de tomas por enfermería y médicos
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  type="button"
                  onClick={() => {
                    setVitalsHistoryModal(prev => ({ ...prev, open: false }));
                    handleOpenVitalsModal();
                  }}
                  className="he-btn-navy flex items-center gap-1.5 px-3 py-1.5 text-xs shadow-sm transition"
                >
                  <FiPlus /> Nueva Toma
                </button>
                <button 
                  type="button" 
                  onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))} 
                  className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <FiX className="text-xl" />
                </button>
              </div>
            </div>

            {/* CUERPO CON TABLA */}
            <div className="flex-1 overflow-y-auto">
              {vitalsHistoryModal.loading ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hes-blue-main"></div>
                  <span className="text-xs font-medium">Cargando historial de signos vitales...</span>
                </div>
              ) : vitalsHistoryModal.history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <FiActivity className="text-4xl text-slate-300" />
                  <p className="text-sm font-bold text-slate-600">No hay registros de signos vitales previos</p>
                  <p className="text-xs text-slate-400">Las tomas de signos vitales que registres aparecerán en este historial cronológico.</p>
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-200 rounded-2xl shadow-sm">
                  <table className="he-hist-table w-full text-left text-[13px]">
                      <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-3.5">Fecha y Hora</th>
                        <th className="py-3 px-3">Capturado Por</th>
                        <th className="py-3 px-3 text-center">TA (mmHg)</th>
                        <th className="py-3 px-3 text-center">FC (lpm)</th>
                        <th className="py-3 px-3 text-center">FR (rpm)</th>
                        <th className="py-3 px-3 text-center">Sat O2</th>
                        <th className="py-3 px-3 text-center">Temp (°C)</th>
                        <th className="py-3 px-3 text-center">Peso / Talla</th>
                        <th className="py-3 px-3 text-center">IMC</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {vitalsHistoryModal.history.map((row, idx) => {
                        const sys = parseInt(row.sistolica);
                        const dia = parseInt(row.diastolica);
                        const fc = parseInt(row.fc);
                        const sat = parseInt(row.sat_o2);
                        const temp = parseFloat(row.temperatura);
                        const pesoN = parseFloat(row.peso);
                        const tallaN = parseFloat(row.talla);
                        const imcN = parseFloat(row.imc);

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 92;
                        const isSatWarn = sat && sat >= 92 && sat < 95;
                        const isFever = temp && temp >= 37.5;
                        const fmtTemp = (row.temperatura === '--' || isNaN(temp)) ? '--' : temp.toFixed(1);
                        const fmtPeso = (row.peso === '--' || isNaN(pesoN)) ? '--' : (Number.isInteger(pesoN) ? String(pesoN) : String(Math.round(pesoN * 10) / 10));
                        const fmtTalla = (row.talla === '--' || isNaN(tallaN)) ? '--' : tallaN.toFixed(2);
                        const fmtImc = (row.imc === '--' || row.imc == null || isNaN(imcN)) ? '--' : imcN.toFixed(1);

                        return (
                          <tr key={row.id || idx} className="hover:bg-blue-50/40 transition-colors">
                            <td className="py-2.5 px-3.5 whitespace-nowrap font-bold text-slate-800">
                              <span className="flex items-center gap-1.5">
                                <FiClock className="text-hes-blue-main shrink-0" />
                                {row.fecha_hora}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-lg text-sm font-semibold">
                                <FiUser className="text-slate-400" /> {row.capturado_por}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isTaAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFcAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isSatLow ? 'he-hist-bad' : isSatWarn ? 'he-hist-warn' : 'he-hist-ok'}`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFever ? 'he-hist-bad' : 'text-slate-800'}`}>
                                {fmtTemp}{fmtTemp !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-[12.5px]">
                              {fmtPeso !== '--' ? `${fmtPeso} kg` : '--'} / {fmtTalla !== '--' ? `${fmtTalla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="he-hist-pill he-hist-mute">
                                 {fmtImc}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="flex justify-between items-center pt-3 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                Total de tomas registradas: <strong className="text-slate-800">{vitalsHistoryModal.history.length}</strong>
              </span>
              <button
                type="button"
                onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold transition shadow-sm"
              >
                Cerrar Historial
              </button>
            </div>

          </div>
        </div>
      )}

      {/* MODAL DE PRESCRIPCIÓN DE RÉGIMEN DIETÉTICO Y CUIDADOS DE ENFERMERÍA (MR_SOL_DIET + POSTGRESQL) */}
      {dietModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 space-y-5 animate-scaleUp max-h-[90vh] overflow-y-auto">
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-red-50 text-red-600 rounded-2xl">
                  <MdOutlineRestaurant className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-slate-800">Prescripción de Régimen Dietético y Cuidados</h3>
                  <p className="text-xs text-slate-500">
                    Sincronización de dietas y cuidados • Firma Biométrica
                  </p>
                </div>
              </div>
              <button 
                type="button" 
                onClick={() => setDietModal(prev => ({ ...prev, open: false, waitingFingerprint: false }))} 
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            {/* MENSAJES */}
            {dietModal.errorMsg && (
              <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100 flex items-center gap-2">
                <FiAlertCircle className="text-base flex-shrink-0" />
                <span>{dietModal.errorMsg}</span>
              </div>
            )}
            {dietModal.successMsg && (
              <div className="p-3 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100 flex items-center gap-2">
                <FiCheckCircle className="text-base flex-shrink-0" />
                <span>{dietModal.successMsg}</span>
              </div>
            )}

            <form onSubmit={handleStartDietFingerprint} className="space-y-4">
              
              {/* TIPO DE DIETA Y HORARIO */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Tipo de Dieta *</label>
                  <select
                    value={dietModal.tipo_dieta}
                    onChange={(e) => setDietModal({ ...dietModal, tipo_dieta: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl p-2.5 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                  >
                    <option value="Ayuno Estricto">Ayuno Estricto (NVO)</option>
                    <option value="Dieta Líquida Clara">Dieta Líquida Clara</option>
                    <option value="Dieta Líquida General">Dieta Líquida General</option>
                    <option value="Dieta Blanda">Dieta Blanda</option>
                    <option value="Dieta Normal / Hospitalaria">Dieta Normal / Hospitalaria</option>
                    <option value="Dieta Hiposódica">Dieta Hiposódica</option>
                    <option value="Dieta Diabética (1500 kcal)">Dieta Diabética (1500 kcal)</option>
                    <option value="Dieta Astringente">Dieta Astringente</option>
                    <option value="Dieta Licuada por Sonda (SNG)">Dieta Licuada por Sonda (SNG)</option>
                    <option value="Dieta Hiperproteica">Dieta Hiperproteica</option>
                    <option value="Dieta Renal">Dieta Renal</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Horario / Turno (HORARIO) *</label>
                  <select
                    value={dietModal.horario}
                    onChange={(e) => setDietModal({ ...dietModal, horario: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl p-2.5 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                  >
                    <option value="Continuo">Continuo (Todo el día)</option>
                    <option value="D">D (Desayuno)</option>
                    <option value="C">C (Comida)</option>
                    <option value="N">N (Cena)</option>
                    <option value="D / C / N">Desayuno, Comida y Cena</option>
                    <option value="Fraccionada en 5 tomas">Fraccionada en 5 tomas</option>
                  </select>
                </div>
              </div>

              {/* FASE CLÍNICA Y TOLERANCIA VÍA ORAL */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Fase Clínica / Justificación *</label>
                  <input
                    type="text"
                    value={dietModal.fase_clinica}
                    onChange={(e) => setDietModal({ ...dietModal, fase_clinica: e.target.value })}
                    placeholder="Ej. Preparación Quirúrgica / Valoración Abdomen Agudo"
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl p-2 text-xs font-semibold"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Tolerancia a Vía Oral *</label>
                  <select
                    value={dietModal.tolerancia_via_oral}
                    onChange={(e) => setDietModal({ ...dietModal, tolerancia_via_oral: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl p-2 text-xs font-semibold"
                  >
                    <option value="Suspendida por dolor y náusea">Suspendida por dolor y náusea</option>
                    <option value="Adecuada sin náusea ni vómito">Adecuada sin náusea ni vómito</option>
                    <option value="Buena tolerancia a líquidos">Buena tolerancia a líquidos</option>
                    <option value="Regular con náusea leve">Regular con náusea leve</option>
                    <option value="En prueba de tolerancia">En prueba de tolerancia</option>
                  </select>
                </div>
              </div>

              {/* ALERGIAS ALIMENTARIAS Y NUTRIÓLOGO */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">
                    Alergias e Intolerancias Alimentarias (INTOLERANCIA)
                  </label>
                  <input
                    type="text"
                    value={dietModal.alergias_alimentarias}
                    onChange={(e) => setDietModal({ ...dietModal, alergias_alimentarias: e.target.value })}
                    placeholder="Ej. Ninguna conocida, Intolerancia a Lactosa, Mariscos..."
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl p-2 text-xs font-semibold"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Nutriólogo / Responsable</label>
                  <input
                    type="text"
                    value={dietModal.nutriologo_responsable}
                    onChange={(e) => setDietModal({ ...dietModal, nutriologo_responsable: e.target.value })}
                    className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl p-2 text-xs font-semibold"
                  />
                </div>
              </div>

              {/* INDICACIONES NUTRICIONALES DETALLADAS */}
              <div>
                <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">
                  Indicaciones Nutricionales Detalladas (DETALLE) *
                </label>
                <textarea
                  value={dietModal.indicaciones_nutricionales}
                  onChange={(e) => setDietModal({ ...dietModal, indicaciones_nutricionales: e.target.value })}
                  placeholder="Ej. Nada por vía oral (NVO). Solución Hartmann IV continua. Mantener sonda en caso de distensión abdominal..."
                  className="w-full border border-slate-200 bg-slate-50 focus:bg-white rounded-xl p-2.5 text-xs leading-relaxed focus:border-hes-blue-main outline-none"
                  rows={2}
                  required
                />
              </div>

              {/* SECCIÓN DE CUIDADOS DE ENFERMERÍA */}
              <div className="space-y-2 bg-slate-50 p-3.5 rounded-2xl border border-slate-200">
                <div className="flex justify-between items-center">
                  <span className="text-[11px] font-bold text-slate-700 uppercase flex items-center gap-1.5">
                    <FiCheckCircle className="text-emerald-600" /> Plan de Cuidados de Enfermería Vinculados
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setDietModal(prev => ({
                        ...prev,
                        cuidados_enfermeria: [
                          ...prev.cuidados_enfermeria,
                          { cuidado: '', frecuencia: 'Cada turno', estado: 'Activo' }
                        ]
                      }));
                    }}
                    className="text-xs font-bold text-hes-blue-main hover:text-hes-blue-dark flex items-center gap-1 bg-white px-2.5 py-1 rounded-lg border border-slate-200 shadow-2xs"
                  >
                    <FiPlus /> Agregar Cuidado
                  </button>
                </div>

                <div className="space-y-2">
                  {dietModal.cuidados_enfermeria && dietModal.cuidados_enfermeria.length > 0 ? (
                    dietModal.cuidados_enfermeria.map((c, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs bg-white p-2 rounded-xl border border-slate-200">
                        <input
                          type="text"
                          value={c.cuidado}
                          onChange={(e) => {
                            const updated = [...dietModal.cuidados_enfermeria];
                            updated[idx].cuidado = e.target.value;
                            setDietModal({ ...dietModal, cuidados_enfermeria: updated });
                          }}
                          className="flex-1 border-none bg-transparent outline-none font-semibold text-slate-800"
                          placeholder="Descripción del cuidado (ej. Monitoreo de signos vitales, Reposo...)"
                        />
                        <input
                          type="text"
                          value={c.frecuencia}
                          onChange={(e) => {
                            const updated = [...dietModal.cuidados_enfermeria];
                            updated[idx].frecuencia = e.target.value;
                            setDietModal({ ...dietModal, cuidados_enfermeria: updated });
                          }}
                          className="w-28 border border-slate-200 rounded-lg px-2 py-0.5 text-[11px] text-slate-600"
                          placeholder="Frecuencia..."
                        />
                        <select
                          value={c.estado}
                          onChange={(e) => {
                            const updated = [...dietModal.cuidados_enfermeria];
                            updated[idx].estado = e.target.value;
                            setDietModal({ ...dietModal, cuidados_enfermeria: updated });
                          }}
                          className="border border-slate-200 rounded-lg px-1.5 py-0.5 text-[11px] font-bold text-slate-700"
                        >
                          <option value="Activo">Activo</option>
                          <option value="Completado">Completado</option>
                          <option value="Suspendido">Suspendido</option>
                        </select>
                        <button
                          type="button"
                          onClick={() => {
                            const updated = dietModal.cuidados_enfermeria.filter((_, i) => i !== idx);
                            setDietModal({ ...dietModal, cuidados_enfermeria: updated });
                          }}
                          className="text-slate-400 hover:text-red-500 p-1"
                          title="Eliminar cuidado"
                        >
                          <FiX className="text-sm" />
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="p-3 text-center text-xs text-slate-400 italic">
                      Opcional: Pulse "+ Agregar Cuidado" si desea asignar indicaciones específicas a enfermería.
                    </div>
                  )}
                </div>
              </div>

              {/* ÁREA DE AUTENTICACIÓN BIOMÉTRICA DACTILAR */}
              <div className="p-4 rounded-2xl bg-blue-50/50 border border-blue-100 flex flex-col items-center justify-center text-center space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-hes-blue-main uppercase tracking-wider">
                  <MdFingerprint className="text-xl" /> Confirmación del médico
                </div>
                
                {dietModal.waitingFingerprint ? (
                  <div className="space-y-2 py-2 animate-fadeIn">
                    <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mx-auto text-hes-blue-main animate-pulse shadow-inner">
                      <MdFingerprint className="text-3xl animate-bounce" />
                    </div>
                    <p className="text-xs font-bold text-slate-700">
                      Coloque su dedo en el lector...
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Al reconocer su huella, se guardará la dieta y el plan de cuidados.
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 max-w-md">
                    Para guardar la indicación, confirme con su huella.
                  </p>
                )}
              </div>

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setDietModal(prev => ({ ...prev, open: false, waitingFingerprint: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={dietModal.submitting}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <MdFingerprint className="text-base" />
                  {dietModal.waitingFingerprint 
                    ? (dietModal.submitting ? 'Guardando indicación...' : 'Coloque su dedo en el lector...') 
                    : 'Firmar y Prescribir con Huella'}
                </button>
              </div>

            </form>

          </div>
        </div>
      )}

      {/* MODAL DE HISTORIAL DE SIGNOS VITALES */}
      {vitalsHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div
            className="he-hist-card bg-white w-full p-5 md:p-6 shadow-2xl space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-100 text-[#0f2a4e] rounded-xl">
                  <FiClock className="text-xl" />
                </div>
                <div>
                  <h3 className="text-[17px] font-bold text-slate-900 tracking-tight">Historial de signos vitales</h3>
                  <p className="text-xs text-slate-500">
                    Expediente: <strong className="text-slate-700">PT-{patientId}</strong> • Registro inmutable de tomas por enfermería y médicos
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  type="button"
                  onClick={() => {
                    setVitalsHistoryModal(prev => ({ ...prev, open: false }));
                    handleOpenVitalsModal();
                  }}
                  className="he-btn-navy flex items-center gap-1.5 px-3 py-1.5 text-xs shadow-sm transition"
                >
                  <FiPlus /> Nueva Toma
                </button>
                <button 
                  type="button" 
                  onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))} 
                  className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <FiX className="text-xl" />
                </button>
              </div>
            </div>

            {/* CUERPO CON TABLA */}
            <div className="flex-1 overflow-y-auto">
              {vitalsHistoryModal.loading ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hes-blue-main"></div>
                  <span className="text-xs font-medium">Cargando historial de signos vitales...</span>
                </div>
              ) : vitalsHistoryModal.history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <FiActivity className="text-4xl text-slate-300" />
                  <p className="text-sm font-bold text-slate-600">No hay registros de signos vitales previos</p>
                  <p className="text-xs text-slate-400">Las tomas de signos vitales que registres aparecerán en este historial cronológico.</p>
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-200 rounded-2xl shadow-sm">
                  <table className="he-hist-table w-full text-left text-[13px]">
                      <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-3.5">Fecha y Hora</th>
                        <th className="py-3 px-3">Capturado Por</th>
                        <th className="py-3 px-3 text-center">TA (mmHg)</th>
                        <th className="py-3 px-3 text-center">FC (lpm)</th>
                        <th className="py-3 px-3 text-center">FR (rpm)</th>
                        <th className="py-3 px-3 text-center">Sat O2</th>
                        <th className="py-3 px-3 text-center">Temp (°C)</th>
                        <th className="py-3 px-3 text-center">Peso / Talla</th>
                        <th className="py-3 px-3 text-center">IMC</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {vitalsHistoryModal.history.map((row, idx) => {
                        const sys = parseInt(row.sistolica);
                        const dia = parseInt(row.diastolica);
                        const fc = parseInt(row.fc);
                        const sat = parseInt(row.sat_o2);
                        const temp = parseFloat(row.temperatura);
                        const pesoN = parseFloat(row.peso);
                        const tallaN = parseFloat(row.talla);
                        const imcN = parseFloat(row.imc);

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 92;
                        const isSatWarn = sat && sat >= 92 && sat < 95;
                        const isFever = temp && temp >= 37.5;
                        const fmtTemp = (row.temperatura === '--' || isNaN(temp)) ? '--' : temp.toFixed(1);
                        const fmtPeso = (row.peso === '--' || isNaN(pesoN)) ? '--' : (Number.isInteger(pesoN) ? String(pesoN) : String(Math.round(pesoN * 10) / 10));
                        const fmtTalla = (row.talla === '--' || isNaN(tallaN)) ? '--' : tallaN.toFixed(2);
                        const fmtImc = (row.imc === '--' || row.imc == null || isNaN(imcN)) ? '--' : imcN.toFixed(1);

                        return (
                          <tr key={row.id || idx} className="hover:bg-blue-50/40 transition-colors">
                            <td className="py-2.5 px-3.5 whitespace-nowrap font-bold text-slate-800">
                              <span className="flex items-center gap-1.5">
                                <FiClock className="text-hes-blue-main shrink-0" />
                                {row.fecha_hora}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-lg text-sm font-semibold">
                                <FiUser className="text-slate-400" /> {row.capturado_por}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isTaAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFcAltered ? 'he-hist-warn' : 'text-slate-800'}`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isSatLow ? 'he-hist-bad' : isSatWarn ? 'he-hist-warn' : 'he-hist-ok'}`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`he-hist-pill ${isFever ? 'he-hist-bad' : 'text-slate-800'}`}>
                                {fmtTemp}{fmtTemp !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-[12.5px]">
                              {fmtPeso !== '--' ? `${fmtPeso} kg` : '--'} / {fmtTalla !== '--' ? `${fmtTalla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="he-hist-pill he-hist-mute">
                                 {fmtImc}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="flex justify-between items-center pt-3 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                Total de tomas registradas: <strong className="text-slate-800">{vitalsHistoryModal.history.length}</strong>
              </span>
              <button
                type="button"
                onClick={() => setVitalsHistoryModal(prev => ({ ...prev, open: false }))}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold transition shadow-sm"
              >
                Cerrar Historial
              </button>
            </div>

          </div>
        </div>
      )}

      {/* MODAL DE EDICIÓN / CAPTURA DE CONSENTIMIENTO 25 */}
      {consentModal25.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-black text-slate-800">
                  {consentModal25.isEdit ? 'Editar' : 'Nuevo'} Consentimiento Revisión Ginecológica y Consulta Externa
                </h3>
                <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-25 • NOM-004-SSA3-2012</p>
              </div>
              <button 
                type="button" 
                onClick={() => setConsentModal25(prev => ({ ...prev, open: false }))} 
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal25} className="space-y-4 text-xs">
              <div className="space-y-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                    <span>Médico Tratante (Autor)</span>
                    <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                      <FiLock /> Bloqueado por sesión
                    </span>
                  </label>
                  <input
                    type="text"
                    value={currentDoctorName || consentModal25.medico_tratante || ''}
                    readOnly
                    className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                    <span>Cédula Profesional</span>
                    <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                      <FiLock /> Asignada por perfil
                    </span>
                  </label>
                  <input
                    type="text"
                    value={currentDoctorCedula || consentModal25.cedula || ''}
                    readOnly
                    className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                  />
                </div>

                <div className="space-y-3">
                  {isPatientAdult(data?.patient || patient) ? (
                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={consentModal25.paciente_capaz}
                            onChange={(e) => setConsentModal25({ ...consentModal25, paciente_capaz: e.target.checked, pariente: e.target.checked ? '' : consentModal25.pariente, paciente_o_representante: e.target.checked ? (data?.patient?.name || patient?.name || '') : consentModal25.pariente })}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main cursor-pointer"
                          />
                          <span className="text-xs font-bold text-slate-800">
                            ¿El paciente puede otorgar consentimiento y firmar por sí mismo? (Mayor de edad)
                          </span>
                        </label>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          Mayor de edad ({data?.patient?.age || patient?.age || '—'} años)
                        </span>
                      </div>

                      {consentModal25.paciente_capaz ? (
                        <div className="text-[11px] text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                          <span>✓</span>
                          <span>Se asignará automáticamente al paciente (<b>{data?.patient?.name || patient?.name}</b>) en la firma legal.</span>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar / Tutor / Representante Legal (Obligatorio):"
                          value={consentModal25.pariente}
                          onChangeValue={(val) => setConsentModal25(prev => ({ ...prev, pariente: val, paciente_o_representante: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal25.paciente_capaz}
                          placeholder="Nombre completo del familiar o representante legal responsable"
                        />
                      )}
                    </div>
                  ) : (
                    <FamiliarSelectorSection
                      label={`Padre, Madre, Tutor o Representante Legal (Paciente menor de edad: ${data?.patient?.age || patient?.age || '—'} años):`}
                      value={consentModal25.pariente}
                      onChangeValue={(val) => setConsentModal25(prev => ({ ...prev, pariente: val, paciente_o_representante: val }))}
                      firmantesList={firmantesList}
                      required={true}
                      placeholder="Nombre completo del padre, madre o tutor responsable"
                    />
                  )}
                </div>

                {firmantesList && firmantesList.length > 0 && (
                  <div className="p-2 bg-blue-50/70 border border-blue-200 rounded-xl flex items-center justify-between gap-2 flex-wrap text-xs">
                    <span className="font-bold text-blue-900 flex items-center gap-1">
                      <FiUsers className="text-hes-blue-main" /> Testigos del expediente:
                    </span>
                    <div className="flex items-center gap-2">
                      <select
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val) {
                            const found = firmantesList.find(f => f.id === parseInt(val, 10));
                            if (found) setConsentModal25(prev => ({ ...prev, testigo1: found.nombre_completo }));
                          }
                        }}
                        defaultValue=""
                        className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                      >
                        <option value="">-- Cargar Testigo 1 --</option>
                        {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                      </select>
                      <select
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val) {
                            const found = firmantesList.find(f => f.id === parseInt(val, 10));
                            if (found) setConsentModal25(prev => ({ ...prev, testigo2: found.nombre_completo }));
                          }
                        }}
                        defaultValue=""
                        className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                      >
                        <option value="">-- Cargar Testigo 2 --</option>
                        {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                      </select>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 1</label>
                    <input
                      type="text"
                      value={consentModal25.testigo1}
                      onChange={(e) => setConsentModal25({ ...consentModal25, testigo1: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                      placeholder="Nombre del Testigo 1"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 2</label>
                    <input
                      type="text"
                      value={consentModal25.testigo2}
                      onChange={(e) => setConsentModal25({ ...consentModal25, testigo2: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                      placeholder="Nombre del Testigo 2"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal25(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal25.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <FiSave /> {consentModal25.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL DE EDICIÓN / CAPTURA DE CONSENTIMIENTO 34/01: MESA INCLINADA (TILT TEST) */}
      {consentModal3401.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-5xl w-full p-6 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp max-h-[92vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-black text-slate-800">
                  {consentModal3401.isEdit ? 'Editar' : 'Nuevo'} Consentimiento y Protocolo Mesa Inclinada (Tilt Test)
                </h3>
                <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-34 / PLT-36 • Protocolo INICICH Oficial</p>
              </div>
              <button 
                type="button" 
                onClick={() => setConsentModal3401(prev => ({ ...prev, open: false }))} 
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal3401} className="space-y-4 text-xs">
              {/* SECCIÓN 1: DATOS DEL PACIENTE, MÉDICO Y RESPONSABLES */}
              <div className="he-ed-sec p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Ficha del Paciente y Responsables</h4>
                  <span className="text-[10px] bg-blue-100 text-hes-blue-main font-bold px-2 py-0.5 rounded-full">
                    Expediente: {data?.patient?.mrn || 'PT-' + patientId}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 bg-white p-3 rounded-xl border border-slate-200">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 block uppercase">Paciente</span>
                    <span className="font-bold text-slate-800 text-xs">{data?.patient?.name || 'Comodín'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 block uppercase">Edad / Sexo</span>
                    <span className="font-bold text-slate-800 text-xs">{data?.patient?.age || '--'} años • {data?.patient?.sex || 'M'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 block uppercase">Grupo y RH</span>
                    <span className="font-bold text-slate-800 text-xs">{consentModal3401.gruporh || 'O POSITIVO'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 block uppercase">Alergias</span>
                    <span className="font-bold text-rose-600 text-xs">{consentModal3401.alergias || 'NEGADAS'}</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Médico Tratante (Autor)</label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal3401.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Cédula Profesional</label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal3401.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-3">
                  {isPatientAdult(data?.patient || patient) ? (
                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={consentModal3401.paciente_capaz}
                            onChange={(e) => setConsentModal3401({ ...consentModal3401, paciente_capaz: e.target.checked, pariente: e.target.checked ? '' : consentModal3401.pariente, tipo_interrogatorio: e.target.checked ? 'DIRECTO' : 'INDIRECTO' })}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main cursor-pointer"
                          />
                          <span className="text-xs font-bold text-slate-800">
                            ¿El paciente puede otorgar consentimiento y firmar por sí mismo? (Mayor de edad)
                          </span>
                        </label>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          Mayor de edad ({data?.patient?.age || patient?.age || '—'} años)
                        </span>
                      </div>

                      {consentModal3401.paciente_capaz ? (
                        <div className="text-[11px] text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                          <span>✓</span>
                          <span>Se asignará automáticamente al paciente (<b>{data?.patient?.name || patient?.name}</b>) en la firma legal.</span>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar / Tutor / Representante Legal (Obligatorio):"
                          value={consentModal3401.pariente}
                          onChangeValue={(val) => setConsentModal3401(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal3401.paciente_capaz}
                          placeholder="Nombre completo del familiar o representante legal responsable"
                        />
                      )}
                    </div>
                  ) : (
                    <FamiliarSelectorSection
                      label={`Padre, Madre, Tutor o Representante Legal (Paciente menor de edad: ${data?.patient?.age || patient?.age || '—'} años):`}
                      value={consentModal3401.pariente}
                      onChangeValue={(val) => setConsentModal3401(prev => ({ ...prev, pariente: val }))}
                      firmantesList={firmantesList}
                      required={true}
                      placeholder="Nombre completo del padre, madre o tutor responsable"
                    />
                  )}
                </div>

                {firmantesList && firmantesList.length > 0 && (
                  <div className="p-2 bg-blue-50/70 border border-blue-200 rounded-xl flex items-center justify-between gap-2 flex-wrap text-xs">
                    <span className="font-bold text-blue-900 flex items-center gap-1">
                      <FiUsers className="text-hes-blue-main" /> Testigos del expediente:
                    </span>
                    <div className="flex items-center gap-2">
                      <select
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val) {
                            const found = firmantesList.find(f => f.id === parseInt(val, 10));
                            if (found) setConsentModal3401(prev => ({ ...prev, testigo1: found.nombre_completo }));
                          }
                        }}
                        defaultValue=""
                        className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                      >
                        <option value="">-- Cargar Testigo 1 --</option>
                        {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                      </select>
                      <select
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val) {
                            const found = firmantesList.find(f => f.id === parseInt(val, 10));
                            if (found) setConsentModal3401(prev => ({ ...prev, testigo2: found.nombre_completo }));
                          }
                        }}
                        defaultValue=""
                        className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                      >
                        <option value="">-- Cargar Testigo 2 --</option>
                        {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                      </select>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 1</label>
                    <input
                      type="text"
                      value={consentModal3401.testigo1}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, testigo1: e.target.value })}
                      placeholder="Nombre completo del Testigo 1"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 2</label>
                    <input
                      type="text"
                      value={consentModal3401.testigo2}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, testigo2: e.target.value })}
                      placeholder="Nombre completo del Testigo 2"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 2: SIGNOS VITALES BASALES */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">2. Signos Vitales y Somatometría</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">TA Basal</label>
                    <input
                      type="text"
                      value={consentModal3401.ta}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, ta: e.target.value })}
                      placeholder="120/80"
                      className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-center font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">FC Meta</label>
                    <input
                      type="text"
                      value={consentModal3401.fc_meta}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, fc_meta: e.target.value })}
                      placeholder="150"
                      className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-center font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">FR (rpm)</label>
                    <input
                      type="text"
                      value={consentModal3401.f_resp}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, f_resp: e.target.value })}
                      placeholder="18"
                      className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-center font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Temp (°C)</label>
                    <input
                      type="text"
                      value={consentModal3401.temperatura}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, temperatura: e.target.value })}
                      placeholder="36.5"
                      className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-center font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Peso (kg)</label>
                    <input
                      type="text"
                      value={consentModal3401.peso}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, peso: e.target.value })}
                      placeholder="65"
                      className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-center font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Talla (cm)</label>
                    <input
                      type="text"
                      value={consentModal3401.talla}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, talla: e.target.value })}
                      placeholder="165"
                      className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-center font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 3: NARRATIVA CLÍNICA PROTOCOLO INICICH */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">3. Narrativa Clínica y Síntomas por Fase</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Fase Basal Refirió (FBPR)</label>
                    <input
                      type="text"
                      value={consentModal3401.fbpr}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, fbpr: e.target.value })}
                      placeholder="asintomática / mareo / etc."
                      className="w-full border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Fase Pasiva 20 min Refirió (FPR)</label>
                    <input
                      type="text"
                      value={consentModal3401.fpr}
                      onChange={(e) => setConsentModal3401({ ...consentModal3401, fpr: e.target.value })}
                      placeholder="mareo / náuseas / vómito biliar"
                      className="w-full border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 4: TABLA DE MONITOREO DE 21 INTERVALOS (PROTOCOLO INICICH) */}
              <div className="he-ed-sec p-4 space-y-3">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  <div>
                    <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">4. Hoja de Monitoreo Hemodinámico (21 Intervalos)</h4>
                    <p className="text-[10px] text-slate-500">Captura la Presión Arterial, FC y Observaciones clínicas de cada etapa.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const baseTA = consentModal3401.ta || '120/80';
                      const baseFC = consentModal3401.fc_meta ? '75' : '75';
                      setConsentModal3401(prev => ({
                        ...prev,
                        ta_basal: prev.ta_basal || baseTA, fc_basal: prev.fc_basal || baseFC, obs_basal: prev.obs_basal || 'Estable',
                        ta_p_inicio: prev.ta_p_inicio || baseTA, fc_p_inicio: prev.fc_p_inicio || baseFC, obs_p_inicio: prev.obs_p_inicio || 'Inicio fase pasiva 70°',
                        ta_p_2: prev.ta_p_2 || baseTA, fc_p_2: prev.fc_p_2 || baseFC, obs_p_2: prev.obs_p_2 || 'Estable',
                        ta_p_4: prev.ta_p_4 || baseTA, fc_p_4: prev.fc_p_4 || baseFC, obs_p_4: prev.obs_p_4 || 'Estable',
                        ta_p_6: prev.ta_p_6 || baseTA, fc_p_6: prev.fc_p_6 || baseFC, obs_p_6: prev.obs_p_6 || 'Estable',
                        ta_p_8: prev.ta_p_8 || baseTA, fc_p_8: prev.fc_p_8 || baseFC, obs_p_8: prev.obs_p_8 || 'Estable',
                        ta_p_10: prev.ta_p_10 || baseTA, fc_p_10: prev.fc_p_10 || baseFC, obs_p_10: prev.obs_p_10 || 'Estable',
                        ta_p_12: prev.ta_p_12 || baseTA, fc_p_12: prev.fc_p_12 || baseFC, obs_p_12: prev.obs_p_12 || 'Estable',
                        ta_p_14: prev.ta_p_14 || baseTA, fc_p_14: prev.fc_p_14 || baseFC, obs_p_14: prev.obs_p_14 || 'Estable',
                        ta_p_16: prev.ta_p_16 || baseTA, fc_p_16: prev.fc_p_16 || baseFC, obs_p_16: prev.obs_p_16 || 'Estable',
                        ta_p_18: prev.ta_p_18 || baseTA, fc_p_18: prev.fc_p_18 || baseFC, obs_p_18: prev.obs_p_18 || 'Estable',
                        ta_p_20: prev.ta_p_20 || baseTA, fc_p_20: prev.fc_p_20 || baseFC, obs_p_20: prev.obs_p_20 || 'Refirió mareo',
                        ta_a_inicio: prev.ta_a_inicio || baseTA, fc_a_inicio: prev.fc_a_inicio || baseFC, obs_a_inicio: prev.obs_a_inicio || 'Isosorbide 5mg SL',
                        ta_a_2: prev.ta_a_2 || baseTA, fc_a_2: prev.fc_a_2 || baseFC, obs_a_2: prev.obs_a_2 || 'Estable',
                        ta_a_4: prev.ta_a_4 || baseTA, fc_a_4: prev.fc_a_4 || baseFC, obs_a_4: prev.obs_a_4 || 'Estable',
                        ta_a_6: prev.ta_a_6 || baseTA, fc_a_6: prev.fc_a_6 || baseFC, obs_a_6: prev.obs_a_6 || 'Estable',
                        ta_a_8: prev.ta_a_8 || baseTA, fc_a_8: prev.fc_a_8 || baseFC, obs_a_8: prev.obs_a_8 || 'Estable',
                        ta_a_10: prev.ta_a_10 || baseTA, fc_a_10: prev.fc_a_10 || baseFC, obs_a_10: prev.obs_a_10 || 'Estable',
                        ta_a_12: prev.ta_a_12 || baseTA, fc_a_12: prev.fc_a_12 || baseFC, obs_a_12: prev.obs_a_12 || 'Estable',
                        ta_a_14: prev.ta_a_14 || baseTA, fc_a_14: prev.fc_a_14 || baseFC, obs_a_14: prev.obs_a_14 || 'Estable',
                        ta_final: prev.ta_final || baseTA, fc_final: prev.fc_final || baseFC, obs_final: prev.obs_final || 'Retorno supino'
                      }));
                    }}
                    className="text-[10px] font-bold bg-blue-50 text-hes-blue-main border border-blue-200 px-3 py-1 rounded-lg hover:bg-blue-100 transition-colors"
                  >
                    ⚡ Rellenar Valores Basales
                  </button>
                </div>

                <div className="border border-slate-200 rounded-xl overflow-hidden shadow-xs bg-white max-h-72 overflow-y-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-hes-blue-main text-white sticky top-0 z-10 text-[10px] font-bold tracking-wider">
                      <tr>
                        <th className="px-3 py-2 w-1/3">Tiempo / Inclinación</th>
                        <th className="px-2 py-2 w-1/5 text-center">Presión Arterial</th>
                        <th className="px-2 py-2 w-1/6 text-center">FC (lpm)</th>
                        <th className="px-3 py-2">Observaciones Clínicas</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-[11px]">
                      {[
                        { label: 'Basal', ta: 'ta_basal', fc: 'fc_basal', obs: 'obs_basal', header: false },
                        { label: 'Inicio fase pasiva 70°', ta: 'ta_p_inicio', fc: 'fc_p_inicio', obs: 'obs_p_inicio', header: true },
                        { label: "2' 70°", ta: 'ta_p_2', fc: 'fc_p_2', obs: 'obs_p_2' },
                        { label: "4' 70°", ta: 'ta_p_4', fc: 'fc_p_4', obs: 'obs_p_4' },
                        { label: "6' 70°", ta: 'ta_p_6', fc: 'fc_p_6', obs: 'obs_p_6' },
                        { label: "8' 70°", ta: 'ta_p_8', fc: 'fc_p_8', obs: 'obs_p_8' },
                        { label: "10' 70°", ta: 'ta_p_10', fc: 'fc_p_10', obs: 'obs_p_10' },
                        { label: "12' 70°", ta: 'ta_p_12', fc: 'fc_p_12', obs: 'obs_p_12' },
                        { label: "14' 70°", ta: 'ta_p_14', fc: 'fc_p_14', obs: 'obs_p_14' },
                        { label: "16' 70°", ta: 'ta_p_16', fc: 'fc_p_16', obs: 'obs_p_16' },
                        { label: "18' 70°", ta: 'ta_p_18', fc: 'fc_p_18', obs: 'obs_p_18' },
                        { label: "20' 70°", ta: 'ta_p_20', fc: 'fc_p_20', obs: 'obs_p_20' },
                        { label: 'Inicio fase activa 70° Isosorbide 5mg', ta: 'ta_a_inicio', fc: 'fc_a_inicio', obs: 'obs_a_inicio', header: true },
                        { label: "2' 70°", ta: 'ta_a_2', fc: 'fc_a_2', obs: 'obs_a_2' },
                        { label: "4' 70°", ta: 'ta_a_4', fc: 'fc_a_4', obs: 'obs_a_4' },
                        { label: "6' 70°", ta: 'ta_a_6', fc: 'fc_a_6', obs: 'obs_a_6' },
                        { label: "8' 70°", ta: 'ta_a_8', fc: 'fc_a_8', obs: 'obs_a_8' },
                        { label: "10' 70°", ta: 'ta_a_10', fc: 'fc_a_10', obs: 'obs_a_10' },
                        { label: "12' 70°", ta: 'ta_a_12', fc: 'fc_a_12', obs: 'obs_a_12' },
                        { label: "14' 70°", ta: 'ta_a_14', fc: 'fc_a_14', obs: 'obs_a_14' },
                        { label: 'Final 0°', ta: 'ta_final', fc: 'fc_final', obs: 'obs_final', header: true },
                      ].map((row, rIdx) => (
                        <tr key={rIdx} className={row.header ? 'bg-blue-50/50 font-bold' : 'hover:bg-slate-50'}>
                          <td className="px-3 py-1.5 font-semibold text-slate-700">{row.label}</td>
                          <td className="px-2 py-1">
                            <input
                              type="text"
                              value={consentModal3401[row.ta] || ''}
                              onChange={(e) => setConsentModal3401({ ...consentModal3401, [row.ta]: e.target.value })}
                              placeholder="120/80"
                              className="w-full border border-slate-200 rounded px-2 py-1 text-center text-xs font-semibold focus:border-hes-blue-main outline-none"
                            />
                          </td>
                          <td className="px-2 py-1">
                            <input
                              type="text"
                              value={consentModal3401[row.fc] || ''}
                              onChange={(e) => setConsentModal3401({ ...consentModal3401, [row.fc]: e.target.value })}
                              placeholder="75"
                              className="w-full border border-slate-200 rounded px-2 py-1 text-center text-xs font-semibold focus:border-hes-blue-main outline-none"
                            />
                          </td>
                          <td className="px-2 py-1">
                            <input
                              type="text"
                              value={consentModal3401[row.obs] || ''}
                              onChange={(e) => setConsentModal3401({ ...consentModal3401, [row.obs]: e.target.value })}
                              placeholder="Observaciones..."
                              className="w-full border border-slate-200 rounded px-2 py-1 text-xs focus:border-hes-blue-main outline-none"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SECCIÓN 5: CONCLUSIONES CLÍNICAS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">5. Conclusiones del Estudio</h4>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Conclusión 1</label>
                  <input
                    type="text"
                    value={consentModal3401.conclusiones}
                    onChange={(e) => setConsentModal3401({ ...consentModal3401, conclusiones: e.target.value })}
                    placeholder="Estudio de mesa inclinada con respuesta hemodinámica normal / vasopresora / etc."
                    className="w-full border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Conclusión 2 (Opcional)</label>
                  <input
                    type="text"
                    value={consentModal3401.conclusiones_2}
                    onChange={(e) => setConsentModal3401({ ...consentModal3401, conclusiones_2: e.target.value })}
                    placeholder="Sin evidencia de síncope vasovagal ni disautonomía..."
                    className="w-full border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Conclusión 3 (Opcional)</label>
                  <input
                    type="text"
                    value={consentModal3401.conclusiones_3}
                    onChange={(e) => setConsentModal3401({ ...consentModal3401, conclusiones_3: e.target.value })}
                    placeholder="Recomendaciones farmacológicas / higiénico-dietéticas..."
                    className="w-full border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal3401(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal3401.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <FiSave /> {consentModal3401.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL CAPTURA / EDICIÓN FORMATO 12 (CONSENTIMIENTO GINECO Y OBSTETRICIA HOSP/URG) */}
      {consentModal12.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-2xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiFileText />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal12.isEdit ? 'Editar' : 'Nuevo'} Consentimiento Gineco y Obstetricia (Hosp/Urg)
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-12 • NOM-004-SSA3-2012</p>
                </div>
              </div>
              <button
                onClick={() => setConsentModal12(prev => ({ ...prev, open: false }))}
                className="w-8 h-8 rounded-full bg-slate-100 text-slate-500 hover:bg-slate-200 flex items-center justify-center transition"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal12} className="space-y-4">
              {/* SECCIÓN 1: DATOS PACIENTE Y SERVICIO */}
              <div className="he-ed-sec p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Paciente y Ubicación Clínica</h4>
                  <span className="text-[11px] font-mono text-slate-500 font-semibold">EXP: {patient.mrn || `PT-${patientId}`}</span>
                </div>
                
                <div className="p-3 bg-white rounded-xl border border-slate-200 flex flex-wrap gap-4 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Paciente</span>
                    <span className="font-bold text-slate-800 text-xs">{patient.name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Fecha Nac.</span>
                    <span className="font-bold text-slate-800 text-xs">{patient.dob || 'S/D'} ({patient.age || '—'} años)</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Sexo</span>
                    <span className="font-bold text-slate-800 text-xs">{patient.sex || 'F'}</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Médico Tratante (Autor)</label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal12.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Cédula Profesional</label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal12.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="md:col-span-2">
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Diagnóstico Clínico</label>
                    <input
                      type="text"
                      value={consentModal12.diagnostico}
                      onChange={(e) => setConsentModal12({ ...consentModal12, diagnostico: e.target.value })}
                      placeholder="Diagnóstico de ingreso gineco-obstétrico"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Servicio</label>
                    <select
                      value={consentModal12.servicio}
                      onChange={(e) => setConsentModal12({ ...consentModal12, servicio: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                    >
                      <option value="URGENCIAS">Urgencias</option>
                      <option value="HOSPITALIZACION">Hospitalización</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-3">
                  {isPatientAdult(data?.patient || patient) ? (
                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={consentModal12.paciente_capaz}
                            onChange={(e) => setConsentModal12({ ...consentModal12, paciente_capaz: e.target.checked, pariente: e.target.checked ? '' : consentModal12.pariente })}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main cursor-pointer"
                          />
                          <span className="text-xs font-bold text-slate-800">
                            ¿El paciente puede otorgar consentimiento y firmar por sí mismo? (Mayor de edad)
                          </span>
                        </label>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          Mayor de edad ({data?.patient?.age || patient?.age || '—'} años)
                        </span>
                      </div>

                      {consentModal12.paciente_capaz ? (
                        <div className="text-[11px] text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                          <span>✓</span>
                          <span>Se asignará automáticamente al paciente (<b>{data?.patient?.name || patient?.name}</b>) en la firma legal.</span>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar / Tutor / Representante Legal (Obligatorio):"
                          value={consentModal12.pariente}
                          onChangeValue={(val) => setConsentModal12(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal12.paciente_capaz}
                          placeholder="Nombre completo del familiar o representante legal responsable"
                        />
                      )}
                    </div>
                  ) : (
                    <FamiliarSelectorSection
                      label={`Padre, Madre, Tutor o Representante Legal (Paciente menor de edad: ${data?.patient?.age || patient?.age || '—'} años):`}
                      value={consentModal12.pariente}
                      onChangeValue={(val) => setConsentModal12(prev => ({ ...prev, pariente: val }))}
                      firmantesList={firmantesList}
                      required={true}
                      placeholder="Nombre completo del padre, madre o tutor responsable"
                    />
                  )}
                </div>

                {firmantesList && firmantesList.length > 0 && (
                  <div className="p-2 bg-blue-50/70 border border-blue-200 rounded-xl flex items-center justify-between gap-2 flex-wrap text-xs">
                    <span className="font-bold text-blue-900 flex items-center gap-1">
                      <FiUsers className="text-hes-blue-main" /> Testigos del expediente:
                    </span>
                    <div className="flex items-center gap-2">
                      <select
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val) {
                            const found = firmantesList.find(f => f.id === parseInt(val, 10));
                            if (found) setConsentModal12(prev => ({ ...prev, testigo1: found.nombre_completo }));
                          }
                        }}
                        defaultValue=""
                        className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                      >
                        <option value="">-- Cargar Testigo 1 --</option>
                        {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                      </select>
                      <select
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val) {
                            const found = firmantesList.find(f => f.id === parseInt(val, 10));
                            if (found) setConsentModal12(prev => ({ ...prev, testigo2: found.nombre_completo }));
                          }
                        }}
                        defaultValue=""
                        className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                      >
                        <option value="">-- Cargar Testigo 2 --</option>
                        {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                      </select>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 1</label>
                    <input
                      type="text"
                      value={consentModal12.testigo1}
                      onChange={(e) => setConsentModal12({ ...consentModal12, testigo1: e.target.value })}
                      placeholder="Nombre del testigo 1"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 2</label>
                    <input
                      type="text"
                      value={consentModal12.testigo2}
                      onChange={(e) => setConsentModal12({ ...consentModal12, testigo2: e.target.value })}
                      placeholder="Nombre del testigo 2"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 2: BENEFICIOS Y PROCEDIMIENTOS ALTERNATIVOS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">2. Beneficios y Procedimientos Alternativos</h4>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Beneficios o Efectos Esperados</label>
                  <textarea
                    rows={2}
                    value={consentModal12.beneficios}
                    onChange={(e) => setConsentModal12({ ...consentModal12, beneficios: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl p-2.5 text-xs text-slate-700 focus:border-hes-blue-main outline-none leading-relaxed"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Procedimientos Alternativos Informados</label>
                  <textarea
                    rows={2}
                    value={consentModal12.alternativas}
                    onChange={(e) => setConsentModal12({ ...consentModal12, alternativas: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl p-2.5 text-xs text-slate-700 focus:border-hes-blue-main outline-none leading-relaxed"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal12(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal12.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <FiSave /> {consentModal12.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL CAPTURA / EDICIÓN FORMATO 04 (CONSENTIMIENTO INFORMADO PARA COLOCACIÓN DE CATÉTER VENOSO CENTRAL) */}
      {consentModal04.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-2xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiFileText />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal04.isEdit ? 'Editar' : 'Nuevo'} Consentimiento Colocación de Catéter Venoso Central
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-04 • NOM-004-SSA3-2012</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal04(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal04} className="space-y-4 text-xs">
              {/* SECCIÓN 1: DATOS CLÍNICOS Y MÉDICOS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Datos del Consentimiento y Personal Responsable</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Tratante (Autor)</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal04.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal04.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-3">
                  {isPatientAdult(data?.patient || patient) ? (
                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={consentModal04.paciente_capaz}
                            onChange={(e) => setConsentModal04({ ...consentModal04, paciente_capaz: e.target.checked, pariente: e.target.checked ? '' : consentModal04.pariente })}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main cursor-pointer"
                          />
                          <span className="text-xs font-bold text-slate-800">
                            ¿El paciente puede otorgar consentimiento y firmar por sí mismo? (Mayor de edad)
                          </span>
                        </label>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          Mayor de edad ({data?.patient?.age || patient?.age || '—'} años)
                        </span>
                      </div>

                      {consentModal04.paciente_capaz ? (
                        <div className="text-[11px] text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                          <span>✓</span>
                          <span>Se asignará automáticamente al paciente (<b>{data?.patient?.name || patient?.name}</b>) en la firma legal.</span>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar / Tutor / Representante Legal (Obligatorio):"
                          value={consentModal04.pariente}
                          onChangeValue={(val) => setConsentModal04(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal04.paciente_capaz}
                          placeholder="Nombre completo del familiar o representante legal responsable"
                        />
                      )}
                    </div>
                  ) : (
                    <FamiliarSelectorSection
                      label={`Padre, Madre, Tutor o Representante Legal (Paciente menor de edad: ${data?.patient?.age || patient?.age || '—'} años):`}
                      value={consentModal04.pariente}
                      onChangeValue={(val) => setConsentModal04(prev => ({ ...prev, pariente: val }))}
                      firmantesList={firmantesList}
                      required={true}
                      placeholder="Nombre completo del padre, madre o tutor responsable"
                    />
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-[11px] font-bold text-slate-600 uppercase">Nombre Completo del Testigo Presencial</label>
                    {firmantesList && firmantesList.length > 0 && (
                      <select
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val) {
                            const found = firmantesList.find(f => f.id === parseInt(val, 10));
                            if (found) {
                              setConsentModal04(prev => ({
                                ...prev,
                                testigo1: found.nombre_completo,
                                parentesco_testigo: found.parentesco || 'Familiar / Testigo Presencial',
                                identificacion_testigo: found.identificacion_oficial || '',
                                domicilio_testigo: found.domicilio || 'Conocido en expediente clínico'
                              }));
                            }
                          }
                        }}
                        defaultValue=""
                        className="text-[10px] border border-blue-300 bg-blue-50 text-blue-900 rounded-lg px-2 py-0.5 font-semibold outline-none cursor-pointer"
                      >
                        <option value="">-- Cargar testigo registrado --</option>
                        {firmantesList.map(f => (
                          <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>
                        ))}
                      </select>
                    )}
                  </div>
                  <input
                    type="text"
                    value={consentModal04.testigo1}
                    onChange={(e) => setConsentModal04({ ...consentModal04, testigo1: e.target.value })}
                    placeholder="Nombre del testigo presencial"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal04(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal04.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <FiSave /> {consentModal04.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL CAPTURA / EDICIÓN FORMATO 15 (CONSENTIMIENTO INFORMADO PARA CESÁREA / DISENTIMIENTO) */}
      {consentModal15.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-2xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiFileText />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal15.isEdit ? 'Editar' : 'Nuevo'} {consentModal15.tipo === 'no_autorizo' ? 'Disentimiento (No Autorizo)' : 'Consentimiento Informado'} para Cesárea
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-15 • NOM-004-SSA3-2012</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal15(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal15} className="space-y-4 text-xs">
              {/* SELECTOR DE MODALIDAD: AUTORIZO VS NO AUTORIZO */}
              <div className="bg-slate-50 p-3 rounded-2xl border border-slate-200">
                <label className="block text-[11px] font-bold text-slate-600 uppercase mb-2">Decisión Informada del Paciente / Tutor</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setConsentModal15({ ...consentModal15, tipo: 'autorizo' })}
                    className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                      consentModal15.tipo === 'autorizo'
                        ? 'bg-emerald-600 text-white shadow-md'
                        : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <span>✓</span> SÍ Autorizo (Consentimiento)
                  </button>
                  <button
                    type="button"
                    onClick={() => setConsentModal15({ ...consentModal15, tipo: 'no_autorizo' })}
                    className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                      consentModal15.tipo === 'no_autorizo'
                        ? 'bg-red-600 text-white shadow-md'
                        : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <span>✕</span> NO Autorizo (Disentimiento)
                  </button>
                </div>
              </div>

              {/* SECCIÓN 1: DATOS DEL MÉDICO Y DIAGNÓSTICO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Personal Responsable y Diagnóstico</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Tratante (Autor)</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal15.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal15.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Diagnóstico Clínico Materno-Fetal</label>
                  <input
                    type="text"
                    value={consentModal15.diagnostico}
                    onChange={(e) => setConsentModal15({ ...consentModal15, diagnostico: e.target.value })}
                    placeholder="Ej. EMBARAZO DE 39 SDG + ESTRECHEZ PÉLVICA / PRESENTACIÓN PÉLVICA"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>
              </div>

              {/* SECCIÓN 2A: CAMPOS MODO AUTORIZO */}
              {consentModal15.tipo === 'autorizo' && (
                <div className="he-ed-sec p-4 space-y-3 animate-fadeIn">
                  <h4 className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">2. Justificación Clínica y Beneficios</h4>
                  
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">El procedimiento consiste en:</label>
                    <input
                      type="text"
                      value={consentModal15.procedimiento_consiste}
                      onChange={(e) => setConsentModal15({ ...consentModal15, procedimiento_consiste: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Beneficios de realizarlo:</label>
                    <input
                      type="text"
                      value={consentModal15.beneficios}
                      onChange={(e) => setConsentModal15({ ...consentModal15, beneficios: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Alternativas médicas informadas:</label>
                    <input
                      type="text"
                      value={consentModal15.alternativas}
                      onChange={(e) => setConsentModal15({ ...consentModal15, alternativas: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>
                </div>
              )}

              {/* SECCIÓN 2B: CAMPOS MODO NO AUTORIZO (DISENTIMIENTO) */}
              {consentModal15.tipo === 'no_autorizo' && (
                <div className="bg-red-50/70 p-4 rounded-2xl border border-red-200 space-y-3 animate-fadeIn">
                  <h4 className="text-[11px] font-bold text-red-800 uppercase tracking-wider">2. Constancia de Disentimiento y Motivo</h4>
                  
                  <div>
                    <label className="block text-[11px] font-bold text-red-900 uppercase mb-1">
                      Motivo por el cual NO acepta la intervención quirúrgica (Obligatorio)
                    </label>
                    <textarea
                      rows={3}
                      required
                      value={consentModal15.motivo_no_acepto}
                      onChange={(e) => setConsentModal15({ ...consentModal15, motivo_no_acepto: e.target.value })}
                      placeholder="Especifique con claridad los motivos manifestados por la paciente o su tutor para no autorizar la cesárea..."
                      className="w-full border border-red-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-red-500 outline-none bg-white"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    <div>
                      <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Identificación Testigo</label>
                      <input
                        type="text"
                        value={consentModal15.identificacion_testigo}
                        onChange={(e) => setConsentModal15({ ...consentModal15, identificacion_testigo: e.target.value })}
                        className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs font-medium text-slate-800 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Parentesco Testigo</label>
                      <input
                        type="text"
                        value={consentModal15.parentesco_testigo}
                        onChange={(e) => setConsentModal15({ ...consentModal15, parentesco_testigo: e.target.value })}
                        className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs font-medium text-slate-800 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">Domicilio Testigo</label>
                      <input
                        type="text"
                        value={consentModal15.domicilio_testigo}
                        onChange={(e) => setConsentModal15({ ...consentModal15, domicilio_testigo: e.target.value })}
                        className="w-full border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs font-medium text-slate-800 bg-white"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* SECCIÓN 3: PACIENTE / TUTOR Y TESTIGOS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">3. Firmantes y Testigos</h4>

                <div className="space-y-3">
                  {isPatientAdult(data?.patient || patient) ? (
                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={consentModal15.paciente_capaz}
                            onChange={(e) => setConsentModal15({ ...consentModal15, paciente_capaz: e.target.checked, pariente: e.target.checked ? '' : consentModal15.pariente })}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main cursor-pointer"
                          />
                          <span className="text-xs font-bold text-slate-800">
                            ¿La paciente puede otorgar consentimiento y firmar por sí misma? (Mayor de edad)
                          </span>
                        </label>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          Mayor de edad ({data?.patient?.age || patient?.age || '—'} años)
                        </span>
                      </div>

                      {consentModal15.paciente_capaz ? (
                        <div className="text-[11px] text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                          <span>✓</span>
                          <span>Se asignará automáticamente a la paciente (<b>{data?.patient?.name || patient?.name}</b>) en la firma legal.</span>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar / Tutor / Representante Legal (Obligatorio):"
                          value={consentModal15.pariente}
                          onChangeValue={(val) => setConsentModal15(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal15.paciente_capaz}
                          placeholder="Nombre completo del familiar o representante legal responsable"
                        />
                      )}
                    </div>
                  ) : (
                    <FamiliarSelectorSection
                      label={`Padre, Madre, Tutor o Representante Legal (Paciente menor de edad: ${data?.patient?.age || patient?.age || '—'} años):`}
                      value={consentModal15.pariente}
                      onChangeValue={(val) => setConsentModal15(prev => ({ ...prev, pariente: val }))}
                      firmantesList={firmantesList}
                      required={true}
                      placeholder="Nombre completo del padre, madre o tutor responsable"
                    />
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-[11px] font-bold text-slate-600 uppercase">Nombre Completo del Testigo Presencial</label>
                    {firmantesList && firmantesList.length > 0 && (
                      <select
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val) {
                            const found = firmantesList.find(f => f.id === parseInt(val, 10));
                            if (found) {
                              setConsentModal15(prev => ({
                                ...prev,
                                testigo1: found.nombre_completo,
                                parentesco_testigo: found.parentesco || 'Familiar / Testigo Presencial',
                                identificacion_testigo: found.identificacion_oficial || '',
                                domicilio_testigo: found.domicilio || 'Conocido en expediente clínico'
                              }));
                            }
                          }
                        }}
                        defaultValue=""
                        className="text-[10px] border border-blue-300 bg-blue-50 text-blue-900 rounded-lg px-2 py-0.5 font-semibold outline-none cursor-pointer"
                      >
                        <option value="">-- Cargar testigo registrado --</option>
                        {firmantesList.map(f => (
                          <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>
                        ))}
                      </select>
                    )}
                  </div>
                  <input
                    type="text"
                    value={consentModal15.testigo1}
                    onChange={(e) => setConsentModal15({ ...consentModal15, testigo1: e.target.value })}
                    placeholder="Nombre del testigo presencial"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:border-hes-blue-main outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal15(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal15.saving}
                  className={`flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 ${
                    consentModal15.tipo === 'no_autorizo' ? 'bg-red-600 hover:bg-red-700' : 'bg-hes-blue-main hover:bg-hes-blue-dark'
                  }`}
                >
                  <FiSave /> {consentModal15.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL FORMATO 08: CONSENTIMIENTO INFORMADO DIAGNÓSTICO EN ADMISIÓN CONTINUA */}
      {consentModal08.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-3xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiFileText />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal08.isEdit ? 'Editar' : 'Nuevo'} Consentimiento Informado para Admisión Continua y Diagnóstico
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-08 • NOM-004-SSA3-2012</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal08(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal08} className="space-y-4 text-xs">
              {/* SECCIÓN 1: DATOS DEL MÉDICO Y DIAGNÓSTICO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Personal Responsable y Diagnóstico</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Tratante</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal08.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal08.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Diagnóstico Clínico del Paciente
                  </label>
                  <textarea
                    rows="2"
                    required
                    value={consentModal08.diagnostico}
                    onChange={(e) => setConsentModal08({ ...consentModal08, diagnostico: e.target.value })}
                    placeholder="Ej. VALORACIÓN Y TRATAMIENTO EN ADMISIÓN CONTINUA..."
                    className="w-full border border-slate-300 rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-hes-blue-main outline-none"
                  />
                </div>
              </div>

              {/* SECCIÓN 2: PROCEDIMIENTOS, RIESGOS Y BENEFICIOS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">2. Procedimientos, Riesgos y Beneficios</h4>
                
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Procedimientos de Diagnóstico y Tratamiento Autorizados
                  </label>
                  <textarea
                    rows="3"
                    required
                    value={consentModal08.procedimientos}
                    onChange={(e) => setConsentModal08({ ...consentModal08, procedimientos: e.target.value })}
                    placeholder="Detalle los accesos vasculares, tomas de muestras, monitorización..."
                    className="w-full border border-slate-300 rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-hes-blue-main outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                    Nivel de Riesgos Inherentes a los Procedimientos
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {['Bajos', 'Medios', 'Altos'].map(nivel => (
                      <button
                        key={nivel}
                        type="button"
                        onClick={() => setConsentModal08({ ...consentModal08, riesgos_inherentes_a_procedimien: nivel })}
                        className={`py-2 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all ${
                          (consentModal08.riesgos_inherentes_a_procedimien || 'Medios').toLowerCase() === nivel.toLowerCase()
                            ? (nivel === 'Altos' ? 'bg-rose-600 text-white shadow-md' : nivel === 'Medios' ? 'bg-amber-600 text-white shadow-md' : 'bg-emerald-600 text-white shadow-md')
                            : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                        }`}
                      >
                        <span>{(consentModal08.riesgos_inherentes_a_procedimien || 'Medios').toLowerCase() === nivel.toLowerCase() ? '●' : '○'}</span>
                        <span>{nivel}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                      Probables Procedimientos y Alternativas
                    </label>
                    <textarea
                      rows="2"
                      required
                      value={consentModal08.prob_proced_y_alts}
                      onChange={(e) => setConsentModal08({ ...consentModal08, prob_proced_y_alts: e.target.value })}
                      placeholder="Estudios de gabinete, observación..."
                      className="w-full border border-slate-300 rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                      Beneficios Esperados
                    </label>
                    <textarea
                      rows="2"
                      required
                      value={consentModal08.beneficios}
                      onChange={(e) => setConsentModal08({ ...consentModal08, beneficios: e.target.value })}
                      placeholder="Estabilización hemodinámica, diagnóstico oportuno..."
                      className="w-full border border-slate-300 rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-hes-blue-main outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 3: FIRMANTES Y TESTIGOS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">3. Firmantes y Testigos</h4>

                <div className="space-y-3">
                  {isPatientAdult(data?.patient || patient) ? (
                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={consentModal08.paciente_capaz}
                            onChange={(e) => setConsentModal08({ ...consentModal08, paciente_capaz: e.target.checked, pariente: e.target.checked ? '' : consentModal08.pariente })}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main cursor-pointer"
                          />
                          <span className="text-xs font-bold text-slate-800">
                            ¿El paciente puede otorgar consentimiento y firmar por sí mismo? (Mayor de edad)
                          </span>
                        </label>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          Mayor de edad ({data?.patient?.age || patient?.age || '—'} años)
                        </span>
                      </div>

                      {consentModal08.paciente_capaz ? (
                        <div className="text-[11px] text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                          <span>✓</span>
                          <span>Se asignará automáticamente al paciente (<b>{data?.patient?.name || patient?.name}</b>) en la firma legal.</span>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar / Tutor / Representante Legal (Obligatorio):"
                          value={consentModal08.pariente}
                          onChangeValue={(val) => setConsentModal08(prev => ({ ...prev, pariente: val }))}
                          parentescoValue={consentModal08.parentesco || ''}
                          onChangeParentesco={(pVal) => setConsentModal08(prev => ({ ...prev, parentesco: pVal }))}
                          firmantesList={firmantesList}
                          required={!consentModal08.paciente_capaz}
                          placeholder="Nombre completo del familiar o tutor responsable..."
                        />
                      )}
                    </div>
                  ) : (
                    <FamiliarSelectorSection
                      label={`Nombre del Padre, Madre o Tutor Responsable (Paciente menor de edad: ${data?.patient?.age || patient?.age || '—'} años):`}
                      value={consentModal08.pariente}
                      onChangeValue={(val) => setConsentModal08(prev => ({ ...prev, pariente: val }))}
                      parentescoValue={consentModal08.parentesco || ''}
                      onChangeParentesco={(pVal) => setConsentModal08(prev => ({ ...prev, parentesco: pVal }))}
                      firmantesList={firmantesList}
                      required={true}
                      placeholder="Nombre completo del padre, madre o tutor..."
                    />
                  )}

                  {firmantesList && firmantesList.length > 0 && (
                    <div className="p-2 bg-blue-50/70 border border-blue-200 rounded-xl flex items-center justify-between gap-2 flex-wrap text-xs">
                      <span className="font-bold text-blue-900 flex items-center gap-1">
                        <FiUsers className="text-hes-blue-main" /> Testigos del expediente:
                      </span>
                      <div className="flex items-center gap-2">
                        <select
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val) {
                              const found = firmantesList.find(f => f.id === parseInt(val, 10));
                              if (found) setConsentModal08(prev => ({ ...prev, testigo1: found.nombre_completo }));
                            }
                          }}
                          defaultValue=""
                          className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                        >
                          <option value="">-- Cargar Testigo 1 --</option>
                          {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                        </select>
                        <select
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val) {
                              const found = firmantesList.find(f => f.id === parseInt(val, 10));
                              if (found) setConsentModal08(prev => ({ ...prev, testigo2: found.nombre_completo }));
                            }
                          }}
                          defaultValue=""
                          className="border border-blue-300 bg-white rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                        >
                          <option value="">-- Cargar Testigo 2 --</option>
                          {firmantesList.map(f => <option key={f.id} value={f.id}>{f.nombre_completo} ({f.tipo_firmante})</option>)}
                        </select>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                        Nombre de Testigo 1
                      </label>
                      <input
                        type="text"
                        value={consentModal08.testigo1}
                        onChange={(e) => setConsentModal08({ ...consentModal08, testigo1: e.target.value })}
                        placeholder="Nombre completo de testigo presencial 1..."
                        className="w-full border border-slate-300 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-hes-blue-main outline-none bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                        Nombre de Testigo 2
                      </label>
                      <input
                        type="text"
                        value={consentModal08.testigo2}
                        onChange={(e) => setConsentModal08({ ...consentModal08, testigo2: e.target.value })}
                        placeholder="Nombre completo de testigo presencial 2..."
                        className="w-full border border-slate-300 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-hes-blue-main outline-none bg-white"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal08(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 text-xs font-semibold transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal08.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 bg-hes-blue-main hover:bg-hes-blue-dark"
                >
                  <FiSave /> {consentModal08.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

            {/* MODAL FORMATO 07: CONSENTIMIENTO INFORMADO PARA PROCEDIMIENTOS QUIRÚRGICOS */}
      {consentModal07.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-3xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiFileText />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal07.isEdit ? 'Editar' : 'Nuevo'} Consentimiento Informado para Procedimientos Quirúrgicos
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-07 • NOM-004-SSA3-2012</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal07(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal07} className="space-y-4 text-xs">
              {/* SECCIÓN 1: DATOS DEL MÉDICO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Médico Responsable</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Tratante (Cirujano)</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal07.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal07.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 2: PROCEDIMIENTO, RIESGOS, BENEFICIOS Y ALTERNATIVAS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">2. Plan Quirúrgico y Justificación Clínica</h4>
                
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Nombre del Procedimiento Quirúrgico:</label>
                  <input
                    type="text"
                    value={consentModal07.procedimiento_quirurgico}
                    onChange={(e) => setConsentModal07({ ...consentModal07, procedimiento_quirurgico: e.target.value })}
                    placeholder="Ej. APENDICECTOMÍA LAPAROSCÓPICA / COLECISTECTOMÍA CONVENCIONAL"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Descripción del Procedimiento y Técnica:</label>
                  <textarea
                    rows={2}
                    value={consentModal07.descripcion_procedimiento}
                    onChange={(e) => setConsentModal07({ ...consentModal07, descripcion_procedimiento: e.target.value })}
                    placeholder="Descripción técnica del procedimiento quirúrgico a realizar..."
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Riesgos Inherentes y Potenciales:</label>
                    <textarea
                      rows={2}
                      value={consentModal07.riesgos_inherentes}
                      onChange={(e) => setConsentModal07({ ...consentModal07, riesgos_inherentes: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Beneficios Esperados:</label>
                    <textarea
                      rows={2}
                      value={consentModal07.beneficios}
                      onChange={(e) => setConsentModal07({ ...consentModal07, beneficios: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Alternativas Terapéuticas:</label>
                  <textarea
                    rows={2}
                    value={consentModal07.alternativas}
                    onChange={(e) => setConsentModal07({ ...consentModal07, alternativas: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>
              </div>

              {/* SECCIÓN 3: CAPACIDAD LEGAL Y PACIENTE / TUTOR */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">3. Paciente o Representante Legal</h4>
                {(() => {
                  const p = data?.patient || patient || {};
                  const isAdult = isPatientAdult(p);
                  return (
                    <>
                      <div className="flex items-center gap-3">
                        <label className={`flex items-center gap-2 font-bold ${!isAdult ? 'cursor-not-allowed opacity-60 text-slate-400' : 'cursor-pointer text-slate-700'}`}>
                          <input
                            type="checkbox"
                            disabled={!isAdult}
                            checked={consentModal07.paciente_capaz}
                            onChange={(e) => setConsentModal07({ ...consentModal07, paciente_capaz: e.target.checked, representante_legal: e.target.checked ? '' : consentModal07.representante_legal })}
                            className="rounded border-slate-300 text-hes-blue-main focus:ring-hes-blue-main"
                          />
                          Paciente mayor de edad y con plena capacidad legal para autorizar/firmar
                        </label>
                        {!isAdult && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded-md">
                            Menor de edad (Requiere Tutor)
                          </span>
                        )}
                      </div>

                      {consentModal07.paciente_capaz ? (
                        <div className="p-3 bg-white rounded-xl border border-slate-200 text-slate-600">
                          <p className="text-[11px]">
                            El documento será firmado autógrafamente por el paciente titular: <b>{p.name || 'PACIENTE REGISTRADO'}</b>.
                          </p>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Representante Legal, Tutor o Familiar Responsable:"
                          value={consentModal07.representante_legal}
                          onChangeValue={(val) => setConsentModal07(prev => ({ ...prev, representante_legal: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal07.paciente_capaz}
                          placeholder="Nombre completo del padre, madre, tutor o apoderado legal"
                        />
                      )}
                    </>
                  );
                })()}
              </div>

              {/* SECCIÓN 4: TESTIGOS PRESENCIALES */}
              <TestigosSelectorSection
                testigo1={consentModal07.testigo1}
                testigo2={consentModal07.testigo2}
                onUpdateTestigo1={({ testigo1 }) => {
                  setConsentModal07(prev => ({ ...prev, testigo1 }));
                }}
                onUpdateTestigo2={({ testigo2 }) => {
                  setConsentModal07(prev => ({ ...prev, testigo2 }));
                }}
                firmantesList={firmantesList}
                showWitness2={true}
              />

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal07(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal07.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 bg-hes-blue-main hover:bg-hes-blue-dark"
                >
                  <FiSave /> {consentModal07.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}


      {/* MODAL FORMATO 02: CONSENTIMIENTO QUIRÚRGICO / DISENTIMIENTO */}
      {consentModal02.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-3xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiFileText />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal02.isEdit ? 'Editar' : 'Nuevo'} {consentModal02.tipo === 'no_autorizo' ? 'Disentimiento (No Autorizo)' : 'Consentimiento Informado'} para Tratamiento Quirúrgico
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-02 • NOM-004-SSA3-2012</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal02(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal02} className="space-y-4 text-xs">
              {/* SELECTOR DE MODALIDAD: AUTORIZO VS NO AUTORIZO */}
              <div className="bg-slate-50 p-3 rounded-2xl border border-slate-200">
                <label className="block text-[11px] font-bold text-slate-600 uppercase mb-2">Decisión Informada del Paciente / Tutor</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setConsentModal02({ ...consentModal02, tipo: 'autorizo' })}
                    className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                      consentModal02.tipo === 'autorizo'
                        ? 'bg-emerald-600 text-white shadow-md'
                        : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <span>✓</span> SÍ Autorizo (Consentimiento)
                  </button>
                  <button
                    type="button"
                    onClick={() => setConsentModal02({ ...consentModal02, tipo: 'no_autorizo' })}
                    className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                      consentModal02.tipo === 'no_autorizo'
                        ? 'bg-red-600 text-white shadow-md'
                        : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <span>✕</span> NO Autorizo (Disentimiento)
                  </button>
                </div>
              </div>

              {/* SECCIÓN 1: DATOS DEL MÉDICO Y DIAGNÓSTICO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Personal Responsable y Diagnóstico</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Tratante (Cirujano)</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal02.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal02.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Diagnóstico Clínico y Quirúrgico</label>
                  <input
                    type="text"
                    value={consentModal02.diagnostico}
                    onChange={(e) => setConsentModal02({ ...consentModal02, diagnostico: e.target.value })}
                    placeholder="Ej. COLECISTITIS CRÓNICA LITIÁSICA AGUDIZADA / APENDICITIS AGUDA"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                    required
                  />
                </div>
              </div>

              {/* SECCIÓN 2A: CAMPOS MODO AUTORIZO */}
              {consentModal02.tipo === 'autorizo' && (
                <div className="he-ed-sec p-4 space-y-3 animate-fadeIn">
                  <h4 className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">2. Plan Quirúrgico, Tratamientos y Beneficios</h4>
                  
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Procedimientos para confirmar diagnósticos:</label>
                    <input
                      type="text"
                      value={consentModal02.proced_para_confirmar_diagnost}
                      onChange={(e) => setConsentModal02({ ...consentModal02, proced_para_confirmar_diagnost: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Beneficios esperados del procedimiento:</label>
                    <input
                      type="text"
                      value={consentModal02.beneficio_de_dicho_procedimiento}
                      onChange={(e) => setConsentModal02({ ...consentModal02, beneficio_de_dicho_procedimiento: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>

                  {/* DESGLOSE DE TRATAMIENTOS */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Tratamientos Médicos:</label>
                      <input
                        type="text"
                        value={consentModal02.tratamientos_medicos}
                        onChange={(e) => setConsentModal02({ ...consentModal02, tratamientos_medicos: e.target.value })}
                        className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Tratamientos Quirúrgicos:</label>
                      <input
                        type="text"
                        value={consentModal02.tratamientos_quirurgicos}
                        onChange={(e) => setConsentModal02({ ...consentModal02, tratamientos_quirurgicos: e.target.value })}
                        className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Tratamientos Endoscópicos:</label>
                      <input
                        type="text"
                        value={consentModal02.tratamientos_endoscopicos}
                        onChange={(e) => setConsentModal02({ ...consentModal02, tratamientos_endoscopicos: e.target.value })}
                        className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Tratamientos de Rehabilitación:</label>
                      <input
                        type="text"
                        value={consentModal02.tratamientos_de_rehabilitacion}
                        onChange={(e) => setConsentModal02({ ...consentModal02, tratamientos_de_rehabilitacion: e.target.value })}
                        className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Alternativas médicas informadas:</label>
                    <input
                      type="text"
                      value={consentModal02.alternativas}
                      onChange={(e) => setConsentModal02({ ...consentModal02, alternativas: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                    />
                  </div>

                  {/* ANESTESIA */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3 bg-blue-50/50 rounded-xl border border-blue-100">
                    <div>
                      <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">Requiere Anestesia:</label>
                      <div className="flex items-center gap-4 mt-1.5">
                        <label className="flex items-center gap-1.5 cursor-pointer font-bold text-slate-700">
                          <input
                            type="radio"
                            name="anestesia_02"
                            value="SI"
                            checked={consentModal02.anestesia === 'SI'}
                            onChange={() => setConsentModal02({ ...consentModal02, anestesia: 'SI' })}
                            className="text-hes-blue-main"
                          />
                          SÍ
                        </label>
                        <label className="flex items-center gap-1.5 cursor-pointer font-bold text-slate-700">
                          <input
                            type="radio"
                            name="anestesia_02"
                            value="NO"
                            checked={consentModal02.anestesia === 'NO'}
                            onChange={() => setConsentModal02({ ...consentModal02, anestesia: 'NO' })}
                            className="text-hes-blue-main"
                          />
                          NO
                        </label>
                      </div>
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">Tipo de Anestesia:</label>
                      <input
                        type="text"
                        value={consentModal02.tipo_de_anestesia}
                        onChange={(e) => setConsentModal02({ ...consentModal02, tipo_de_anestesia: e.target.value })}
                        placeholder="Ej. General balanceada / Bloqueo neuroaxial"
                        className="w-full border border-slate-200 bg-white rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Principales Riesgos Informados:</label>
                    <textarea
                      rows={2}
                      value={consentModal02.principales_riesgos}
                      onChange={(e) => setConsentModal02({ ...consentModal02, principales_riesgos: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none resize-none"
                    />
                  </div>
                </div>
              )}

              {/* SECCIÓN 2B: CAMPOS MODO NO AUTORIZO (DISENTIMIENTO) */}
              {consentModal02.tipo === 'no_autorizo' && (
                <div className="bg-red-50 p-4 rounded-2xl border border-red-200 space-y-3 animate-fadeIn">
                  <div className="flex items-center gap-2">
                    <span className="text-red-700 font-extrabold text-sm">⚠️</span>
                    <h4 className="text-[11px] font-bold text-red-800 uppercase tracking-wider">
                      2. Registro de Negativa Informada (Disentimiento)
                    </h4>
                  </div>
                  <p className="text-[11px] text-red-700 leading-relaxed">
                    Al seleccionar esta modalidad, se generará la hoja de Disentimiento conforme a la NOM-004-SSA3-2012, liberando de responsabilidad médico-legal al cirujano y al hospital por las complicaciones inherentes al rechazo.
                  </p>
                  <div>
                    <label className="block text-[11px] font-bold text-red-900 uppercase mb-1">Motivo por el cual NO autoriza la intervención:</label>
                    <textarea
                      rows={3}
                      required={consentModal02.tipo === 'no_autorizo'}
                      value={consentModal02.motivo_de_no_autorizacion}
                      onChange={(e) => setConsentModal02({ ...consentModal02, motivo_de_no_autorizacion: e.target.value })}
                      placeholder="Escriba con precisión el motivo manifestado por el paciente o tutor (Ej. Decisión familiar, traslado a otra institución privada, rechazo a transfusión o procedimiento, etc.)..."
                      className="w-full border border-red-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-red-600 outline-none resize-none"
                    />
                  </div>
                </div>
              )}

              {/* SECCIÓN 3: CAPACIDAD Y FIRMANTE */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">3. Paciente o Representante Legal</h4>
                
                {(() => {
                  const p = data?.patient || patient || {};
                  const isAdult = isPatientAdult(p);

                  return (
                    <>
                      <div className="flex items-center gap-3">
                        <label className={`flex items-center gap-2 font-bold ${!isAdult ? 'cursor-not-allowed opacity-60 text-slate-400' : 'cursor-pointer text-slate-700'}`}>
                          <input
                            type="checkbox"
                            disabled={!isAdult}
                            checked={consentModal02.paciente_capaz}
                            onChange={(e) => setConsentModal02({ ...consentModal02, paciente_capaz: e.target.checked, pariente: e.target.checked ? '' : consentModal02.pariente })}
                            className="rounded border-slate-300 text-hes-blue-main focus:ring-hes-blue-main"
                          />
                          Paciente mayor de edad y con plena capacidad legal para autorizar/firmar
                        </label>
                        {!isAdult && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded-md">
                            Menor de edad (Requiere Tutor)
                          </span>
                        )}
                      </div>

                      {consentModal02.paciente_capaz ? (
                        <div className="p-3 bg-white rounded-xl border border-slate-200 text-slate-600">
                          <p className="text-[11px]">
                            El documento será firmado autógrafamente por el paciente titular: <b>{p.name || 'PACIENTE REGISTRADO'}</b>.
                          </p>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Representante Legal, Tutor o Familiar Responsable:"
                          value={consentModal02.pariente}
                          onChangeValue={(val) => setConsentModal02(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal02.paciente_capaz}
                          placeholder="Nombre completo del padre, madre, tutor o apoderado legal"
                        />
                      )}
                    </>
                  );
                })()}
              </div>

              {/* SECCIÓN 4: TESTIGOS PRESENCIALES */}
              <TestigosSelectorSection
                testigo1={consentModal02.testigo1}
                parentesco1={consentModal02.parentesco_testigo1}
                identificacion1={consentModal02.identificacion_testigo1}
                domicilio1={consentModal02.domicilio_testigo1}
                testigo2={consentModal02.testigo2}
                onUpdateTestigo1={({ testigo1, parentesco1, identificacion1, domicilio1 }) => {
                  setConsentModal02(prev => ({
                    ...prev,
                    testigo1,
                    parentesco_testigo1: parentesco1,
                    identificacion_testigo1: identificacion1,
                    domicilio_testigo1: domicilio1
                  }));
                }}
                onUpdateTestigo2={({ testigo2 }) => {
                  setConsentModal02(prev => ({ ...prev, testigo2 }));
                }}
                firmantesList={firmantesList}
                showWitness2={true}
              />

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal02(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal02.saving}
                  className={`flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 ${
                    consentModal02.tipo === 'no_autorizo' ? 'bg-red-600 hover:bg-red-700' : 'bg-hes-blue-main hover:bg-hes-blue-dark'
                  }`}
                >
                  <FiSave /> {consentModal02.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL CAPTURA / EDICIÓN FORMATO 43 (ORDEN DE INTUBACIÓN ENDOTRAQUEAL / SOPORTE VENTILATORIO) */}
      {consentModal43.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-2xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiActivity />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal43.isEdit ? 'Editar' : 'Nueva'} Orden de Intubación Endotraqueal
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-SINPRO-PLT-43 • NOM-004-SSA3-2012 / NOM-024-SSA3-2012</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal43(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal43} className="space-y-4 text-xs">
              {/* SECCIÓN 1: DATOS DEL MÉDICO, SERVICIO Y DIAGNÓSTICO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Personal Responsable, Área y Diagnóstico</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Tratante (Autor)</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal43.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal43.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Servicio o Área Hospitalaria</label>
                    <input
                      type="text"
                      value={consentModal43.servicio}
                      onChange={(e) => setConsentModal43({ ...consentModal43, servicio: e.target.value })}
                      placeholder="URGENCIAS / TERAPIA INTENSIVA"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Diagnóstico Clínico de Base</label>
                    <input
                      type="text"
                      value={consentModal43.diagnostico}
                      onChange={(e) => setConsentModal43({ ...consentModal43, diagnostico: e.target.value })}
                      placeholder="INSUFICIENCIA RESPIRATORIA AGUDA / COMPROMISO DE VÍA AÉREA"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                      required
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 2: BENEFICIOS, RIESGOS Y ALTERNATIVAS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-teal-700 uppercase tracking-wider">2. Justificación Clínica y Pronóstico</h4>
                
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Beneficios Esperados del Procedimiento:</label>
                  <textarea
                    rows={2}
                    value={consentModal43.beneficios}
                    onChange={(e) => setConsentModal43({ ...consentModal43, beneficios: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Riesgos Inherentes y Potenciales Complicaciones:</label>
                  <textarea
                    rows={2}
                    value={consentModal43.riesgos}
                    onChange={(e) => setConsentModal43({ ...consentModal43, riesgos: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Alternativas Clínicas Informadas:</label>
                  <textarea
                    rows={2}
                    value={consentModal43.alternativas}
                    onChange={(e) => setConsentModal43({ ...consentModal43, alternativas: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>
              </div>

              {/* SECCIÓN 3: PACIENTE O TUTOR / DECLARANTE */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">3. Declarante y Capacidad Legal</h4>
                
                {(() => {
                  const p = data?.patient || patient || {};
                  const isAdult = isPatientAdult(p);

                  return (
                    <>
                      <div className="flex items-center gap-3">
                        <label className={`flex items-center gap-2 font-bold ${!isAdult ? 'cursor-not-allowed opacity-60 text-slate-400' : 'cursor-pointer text-slate-700'}`}>
                          <input
                            type="checkbox"
                            disabled={!isAdult}
                            checked={consentModal43.paciente_capaz}
                            onChange={(e) => setConsentModal43({ ...consentModal43, paciente_capaz: e.target.checked, pariente: e.target.checked ? '' : consentModal43.pariente })}
                            className="rounded border-slate-300 text-hes-blue-main focus:ring-hes-blue-main"
                          />
                          Paciente mayor de edad y con capacidad para otorgar consentimiento
                        </label>
                        {!isAdult && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded-md">
                            Menor de edad (Requiere Tutor)
                          </span>
                        )}
                      </div>

                      {consentModal43.paciente_capaz ? (
                        <div className="p-3 bg-white rounded-xl border border-slate-200 text-slate-600">
                          <p className="text-[11px]">
                            El documento será asignado y firmado por el propio paciente titular: <b>{p.name || 'PACIENTE REGISTRADO'}</b>.
                          </p>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar, Tutor o Representante Legal Responsable:"
                          value={consentModal43.pariente}
                          onChangeValue={(val) => setConsentModal43(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal43.paciente_capaz}
                          placeholder="Nombre completo del familiar responsable o apoderado legal"
                        />
                      )}
                    </>
                  );
                })()}
              </div>

              {/* SECCIÓN 4: TESTIGOS PRESENCIALES */}
              <TestigosSelectorSection
                testigo1={consentModal43.testigo1}
                parentesco1={consentModal43.parentesco_testigo1}
                identificacion1={consentModal43.identificacion_testigo1}
                domicilio1={consentModal43.domicilio_testigo1}
                testigo2={consentModal43.testigo2}
                parentesco2={consentModal43.parentesco_testigo2}
                onUpdateTestigo1={({ testigo1, parentesco1, identificacion1, domicilio1 }) => {
                  setConsentModal43(prev => ({
                    ...prev,
                    testigo1,
                    parentesco_testigo1: parentesco1,
                    identificacion_testigo1: identificacion1,
                    domicilio_testigo1: domicilio1
                  }));
                }}
                onUpdateTestigo2={({ testigo2, parentesco2 }) => {
                  setConsentModal43(prev => ({ ...prev, testigo2, parentesco_testigo2: parentesco2 || prev.parentesco_testigo2 }));
                }}
                firmantesList={firmantesList}
                showWitness2={true}
              />

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal43(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal43.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 bg-hes-blue-main hover:bg-hes-blue-dark"
                >
                  <FiSave /> {consentModal43.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL CAPTURA / EDICIÓN FORMATO 06 (PROCEDIMIENTO ANESTÉSICO) */}
      {consentModal06.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-2xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiActivity />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal06.isEdit ? 'Editar' : 'Nuevo'} Consentimiento para Procedimiento Anestésico
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-06 • NOM-004-SSA3-2012 / NOM-006-SSA3-2011</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal06(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal06} className="space-y-4 text-xs">
              {/* SECCIÓN 1: DATOS DEL MÉDICO ANESTESIÓLOGO Y SERVICIO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Médico Anestesiólogo y Servicio</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Anestesiólogo</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal06.medico_anestesiologo || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal06.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Servicio / Ubicación</label>
                    <input
                      type="text"
                      value={consentModal06.servicio}
                      onChange={(e) => setConsentModal06({ ...consentModal06, servicio: e.target.value })}
                      placeholder="QUIRÓFANO / URGENCIAS"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Diagnóstico Clínico</label>
                    <input
                      type="text"
                      value={consentModal06.diagnostico}
                      onChange={(e) => setConsentModal06({ ...consentModal06, diagnostico: e.target.value })}
                      placeholder="PROGRAMACIÓN QUIRÚRGICA / VALORACIÓN ANESTESIOLÓGICA"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                      required
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 2: CLASIFICACIÓN QUIRÚRGICA Y ANESTÉSICA */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider">2. Clasificación Quirúrgica y Riesgo ASA</h4>
                
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Tipo de Cirugía</label>
                    <select
                      value={consentModal06.tipo_cirugia}
                      onChange={(e) => setConsentModal06({ ...consentModal06, tipo_cirugia: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                    >
                      <option value="PROGRAMADA">PROGRAMADA</option>
                      <option value="URGENTE">URGENTE</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Magnitud de Cirugía</label>
                    <select
                      value={consentModal06.magnitud_cirugia}
                      onChange={(e) => setConsentModal06({ ...consentModal06, magnitud_cirugia: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                    >
                      <option value="MAYOR">MAYOR</option>
                      <option value="MENOR">MENOR</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Estado Físico A.S.A.</label>
                    <select
                      value={consentModal06.asa}
                      onChange={(e) => setConsentModal06({ ...consentModal06, asa: e.target.value })}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                    >
                      <option value="CLASE I">CLASE I (Sano)</option>
                      <option value="CLASE II">CLASE II (Enfermedad sistémica leve)</option>
                      <option value="CLASE III">CLASE III (Enfermedad sistémica grave)</option>
                      <option value="CLASE IV">CLASE IV (Amenaza constante para la vida)</option>
                      <option value="CLASE V">CLASE V (Moribundo)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Tipo de Anestesia Indicada</label>
                  <input
                    type="text"
                    value={consentModal06.tipo_anestesia}
                    onChange={(e) => setConsentModal06({ ...consentModal06, tipo_anestesia: e.target.value })}
                    placeholder="ANESTESIA GENERAL BALANCEADA CON INTUBACIÓN OROTRAQUEAL / BLOQUEO NEUROAXIAL"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                    required
                  />
                </div>
              </div>

              {/* SECCIÓN 3: BENEFICIOS Y ALTERNATIVAS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">3. Beneficios y Alternativas Anestésicas</h4>
                
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Beneficios de la Anestesia:</label>
                  <textarea
                    rows={2}
                    value={consentModal06.beneficios_anestesia}
                    onChange={(e) => setConsentModal06({ ...consentModal06, beneficios_anestesia: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Alternativas Clínicas Explicadas:</label>
                  <textarea
                    rows={2}
                    value={consentModal06.alternativas_anestesia}
                    onChange={(e) => setConsentModal06({ ...consentModal06, alternativas_anestesia: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>
              </div>

              {/* SECCIÓN 4: DECLARANTE Y CAPACIDAD LEGAL */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">4. Declarante y Capacidad Legal</h4>
                {(() => {
                  const p = data?.patient || patient || {};
                  const isAdult = isPatientAdult(p);
                  return (
                    <>
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 text-slate-700 font-bold cursor-pointer">
                          <input
                            type="checkbox"
                            checked={consentModal06.paciente_capaz}
                            onChange={(e) => setConsentModal06(prev => ({ ...prev, paciente_capaz: e.target.checked }))}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main"
                          />
                          Paciente con capacidad para otorgar consentimiento
                        </label>
                        {!isAdult && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded-md">
                            Menor de edad (Requiere Tutor)
                          </span>
                        )}
                      </div>

                      {consentModal06.paciente_capaz ? (
                        <div className="p-3 bg-white rounded-xl border border-slate-200 text-slate-600">
                          <p className="text-[11px]">
                            El documento será firmado por el propio paciente: <b>{p.name || 'PACIENTE REGISTRADO'}</b>.
                          </p>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar, Tutor o Representante Legal Responsable:"
                          value={consentModal06.pariente}
                          onChangeValue={(val) => setConsentModal06(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal06.paciente_capaz}
                          placeholder="Nombre completo del familiar responsable o apoderado legal"
                        />
                      )}
                    </>
                  );
                })()}
              </div>

              {/* SECCIÓN 5: TESTIGOS PRESENCIALES */}
              <TestigosSelectorSection
                testigo1={consentModal06.testigo1}
                parentesco1={consentModal06.parentesco_testigo1}
                identificacion1={consentModal06.identificacion_testigo1}
                domicilio1={consentModal06.domicilio_testigo1}
                testigo2={consentModal06.testigo2}
                parentesco2={consentModal06.parentesco_testigo2}
                identificacion2={consentModal06.identificacion_testigo2}
                domicilio2={consentModal06.domicilio_testigo2}
                onUpdateTestigo1={({ testigo1, parentesco1, identificacion1, domicilio1 }) => {
                  setConsentModal06(prev => ({
                    ...prev,
                    testigo1,
                    parentesco_testigo1: parentesco1,
                    identificacion_testigo1: identificacion1,
                    domicilio_testigo1: domicilio1
                  }));
                }}
                onUpdateTestigo2={({ testigo2, parentesco2, identificacion2, domicilio2 }) => {
                  setConsentModal06(prev => ({
                    ...prev,
                    testigo2,
                    parentesco_testigo2: parentesco2,
                    identificacion_testigo2: identificacion2,
                    domicilio_testigo2: domicilio2
                  }));
                }}
                firmantesList={firmantesList}
                showWitness2={true}
              />

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal06(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal06.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 bg-hes-blue-main hover:bg-hes-blue-dark"
                >
                  <FiSave /> {consentModal06.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL CAPTURA / EDICIÓN FORMATO 11 (CONSENTIMIENTO DE NO REANIMACIÓN / VOLUNTAD ANTICIPADA) */}
      {consentModal11.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-2xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiActivity />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal11.isEdit ? 'Editar' : 'Nuevo'} Consentimiento de No Reanimación
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-11 • NOM-004-SSA3-2012 / Voluntad Anticipada</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal11(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal11} className="space-y-4 text-xs">
              {/* SECCIÓN 1: DATOS DEL MÉDICO TRATANTE Y SERVICIO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Personal Médico y Área</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Tratante</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal11.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal11.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Servicio / Área Hospitalaria</label>
                    <input
                      type="text"
                      value={consentModal11.servicio}
                      onChange={(e) => setConsentModal11({ ...consentModal11, servicio: e.target.value })}
                      placeholder="URGENCIAS / MEDICINA INTERNA"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Diagnóstico Clínico</label>
                    <input
                      type="text"
                      value={consentModal11.diagnostico}
                      onChange={(e) => setConsentModal11({ ...consentModal11, diagnostico: e.target.value })}
                      placeholder="ENFERMEDAD EN ETAPA AVANZADA / PRONÓSTICO GRAVE Y LIMITADO"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                      required
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 2: DISPOSICIONES BIOÉTICAS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">2. Justificación Bioética y Pronóstico</h4>
                
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Beneficios y Riesgos de No Reanimación:</label>
                  <textarea
                    rows={2}
                    value={consentModal11.beneficios_y_riesgos_de_nr}
                    onChange={(e) => setConsentModal11({ ...consentModal11, beneficios_y_riesgos_de_nr: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Riesgos de No Aplicar Maniobras de Reanimación:</label>
                  <textarea
                    rows={2}
                    value={consentModal11.riesgos_de_no_aplicar}
                    onChange={(e) => setConsentModal11({ ...consentModal11, riesgos_de_no_aplicar: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Alternativas Médicas Bioéticas y Paliativas:</label>
                  <textarea
                    rows={2}
                    value={consentModal11.alternativa_nr}
                    onChange={(e) => setConsentModal11({ ...consentModal11, alternativa_nr: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>
              </div>

              {/* SECCIÓN 3: DECLARANTE Y CAPACIDAD LEGAL */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">3. Declarante y Capacidad Legal</h4>
                {(() => {
                  const p = data?.patient || patient || {};
                  const isAdult = isPatientAdult(p);
                  return (
                    <>
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 text-slate-700 font-bold cursor-pointer">
                          <input
                            type="checkbox"
                            checked={consentModal11.paciente_capaz}
                            onChange={(e) => setConsentModal11(prev => ({ ...prev, paciente_capaz: e.target.checked }))}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main"
                          />
                          Paciente con capacidad para otorgar consentimiento
                        </label>
                        {!isAdult && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded-md">
                            Menor de edad (Requiere Tutor)
                          </span>
                        )}
                      </div>

                      {consentModal11.paciente_capaz ? (
                        <div className="p-3 bg-white rounded-xl border border-slate-200 text-slate-600">
                          <p className="text-[11px]">
                            El documento será firmado por el propio paciente: <b>{p.name || 'PACIENTE REGISTRADO'}</b>.
                          </p>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar, Tutor o Representante Legal Responsable:"
                          value={consentModal11.pariente}
                          onChangeValue={(val) => setConsentModal11(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal11.paciente_capaz}
                          placeholder="Nombre completo del familiar responsable o apoderado legal"
                        />
                      )}
                    </>
                  );
                })()}
              </div>

              {/* SECCIÓN 4: TESTIGOS PRESENCIALES */}
              <TestigosSelectorSection
                testigo1={consentModal11.testigo1}
                parentesco1={consentModal11.parentesco_testigo1}
                identificacion1={consentModal11.identificacion_testigo1}
                domicilio1={consentModal11.domicilio_testigo1}
                testigo2={consentModal11.testigo2}
                parentesco2={consentModal11.parentesco_testigo2}
                identificacion2={consentModal11.identificacion_testigo2}
                domicilio2={consentModal11.domicilio_testigo2}
                onUpdateTestigo1={({ testigo1, parentesco1, identificacion1, domicilio1 }) => {
                  setConsentModal11(prev => ({
                    ...prev,
                    testigo1,
                    parentesco_testigo1: parentesco1,
                    identificacion_testigo1: identificacion1,
                    domicilio_testigo1: domicilio1
                  }));
                }}
                onUpdateTestigo2={({ testigo2, parentesco2, identificacion2, domicilio2 }) => {
                  setConsentModal11(prev => ({
                    ...prev,
                    testigo2,
                    parentesco_testigo2: parentesco2,
                    identificacion_testigo2: identificacion2,
                    domicilio_testigo2: domicilio2
                  }));
                }}
                firmantesList={firmantesList}
                showWitness2={true}
              />

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal11(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal11.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 bg-hes-blue-main hover:bg-hes-blue-dark"
                >
                  <FiSave /> {consentModal11.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL CAPTURA / EDICIÓN FORMATO 19 (CONSENTIMIENTO PARA HISTERECTOMÍA) */}
      {consentModal19.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-2xl w-full p-6 space-y-5 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiActivity />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {consentModal19.isEdit ? 'Editar' : 'Nuevo'} Consentimiento para Histerectomía
                  </h3>
                  <p className="text-xs text-slate-500">HE-DIRMED-CONSUL-PLT-19 • NOM-004-SSA3-2012 / Ginecología</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConsentModal19(prev => ({ ...prev, open: false }))}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleSaveConsentModal19} className="space-y-4 text-xs">
              {/* TIPO DE DECISIÓN: AUTORIZO / NO AUTORIZO */}
              <div className="flex items-center justify-center gap-4 p-2 bg-slate-100 rounded-2xl">
                <button
                  type="button"
                  onClick={() => setConsentModal19(prev => ({ ...prev, tipo: 'autorizo' }))}
                  className={`px-5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                    consentModal19.tipo === 'autorizo'
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'text-slate-600 hover:text-slate-800'
                  }`}
                >
                  <FiCheck /> SÍ AUTORIZO
                </button>
                <button
                  type="button"
                  onClick={() => setConsentModal19(prev => ({ ...prev, tipo: 'no_autorizo' }))}
                  className={`px-5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                    consentModal19.tipo === 'no_autorizo'
                      ? 'bg-red-600 text-white shadow-sm'
                      : 'text-slate-600 hover:text-slate-800'
                  }`}
                >
                  <FiX /> NO AUTORIZO (DISENTIMIENTO)
                </button>
              </div>

              {/* SECCIÓN 1: DATOS DEL MÉDICO TRATANTE */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-hes-blue-main uppercase tracking-wider">1. Personal Médico Responsable</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Médico Tratante</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Bloqueado por sesión
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorName || consentModal19.medico_tratante || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1 flex items-center justify-between">
                      <span>Cédula Profesional</span>
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <FiLock /> Asignada por perfil
                      </span>
                    </label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal19.cedula || ''}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Diagnóstico Clínico</label>
                  <input
                    type="text"
                    value={consentModal19.diagnostico}
                    onChange={(e) => setConsentModal19({ ...consentModal19, diagnostico: e.target.value })}
                    placeholder="MIOMATOSIS UTERINA / HEMORRAGIA UTERINA ANORMAL"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none bg-white"
                    required
                  />
                </div>
              </div>

              {/* SECCIÓN 2: EXPLICACIÓN QUIRÚRGICA */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-pink-700 uppercase tracking-wider">2. Procedimiento Quirúrgico</h4>
                
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Explicación del Proceso Quirúrgico:</label>
                  <textarea
                    rows={2}
                    value={consentModal19.explicacion_de_proceso}
                    onChange={(e) => setConsentModal19({ ...consentModal19, explicacion_de_proceso: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Beneficios del Procedimiento:</label>
                  <textarea
                    rows={2}
                    value={consentModal19.beneficios_de_procedimiento}
                    onChange={(e) => setConsentModal19({ ...consentModal19, beneficios_de_procedimiento: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Intervención Complementaria Informada:</label>
                  <textarea
                    rows={2}
                    value={consentModal19.intervencion_complementaria}
                    onChange={(e) => setConsentModal19({ ...consentModal19, intervencion_complementaria: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Alternativas Terapéuticas:</label>
                  <textarea
                    rows={2}
                    value={consentModal19.alternativas_terapeuticas}
                    onChange={(e) => setConsentModal19({ ...consentModal19, alternativas_terapeuticas: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 focus:border-hes-blue-main outline-none bg-white resize-none"
                    required
                  />
                </div>

                {consentModal19.tipo === 'no_autorizo' && (
                  <div className="p-3 bg-red-50 rounded-xl border border-red-200 space-y-1">
                    <label className="block text-[11px] font-bold text-red-700 uppercase">Motivo de No Autorización (Obligatorio):</label>
                    <textarea
                      rows={2}
                      value={consentModal19.motivo_de_no_autorizacion}
                      onChange={(e) => setConsentModal19({ ...consentModal19, motivo_de_no_autorizacion: e.target.value })}
                      placeholder="Especifique las razones por las cuales el paciente o representante decide no autorizar la intervención..."
                      className="w-full border border-red-300 rounded-xl px-3 py-2 text-xs font-medium text-red-900 focus:border-red-500 outline-none bg-white resize-none"
                      required={consentModal19.tipo === 'no_autorizo'}
                    />
                  </div>
                )}
              </div>

              {/* SECCIÓN 3: DECLARANTE Y CAPACIDAD LEGAL */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">3. Declarante y Capacidad Legal</h4>
                {(() => {
                  const p = data?.patient || patient || {};
                  const isAdult = isPatientAdult(p);
                  return (
                    <>
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 text-slate-700 font-bold cursor-pointer">
                          <input
                            type="checkbox"
                            checked={consentModal19.paciente_capaz}
                            onChange={(e) => setConsentModal19(prev => ({ ...prev, paciente_capaz: e.target.checked }))}
                            className="w-4 h-4 rounded text-hes-blue-main focus:ring-hes-blue-main"
                          />
                          Paciente con capacidad para otorgar consentimiento
                        </label>
                        {!isAdult && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded-md">
                            Menor de edad (Requiere Tutor)
                          </span>
                        )}
                      </div>

                      {consentModal19.paciente_capaz ? (
                        <div className="p-3 bg-white rounded-xl border border-slate-200 text-slate-600">
                          <p className="text-[11px]">
                            El documento será firmado por el propio paciente: <b>{p.name || 'PACIENTE REGISTRADO'}</b>.
                          </p>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Nombre del Familiar, Tutor o Representante Legal Responsable:"
                          value={consentModal19.pariente}
                          onChangeValue={(val) => setConsentModal19(prev => ({ ...prev, pariente: val }))}
                          firmantesList={firmantesList}
                          required={!consentModal19.paciente_capaz}
                          placeholder="Nombre completo del familiar responsable o apoderado legal"
                        />
                      )}
                    </>
                  );
                })()}
              </div>

              {/* SECCIÓN 4: TESTIGOS PRESENCIALES */}
              <TestigosSelectorSection
                testigo1={consentModal19.testigo1}
                parentesco1={consentModal19.parentesco_testigo1}
                identificacion1={consentModal19.identificacion_testigo1}
                domicilio1={consentModal19.domicilio_testigo1}
                testigo2={consentModal19.testigo2}
                parentesco2={consentModal19.parentesco_testigo2}
                identificacion2={consentModal19.identificacion_testigo2}
                domicilio2={consentModal19.domicilio_testigo2}
                onUpdateTestigo1={({ testigo1, parentesco1, identificacion1, domicilio1 }) => {
                  setConsentModal19(prev => ({
                    ...prev,
                    testigo1,
                    parentesco_testigo1: parentesco1,
                    identificacion_testigo1: identificacion1,
                    domicilio_testigo1: domicilio1
                  }));
                }}
                onUpdateTestigo2={({ testigo2, parentesco2, identificacion2, domicilio2 }) => {
                  setConsentModal19(prev => ({
                    ...prev,
                    testigo2,
                    parentesco_testigo2: parentesco2,
                    identificacion_testigo2: identificacion2,
                    domicilio_testigo2: domicilio2
                  }));
                }}
                firmantesList={firmantesList}
                showWitness2={true}
              />

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConsentModal19(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={consentModal19.saving}
                  className={`flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 ${
                    consentModal19.tipo === 'no_autorizo' ? 'bg-red-600 hover:bg-red-700' : 'bg-hes-blue-main hover:bg-hes-blue-dark'
                  }`}
                >
                  <FiSave /> {consentModal19.saving ? 'Guardando...' : 'Guardar en el expediente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL PARA FORMATO 15: EGRESO VOLUNTARIO (MR_EV_HOSP) */}
      {modal15EV.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-amber-500 text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiFileText />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 text-sm md:text-base">
                    {modal15EV.isEdit ? 'Editar Formato 15: Egreso Voluntario' : 'Nuevo Formato 15: Egreso Voluntario'}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    NOM-004-SSA3-2012 • Tabla MR_EV_HOSP en SQL Server y expediente clínico
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setModal15EV(prev => ({ ...prev, open: false }))}
                className="w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition"
              >
                <FiX />
              </button>
            </div>

            <form onSubmit={handleSaveModal15EV} className="mt-4 space-y-4 overflow-y-auto pr-1">
              {/* SECCIÓN 1: DATOS MÉDICOS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                  1. Datos del Médico Responsable
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Médico Tratante:</label>
                    <input
                      type="text"
                      value={modal15EV.medico_tratante}
                      onChange={(e) => setModal15EV(prev => ({ ...prev, medico_tratante: e.target.value }))}
                      required
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Cédula Profesional:</label>
                    <input
                      type="text"
                      value={modal15EV.cedula}
                      onChange={(e) => setModal15EV(prev => ({ ...prev, cedula: e.target.value }))}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 2: DIAGNÓSTICOS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                  2. Diagnósticos Clínicos
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Diagnóstico de Ingreso:</label>
                    <input
                      type="text"
                      value={modal15EV.diagnostico_ingreso}
                      onChange={(e) => setModal15EV(prev => ({ ...prev, diagnostico_ingreso: e.target.value }))}
                      required
                      placeholder="Diagnóstico de ingreso hospitalario"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Diagnóstico de Egreso:</label>
                    <input
                      type="text"
                      value={modal15EV.diagnostico_egreso}
                      onChange={(e) => setModal15EV(prev => ({ ...prev, diagnostico_egreso: e.target.value }))}
                      required
                      placeholder="Diagnóstico al momento del egreso voluntario"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 3: MOTIVO DEL EGRESO VOLUNTARIO */}
              <div className="he-ed-sec p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                    3. Motivo del Egreso Voluntario
                  </h4>
                  <span className="text-[10px] text-slate-400 font-medium">Opciones rápidas o personalizadas</span>
                </div>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {[
                    'Decisión personal y familiar para continuar con la convalecencia y cuidados médicos en domicilio particular.',
                    'Deseo de traslado a otra institución hospitalaria por conveniencia geográfica o familiar.',
                    'Inconformidad con la estancia hospitalaria por motivos personales no médicos.',
                    'Dificultad para continuar hospitalizado por compromisos familiares / laborales ineludibles.'
                  ].map((preset, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setModal15EV(prev => ({ ...prev, motivo_egreso: preset }))}
                      className="text-[10px] px-2.5 py-1 bg-white border border-slate-200 hover:border-amber-400 hover:bg-amber-50 text-slate-600 rounded-lg transition"
                    >
                      {idx === 0 ? 'Domicilio' : idx === 1 ? 'Traslado' : idx === 2 ? 'Inconformidad' : 'Familiar'}
                    </button>
                  ))}
                </div>
                <textarea
                  rows={2}
                  value={modal15EV.motivo_egreso}
                  onChange={(e) => setModal15EV(prev => ({ ...prev, motivo_egreso: e.target.value }))}
                  required
                  className="w-full border border-slate-200 rounded-xl p-3 text-xs text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                  placeholder="Especifique el motivo manifestado por el paciente o familiar..."
                />
              </div>

              {/* SECCIÓN 4: MEDIDAS RECOMENDADAS Y FACTORES DE RIESGO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                  4. Medidas Recomendadas y Factores de Riesgo Notificados
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Medidas Recomendadas:</label>
                    <textarea
                      rows={2}
                      value={modal15EV.medidas_recomendadas}
                      onChange={(e) => setModal15EV(prev => ({ ...prev, medidas_recomendadas: e.target.value }))}
                      className="w-full border border-slate-200 rounded-xl p-3 text-xs text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                      placeholder="Medidas terapéuticas, cuidados en domicilio, signos de alarma..."
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Factores de Riesgo Notificados al Paciente/Tutor:</label>
                    <textarea
                      rows={2}
                      value={modal15EV.factores_riesgo}
                      onChange={(e) => setModal15EV(prev => ({ ...prev, factores_riesgo: e.target.value }))}
                      className="w-full border border-slate-200 rounded-xl p-3 text-xs text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                      placeholder="Riesgos por suspender la atención médica intrahospitalaria..."
                    />
                  </div>
                </div>
              </div>

              {/* SECCIÓN 5: DECLARANTE / REPRESENTANTE LEGAL */}
              <div className="he-ed-sec p-4 space-y-3">
                {(() => {
                  const p = data?.patient || patient || {};
                  const isAdult = isPatientAdult(p);
                  return (
                    <>
                      <div className="flex items-center justify-between">
                        <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                          5. Declarante del Egreso Voluntario
                        </h4>
                        {isAdult ? (
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold text-slate-500">¿Firma el propio paciente?</span>
                            <button
                              type="button"
                              onClick={() => setModal15EV(prev => ({
                                ...prev,
                                paciente_capaz: !prev.paciente_capaz,
                                declarante: !prev.paciente_capaz ? (p.name || '') : prev.declarante
                              }))}
                              className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                                modal15EV.paciente_capaz ? 'bg-emerald-600 text-white' : 'bg-amber-500 text-white'
                              }`}
                            >
                              {modal15EV.paciente_capaz ? 'Sí (Paciente Titular)' : 'No (Familiar / Tutor)'}
                            </button>
                          </div>
                        ) : (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded-md">
                            Menor de edad (Requiere Tutor)
                          </span>
                        )}
                      </div>

                      {modal15EV.paciente_capaz ? (
                        <div className="p-3 bg-white rounded-xl border border-slate-200 text-slate-600">
                          <p className="text-[11px]">
                            El documento de egreso será firmado por el paciente titular: <b>{p.name || 'PACIENTE REGISTRADO'}</b>.
                          </p>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Seleccionar Familiar o Tutor Responsable del Egreso:"
                          value={modal15EV.declarante}
                          onChangeValue={(val) => setModal15EV(prev => ({ ...prev, declarante: val }))}
                          parentescoValue={modal15EV.parentesco}
                          onChangeParentesco={(par) => setModal15EV(prev => ({ ...prev, parentesco: par }))}
                          firmantesList={firmantesList}
                          required={!modal15EV.paciente_capaz}
                        />
                      )}
                    </>
                  );
                })()}
              </div>

              {/* SECCIÓN 6: TESTIGOS PRESENCIALES */}
              <TestigosSelectorSection
                testigo1={modal15EV.testigo1}
                parentesco1={modal15EV.parentesco1}
                identificacion1={modal15EV.identificacion1}
                domicilio1={modal15EV.domicilio1}
                testigo2={modal15EV.testigo2}
                parentesco2={modal15EV.parentesco2}
                identificacion2={modal15EV.identificacion2}
                domicilio2={modal15EV.domicilio2}
                onUpdateTestigo1={({ testigo1, parentesco1, identificacion1, domicilio1 }) => {
                  setModal15EV(prev => ({
                    ...prev,
                    testigo1,
                    parentesco1,
                    identificacion1,
                    domicilio1
                  }));
                }}
                onUpdateTestigo2={({ testigo2, parentesco2, identificacion2, domicilio2 }) => {
                  setModal15EV(prev => ({
                    ...prev,
                    testigo2,
                    parentesco2,
                    identificacion2,
                    domicilio2
                  }));
                }}
                firmantesList={firmantesList}
                showWitness2={true}
              />

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setModal15EV(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={modal15EV.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold bg-hes-blue-main hover:bg-hes-blue-dark shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <FiSave /> {modal15EV.saving ? 'Guardando...' : 'Guardar Egreso Voluntario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL UNIVERSAL PARA CUALQUIERA DE LOS 100+ FORMATOS CLÍNICOS */}
      {universalEditModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                  <FiEdit3 />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 text-sm md:text-base">
                    {universalEditModal.isNew ? 'Nuevo Registro Clínico' : 'Editar Registro Clínico'}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    {universalEditModal.codigo} • {universalEditModal.nombre}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setUniversalEditModal(prev => ({ ...prev, open: false }))}
                className="w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition"
              >
                <FiX />
              </button>
            </div>

            <form onSubmit={handleSaveUniversalModal} className="mt-4 space-y-4 overflow-y-auto pr-1">
              {/* SECCIÓN 1: MÉDICO RESPONSABLE */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                  1. Médico Responsable del Registro
                </h4>
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Nombre del Médico:</label>
                  <input
                    type="text"
                    value={universalEditModal.medico_tratante}
                    onChange={(e) => setUniversalEditModal(prev => ({ ...prev, medico_tratante: e.target.value }))}
                    required
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                  />
                </div>
              </div>

              {/* SECCIÓN 2: DIAGNÓSTICO */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                  2. Diagnóstico Clínico
                </h4>
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Diagnóstico Asociado:</label>
                  <input
                    type="text"
                    value={universalEditModal.diagnostico}
                    onChange={(e) => setUniversalEditModal(prev => ({ ...prev, diagnostico: e.target.value }))}
                    required
                    placeholder="Diagnóstico clínico del paciente"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                  />
                </div>
              </div>

              {/* SECCIÓN 3: OBSERVACIONES / PLAN / NOTAS */}
              <div className="he-ed-sec p-4 space-y-3">
                <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                  3. Observaciones / Notas Clínicas / Plan
                </h4>
                <textarea
                  rows={3}
                  value={universalEditModal.observaciones}
                  onChange={(e) => setUniversalEditModal(prev => ({ ...prev, observaciones: e.target.value }))}
                  placeholder="Detalles clínicos, evolución, observaciones pertinentes del formato..."
                  className="w-full border border-slate-200 rounded-xl p-3 text-xs text-slate-800 bg-white focus:border-hes-blue-main outline-none"
                />
              </div>

              {/* SECCIÓN 4: TUTOR / FAMILIAR / CONTACTO */}
              <div className="he-ed-sec p-4 space-y-3">
                {(() => {
                  const p = data?.patient || patient || {};
                  const isAdult = isPatientAdult(p);
                  return (
                    <>
                      <div className="flex items-center justify-between">
                        <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                          4. Paciente Titular o Familiar / Tutor
                        </h4>
                        {isAdult ? (
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold text-slate-500">¿Firma el propio paciente?</span>
                            <button
                              type="button"
                              onClick={() => setUniversalEditModal(prev => ({
                                ...prev,
                                paciente_capaz: !prev.paciente_capaz,
                                tutor: !prev.paciente_capaz ? '' : prev.tutor
                              }))}
                              className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                                universalEditModal.paciente_capaz ? 'bg-emerald-600 text-white' : 'bg-amber-500 text-white'
                              }`}
                            >
                              {universalEditModal.paciente_capaz ? 'Sí (Paciente Titular)' : 'No (Familiar / Tutor)'}
                            </button>
                          </div>
                        ) : (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded-md">
                            Menor de edad (Requiere Tutor)
                          </span>
                        )}
                      </div>

                      {universalEditModal.paciente_capaz ? (
                        <div className="p-3 bg-white rounded-xl border border-slate-200 text-slate-600">
                          <p className="text-[11px]">
                            El documento será firmado directamente por el paciente: <b>{p.name || 'PACIENTE REGISTRADO'}</b>.
                          </p>
                        </div>
                      ) : (
                        <FamiliarSelectorSection
                          label="Seleccionar Familiar o Tutor Responsable:"
                          value={universalEditModal.tutor}
                          onChangeValue={(val) => setUniversalEditModal(prev => ({ ...prev, tutor: val }))}
                          parentescoValue={universalEditModal.parentesco}
                          onChangeParentesco={(par) => setUniversalEditModal(prev => ({ ...prev, parentesco: par }))}
                          firmantesList={firmantesList}
                          required={!universalEditModal.paciente_capaz}
                        />
                      )}
                    </>
                  );
                })()}
              </div>

              {/* SECCIÓN 5: TESTIGOS PRESENCIALES */}
              <TestigosSelectorSection
                testigo1={universalEditModal.testigo1}
                parentesco1={universalEditModal.parentesco1}
                identificacion1={universalEditModal.identificacion1}
                domicilio1={universalEditModal.domicilio1}
                testigo2={universalEditModal.testigo2}
                parentesco2={universalEditModal.parentesco2}
                identificacion2={universalEditModal.identificacion2}
                domicilio2={universalEditModal.domicilio2}
                onUpdateTestigo1={({ testigo1, parentesco1, identificacion1, domicilio1 }) => {
                  setUniversalEditModal(prev => ({
                    ...prev,
                    testigo1,
                    parentesco1,
                    identificacion1,
                    domicilio1
                  }));
                }}
                onUpdateTestigo2={({ testigo2, parentesco2, identificacion2, domicilio2 }) => {
                  setUniversalEditModal(prev => ({
                    ...prev,
                    testigo2,
                    parentesco2,
                    identificacion2,
                    domicilio2
                  }));
                }}
                firmantesList={firmantesList}
                showWitness2={true}
              />

              {/* BOTONES DE ACCIÓN */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setUniversalEditModal(prev => ({ ...prev, open: false }))}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={universalEditModal.saving}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-xs font-bold bg-hes-blue-main hover:bg-hes-blue-dark shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <FiSave /> {universalEditModal.saving ? 'Guardando...' : 'Guardar Registro'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <AllergiesModal
        isOpen={allergyModal.open}
        onClose={() => setAllergyModal(prev => ({ ...prev, open: false }))}
        patientId={patientId}
        allergiesList={allergyModal.allergiesList || []}
        initialCustomText={allergyModal.customAllergiesText || ''}
        onUpdate={async () => {
          await fetchPatientAllergies();
          await fetchData();
        }}
      />

      {/* MODAL DE GESTIÓN DE FIRMANTES Y BIOMETRÍA DACTILAR (NOM-004 / VERTICAL PTCN) */}
      {firmantesModalOpen && (
        <FirmantesEpisodioModal
          open={firmantesModalOpen}
          onClose={() => {
            setFirmantesModalOpen(false);
            setSelectedFirmanteForModal(null);
          }}
          paciente={{
            id: patientId,
            nombre_completo: data?.patient?.name || 'Paciente',
            num_habitacion: data?.patient?.cama || 'Cama Virtual',
            edad: data?.patient?.age || '30'
          }}
          initialSelectedFirmante={selectedFirmanteForModal}
          onSaveSuccess={async () => {
            await fetchFirmantes();
          }}
        />
      )}

      {/* MODAL UNIVERSAL DE FIRMA DACTILAR DE PACIENTES / TUTORES / TESTIGOS */}
      {patientSignModal.open && (
        <BiometricPatientSignModal
          open={patientSignModal.open}
          onClose={() => setPatientSignModal(prev => ({ ...prev, open: false }))}
          patientId={patientId}
          documentInfo={patientSignModal.documentInfo}
          onSignSuccess={async () => {
            await fetchFirmas();
            await fetchData();
            if (fetchGenericHistory && selectedFormat) {
              await fetchGenericHistory(selectedFormat.codigo);
            }
          }}
          onOpenEnrollModal={() => setFirmantesModalOpen(true)}
          onProceedToDoctorSign={() => {
            const docInfo = patientSignModal.documentInfo || {};
            handleOpenBiometricSign(
              docInfo.slot || 0,
              docInfo.title || 'Documento Clínico',
              docInfo.content || '',
              docInfo.codigo_formato || 'HE-DIRMED-CONSUL-PLT-02',
              docInfo.tipo_documento || 'Consentimiento Informado'
            );
          }}
        />
      )}

    </div>
  );
}


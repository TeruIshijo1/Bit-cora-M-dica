import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import { useDigitalPersona } from '../hooks/useDigitalPersona';
import { useEscapeKey } from '../hooks/useEscapeKey';
import { 
  FiSearch, FiBell, FiCalendar, FiFileText, FiActivity, FiImage, 
  FiSettings, FiUser, FiMessageSquare, FiPlus, FiClock, FiChevronRight, 
  FiEdit3, FiCheckCircle, FiAlertCircle, FiScissors, FiHome, FiUsers, 
  FiFolder, FiDownload, FiCheck, FiLayers, FiSave, FiX, FiCheckSquare,
  FiArrowLeft, FiExternalLink, FiShield, FiLock, FiCopy, FiServer
} from 'react-icons/fi';
import { 
  MdOutlineBloodtype, MdOutlineMonitorHeart, MdOutlineWaterDrop, 
  MdOutlineRestaurant, MdOutlineMedicalServices, MdOutlineBiotech,
  MdFingerprint, MdVerifiedUser 
} from 'react-icons/md';
import { FaTemperatureHalf } from 'react-icons/fa6';
import AllergiesModal from '../features/ehr/modals/AllergiesModal';

export default function PatientDashboard() {
  const { pt_num } = useParams();
  const patientId = pt_num || '5704';

  const [activeTab, setActiveTab] = useState('Timeline'); // DEFAULT TAB IS TIMELINE
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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

  const canModifyOrSignDocument = (docDoctorName) => {
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
  const [firmas, setFirmas] = useState([]); // Firmas biométricas de PostgreSQL

  // Lector Biométrico DigitalPersona
  const { 
    status: dpStatus, 
    isReady: dpReady, 
    isAcquiring: dpAcquiring, 
    fmdTemplate: dpFmd, 
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
  const [selloCopiado, setSelloCopiado] = useState(false);

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

  const handleOpenAuditModal = async (firma) => {
    setAuditModal({
      open: true,
      firma: firma,
      loading: true,
      verification: null,
      copied: null,
      showVerticalQR: true
    });

    try {
      const res = await api.post(`/ehr/paciente/${patientId}/verificar-integridad`, {
        firma_id: firma.id
      });
      if (res.data) {
        setAuditModal(prev => ({
          ...prev,
          loading: false,
          verification: res.data
        }));
      }
    } catch (err) {
      console.error("Error verifying integrity in real time:", err);
      setAuditModal(prev => ({
        ...prev,
        loading: false,
        verification: {
          integro: false,
          estado: "No se pudo completar la verificación en tiempo real con el servidor."
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
    dpStartCapture();
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
    dpStartCapture();
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
    dpStartCapture();
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
  useEscapeKey(consentModal3201.open, () => setConsentModal3201(prev => ({ ...prev, open: false })));
  useEscapeKey(consentModalEED.open, () => setConsentModalEED(prev => ({ ...prev, open: false })));

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
    vitals_ta: '120/80',
    vitals_fc: '80',
    vitals_fr: '18',
    vitals_sato2: '98',
    vitals_peso: '78.5',
    vitals_talla: '1.72',
    vitals_temp: '36.5',
    subjetivo: '',
    objetivo: '',
    analisis: '',
    plan: '',
    medico: 'JOSE JOSE PRUEBA ENRIQUEZ',
    cedula: 'PRUEBA-99281',
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

  useEffect(() => {
    fetchData();
    fetchFirmas();
  }, [patientId]);

  // Manejar captura de huella para firmar documento
  const handleOpenBiometricSign = (slot, title, content, codigoFormato, tipoDocumento) => {
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
    setSelloCopiado(false);
    dpResetFmd();
    dpStartCapture();
  };

  const signingSello = signingModal.successMsg
    ? signingModal.successMsg.replace('¡Documento firmado biométricamente con éxito! Sello: ', '')
    : null;

  useEffect(() => {
    if (signingModal.open && dpFmd && !signingModal.submitting && !signingModal.successMsg) {
      const executeBiometricSign = async () => {
        try {
          setSigningModal(prev => ({ ...prev, submitting: true, errorMsg: null }));
          const res = await api.post(`/ehr/paciente/${patientId}/firmar-biometrico`, {
            codigo_formato: signingModal.codigoFormato || 'HE-DIRMED-SINPRO-PLT-87/01',
            tipo_documento: signingModal.tipoDocumento || `Nota de Evolución de Urgencias (Evolución ${signingModal.slot})`,
            evolution_slot: signingModal.slot,
            fmd_template: dpFmd,
            contenido_resumen: signingModal.content
          });
          
          if (res.data && res.data.success) {
            setSigningModal(prev => ({
              ...prev,
              submitting: false,
              successMsg: `¡Documento firmado biométricamente con éxito! Sello: ${res.data.firma.sello_digital}`
            }));
            await fetchFirmas();
            await fetchData();
            setTimeout(() => {
              setSigningModal(prev => ({ ...prev, open: false }));
              dpResetFmd();
            }, 2500);
          } else {
            setSigningModal(prev => ({ ...prev, submitting: false, errorMsg: res.data?.error || "Error al firmar documento." }));
          }
        } catch (err) {
          console.error("Error signing biometricamente:", err);
          setSigningModal(prev => ({ 
            ...prev, 
            submitting: false, 
            errorMsg: err.response?.data?.detail || "Huella no reconocida o error de conexión biométrica." 
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
            fmd_template: dpFmd
          });

          if (res.data && res.data.success) {
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
            setPrescriptionModal(prev => ({ ...prev, submitting: false, errorMsg: res.data?.error || "Error al prescribir fármaco." }));
          }
        } catch (err) {
          console.error("Error prescribiendo con huella:", err);
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
            fmd_template: dpFmd
          });
          if (res.data && res.data.success) {
            setDiscontinueModal(prev => ({ ...prev, submitting: false, successMsg: res.data.message }));
            await fetchData();
            setTimeout(() => {
              setDiscontinueModal(prev => ({ ...prev, open: false, waitingFingerprint: false, successMsg: null }));
              dpResetFmd();
            }, 1800);
          } else {
            setDiscontinueModal(prev => ({ ...prev, submitting: false, errorMsg: res.data?.error || "Error al suspender medicamento." }));
          }
        } catch (err) {
          console.error("Error suspendiendo con huella:", err);
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
            fmd_template: dpFmd
          });

          if (res.data && res.data.success) {
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
            setDietModal(prev => ({ ...prev, submitting: false, errorMsg: res.data?.error || "Error al prescribir dieta." }));
          }
        } catch (err) {
          console.error("Error prescribiendo dieta con huella:", err);
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
  const handleOpenNewEvol = (slotNum = 1) => {
    let doctorName = currentDoctorName || 'JOSE JOSE PRUEBA ENRIQUEZ';
    let doctorCed = currentDoctorCedula || 'PRUEBA-99281';

    const ptvs = data?.ptvs || {};
    const defaultTa = ptvs.ta || '120/80';
    const defaultFc = ptvs.fc || '78';
    const defaultFr = ptvs.fr || '18';
    const defaultSat = ptvs.sat_o2 || '98';
    const defaultPeso = ptvs.peso || '75.0';
    const defaultTalla = ptvs.talla || '1.72';
    const defaultTemp = ptvs.temp || '36.5';

    const now = new Date();
    setNotaModal({
      open: true,
      isEdit: false,
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
      mip: ''
    });
  };

  // Abrir modal para editar evolución existente
  const handleOpenEditEvol = (evol) => {
    if (!evol) return;
    setNotaModal({
      open: true,
      isEdit: true,
      evolution_num: evol.num || evol.evolution_num || 1,
      fecha: evol.fecha || evol.date || new Date().toISOString().split('T')[0],
      hora: evol.hora || evol.time || '12:00',
      turno: evol.turno || 'Matutino',
      vitals_ta: evol.vitals_ta || '120/80',
      vitals_fc: evol.vitals_fc || '80',
      vitals_fr: evol.vitals_fr || '18',
      vitals_sato2: evol.vitals_sato2 || '98',
      vitals_peso: evol.vitals_peso || '78.5',
      vitals_talla: evol.vitals_talla || '1.72',
      vitals_temp: evol.vitals_temp || '36.5',
      subjetivo: evol.subjetivo || evol.soap?.s || '',
      objetivo: evol.objetivo || evol.soap?.o || '',
      analisis: evol.analisis || evol.soap?.a || '',
      plan: evol.plan || evol.soap?.p || '',
      medico: evol.medico || evol.doctor || 'JOSE JOSE PRUEBA ENRIQUEZ',
      cedula: evol.cedula || 'PRUEBA-99281',
      mip: evol.mip || ''
    });
  };

  // Guardar evolución en backend / SQL Server
  const handleSaveNota = async (e) => {
    e.preventDefault();
    try {
      setSavingNota(true);
      const res = await api.post(`/ehr/paciente/${patientId}/nota-urgencias`, notaModal);
      if (res.data && (res.data.success || !res.data.error)) {
        setNotaModal(prev => ({ ...prev, open: false }));
        await fetchData();
        await fetchFirmas();
        alert(`¡Evolución ${notaModal.evolution_num} guardada con éxito en el expediente!\n(Al modificar el documento, cualquier firma digital previa se revocó conforme a la NOM)`);
      } else {
        alert(res.data?.error || "Error al guardar la nota.");
      }
    } catch (err) {
      console.error("Error saving note:", err);
      alert("Error al conectar con el servidor para guardar la nota.");
    } finally {
      setSavingNota(false);
    }
  };

  const handleOpenNewConsent25 = () => {
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    setConsentModal25({
      open: true,
      isEdit: false,
      isNew: true,
      mrnum: null,
      medico_tratante: currentDoctorName || 'JOSE JOSE PRUEBA ENRIQUEZ',
      cedula: currentDoctorCedula || '7876310/5265849',
      testigo1: data?.consentimiento_25?.testigo1 || '',
      testigo2: data?.consentimiento_25?.testigo2 || '',
      paciente_capaz: isAdult,
      pariente: '',
      paciente_o_representante: isAdult ? (p.name || '') : '',
      saving: false
    });
  };

  const handleOpenEditConsent25 = (record) => {
    const c = record || data?.consentimiento_25 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const savedRep = c.paciente_o_representante || '';
    const hasOtherRep = savedRep && savedRep !== p.name;
    setConsentModal25({
      open: true,
      isEdit: true,
      isNew: false,
      mrnum: c.mrnum || null,
      medico_tratante: c.medico_tratante || currentDoctorName || 'JOSE JOSE PRUEBA ENRIQUEZ',
      cedula: currentDoctorCedula || '7876310/5265849',
      testigo1: c.testigo1 || '',
      testigo2: c.testigo2 || '',
      paciente_capaz: isAdult ? !hasOtherRep : false,
      pariente: hasOtherRep ? savedRep : '',
      paciente_o_representante: savedRep || p.name || '',
      saving: false
    });
  };

  const handleSaveConsentModal25 = async (e) => {
    e.preventDefault();
    setConsentModal25(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = {
        is_new: Boolean(consentModal25.isNew),
        mrnum: consentModal25.mrnum,
        medico_tratante: currentDoctorName || consentModal25.medico_tratante || 'JOSE JOSE PRUEBA ENRIQUEZ',
        cedula: currentDoctorCedula || consentModal25.cedula || '7876310/5265849',
        testigo1: consentModal25.testigo1 || '',
        testigo2: consentModal25.testigo2 || '',
        paciente_o_representante: consentModal25.paciente_capaz ? (p.name || '') : (consentModal25.pariente || consentModal25.paciente_o_representante || '')
      };
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-25`, payload);
      if (res.data?.status === 'success' || res.data?.success || !res.data?.error) {
        setConsentModal25(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        if (res.data?.mrnum) {
          setSelectedMrnum25(res.data.mrnum);
        }
        alert('¡Consentimiento Formato 25 guardado con éxito en el expediente SQL Server!\n(Conforme a la NOM-024, el documento ha quedado registrado bajo tu autoría)');
      } else {
        alert(res.data?.error || 'Error al guardar el consentimiento.');
        setConsentModal25(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error('Error saving consent 25:', err);
      alert('Error al conectar con el servidor para guardar el consentimiento.');
      setConsentModal25(prev => ({ ...prev, saving: false }));
    }
  };


    const handleOpenNewConsent3201 = () => {
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    setConsentModal3201({
      open: true,
      isEdit: false,
      isNew: true,
      tipo_interrogatorio: isAdult ? 'Directo' : 'Indirecto',
      testigo1: '',
      testigo2: '',
      paciente_capaz: isAdult,
      representante_legal: '',
      paciente_o_representante: p.name || '',
      saving: false
    });
  };

  const handleOpenEditConsent3201 = () => {
    const c = data?.consentimiento_32_01 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const savedRep = c.representante_legal || '';
    const hasOtherRep = savedRep && savedRep !== p.name;
    setConsentModal3201({
      open: true,
      isEdit: true,
      isNew: false,
      tipo_interrogatorio: c.tipo_interrogatorio || consentForm3201.tipo_interrogatorio || (isAdult ? 'Directo' : 'Indirecto'),
      testigo1: c.testigo1 || consentForm3201.testigo1 || '',
      testigo2: c.testigo2 || consentForm3201.testigo2 || '',
      paciente_capaz: isAdult ? !hasOtherRep : false,
      representante_legal: savedRep,
      paciente_o_representante: c.paciente_o_representante || consentForm3201.paciente_o_representante || p.name || '',
      saving: false
    });
  };

  const handleSaveConsentModal3201 = async (e) => {
    e.preventDefault();
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
        medico_tratante: currentDoctorName || data?.patient?.attending || 'JOSE JOSE PRUEBA ENRIQUEZ',
        cedula: currentDoctorCedula || data?.patient?.cedula || 'PRUEBA-99281',
        alergias: data?.patient?.allergies || 'NEGADAS',
        diagnostico: data?.patient?.diagnostico || 'VALORACIÓN CARDIOLÓGICA'
      };
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-32-01`, payload);
      if (res.data?.success || !res.data?.error) {
        setConsentForm3201(payload);
        setConsentModal3201(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert("¡Consentimiento 32/01 guardado con éxito en el expediente SQL Server!\n(Conforme a la NOM-024, el documento ha quedado registrado bajo tu autoría)");
      } else {
        alert(res.data?.error || "Error al guardar el consentimiento.");
        setConsentModal3201(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error("Error saving consent:", err);
      alert("Error al conectar con el servidor para guardar el consentimiento.");
      setConsentModal3201(prev => ({ ...prev, saving: false }));
    }
  };


    const handleOpenNewConsentEED = () => {
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    setConsentModalEED({
      open: true, isEdit: false, isNew: true,
      tipo_interrogatorio: isAdult ? 'Directo' : 'Indirecto',
      paciente_capaz: isAdult,
      responsable: isAdult ? (p.name || '') : '',
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
    const c = data?.consentimiento_eed || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const savedResp = c.responsable || '';
    const hasOtherResp = savedResp && savedResp !== p.name;
    setConsentModalEED({
      open: true, isEdit: true, isNew: false, saving: false,
      tipo_interrogatorio: c.tipo_interrogatorio || (isAdult ? 'Directo' : 'Indirecto'),
      paciente_capaz: isAdult ? !hasOtherResp : false,
      responsable: savedResp || p.name || '',
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
    setConsentModalEED(prev => ({ ...prev, saving: true }));
    try {
      const p = data?.patient || patient || {};
      const payload = { 
        ...consentModalEED,
        is_new: Boolean(consentModalEED.isNew),
        medico: currentDoctorName || consentModalEED.medico || 'JOSE JOSE PRUEBA ENRIQUEZ',
        cedula: currentDoctorCedula || consentModalEED.cedula || 'PRUEBA-99281',
        responsable: consentModalEED.paciente_capaz ? (p.name || '') : (consentModalEED.responsable || ''),
        tipo_interrogatorio: consentModalEED.paciente_capaz ? 'Directo' : 'Indirecto'
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.isNew;
      delete payload.saving;
      const token = localStorage.getItem('token');
      const res = await api.post('/ehr/paciente/'+patientId+'/consentimiento-eed', payload, { headers: { Authorization: `Bearer ${token}` } });
      if (res.data?.success || !res.data?.error) {
        setConsentModalEED(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('Guardado con exito.');
      } else {
        alert(res.data?.error || 'Error al guardar.');
        setConsentModalEED(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al guardar.');
      setConsentModalEED(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent3401 = () => {
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const defaultTA = '120/80';
    const defaultFC = '75';
    setConsentModal3401({
      open: true,
      isEdit: false,
      isNew: true,
      medico_tratante: currentDoctorName || p.attending || 'DR. CARLOS MENDEZ CARDIOLOGO',
      cedula: currentDoctorCedula || '7876310/5265849',
      tipo_interrogatorio: isAdult ? 'DIRECTO' : 'INDIRECTO',
      paciente_capaz: isAdult,
      pariente: '',
      testigo1: data?.consentimiento_34_01?.testigo1 || data?.consentimiento_25?.testigo1 || '',
      testigo2: data?.consentimiento_34_01?.testigo2 || data?.consentimiento_25?.testigo2 || '',
      gruporh: p.grupo_rh || 'O POSITIVO',
      alergias: p.allergies || 'NEGADAS',
      ta: defaultTA,
      fc_meta: '150',
      f_resp: '18',
      temperatura: '36.5',
      peso: p.weight || '70',
      talla: p.height || '1.70',
      irm: 'Negativo para isquemia',
      fbpr: 'Respuesta vasodepresora',
      fpr: 'Normal',
      conclusiones: 'Prueba de inclinación diagnóstica para Síncope Vasovagal.',
      conclusiones_2: 'Monitoreo hemodinámico continuo satisfactorio sin arritmias ventriculares.',
      conclusiones_3: 'Se recomienda hidratación oral abundante, incremento de sal y maniobras de contrapresión.',
      ta_basal: defaultTA, fc_basal: defaultFC, obs_basal: 'Decúbito supino',
      ta_p_inicio: defaultTA, fc_p_inicio: defaultFC, obs_p_inicio: 'Inclinación a 70°',
      ta_p_2: defaultTA, fc_p_2: defaultFC, obs_p_2: 'Estable',
      ta_p_4: defaultTA, fc_p_4: defaultFC, obs_p_4: 'Estable',
      ta_p_6: defaultTA, fc_p_6: defaultFC, obs_p_6: 'Estable',
      ta_p_8: defaultTA, fc_p_8: defaultFC, obs_p_8: 'Estable',
      ta_p_10: defaultTA, fc_p_10: defaultFC, obs_p_10: 'Estable',
      ta_p_12: defaultTA, fc_p_12: defaultFC, obs_p_12: 'Estable',
      ta_p_14: defaultTA, fc_p_14: defaultFC, obs_p_14: 'Estable',
      ta_p_16: defaultTA, fc_p_16: defaultFC, obs_p_16: 'Estable',
      ta_p_18: defaultTA, fc_p_18: defaultFC, obs_p_18: 'Estable',
      ta_p_20: defaultTA, fc_p_20: defaultFC, obs_p_20: 'Estable',
      ta_a_inicio: defaultTA, fc_a_inicio: defaultFC, obs_a_inicio: 'Fase farmacológica (Aerosol)',
      ta_a_2: defaultTA, fc_a_2: defaultFC, obs_a_2: 'Estable',
      ta_a_4: defaultTA, fc_a_4: defaultFC, obs_a_4: 'Estable',
      ta_a_6: defaultTA, fc_a_6: defaultFC, obs_a_6: 'Estable',
      ta_a_8: defaultTA, fc_a_8: defaultFC, obs_a_8: 'Estable',
      ta_a_10: defaultTA, fc_a_10: defaultFC, obs_a_10: 'Estable',
      ta_a_12: defaultTA, fc_a_12: defaultFC, obs_a_12: 'Estable',
      ta_a_14: defaultTA, fc_a_14: defaultFC, obs_a_14: 'Estable',
      ta_final: defaultTA, fc_final: defaultFC, obs_final: 'Retorno a decúbito supino',
      saving: false
    });
  };

  const handleOpenEditConsent3401 = () => {
    const c = data?.consentimiento_34_01 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const savedPariente = c.pariente || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    setConsentModal3401({
      open: true,
      isEdit: true,
      saving: false,
      medico_tratante: c.medico_tratante || currentDoctorName || 'DR. CARLOS MENDEZ CARDIOLOGO',
      cedula: c.cedula || currentDoctorCedula || '7876310/5265849',
      tipo_interrogatorio: c.tipo_interrogatorio || (isAdult ? 'DIRECTO' : 'INDIRECTO'),
      paciente_capaz: isAdult ? !hasOtherPariente : false,
      pariente: savedPariente,
      testigo1: c.testigo1 || '',
      testigo2: c.testigo2 || '',
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
    setConsentModal3401(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal3401,
        medico_tratante: currentDoctorName || consentModal3401.medico_tratante || 'DR. CARLOS MENDEZ CARDIOLOGO',
        cedula: currentDoctorCedula || consentModal3401.cedula || '7876310/5265849',
        pariente: consentModal3401.paciente_capaz ? '' : (consentModal3401.pariente || ''),
        tipo_interrogatorio: consentModal3401.paciente_capaz ? 'DIRECTO' : 'INDIRECTO'
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-34-01`, payload);
      if (res.data?.status === 'success' || res.data?.success || !res.data?.error) {
        setConsentModal3401(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Consentimiento Formato 34/01 (Mesa Inclinada) guardado con éxito en el expediente SQL Server!');
      } else {
        alert(res.data?.error || 'Error al guardar el formato.');
        setConsentModal3401(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal3401(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent12 = () => {
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    setConsentModal12({
      open: true,
      isEdit: false,
      isNew: true,
      medico_tratante: currentDoctorName || p.attending || 'DR. JOSE JOSE PRUEBA ENRIQUEZ',
      cedula: currentDoctorCedula || '7876310/5265849',
      diagnostico: p.diagnostico || 'REVISIÓN GINECOLÓGICA Y OBSTÉTRICA',
      servicio: 'URGENCIAS',
      beneficios: 'Evaluación integral de la condición materno-fetal, resolución adecuada del evento obstétrico.',
      alternativas: 'Manejo médico expectante, tratamiento farmacológico alternativo o diferimiento según evolución clínica.',
      paciente_capaz: isAdult,
      pariente: '',
      testigo1: data?.consentimiento_12?.testigo1 || data?.consentimiento_25?.testigo1 || '',
      testigo2: data?.consentimiento_12?.testigo2 || data?.consentimiento_25?.testigo2 || '',
      saving: false
    });
  };

  const handleOpenEditConsent12 = (item) => {
    const c = item || data?.consentimiento_12 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const savedPariente = c.pariente || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    setConsentModal12({
      open: true,
      isEdit: true,
      isNew: false,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || 'DR. JOSE JOSE PRUEBA ENRIQUEZ',
      cedula: c.cedula || currentDoctorCedula || '7876310/5265849',
      diagnostico: c.diagnostico || p.diagnostico || 'REVISIÓN GINECOLÓGICA Y OBSTÉTRICA',
      servicio: c.servicio || 'URGENCIAS',
      beneficios: c.beneficios || 'Evaluación integral de la condición materno-fetal, resolución adecuada del evento obstétrico.',
      alternativas: c.alternativas || 'Manejo médico expectante, tratamiento farmacológico alternativo o diferimiento según evolución clínica.',
      paciente_capaz: isAdult ? !hasOtherPariente : false,
      pariente: savedPariente,
      testigo1: c.testigo1 || '',
      testigo2: c.testigo2 || '',
      saving: false
    });
  };

  const handleSaveConsentModal12 = async (e) => {
    e.preventDefault();
    setConsentModal12(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal12,
        medico_tratante: currentDoctorName || consentModal12.medico_tratante || 'DR. JOSE JOSE PRUEBA ENRIQUEZ',
        cedula: currentDoctorCedula || consentModal12.cedula || '7876310/5265849',
        pariente: consentModal12.paciente_capaz ? '' : (consentModal12.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-12`, payload);
      if (res.data?.status === 'success' || res.data?.success || !res.data?.error) {
        setConsentModal12(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Consentimiento Formato 12 (Gineco Hosp/Urg) guardado con éxito en el expediente SQL Server!');
      } else {
        alert(res.data?.error || 'Error al guardar el formato.');
        setConsentModal12(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal12(prev => ({ ...prev, saving: false }));
    }
  };

  const handleOpenNewConsent04 = () => {
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    setConsentModal04({
      open: true,
      isEdit: false,
      isNew: true,
      medico_tratante: currentDoctorName || 'DR. JOSE JOSE PRUEBA ENRIQUEZ',
      cedula: currentDoctorCedula || '7876310/5265849',
      paciente_capaz: isAdult,
      pariente: '',
      testigo1: data?.consentimiento_04?.testigo1 || data?.consentimiento_12?.testigo1 || '',
      saving: false
    });
  };

  const handleOpenEditConsent04 = (item) => {
    const c = item || data?.consentimiento_04 || {};
    const p = data?.patient || patient || {};
    const isAdult = isPatientAdult(p);
    const savedPariente = c.pariente || '';
    const hasOtherPariente = savedPariente && savedPariente !== p.name;
    setConsentModal04({
      open: true,
      isEdit: true,
      isNew: false,
      medico_tratante: c.medico_tratante || c.n_medico || currentDoctorName || 'DR. JOSE JOSE PRUEBA ENRIQUEZ',
      cedula: c.cedula || currentDoctorCedula || '7876310/5265849',
      paciente_capaz: isAdult ? !hasOtherPariente : false,
      pariente: savedPariente,
      testigo1: c.testigo1 || '',
      saving: false
    });
  };

  const handleSaveConsentModal04 = async (e) => {
    e.preventDefault();
    setConsentModal04(prev => ({ ...prev, saving: true }));
    try {
      const payload = { 
        ...consentModal04,
        medico_tratante: currentDoctorName || consentModal04.medico_tratante || 'DR. JOSE JOSE PRUEBA ENRIQUEZ',
        cedula: currentDoctorCedula || consentModal04.cedula || '7876310/5265849',
        pariente: consentModal04.paciente_capaz ? '' : (consentModal04.pariente || '')
      };
      delete payload.open;
      delete payload.isEdit;
      delete payload.saving;
      const res = await api.post(`/ehr/paciente/${patientId}/consentimiento-04`, payload);
      if (res.data?.status === 'success' || res.data?.success || !res.data?.error) {
        setConsentModal04(prev => ({ ...prev, open: false, saving: false }));
        await fetchData();
        await fetchFirmas();
        alert('¡Consentimiento Formato 04 (Catéter Venoso Central) guardado con éxito en SQL Server!');
      } else {
        alert(res.data?.error || 'Error al guardar el formato.');
        setConsentModal04(prev => ({ ...prev, saving: false }));
      }
    } catch (err) {
      console.error(err);
      alert('Error al conectar con el servidor.');
      setConsentModal04(prev => ({ ...prev, saving: false }));
    }
  };

  // Filtrado de formatos (únicamente los formatos activos / desarrollados)
  const allFormatos = formatos_disponibles
    .flatMap(cat => cat.formatos.map(f => ({ ...f, area: cat.area })))
    .filter(f => f.activo !== false);

  const availableAreas = ['Todos', ...Array.from(new Set(allFormatos.map(f => f.area)))];

  const filteredFormatos = (selectedFormatArea === 'Todos' 
    ? allFormatos 
    : allFormatos.filter(f => f.area === selectedFormatArea)
  ).filter(f => f.nombre.toLowerCase().includes(searchFormatoQuery.toLowerCase()) || f.codigo.toLowerCase().includes(searchFormatoQuery.toLowerCase()));

  const tabsList = [
    { id: 'Timeline', label: 'Timeline (Historial)', icon: <FiClock /> },
    { id: 'Formatos Clínicos', label: `Formatos Clínicos (${allFormatos.length})`, icon: <FiFileText /> },
    { id: 'Medicamentos', label: 'Medicamentos', icon: <MdOutlineMedicalServices /> },
    { id: 'Dietas y Cuidados', label: 'Dietas y Cuidados', icon: <MdOutlineRestaurant /> },
    { id: 'Laboratorios', label: 'Laboratorios', icon: <MdOutlineBiotech /> },
    { id: 'Imagenología', label: 'Imagenología', icon: <FiImage /> },
    { id: 'Agenda y Citas', label: 'Agenda y Citas', icon: <FiCalendar /> }
  ];

  return (
    <div className="flex-1 bg-slate-50/50 min-h-screen p-4 md:p-8 flex flex-col gap-6">
      
      {/* TOP BAR / BREADCRUMB */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center font-bold text-lg shadow-sm">
            {patient.name.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-800">{patient.name}</h1>
              <span className="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded border border-emerald-200">
                {patient.cama || 'Cama Virtual'}
              </span>
            </div>
            <p className="text-xs text-slate-500">Expediente: <strong className="text-slate-700">{patient.mrn}</strong> • Ingreso: {patient.fecha_ingreso} {patient.hora_ingreso}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={() => handleOpenNewEvol(evoluciones.evolucion2 ? 3 : (evoluciones.evolucion1 ? 2 : 1))}
            className="flex items-center justify-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all"
          >
            <FiEdit3 /> Nueva Evolución
          </button>
          <a 
            href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
            target="_blank" 
            rel="noreferrer"
            className="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all"
            title="Genera e imprime el documento institucional de 2 páginas con las 3 evoluciones y sello biométrico"
          >
            <FiFileText /> Imprimir Formato General (87/01)
          </a>
        </div>
      </div>

      {/* PATIENT DEMOGRAPHICS & VITALS CARD */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 pb-4 border-b border-slate-100 text-xs">
          <div>
            <span className="text-slate-400 font-medium uppercase block">Edad / Sexo</span>
            <span className="font-bold text-slate-800 text-sm">{patient.age} • {patient.gender}</span>
          </div>
          <div>
            <span className="text-slate-400 font-medium uppercase block">Fecha Nacimiento</span>
            <span className="font-bold text-slate-800 text-sm">{patient.dob}</span>
          </div>
          <div>
            <span className="text-slate-400 font-medium uppercase block">Ubicación / Cama</span>
            <span className="font-bold text-hes-blue-main text-sm">{patient.cama}</span>
          </div>
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-medium uppercase block">Alergias</span>
              <button
                type="button"
                onClick={handleOpenAllergyModal}
                className="text-[10px] font-bold text-hes-blue-main hover:underline flex items-center gap-0.5"
                title="Gestionar Alergias"
              >
                <FiEdit3 className="text-[10px]" /> Gestionar
              </button>
            </div>
            <div 
              onClick={handleOpenAllergyModal}
              className="mt-0.5 cursor-pointer font-bold text-red-600 text-xs bg-red-50 hover:bg-red-100/80 px-2 py-1 rounded-lg border border-red-100 block truncate transition-colors shadow-2xs"
              title={`${patient.allergies} (Clic para gestionar)`}
            >
              {patient.allergies || "Sin alergias registradas"}
            </div>
          </div>
          <div className="col-span-2">
            <span className="text-slate-400 font-medium uppercase block">Diagnóstico de Ingreso</span>
            <span className="font-bold text-slate-800 text-sm truncate block" title={patient.diagnostico}>{patient.diagnostico}</span>
          </div>
        </div>

        {/* VITALS SECTION HEADER */}
        <div className="flex flex-wrap items-center justify-between gap-2 mt-4 pt-3 border-t border-slate-100">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">Signos Vitales del Paciente</span>
            <span className="bg-blue-50 text-hes-blue-main text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-100 flex items-center gap-1">
              <FiActivity /> Signos Vitales
            </span>
            {data?.ptvs?.procedure_date && (
              <span className="text-[11px] text-slate-400">
                Última toma: <strong className="text-slate-600">{data.ptvs.procedure_date}</strong>
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleOpenVitalsHistory}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 text-xs font-bold transition-all border border-slate-300 shadow-sm"
              title="Ver historial cronológico de todas las tomas"
            >
              <FiClock /> Ver Historial de Signos
            </button>
            <button
              type="button"
              onClick={handleOpenVitalsModal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-hes-blue-light/60 hover:bg-hes-blue-light text-hes-blue-main text-xs font-bold transition-all border border-hes-blue-main/20 shadow-sm"
              title="Capturar o modificar signos vitales"
            >
              <FiEdit3 /> Nueva Toma de Signos
            </button>
          </div>
        </div>

        {/* VITALS ROW */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-3">
          {vitals.map((v, i) => (
            <div 
              key={i} 
              onClick={handleOpenVitalsModal}
              className="flex items-center gap-3 p-2.5 bg-slate-50 hover:bg-blue-50/60 hover:border-hes-blue-main/30 cursor-pointer rounded-xl border border-slate-100 transition-all group"
              title="Haz clic para modificar signos vitales"
            >
              <div className={`p-2 rounded-lg ${getVitalColor(v.label)} group-hover:scale-105 transition-transform`}>
                {getVitalIcon(v.label)}
              </div>
              <div>
                <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide truncate max-w-[90px]" title={v.label}>{v.label}</div>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-extrabold text-slate-800">{v.value}</span>
                  <span className="text-[10px] text-slate-500">{v.unit}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* MAIN CONTENT AREA: TABS & SIDEBAR */}
      <div className="flex flex-col xl:flex-row gap-6">
        
        {/* TABS CONTAINER */}
        <div className="flex-1">
          
          {/* TABS NAVIGATION */}
          <div className="flex gap-2 overflow-x-auto border-b border-slate-200 mb-5 pb-1">
            {tabsList.map(tab => (
              <button 
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  if (tab.id !== 'Formatos Clínicos') {
                    setSelectedFormat(null);
                  }
                }}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold whitespace-nowrap transition-all ${
                  activeTab === tab.id 
                    ? 'bg-hes-blue-main text-white shadow-sm' 
                    : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* TAB 1: TIMELINE (HISTORIAL CRONOLÓGICO) */}
          {activeTab === 'Timeline' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Línea de Tiempo del Paciente</h2>
                  <p className="text-xs text-slate-500">Historial completo y cronológico de eventos clínicos, notas y atenciones.</p>
                </div>
                <span className="text-xs bg-blue-50 text-hes-blue-main font-semibold px-3 py-1 rounded-full border border-blue-100">
                  {timelineEvents.length} Eventos Registrados
                </span>
              </div>

              <div className="space-y-6 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-200">
                {timelineEvents.length === 0 ? (
                  <div className="text-center py-8 text-slate-400 text-xs">No hay eventos clínicos registrados aún.</div>
                ) : (
                  timelineEvents.map((evt, idx) => {
                    const matchingFirma = firmas.find(f => 
                      (evt.format_code && f.codigo_formato === evt.format_code) ||
                      (evt.type?.includes('Evolución') && f.evolution_slot === (evt.type.includes('1') ? 1 : evt.type.includes('2') ? 2 : 3))
                    );
                    const isSigned = Boolean(evt.signed || matchingFirma);

                    const getBadgeClass = (badge, cat) => {
                      if (badge?.includes('87/01') || cat?.includes('Evolución')) return 'bg-blue-50 text-hes-blue-main border-blue-200';
                      if (badge?.includes('32/01') || badge?.includes('EED') || cat?.includes('Consentimiento')) return 'bg-purple-50 text-purple-700 border-purple-200';
                      if (badge?.includes('Dieta') || cat?.includes('Nutrición')) return 'bg-amber-50 text-amber-700 border-amber-200';
                      if (badge?.includes('Medicamento') || cat?.includes('Farmaco')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
                      if (badge?.includes('Signos') || cat?.includes('Monitoreo')) return 'bg-teal-50 text-teal-700 border-teal-200';
                      return 'bg-slate-100 text-slate-700 border-slate-200';
                    };

                    return (
                      <div key={evt.id || idx} className="relative flex items-start gap-4 group">
                        <div className="w-8 h-8 rounded-full bg-hes-blue-main text-white flex items-center justify-center shadow shrink-0 z-10 text-xs font-bold ring-4 ring-white">
                          {idx + 1}
                        </div>
                        <div className="flex-1 bg-slate-50 hover:bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs hover:border-hes-blue-main/40 transition-all space-y-2">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-bold text-slate-800 text-sm">{evt.type}</span>
                              {evt.badge && (
                                <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full border ${getBadgeClass(evt.badge, evt.category)}`}>
                                  {evt.badge}
                                </span>
                              )}
                              {isSigned && (
                                <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold px-2 py-0.5 rounded-full">
                                  <MdVerifiedUser className="text-emerald-600 text-xs" /> Firmado Digitalmente (NOM-024)
                                </span>
                              )}
                            </div>
                            <span className="text-xs font-semibold text-hes-blue-main bg-blue-50 px-2.5 py-0.5 rounded-md self-start sm:self-auto border border-blue-100 shrink-0">
                              {evt.date} • {evt.time}
                            </span>
                          </div>

                          <p className="text-xs text-slate-600 leading-relaxed">{evt.desc}</p>

                          {/* ACCIONES Y BOTONES DEL EVENTO */}
                          <div className="flex items-center justify-between flex-wrap gap-2 pt-2.5 mt-2 border-t border-slate-200/60">
                            <div className="flex items-center gap-3 flex-wrap">
                              {/* Acción Formato Clínico */}
                              {evt.format_code && (
                                <button 
                                  onClick={() => {
                                    const fmt = allFormatos.find(f => f.codigo === evt.format_code) || {
                                      codigo: evt.format_code,
                                      nombre: evt.type,
                                      subtitulo: 'Formato Institucional HES',
                                      area: evt.category || 'Servicios Clínicos'
                                    };
                                    setSelectedFormat(fmt);
                                    setActiveTab('Formatos Clínicos');
                                  }}
                                  className="text-xs font-bold text-hes-blue-main hover:underline flex items-center gap-1 bg-white hover:bg-blue-50/60 px-2.5 py-1 rounded-lg border border-slate-200 shadow-2xs transition-colors"
                                >
                                  Ver Formato Oficial <FiChevronRight />
                                </button>
                              )}

                              {/* Acción Imprimir PDF */}
                              {evt.pdf_url && (
                                <a 
                                  href={`${api.defaults.baseURL}${evt.pdf_url}`} 
                                  target="_blank" 
                                  rel="noreferrer"
                                  className="text-xs font-bold text-emerald-600 hover:underline flex items-center gap-1 bg-white hover:bg-emerald-50/60 px-2.5 py-1 rounded-lg border border-slate-200 shadow-2xs transition-colors"
                                >
                                  <FiDownload /> Imprimir PDF Oficial
                                </a>
                              )}

                              {/* Acción Medicamentos */}
                              {evt.action_type === 'tab_medications' && (
                                <button 
                                  onClick={() => setActiveTab('Medicamentos')}
                                  className="text-xs font-bold text-hes-blue-main hover:underline flex items-center gap-1 bg-white hover:bg-blue-50/60 px-2.5 py-1 rounded-lg border border-slate-200 shadow-2xs transition-colors"
                                >
                                  Ver en Medicamentos <FiChevronRight />
                                </button>
                              )}

                              {/* Acción Dietas */}
                              {evt.action_type === 'tab_diets' && (
                                <button 
                                  onClick={() => setActiveTab('Dietas y Cuidados')}
                                  className="text-xs font-bold text-amber-700 hover:underline flex items-center gap-1 bg-white hover:bg-amber-50/60 px-2.5 py-1 rounded-lg border border-slate-200 shadow-2xs transition-colors"
                                >
                                  Ver en Dietas y Cuidados <FiChevronRight />
                                </button>
                              )}

                              {/* Acción Signos Vitales */}
                              {evt.action_type === 'vitals_modal' && (
                                <button 
                                  onClick={handleOpenVitalsModal}
                                  className="text-xs font-bold text-teal-700 hover:underline flex items-center gap-1 bg-white hover:bg-teal-50/60 px-2.5 py-1 rounded-lg border border-slate-200 shadow-2xs transition-colors"
                                >
                                  <FiActivity /> Registrar / Modificar Signos
                                </button>
                              )}
                            </div>

                            {/* Botón de Auditoría Forense si está firmado */}
                            {matchingFirma && (
                              <button
                                type="button"
                                onClick={() => handleOpenAuditModal(matchingFirma)}
                                className="text-[10px] font-mono text-emerald-800 bg-emerald-50 hover:bg-emerald-100 px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1 transition-colors ml-auto cursor-pointer"
                                title="Verificar Sello HMAC y Auditoría NOM-024"
                              >
                                <MdFingerprint className="text-emerald-600" /> Sello NOM: {matchingFirma.sello_digital ? `${matchingFirma.sello_digital.slice(0, 14)}...` : 'Verificado'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
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
                  
                  {/* BOTÓN VOLVER Y CABECERA DEL FORMATO SELECCIONADO */}
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setSelectedFormat(null)}
                        className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3.5 py-2 rounded-xl text-xs font-bold transition-colors"
                      >
                        <FiArrowLeft /> Volver al Catálogo
                      </button>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs bg-emerald-100 text-emerald-800 font-extrabold px-2.5 py-0.5 rounded-full uppercase">Activo</span>
                          <span className="text-xs bg-blue-50 text-hes-blue-main font-semibold px-2 py-0.5 rounded border border-blue-100">{selectedFormat.codigo}</span>
                        </div>
                        <h2 className="text-lg font-bold text-slate-800 mt-0.5">{selectedFormat.nombre}</h2>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap self-end sm:self-auto">
                      {selectedFormat.codigo === 'HE-DIRMED-SINPRO-PLT-87/01' && (
                        <>
                          <button
                            onClick={() => handleOpenNewEvol(evoluciones.evolucion2 ? 3 : (evoluciones.evolucion1 ? 2 : 1))}
                            className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                          >
                            <FiPlus /> Nueva Evolución
                          </button>
                          <a 
                            href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
                            target="_blank" 
                            rel="noreferrer"
                            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                          >
                            <FiDownload /> Imprimir Formato General (3 en 1)
                          </a>
                        </>
                      )}
                      {selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-32/01' && (
                        <>
                          {data?.consentimiento_32_01 ? (
                            <button 
                              onClick={handleOpenEditConsent3201}
                              className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                            >
                              <FiEdit3 /> Editar Consentimiento
                            </button>
                          ) : (
                            <button 
                              onClick={handleOpenNewConsent3201}
                              className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                            >
                              <FiPlus /> Capturar Consentimiento
                            </button>
                          )}
                          <a 
                            href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-32-01?tipo_interrogatorio=${encodeURIComponent(consentForm3201.tipo_interrogatorio)}&testigo1=${encodeURIComponent(consentForm3201.testigo1)}&testigo2=${encodeURIComponent(consentForm3201.testigo2)}&paciente_o_representante=${encodeURIComponent(consentForm3201.paciente_o_representante || data?.patient?.name || '')}&representante_legal=${encodeURIComponent(consentForm3201.representante_legal || '')}`} 
                            target="_blank" 
                            rel="noreferrer"
                            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                          >
                            <FiDownload /> Imprimir Formato (PDF)
                          </a>
                        </>
                      )}
                      {selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-34' && (
                        <>
                          <button
                            onClick={handleOpenNewConsent3401}
                            className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                          >
                            <FiPlus /> Capturar Nuevo Consentimiento
                          </button>
                          {(data?.consentimiento_34_01 || (data?.historial_34_01 && data.historial_34_01.length > 0)) && (
                            <a 
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-34-01${selectedMrnum3401 ? `?mrnum=${selectedMrnum3401}` : ''}`} 
                              target="_blank" 
                              rel="noreferrer"
                              className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                            >
                              <FiDownload /> Imprimir Formato (PDF)
                            </a>
                          )}
                        </>
                      )}
                      {selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-25' && (
                        <>
                          <button
                            onClick={handleOpenNewConsent25}
                            className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                          >
                            <FiPlus /> Capturar Nuevo Consentimiento
                          </button>
                          {(data?.consentimiento_25 || (data?.historial_25 && data.historial_25.length > 0)) && (
                            <a 
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-25${selectedMrnum25 ? `?mrnum=${selectedMrnum25}` : ''}`} 
                              target="_blank" 
                              rel="noreferrer"
                              className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                            >
                              <FiDownload /> Imprimir Formato (PDF)
                            </a>
                          )}
                        </>
                      )}
                      {selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-12' && (
                        <>
                          <button
                            onClick={handleOpenNewConsent12}
                            className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                          >
                            <FiPlus /> Capturar Nuevo Consentimiento
                          </button>
                          {(data?.consentimiento_12 || (data?.historial_12 && data.historial_12.length > 0)) && (
                            <a 
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-12${selectedMrnum12 ? `?mrnum=${selectedMrnum12}` : ''}`} 
                              target="_blank" 
                              rel="noreferrer"
                              className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                            >
                              <FiDownload /> Imprimir Formato (PDF)
                            </a>
                          )}
                        </>
                      )}
                      {selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-04' && (
                        <>
                          <button
                            onClick={handleOpenNewConsent04}
                            className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                          >
                            <FiPlus /> Capturar Nuevo Consentimiento
                          </button>
                          {(data?.consentimiento_04 || (data?.historial_04 && data.historial_04.length > 0)) && (
                            <a 
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-04${selectedMrnum04 ? `?mrnum=${selectedMrnum04}` : ''}`} 
                              target="_blank" 
                              rel="noreferrer"
                              className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                            >
                              <FiDownload /> Imprimir Formato (PDF)
                            </a>
                          )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* VISTA DE LAS 3 EVOLUCIONES DE URGENCIAS */}
                  {selectedFormat.codigo === 'HE-DIRMED-SINPRO-PLT-87/01' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
                      <div className="pb-3 border-b border-slate-100">
                        <h3 className="font-bold text-slate-800 text-base">Evoluciones Consecutivas del Paciente (Hasta 3 notas en 1)</h3>
                        <p className="text-xs text-slate-500">Puedes capturar nuevas notas en los slots vacíos, editarlas y firmarlas con tu huella digital.</p>
                      </div>

                      <div className="grid grid-cols-1 gap-4">
                        {[1, 2, 3].map((slot) => {
                          const evolKey = `evolucion${slot}`;
                          const evolData = evoluciones[evolKey];
                          const exists = Boolean(evolData && (evolData.subjetivo || evolData.fecha));
                          
                          // Buscar si esta evolución ya tiene firma biométrica registrada en PostgreSQL
                          const firmaSlot = firmas.find(f => f.evolution_slot === slot);

                          return (
                            <div key={slot} className={`p-5 rounded-2xl border transition-all ${
                              exists ? 'border-slate-200 bg-slate-50/60' : 'border-dashed border-slate-300 bg-white/70'
                            }`}>
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 mb-3 border-b border-slate-200">
                                <div className="flex items-center gap-3">
                                  <span className={`w-8 h-8 rounded-lg font-bold flex items-center justify-center text-sm shadow-xs ${
                                    exists ? 'bg-hes-blue-main text-white' : 'bg-slate-200 text-slate-500'
                                  }`}>
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

                                    {exists ? (
                                      <div className="text-xs text-slate-500">
                                        Fecha: <span className="font-medium text-slate-700">{evolData.fecha} {evolData.hora}</span> • Turno: <span className="font-medium text-slate-700">{evolData.turno}</span>
                                      </div>
                                    ) : (
                                      <div className="text-xs text-slate-400 font-medium">Espacio disponible para captura médica subsecuente</div>
                                    )}
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {exists ? (
                                    <>
                                      {/* BOTÓN FIRMAR CON HUELLA BIOMÉTRICA */}
                                      <button
                                        onClick={() => handleOpenBiometricSign(slot, `Evolución ${slot}`, evolData.subjetivo || '')}
                                        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                          firmaSlot 
                                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100' 
                                            : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                        }`}
                                        title="Firmar electrónicamente con lector DigitalPersona"
                                      >
                                        <MdFingerprint className="text-base" /> {firmaSlot ? 'Refirmar con Huella' : 'Firmar con Huella (NOM)'}
                                      </button>

                                      <button
                                        onClick={() => handleOpenEditEvol(evolData)}
                                        className="flex items-center gap-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                      >
                                        <FiEdit3 /> Editar
                                      </button>
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias?evolucion=${slot}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white hover:bg-blue-50 text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                      >
                                        <FiFileText /> Imprimir Nota {slot}
                                      </a>
                                    </>
                                  ) : (
                                    <button
                                      onClick={() => handleOpenNewEvol(slot)}
                                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                    >
                                      <FiPlus /> Capturar Evolución {slot}
                                    </button>
                                  )}
                                </div>
                              </div>

                              {/* CONTENIDO SOAP SI EXISTE */}
                              {exists ? (
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
                                        title="Haga clic para consultar el Sello HMAC, Tríada de Seguridad y Auditoría NOM"
                                      >
                                        <MdVerifiedUser className="text-emerald-600 shrink-0 text-xs" />
                                        <span>Sello: {firmaSlot.sello_digital ? `${firmaSlot.sello_digital.slice(0, 24)}...` : 'Verificado'} • {firmaSlot.fecha_hora_firma}</span>
                                        <span className="text-[9px] font-sans font-bold text-hes-blue-main bg-blue-50 px-1.5 py-0.5 rounded ml-1">Ver Auditoría 🔍</span>
                                      </button>
                                    )}
                                  </div>
                                </div>
                              ) : (
                                <div className="py-2 text-center text-xs text-slate-400">
                                  Haz clic en <strong>"+ Capturar Evolución {slot}"</strong> para redactar la nota SOAP de este turno.
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : selectedFormat.codigo === 'HE-DIRMED-CONSUL-PLT-32/01' ? (
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
                                  const firmaConsent = firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-32/01');
                                  return firmaConsent ? (
                                    <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                      <FiCheckCircle /> Firmado Biométricamente (NOM)
                                    </span>
                                  ) : data?.consentimiento_32_01 ? (
                                    <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                      Pendiente de Firma
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 font-semibold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                      No registrado
                                    </span>
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

                          {/* ACCIONES TOP RIGHT (IDÉNTICO A NOTA DE EVOLUCIÓN 87/01) */}
                          <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                            {data?.consentimiento_32_01 ? (
                              <>
                                {(() => {
                                  const firmaConsent = firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-32/01');
                                  return (
                                    <button
                                      onClick={() => handleOpenBiometricSign(0, 'Consentimiento 32/01', JSON.stringify(consentForm3201), 'HE-DIRMED-CONSUL-PLT-32/01', 'Consentimiento Informado para Ecocardiograma Transesofágico')}
                                      className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
                                        firmaConsent 
                                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100' 
                                          : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                      }`}
                                      title="Firmar electrónicamente con lector DigitalPersona"
                                    >
                                      <MdFingerprint className="text-base" /> {firmaConsent ? 'Refirmar con Huella' : 'Firmar con Huella (NOM)'}
                                    </button>
                                  );
                                })()}
                                <button
                                  onClick={handleOpenEditConsent3201}
                                  className="flex items-center gap-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                >
                                  <FiEdit3 /> Editar
                                </button>
                                <a
                                  href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-32-01?tipo_interrogatorio=${encodeURIComponent(consentForm3201.tipo_interrogatorio)}&testigo1=${encodeURIComponent(consentForm3201.testigo1)}&testigo2=${encodeURIComponent(consentForm3201.testigo2)}&paciente_o_representante=${encodeURIComponent(consentForm3201.paciente_o_representante || data?.patient?.name || '')}&representante_legal=${encodeURIComponent(consentForm3201.representante_legal || '')}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="flex items-center gap-1 bg-white hover:bg-blue-50 text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
                                >
                                  <FiFileText /> Imprimir Formato
                                </a>
                              </>
                            ) : (
                              <button
                                onClick={handleOpenNewConsent3201}
                                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                              >
                                <FiPlus /> Capturar Consentimiento 32/01
                              </button>
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
                                <div><span className="font-semibold text-slate-500">Médico Autorizado:</span> <span className="font-bold text-slate-800">{data?.patient?.attending || 'DR. MEDICO TRATANTE'}</span> <span className="text-slate-500">(Céd. {data?.patient?.cedula || 'PRUEBA-99281'})</span></div>
                              </div>
                            </div>

                            {/* PREVIEW EN VIVO DE LA DECLARACIÓN */}
                            <div className="col-span-1 md:col-span-2 p-3.5 bg-blue-50/50 rounded-xl border border-blue-100 text-xs text-slate-700 leading-relaxed">
                              <span className="font-bold text-hes-blue-main block uppercase text-[10px] mb-1">Declaración del Procedimiento:</span>
                              <p className="italic">
                                "Yo <strong>{consentForm3201.paciente_o_representante || data?.patient?.name}</strong> en calidad de Paciente 
                                {consentForm3201.representante_legal ? <span> y <strong>{consentForm3201.representante_legal}</strong> en calidad de Representante Legal</span> : ''}, 
                                acepto voluntariamente y autorizo al Dr(a). <strong>{data?.patient?.attending}</strong> para que practique en la persona del denominado paciente el Ecocardiograma transesofágico..."
                              </p>
                            </div>

                            {/* FOOTER DE FIRMA Y MÉDICO */}
                            <div className="col-span-1 md:col-span-2 pt-2.5 border-t border-slate-200/60 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-[11px]">
                              <div>
                                Médico Responsable: <strong className="text-slate-800">{data?.patient?.attending || 'JOSE JOSE PRUEBA ENRIQUEZ'}</strong> (Céd. {data?.patient?.cedula || 'PRUEBA-99281'})
                              </div>
                              {(() => {
                                const firmaConsent = firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-32/01');
                                return firmaConsent ? (
                                  <button
                                    type="button"
                                    onClick={() => handleOpenAuditModal(firmaConsent)}
                                    className="text-emerald-700 font-mono text-[10px] bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md border border-emerald-200 flex items-center gap-1.5 transition-colors cursor-pointer text-left"
                                    title="Haga clic para consultar el Sello HMAC, Tríada de Seguridad y Auditoría NOM"
                                  >
                                    <MdVerifiedUser className="text-emerald-600 shrink-0 text-xs" />
                                    <span>Sello: {firmaConsent.sello_digital ? `${firmaConsent.sello_digital.slice(0, 24)}...` : 'Verificado'} • {firmaConsent.fecha_hora_firma}</span>
                                    <span className="text-[9px] font-sans font-bold text-hes-blue-main bg-blue-50 px-1.5 py-0.5 rounded ml-1">Ver Auditoría 🔍</span>
                                  </button>
                                ) : null;
                              })()}
                            </div>
                          </div>
                        ) : (
                          <div className="py-8 text-center text-xs text-slate-400 space-y-3">
                            <p>No se ha registrado aún el consentimiento informado para este paciente en SQL Server.</p>
                            <button
                              onClick={handleOpenNewConsent3201}
                              className="inline-flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                            >
                              <FiPlus /> Capturar Consentimiento 32/01
                            </button>
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
                        const firmaDoc25 = firmas.find(f => 
                          f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-25' && 
                          (
                            (activeDoc25?.mrnum && f.evolution_slot === activeDoc25.mrnum) ||
                            (!activeDoc25?.mrnum && f.evolution_slot === 0) ||
                            (historial25.length === 1 && f.evolution_slot === 0)
                          )
                        );
                        const isSigned25 = Boolean(activeDoc25?.firmado || activeDoc25?.signed_by || firmaDoc25);

                        return (
                          <>
                            <div className="p-4 sm:p-5 bg-gradient-to-r from-blue-50/70 via-slate-50 to-indigo-50/60 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
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
                                      {isSigned25 ? (
                                        <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          <MdVerifiedUser /> Firmado
                                        </span>
                                      ) : activeDoc25 ? (
                                        <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          Pendiente de Firma
                                        </span>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 font-semibold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          No registrado
                                        </span>
                                      )}
                                      {!isOwner25 && docDoctor25 && (
                                        <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-900 border border-amber-300 font-bold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full shadow-xs">
                                          <FiLock /> Bloqueado ({docDoctor25})
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  <button
                                    onClick={handleOpenNewConsent25}
                                    className="flex items-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                  >
                                    <FiPlus /> Capturar Nuevo Consentimiento
                                  </button>

                                  {activeDoc25 && (
                                    <>
                                      {isOwner25 ? (
                                        <>
                                          <button
                                            onClick={() => handleOpenBiometricSign(activeDoc25.mrnum || 0, 'Consentimiento Revisión Ginecológica', JSON.stringify(activeDoc25), 'HE-DIRMED-CONSUL-PLT-25', 'Consentimiento Informado')}
                                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${isSigned25 ? 'bg-emerald-50 text-emerald-700 border border-emerald-300' : 'bg-emerald-600 text-white'}`}
                                          >
                                            <MdFingerprint className="text-base" /> {isSigned25 ? 'Refirmar con Huella' : 'Firmar con Huella'}
                                          </button>
                                          <button onClick={() => handleOpenEditConsent25(activeDoc25)} className="flex items-center gap-1 bg-white border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold">
                                            <FiEdit3 /> Editar
                                          </button>
                                        </>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                          <FiLock /> Solo Lectura
                                        </span>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-25${activeDoc25.mrnum ? `?mrnum=${activeDoc25.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF
                                      </a>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES / DOCUMENTOS PREVIOS */}
                              {historial25.length > 0 && (
                                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                                  <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 uppercase">
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
                                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0 transition-all flex items-center gap-2 border text-left ${
                                            isSelected 
                                              ? 'bg-blue-600 text-white border-blue-600 shadow-xs' 
                                              : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200'
                                          }`}
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
                                  <button onClick={handleOpenNewConsent25} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                    <FiPlus /> Capturar Primer Consentimiento Formato 25
                                  </button>
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
) : selectedFormat?.codigo === 'HE-DIRMED-CONSUL-PLT-EED' ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full ring-1 ring-slate-100">
                      <div className="bg-slate-50 border-b border-slate-200 p-4 sm:p-5">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
                              <FiActivity />
                            </div>
                            <div>
                              <h3 className="font-bold text-slate-800 text-sm">{selectedFormat.nombre}</h3>
                              <div className="flex items-center gap-2 mt-1">
                                {(() => {
                                  const firma = firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-EED');
                                  return firma ? (
                                    <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                      <MdVerifiedUser /> Firmado
                                    </span>
                                  ) : data?.consentimiento_eed ? (
                                    <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                      Pendiente de Firma
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 font-semibold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                      No registrado
                                    </span>
                                  );
                                })()}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                            {(() => {
                              const docDoctorEED = data?.consentimiento_eed?.medico || data?.patient?.attending || '';
                              const isOwnerEED = canModifyOrSignDocument(docDoctorEED);
                              const firma = firmas.find(f => f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-EED');

                              return data?.consentimiento_eed ? (
                                <>
                                  {isOwnerEED ? (
                                    <>
                                      <button
                                        onClick={() => handleOpenBiometricSign(0, 'Ecocardiograma Estrés', JSON.stringify(data.consentimiento_eed), 'HE-DIRMED-CONSUL-PLT-EED', 'Consentimiento Informado')}
                                        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${firma ? 'bg-emerald-50 text-emerald-700 border border-emerald-300' : 'bg-emerald-600 text-white'}`}
                                      >
                                        <MdFingerprint className="text-base" /> {firma ? 'Refirmar con Huella' : 'Firmar con Huella'}
                                      </button>
                                      <button onClick={handleOpenEditConsentEED} className="flex items-center gap-1 bg-white border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold">
                                        <FiEdit3 /> Editar
                                      </button>
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
                                <button onClick={handleOpenNewConsentEED} className="flex items-center gap-1.5 bg-emerald-600 text-white px-4 py-1.5 rounded-lg text-xs font-bold">
                                  <FiPlus /> Capturar EED
                                </button>
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
                            <button onClick={handleOpenNewConsentEED} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                              <FiPlus /> Capturar Formato EED
                            </button>
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
                        const firmaDoc34 = firmas.find(f => 
                          (f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-34' || f.codigo_formato?.includes('34')) && 
                          (
                            (activeDoc34?.mrnum && f.evolution_slot === activeDoc34.mrnum) ||
                            (!activeDoc34?.mrnum && f.evolution_slot === 0) ||
                            (historial34.length === 1 && f.evolution_slot === 0)
                          )
                        );
                        const isSigned34 = Boolean(activeDoc34?.firmado || activeDoc34?.signed_by || firmaDoc34);

                        return (
                          <>
                            <div className="p-4 sm:p-5 bg-gradient-to-r from-blue-50/70 via-slate-50 to-indigo-50/60 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
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
                                      {isSigned34 ? (
                                        <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          <MdVerifiedUser /> Firmado
                                        </span>
                                      ) : activeDoc34 ? (
                                        <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          Pendiente de Firma
                                        </span>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 font-semibold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          No registrado
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc34 ? (
                                    <>
                                      {isOwner34 ? (
                                        <>
                                          <button
                                            onClick={() => handleOpenBiometricSign(activeDoc34.mrnum || 0, 'Mesa Inclinada (Tilt Test)', JSON.stringify(activeDoc34), 'HE-DIRMED-CONSUL-PLT-34', 'Consentimiento Informado')}
                                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${isSigned34 ? 'bg-emerald-50 text-emerald-700 border border-emerald-300' : 'bg-emerald-600 text-white'}`}
                                          >
                                            <MdFingerprint className="text-base" /> {isSigned34 ? 'Refirmar con Huella' : 'Firmar con Huella'}
                                          </button>
                                          <button
                                            onClick={() => handleOpenEditConsent3401(activeDoc34)}
                                            className="flex items-center gap-1 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold"
                                          >
                                            <FiEdit3 /> Editar
                                          </button>
                                          <button
                                            onClick={handleOpenNewConsent3401}
                                            className="flex items-center gap-1 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                          >
                                            <FiPlus /> Capturar Nuevo Consentimiento
                                          </button>
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          <button
                                            onClick={handleOpenNewConsent3401}
                                            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                          >
                                            <FiPlus /> Capturar Nuevo Consentimiento
                                          </button>
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-34-01${activeDoc34.mrnum ? `?mrnum=${activeDoc34.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    <button
                                      onClick={handleOpenNewConsent3401}
                                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                    >
                                      <FiPlus /> Capturar Mesa Inclinada
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES / DOCUMENTOS PREVIOS */}
                              {historial34.length > 0 && (
                                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                                  <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 uppercase">
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
                                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0 transition-all flex items-center gap-2 border text-left ${
                                            isSelected 
                                              ? 'bg-blue-600 text-white border-blue-600 shadow-xs' 
                                              : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200'
                                          }`}
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
                                  <button
                                    onClick={handleOpenNewConsent3401}
                                    className="inline-flex items-center gap-1 bg-amber-600 hover:bg-amber-700 text-white px-3 py-1 rounded-lg text-xs font-bold shadow-xs transition-colors shrink-0"
                                  >
                                    <FiPlus /> Capturar Nuevo Consentimiento
                                  </button>
                                </div>
                              )}

                              {activeDoc34 ? (
                                <div className="text-xs space-y-4">
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                                     <div><span className="text-slate-500 block">Médico Tratante:</span><span className="font-bold text-slate-800">{activeDoc34.medico_tratante || activeDoc34.nombre_medico_mi || 'DR. CARLOS MENDEZ'}</span></div>
                                     <div><span className="text-slate-500 block">Pariente / Representante:</span><span className="font-bold text-slate-800">{activeDoc34.pariente || data.patient.name}</span></div>
                                     <div><span className="text-slate-500 block">Signos Vitales:</span><span className="font-bold text-slate-800">TA: {activeDoc34.ta || '--'} | FC Meta: {activeDoc34.fc_meta || '--'} | FR: {activeDoc34.f_resp || '--'}</span></div>
                                  </div>
                                  <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100">
                                     <span className="text-hes-blue-main font-bold block mb-1">Conclusiones del Estudio:</span>
                                     <p className="text-slate-700">{activeDoc34.conclusiones || 'Estudio de mesa inclinada con respuesta hemodinámica normal.'}</p>
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
                                  <button onClick={handleOpenNewConsent3401} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                    <FiPlus /> Capturar Formato 34/01
                                  </button>
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
                        const firmaDoc12 = firmas.find(f => 
                          (f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-12' || f.codigo_formato?.includes('12')) && 
                          (
                            (activeDoc12?.mrnum && f.evolution_slot === activeDoc12.mrnum) ||
                            (!activeDoc12?.mrnum && f.evolution_slot === 0) ||
                            (historial12.length === 1 && f.evolution_slot === 0)
                          )
                        );
                        const isSigned12 = Boolean(activeDoc12?.firmado || activeDoc12?.signed_by || firmaDoc12);

                        return (
                          <>
                            <div className="p-4 sm:p-5 bg-gradient-to-r from-blue-50/70 via-slate-50 to-indigo-50/60 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
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
                                      {isSigned12 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc12) {
                                              handleOpenAuditModal(firmaDoc12);
                                            }
                                          }}
                                          className="inline-flex items-center gap-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> Firmado (Ver Sello)
                                        </button>
                                      ) : activeDoc12 ? (
                                        <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          Pendiente de Firma
                                        </span>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 font-semibold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          No registrado
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc12 ? (
                                    <>
                                      {isOwner12 ? (
                                        <>
                                          <button
                                            onClick={() => handleOpenBiometricSign(activeDoc12.mrnum || 0, 'Consentimiento Gineco y Obstetricia (Hosp/Urg)', JSON.stringify(activeDoc12), 'HE-DIRMED-CONSUL-PLT-12', 'Consentimiento Informado')}
                                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${isSigned12 ? 'bg-emerald-50 text-emerald-700 border border-emerald-300' : 'bg-emerald-600 text-white'}`}
                                          >
                                            <MdFingerprint className="text-base" /> {isSigned12 ? 'Refirmar con Huella' : 'Firmar con Huella'}
                                          </button>
                                          <button
                                            onClick={() => handleOpenEditConsent12(activeDoc12)}
                                            className="flex items-center gap-1 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold"
                                          >
                                            <FiEdit3 /> Editar
                                          </button>
                                          <button
                                            onClick={handleOpenNewConsent12}
                                            className="flex items-center gap-1 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                          >
                                            <FiPlus /> Capturar Nuevo Consentimiento
                                          </button>
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          <button
                                            onClick={handleOpenNewConsent12}
                                            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                          >
                                            <FiPlus /> Capturar Nuevo Consentimiento
                                          </button>
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-12${activeDoc12.mrnum ? `?mrnum=${activeDoc12.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    <button
                                      onClick={handleOpenNewConsent12}
                                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                    >
                                      <FiPlus /> Capturar Consentimiento 12
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES */}
                              {historial12.length > 0 && (
                                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                                  <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 uppercase">
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
                                          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition whitespace-nowrap ${
                                            isSelected 
                                              ? 'bg-hes-blue-main text-white shadow-sm' 
                                              : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                                          }`}
                                        >
                                          <span>Doc #{historial12.length - idx}</span>
                                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${isSelected ? 'bg-blue-800 text-white' : 'bg-slate-100 text-slate-600'}`}>
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
                                      <p className="text-sm font-extrabold text-slate-800">{activeDoc12.diagnostico || 'REVISIÓN GINECOLÓGICA Y OBSTÉTRICA'}</p>
                                      <div className="pt-2 flex items-center gap-2 text-xs">
                                        <span className="font-semibold text-slate-500">Servicio:</span>
                                        <span className="font-bold px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-[11px]">{activeDoc12.servicio || 'URGENCIAS'}</span>
                                      </div>
                                    </div>
                                    <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                                      <p className="text-[11px] font-bold text-slate-500 uppercase">Médico Tratante Responsable</p>
                                      <p className="text-sm font-extrabold text-slate-800">{activeDoc12.medico_tratante || activeDoc12.n_medico || 'DR. JOSE JOSE PRUEBA ENRIQUEZ'}</p>
                                      <p className="text-xs text-slate-600">Cédula Profesional: <span className="font-mono font-bold">{activeDoc12.cedula || '7876310/5265849'}</span></p>
                                    </div>
                                  </div>

                                  <div className="p-3.5 bg-blue-50/50 rounded-xl border border-blue-200 space-y-2 text-xs">
                                    <p className="font-bold text-hes-blue-main uppercase text-[11px]">Procedimientos e Intervenciones Proyectados</p>
                                    <p className="text-slate-700 leading-relaxed">
                                      Revisión ginecológica u obstétrica (tacto vaginal, tacto rectal, exploración mamaria), hospitalización, colocación de sondas y catéteres, aplicación de medicamentos, transfusiones sanguíneas, estudios de gabinete (ultrasonido pélvico y vaginal), tomografía abdominopélvica u otros de ser necesario.
                                    </p>
                                  </div>

                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                                      <p className="font-bold text-slate-600 text-[11px]">Beneficios Esperados</p>
                                      <p className="text-slate-700 italic">{activeDoc12.beneficios || 'Evaluación integral de la condición materno-fetal, resolución adecuada del evento obstétrico.'}</p>
                                    </div>
                                    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                                      <p className="font-bold text-slate-600 text-[11px]">Procedimientos Alternativos</p>
                                      <p className="text-slate-700 italic">{activeDoc12.alternativas || 'Manejo médico expectante, tratamiento farmacológico alternativo o diferimiento según evolución clínica.'}</p>
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
                                  <button onClick={handleOpenNewConsent12} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                    <FiPlus /> Capturar Consentimiento Formato 12
                                  </button>
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
                        const firmaDoc04 = firmas.find(f => 
                          (f.codigo_formato === 'HE-DIRMED-CONSUL-PLT-04' || f.codigo_formato?.includes('04')) && 
                          (
                            (activeDoc04?.mrnum && f.evolution_slot === activeDoc04.mrnum) ||
                            (!activeDoc04?.mrnum && f.evolution_slot === 0) ||
                            (historial04.length === 1 && f.evolution_slot === 0)
                          )
                        );
                        const isSigned04 = Boolean(activeDoc04?.firmado || activeDoc04?.signed_by || firmaDoc04);

                        return (
                          <>
                            <div className="p-4 sm:p-5 bg-gradient-to-r from-blue-50/70 via-slate-50 to-indigo-50/60 border-b border-slate-200">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 rounded-xl bg-hes-blue-main text-white flex items-center justify-center text-lg font-bold shadow-xs">
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
                                      {isSigned04 ? (
                                        <button
                                          onClick={() => {
                                            if (firmaDoc04) {
                                              handleOpenAuditModal(firmaDoc04);
                                            }
                                          }}
                                          className="inline-flex items-center gap-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full cursor-pointer transition-colors"
                                          title="Ver verificación de integridad y sello digital"
                                        >
                                          <MdVerifiedUser /> Firmado (Ver Sello)
                                        </button>
                                      ) : activeDoc04 ? (
                                        <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 font-extrabold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          Pendiente de Firma
                                        </span>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 font-semibold text-[10px] sm:text-xs px-2.5 py-0.5 rounded-full">
                                          No registrado
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                                  {activeDoc04 ? (
                                    <>
                                      {isOwner04 ? (
                                        <>
                                          <button
                                            onClick={() => handleOpenBiometricSign(activeDoc04.mrnum || 0, 'Consentimiento Colocación de Catéter Venoso Central', JSON.stringify(activeDoc04), 'HE-DIRMED-CONSUL-PLT-04', 'Consentimiento Informado')}
                                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${isSigned04 ? 'bg-emerald-50 text-emerald-700 border border-emerald-300' : 'bg-emerald-600 text-white'}`}
                                          >
                                            <MdFingerprint className="text-base" /> {isSigned04 ? 'Refirmar con Huella' : 'Firmar con Huella'}
                                          </button>
                                          <button
                                            onClick={() => handleOpenEditConsent04(activeDoc04)}
                                            className="flex items-center gap-1 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold"
                                          >
                                            <FiEdit3 /> Editar
                                          </button>
                                          <button
                                            onClick={handleOpenNewConsent04}
                                            className="flex items-center gap-1 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                          >
                                            <FiPlus /> Capturar Nuevo Consentimiento
                                          </button>
                                        </>
                                      ) : (
                                        <>
                                          <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold" title="Documento elaborado por otro médico">
                                            <FiLock /> Solo Lectura
                                          </span>
                                          <button
                                            onClick={handleOpenNewConsent04}
                                            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors"
                                          >
                                            <FiPlus /> Capturar Nuevo Consentimiento
                                          </button>
                                        </>
                                      )}
                                      <a
                                        href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-consentimiento-04${activeDoc04.mrnum ? `?mrnum=${activeDoc04.mrnum}` : ''}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-1 bg-white text-hes-blue-main border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold"
                                      >
                                        <FiFileText /> Imprimir PDF Oficial
                                      </a>
                                    </>
                                  ) : (
                                    <button
                                      onClick={handleOpenNewConsent04}
                                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-xs"
                                    >
                                      <FiPlus /> Capturar Consentimiento Formato 04
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="p-4 sm:p-5 bg-white grow flex flex-col space-y-4">
                              {/* SELECTOR DE HISTORIAL DE VERSIONES */}
                              {historial04.length > 0 && (
                                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                                  <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 uppercase">
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
                                          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition whitespace-nowrap ${
                                            isSelected 
                                              ? 'bg-hes-blue-main text-white shadow-sm' 
                                              : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                                          }`}
                                        >
                                          <span>Doc #{historial04.length - idx}</span>
                                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${isSelected ? 'bg-blue-800 text-white' : 'bg-slate-100 text-slate-600'}`}>
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
                                    <p className="text-sm font-extrabold text-slate-800">{activeDoc04.medico_tratante || activeDoc04.n_medico || 'DR. JOSE JOSE PRUEBA ENRIQUEZ'}</p>
                                    <p className="text-xs text-slate-600">Cédula Profesional: <span className="font-mono font-bold">{activeDoc04.cedula || '7876310/5265849'}</span></p>
                                  </div>

                                  <div className="p-3.5 bg-blue-50/50 rounded-xl border border-blue-200 space-y-2 text-xs">
                                    <p className="font-bold text-hes-blue-main uppercase text-[11px]">Procedimiento y Objetivo Autorizado</p>
                                    <p className="text-slate-700 leading-relaxed">
                                      Colocación de catéter en vena central o periférica por punción o venodisección para infusión de soluciones parenterales, hemoderivados, monitorización hemodinámica y toma de muestras sanguíneas.
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
                                  <button onClick={handleOpenNewConsent04} className="inline-flex items-center gap-1.5 bg-hes-blue-main text-white px-4 py-2 rounded-xl text-xs font-bold">
                                    <FiPlus /> Capturar Consentimiento Formato 04
                                  </button>
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center space-y-3">
                      <div className="w-12 h-12 rounded-full bg-blue-50 text-hes-blue-main flex items-center justify-center mx-auto text-xl font-bold">
                        <FiFolder />
                      </div>
                      <h3 className="font-bold text-slate-800 text-lg">{selectedFormat.nombre}</h3>
                      <p className="text-xs text-slate-500 max-w-md mx-auto">{selectedFormat.subtitulo}</p>
                      <span className="inline-block text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full">
                        Formato en proceso de parametrización institucional
                      </span>
                    </div>
                  )}

                </div>
              ) : (
                /* CASO B: VISTA GENERAL DE CATÁLOGO MAESTRO DE FORMATOS */
                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-slate-100">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold text-slate-800">Catálogo de Formatos Clínicos</h2>
                        <span className="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded border border-emerald-200">{allFormatos.length} Formatos Activos</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">Expediente clínico conforme a la norma NOM-004-SSA3-2012 y Calidad Institucional.</p>
                    </div>

                    {/* BUSCADOR Y FILTRO POR AREA */}
                    <div className="flex flex-col md:items-end gap-3 w-full md:w-auto">
                      <div className="relative w-full md:w-64">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <FiSearch className="text-slate-400" />
                        </div>
                        <input
                          type="text"
                          className="block w-full pl-10 pr-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-hes-blue-main focus:border-hes-blue-main"
                          placeholder="Buscar formato o código..."
                          value={searchFormatoQuery}
                          onChange={(e) => setSearchFormatoQuery(e.target.value)}
                        />
                      </div>
                      <div className="flex gap-1.5 overflow-x-auto w-full pb-1">
                        {availableAreas.map(area => (
                          <button
                            key={area}
                            onClick={() => setSelectedFormatArea(area)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-colors ${
                              selectedFormatArea === area 
                                ? 'bg-slate-800 text-white' 
                                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                          >
                            {area}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* GRID DE TODOS LOS FORMATOS */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredFormatos.map((fmt, i) => (
                      <div 
                        key={i} 
                        className={`p-5 rounded-2xl border transition-all flex flex-col justify-between cursor-pointer ${
                          fmt.activo 
                            ? 'border-emerald-200 bg-emerald-50/15 hover:border-emerald-400 hover:shadow-sm' 
                            : 'border-slate-200 bg-white hover:border-slate-300 opacity-90'
                        }`}
                        onClick={() => setSelectedFormat(fmt)}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-blue-50 text-hes-blue-main border border-blue-100">
                              {fmt.codigo}
                            </span>
                            {fmt.activo ? (
                              <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-full flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse"></span> Activo / Imprimible
                              </span>
                            ) : (
                              <span className="text-sm font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                                En Integración
                              </span>
                            )}
                          </div>
                          
                          <h3 className="font-bold text-slate-800 text-base mb-1">{fmt.nombre}</h3>
                          <p className="text-xs text-slate-500 leading-relaxed mb-3">{fmt.subtitulo}</p>
                          
                          <div className="flex items-center gap-3 text-[11px] text-slate-400 font-medium">
                            <span>Área: <strong className="text-slate-600">{fmt.area}</strong></span>
                            <span>•</span>
                            <span>{fmt.paginas} Pág(s)</span>
                            <span>•</span>
                            <span>{fmt.norma}</span>
                          </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2" onClick={e => e.stopPropagation()}>
                          {fmt.activo ? (
                            <div className="flex items-center gap-2 w-full">
                              <button
                                onClick={() => setSelectedFormat(fmt)}
                                className="flex-1 flex items-center justify-center gap-1.5 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-3 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                              >
                                <FiEdit3 /> Abrir Formato / Capturar
                              </button>
                              <a
                                href={fmt.url_pdf?.startsWith('/api') ? fmt.url_pdf : `${api.defaults.baseURL}${fmt.url_pdf}`}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center justify-center gap-1 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors"
                                title="Imprimir PDF oficial"
                              >
                                <FiDownload /> PDF
                              </a>
                            </div>
                          ) : (
                            <button 
                              onClick={() => setSelectedFormat(fmt)}
                              className="w-full text-center py-1.5 text-xs font-semibold text-slate-500 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors"
                            >
                              Ver Información del Formato
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: MEDICAMENTOS (TABLA MAESTRA PTDG - SQL SERVER) */}
          {activeTab === 'Medicamentos' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex flex-wrap justify-between items-center gap-3 pb-4 border-b border-slate-100">
                <div>
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
                <button 
                  type="button"
                  onClick={handleOpenPrescriptionModal}
                  className="flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all"
                >
                  <FiPlus className="text-sm" /> Prescribir Fármaco (Receta)
                </button>
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

                        {med.status === 'Activo' && med.ptdg_num && (
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
                    <button
                      type="button"
                      onClick={handleOpenPrescriptionModal}
                      className="inline-flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all"
                    >
                      <FiPlus /> Prescribir Primer Fármaco
                    </button>
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
                <button 
                  type="button"
                  onClick={handleOpenDietModal}
                  className="flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all"
                >
                  <FiPlus className="text-sm" /> Prescribir Dieta y Cuidados
                </button>
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

          {/* TAB 5: LABORATORIOS */}
          {activeTab === 'Laboratorios' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Estudios de Laboratorio Clínico</h2>
                  <p className="text-xs text-slate-500">Resultados, parámetros y pruebas de diagnóstico central.</p>
                </div>
                <button className="flex items-center gap-1 bg-hes-blue-main text-white px-3 py-1.5 rounded-xl text-xs font-bold">
                  <FiPlus /> Solicitar Estudio
                </button>
              </div>

              <div className="space-y-4">
                {laboratorios.map((lab) => (
                  <div key={lab.id} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/40 hover:bg-white transition-all space-y-2">
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <span className="text-xs font-bold text-hes-blue-main block">{lab.id}</span>
                        <h3 className="font-bold text-slate-800 text-base">{lab.estudio}</h3>
                        <span className="text-xs text-slate-400">Solicitado: {lab.fecha_solicitud} • Por: {lab.solicitado_por}</span>
                      </div>
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                        lab.estatus === 'Completado' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {lab.estatus}
                      </span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-100 text-xs space-y-1">
                      <div className="font-semibold text-slate-700">Resultado: {lab.resultado_resumen}</div>
                      {lab.valores_criticos && (
                        <div className="text-slate-500 font-medium">Interpretación: {lab.valores_criticos}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 6: IMAGENOLOGÍA */}
          {activeTab === 'Imagenología' && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Estudios de Imagenología y Gabinete</h2>
                  <p className="text-xs text-slate-500">Ultrasonidos, tomografías y radiografías con reporte radiológico.</p>
                </div>
                <button className="flex items-center gap-1 bg-hes-blue-main text-white px-3 py-1.5 rounded-xl text-xs font-bold">
                  <FiPlus /> Solicitar Imagen
                </button>
              </div>

              <div className="space-y-4">
                {imagenologia.map((img) => (
                  <div key={img.id} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/40 hover:bg-white transition-all space-y-3">
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <span className="text-xs font-bold text-hes-blue-main block">{img.id}</span>
                        <h3 className="font-bold text-slate-800 text-base">{img.estudio}</h3>
                        <span className="text-xs text-slate-400">Solicitado: {img.fecha_solicitud} • Por: {img.solicitado_por}</span>
                      </div>
                      <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {img.estatus}
                      </span>
                    </div>
                    <div className="p-3.5 bg-white rounded-xl border border-slate-100 text-xs space-y-2">
                      <div>
                        <strong className="text-slate-700 block mb-0.5">Hallazgos Radiológicos:</strong>
                        <p className="text-slate-600 leading-relaxed">{img.hallazgos}</p>
                      </div>
                      <div className="pt-2 border-t border-slate-100 text-hes-blue-main font-semibold">
                        Conclusión: {img.conclusion}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
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
        <div className="w-full xl:w-80 flex flex-col gap-6">
          
          {/* CHARGES & ACTIVE REQUESTS CARD */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 space-y-4">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2 pb-2 border-b border-slate-100">
              <FiLayers className="text-hes-blue-main text-base" /> Resumen de Solicitudes y Cargos
            </h3>

            {/* DIETA ACTIVA */}
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <div className="text-sm font-semibold text-slate-400 uppercase">Dieta Actual</div>
              <div className="font-bold text-slate-800 text-sm mt-0.5">{cargos_solicitudes.dieta_activa || 'Ayuno'}</div>
              <div className="text-[10px] text-red-600 font-medium">NVO / Solución IV</div>
            </div>

            {/* COUNTERS */}
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-xl bg-blue-50/50 border border-blue-100 text-center">
                <div className="text-lg font-black text-hes-blue-main">{cargos_solicitudes.laboratorios_count || 4}</div>
                <div className="text-[10px] font-bold text-slate-600 uppercase">Labs Solicitados</div>
              </div>
              <div className="p-3 rounded-xl bg-teal-50/50 border border-teal-100 text-center">
                <div className="text-lg font-black text-teal-700">{cargos_solicitudes.imagenologia_count || 2}</div>
                <div className="text-[10px] font-bold text-slate-600 uppercase">Estudios Imagen</div>
              </div>
            </div>

            {/* PENDING ITEMS */}
            <div>
              <div className="text-sm font-semibold text-slate-400 uppercase mb-2">Seguimiento en Curso</div>
              <div className="space-y-1.5 text-xs">
                {cargos_solicitudes.solicitudes_pendientes?.map((s, i) => (
                  <div key={i} className="flex justify-between items-center p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="font-medium text-slate-700">{s.titulo}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      s.estado === 'Completado' || s.estado === 'Reportado' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {s.estado}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* PROXIMA CITA */}
            {cargos_solicitudes.proxima_cita && (
              <div className="p-3 rounded-xl bg-purple-50/50 border border-purple-100 text-xs">
                <div className="text-[10px] font-bold text-purple-700 uppercase">Próxima Valoración</div>
                <div className="font-bold text-slate-800 mt-0.5">{cargos_solicitudes.proxima_cita.fecha} {cargos_solicitudes.proxima_cita.hora}</div>
                <div className="text-slate-500 text-[11px] mt-0.5">{cargos_solicitudes.proxima_cita.medico}</div>
              </div>
            )}
          </div>

          {/* QUICK ACTIONS CARD */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 space-y-2">
            <h3 className="font-bold text-slate-800 text-sm mb-3">Acciones Rápidas</h3>
            
            <button
              onClick={() => handleOpenNewEvol(evoluciones.evolucion2 ? 3 : (evoluciones.evolucion1 ? 2 : 1))}
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-hes-blue-main/30 bg-blue-50/40 hover:bg-hes-blue-main hover:text-white transition-all text-left group"
            >
              <div className="p-2 bg-hes-blue-main text-white rounded-lg group-hover:bg-white group-hover:text-hes-blue-main transition-colors"><FiEdit3 className="text-lg" /></div>
              <div>
                <div className="font-bold text-hes-blue-main text-xs group-hover:text-white">Nueva Evolución</div>
                <div className="text-[10px] text-slate-500 group-hover:text-blue-100">Capturar SOAP turno actual</div>
              </div>
            </button>

            <a 
              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
              target="_blank" 
              rel="noreferrer"
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-emerald-500/30 bg-emerald-50/50 hover:bg-emerald-600 hover:text-white transition-all text-left group"
            >
              <div className="p-2 bg-emerald-600 text-white rounded-lg group-hover:bg-white group-hover:text-emerald-600 transition-colors"><FiFileText className="text-lg" /></div>
              <div>
                <div className="font-bold text-emerald-800 text-xs group-hover:text-white">Imprimir Formato General</div>
                <div className="text-[10px] text-emerald-600 group-hover:text-emerald-100">87/01 Oficial (2 páginas)</div>
              </div>
            </a>

            <button 
              onClick={() => {
                setSelectedFormat(null);
                setActiveTab('Formatos Clínicos');
              }}
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-hes-blue-main hover:bg-blue-50/30 transition-all text-left group"
            >
              <div className="p-2 bg-slate-50 text-slate-600 rounded-lg group-hover:bg-hes-blue-main group-hover:text-white transition-colors"><FiFolder className="text-lg" /></div>
              <div>
                <div className="font-bold text-slate-800 text-xs group-hover:text-hes-blue-main">Catálogo de Formatos</div>
                <div className="text-[10px] text-slate-500">+100 Formatos Oficiales</div>
              </div>
            </button>

            <a 
              href="/agenda"
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-purple-500 hover:bg-purple-50/30 transition-all text-left group"
            >
              <div className="p-2 bg-slate-50 text-slate-600 rounded-lg group-hover:bg-purple-600 group-hover:text-white transition-colors"><FiCalendar className="text-lg" /></div>
              <div>
                <div className="font-bold text-slate-800 text-xs group-hover:text-purple-600">Agenda Médica</div>
                <div className="text-[10px] text-slate-500">Programar visitas / citas</div>
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
                <FiShield /> Firma Electrónica Avanzada NOM
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
              <p className="text-xs text-slate-500 mt-0.5">Coloque su dedo en el lector DigitalPersona para estampar la firma biométrica de la nota.</p>
            </div>

            {/* SENSOR ANIMADO */}
            <div className="py-4 flex flex-col items-center justify-center">
              <div className={`w-32 h-32 rounded-full border-4 flex items-center justify-center relative transition-all ${
                signingModal.successMsg 
                  ? 'border-emerald-500 bg-emerald-50 text-emerald-600' 
                  : dpAcquiring 
                  ? 'border-hes-blue-main bg-blue-50/60 text-hes-blue-main animate-pulse' 
                  : 'border-slate-200 bg-slate-50 text-slate-400'
              }`}>
                {dpAcquiring && (
                  <div className="absolute inset-0 rounded-full border-2 border-hes-blue-main animate-ping opacity-25"></div>
                )}
                {signingModal.successMsg ? (
                  <MdVerifiedUser className="text-6xl text-emerald-600" />
                ) : (
                  <MdFingerprint className="text-6xl" />
                )}
              </div>

              <div className="mt-4 w-full px-1 sm:px-2">
                {signingModal.successMsg ? (
                  <div className="w-full p-3 bg-emerald-50 rounded-xl border border-emerald-200 shadow-sm space-y-2">
                    <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-emerald-700 text-center">
                      <FiCheckCircle className="shrink-0" />
                      <span>¡Documento firmado biométricamente con éxito!</span>
                    </div>
                    <div className="bg-white/90 rounded-lg border border-emerald-100 p-2 space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[9px] font-black uppercase tracking-wider text-emerald-600">
                          Sello Digital HMAC-SHA512
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(signingSello || '');
                            setSelloCopiado(true);
                            setTimeout(() => setSelloCopiado(false), 2000);
                          }}
                          className="text-[9px] font-bold text-emerald-700 hover:text-emerald-900 bg-emerald-100 hover:bg-emerald-200 px-2 py-0.5 rounded-md transition-colors flex items-center gap-1 shrink-0"
                        >
                          {selloCopiado ? <FiCheck /> : <FiCopy />} {selloCopiado ? 'Copiado' : 'Copiar'}
                        </button>
                      </div>
                      <p className="text-[10px] font-mono leading-relaxed break-all text-emerald-900/80 text-left">
                        {signingSello}
                      </p>
                    </div>
                  </div>
                ) : signingModal.submitting ? (
                  <div className="text-xs font-semibold text-hes-blue-main font-bold text-center">Verificando huella dactilar y generando sello digital...</div>
                ) : dpAcquiring ? (
                  <div className="text-xs font-semibold text-hes-blue-main font-bold text-center">Esperando lectura en el sensor...</div>
                ) : (
                  <div className="text-xs font-semibold text-slate-500 text-center">{dpStatus}</div>
                )}
              </div>

              {signingModal.errorMsg && (
                <div className="mt-3 p-2.5 bg-red-50 text-red-700 rounded-xl text-xs font-semibold border border-red-200 w-full break-words text-left">
                  {signingModal.errorMsg}
                </div>
              )}
            </div>

            <div className="text-[11px] text-slate-400 bg-slate-50 p-2.5 rounded-xl border border-slate-100 text-left space-y-1">
              <div><strong>Normativa Aplicable:</strong> NOM-004-SSA3-2012 y NOM-024-SSA3-2012</div>
              <div><strong>Algoritmo Criptográfico:</strong> ECDSA P-256 (SECP256R1) + Hash SHA-256</div>
              <div><strong>Almacenamiento:</strong> Base de datos central del Hospital Escandón</div>
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
                    dpStartCapture();
                  }}
                  className="px-5 py-2 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-xs"
                >
                  Reintentar Captura
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
                  <span className="text-xs bg-blue-50 text-hes-blue-main font-bold px-2.5 py-0.5 rounded border border-blue-100">HE-DIRMED-SINPRO-PLT-87/01</span>
                  <h3 className="text-lg font-bold text-slate-800">
                    {notaModal.isEdit ? `Editar Evolución ${notaModal.evolution_num}` : `Capturar Nueva Evolución ${notaModal.evolution_num}`}
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
                  <select 
                    value={notaModal.evolution_num}
                    onChange={(e) => setNotaModal({ ...notaModal, evolution_num: parseInt(e.target.value) })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-hes-blue-main"
                  >
                    <option value={1}>Evolución 1 (Inicial)</option>
                    <option value={2}>Evolución 2 (Continuación)</option>
                    <option value={3}>Evolución 3 (Continuación)</option>
                  </select>
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
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                <div className="sm:col-span-2">
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Médico Responsable *</label>
                  <input 
                    type="text" 
                    value={notaModal.medico}
                    onChange={(e) => setNotaModal({ ...notaModal, medico: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Cédula Profesional *</label>
                  <input 
                    type="text" 
                    value={notaModal.cedula}
                    onChange={(e) => setNotaModal({ ...notaModal, cedula: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800"
                    required
                  />
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
            className="bg-white rounded-3xl w-full p-8 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <FiClock className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-slate-800">Historial Cronológico de Signos Vitales</h3>
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition"
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
                  <table className="w-full text-left text-base">
                      <thead className="bg-slate-50 text-slate-700 font-bold uppercase text-sm tracking-wider border-b border-slate-200">
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

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 94;
                        const isFever = temp && temp >= 37.8;

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
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isTaAltered ? 'bg-amber-100 text-amber-900 border border-amber-200' : 'text-slate-800'
                              }`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFcAltered ? 'bg-amber-100 text-amber-900' : 'text-slate-800'
                              }`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isSatLow ? 'bg-red-100 text-red-800 border border-red-200' : 'text-emerald-700 bg-emerald-50'
                              }`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFever ? 'bg-red-100 text-red-800' : 'text-slate-800'
                              }`}>
                                {row.temperatura}{row.temperatura !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-sm">
                              {row.peso !== '--' ? `${row.peso} kg` : '--'} / {row.talla !== '--' ? `${row.talla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="font-extrabold text-slate-700 bg-slate-100 px-3 py-1 rounded-md text-sm">
                                 {row.imc}
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
                            <div className="space-y-1 pt-1 animate-fadeIn">
                              <label className="block text-[11px] font-bold text-amber-900 uppercase">
                                Nombre del Familiar / Tutor / Representante Legal (Obligatorio)
                              </label>
                              <input
                                type="text"
                                required={!consentModalEED.paciente_capaz}
                                value={consentModalEED.responsable}
                                onChange={(e) => setConsentModalEED({ ...consentModalEED, responsable: e.target.value })}
                                placeholder="Nombre completo del familiar o representante legal responsable"
                                className="w-full border border-amber-300 bg-amber-50/50 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                              />
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5 text-amber-800 font-bold text-xs">
                              <span>⚠️ Paciente menor de edad ({data?.patient?.age || patient?.age || '—'} años)</span>
                            </div>
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900">
                              Menor de edad
                            </span>
                          </div>
                          <p className="text-[11px] text-amber-700 leading-tight">
                            Conforme a la NOM-004-SSA3-2012, el consentimiento debe ser otorgado y firmado obligatoriamente por el padre, madre, tutor o representante legal.
                          </p>
                          <div className="space-y-1 pt-1">
                            <label className="block text-[11px] font-bold text-amber-900 uppercase">
                              Padre, Madre, Tutor o Representante Legal (Obligatorio)
                            </label>
                            <input
                              type="text"
                              required
                              value={consentModalEED.responsable}
                              onChange={(e) => setConsentModalEED({ ...consentModalEED, responsable: e.target.value })}
                              placeholder="Nombre completo del padre, madre o tutor responsable"
                              className="w-full border border-amber-400 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                            />
                          </div>
                        </div>
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
            className="bg-white rounded-3xl w-full p-8 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <FiClock className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-slate-800">Historial Cronológico de Signos Vitales</h3>
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition"
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
                  <table className="w-full text-left text-base">
                      <thead className="bg-slate-50 text-slate-700 font-bold uppercase text-sm tracking-wider border-b border-slate-200">
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

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 94;
                        const isFever = temp && temp >= 37.8;

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
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isTaAltered ? 'bg-amber-100 text-amber-900 border border-amber-200' : 'text-slate-800'
                              }`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFcAltered ? 'bg-amber-100 text-amber-900' : 'text-slate-800'
                              }`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isSatLow ? 'bg-red-100 text-red-800 border border-red-200' : 'text-emerald-700 bg-emerald-50'
                              }`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFever ? 'bg-red-100 text-red-800' : 'text-slate-800'
                              }`}>
                                {row.temperatura}{row.temperatura !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-sm">
                              {row.peso !== '--' ? `${row.peso} kg` : '--'} / {row.talla !== '--' ? `${row.talla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="font-extrabold text-slate-700 bg-slate-100 px-3 py-1 rounded-md text-sm">
                                 {row.imc}
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
                        <div className="space-y-1 pt-1 animate-fadeIn">
                          <label className="block text-[11px] font-bold text-amber-900 uppercase">
                            Nombre del Familiar / Tutor / Representante Legal (Obligatorio)
                          </label>
                          <input
                            type="text"
                            required={!consentModal3201.paciente_capaz}
                            value={consentModal3201.representante_legal}
                            onChange={(e) => setConsentModal3201({ ...consentModal3201, representante_legal: e.target.value })}
                            placeholder="Nombre completo del familiar o representante legal responsable"
                            className="w-full border border-amber-300 bg-amber-50/50 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-amber-800 font-bold text-xs">
                          <span>⚠️ Paciente menor de edad ({data?.patient?.age || patient?.age || '—'} años)</span>
                        </div>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900">
                          Menor de edad
                        </span>
                      </div>
                      <p className="text-[11px] text-amber-700 leading-tight">
                        Conforme a la NOM-004-SSA3-2012, el consentimiento debe ser otorgado y firmado obligatoriamente por el padre, madre, tutor o representante legal.
                      </p>
                      <div className="space-y-1 pt-1">
                        <label className="block text-[11px] font-bold text-amber-900 uppercase">
                          Padre, Madre, Tutor o Representante Legal (Obligatorio)
                        </label>
                        <input
                          type="text"
                          required
                          value={consentModal3201.representante_legal}
                          onChange={(e) => setConsentModal3201({ ...consentModal3201, representante_legal: e.target.value })}
                          placeholder="Nombre completo del padre, madre o tutor responsable"
                          className="w-full border border-amber-400 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Testigo 1 (Nombre Completo) *</label>
                  <input 
                    type="text" 
                    value={consentModal3201.testigo1}
                    onChange={(e) => setConsentModal3201({ ...consentModal3201, testigo1: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs"
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
                    className="w-full border border-slate-200 bg-white rounded-lg px-2.5 py-1.5 text-xs"
                    placeholder="Nombre completo de Testigo 2"
                    required
                  />
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
            className="bg-white rounded-3xl w-full p-8 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <FiClock className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-slate-800">Historial Cronológico de Signos Vitales</h3>
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition"
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
                  <table className="w-full text-left text-base">
                      <thead className="bg-slate-50 text-slate-700 font-bold uppercase text-sm tracking-wider border-b border-slate-200">
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

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 94;
                        const isFever = temp && temp >= 37.8;

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
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isTaAltered ? 'bg-amber-100 text-amber-900 border border-amber-200' : 'text-slate-800'
                              }`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFcAltered ? 'bg-amber-100 text-amber-900' : 'text-slate-800'
                              }`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isSatLow ? 'bg-red-100 text-red-800 border border-red-200' : 'text-emerald-700 bg-emerald-50'
                              }`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFever ? 'bg-red-100 text-red-800' : 'text-slate-800'
                              }`}>
                                {row.temperatura}{row.temperatura !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-sm">
                              {row.peso !== '--' ? `${row.peso} kg` : '--'} / {row.talla !== '--' ? `${row.talla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="font-extrabold text-slate-700 bg-slate-100 px-3 py-1 rounded-md text-sm">
                                 {row.imc}
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
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full p-6 space-y-5 text-left my-8 max-h-[92vh] overflow-y-auto">
            
            {/* HEADER */}
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <span className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 font-bold text-xl border border-emerald-200">
                  <MdVerifiedUser />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-800">Verificación de Integridad y Sello Digital</h3>
                  <p className="text-xs text-slate-500">Expediente Clínico Electrónico — Hospital Escandón</p>
                </div>
              </div>
              <button 
                onClick={() => setAuditModal({ open: false, firma: null, loading: false, verification: null, copied: null })}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold p-1"
              >
                <FiX />
              </button>
            </div>

            {/* ESTADO EN VIVO DE VERIFICACIÓN CRIPTOGRÁFICA */}
            {auditModal.loading ? (
              <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 flex items-center gap-3 animate-pulse">
                <div className="w-5 h-5 border-2 border-hes-blue-main border-t-transparent rounded-full animate-spin"></div>
                <div className="text-xs font-semibold text-hes-blue-main">
                  Recalculando hashes matemáticos y verificando integridad criptográfica en tiempo real...
                </div>
              </div>
            ) : auditModal.verification?.integro ? (
              <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <FiCheckCircle className="text-emerald-600 text-2xl shrink-0" />
                  <div>
                    <span className="font-extrabold text-emerald-900 text-sm block">Firma íntegra y verificable</span>
                    <span className="text-xs text-emerald-700">El recálculo criptográfico en vivo confirma que el documento no ha sido alterado ni modificado.</span>
                  </div>
                </div>
                <span className="text-[11px] font-extrabold bg-emerald-200/90 text-emerald-950 px-3 py-1 rounded-full border border-emerald-300 self-end sm:self-auto">
                  ✓ Verificación Exitosa
                </span>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-red-50 border border-red-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <FiAlertCircle className="text-red-600 text-2xl shrink-0" />
                  <div>
                    <span className="font-extrabold text-red-900 text-sm block">Integridad invalidada</span>
                    <span className="text-xs text-red-700">Discrepancia detectada: el contenido actual del documento difiere del estado al momento de firmar.</span>
                  </div>
                </div>
                <span className="text-[11px] font-extrabold bg-red-200 text-red-900 px-3 py-1 rounded-full border border-red-300 self-end sm:self-auto">
                  ⚠ Alerta de Seguridad
                </span>
              </div>
            )}

            {/* TRÍADA EXPLÍCITA DE SEGURIDAD (3 TARJETAS) */}
            <div className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                Tríada de Seguridad Criptográfica
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                
                {/* 1. IDENTIDAD */}
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex items-center gap-1.5 text-hes-blue-main font-bold text-xs uppercase">
                    <FiUser /> 1. Identidad del Firmante
                  </div>
                  <div className="font-semibold text-slate-800">{auditModal.firma.nombre_medico}</div>
                  <div className="text-[11px] text-slate-500">Céd. Prof. <strong className="text-slate-700">{auditModal.firma.cedula_profesional}</strong></div>
                  <div className="text-[10px] text-emerald-700 font-medium pt-1 border-t border-slate-200/60">
                    Comprobada mediante Biometría Dactilar DigitalPersona (FMD ANSI 378-2004)
                  </div>
                </div>

                {/* 2. INTEGRIDAD */}
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex items-center gap-1.5 text-hes-blue-main font-bold text-xs uppercase">
                    <FiShield /> 2. Integridad del Documento
                  </div>
                  <div className="font-semibold text-slate-800">Función Hash SHA-256</div>
                  <div className="text-[11px] text-slate-500">Recalculado sobre Cadena Original</div>
                  <div className="text-[10px] text-emerald-700 font-medium pt-1 border-t border-slate-200/60">
                    Garantiza inalterabilidad total del texto y signos vitales
                  </div>
                </div>

                {/* 3. AUTENTICIDAD Y NO REPUDIO */}
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex items-center gap-1.5 text-hes-blue-main font-bold text-xs uppercase">
                    <FiLock /> 3. Autenticidad y No Repudio
                  </div>
                  <div className="font-semibold text-slate-800">
                    {(auditModal.firma.sello_digital || '').startsWith('ECDSA:') ? 'Firma ECDSA P-256' : 'Sello HMAC-SHA512 (Legacy)'}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {(auditModal.firma.sello_digital || '').startsWith('ECDSA:') ? 'Clave privada asimétrica exclusiva del firmante' : 'Generado con Clave Criptográfica institucional'}
                  </div>
                  <div className="text-[10px] text-emerald-700 font-medium pt-1 border-t border-slate-200/60">
                    Imposibilidad de falsificación o suplantación pericial
                  </div>
                </div>

              </div>
            </div>

            {/* SECCIÓN FIRMA Y CÓDIGO QR DE VERTICAL (EHR HOST) */}
            {auditModal.verification?.firma_vertical?.disponible && (
              <div className="p-4 bg-gradient-to-r from-blue-50/90 to-indigo-50/80 border border-blue-200/80 rounded-2xl space-y-3 shadow-sm">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-hes-blue-main text-white flex items-center justify-center font-bold text-sm shadow-sm shrink-0">
                      <FiServer />
                    </div>
                    <div>
                      <div className="font-bold text-slate-800 text-xs uppercase tracking-wide flex items-center gap-1.5">
                        Firma Vertical (EHR Host)
                        <span className="text-[10px] font-black bg-blue-100 text-blue-800 border border-blue-300 px-2 py-0.5 rounded-full">
                          ✓ Sincronizado
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500">
                        Firmado por: <strong className="text-slate-700">{auditModal.verification.firma_vertical.firmado_por}</strong>
                        {auditModal.verification.firma_vertical.fecha_firma && ` • ${auditModal.verification.firma_vertical.fecha_firma}`}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setAuditModal(prev => ({ ...prev, showVerticalQR: !prev.showVerticalQR }))}
                    className="text-xs font-bold bg-white text-hes-blue-main hover:bg-blue-50 border border-blue-300 px-3 py-1.5 rounded-xl transition flex items-center gap-1.5 shadow-sm"
                  >
                    <FiExternalLink /> {auditModal.showVerticalQR ? 'Ocultar QR' : 'Firma Vertical (Ver QR)'}
                  </button>
                </div>

                {auditModal.showVerticalQR && (
                  <div className="pt-2 border-t border-blue-200/60 flex flex-col sm:flex-row items-center gap-4 bg-white/80 p-3 rounded-xl">
                    {auditModal.verification.firma_vertical.qr_data_url ? (
                      <div className="flex flex-col items-center gap-1 bg-white p-2.5 rounded-xl border border-slate-200 shadow-sm shrink-0">
                        <img
                          src={auditModal.verification.firma_vertical.qr_data_url}
                          alt="Código QR Vertical"
                          className="w-36 h-36 object-contain"
                        />
                        <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider font-semibold">QR Oficial Vertical</span>
                      </div>
                    ) : (
                      <div className="w-36 h-36 flex items-center justify-center bg-slate-100 rounded-xl text-slate-400 text-xs">
                        QR no disponible
                      </div>
                    )}

                    <div className="flex-1 space-y-1.5 w-full text-xs">
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="font-bold text-slate-700">Token Criptográfico Vertical</span>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(auditModal.verification.firma_vertical.cadena_firma || '');
                            setAuditModal(prev => ({ ...prev, copied: 'vertical' }));
                            setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                          }}
                          className="text-[11px] font-bold text-hes-blue-main hover:underline flex items-center gap-1"
                        >
                          <FiCheckSquare /> {auditModal.copied === 'vertical' ? '¡Copiado!' : 'Copiar Token'}
                        </button>
                      </div>
                      <div className="p-2.5 bg-slate-900 text-blue-300 font-mono text-[10px] rounded-xl break-all select-all shadow-inner max-h-24 overflow-y-auto leading-relaxed">
                        {auditModal.verification.firma_vertical.cadena_firma}
                      </div>
                      <p className="text-[10px] text-slate-500">
                        Este código QR y token corresponden al registro nativo en el servidor EHR de Vertical para este documento.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* SELLO CRIPTOGRÁFICO DIGITAL */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-bold text-slate-700 uppercase tracking-wide flex items-center gap-1.5">
                  <FiLock className="text-hes-blue-main" /> {(auditModal.firma.sello_digital || '').startsWith('ECDSA:') ? 'Sello Digital ECDSA P-256' : 'Sello Criptográfico HMAC-SHA512 (Legacy)'}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(auditModal.firma.sello_digital || '');
                    setAuditModal(prev => ({ ...prev, copied: 'sello' }));
                    setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                  }}
                  className="text-xs font-bold text-hes-blue-main hover:underline flex items-center gap-1"
                >
                  <FiCheckSquare /> {auditModal.copied === 'sello' ? '¡Copiado al portapapeles!' : 'Copiar Sello Completo'}
                </button>
              </div>
              <div className="p-3 bg-slate-900 text-emerald-400 font-mono text-[11px] rounded-xl break-all leading-relaxed select-all shadow-inner">
                {auditModal.firma.sello_digital || 'No disponible'}
              </div>
            </div>

            {/* HASH SHA-256 DE INTEGRIDAD DOCUMENTAL */}
            {auditModal.firma.hash_sha256 && (
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wide flex items-center gap-1.5">
                    <FiShield className="text-hes-blue-main" /> Hash SHA-256 de Integridad Documental
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(auditModal.firma.hash_sha256 || '');
                      setAuditModal(prev => ({ ...prev, copied: 'hash' }));
                      setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                    }}
                    className="text-xs font-bold text-hes-blue-main hover:underline flex items-center gap-1"
                  >
                    <FiCheckSquare /> {auditModal.copied === 'hash' ? '¡Copiado!' : 'Copiar Hash'}
                  </button>
                </div>
                <div className="p-2.5 bg-slate-100 text-slate-800 font-mono text-[11px] rounded-xl break-all select-all border border-slate-200">
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
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wide">
                    Cadena Original Normalizada
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(auditModal.verification?.cadena_original || auditModal.firma.cadena_original || '');
                      setAuditModal(prev => ({ ...prev, copied: 'cadena' }));
                      setTimeout(() => setAuditModal(prev => ({ ...prev, copied: null })), 2000);
                    }}
                    className="text-xs font-bold text-hes-blue-main hover:underline flex items-center gap-1"
                  >
                    <FiCheckSquare /> {auditModal.copied === 'cadena' ? '¡Copiado!' : 'Copiar Cadena'}
                  </button>
                </div>
                <div className="p-2.5 bg-slate-50 text-slate-600 font-mono text-[10px] rounded-xl break-all select-all border border-slate-200 max-h-20 overflow-y-auto">
                  {auditModal.verification?.cadena_original || auditModal.firma.cadena_original}
                </div>
              </div>
            )}

            {/* FOOTER Y MARCO NORMATIVO */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pt-3 border-t border-slate-100 text-xs">
              <div className="text-slate-500 font-medium">
                <strong>Marco Normativo de Referencia:</strong> NOM-004-SSA3-2012 / NOM-024-SSA3-2012
              </div>
              <button
                type="button"
                onClick={() => setAuditModal({ open: false, firma: null, loading: false, verification: null, copied: null })}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold transition-colors self-end sm:self-auto"
              >
                Cerrar Verificación
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
                  <FiSave /> {vitalsModal.submitting ? 'Guardando...' : 'Guardar y Sincronizar'}
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
            className="bg-white rounded-3xl w-full p-8 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <FiClock className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-slate-800">Historial Cronológico de Signos Vitales</h3>
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition"
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
                  <table className="w-full text-left text-base">
                      <thead className="bg-slate-50 text-slate-700 font-bold uppercase text-sm tracking-wider border-b border-slate-200">
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

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 94;
                        const isFever = temp && temp >= 37.8;

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
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isTaAltered ? 'bg-amber-100 text-amber-900 border border-amber-200' : 'text-slate-800'
                              }`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFcAltered ? 'bg-amber-100 text-amber-900' : 'text-slate-800'
                              }`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isSatLow ? 'bg-red-100 text-red-800 border border-red-200' : 'text-emerald-700 bg-emerald-50'
                              }`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFever ? 'bg-red-100 text-red-800' : 'text-slate-800'
                              }`}>
                                {row.temperatura}{row.temperatura !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-sm">
                              {row.peso !== '--' ? `${row.peso} kg` : '--'} / {row.talla !== '--' ? `${row.talla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="font-extrabold text-slate-700 bg-slate-100 px-3 py-1 rounded-md text-sm">
                                 {row.imc}
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
                  <MdFingerprint className="text-xl" /> Firma Biométrica Obligatoria (NOM-004 / NOM-024)
                </div>
                
                {prescriptionModal.waitingFingerprint ? (
                  <div className="space-y-2 py-2 animate-fadeIn">
                    <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mx-auto text-hes-blue-main animate-pulse shadow-inner">
                      <MdFingerprint className="text-3xl animate-bounce" />
                    </div>
                    <p className="text-xs font-bold text-slate-700">
                      Coloque su dedo en el lector DigitalPersona...
                    </p>
                    <p className="text-[11px] text-slate-500">
                      El sistema validará su huella dactilar, estampará el sello criptográfico y registrará el medicamento.
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 max-w-md">
                    Al confirmar, se activará el lector de huella para validar la autoría médica y estampar el sello digital de la receta.
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
                    ? (prescriptionModal.submitting ? 'Verificando huella y firmando...' : 'Esperando huella dactilar...') 
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
            className="bg-white rounded-3xl w-full p-8 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <FiClock className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-slate-800">Historial Cronológico de Signos Vitales</h3>
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition"
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
                  <table className="w-full text-left text-base">
                      <thead className="bg-slate-50 text-slate-700 font-bold uppercase text-sm tracking-wider border-b border-slate-200">
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

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 94;
                        const isFever = temp && temp >= 37.8;

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
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isTaAltered ? 'bg-amber-100 text-amber-900 border border-amber-200' : 'text-slate-800'
                              }`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFcAltered ? 'bg-amber-100 text-amber-900' : 'text-slate-800'
                              }`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isSatLow ? 'bg-red-100 text-red-800 border border-red-200' : 'text-emerald-700 bg-emerald-50'
                              }`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFever ? 'bg-red-100 text-red-800' : 'text-slate-800'
                              }`}>
                                {row.temperatura}{row.temperatura !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-sm">
                              {row.peso !== '--' ? `${row.peso} kg` : '--'} / {row.talla !== '--' ? `${row.talla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="font-extrabold text-slate-700 bg-slate-100 px-3 py-1 rounded-md text-sm">
                                 {row.imc}
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
            className="bg-white rounded-3xl w-full p-8 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <FiClock className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-slate-800">Historial Cronológico de Signos Vitales</h3>
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition"
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
                  <table className="w-full text-left text-base">
                      <thead className="bg-slate-50 text-slate-700 font-bold uppercase text-sm tracking-wider border-b border-slate-200">
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

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 94;
                        const isFever = temp && temp >= 37.8;

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
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isTaAltered ? 'bg-amber-100 text-amber-900 border border-amber-200' : 'text-slate-800'
                              }`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFcAltered ? 'bg-amber-100 text-amber-900' : 'text-slate-800'
                              }`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isSatLow ? 'bg-red-100 text-red-800 border border-red-200' : 'text-emerald-700 bg-emerald-50'
                              }`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFever ? 'bg-red-100 text-red-800' : 'text-slate-800'
                              }`}>
                                {row.temperatura}{row.temperatura !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-sm">
                              {row.peso !== '--' ? `${row.peso} kg` : '--'} / {row.talla !== '--' ? `${row.talla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="font-extrabold text-slate-700 bg-slate-100 px-3 py-1 rounded-md text-sm">
                                 {row.imc}
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
                  <MdFingerprint className="text-xl" /> Firma Biométrica Obligatoria (NOM-004 / NOM-024)
                </div>
                
                {dietModal.waitingFingerprint ? (
                  <div className="space-y-2 py-2 animate-fadeIn">
                    <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mx-auto text-hes-blue-main animate-pulse shadow-inner">
                      <MdFingerprint className="text-3xl animate-bounce" />
                    </div>
                    <p className="text-xs font-bold text-slate-700">
                      Coloque su dedo en el lector DigitalPersona...
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Se validará su identidad médica, estampará el sello criptográfico y guardará el régimen dietético.
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 max-w-md">
                    Al confirmar, se activará el lector de huella para validar la autoría médica y estampar el sello digital.
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
                    ? (dietModal.submitting ? 'Verificando huella y firmando...' : 'Esperando huella dactilar...') 
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
            className="bg-white rounded-3xl w-full p-8 shadow-2xl border border-slate-100 space-y-4 animate-scaleUp max-h-[95vh] flex flex-col"
            style={{ width: `min(97vw, ${Math.max(60, Math.min(97, 50 + vitalsHistoryModal.history.length * 2.5))}vw)` }}
          >
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-50 text-hes-blue-main rounded-2xl">
                  <FiClock className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-slate-800">Historial Cronológico de Signos Vitales</h3>
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-hes-blue-main hover:bg-hes-blue-dark text-white text-xs font-bold shadow-sm transition"
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
                  <table className="w-full text-left text-base">
                      <thead className="bg-slate-50 text-slate-700 font-bold uppercase text-sm tracking-wider border-b border-slate-200">
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

                        const isTaAltered = (sys && (sys > 139 || sys < 90)) || (dia && (dia > 89 || dia < 60));
                        const isFcAltered = fc && (fc > 100 || fc < 60);
                        const isSatLow = sat && sat < 94;
                        const isFever = temp && temp >= 37.8;

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
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isTaAltered ? 'bg-amber-100 text-amber-900 border border-amber-200' : 'text-slate-800'
                              }`}>
                                {row.ta}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFcAltered ? 'bg-amber-100 text-amber-900' : 'text-slate-800'
                              }`}>
                                {row.fc}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center text-slate-800 font-bold whitespace-nowrap">
                              {row.fr}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isSatLow ? 'bg-red-100 text-red-800 border border-red-200' : 'text-emerald-700 bg-emerald-50'
                              }`}>
                                {row.sat_o2}{row.sat_o2 !== '--' ? '%' : ''}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-md font-bold text-sm ${
                                isFever ? 'bg-red-100 text-red-800' : 'text-slate-800'
                              }`}>
                                {row.temperatura}{row.temperatura !== '--' ? '°' : ''}
                              </span>
                            </td>
                              <td className="py-3 px-4 text-center text-slate-600 whitespace-nowrap text-sm">
                              {row.peso !== '--' ? `${row.peso} kg` : '--'} / {row.talla !== '--' ? `${row.talla} m` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                <span className="font-extrabold text-slate-700 bg-slate-100 px-3 py-1 rounded-md text-sm">
                                 {row.imc}
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
                    value={currentDoctorName || consentModal25.medico_tratante || 'JOSE JOSE PRUEBA ENRIQUEZ'}
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
                    value={currentDoctorCedula || consentModal25.cedula || '7876310/5265849'}
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
                        <div className="space-y-1 pt-1 animate-fadeIn">
                          <label className="block text-[11px] font-bold text-amber-900 uppercase">
                            Nombre del Familiar / Tutor / Representante Legal (Obligatorio)
                          </label>
                          <input
                            type="text"
                            required={!consentModal25.paciente_capaz}
                            value={consentModal25.pariente}
                            onChange={(e) => setConsentModal25({ ...consentModal25, pariente: e.target.value, paciente_o_representante: e.target.value })}
                            placeholder="Nombre completo del familiar o representante legal responsable"
                            className="w-full border border-amber-300 bg-amber-50/50 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-amber-800 font-bold text-xs">
                          <span>⚠️ Paciente menor de edad ({data?.patient?.age || patient?.age || '—'} años)</span>
                        </div>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900">
                          Menor de edad
                        </span>
                      </div>
                      <p className="text-[11px] text-amber-700 leading-tight">
                        Conforme a la NOM-004-SSA3-2012, el consentimiento debe ser otorgado y firmado obligatoriamente por el padre, madre, tutor o representante legal.
                      </p>
                      <div className="space-y-1 pt-1">
                        <label className="block text-[11px] font-bold text-amber-900 uppercase">
                          Padre, Madre, Tutor o Representante Legal (Obligatorio)
                        </label>
                        <input
                          type="text"
                          required
                          value={consentModal25.pariente}
                          onChange={(e) => setConsentModal25({ ...consentModal25, pariente: e.target.value, paciente_o_representante: e.target.value })}
                          placeholder="Nombre completo del padre, madre o tutor responsable"
                          className="w-full border border-amber-400 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                        />
                      </div>
                    </div>
                  )}
                </div>

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
                  <FiSave /> {consentModal25.saving ? 'Guardando...' : 'Guardar y Sincronizar'}
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
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-3">
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
                      value={currentDoctorName || consentModal3401.medico_tratante || 'DR. CARLOS MENDEZ CARDIOLOGO'}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Cédula Profesional</label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal3401.cedula || '7876310/5265849'}
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
                        <div className="space-y-1 pt-1 animate-fadeIn">
                          <label className="block text-[11px] font-bold text-amber-900 uppercase">
                            Nombre del Familiar / Tutor / Representante Legal (Obligatorio)
                          </label>
                          <input
                            type="text"
                            required={!consentModal3401.paciente_capaz}
                            value={consentModal3401.pariente}
                            onChange={(e) => setConsentModal3401({ ...consentModal3401, pariente: e.target.value })}
                            placeholder="Nombre completo del familiar o representante legal responsable"
                            className="w-full border border-amber-300 bg-amber-50/50 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-amber-800 font-bold text-xs">
                          <span>⚠️ Paciente menor de edad ({data?.patient?.age || patient?.age || '—'} años)</span>
                        </div>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900">
                          Menor de edad
                        </span>
                      </div>
                      <p className="text-[11px] text-amber-700 leading-tight">
                        Conforme a la NOM-004-SSA3-2012, el consentimiento debe ser otorgado y firmado obligatoriamente por el padre, madre, tutor o representante legal.
                      </p>
                      <div className="space-y-1 pt-1">
                        <label className="block text-[11px] font-bold text-amber-900 uppercase">
                          Padre, Madre, Tutor o Representante Legal (Obligatorio)
                        </label>
                        <input
                          type="text"
                          required
                          value={consentModal3401.pariente}
                          onChange={(e) => setConsentModal3401({ ...consentModal3401, pariente: e.target.value })}
                          placeholder="Nombre completo del padre, madre o tutor responsable"
                          className="w-full border border-amber-400 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                        />
                      </div>
                    </div>
                  )}
                </div>

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
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-3">
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
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-3">
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
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-3">
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
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-3">
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
                  <FiSave /> {consentModal3401.saving ? 'Guardando...' : 'Guardar y Sincronizar'}
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
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-3">
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
                      value={currentDoctorName || consentModal12.medico_tratante || 'DR. JOSE JOSE PRUEBA ENRIQUEZ'}
                      readOnly
                      className="w-full border border-slate-200 bg-slate-100 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold cursor-not-allowed outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Cédula Profesional</label>
                    <input
                      type="text"
                      value={currentDoctorCedula || consentModal12.cedula || '7876310/5265849'}
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
                        <div className="space-y-1 pt-1 animate-fadeIn">
                          <label className="block text-[11px] font-bold text-amber-900 uppercase">
                            Nombre del Familiar / Tutor / Representante Legal (Obligatorio)
                          </label>
                          <input
                            type="text"
                            required={!consentModal12.paciente_capaz}
                            value={consentModal12.pariente}
                            onChange={(e) => setConsentModal12({ ...consentModal12, pariente: e.target.value })}
                            placeholder="Nombre completo del familiar o representante legal responsable"
                            className="w-full border border-amber-300 bg-amber-50/50 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-amber-800 font-bold text-xs">
                          <span>⚠️ Paciente menor de edad ({data?.patient?.age || patient?.age || '—'} años)</span>
                        </div>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900">
                          Menor de edad
                        </span>
                      </div>
                      <p className="text-[11px] text-amber-700 leading-tight">
                        Conforme a la NOM-004-SSA3-2012, el consentimiento debe ser otorgado y firmado obligatoriamente por el padre, madre, tutor o representante legal.
                      </p>
                      <div className="space-y-1 pt-1">
                        <label className="block text-[11px] font-bold text-amber-900 uppercase">
                          Padre, Madre, Tutor o Representante Legal (Obligatorio)
                        </label>
                        <input
                          type="text"
                          required
                          value={consentModal12.pariente}
                          onChange={(e) => setConsentModal12({ ...consentModal12, pariente: e.target.value })}
                          placeholder="Nombre completo del padre, madre o tutor responsable"
                          className="w-full border border-amber-400 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                        />
                      </div>
                    </div>
                  )}
                </div>

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
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-3">
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
                  <FiSave /> {consentModal12.saving ? 'Guardando...' : 'Guardar y Sincronizar'}
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
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-3">
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
                      value={currentDoctorName || consentModal04.medico_tratante || 'DR. JOSE JOSE PRUEBA ENRIQUEZ'}
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
                      value={currentDoctorCedula || consentModal04.cedula || '7876310/5265849'}
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
                        <div className="space-y-1 pt-1 animate-fadeIn">
                          <label className="block text-[11px] font-bold text-amber-900 uppercase">
                            Nombre del Familiar / Tutor / Representante Legal (Obligatorio)
                          </label>
                          <input
                            type="text"
                            required={!consentModal04.paciente_capaz}
                            value={consentModal04.pariente}
                            onChange={(e) => setConsentModal04({ ...consentModal04, pariente: e.target.value })}
                            placeholder="Nombre completo del familiar o representante legal responsable"
                            className="w-full border border-amber-300 bg-amber-50/50 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-amber-800 font-bold text-xs">
                          <span>⚠️ Paciente menor de edad ({data?.patient?.age || patient?.age || '—'} años)</span>
                        </div>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900">
                          Menor de edad
                        </span>
                      </div>
                      <p className="text-[11px] text-amber-700 leading-tight">
                        Conforme a la NOM-004-SSA3-2012, el consentimiento debe ser otorgado y firmado obligatoriamente por el padre, madre, tutor o representante legal.
                      </p>
                      <div className="space-y-1 pt-1">
                        <label className="block text-[11px] font-bold text-amber-900 uppercase">
                          Padre, Madre, Tutor o Representante Legal (Obligatorio)
                        </label>
                        <input
                          type="text"
                          required
                          value={consentModal04.pariente}
                          onChange={(e) => setConsentModal04({ ...consentModal04, pariente: e.target.value })}
                          placeholder="Nombre completo del padre, madre o tutor responsable"
                          className="w-full border border-amber-400 bg-white rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-hes-blue-main outline-none"
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Nombre Completo del Testigo</label>
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
                  <FiSave /> {consentModal04.saving ? 'Guardando...' : 'Guardar y Sincronizar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL DE GESTIÓN DE ALERGIAS (MODULARIZADO) */}
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

    </div>
  );
}


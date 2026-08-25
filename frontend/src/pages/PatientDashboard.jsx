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
  FiArrowLeft, FiExternalLink, FiShield, FiLock, FiCopy
} from 'react-icons/fi';
import { 
  MdOutlineBloodtype, MdOutlineMonitorHeart, MdOutlineWaterDrop, 
  MdOutlineRestaurant, MdOutlineMedicalServices, MdOutlineBiotech,
  MdFingerprint, MdVerifiedUser 
} from 'react-icons/md';
import { FaTemperatureHalf } from 'react-icons/fa6';

export default function PatientDashboard() {
  const { pt_num } = useParams();
  const patientId = pt_num || '5704';

  const [activeTab, setActiveTab] = useState('Timeline'); // DEFAULT TAB IS TIMELINE
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFormatArea, setSelectedFormatArea] = useState('Todos');
  const [selectedFormat, setSelectedFormat] = useState(null); // FORMATO SELECCIONADO EN PESTAÑA FORMATOS
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
      copied: null
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
  useEscapeKey(vitalsModal.open, () => setVitalsModal(prev => ({ ...prev, open: false })));
  useEscapeKey(prescriptionModal.open, () => setPrescriptionModal(prev => ({ ...prev, open: false, waitingFingerprint: false })));
  useEscapeKey(discontinueModal.open, () => setDiscontinueModal(prev => ({ ...prev, open: false })));
  useEscapeKey(dietModal.open, () => setDietModal(prev => ({ ...prev, open: false, waitingFingerprint: false })));
  useEscapeKey(allergyModal.open, () => setAllergyModal(prev => ({ ...prev, open: false })));

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

  const handleUpdateCustomAllergiesText = async (e) => {
    e.preventDefault();
    try {
      setAllergyModal(prev => ({ ...prev, submittingText: true, errorMsg: null }));
      const user = localStorage.getItem('usuario') || 'jose_prueba';
      const res = await api.post(`/ehr/paciente/${patientId}/alergias/actualizar-texto`, {
        allergies_text: allergyModal.customAllergiesText || 'NEGADAS',
        user: user
      });
      if (res.data && res.data.success) {
        setAllergyModal(prev => ({
          ...prev,
          submittingText: false,
          successMsg: res.data.message
        }));
        await fetchData();
        setTimeout(() => {
          setAllergyModal(prev => ({ ...prev, successMsg: null }));
        }, 2000);
      }
    } catch (err) {
      console.error("Error updating text allergies:", err);
      setAllergyModal(prev => ({
        ...prev,
        submittingText: false,
        errorMsg: err.response?.data?.detail || "Error al actualizar texto de alergias."
      }));
    }
  };

  // Buscar catálogo DIS_AL en vivo
  useEffect(() => {
    if (!allergyModal.open) return;
    const timer = setTimeout(async () => {
      try {
        setAllergyModal(prev => ({ ...prev, loadingCatalog: true }));
        const res = await api.get(`/ehr/alergias/catalogo?q=${encodeURIComponent(allergyModal.searchCatalog || '')}&limit=40`);
        if (res.data && Array.isArray(res.data)) {
          setAllergyModal(prev => ({ ...prev, catalogResults: res.data, loadingCatalog: false }));
        }
      } catch (err) {
        console.error("Error fetching allergy catalog:", err);
        setAllergyModal(prev => ({ ...prev, loadingCatalog: false }));
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [allergyModal.searchCatalog, allergyModal.open]);

  const handleSaveAllergy = async (e) => {
    e.preventDefault();
    if (!allergyModal.selectedAllergy) {
      setAllergyModal(prev => ({ ...prev, errorMsg: "Debe seleccionar una alergia del catálogo oficial." }));
      return;
    }
    try {
      setAllergyModal(prev => ({ ...prev, submitting: true, errorMsg: null }));
      const user = localStorage.getItem('usuario') || 'jose_prueba';
      const res = await api.post(`/ehr/paciente/${patientId}/alergias/registrar`, {
        allergy_num: allergyModal.selectedAllergy.allergy_id,
        allergic_since: allergyModal.allergic_since || null,
        notes: allergyModal.notes || '',
        user: user
      });
      if (res.data && res.data.success) {
        setAllergyModal(prev => ({
          ...prev,
          submitting: false,
          successMsg: res.data.message,
          selectedAllergy: null,
          searchCatalog: '',
          notes: '',
          allergic_since: ''
        }));
        await fetchPatientAllergies();
        await fetchData();
        setTimeout(() => {
          setAllergyModal(prev => ({ ...prev, successMsg: null }));
        }, 2000);
      }
    } catch (err) {
      console.error("Error saving allergy:", err);
      setAllergyModal(prev => ({
        ...prev,
        submitting: false,
        errorMsg: err.response?.data?.detail || "Error al registrar alergia."
      }));
    }
  };

  const handleInactivateAllergy = async (ptalNum) => {
    if (!window.confirm("¿Confirma que desea inactivar esta alergia en el expediente?")) return;
    try {
      const user = localStorage.getItem('usuario') || 'jose_prueba';
      const res = await api.post(`/ehr/paciente/${patientId}/alergias/inactivar`, {
        ptal_num: ptalNum,
        user: user
      });
      if (res.data && res.data.success) {
        await fetchPatientAllergies();
        await fetchData();
      }
    } catch (err) {
      console.error("Error inactivating allergy:", err);
      alert(err.response?.data?.detail || "Error al inactivar alergia.");
    }
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
  const handleOpenBiometricSign = (slot, title, content) => {
    setSigningModal({
      open: true,
      slot,
      title,
      content,
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
            codigo_formato: 'HE-DIRMED-SINPRO-PLT-87/01',
            tipo_documento: `Nota de Evolución de Urgencias (Evolución ${signingModal.slot})`,
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
    let doctorName = 'JOSE JOSE PRUEBA ENRIQUEZ';
    let doctorCed = 'PRUEBA-99281';
    try {
      const storedMed = JSON.parse(localStorage.getItem('medico'));
      if (storedMed && storedMed.nombre_completo) {
        doctorName = storedMed.nombre_completo;
        doctorCed = storedMed.cedula || doctorCed;
      }
    } catch(e){}

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

  // Filtrado de formatos
  const allFormatos = formatos_disponibles.flatMap(cat => cat.formatos.map(f => ({ ...f, area: cat.area })));
  const filteredFormatos = selectedFormatArea === 'Todos' 
    ? allFormatos 
    : allFormatos.filter(f => f.area === selectedFormatArea);

  const tabsList = [
    { id: 'Timeline', label: 'Timeline (Historial)', icon: <FiClock /> },
    { id: 'Formatos Clínicos', label: 'Formatos Clínicos (+100)', icon: <FiFileText /> },
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
          <button
            type="button"
            onClick={handleOpenVitalsModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-hes-blue-light/60 hover:bg-hes-blue-light text-hes-blue-main text-xs font-bold transition-all border border-hes-blue-main/20 shadow-sm"
            title="Capturar o modificar signos vitales"
          >
            <FiEdit3 /> Registrar / Modificar Signos Vitales
          </button>
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
                  timelineEvents.map((evt, idx) => (
                    <div key={idx} className="relative flex items-start gap-4 group">
                      <div className="w-8 h-8 rounded-full bg-hes-blue-main text-white flex items-center justify-center shadow shrink-0 z-10 text-xs font-bold ring-4 ring-white">
                        {idx + 1}
                      </div>
                      <div className="flex-1 bg-slate-50 hover:bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-hes-blue-main/40 transition-all">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                          <span className="font-bold text-slate-800 text-sm">{evt.type}</span>
                          <span className="text-xs font-semibold text-hes-blue-main bg-blue-50 px-2 py-0.5 rounded self-start sm:self-auto">
                            {evt.date} • {evt.time}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed mt-1">{evt.desc}</p>
                        
                        {evt.type && evt.type.startsWith('Nota de Evolución') && (
                          <div className="flex items-center gap-3 mt-3 pt-2 border-t border-slate-200/60">
                            <button 
                              onClick={() => {
                                const fmt = allFormatos.find(f => f.codigo === 'HE-DIRMED-SINPRO-PLT-87/01') || allFormatos[0];
                                setSelectedFormat(fmt);
                                setActiveTab('Formatos Clínicos');
                              }}
                              className="text-xs font-semibold text-hes-blue-main hover:underline flex items-center gap-1"
                            >
                              Ver Formato Oficial <FiChevronRight />
                            </button>
                            <a 
                              href={`${api.defaults.baseURL}/ehr/paciente/${patientId}/pdf-nota-urgencias`} 
                              target="_blank" 
                              rel="noreferrer"
                              className="text-xs font-semibold text-emerald-600 hover:underline flex items-center gap-1"
                            >
                              <FiDownload /> Imprimir PDF Oficial
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
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
                        <h2 className="text-lg font-bold text-slate-800">Catálogo Maestro de Formatos Clínicos</h2>
                        <span className="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded border border-emerald-200">+100 Formatos HES</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">Expediente clínico conforme a la norma NOM-004-SSA3-2012 y Calidad Institucional.</p>
                    </div>

                    {/* FILTRO POR AREA */}
                    <div className="flex gap-1.5 overflow-x-auto w-full md:w-auto pb-1">
                      {['Todos', 'Urgencias', 'Hospitalización', 'Cirugía y Quirófano', 'Consulta Externa e Interconsultas', 'Servicios Auxiliares y Diagnóstico'].map(area => (
                        <button
                          key={area}
                          onClick={() => setSelectedFormatArea(area)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-colors ${
                            selectedFormatArea === area 
                              ? 'bg-slate-800 text-white' 
                              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          {area.split(' ')[0]}
                        </button>
                      ))}
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
                              <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
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
                                href={`${api.defaults.baseURL}${fmt.url_pdf}`}
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
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Dieta Actual</div>
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
              <div className="text-[11px] font-semibold text-slate-400 uppercase mb-2">Seguimiento en Curso</div>
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
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
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
            </form>

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

      {/* MODAL DE GESTIÓN DE ALERGIAS (PTAL + CATÁLOGO OFICIAL DIS_AL) */}
      {allergyModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-3xl w-full p-6 shadow-2xl border border-slate-100 space-y-5 animate-scaleUp max-h-[90vh] overflow-y-auto">
            
            {/* CABECERA */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-red-50 text-red-600 rounded-2xl">
                  <FiAlertCircle className="text-2xl" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-slate-800">Catálogo de Alergias del Paciente</h3>
                  <p className="text-xs text-slate-500">
                    Sincronización de alergias con el catálogo oficial
                  </p>
                </div>
              </div>
              <button 
                type="button" 
                onClick={() => setAllergyModal(prev => ({ ...prev, open: false }))} 
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            {/* MENSAJES */}
            {allergyModal.errorMsg && (
              <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl border border-red-100 flex items-center gap-2">
                <FiAlertCircle className="text-base flex-shrink-0" />
                <span>{allergyModal.errorMsg}</span>
              </div>
            )}
            {allergyModal.successMsg && (
              <div className="p-3 bg-emerald-50 text-emerald-700 text-xs rounded-xl border border-emerald-100 flex items-center gap-2">
                <FiCheckCircle className="text-base flex-shrink-0" />
                <span>{allergyModal.successMsg}</span>
              </div>
            )}

            {/* SECCIÓN 1: ALERGIAS ACTIVAS EN VERTICAL (PTAL) */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                  <FiActivity className="text-red-500" /> Alergias Registradas del Paciente
                </h4>
                <span className="text-[11px] font-bold bg-red-50 text-red-700 px-2.5 py-0.5 rounded-full border border-red-100">
                  {allergyModal.allergiesList.length} Activas
                </span>
              </div>

              {allergyModal.allergiesList.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {allergyModal.allergiesList.map((al) => (
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
                        <button
                          type="button"
                          onClick={() => handleInactivateAllergy(al.ptal_num)}
                          className="text-[10px] font-bold text-red-600 hover:text-red-800 hover:bg-red-100 px-2 py-1 rounded-lg transition-colors flex items-center gap-1"
                        >
                          <FiX className="text-xs" /> Inactivar
                        </button>
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

            {/* SECCIÓN 2: FORMULARIO PARA REGISTRAR NUEVA ALERGIA */}
            <form onSubmit={handleSaveAllergy} className="space-y-4 pt-4 border-t border-slate-100 bg-slate-50/70 p-4 rounded-2xl border border-slate-200">
              <h4 className="text-xs font-black uppercase tracking-wider text-hes-blue-main flex items-center gap-1.5">
                <FiPlus /> Registrar Nueva Alergia (Catálogo Oficial DIS_AL)
              </h4>

              {/* BUSCADOR DE CATÁLOGO DIS_AL */}
              <div className="space-y-1 text-xs">
                <label className="block text-[10px] font-bold text-slate-600 uppercase">
                  Buscar Alergia o Sustancia en Catálogo *
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={allergyModal.searchCatalog}
                    onChange={(e) => setAllergyModal({ ...allergyModal, searchCatalog: e.target.value })}
                    placeholder="Escriba el nombre del fármaco o sustancia (ej. Penicilinas, Sulfas, Betanecol, Huevo, OTROS)..."
                    className="w-full border border-slate-200 bg-white rounded-xl p-2.5 text-xs font-semibold focus:border-hes-blue-main outline-none"
                  />
                  {allergyModal.loadingCatalog && (
                    <span className="absolute right-3 top-2.5 text-[10px] text-hes-blue-main font-bold animate-pulse">
                      Buscando...
                    </span>
                  )}
                </div>

                {/* RESULTADOS DEL CATÁLOGO DIS_AL */}
                {allergyModal.catalogResults.length > 0 && !allergyModal.selectedAllergy && (
                  <div className="max-h-44 overflow-y-auto bg-white border border-slate-200 rounded-xl shadow-lg mt-1 divide-y divide-slate-100">
                    {allergyModal.catalogResults.map((cat) => (
                      <div
                        key={cat.allergy_id}
                        onClick={() => {
                          setAllergyModal({
                            ...allergyModal,
                            selectedAllergy: cat,
                            searchCatalog: cat.name
                          });
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

                {/* ALERGIA SELECCIONADA */}
                {allergyModal.selectedAllergy && (
                  <div className="p-2.5 bg-blue-50 rounded-xl border border-blue-200 flex items-center justify-between mt-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] bg-hes-blue-main text-white font-extrabold px-1.5 py-0.5 rounded">
                        ID #{allergyModal.selectedAllergy.allergy_id}
                      </span>
                      <span className="text-xs font-black text-hes-blue-main">
                        {allergyModal.selectedAllergy.name}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setAllergyModal({ ...allergyModal, selectedAllergy: null, searchCatalog: '' })}
                      className="text-xs text-slate-400 hover:text-red-500 font-bold"
                    >
                      Cambiar
                    </button>
                  </div>
                )}
              </div>

              {/* CAMPOS ADICIONALES: FECHA Y NOTAS */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">
                    Alérgico Desde (Opcional)
                  </label>
                  <input
                    type="date"
                    value={allergyModal.allergic_since}
                    onChange={(e) => setAllergyModal({ ...allergyModal, allergic_since: e.target.value })}
                    className="w-full border border-slate-200 bg-white rounded-xl p-2 text-xs font-semibold outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase mb-1">
                    Notas / Reacción Clínica
                  </label>
                  <input
                    type="text"
                    value={allergyModal.notes}
                    onChange={(e) => setAllergyModal({ ...allergyModal, notes: e.target.value })}
                    placeholder="Ej. Anafilaxia previa, Urticaria, Shock, Intolerancia..."
                    className="w-full border border-slate-200 bg-white rounded-xl p-2 text-xs font-semibold outline-none"
                  />
                </div>
              </div>

              {/* BOTÓN DE REGISTRO */}
              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={allergyModal.submitting || !allergyModal.selectedAllergy}
                  className="flex items-center gap-2 bg-hes-blue-main hover:bg-hes-blue-dark text-white px-5 py-2.5 rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <FiPlus />
                  {allergyModal.submitting ? 'Registrando...' : 'Guardar Alergia'}
                </button>
              </div>
            </form>

            {/* SECCIÓN 3: TEXTO CONSOLIDADO EN FORMATOS CLÍNICOS (MR_NE_URG / MR_SOL_DIET) */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="text-xs font-black uppercase tracking-wider text-slate-700">
                    Texto en Formatos y Notas Clínicas
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    Este texto se imprime en el Formato 87/01 y en Dietas.
                  </p>
                </div>
              </div>

              <form onSubmit={handleUpdateCustomAllergiesText} className="flex flex-col sm:flex-row gap-2">
                <input
                  type="text"
                  value={allergyModal.customAllergiesText}
                  onChange={(e) => setAllergyModal({ ...allergyModal, customAllergiesText: e.target.value })}
                  placeholder="Ej. Alérgico a Penicilina, Sulfas, Betanecol..."
                  className="flex-1 border border-slate-200 bg-white rounded-xl p-2 text-xs font-semibold focus:border-hes-blue-main outline-none"
                />
                <button
                  type="submit"
                  disabled={allergyModal.submittingText}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold transition-all shadow-xs shrink-0 disabled:opacity-50"
                >
                  {allergyModal.submittingText ? 'Actualizando...' : 'Actualizar Texto Directo'}
                </button>
              </form>
            </div>

            {/* PIE */}
            <div className="flex justify-end pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setAllergyModal(prev => ({ ...prev, open: false }))}
                className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 text-xs font-bold transition-all"
              >
                Cerrar
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

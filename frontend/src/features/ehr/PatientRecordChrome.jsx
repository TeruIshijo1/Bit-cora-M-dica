import { useId } from 'react';
import { FiActivity, FiAlertTriangle, FiCheckCircle, FiChevronDown, FiClock, FiEdit3, FiMenu } from 'react-icons/fi';
import Button from '../../components/ui/Button';
import { getVitalAlert, getVitalSummaryLabel } from '../../utils/vitalAlerts';
import '../../styles/patient-record.css';

export function RecordDisclosure({ title, icon, summary, open, onToggle, children, className = '' }) {
  const id = useId();
  return (
    <section className={`he-record-disclosure ${className}`}>
      <Button
        variant="ghost"
        className="he-record-disclosure-toggle"
        aria-expanded={open}
        aria-controls={`${id}-content`}
        id={`${id}-toggle`}
        onClick={onToggle}
      >
        <span className="he-record-disclosure-title">{icon}<span>{title}</span></span>
        {summary}
        <FiChevronDown aria-hidden="true" className="he-record-chevron" />
      </Button>
      <div id={`${id}-content`} role="region" aria-labelledby={`${id}-toggle`} hidden={!open} className="he-record-disclosure-body">
        {children}
      </div>
    </section>
  );
}

export function PatientRecordHeader({ patient, patientId, discharged, open, onToggle, onManageAllergies, children }) {
  const name = patient.name || 'Paciente sin nombre';
  const allergy = patient.allergies || 'Sin alergias registradas';
  const hasAllergies = Boolean(patient.allergies && !/sin alergia/i.test(patient.allergies));
  return (
    <header className="he-record-header">
      <div className="he-record-identity-row">
        <div className="he-record-avatar" aria-hidden="true">{name.trim().charAt(0).toUpperCase() || 'P'}</div>
        <div className="he-record-identity">
          <h1>{name}</h1>
          <div className="he-record-meta">
            <span className="he-record-mrn">{patient.mrn || `PT-${patientId}`}</span>
            <span>{patient.age} · {patient.gender}</span>
            {discharged
              ? <span className="he-record-discharged"><FiCheckCircle aria-hidden="true" /> Alta / Histórico</span>
              : <span>{patient.cama || 'Cama virtual'}</span>}
          </div>
        </div>
        <div className="he-record-header-actions">{children}</div>
      </div>
      <RecordDisclosure title="Datos del paciente" open={open} onToggle={onToggle} className="he-record-patient-details">
        <dl className="he-record-demographics">
          <div><dt>Fecha de nacimiento</dt><dd>{patient.dob || '—'}</dd></div>
          <div><dt>Ingreso</dt><dd>{patient.fecha_ingreso || '—'} {patient.hora_ingreso || ''}</dd></div>
          {discharged && patient.fecha_egreso && patient.fecha_egreso !== '___/___/___' && (
            <div><dt>Egreso</dt><dd>{patient.fecha_egreso} {patient.hora_egreso !== '__:__' ? patient.hora_egreso : ''}</dd></div>
          )}
          <div><dt>Diagnóstico de ingreso</dt><dd>{patient.diagnostico || 'Sin diagnóstico registrado'}</dd></div>
        </dl>
      </RecordDisclosure>
      <div className={`he-record-allergies ${hasAllergies ? 'has-alert' : ''}`}>
        <FiAlertTriangle aria-hidden="true" />
        <span><strong>Alergias:</strong> {allergy}</span>
        {!discharged && <Button variant="ghost" size="sm" onClick={onManageAllergies} className="he-record-manage-allergies">Gestionar</Button>}
      </div>
    </header>
  );
}

export function PatientRecordNavigation({ tabs, activeTab, onSelect, menuOpen, onToggleMenu }) {
  const id = useId();
  const selected = tabs.find(tab => tab.id === activeTab);
  return (
    <aside className={`he-record-navigation ${menuOpen ? 'is-menu-open' : ''}`}>
      <Button variant="ghost" className="he-record-menu-toggle" onClick={onToggleMenu} aria-controls={id} aria-expanded={menuOpen}>
        <FiMenu aria-hidden="true" /><span>{selected?.label || 'Secciones del expediente'}</span><FiChevronDown aria-hidden="true" />
      </Button>
      <nav id={id} aria-label="Secciones del expediente" className="he-record-nav">
        <span className="he-record-nav-label">Expediente</span>
        {tabs.map(tab => (
          <Button
            key={tab.id}
            variant="ghost"
            className="he-record-nav-item"
            aria-current={activeTab === tab.id ? 'page' : undefined}
            aria-label={tab.accessibleLabel || tab.label}
            onClick={() => onSelect(tab.id)}
          >
            {tab.icon}<span>{tab.label}</span>
            {tab.count != null && <span className="he-record-nav-count">{tab.count}</span>}
          </Button>
        ))}
      </nav>
    </aside>
  );
}

export function PatientVitalsPanel({ vitals, lastTaken, discharged, open, onToggle, onHistory, onNewReading }) {
  const readings = vitals.map(vital => ({ ...vital, alert: getVitalAlert(vital) }));
  const alerts = readings.filter(vital => vital.alert);
  return (
    <RecordDisclosure
      title="Signos vitales"
      icon={<FiActivity aria-hidden="true" />}
      open={open}
      onToggle={onToggle}
      className="he-record-vitals"
      summary={<>
        <span className="he-record-reading-date">{lastTaken ? `Última toma: ${lastTaken}` : 'Sin fecha de toma registrada'}</span>
        {!open && alerts.length > 0 && <span className="he-record-vital-alerts">
          {alerts.map((vital, index) => <span key={`${vital.label}-${index}`} className="he-record-vital-alert">
            <FiAlertTriangle aria-hidden="true" />{getVitalSummaryLabel(vital.label)} {vital.value} {vital.unit} · {vital.alert}
          </span>)}
        </span>}
      </>}
    >
      <div className="he-record-vitals-actions">
        <Button variant="ghost" size="sm" icon={<FiClock aria-hidden="true" />} onClick={onHistory}>Historial</Button>
        {!discharged && <Button variant="outline" size="sm" icon={<FiEdit3 aria-hidden="true" />} onClick={onNewReading}>Nueva toma</Button>}
      </div>
      <div className="he-record-vitals-grid">
        {readings.map((vital, index) => (
          <Button
            key={`${vital.label}-${index}`}
            variant="ghost"
            className={`he-record-reading ${vital.alert ? 'has-alert' : ''}`}
            onClick={discharged ? onHistory : onNewReading}
            aria-label={`${vital.label}: ${vital.value} ${vital.unit || ''}${vital.alert ? `, ${vital.alert}` : ''}. ${discharged ? 'Ver historial' : 'Nueva toma'}`}
          >
            <span className="he-record-reading-label">{vital.label}</span>
            <span className="he-record-reading-value">{vital.value}<small>{vital.unit}</small></span>
            {vital.alert && <span className="he-record-reading-flag"><FiAlertTriangle aria-hidden="true" />{vital.alert}</span>}
          </Button>
        ))}
      </div>
      {!readings.length && <p className="he-record-empty">Sin signos vitales registrados.</p>}
    </RecordDisclosure>
  );
}

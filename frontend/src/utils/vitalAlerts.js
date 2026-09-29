// Preserve the existing dashboard thresholds for both expanded and folded views.
export function getVitalAlert(vital) {
  const raw = String(vital.value ?? '').replace(',', '.');
  const num = parseFloat(raw);
  const label = vital.label || '';
  if (/arteri|tensi|TA\b/i.test(label)) {
    const match = raw.match(/(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)/);
    if (match) {
      const systolic = parseFloat(match[1]);
      const diastolic = parseFloat(match[2]);
      if (systolic >= 140 || diastolic >= 90) return 'Alta';
      if (systolic < 90 || diastolic < 60) return 'Baja';
    }
  } else if (/card[ií]aca|FC\b|pulso/i.test(label)) {
    if (!isNaN(num) && (num >= 100 || num < 60)) return num >= 100 ? 'Alta' : 'Baja';
  } else if (/respirat|FR\b/i.test(label)) {
    if (!isNaN(num) && (num >= 22 || num < 12)) return num >= 22 ? 'Alta' : 'Baja';
  } else if (/saturaci|O2|spo2/i.test(label)) {
    if (!isNaN(num) && num < 92) return 'Baja';
  } else if (/temperatura/i.test(label)) {
    if (!isNaN(num) && (num >= 37.5 || num < 36)) return num >= 37.5 ? 'Fiebre' : 'Baja';
  }
  return null;
}

export function getVitalSummaryLabel(label = '') {
  if (/arteri|tensi|TA\b/i.test(label)) return 'PA';
  if (/card[ií]aca|FC\b|pulso/i.test(label)) return 'FC';
  if (/respirat|FR\b/i.test(label)) return 'FR';
  if (/saturaci|O2|spo2/i.test(label)) return 'SpO₂';
  if (/temperatura/i.test(label)) return 'Temperatura';
  return label;
}

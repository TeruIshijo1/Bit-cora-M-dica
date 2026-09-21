export const representativeRoles = ['REPRESENTANTE_LEGAL', 'TUTOR', 'FAMILIAR'];
export const signerRole = person => (person?.tipo_firmante || '').toUpperCase();
export const witnessSigned = (role, status) => role === 'TESTIGO_1'
  ? Boolean(status?.testigo1_firmado) : role === 'TESTIGO_2' && Boolean(status?.testigo2_firmado);

export function nextDocumentSigner(people, capable, status) {
  const authorizer = people.find(person => capable
    ? signerRole(person) === 'PACIENTE' : representativeRoles.includes(signerRole(person)));
  if (!status?.paciente_firmado) return authorizer || null;
  return people.find(person => ['TESTIGO_1', 'TESTIGO_2'].includes(signerRole(person))
    && !witnessSigned(signerRole(person), status)) || authorizer || null;
}

export function captureBelongsToSigner(context, patientId, code, slot, signerId) {
  return context?.action === 'FIRMA_FIRMANTE'
    && context.expectedIdentityRef === `firmante:${signerId}`
    && String(context.patientRef) === String(patientId)
    && context.documentCode === code
    && String(context.documentRef ?? 0) === String(slot ?? 0);
}

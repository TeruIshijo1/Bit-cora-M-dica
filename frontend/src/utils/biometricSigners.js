export const representativeRoles = ['REPRESENTANTE_LEGAL', 'TUTOR', 'FAMILIAR'];
export const signerRole = person => (person?.tipo_firmante || '').toUpperCase();
export const patientCanAuthorize = (value, fallback = true) => {
  if (value === null || value === undefined || value === '') return fallback;
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value !== 0;
  const normalized = String(value).trim().toLowerCase();
  if (['false', '0', 'no', 'n', 'incapaz'].includes(normalized)) return false;
  if (['true', '1', 'si', 'sí', 's', 'capaz'].includes(normalized)) return true;
  return fallback;
};
export const witnessCandidateRoles = [...representativeRoles, 'TESTIGO_1', 'TESTIGO_2'];
export const witnessSigned = (role, status) => role === 'TESTIGO_1'
  ? Boolean(status?.testigo1_firmado) : role === 'TESTIGO_2' && Boolean(status?.testigo2_firmado);
export const witnessProgress = status => Number(Boolean(status?.testigo1_firmado))
  + Number(Boolean(status?.testigo2_firmado));
export const requiredWitnesses = (status, patientCapable = undefined) => {
  if (!status) return 0;
  // El servidor entrega los testigos ADICIONALES exigidos para este documento.
  // No descontar de nuevo al representante: ya está incluido en esa cifra.
  const configured = status?.testigos_requeridos;
  if (configured !== null && configured !== undefined) {
    return Math.max(0, Number(configured) || 0);
  }
  // Compatibilidad con servidores anteriores que sólo devolvían un booleano.
  const required = status?.requiere_testigos !== undefined
    ? (status.requiere_testigos ? 2 : 0)
    : 2;
  const authorizerRole = String(status?.detalles?.rol_firmante_paciente || '').toUpperCase();
  const representativeAuthorizer = ['REPRESENTANTE_LEGAL', 'TUTOR', 'FAMILIAR'].includes(authorizerRole)
    || (patientCapable === false && !authorizerRole);
  return required >= 2 && representativeAuthorizer ? 1 : required;
};

export const expectedWitnesses = (status, patientCapable = undefined) => {
  if (!status) return 0;
  const configured = status.testigos_esperados;
  if (configured !== null && configured !== undefined) {
    return Math.max(0, Number(configured) || 0);
  }
  return requiredWitnesses(status, patientCapable);
};

export const signedWitnessRoleFor = (personId, status) => {
  if (String(status?.detalles?.firmante_testigo1_id ?? '') === String(personId)) return 'TESTIGO_1';
  if (String(status?.detalles?.firmante_testigo2_id ?? '') === String(personId)) return 'TESTIGO_2';
  return null;
};

export const availableWitnessRoleFor = (person, status, patientCapable = undefined) => {
  if (!person || !witnessCandidateRoles.includes(signerRole(person))) return null;
  if (signedWitnessRoleFor(person.id, status)) return null;
  const authorizerId = status?.detalles?.firmante_paciente_id;
  if (authorizerId != null && String(authorizerId) === String(person.id)) return null;
  const slots = expectedWitnesses(status, patientCapable);
  if (slots < 1) return null;
  if (witnessProgress(status) >= slots) return null;
  if (!status?.testigo1_firmado) return 'TESTIGO_1';
  if (slots >= 2 && !status?.testigo2_firmado) return 'TESTIGO_2';
  return null;
};

export const signerIdentityForRole = (signerId, role) => `firmante:${signerId}|role:${String(role || '').toUpperCase()}`;

export function nextDocumentSigner(people, capable, status) {
  const authorizer = people.find(person => capable
    ? signerRole(person) === 'PACIENTE' : representativeRoles.includes(signerRole(person)));
  if (!status?.paciente_firmado) return authorizer || null;
  return people.find(person => availableWitnessRoleFor(person, status, capable)) || authorizer || null;
}

export function captureBelongsToSigner(context, patientId, code, slot, signerId, role) {
  return context?.action === 'FIRMA_FIRMANTE'
    && context.expectedIdentityRef === signerIdentityForRole(signerId, role)
    && String(context.patientRef) === String(patientId)
    && context.documentCode === code
    && String(context.documentRef ?? 0) === String(slot ?? 0);
}

export const medicalBiometricFlow = doctor => {
  if (doctor?.requiere_actualizacion_fea) {
    return {
      kind: 'fea',
      action: 'ACTUALIZACION_FEA',
      endpoint: `/medicos/${doctor.id}/fea/completar-actualizacion`,
      title: 'Activar la firma del médico',
      requiresReason: true
    };
  }

  if (doctor?.biometric_status === 'SIN_BIOMETRIA') {
    return {
      kind: 'enroll',
      action: 'ENROLAMIENTO_MEDICO',
      endpoint: `/medicos/${doctor.id}/biometria/enrolar`,
      title: 'Registrar huella',
      requiresReason: false
    };
  }

  return {
    kind: 'reenroll',
    action: 'REENROLAMIENTO_MEDICO',
    endpoint: `/medicos/${doctor.id}/biometria/reenrolar`,
    title: 'Actualizar huella',
    requiresReason: true
  };
};

export const captureBelongsToMedicalFlow = (context, doctor, flow) => Boolean(
  context
  && doctor?.id != null
  && flow?.action
  && context.action === flow.action
  && context.expectedIdentityRef === `medico:${doctor.id}`
  && String(context.documentRef) === String(doctor.id)
);

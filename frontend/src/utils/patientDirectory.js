/**
 * Reglas compartidas para el acceso rápido a expedientes.
 *
 * El censo de camas del backend ya excluye camas virtuales, pero mantenemos
 * esta defensa en el cliente para que una respuesta antigua o enriquecida no
 * vuelva a mostrar pacientes virtuales en la vista inicial.
 */
export function isVirtualBed(bed) {
  const room = `${bed?.RoomName || ''} ${bed?.RoomCode || ''}`.toUpperCase();
  return room.includes('VIRTUAL') || room.includes('VIRT') || room.includes('CV');
}

export function getOccupiedBedPatients(beds = []) {
  return (Array.isArray(beds) ? beds : [])
    .filter((bed) => bed?.Estatus === 'Ocupada' && bed?.PTNum && !isVirtualBed(bed))
    .map((bed) => ({
      pt_num: String(bed.PTNum),
      name: bed.PatientName || 'Paciente sin nombre',
      cama: bed.RoomName || bed.RoomCode || 'Cama asignada',
      doctor: bed.DoctorName || '',
      status: 'Hospitalizado / Activo',
      is_active: true,
      diagnostico: 'Paciente actualmente en cama',
      source: 'bed',
    }));
}


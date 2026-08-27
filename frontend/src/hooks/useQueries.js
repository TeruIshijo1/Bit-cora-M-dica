import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

/**
 * Hook centralizado de queries con TanStack React Query.
 * Implementa Stale-While-Revalidate y caché instantánea en memoria.
 */

// 1. Pacientes Activos
export function usePacientesQuery() {
  return useQuery({
    queryKey: ['pacientes'],
    queryFn: async () => {
      const res = await api.get('/pacientes');
      return res.data || [];
    },
    staleTime: 1000 * 30, // 30 segundos
  });
}

// 2. Personal Médico
export function useMedicosQuery() {
  return useQuery({
    queryKey: ['medicos'],
    queryFn: async () => {
      const res = await api.get('/medicos');
      return res.data || [];
    },
    staleTime: 1000 * 60 * 5, // 5 minutos (datos estables)
  });
}

// 3. Catálogo de Áreas Hospitalarias
export function useCatalogosAreasQuery() {
  return useQuery({
    queryKey: ['catalogos', 'areas'],
    queryFn: async () => {
      const res = await api.get('/catalogos/areas');
      return res.data || [];
    },
    staleTime: 1000 * 60 * 10, // 10 minutos
  });
}

// 4. Catálogo de Tipos de Atención
export function useCatalogosTiposQuery() {
  return useQuery({
    queryKey: ['catalogos', 'tipos'],
    queryFn: async () => {
      const res = await api.get('/catalogos/tipos');
      return res.data || [];
    },
    staleTime: 1000 * 60 * 10,
  });
}

// 5. Censo de Camas en Vivo
export function useCamasQuery() {
  return useQuery({
    queryKey: ['camas'],
    queryFn: async () => {
      const res = await api.get('/camas');
      return Array.isArray(res.data) ? res.data : [];
    },
    staleTime: 1000 * 15, // 15 segundos
  });
}

// 6. Expediente Clínico de Paciente
export function usePatientDashboardQuery(patientId) {
  return useQuery({
    queryKey: ['patient', patientId],
    queryFn: async () => {
      if (!patientId) return null;
      const res = await api.get(`/ehr/paciente/${patientId}`);
      return res.data;
    },
    enabled: Boolean(patientId),
    staleTime: 1000 * 30,
  });
}

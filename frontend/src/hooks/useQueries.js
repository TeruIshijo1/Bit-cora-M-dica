import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { useInfiniteQuery } from '@tanstack/react-query';

export function useAreaSignaturesQuery(state) {
  return useInfiniteQuery({
    queryKey: ['area-signatures', state], initialPageParam: '',
    queryFn: async ({ signal, pageParam }) => (await api.get('/firmas-area', {
      signal, params: { estado: state, cursor: pageParam }, timeout: 30000,
    })).data,
    getNextPageParam: page => page.next_cursor || undefined,
    staleTime: 0, refetchInterval: 20000, retry: false,
  });
}

export function useAreaSignatureDocumentQuery(document) {
  return useQuery({
    queryKey: ['area-signature-document', document?.pt_num, document?.codigo_formato, document?.slot],
    queryFn: async ({ signal }) => (await api.get('/firmas-area/documento', {
      signal, params: { pt_num: document.pt_num, codigo_formato: document.codigo_formato, slot: document.slot },
      timeout: 20000,
    })).data,
    enabled: Boolean(document), staleTime: 0, gcTime: 0, refetchInterval: 20000, retry: false,
  });
}

export function useSessionPermissionsQuery(enabled) {
  return useQuery({
    queryKey: ['session-access'],
    queryFn: async ({ signal }) => (await api.get('/auth/me', { signal })).data,
    enabled: Boolean(enabled), staleTime: 0, refetchInterval: 60000, retry: false,
  });
}

export function usePermissionCatalogQuery() {
  return useQuery({
    queryKey: ['permission-catalog'],
    queryFn: async ({ signal }) => (await api.get('/catalogos/permisos', { signal })).data,
    staleTime: 60000,
  });
}

export function useAdminResourceQuery(path, enabled) {
  return useQuery({
    queryKey: ['admin-resource', path],
    queryFn: async ({ signal }) => (await api.get(path, { signal })).data,
    enabled: Boolean(enabled), staleTime: 30000,
  });
}

export function useSaveUser() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }) => (await (id ? api.put(`/usuarios/${id}`, payload) : api.post('/usuarios', payload))).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ['admin-resource', '/usuarios'] }),
  });
}

export function usePublicDocumentVerificationQuery(docId) {
  return useQuery({
    queryKey: ['public-document-verification', docId],
    queryFn: async ({ signal }) => {
      const response = await fetch(`/api/verificar/documento-estado?id=${encodeURIComponent(docId)}`, {
        signal,
        credentials: 'omit',
        cache: 'no-store',
      });
      if (!response.ok) throw new Error('No se encontró un documento para este QR.');
      return response.json();
    },
    enabled: Boolean(docId),
    staleTime: 0,
    gcTime: 0,
    retry: false,
  });
}

export function useBiometricSignersQuery(patientId, enabled) {
  return useQuery({
    queryKey: ['biometric-signers', String(patientId)],
    queryFn: async ({ signal }) => (await api.get(`/pacientes/${encodeURIComponent(patientId)}/firmantes-biometricos`, { signal })).data,
    enabled: Boolean(enabled && patientId), staleTime: 0, gcTime: 0,
  });
}

const documentSignatureOptions = (patientId, code, slot) => ({
    queryKey: ['document-signatures', String(patientId), code, slot],
    queryFn: async ({ signal }) => (await api.get(`/ehr/paciente/${encodeURIComponent(patientId)}/firmas-documento`, {
      signal, timeout: 15000, params: { codigo_formato: code, slot },
    })).data,
    staleTime: 0, gcTime: 0, retry: false,
});

export function useDocumentSignaturesQuery(patientId, code, slot, enabled) {
  return useQuery({
    ...documentSignatureOptions(patientId, code, slot),
    enabled: Boolean(enabled && patientId && code),
  });
}

export function useBankBloodSignersQuery(code, enabled) {
  return useQuery({
    queryKey: ['bank-blood-signers', code],
    queryFn: async ({ signal }) => (await api.get('/ehr/banco-sangre/firmantes', {
      signal, params: { codigo_formato: code },
    })).data,
    enabled: Boolean(enabled && code), staleTime: 0, gcTime: 0, retry: false,
  });
}

export function useSpecialSignatureSignersQuery(code, role, enabled) {
  return useQuery({
    queryKey: ['special-signature-signers', code, role],
    queryFn: async ({ signal }) => (await api.get('/ehr/firmantes-especiales', {
      signal, params: { codigo_formato: code, rol_firmante: role },
    })).data,
    enabled: Boolean(enabled && code && role), staleTime: 0, gcTime: 0, retry: false,
  });
}

export function useReadDocumentSignatures() {
  const client = useQueryClient();
  return (patientId, code, slot) => client.fetchQuery(documentSignatureOptions(patientId, code, slot));
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async credentials => (await api.post('/auth/change-password', credentials, { timeout: 15000 })).data,
    retry: false,
    gcTime: 0,
  });
}

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
export function useCamasQuery(enabled = true) {
  return useQuery({
    queryKey: ['camas'],
    queryFn: async () => {
      const res = await api.get('/camas');
      return Array.isArray(res.data) ? res.data : [];
    },
    enabled,
    staleTime: 1000 * 15, // 15 segundos
    refetchInterval: enabled ? 1000 * 30 : false,
  });
}

// 6. Búsqueda explícita de cualquier expediente (incluidos virtuales e históricos)
export function usePatientSearchQuery(term, enabled = true, limit = 40) {
  const normalizedTerm = String(term || '').trim();
  return useQuery({
    queryKey: ['patient-search', normalizedTerm, limit],
    queryFn: async ({ signal }) => {
      const res = await api.get('/ehr/pacientes/buscar', {
        params: { q: normalizedTerm, limit },
        signal,
      });
      return Array.isArray(res.data) ? res.data : [];
    },
    enabled: Boolean(enabled && normalizedTerm.length >= 2),
    staleTime: 1000 * 30,
    retry: false,
  });
}

// 7. Expediente Clínico de Paciente
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

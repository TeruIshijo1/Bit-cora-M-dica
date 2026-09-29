const safeApiEndpoint = (endpoint) => {
  const value = String(endpoint || '').trim();
  if (!value.startsWith('/') || value.startsWith('//') || /^\/https?:/i.test(value)) {
    throw new Error('Ruta de documento no permitida.');
  }
  return value.startsWith('/api/') ? value.slice(4) : value;
};

export const resolvePdfRequest = (endpoint) => {
  const safeEndpoint = safeApiEndpoint(endpoint);
  const [path, query = ''] = safeEndpoint.split('?', 2);
  const ehrPdfMatch = path.match(/^\/ehr\/paciente\/([0-9]+)\/pdf-consentimiento-09$/);
  if (ehrPdfMatch && /^mrnum=[1-9][0-9]*$/.test(query)) {
    return {
      method: 'post',
      url: `/ehr/paciente/${ehrPdfMatch[1]}/pdf-preparar?source=${encodeURIComponent(safeEndpoint)}`,
    };
  }
  // Las vistas previas y los motores aún sin preparador son lecturas JWT.
  return { method: 'get', url: safeEndpoint };
};

const GENERIC_PDF_STEM = /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|[0-9a-f]{24,})$/i;

const normalizeFilenamePart = (value, fallback = 'Resultado') => {
  const normalized = String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^A-Za-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 80);

  return normalized || fallback;
};

export const isGenericPdfFilename = (value) => {
  const raw = String(value ?? '').trim();
  if (!raw) return true;

  const baseName = raw.replace(/\\/g, '/').split('/').pop() || '';
  const stem = baseName.replace(/\.pdf$/i, '');
  return !stem || GENERIC_PDF_STEM.test(stem);
};

export const getStudyPdfDownloadName = (study) => {
  const rawName = String(study?.nombre_archivo ?? '').trim();
  if (rawName && !isGenericPdfFilename(rawName)) {
    const rawStem = rawName
      .replace(/\\/g, '/')
      .split('/')
      .pop()
      .replace(/\.pdf$/i, '');
    const safeStem = normalizeFilenamePart(rawStem);
    return `${safeStem}.pdf`;
  }

  const tipo = study?.tipo === 'Imagenología' ? 'Imagenologia' : 'Laboratorio';
  const estudio = normalizeFilenamePart(study?.estudio, 'Resultado');
  const identifier = study?.ptmt_num ?? study?.id ?? 'estudio';
  const safeIdentifier = normalizeFilenamePart(identifier, 'estudio');
  return `${tipo}_${estudio}_PTMT-${safeIdentifier}.pdf`;
};

export const normalizePdfDownloadName = (value) => {
  const baseName = String(value ?? '').replace(/\\/g, '/').split('/').pop() || '';
  if (isGenericPdfFilename(baseName)) return 'Documento_Clinico_HES.pdf';
  return `${normalizeFilenamePart(baseName.replace(/\.pdf$/i, ''), 'Documento_Clinico_HES')}.pdf`;
};

export const parseContentDispositionFilename = (header) => {
  if (!header || typeof header !== 'string') return null;
  const utf8Match = header.match(/filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      const decoded = decodeURIComponent(utf8Match[1].trim().replace(/^["']|["']$/g, ''));
      if (decoded && !isGenericPdfFilename(decoded)) return decoded;
    } catch {
      // ignore decode error
    }
  }
  const match = header.match(/filename\s*=\s*(?:"([^"]+)"|([^;]+))/i);
  if (match) {
    const raw = (match[1] || match[2] || '').trim().replace(/^["']|["']$/g, '');
    if (raw && !isGenericPdfFilename(raw)) return raw;
  }
  return null;
};

export const inferPdfFilenameFromEndpoint = (endpoint) => {
  const url = String(endpoint || '');
  const ptMatch = url.match(/paciente\/([^/?#]+)/);
  const pt = ptMatch ? normalizeFilenamePart(ptMatch[1], '') : '';
  if (url.includes('pdf-expediente-completo')) {
    return `Expediente_Completo${pt ? `_PT_${pt}` : ''}.pdf`;
  }
  if (url.includes('pdf-nota-urgencias')) {
    return `Nota_Urgencias${pt ? `_PT_${pt}` : ''}.pdf`;
  }
  if (url.includes('pdf-nota-hospitalizacion')) {
    return `Nota_Hospitalizacion${pt ? `_PT_${pt}` : ''}.pdf`;
  }
  if (url.includes('pdf-consentimiento-')) {
    const format = url.split('pdf-consentimiento-')[1]?.split(/[/?#]/)[0] || '';
    return `Consentimiento_${normalizeFilenamePart(format)}${pt ? `_PT_${pt}` : ''}.pdf`;
  }
  const egreso = url.match(/pdf-egreso-([a-z0-9-]+)/i);
  if (egreso) return `Egreso_${normalizeFilenamePart(egreso[1])}${pt ? `_PT_${pt}` : ''}.pdf`;
  const folio = url.match(/atenciones\/([^/?#]+)\/pdf/i);
  if (folio) return `Comprobante_${normalizeFilenamePart(folio[1])}.pdf`;
  return 'Documento_Clinico_HES.pdf';
};

import { normalizePdfDownloadName } from './pdfFilename';

export const NAMED_PDF_PREVIEW_KEY = 'hes:named-pdf-preview';

export const openNamedPdfPreview = (preview, blobUrl, filename) => {
  const downloadName = normalizePdfDownloadName(filename);
  if (preview && !preview.closed) {
    try {
      preview.sessionStorage.setItem(
        NAMED_PDF_PREVIEW_KEY,
        JSON.stringify({ blobUrl, filename: downloadName }),
      );
      preview.opener = null;
      preview.location.replace(`${window.location.origin}/ehr/visor-pdf`);
      return;
    } catch {
      preview.close();
    }
  }

  // Si el navegador bloqueó la pestaña, el mismo clic descarga el archivo
  // con su nombre clínico y sin depender de la URL blob con UUID.
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = downloadName;
  document.body.appendChild(link);
  link.click();
  link.remove();
};

import { useState } from 'react';
import { FiRotateCcw } from 'react-icons/fi';
import { api } from '../api';
import { resolvePdfRequest } from '../utils/pdfRequest';
import { parseContentDispositionFilename, inferPdfFilenameFromEndpoint } from '../utils/pdfFilename';
import { openNamedPdfPreview } from '../utils/namedPdfPreview';

const readErrorPayload = async (error) => {
  let payload = error?.response?.data;
  if (error?.response?.data instanceof Blob) {
    try {
      payload = JSON.parse(await error.response.data.text());
    } catch {
      payload = null;
    }
  }
  const detail = payload?.detail;
  if (typeof detail === 'string') return { message: detail };
  if (detail && typeof detail === 'object') {
    return {
      ...detail,
      message: detail.message || detail.question || 'El documento requiere una revisión antes de continuar.',
    };
  }
  return { message: null };
};

const readSignatureReport = (encodedReport) => {
  if (!encodedReport) return null;
  try {
    const padded = `${encodedReport}${'='.repeat((4 - (encodedReport.length % 4)) % 4)}`;
    return JSON.parse(window.atob(padded.replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return null;
  }
};

const notifyPendingSignatures = (report) => {
  if (!report?.requiere_atencion || !Array.isArray(report.pendientes) || !report.pendientes.length) {
    return;
  }
  const lines = report.pendientes.map((document) => {
    const pending = Array.isArray(document.firmas_pendientes)
      ? document.firmas_pendientes.join(', ')
      : 'Revisión requerida';
    return `• ${document.nombre || document.codigo}: ${pending}`;
  });
  window.alert(
    `El expediente se generó, pero hay formatos que requieren atención de firmas:\n\n${lines.join('\n')}\n\nLas firmas existentes no se sustituyen ni se borran. Revise estos formatos antes de imprimir o entregar el expediente.`
  );
};

const renderPdfLoadingScreen = (preview) => {
  if (!preview || preview.closed) return () => {};
  // Logo de la app (/logo.png), igual que Layout/Login/VerificarDocumento.
  // No usar official_logo_600dpi.png: trae un recorte con texto fragmentado
  // en el borde inferior que se ve "raro/incompleto" al mostrarlo.
  const logoUrl = `${window.location.origin}/logo.png?v=6`;
  // NOTA: sin <script> dentro del preview. La CSP del backend
  // (default-src 'self', sin script-src 'unsafe-inline') hereda al about:blank
  // y bloquea el inline-script, por eso se quedaba fijo en 8%.
  // La animación se maneja desde el opener con setInterval (sigue corriendo
  // ~1Hz en pestaña oculta, a diferencia de requestAnimationFrame que se pausa).
  preview.document.open();
  preview.document.write(`<!doctype html>
    <html lang="es">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Preparando documento · Hospital Escandón</title>
        <style>
          :root { color-scheme: light; font-family: Arial, Helvetica, sans-serif; }
          * { box-sizing: border-box; }
          body {
            margin: 0; min-height: 100vh; display: grid; place-items: center;
            color: #0f2a4e; background: linear-gradient(135deg, #f4f8fc 0%, #ffffff 52%, #edf7f6 100%);
          }
          .card {
            width: min(92vw, 560px); padding: 42px 44px 38px; text-align: center;
            background: rgba(255,255,255,.94); border: 1px solid #dce7f0;
            border-radius: 24px; box-shadow: 0 22px 60px rgba(15,42,78,.12);
          }
          .logo { width: min(82%, 330px); height: auto; object-fit: contain; margin: 0 auto 26px; display: block; }
          h1 { margin: 0; font-size: 20px; letter-spacing: -.02em; font-weight: 700; }
          p { margin: 9px 0 25px; color: #64748b; font-size: 14px; }
          .track { height: 12px; overflow: hidden; border-radius: 999px; background: #e5edf4; box-shadow: inset 0 1px 2px rgba(15,42,78,.08); }
          .bar {
            width: 8%; height: 100%; border-radius: inherit; position: relative;
            background: linear-gradient(90deg, #005fa9, #00a99d, #00a99d);
            box-shadow: 0 2px 8px rgba(0,95,169,.25);
            transition: width .2s linear;
          }
          .bar::after {
            content: ''; position: absolute; inset: 0; width: 44%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,.5), transparent);
            animation: progress-shine 1.8s ease-in-out infinite;
          }
          @keyframes progress-shine {
            from { transform: translateX(-130%); }
            to { transform: translateX(300%); }
          }
          .status { margin-top: 14px; color: #005fa9; font-size: 12px; font-weight: 700; letter-spacing: .04em; }
          .progress-value { margin-top: 7px; color: #64748b; font-size: 11px; font-variant-numeric: tabular-nums; }
          @media (prefers-reduced-motion: reduce) {
            .bar { width: 58%; }
            .bar::after { animation: none; }
          }
        </style>
      </head>
      <body>
        <main class="card" role="status" aria-live="polite" aria-label="Preparando documento">
          <img class="logo" src="${logoUrl}" alt="Bitácora HE · Hospital Escandón" />
          <h1>Preparando documento para impresión</h1>
          <p class="detail">Estamos leyendo los registros actuales del paciente.</p>
          <div class="track" role="progressbar" aria-label="Progreso de preparación" aria-valuemin="0" aria-valuemax="100" aria-valuenow="8"><div class="bar"></div></div>
          <div class="status">Consultando información clínica…</div>
          <div class="progress-value">Avance estimado: <span class="progress-number">8%</span></div>
        </main>
      </body>
    </html>`);
  preview.document.close();

  let nodes = null;
  try {
    const doc = preview.document;
    nodes = {
      bar: doc.querySelector('.bar'),
      status: doc.querySelector('.status'),
      detail: doc.querySelector('.detail'),
      track: doc.querySelector('.track'),
      progressNumber: doc.querySelector('.progress-number'),
    };
    if (!nodes.bar || !nodes.status || !nodes.detail || !nodes.track || !nodes.progressNumber) return () => {};
  } catch {
    return () => {};
  }

  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    try {
      nodes.bar.style.width = '58%';
      nodes.track.setAttribute('aria-valuenow', '58');
      nodes.progressNumber.textContent = '58%';
    } catch { /* decorativo */ }
    return () => {};
  }

  const stages = [
    { until: 25, status: 'Consultando información clínica…', detail: 'Estamos leyendo los registros actuales del paciente.' },
    { until: 52, status: 'Integrando formatos y estudios…', detail: 'Estamos reuniendo notas, formatos, laboratorio e imagenología.' },
    { until: 74, status: 'Validando firmas y versiones…', detail: 'Estamos comprobando que cada firma corresponda a su documento.' },
    { until: 88, status: 'Preparando el expediente final…', detail: 'Estamos ordenando la información para impresión y verificación.' },
    { until: 92, status: 'Unificando documentos…', detail: 'Casi terminamos. Conserva esta ventana abierta un momento.' },
  ];
  const startedAt = Date.now();
  let lastProgress = 8;

  const tick = () => {
    try {
      if (preview.closed) {
        window.clearInterval(timer);
        return;
      }
      const elapsed = Math.max(0, Date.now() - startedAt);
      // Avanza rápido al inicio y se desacelera hasta 92%. Nunca retrocede.
      const target = Math.min(92, 8 + 84 * (1 - Math.exp(-elapsed / 7000)));
      if (target > lastProgress) lastProgress = target;
      const rounded = Math.floor(lastProgress);
      nodes.bar.style.width = `${lastProgress.toFixed(2)}%`;
      nodes.track.setAttribute('aria-valuenow', String(rounded));
      nodes.progressNumber.textContent = `${rounded}%`;
      const stage = stages.find((item) => rounded <= item.until) || stages[stages.length - 1];
      nodes.status.textContent = stage.status;
      nodes.detail.textContent = stage.detail;
    } catch {
      // La ventana ya navegó al blob del PDF (acceso denegado): detener.
      window.clearInterval(timer);
    }
  };

  const timer = window.setInterval(tick, 200);
  tick();

  return () => {
    window.clearInterval(timer);
  };
};

/**
 * Opens a protected clinical PDF without putting the JWT in the URL.
 * Axios obtains the bytes with the existing Authorization interceptor and the
 * browser receives only a short-lived local Blob URL.
 */
export default function AuthenticatedPdfButton({
  endpoint,
  className = '',
  title,
  children,
  onSignatureRepair = null,
  onSignatureReport = null,
}) {
  const [loading, setLoading] = useState(false);

  const openPdf = async () => {
    if (loading) return;
    setLoading(true);
    const preview = window.open('about:blank', '_blank');
    const stopLoading = preview ? renderPdfLoadingScreen(preview) : () => {};
    if (preview) {
      preview.opener = null;
    }

    try {
      const request = resolvePdfRequest(endpoint);
      const response = await api.request({ ...request, responseType: 'blob' });
      const contentType = String(response.headers?.['content-type'] || 'application/pdf');
      if (!contentType.toLowerCase().includes('application/pdf')) {
        throw new Error('El servidor no devolvió un documento PDF.');
      }
      const serverFilename = parseContentDispositionFilename(response.headers?.['content-disposition']);
      const effectiveFilename = serverFilename || inferPdfFilenameFromEndpoint(endpoint);
      const pdfBlob = new Blob([response.data], { type: 'application/pdf' });
      const objectUrl = URL.createObjectURL(pdfBlob);
      stopLoading();
      openNamedPdfPreview(preview, objectUrl, effectiveFilename);
      const signatureReport = readSignatureReport(response.headers?.['x-hes-signature-report']);
      if (typeof onSignatureReport === 'function') {
        onSignatureReport(signatureReport);
      } else {
        notifyPendingSignatures(signatureReport);
      }
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 10 * 60 * 1000);
    } catch (error) {
      stopLoading();
      if (preview && !preview.closed) preview.close();
      const problem = await readErrorPayload(error);
      if (problem.action === 'REVISAR_Y_REFIRMAR') {
        const formats = Array.isArray(problem.formatos) ? problem.formatos : [];
        const formatLines = formats.map((item) => {
          const pending = Array.isArray(item.firmas_pendientes) && item.firmas_pendientes.length
            ? ` — pendiente: ${item.firmas_pendientes.join(', ')}`
            : '';
          return `• ${item.nombre || item.codigo}${pending}`;
        });
        const prompt = [
          problem.message,
          formatLines.length ? `\nFormatos a revisar:\n${formatLines.join('\n')}` : '',
          `\n${problem.question || '¿Desea revisar y volver a firmar la versión vigente?'}`,
        ].join('');
        if (window.confirm(prompt)) {
          if (typeof onSignatureRepair === 'function') {
            onSignatureRepair(problem);
          } else {
            window.alert('Abra la pestaña “Formatos Clínicos” para revisar y firmar nuevamente la versión vigente.');
          }
        }
      } else {
        alert(problem.message || error?.message || 'No se pudo abrir el documento. Revise su sesión e intente de nuevo.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={openPdf}
      disabled={loading}
      aria-busy={loading}
      className={`${className} disabled:cursor-wait disabled:opacity-70`}
      title={title}
    >
      {loading ? <FiRotateCcw className="animate-spin" /> : children}
    </button>
  );
}

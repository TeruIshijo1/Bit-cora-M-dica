import { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import workerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { NAMED_PDF_PREVIEW_KEY } from '../utils/namedPdfPreview';
import { normalizePdfDownloadName } from '../utils/pdfFilename';

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

const readPreview = () => {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(NAMED_PDF_PREVIEW_KEY) || 'null');
    if (!saved?.blobUrl?.startsWith(`blob:${window.location.origin}/`)) return null;
    return {
      blobUrl: saved.blobUrl,
      filename: normalizePdfDownloadName(saved.filename),
    };
  } catch {
    return null;
  }
};

export default function PdfPreviewPage() {
  const [preview] = useState(readPreview);
  const [pdf, setPdf] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState('');
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.25);
  const [error, setError] = useState('');
  const canvasRef = useRef(null);
  const downloadRef = useRef(null);

  useEffect(() => {
    window.sessionStorage.removeItem(NAMED_PDF_PREVIEW_KEY);
    if (preview) document.title = `${preview.filename} · Hospital Escandón`;
  }, [preview]);

  useEffect(() => {
    if (!preview) return undefined;
    let active = true;
    let task;
    let localUrl;

    (async () => {
      try {
        const response = await fetch(preview.blobUrl);
        if (!response.ok) throw new Error('El PDF ya no está disponible en esta pestaña.');
        const blob = await response.blob();
        if (!active) return;
        localUrl = URL.createObjectURL(blob);
        task = pdfjsLib.getDocument({
          data: new Uint8Array(await blob.arrayBuffer()),
          useSystemFonts: true,
          isEvalSupported: false,
        });
        const documentPdf = await task.promise;
        if (!active) return;
        setPdf(documentPdf);
        setDownloadUrl(localUrl);
      } catch (cause) {
        if (active) setError(cause?.message || 'No se pudo abrir el PDF.');
      }
    })();

    return () => {
      active = false;
      task?.destroy();
      if (localUrl) URL.revokeObjectURL(localUrl);
    };
  }, [preview]);

  useEffect(() => {
    if (!pdf) return undefined;
    let active = true;
    let renderTask;

    (async () => {
      try {
        const page = await pdf.getPage(pageNumber);
        if (!active || !canvasRef.current) return;
        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.floor(viewport.width * pixelRatio);
        canvas.height = Math.floor(viewport.height * pixelRatio);
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;
        const context = canvas.getContext('2d');
        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
        renderTask = page.render({ canvasContext: context, viewport });
        await renderTask.promise;
      } catch (cause) {
        if (active && cause?.name !== 'RenderingCancelledException') {
          setError('No se pudo mostrar esta página del PDF.');
        }
      }
    })();

    return () => {
      active = false;
      renderTask?.cancel();
    };
  }, [pdf, pageNumber, scale]);

  useEffect(() => {
    const saveWithName = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's' && downloadRef.current) {
        event.preventDefault();
        downloadRef.current.click();
      }
    };
    window.addEventListener('keydown', saveWithName);
    return () => window.removeEventListener('keydown', saveWithName);
  }, []);

  return (
    <main className="h-screen flex flex-col bg-slate-100 text-slate-800">
      <header className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-bold text-sm">{preview?.filename || 'Documento clínico'}</h1>
          <p className="text-xs text-slate-500">Hospital Escandón · PDF original</p>
        </div>
        {pdf && (
          <div className="flex items-center gap-2 text-sm">
            <button type="button" className="rounded-lg border px-3 py-1.5 disabled:opacity-40" disabled={pageNumber === 1} onClick={() => setPageNumber((number) => number - 1)}>Anterior</button>
            <span className="whitespace-nowrap">{pageNumber} / {pdf.numPages}</span>
            <button type="button" className="rounded-lg border px-3 py-1.5 disabled:opacity-40" disabled={pageNumber === pdf.numPages} onClick={() => setPageNumber((number) => number + 1)}>Siguiente</button>
            <button type="button" className="rounded-lg border px-3 py-1.5" onClick={() => setScale((value) => Math.max(0.6, value - 0.2))}>−</button>
            <button type="button" className="rounded-lg border px-3 py-1.5" onClick={() => setScale((value) => Math.min(3, value + 0.2))}>+</button>
          </div>
        )}
        {downloadUrl && (
          <a ref={downloadRef} href={downloadUrl} download={preview.filename} className="rounded-lg bg-hes-blue-main px-4 py-2 text-sm font-bold text-white">Descargar PDF</a>
        )}
        {downloadUrl && (
          <button type="button" className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold" onClick={() => window.open(downloadUrl, '_blank')}>Imprimir</button>
        )}
      </header>
      <section className="min-h-0 flex-1 overflow-auto p-4 text-center">
        {!preview && <p className="mt-12 text-sm">La vista previa ya no está disponible. Abra el PDF nuevamente desde el expediente.</p>}
        {preview && !pdf && !error && <p className="mt-12 text-sm">Preparando documento…</p>}
        {error && <p className="mt-12 text-sm text-red-700">{error}</p>}
        {pdf && !error && <canvas ref={canvasRef} className="mx-auto bg-white shadow-lg" />}
      </section>
    </main>
  );
}

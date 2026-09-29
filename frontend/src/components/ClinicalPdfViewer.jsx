import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import workerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { openNamedPdfPreview } from '../utils/namedPdfPreview';
import { shouldReloadForMissingAsset } from '../utils/dynamicImportRecovery';
import {
  FiMousePointer, FiEdit2, FiUnderline, FiEdit3, FiMessageSquare,
  FiSquare, FiTrash2, FiSave, FiDownload, FiPrinter, FiX,
  FiChevronLeft, FiChevronRight, FiZoomIn, FiZoomOut, FiRotateCw,
  FiMaximize2, FiMinimize2, FiList, FiFileText, FiCheck, FiExternalLink,
} from 'react-icons/fi';

if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc || `https://unpkg.com/pdfjs-dist@${pdfjsLib.version || '4.0.379'}/build/pdf.worker.min.mjs`;
}

const COLORS = [
  { id: 'black', value: 'rgba(15, 23, 42, 0.95)', solid: '#0f172a', label: 'Negro' },
  { id: 'yellow', value: 'rgba(253, 224, 71, 0.55)', solid: '#eab308', label: 'Amarillo' },
  { id: 'green', value: 'rgba(110, 231, 183, 0.55)', solid: '#059669', label: 'Verde' },
  { id: 'pink', value: 'rgba(249, 168, 212, 0.55)', solid: '#db2777', label: 'Rosa' },
  { id: 'blue', value: 'rgba(147, 197, 253, 0.55)', solid: '#2563eb', label: 'Azul' },
  { id: 'red', value: 'rgba(252, 165, 165, 0.6)', solid: '#dc2626', label: 'Rojo' },
];

const TOOLS = [
  { id: 'select', icon: FiMousePointer, label: 'Seleccionar / leer' },
  { id: 'highlight', icon: FiEdit2, label: 'Resaltador' },
  { id: 'underline', icon: FiUnderline, label: 'Subrayar' },
  { id: 'pen', icon: FiEdit3, label: 'Pluma libre' },
  { id: 'note', icon: FiMessageSquare, label: 'Nota clínica' },
  { id: 'rect', icon: FiSquare, label: 'Recuadro' },
  { id: 'eraser', icon: FiTrash2, label: 'Borrar marca' },
];

const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
const storageKey = (docId) => `hes-pdf-annots::${docId || 'default'}`;

/* ---------------- Página individual ---------------- */
function PdfPage({
  pdfDoc, pageNumber, scale, rotation, tool, color, penWidth,
  annots, onCommit, onDelete, registerRef, annotateMode,
}) {
  const canvasRef = useRef(null);
  const textRef = useRef(null);
  const wrapRef = useRef(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [rendering, setRendering] = useState(true);
  const [draft, setDraft] = useState(null); // {x1,y1,x2,y2,points[]}
  const drawingRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    const render = async () => {
      if (!pdfDoc) return;
      setRendering(true);
      try {
        const page = await pdfDoc.getPage(pageNumber);
        const viewport = page.getViewport({ scale, rotation });
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const canvas = canvasRef.current;
        if (!canvas) return;
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;
        const ctx = canvas.getContext('2d');
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        await page.render({ canvasContext: ctx, viewport }).promise;
        if (cancelled) return;
        setSize({ w: viewport.width, h: viewport.height });

        // Capa de texto seleccionable (nativa)
        const textContent = await page.getTextContent();
        const layer = textRef.current;
        if (layer) {
          layer.innerHTML = '';
          layer.style.width = `${viewport.width}px`;
          layer.style.height = `${viewport.height}px`;
          textContent.items.forEach((item) => {
            if (!item.str?.trim()) return;
            const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
            const fontSize = Math.hypot(tx[2], tx[3]);
            const el = document.createElement('span');
            el.textContent = item.str;
            el.style.cssText = `position:absolute;left:${tx[4]}px;top:${tx[5] - fontSize}px;font-size:${fontSize}px;font-family:sans-serif;white-space:pre;transform-origin:0 0;color:transparent;cursor:text;`;
            // selección visible tenue
            el.addEventListener('mouseup', () => {});
            layer.appendChild(el);
          });
          // ::selection se estiliza por CSS global inline abajo
        }
      } catch (e) {
        console.error('Error render página PDF', e);
      } finally {
        if (!cancelled) setRendering(false);
      }
    };
    render();
    return () => { cancelled = true; };
  }, [pdfDoc, pageNumber, scale, rotation]);

  const toNorm = (e) => {
    const r = wrapRef.current.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    const y = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
    return { x, y };
  };

  const onDown = (e) => {
    if (!annotateMode || tool === 'select' || tool === 'eraser') return;
    if (e.button !== 0) return;
    const p = toNorm(e);
    drawingRef.current = true;
    if (tool === 'pen') setDraft({ x1: p.x, y1: p.y, x2: p.x, y2: p.y, points: [p] });
    else setDraft({ x1: p.x, y1: p.y, x2: p.x, y2: p.y, points: [] });
  };
  const onMove = (e) => {
    if (!drawingRef.current || !draft) return;
    const p = toNorm(e);
    if (tool === 'pen') setDraft((d) => ({ ...d, x2: p.x, y2: p.y, points: [...(d.points || []), p] }));
    else setDraft((d) => ({ ...d, x2: p.x, y2: p.y }));
  };
  const finish = (e) => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    if (!draft) return;
    const end = e?.clientX ? toNorm(e) : { x: draft.x2, y: draft.y2 };
    const d = { ...draft, x2: end.x, y2: end.y };
    if (tool === 'pen' && e?.clientX) d.points = [...(d.points || []), end];
    setDraft(null);
    if (tool === 'note') {
      onCommit({
        id: uid(), page: pageNumber, type: 'note',
        x1: d.x1, y1: d.y1, x2: d.x1 + 0.001, y2: d.y1 + 0.001,
        points: [], color, width: penWidth, text: '',
        createdAt: new Date().toISOString(), draftText: true,
      });
      return;
    }
    const w = Math.abs(d.x2 - d.x1);
    const h = Math.abs(d.y2 - d.y1);
    if (tool === 'pen') {
      if ((d.points || []).length < 2) return;
      onCommit({
        id: uid(), page: pageNumber, type: 'pen',
        x1: 0, y1: 0, x2: 1, y2: 1, points: d.points,
        color, width: penWidth, text: '', createdAt: new Date().toISOString(),
      });
    } else {
      if (w < 0.005 && h < 0.004) return;
      onCommit({
        id: uid(), page: pageNumber, type: tool,
        x1: Math.min(d.x1, d.x2), y1: Math.min(d.y1, d.y2),
        x2: Math.max(d.x1, d.x2), y2: Math.max(d.y1, d.y2),
        points: [], color, width: penWidth, text: '', createdAt: new Date().toISOString(),
      });
    }
  };

  const draftRect = draft ? {
    x: Math.min(draft.x1, draft.x2), y: Math.min(draft.y1, draft.y2),
    w: Math.abs(draft.x2 - draft.x1), h: Math.abs(draft.y2 - draft.y1),
  } : null;

  return (
    <div
      ref={(el) => registerRef(pageNumber, el)}
      data-page={pageNumber}
      className="relative mx-auto w-fit bg-white rounded-lg shadow-[0_1px_8px_rgba(15,23,42,0.12)] border border-slate-200 overflow-hidden"
      style={{ width: size.w || '100%', maxWidth: 'none' }}
    >
      {rendering && (
        <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2" style={{ minHeight: 300 }}>
          <span className="w-5 h-5 border-[3px] border-slate-300 border-t-hes-blue-main rounded-full animate-spin" />
          Renderizando página {pageNumber}…
        </div>
      )}
      <div
        ref={wrapRef}
        className="relative"
        style={{ width: size.w || 'auto', height: size.h || 'auto', maxWidth: 'none' }}
        onMouseDown={onDown}
        onMouseMove={onMove}
        onMouseUp={finish}
        onMouseLeave={() => { if (drawingRef.current) finish(); }}
      >
        <canvas ref={canvasRef} className="block select-none" />
        {/* texto seleccionable */}
        <div
          ref={textRef}
          className="absolute inset-0 overflow-hidden pdf-text-layer"
          style={{ pointerEvents: annotateMode && tool !== 'select' ? 'none' : 'auto' }}
        />
        {/* anotaciones guardadas */}
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 1 1"
          preserveAspectRatio="none"
          style={{ pointerEvents: tool === 'eraser' ? 'auto' : 'none' }}
        >
          {annots.map((a) => {
            const common = {
              key: a.id,
              style: tool === 'eraser'
                ? { pointerEvents: 'auto', cursor: 'not-allowed' }
                : { pointerEvents: 'none' },
              onClick: tool === 'eraser' ? (ev) => { ev.stopPropagation(); onDelete(a.id); } : undefined,
            };
            if (a.type === 'highlight') {
              return <rect {...common} x={a.x1} y={a.y1} width={Math.max(0.001, a.x2 - a.x1)} height={Math.max(0.002, a.y2 - a.y1)} fill={a.color} rx={0.004} />;
            }
            if (a.type === 'underline') {
              return <line {...common} x1={a.x1} x2={a.x2} y1={a.y2} y2={a.y2} stroke={a.color.replace(/[\d.]+\)$/, '1)').replace('rgba', 'rgb').split(',').slice(0, 3).join(',') + ')'} strokeWidth={0.006} strokeLinecap="round" />;
            }
            if (a.type === 'rect') {
              return <rect {...common} x={a.x1} y={a.y1} width={Math.max(0.001, a.x2 - a.x1)} height={Math.max(0.001, a.y2 - a.y1)} fill="none" stroke={a.color.replace(/[\d.]+\)$/, '1)').replace('rgba', 'rgb').split(',').slice(0, 3).join(',') + ')'} strokeWidth={0.005} rx={0.004} />;
            }
            if (a.type === 'pen' && a.points?.length) {
              const penStroke = (a.color && a.color.startsWith('rgba')) ? a.color.replace(/[\d.]+\)$/, '0.95)') : (a.color || '#2563eb');
              return <polyline {...common} points={a.points.map((p) => `${p.x},${p.y}`).join(' ')} fill="none" stroke={penStroke} strokeWidth={0.003 + (a.width || 2) * 0.0015} strokeLinecap="round" strokeLinejoin="round" />;
            }
            return null;
          })}
          {/* borrador en curso */}
          {draftRect && tool !== 'pen' && tool !== 'note' && (
            tool === 'highlight'
              ? <rect x={draftRect.x} y={draftRect.y} width={draftRect.w} height={Math.max(draftRect.h, 0.008)} fill={color} rx={0.004} />
              : tool === 'underline'
                ? <line x1={draftRect.x} x2={draftRect.x + draftRect.w} y1={draftRect.y + draftRect.h} y2={draftRect.y + draftRect.h} stroke="#dc2626" strokeWidth={0.006} strokeLinecap="round" />
                : <rect x={draftRect.x} y={draftRect.y} width={draftRect.w} height={draftRect.h} fill="none" stroke="#2563eb" strokeWidth={0.005} strokeDasharray="0.01 0.006" />
          )}
          {draft?.points?.length > 1 && tool === 'pen' && (
            <polyline points={draft.points.map((p) => `${p.x},${p.y}`).join(' ')} fill="none" stroke={(color && color.startsWith('rgba')) ? color.replace(/[\d.]+\)$/, '0.95)') : (color || '#2563eb')} strokeWidth={0.003 + (penWidth || 2) * 0.0015} strokeLinecap="round" strokeLinejoin="round" />
          )}
        </svg>
        {/* pines de nota */}
        {annots.filter((a) => a.type === 'note').map((a) => (
          <button
            key={a.id}
            type="button"
            title={a.text || 'Nota clínica'}
            onClick={(ev) => {
              if (tool === 'eraser') { ev.stopPropagation(); onDelete(a.id); }
              else onCommit({ ...a, focus: true });
            }}
            className={`absolute w-6 h-6 -ml-3 -mt-3 rounded-full shadow border-2 border-white flex items-center justify-center text-white ${tool === 'eraser' ? 'cursor-not-allowed animate-pulse' : 'cursor-pointer hover:scale-110 transition-transform'}`}
            style={{ left: `${a.x1 * 100}%`, top: `${a.y1 * 100}%`, background: '#f59e0b', pointerEvents: 'auto' }}
          >
            <FiMessageSquare className="text-xs" />
          </button>
        ))}
        {/* cursor contextual */}
        {annotateMode && tool !== 'select' && (
          <div className={`absolute inset-0 ${tool === 'eraser' ? 'cursor-not-allowed' : 'cursor-crosshair'}`} style={{ pointerEvents: 'none' }} />
        )}
      </div>
      <style>{`.pdf-text-layer span::selection{background:rgba(37,99,235,.25);color:transparent;}`}</style>
    </div>
  );
}

/* ---------------- Visor principal ---------------- */
export default function ClinicalPdfViewer({
  fileUrl, fileData = null, docId, title = 'Documento PDF', meta = '',
  downloadName = 'documento.pdf', onClose, onOpenNewTab,
}) {
  const [pdfDoc, setPdfDoc] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [scale, setScale] = useState(1.8);
  const [rotation, setRotation] = useState(0);
  const [activePage, setActivePage] = useState(1);
  const [pageJump, setPageJump] = useState('1');
  const [annotateMode, setAnnotateMode] = useState(false);
  const [tool, setTool] = useState('highlight');
  const [color, setColor] = useState(COLORS[0].value);
  const [penWidth, setPenWidth] = useState(2);
  const [annots, setAnnots] = useState([]);
  const [history, setHistory] = useState({ undo: [], redo: [] });
  const [showNotes, setShowNotes] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [noteDraft, setNoteDraft] = useState('');
  const [toast, setToast] = useState('');
  const [retryCount, setRetryCount] = useState(0);

  const scrollRef = useRef(null);
  const pageEls = useRef({});
  const registerRef = useCallback((n, el) => { if (el) pageEls.current[n] = el; }, []);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 2200);
  };

  // Cargar PDF desde el Blob autenticado; fileUrl queda para descargar/abrir fuera.
  useEffect(() => {
    let alive = true;
    let docInstance = null;
    setLoading(true);
    setLoadError('');
    setPdfDoc(null);
    setNumPages(0);
    (async () => {
      try {
        let buf;
        if (fileData instanceof Blob) {
          buf = await fileData.arrayBuffer();
        } else {
          const res = await fetch(fileUrl);
          if (!res.ok) throw new Error(`HTTP ${res.status} al obtener el PDF`);
          buf = await res.arrayBuffer();
        }
        if (!alive) return;
        const data = new Uint8Array(buf);
        try {
          const loadingTask = pdfjsLib.getDocument({
            data,
            useSystemFonts: true,
            isEvalSupported: false,
          });
          docInstance = await loadingTask.promise;
        } catch (workerErr) {
          console.warn('[ClinicalPdfViewer] El worker local no pudo procesar el PDF.', workerErr);
          try {
            const workerResponse = await fetch(workerSrc, { method: 'HEAD', cache: 'no-store' });
            if (
              (workerResponse.status === 404 || workerResponse.status === 410)
              && shouldReloadForMissingAsset(workerSrc, window.sessionStorage)
            ) {
              window.location.reload();
              return;
            }
          } catch {
            // Conserva el error original de PDF.js; no se depende de CDNs externos.
          }
          throw workerErr;
        }
        if (!alive) return;
        setPdfDoc(docInstance);
        setNumPages(docInstance.numPages);
        setLoading(false);
      } catch (e) {
        console.error('[ClinicalPdfViewer] Error cargando PDF:', e);
        if (alive) {
          setLoadError(e?.message || 'No se pudo renderizar el PDF en el visor nativo.');
          setLoading(false);
        }
      }
    })();
    return () => {
      alive = false;
      try { docInstance?.destroy(); } catch {}
    };
  }, [fileData, fileUrl, retryCount]);

  // Cargar / guardar anotaciones
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey(docId));
      setAnnots(raw ? JSON.parse(raw) : []);
    } catch { setAnnots([]); }
    setHistory({ undo: [], redo: [] });
    setActivePage(1);
    setPageJump('1');
  }, [docId]);

  useEffect(() => {
    try { localStorage.setItem(storageKey(docId), JSON.stringify(annots)); } catch {}
  }, [annots, docId]);

  // Spy de página activa
  useEffect(() => {
    const root = scrollRef.current;
    if (!root) return;
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) {
          const n = Number(en.target.dataset.page);
          if (n) { setActivePage(n); setPageJump(String(n)); }
        }
      });
    }, { root, threshold: 0.4 });
    Object.values(pageEls.current).forEach((el) => el && obs.observe(el));
    return () => obs.disconnect();
  }, [numPages, scale, rotation, pdfDoc, expanded]);

  const pushHistory = (prev) => {
    setHistory((h) => ({ undo: [...h.undo.slice(-29), prev], redo: [] }));
  };

  const handleCommit = useCallback((a) => {
    if (a.focus) {
      setEditingNoteId(a.id);
      setNoteDraft(a.text || '');
      setShowNotes(true);
      return;
    }
    setAnnots((prev) => {
      pushHistory(prev);
      if (a.draftText) {
        setEditingNoteId(a.id);
        setNoteDraft('');
        setShowNotes(true);
        return [...prev, a];
      }
      return [...prev, a];
    });
    if (!a.draftText && !a.focus) showToast('Marca agregada ✓');
  }, []);

  const handleDelete = useCallback((id) => {
    setAnnots((prev) => { pushHistory(prev); return prev.filter((a) => a.id !== id); });
  }, []);

  const undo = () => {
    setHistory((h) => {
      if (!h.undo.length) return h;
      const prev = h.undo[h.undo.length - 1];
      setAnnots((cur) => cur);
      setTimeout(() => setAnnots(prev), 0);
      return { undo: h.undo.slice(0, -1), redo: [...h.redo, annots] };
    });
  };
  const redo = () => {
    setHistory((h) => {
      if (!h.redo.length) return h;
      const next = h.redo[h.redo.length - 1];
      setTimeout(() => setAnnots(next), 0);
      return { undo: [...h.undo, annots], redo: h.redo.slice(0, -1) };
    });
  };

  const goTo = (n) => {
    const target = Math.min(numPages, Math.max(1, n));
    pageEls.current[target]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setActivePage(target);
  };

  const fitWidth = () => {
    const el = scrollRef.current;
    if (!el) return;
    const baseW = 595; // ancho carta en pt a escala 1
    // scrollRef ya excluye el panel de notas (flex-1), solo restamos padding lateral
    const avail = el.clientWidth - 24;
    setScale(Math.min(3.0, Math.max(0.6, avail / baseW)));
  };

  const saveNoteText = () => {
    if (!editingNoteId) return;
    setAnnots((prev) => {
      pushHistory(prev);
      return prev.map((a) => (a.id === editingNoteId ? { ...a, text: noteDraft, draftText: false } : a));
    });
    setEditingNoteId(null);
    setNoteDraft('');
    showToast('Nota guardada ✓');
  };

  const exportNotes = () => {
    const lines = [
      `NOTAS CLÍNICAS SOBRE PDF — ${title}`,
      `${meta} · Fecha: ${new Date().toLocaleString('es-MX')}`,
      `Total de marcas: ${annots.length}`,
      '—'.repeat(40),
      ...annots.map((a, i) => {
        const tipo = { highlight: 'RESALTADO', underline: 'SUBRAYADO', pen: 'TRAZO', note: 'NOTA', rect: 'RECUADRO' }[a.type] || a.type;
        return `${i + 1}. [${tipo}] Pág. ${a.page}${a.text ? ` — ${a.text}` : ''}`;
      }),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `notas-${docId || 'pdf'}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const editingNote = annots.find((a) => a.id === editingNoteId);

  const viewerBody = (
    <div className={`flex flex-col bg-slate-100 rounded-2xl border border-slate-200 overflow-hidden shadow-sm ${expanded ? 'h-full' : ''}`}>
      {/* Barra superior nativa */}
      <div className="he-viewer-topbar flex items-center gap-2 px-3 py-2.5 backdrop-blur flex-wrap">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className="p-2 rounded-xl text-white shrink-0" style={{ background: 'linear-gradient(135deg,#0e7490,#06b6d4)', boxShadow: '0 4px 10px -4px rgba(14,116,144,0.7)' }}>
            <FiFileText className="text-base" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-bold text-slate-800 truncate leading-tight">{title}</p>
            {meta && <p className="text-[10px] text-slate-400 truncate">{meta}</p>}
          </div>
          <span className="hidden sm:inline-flex text-[10px] font-black px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
            ● {annots.length} marca{annots.length === 1 ? '' : 's'}
          </span>
          <span className="hidden lg:inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-1 rounded-full bg-blue-50 text-hes-blue-main border border-blue-200 shrink-0" title="El archivo original en la base de datos se mantiene 100% íntegro. Las anotaciones son una capa clínica de uso interno.">
            🛡️ Doc. Original Íntegro
          </span>
        </div>

        <div className="flex items-center gap-1 text-slate-600">
          <button type="button" onClick={() => goTo(activePage - 1)} disabled={activePage <= 1} className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-30" title="Página anterior">
            <FiChevronLeft />
          </button>
          <span className="text-[11px] font-semibold flex items-center gap-1">
            <input
              value={pageJump}
              onChange={(e) => setPageJump(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') goTo(parseInt(pageJump, 10) || 1); }}
              className="w-9 text-center border border-slate-200 rounded-md py-0.5 text-[11px] font-bold text-slate-700 outline-none focus:border-hes-blue-main"
            />
            <span className="text-slate-400">/ {numPages || '–'}</span>
          </span>
          <button type="button" onClick={() => goTo(activePage + 1)} disabled={activePage >= numPages} className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-30" title="Página siguiente">
            <FiChevronRight />
          </button>
        </div>

        <div className="h-5 w-px bg-slate-200 hidden md:block" />

        <div className="flex items-center gap-1 text-slate-600">
          <button type="button" onClick={() => setScale((s) => Math.max(0.5, +(s - 0.15).toFixed(2)))} className="p-1.5 rounded-lg hover:bg-slate-100" title="Reducir zoom">
            <FiZoomOut />
          </button>
          <button type="button" onClick={fitWidth} className="text-[11px] font-bold px-2 py-1 rounded-lg hover:bg-slate-100 min-w-[52px]" title="Ajustar al ancho">
            {Math.round(scale * 100)}%
          </button>
          <button type="button" onClick={() => setScale((s) => Math.min(3.0, +(s + 0.15).toFixed(2)))} className="p-1.5 rounded-lg hover:bg-slate-100" title="Ampliar zoom">
            <FiZoomIn />
          </button>
          <button type="button" onClick={() => setRotation((r) => (r + 90) % 360)} className="p-1.5 rounded-lg hover:bg-slate-100" title="Rotar">
            <FiRotateCw />
          </button>
        </div>

        <div className="h-5 w-px bg-slate-200 hidden md:block" />

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => { setAnnotateMode((v) => !v); if (!annotateMode) setTool('highlight'); }}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-[11px] font-black transition-all shadow-sm ${annotateMode ? 'bg-amber-400 text-amber-950 hover:bg-amber-500' : 'text-white hover:brightness-110'}`}
            style={!annotateMode ? { background: 'linear-gradient(135deg,#0f2a4e,#004687)' } : undefined}
            title="Activar herramientas de anotación"
          >
            <FiEdit3 /> {annotateMode ? 'Anotando…' : '✨ Anotar'}
          </button>
          <button type="button" onClick={() => setShowNotes((v) => !v)} className={`p-1.5 rounded-lg border ${showNotes ? 'bg-blue-50 text-hes-blue-main border-blue-200' : 'text-slate-500 hover:bg-slate-100 border-transparent'}`} title="Panel de notas">
            <FiList />
          </button>
          {onOpenNewTab && (
            <button type="button" onClick={onOpenNewTab} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100" title="Abrir en pestaña nueva">
              <FiExternalLink />
            </button>
          )}
          <a href={fileUrl} download={downloadName} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100" title="Descargar PDF original">
            <FiDownload />
          </a>
          <button type="button" onClick={() => openNamedPdfPreview(window.open('about:blank', '_blank'), fileUrl, downloadName)} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100" title="Abrir vista para imprimir">
            <FiPrinter />
          </button>
          <button type="button" onClick={() => setExpanded((v) => !v)} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100" title={expanded ? 'Salir de pantalla completa' : 'Pantalla completa'}>
            {expanded ? <FiMinimize2 /> : <FiMaximize2 />}
          </button>
          {onClose && (
            <button type="button" onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-600" title="Cerrar visor">
              <FiX />
            </button>
          )}
        </div>
      </div>

      {/* Barra de anotación */}
      {annotateMode && (
        <div className="flex items-center gap-1.5 px-3 py-2 bg-amber-50/80 border-b border-amber-100 flex-wrap animate-fadeIn">
          <div className="flex items-center gap-1 bg-white rounded-xl border border-amber-200 p-1">
            {TOOLS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTool(t.id)}
                title={t.label}
                className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-[11px] font-bold transition-all ${tool === t.id ? 'bg-slate-900 text-white shadow' : 'text-slate-600 hover:bg-slate-100'}`}
              >
                <t.icon className="text-sm" />
                <span className="hidden lg:inline">{t.label}</span>
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1 bg-white rounded-xl border border-slate-200 p-1.5">
            {COLORS.map((c) => (
              <button
                key={c.id}
                type="button"
                title={c.label}
                onClick={() => setColor(c.value)}
                className={`w-6 h-6 rounded-full border-2 transition-all ${color === c.value ? 'border-slate-900 scale-110' : 'border-white shadow'}`}
                style={{ background: c.solid }}
              />
            ))}
          </div>
          {(tool === 'pen' || tool === 'underline') && (
            <div className="flex items-center gap-2 bg-white rounded-xl border border-slate-200 px-2.5 py-1.5">
              <span className="text-[10px] font-bold text-slate-500 uppercase">Trazo</span>
              <input type="range" min={1} max={6} value={penWidth} onChange={(e) => setPenWidth(Number(e.target.value))} className="w-20 accent-slate-900" />
            </div>
          )}
          <div className="flex items-center gap-1 ml-auto">
            <button type="button" onClick={undo} disabled={!history.undo.length} className="text-[11px] font-bold px-2 py-1.5 rounded-lg text-slate-600 hover:bg-white disabled:opacity-30">Deshacer</button>
            <button type="button" onClick={redo} disabled={!history.redo.length} className="text-[11px] font-bold px-2 py-1.5 rounded-lg text-slate-600 hover:bg-white disabled:opacity-30">Rehacer</button>
            <button type="button" onClick={() => { if (window.confirm('¿Borrar todas las marcas de este documento?')) { pushHistory(annots); setAnnots([]); } }} className="text-[11px] font-bold px-2 py-1.5 rounded-lg text-rose-600 hover:bg-rose-50">Limpiar</button>
          </div>
          <p className="w-full text-[10px] text-amber-800/80 font-medium">
            {tool === 'select' && 'Modo lectura: selecciona y copia texto del estudio.'}
            {tool === 'highlight' && 'Arrastra sobre el texto para resaltarlo.'}
            {tool === 'underline' && 'Arrastra para subrayar un valor o hallazgo.'}
            {tool === 'pen' && 'Dibuja a mano alzada: encierra valores, flechas, marcas.'}
            {tool === 'note' && 'Haz clic donde va la nota clínica y escribe el comentario.'}
            {tool === 'rect' && 'Arrastra para crear un recuadro de interés.'}
            {tool === 'eraser' && 'Haz clic sobre una marca para eliminarla.'}
          </p>
        </div>
      )}

      {/* Cuerpo */}
      <div className="flex min-h-0" style={{ height: expanded ? 'calc(100vh - 220px)' : 680 }}>
        <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-auto p-2 sm:p-3 space-y-4 bg-slate-100">
          {loading && (
            <div className="flex flex-col items-center justify-center py-24 text-slate-400 text-xs gap-3">
              <span className="w-8 h-8 border-4 border-slate-300 border-t-hes-blue-main rounded-full animate-spin" />
              Cargando documento clínico…
            </div>
          )}
          {loadError && (
            <div className="space-y-3">
              <div className="max-w-md mx-auto bg-white border border-amber-200 rounded-xl p-4 text-center text-xs">
                <p className="font-bold text-slate-700">El visor de anotaciones no pudo procesar este PDF</p>
                <p className="text-slate-400 mt-1 break-words">{loadError}</p>
                <div className="mt-3 flex justify-center gap-2">
                  <button type="button" onClick={() => setRetryCount((c) => c + 1)} className="px-3 py-2 rounded-lg bg-slate-900 text-white font-bold">Reintentar visor nativo</button>
                  <a href={fileUrl} download={downloadName} className="px-3 py-2 rounded-lg bg-slate-100 font-bold text-slate-700">Descargar</a>
                  {onOpenNewTab && <button type="button" onClick={onOpenNewTab} className="px-3 py-2 rounded-lg bg-slate-100 font-bold text-slate-700">Abrir fuera</button>}
                </div>
                <p className="mt-2 text-[10px] text-slate-400">El documento original sigue disponible para descargar o abrir fuera. Las anotaciones requieren el visor clínico.</p>
              </div>
            </div>
          )}
          {!loading && !loadError && pdfDoc && Array.from({ length: numPages }, (_, i) => i + 1).map((n) => (
            <PdfPage
              key={`${fileUrl}-${n}-${scale}-${rotation}`}
              pdfDoc={pdfDoc}
              pageNumber={n}
              scale={scale}
              rotation={rotation}
              tool={tool}
              color={color}
              penWidth={penWidth}
              annots={annots.filter((a) => a.page === n)}
              onCommit={handleCommit}
              onDelete={handleDelete}
              registerRef={registerRef}
              annotateMode={annotateMode}
            />
          ))}
        </div>

        {showNotes && (
          <aside className="w-60 shrink-0 bg-gradient-to-b from-white to-slate-50 border-l border-slate-200 hidden md:flex flex-col min-h-0">
            <div className="px-3 py-3 border-b border-slate-100 flex items-center justify-between bg-white">
              <p className="text-[11px] font-black text-slate-800 uppercase tracking-[0.1em] flex items-center gap-1.5">🩺 Notas del médico</p>
              <span className="text-[10px] font-black text-white bg-slate-800 px-2 py-0.5 rounded-full">{annots.length}</span>
            </div>
            <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
              {annots.length === 0 && (
                <div className="text-center py-8 px-2">
                  <FiMessageSquare className="mx-auto text-2xl text-slate-200 mb-2" />
                  <p className="text-[11px] text-slate-400 font-medium leading-relaxed">
                    Sin marcas todavía.<br />Activa <strong className="text-slate-600">Anotar</strong> y subraya valores, agrega notas o encierra hallazgos.
                  </p>
                </div>
              )}
              {annots.map((a, i) => (
                <div key={a.id} className={`p-2 rounded-xl border text-[11px] ${editingNoteId === a.id ? 'border-amber-300 bg-amber-50' : 'border-slate-150 bg-slate-50 border-slate-200'}`}>
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="font-black text-slate-600">#{i + 1} · Pág. {a.page}</span>
                    <span className="flex items-center gap-0.5">
                      <button type="button" onClick={() => goTo(a.page)} className="p-1 rounded hover:bg-white text-hes-blue-main" title="Ir a la marca"><FiChevronRight /></button>
                      <button type="button" onClick={() => handleDelete(a.id)} className="p-1 rounded hover:bg-white text-rose-500" title="Eliminar"><FiTrash2 /></button>
                    </span>
                  </div>
                  <span className="inline-block text-[9px] font-black uppercase tracking-wide px-1.5 py-0.5 rounded mb-1" style={{ background: a.color, color: a.color && (a.color.includes('15, 23, 42') || a.color.includes('#0f172a')) ? '#ffffff' : '#0f172a' }}>
                    {{ highlight: 'Resaltado', underline: 'Subrayado', pen: 'Trazo', note: 'Nota', rect: 'Recuadro' }[a.type]}
                  </span>
                  {a.type === 'note' ? (
                    editingNoteId === a.id ? (
                      <div className="space-y-1.5">
                        <textarea value={noteDraft} onChange={(e) => setNoteDraft(e.target.value)} rows={3} placeholder="Ej. Hemoglobina en límite bajo, correlacionar con clínica…" className="w-full text-[11px] border border-amber-300 rounded-lg p-1.5 outline-none focus:border-amber-500 bg-white" />
                        <div className="flex gap-1">
                          <button type="button" onClick={saveNoteText} className="flex-1 py-1 rounded-lg bg-slate-900 text-white text-[10px] font-bold flex items-center justify-center gap-1"><FiCheck /> Guardar</button>
                          <button type="button" onClick={() => { if (!a.text) handleDelete(a.id); setEditingNoteId(null); }} className="px-2 py-1 rounded-lg bg-white border text-[10px] font-bold text-slate-500">X</button>
                        </div>
                      </div>
                    ) : (
                      <button type="button" onClick={() => { setEditingNoteId(a.id); setNoteDraft(a.text || ''); }} className="block w-full text-left text-slate-600 leading-snug hover:text-slate-900">
                        {a.text || <span className="italic text-slate-400">Clic para escribir nota…</span>}
                      </button>
                    )
                  ) : (
                    <p className="text-slate-400 italic">Marca visual sobre el documento</p>
                  )}
                </div>
              ))}
            </div>
            <div className="p-2.5 border-t border-slate-100 grid grid-cols-2 gap-1.5">
              <button type="button" onClick={() => { pushHistory(annots); }} className="hidden" />
              <button type="button" onClick={exportNotes} disabled={!annots.length} className="flex items-center justify-center gap-1 py-2 rounded-xl bg-slate-900 text-white text-[10px] font-bold hover:bg-slate-700 disabled:opacity-30">
                <FiSave /> Exportar
              </button>
              <button type="button" onClick={() => setAnnotateMode((v) => !v)} className="flex items-center justify-center gap-1 py-2 rounded-xl bg-amber-100 text-amber-900 text-[10px] font-bold hover:bg-amber-200">
                <FiEdit3 /> {annotateMode ? 'Terminar' : 'Anotar'}
              </button>
            </div>
          </aside>
        )}
      </div>

      {/* Pie nativo */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-white border-t border-slate-200 text-[10px] text-slate-400 font-medium flex-wrap gap-1">
        <span>Visor clínico interactivo · Selección de texto · Anotaciones de uso interno</span>
        <span className="flex items-center gap-2">
          <span>Pág. {activePage} de {numPages || '–'}</span>
          <span className="hidden sm:inline">·</span>
          <span className="hidden sm:inline">Documento original inalterado</span>
        </span>
      </div>

      {toast && (
        <div className="absolute bottom-14 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-full bg-slate-900 text-white text-[11px] font-bold shadow-lg animate-fadeIn">
          {toast}
        </div>
      )}

      {/* Editor flotante de nota recién creada (móvil / escritorio) */}
      {editingNote && expanded === false && null}
    </div>
  );

  if (expanded) {
    return (
      <div className="fixed inset-0 z-[90] bg-slate-900/60 backdrop-blur-sm p-3 sm:p-6 flex flex-col animate-fadeIn">
        <div className="flex items-center justify-between text-white px-1 pb-2">
          <p className="text-xs font-bold truncate">{title} · pantalla completa</p>
          <button type="button" onClick={() => setExpanded(false)} className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-bold">
            <FiMinimize2 /> Cerrar expansión
          </button>
        </div>
        <div className="flex-1 min-h-0 relative">
          {viewerBody}
        </div>
      </div>
    );
  }

  return <div className="relative">{viewerBody}</div>;
}

export const pdfViewerStorageKey = storageKey;

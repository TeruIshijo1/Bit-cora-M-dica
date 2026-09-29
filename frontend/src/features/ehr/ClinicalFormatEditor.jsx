import { useEffect, useId, useRef } from 'react';
import { FiFileText, FiSave, FiX } from 'react-icons/fi';
import Button from '../../components/ui/Button';
import '../../styles/clinical-formats.css';

/** Shared presentation only; each format retains its fields, validation and save handler. */
export default function ClinicalFormatEditor({
  title, code, patient, onClose, onSubmit, isSaving = false, isEdit = false, children,
}) {
  const titleId = useId();
  const contextId = useId();
  const dialogRef = useRef(null);
  const headingRef = useRef(null);

  useEffect(() => {
    const previousFocus = document.activeElement;
    headingRef.current?.focus({ preventScroll: true });
    return () => {
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, []);

  const handleKeys = event => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      if (!isSaving) onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = [...dialogRef.current.querySelectorAll(
      'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]',
    )].filter(element => element.getClientRects().length > 0);
    const first = focusable[0];
    const last = focusable.at(-1);
    if (event.shiftKey && (document.activeElement === first || document.activeElement === headingRef.current)) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  };

  return (
    <div className="he-clinical-editor-overlay">
      <section
        className="he-clinical-editor" role="dialog" aria-modal="true"
        aria-labelledby={titleId} aria-describedby={contextId}
        ref={dialogRef} onKeyDown={handleKeys}
      >
        <header className="he-clinical-editor-header">
          <div className="he-clinical-editor-heading">
            <div className="he-clinical-editor-eyebrow"><FiFileText aria-hidden="true" /> {code || 'Formato clínico'}</div>
            <h2 id={titleId} ref={headingRef} tabIndex={-1}>{title}</h2>
            <p id={contextId} className="he-clinical-editor-patient">
              <strong>{patient?.name}</strong><span>{patient?.mrn}</span>
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSaving}
            aria-label="Cerrar formulario" className="he-clinical-editor-close"><FiX aria-hidden="true" /></Button>
        </header>
        <form className="he-clinical-editor-form" onSubmit={onSubmit} aria-busy={isSaving}>
          <div className="he-clinical-editor-body">{children}</div>
          <footer className="he-clinical-editor-footer">
            <span className="he-clinical-editor-hint">Revisa los datos antes de guardar.</span>
            <Button variant="outline" onClick={onClose} disabled={isSaving}>Cancelar</Button>
            <Button type="submit" disabled={isSaving} icon={<FiSave aria-hidden="true" />}>
              {isSaving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Guardar formato'}
            </Button>
          </footer>
        </form>
      </section>
    </div>
  );
}

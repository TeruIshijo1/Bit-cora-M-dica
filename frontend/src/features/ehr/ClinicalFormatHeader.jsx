import { Children, Fragment, isValidElement, useId, useState } from 'react';
import { FiChevronDown, FiUsers } from 'react-icons/fi';
import Button from '../../components/ui/Button';

function hasSignatureActions(children) {
  return Children.toArray(children).some(child => isValidElement(child)
    ? child.type === Fragment ? hasSignatureActions(child.props.children) : true
    : typeof child === 'string' && child.trim().length > 0);
}

export default function ClinicalFormatHeader({ identity, actions, signatureActions }) {
  const [signaturesOpen, setSignaturesOpen] = useState(false);
  const signaturesId = useId();
  const hasSignatures = hasSignatureActions(signatureActions);

  return (
    <header className="he-fmt-head he-clinical-format-header">
      <div className="he-clinical-format-top">
        {identity}
        <div className="he-clinical-document-actions he-clinical-main-actions">
          {hasSignatures && <Button variant="outline" size="sm" aria-expanded={signaturesOpen}
            aria-controls={signaturesId} onClick={() => setSignaturesOpen(open => !open)}
            className="he-clinical-signatures-toggle">
            <FiUsers aria-hidden="true" /> Firmas <FiChevronDown aria-hidden="true" />
          </Button>}
          {actions}
        </div>
      </div>
      <div id={signaturesId} hidden={!hasSignatures || !signaturesOpen} className="he-clinical-signatures-panel">
        <p>Firmas y autorizaciones</p>
        <div className="he-clinical-document-actions">{signatureActions}</div>
      </div>
    </header>
  );
}

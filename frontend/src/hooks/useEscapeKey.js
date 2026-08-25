import { useEffect } from 'react';

/**
 * Cierra un modal/ventana al presionar la tecla ESC.
 * @param {boolean} isOpen Indica si el modal está abierto.
 * @param {Function} onClose Función para cerrar el modal.
 */
export function useEscapeKey(isOpen, onClose) {
  useEffect(() => {
    if (!isOpen) return undefined;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);
}

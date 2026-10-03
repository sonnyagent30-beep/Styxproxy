'use client';

import { useEffect, useRef, useCallback } from 'react';

/**
 * Modal accessibility hook — adds Escape-to-close and focus trap.
 * 
 * Usage:
 *   const { modalRef, handleKeyDown } = useModalAccessibility(isOpen, onClose);
 *   <div ref={modalRef} onKeyDown={handleKeyDown} role="dialog" aria-modal="true" aria-labelledby="modal-title">
 *     <h2 id="modal-title">Title</h2>
 *     ...
 *   </div>
 */
export function useModalAccessibility(isOpen: boolean, onClose: () => void) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // Focus trap + Escape handling
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key !== 'Tab' || !modalRef.current) return;

      const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );

      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    },
    [onClose]
  );

  // Store previously focused element and focus the modal on open
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      // Focus the modal container after render
      requestAnimationFrame(() => {
        modalRef.current?.focus();
      });
    } else if (previousActiveElement.current) {
      // Restore focus when modal closes
      previousActiveElement.current.focus();
      previousActiveElement.current = null;
    }
  }, [isOpen]);

  // Attach keydown listener
  useEffect(() => {
    if (!isOpen) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, handleKeyDown]);

  return { modalRef, handleKeyDown };
}

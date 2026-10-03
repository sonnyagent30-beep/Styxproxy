'use client';

import { useState, useEffect, useRef } from 'react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
  onConfirm: (value?: string) => void;
  onCancel: () => void;
  /** If provided, shows a text input and passes its value to onConfirm */
  inputPlaceholder?: string;
  inputLabel?: string;
}

/**
 * Accessible confirmation modal with optional text input.
 * Used to replace window.confirm() and window.prompt() calls.
 */
export default function ConfirmModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'warning',
  onConfirm,
  onCancel,
  inputPlaceholder,
  inputLabel,
}: ConfirmModalProps) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setInputValue('');
      // Focus the input if present, otherwise the modal
      requestAnimationFrame(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        } else {
          modalRef.current?.focus();
        }
      });
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
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
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  const variantStyles = {
    danger: 'bg-red-500/10 border-red-500/30 text-red-400',
    warning: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400',
    info: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
  };

  const confirmStyles = {
    danger: 'bg-red-500 text-white hover:bg-red-600',
    warning: 'bg-yellow-500 text-black hover:bg-yellow-600',
    info: 'bg-blue-500 text-white hover:bg-blue-600',
  };

  const handleConfirm = () => {
    if (inputLabel && !inputValue.trim()) return;
    onConfirm(inputLabel ? inputValue : undefined);
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
      ref={modalRef}
      tabIndex={-1}
    >
      <div
        className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-xl font-bold mb-2" id="confirm-modal-title">
          {title}
        </h3>
        <p className="text-[var(--muted)] mb-4">{message}</p>

        {inputLabel && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">{inputLabel}</label>
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={inputPlaceholder}
              className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
            />
          </div>
        )}

        <div className={`p-3 rounded-xl border text-sm mb-4 ${variantStyles[variant]}`}>
          {message}
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={inputLabel && !inputValue.trim()}
            className={`flex-1 px-4 py-2 rounded-xl font-medium transition-colors disabled:opacity-50 ${confirmStyles[variant]}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

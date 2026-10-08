'use client';

import { useEffect, useState } from 'react';

interface ShortcutHelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const shortcuts: { keys: string; action: string }[] = [
  { keys: 'g d', action: 'Dashboard' },
  { keys: 'g o', action: 'Orders' },
  { keys: 'g c', action: 'Customers' },
  { keys: 'g p', action: 'Plans' },
  { keys: 'g a', action: 'Analytics' },
  { keys: 'g s', action: 'Settings' },
  { keys: 'g t', action: 'Team' },
  { keys: 'g b', action: 'Blog' },
  { keys: 'g e', action: 'Escalations' },
  { keys: 'g u', action: 'Support' },
  { keys: 'g r', action: 'Audit' },
  { keys: 'g v', action: 'Secrets' },
  { keys: 'g n', action: 'Permissions' },
  { keys: 'g l', action: 'RLS' },
  { keys: 'g f', action: 'Profile' },
  { keys: '?', action: 'Show keyboard shortcuts' },
];

export default function ShortcutHelpModal({ isOpen, onClose }: ShortcutHelpModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setMounted(true);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !mounted) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-md max-h-[85vh] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-2xl">
        <div className="sticky top-0 flex items-center justify-between p-4 border-b border-[var(--border)] bg-[var(--card)]">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">Keyboard Shortcuts</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="flex items-center justify-center w-10 h-10 rounded-lg text-[var(--muted)] hover:bg-[var(--card-hover)] transition-colors"
          >
            \u2715
          </button>
        </div>
        <div className="p-4 space-y-1">
          {shortcuts.map(({ keys, action }) => (
            <div
              key={keys}
              className="flex items-center justify-between py-2 px-2 rounded-lg hover:bg-[var(--card-hover)] transition-colors"
            >
              <span className="text-sm text-[var(--foreground)]">{action}</span>
              <kbd className="px-2.5 py-1 text-xs font-mono font-medium text-[var(--muted)] bg-[var(--card-hover)] border border-[var(--border)] rounded-md min-w-[44px] text-center">
                {keys}
              </kbd>
            </div>
          ))}
        </div>
        <div className="border-t border-[var(--border)] p-4">
          <p className="text-xs text-[var(--muted)] text-center">
            Press <kbd className="px-1.5 py-0.5 text-xs font-mono bg-[var(--card-hover)] border border-[var(--border)] rounded">Esc</kbd> to close
          </p>
        </div>
      </div>
    </div>
  );
}

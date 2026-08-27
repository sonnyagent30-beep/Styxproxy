'use client';

import Link from 'next/link';

interface Action {
  kind: string;
  label: string;
  href?: string;
  disabled?: boolean;
  reason?: string;
  confirm?: boolean;
  variant: 'primary' | 'secondary' | 'tertiary' | 'danger';
}

interface ActionBarProps {
  actions: Action[];
  onAction?: (action: Action) => void;
}

export default function ActionBar({ actions, onAction }: ActionBarProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3">
      {actions.map((action, i) => {
        const base = 'px-5 py-3 rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2';
        const variants = {
          primary: 'bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold',
          secondary: 'border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)]',
          tertiary: 'text-[var(--muted)] hover:text-[var(--foreground)]',
          danger: 'border border-[var(--error)]/30 text-[var(--error)] hover:bg-[var(--error)]/10',
        };

        if (action.href && !action.disabled) {
          return (
            <Link
              key={action.kind + i}
              href={action.href}
              className={`${base} ${variants[action.variant]}`}
              title={action.reason}
            >
              {action.label}
            </Link>
          );
        }

        return (
          <button
            key={action.kind + i}
            onClick={() => onAction?.(action)}
            disabled={action.disabled}
            className={`${base} ${variants[action.variant]} ${action.disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            title={action.reason}
          >
            {action.label}
          </button>
        );
      })}
    </div>
  );
}

'use client';

import { getStatusGroup, getStatusLabel, getStatusIcon } from '@/lib/order-status';

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const group = getStatusGroup(status);
  const label = getStatusLabel(status);

  const colors = {
    'in-progress': 'bg-[var(--warning)]/20 text-[var(--warning)] border-[var(--warning)]/30',
    success: 'bg-[var(--success)]/20 text-[var(--success)] border-[var(--success)]/30',
    'terminal-bad': 'bg-[var(--error)]/20 text-[var(--error)] border-[var(--error)]/30',
  };

  return (
    <span className={`text-xs font-mono px-2 py-1 rounded-md border ${colors[group]}`}>
      {label}
    </span>
  );
}

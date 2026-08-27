'use client';

import { getStatusGroup, getStatusLabel } from '@/lib/order-status';

interface StatusBannerProps {
  status: string;
  userMessage?: string;
}

export default function StatusBanner({ status, userMessage }: StatusBannerProps) {
  const group = getStatusGroup(status);
  const label = getStatusLabel(status);

  const colors = {
    'in-progress': 'bg-[var(--warning)]/10 border-[var(--warning)]/30',
    success: 'bg-[var(--success)]/10 border-[var(--success)]/30',
    'terminal-bad': 'bg-[var(--error)]/10 border-[var(--error)]/30',
  };

  const iconColors = {
    'in-progress': 'text-[var(--warning)]',
    success: 'text-[var(--success)]',
    'terminal-bad': 'text-[var(--error)]',
  };

  return (
    <div className={`rounded-2xl p-5 border ${colors[group]}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
            group === 'in-progress' ? 'bg-[var(--warning)]/20' :
            group === 'success' ? 'bg-[var(--success)]/20' : 'bg-[var(--error)]/20'
          }`}>
            {group === 'success' ? (
              <svg className={`w-5 h-5 ${iconColors[group]}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : group === 'in-progress' ? (
              <svg className={`w-5 h-5 ${iconColors[group]} animate-spin`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            ) : (
              <svg className={`w-5 h-5 ${iconColors[group]}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
          </div>
          <div>
            <p className={`font-semibold text-sm ${iconColors[group]}`}>{label}</p>
            {userMessage && <p className="text-xs text-[var(--muted)] mt-0.5">{userMessage}</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

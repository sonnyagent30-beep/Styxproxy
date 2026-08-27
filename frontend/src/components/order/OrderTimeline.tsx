'use client';

import { TimelineStep } from '@/lib/order-status';

interface OrderTimelineProps {
  steps: TimelineStep[];
}

export default function OrderTimeline({ steps }: OrderTimelineProps) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
      <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Order Timeline</h2>
      <div className="space-y-0">
        {steps.map((step, i) => (
          <div key={step.key} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full ${
                step.state === 'done'
                  ? 'bg-[var(--success)]'
                  : step.state === 'current'
                  ? 'bg-[var(--primary)] animate-pulse'
                  : 'bg-[var(--border)]'
              }`} />
              {i < steps.length - 1 && (
                <div className={`w-0.5 h-8 ${
                  step.state === 'done' ? 'bg-[var(--success)]' : 'bg-[var(--border)]'
                }`} />
              )}
            </div>
            <div className="pb-4">
              <p className={`text-sm font-medium ${
                step.state === 'pending' ? 'text-[var(--muted)]' : 'text-[var(--foreground)]'
              }`}>{step.label}</p>
              {step.date && (
                <p className="text-xs text-[var(--muted)]">
                  {new Date(step.date).toLocaleDateString('en-NG', { year: 'numeric', month: 'short', day: 'numeric' })}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

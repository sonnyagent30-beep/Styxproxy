'use client';

import { useState } from 'react';
import api from '@/lib/api';

interface AdminTotpStepUpModalProps {
  isOpen: boolean;
  onSuccess: () => void;
  onCancel: () => void;
  title?: string;
  description?: string;
}

/**
 * TOTP step-up modal — auto-prompts admins for their 6-digit TOTP code when
 * a sensitive action requires step-up auth. Refreshes the 5-min window on success.
 *
 * Usage:
 *   <AdminTotpStepUpModal
 *     isOpen={needsStepUp}
 *     onSuccess={() => doSensitiveAction()}
 *     onCancel={() => setNeedsStepUp(false)}
 *   />
 */
export default function AdminTotpStepUpModal({
  isOpen,
  onSuccess,
  onCancel,
  title = 'Confirm with TOTP',
  description = 'Enter your 6-digit authenticator code to authorize this action.',
}: AdminTotpStepUpModalProps) {
  const [code, setCode] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 6) {
      setError('Code must be 6 digits');
      return;
    }
    setLoading(true);
    setError('');

    const result = await api.elevateTotp(code, remember);
    setLoading(false);

    if (result.error) {
      setError(result.error);
      return;
    }
    onSuccess();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold">{title}</h2>
        <p className="text-sm text-[var(--muted)] mt-2">{description}</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              6-digit code
            </label>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              autoFocus
              placeholder="123456"
              className="w-full px-4 py-3 rounded-lg bg-[var(--background)] border border-[var(--border)] text-center text-2xl font-mono tracking-widest focus:border-[var(--primary)] focus:outline-none"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-[var(--muted)] cursor-pointer">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="rounded"
            />
            <span>Remember this device for 30 days</span>
          </label>

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="flex-1 px-4 py-2.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="flex-1 px-4 py-2.5 rounded-lg bg-[var(--primary)] text-black font-semibold hover:bg-[var(--primary-dark)] transition-colors disabled:opacity-50"
            >
              {loading ? 'Verifying…' : 'Confirm'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

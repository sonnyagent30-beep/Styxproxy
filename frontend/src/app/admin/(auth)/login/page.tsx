'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [needsTotp, setNeedsTotp] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const payload: { email: string; password: string; totp_code?: string } = { email, password };
      if (needsTotp && totpCode) payload.totp_code = totpCode;

      const result = await api.adminLogin(payload);

      if (result.error) {
        // If the backend says TOTP is required, advance to TOTP step
        if (!needsTotp && result.error.toLowerCase().includes('totp')) {
          setNeedsTotp(true);
          setError('');
        } else {
          setError(result.error);
        }
      } else if (result.data) {
        api.setAdminToken(result.data.access_token);
        router.push('/admin/dashboard');
      }
    } catch {
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo / Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Styxproxy <span className="gradient-text">Admin</span>
          </h1>
          <p className="text-[var(--muted)]">
            {needsTotp ? 'Enter your 2FA code' : 'Sign in to your account'}
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {!needsTotp ? (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2 text-[var(--muted)]">Email</label>
                  <input
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@styxproxy.com"
                    className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2 text-[var(--muted)]">Password</label>
                  <input
                    type="password"
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
                  />
                </div>
              </>
            ) : (
              <>
                <div className="text-sm text-[var(--muted)] mb-2">
                  Signed in as <span className="text-[var(--foreground)]">{email}</span>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2 text-[var(--muted)]">2FA Code</label>
                  <input
                    type="text"
                    required
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="123456"
                    className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20 text-center text-2xl tracking-widest"
                  />
                </div>
              </>
            )}

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Signing in...
                </>
              ) : needsTotp ? 'Verify & Continue' : 'Sign In'}
            </button>

            {needsTotp && (
              <button
                type="button"
                onClick={() => { setNeedsTotp(false); setTotpCode(''); setError(''); }}
                className="w-full text-sm text-[var(--muted)] hover:text-[var(--foreground)]"
              >
                ← Back
              </button>
            )}
          </form>
        </div>

        <div className="text-center text-xs text-[var(--muted)] mt-6">
          Secure admin access · Powered by Styxproxy
        </div>
      </div>
    </div>
  );
}

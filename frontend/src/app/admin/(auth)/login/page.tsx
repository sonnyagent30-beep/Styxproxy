'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

type Step = 'credentials' | 'totp';

export default function AdminLoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('credentials');
  const [stepToken, setStepToken] = useState('');
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Check if already logged in
    const token = api.getAdminToken();
    if (token) {
      router.push('/admin/dashboard');
    }
  }, [router]);

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const normalizedPhone = phone.replace(/\D/g, '').startsWith('0')
      ? '+234' + phone.replace(/\D/g, '')
      : phone.replace(/\D/g, '');

    try {
      const result = await api.adminLoginStep1({
        admin_phone: normalizedPhone,
        pin,
      });

      if (result.error) {
        setError(result.error);
      } else if (result.data) {
        if (!result.data.totp_required) {
          // No TOTP — directly request a token via step2 with empty? No, this shouldn't happen
          // for any existing admin. If TOTP is disabled, the user can still log in but we need
          // to issue a real token. For now, treat as error.
          setError('TOTP is disabled for this account. Please contact administrator.');
          return;
        }
        setStepToken(result.data.step_token);
        setStep('totp');
      }
    } catch (err) {
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleTotpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await api.adminLoginStep2({
        step_token: stepToken,
        totp_code: totpCode,
      });

      if (result.error) {
        setError(result.error);
        // If step token expired, go back to credentials
        if (result.error.toLowerCase().includes('expired') || result.error.toLowerCase().includes('invalid')) {
          setStep('credentials');
          setStepToken('');
          setTotpCode('');
          setPin('');
        }
      } else if (result.data) {
        api.setAdminToken(result.data.access_token);
        router.push('/admin/dashboard');
      }
    } catch (err) {
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
          <p className="text-[var(--muted)]">Sign in to your account</p>
        </div>

        {/* Login Form */}
        <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          {step === 'credentials' && (
            <form onSubmit={handleCredentialsSubmit} className="space-y-6">
              {error && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-2">Phone Number</label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+234 703 298 1049"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">PIN</label>
                <input
                  type="password"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  placeholder="Enter your PIN"
                  maxLength={6}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Verifying...' : 'Continue'}
              </button>
            </form>
          )}

          {step === 'totp' && (
            <form onSubmit={handleTotpSubmit} className="space-y-6">
              {error && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div className="text-center space-y-2">
                <div className="text-4xl">🔐</div>
                <p className="text-sm font-medium">Two-Factor Authentication</p>
                <p className="text-xs text-[var(--muted)]">
                  Enter the 6-digit code from Google Authenticator
                </p>
              </div>

              <div>
                <input
                  type="text"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000 000"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  autoComplete="one-time-code"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors text-center text-2xl tracking-[0.5em] font-mono"
                  required
                  autoFocus
                />
              </div>

              <button
                type="submit"
                disabled={loading || totpCode.length !== 6}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep('credentials');
                  setStepToken('');
                  setTotpCode('');
                  setError('');
                }}
                className="w-full py-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
              >
                ← Back
              </button>
            </form>
          )}
        </div>

        {/* Back to site */}
        <div className="mt-6 text-center">
          <a href="/" className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors">
            ← Back to Styxproxy
          </a>
        </div>
      </div>
    </div>
  );
}

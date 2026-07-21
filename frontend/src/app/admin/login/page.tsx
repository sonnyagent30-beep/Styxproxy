'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

type Step = 'credentials' | 'totp';

export default function AdminLoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('credentials');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [verifying, setVerifying] = useState(false);

  // Step indicator dots
  const steps: { key: Step; label: string }[] = [
    { key: 'credentials', label: 'Account' },
    { key: 'totp', label: '2FA' },
  ];
  const currentIndex = steps.findIndex(s => s.key === step);

  useEffect(() => {
    const token = api.getAdminToken();
    if (token) {
      router.push('/admin/dashboard');
    }
  }, [router]);

  // Step 1: submit email + password
  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await api.adminLogin({ email, password });

      if (result.error) {
        const err = result.error.toLowerCase();
        if (err.includes('totp') || err.includes('2fa') || err.includes('code required')) {
          // Move to step 2
          setStep('totp');
        } else {
          setError(result.error);
        }
      }
    } catch {
      setError('Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: submit TOTP
  const handleTotpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totpCode.length !== 6) {
      setError('Enter your 6-digit code');
      return;
    }
    setError('');
    setVerifying(true);

    try {
      const result = await api.adminLogin({ email, password, totp_code: totpCode });

      if (result.error) {
        setError(result.error);
        // If still TOTP error, maybe code expired — stay on step 2
      } else if (result.data) {
        api.setAdminToken(result.data.access_token);
        // Use hard navigation to ensure clean state after login
        window.location.href = '/admin/dashboard';
      }
    } catch {
      setError('Connection error. Please try again.');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Styxproxy <span className="gradient-text">Admin</span>
          </h1>
          <p className="text-[var(--muted)]">
            {step === 'credentials' ? 'Sign in to your account' : 'Enter your verification code'}
          </p>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-3 mb-8">
          {steps.map((s, i) => (
            <div key={s.key} className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all
                ${i <= currentIndex
                  ? 'bg-[var(--primary)] text-black'
                  : 'bg-[var(--card-hover)] text-[var(--muted)]'}`}>
                <span className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-xs">
                  {i + 1}
                </span>
                {s.label}
              </div>
              {i < steps.length - 1 && (
                <div className={`w-8 h-px ${i < currentIndex ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'}`} />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Step 1: Email + Password */}
          {step === 'credentials' && (
            <form onSubmit={handleCredentialsSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@example.com"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Verifying...' : 'Continue'}
              </button>
            </form>
          )}

          {/* Step 2: TOTP only */}
          {step === 'totp' && (
            <form onSubmit={handleTotpSubmit} className="space-y-5">
              <div className="text-center mb-4">
                <p className="text-sm text-[var(--muted)]">
                  Welcome back, <span className="text-[var(--foreground)] font-medium">{email}</span>
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Verification Code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="6-digit code"
                  maxLength={6}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors text-center text-2xl tracking-widest font-mono"
                  required
                  autoFocus
                />
                <p className="text-xs text-[var(--muted)] mt-2 text-center">
                  Open your authenticator app and enter the code
                </p>
              </div>

              <button
                type="submit"
                disabled={verifying || totpCode.length !== 6}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {verifying ? 'Signing in...' : 'Sign In'}
              </button>

              <button
                type="button"
                onClick={() => { setStep('credentials'); setTotpCode(''); setError(''); }}
                className="w-full py-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
              >
                ← Back to account sign in
              </button>
            </form>
          )}
        </div>

        {/* Setup link */}
        <div className="mt-6 text-center">
          <a href="/admin/setup" className="text-sm text-[var(--muted)] hover:text-[var(--primary)] transition-colors">
            Need to set up your account?
          </a>
        </div>

        <div className="mt-4 text-center">
          <a href="/" className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors">
            ← Back to Styxproxy
          </a>
        </div>

      </div>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function AdminSetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<'credentials' | 'totp'>('credentials');
  const [inviteCode, setInviteCode] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // TOTP step data from step 1 response
  const [tempToken, setTempToken] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [otpauthUrl, setOtpauthUrl] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);

  useEffect(() => {
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    const result = await api.checkAdminSetupStatus();
    if (result.data?.setup_required === false) {
      router.push('/admin/login');
    }
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      setLoading(false);
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }
    if (!email.includes('@')) {
      setError('Please enter a valid email address');
      setLoading(false);
      return;
    }

    try {
      const result = await api.setupAdmin({
        invite_code: inviteCode,
        email,
        password,
      });

      if (result.error) {
        setError(typeof result.error === 'string' ? result.error : (result.error as any)?.detail || 'Setup failed');
        setLoading(false);
        return;
      }

      const data = result.data as any;
      // Save TOTP setup data and move to TOTP step
      setTempToken(data.temp_token || '');
      setTotpSecret(data.totp_secret || '');
      setOtpauthUrl(data.otpauth_url || '');
      setBackupCodes(data.backup_codes || []);
      setStep('totp');
    } catch {
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleTotpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await api.setupAdminComplete({
        temp_token: tempToken,
        totp_code: totpCode,
      });

      if (result.error) {
        setError(typeof result.error === 'string' ? result.error : (result.error as any)?.detail || 'Verification failed');
        setLoading(false);
        return;
      }

      // Setup complete — redirect to login
      router.push('/admin/login?setup=complete');
    } catch {
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
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
            {step === 'credentials' ? 'Create your admin account' : 'Set up 2FA authenticator'}
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className={`w-3 h-3 rounded-full transition-colors ${step === 'credentials' ? 'bg-[var(--primary)]' : 'bg-[var(--primary)]/30'}`} />
          <div className={`w-3 h-3 rounded-full transition-colors ${step === 'totp' ? 'bg-[var(--primary)]' : 'bg-[var(--primary)]/30'}`} />
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* ── Step 1: Credentials ── */}
        {step === 'credentials' && (
          <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
            <form onSubmit={handleCredentialsSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2">Invite Code</label>
                <input
                  type="text"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  placeholder="Paste your invite code"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  minLength={8}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Confirm Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                  minLength={8}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Generating 2FA setup...' : 'Continue'}
              </button>
            </form>
          </div>
        )}

        {/* ── Step 2: TOTP Setup ── */}
        {step === 'totp' && (
          <div className="space-y-6">
            {/* QR Code + Secret */}
            <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <p className="text-sm text-[var(--muted)] mb-6 text-center">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
              </p>

              {/* QR Code Image */}
              {otpauthUrl && (
                <div className="flex justify-center mb-6">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(otpauthUrl)}`}
                    alt="TOTP QR Code"
                    className="w-48 h-48 rounded-xl border border-[var(--border)]"
                  />
                </div>
              )}

              {/* Manual Secret */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2 text-center">
                  Or enter this code manually in your app
                </label>
                <div className="p-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] text-center">
                  <code className="text-sm font-mono break-all text-[var(--foreground)]">
                    {totpSecret}
                  </code>
                </div>
              </div>
            </div>

            {/* Backup Codes */}
            <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🔑</span>
                <h3 className="font-semibold">Backup Codes</h3>
              </div>
              <p className="text-xs text-[var(--muted)] mb-3">
                Save these — each code works once if you lose your device
              </p>
              <div className="grid grid-cols-2 gap-2">
                {backupCodes.map((code, i) => (
                  <div key={i} className="px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] text-center">
                    <code className="text-xs font-mono">{code}</code>
                  </div>
                ))}
              </div>
            </div>

            {/* Verify TOTP Code */}
            <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <form onSubmit={handleTotpSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Enter the 6-digit code from your authenticator app
                  </label>
                  <input
                    type="text"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxLength={6}
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors text-center text-2xl tracking-widest font-mono"
                    required
                    autoFocus
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || totpCode.length !== 6}
                  className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {loading ? 'Verifying...' : 'Verify & Complete Setup'}
                </button>

                <button
                  type="button"
                  onClick={() => setStep('credentials')}
                  className="w-full py-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
                >
                  ← Back
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 text-center">
          <a href="/" className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors">
            ← Back to Styxproxy
          </a>
        </div>
      </div>
    </div>
  );
}

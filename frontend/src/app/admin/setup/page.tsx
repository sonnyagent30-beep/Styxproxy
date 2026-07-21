'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function AdminSetupPage() {
  const router = useRouter();

  // 3 steps: invite → credentials → totp
  const [step, setStep] = useState<'invite' | 'credentials' | 'totp'>('invite');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 1 data
  const [inviteCode, setInviteCode] = useState('');
  const [inviteValid, setInviteValid] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');

  // Step 2 data
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Step 3 data
  const [totpCode, setTotpCode] = useState('');
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

  // ── Step 1: Validate invite code ─────────────────────────────────────────
  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (inviteCode.trim().length < 8) {
      setError('Invite code must be at least 8 characters');
      setLoading(false);
      return;
    }

    const result = await api.checkInviteCode(inviteCode.trim());
    const data = result.data as any;

    if (!data?.valid) {
      setError('Invalid, expired, or already-used invite code');
      setLoading(false);
      return;
    }

    setInviteValid(true);
    setInviteEmail(data.email || '');
    if (data.email) setEmail(data.email);
    setStep('credentials');
    setLoading(false);
  };

  // ── Step 2: Submit credentials ───────────────────────────────────────────
  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!email.includes('@')) {
      setError('Please enter a valid email address');
      setLoading(false);
      return;
    }
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

    try {
      const result = await api.setupAdmin({
        invite_code: inviteCode,
        email,
        password,
      });

      if (result.error) {
        const msg = typeof result.error === 'string'
          ? result.error
          : (result.error as any)?.detail || 'Setup failed';
        setError(msg);
        setLoading(false);
        return;
      }

      const data = result.data as any;
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

  // ── Step 3: Verify TOTP ─────────────────────────────────────────────────
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
        const msg = typeof result.error === 'string'
          ? result.error
          : (result.error as any)?.detail || 'Verification failed';
        setError(msg);
        setLoading(false);
        return;
      }

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
            {step === 'invite' && 'Enter your invite code to begin'}
            {step === 'credentials' && 'Create your admin account'}
            {step === 'totp' && 'Set up 2FA authenticator'}
          </p>
        </div>

        {/* Step dots */}
        <div className="flex items-center justify-center gap-3 mb-8">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className={`w-2.5 h-2.5 rounded-full transition-colors ${
                (i === 0 && step === 'invite') ||
                (i === 1 && step === 'credentials') ||
                (i === 2 && step === 'totp')
                  ? 'bg-[var(--primary)]'
                  : 'bg-[var(--border)]'
              }`}
            />
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* ── Step 1: Invite Code ── */}
        {step === 'invite' && (
          <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
            <form onSubmit={handleInviteSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2">Invite Code</label>
                <input
                  type="text"
                  value={inviteCode}
                  onChange={(e) => {
                    setInviteCode(e.target.value);
                    setError('');
                  }}
                  placeholder="Paste your invite code"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                  autoFocus
                />
                <p className="text-xs text-[var(--muted)] mt-2">
                  Get this from your SuperAdmin
                </p>
              </div>

              <button
                type="submit"
                disabled={loading || inviteCode.trim().length < 8}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Checking...' : 'Continue'}
              </button>
            </form>
          </div>
        )}

        {/* ── Step 2: Credentials ── */}
        {step === 'credentials' && (
          <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
            <div className="mb-5 p-3 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
              Invite code verified ✓
            </div>

            <form onSubmit={handleCredentialsSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError('');
                  }}
                  placeholder="admin@example.com"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
                {inviteEmail && email !== inviteEmail && (
                  <p className="text-xs text-[var(--muted)] mt-1">
                    Hint: this invite was created for {inviteEmail}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setError('');
                  }}
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
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    setError('');
                  }}
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
                {loading ? 'Setting up 2FA...' : 'Continue to 2FA Setup'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep('invite');
                  setError('');
                }}
                className="w-full py-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
              >
                ← Back
              </button>
            </form>
          </div>
        )}

        {/* ── Step 3: TOTP Setup ── */}
        {step === 'totp' && (
          <div className="space-y-5">
            {/* QR + Manual Secret */}
            <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <p className="text-sm text-[var(--muted)] mb-5 text-center">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, 1Password, etc.)
              </p>

              {otpauthUrl && (
                <div className="flex justify-center mb-5">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(otpauthUrl)}`}
                    alt="TOTP QR Code"
                    width={200}
                    height={200}
                    className="rounded-xl border border-[var(--border)]"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-2 text-center">
                  Or enter this key manually in your app
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
                Save these — each works once if you lose your device
              </p>
              <div className="grid grid-cols-2 gap-2">
                {backupCodes.map((code, i) => (
                  <div
                    key={i}
                    className="px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] text-center"
                  >
                    <code className="text-xs font-mono">{code}</code>
                  </div>
                ))}
              </div>
            </div>

            {/* Verify Code */}
            <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <form onSubmit={handleTotpSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium mb-2 text-center">
                    Enter the 6-digit code from your authenticator app
                  </label>
                  <input
                    type="text"
                    value={totpCode}
                    onChange={(e) => {
                      setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6));
                      setError('');
                    }}
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
                  onClick={() => {
                    setStep('credentials');
                    setError('');
                  }}
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
          <a
            href="/"
            className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
          >
            ← Back to Styxproxy
          </a>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

type Step = 'invite' | 'credentials' | 'totp';

export default function AdminSetupPage() {
  const router = useRouter();

  // Step 1: invite code (only). Server validates it before we advance.
  const [step, setStep] = useState<Step>('invite');
  const [inviteCode, setInviteCode] = useState('');
  const [inviteValid, setInviteValid] = useState(false);
  const [inviteEmail, setInviteEmail] = useState(''); // server-stored email (revealed after invite validated)

  // Step 2: user types email (must match invite). Never pre-filled.
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Step 3: TOTP code; backend returns temp_token for /setup/complete.
  const [totpCode, setTotpCode] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [otpauthUrl, setOtpauthUrl] = useState('');
  const [tempToken, setTempToken] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [qrSvg, setQrSvg] = useState<string>('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Step 1: only the invite code is shown on this page.
  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const result = await api.adminSetupCheckInvite({ invite_code: inviteCode });
    setLoading(false);
    if (result.error) {
      setError(result.error);
      return;
    }
    if (!result.data?.valid) {
      setError('Invite code is invalid, expired, or already used.');
      return;
    }
    setInviteValid(true);
    setInviteEmail((result.data.email || '').toLowerCase());
    // DO NOT pre-fill the email field — the user must type it themselves.
    // The server enforces that what they type matches the invite-scoped email.
    setStep('credentials');
  };

  // Step 2: email must match the invite's stored email; then password.
  const handleCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (inviteEmail && email.toLowerCase() !== inviteEmail) {
      setError(
        `This invite was sent to ${inviteEmail || 'a specific address'}. Use that email — or request a new invite for this one.`,
      );
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    const result = await api.adminSetupStep1({
      invite_code: inviteCode,
      email: email.toLowerCase(),
      password,
    });
    setLoading(false);
    if (result.error) {
      setError(result.error);
      return;
    }
    if (!result.data) {
      setError('Setup failed. Please try again.');
      return;
    }
    setTotpSecret(result.data.totp_secret);
    setOtpauthUrl(result.data.otpauth_url);
    setTempToken(result.data.temp_token);
    setBackupCodes(result.data.backup_codes || []);
    setStep('totp');

    // Render a QR code SVG from the otpauth URL so the user can scan it.
    try {
      const QR = (await import('qrcode')).default;
      const svg = await QR.toString(result.data.otpauth_url, {
        type: 'svg',
        margin: 1,
        color: { dark: '#000', light: '#fff' },
        errorCorrectionLevel: 'M',
      });
      setQrSvg(svg);
    } catch {
      setQrSvg('');
    }
  };

  const handleTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const result = await api.adminSetupStep2({
      temp_token: tempToken,
      totp_code: totpCode,
    });
    setLoading(false);
    if (result.error) {
      setError(result.error);
      return;
    }
    if (result.data) {
      api.setAdminToken(result.data.access_token);
      // Per user requirement: redirect to the login page (not dashboard).
      router.push('/admin/login');
    }
  };

  // ─────────── UI ───────────
  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Styxproxy <span className="gradient-text">Setup</span>
          </h1>
          <p className="text-[var(--muted)]">
            {step === 'invite' && 'Step 1 of 3 — enter your invite code'}
            {step === 'credentials' && 'Step 2 of 3 — set your email and password'}
            {step === 'totp' && 'Step 3 of 3 — enable two-factor authentication'}
          </p>
        </div>

        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6">
          {step === 'invite' && (
            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">
                  Invite Code
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  placeholder="Enter invite code"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
                />
                <p className="text-xs text-[var(--muted)] mt-2">
                  This code was emailed to the future admin. We never show the
                  email field until we've verified it.
                </p>
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !inviteCode}
                className="w-full px-4 py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Validating…' : 'Continue'}
              </button>
            </form>
          )}

          {step === 'credentials' && (
            <form onSubmit={handleCredentials} className="space-y-4">
              {inviteValid && inviteEmail && (
                <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs">
                  Invite valid for <strong>{inviteEmail}</strong>. Use this email
                  below.
                </div>
              )}
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">
                  Password
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">
                  Confirm Password
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
                />
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !email || !password || !confirmPassword}
                className="w-full px-4 py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Generating 2FA…' : 'Continue'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep('invite');
                  setError('');
                }}
                className="w-full text-sm text-[var(--muted)] hover:text-[var(--foreground)]"
              >
                ← Back
              </button>
            </form>
          )}

          {step === 'totp' && (
            <form onSubmit={handleTotp} className="space-y-4">
              <div className="text-center">
                <p className="text-sm text-[var(--muted)] mb-3">
                  Scan this QR code with Google Authenticator, 1Password,
                  Authy, or any TOTP app. Then enter the 6-digit code below.
                </p>
                {qrSvg ? (
                  <div
                    className="mx-auto inline-block p-3 bg-white rounded-xl border border-[var(--border)]"
                    // The SVG is generated client-side from the otpauth URL.
                    // We render it via dangerouslySetInnerHTML so the user can
                    // tap-and-hold to save it. The src string is fixed format
                    // produced by the 'qrcode' npm package; no user input is
                    // interpolated, so this is safe.
                    dangerouslySetInnerHTML={{ __html: qrSvg }}
                  />
                ) : (
                  <div className="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-xs font-mono break-all text-[var(--muted)]">
                    {otpauthUrl}
                  </div>
                )}
                <details className="mt-3 text-left">
                  <summary className="text-xs text-[var(--muted)] cursor-pointer">
                    Or enter secret manually
                  </summary>
                  <div className="mt-2 p-2 rounded bg-[var(--background)] border border-[var(--border)] text-xs font-mono break-all">
                    {totpSecret}
                  </div>
                </details>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">
                  6-digit Code
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  inputMode="numeric"
                  maxLength={6}
                  autoComplete="one-time-code"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20 text-center text-2xl tracking-widest"
                />
              </div>

              {backupCodes.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs">
                  <p className="font-medium mb-1">Save these backup codes:</p>
                  <div className="grid grid-cols-2 gap-1 font-mono text-[10px]">
                    {backupCodes.map((c, i) => (
                      <div key={i}>{c}</div>
                    ))}
                  </div>
                </div>
              )}

              {error && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || totpCode.length !== 6}
                className="w-full px-4 py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Verifying…' : 'Complete Setup'}
              </button>
              <p className="text-xs text-center text-[var(--muted)]">
                You'll be redirected to the login page after setup.
              </p>
            </form>
          )}
        </div>

        <div className="text-center text-xs text-[var(--muted)] mt-6">
          Already have an account?{' '}
          <a href="/admin/login" className="text-[var(--primary)] hover:underline">
            Sign in
          </a>
        </div>
      </div>
    </div>
  );
}

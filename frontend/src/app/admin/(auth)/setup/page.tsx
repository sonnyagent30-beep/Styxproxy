'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function AdminSetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<'invite' | 'credentials' | 'totp'>('invite');
  const [inviteCode, setInviteCode] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [otpauthUrl, setOtpauthUrl] = useState('');
  const [tempToken, setTempToken] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const result = await api.adminSetupStep1({
      invite_code: inviteCode,
      email,
      password,
    });
    setLoading(false);
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setTotpSecret(result.data.totp_secret);
      setOtpauthUrl(result.data.otpauth_url);
      setTempToken(result.data.temp_token);
      setBackupCodes(result.data.backup_codes || []);
      setStep('totp');
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
    } else if (result.data) {
      api.setAdminToken(result.data.access_token);
      router.push('/admin/dashboard');
    }
  };

  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Styxproxy <span className="gradient-text">Setup</span>
          </h1>
          <p className="text-[var(--muted)]">Create the first admin account</p>
        </div>

        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6">
          {step === 'invite' && (
            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">Invite Code</label>
                <input
                  type="text"
                  required
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  placeholder="Enter invite code"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">Email</label>
                <input
                  type="email"
                  required
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
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">Confirm Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
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
                disabled={loading || password !== confirmPassword}
                className="w-full px-4 py-3 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Validating...' : 'Continue'}
              </button>
            </form>
          )}

          {step === 'totp' && (
            <form onSubmit={handleTotp} className="space-y-4">
              <div>
                <p className="text-sm text-[var(--muted)] mb-3">
                  Scan this URL in your authenticator app, then enter the 6-digit code:
                </p>
                <div className="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-xs font-mono break-all text-[var(--muted)]">
                  {otpauthUrl}
                </div>
                <details className="mt-2">
                  <summary className="text-xs text-[var(--muted)] cursor-pointer">Or enter secret manually</summary>
                  <div className="mt-2 p-2 rounded bg-[var(--background)] border border-[var(--border)] text-xs font-mono break-all">
                    {totpSecret}
                  </div>
                </details>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--muted)]">6-digit Code</label>
                <input
                  type="text"
                  required
                  inputMode="numeric"
                  maxLength={6}
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
                    {backupCodes.map((c, i) => <div key={i}>{c}</div>)}
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
                {loading ? 'Verifying...' : 'Complete Setup'}
              </button>
            </form>
          )}
        </div>

        <div className="text-center text-xs text-[var(--muted)] mt-6">
          Already have an account?{' '}
          <a href="/admin/login" className="text-[var(--primary)] hover:underline">Sign in</a>
        </div>
      </div>
    </div>
  );
}

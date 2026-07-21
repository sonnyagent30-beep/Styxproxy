'use client';

import { useState, useEffect } from 'react';
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    // Check if already has admin
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    const result = await api.checkAdminSetupStatus();
    if (result.data?.setup_required === false) {
      // Admin already exists, redirect to login
      router.push('/admin/login');
    }
  };

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Basic validation
    if (inviteCode.length < 8) {
      setError('Invite code must be at least 8 characters');
      setLoading(false);
      return;
    }

    // Store invite code temporarily and move to next step
    setStep('credentials');
    setLoading(false);
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate email
    if (!email || !email.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }

    // Validate password
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Move to TOTP step
    setStep('totp');
  };

  const handleFinalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await api.setupAdmin({
        invite_code: inviteCode,
        email,
        password,
        totp_code: totpCode || undefined,
      });

      if (result.error) {
        setError(result.error);
      } else if (result.data) {
        setSuccess('Account setup complete! Redirecting to login...');
        setTimeout(() => {
          router.push('/admin/login');
        }, 2000);
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
          <p className="text-[var(--muted)]">Set up your admin account</p>
        </div>

        {/* Steps indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className={`w-3 h-3 rounded-full ${step === 'invite' ? 'bg-[var(--primary)]' : 'bg-[var(--primary)]/30'}`} />
          <div className={`w-3 h-3 rounded-full ${step === 'credentials' ? 'bg-[var(--primary)]' : 'bg-[var(--primary)]/30'}`} />
          <div className={`w-3 h-3 rounded-full ${step === 'totp' ? 'bg-[var(--primary)]' : 'bg-[var(--primary)]/30'}`} />
        </div>

        {/* Form Card */}
        <div className="p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
              {success}
            </div>
          )}

          {step === 'invite' && (
            <form onSubmit={handleInviteSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">Invite Code</label>
                <input
                  type="text"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  placeholder="Enter your invite code"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
                <p className="text-xs text-[var(--muted)] mt-2">
                  Get this code from your SuperAdmin
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Checking...' : 'Continue'}
              </button>
            </form>
          )}

          {step === 'credentials' && (
            <form onSubmit={handleCredentialsSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@example.com"
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
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity"
              >
                Continue
              </button>

              <button
                type="button"
                onClick={() => setStep('invite')}
                className="w-full py-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
              >
                ← Back
              </button>
            </form>
          )}

          {step === 'totp' && (
            <form onSubmit={handleFinalSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">
                  TOTP Code <span className="text-[var(--muted)]">(optional)</span>
                </label>
                <input
                  type="text"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="6-digit code (skip if not using 2FA)"
                  maxLength={6}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                />
                <p className="text-xs text-[var(--muted)] mt-2">
                  If you want to enable 2FA, enter the code from your authenticator app. 
                  You can skip this and enable it later.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Setting up...' : 'Complete Setup'}
              </button>

              <button
                type="button"
                onClick={() => setStep('credentials')}
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

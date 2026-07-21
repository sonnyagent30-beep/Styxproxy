'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function AdminSetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<'phone' | 'invite' | 'pin' | 'totp'>('phone');
  const [adminPhone, setAdminPhone] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [statusLoaded, setStatusLoaded] = useState(false);

  useEffect(() => {
    // Check if already has admin
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    try {
      // Timeout after 5s — if backend unreachable, assume setup is needed
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);

      const res = await fetch(
        `/api-proxy/api/admin/auth/status`,
        { signal: controller.signal }
      );
      clearTimeout(timeout);

      if (res.ok) {
        const data = await res.json();
        if (data.setup_required === false) {
          router.push('/admin/login');
          return;
        }
      }
      // Backend unreachable or not set up — show setup form (default)
    } catch {
      // Backend offline or unreachable — show setup form as-is
    } finally {
      setStatusLoaded(true);
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
    setStep('pin');
    setLoading(false);
  };

  const handlePinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate PIN
    if (pin.length < 4 || pin.length > 6) {
      setError('PIN must be 4-6 digits');
      return;
    }

    if (pin !== confirmPin) {
      setError('PINs do not match');
      return;
    }

    // Fetch TOTP provisioning info BEFORE moving to TOTP step
    setLoading(true);
    try {
      const result = await api.getTotpProvision();
      if (result.data) {
        setTotpSecret(result.data.secret || '');
        setQrCodeUrl(result.data.qr_code_url || '');
      } else if (result.error) {
        setError(`Failed to load authenticator setup: ${result.error}. Please try again.`);
        setLoading(false);
        return;
      }
    } catch (err) {
      console.error('Failed to fetch TOTP provision:', err);
      setError('Cannot connect to server. Please check your connection.');
      setLoading(false);
      return;
    }
    setLoading(false);

    // Now move to TOTP step — QR code data is ready
    setStep('totp');
  };

  const handleFinalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Validate TOTP code - must be 6 digits
    if (!totpCode || totpCode.length !== 6) {
      setError('TOTP code is required - enter the 6-digit code from your authenticator app');
      setLoading(false);
      return;
    }

    try {
      const result = await api.setupAdmin({
        admin_phone: adminPhone.replace(/\D/g, '').startsWith('0')
          ? '+234' + adminPhone.replace(/\D/g, '')
          : adminPhone.replace(/\D/g, ''),
        invite_code: inviteCode,
        pin,
        totp_code: totpCode,
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
          <div className={`w-3 h-3 rounded-full ${step === 'phone' ? 'bg-[var(--primary)]' : 'bg-[var(--primary)]/30'}`} />
          <div className={`w-3 h-3 rounded-full ${step === 'invite' ? 'bg-[var(--primary)]' : 'bg-[var(--primary)]/30'}`} />
          <div className={`w-3 h-3 rounded-full ${step === 'pin' ? 'bg-[var(--primary)]' : 'bg-[var(--primary)]/30'}`} />
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

          {step === 'phone' && (
            <form onSubmit={(e) => { e.preventDefault(); if (adminPhone.replace(/\D/g,'').length >= 10) setStep('invite'); }} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">Phone Number</label>
                <input
                  type="tel"
                  value={adminPhone}
                  onChange={(e) => setAdminPhone(e.target.value)}
                  placeholder="+234 703 298 1049"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
                <p className="text-xs text-[var(--muted)] mt-2">
                  Your admin login phone number — Nigerian format preferred
                </p>
              </div>

              <button
                type="submit"
                disabled={adminPhone.replace(/\D/g,'').length < 10}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                Continue
              </button>
            </form>
          )}

          {step === 'invite' && (
            <form onSubmit={handleInviteSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">Invite Code</label>
                <input
                  type="text"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  placeholder={adminPhone ? "Enter your invite code" : "Bootstrap token"}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
                <p className="text-xs text-[var(--muted)] mt-2">
                  First-time setup: use the ADMIN_TOKEN bootstrap code from your server env
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? 'Checking...' : 'Continue'}
              </button>

              <button
                type="button"
                onClick={() => setStep('phone')}
                className="w-full py-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
              >
                ← Back
              </button>
            </form>
          )}

          {step === 'pin' && (
            <form onSubmit={handlePinSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">Create PIN</label>
                <input
                  type="password"
                  value={pin}
                  onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="4-6 digit PIN"
                  maxLength={6}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Confirm PIN</label>
                <input
                  type="password"
                  value={confirmPin}
                  onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="Re-enter PIN"
                  maxLength={6}
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
              {/* TOTP Setup - shown before the code entry field */}
              <div className="text-center space-y-4">
                <p className="text-sm font-medium">Set up your Authenticator App</p>

                {/* QR Code - if loaded */}
                {qrCodeUrl ? (
                  <div className="space-y-2">
                    <img 
                      src={qrCodeUrl} 
                      alt="QR code for authenticator app" 
                      className="mx-auto w-48 h-48 border border-[var(--border)] rounded-xl"
                    />
                    <p className="text-xs text-[var(--muted)]">Scan with Google Authenticator app</p>
                  </div>
                ) : (
                  <div className="w-48 h-48 mx-auto border-2 border-dashed border-[var(--border)] rounded-xl flex items-center justify-center">
                    <p className="text-xs text-[var(--muted)]">Loading QR code...</p>
                  </div>
                )}

                {/* Secret key - always shown, prominent */}
                <div className="bg-[var(--card-hover)] border border-[var(--border)] rounded-xl p-4 space-y-2">
                  <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wide">Manual Entry Key</p>
                  <p className="text-sm font-mono text-[var(--foreground)]">
                    {totpSecret ? totpSecret.match(/.{1,4}/g)?.join(' ') || totpSecret : 'Not available'}
                  </p>
                  <p className="text-xs text-[var(--muted)]">
                    On your phone: Open Google Authenticator → tap <strong>+</strong> → tap <strong>"Enter a provided key"</strong> → paste the key above
                  </p>
                </div>
              </div>

              <hr className="border-[var(--border)]" />

              {/* 6-digit code entry */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  6-Digit Code from Authenticator <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000 000"
                  maxLength={6}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors text-center text-2xl tracking-[0.5em] font-mono"
                  required
                  autoFocus
                />
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
                onClick={() => setStep('pin')}
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

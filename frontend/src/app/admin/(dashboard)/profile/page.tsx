'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { AdminMeResponse, AdminRole } from '@/types';

export default function AdminProfilePage() {
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // PIN change state
  const [showPinModal, setShowPinModal] = useState(false);
  const [currentPin, setCurrentPin] = useState('');
  const [newPin, setNewPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [pinLoading, setPinLoading] = useState(false);
  const [pinMessage, setPinMessage] = useState('');

  // TOTP state
  const [showTotpModal, setShowTotpModal] = useState(false);
  const [totpCode, setTotpCode] = useState('');
  const [totpLoading, setTotpLoading] = useState(false);
  const [totpMessage, setTotpMessage] = useState('');
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [totpSecret, setTotpSecret] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    const result = await api.getAdminMe();
    
    if (result.error) {
      setError(result.error);
    } else {
      setAdmin(result.data || null);
    }
    
    setLoading(false);
  };

  const handlePinChange = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (newPin !== confirmPin) {
      setPinMessage('PINs do not match');
      return;
    }
    
    if (newPin.length < 4 || newPin.length > 6) {
      setPinMessage('PIN must be 4-6 digits');
      return;
    }

    setPinLoading(true);
    setPinMessage('');

    const result = await api.changeAdminPin(currentPin, newPin);
    
    if (result.error) {
      setPinMessage(result.error);
    } else {
      setPinMessage('PIN changed successfully!');
      setCurrentPin('');
      setNewPin('');
      setConfirmPin('');
      setShowPinModal(false);
    }

    setPinLoading(false);
  };

  const handleTotpSetup = async () => {
    // First, get the provisioning info
    const provisionResult = await api.getTotpProvision();
    
    if (provisionResult.error) {
      setTotpMessage(provisionResult.error);
      return;
    }

    setQrCodeUrl(provisionResult.data?.qr_code_url || '');
    setTotpSecret(provisionResult.data?.secret || '');
    setShowTotpModal(true);
  };

  const handleTotpEnable = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpLoading(true);
    setTotpMessage('');

    const result = await api.toggleAdminTOTP('enable', totpCode);

    if (result.error) {
      setTotpMessage(result.error);
    } else {
      setTotpMessage('2FA enabled successfully!');
      setTotpCode('');
      setShowTotpModal(false);
      loadProfile();
    }

    setTotpLoading(false);
  };

  const handleTotpDisable = async () => {
    const code = prompt('Enter your 2FA code to disable:');
    if (!code) return;

    setTotpLoading(true);
    const result = await api.toggleAdminTOTP('disable', code);

    if (result.error) {
      alert(result.error);
    } else {
      alert('2FA disabled successfully');
      loadProfile();
    }

    setTotpLoading(false);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getRoleBadge = (role?: string) => {
    const styles: Record<string, string> = {
      superadmin: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      admin: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      viewer: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    };
    return styles[role || ''] || styles.viewer;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  if (error || !admin) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="p-8 rounded-2xl bg-[var(--card)] border border-red-500/30 text-center">
          <h2 className="text-xl font-bold text-red-400 mb-2">Error</h2>
          <p className="text-[var(--muted)]">{error || 'Failed to load profile'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl lg:text-4xl font-bold mb-2">
          My <span className="gradient-text">Profile</span>
        </h1>
        <p className="text-[var(--muted)]">Manage your account settings and security</p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {/* Profile Card */}
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
        <h2 className="text-xl font-bold mb-6">Account Information</h2>
        
        <div className="grid gap-6">
          {/* Phone */}
          <div className="flex items-center justify-between py-3 border-b border-[var(--border)]">
            <div>
              <p className="text-sm text-[var(--muted)]">Phone Number</p>
              <p className="font-mono text-lg">{admin.admin_phone}</p>
            </div>
          </div>

          {/* Role */}
          <div className="flex items-center justify-between py-3 border-b border-[var(--border)]">
            <div>
              <p className="text-sm text-[var(--muted)]">Role</p>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getRoleBadge(admin.role)}`}>
                {admin.role}
              </span>
            </div>
          </div>

          {/* 2FA Status */}
          <div className="flex items-center justify-between py-3 border-b border-[var(--border)]">
            <div>
              <p className="text-sm text-[var(--muted)]">Two-Factor Authentication</p>
              <div className="flex items-center gap-3 mt-1">
                {admin.totp_enabled ? (
                  <>
                    <span className="text-green-400">✓ Enabled</span>
                    <button
                      onClick={handleTotpDisable}
                      disabled={totpLoading}
                      className="text-sm text-red-400 hover:text-red-300"
                    >
                      Disable
                    </button>
                  </>
                ) : (
                  <>
                    <span className="text-[var(--muted)]">✕ Disabled</span>
                    <button
                      onClick={handleTotpSetup}
                      className="text-sm text-[var(--primary)] hover:opacity-80"
                    >
                      Enable 2FA
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* PIN */}
          <div className="flex items-center justify-between py-3 border-b border-[var(--border)]">
            <div>
              <p className="text-sm text-[var(--muted)]">PIN</p>
              <p className="text-[var(--muted)]">••••</p>
            </div>
            <button
              onClick={() => setShowPinModal(true)}
              className="px-4 py-2 text-sm bg-[var(--card-hover)] hover:bg-[var(--primary)] hover:text-black rounded-lg transition-colors"
            >
              Change PIN
            </button>
          </div>

          {/* Account Created */}
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm text-[var(--muted)]">Account Created</p>
              <p>{formatDate(admin.created_at)}</p>
            </div>
          </div>

          {/* Last Login */}
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm text-[var(--muted)]">Last Login</p>
              <p>{formatDate(admin.last_used)}</p>
            </div>
          </div>

          {/* Lock Status */}
          {admin.locked_until && (
            <div className="flex items-center justify-between py-3 bg-red-500/10 -mx-6 px-6 -mb-6 rounded-b-2xl">
              <div>
                <p className="text-sm text-red-400">Account Locked Until</p>
                <p className="text-red-300">{formatDate(admin.locked_until)}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Security Tips */}
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6">
        <h2 className="text-xl font-bold mb-4">Security Tips</h2>
        <ul className="space-y-3 text-[var(--muted)]">
          <li className="flex items-start gap-2">
            <span className="text-green-400">✓</span>
            <span>Use a unique PIN that's not easily guessable</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-400">✓</span>
            <span>Enable two-factor authentication for added security</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-400">✓</span>
            <span>Never share your login credentials with anyone</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-400">✓</span>
            <span>Log out when using shared devices</span>
          </li>
        </ul>
      </div>

      {/* Change PIN Modal */}
      {showPinModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 w-full max-w-md">
            <h3 className="text-xl font-bold mb-4">Change PIN</h3>
            
            <form onSubmit={handlePinChange} className="space-y-4">
              {pinMessage && (
                <div className={`p-4 rounded-xl text-sm ${
                  pinMessage.includes('success') 
                    ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                    : 'bg-red-500/10 border border-red-500/30 text-red-400'
                }`}>
                  {pinMessage}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-2">Current PIN</label>
                <input
                  type="password"
                  value={currentPin}
                  onChange={(e) => setCurrentPin(e.target.value)}
                  placeholder="Enter current PIN"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                  maxLength={6}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">New PIN</label>
                <input
                  type="password"
                  value={newPin}
                  onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ''))}
                  placeholder="Enter new PIN (4-6 digits)"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                  maxLength={6}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Confirm New PIN</label>
                <input
                  type="password"
                  value={confirmPin}
                  onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, ''))}
                  placeholder="Confirm new PIN"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                  maxLength={6}
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowPinModal(false);
                    setPinMessage('');
                    setCurrentPin('');
                    setNewPin('');
                    setConfirmPin('');
                  }}
                  className="flex-1 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] font-medium hover:bg-[var(--card)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={pinLoading || !currentPin || !newPin || !confirmPin}
                  className="flex-1 py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {pinLoading ? 'Changing...' : 'Change PIN'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TOTP Setup Modal */}
      {showTotpModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 w-full max-w-md">
            <h3 className="text-xl font-bold mb-4">Enable 2FA</h3>
            
            <form onSubmit={handleTotpEnable} className="space-y-4">
              {totpMessage && (
                <div className={`p-4 rounded-xl text-sm ${
                  totpMessage.includes('success') 
                    ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                    : 'bg-red-500/10 border border-red-500/30 text-red-400'
                }`}>
                  {totpMessage}
                </div>
              )}

              {qrCodeUrl && (
                <div className="flex flex-col items-center mb-4">
                  <img 
                    src={qrCodeUrl} 
                    alt="2FA QR Code" 
                    className="w-48 h-48 border border-[var(--border)] rounded-lg"
                  />
                  <p className="text-sm text-[var(--muted)] mt-2 text-center">
                    Scan this QR code with your authenticator app
                  </p>
                  {totpSecret && (
                    <p className="text-xs text-[var(--muted)] mt-2 font-mono">
                      Or enter this secret: {totpSecret}
                    </p>
                  )}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-2">Verification Code</label>
                <input
                  type="text"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="Enter 6-digit code"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                  maxLength={6}
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowTotpModal(false);
                    setTotpMessage('');
                    setTotpCode('');
                  }}
                  className="flex-1 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] font-medium hover:bg-[var(--card)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={totpLoading || totpCode.length !== 6}
                  className="flex-1 py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {totpLoading ? 'Enabling...' : 'Enable 2FA'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

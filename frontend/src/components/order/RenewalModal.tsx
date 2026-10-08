'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { X, ShoppingCart, Clock, Shield } from '@phosphor-icons/react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.styxproxy.com';

interface OrderData {
  order_id: string;
  tx_ref?: string;
  status: string;
  plan_type: string;
  country: string;
  amount_paid_ngn: number;
  created_at?: string;
  expires_at?: string;
  styxproxy_credential?: {
    styxproxy_username: string;
    styxproxy_password: string;
    upstream_proxy_ip: string;
    upstream_proxy_port: number;
    expires_at: string;
  };
  max_rotations?: number;
  rotation_count?: number;
  is_renewable?: boolean;
  user_message?: string;
  next_action?: string;
}

interface RenewalModalProps {
  order: OrderData;
  onClose: () => void;
  onRenewed: (updatedOrder: OrderData) => void;
}

const GB_TIERS = [5, 10, 20, 50, 100];
const MIN_GB = 5;

type Gateway = 'flutterwave' | 'paystack';

export default function RenewalModal({ order, onClose, onRenewed }: RenewalModalProps) {
  const [selectedGb, setSelectedGb] = useState<number | null>(10);
  const [customGb, setCustomGb] = useState('');
  const [isCustom, setIsCustom] = useState(false);
  const [gateway, setGateway] = useState<Gateway>('flutterwave');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  const effectiveGb = isCustom ? parseFloat(customGb) || 0 : selectedGb || 0;
  const isValid = effectiveGb >= MIN_GB;

  const handleBackdropClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  }, [onClose]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (modalRef.current) {
      modalRef.current.focus();
    }
  }, []);

  async function handleRenew() {
    if (!isValid || loading) return;
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/renewals/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: order.order_id,
          quantity_gb: effectiveGb,
          gateway,
          customer_email: email || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        const msg = typeof data.detail === 'string' ? data.detail
          : typeof data.error === 'string' ? data.error
          : 'Renewal failed. Please try again.';
        setError(msg);
        setLoading(false);
        return;
      }

      setSuccess(true);
      setTimeout(() => {
        if (data.checkout_url) {
          window.location.href = data.checkout_url;
        }
      }, 800);
    } catch {
      setError('Network error. Please check your connection and try again.');
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="renewal-modal-title"
    >
      <div
        ref={modalRef}
        tabIndex={-1}
        className="bg-[var(--card)] border border-[var(--border)] rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[var(--border)]">
          <div>
            <h2 id="renewal-modal-title" className="text-xl font-bold">
              Renew Proxy
            </h2>
            <p className="text-sm text-[var(--muted)] mt-1">
              Extend your subscription — stack 30 days from today
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors p-1"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Current Plan Summary */}
          <div className="bg-[var(--background)] rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[var(--muted)] uppercase tracking-wide">Current Plan</p>
                <p className="text-sm font-semibold mt-1">
                  {order.plan_type?.charAt(0).toUpperCase()}{order.plan_type?.slice(1)} Proxy
                  {order.country ? ` — ${order.country}` : ''}
                </p>
              </div>
              {order.expires_at && (
                <div className="text-right">
                  <p className="text-xs text-[var(--muted)]">Expires</p>
                  <p className="text-sm font-medium">
                    {new Date(order.expires_at).toLocaleDateString('en-NG', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* GB Selection */}
          <div>
            <label className="block text-sm font-medium mb-3">Select Data</label>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 mb-3">
              {GB_TIERS.map((gb) => (
                <button
                  key={gb}
                  onClick={() => { setSelectedGb(gb); setIsCustom(false); }}
                  className={`py-3 rounded-xl text-sm font-semibold transition-all ${
                    !isCustom && selectedGb === gb
                      ? 'bg-[var(--primary)] text-black'
                      : 'bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)]'
                  }`}
                >
                  {gb} GB
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="number"
                min={MIN_GB}
                value={customGb}
                onChange={(e) => { setCustomGb(e.target.value); setIsCustom(true); }}
                placeholder={`Custom (min ${MIN_GB} GB)`}
                className="flex-1 px-4 py-3 bg-[var(--background)] border border-[var(--border)] rounded-xl focus:outline-none focus:border-[var(--primary)] transition-colors text-sm"
              />
              <button
                onClick={() => setIsCustom(true)}
                className={`px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  isCustom
                    ? 'bg-[var(--primary)] text-black'
                    : 'bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)]'
                }`}
              >
                Custom
              </button>
            </div>
            {!isValid && (isCustom || customGb) && (
              <p className="text-xs text-[var(--error)] mt-2">Minimum renewal is {MIN_GB} GB</p>
            )}
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium mb-2">Email (for payment receipt)</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="w-full px-4 py-3 bg-[var(--background)] border border-[var(--border)] rounded-xl focus:outline-none focus:border-[var(--primary)] transition-colors text-sm"
            />
          </div>

          {/* Gateway */}
          <div>
            <label className="block text-sm font-medium mb-3">Payment Method</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setGateway('flutterwave')}
                className={`py-3 px-4 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                  gateway === 'flutterwave'
                    ? 'bg-[var(--primary)] text-black'
                    : 'bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)]'
                }`}
              >
                Flutterwave
              </button>
              <button
                onClick={() => setGateway('paystack')}
                className={`py-3 px-4 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                  gateway === 'paystack'
                    ? 'bg-[var(--primary)] text-black'
                    : 'bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)]'
                }`}
              >
                Paystack
              </button>
            </div>
          </div>

          {/* Summary */}
          {isValid && (
            <div className="bg-[var(--background)] rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--muted)]">Data</span>
                <span className="text-sm font-semibold">{effectiveGb} GB</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--muted)]">Duration</span>
                <span className="text-sm font-semibold">30 days</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--muted)]">Stacking</span>
                <span className="text-sm font-semibold">From today</span>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-xl p-3">
              <p className="text-sm text-[var(--error)]">{error}</p>
            </div>
          )}

          {/* Success */}
          {success && (
            <div className="bg-[var(--success)]/10 border border-[var(--success)]/30 rounded-xl p-3">
              <p className="text-sm text-[var(--success)] font-medium">Redirecting to payment…</p>
            </div>
          )}

          {/* Info */}
          <div className="flex items-start gap-2 text-xs text-[var(--muted)]">
            <Shield className="w-4 h-4 shrink-0 mt-0.5" />
            <p>
              Your proxy credentials stay the same. Renewal extends the expiry date and adds data — no new proxy issued.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[var(--border)] flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors font-medium text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleRenew}
            disabled={!isValid || loading || success}
            className="flex-1 px-4 py-3 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Clock className="w-4 h-4 animate-spin" />
                Processing…
              </>
            ) : success ? (
              'Redirecting…'
            ) : (
              <>
                <ShoppingCart className="w-4 h-4" />
                Renew {isValid ? `${effectiveGb} GB` : ''}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

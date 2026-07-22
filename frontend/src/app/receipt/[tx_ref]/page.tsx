'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useToast } from '@/components/Toast';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.styxproxy.com';

interface OrderData {
  order_id?: string;
  tx_ref?: string;
  status?: string;
  plan_type?: string;
  plan_code?: string;
  country?: string;
  quantity?: number;
  amount_paid_ngn?: number;
  customer_name?: string | null;
  created_at?: string;
  expires_at?: string;
  styxproxy_credential?: {
    bun_username?: string;
    styxproxy_password?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    protocol?: string;
    expires_at?: string;
    status?: string;
  };
}

function ReceiptContent() {
  const searchParams = useSearchParams();
  const txRef = searchParams.get('tx_ref');
  const { toast } = useToast();

  const [order, setOrder] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch order data on mount
  useEffect(() => {
    if (!txRef) {
      setError('No transaction reference provided');
      setLoading(false);
      return;
    }

    const fetchOrder = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/orders/${txRef}/receipt`);
        if (!res.ok) {
          if (res.status === 404) {
            setError('Order not found');
          } else {
            setError('Failed to fetch order');
          }
          return;
        }
        const data = await res.json();
        setOrder(data);
      } catch (err) {
        setError('Failed to fetch order');
        console.error('Error fetching order:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchOrder();
  }, [txRef]);

  // Handle PDF download from backend
  const handleDownloadPDF = async () => {
    if (!txRef) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/orders/${txRef}/pdf`);
      if (!response.ok) {
        toast({ type: 'error', title: 'Download failed', message: 'Could not generate PDF' });
        return;
      }
      
      // Get blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `styxproxy-receipt-${txRef}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
      
      toast({ type: 'success', title: 'Downloaded', message: 'Receipt PDF downloaded' });
    } catch (err) {
      toast({ type: 'error', title: 'Download failed', message: 'Could not download PDF' });
      console.error('Error downloading PDF:', err);
    }
  };

  // Handle copy credentials
  const handleCopyCredentials = async () => {
    if (!order?.styxproxy_credential) return;
    const cred = order.styxproxy_credential;
    const text = [
      `Username: ${cred.styxproxy_username || ''}`,
      `Password: ${cred.styxproxy_password || ''}`,
      `Proxy: ${cred.upstream_proxy_ip || ''}:${cred.upstream_proxy_port || ''}`,
      `Full: http://${cred.styxproxy_username || ''}:${cred.styxproxy_password || ''}@${cred.upstream_proxy_ip || ''}:${cred.upstream_proxy_port || ''}`,
    ].join('\n');
    try {
      await navigator.clipboard.writeText(text);
      toast({ type: 'success', title: 'Copied!', message: 'Credentials copied to clipboard.' });
    } catch {
      toast({ type: 'error', title: 'Copy failed', message: 'Use Ctrl+C / Cmd+C instead.' });
    }
  };

  if (loading) {
    return (
      <main className="flex-1 flex items-center justify-center px-4">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-[var(--primary)] border-t-transparent animate-spin" />
          <h1 className="text-2xl font-bold mb-2">Loading Receipt...</h1>
          <p className="text-[var(--muted)]">Fetching your order details</p>
        </div>
      </main>
    );
  }

  if (error || !txRef) {
    return (
      <main className="flex-1 flex items-center justify-center px-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Receipt Not Found</h1>
          <p className="text-[var(--muted)] mb-6">
            {error || "We couldn't find an order with that reference."}
          </p>
          <Link
            href="/order"
            className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
          >
            Place New Order
          </Link>
        </div>
      </main>
    );
  }

  const isSuccess = order?.status === 'fulfilled' || order?.status === 'active';
  const statusColor = isSuccess ? 'var(--primary)' : 'var(--muted)';

  return (
    <main className="flex-1 flex items-start justify-center px-4 pt-32 pb-16">
      <div className="max-w-lg w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">Payment Receipt</h1>
          <p className="text-[var(--muted)]">Reference: {txRef}</p>
        </div>

        {/* Order Details Card */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Order Details</h2>
            <span 
              className="px-3 py-1 rounded-full text-sm font-medium capitalize"
              style={{ 
                backgroundColor: `${statusColor}20`, 
                color: statusColor,
                border: `1px solid ${statusColor}40`
              }}
            >
              {order?.status || 'Unknown'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-[var(--muted)]">Order ID</span>
              <p className="font-medium">{order?.order_id || 'N/A'}</p>
            </div>
            <div>
              <span className="text-[var(--muted)]">Date</span>
              <p className="font-medium">
                {order?.created_at 
                  ? new Date(order.created_at).toLocaleDateString('en-NG', {
                      year: 'numeric', month: 'long', day: 'numeric'
                    })
                  : 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-[var(--muted)]">Plan</span>
              <p className="font-medium">{order?.plan_code || 'N/A'}</p>
            </div>
            <div>
              <span className="text-[var(--muted)]">Country</span>
              <p className="font-medium">{order?.country || 'N/A'}</p>
            </div>
            <div>
              <span className="text-[var(--muted)]">Quantity</span>
              <p className="font-medium">{order?.quantity || 1} proxy{(order?.quantity || 1) !== 1 ? 'ies' : ''}</p>
            </div>
            <div>
              <span className="text-[var(--muted)]">Amount Paid</span>
              <p className="font-medium text-[var(--primary)]">
                ₦{Number(order?.amount_paid_ngn || 0).toLocaleString('en-NG')}
              </p>
            </div>
          </div>
        </div>

        {/* Credentials Card - Show if available */}
        {order?.styxproxy_credential && (
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Proxy Credentials</h2>
              <button
                onClick={handleCopyCredentials}
                className="text-xs px-3 py-1.5 bg-[var(--primary)]/10 hover:bg-[var(--primary)]/20 text-[var(--primary)] border border-[var(--primary)]/30 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm text-[var(--muted)]">Username</label>
                <p className="font-mono text-lg">{order.styxproxy_credential.styxproxy_username}</p>
              </div>
              <div>
                <label className="text-sm text-[var(--muted)]">Protocol</label>
                <p className="font-mono text-sm">HTTP / SOCKS5</p>
              </div>
              <div>
                <label className="text-sm text-[var(--muted)]">Proxy Address</label>
                <p className="font-mono text-lg">
                  {order.styxproxy_credential.upstream_proxy_ip}:{order.styxproxy_credential.upstream_proxy_port}
                </p>
              </div>
              <div>
                <label className="text-sm text-[var(--muted)]">Password</label>
                <p className="font-mono text-sm">{order.styxproxy_credential.styxproxy_password || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm text-[var(--muted)]">Full Format</label>
                <p className="font-mono text-xs text-[var(--muted)] break-all leading-relaxed">
                  http://{order.styxproxy_credential.styxproxy_username}:{order.styxproxy_credential.styxproxy_password || 'YOUR_PASSWORD'}@{order.styxproxy_credential.upstream_proxy_ip}:{order.styxproxy_credential.upstream_proxy_port}
                </p>
              </div>
              <div>
                <label className="text-sm text-[var(--muted)]">Expires</label>
                <p className="font-medium">
                  {order.styxproxy_credential.expires_at
                    ? new Date(order.styxproxy_credential.expires_at).toLocaleDateString('en-NG', {
                        year: 'numeric', month: 'long', day: 'numeric',
                      })
                    : 'N/A'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={handleDownloadPDF}
            className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download PDF Receipt
          </button>
          
          <Link
            href="/order"
            className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
          >
            Place New Order
          </Link>
        </div>

        {/* Support Footer */}
        <div className="mt-8 text-center text-sm text-[var(--muted)]">
          <p>Need help? <a href="/contact" className="text-[var(--primary)] hover:underline">Contact support</a></p>
        </div>
      </div>
    </main>
  );
}

export default function ReceiptPage() {
  return (
    <Suspense fallback={
      <main className="flex-1 flex items-center justify-center px-4">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-[var(--primary)] border-t-transparent animate-spin" />
        </div>
      </main>
    }>
      <ReceiptContent />
    </Suspense>
  );
}

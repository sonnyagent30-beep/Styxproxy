'use client';

/* eslint-disable react-hooks/set-state-in-effect */

import { useParams, useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useToast } from '@/components/Toast';
import { generateReceiptPDF } from '@/lib/pdf-receipt';

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
  // The public receipt endpoint is UNAUTHENTICATED and discloses no proxy
  // connection details — only whether a credential exists and its status.
  // `tx_ref` is the payment reference (it appears in gateway dashboards, access
  // logs and emailed links), so it is not a secret and must never be treated as
  // a bearer token for proxy access.
  styxproxy_credential?: {
    status?: string;
  };
}

function ReceiptContent() {
  const searchParams = useSearchParams();
  // Read the ref from the ROUTE segment. This page lives at
  // receipt/[tx_ref]/page.tsx, and every receipt URL the system generates is
  // the path form (https://styxproxy.com/receipt/{tx_ref}) — fulfilment
  // worker, both gateway services, the admin resend endpoint and the Charon
  // tools all emit it, and it is what ships inside the credential email.
  //
  // It used to read only `?tx_ref=`, which the route never provides, so every
  // emailed link rendered "Receipt Not Found / No transaction reference
  // provided" even though the data endpoint returned 200. The query form is
  // kept as a fallback so a hand-edited `?tx_ref=` link still works.
  const params = useParams<{ tx_ref?: string | string[] }>();
  const routeTxRef = Array.isArray(params.tx_ref) ? params.tx_ref[0] : params.tx_ref;
  const txRef = routeTxRef || searchParams.get('tx_ref');
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

  // Generate the PDF in the browser via the shared jsPDF generator
  // (src/lib/pdf-receipt.ts) -- the same code path /thank-you uses.
  //
  // There is deliberately no server-side PDF endpoint: the backend route that
  // rendered receipts with WeasyPrint was removed because WeasyPrint was never
  // installed on production and needs native pango/cairo libraries the host
  // does not have, so the endpoint could only ever 500. jspdf is already a
  // declared, installed frontend dependency, so this path cannot regress the
  // same way.
  const handleDownloadPDF = async () => {
    if (!txRef || !order) return;

    // The generator takes cart line-items. This page is reached from a URL, so
    // there is no in-memory cart to reuse -- rebuild a single line from the
    // order itself. price_ngn is per-unit, and the generator prints
    // price_ngn * quantity as the line total, so derive the unit price to keep
    // the printed TOTAL PAID equal to the amount actually charged.
    const quantity = order.quantity || 1;
    const total = Number(order.amount_paid_ngn || 0);

    try {
      await generateReceiptPDF(
        {
          order_id: order.order_id,
          status: order.status,
          customer_name: order.customer_name,
          styxproxy_credential: order.styxproxy_credential,
        },
        [
          {
            name: order.plan_code || 'Proxy',
            quantity,
            price_ngn: total / quantity,
          },
        ],
        txRef,
        `styxproxy-receipt-${txRef}.pdf`,
      );

      toast({ type: 'success', title: 'Downloaded', message: 'Receipt PDF downloaded' });
    } catch (err) {
      toast({ type: 'error', title: 'Download failed', message: 'Could not download PDF' });
      console.error('Error generating PDF:', err);
    }
  };

  // Handle copy credentials
  const handleCopyCredentials = async () => {
    // Credential details are NOT on this page by design (see the type above).
    // Copy is intentionally not offered here; the receipt proves payment and the
    // credential arrives by email / an authenticated lookup.
    return;
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

        {/* Credentials status — the public endpoint deliberately discloses no
                    username / IP / port / password. See ReceiptCredentialPublic. */}
                {order?.styxproxy_credential && (
                  <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
                    <h2 className="text-lg font-semibold mb-2">Proxy Access</h2>
                    <p className="text-sm text-[var(--muted)] leading-relaxed">
                      Your proxy credentials were sent to the email address on this order. This receipt
                      confirms your payment; for security it does not display connection details on a
                      public page.
                    </p>
                    <div className="mt-4">
                      <label className="text-sm text-[var(--muted)]">Credential status</label>
                      <p className="font-mono text-sm">{order.styxproxy_credential.status || 'active'}</p>
                    </div>
                    <p className="text-xs text-[var(--muted)] mt-4">
                      Can&apos;t find the email? Contact support with your payment reference and we&apos;ll
                      resend it.
                    </p>
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

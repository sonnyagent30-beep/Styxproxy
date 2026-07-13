'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';

// Cart item type (matches order page)
interface CartItem {
  plan_code: string;
  name: string;
  flag: string;
  price_ngn: number;
  quantity: number;
}

interface OrderData {
  order_id?: string;
  status?: string;
  plan_type?: string;
  country?: string;
  amount_paid_ngn?: number;
  tx_ref?: string;
  bunche_credential?: {
    bun_username?: string;
    bun_password?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    expires_at?: string;
  };
  created_at?: string;
  expires_at?: string;
}

// PDF generation function
async function generateReceiptPDF(order: OrderData, cart: CartItem[], txRef: string) {
  const { jsPDF } = await import('jspdf');

  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();

  // ── Dark background ──────────────────────────────────────────
  doc.setFillColor(15, 15, 15);
  doc.rect(0, 0, W, H, 'F');

  // ── Top accent bar ────────────────────────────────────────────
  doc.setFillColor(16, 185, 129); // primary
  doc.rect(0, 0, W, 6, 'F');

  // ── Brand logo area ────────────────────────────────────────────
  doc.setFillColor(16, 185, 129);
  doc.roundedRect(20, 18, 12, 12, 3, 3, 'F');
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text('S', 26, 25.5, { align: 'center' });

  doc.setTextColor(245, 245, 245);
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy', 35, 25);

  doc.setTextColor(115, 115, 115);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('Anonymous Proxy Service', 35, 30.5);

  // ── RECEIPT label ─────────────────────────────────────────────
  doc.setTextColor(16, 185, 129);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('PAYMENT RECEIPT', W - 20, 22, { align: 'right' });
  doc.setTextColor(115, 115, 115);
  doc.setFontSize(8);
  doc.text('styxproxy.com', W - 20, 27, { align: 'right' });

  // ── Divider ───────────────────────────────────────────────────
  doc.setDrawColor(42, 42, 42);
  doc.setLineWidth(0.5);
  doc.line(20, 40, W - 20, 40);

  // ── Order IDs ─────────────────────────────────────────────────
  let y = 52;
  doc.setFillColor(26, 26, 26);
  doc.roundedRect(20, y - 6, W - 40, 22, 3, 3, 'F');

  doc.setTextColor(115, 115, 115);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('TRANSACTION REFERENCE', 25, y);
  doc.text('ORDER ID', W / 2 + 5, y);

  doc.setTextColor(245, 245, 245);
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text(txRef || 'N/A', 25, y + 8);

  const orderIdDisplay = order?.order_id || 'N/A';
  doc.text(orderIdDisplay.length > 20 ? orderIdDisplay.slice(0, 20) + '…' : orderIdDisplay, W / 2 + 5, y + 8);

  doc.setTextColor(115, 115, 115);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Flutterwave', 25, y + 14);
  doc.text('Internal', W / 2 + 5, y + 14);

  // ── Date + Status ─────────────────────────────────────────────
  y = 82;
  doc.setTextColor(115, 115, 115);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('DATE', 25, y);
  doc.text('STATUS', W / 2 + 5, y);

  doc.setTextColor(245, 245, 245);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(new Date().toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' }), 25, y + 7);

  const status = order?.status?.toUpperCase() || 'PENDING';
  doc.setTextColor(16, 185, 129);
  doc.setFont('helvetica', 'bold');
  doc.text(status, W / 2 + 5, y + 7);

  // ── Divider ───────────────────────────────────────────────────
  doc.setDrawColor(42, 42, 42);
  doc.line(20, 98, W - 20, 98);

  // ── Items ─────────────────────────────────────────────────────
  y = 106;
  doc.setTextColor(115, 115, 115);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('ITEM', 25, y);
  doc.text('QTY', W - 45, y, { align: 'right' });
  doc.text('AMOUNT', W - 20, y, { align: 'right' });

  doc.setDrawColor(42, 42, 42);
  doc.line(20, y + 3, W - 20, y + 3);

  let subtotal = 0;
  y += 10;

  doc.setTextColor(245, 245, 245);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');

  cart.forEach((item) => {
    const lineTotal = item.price_ngn * item.quantity;
    subtotal += lineTotal;

    doc.setTextColor(245, 245, 245);
    doc.text(`${item.flag} ${item.name}`, 25, y);
    doc.text(String(item.quantity), W - 45, y, { align: 'right' });
    doc.text(`₦${lineTotal.toLocaleString('en-NG')}`, W - 20, y, { align: 'right' });
    y += 8;
  });

  // ── Total ─────────────────────────────────────────────────────
  y += 4;
  doc.setDrawColor(42, 42, 42);
  doc.line(20, y, W - 20, y);
  y += 10;

  doc.setFillColor(16, 185, 129);
  doc.roundedRect(W - 70, y - 6, 50, 12, 2, 2, 'F');
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.text('TOTAL', W - 65, y - 1);
  doc.text(`₦${subtotal.toLocaleString('en-NG')}`, W - 25, y + 3, { align: 'right' });

  // ── Proxy Credentials ────────────────────────────────────────
  if (order?.bunche_credential) {
    y += 22;
    doc.setTextColor(16, 185, 129);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.text('YOUR PROXY CREDENTIALS', 20, y);

    doc.setFillColor(26, 26, 26);
    doc.roundedRect(20, y + 4, W - 40, 48, 3, 3, 'F');

    const cred = order.bunche_credential;
    y += 14;

    // Username
    doc.setTextColor(115, 115, 115);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('USERNAME', 28, y);
    doc.setTextColor(52, 211, 153);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text(cred.bun_username || 'N/A', 28, y + 7);

    // Password
    doc.setTextColor(115, 115, 115);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('PASSWORD', W / 2 + 5, y);
    doc.setTextColor(52, 211, 153);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text('********', W / 2 + 5, y + 7);

    y += 18;

    // Proxy address
    doc.setTextColor(115, 115, 115);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('PROXY ADDRESS', 28, y);
    const proxyStr = `${cred.upstream_proxy_ip}:${cred.upstream_proxy_port}`;
    doc.setTextColor(52, 211, 153);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text(proxyStr, 28, y + 7);

    // Protocol
    doc.setTextColor(115, 115, 115);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('PROTOCOL', W / 2 + 5, y);
    doc.setTextColor(52, 211, 153);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text('HTTP / SOCKS5', W / 2 + 5, y + 7);

    y += 18;

    // Full format string
    doc.setTextColor(115, 115, 115);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('FULL FORMAT', 28, y);

    const fullStr = `http://${cred.bun_username}:YOUR_PASSWORD@${proxyStr}`;
    doc.setTextColor(115, 115, 115);
    doc.setFontSize(7.5);
    doc.setFont('helvetica', 'normal');
    const lines = doc.splitTextToSize(fullStr, W - 56);
    doc.text(lines, 28, y + 7);

    //Expires
    y += 7 + (lines.length * 4);
    doc.setTextColor(115, 115, 115);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('EXPIRES', 28, y);
    doc.setTextColor(245, 245, 245);
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(cred.expires_at ? new Date(cred.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A', 28, y + 6);
  }

  // ── Footer ────────────────────────────────────────────────────
  const footerY = H - 18;
  doc.setDrawColor(42, 42, 42);
  doc.line(20, footerY - 6, W - 20, footerY - 6);

  doc.setTextColor(115, 115, 115);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Need help? Chat with Charon → @StyxproxyBot  |  hello@styxproxy.com  |  styxproxy.com', W / 2, footerY, { align: 'center' });

  doc.setFontSize(6);
  doc.text('This receipt was generated automatically. No signature required.', W / 2, footerY + 5, { align: 'center' });

  // Save
  doc.save(`styxproxy-receipt-${txRef}.pdf`);
}

function ThankYouContent() {
  const searchParams = useSearchParams();
  const txRef = searchParams.get('tx_ref');

  const [order, setOrder] = useState<OrderData | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 60;

  // Load cart from sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem('styxproxy_cart');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setCart(parsed);
        }
      } catch (e) {
        // Invalid cart
      }
    }
  }, []);

  // Poll for order status
  useEffect(() => {
    if (!txRef) {
      setError(true);
      setLoading(false);
      return;
    }

    const fetchOrder = async () => {
      try {
        const res = await fetch(`/api/orders/${txRef}`);
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();

        if (data.order_id) setOrder(data);

        if (data.status === 'fulfilled' || data.status === 'active' ||
            data.status === 'expired' || data.status === 'cancelled') {
          setLoading(false);
          return;
        }
        setAttempts(prev => prev + 1);
      } catch {
        setAttempts(prev => prev + 1);
      }
    };

    fetchOrder();

    const interval = setInterval(() => {
      if (attempts >= maxAttempts) {
        setLoading(false);
        clearInterval(interval);
        return;
      }
      fetchOrder();
    }, 5000);

    return () => clearInterval(interval);
  }, [txRef, attempts]);

  // Calculate totals from cart
  const cartTotal = cart.reduce((sum, item) => sum + item.price_ngn * item.quantity, 0);

  // Handle PDF download
  const handleDownloadPDF = async () => {
    if (order && cart.length > 0) {
      await generateReceiptPDF(order, cart, txRef!);
    }
  };

  if (!txRef || error) {
    return (
      <main className="flex-1 flex items-center justify-center px-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Order Not Found</h1>
          <p className="text-[var(--muted)] mb-6">
            We couldn&apos;t find an order with that reference.
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

  const isPending = order?.status === 'pending' || order?.status === 'paid';
  const isSuccess = order?.status === 'fulfilled' || order?.status === 'active';
  const isErrorState = order?.status === 'expired' || order?.status === 'cancelled';

  return (
    <main className="flex-1 flex items-start justify-center px-4 pt-32 pb-16">
      <div className="max-w-lg w-full">
        {/* Pending/Processing State */}
        {loading && isPending && (
          <div className="text-center animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-[var(--primary)] border-t-transparent animate-spin" />
            <h1 className="text-2xl font-bold mb-2">Payment Confirmed!</h1>
            <p className="text-[var(--muted)]">
              Preparing your proxy credentials...
            </p>
            <p className="text-sm text-[var(--muted)] mt-4">
              Reference: {txRef}
            </p>
          </div>
        )}

        {/* Success State */}
        {isSuccess && (
          <div className="animate-fade-in">
            <div className="text-center mb-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--primary)]/20 flex items-center justify-center">
                <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-[var(--primary)] mb-2">Order Complete!</h1>
              <p className="text-[var(--muted)]">
                Your proxies are ready. Here are your credentials:
              </p>
            </div>

            {/* Credentials Card - Show all proxies from cart */}
            <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
              <h2 className="text-lg font-semibold mb-4">Proxy Credentials</h2>
              
              {/* If we have credential from API, show it */}
              {order?.bunche_credential ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-[var(--muted)]">Username</label>
                    <p className="font-mono text-lg">{order.bunche_credential.bun_username}</p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Protocol</label>
                    <p className="font-mono text-sm">HTTP / SOCKS5</p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Proxy Address</label>
                    <p className="font-mono text-lg">
                      {order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Password</label>
                    <p className="font-mono text-sm">{order.bunche_credential.bun_password || 'N/A'}</p>
                  </div>
                  <div className="col-span-2">
                    <label className="text-sm text-[var(--muted)]">Full Format</label>
                    <p className="font-mono text-xs text-[var(--muted)] break-all leading-relaxed">
                      http://{order.bunche_credential.bun_username}:YOUR_PASSWORD@{order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Expires</label>
                    <p className="font-medium">
                      {order.bunche_credential.expires_at
                        ? new Date(order.bunche_credential.expires_at).toLocaleDateString('en-NG', {
                            year: 'numeric', month: 'long', day: 'numeric',
                          })
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              ) : (
                // Fallback: show cart items as pending credentials
                <div className="space-y-3">
                  {cart.map((item, idx) => (
                    <div key={item.plan_code} className="p-3 rounded-lg bg-[var(--card-hover)]">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xl">{item.flag}</span>
                        <span className="font-medium">{item.name}</span>
                        <span className="text-sm text-[var(--muted)]">× {item.quantity}</span>
                      </div>
                      <p className="text-sm text-[var(--muted)]">Credentials will be delivered shortly</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Order Summary */}
            <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-[var(--muted)]">Order ID</span>
                  <p className="font-medium">{order?.order_id || txRef}</p>
                </div>
                <div>
                  <span className="text-[var(--muted)]">Amount Paid</span>
                  <p className="font-medium">₦{cartTotal.toLocaleString('en-NG')}</p>
                </div>
                <div>
                  <span className="text-[var(--muted)]">Status</span>
                  <p className="font-medium text-[var(--primary)] capitalize">{order?.status}</p>
                </div>
                <div>
                  <span className="text-[var(--muted)]">Items</span>
                  <p className="font-medium">{cart.reduce((s, i) => s + i.quantity, 0)} proxies</p>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-3">
              {cart.length > 0 && (
                <button
                  onClick={handleDownloadPDF}
                  className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download Receipt (PDF)
                </button>
              )}
              
              <Link
                href={`/manage?ref=${txRef}`}
                className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
              >
                Manage Order
              </Link>
              
              <Link
                href="/order"
                className="block w-full px-6 py-3 text-[var(--muted)] hover:text-[var(--foreground)] text-center transition-colors"
              >
                Order Another
              </Link>
            </div>
          </div>
        )}

        {/* Error/Expired State */}
        {!loading && isErrorState && (
          <div className="text-center animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--error)]/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-[var(--error)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold mb-2">Order {order?.status === 'expired' ? 'Expired' : 'Cancelled'}</h1>
            <p className="text-[var(--muted)] mb-6">This order is no longer active.</p>
            <Link
              href="/order"
              className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
            >
              Place New Order
            </Link>
          </div>
        )}

        {/* Timeout State */}
        {!loading && !order && attempts >= maxAttempts && (
          <div className="text-center animate-fade-in">
            <h1 className="text-2xl font-bold mb-2">Still Processing</h1>
            <p className="text-[var(--muted)] mb-6">
              Your order is being processed. Please check back in a few minutes.
            </p>
            <Link
              href={`/manage?ref=${txRef}`}
              className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
            >
              Check Order Status
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}

export default function ThankYouPage() {
  return (
    <Suspense fallback={
      <main className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </main>
    }>
      <ThankYouContent />
    </Suspense>
  );
}

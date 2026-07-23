'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useToast } from '@/components/Toast';
import { generateReceiptPDF } from '@/lib/pdf-receipt';
import type { ReceiptOrder } from '@/lib/pdf-receipt';

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
  customer_name?: string | null;
  is_renewable?: boolean;
  rotation_count?: number;
  max_rotations?: number;
  styxproxy_credential?: {
    bun_username?: string;
    styxproxy_username?: string;
    styxproxy_password?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    expires_at?: string;
  };
  created_at?: string;
  expires_at?: string;
}

// PDF generation function — matches the design template
async function generateLocalPDF(order: OrderData, cart: CartItem[], txRef: string) {
  const { jsPDF } = await import('jspdf');

  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();

  // Brand colors (matching template)
  const PRIMARY: [number, number, number] = [10, 210, 90];   // #0AD25A
  const BG: [number, number, number] = [10, 10, 10];          // #0a0a0a
  const CARD: [number, number, number] = [26, 26, 26];        // #1a1a1a
  const MUTED: [number, number, number] = [156, 163, 175];    // #9CA3AF
  const DIM: [number, number, number] = [107, 114, 128];      // #6B7280
  const WHITE: [number, number, number] = [255, 255, 255];
  const LIGHT: [number, number, number] = [209, 213, 219];    // #D1D5DB
  const BORDER: [number, number, number] = [38, 38, 38];      // #262626

  // ── Background ──────────────────────────────────────────
  doc.setFillColor(...BG);
  doc.rect(0, 0, W, H, 'F');

  // ── Top accent bar ─────────────────────────────────────
  doc.setFillColor(...PRIMARY);
  doc.rect(0, 0, W, 4, 'F');

  // ── Header: full lockup logo (S-mark + wordmark) ───────
  doc.setFillColor(...PRIMARY);
  doc.roundedRect(15, 14, 8, 8, 1.5, 1.5, 'F');
  doc.setTextColor(...BG);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'bold');
  doc.text('S', 19, 19, { align: 'center' });

  doc.setTextColor(...WHITE);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy', 26, 20);

  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Anonymous Proxy Service', 26, 24);

  // ── Right header: PAYMENT RECEIPT label ─────────────────
  doc.setTextColor(...PRIMARY);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.text('PAYMENT RECEIPT', W - 15, 17, { align: 'right' });

  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.text('styxproxy.com', W - 15, 21.5, { align: 'right' });
  doc.text(`Issued: ${new Date().toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })}`, W - 15, 25, { align: 'right' });

  // ── Divider ─────────────────────────────────────────────
  doc.setDrawColor(...BORDER);
  doc.setLineWidth(0.2);
  doc.line(15, 30, W - 15, 30);

  // ── ORDER CONFIRMATION section ──────────────────────────
  // Use real name if customer set one (WhatsApp/Telegram orders only)
  // Website orders remain anonymous — keep generic "customer"
  const customerName = order?.customer_name?.trim();
  const thankYouText = customerName ? `Thank you, ${customerName}.` : 'Thank you, customer.';

  doc.setTextColor(...MUTED);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('ORDER CONFIRMATION', 15, 37);

  doc.setTextColor(...WHITE);
  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text(thankYouText, 15, 49);

  doc.setTextColor(...MUTED);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('Your proxy is ready to use. Below are your credentials.', 15, 56);

  // FULFILLED pill on the right
  const status = order?.status?.toUpperCase() || 'PENDING';
  doc.setFillColor(...PRIMARY);
  doc.roundedRect(W - 50, 43, 35, 9, 4.5, 4.5, 'F');
  doc.setTextColor(...BG);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text(status, W - 32.5, 49, { align: 'center' });

  // ── Order details card ──────────────────────────────────
  const cardTop = 65;
  const cardBottom = cardTop - 42;
  doc.setFillColor(...CARD);
  doc.roundedRect(15, cardBottom, W - 30, 42, 3, 3, 'F');

  // Row 1: TX Ref | Order ID
  doc.setTextColor(...MUTED);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('TRANSACTION REFERENCE', 20, cardTop - 8);
  doc.text('ORDER ID', W / 2 + 5, cardTop - 8);

  doc.setTextColor(...WHITE);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text(txRef || 'N/A', 20, cardTop - 16);

  const orderIdDisplay = order?.order_id || 'N/A';
  doc.text(orderIdDisplay.length > 22 ? orderIdDisplay.slice(0, 22) + '…' : orderIdDisplay, W / 2 + 5, cardTop - 16);

  doc.setTextColor(...DIM);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'normal');
  doc.text('Flutterwave payment reference', 20, cardTop - 21);
  doc.text('Internal order reference', W / 2 + 5, cardTop - 21);

  // Divider inside card
  doc.setDrawColor(...BORDER);
  doc.line(20, cardTop - 26, W - 20, cardTop - 26);

  // Row 2: DATE | METHOD
  doc.setTextColor(...MUTED);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('DATE', 20, cardTop - 32);
  doc.text('METHOD', W / 2 + 5, cardTop - 32);

  doc.setTextColor(...WHITE);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(new Date().toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' }), 20, cardTop - 38);
  doc.text('Card / Bank / USSD / QR', W / 2 + 5, cardTop - 38);

  // ── Items section ───────────────────────────────────────
  let y = 72;
  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('ITEMS', 15, y);
  doc.text('QTY', W - 35, y, { align: 'right' });
  doc.text('AMOUNT', W - 15, y, { align: 'right' });

  doc.setDrawColor(...BORDER);
  doc.line(15, y + 2, W - 15, y + 2);

  y += 8;
  let subtotal = 0;

  cart.forEach((item) => {
    const lineTotal = item.price_ngn * item.quantity;
    subtotal += lineTotal;

    doc.setTextColor(...WHITE);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`${item.flag || ''} ${item.name}`, 15, y);

    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.text(`${item.quantity} ${item.quantity === 1 ? 'unit' : 'units'}  |  HTTP/SOCKS5`, 15, y + 4);

    doc.setTextColor(...WHITE);
    doc.setFontSize(10);
    doc.text(String(item.quantity), W - 35, y, { align: 'right' });
    doc.text(`N${lineTotal.toLocaleString('en-NG')}`, W - 15, y, { align: 'right' });
    y += 11;
  });

  // ── TOTAL PAID pill ─────────────────────────────────────
  doc.setFillColor(...PRIMARY);
  doc.roundedRect(W - 75, y, 60, 11, 2, 2, 'F');
  doc.setTextColor(...BG);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('TOTAL PAID', W - 70, y + 7.5);
  doc.setFontSize(11);
  doc.text(`N${subtotal.toLocaleString('en-NG')}`, W - 19, y + 7.5, { align: 'right' });

  // ── Credentials card (if available) ─────────────────────
  if (order?.styxproxy_credential) {
    const cred = order.styxproxy_credential;
    y += 18;

    // Section header (above card)
    doc.setTextColor(...PRIMARY);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.text('YOUR PROXY CREDENTIALS', 15, y);

    // Card with green border
    const cardH = 70;
    const credCardTop = y + 2;
    const credCardBottom = credCardTop - cardH;
    doc.setFillColor(...BG);
    doc.setDrawColor(...PRIMARY);
    doc.setLineWidth(0.6);
    doc.roundedRect(15, credCardBottom, W - 30, cardH, 3, 3, 'FD');
    doc.setDrawColor(...BORDER);
    doc.setLineWidth(0.2);

    // Layout: 4 rows
    let innerY = credCardTop - 8;
    const rowH = 16;

    // Row 1: USERNAME | PASSWORD
    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('USERNAME', 20, innerY);
    doc.text('PASSWORD', W / 2 + 5, innerY);

    doc.setTextColor(...PRIMARY);
    doc.setFontSize(9.5);
    doc.setFont('helvetica', 'bold');
    doc.text(cred.styxproxy_username || 'N/A', 20, innerY + 5);
    doc.text(cred.styxproxy_password || 'N/A', W / 2 + 5, innerY + 5);

    doc.setDrawColor(...BORDER);
    doc.line(20, innerY + 8, W - 20, innerY + 8);
    innerY -= rowH;

    // Row 2: PROXY ADDRESS | PROTOCOL
    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('PROXY ADDRESS', 20, innerY);
    doc.text('PROTOCOL', W / 2 + 5, innerY);

    doc.setTextColor(...PRIMARY);
    doc.setFontSize(9.5);
    doc.setFont('helvetica', 'bold');
    doc.text(`${cred.upstream_proxy_ip || 'N/A'}:${cred.upstream_proxy_port || ''}`, 20, innerY + 5);
    doc.text('HTTP / SOCKS5', W / 2 + 5, innerY + 5);

    doc.setDrawColor(...BORDER);
    doc.line(20, innerY + 8, W - 20, innerY + 8);
    innerY -= rowH;

    // Row 3: FULL FORMAT
    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('FULL FORMAT', 20, innerY);

    doc.setTextColor(...LIGHT);
    doc.setFontSize(7.5);
    doc.setFont('courier', 'normal');
    const fullStr = `http://${cred.styxproxy_username || 'user'}:${cred.styxproxy_password || 'pass'}@${cred.upstream_proxy_ip || '0.0.0.0'}:${cred.upstream_proxy_port || 8080}`;
    const lines = doc.splitTextToSize(fullStr, W - 40);
    doc.text(lines, 20, innerY + 5);

    doc.setDrawColor(...BORDER);
    doc.line(20, innerY + 8, W - 20, innerY + 8);
    innerY -= rowH;

    // Row 4: EXPIRES | AUTO-RENEW
    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('EXPIRES', 20, innerY);
    doc.text('AUTO-RENEW', W / 2 + 5, innerY);

    doc.setTextColor(...WHITE);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.text(cred.expires_at ? new Date(cred.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A', 20, innerY + 5);
    doc.text('On (manage to disable)', W / 2 + 5, innerY + 5);

    y = credCardBottom;
  }

  // ── Support section ─────────────────────────────────────
  const supY = y - 8;
  const supH = 18;
  doc.setFillColor(...CARD);
  doc.roundedRect(15, supY - supH, W - 30, supH, 3, 3, 'F');

  // Left: NEED HELP + Charon
  doc.setTextColor(...PRIMARY);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('NEED HELP?', 20, supY - 5);

  doc.setTextColor(...WHITE);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.text('Chat support:', 20, supY - 10);

  doc.setTextColor(...PRIMARY);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy.com/contact', 20, supY - 14.5);

  // Right: email + web
  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Email:', 90, supY - 5);
  doc.text('Web:', 90, supY - 10);

  doc.setTextColor(...WHITE);
  doc.setFontSize(8);
  doc.text('support@styxproxy.com', 100, supY - 5);

  doc.setTextColor(...PRIMARY);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy.com', 100, supY - 10);

  // ── Footer ──────────────────────────────────────────────
  const footerLine = 25;
  doc.setDrawColor(...BORDER);
  doc.line(15, footerLine, W - 15, footerLine);

  doc.setTextColor(...DIM);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'normal');
  doc.text('This receipt was generated automatically. No signature required.', W / 2, 20, { align: 'center' });
  doc.text('© 2026 Styxproxy — Anonymous proxy service for the discerning.', W / 2, 16, { align: 'center' });

  // ── Bottom accent bar ───────────────────────────────────
  doc.setFillColor(...PRIMARY);
  doc.rect(0, H - 3, W, 3, 'F');

  // Save
  doc.save(`styxproxy-receipt-${txRef}.pdf`);
}

function ThankYouContent() {
  const searchParams = useSearchParams();
  const txRef = searchParams.get('tx_ref');
  const { toast } = useToast();

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
          // Order fulfilled — clear in-flight lock so customer can buy again
          if (data.status === 'active') {
            import('@/lib/device-id').then(({ clearInflightOrder }) => clearInflightOrder());
          }
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
      await generateReceiptPDF(order, cart, txRef!, `styxproxy-receipt-${txRef}.pdf`);
    }
  };

  // Handle copy credentials to clipboard
  const handleCopyCredentials = async (cred?: OrderData['styxproxy_credential']) => {
    if (!cred) return;
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
              <h1 className="text-3xl font-bold text-[var(--primary)] mb-2">
                {order?.customer_name?.trim()
                  ? `Thank you, ${order.customer_name.trim()}.`
                  : 'Thank you, customer.'}
              </h1>
              <p className="text-[var(--muted)]">
                Your proxies are ready. Here are your credentials:
              </p>
            </div>

            {/* Credentials Card - Show all proxies from cart */}
            <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Proxy Credentials</h2>
                {order?.styxproxy_credential && (
                  <button
                    onClick={() => handleCopyCredentials(order?.styxproxy_credential)}
                    className="text-xs px-3 py-1.5 bg-[var(--primary)]/10 hover:bg-[var(--primary)]/20 text-[var(--primary)] border border-[var(--primary)]/30 rounded-lg transition-colors flex items-center gap-1.5"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                  </button>
                )}
              </div>

              {/* If we have credential from API, show it */}
              {order?.styxproxy_credential ? (
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
                  <div className="col-span-2">
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

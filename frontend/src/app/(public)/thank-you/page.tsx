
/* eslint-disable react-hooks/set-state-in-effect */

'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useToast } from '@/components/Toast';
import { Flag } from '@/components/ui/Flag';
import { generateReceiptPDF } from '@/lib/pdf-receipt';
import type { ReceiptOrder } from '@/lib/pdf-receipt';
import type { CartItem } from '@/types';
import { Check, Copy, Warning, XCircle, ArrowLineDown, WarningCircle } from '@phosphor-icons/react';

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
  fulfilled_at?: string;
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
    doc.text(`${item.country_code} ${item.name}`, 15, y);

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
  const [nextAction, setNextAction] = useState<string | null>(null);
  const [userMessage, setUserMessage] = useState<string | null>(null);
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
  // TWO STAGES: (1) resolve tx_ref → order_id, (2) poll /api/orders/{order_id}/status
  // The new endpoint (commit fd7559c) returns a unified next_action state machine
  // that drives the UI: pending/paid → poll, fulfilled/active → success.
  useEffect(() => {
    if (!txRef) {
      Promise.resolve().then(() => {
        setError(true);
        setLoading(false);
      });
      return;
    }

    let cancelled = false;
    let resolvedRef: string | null = null;

    const fetchOrderStatus = async () => {
      try {
        let oid = resolvedRef;
        if (!oid) {
          // Stage 1: resolve tx_ref → order_id
          const refRes = await fetch(`/api/orders/by-payment-reference/${txRef}`);
          if (cancelled) return;
          if (refRes.status === 404) {
            setAttempts(prev => prev + 1);
            return;
          }
          if (!refRes.ok) throw new Error(`HTTP ${refRes.status}`);
          const refData = await refRes.json();
          if (!refData.order_id) {
            setLoading(false);
            setError(true);
            return;
          }
          oid = refData.order_id;
          resolvedRef = oid;
        }

        // Stage 2: poll the new payment-status endpoint
        const res = await fetch(`/api/orders/${oid}/status`);
        if (cancelled) return;
        if (!res.ok) {
          if (res.status === 404) {
            setAttempts(prev => prev + 1);
            return;
          }
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (cancelled) return;

        // Map new endpoint response → existing UI OrderData shape
        const orderData: OrderData = {
          order_id: data.order_id,
          status: data.order_status,
          plan_type: data.plan_type,
          country: data.country,
          amount_paid_ngn: data.amount_paid_ngn,
          tx_ref: txRef || undefined,
          created_at: data.created_at,
          fulfilled_at: data.fulfilled_at || undefined,
          expires_at: data.expires_at || undefined,
          // Map credential from new endpoint shape to legacy shape
          styxproxy_credential: data.credential ? {
            styxproxy_username: data.credential.styxproxy_username,
            styxproxy_password: data.credential.styxproxy_password,
            upstream_proxy_ip: data.credential.proxy_host,
            upstream_proxy_port: data.credential.proxy_port_socks5,
            expires_at: data.expires_at || undefined,
          } : undefined,
        };
        setOrder(orderData);

        // Stop polling when next_action is terminal
        if (data.next_action && data.next_action !== 'poll') {
          setLoading(false);
          setNextAction(data.next_action);
          setUserMessage(data.user_message || null);
          if (data.next_action === 'redirect_to_proxy_details') {
            import('@/lib/device-id').then(({ clearInflightOrder }) => clearInflightOrder());
          }
          return;
        }
        setAttempts(prev => prev + 1);
      } catch {
        if (cancelled) return;
        setAttempts(prev => prev + 1);
      }
    };

    fetchOrderStatus();

    const interval = setInterval(() => {
      if (attempts >= maxAttempts) {
        setLoading(false);
        clearInterval(interval);
        return;
      }
      fetchOrderStatus();
    }, 3500);  // 3.5s — faster than the old 5s for snappier UX

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
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
  // Bug walk theme-B fix: add 'refunded' to terminal failure states. Auto-refund
  // (commit ec0fb07) sets order.status = "refunded" when provider exhausts 5 retries.
  const isErrorState =
    order?.status === 'expired' ||
    order?.status === 'cancelled' ||
    order?.status === 'refunded';
  
  // Detect failed payment states from next_action
  const isPaymentFailed = nextAction === 'show_failure' || nextAction === 'show_retry';
  const isRetryState = nextAction === 'show_retry';
  const isProviderDown = nextAction === 'provider_down';

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
                <Check className="w-8 h-8 text-[var(--primary)]" weight="bold" />
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
                    <Copy className="w-3.5 h-3.5" />
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
                        <Flag countryCode={item.country_code} size={20} />
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
                  <ArrowLineDown className="w-5 h-5" />
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

        {/* Provider Down State */}
        {!loading && isProviderDown && (
          <div className="text-center animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-orange-500/20 flex items-center justify-center">
              <Warning className="w-8 h-8 text-orange-500" weight="bold" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Provider Temporarily Unavailable</h1>
            <p className="text-[var(--muted)] mb-2">
              Our proxy provider is temporarily out of stock for your selected region.
            </p>
            {order?.user_message && (
              <p className="text-sm text-orange-400 mb-6">{order.user_message}</p>
            )}
            <p className="text-sm text-[var(--muted)] mb-6">
              Your payment was received. Your credentials are being generated — this usually takes a few minutes.
              Reference: <span className="font-mono">{txRef}</span>
            </p>
            <div className="space-y-3">
              <Link
                href={`/manage?ref=${txRef}`}
                className="block w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg text-center transition-colors"
              >
                Check Order Status
              </Link>
              <Link
                href="/order"
                className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
              >
                Browse Other Plans
              </Link>
            </div>
          </div>
        )}

        {/* Error/Expired State */}
        {/* Error State (expired / cancelled / refunded) */}
        {!loading && isErrorState && (
          <div className="text-center animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--error)]/20 flex items-center justify-center">
              <XCircle className="w-8 h-8 text-[var(--error)]" weight="bold" />
            </div>
            <h1 className="text-2xl font-bold mb-2">
              {order?.status === 'expired'
                ? 'Order Expired'
                : order?.status === 'refunded'
                  ? 'Order Refunded'
                  : 'Order Cancelled'}
            </h1>
            <p className="text-[var(--muted)] mb-6">
              {order?.status === 'refunded' ? (
                <>
                  Your order has been refunded. The provider could not deliver
                  a working proxy. Refund processing typically takes 5–10 minutes —
                  contact <a href="https://wa.me/2347032981049" className="text-[var(--primary)] hover:underline">support</a>
                  {' '}if you don&apos;t see it within 24 hours.
                </>
              ) : (
                'This order is no longer active.'
              )}
            </p>
            <Link
              href="/order"
              className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
            >
              Place New Order
            </Link>
          </div>
        )}

        {/* Payment Failed State (show_failure / show_retry) */}
        {!loading && isPaymentFailed && (
          <div className="animate-fade-in">
            {/* Red error banner for show_failure */}
            {nextAction === 'show_failure' && (
              <div className="mb-6 p-4 bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[var(--error)]/20 flex items-center justify-center flex-shrink-0">
                    <WarningCircle className="w-5 h-5 text-[var(--error)]" weight="bold" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-red-400">Payment could not be processed</h2>
                    <p className="text-sm text-[var(--muted)] mt-1">
                      {userMessage || 'There was an issue processing your payment. Please contact support if you were charged.'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Yellow warning banner for show_retry */}
            {nextAction === 'show_retry' && (
              <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                    <Warning className="w-5 h-5 text-yellow-500" weight="bold" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-yellow-400">Your order is still being processed</h2>
                    <p className="text-sm text-[var(--muted)] mt-1">
                      {userMessage || 'Please wait while we complete your order. This usually takes a few moments.'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Order reference */}
            <div className="text-center mb-6">
              <p className="text-sm text-[var(--muted)]">
                Reference: <span className="font-mono">{txRef}</span>
              </p>
              {order?.order_id && (
                <p className="text-sm text-[var(--muted)]">
                  Order ID: <span className="font-mono">{order.order_id}</span>
                </p>
              )}
            </div>

            {/* Action buttons */}
            <div className="space-y-3">
              <Link
                href="/order"
                className="block w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg text-center transition-colors"
              >
                Try Again
              </Link>
              <Link
                href="/contact"
                className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--error)]/50 text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
              >
                Contact Support
              </Link>
            </div>
          </div>
        )}

        {/* Timeout State */}
        {!loading && !order && attempts >= maxAttempts && (
          <div className="text-center animate-fade-in">
            <h1 className="text-2xl font-bold mb-2">Still Processing</h1>
            <p className="text-[var(--muted)] mb-2">
              Your order is still being processed. Your payment was
              received — credentials are being generated.
            </p>
            <p className="text-sm text-[var(--muted)] mb-6">
              Reference: <span className="font-mono">{txRef}</span>
            </p>
            <div className="space-y-3">
              <button
                onClick={() => {
                  setAttempts(0);
                  setOrder(undefined);
                  setNextAction('poll');
                }}
                className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
              >
                Retry Now
              </button>
              <Link
                href={`/manage?ref=${txRef}`}
                className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
              >
                Check Order Status
              </Link>
              <Link
                href="/order"
                className="block w-full px-6 py-3 text-[var(--muted)] hover:text-[var(--foreground)] text-center transition-colors"
              >
                Order Another
              </Link>
            </div>
            <p className="text-xs text-[var(--muted)] mt-4">
              Tip: paste your reference (STX-XXXXXX) in the search box on
              the next page. If it shows credentials, you can use them
              immediately.
            </p>
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

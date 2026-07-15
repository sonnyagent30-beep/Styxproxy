/**
 * Shared PDF receipt generator for Styxproxy.
 * Both /thank-you and /preview use this — one source of truth.
 */

interface CartItem {
  name: string;
  flag?: string;
  quantity: number;
  price_ngn: number;
}

interface Credential {
  bun_username?: string;
  bun_password?: string;
  upstream_proxy_ip?: string;
  upstream_proxy_port?: number;
  expires_at?: string;
}

export interface ReceiptOrder {
  order_id?: string;
  status?: string;
  customer_name?: string | null;
  bunche_credential?: Credential;
}

const PRIMARY: [number, number, number] = [10, 210, 90];   // #0AD25A
const BG: [number, number, number] = [10, 10, 10];          // #0a0a0a
const CARD: [number, number, number] = [26, 26, 26];        // #1a1a1a
const MUTED: [number, number, number] = [156, 163, 175];    // #9CA3AF
const DIM: [number, number, number] = [107, 114, 128];      // #6B7280
const WHITE: [number, number, number] = [255, 255, 255];
const LIGHT: [number, number, number] = [209, 213, 219];    // #D1D5DB
const BORDER: [number, number, number] = [38, 38, 38];      // #262626

export async function generateReceiptPDF(
  order: ReceiptOrder,
  cart: CartItem[],
  txRef: string,
  filename?: string,
) {
  const { jsPDF } = await import('jspdf');

  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();

  // ── Background ────────────────────────────────────────────
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
  doc.setFillColor(...CARD);
  doc.roundedRect(15, cardTop - 42, W - 30, 42, 3, 3, 'F');

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
  if (order?.bunche_credential) {
    const cred = order.bunche_credential;
    y += 18;

    doc.setTextColor(...PRIMARY);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.text('YOUR PROXY CREDENTIALS', 15, y);

    const cardH = 70;
    const credCardTop = y + 2;
    const credCardBottom = credCardTop - cardH;
    doc.setFillColor(...BG);
    doc.setDrawColor(...PRIMARY);
    doc.setLineWidth(0.6);
    doc.roundedRect(15, credCardBottom, W - 30, cardH, 3, 3, 'FD');
    doc.setDrawColor(...BORDER);
    doc.setLineWidth(0.2);

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
    doc.text(cred.bun_username || 'N/A', 20, innerY + 5);
    doc.text(cred.bun_password || 'N/A', W / 2 + 5, innerY + 5);

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
    const fullStr = `http://${cred.bun_username || 'user'}:${cred.bun_password || 'pass'}@${cred.upstream_proxy_ip || '0.0.0.0'}:${cred.upstream_proxy_port || 8080}`;
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

  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Email:', 90, supY - 5);
  doc.text('Web:', 90, supY - 10);

  doc.setTextColor(...WHITE);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('oyebiyiayomide30@gmail.com', 100, supY - 5);
  doc.text('styxproxy.com', 100, supY - 10);

  // ── Footer ─────────────────────────────────────────────
  doc.setTextColor(...DIM);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.text('This receipt was generated automatically. No signature required.', W / 2, H - 8, { align: 'center' });

  // ── Save ───────────────────────────────────────────────
  doc.save(filename || `styxproxy-receipt-${txRef}.pdf`);
}

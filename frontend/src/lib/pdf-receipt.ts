/**
 * Shared PDF receipt generator for Styxproxy.
 * Both /thank-you and /preview use this — one source of truth.
 *
 * Top-down Y math (no inverted drawing). Verified visually.
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

// Brand colors (RGB tuples for jsPDF)
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

  // ── Header ─────────────────────────────────────────────
  // Logo mark
  doc.setFillColor(...PRIMARY);
  doc.roundedRect(15, 14, 8, 8, 1.5, 1.5, 'F');
  doc.setTextColor(...BG);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'bold');
  doc.text('S', 19, 19, { align: 'center' });

  // Wordmark
  doc.setTextColor(...WHITE);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy', 26, 20);

  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Anonymous Proxy Service', 26, 24);

  // Right header: PAYMENT RECEIPT label
  doc.setTextColor(...PRIMARY);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.text('PAYMENT RECEIPT', W - 15, 17, { align: 'right' });

  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('styxproxy.com', W - 15, 21.5, { align: 'right' });
  doc.text(
    `Issued: ${new Date().toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })}`,
    W - 15,
    25,
    { align: 'right' }
  );

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

  // FULFILLED pill on the right (vertically centered with thank-you line at y=49)
  const status = order?.status?.toUpperCase() || 'PENDING';
  doc.setFillColor(...PRIMARY);
  doc.roundedRect(W - 50, 42, 35, 9, 4.5, 4.5, 'F');
  doc.setTextColor(...BG);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text(status, W - 32.5, 48, { align: 'center' });

  // ── Order details card ──────────────────────────────────
  // Card layout (top-down):
  //   y0: card top
  //   y0+10: section labels (TX REF | ORDER ID)
  //   y0+16: large values
  //   y0+20: small dim labels
  //   y0+24: divider
  //   y0+30: section labels (DATE | METHOD)
  //   y0+36: large values
  //   y0+40: card bottom
  const orderCardTop = 64;
  const orderCardBottom = 108;
  doc.setFillColor(...CARD);
  doc.roundedRect(15, orderCardTop, W - 30, orderCardBottom - orderCardTop, 3, 3, 'F');

  // Row 1: TX Ref | Order ID
  doc.setTextColor(...MUTED);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('TRANSACTION REFERENCE', 20, orderCardTop + 10);
  doc.text('ORDER ID', W / 2 + 5, orderCardTop + 10);

  doc.setTextColor(...WHITE);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text(txRef || 'N/A', 20, orderCardTop + 16);

  const orderIdDisplay = order?.order_id || 'N/A';
  doc.text(
    orderIdDisplay.length > 22 ? orderIdDisplay.slice(0, 22) + '…' : orderIdDisplay,
    W / 2 + 5,
    orderCardTop + 16
  );

  doc.setTextColor(...DIM);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'normal');
  doc.text('Flutterwave payment reference', 20, orderCardTop + 20);
  doc.text('Internal order reference', W / 2 + 5, orderCardTop + 20);

  // Divider
  doc.setDrawColor(...BORDER);
  doc.setLineWidth(0.2);
  doc.line(20, orderCardTop + 24, W - 20, orderCardTop + 24);

  // Row 2: DATE | METHOD
  doc.setTextColor(...MUTED);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('DATE', 20, orderCardTop + 30);
  doc.text('METHOD', W / 2 + 5, orderCardTop + 30);

  doc.setTextColor(...WHITE);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(
    new Date().toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' }),
    20,
    orderCardTop + 36
  );
  doc.text('Card / Bank / USSD / QR', W / 2 + 5, orderCardTop + 36);

  // ── Items section ───────────────────────────────────────
  let y = 120;
  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('ITEMS', 15, y);
  doc.text('QTY', W - 35, y, { align: 'right' });
  doc.text('AMOUNT', W - 15, y, { align: 'right' });

  doc.setDrawColor(...BORDER);
  doc.setLineWidth(0.2);
  doc.line(15, y + 2, W - 15, y + 2);

  y += 10;
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
    doc.setFont('helvetica', 'normal');
    doc.text(`${item.quantity} ${item.quantity === 1 ? 'unit' : 'units'}  |  HTTP/SOCKS5`, 15, y + 4);

    doc.setTextColor(...WHITE);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(String(item.quantity), W - 35, y, { align: 'right' });
    doc.text(`N${lineTotal.toLocaleString('en-NG')}`, W - 15, y, { align: 'right' });
    y += 14;
  });

  // ── TOTAL PAID pill ─────────────────────────────────────
  doc.setFillColor(...PRIMARY);
  doc.roundedRect(W - 75, y, 60, 11, 2, 2, 'F');
  doc.setTextColor(...BG);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('TOTAL PAID', W - 70, y + 7.5);
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text(`N${subtotal.toLocaleString('en-NG')}`, W - 19, y + 7.5, { align: 'right' });

  // ── Credentials card (if available) ─────────────────────
  if (order?.bunche_credential) {
    const cred = order.bunche_credential;
    y += 22; // breathing room after total pill

    // Section label
    doc.setTextColor(...PRIMARY);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.text('YOUR PROXY CREDENTIALS', 15, y);

    // Card (top-down y math)
    const cardH = 80;
    const cardTop = y + 5;
    const cardBottom = cardTop + cardH;
    doc.setFillColor(...BG);
    doc.setDrawColor(...PRIMARY);
    doc.setLineWidth(0.6);
    doc.roundedRect(15, cardTop, W - 30, cardH, 3, 3, 'FD');
    doc.setDrawColor(...BORDER);
    doc.setLineWidth(0.2);

    // Layout: each row 16mm tall
    //   label at rowTop+5
    //   value at rowTop+12
    //   divider at rowTop+15
    const rowH = 16;
    let rowTop = cardTop + 5;

    // Row 1: USERNAME | PASSWORD
    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('USERNAME', 20, rowTop + 3);
    doc.text('PASSWORD', W / 2 + 5, rowTop + 3);

    doc.setTextColor(...PRIMARY);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text(cred.bun_username || 'N/A', 20, rowTop + 10);
    doc.text(cred.bun_password || 'N/A', W / 2 + 5, rowTop + 10);

    doc.setDrawColor(...BORDER);
    doc.line(20, rowTop + 13, W - 20, rowTop + 13);
    rowTop += rowH;

    // Row 2: PROXY ADDRESS | PROTOCOL
    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('PROXY ADDRESS', 20, rowTop + 3);
    doc.text('PROTOCOL', W / 2 + 5, rowTop + 3);

    doc.setTextColor(...PRIMARY);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text(`${cred.upstream_proxy_ip || 'N/A'}:${cred.upstream_proxy_port || ''}`, 20, rowTop + 10);
    doc.text('HTTP / SOCKS5', W / 2 + 5, rowTop + 10);

    doc.setDrawColor(...BORDER);
    doc.line(20, rowTop + 13, W - 20, rowTop + 13);
    rowTop += rowH;

    // Row 3: FULL FORMAT (full-width)
    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('FULL FORMAT', 20, rowTop + 3);

    doc.setTextColor(...LIGHT);
    doc.setFontSize(7.5);
    doc.setFont('courier', 'normal');
    const fullStr = `http://${cred.bun_username || 'user'}:${cred.bun_password || 'pass'}@${cred.upstream_proxy_ip || '0.0.0.0'}:${cred.upstream_proxy_port || 8080}`;
    const lines = doc.splitTextToSize(fullStr, W - 40);
    doc.text(lines, 20, rowTop + 10);

    doc.setDrawColor(...BORDER);
    doc.line(20, rowTop + 13, W - 20, rowTop + 13);
    rowTop += rowH;

    // Row 4: EXPIRES | AUTO-RENEW
    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('EXPIRES', 20, rowTop + 3);
    doc.text('AUTO-RENEW', W / 2 + 5, rowTop + 3);

    doc.setTextColor(...WHITE);
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(
      cred.expires_at
        ? new Date(cred.expires_at).toLocaleDateString('en-NG', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })
        : 'N/A',
      20,
      rowTop + 10
    );
    doc.text('On (manage to disable)', W / 2 + 5, rowTop + 10);

    y = cardBottom;
  }

  // ── Support section ─────────────────────────────────────
  y += 14; // breathing room after credentials
  const supH = 22;
  const supTop = y;
  doc.setFillColor(...CARD);
  doc.roundedRect(15, supTop, W - 30, supH, 3, 3, 'F');

  // Left column
  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('NEED HELP?', 20, supTop + 6);

  doc.setTextColor(...WHITE);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.text('Chat support:', 20, supTop + 12);

  doc.setTextColor(...PRIMARY);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy.com/contact', 20, supTop + 18);

  // Right column
  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Email:', 95, supTop + 12);
  doc.text('Web:', 95, supTop + 18);

  doc.setTextColor(...WHITE);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('oyebiyiayomide30@gmail.com', 105, supTop + 12);
  doc.text('styxproxy.com', 105, supTop + 18);

  y = supTop + supH;

  // ── Footer ─────────────────────────────────────────────
  doc.setTextColor(...DIM);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.text(
    'This receipt was generated automatically. No signature required.',
    W / 2,
    H - 8,
    { align: 'center' }
  );

  // ── Save ───────────────────────────────────────────────
  doc.save(filename || `styxproxy-receipt-${txRef}.pdf`);
}
/**
 * Shared PDF receipt generator for Styxproxy.
 * Both /thank-you and /preview use this — one source of truth.
 * jsPDF uses standard screen coords: y=0 is top, y increases going DOWN.
 */

interface CartItem {
  name: string;
  flag?: string;
  quantity: number;
  price_ngn: number;
}

interface Credential {
  styxproxy_username?: string;
  styxproxy_password?: string;
  upstream_proxy_ip?: string;
  upstream_proxy_port?: number;
  expires_at?: string;
}

export interface ReceiptOrder {
  order_id?: string;
  status?: string;
  customer_name?: string | null;
  styxproxy_credential?: Credential;
}

interface BrandColors {
  primary: [number, number, number];
  bg: [number, number, number];
  card: [number, number, number];
  muted: [number, number, number];
  dim: [number, number, number];
  foreground: [number, number, number];
  border: [number, number, number];
  light: [number, number, number];
}

// Dark theme (default — for screen viewing)
const DARK_COLORS: BrandColors = {
  primary: [10, 210, 90],
  bg: [10, 10, 10],
  card: [26, 26, 26],
  muted: [156, 163, 175],
  dim: [107, 114, 128],
  foreground: [255, 255, 255],
  border: [38, 38, 38],
  light: [209, 213, 219],
};

// Light theme (for printing on white paper)
const LIGHT_COLORS: BrandColors = {
  primary: [5, 150, 105],
  bg: [255, 255, 255],
  card: [249, 250, 251],
  muted: [107, 114, 128],
  dim: [156, 163, 175],
  foreground: [15, 15, 15],
  border: [229, 231, 235],
  light: [75, 85, 99],
};

export type ReceiptTheme = 'dark' | 'light';

export async function generateReceiptPDF(
  order: ReceiptOrder,
  cart: CartItem[],
  txRef: string,
  filename?: string,
  theme: ReceiptTheme = 'dark',
) {
  const { jsPDF } = await import('jspdf');
  const colors = theme === 'light' ? LIGHT_COLORS : DARK_COLORS;

  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const W = doc.internal.pageSize.getWidth();  // 210mm
  const H = doc.internal.pageSize.getHeight(); // 297mm

  // ── Background ────────────────────────────────────────────
  doc.setFillColor(...colors.bg);
  doc.rect(0, 0, W, H, 'F');

  // ── Top accent bar ─────────────────────────────────────
  doc.setFillColor(...colors.primary);
  doc.rect(0, 0, W, 4, 'F');

  // ── Header ─────────────────────────────────────────────
  // Logo mark (green S-box)
  doc.setFillColor(...colors.primary);
  doc.roundedRect(15, 14, 8, 8, 1.5, 1.5, 'F');
  doc.setTextColor(...colors.bg);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'bold');
  doc.text('S', 19, 19, { align: 'center' });

  // Wordmark
  doc.setTextColor(...colors.foreground);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy', 26, 20);

  doc.setTextColor(...colors.muted);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Anonymous Proxy Service', 26, 24);

  // Right header: PAYMENT RECEIPT
  doc.setTextColor(...colors.primary);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.text('PAYMENT RECEIPT', W - 15, 17, { align: 'right' });

  doc.setTextColor(...colors.muted);
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
  const dividerY = 32;
  doc.setDrawColor(...colors.border);
  doc.setLineWidth(0.2);
  doc.line(15, dividerY, W - 15, dividerY);

  // ── ORDER CONFIRMATION ─────────────────────────────────
  // "ORDER CONFIRMATION" label at y=39
  const labelY = 39;
  doc.setTextColor(...colors.muted);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('ORDER CONFIRMATION', 15, labelY);

  // "Thank you, Dannion." at y=49
  const customerName = order?.customer_name?.trim();
  const thankYouText = customerName ? `Thank you, ${customerName}.` : 'Thank you, customer.';
  doc.setTextColor(...colors.foreground);
  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text(thankYouText, 15, 49);

  // Subtitle at y=56
  doc.setTextColor(...colors.muted);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('Your proxy is ready to use. Below are your credentials.', 15, 56);

  // FULFILLED pill
  const status = order?.status?.toUpperCase() || 'PENDING';
  doc.setFillColor(...colors.primary);
  doc.roundedRect(W - 50, 48, 35, 9, 4.5, 4.5, 'F');
  doc.setTextColor(...colors.bg);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text(status, W - 32.5, 53.5, { align: 'center' });

  // ── Order details card ──────────────────────────────────
  const cardTop = 64;
  const cardH = 44;
  doc.setFillColor(...colors.card);
  doc.roundedRect(15, cardTop, W - 30, cardH, 3, 3, 'F');

  // Row 1: TX REF | ORDER ID labels
  doc.setTextColor(...colors.muted);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('TRANSACTION REFERENCE', 20, cardTop + 10);
  doc.text('ORDER ID', W / 2 + 5, cardTop + 10);

  // Row 1: values
  doc.setTextColor(...colors.foreground);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text(txRef || 'N/A', 20, cardTop + 16);
  const orderIdDisplay = order?.order_id || 'N/A';
  doc.text(
    orderIdDisplay.length > 22 ? orderIdDisplay.slice(0, 22) + '…' : orderIdDisplay,
    W / 2 + 5,
    cardTop + 16
  );

  // Row 1: dim labels
  doc.setTextColor(...colors.dim);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'normal');
  doc.text('Flutterwave payment reference', 20, cardTop + 20);
  doc.text('Internal order reference', W / 2 + 5, cardTop + 20);

  // Divider
  doc.setDrawColor(...colors.border);
  doc.setLineWidth(0.2);
  doc.line(20, cardTop + 24, W - 20, cardTop + 24);

  // Row 2: DATE | METHOD labels
  doc.setTextColor(...colors.muted);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('DATE', 20, cardTop + 30);
  doc.text('METHOD', W / 2 + 5, cardTop + 30);

  // Row 2: values
  doc.setTextColor(...colors.foreground);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(
    new Date().toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' }),
    20,
    cardTop + 36
  );
  doc.text('Card / Bank / USSD / QR', W / 2 + 5, cardTop + 36);

  // ── Items section ───────────────────────────────────────
  const itemsY = cardTop + cardH + 14;
  doc.setTextColor(...colors.muted);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('ITEMS', 15, itemsY);
  doc.text('QTY', W - 35, itemsY, { align: 'right' });
  doc.text('AMOUNT', W - 15, itemsY, { align: 'right' });

  doc.setDrawColor(...colors.border);
  doc.line(15, itemsY + 2, W - 15, itemsY + 2);

  let itemY = itemsY + 10;
  let subtotal = 0;

  cart.forEach((item) => {
    const lineTotal = item.price_ngn * item.quantity;
    subtotal += lineTotal;

    doc.setTextColor(...colors.foreground);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`${item.flag || ''} ${item.name}`, 15, itemY);

    doc.setTextColor(...colors.muted);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'normal');
    doc.text(`${item.quantity} ${item.quantity === 1 ? 'unit' : 'units'}  |  HTTP/SOCKS5`, 15, itemY + 4);

    doc.setTextColor(...colors.foreground);
    doc.setFontSize(10);
    doc.text(String(item.quantity), W - 35, itemY, { align: 'right' });
    doc.text(`N${lineTotal.toLocaleString('en-NG')}`, W - 15, itemY, { align: 'right' });
    itemY += 14;
  });

  // ── TOTAL PAID pill ─────────────────────────────────────
  const totalY = itemY + 2;
  doc.setFillColor(...colors.primary);
  doc.roundedRect(W - 75, totalY, 60, 11, 2, 2, 'F');
  doc.setTextColor(...colors.bg);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('TOTAL PAID', W - 70, totalY + 7.5);
  doc.setFontSize(11);
  doc.text(`N${subtotal.toLocaleString('en-NG')}`, W - 19, totalY + 7.5, { align: 'right' });

  // ── Credentials card (if available) ─────────────────────
  if (order?.styxproxy_credential) {
    const cred = order.styxproxy_credential;
    const credSectionY = totalY + 16;

    doc.setTextColor(...colors.primary);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.text('YOUR PROXY CREDENTIALS', 15, credSectionY);

    const credCardTop = credSectionY + 5;
    const credCardH = 80;
    const credCardBottom = credCardTop + credCardH;

    doc.setFillColor(...colors.bg);
    doc.setDrawColor(...colors.primary);
    doc.setLineWidth(0.6);
    doc.roundedRect(15, credCardTop, W - 30, credCardH, 3, 3, 'FD');
    doc.setDrawColor(...colors.border);
    doc.setLineWidth(0.2);

    const rowH = 16;
    let rowTop = credCardTop + 5;

    // Row 1: USERNAME | PASSWORD
    doc.setTextColor(...colors.muted);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('USERNAME', 20, rowTop + 3);
    doc.text('PASSWORD', W / 2 + 5, rowTop + 3);
    doc.setTextColor(...colors.primary);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text(cred.styxproxy_username || 'N/A', 20, rowTop + 10);
    doc.text(cred.styxproxy_password || 'N/A', W / 2 + 5, rowTop + 10);
    doc.setDrawColor(...colors.border);
    doc.line(20, rowTop + 13, W - 20, rowTop + 13);
    rowTop += rowH;

    // Row 2: PROXY ADDRESS | PROTOCOL
    doc.setTextColor(...colors.muted);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('PROXY ADDRESS', 20, rowTop + 3);
    doc.text('PROTOCOL', W / 2 + 5, rowTop + 3);
    doc.setTextColor(...colors.primary);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text(`${cred.upstream_proxy_ip || 'N/A'}:${cred.upstream_proxy_port || ''}`, 20, rowTop + 10);
    doc.text('HTTP / SOCKS5', W / 2 + 5, rowTop + 10);
    doc.setDrawColor(...colors.border);
    doc.line(20, rowTop + 13, W - 20, rowTop + 13);
    rowTop += rowH;

    // Row 3: FULL FORMAT (full width)
    doc.setTextColor(...colors.muted);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('FULL FORMAT', 20, rowTop + 3);
    doc.setTextColor(...colors.light);
    doc.setFontSize(7.5);
    doc.setFont('courier', 'normal');
    const fullStr = `http://${cred.styxproxy_username || 'user'}:${cred.styxproxy_password || 'pass'}@${cred.upstream_proxy_ip || '0.0.0.0'}:${cred.upstream_proxy_port || 8080}`;
    const lines = doc.splitTextToSize(fullStr, W - 40);
    doc.text(lines, 20, rowTop + 10);
    doc.setDrawColor(...colors.border);
    doc.line(20, rowTop + 13, W - 20, rowTop + 13);
    rowTop += rowH;

    // Row 4: EXPIRES | AUTO-RENEW
    doc.setTextColor(...colors.muted);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('EXPIRES', 20, rowTop + 3);
    doc.text('AUTO-RENEW', W / 2 + 5, rowTop + 3);
    doc.setTextColor(...colors.foreground);
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(
      cred.expires_at
        ? new Date(cred.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })
        : 'N/A',
      20,
      rowTop + 10
    );
    doc.text('On (manage to disable)', W / 2 + 5, rowTop + 10);

    const supY = credCardBottom + 16;
    drawSupportSection(doc, supY, W, colors);
  } else {
    const supY = totalY + 16;
    drawSupportSection(doc, supY, W, colors);
  }

  // ── Footer ─────────────────────────────────────────────
  doc.setTextColor(...colors.dim);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.text('This receipt was generated automatically. No signature required.', W / 2, H - 8, { align: 'center' });

  // ── Save ───────────────────────────────────────────────
  doc.save(filename || `styxproxy-receipt-${txRef}.pdf`);
}

function drawSupportSection(doc: InstanceType<typeof import('jspdf')['jsPDF']>, supY: number, W: number, colors: BrandColors) {
  const supH = 22;
  const supTop = supY;
  doc.setFillColor(...colors.card);
  doc.roundedRect(15, supTop, W - 30, supH, 3, 3, 'F');

  // Left column
  doc.setTextColor(...colors.muted);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('NEED HELP?', 20, supTop + 6);
  doc.setTextColor(...colors.foreground);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.text('Chat support:', 20, supTop + 12);
  doc.setTextColor(...colors.primary);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy.com/contact', 20, supTop + 18);

  // Right column
  doc.setTextColor(...colors.muted);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Email:', 95, supTop + 12);
  doc.text('Web:', 95, supTop + 18);
  doc.setTextColor(...colors.foreground);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('oyebiyiayomide30@gmail.com', 105, supTop + 12);
  doc.text('styxproxy.com', 105, supTop + 18);
}

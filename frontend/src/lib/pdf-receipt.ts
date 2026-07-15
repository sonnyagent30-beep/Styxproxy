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

// Brand colors
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
  const W = doc.internal.pageSize.getWidth();  // 210mm
  const H = doc.internal.pageSize.getHeight(); // 297mm

  // ── Background ────────────────────────────────────────────
  doc.setFillColor(...BG);
  doc.rect(0, 0, W, H, 'F');

  // ── Top accent bar ─────────────────────────────────────
  doc.setFillColor(...PRIMARY);
  doc.rect(0, 0, W, 4, 'F');

  // ── Header ─────────────────────────────────────────────
  // Logo mark (green S-box)
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

  // Right header: PAYMENT RECEIPT
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
  const dividerY = 32;
  doc.setDrawColor(...BORDER);
  doc.setLineWidth(0.2);
  doc.line(15, dividerY, W - 15, dividerY);

  // ── ORDER CONFIRMATION ─────────────────────────────────
  // "ORDER CONFIRMATION" label at y=39
  const labelY = 39;
  doc.setTextColor(...MUTED);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('ORDER CONFIRMATION', 15, labelY);

  // "Thank you, Dannion." at y=49
  const customerName = order?.customer_name?.trim();
  const thankYouText = customerName ? `Thank you, ${customerName}.` : 'Thank you, customer.';
  doc.setTextColor(...WHITE);
  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text(thankYouText, 15, 49);

  // Subtitle at y=56
  doc.setTextColor(...MUTED);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('Your proxy is ready to use. Below are your credentials.', 15, 56);

  // FULFILLED pill — vertically centered with thank-you text (thank-you is at y=49, subtitle at y=56)
  // Center of that range = 52.5. Pill height=9, so top at 52.5-4.5=48, bottom at 57
  const status = order?.status?.toUpperCase() || 'PENDING';
  doc.setFillColor(...PRIMARY);
  doc.roundedRect(W - 50, 48, 35, 9, 4.5, 4.5, 'F');
  doc.setTextColor(...BG);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text(status, W - 32.5, 53.5, { align: 'center' });

  // ── Order details card ──────────────────────────────────
  // Card top at y=64, height 44mm → bottom at y=108
  const cardTop = 64;
  const cardH = 44;
  doc.setFillColor(...CARD);
  doc.roundedRect(15, cardTop, W - 30, cardH, 3, 3, 'F');

  // Row 1: TX REF | ORDER ID labels at cardTop+10=74
  doc.setTextColor(...MUTED);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('TRANSACTION REFERENCE', 20, cardTop + 10);
  doc.text('ORDER ID', W / 2 + 5, cardTop + 10);

  // Row 1: values at cardTop+16=80
  doc.setTextColor(...WHITE);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text(txRef || 'N/A', 20, cardTop + 16);
  const orderIdDisplay = order?.order_id || 'N/A';
  doc.text(
    orderIdDisplay.length > 22 ? orderIdDisplay.slice(0, 22) + '…' : orderIdDisplay,
    W / 2 + 5,
    cardTop + 16
  );

  // Row 1: dim labels at cardTop+20=84
  doc.setTextColor(...DIM);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'normal');
  doc.text('Flutterwave payment reference', 20, cardTop + 20);
  doc.text('Internal order reference', W / 2 + 5, cardTop + 20);

  // Divider at cardTop+24=88
  doc.setDrawColor(...BORDER);
  doc.setLineWidth(0.2);
  doc.line(20, cardTop + 24, W - 20, cardTop + 24);

  // Row 2: DATE | METHOD labels at cardTop+30=94
  doc.setTextColor(...MUTED);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.text('DATE', 20, cardTop + 30);
  doc.text('METHOD', W / 2 + 5, cardTop + 30);

  // Row 2: values at cardTop+36=100
  doc.setTextColor(...WHITE);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(
    new Date().toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' }),
    20,
    cardTop + 36
  );
  doc.text('Card / Bank / USSD / QR', W / 2 + 5, cardTop + 36);

  // Card bottom = cardTop + cardH = 108
  // Items section starts at cardBottom + 14 = 122
  const itemsY = cardTop + cardH + 14; // = 122

  // ── Items section ───────────────────────────────────────
  doc.setTextColor(...MUTED);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('ITEMS', 15, itemsY);
  doc.text('QTY', W - 35, itemsY, { align: 'right' });
  doc.text('AMOUNT', W - 15, itemsY, { align: 'right' });

  doc.setDrawColor(...BORDER);
  doc.line(15, itemsY + 2, W - 15, itemsY + 2);

  let itemY = itemsY + 10;
  let subtotal = 0;

  cart.forEach((item) => {
    const lineTotal = item.price_ngn * item.quantity;
    subtotal += lineTotal;

    doc.setTextColor(...WHITE);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`${item.flag || ''} ${item.name}`, 15, itemY);

    doc.setTextColor(...MUTED);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'normal');
    doc.text(`${item.quantity} ${item.quantity === 1 ? 'unit' : 'units'}  |  HTTP/SOCKS5`, 15, itemY + 4);

    doc.setTextColor(...WHITE);
    doc.setFontSize(10);
    doc.text(String(item.quantity), W - 35, itemY, { align: 'right' });
    doc.text(`N${lineTotal.toLocaleString('en-NG')}`, W - 15, itemY, { align: 'right' });
    itemY += 14;
  });

  // ── TOTAL PAID pill ─────────────────────────────────────
  const totalY = itemY + 2;
  doc.setFillColor(...PRIMARY);
  doc.roundedRect(W - 75, totalY, 60, 11, 2, 2, 'F');
  doc.setTextColor(...BG);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('TOTAL PAID', W - 70, totalY + 7.5);
  doc.setFontSize(11);
  doc.text(`N${subtotal.toLocaleString('en-NG')}`, W - 19, totalY + 7.5, { align: 'right' });

  // ── Credentials card (if available) ─────────────────────
  if (order?.bunche_credential) {
    const cred = order.bunche_credential;
    const credSectionY = totalY + 16; // = totalY + 16mm gap

    // Section label
    doc.setTextColor(...PRIMARY);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.text('YOUR PROXY CREDENTIALS', 15, credSectionY);

    // Card top = credSectionY + 5, height 80mm → bottom at credSectionY - 75
    const credCardTop = credSectionY + 5;
    const credCardH = 80;
    const credCardBottom = credCardTop + credCardH;

    doc.setFillColor(...BG);
    doc.setDrawColor(...PRIMARY);
    doc.setLineWidth(0.6);
    doc.roundedRect(15, credCardTop, W - 30, credCardH, 3, 3, 'FD');
    doc.setDrawColor(...BORDER);
    doc.setLineWidth(0.2);

    // Row layout: each row 16mm, label at rowTop+3, value at rowTop+10, divider at rowTop+13
    const rowH = 16;
    let rowTop = credCardTop + 5;  // first row top

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

    // Row 3: FULL FORMAT (full width)
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
        ? new Date(cred.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })
        : 'N/A',
      20,
      rowTop + 10
    );
    doc.text('On (manage to disable)', W / 2 + 5, rowTop + 10);

    // Support section starts 16mm below credentials card bottom
    const supY = credCardBottom + 16;
    drawSupportSection(doc, supY, W);

  } else {
    const supY = totalY + 16;
    drawSupportSection(doc, supY, W);
  }

  // ── Footer ─────────────────────────────────────────────
  doc.setTextColor(...DIM);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.text('This receipt was generated automatically. No signature required.', W / 2, H - 8, { align: 'center' });

  // ── Save ───────────────────────────────────────────────
  doc.save(filename || `styxproxy-receipt-${txRef}.pdf`);
}

function drawSupportSection(doc: InstanceType<typeof import('jspdf')['jsPDF']>, supY: number, W: number) {
  const supH = 22;
  const supTop = supY;
  doc.setFillColor(26, 26, 26);
  doc.roundedRect(15, supTop, W - 30, supH, 3, 3, 'F');

  // Left column
  doc.setTextColor(156, 163, 175);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('NEED HELP?', 20, supTop + 6);
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.text('Chat support:', 20, supTop + 12);
  doc.setTextColor(10, 210, 90);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('styxproxy.com/contact', 20, supTop + 18);

  // Right column
  doc.setTextColor(156, 163, 175);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Email:', 95, supTop + 12);
  doc.text('Web:', 95, supTop + 18);
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('oyebiyiayomide30@gmail.com', 105, supTop + 12);
  doc.text('styxproxy.com', 105, supTop + 18);
}
/**
 * Shared PDF receipt generator for Styxproxy.
 * Both /thank-you and /receipt use this — one source of truth.
 * jsPDF uses standard screen coords: y=0 is top, y increases going DOWN.
 */

interface CartItem {
  name: string;
  flag?: string;
  quantity: number;
  price_ngn: number;
}

interface Credential {
  // The PUBLIC receipt endpoint discloses credential STATUS only — no username,
  // password, IP or port. Those are delivered by email / authenticated lookup.
  // See ReceiptCredentialPublic in backend/app/routers/schemas.py.
  status?: string;
}

export interface ReceiptOrder {
  order_id?: string;
  status?: string;
  customer_name?: string | null;
  created_at?: string;
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

/** Which brand lockup to embed. `header-logo-dark.png` carries a WHITE
 *  wordmark (for dark surfaces); `header-logo-light.png` a near-black one. */
export const LOGO_URL: Record<ReceiptTheme, string> = {
  dark: '/header-logo-dark.png',
  light: '/header-logo-light.png',
};

/** Device colour-scheme detection for the PDF theme.
 *
 *  Both call sites (/receipt/[tx_ref] and /thank-you) previously omitted the
 *  theme argument entirely, so every receipt rendered dark on white paper.
 *  SSR-safe: returns `dark` when matchMedia is unavailable. */
export function detectReceiptTheme(): ReceiptTheme {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

/** Fetch the brand lockup as a data URL.
 *
 *  jsPDF cannot load a URL, so the PNG is inlined. Cached per theme: the
 *  receipt is downloadable repeatedly and we should not refetch the asset
 *  (or re-base64 a 12KB image) on every click.
 *
 *  Returns null on any failure — the caller keeps its drawn wordmark rather
 *  than emitting a broken/blank image, so a missing asset degrades instead
 *  of corrupting the receipt. */
const _logoCache = new Map<ReceiptTheme, Promise<string | null>>();

export function loadLogoDataUrl(theme: ReceiptTheme): Promise<string | null> {
  const hit = _logoCache.get(theme);
  if (hit) return hit;
  const p = (async () => {
    try {
      const res = await fetch(LOGO_URL[theme]);
      if (!res.ok) return null;
      const blob = await res.blob();
      return await new Promise<string>((resolve, reject) => {
        const fr = new FileReader();
        fr.onload = () => resolve(String(fr.result));
        fr.onerror = () => reject(fr.error);
        fr.readAsDataURL(blob);
      });
    } catch {
      return null;
    }
  })();
  _logoCache.set(theme, p);
  return p;
}

export async function generateReceiptPDF(
  order: ReceiptOrder,
  cart: CartItem[],
  txRef: string,
  filename?: string,
  theme: ReceiptTheme = 'dark',
) {
  const { jsPDF } = await import('jspdf');
  const colors = theme === 'light' ? LIGHT_COLORS : DARK_COLORS;
  const logoDataUrl = await loadLogoDataUrl(theme);

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
  // Brand lockup. The PNG is inlined as a data URL because jsPDF cannot fetch
  // a URL. Fall back to the drawn mark only if the asset failed to load, so a
  // missing file degrades to the old placeholder instead of a blank header.
  if (logoDataUrl) {
    // header-logo-*.png is 181x64 → aspect 2.828. Derive height from width so
    // the lockup is never squashed (the email header shipped a 17% squash by
    // hard-coding a height that disagreed with the source aspect).
    const LOGO_W = 30;                       // mm
    const LOGO_H = LOGO_W * (64 / 181);      // ≈ 10.6mm
    doc.addImage(logoDataUrl, 'PNG', 15, 12.5, LOGO_W, LOGO_H);
  } else {
    // Logo mark (green S-box) — degraded fallback
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
  }

  doc.setTextColor(...colors.muted);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('Anonymous Proxy Service', 15, 26);

  // Right header: PAYMENT RECEIPT
  doc.setTextColor(...colors.primary);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.text('PAYMENT RECEIPT', W - 15, 17, { align: 'right' });

  doc.setTextColor(...colors.muted);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.text('styxproxy.com', W - 15, 21.5, { align: 'right' });
  const orderDate = order?.created_at
    ? new Date(order.created_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })
    : new Date().toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' });
  doc.text(
    `Issued: ${orderDate}`,
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
  doc.text('Your proxy is ready to use.', 15, 56);

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
  doc.text('Payment reference', 20, cardTop + 20);
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
  doc.text(orderDate, 20, cardTop + 36);
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
    doc.text(`NGN ${lineTotal.toLocaleString('en-NG')}`, W - 15, itemY, { align: 'right' });
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
  doc.text(`NGN ${subtotal.toLocaleString('en-NG')}`, W - 19, totalY + 7.5, { align: 'right' });

  // ── Credential status card (if available) ─────────────────────
  // Deliberately does NOT print username / password / IP / port. The public
  // receipt endpoint returns status only — see ReceiptCredentialPublic. A PDF is
  // emailed, forwarded and stored; it must not become a credential artefact.
  if (order?.styxproxy_credential) {
    const cred = order.styxproxy_credential;
    const credSectionY = totalY + 16;

    doc.setTextColor(...colors.primary);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.text('PROXY ACCESS', 15, credSectionY);

    const credCardTop = credSectionY + 5;
    const credCardH = 42;
    const credCardBottom = credCardTop + credCardH;

    doc.setFillColor(...colors.bg);
    doc.setDrawColor(...colors.primary);
    doc.setLineWidth(0.6);
    doc.roundedRect(15, credCardTop, W - 30, credCardH, 3, 3, 'FD');
    doc.setDrawColor(...colors.border);
    doc.setLineWidth(0.2);

    const rowTop = credCardTop + 6;

    doc.setTextColor(...colors.muted);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('CREDENTIAL STATUS', 20, rowTop + 3);
    doc.setTextColor(...colors.primary);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text(String(cred.status || 'active').toUpperCase(), 20, rowTop + 12);

    doc.setTextColor(...colors.muted);
    doc.setFontSize(6);
    doc.setFont('helvetica', 'normal');
    const note = 'Your credentials were delivered separately.';
    const noteLines = doc.splitTextToSize(note, W - 40);
    doc.text(noteLines, 20, rowTop + 21);

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
  doc.text('support@styxproxy.com', 105, supTop + 12);
  doc.text('styxproxy.com', 105, supTop + 18);
}

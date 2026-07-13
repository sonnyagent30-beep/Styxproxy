import { readFileSync } from 'fs';
import { jsPDF } from 'jspdf';

const doc = new jsPDF({ unit: 'mm', format: 'a4' });
const W = doc.internal.pageSize.getWidth();
const H = doc.internal.pageSize.getHeight();

// Read logo as base64
const logoPath = new URL('./public/header-icon.png', import.meta.url);
const logoBase64 = readFileSync(logoPath).toString('base64');

doc.setFillColor(15, 15, 15);
doc.rect(0, 0, W, H, 'F');

doc.setFillColor(16, 185, 129);
doc.rect(0, 0, W, 6, 'F');

// Add actual logo image
doc.addImage(`data:image/png;base64,${logoBase64}`, 'PNG', 20, 18, 12, 12);

// Brand name
doc.setTextColor(245, 245, 245);
doc.setFontSize(18);
doc.setFont('helvetica', 'bold');
doc.text('styxproxy', 35, 25);
doc.setTextColor(115, 115, 115);
doc.setFontSize(9);
doc.setFont('helvetica', 'normal');
doc.text('Anonymous Proxy Service', 35, 30.5);

doc.setTextColor(16, 185, 129);
doc.setFontSize(8);
doc.setFont('helvetica', 'bold');
doc.text('PAYMENT RECEIPT', W - 20, 22, { align: 'right' });
doc.setTextColor(115, 115, 115);
doc.setFontSize(8);
doc.text('styxproxy.com', W - 20, 27, { align: 'right' });

doc.setDrawColor(42, 42, 42);
doc.setLineWidth(0.5);
doc.line(20, 40, W - 20, 40);

let y = 52;
doc.setFillColor(26, 26, 26);
doc.roundedRect(20, y - 6, W - 40, 22, 3, 3, 'F');

doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'bold');
doc.text('TRANSACTION REFERENCE', 25, y);
doc.text('ORDER ID', W / 2 + 5, y);
doc.setTextColor(245, 245, 245);
doc.setFontSize(10);
doc.setFont('helvetica', 'bold');
doc.text('TXF-DANNION-PREVIEW', 25, y + 8);
doc.text('ORD-2025-XXXXX', W / 2 + 5, y + 8);
doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'normal');
doc.text('Flutterwave', 25, y + 14);
doc.text('Internal', W / 2 + 5, y + 14);

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
doc.setTextColor(16, 185, 129);
doc.setFont('helvetica', 'bold');
doc.text('FULFILLED', W / 2 + 5, y + 7);

doc.setDrawColor(42, 42, 42);
doc.line(20, 98, W - 20, 98);

y = 106;
doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'bold');
doc.text('ITEM', 25, y);
doc.text('QTY', W - 48, y, { align: 'right' });
doc.text('AMOUNT', W - 20, y, { align: 'right' });
doc.setDrawColor(42, 42, 42);
doc.line(20, y + 3, W - 20, y + 3);

y += 10;
doc.setTextColor(245, 245, 245);
doc.setFontSize(9);
doc.setFont('helvetica', 'normal');
doc.text('UK ISP Proxy', 25, y);
doc.text('1', W - 48, y, { align: 'right' });
doc.text('N 6,500', W - 20, y, { align: 'right' });

y += 8;
doc.setDrawColor(42, 42, 42);
doc.line(20, y, W - 20, y);
y += 10;

doc.setFillColor(16, 185, 129);
doc.roundedRect(W - 72, y - 6, 52, 12, 2, 2, 'F');
doc.setTextColor(0, 0, 0);
doc.setFontSize(9);
doc.setFont('helvetica', 'bold');
doc.text('TOTAL', W - 67, y - 1);
doc.text('N 6,500', W - 23, y + 3, { align: 'right' });

y += 24;
doc.setTextColor(16, 185, 129);
doc.setFontSize(8);
doc.setFont('helvetica', 'bold');
doc.text('YOUR PROXY CREDENTIALS', 20, y);

doc.setFillColor(26, 26, 26);
doc.roundedRect(20, y + 4, W - 40, 64, 3, 3, 'F');

y += 14;
doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'bold');
doc.text('USERNAME', 28, y);
doc.setTextColor(52, 211, 153);
doc.setFontSize(10);
doc.setFont('helvetica', 'bold');
doc.text('demo_user_4821', 28, y + 7);

doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'bold');
doc.text('PASSWORD', W / 2 + 5, y);
doc.setTextColor(52, 211, 153);
doc.setFontSize(10);
doc.setFont('helvetica', 'bold');
doc.text('proxyPass_4821!', W / 2 + 5, y + 7);

y += 20;
doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'bold');
doc.text('PROXY ADDRESS', 28, y);
doc.setTextColor(52, 211, 153);
doc.setFontSize(10);
doc.setFont('helvetica', 'bold');
doc.text('185.199.228.105:8080', 28, y + 7);

doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'bold');
doc.text('PROTOCOL', W / 2 + 5, y);
doc.setTextColor(52, 211, 153);
doc.setFontSize(10);
doc.setFont('helvetica', 'bold');
doc.text('HTTP / SOCKS5', W / 2 + 5, y + 7);

y += 20;
doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'bold');
doc.text('FULL FORMAT', 28, y);
doc.setTextColor(115, 115, 115);
doc.setFontSize(7.5);
doc.setFont('helvetica', 'normal');
const fmt = 'http://demo_user_4821:proxyPass_4821!@185.199.228.105:8080';
const fmtLines = doc.splitTextToSize(fmt, W - 56);
doc.text(fmtLines, 28, y + 7);

y += 7 + fmtLines.length * 5;
doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'bold');
doc.text('EXPIRES', 28, y);
doc.setTextColor(245, 245, 245);
doc.setFontSize(9);
doc.setFont('helvetica', 'normal');
doc.text('August 13, 2026', 28, y + 6);

const footerY = H - 18;
doc.setDrawColor(42, 42, 42);
doc.line(20, footerY - 6, W - 20, footerY - 6);
doc.setTextColor(115, 115, 115);
doc.setFontSize(7);
doc.setFont('helvetica', 'normal');
doc.text('Need help? Chat with Charon -> @StyxproxyBot  |  hello@styxproxy.com  |  styxproxy.com', W / 2, footerY, { align: 'center' });
doc.setFontSize(6);
doc.text('This receipt was generated automatically. No signature required.', W / 2, footerY + 5, { align: 'center' });

doc.save('./public/sample-receipt.pdf');
console.log('done');

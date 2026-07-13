"""Generate sample-receipt.pdf with actual S-mark logo and dark theme."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from PIL import Image
import io

W, H = A4
pub = '/root/bunche/frontend/public'

# Load logo
logo_img = Image.open(f'{pub}/pdf-icon.png').convert('RGBA')
# Save as temp PNG for ReportLab
logo_path = '/tmp/styx-icon.png'
logo_img.save(logo_path)

# Build PDF
c = canvas.Canvas(f'{pub}/sample-receipt.pdf', pagesize=A4)

# ── Background: solid dark ──
c.setFillColor(HexColor('#0a0a0a'))
c.rect(0, 0, W, H, fill=1, stroke=0)

# ── Top accent bar ──
c.setFillColor(HexColor('#0AD25A'))
c.rect(0, H - 8, W, 8, fill=1, stroke=0)

# ── Logo (top-left) ──
c.drawImage(logo_path, 40, H - 80, width=48, height=48, mask='auto')

# ── Brand name (right of logo) ──
c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica-Bold', 22)
c.drawString(100, H - 55, 'styxproxy')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 9)
c.drawString(100, H - 70, 'Anonymous Proxy Service')

# ── Right side: receipt label ──
c.setFillColor(HexColor('#0AD25A'))
c.setFont('Helvetica-Bold', 10)
c.drawRightString(W - 40, H - 50, 'PAYMENT RECEIPT')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 9)
c.drawRightString(W - 40, H - 65, 'styxproxy.com')
c.drawRightString(W - 40, H - 78, f'Issued: {__import__("datetime").date.today().strftime("%B %d, %Y")}')

# ── Divider ──
c.setStrokeColor(HexColor('#262626'))
c.setLineWidth(0.5)
c.line(40, H - 100, W - 40, H - 100)

# ── Order details grid (tx_ref + order_id) ──
c.setFillColor(HexColor('#1a1a1a'))
c.roundRect(40, H - 175, W - 80, 55, 6, fill=1, stroke=0)

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(55, H - 138, 'TRANSACTION REFERENCE')
c.drawString(W/2 + 15, H - 138, 'ORDER ID')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica-Bold', 11)
c.drawString(55, H - 155, 'TXF-DANNION-PREVIEW')
c.drawString(W/2 + 15, H - 155, 'ORD-2025-XXXXX')

c.setFillColor(HexColor('#6B7280'))
c.setFont('Helvetica', 7)
c.drawString(55, H - 168, 'Flutterwave payment ID')
c.drawString(W/2 + 15, H - 168, 'Internal order reference')

# ── Date + Status row ──
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(55, H - 200, 'DATE')
c.drawString(W/2 + 15, H - 200, 'STATUS')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 10)
c.drawString(55, H - 215, 'July 13, 2026')

c.setFillColor(HexColor('#0AD25A'))
c.setFont('Helvetica-Bold', 10)
c.drawString(W/2 + 15, H - 215, 'FULFILLED')

# ── Divider ──
c.line(40, H - 240, W - 40, H - 240)

# ── Items table ──
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(55, H - 260, 'ITEM')
c.drawRightString(W - 175, H - 260, 'QTY')
c.drawRightString(W - 40, H - 260, 'AMOUNT')

c.line(40, H - 268, W - 40, H - 268)

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 11)
c.drawString(55, H - 290, 'UK ISP Proxy')
c.drawRightString(W - 175, H - 290, '1')
c.drawRightString(W - 40, H - 290, 'N 6,500')

# ── Total badge ──
c.setFillColor(HexColor('#0AD25A'))
c.roundRect(W - 175, H - 325, 135, 28, 4, fill=1, stroke=0)
c.setFillColor(HexColor('#000000'))
c.setFont('Helvetica-Bold', 11)
c.drawString(W - 165, H - 315, 'TOTAL')
c.drawRightString(W - 50, H - 315, 'N 6,500')

# ── Credentials card header ──
c.setFillColor(HexColor('#0AD25A'))
c.setFont('Helvetica-Bold', 10)
c.drawString(40, H - 360, 'YOUR PROXY CREDENTIALS')

# ── Credentials card ──
c.setFillColor(HexColor('#1a1a1a'))
c.roundRect(40, H - 480, W - 80, 110, 6, fill=1, stroke=0)

# Username + Password (top row)
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(55, H - 388, 'USERNAME')
c.drawString(W/2 + 15, H - 388, 'PASSWORD')

c.setFillColor(HexColor('#34D399'))
c.setFont('Helvetica-Bold', 12)
c.drawString(55, H - 405, 'demo_user_4821')
c.drawString(W/2 + 15, H - 405, 'proxyPass_4821!')

# Proxy + Protocol (middle row)
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(55, H - 425, 'PROXY ADDRESS')
c.drawString(W/2 + 15, H - 425, 'PROTOCOL')

c.setFillColor(HexColor('#34D399'))
c.setFont('Helvetica-Bold', 12)
c.drawString(55, H - 442, '185.199.228.105:8080')
c.drawString(W/2 + 15, H - 442, 'HTTP / SOCKS5')

# Full Format (full width)
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(55, H - 462, 'FULL FORMAT')

c.setFillColor(HexColor('#D1D5DB'))
c.setFont('Courier', 9)
c.drawString(55, H - 475, 'http://demo_user_4821:proxyPass_4821!@185.199.228.105:8080')

# ── Bottom: Support + Expires ──
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(40, H - 510, 'EXPIRES')
c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 10)
c.drawString(40, H - 525, 'August 13, 2026')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawRightString(W - 40, H - 510, 'SUPPORT')
c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 10)
c.drawRightString(W - 40, H - 525, '@StyxproxyBot  |  hello@styxproxy.com')

# ── Footer ──
c.setStrokeColor(HexColor('#262626'))
c.line(40, H - 580, W - 40, H - 580)

c.setFillColor(HexColor('#6B7280'))
c.setFont('Helvetica', 8)
c.drawCentredString(W/2, H - 600, 'Need help? Chat with Charon via @StyxproxyBot')
c.setFont('Helvetica', 7)
c.drawCentredString(W/2, H - 614, 'This receipt was generated automatically. No signature required.')

# ── Bottom accent bar ──
c.setFillColor(HexColor('#0AD25A'))
c.rect(0, 0, W, 4, fill=1, stroke=0)

# Logo watermark (subtle)
c.saveState()
c.translate(W - 110, 50)
c.setFillColor(HexColor('#0AD25A'))
c.setFillAlpha(0.08)
c.drawImage(logo_path, 0, 0, width=80, height=80, mask='auto')
c.restoreState()

c.showPage()
c.save()
print('PDF generated')

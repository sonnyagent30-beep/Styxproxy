"""Generate sample-receipt.pdf — full lockup, brand green, polished layout."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from PIL import Image
import io

W, H = A4
pub = '/root/bunche/frontend/public'

# Load FULL lockup (S-mark + wordmark) — cropped from PNG (already done)
# We need to crop this to a usable header size first
src_dark = Image.open('/root/sytxproxy_logo_pack/Logo for dark mode.png').convert('RGBA')
src_light = Image.open('/root/sytxproxy_logo_pack/Logo for light mode.png').convert('RGBA')

# Crop content area (no transparent margins)
dark_content = src_dark.crop((421, 377, 2911, 1254))  # 2490 x 877
light_content = src_light.crop((422, 379, 2904, 1253))  # 2482 x 874

# Scale to PDF header size (preserve 2.84:1 aspect)
# PDF header logo: 360px tall in PDF terms, so 360 x 2.84 = 1022px wide
# But for PDF we use point sizes (72pt/inch). A4 page is 595x842pt.
# 360px in PDF = 360 / 96 * 72 = 270 points... too big.
# Let's use ~120 points wide for the header logo, 42 points tall
logo_w = 140  # points
logo_h = 50   # points

# Create the PDF header logo by scaling our content
def make_pdf_header(src_content, target_w, target_h):
    sw, sh = src_content.size
    # Calculate scale to fit target height while preserving aspect
    scale = target_h / sh
    new_w = int(sw * scale)
    resized = src_content.resize((new_w, target_h), Image.LANCZOS)
    # Pad to match target_w if needed (center)
    if new_w < target_w:
        pad = (target_w - new_w) // 2
        new_img = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
        new_img.paste(resized, (pad, 0), resized)
        return new_img
    return resized

# Make PDF-ready logos
hdr_logo_dark = make_pdf_header(dark_content, logo_w, logo_h)
hdr_logo_light = make_pdf_header(light_content, logo_w, logo_h)
hdr_logo_dark.save('/tmp/pdf-logo-dark.png')
hdr_logo_light.save('/tmp/pdf-logo-light.png')

# Also make watermark version (very large, faded)
wm_scale = 4
wm = dark_content.resize((dark_content.width // wm_scale, dark_content.height // wm_scale), Image.LANCZOS)
wm.save('/tmp/pdf-watermark.png')

# Build PDF
c = canvas.Canvas(f'{pub}/sample-receipt.pdf', pagesize=A4)

# Background
c.setFillColor(HexColor('#0a0a0a'))
c.rect(0, 0, W, H, fill=1, stroke=0)

# Brand green: #0AD25A exact (matching logo)
PRIMARY = HexColor('#0AD25A')
PRIMARY_DARK = HexColor('#08a846')
PRIMARY_FADED = HexColor('#0AD25A')

# Top accent bar
c.setFillColor(PRIMARY)
c.rect(0, H - 12, W, 12, fill=1, stroke=0)

# Logo (top-left) — full lockup
c.drawImage('/tmp/pdf-logo-dark.png', 40, H - 95, width=logo_w, height=logo_h, mask='auto')

# Right side receipt label
c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 11)
c.drawRightString(W - 40, H - 50, 'PAYMENT RECEIPT')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 9)
c.drawRightString(W - 40, H - 65, 'styxproxy.com')
c.drawRightString(W - 40, H - 80, 'Issued: July 13, 2026')

# Divider
c.setStrokeColor(HexColor('#262626'))
c.setLineWidth(0.5)
c.line(40, H - 115, W - 40, H - 115)

# ── Receipt title row ──
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(40, H - 140, 'ORDER CONFIRMATION')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica-Bold', 28)
c.drawString(40, H - 175, 'Thank you, customer.')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 11)
c.drawString(40, H - 195, 'Your proxy is ready to use. Below are your credentials.')

# ── Status pill ──
c.setFillColor(PRIMARY)
c.roundRect(W - 130, H - 195, 90, 28, 14, fill=1, stroke=0)
c.setFillColor(HexColor('#000000'))
c.setFont('Helvetica-Bold', 11)
c.drawCentredString(W - 85, H - 184, 'FULFILLED')

# ── Order details card ──
card_y = H - 245
c.setFillColor(HexColor('#1a1a1a'))
c.roundRect(40, card_y - 75, W - 80, 75, 8, fill=1, stroke=0)

# TX Ref
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, card_y - 25, 'TRANSACTION REFERENCE')
c.drawString(W/2 + 20, card_y - 25, 'ORDER ID')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica-Bold', 13)
c.drawString(60, card_y - 45, 'TXF-DANNION-PREVIEW')
c.drawString(W/2 + 20, card_y - 45, 'ORD-2025-XXXXX')

c.setFillColor(HexColor('#6B7280'))
c.setFont('Helvetica', 8)
c.drawString(60, card_y - 60, 'Flutterwave payment reference')
c.drawString(W/2 + 20, card_y - 60, 'Internal order reference')

# Date row
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, card_y - 78, 'DATE')
c.drawString(W/2 + 20, card_y - 78, 'METHOD')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 11)
c.drawString(60, card_y - 95, 'July 13, 2026')
c.drawString(W/2 + 20, card_y - 95, 'Card / Bank / USSD / QR')

# ── Items section ──
items_y = card_y - 130
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 9)
c.drawString(40, items_y, 'ITEMS')
c.drawRightString(W - 175, items_y, 'QTY')
c.drawRightString(W - 40, items_y, 'AMOUNT')

c.setStrokeColor(HexColor('#262626'))
c.line(40, items_y - 8, W - 40, items_y - 8)

# Item
c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 12)
c.drawString(40, items_y - 30, 'UK ISP Proxy')
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 9)
c.drawString(40, items_y - 45, '1 month | HTTP/SOCKS5 | United Kingdom')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 12)
c.drawRightString(W - 175, items_y - 30, '1')
c.drawRightString(W - 40, items_y - 30, 'N 6,500')

# ── Total pill ──
total_y = items_y - 80
c.setFillColor(PRIMARY)
c.roundRect(W - 200, total_y - 10, 160, 35, 6, fill=1, stroke=0)
c.setFillColor(HexColor('#000000'))
c.setFont('Helvetica-Bold', 12)
c.drawString(W - 185, total_y + 5, 'TOTAL PAID')
c.setFont('Helvetica-Bold', 16)
c.drawRightString(W - 50, total_y + 5, 'N 6,500')

# ── Credentials card (highlighted section) ──
cred_y = total_y - 60
c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 11)
c.drawString(40, cred_y, 'YOUR PROXY CREDENTIALS')

c.setFillColor(HexColor('#0a0a0a'))
c.setStrokeColor(PRIMARY)
c.setLineWidth(1.5)
cred_card_h = 200
c.roundRect(40, cred_y - cred_card_h, W - 80, cred_card_h, 8, fill=1, stroke=1)
c.setStrokeColor(HexColor('#262626'))
c.setLineWidth(0.5)

# Layout from top of card downward
card_top = cred_y - 30
row_h = 50

# Username + Password (top row)
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, card_top, 'USERNAME')
c.drawString(W/2 + 20, card_top, 'PASSWORD')

c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 13)
c.drawString(60, card_top - 18, 'demo_user_4821')
c.drawString(W/2 + 20, card_top - 18, 'proxyPass_4821!')

# Divider
c.setStrokeColor(HexColor('#262626'))
c.line(60, card_top - 32, W - 60, card_top - 32)

# Proxy + Protocol (middle row)
row2_top = card_top - 50
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, row2_top, 'PROXY ADDRESS')
c.drawString(W/2 + 20, row2_top, 'PROTOCOL')

c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 13)
c.drawString(60, row2_top - 18, '185.199.228.105:8080')
c.drawString(W/2 + 20, row2_top - 18, 'HTTP / SOCKS5')

# Divider
c.line(60, row2_top - 32, W - 60, row2_top - 32)

# Full Format (full width)
row3_top = row2_top - 50
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, row3_top, 'FULL FORMAT')

c.setFillColor(HexColor('#D1D5DB'))
c.setFont('Courier', 9)
c.drawString(60, row3_top - 18, 'http://demo_user_4821:proxyPass_4821!@185.199.228.105:8080')

# Divider
c.line(60, row3_top - 32, W - 60, row3_top - 32)

# Expires (bottom row of card)
row4_top = row3_top - 50
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, row4_top, 'EXPIRES')
c.drawString(W/2 + 20, row4_top, 'AUTO-RENEW')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 11)
c.drawString(60, row4_top - 18, 'August 13, 2026')
c.drawString(W/2 + 20, row4_top - 18, 'On (manage to disable)')

# ── Support section ──
sup_y = cred_y - 240
c.setFillColor(HexColor('#1a1a1a'))
c.roundRect(40, sup_y - 60, W - 80, 60, 8, fill=1, stroke=0)

c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 9)
c.drawString(60, sup_y - 22, 'NEED HELP?')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 11)
c.drawString(60, sup_y - 40, 'Chat with Charon on Telegram:')
c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 11)
c.drawString(255, sup_y - 40, '@StyxproxyBot')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 9)
c.drawString(W - 200, sup_y - 22, 'Email:')
c.drawString(W - 200, sup_y - 40, 'Web:')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 11)
c.drawRightString(W - 60, sup_y - 22, 'hello@styxproxy.com')
c.setFont('Helvetica-Bold', 11)
c.setFillColor(PRIMARY)
c.drawRightString(W - 60, sup_y - 40, 'styxproxy.com')

# ── Footer ──
c.setStrokeColor(HexColor('#262626'))
c.line(40, 50, W - 40, 50)

c.setFillColor(HexColor('#6B7280'))
c.setFont('Helvetica', 8)
c.drawCentredString(W/2, 35, 'This receipt was generated automatically. No signature required.')
c.setFont('Helvetica', 7)
c.drawCentredString(W/2, 22, '© 2026 Styxproxy — Anonymous proxy service for the discerning.')

# Bottom accent bar
c.setFillColor(PRIMARY)
c.rect(0, 0, W, 4, fill=1, stroke=0)

# Save
c.showPage()
c.save()
print('PDF generated with full lockup, exact brand green, polished layout')

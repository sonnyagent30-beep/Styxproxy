"""Generate sample-receipt.pdf — properly aligned, no overlaps."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from PIL import Image

W, H = A4  # 595 x 842
pub = '/root/bunche/frontend/public'

# Load full lockup
src_dark = Image.open('/root/sytxproxy_logo_pack/Logo for dark mode.png').convert('RGBA')
dark_content = src_dark.crop((421, 377, 2911, 1254))  # 2490 x 877

# Scale logo to header size (140pt wide, ~50pt tall preserving 2.84:1 aspect)
logo_w = 130
logo_h = 46
def make_pdf_header(src_content, target_w, target_h):
    sw, sh = src_content.size
    scale = target_h / sh
    new_w = int(sw * scale)
    resized = src_content.resize((new_w, target_h), Image.LANCZOS)
    if new_w < target_w:
        pad = (target_w - new_w) // 2
        new_img = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
        new_img.paste(resized, (pad, 0), resized)
        return new_img
    return resized

hdr_logo = make_pdf_header(dark_content, logo_w, logo_h)
hdr_logo.save('/tmp/pdf-logo.png')

# Brand green
PRIMARY = HexColor('#0AD25A')

# Build PDF
c = canvas.Canvas(f'{pub}/sample-receipt.pdf', pagesize=A4)

# Background
c.setFillColor(HexColor('#0a0a0a'))
c.rect(0, 0, W, H, fill=1, stroke=0)

# Top accent bar
c.setFillColor(PRIMARY)
c.rect(0, H - 12, W, 12, fill=1, stroke=0)

# ────────────────────────────────────────────────────────────────────
# HEADER (y range: H-50 to H-20)
# Logo on left
c.drawImage('/tmp/pdf-logo.png', 40, H - 80, width=logo_w, height=logo_h, mask='auto')

# Receipt label block on right — properly spaced
# Right-aligned, each line 18pt apart
c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 12)
c.drawRightString(W - 40, H - 45, 'PAYMENT RECEIPT')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 9)
c.drawRightString(W - 40, H - 62, 'styxproxy.com')
c.drawRightString(W - 40, H - 76, 'Issued: July 13, 2026')

# Divider
c.setStrokeColor(HexColor('#262626'))
c.setLineWidth(0.5)
c.line(40, H - 100, W - 40, H - 100)

# ────────────────────────────────────────────────────────────────────
# HEADLINE SECTION (y range: H-105 to H-180)
# Section label
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(40, H - 120, 'ORDER CONFIRMATION')

# Big headline
c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica-Bold', 26)
c.drawString(40, H - 152, 'Thank you, customer.')

# Subtitle
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 11)
c.drawString(40, H - 172, 'Your proxy is ready to use. Below are your credentials.')

# FULFILLED pill on the right, aligned with headline
c.setFillColor(PRIMARY)
c.roundRect(W - 140, H - 158, 100, 26, 13, fill=1, stroke=0)
c.setFillColor(HexColor('#000000'))
c.setFont('Helvetica-Bold', 11)
c.drawCentredString(W - 90, H - 149, 'FULFILLED')

# ────────────────────────────────────────────────────────────────────
# ORDER DETAILS CARD (y range: H-185 to H-340)
card_top = H - 195
card_bottom = card_top - 130
card_h = card_top - card_bottom

c.setFillColor(HexColor('#1a1a1a'))
c.roundRect(40, card_bottom, W - 80, card_h, 8, fill=1, stroke=0)

# Two columns: left starts at x=60, right at x=W/2+20
# Row 1: TRANSACTION REFERENCE | ORDER ID (labels)
row1_y = card_top - 25
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, row1_y, 'TRANSACTION REFERENCE')
c.drawString(W/2 + 20, row1_y, 'ORDER ID')

# Row 1 values
c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica-Bold', 12)
c.drawString(60, row1_y - 18, 'TXF-DANNION-PREVIEW')
c.drawString(W/2 + 20, row1_y - 18, 'ORD-2025-XXXXX')

# Row 1 sub-labels
c.setFillColor(HexColor('#6B7280'))
c.setFont('Helvetica', 7)
c.drawString(60, row1_y - 32, 'Flutterwave payment reference')
c.drawString(W/2 + 20, row1_y - 32, 'Internal order reference')

# Divider inside card
c.setStrokeColor(HexColor('#262626'))
c.line(60, card_top - 70, W - 60, card_top - 70)

# Row 2: DATE | METHOD
row2_y = card_top - 88
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, row2_y, 'DATE')
c.drawString(W/2 + 20, row2_y, 'METHOD')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 11)
c.drawString(60, row2_y - 16, 'July 13, 2026')
c.drawString(W/2 + 20, row2_y - 16, 'Card / Bank / USSD / QR')

# ────────────────────────────────────────────────────────────────────
# ITEMS SECTION (y range: H-360 to H-430)
items_y = H - 380

# Header row
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 9)
c.drawString(40, items_y, 'ITEMS')
c.drawRightString(W - 175, items_y, 'QTY')
c.drawRightString(W - 40, items_y, 'AMOUNT')

c.setStrokeColor(HexColor('#262626'))
c.line(40, items_y - 8, W - 40, items_y - 8)

# Item row
item_y = items_y - 30
c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 12)
c.drawString(40, item_y, 'UK ISP Proxy')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 8)
c.drawString(40, item_y - 14, '1 month  |  HTTP/SOCKS5  |  United Kingdom')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 12)
c.drawRightString(W - 175, item_y, '1')
c.drawRightString(W - 40, item_y, 'N 6,500')

# ────────────────────────────────────────────────────────────────────
# TOTAL PAID pill (y range: H-470 to H-440)
c.setFillColor(PRIMARY)
c.roundRect(W - 200, H - 470, 160, 32, 6, fill=1, stroke=0)
c.setFillColor(HexColor('#000000'))
c.setFont('Helvetica-Bold', 11)
c.drawString(W - 188, H - 458, 'TOTAL PAID')
c.setFont('Helvetica-Bold', 14)
c.drawRightString(W - 50, H - 458, 'N 6,500')

# ────────────────────────────────────────────────────────────────────
# CREDENTIALS CARD (y range: H-490 to H-700)
cred_header_y = H - 500
cred_card_top = cred_header_y - 12
cred_card_bottom = cred_card_top - 200  # 200pt tall, 4 rows × 50pt
cred_card_h = cred_card_top - cred_card_bottom

# "YOUR PROXY CREDENTIALS" header — above the card
c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 11)
c.drawString(40, cred_header_y, 'YOUR PROXY CREDENTIALS')

# Card with green border
c.setFillColor(HexColor('#0a0a0a'))
c.setStrokeColor(PRIMARY)
c.setLineWidth(1.5)
c.roundRect(40, cred_card_bottom, W - 80, cred_card_h, 8, fill=1, stroke=1)
c.setStrokeColor(HexColor('#262626'))
c.setLineWidth(0.5)

# Inside card layout — 4 rows, 45pt each, top at cred_card_top - 25
inner_top = cred_card_top - 28
row_h = 45

# Row 1: USERNAME | PASSWORD
r1 = inner_top
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, r1, 'USERNAME')
c.drawString(W/2 + 20, r1, 'PASSWORD')

c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 12)
c.drawString(60, r1 - 16, 'demo_user_4821')
c.drawString(W/2 + 20, r1 - 16, 'proxyPass_4821!')

# Divider 1
c.line(60, r1 - 28, W - 60, r1 - 28)

# Row 2: PROXY ADDRESS | PROTOCOL
r2 = r1 - row_h
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, r2, 'PROXY ADDRESS')
c.drawString(W/2 + 20, r2, 'PROTOCOL')

c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 12)
c.drawString(60, r2 - 16, '185.199.228.105:8080')
c.drawString(W/2 + 20, r2 - 16, 'HTTP / SOCKS5')

c.line(60, r2 - 28, W - 60, r2 - 28)

# Row 3: FULL FORMAT (full width)
r3 = r2 - row_h
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, r3, 'FULL FORMAT')

c.setFillColor(HexColor('#D1D5DB'))
c.setFont('Courier', 9)
c.drawString(60, r3 - 16, 'http://demo_user_4821:proxyPass_4821!@185.199.228.105:8080')

c.line(60, r3 - 28, W - 60, r3 - 28)

# Row 4: EXPIRES | AUTO-RENEW
r4 = r3 - row_h
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica-Bold', 8)
c.drawString(60, r4, 'EXPIRES')
c.drawString(W/2 + 20, r4, 'AUTO-RENEW')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 10)
c.drawString(60, r4 - 16, 'August 13, 2026')
c.drawString(W/2 + 20, r4 - 16, 'On (manage to disable)')

# ────────────────────────────────────────────────────────────────────
# SUPPORT SECTION — placed BELOW credentials card
# cred_card_bottom is the bottom of cred card
support_y_top = cred_card_bottom - 20  # 20pt gap below credentials card
sup_top = support_y_top
sup_h = 65

c.setFillColor(HexColor('#1a1a1a'))
c.roundRect(40, sup_top - sup_h, W - 80, sup_h, 8, fill=1, stroke=0)

# Two columns: left = contact, right = web
# Left column
c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 9)
c.drawString(60, sup_top - 18, 'NEED HELP?')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 11)
c.drawString(60, sup_top - 35, 'Chat with Charon:')

c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 11)
c.drawString(60, sup_top - 50, '@StyxproxyBot')

# Right column
c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 9)
c.drawString(290, sup_top - 18, 'Email:')

c.setFillColor(HexColor('#FFFFFF'))
c.setFont('Helvetica', 11)
c.drawString(320, sup_top - 18, 'hello@styxproxy.com')

c.setFillColor(HexColor('#9CA3AF'))
c.setFont('Helvetica', 9)
c.drawString(290, sup_top - 35, 'Web:')

c.setFillColor(PRIMARY)
c.setFont('Helvetica-Bold', 11)
c.drawString(320, sup_top - 35, 'styxproxy.com')

# ────────────────────────────────────────────────────────────────────
# FOOTER (y range: 20 to 50)
c.setStrokeColor(HexColor('#262626'))
c.line(40, 35, W - 40, 35)

c.setFillColor(HexColor('#6B7280'))
c.setFont('Helvetica', 7)
c.drawCentredString(W/2, 22, 'This receipt was generated automatically. No signature required.')
c.drawCentredString(W/2, 12, '© 2026 Styxproxy — Anonymous proxy service for the discerning.')

# Bottom accent bar
c.setFillColor(PRIMARY)
c.rect(0, 0, W, 3, fill=1, stroke=0)

# Save
c.showPage()
c.save()
print('PDF regenerated with proper alignment')

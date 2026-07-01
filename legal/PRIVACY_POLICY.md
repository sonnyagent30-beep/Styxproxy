# Privacy Policy
*Bunche — Automated Proxy Retail Service*
*Effective Date: 2026-07-01*

---

## Introduction

Bunche ("we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our WhatsApp-based proxy ordering service.

This policy complies with:
- Nigeria Data Protection Regulation (NDPR) 2019
- Nigeria Data Protection Act (NDPA) 2023
- General Data Protection Regulation (GDPR) for EU users

---

## 1. Information We Collect

### 1.1 Information You Provide
- Phone number (primary identifier)
- Name (optional, collected during first purchase setup)
- Order history and communication preferences
- Recovery method (PIN or OTP — your choice)
- Free trial usage history

### 1.2 Information Collected Automatically
- WhatsApp messages you send us (processed via WhatsApp Business API)
- IP addresses (when you interact with our webhook endpoints)
- Device information (browser type, OS — if you access our links)
- n8n workflow execution logs
- Proxy usage volume and data consumption

### 1.3 Information from Third Parties
- **Payment Processor:** Transaction status, payment confirmation, payment metadata
- **Meta / WhatsApp:** Message metadata via WhatsApp Business API
- **Survey Partner:** Free trial survey completion verification
- **Vetted Infrastructure Partners:** Proxy allocation data, proxy status

---

## 2. How We Use Your Information

| Purpose | Data Used | Legal Basis |
|---------|-----------|-------------|
| Process and fulfill orders | Phone number, order details | Contract performance |
| Deliver proxy credentials | WhatsApp number | Contract performance |
| Send renewal reminders | Phone number, order history | Contract performance |
| Handle refunds | Phone number, transaction info | Contract performance |
| Verify free trial completion | Phone number, survey ID | Consent |
| Fraud prevention | Payment data, usage patterns | Legitimate interest |
| Service improvement | Aggregated usage data | Legitimate interest |

---

## 3. Free Trial Data

When you participate in our free trial program:

- We collect your phone number to verify daily limits
- We receive survey completion confirmation from our survey partner
- We log free trial usage (timestamp, survey ID, proxy assigned)
- We do NOT store your free trial browsing activity
- Free trial proxies are hosted on Bunche's own infrastructure

Free trial data is retained for 90 days, then anonymized for analytics.

---

## 4. Data Sharing

We do NOT sell your data. We share data only with:

### 4.1 Service Providers
- **Payment Processor:** For payment processing
- **Meta / WhatsApp:** For message delivery via WhatsApp Business API
- **Vetted Infrastructure Partners:** For proxy allocation (no personal data beyond proxy requirements)
- **Survey Partner:** For free trial survey verification
- **n8n:** For workflow processing

### 4.2 Infrastructure Partners Disclosure

Bunche sources proxy infrastructure from vetted third-party providers. We do not publicly name our infrastructure partners. These partners receive only the minimum data required to allocate proxy IPs (e.g., country selection). We require all partners to comply with applicable data protection laws.

### 4.3 Legal Requirements
We may disclose information if required by:
- Court order or legal process
- Nigerian law enforcement (with valid subpoena)
- NDPC (Nigeria Data Protection Commission) investigations
- Prevention of fraud or illegal activity

### 4.4 Business Transfers
If Bunche is acquired or merged, customer data may be transferred to the acquiring entity. You will be notified via WhatsApp before any transfer.

---

## 5. Data Retention

| Data Type | Retention Period |
|-----------|-----------------|
| Order history | 7 years (for tax/audit) |
| Customer contact info | Until deletion or 2 years of inactivity |
| Payment records | 7 years |
| WhatsApp messages (processed) | 90 days |
| n8n execution logs | 30 days |
| Free trial usage | 90 days, then anonymized |
| Recovery PIN (hashed) | Until account deletion |

---

## 6. Your Rights

### Under NDPR/NDPA (Nigeria):
- Know what personal data we hold about you
- Request access to your data
- Request correction of inaccurate data
- Request deletion of your data
- Lodge a complaint with the Nigeria Data Protection Commission (NDPC)

### Under GDPR (EU Users):
- Right to access
- Right to rectification
- Right to erasure ("right to be forgotten")
- Right to restrict processing
- Right to data portability
- Right to object
- Rights related to automated decision-making

### How to Exercise Your Rights
Contact us via WhatsApp or email. We will respond within 30 days.

---

## 7. Data Security

### 7.1 Technical Measures
- **Encryption:** All data in transit uses TLS 1.2+
- **Hashing:** PINs stored as bcrypt hashes (never plaintext)
- **API Security:** All API keys stored securely in n8n credentials
- **Webhook Verification:** All incoming webhooks (payment processor, survey partner) verified for authenticity
- **Credential Rotation:** Proxy credentials rotated on refund, expiry, and free trial completion

### 7.2 Organizational Measures
- Access to customer data restricted to authorized personnel only
- Admin commands logged for audit
- Regular security reviews
- Incident response plan in place

### 7.3 Proxy Security
- Bunche controls the authentication layer — all proxy access requires Bunche credentials
- Credentials are revoked instantly on refund, expiry, or abuse detection
- Free trial proxies use shared credentials with 2-hour TTL
- We do not monitor or inspect proxy traffic content

---

## 8. Children's Privacy

Bunche does not knowingly collect data from users under 18. If you are under 18, do not use our services.

---

## 9. International Data Transfers

Your data may be transferred internationally as necessary for service delivery, including:
- **Payment processing** via our payment processor (Nigeria)
- **Message delivery** via Meta/WhatsApp (USA/International)
- **Proxy infrastructure** sourced from vetted partners (various jurisdictions)

By using Bunche, you consent to international data transfers necessary for service delivery.

---

## 10. Cookies and Tracking

Bunche WhatsApp interface does not use cookies. If you click links to our legal documents (Terms, Privacy, AUP), our web hosting may use standard cookies. We do not use third-party tracking cookies on our properties.

---

## 11. Changes to Privacy Policy

We may update this Privacy Policy. Changes will be communicated via:
- Updated "Effective Date" at the top of this document
- WhatsApp notification for material changes

Continued use of Bunche after changes constitutes acceptance.

---

## 12. Contact Us

**Bunche**
**WhatsApp:** +2347032981049
**Email:** hello@bunche.ng

**Nigeria Data Protection Commission:**
www.ndpc.gov.ng

*This Privacy Policy is incorporated by reference into our Terms of Service.*

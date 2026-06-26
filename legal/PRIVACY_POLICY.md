# Privacy Policy
*Bunche — Automated Proxy Retail Service*
*Effective Date: 2026-06-26*

---

## Introduction

Bunche ("we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our WhatsApp-based proxy ordering service.

This policy complies with:
- Nigeria Data Protection Regulation (NDPR) 2019
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
- **Flutterwave:** Transaction status, payment confirmation, payment metadata
- **Meta / WhatsApp:** Message metadata via WhatsApp Business API
- **Proxy Providers (Proxy-Seller, DataImpulse):** Proxy allocation data, proxy status
- **CPAGrip:** Free trial survey completion verification (user_id, survey_id, reward)
- **Geonode Free Proxy API:** Public proxy list data (no personal data)
- **Google Sheets:** Order database

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
- We receive survey completion confirmation from CPAGrip (no payment data)
- We log free trial usage (timestamp, survey ID, proxy assigned)
- We do NOT store your free trial browsing activity
- Free trial proxies are sourced from Geonode Free Proxy List (public proxies)

Free trial data is retained for 90 days, then anonymized for analytics.

---

## 4. Data Sharing

We do NOT sell your data. We share data only with:

### 4.1 Service Providers
- **Flutterwave:** For payment processing
- **Meta / WhatsApp:** For message delivery via WhatsApp Business API
- **Proxy-Seller:** For ISP and Datacenter proxy allocation
- **DataImpulse:** For Residential and Mobile proxy allocation
- **CPAGrip:** For free trial survey verification
- **Geonode Free Proxy API:** For free trial proxy sourcing (public data only)
- **Google Sheets:** For order database
- **n8n:** For workflow processing

### 4.2 Legal Requirements
We may disclose information if required by:
- Court order or legal process
- Nigerian law enforcement (with valid subpoena)
- NDPR (Nigeria Data Protection Commission) investigations
- Prevention of fraud or illegal activity

### 4.3 Business Transfers
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

### Under NDPR (Nigeria):
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
- **Webhook Verification:** All incoming webhooks (Flutterwave, CPAGrip) verified for authenticity

### 7.2 Organizational Measures
- Access to customer data restricted to authorized personnel only
- Admin commands logged for audit
- Regular security reviews
- Incident response plan in place

### 7.3 Free Trial Security
- Free trial proxies are PUBLIC proxies (not managed by us)
- We do not control or monitor free trial proxy traffic
- Free trial users assume all security risk

---

## 8. Children's Privacy

Bunche does not knowingly collect data from users under 18. If you are under 18, do not use our services.

---

## 9. International Data Transfers

- **Proxy-Seller** (Cyprus/EU) — proxy data
- **DataImpulse** (International) — proxy data
- **Flutterwave** (Nigeria) — payment data
- **CPAGrip** (International) — survey verification
- **Meta/WhatsApp** (USA/International) — message delivery

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
**WhatsApp:** +234 XXX XXX XXXX
**Email:** privacy@bunche.com

**Nigeria Data Protection Commission:**
www.ndpc.gov.ng

---

*This Privacy Policy is incorporated by reference into our Terms of Service.*
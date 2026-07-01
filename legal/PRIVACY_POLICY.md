# Privacy Policy
*Bunche — Automated Proxy Retail Service*
*Effective Date: 2026-07-01*

---

## 1. Introduction

Bunche ("we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our services across any channel — our website (bunche.ng), our Telegram bot, or our WhatsApp bot.

We collect different information depending on how you interact with us. This policy is designed to be honest and clear about what we collect and why.

By using Bunche, you consent to the data practices described in this policy.

---

## 2. Three Channels, Three Data Models

We operate three independent channels. Each collects different information.

### 2.1 Website (bunche.ng) — Anonymous Orders

**We collect almost nothing.**

When you order via bunche.ng, we collect:

| Data | Why we collect it | How long we keep it |
|------|------------------|---------------------|
| Flutterwave tx_ref | To identify your order | 7 years (financial records) |
| Product purchased | To fulfil your order | 7 years |
| Amount paid (₦) | To process payment | 7 years |
| IP address (of our server) | Technical operation | 90 days |
| Email address (optional) | To send receipt if you provide it | Until you request deletion |
| Your IP address (of your device) | **We do NOT collect this** | — |

We do not know your name, your phone number, your device IP address, or any other identifying information unless you voluntarily provide it.

The tx_ref (Flutterwave transaction reference) is your only order identifier. You do not create an account.

### 2.2 Telegram Bot

When you interact with the Bunche Telegram bot, we collect:

| Data | Why we collect it | How long we keep it |
|------|------------------|---------------------|
| Telegram chat ID | To identify you and deliver messages | Until you request deletion |
| Telegram username (if set) | To display your name in support | Until you request deletion |
| Display name (if shared) | For customer support purposes | Until you request deletion |
| Messages you send us | To understand and respond to requests | 90 days |
| Order history | To fulfil and support orders | 7 years |
| PIN (if you set one) | To secure your account | Until you request deletion |

We do not collect your Telegram phone number.

### 2.3 WhatsApp Bot

When you interact with the Bunche WhatsApp bot, we collect:

| Data | Why we collect it | How long we keep it |
|------|------------------|---------------------|
| WhatsApp phone number (hashed) | To identify you and deliver messages | Until you request deletion |
| Display name (if shared) | For customer support purposes | Until you request deletion |
| Messages you send us | To understand and respond to requests | 90 days |
| Order history | To fulfil and support orders | 7 years |
| PIN (if you set one) | To secure your account | Until you request deletion |

Your phone number is hashed before storage. We do not store your phone number in plain text.

---

## 3. What We Collect

### 3.1 Information You Give Us

- **Order information:** product, country, payment amount, tx_ref
- **Payment information:** processed entirely by Flutterwave. We never see your card number, bank account, or full bank details
- **Support communications:** messages sent via Telegram, WhatsApp, or email
- **PIN:** if you choose to set a PIN to secure your chat account
- **Optional email:** for receipt delivery on website orders
- **Ban claim evidence:** screenshots or information you upload when raising a ban claim

### 3.2 Information We Create

- **Order records:** tx_ref, product, amount, status, IP assigned, timestamps
- **Proxy credentials issued:** username, hashed password, validity period
- **Free trial records:** survey postback data, earned trial time
- **Audit logs:** timestamped records of significant events (order placed, credentials issued, refund processed, account deleted)

### 3.3 Information We Do NOT Collect

- Your device IP address (when using the website)
- Your phone number (WhatsApp — only the hash is stored)
- Your Telegram phone number
- Your name (unless you voluntarily provide it)
- Your location (unless you share it with us)
- Cookies on bunche.ng (we do not use cookies)
- Any data from third-party websites or services you access using Bunche proxies

---

## 4. How We Use Your Information

We use your information to:

| Purpose | Data used |
|---------|-----------|
| Fulfill orders | tx_ref, product, payment |
| Deliver proxy credentials | Credentials, delivery channel |
| Provide customer support | Chat ID / phone hash, order history |
| Process refunds | tx_ref, payment information |
| Investigate ban claims | tx_ref, evidence you provide |
| Detect and prevent fraud | Order patterns, payment verification |
| Comply with legal obligations | Financial records, audit logs |
| Send service notifications | Chat ID / phone hash / email (if provided) |

---

## 5. Data Sharing

### 5.1 We Do Not Sell Your Data

We do not sell, rent, or trade your personal information to any third party.

### 5.2 We Share Only What Is Necessary

| Recipient | What we share | Why |
|-----------|---------------|-----|
| Flutterwave | tx_ref, amount, product | Payment processing |
| Proxy providers (Proxy-Seller, DataImpulse) | Proxy credentials | To generate and deliver your proxy IP |
| Telegram | Messages you send | To deliver messages via Telegram API |
| Meta / WhatsApp | Messages you send | To deliver messages via WhatsApp Business API |
| Theorem Reach | Survey completion data | To track free trial earnings |
| Law enforcement | As required by Nigerian law | To comply with legal obligations |

### 5.3 Data Processors

We use third-party service providers who process data on our behalf:

| Service | What they process | Their privacy policy |
|---------|-------------------|---------------------|
| Flutterwave | Payment data | flutterwave.com/privacy |
| Telegram | Chat messages | telegram.org/privacy |
| Meta / WhatsApp | Chat messages | whatsapp.com/legal/privacy-policy |
| Theorem Reach | Survey data | theoremreach.com/privacy |
| Resend | Transactional emails | resend.com/privacy |

---

## 6. Data Retention

| Data type | Retention period | Reason |
|-----------|-----------------|--------|
| Financial records (orders, payments, tx_ref) | 7 years | Nigerian tax law / financial record keeping |
| Order fulfillment records | 7 years | Contract performance |
| Customer support messages | 90 days | Operational efficiency |
| Chat credentials (Telegram chat ID, WhatsApp hash) | Until deletion requested | Service delivery |
| Proxy credentials (issued IPs) | 7 years | Credential audit trail |
| Audit logs | 7 years | Compliance |
| Error logs | 1 year | System troubleshooting |
| Rate limit logs | 90 days | Security |
| Webhook security logs | 90 days | Security |

### 6.1 Deletion Requests

You may request deletion of your personal data at any time. To request deletion:

- **Telegram:** Send "delete my data" to @bunche
- **WhatsApp:** Send "delete my data" to the Bunche WhatsApp bot
- **Website orders:** Email hello@bunche.ng with your tx_ref

We will delete your personal data within 30 days, except:
- Financial records required by law (7 years)
- Data we are required to retain by Nigerian law

---

## 7. Data Security

### 7.1 Technical Measures

- HTTPS-only on all Bunche properties
- PostgreSQL with restricted access (localhost only)
- API keys stored in environment variables, not in code
- HMAC verification on all incoming webhooks (Flutterwave, Theorem Reach)
- Rate limiting on all API endpoints
- Audit logging of significant system events

### 7.2 Organizational Measures

- Access to customer data restricted to authorized personnel only
- No customer data in development or test environments
- Secrets rotation policy: API keys rotated every 90 days

---

## 8. Your Rights Under NDPR

Under Nigeria's NDPR (Nigeria Data Protection Regulation), you have the right to:

| Right | How to exercise |
|-------|----------------|
| Access your personal data | Request via any channel — we respond within 30 days |
| Correct inaccurate data | Contact us with the correct information |
| Delete your data | Send "delete my data" on Telegram/WhatsApp or email us |
| Object to processing | Contact us — we will assess the objection |
| Data portability | We will provide your data in a machine-readable format |
| Withdraw consent | Stop using the service and request deletion |

To exercise any of these rights, contact us via:
- Telegram: @bunche
- WhatsApp: Bunche WhatsApp bot
- Email: hello@bunche.ng

---

## 9. Cookies and Tracking

### 9.1 bunche.ng

**We do not use cookies on bunche.ng.**

When you visit bunche.ng, we do not store any cookies in your browser. We do not use third-party tracking pixels or analytics tools.

### 9.2 Telegram and WhatsApp

We do not control the cookies or tracking used by Telegram or Meta/WhatsApp. These platforms have their own privacy policies.

### 9.3 Links to Legal Documents

If you click links to our legal documents from Telegram or WhatsApp, our web hosting provider may use standard server logs (which record your server IP address, not your device IP). This is standard web hosting practice and is not used for tracking.

---

## 10. Children's Privacy

Bunche services are not intended for persons under the age of 18. We do not knowingly collect data from minors. If we become aware that data from a minor has been collected, we will delete it immediately.

---

## 11. International Data Transfers

Bunche operates primarily in Nigeria. Some of our service providers (Flutterwave, Meta/WhatsApp, Telegram) operate internationally. When your data is transferred outside Nigeria, we ensure appropriate safeguards are in place through the data processor's standard contractual clauses or equivalent legal mechanisms.

---

## 12. Data Breach Notification

In the event of a data breach that poses a risk to your rights and freedoms, we will notify the Nigeria Data Protection Commission within 72 hours of becoming aware of the breach.

We will also notify affected customers via their contact channel (Telegram, WhatsApp, or email) as soon as reasonably practicable.

---

## 13. Changes to This Policy

We may update this Privacy Policy from time to time. Material changes will be communicated via:
- Telegram message (for Telegram customers)
- WhatsApp message (for WhatsApp customers)
- Notice on bunche.ng

The effective date at the top of this policy indicates when it was last updated.

---

## 14. Contact Us

**Bunche**

For any questions about this Privacy Policy or to exercise your data rights:

- **Telegram:** @bunche
- **WhatsApp:** Available via bunche.ng
- **Email:** hello@bunche.ng
- **Website:** bunche.ng

We will respond to all enquiries within 30 days.

---

*Version: 2026-07-01*

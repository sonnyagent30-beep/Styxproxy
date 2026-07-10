const content = `# Terms of Service
*Styxproxy — Anonymous Proxy Service*
*Effective Date: July 1, 2026*

---

## 1. Acceptance of Terms

By accessing or using Styxproxy's services, you agree to be bound by these Terms of Service, our Privacy Policy, and our Acceptable Use Policy. If you do not agree to these terms, do not use our services.

Your first interaction with Styxproxy constitutes acceptance of these terms, regardless of channel — website or Telegram bot.

---

## 2. Our Service Channels

Styxproxy operates across three independent channels. All three channels offer the same products and pricing. No channel requires you to use another.

### 2.1 Website

The primary order path. No account required. No personal data collected beyond what is necessary to process your order.
- Select product → pay securely via our payment processor → receive credentials immediately on screen
- No registration. No phone number. No email required.
- Your transaction reference is your only order identifier
- Manage orders at styxproxy.com/manage

### 2.2 Telegram Bot (@styxproxy)

Full ordering and support via the Styxproxy Telegram bot.
- Order via chat → payment link → credentials delivered in Telegram
- Identity: your Telegram chat ID (not your phone number)
- Optional: set a PIN to secure your account

## 3. No Account Required (Website)

Customers who order via the website do not create an account. We do not collect:
- Your name
- Your email address (unless voluntarily provided)
- Your phone number
- Your IP address
- Any identifying information beyond what is needed to process payment

Your transaction reference is the only identifier for website orders.

---

## 4. Ordering

### 4.1 How to Order

Via Website: Select your product, complete payment via our payment processor (card, bank transfer, USSD, or QR), your credentials are displayed immediately on the confirmation page.

Via Telegram: Send your order request to the Styxproxy bot, receive a payment link, complete payment, your credentials are delivered in the same chat.

### 4.2 Payment

All payments are processed by our payment processor. Styxproxy does not store your card details or bank information. A transaction reference (tx_ref) is issued for every payment.

### 4.3 Order Fulfilment

Website orders: credentials are displayed on the confirmation page immediately after payment is confirmed (typically 10-30 seconds). Chat orders: credentials are delivered in Telegram within 2 minutes of payment confirmation.

---

## 5. Proxy Credentials

### 5.1 Authentication Layer

All proxy credentials are issued under Styxproxy's branding. You interact with Styxproxy's proxy infrastructure, not directly with any underlying provider. Styxproxy controls the authentication layer, enabling instant credential revocation on refund, abuse, or expiry.

### 5.2 Credential Delivery

Website: displayed on confirmation page. Telegram: sent in chat. Optional email: sent if you voluntarily provide your email address.

### 5.3 Credential Validity

Monthly plans: valid until the end of the purchased month. Data plans: valid until data quota is exhausted or plan expires. Credentials are automatically deactivated upon expiry.

---

## 6. Acceptable Use

You agree to use Styxproxy proxies only for lawful purposes. See our Acceptable Use Policy for full details.

Prohibited uses include: sending spam, fraud or financial crimes, unauthorized access to computer systems, illegal activities of any kind, network disruption or denial-of-service attacks, credential sharing.

Violations may result in immediate credential revocation without refund.

---

## 7. Ban Claims

If your proxy IP is blocked by a website or service:

Via Management Portal: Go to styxproxy.com/manage, enter your transaction reference, select Report a Ban, upload a screenshot showing the block.

Via Telegram: Send "Ban claim for order [tx_ref]" to @styxproxy.

Ban claims are reviewed by our team. Replacement credentials are issued at our discretion based on evidence provided.

---

## 8. Refunds

### 8.1 Refund Window

You may request a refund within 24 hours of receiving your credentials if: the proxy does not work at the time of delivery, or the service is materially different from what was described.

### 8.2 How to Request

Request a refund via styxproxy.com/manage or by contacting support via Telegram or email. All refund requests are reviewed manually.

### 8.3 Refund Processing

Approved refunds are processed within 5-10 business days to your original payment method.

### 8.4 Non-Refundable Circumstances

Refunds are not available for: requests made more than 24 hours after delivery, IPs blocked by your target website (this is a ban claim), change of mind after the 24-hour window, proxies that stopped working due to misuse, data plans where more than 10% of the quota has been used.

---

## 9. Data and Expiry

### 9.1 Monthly Plans

Unused days are not refundable or transferable. Your proxy access ends on the last day of your purchased period.

### 9.2 Data Plans

Unused data does not roll over. Renewing grants a fresh data quota.

---

## 10. Support

Support is available via:
- Telegram: @styxproxy
- Chat widget on the website
- Management portal at styxproxy.com/manage
- Email: hello@styxproxy.com

Response time: within 2 hours during business hours (9am-6pm WAT, Monday-Saturday).

---

## 11. Third-Party Services

### 11.1 Proxy Infrastructure

Proxy IPs are sourced from vetted third-party infrastructure providers. Styxproxy is not affiliated with, endorsed by, or responsible for the practices of any proxy provider.

### 11.2 Payment Processing

All payment processing is handled by our payment processor. Your payment data is subject to their privacy policy and terms. Styxproxy does not store card details or bank account information.

### 11.3 Free Trial

The free trial is supported by a third-party rewards provider. Customers who participate may encounter survey offers. Styxproxy is not responsible for third-party survey content.

---

## 12. Service Availability

Styxproxy does not guarantee uninterrupted service. Proxy IPs may be blocked by websites or services at any time. We will make reasonable efforts to notify customers of planned maintenance.

---

## 13. Limitation of Liability

To the maximum extent permitted by applicable law, Styxproxy shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising from the use of our services. Our total liability shall not exceed the amount you paid for the affected service.

---

## 14. Indemnification

You agree to indemnify and hold Styxproxy harmless from any claims, damages, or expenses arising from your use of our services in violation of these terms or applicable law.

---

## 15. Changes to These Terms

We may update these terms from time to time. Material changes will be communicated via Telegram or notice on our website. Changes to pricing take effect immediately for new orders. Changes to other terms take effect 14 days after notification.

---

## 16. Governing Law

These terms are governed by the laws of the Federal Republic of Nigeria. Any disputes shall be subject to the jurisdiction of Nigerian courts.

---

## 17. Contact

Styxproxy
- Telegram: @styxproxy
- Chat widget on styxproxy.com
- Email: hello@styxproxy.com
- Website: styxproxy.com
- Management portal: styxproxy.com/manage

Version: 2026-07-01
`;

module.exports = { content };

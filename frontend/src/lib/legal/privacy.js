const content = `<h1>Privacy Policy</h1>
<p><em>Styxproxy — Anonymous Proxy Service</em><br><em>Effective Date: July 1, 2026</em></p>

<h2>1. Introduction</h2>
<p>Styxproxy ("we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our services across any channel — our website or our Telegram bot.</p>
<p>We collect different information depending on how you interact with us. This policy is designed to be honest and clear about what we collect and why. By using Styxproxy, you consent to the data practices described in this policy.</p>

<h2>2. Our Service Channels</h2>
<p>We operate two independent channels: the website and the Telegram bot. Each collects different information.</p>

<h3>2.1 Website — Anonymous Orders</h3>
<p>When you order via styxproxy.com, we collect almost nothing.</p>
<ul>
<li><strong>Transaction reference</strong> — To identify your order — Retained 7 years</li>
<li><strong>Product purchased</strong> — To fulfil your order — Retained 7 years</li>
<li><strong>Amount paid</strong> — To process payment — Retained 7 years</li>
<li><strong>IP address (of our server)</strong> — Technical operation — Retained 90 days</li>
<li><strong>Email address (optional)</strong> — To send a receipt if you provide it — Retained until you request deletion</li>
</ul>
<p>We do not know your name, your device IP address, your phone number, or any other identifying information unless you voluntarily provide it. The transaction reference is your only order identifier. You do not create an account.</p>

<h3>2.2 Telegram Bot</h3>
<p>When you interact with the Styxproxy Telegram bot, we collect: your Telegram chat ID (to identify you and deliver messages), Telegram username if set, display name if shared, messages you send us (90 days), order history (7 years), and PIN if you set one. We do not collect your Telegram phone number.</p>

<h2>3. What We Collect</h2>

<h3>3.1 Information You Give Us</h3>
<ul>
<li>Order information: product, country, payment amount, transaction reference</li>
<li>Payment information: processed entirely by our payment processor. We never see your card number, bank account, or full bank details</li>
<li>Support communications: messages sent via the chat widget, Telegram, or email</li>
<li>PIN: if you choose to set a PIN to secure your chat account</li>
<li>Optional email: for receipt delivery on website orders</li>
<li>Ban claim evidence: screenshots or information you upload when raising a ban claim</li>
</ul>

<h3>3.2 Information We Create</h3>
<ul>
<li>Order records: transaction reference, product, amount, status, assigned IP, timestamps</li>
<li>Proxy credentials issued: username, hashed password, validity period</li>
<li>Free trial records: survey postback data, earned trial time</li>
<li>Audit logs: timestamped records of significant system events</li>
</ul>

<h3>3.3 Information We Do NOT Collect</h3>
<ul>
<li>Your device IP address (when using the website)</li>
<li>Your phone number</li>
<li>Your Telegram phone number</li>
<li>Your name (unless you voluntarily provide it)</li>
<li>Your location (unless you share it with us)</li>
<li>Cookies on our website (we do not use cookies)</li>
<li>Any data from third-party websites or services you access using Styxproxy proxies</li>
</ul>

<h2>4. How We Use Your Information</h2>
<ul>
<li><strong>Fulfill orders</strong> — transaction reference, product, payment</li>
<li><strong>Deliver proxy credentials</strong> — credentials, delivery channel</li>
<li><strong>Provide customer support</strong> — chat ID, order history</li>
<li><strong>Process refunds</strong> — transaction reference, payment information</li>
<li><strong>Investigate ban claims</strong> — transaction reference, evidence you provide</li>
<li><strong>Detect and prevent fraud</strong> — order patterns, payment verification</li>
<li><strong>Comply with legal obligations</strong> — financial records, audit logs</li>
<li><strong>Send service notifications</strong> — chat ID or email if provided</li>
</ul>

<h2>5. Data Sharing</h2>
<p><strong>We do not sell your data.</strong> We do not sell, rent, or trade your personal information to any third party.</p>
<p>We share only what is necessary with: our payment processor (payment processing), vetted third-party proxy infrastructure providers (to generate and deliver your proxy IP), Telegram (to deliver messages via their API), Theorem Reach (to track free trial earnings), and law enforcement as required by applicable law.</p>

<h3>5.1 Data Processors</h3>
<ul>
<li><strong>Payment processor</strong> — Payment data</li>
<li><strong>Telegram</strong> — Chat messages — telegram.org/privacy</li>
<li><strong>Theorem Reach</strong> — Survey data — theoremreach.com/privacy</li>
<li><strong>Email service</strong> — Transactional emails — resend.com/privacy</li>
</ul>

<h2>6. Data Retention</h2>
<ul>
<li><strong>Financial records</strong> (orders, payments, transaction reference) — 7 years — legal obligation</li>
<li><strong>Order fulfillment records</strong> — 7 years — contract performance</li>
<li><strong>Customer support messages</strong> — 90 days — operational efficiency</li>
<li><strong>Proxy credentials (issued IPs)</strong> — 7 years — audit trail</li>
<li><strong>Audit logs</strong> — 7 years — compliance</li>
<li><strong>Error logs</strong> — 1 year — system troubleshooting</li>
<li><strong>Rate limit logs</strong> — 90 days — security</li>
</ul>

<h3>6.1 Deletion Requests</h3>
<p>You may request deletion of your personal data at any time. To request deletion: on Telegram, send "delete my data" to @styxproxy; for website orders, email hello@styxproxy.com with your transaction reference.</p>
<p>We will delete your personal data within 30 days, except financial records required by law (7 years) and data we are required to retain under applicable law.</p>

<h2>7. Data Security</h2>
<h3>7.1 Technical Measures</h3>
<ul>
<li>HTTPS-only on all Styxproxy properties</li>
<li>Database with restricted network access (localhost connections only)</li>
<li>API keys and secrets stored in environment variables, not in code</li>
<li>Webhook verification on all incoming payment notifications</li>
<li>Rate limiting on all API endpoints</li>
<li>Audit logging of significant system events</li>
</ul>

<h3>7.2 Organizational Measures</h3>
<ul>
<li>Access to customer data restricted to authorized personnel only</li>
<li>No customer data in development or test environments</li>
<li>Secrets rotation policy: API keys rotated on a regular schedule</li>
</ul>

<h2>8. Your Rights</h2>
<ul>
<li><strong>Access your personal data</strong> — Request via any channel — we respond within 30 days</li>
<li><strong>Correct inaccurate data</strong> — Contact us with the correct information</li>
<li><strong>Delete your data</strong> — Send "delete my data" on Telegram or email us</li>
<li><strong>Object to processing</strong> — Contact us — we will assess the objection</li>
<li><strong>Data portability</strong> — We will provide your data in a machine-readable format</li>
<li><strong>Withdraw consent</strong> — Stop using the service and request deletion</li>
</ul>

<h2>9. Cookies and Tracking</h2>
<p><strong>We do not use cookies on our website.</strong> We do not store any cookies in your browser. We do not use third-party tracking pixels or analytics tools. We do not control the cookies or tracking used by Telegram.</p>

<h2>10. Children's Privacy</h2>
<p>Styxproxy services are not intended for persons under the age of 18. We do not knowingly collect data from minors. If we become aware that data from a minor has been collected, we will delete it immediately.</p>

<h2>11. International Data Transfers</h2>
<p>Styxproxy operates primarily in Nigeria. Some of our service providers operate internationally. When your data is transferred outside Nigeria, we ensure appropriate safeguards are in place through standard contractual clauses or equivalent legal mechanisms.</p>

<h2>12. Data Breach Notification</h2>
<p>In the event of a data breach that poses a risk to your rights and freedoms, we will notify the Nigeria Data Protection Commission within 72 hours of becoming aware of the breach. We will also notify affected customers via their contact channel as soon as reasonably practicable.</p>

<h2>13. Changes to This Policy</h2>
<p>We may update this Privacy Policy from time to time. Material changes will be communicated via Telegram or notice on our website.</p>

<h2>14. Contact Us</h2>
<p><strong>Styxproxy</strong></p>
<ul>
<li><strong>Telegram:</strong> @styxproxy</li>
<li><strong>Email:</strong> hello@styxproxy.com</li>
<li><strong>Website:</strong> styxproxy.com</li>
</ul>
<p>We will respond to all enquiries within 30 days.</p>`;

module.exports = { content };

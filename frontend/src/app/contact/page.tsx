'use client';

import { useState } from 'react';
import Header from '@/components/Header';
// Footer is rendered globally in layout.tsx

const faqs = [
  {
    q: 'How fast is delivery?',
    a: 'Website orders: credentials are ready in minutes after payment. Bank transfers may take a bit longer while the bank settles. If credentials don\'t appear shortly, contact us.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept all major payment methods: Visa, Mastercard, direct bank transfer, USSD, and QR code payments. All payments are processed securely via our payment processor. We do not accept crypto.',
  },
  {
    q: 'Can I get a refund?',
    a: 'Yes. If your proxy doesn\'t work and replacement fails, or if payment was made but proxy was never delivered, you\'re eligible for a full refund within 7 days of purchase.',
  },
  {
    q: 'What\'s your ban replacement policy?',
    a: 'If your IP gets banned within 24 hours of delivery (due to IP-level bans, not account bans), you\'re eligible for a free replacement. Contact us with your tx_ref to claim.',
  },
  {
    q: 'What\'s the difference between ISP, Residential, and Mobile proxies?',
    a: 'ISP proxies: Fast, stable, best value. Residential proxies: Real ISP IPs, harder to detect. Mobile 4G proxies: Highest trust on social media platforms (Instagram, TikTok). Datacenter proxies: Budget-friendly, general purpose.',
  },
  {
    q: 'Do I need an account to order?',
    a: 'No. Website orders require no account, no email, and no phone number. Your tx_ref (transaction reference) is your only order identifier.',
  },
  {
    q: 'How do I check my order status?',
    a: 'Go to /manage and enter your tx_ref to check credentials, expiry, and manage your order. You can also renew or raise a ban claim from there.',
  },
];

export default function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.email || !form.message) return;
    setLoading(true);
    setError('');
    await new Promise(r => setTimeout(r, 1000));
    setSent(true);
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 pt-24 pb-16">
        <div className="max-w-2xl mx-auto px-4">
          <h1 className="text-4xl font-bold mb-4 text-center">
            Get in <span className="gradient-text">Touch</span>
          </h1>
          <p className="text-[var(--muted)] text-center mb-10">
            Have a question? Need help? We're here.
          </p>

          {/* FAQ Accordion */}
          <div className="mb-12">
            <h2 className="text-xl font-bold mb-6 text-center">Frequently Asked Questions</h2>
            <div className="space-y-2">
              {faqs.map((faq, i) => (
                <div key={i} className="rounded-xl border border-[var(--border)] overflow-hidden">
                  <button
                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    className="w-full flex items-center justify-between px-4 py-3.5 text-left bg-[var(--card)] hover:bg-[var(--card-hover)] transition-colors"
                  >
                    <span className="font-medium text-sm pr-4">{faq.q}</span>
                    <svg
                      className={`w-4 h-4 shrink-0 transition-transform ${openFaq === i ? 'rotate-180' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {openFaq === i && (
                    <div className="px-4 py-3 bg-[var(--background)] border-t border-[var(--border)]">
                      <p className="text-sm text-[var(--muted)] leading-relaxed">{faq.a}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {sent ? (
            <div className="text-center p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <div className="w-16 h-16 rounded-full bg-[var(--primary)]/15 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
              </div>
              <h2 className="text-xl font-bold mb-2">Message Sent!</h2>
              <p className="text-[var(--muted)]">We'll get back to you within 24 hours.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Name</label>
                  <input required type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Your name" className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Email</label>
                  <input required type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} placeholder="your@email.com" className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Subject</label>
                <select value={form.subject} onChange={e => setForm({...form, subject: e.target.value})} className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors">
                  <option value="">Select a topic</option>
                  <option value="order">I want to order</option>
                  <option value="payment">Payment issue</option>
                  <option value="proxy-issue">Proxy not working</option>
                  <option value="refund">Refund request</option>
                  <option value="bulk">Bulk / business pricing</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Message</label>
                <textarea required rows={5} value={form.message} onChange={e => setForm({...form, message: e.target.value})} placeholder="Tell us how we can help..." className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors resize-none" />
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <button disabled={loading} className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 text-black font-semibold rounded-xl transition-colors">
                {loading ? 'Sending...' : 'Send Message'}
              </button>
            </form>
          )}

          {/* Alternative contact methods */}
          <div className="mt-12 pt-8 border-t border-[var(--border)]">
            <p className="text-center text-[var(--muted)] mb-6">Or reach us directly:</p>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-4">
              <a href="https://t.me/StyxproxyBot" target="_blank" rel="noopener noreferrer" className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-[#0088CC] hover:bg-[#0077B5] text-white font-semibold rounded-xl transition-colors min-w-[160px]">
                <svg className="w-5 h-5 shrink-0" fill="currentColor" viewBox="0 0 24 24"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
                Telegram
              </a>
              <a href="https://wa.me/2347032981049" target="_blank" rel="noopener noreferrer" className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-[#25D366] hover:bg-[#1da851] text-white font-semibold rounded-xl transition-colors min-w-[160px]">
                <svg className="w-5 h-5 shrink-0" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                WhatsApp
              </a>
              <a href="mailto:hello@bunche.ng" className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold rounded-xl transition-colors min-w-[160px]">
                <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                Email
              </a>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

// eslint-disable-next-line react-hooks/immutability, react-hooks/purity, react-hooks/set-state-in-effect
'use client';

import { useState } from 'react';
import Link from 'next/link';
import { CaretDown, Check, TelegramLogo, WhatsappLogo, Envelope } from '@phosphor-icons/react';
import { useChannelFlags } from '@/lib/feature-flags';

const faqs = [
  {
    q: 'How fast is delivery?',
    a: 'Website orders: credentials are ready within seconds of payment confirmation. If you do not see your credentials after payment, open the chat widget and say &quot;I paid but didn\'t get my proxy&quot; — share your transaction reference and Charon will look it up immediately.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept multiple payment methods: Flutterwave (card, bank transfer, USSD, QR), Paystack (card, bank transfer, USSD), Stripe (international cards), and Paynow (Bitcoin, USDT, crypto). All transactions are processed securely.',
  },
  {
    q: 'Can I get a refund?',
    a: 'Yes — within 24 hours of receiving your credentials, if the proxy did not work at the time of delivery. Contact us via the chat widget, Telegram (@styxproxy), or email support@styxproxy.com with your transaction reference.',
  },
  {
    q: "What's your ban replacement policy?",
    a: "If your IP gets blocked by a website after delivery (while the service was working at time of delivery), this is a ban claim — not a refund. Contact us via the chat widget, @styxproxy on Telegram, or support@styxproxy.com with your transaction reference.",
  },
  {
    q: "What's the difference between ISP, Residential, and Mobile proxies?",
    a: 'ISP proxies: Fast, stable, best value. Residential proxies: Real ISP IPs, harder to detect. Mobile 4G proxies: Highest trust on social media platforms (Instagram, TikTok). Datacenter proxies: Budget-friendly, general purpose.',
  },
  {
    q: 'Do I need an account to order?',
    a: 'No. Website orders require no account, no email, and no phone number. Your Flutterwave transaction reference is your only order identifier. Keep it to retrieve your credentials at any time.',
  },
  {
    q: 'How do I check my order status or retrieve my credentials?',
    a: 'Go to styxproxy.com/manage and enter your transaction reference. Or open the chat widget on the website and say &quot;I paid but didn\'t get my proxy&quot; — Charon will find your order and deliver your credentials in the chat.',
  },
  {
    q: "I paid but didn't get my proxy. What do I do?",
    a: "Don't worry — your proxy was likely generated. Open the chat widget on the website and say &quot;I paid but didn't get my proxy&quot;. Share your Flutterwave transaction reference when asked. Charon will find your order and send you your credentials directly in the chat.",
  },
];

export default function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const { isChannelEnabled, getChannelUrl } = useChannelFlags();

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
    <div className="min-h-screen relative overflow-hidden">

      {/* ── Hero background layers ── */}
      <div className="absolute inset-0 hero-bg-grid" />
      <div className="absolute inset-0 hero-bg-rings" />
      <div className="absolute inset-0 hero-bg-vignette" />
      <div className="hero-orb hero-orb-1" />
      <div className="hero-orb hero-orb-2" />
      <div className="hero-orb hero-orb-3" />

      {/* Top accent line */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-20 bg-gradient-to-b from-[var(--primary)] to-transparent opacity-50" />

      <main className="relative z-10 flex-1 pt-28 pb-16">
        <div className="max-w-2xl mx-auto px-6">

          {/* Hero heading */}
          <div className="text-center mb-12">
            <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">Support</p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-[var(--foreground)] mb-4 leading-tight">
              Get in <span className="text-[var(--primary)]">Touch</span>
            </h1>
            <p className="text-[var(--muted)] text-lg max-w-md mx-auto leading-relaxed">
              Questions, issues, or just curious? We&apos;re here.
            </p>
          </div>

          {/* FAQ Accordion */}
          <div className="mb-12">
            <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-4">FAQ</p>
            <div className="space-y-2">
              {faqs.map((faq, i) => (
                <div key={i} className="rounded-xl border border-[var(--border)] overflow-hidden bg-[var(--card)]">
                  <button
                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    className="w-full flex items-center justify-between px-5 py-4 text-left hover:text-[var(--primary)] transition-colors"
                  >
                    <span className="font-medium text-sm pr-4 text-[var(--foreground)]">{faq.q}</span>
                    <CaretDown className={`w-4 h-4 shrink-0 text-[var(--muted)] transition-transform ${openFaq === i ? 'rotate-180' : ''}`} />
                  </button>
                  {openFaq === i && (
                    <div className="px-5 py-4 bg-[var(--background)] border-t border-[var(--border)]">
                      <p className="text-sm text-[var(--muted)] leading-relaxed">{faq.a}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="section-divider-glow mb-12" />

          {/* Contact form */}
          <div className="mb-12">
            <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-4">Send a message</p>
            <h2 className="text-xl font-bold text-[var(--foreground)] mb-6">Write to us</h2>

            {sent ? (
              <div className="text-center p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
                <div className="w-16 h-16 rounded-full bg-[var(--primary)]/15 flex items-center justify-center mx-auto mb-4">
                  <Check className="w-8 h-8 text-[var(--primary)]" weight="bold" />
                </div>
                <h2 className="text-xl font-bold mb-2">Message Sent!</h2>
                <p className="text-[var(--muted)]">We&apos;ll get back to you within 24 hours.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-[var(--muted)] mb-2">Name</label>
                    <input required type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Your name" className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[var(--muted)] mb-2">Email</label>
                    <input required type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} placeholder="your@email.com" className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors text-sm" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[var(--muted)] mb-2">Subject</label>
                  <select value={form.subject} onChange={e => setForm({...form, subject: e.target.value})} className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors text-sm">
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
                  <label className="block text-xs font-medium text-[var(--muted)] mb-2">Message</label>
                  <textarea required rows={5} value={form.message} onChange={e => setForm({...form, message: e.target.value})} placeholder="Tell us how we can help..." className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors resize-none text-sm" />
                </div>
                {error && <p className="text-red-400 text-sm">{error}</p>}
                <button disabled={loading} className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 text-black font-bold rounded-xl transition-colors text-sm">
                  {loading ? 'Sending...' : 'Send Message'}
                </button>
              </form>
            )}
          </div>

          {/* Direct contact channels */}
          <div className="section-divider mb-10" />
          <div className="text-center mb-6">
            <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--muted)]">Or reach us directly</p>
          </div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3">
            {isChannelEnabled('telegram') ? (
              <a href={getChannelUrl('telegram') || 'https://t.me/StyxproxyBot'} target="_blank" rel="noopener noreferrer" className="flex-1 sm:flex-none flex items-center justify-center gap-2.5 px-6 py-3.5 bg-[#0088CC] hover:bg-[#0077B5] text-white font-bold rounded-xl transition-colors text-sm min-w-[160px]">
                <TelegramLogo className="w-5 h-5 shrink-0" weight="fill" />
                Telegram
              </a>
            ) : (
              <span className="flex-1 sm:flex-none flex items-center justify-center gap-2.5 px-6 py-3.5 bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] font-semibold rounded-xl text-sm min-w-[160px] cursor-not-allowed">
                <TelegramLogo className="w-5 h-5 shrink-0" weight="fill" />
                Telegram
              </span>
            )}
            {isChannelEnabled('whatsapp') ? (
              <a href={getChannelUrl('whatsapp') || 'https://wa.me/2347032981049'} target="_blank" rel="noopener noreferrer" className="flex-1 sm:flex-none flex items-center justify-center gap-2.5 px-6 py-3.5 bg-[#25D366] hover:bg-[#1da851] text-white font-bold rounded-xl transition-colors text-sm min-w-[160px]">
                <WhatsappLogo className="w-5 h-5 shrink-0" weight="fill" />
                WhatsApp
              </a>
            ) : (
              <span className="flex-1 sm:flex-none flex items-center justify-center gap-2.5 px-6 py-3.5 bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] font-semibold rounded-xl text-sm min-w-[160px] cursor-not-allowed">
                <WhatsappLogo className="w-5 h-5 shrink-0" weight="fill" />
                WhatsApp
              </span>
            )}
            <a href="mailto:support@styxproxy.com" className="flex-1 sm:flex-none flex items-center justify-center gap-2.5 px-6 py-3.5 bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-bold rounded-xl transition-colors text-sm min-w-[160px]">
              <Envelope className="w-5 h-5 shrink-0" />
              Email
            </a>
          </div>

          {/* CTA */}
          <div className="section-divider mt-12 mb-10" />
          <div className="text-center">
            <p className="text-[var(--muted)] text-sm mb-4">Prefer to order now and figure it out later?</p>
            <Link href="/order" className="inline-block px-8 py-3.5 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-bold text-sm transition-colors">
              Order Now →
            </Link>
          </div>

        </div>
      </main>
    </div>
  );
}

'use client';

import { useState } from 'react';
import Header from '@/components/Header';
import { useChannelFlags } from '@/lib/feature-flags';
import { CaretDown, Check, TelegramLogo, WhatsappLogo, Envelope } from '@phosphor-icons/react';
// Footer is rendered globally in layout.tsx

const faqs = [
  {
    q: 'How fast is delivery?',
    a: 'Website orders: credentials are ready within seconds of payment confirmation. If you do not see your credentials after payment, open the chat widget and say "I paid but didn\'t get my proxy" — share your transaction reference and Charon will look it up immediately.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept all major payment methods via Flutterwave: Visa, Mastercard, direct bank transfer, USSD, and QR code. All payments are processed securely. We do not accept crypto.',
  },
  {
    q: 'Can I get a refund?',
    a: 'Yes — within 24 hours of receiving your credentials, if the proxy did not work at the time of delivery. Contact us via the chat widget, Telegram (@styxproxy), or email support@styxproxy.com with your transaction reference.',
  },
  {
    q: 'What\'s your ban replacement policy?',
    a: 'If your IP gets blocked by a website after delivery (while the service was working at time of delivery), this is a ban claim — not a refund. Contact us via the chat widget, @styxproxy on Telegram, or support@styxproxy.com with your transaction reference.',
  },
  {
    q: 'What\'s the difference between ISP, Residential, and Mobile proxies?',
    a: 'ISP proxies: Fast, stable, best value. Residential proxies: Real ISP IPs, harder to detect. Mobile 4G proxies: Highest trust on social media platforms (Instagram, TikTok). Datacenter proxies: Budget-friendly, general purpose.',
  },
  {
    q: 'Do I need an account to order?',
    a: 'No. Website orders require no account, no email, and no phone number. Your Flutterwave transaction reference is your only order identifier. Keep it to retrieve your credentials at any time.',
  },
  {
    q: 'How do I check my order status or retrieve my credentials?',
    a: 'Go to styxproxy.com/manage and enter your transaction reference. Or open the chat widget on the website and say "I paid but didn\'t get my proxy" — Charon will look up your order and deliver your credentials in the chat.',
  },
  {
    q: 'I paid but didn\'t get my proxy. What do I do?',
    a: 'Don\'t worry — your proxy was likely generated. Open the chat widget on the website and say "I paid but didn\'t get my proxy". Share your Flutterwave transaction reference when asked. Charon will find your order and send you your credentials directly in the chat. You can also check styxproxy.com/manage.',
  },
];

export default function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  
  // Channel feature flags
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
                    <CaretDown className={`w-4 h-4 shrink-0 transition-transform ${openFaq === i ? 'rotate-180' : ''}`} />
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
                <Check className="w-8 h-8 text-[var(--primary)]" weight="bold" />
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

          {/* Alternative contact methods - email is primary, Telegram/WhatsApp conditional */}
          <div className="mt-12 pt-8 border-t border-[var(--border)]">
            <p className="text-center text-[var(--muted)] mb-6">Or reach us directly:</p>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-4">
              {/* Telegram - conditional */}
              {isChannelEnabled('telegram') ? (
                <a href={getChannelUrl('telegram') || 'https://t.me/StyxproxyBot'} target="_blank" rel="noopener noreferrer" className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-[#0088CC] hover:bg-[#0077B5] text-white font-semibold rounded-xl transition-colors min-w-[160px]">
                  <TelegramLogo className="w-5 h-5 shrink-0" weight="fill" />
                  Telegram
                </a>
              ) : (
                <span className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] font-semibold rounded-xl min-w-[160px] cursor-not-allowed">
                  <TelegramLogo className="w-5 h-5 shrink-0" weight="fill" />
                  Telegram
                </span>
              )}
              
              {/* WhatsApp - conditional */}
              {isChannelEnabled('whatsapp') ? (
                <a href={getChannelUrl('whatsapp') || 'https://wa.me/2347032981049'} target="_blank" rel="noopener noreferrer" className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-[#25D366] hover:bg-[#1da851] text-white font-semibold rounded-xl transition-colors min-w-[160px]">
                  <WhatsappLogo className="w-5 h-5 shrink-0" weight="fill" />
                  WhatsApp
                </a>
              ) : (
                <span className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] font-semibold rounded-xl min-w-[160px] cursor-not-allowed">
                  <WhatsappLogo className="w-5 h-5 shrink-0" weight="fill" />
                  WhatsApp
                </span>
              )}
              
              {/* Email - always available */}
              <a href="mailto:support@styxproxy.com" className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold rounded-xl transition-colors min-w-[160px]">
                <Envelope className="w-5 h-5 shrink-0" />
                Email
              </a>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
